#!/usr/bin/env bash
set -euo pipefail

MOANA_HOME="${MOANA_HOME:?MOANA_HOME is required}"
VENV="$MOANA_HOME/venvs/whisper"
MODEL_DIR="$MOANA_HOME/models/whisper"

python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -r "$(dirname "$0")/requirements-whisper.txt"
"$VENV/bin/python" - "$MODEL_DIR" <<'PY'
from faster_whisper import WhisperModel
from pathlib import Path
import sys
WhisperModel('base', device='cpu', compute_type='int8', download_root=str(Path(sys.argv[1])))
print('Whisper base model ready')
PY
