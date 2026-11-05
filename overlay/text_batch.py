#!/usr/bin/env python3
"""Raise Telegram short-message text-batch delays to 2.0s (idempotent).

Upstream caps short bubbles at ~180–240ms so env HERMES_TELEGRAM_TEXT_BATCH_DELAY_SECONDS
alone cannot coalesce multi-bubble tasks. Re-run after hermes-agent upgrades.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

MARKER = "MOANAIZATION PATCH: text-batch-debounce"
TARGET = Path(
    os.environ.get(
        "HERMES_TELEGRAM_ADAPTER",
        str(Path.home() / ".hermes/hermes-agent/plugins/platforms/telegram/adapter.py"),
    )
)

OLD_FAST = "    _TEXT_BATCH_FAST_DELAY_S = 0.18"
NEW_FAST = (
    "    # MOANAIZATION PATCH: text-batch-debounce — short bubbles wait 2.0s so N "
    "messages coalesce\n"
    "    _TEXT_BATCH_FAST_DELAY_S = 2.0"
)
OLD_SHORT = "    _TEXT_BATCH_SHORT_DELAY_S = 0.24"
NEW_SHORT = "    _TEXT_BATCH_SHORT_DELAY_S = 2.0  # MOANAIZATION PATCH: text-batch-debounce"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    check_only = args.check and not args.apply

    if not TARGET.is_file():
        raise SystemExit(f"missing target: {TARGET}")

    text = TARGET.read_text()
    if MARKER in text and "_TEXT_BATCH_FAST_DELAY_S = 2.0" in text:
        print(f"already patched: {TARGET}")
        return

    if check_only:
        raise SystemExit(f"NOT patched: {TARGET}")

    if OLD_FAST not in text or OLD_SHORT not in text:
        if "_TEXT_BATCH_FAST_DELAY_S = 2.0" in text:
            print(f"already patched (no marker): {TARGET}")
            return
        raise SystemExit(f"anchor not found in {TARGET} — hermes-agent layout changed?")

    text = text.replace(OLD_FAST, NEW_FAST, 1).replace(OLD_SHORT, NEW_SHORT, 1)
    bak = TARGET.with_suffix(TARGET.suffix + ".orig-moanaization-textbatch")
    if not bak.exists():
        bak.write_text(TARGET.read_text())
    TARGET.write_text(text)
    print(f"patched: {TARGET}")


if __name__ == "__main__":
    main()
