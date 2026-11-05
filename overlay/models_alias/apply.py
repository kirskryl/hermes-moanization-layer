#!/usr/bin/env python3
"""Expose /models as the existing /model Telegram picker."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

ROOT = Path(os.environ.get("HERMES_AGENT_ROOT", Path.home() / ".hermes/hermes-agent"))
ADAPTER = ROOT / "plugins/platforms/telegram/adapter.py"
MENU = ROOT / "hermes_cli/commands_platforms.py"
ANCHOR = "        event = await self._build_triggered_event(msg, update, MessageType.COMMAND)\n"
INSERT = ANCHOR + '''        # MOANAIZATION PATCH: models-alias — reuse the native inline picker.
        if (event.text or "").split(None, 1)[0].split("@", 1)[0].lower() == "/models":
            event.text = "/model" + (" " + event.text.split(None, 1)[1] if len(event.text.split(None, 1)) > 1 else "")
'''
MENU_ANCHOR = '    core_commands = list(telegram_bot_commands(include_plugins=False))\n'
MENU_INSERT = MENU_ANCHOR + '    core_commands.append(("models", "Выбрать модель"))  # MOANAIZATION PATCH: models-alias\n'
PRIORITY_ANCHOR = '    "help", "new", "stop", "status", "egress", "resume", "sessions", "model",\n'
PRIORITY_INSERT = '    "help", "new", "stop", "status", "egress", "resume", "sessions", "model", "models",  # MOANAIZATION PATCH: models-alias\n'

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    for path, anchor, insert in ((ADAPTER, ANCHOR, INSERT), (MENU, MENU_ANCHOR, MENU_INSERT), (MENU, PRIORITY_ANCHOR, PRIORITY_INSERT)):
        source = path.read_text()
        if insert in source:
            continue
        if args.check and not args.apply:
            raise SystemExit(f"NOT patched: {path}")
        if source.count(anchor) != 1:
            raise SystemExit(f"anchor count {source.count(anchor)}: {path}")
        backup = path.with_suffix(path.suffix + ".orig-moanaization-models")
        if not backup.exists():
            backup.write_text(source)
        path.write_text(source.replace(anchor, insert, 1))
    print("models alias present")

if __name__ == "__main__":
    main()
