"""
General Google Shopping price fetcher via SerpApi.

Unlike the other retailer files, this doesn't scrape a specific store's
page - it searches Google Shopping for the product (query derived from the
URL you put in the sheet) and returns the LOWEST price found across all
listed retailers, plus which retailer had it. This is a good fit for items
where you don't care which store you buy from, just the best price - or
for sites that block direct scraping entirely (like Red Tool Store).

Trade-offs:
  - Uses one SerpApi search per item per run (same quota as the Home Depot
    fetcher - be mindful of item count vs. your SerpApi plan).
  - Query is guessed from the URL's slug, so results depend on how well
    that guess matches real listings. If matches look wrong, try using a
    cleaner/more specific URL (even a Google search URL with the product
    name in the path works, since only the slug text matters).
  - Since it's not tied to a specific retailer, "Current Price" in your
    sheet reflects whichever store was cheapest THAT run - it may bounce
    between retailers over time. The Notes/Name field shows which store
    had the winning price.
"""
import re

import requests

import config


def fetch(url: str) -> dict:
    if not config.SERPAPI_KEY:
        return {"price": None, "name": None, "in_stock": None, "error": "SERPAPI_KEY is not set (check GitHub secret + workflow env)."}

    query = _query_from_url(url)
    if not query:
        return {"price": None, "name": None, "in_stock": None, "error": "Could not derive a search query from this URL."}

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
    if not results:
        return {"price": None, "name": None, "in_stock": None, "error": f"No Google Shopping results found for query: \"{query}\"."}

    best = _lowest_priced(results)
    if best is None:
        return {"price": None, "name": None, "in_stock": None, "error": "Found results but none had a parseable price."}

    price, item = best
    store = item.get("source") or "unknown store"
    title = item.get("title") or query
    display_name = f"{title} (lowest: {store})"

    return {"price": price, "name": display_name, "in_stock": None, "error": None}


def _query_from_url(url: str) -> str:
    # Try to pull a readable product name out of common URL shapes:
    # e.g. .../products/milwaukee-2737-20-jig-saw or .../p/Milwaukee-Jig-Saw/12345
    match = re.search(r"/(?:products|p)/([a-z0-9\-]+)", url, re.IGNORECASE)
    if match:
        slug = match.group(1)
    else:
        # Fall back to the last non-empty path segment
        segments = [s for s in url.split("/") if s and "." not in s]
        slug = segments[-1] if segments else ""

    # Strip a trailing numeric ID segment (common on Home Depot-style URLs)
    words = [w for w in slug.split("-") if not w.isdigit()]
    return " ".join(words).strip()


def _lowest_priced(results: list):
    best_price = None
    best_item = None
    for item in results:
        price = _parse_price(item.get("price") or item.get("extracted_price"))
        if price is None:
            continue
        if best_price is None or price < best_price:
            best_price = price
            best_item = item
    if best_item is None:
        return None
    return best_price, best_item


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
