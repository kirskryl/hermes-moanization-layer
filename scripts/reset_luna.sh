#!/usr/bin/env bash
set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_AGENT_ROOT="${HERMES_AGENT_ROOT:-$HERMES_HOME/hermes-agent}"
MOANA_HOME="${MOANA_HOME:-$HERMES_HOME/moanaization}"
HERMES_PYTHON="${HERMES_PYTHON:-$(find "$HERMES_HOME/tools" -path '*/bin/python3' -type f -print -quit 2>/dev/null || true)}"
HERMES_PYTHON="${HERMES_PYTHON:-python3}"

run_reset() {
  env HERMES_HOME="$HERMES_HOME" PYTHONPATH="$HERMES_AGENT_ROOT" "$HERMES_PYTHON" "$MOANA_HOME/bin/reset_luna.py" "$@"
}

run_reset --needs-reset >/dev/null || exit 0
run_reset
