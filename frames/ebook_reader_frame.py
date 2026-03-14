# frames/ebook_reader_frame.py
# Copyright (c) 2025-2026 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging
import os
import threading
from typing import List, Optional, Tuple
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

import wx

from audiobookshelf_client import AudiobookshelfClient, AudiobookshelfError
from database import db_manager
from db_layer.helpers import is_remote_source
from ebook_content import EbookContent, EbookLoadError, load_ebook_content
from i18n import _
from nvda_controller import LEVEL_CRITICAL, LEVEL_MINIMAL, set_app_focus_status, speak
from playback.abs_link_resolver import resolve_audiobookshelf_target


class EbookReaderFrame(wx.Frame):
    CHUNK_SIZE = 14000
    AUTOSAVE_INTERVAL_MS = 15000

    def __init__(
            self,
            parent: wx.Frame,
            book_id: int,
            library_playlist: List[Tuple[int, str]],
            current_playlist_index: int
    ):
        style = wx.DEFAULT_FRAME_STYLE & ~(wx.MAXIMIZE_BOX)
        super(EbookReaderFrame, self).__init__(parent, title="", style=style, size=(900, 680))

        self.parent_frame = parent
        self.book_id = book_id
        self.library_playlist = library_playlist
        self.current_playlist_index = current_playlist_index

        try:
            _id, title = self.library_playlist[self.current_playlist_index]
            self.book_title = title
        except (IndexError, ValueError):
            self.book_title = _("Unknown Book")

        self.full_text = ""
        self.chapters = []
        self.chunk_start = 0
        self.source_path: Optional[str] = None
        self.root_path: Optional[str] = None
        self.local_file_path: Optional[str] = None
        self.last_synced_offset = -1

        self._init_ui()
        self._bind_events()

        self.save_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_save_timer, self.save_timer)

        self._load_book_async()

    def _init_ui(self):
        self.panel = wx.Panel(self)

        self.title_text = wx.StaticText(self.panel, label=self.book_title)
        title_font = self.title_text.GetFont()
        title_font.MakeBold()
        self.title_text.SetFont(title_font)

        self.progress_text = wx.StaticText(self.panel, label=_("Loading ebook..."))

        self.text_ctrl = wx.TextCtrl(
            self.panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.BORDER_SUNKEN
        )

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.title_text, 0, wx.EXPAND | wx.ALL, 8)
        vbox.Add(self.progress_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        vbox.Add(self.text_ctrl, 1, wx.EXPAND | wx.ALL, 8)

        self.panel.SetSizer(vbox)
        self.CentreOnParent()

    def _bind_events(self):
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_ACTIVATE, self.on_activate)
        self.text_ctrl.Bind(wx.EVT_CHAR_HOOK, self.on_key_down)

    def _load_book_async(self):
        worker = threading.Thread(target=self._load_book_worker, daemon=True)
        worker.start()

    def _load_book_worker(self):
        try:
            files = db_manager.get_book_files(self.book_id)
            if not files:
                raise EbookLoadError(_("This book has no files to read."))

            primary_file_row = files[0]
            source_path = primary_file_row[1]
            local_file_path = self._materialize_file(source_path)
            content = load_ebook_content(local_file_path)

            local_state = db_manager.get_reading_state(self.book_id) or {}
            local_offset = max(0, int(local_state.get("char_offset") or 0))
            root_path = db_manager.book_repo.get_book_path(self.book_id)
            remote_offset = self._fetch_remote_offset(root_path, source_path, len(content.text), local_offset)
            start_offset = remote_offset if remote_offset is not None else local_offset

            wx.CallAfter(
                self._on_book_loaded,
                content,
                start_offset,
                source_path,
                root_path,
                local_file_path
            )
        except Exception as e:
            logging.error(f"Failed to load ebook for book {self.book_id}: {e}", exc_info=True)
            wx.CallAfter(self._on_book_load_failed, str(e))

    def _materialize_file(self, source_path: str) -> str:
        if not source_path:
            raise EbookLoadError(_("Invalid ebook path."))

        if is_remote_source(source_path):
            parsed = urlparse(source_path)
            filename = os.path.basename(parsed.path or "").strip()
            filename = unquote(filename) if filename else f"book_{self.book_id}.ebook"

            cache_dir = os.path.join(os.path.dirname(db_manager.db_file), "ebook_cache", str(self.book_id))
            os.makedirs(cache_dir, exist_ok=True)
            cache_path = os.path.join(cache_dir, filename)

            if os.path.exists(cache_path) and os.path.getsize(cache_path) > 0:
                return cache_path

            tmp_path = cache_path + ".part"
            headers = {"User-Agent": "AudioShelf/1.0"}
            req = Request(url=source_path, method="GET", headers=headers)
            try:
                with urlopen(req, timeout=120) as response, open(tmp_path, "wb") as out:
                    while True:
                        chunk = response.read(1024 * 512)
                        if not chunk:
                            break
                        out.write(chunk)
                os.replace(tmp_path, cache_path)
            except Exception as e:
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception:
                    pass
                raise EbookLoadError(_("Failed to download ebook content from server.")) from e

            return cache_path

        if not os.path.exists(source_path):
            raise EbookLoadError(_("Ebook file not found on disk."))
        return source_path

    def _resolve_abs_target(self, root_path: Optional[str], source_path: Optional[str], allow_lookup: bool = False):
        return resolve_audiobookshelf_target(
            book_id=self.book_id,
            root_path=root_path,
            preferred_stream_url=source_path,
            allow_lookup=allow_lookup,
            timeout_seconds=10,
        )

    def _fetch_remote_offset(
            self,
            root_path: Optional[str],
            source_path: Optional[str],
            total_chars: int,
            local_offset: int
    ) -> Optional[int]:
        base_url, item_id, api_key = self._resolve_abs_target(root_path, source_path, allow_lookup=True)
        if not base_url or not item_id or not api_key or total_chars <= 0:
            return None

        try:
            client = AudiobookshelfClient(base_url, api_key, timeout_seconds=8)
            progress = client.get_media_progress(item_id)
            if not isinstance(progress, dict):
                return None

            raw_progress = progress.get("progress")
            if raw_progress is None:
                duration = float(progress.get("duration") or 0.0)
                current = float(progress.get("currentTime") or 0.0)
                if duration <= 0:
                    return None
                raw_progress = current / duration

            progress_ratio = max(0.0, min(1.0, float(raw_progress)))
            remote_offset = int(progress_ratio * total_chars)

            # Prefer remote only when it is clearly ahead of local.
            if local_offset <= 0:
                return remote_offset

            min_delta = max(250, int(total_chars * 0.01))
            if remote_offset > local_offset + min_delta:
                return remote_offset
        except (AudiobookshelfError, ValueError, TypeError):
            return None
        except Exception:
            return None

        return None

    def _on_book_loaded(
            self,
            content: EbookContent,
            start_offset: int,
            source_path: str,
            root_path: Optional[str],
            local_file_path: str
    ):
        self.full_text = content.text or ""
        self.chapters = content.chapters or []
        self.source_path = source_path
        self.root_path = root_path
        self.local_file_path = local_file_path

        if not self.full_text:
            self._on_book_load_failed(_("No readable content was found in this ebook."))
            return

        self.SetTitle(_("{0} - Ebook Reader").format(self.book_title))
        self._jump_to_offset(start_offset, announce=False)
        self.save_timer.Start(self.AUTOSAVE_INTERVAL_MS)
        self.text_ctrl.SetFocus()
        speak(_("Ebook opened."), LEVEL_MINIMAL)

    def _on_book_load_failed(self, message: str):
        speak(_("Could not open ebook."), LEVEL_CRITICAL)
        wx.MessageBox(str(message), _("Ebook Error"), wx.OK | wx.ICON_ERROR, parent=self)
        self.Close()

    def _current_offset(self) -> int:
        local_pos = self.text_ctrl.GetInsertionPoint()
        absolute = max(0, self.chunk_start + local_pos)
        return min(absolute, len(self.full_text))

    def _jump_to_offset(self, absolute_offset: int, announce: bool = True):
        if not self.full_text:
            return

        total = len(self.full_text)
        absolute_offset = max(0, min(int(absolute_offset or 0), total))

        start = max(0, absolute_offset - (self.CHUNK_SIZE // 3))
        if start > 0:
            maybe_break = self.full_text.rfind("\n", max(0, start - 300), start)
            if maybe_break != -1:
                start = maybe_break + 1

        end = min(total, start + self.CHUNK_SIZE)
        chunk = self.full_text[start:end]
        if not chunk:
            return

        self.chunk_start = start
        self.text_ctrl.ChangeValue(chunk)

        local_offset = max(0, min(absolute_offset - start, len(chunk)))
        self.text_ctrl.SetInsertionPoint(local_offset)
        self.text_ctrl.ShowPosition(local_offset)
        self._update_progress_label()

        if announce:
            speak(self.progress_text.GetLabel(), LEVEL_MINIMAL)

    def _update_progress_label(self):
        total = len(self.full_text)
        current = self._current_offset()
        if total <= 0:
            label = _("Progress: 0%")
        else:
            pct = int((current / total) * 100)
            label = _("Progress: {0}% ({1} of {2} characters)").format(pct, current, total)
        self.progress_text.SetLabel(label)

    def _sync_remote_progress_async(self, offset: int, total_chars: int):
        if total_chars <= 0:
            return

        base_url, item_id, api_key = self._resolve_abs_target(self.root_path, self.source_path, allow_lookup=False)
        if not base_url or not item_id or not api_key:
            return

        ratio = max(0.0, min(1.0, float(offset) / float(total_chars)))
        finished = ratio >= 0.999

        def worker():
            try:
                client = AudiobookshelfClient(base_url, api_key, timeout_seconds=8)
                client.update_media_progress(
                    item_id=item_id,
                    current_time_seconds=ratio,
                    duration_seconds=1.0,
                    is_finished=finished
                )
            except Exception as e:
                logging.warning(f"Audiobookshelf ebook progress sync failed for item {item_id}: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def save_progress(self, periodic: bool = False):
        if not self.full_text:
            return

        offset = self._current_offset()
        total = len(self.full_text)
        db_manager.save_reading_state(self.book_id, offset, total)
        self._update_progress_label()

        # Avoid syncing too often if nothing meaningful changed.
        min_delta = max(300, int(total * 0.005))
        changed_enough = abs(offset - self.last_synced_offset) >= min_delta
        if not periodic or changed_enough:
            self._sync_remote_progress_async(offset, total)
            self.last_synced_offset = offset

    def on_save_timer(self, _event):
        self.save_progress(periodic=True)

    def on_key_down(self, event: wx.KeyEvent):
        keycode = event.GetKeyCode()
        ctrl = event.ControlDown()

        if keycode == wx.WXK_ESCAPE:
            self.Close()
            return

        if ctrl and keycode == wx.WXK_HOME:
            self._jump_to_offset(0)
            return

        if ctrl and keycode == wx.WXK_END:
            self._jump_to_offset(len(self.full_text))
            return

        if keycode == wx.WXK_PAGEUP:
            self._jump_to_offset(self._current_offset() - (self.CHUNK_SIZE // 2))
            return

        if keycode == wx.WXK_PAGEDOWN:
            self._jump_to_offset(self._current_offset() + (self.CHUNK_SIZE // 2))
            return

        event.Skip()

    def on_activate(self, event: wx.ActivateEvent):
        if event.GetActive():
            wx.CallAfter(set_app_focus_status, True)
            if self.text_ctrl and not self.text_ctrl.IsBeingDeleted():
                self.text_ctrl.SetFocus()
        else:
            wx.CallAfter(set_app_focus_status, False)
        event.Skip()

    def on_close(self, event):
        try:
            if self.save_timer.IsRunning():
                self.save_timer.Stop()
        except Exception:
            pass

        try:
            self.save_progress(periodic=False)
        except Exception as e:
            logging.warning(f"Failed to save ebook progress on close: {e}")

        try:
            if self.parent_frame and not self.parent_frame.IsBeingDeleted():
                self.parent_frame.Show()
                self.parent_frame.Raise()
                if getattr(self.parent_frame, "last_focused_control", None):
                    wx.CallAfter(self.parent_frame.last_focused_control.SetFocus)
        except Exception:
            pass

        event.Skip()
