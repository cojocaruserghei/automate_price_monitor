"""Command-line entry point."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import requests

from .config import ConfigurationError, load_notifications_config, load_products_config
from .notifiers import build_notifiers
from .scraper import TemuScraper
from .service import PriceMonitorService
from .state import JsonStateStore, StateError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="price-monitor", description="Monitor Temu prices and send alerts")
    subparsers = parser.add_subparsers(dest="command", required=False)
    run_parser = subparsers.add_parser("run_once", help="check all configured products once")
    run_parser.add_argument("--products", type=Path, default=Path("config/products.json"))
    run_parser.add_argument("--notifications", type=Path, default=Path("config/notifications.json"))
    run_parser.add_argument("--state", type=Path, default=Path("data/state.json"))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)
    if args.command != "run_once":
        parser.print_help()
        return 0

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        products = load_products_config(args.products)
        notifications = load_notifications_config(args.notifications)
        service = PriceMonitorService(
            TemuScraper(requests),
            build_notifiers(notifications),
            JsonStateStore(args.state),
        )
        summary = service.run_once(products)
    except (ConfigurationError, StateError) as exc:
        logging.error("Configuration error: %s", exc)
        return 2
    for error in summary.errors:
        logging.error("%s", error)
    logging.info("Checked %d product(s); sent %d alert(s); %d failed", summary.checked, summary.alerts_sent, summary.failed)
    return 1 if summary.failed else 0
