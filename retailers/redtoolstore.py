"""
Red Tool Store (redtoolstore.com) price fetcher.

Red Tool Store runs on Shopify. Shopify exposes a free, unauthenticated
JSON endpoint for any product page - just append ".json" to the product
URL - which is far more reliable than scraping HTML. No API key needed.

Example:
    https://www.redtoolstore.com/products/some-product-handle
    -> https://www.redtoolstore.com/products/some-product-handle.json
"""
import requests

import config


def fetch(url: str) -> dict:
    json_url = url.split("?")[0].rstrip("/") + ".json"

    try:
        resp = requests.get(
            json_url,
            headers={"User-Agent": config.USER_AGENT},
            timeout=config.REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        return {"price": None, "name": None, "in_stock": None, "error": f"Request failed: {e}"}

    if resp.status_code == 404:
        return {"price": None, "name": None, "in_stock": None, "error": "Product not found (404) - check the URL is a valid /products/... page."}
    resp.raise_for_status()

    try:
        data = resp.json()
    except ValueError:
        return {"price": None, "name": None, "in_stock": None, "error": "Red Tool Store returned non-JSON response."}

    product = data.get("product")
    if not product:
        return {"price": None, "name": None, "in_stock": None, "error": "No 'product' field in Red Tool Store's JSON response."}

    name = product.get("title")
    variants = product.get("variants") or []

    if not variants:
        return {"price": None, "name": name, "in_stock": None, "error": "Product has no variants listed."}

    # Use the first available (in-stock) variant's price if there is one,
    # otherwise fall back to the first variant regardless of stock.
    variant = next((v for v in variants if v.get("available")), variants[0])

    price = variant.get("price")
    try:
        price = float(price) if price is not None else None
    except (TypeError, ValueError):
        price = None

    if price is None:
        return {"price": None, "name": name, "in_stock": None, "error": "Could not parse a price from the variant data."}

    return {
        "price": price,
        "name": name,
        "in_stock": variant.get("available", False),
        "error": None,
    }
