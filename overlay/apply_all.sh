#!/usr/bin/env bash
set -euo pipefail

MODE="${1:---check}"
ROOT="$(cd "$(dirname "$0")" && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
export HERMES_HOME HERMES_AGENT_ROOT="${HERMES_AGENT_ROOT:-$HERMES_HOME/hermes-agent}"

[[ -d "$HERMES_AGENT_ROOT" ]] || { echo 'hermes-agent source is missing' >&2; exit 1; }

run() {
  local name="$1"
  shift
  echo "==> $name ($MODE)"
  "$@"
}

case "$MODE" in
  --check)
    run text-batch python3 "$ROOT/text_batch.py" --check
    run unified-inbox python3 "$ROOT/unified_inbox/apply.py" --check
    run models-alias python3 "$ROOT/models_alias/apply.py" --check
    run model-picker python3 "$ROOT/model_picker/apply.py" --check
    ;;
  --apply|--check-or-apply)
    run text-batch python3 "$ROOT/text_batch.py" --apply
    run unified-inbox python3 "$ROOT/unified_inbox/apply.py" --apply
    run models-alias python3 "$ROOT/models_alias/apply.py" --apply
    run model-picker python3 "$ROOT/model_picker/apply.py" --apply
    "$ROOT/apply_all.sh" --check
    ;;
  *)
    echo 'Usage: apply_all.sh --check|--apply|--check-or-apply' >&2
    exit 2
    ;;
esac
