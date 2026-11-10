import json

import pytest

from price_monitor.config import (
    ConfigurationError,
    load_notifications_config,
    load_products_config,
)


def write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def test_loads_multiple_products_with_decimal_thresholds(tmp_path):
    path = tmp_path / "products.json"
    write_json(
        path,
        {
            "products": [
                {"name": "Lamp", "url": "https://www.temu.com/lamp.html", "threshold": 12.50},
                {"url": "https://www.temu.com/chair.html", "threshold": "39.99", "currency": "EUR"},
            ]
        },
    )

    products = load_products_config(path)

    assert products[0].name == "Lamp"
    assert products[0].threshold == pytest.approx(12.50)
    assert products[1].currency == "EUR"


def test_rejects_missing_product_url(tmp_path):
    path = tmp_path / "products.json"
    write_json(path, {"products": [{"threshold": 10}]})

    with pytest.raises(ConfigurationError, match="url"):
        load_products_config(path)


def test_rejects_non_finite_threshold(tmp_path):
    path = tmp_path / "products.json"
    write_json(path, {"products": [{"url": "https://www.temu.com/lamp.html", "threshold": "NaN"}]})

    with pytest.raises(ConfigurationError, match="threshold"):
        load_products_config(path)


def test_rejects_unknown_notification_channel(tmp_path):
    path = tmp_path / "notifications.json"
    write_json(path, {"channels": ["sms"]})

    with pytest.raises(ConfigurationError, match="sms"):
        load_notifications_config(path)
