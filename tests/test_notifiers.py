from decimal import Decimal

from price_monitor.config import EmailConfig, NotificationConfig, TelegramConfig
from price_monitor.models import ProductObservation
from price_monitor.notifiers import EmailNotifier, TelegramNotifier, build_notifiers


def observation():
    return ProductObservation("https://www.temu.com/lamp.html", "Lamp", Decimal("9.99"), "USD")


class FakeHttp:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))

        class Response:
            def raise_for_status(self):
                return None

        return Response()


def test_telegram_sends_bot_api_payload(monkeypatch):
    http = FakeHttp()
    monkeypatch.setenv("BOT_TOKEN", "secret-token")
    monkeypatch.setenv("CHAT_ID", "12345")
    notifier = TelegramNotifier(TelegramConfig("BOT_TOKEN", "CHAT_ID"), http)

    notifier.send(observation(), Decimal("20.00"))

    assert http.calls[0][0] == "https://api.telegram.org/botsecret-token/sendMessage"
    assert http.calls[0][1]["data"]["chat_id"] == "12345"
    assert "Lamp" in http.calls[0][1]["data"]["text"]


def test_build_notifiers_only_builds_enabled_channels(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "token")
    monkeypatch.setenv("CHAT_ID", "chat")
    config = NotificationConfig(
        channels=("telegram",),
        telegram=TelegramConfig("BOT_TOKEN", "CHAT_ID"),
    )

    notifiers = build_notifiers(config, http_client=FakeHttp())

    assert len(notifiers) == 1
    assert isinstance(notifiers[0], TelegramNotifier)


def test_email_notifier_uses_injected_smtp_and_environment():
    class FakeSMTP:
        instance = None

        def __init__(self, host, port, timeout):
            self.messages = []
            self.tls_started = False
            FakeSMTP.instance = self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            self.tls_started = True

        def login(self, username, password):
            self.login_args = (username, password)

        def send_message(self, message):
            self.messages.append(message)

    config = EmailConfig("smtp.example.com", 587, "sender", "PASSWORD", "sender@example.com", ("to@example.com",))
    notifier = EmailNotifier(config, smtp_factory=FakeSMTP, environ={"PASSWORD": "secret"})

    notifier.send(observation(), Decimal("20.00"))

    assert FakeSMTP.instance.tls_started is True
    assert FakeSMTP.instance.login_args == ("sender", "secret")
    assert "Lamp" in FakeSMTP.instance.messages[0].get_content()
