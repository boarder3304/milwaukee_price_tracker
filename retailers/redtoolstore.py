"""
Red Tool Store (redtoolstore.com) price fetcher.

Red Tool Store runs on Shopify. Shopify normally exposes a free JSON
endpoint for any product page (append ".json" to the URL), but some
Shopify stores block that endpoint for non-browser-like requests (via
Cloudflare or similar) while still allowing the regular HTML page through.

Strategy: try the .json endpoint first (fast, clean data). If that's
blocked (403) or fails, fall back to scraping the normal product page's
embedded JSON-LD, which is present on essentially all Shopify themes.
"""
import json

import requests
from bs4 import BeautifulSoup

import config

BROWSER_HEADERS = {
    "User-Agent": config.USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.redtoolstore.com/",
}


def fetch(url: str) -> dict:
    clean_url = url.split("?")[0].rstrip("/")

    result = _try_json_endpoint(clean_url + ".json")
    if result["price"] is not None:
        return result

    # .json failed or was blocked - fall back to scraping the HTML page directly
    html_result = _try_html_page(clean_url)
    if html_result["price"] is not None:
        return html_result

    # Neither worked - report the HTML attempt's outcome (the more recent,
    # more informative attempt), but include the JSON error too for context.
    combined_error = f"{html_result['error']} (JSON endpoint also failed: {result['error']})"
    html_result["error"] = combined_error
    return html_result


def _try_json_endpoint(json_url: str) -> dict:
    try:
        resp = requests.get(json_url, headers=BROWSER_HEADERS, timeout=config.REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as e:
        return {"price": None, "name": None, "in_stock": None, "error": f"Request failed: {e}"}

    if resp.status_code == 403:
        return {"price": None, "name": None, "in_stock": None, "error": "JSON endpoint returned 403 (blocked) - falling back to HTML."}
    if resp.status_code == 404:
        return {"price": None, "name": None, "in_stock": None, "error": "Product not found (404) at .json endpoint."}
    if resp.status_code != 200:
        return {"price": None, "name": None, "in_stock": None, "error": f"JSON endpoint returned HTTP {resp.status_code}."}

    try:
        data = resp.json()
    except ValueError:
        return {"price": None, "name": None, "in_stock": None, "error": "JSON endpoint returned non-JSON response."}

    product = data.get("product")
    if not product:
        return {"price": None, "name": None, "in_stock": None, "error": "No 'product' field in JSON response."}

    return _extract_from_shopify_product(product)


def _try_html_page(url: str) -> dict:
    try:
        resp = requests.get(url, headers=BROWSER_HEADERS, timeout=config.REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as e:
        return {"price": None, "name": None, "in_stock": None, "error": f"HTML page request failed: {e}"}

    if resp.status_code != 200:
        return {"price": None, "name": None, "in_stock": None, "error": f"HTML page returned HTTP {resp.status_code} - store may be blocking automated requests entirely."}

    soup = BeautifulSoup(resp.text, "lxml")

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
        except (json.JSONDecodeError, TypeError):
            continue

        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if not isinstance(item, dict) or item.get("@type") != "Product":
                continue

            name = item.get("name")
            offers = item.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}

            price = offers.get("price")
            try:
                price = float(price) if price is not None else None
            except (TypeError, ValueError):
                price = None

            if price is not None:
                availability = offers.get("availability", "")
                in_stock = "InStock" in availability if availability else None
                return {"price": price, "name": name, "in_stock": in_stock, "error": None}

    return {"price": None, "name": None, "in_stock": None, "error": "Could not find product JSON-LD on the HTML page either - site may need a different approach."}


def _extract_from_shopify_product(product: dict) -> dict:
    name = product.get("title")
    variants = product.get("variants") or []

    if not variants:
        return {"price": None, "name": name, "in_stock": None, "error": "Product has no variants listed."}

    variant = next((v for v in variants if v.get("available")), variants[0])

    price = variant.get("price")
    try:
        price = float(price) if price is not None else None
    except (TypeError, ValueError):
        price = None

    if price is None:
        return {"price": None, "name": name, "in_stock": None, "error": "Could not parse a price from the variant data."}

    return {"price": price, "name": name, "in_stock": variant.get("available", False), "error": None}
