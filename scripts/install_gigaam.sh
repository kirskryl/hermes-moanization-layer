#!/usr/bin/env bash
set -euo pipefail

MOANA_HOME="${MOANA_HOME:?MOANA_HOME is required}"
VENV="$MOANA_HOME/venvs/gigaam"
MODEL_DIR="$MOANA_HOME/models/gigaam-v3-e2e-rnnt"
GIGAAM_REVISION="7655ad717f8122257385bb4b2f373db3697e8680"
GIGAAM_MODELING_SHA256="269be43b635b1e510115baa2a843c5cbaa052e8adf0be30dc133a2ba5b5f2d86"

command -v ffmpeg >/dev/null || { echo 'ffmpeg is required' >&2; exit 1; }
python3 -c 'import sys; assert sys.version_info >= (3, 10)' || { echo 'Python 3.10+ is required' >&2; exit 1; }

python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -r "$(dirname "$0")/requirements-gigaam.txt" torch torchaudio
"$VENV/bin/python" - "$MODEL_DIR" "$GIGAAM_REVISION" <<'PY'
from pathlib import Path
from huggingface_hub import snapshot_download
import sys
target = Path(sys.argv[1])
revision = sys.argv[2]
snapshot_download(
    repo_id='ai-sage/GigaAM-v3',
    revision=revision,
    local_dir=str(target),
)
print(f'GigaAM snapshot ready: {target}')
PY
actual_sha256="$(sha256sum "$MODEL_DIR/modeling_gigaam.py" | awk '{print $1}')"
if [[ "$actual_sha256" != "$GIGAAM_MODELING_SHA256" ]]; then
  echo 'GigaAM model code hash mismatch' >&2
  exit 1
fi
