"""Backward-compatible launcher for the packaged CLI."""

from price_monitor.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
