"""
Milwaukee Tool (milwaukeetool.com) price fetcher.

Milwaukee's site is generally less aggressive about bot-detection than
Home Depot, but it's still worth being polite (low polling frequency,
a real-looking User-Agent).

Approach: same JSON-LD-first strategy as Home Depot, falling back to
generic meta tags.
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
    soup = BeautifulSoup(resp.text, "lxml")

    price, name = _from_json_ld(soup)
    if price is not None:
        return {"price": price, "name": name, "in_stock": None, "error": None}

    result = generic.fetch(url)
    if result["price"] is None:
        result["error"] = "milwaukeetool.com markup not recognized - selectors likely need updating."
    return result


def _from_json_ld(soup: BeautifulSoup):
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

            return price, name

    return None, None
