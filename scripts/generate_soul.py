#!/usr/bin/env python3
"""Render a neutral SOUL with the name and grammatical form chosen at install time."""
from __future__ import annotations

import argparse
from pathlib import Path

FORMS = {
    "neutral": "В русском избегай форм, которые маркируют пол: выбирай нейтральные обороты «готово», «сделаю», «получилось».",
    "feminine": "В русском говори о себе в женском роде: «готова», «сделала», «поняла».",
    "masculine": "В русском говори о себе в мужском роде: «готов», «сделал», «понял».",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--form", choices=FORMS, required=True)
    parser.add_argument("--address", required=True)
    parser.add_argument("--tone", required=True)
    parser.add_argument("--length", required=True)
    parser.add_argument("--initiative", required=True)
    parser.add_argument("--style", required=True)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    name = args.name.strip() or "Hermes"
    text = args.template.read_text(encoding="utf-8")
    text = text.replace("{{AGENT_NAME}}", name).replace("{{SELF_FORM}}", FORMS[args.form])
    text = text.replace("{{USER_ADDRESS}}", args.address)
    text = text.replace("{{TONE}}", args.tone)
    text = text.replace("{{LENGTH}}", args.length)
    text = text.replace("{{INITIATIVE}}", args.initiative)
    text = text.replace("{{STYLE}}", args.style)
    args.output.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
