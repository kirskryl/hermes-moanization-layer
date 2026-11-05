#!/usr/bin/env python3
"""Retry one ordinary text refusal through the configured fallback provider."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

MARKER = "MOANAIZATION PATCH: soft-refusal-fallback"
TARGET = Path(
    os.environ.get(
        "HERMES_TURN_FINAL_RESPONSE",
        str(Path.home() / ".hermes/hermes-agent/agent/turn_final_response.py"),
    )
)

HELPER = r'''
# MOANAIZATION PATCH: soft-refusal-fallback helpers
import re as _mo_re

_MO_SOFT_REFUSAL_RE = _mo_re.compile(
    r"(?is)"
    r"("
    r"i (?:can'?t|cannot|won'?t|am unable to|must refuse|have to refuse)\b"
    r"|i'?m (?:not (?:able|allowed|permitted|comfortable)|sorry,? but i (?:can'?t|cannot))"
    r"|against (?:my |the )?(?:ethical |content |usage )?(?:guidelines|policies|principles)"
    r"|(?:full|дословн\w*)\s+(?:transcript|расшифров\w*|транскри\w*).{0,80}"
    r"(?:can'?t|cannot|не\s+могу|не\s+смогу)"
    r"|не\s+могу\s+(?:полная|дословн|сделать\s+полн|перенести)"
    r"|полную\s+дословную\s+расшифровку.{0,40}не\s+могу"
    r"|Могу добавить в новую вкладку краткий пересказ"
    r")"
)


def _mo_looks_like_soft_refusal(text: str) -> bool:
    """Narrow allowlist: ordinary ethics/policy refusals only."""
    t = (text or "").strip()
    if len(t) < 40 or len(t) > 4000:
        return False
    return bool(_MO_SOFT_REFUSAL_RE.search(t))

'''

BLOCK = r'''
    # MOANAIZATION PATCH: soft-refusal-fallback
    # Soft ethics refusal often arrives as finish_reason=stop (not content_filter).
    # One runtime fallback via fallback_providers; primary restores on next turn.
    if (
        final_response
        and finish_reason == "stop"
        and not getattr(agent, "_mo_soft_refusal_fallback_used", False)
        and _mo_looks_like_soft_refusal(final_response)
    ):
        import hashlib
        import json
        import time
        from pathlib import Path as _BaPath

        from agent.conversation_loop import _arm_fallback_restart, _sync_failover_system_message

        agent._mo_soft_refusal_fallback_used = True
        _prev_model = getattr(agent, "model", None)
        _prev_provider = getattr(agent, "provider", None)
        if agent._has_pending_fallback() and agent._try_activate_fallback():
            try:
                _log = _BaPath.home() / ".hermes/logs/moanaization-fallback.jsonl"
                _log.parent.mkdir(parents=True, exist_ok=True)
                _sid = str(getattr(agent, "session_id", "") or "")
                with _log.open("a", encoding="utf-8") as _fh:
                    _fh.write(json.dumps({
                        "ts": time.time(),
                        "reason": "soft_refusal",
                        "session_hash": hashlib.sha256(_sid.encode()).hexdigest()[:16] if _sid else "",
                        "previous_model": _prev_model,
                        "previous_provider": _prev_provider,
                        "fallback_model": getattr(agent, "model", None),
                        "fallback_provider": getattr(agent, "provider", None),
                    }, ensure_ascii=False) + "\n")
            except Exception:
                logger.debug("moanaization fallback log write failed", exc_info=True)
            agent._buffer_diagnostic_status(
                "Основная модель ограничила ответ — один раз пробую резервную.")
            if _retry is not None:
                active_system_prompt = _arm_fallback_restart(
                    agent, api_messages, active_system_prompt, _retry)
            else:
                active_system_prompt = _sync_failover_system_message(
                    agent, api_messages, active_system_prompt)
            final_response = None
            return _verdict("continue")
        logger.warning(
            "%ssoft refusal matched but fallback unavailable (model=%s provider=%s)",
            agent.log_prefix, _prev_model, _prev_provider,
        )

'''

SIG_OLD = """def finish_text_response(
    agent: Any, *, assistant_message: Any, response: Any, finish_reason: Any, messages: Any,
    api_messages: Any, conversation_history: Any, api_call_count: Any, user_message: Any,
    active_system_prompt: Any, final_response: Any, _turn_exit_reason: Any,
    _preflight_compression_blocked: Any, codex_ack_continuations: Any,
    truncated_response_parts: Any, length_continue_retries: Any,
    _pending_verification_response: Any, _pending_verification_response_previewed: Any,
    effective_task_id: Any,
) -> FinalResponseVerdict:"""

SIG_NEW = """def finish_text_response(
    agent: Any, *, assistant_message: Any, response: Any, finish_reason: Any, messages: Any,
    api_messages: Any, conversation_history: Any, api_call_count: Any, user_message: Any,
    active_system_prompt: Any, final_response: Any, _turn_exit_reason: Any,
    _preflight_compression_blocked: Any, codex_ack_continuations: Any,
    truncated_response_parts: Any, length_continue_retries: Any,
    _pending_verification_response: Any, _pending_verification_response_previewed: Any,
    effective_task_id: Any, _retry: Any = None,
) -> FinalResponseVerdict:"""

STRIP_LINE = "    final_response = agent._strip_think_blocks(final_response).strip()\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    check_only = args.check and not args.apply

    if not TARGET.is_file():
        raise SystemExit(f"missing target: {TARGET}")

    original = TARGET.read_text()
    if MARKER in original:
        print(f"already patched: {TARGET}")
        return

    if check_only:
        raise SystemExit(f"NOT patched: {TARGET}")

    if SIG_OLD not in original:
        raise SystemExit(f"signature anchor not found in {TARGET}")
    if STRIP_LINE not in original:
        raise SystemExit(f"strip_think_blocks anchor not found in {TARGET}")

    text = original.replace(SIG_OLD, SIG_NEW, 1)
    text = text.replace(STRIP_LINE, STRIP_LINE + BLOCK, 1)
    idx = text.find("def finish_text_response(")
    if idx < 0:
        raise SystemExit("finish_text_response missing after edits")
    text = text[:idx] + HELPER + text[idx:]

    bak = TARGET.with_suffix(TARGET.suffix + ".orig-moanaization-softrefusal")
    if not bak.exists():
        bak.write_text(original)
    TARGET.write_text(text)
    print(f"patched: {TARGET}")


if __name__ == "__main__":
    main()
