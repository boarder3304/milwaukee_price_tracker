"""
Amazon price fetcher.

Amazon actively blocks plain scraping, so this uses the Keepa API instead
(https://keepa.com/#!api - a paid API with a cheap entry tier, ~$0-20/mo
depending on request volume for a small personal tracker). Requires
KEEPA_API_KEY to be set.

If no Keepa key is configured, this returns an error explaining that Amazon
support is disabled until one is added, rather than silently failing.
"""
import re

import requests

import config

ASIN_RE = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})")


def _extract_asin(url: str):
    match = ASIN_RE.search(url)
    return match.group(1) if match else None


def fetch(url: str) -> dict:
    if not config.KEEPA_API_KEY:
        return {
            "price": None,
            "name": None,
            "in_stock": None,
            "error": "Amazon tracking needs a Keepa API key (KEEPA_API_KEY) - see README.",
        }

    asin = _extract_asin(url)
    if not asin:
        return {
            "price": None,
            "name": None,
            "in_stock": None,
            "error": "Could not find an ASIN in this Amazon URL - use the /dp/XXXXXXXXXX link format.",
        }

    resp = requests.get(
        "https://api.keepa.com/product",
        params={"key": config.KEEPA_API_KEY, "domain": 1, "asin": asin},
        timeout=config.REQUEST_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    data = resp.json()

    products = data.get("products") or []
    if not products:
        return {"price": None, "name": None, "in_stock": None, "error": "Keepa returned no product data for this ASIN."}

    product = products[0]
    name = product.get("title")

    # Keepa prices are in cents; -1 means "no current value"
    csv_data = product.get("csv") or []
    # Index 1 = AMAZON price history, index 3 = NEW price history (3rd party new)
    price_cents = _latest_valid(csv_data, index=1) or _latest_valid(csv_data, index=3)

    if price_cents is None or price_cents < 0:
        return {"price": None, "name": name, "in_stock": None, "error": "No current price available from Keepa (may be out of stock)."}

    return {"price": price_cents / 100.0, "name": name, "in_stock": True, "error": None}


def _latest_valid(csv_data, index: int):
    if index >= len(csv_data) or not csv_data[index]:
        return None
    series = csv_data[index]
    # Keepa CSV series alternate [timestamp, value, timestamp, value, ...]
    for i in range(len(series) - 1, 0, -2):
        value = series[i]
        if value is not None and value >= 0:
            return value
    return None
