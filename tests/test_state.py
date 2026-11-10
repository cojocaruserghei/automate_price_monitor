from decimal import Decimal

from price_monitor.state import JsonStateStore
from price_monitor.state import StateError


def test_state_store_round_trips_alerted_urls(tmp_path):
    store = JsonStateStore(tmp_path / "state.json")

    assert store.is_alerted("https://www.temu.com/lamp.html") is False
    store.mark_alerted("https://www.temu.com/lamp.html", Decimal("9.99"))

    reloaded = JsonStateStore(tmp_path / "state.json")
    assert reloaded.is_alerted("https://www.temu.com/lamp.html") is True
    assert reloaded.get_price("https://www.temu.com/lamp.html") == Decimal("9.99")

    reloaded.clear_alert("https://www.temu.com/lamp.html")
    assert reloaded.is_alerted("https://www.temu.com/lamp.html") is False


def test_corrupted_state_fails_loudly(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{not-json", encoding="utf-8")

    try:
        JsonStateStore(path)
    except StateError as exc:
        assert "state" in str(exc).lower()
    else:
        raise AssertionError("corrupted state should not be silently discarded")
