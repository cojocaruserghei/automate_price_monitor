"""Temu HTTP retrieval and HTML/structured-data parsing."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol

import requests
from bs4 import BeautifulSoup

from .models import ProductObservation


class ScraperError(RuntimeError):
    """Raised when a product cannot be fetched or parsed safely."""


class HttpClient(Protocol):
    def get(self, url: str, **kwargs: Any) -> Any: ...


class TemuScraper:
    def __init__(self, http_client: HttpClient | None = None, timeout: int = 20):
        self.http_client = http_client or requests
        self.timeout = timeout

    def fetch(self, product: Any) -> ProductObservation:
        try:
            response = self.http_client.get(
                product.url,
                timeout=self.timeout,
                headers={"User-Agent": "PriceMonitor/0.1 (+portfolio project)"},
            )
            response.raise_for_status()
        except Exception as exc:
            raise ScraperError(f"Could not fetch product page: {exc}") from exc

        soup = BeautifulSoup(response.text, "html.parser")
        title, price, currency = self._parse(soup)
        if price is None:
            raise ScraperError(f"Could not find a valid price for {product.url}")
        return ProductObservation(product.url, title or product.name, price, currency)

    @staticmethod
    def _parse(soup: BeautifulSoup) -> tuple[str | None, Decimal | None, str | None]:
        title = None
        price_text = None
        currency = None

        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or script.get_text())
            except json.JSONDecodeError:
                continue
            candidates = data if isinstance(data, list) else [data]
            expanded = []
            for candidate in candidates:
                if isinstance(candidate, dict) and isinstance(candidate.get("@graph"), list):
                    expanded.extend(candidate["@graph"])
                else:
                    expanded.append(candidate)
            for item in expanded:
                if not isinstance(item, dict):
                    continue
                item_type = item.get("@type")
                is_product = item_type == "Product" or (isinstance(item_type, list) and "Product" in item_type)
                if is_product:
                    title = title or item.get("name")
                    offers = item.get("offers", {})
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    if isinstance(offers, dict):
                        price_text = price_text or offers.get("price")
                        currency = currency or offers.get("priceCurrency")

        title = title or TemuScraper._content(soup, "meta[property='og:title']")
        price_text = price_text or TemuScraper._attribute(soup, "meta[itemprop='price']", "content")
        currency = currency or TemuScraper._attribute(soup, "meta[itemprop='priceCurrency']", "content")
        try:
            price = Decimal(str(price_text)) if price_text is not None else None
        except (InvalidOperation, ValueError):
            price = None
        if price is not None and price < 0:
            price = None
        return title, price, currency

    @staticmethod
    def _content(soup: BeautifulSoup, selector: str) -> str | None:
        node = soup.select_one(selector)
        return node.get("content", "").strip() if node else None

    @staticmethod
    def _attribute(soup: BeautifulSoup, selector: str, attribute: str) -> str | None:
        node = soup.select_one(selector)
        value = node.get(attribute) if node else None
        return value.strip() if isinstance(value, str) else None
