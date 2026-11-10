"""JSON configuration loading and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


class ConfigurationError(ValueError):
    """Raised when a configuration file cannot be used safely."""


@dataclass(frozen=True)
class ProductConfig:
    url: str
    threshold: Decimal
    name: str
    currency: str | None = None


@dataclass(frozen=True)
class EmailConfig:
    smtp_host: str
    smtp_port: int
    username: str
    password_env: str
    sender: str
    recipients: tuple[str, ...]
    use_tls: bool = True


@dataclass(frozen=True)
class TelegramConfig:
    bot_token_env: str
    chat_id_env: str


@dataclass(frozen=True)
class NotificationConfig:
    channels: tuple[str, ...]
    email: EmailConfig | None = None
    telegram: TelegramConfig | None = None


def _read_json(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"Could not read JSON config {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigurationError(f"Config {path} must contain a JSON object")
    return value


def _required_string(data: dict[str, Any], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{context} requires a non-empty {key}")
    return value.strip()


def load_products_config(path: str | Path) -> tuple[ProductConfig, ...]:
    data = _read_json(path)
    raw_products = data.get("products")
    if not isinstance(raw_products, list) or not raw_products:
        raise ConfigurationError("products config requires a non-empty products list")

    products: list[ProductConfig] = []
    for index, raw_product in enumerate(raw_products):
        context = f"product {index + 1}"
        if not isinstance(raw_product, dict):
            raise ConfigurationError(f"{context} must be a JSON object")
        url = _required_string(raw_product, "url", context)
        if not url.startswith(("https://www.temu.com/", "https://temu.com/")):
            raise ConfigurationError(f"{context} url must be a Temu HTTPS URL")
        try:
            threshold = Decimal(str(raw_product["threshold"]))
        except (KeyError, InvalidOperation, ValueError) as exc:
            raise ConfigurationError(f"{context} requires a numeric threshold") from exc
        if not threshold.is_finite():
            raise ConfigurationError(f"{context} threshold must be finite")
        if threshold < 0:
            raise ConfigurationError(f"{context} threshold cannot be negative")
        name = str(raw_product.get("name") or url).strip()
        currency = raw_product.get("currency")
        if currency is not None and (not isinstance(currency, str) or not currency.strip()):
            raise ConfigurationError(f"{context} currency must be a non-empty string")
        products.append(ProductConfig(url, threshold, name, currency.strip() if currency else None))
    return tuple(products)


def load_notifications_config(path: str | Path) -> NotificationConfig:
    data = _read_json(path)
    raw_channels = data.get("channels")
    if not isinstance(raw_channels, list) or not raw_channels:
        raise ConfigurationError("notifications config requires a non-empty channels list")
    channels = tuple(str(channel).strip().lower() for channel in raw_channels)
    unsupported = set(channels) - {"email", "telegram"}
    if unsupported:
        raise ConfigurationError(f"unsupported notification channel(s): {', '.join(sorted(unsupported))}")
    if len(set(channels)) != len(channels):
        raise ConfigurationError("notification channels must be unique")

    email = None
    if "email" in channels:
        raw_email = data.get("email")
        if not isinstance(raw_email, dict):
            raise ConfigurationError("email channel requires an email object")
        recipients = raw_email.get("recipients")
        if not isinstance(recipients, list) or not recipients or not all(isinstance(x, str) and x.strip() for x in recipients):
            raise ConfigurationError("email requires a non-empty recipients list")
        try:
            smtp_port = int(raw_email["smtp_port"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ConfigurationError("email requires a numeric smtp_port") from exc
        email = EmailConfig(
            smtp_host=_required_string(raw_email, "smtp_host", "email"),
            smtp_port=smtp_port,
            username=_required_string(raw_email, "username", "email"),
            password_env=_required_string(raw_email, "password_env", "email"),
            sender=_required_string(raw_email, "sender", "email"),
            recipients=tuple(x.strip() for x in recipients),
            use_tls=bool(raw_email.get("use_tls", True)),
        )

    telegram = None
    if "telegram" in channels:
        raw_telegram = data.get("telegram")
        if not isinstance(raw_telegram, dict):
            raise ConfigurationError("telegram channel requires a telegram object")
        telegram = TelegramConfig(
            bot_token_env=_required_string(raw_telegram, "bot_token_env", "telegram"),
            chat_id_env=_required_string(raw_telegram, "chat_id_env", "telegram"),
        )
    return NotificationConfig(channels, email, telegram)
