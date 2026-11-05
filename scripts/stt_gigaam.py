#!/usr/bin/env python3
"""Offline Russian STT with a pinned local GigaAM-v3 e2e RNNT snapshot."""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path
from subprocess import run

import numpy as np
import soundfile as sf
import torch
from omegaconf import OmegaConf

MODEL_DIR = Path(os.environ["MOANA_GIGAAM_MODEL_DIR"])
MAX_AUDIO_SECONDS = 300
MAX_AUDIO_BYTES = 25 * 1024 * 1024
SAMPLE_RATE = 16_000
CHUNK_SECONDS = 20
OVERLAP_SECONDS = 0.25


def normalize(word: str) -> str:
    return re.sub(r"[^а-яa-z0-9]", "", word.lower().replace("ё", "е"))


def join_parts(parts: list[str]) -> str:
    merged: list[str] = []
    for part in parts:
        words = part.split()
        max_overlap = min(8, len(merged), len(words))
        overlap = next((size for size in range(max_overlap, 0, -1)
                        if [normalize(word) for word in merged[-size:]]
                        == [normalize(word) for word in words[:size]]), 0)
        merged.extend(words[overlap:])
    return " ".join(merged).strip()


def load_model():
    required = ("config.json", "modeling_gigaam.py", "pytorch_model.bin", "tokenizer.model")
    if not all((MODEL_DIR / name).is_file() for name in required):
        raise FileNotFoundError("GigaAM model snapshot is incomplete")
    sys.path.insert(0, str(MODEL_DIR))
    from modeling_gigaam import GigaAMASR

    config = json.loads((MODEL_DIR / "config.json").read_text())
    cfg = OmegaConf.create(config["cfg"]["model"]["cfg"])
    cfg.decoding.model_path = str(MODEL_DIR / "tokenizer.model")
    model = GigaAMASR(cfg)
    state = torch.load(MODEL_DIR / "pytorch_model.bin", map_location="cpu", weights_only=True)
    model.load_state_dict({key.removeprefix("model."): value for key, value in state.items()})
    return model.to("cpu").eval()


def transcribe(source: Path) -> str:
    if not source.is_file() or source.stat().st_size > MAX_AUDIO_BYTES:
        raise ValueError("input missing or too large")
    torch.set_num_threads(2)
    with tempfile.TemporaryDirectory(prefix="moana-gigaam-") as directory:
        temp = Path(directory)
        wav = temp / "input.wav"
        run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(source), "-ac", "1", "-ar", str(SAMPLE_RATE),
             "-c:a", "pcm_s16le", str(wav)], check=True, timeout=45)
        audio, rate = sf.read(wav, dtype="float32", always_2d=False)
        if rate != SAMPLE_RATE or len(audio) > MAX_AUDIO_SECONDS * rate:
            raise ValueError("input duration exceeds limit")
        if not len(audio) or float(np.sqrt(np.mean(np.square(audio)))) < 0.001:
            return ""
        model = load_model()
        step = CHUNK_SECONDS * rate
        overlap = int(OVERLAP_SECONDS * rate)
        parts: list[str] = []
        with torch.inference_mode():
            for number, start in enumerate(range(0, len(audio), step)):
                left = max(0, start - (overlap if number else 0))
                right = min(len(audio), start + step + overlap)
                chunk = audio[left:right]
                if float(np.sqrt(np.mean(np.square(chunk)))) < 0.001:
                    continue
                chunk_path = temp / f"chunk-{number}.wav"
                sf.write(chunk_path, chunk, rate, subtype="PCM_16")
                text = str(model.transcribe(str(chunk_path))).strip()
                if text:
                    parts.append(text)
        return join_parts(parts)


if __name__ == "__main__":
    try:
        text = transcribe(Path(sys.argv[1]))
    except Exception as error:
        print(f"gigaam failed: {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
    if not text:
        raise SystemExit(1)
    print(text)
