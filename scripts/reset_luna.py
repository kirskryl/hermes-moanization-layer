#!/usr/bin/env python3
"""Clear Telegram-only model overrides so the global Luna default applies."""
from __future__ import annotations

import argparse
from pathlib import Path

import hermes_bootstrap  # noqa: F401
from gateway.config import load_gateway_config
from gateway.session import SessionStore


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--needs-reset", action="store_true")
    args = parser.parse_args()
    config = load_gateway_config()
    store = SessionStore(Path(config.sessions_dir), config)
    keys = [entry.session_key for entry in store.list_sessions()
            if getattr(getattr(entry.origin, "platform", None), "value", None) == "telegram"
            and entry.model_override]
    if args.needs_reset:
        return 0 if keys else 1
    for key in keys:
        store.set_model_override(key, None)
    print(f"Telegram model overrides reset: {len(keys)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
