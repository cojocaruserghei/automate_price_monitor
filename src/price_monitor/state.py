"""Small atomic JSON persistence for alert deduplication."""

from __future__ import annotations

import json
import os
import tempfile
from decimal import Decimal
from pathlib import Path


class StateError(RuntimeError):
    """Raised when persisted alert state cannot be read safely."""


class JsonStateStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._state = self._load()

    def is_alerted(self, url: str) -> bool:
        return bool(self._state.get(url, {}).get("alerted", False))

    def get_price(self, url: str) -> Decimal | None:
        value = self._state.get(url, {}).get("price")
        return Decimal(str(value)) if value is not None else None

    def mark_alerted(self, url: str, price: Decimal) -> None:
        self._state[url] = {"alerted": True, "price": str(price)}
        self._save()

    def clear_alert(self, url: str) -> None:
        if url in self._state:
            self._state[url]["alerted"] = False
            self._save()

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StateError(f"Could not read state file {self.path}: {exc}") from exc
        return value if isinstance(value, dict) else {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix="price-monitor-", suffix=".json", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self._state, handle, indent=2)
                handle.write("\n")
            os.replace(temp_name, self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
