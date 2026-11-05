#!/usr/bin/env python3
"""Render the optional systemd unit with validated values, without shell interpolation."""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


PATH_VALUE = re.compile(r"^/[A-Za-z0-9._/-]+$")
USER_VALUE = re.compile(r"^[a-z_][a-z0-9_-]*$")


def checked_path(value: str, label: str) -> str:
    if not PATH_VALUE.fullmatch(value):
        raise SystemExit(f"Unsafe {label}: use an absolute path without spaces or shell characters")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--service-user", required=True)
    parser.add_argument("--hermes-home", required=True)
    parser.add_argument("--hermes-agent-root", required=True)
    parser.add_argument("--moana-home", required=True)
    args = parser.parse_args()
    if not USER_VALUE.fullmatch(args.service_user):
        raise SystemExit("Unsafe service user")
    values = {
        "__SERVICE_USER__": args.service_user,
        "__HERMES_HOME__": checked_path(args.hermes_home, "HERMES_HOME"),
        "__HERMES_AGENT_ROOT__": checked_path(args.hermes_agent_root, "HERMES_AGENT_ROOT"),
        "__MOANA_HOME__": checked_path(args.moana_home, "MOANA_HOME"),
    }
    content = args.template.read_text(encoding="utf-8")
    for marker, value in values.items():
        if marker not in content:
            raise SystemExit(f"Template marker is missing: {marker}")
        content = content.replace(marker, value)
    if "__" in content:
        raise SystemExit("Unresolved template marker")
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.chmod(temporary, 0o644)
    os.replace(temporary, args.output)


if __name__ == "__main__":
    main()
