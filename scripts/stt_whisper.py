#!/usr/bin/env python3
"""Offline fallback STT using faster-whisper on CPU/int8."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from faster_whisper import WhisperModel


def transcribe(source: Path) -> str:
    model = WhisperModel(
        "base",
        device="cpu",
        compute_type="int8",
        download_root=os.environ["MOANA_WHISPER_MODEL_DIR"],
    )
    segments, _ = model.transcribe(str(source), language="ru", vad_filter=True)
    return " ".join(segment.text.strip() for segment in segments).strip()


if __name__ == "__main__":
    try:
        text = transcribe(Path(sys.argv[1]))
    except Exception as error:
        print(f"whisper failed: {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
    if not text:
        raise SystemExit(1)
    print(text)
