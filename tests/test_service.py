from decimal import Decimal

from price_monitor.models import ProductObservation
from price_monitor.service import PriceMonitorService


class FakeScraper:
    def __init__(self, observation):
        self.observation = observation

    def fetch(self, product):
        if isinstance(self.observation, Exception):
            raise self.observation
        return self.observation


class FakeNotifier:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def send(self, observation, threshold):
        self.calls.append((observation, threshold))
        if self.fail:
            raise RuntimeError("delivery unavailable")


class FakeState:
    def __init__(self):
        self.alerted = set()
        self.marked = []
        self.cleared = []

    def is_alerted(self, url):
        return url in self.alerted

    def mark_alerted(self, url, price):
        self.alerted.add(url)
        self.marked.append((url, price))

    def clear_alert(self, url):
        self.alerted.discard(url)
        self.cleared.append(url)


def product():
    return type("Product", (), {"url": "https://www.temu.com/lamp.html", "name": "Lamp", "threshold": Decimal("10")})()


def observation(price):
    return ProductObservation(product().url, "Lamp", Decimal(price), "USD")


def test_notifies_once_and_marks_alerted_only_after_success():
    state = FakeState()
    notifier = FakeNotifier()
    service = PriceMonitorService(FakeScraper(observation("9.99")), [notifier], state)

    first = service.run_once([product()])
    second = service.run_once([product()])

    assert first.alerts_sent == 1
    assert second.alerts_sent == 0
    assert len(notifier.calls) == 1
    assert len(state.marked) == 1


def test_rearms_after_price_rises_above_threshold():
    state = FakeState()
    notifier = FakeNotifier()
    service = PriceMonitorService(FakeScraper(observation("9.99")), [notifier], state)
    service.run_once([product()])
    service.scraper = FakeScraper(observation("12.00"))
    service.run_once([product()])
    service.scraper = FakeScraper(observation("8.00"))
    result = service.run_once([product()])

    assert result.alerts_sent == 1
    assert len(notifier.calls) == 2
    assert state.cleared == [product().url]


def test_delivery_failure_is_reported_and_not_marked_alerted():
    state = FakeState()
    service = PriceMonitorService(FakeScraper(observation("9.99")), [FakeNotifier(fail=True)], state)

    result = service.run_once([product()])

    assert result.failed == 1
    assert state.marked == []
