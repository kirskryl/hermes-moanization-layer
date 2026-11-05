#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_AGENT_ROOT="${HERMES_AGENT_ROOT:-$HERMES_HOME/hermes-agent}"
MOANA_HOME="${MOANA_HOME:-$HERMES_HOME/moanaization}"
SERVICE_USER="${SUDO_USER:-$USER}"

command -v hermes >/dev/null || { echo 'Hermes CLI is not installed' >&2; exit 1; }
[[ -d "$HERMES_AGENT_ROOT" ]] || { echo "Hermes source not found: $HERMES_AGENT_ROOT" >&2; exit 1; }
command -v ffmpeg >/dev/null || { echo 'ffmpeg is required for local voice recognition' >&2; exit 1; }

install -d -m 700 "$MOANA_HOME" "$MOANA_HOME/bin" "$MOANA_HOME/models" "$MOANA_HOME/venvs" "$MOANA_HOME/overlay"
install -m 644 "$ROOT/SOUL.md" "$MOANA_HOME/SOUL.template.md"
if [[ ! -e "$HERMES_HOME/SOUL.md" ]]; then
  install -m 600 "$ROOT/SOUL.md" "$HERMES_HOME/SOUL.md"
else
  read -r -p 'Replace existing Hermes SOUL.md with the generic layer template? [y/N] ' answer
  if [[ "$answer" =~ ^[Yy]$ ]]; then
    cp "$HERMES_HOME/SOUL.md" "$HERMES_HOME/SOUL.md.orig-moanaization"
    install -m 600 "$ROOT/SOUL.md" "$HERMES_HOME/SOUL.md"
  fi
fi
cp "$ROOT"/scripts/{stt_gigaam.py,stt_whisper.py,stt_local.py,reset_luna.py,reset_luna.sh} "$MOANA_HOME/bin/"
chmod 700 "$MOANA_HOME/bin/"*.py "$MOANA_HOME/bin/reset_luna.sh"
cp -R "$ROOT/overlay/." "$MOANA_HOME/overlay/"
chmod 700 "$MOANA_HOME/overlay/apply_all.sh"

hermes config set model.provider openai-codex
hermes config set model.default gpt-6-luna
hermes config set agent.max_turns 30
hermes config set agent.reasoning_effort medium
hermes config set display.language ru
hermes config set display.busy_input_mode queue
hermes config set display.platforms.telegram.interim_assistant_messages false
hermes config set display.platforms.telegram.tool_progress false
hermes config set display.platforms.telegram.busy_ack_detail false
hermes config set cron.wrap_response false
hermes config set stt.enabled true
hermes config set stt.provider local_command
hermes config set stt.language ru
hermes config set fallback_providers '[]'
hermes config set HERMES_LANGUAGE ru
hermes config set HERMES_LOCAL_STT_COMMAND "MOANA_HOME=$MOANA_HOME python3 $MOANA_HOME/bin/stt_local.py {input_path} {output_dir} {language} {model}"

HERMES_HOME="$HERMES_HOME" HERMES_AGENT_ROOT="$HERMES_AGENT_ROOT" "$MOANA_HOME/overlay/apply_all.sh" --apply

read -r -p 'Download local GigaAM and Whisper models now? [y/N] ' answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
  MOANA_HOME="$MOANA_HOME" "$ROOT/scripts/install_gigaam.sh"
  MOANA_HOME="$MOANA_HOME" "$ROOT/scripts/install_whisper.sh"
fi

read -r -p 'Install the 23:59 daily Luna reset timer now? [y/N] ' answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
  service_file="/etc/systemd/system/hermes-luna-reset.service"
  sudo sed \
    -e "s|__SERVICE_USER__|$SERVICE_USER|g" \
    -e "s|__HERMES_HOME__|$HERMES_HOME|g" \
    -e "s|__HERMES_AGENT_ROOT__|$HERMES_AGENT_ROOT|g" \
    -e "s|__MOANA_HOME__|$MOANA_HOME|g" \
    "$ROOT/systemd/hermes-luna-reset.service.in" | sudo tee "$service_file" >/dev/null
  sudo install -m 644 "$ROOT/systemd/hermes-luna-reset.timer" /etc/systemd/system/hermes-luna-reset.timer
  sudo systemctl daemon-reload
  sudo systemctl enable --now hermes-luna-reset.timer
fi

echo 'Layer installed. Complete ChatGPT OAuth: hermes auth add openai-codex --browser'
echo 'Configure your own Telegram bot token and allowed users with Hermes, then restart hermes-gateway.'
