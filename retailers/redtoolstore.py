"""
Red Tool Store (redtoolstore.com) price fetcher.

Red Tool Store blocks plain automated requests at the network level (likely
Cloudflare or similar) - both its Shopify .json endpoint and its normal HTML
pages return 403 to non-browser requests. Header tweaks don't get around
this, so instead of fetching the page directly, this searches Google
Shopping via SerpApi for the product and looks for a result whose listing
is from redtoolstore.com.

Trade-offs vs. a direct URL fetch:
  - Uses one SerpApi search per item per run (counts against your quota,
    same as the Home Depot fetcher).
  - Not guaranteed to find every SKU - depends on whether Google Shopping
    has indexed that specific Red Tool Store listing.
  - The search query is guessed from the product URL's slug, since the
    sheet only stores a URL. If matching seems off, try setting a more
    exact "Name" in the sheet - see README.
"""
import re

import requests

import config


def fetch(url: str) -> dict:
    if not config.SERPAPI_KEY:
        return {"price": None, "name": None, "in_stock": None, "error": "SERPAPI_KEY is not set (check GitHub secret + workflow env)."}

    query = _query_from_url(url)
    if not query:
        return {"price": None, "name": None, "in_stock": None, "error": "Could not derive a search query from this Red Tool Store URL."}

    params = {
        "engine": "google_shopping",
        "q": query,
        "gl": "us",
        "hl": "en",
        "api_key": config.SERPAPI_KEY,
    }

    try:
        response = requests.get("https://serpapi.com/search", params=params, timeout=config.REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as e:
        return {"price": None, "name": None, "in_stock": None, "error": f"SerpApi request failed: {e}"}

    try:
        data = response.json()
    except ValueError:
        return {"price": None, "name": None, "in_stock": None, "error": f"SerpApi returned non-JSON response (HTTP {response.status_code})."}

    if "error" in data:
        return {"price": None, "name": None, "in_stock": None, "error": f"SerpApi error: {data['error']}"}

    results = data.get("shopping_results") or []
    match = _find_redtoolstore_result(results)

    if not match:
        return {
            "price": None,
            "name": None,
            "in_stock": None,
            "error": f"No Red Tool Store listing found in Google Shopping results for query: \"{query}\".",
        }

    price = _parse_price(match.get("price") or match.get("extracted_price"))
    if price is None:
        return {"price": None, "name": match.get("title"), "in_stock": None, "error": "Found a Red Tool Store result but couldn't parse its price."}

    return {"price": price, "name": match.get("title"), "in_stock": None, "error": None}


def _query_from_url(url: str) -> str:
    match = re.search(r"/products/([a-z0-9\-]+)", url, re.IGNORECASE)
    if not match:
        return ""
    slug = match.group(1)
    words = slug.split("-")
    return " ".join(words)


def _find_redtoolstore_result(results: list) -> dict | None:
    for item in results:
        source = (item.get("source") or "").lower()
        link = (item.get("link") or item.get("product_link") or "").lower()
        if "red tool store" in source or "redtoolstore.com" in link:
            return item
    return None


def _parse_price(raw):
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    cleaned = str(raw).replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None
