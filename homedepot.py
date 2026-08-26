"""
Home Depot price fetcher.

IMPORTANT: Home Depot uses bot-detection (Akamai) and changes its page
structure periodically. A plain requests.get() will sometimes get blocked
or served a CAPTCHA page instead of the real product page. If this starts
returning None consistently, that's the likely cause - see README for
mitigation options (rotating headers, a headless browser, or lower
frequency polling).

Approach: try Home Depot's embedded JSON-LD product data first (most
reliable when it works), fall back to the generic meta-tag scraper.
"""
import json

import requests
from bs4 import BeautifulSoup

import config
from . import generic


def fetch(url: str) -> dict:
    resp = requests.get(
        url,
        headers={"User-Agent": config.USER_AGENT},
        timeout=config.REQUEST_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()

    if "Access Denied" in resp.text or "captcha" in resp.text.lower():
        return {
            "price": None,
            "name": None,
            "in_stock": None,
            "error": "Home Depot returned a bot-check page instead of product data. "
                     "Try lowering polling frequency or see README for workarounds.",
        }

    soup = BeautifulSoup(resp.text, "lxml")
    price, name, in_stock = _from_json_ld(soup)

    if price is not None:
        return {"price": price, "name": name, "in_stock": in_stock, "error": None}

    # Fall back to generic meta-tag scraping
    result = generic.fetch(url)
    if result["price"] is None:
        result["error"] = "Home Depot markup not recognized - selectors likely need updating."
    return result


def _from_json_ld(soup: BeautifulSoup):
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
        except (json.JSONDecodeError, TypeError):
            continue

        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if not isinstance(item, dict):
                continue
            if item.get("@type") != "Product":
                continue

            name = item.get("name")
            offers = item.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}

            price = offers.get("price")
            availability = offers.get("availability", "")
            in_stock = "InStock" in availability if availability else None

            try:
                price = float(price) if price is not None else None
            except (TypeError, ValueError):
                price = None

            return price, name, in_stock

    return None, None, None
