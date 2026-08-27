"""
Dispatches a product URL to the right retailer-specific price fetcher.

Each fetcher function takes a URL and returns a dict:
    {"price": float | None, "name": str | None, "in_stock": bool | None, "error": str | None}

A None price with no error usually means the page structure changed and the
CSS selector needs updating - check the "error" field for a hint.
"""
from urllib.parse import urlparse

from . import homedepot, milwaukeetool, redtoolstore, acehardware, generic


def get_fetcher(url: str):
    host = urlparse(url).netloc.lower()

    if "homedepot.com" in host:
        return homedepot.fetch
    if "redtoolstore.com" in host:
        return redtoolstore.fetch
    if "milwaukeetool.com" in host:
        return milwaukeetool.fetch
    if "acehardware.com" in host:
        return acehardware.fetch

    # Fallback: generic scraper that guesses at common price patterns.
    # Works sometimes, not reliable - flagged in the result.
    return generic.fetch


def fetch_price(url: str) -> dict:
    fetcher = get_fetcher(url)
    try:
        return fetcher(url)
    except Exception as e:  # noqa: BLE001 - we want to keep the loop going for other rows
        return {"price": None, "name": None, "in_stock": None, "error": f"{type(e).__name__}: {e}"}
