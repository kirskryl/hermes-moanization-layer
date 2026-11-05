#!/usr/bin/env python3
"""Keep adjacent Telegram text and image messages in one inbound turn."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

TARGET = Path(os.environ.get("HERMES_TELEGRAM_ADAPTER", Path.home() / ".hermes/hermes-agent/plugins/platforms/telegram/adapter.py"))
MARKER = "MOANAIZATION PATCH: unified-inbox"

OLD_TEXT = '''    def _enqueue_text_event(self, event: MessageEvent) -> None:
        """Buffer a text chunk, or hold it while delayed delivery must be dropped."""
        if self._should_drop_delayed_delivery():
            self._hold_inbound_event(event, where="text-enqueue")
            return
        super()._enqueue_text_event(event)
        self._accept_update()
'''
NEW_TEXT = '''    def _enqueue_text_event(self, event: MessageEvent) -> None:
        """Buffer text with adjacent photos from the same session when possible."""
        if self._should_drop_delayed_delivery():
            self._hold_inbound_event(event, where="text-enqueue")
            return
        # MOANAIZATION PATCH: unified-inbox
        session_key = self._text_batch_key(event)
        photo_key = f"{session_key}:photo-burst"
        if photo_key in self._pending_photo_batches:
            self._enqueue_photo_event(photo_key, event)
            return
        for group_id, group_event in list(self._media_group_events.items()):
            if self._event_session_key(group_event) == session_key:
                self._merge_into_pending(self._media_group_events, group_id, event)
                prior = self._media_group_tasks.get(group_id)
                if prior and not prior.done():
                    prior.cancel()
                self._media_group_tasks[group_id] = asyncio.create_task(self._flush_media_group_event(group_id))
                self._accept_update()
                return
        super()._enqueue_text_event(event)
        self._accept_update()
'''

OLD_PHOTO = '''    def _enqueue_photo_event(self, batch_key: str, event: MessageEvent) -> None:
        """Merge photo events into a pending batch and schedule flush."""
        if self._should_drop_delayed_delivery():
            self._hold_inbound_event(event, where="photo-enqueue")
            return
        self._merge_into_pending(self._pending_photo_batches, batch_key, event)
        self._accept_update()
'''
NEW_PHOTO = '''    def _enqueue_photo_event(self, batch_key: str, event: MessageEvent) -> None:
        """Merge photo events with nearby text and schedule one flush."""
        if self._should_drop_delayed_delivery():
            self._hold_inbound_event(event, where="photo-enqueue")
            return
        # MOANAIZATION PATCH: unified-inbox
        text_key = self._text_batch_key(event)
        pending_text = self._pending_text_batches.pop(text_key, None)
        if pending_text is not None:
            prior_text = self._pending_text_batch_tasks.pop(text_key, None)
            if prior_text and not prior_text.done():
                prior_text.cancel()
            event.text = self._merge_caption(pending_text.text, event.text)
        self._merge_into_pending(self._pending_photo_batches, batch_key, event)
        self._accept_update()
'''

OLD_GROUP = '''        self._merge_into_pending(self._media_group_events, media_group_id, event)
        self._accept_update()
'''
NEW_GROUP = '''        # MOANAIZATION PATCH: unified-inbox
        text_key = self._text_batch_key(event)
        pending_text = self._pending_text_batches.pop(text_key, None)
        if pending_text is not None:
            prior_text = self._pending_text_batch_tasks.pop(text_key, None)
            if prior_text and not prior_text.done():
                prior_text.cancel()
            event.text = self._merge_caption(pending_text.text, event.text)
        self._merge_into_pending(self._media_group_events, media_group_id, event)
        self._accept_update()
'''

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    source = TARGET.read_text()
    if all(fragment in source for fragment in ("# " + MARKER, "if photo_key in self._pending_photo_batches:", "pending_text = self._pending_text_batches.pop(text_key, None)")):
        print(f"already patched: {TARGET}")
        return
    if args.check and not args.apply:
        raise SystemExit(f"NOT patched: {TARGET}")
    for old, new in ((OLD_TEXT, NEW_TEXT), (OLD_PHOTO, NEW_PHOTO), (OLD_GROUP, NEW_GROUP)):
        if source.count(old) != 1:
            raise SystemExit(f"anchor count {source.count(old)} in {TARGET}")
        source = source.replace(old, new, 1)
    group_delay = "    MEDIA_GROUP_WAIT_SECONDS = 0.8"
    if source.count(group_delay) != 1:
        raise SystemExit(f"media group delay anchor count {source.count(group_delay)}")
    source = source.replace(group_delay, "    MEDIA_GROUP_WAIT_SECONDS = 2.0  # MOANAIZATION PATCH: unified-inbox", 1)
    backup = TARGET.with_suffix(TARGET.suffix + ".orig-moanaization-unified")
    if not backup.exists():
        backup.write_text(TARGET.read_text())
    TARGET.write_text(source)
    print(f"patched: {TARGET}")

if __name__ == "__main__":
    main()
