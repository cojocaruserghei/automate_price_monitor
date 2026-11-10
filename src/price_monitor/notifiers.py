"""Email and Telegram notification adapters."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from decimal import Decimal
from typing import Any

import requests

from .config import NotificationConfig
from .models import ProductObservation


class NotificationError(RuntimeError):
    """Raised when a notification channel cannot deliver an alert."""


def format_alert(observation: ProductObservation, threshold: Decimal) -> str:
    currency = f" {observation.currency}" if observation.currency else ""
    return (
        f"Price drop: {observation.title}\n"
        f"Current price: {observation.price}{currency}\n"
        f"Threshold: {threshold}{currency}\n"
        f"URL: {observation.url}"
    )


class Notifier:
    def send(self, observation: ProductObservation, threshold: Decimal) -> None:
        raise NotImplementedError


class EmailNotifier(Notifier):
    def __init__(self, config, smtp_factory=smtplib.SMTP, environ: dict[str, str] | None = None):
        self.config = config
        self.smtp_factory = smtp_factory
        self.environ = environ or os.environ

    def send(self, observation: ProductObservation, threshold: Decimal) -> None:
        password = self.environ.get(self.config.password_env)
        if not password:
            raise NotificationError(f"Email password environment variable {self.config.password_env} is missing")
        message = EmailMessage()
        message["Subject"] = f"Price drop: {observation.title}"
        message["From"] = self.config.sender
        message["To"] = ", ".join(self.config.recipients)
        message.set_content(format_alert(observation, threshold))
        try:
            with self.smtp_factory(self.config.smtp_host, self.config.smtp_port, timeout=20) as smtp:
                if self.config.use_tls:
                    smtp.starttls()
                smtp.login(self.config.username, password)
                smtp.send_message(message)
        except Exception as exc:
            raise NotificationError(f"Email delivery failed: {exc}") from exc


class TelegramNotifier(Notifier):
    def __init__(self, config, http_client: Any | None = None, environ: dict[str, str] | None = None):
        self.config = config
        self.http_client = http_client or requests
        self.environ = environ or os.environ

    def send(self, observation: ProductObservation, threshold: Decimal) -> None:
        token = self.environ.get(self.config.bot_token_env)
        chat_id = self.environ.get(self.config.chat_id_env)
        if not token or not chat_id:
            raise NotificationError("Telegram bot token or chat ID environment variable is missing")
        try:
            response = self.http_client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={"chat_id": chat_id, "text": format_alert(observation, threshold)},
                timeout=20,
            )
            response.raise_for_status()
        except Exception as exc:
            raise NotificationError("Telegram delivery failed") from exc


def build_notifiers(
    config: NotificationConfig,
    http_client: Any | None = None,
    smtp_factory: Any = smtplib.SMTP,
    environ: dict[str, str] | None = None,
) -> list[Notifier]:
    notifiers: list[Notifier] = []
    if "email" in config.channels and config.email:
        notifiers.append(EmailNotifier(config.email, smtp_factory=smtp_factory, environ=environ))
    if "telegram" in config.channels and config.telegram:
        notifiers.append(TelegramNotifier(config.telegram, http_client=http_client, environ=environ))
    return notifiers
