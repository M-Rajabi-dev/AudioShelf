# frames/library/chapter_selector.py
# Copyright (c) 2025-2026 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging
from typing import Optional, Tuple

import wx

from database import db_manager
from i18n import _
from nvda_controller import speak, LEVEL_MINIMAL
from audiobookshelf_client import AudiobookshelfClient, AudiobookshelfError
from playback.abs_link_resolver import resolve_audiobookshelf_target
from dialogs.chapter_list_dialog import ChapterListDialog


def _get_abs_client_and_item_for_book(book_id: int) -> Tuple[Optional[AudiobookshelfClient], Optional[str]]:
    details = db_manager.get_book_details(book_id)
    root_path = details.get("root_path") if details else None
    files = db_manager.get_book_files(book_id)
    first_stream_url = files[0][1] if files else None
    base_url, item_id, api_key = resolve_audiobookshelf_target(
        book_id=book_id,
        root_path=root_path,
        preferred_stream_url=first_stream_url,
        allow_lookup=True,
        timeout_seconds=10,
    )
    if not base_url or not item_id or not api_key:
        return None, None

    try:
        return AudiobookshelfClient(base_url, api_key, timeout_seconds=10), item_id
    except Exception:
        return None, None


def _load_abs_book_chapters(book_id: int) -> list:
    client, item_id = _get_abs_client_and_item_for_book(book_id)
    if not client or not item_id:
        return []

    try:
        chapters = client.get_item_chapters(item_id)
    except AudiobookshelfError as e:
        logging.warning(f"Audiobookshelf chapter fetch failed for item {item_id}: {e}")
        return []
    except Exception as e:
        logging.warning(f"Audiobookshelf chapter fetch failed for item {item_id}: {e}")
        return []

    normalized = []
    for idx, chapter in enumerate(chapters):
        try:
            start_ms = max(0, int(chapter.start_ms))
            end_ms = max(start_ms, int(chapter.end_ms))
            title = str(chapter.title or "").strip() or f"Chapter {idx + 1}"
            normalized.append({
                "index": idx,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "title": title,
            })
        except Exception:
            continue
    return normalized


def prompt_abs_chapter_start(
        parent: wx.Window,
        book_id: int,
        current_total_position_ms: int = 0,
        announce_if_unavailable: bool = True
) -> Optional[int]:
    """
    Returns selected chapter start position in milliseconds, or None.
    """
    chapters = _load_abs_book_chapters(book_id)
    if not chapters:
        if announce_if_unavailable:
            speak(_("No chapters are available for this book."), LEVEL_MINIMAL)
        return None

    dlg = ChapterListDialog(parent, chapters, current_total_position_ms)
    try:
        if dlg.ShowModal() != wx.ID_OK:
            return None
        selected_index = dlg.get_selected_index()
    finally:
        dlg.Destroy()

    if not (0 <= selected_index < len(chapters)):
        return None

    chapter = chapters[selected_index]
    return max(0, int(chapter.get("start_ms") or 0))
