from decimal import Decimal

import pytest

from price_monitor.models import ProductObservation
from price_monitor.scraper import ScraperError, TemuScraper


class FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeHttp:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def product():
    return type("Product", (), {"url": "https://www.temu.com/lamp.html", "name": "Lamp"})()


def test_fetches_price_from_json_ld_product_data():
    html = '''<script type="application/ld+json">
      {"@type":"Product","name":"Bright Lamp","offers":{"price":"14.95","priceCurrency":"USD"}}
    </script>'''
    http = FakeHttp(FakeResponse(html))

    observation = TemuScraper(http).fetch(product())

    assert isinstance(observation, ProductObservation)
    assert observation.title == "Bright Lamp"
    assert observation.price == Decimal("14.95")
    assert observation.currency == "USD"
    assert http.calls[0][1]["timeout"] == 20


def test_fetches_product_from_json_ld_graph_and_type_array():
    html = '''<script type="application/ld+json">
      {"@graph":[{"@type":["Thing","Product"],"name":"Graph Lamp","offers":{"price":"11.25","priceCurrency":"USD"}}]}
    </script>'''

    result = TemuScraper(FakeHttp(FakeResponse(html))).fetch(product())

    assert result.title == "Graph Lamp"
    assert result.price == Decimal("11.25")


def test_fetches_price_from_meta_tags_when_json_ld_is_missing():
    html = '<meta property="og:title" content="Desk Lamp"><meta itemprop="price" content="9.50"><meta itemprop="priceCurrency" content="EUR">'

    observation = TemuScraper(FakeHttp(FakeResponse(html))).fetch(product())

    assert observation.title == "Desk Lamp"
    assert observation.price == Decimal("9.50")
    assert observation.currency == "EUR"


def test_rejects_page_without_a_valid_price():
    with pytest.raises(ScraperError, match="price"):
        TemuScraper(FakeHttp(FakeResponse("<html><title>Unavailable</title></html>"))).fetch(product())


def test_wraps_http_failures_as_scraper_errors():
    with pytest.raises(ScraperError, match="fetch"):
        TemuScraper(FakeHttp(FakeResponse("", status_code=503))).fetch(product())
