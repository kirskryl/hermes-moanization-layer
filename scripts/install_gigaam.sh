#!/usr/bin/env bash
set -euo pipefail

MOANA_HOME="${MOANA_HOME:?MOANA_HOME is required}"
VENV="$MOANA_HOME/venvs/gigaam"
MODEL_DIR="$MOANA_HOME/models/gigaam-v3-e2e-rnnt"

command -v ffmpeg >/dev/null || { echo 'ffmpeg is required' >&2; exit 1; }
python3 -c 'import sys; assert sys.version_info >= (3, 10)' || { echo 'Python 3.10+ is required' >&2; exit 1; }

python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -r "$(dirname "$0")/requirements-gigaam.txt" torch torchaudio
"$VENV/bin/python" - "$MODEL_DIR" <<'PY'
from pathlib import Path
from huggingface_hub import snapshot_download
import sys
target = Path(sys.argv[1])
snapshot_download(
    repo_id='ai-sage/GigaAM-v3',
    revision='e2e_rnnt',
    local_dir=str(target),
)
print(f'GigaAM snapshot ready: {target}')
PY
