"""
Fallback scraper for any URL that doesn't match a known retailer.

Tries common patterns first (schema.org / Open Graph meta tags), which a
surprising number of ecommerce sites include even if their visible HTML
structure changes often. This is a best-effort fallback, not a guarantee.
"""
import re

import requests
from bs4 import BeautifulSoup

import config


def fetch(url: str) -> dict:
    resp = requests.get(
        url,
        headers={"User-Agent": config.USER_AGENT},
        timeout=config.REQUEST_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    price = _find_price_meta(soup)
    name = _find_name_meta(soup)

    if price is None:
        return {
            "price": None,
            "name": name,
            "in_stock": None,
            "error": "No price found with generic meta-tag patterns - this site needs a custom scraper.",
        }

    return {"price": price, "name": name, "in_stock": None, "error": None}


def _find_price_meta(soup: BeautifulSoup):
    # Open Graph / schema.org patterns used by many storefronts
    candidates = [
        ("meta", {"property": "product:price:amount"}),
        ("meta", {"property": "og:price:amount"}),
        ("meta", {"itemprop": "price"}),
    ]
    for tag, attrs in candidates:
        el = soup.find(tag, attrs=attrs)
        if el and el.get("content"):
            return _parse_price(el["content"])

    # Last resort: look for a $ amount near the word "price" in the raw text
    match = re.search(r"\$\s?([0-9][0-9,]*\.[0-9]{2})", soup.get_text())
    if match:
        return _parse_price(match.group(1))
    return None


def _find_name_meta(soup: BeautifulSoup):
    el = soup.find("meta", attrs={"property": "og:title"})
    if el and el.get("content"):
        return el["content"].strip()
    if soup.title:
        return soup.title.get_text().strip()
    return None


def _parse_price(raw: str):
    cleaned = raw.replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None
