#!/usr/bin/env python3
"""Hermes local_command bridge: GigaAM first, faster-whisper fallback."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

MOANA_HOME = Path(os.environ.get("MOANA_HOME", Path.home() / ".hermes/moanaization"))
GIGAAM = MOANA_HOME / "venvs/gigaam/bin/python"
WHISPER = MOANA_HOME / "venvs/whisper/bin/python"
SCRIPT_DIR = MOANA_HOME / "bin"


def run_stt(name: str, python: Path, script: str, source: Path) -> str:
    env = dict(os.environ)
    env.update({
        "MOANA_GIGAAM_MODEL_DIR": str(MOANA_HOME / "models/gigaam-v3-e2e-rnnt"),
        "MOANA_WHISPER_MODEL_DIR": str(MOANA_HOME / "models/whisper"),
        "OMP_NUM_THREADS": "2",
        "MKL_NUM_THREADS": "2",
        "HF_HUB_OFFLINE": "1",
    })
    command = [str(python), str(SCRIPT_DIR / script), str(source)]
    if name == "gigaam":
        command = ["flock", "-w", "30", "/tmp/moanaization-gigaam.lock", *command]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180, env=env)
    if result.returncode or not result.stdout.strip():
        raise RuntimeError(result.stderr.strip()[-300:] or "empty transcript")
    return result.stdout.strip()


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: stt_local.py <input> <output_dir> [language] [model]", file=sys.stderr)
        return 2
    source, output_dir = Path(sys.argv[1]), Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, python, script in (("gigaam", GIGAAM, "stt_gigaam.py"), ("whisper", WHISPER, "stt_whisper.py")):
        try:
            text = run_stt(name, python, script, source)
            (output_dir / f"{source.stem}.txt").write_text(text, encoding="utf-8")
            print(f"ok via {name}", file=sys.stderr)
            return 0
        except Exception as error:  # next local provider preserves the voice task
            print(f"{name} failed: {type(error).__name__}: {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
