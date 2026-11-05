#!/usr/bin/env python3
"""Ensure an existing SOUL can route the owner to the local integration plan."""
from __future__ import annotations

import argparse
import os
from pathlib import Path


MARKER = "<!-- MOANAIZATION INTEGRATION ONBOARDING -->"
BLOCK = f'''\n\n{MARKER}
Если существует `~/.hermes/moanaization/INTEGRATIONS.md` с выбранными пунктами, предложи владельцу подключать их по одному. Сначала объясни доступ и следующий безопасный шаг, затем дождись подтверждённого OAuth или иной штатной авторизации и проверь конкретную интеграцию. Не проси в чате и не записывай в него пароли, токены, cookie, ключи или коды 2FA.
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--soul", type=Path, required=True)
    args = parser.parse_args()
    if not args.soul.exists():
        raise SystemExit("SOUL.md is missing")
    content = args.soul.read_text(encoding="utf-8")
    if MARKER in content:
        print("integration onboarding already present")
        return
    backup = args.soul.with_name(args.soul.name + ".orig-moanaization-onboarding")
    if not backup.exists():
        backup.write_text(content, encoding="utf-8")
        os.chmod(backup, 0o600)
    args.soul.write_text(content.rstrip() + BLOCK, encoding="utf-8")
    os.chmod(args.soul, 0o600)
    print("integration onboarding added")


if __name__ == "__main__":
    main()
