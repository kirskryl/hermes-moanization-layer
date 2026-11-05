#!/usr/bin/env python3
"""Show one receipt after a queued Telegram text task is durably accepted."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

TARGET = Path(os.environ.get(
    "HERMES_TELEGRAM_ADAPTER",
    Path.home() / ".hermes/hermes-agent/plugins/platforms/telegram/adapter.py",
))
MARKER = "MOANAIZATION PATCH: queue-ack v2"
LEGACY_MARKER = "MOANAIZATION PATCH: queue-ack"

ANCHOR = '''    async def _flush_text_batch(self, key: str) -> None:
        """Telegram keeps its own flush body: a cancel after the pop must HOLD the event and re-raise
        (PTB already acked the update; the hold queue redispatches after reconnect) rather than shield
        the dispatch — teardown must be able to stop a flush from reaching a torn-down session."""
        await self._flush_buffered(
            self._pending_text_batches, self._pending_text_batch_tasks, key,
            self._text_batch_delay_for(self._pending_text_batches.get(key)), "text",
            lambda ev: logger.info("[Telegram] Flushing text batch %s (%d chars)", key, len(ev.text or "")))

'''

LEGACY_INSERT = ANCHOR + '''    async def _flush_text_debounce_now(self, session_key: str) -> bool:
        """Acknowledge one accepted queued text task after its quiet-window merge."""
        # MOANAIZATION PATCH: queue-ack
        state = self._text_debounce_store().get(session_key)
        event = state.event if state is not None else None
        accepted = await super()._flush_text_debounce_now(session_key)
        if not accepted or event is None:
            return accepted
        try:
            await self._send_with_retry(
                chat_id=event.source.chat_id,
                content="Принято, поставлено в очередь.",
                reply_to=event.message_id,
                metadata=None,
            )
        except Exception:
            logger.debug("[Telegram] Queue acknowledgement failed", exc_info=True)
        return accepted

'''

INSERT = ANCHOR + '''    async def _flush_text_debounce_now(self, session_key: str) -> bool:
        """Acknowledge one accepted queued text task after its quiet-window merge."""
        # MOANAIZATION PATCH: queue-ack v2
        state = self._text_debounce_store().get(session_key)
        event = state.event if state is not None else None
        already_queued = session_key in self._pending_messages
        accepted = await super()._flush_text_debounce_now(session_key)
        if not accepted or event is None or already_queued:
            return accepted
        try:
            await self._send_with_retry(
                chat_id=event.source.chat_id,
                content="Принято, поставлено в очередь.",
                reply_to=event.message_id,
                metadata=None,
            )
        except Exception:
            logger.debug("[Telegram] Queue acknowledgement failed", exc_info=True)
        return accepted

'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    source = TARGET.read_text()
    if MARKER in source:
        print(f"already patched: {TARGET}")
        return
    if LEGACY_MARKER in source:
        if source.count(LEGACY_INSERT) != 1:
            raise SystemExit(f"legacy anchor count {source.count(LEGACY_INSERT)} in {TARGET}")
        TARGET.write_text(source.replace(LEGACY_INSERT, INSERT, 1))
        print(f"migrated: {TARGET}")
        return
    if args.check and not args.apply:
        raise SystemExit(f"NOT patched: {TARGET}")
    if source.count(ANCHOR) != 1:
        raise SystemExit(f"anchor count {source.count(ANCHOR)} in {TARGET}")
    backup = TARGET.with_suffix(TARGET.suffix + ".orig-moanaization-queue-ack")
    if not backup.exists():
        backup.write_text(source)
    TARGET.write_text(source.replace(ANCHOR, INSERT, 1))
    print(f"patched: {TARGET}")


if __name__ == "__main__":
    main()
