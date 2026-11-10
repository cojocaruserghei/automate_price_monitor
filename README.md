# Temu Price Monitor

A small, portfolio-ready Python CLI that checks Temu product prices and sends an alert when a price is at or below its configured threshold.

## Setup

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item config\products.example.json config\products.json
Copy-Item config\notifications.example.json config\notifications.json
```

Edit `config/products.json` to add one or more Temu URLs and thresholds. Set `channels` in `config/notifications.json` to `email`, `telegram`, or both. Only enabled channels need valid settings.

Secrets are supplied through environment variables named by the JSON settings:

```powershell
$env:PRICE_MONITOR_SMTP_PASSWORD = "your-password"
$env:PRICE_MONITOR_TELEGRAM_BOT_TOKEN = "bot-token"
$env:PRICE_MONITOR_TELEGRAM_CHAT_ID = "chat-id"
```

Run one check:

```powershell
.venv\Scripts\python.exe -m price_monitor run_once
```

The default state file is `data/state.json`. A product alerts once while it stays below its threshold and becomes eligible again after its price rises above the threshold. Schedule `run_once` with Windows Task Scheduler or cron.

## Development

```powershell
.venv\Scripts\python.exe -m pytest
```

The tests inject fake HTTP, state, and notification dependencies; they do not access Temu, SMTP, or Telegram.

## Limitations

Temu can change its HTML, serve localized pages, or require JavaScript rendering. The scraper intentionally uses publicly visible structured metadata and does not bypass login, CAPTCHA, or anti-bot controls. Check the site's terms and applicable rules before automating requests.
