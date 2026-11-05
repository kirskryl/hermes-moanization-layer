#!/usr/bin/env python3
"""Limit Telegram /model and /models to ChatGPT OAuth GPT models only."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

TARGET = Path(os.environ.get(
    "HERMES_MODEL_COMMANDS",
    Path.home() / ".hermes/hermes-agent/gateway/slash_commands_model.py"))
OLD = '''        if not providers:
            return False
        result = await adapter.send_model_picker(
'''
NEW = '''        if not providers:
            return False
        # MOANAIZATION PATCH: GPT models available through ChatGPT OAuth.
        allowed = {"openai-codex": ("gpt-6-sol", "gpt-6.1-terra", "gpt-6-luna")}
        providers = [
            {**row, "models": list(allowed[row["slug"]]), "total_models": len(allowed[row["slug"]])}
            for row in providers if row.get("slug") in allowed
        ]
        if not providers:
            return False
        result = await adapter.send_model_picker(
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    source = TARGET.read_text()
    if NEW in source:
        print(f"model picker present: {TARGET}")
        return
    if args.check and not args.apply:
        raise SystemExit(f"NOT patched: {TARGET}")
    if source.count(OLD) != 1:
        raise SystemExit(f"anchor count {source.count(OLD)} in {TARGET}")
    backup = TARGET.with_suffix(TARGET.suffix + ".orig-moanaization-model-picker")
    if not backup.exists():
        backup.write_text(source)
    TARGET.write_text(source.replace(OLD, NEW, 1))
    print(f"patched: {TARGET}")


if __name__ == "__main__":
    main()
