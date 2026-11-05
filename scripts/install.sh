#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_AGENT_ROOT="${HERMES_AGENT_ROOT:-$HERMES_HOME/hermes-agent}"
MOANA_HOME="${MOANA_HOME:-$HERMES_HOME/moanaization}"
SERVICE_USER="${SUDO_USER:-$USER}"

safe_path() {
  [[ "$1" =~ ^/[A-Za-z0-9._/-]+$ ]] || { echo "Unsafe $2: use an absolute path without spaces or shell characters" >&2; exit 2; }
}
safe_path "$HERMES_HOME" HERMES_HOME
safe_path "$HERMES_AGENT_ROOT" HERMES_AGENT_ROOT
safe_path "$MOANA_HOME" MOANA_HOME
[[ "$SERVICE_USER" =~ ^[a-z_][a-z0-9_-]*$ ]] || { echo 'Unsafe service user' >&2; exit 2; }

command -v hermes >/dev/null || { echo 'Hermes CLI is not installed' >&2; exit 1; }
[[ -d "$HERMES_AGENT_ROOT" ]] || { echo "Hermes source not found: $HERMES_AGENT_ROOT" >&2; exit 1; }
command -v ffmpeg >/dev/null || { echo 'ffmpeg is required for local voice recognition' >&2; exit 1; }

install -d -m 700 "$MOANA_HOME" "$MOANA_HOME/bin" "$MOANA_HOME/models" "$MOANA_HOME/venvs" "$MOANA_HOME/overlay"
cp "$ROOT/SOUL.template.md" "$MOANA_HOME/SOUL.template.md"
cp "$ROOT/scripts/generate_soul.py" "$ROOT/scripts/configure_integrations.py" "$ROOT/scripts/append_integration_onboarding.py" "$MOANA_HOME/bin/"
read -r -p 'Agent name [Hermes] ' agent_name
agent_name="${agent_name:-Hermes}"
read -r -p 'Agent grammatical form: neutral, feminine, masculine [neutral] ' agent_form
agent_form="${agent_form:-neutral}"
case "$agent_form" in neutral|feminine|masculine) ;; *) echo 'Invalid grammatical form' >&2; exit 2;; esac
read -r -p 'Address the user as [ты] ' user_address
user_address="${user_address:-ты}"
read -r -p 'Tone: calm, warm, business, direct, or your wording [calm] ' agent_tone
agent_tone="${agent_tone:-calm}"
read -r -p 'Response length: concise, balanced, detailed [concise] ' response_length
response_length="${response_length:-concise}"
read -r -p 'Initiative: ask first, balanced, proactive [ask first] ' initiative
initiative="${initiative:-ask first}"
read -r -p 'Additional style instruction [none] ' style_instruction
style_instruction="${style_instruction:-none}"
python3 "$MOANA_HOME/bin/generate_soul.py" \
  --name "$agent_name" --form "$agent_form" --address "$user_address" \
  --tone "$agent_tone" --length "$response_length" --initiative "$initiative" \
  --style "$style_instruction" --template "$MOANA_HOME/SOUL.template.md" \
  --output "$MOANA_HOME/SOUL.md"
if [[ ! -e "$HERMES_HOME/SOUL.md" ]]; then
  install -m 600 "$MOANA_HOME/SOUL.md" "$HERMES_HOME/SOUL.md"
else
  read -r -p 'Replace existing Hermes SOUL.md with the generic layer template? [y/N] ' answer
  if [[ "$answer" =~ ^[Yy]$ ]]; then
    cp "$HERMES_HOME/SOUL.md" "$HERMES_HOME/SOUL.md.orig-moanaization"
    install -m 600 "$MOANA_HOME/SOUL.md" "$HERMES_HOME/SOUL.md"
  fi
fi
cp "$ROOT"/scripts/{stt_gigaam.py,stt_whisper.py,stt_local.py,reset_luna.py,reset_luna.sh} "$MOANA_HOME/bin/"
chmod 700 "$MOANA_HOME/bin/"*.py "$MOANA_HOME/bin/reset_luna.sh"
cp -R "$ROOT/overlay/." "$MOANA_HOME/overlay/"
chmod 700 "$MOANA_HOME/overlay/apply_all.sh"

hermes config set model.provider openai-codex
hermes config set model.default gpt-6-luna
hermes config set image_gen.provider openai-codex
hermes config set image_gen.model gpt-image-2-medium
hermes config set agent.max_turns 30
hermes config set agent.reasoning_effort medium
hermes config set display.language ru
hermes config set display.busy_input_mode queue
hermes config set display.busy_ack_enabled false
hermes config set display.platforms.telegram.interim_assistant_messages true
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

read -r -p 'Enable DeepSeek Flash fallback? It may receive task context when used. [y/N] ' answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
  if grep -q '^DEEPSEEK_API_KEY=.' "$HERMES_HOME/.env" 2>/dev/null; then
    hermes config set fallback_providers '[{"provider":"deepseek","model":"deepseek-flash"}]'
    echo 'DeepSeek Flash fallback enabled. Task context may be sent to DeepSeek when fallback is used.'
  else
    echo 'DeepSeek is not enabled: add your own DEEPSEEK_API_KEY to ~/.hermes/.env, then rerun this installer.' >&2
  fi
fi

MOANA_HOME="$MOANA_HOME" "$ROOT/scripts/install_gigaam.sh"
MOANA_HOME="$MOANA_HOME" "$ROOT/scripts/install_whisper.sh"

read -r -p 'Install the 23:59 daily Luna reset timer now? [y/N] ' answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
  user_unit_dir="$HOME/.config/systemd/user"
  install -d -m 700 "$user_unit_dir"
  service_file="$user_unit_dir/hermes-luna-reset.service"
  python3 "$ROOT/scripts/render_luna_unit.py" \
    --template "$ROOT/systemd/hermes-luna-reset.user.service.in" --output "$service_file" \
    --service-user "$SERVICE_USER" --hermes-home "$HERMES_HOME" \
    --hermes-agent-root "$HERMES_AGENT_ROOT" --moana-home "$MOANA_HOME"
  install -m 644 "$ROOT/systemd/hermes-luna-reset.timer" "$user_unit_dir/hermes-luna-reset.timer"
  systemctl --user daemon-reload
  systemctl --user enable --now hermes-luna-reset.timer
  systemctl --user is-active --quiet hermes-luna-reset.timer || { echo 'User systemd timer did not start' >&2; exit 1; }
  if command -v loginctl >/dev/null && [[ "$(loginctl show-user "$USER" -p Linger --value 2>/dev/null || true)" != "yes" ]]; then
    echo 'The daily timer needs a running user manager after logout. Ask an administrator to run: sudo loginctl enable-linger' "$USER" >&2
  fi
fi

python3 "$MOANA_HOME/bin/configure_integrations.py" --output "$MOANA_HOME/INTEGRATIONS.md"
python3 "$MOANA_HOME/bin/append_integration_onboarding.py" --soul "$HERMES_HOME/SOUL.md"

echo 'Layer installed. Complete ChatGPT OAuth: hermes auth add openai-codex --browser'
echo 'Configure your own Telegram bot token and allowed users with Hermes, then restart hermes-gateway.'
