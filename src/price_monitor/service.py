"""Application use case for one monitoring pass."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RunSummary:
    checked: int = 0
    alerts_sent: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


class PriceMonitorService:
    def __init__(self, scraper: Any, notifiers: list[Any], state_store: Any):
        self.scraper = scraper
        self.notifiers = notifiers
        self.state_store = state_store

    def run_once(self, products) -> RunSummary:
        summary = RunSummary()
        for product in products:
            summary.checked += 1
            try:
                observation = self.scraper.fetch(product)
                if observation.price > product.threshold:
                    self.state_store.clear_alert(product.url)
                    continue
                if self.state_store.is_alerted(product.url):
                    continue
                delivery_errors = []
                for notifier in self.notifiers:
                    try:
                        notifier.send(observation, product.threshold)
                    except Exception as exc:
                        delivery_errors.append(str(exc))
                if delivery_errors:
                    raise RuntimeError("; ".join(delivery_errors))
                self.state_store.mark_alerted(product.url, observation.price)
                summary.alerts_sent += 1
            except Exception as exc:
                summary.failed += 1
                summary.errors.append(f"{product.name}: {exc}")
        return summary
