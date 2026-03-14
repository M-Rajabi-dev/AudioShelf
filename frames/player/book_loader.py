# frames/player/book_loader.py
# Copyright (c) 2025-2026 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
import os
import logging
from datetime import datetime
from typing import Optional, Tuple
from database import db_manager
from i18n import _
from audiobookshelf_client import AudiobookshelfClient, AudiobookshelfError
from playback.abs_link_resolver import resolve_audiobookshelf_target
from playback.abs_sync_utils import (
    compute_total_position_ms,
    split_total_position_ms,
    parse_local_timestamp_to_epoch_ms,
    should_prefer_remote_progress,
)
from . import event_handlers

class BookLoader:
    def __init__(self, frame):
        self.frame = frame

    def _get_abs_client_and_item(self, root_path: Optional[str], first_stream_url: Optional[str]) -> Tuple[Optional[AudiobookshelfClient], Optional[str]]:
        base_url, item_id, api_key = resolve_audiobookshelf_target(
            book_id=self.frame.book_id,
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

    def _load_remote_chapters(
            self,
            root_path: Optional[str],
            first_stream_url: Optional[str]
    ) -> list:
        client, item_id = self._get_abs_client_and_item(root_path, first_stream_url)
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

    def _apply_remote_progress_if_newer(
            self,
            root_path: Optional[str],
            local_state: Optional[dict],
            local_file_index: int,
            local_start_pos_ms: int,
            file_durations_ms: list,
            first_stream_url: Optional[str]
    ) -> Tuple[int, int]:
        client, item_id = self._get_abs_client_and_item(root_path, first_stream_url)
        if not client or not item_id:
            return local_file_index, local_start_pos_ms

        try:
            remote_progress = client.get_media_progress(item_id)
        except AudiobookshelfError as e:
            logging.warning(f"Audiobookshelf progress fetch failed for item {item_id}: {e}")
            return local_file_index, local_start_pos_ms
        except Exception as e:
            logging.warning(f"Audiobookshelf progress fetch failed for item {item_id}: {e}")
            return local_file_index, local_start_pos_ms

        if not remote_progress:
            return local_file_index, local_start_pos_ms

        remote_current_time_sec = float(remote_progress.get("currentTime") or 0.0)
        remote_position_ms = max(0, int(remote_current_time_sec * 1000))
        remote_last_update_ms = remote_progress.get("lastUpdate")
        try:
            remote_last_update_ms = int(remote_last_update_ms) if remote_last_update_ms is not None else None
        except (TypeError, ValueError):
            remote_last_update_ms = None

        local_last_update_ms = parse_local_timestamp_to_epoch_ms((local_state or {}).get("last_played_at"))
        local_total_position_ms = compute_total_position_ms(file_durations_ms, local_file_index, local_start_pos_ms)

        if should_prefer_remote_progress(
                remote_last_update_ms=remote_last_update_ms,
                local_last_update_ms=local_last_update_ms,
                remote_total_position_ms=remote_position_ms,
                local_total_position_ms=local_total_position_ms,
        ):
            remote_file_index, remote_file_pos_ms = split_total_position_ms(file_durations_ms, remote_position_ms)
            logging.info(f"Audiobookshelf progress applied for item {item_id}: file={remote_file_index}, pos={remote_file_pos_ms}ms")
            return remote_file_index, remote_file_pos_ms

        return local_file_index, local_start_pos_ms

    def load_book_data(self):
        frame = self.frame
        try:
            details = db_manager.get_book_details(frame.book_id)
            if not frame.book_title:
                frame.book_title = details['title'] if details else _("Unknown Book")

            frame.SetTitle(frame.book_title)
            if frame.title_text:
                frame.title_text.SetLabel(frame.book_title)

            frame.book_files_data = db_manager.get_book_files(frame.book_id)
            if not frame.book_files_data:
                raise ValueError(f"No playable files found for book_id {frame.book_id}")

            frame.book_file_durations = [duration for (_, _, _, duration) in frame.book_files_data]
            frame.total_book_duration_ms = sum(frame.book_file_durations)
            frame.book_chapters = []

            state = db_manager.get_playback_state(frame.book_id)

            file_index = 0
            start_pos_ms = 0
            start_rate = 1.0
            eq_settings = "0,0,0,0,0,0,0,0,0,0"
            is_eq_enabled = False

            if state:
                file_index = state.get('last_file_index', 0)
                start_pos_ms = state.get('last_position_ms', 0)
                start_rate = state.get('last_speed_rate', 1.0)
                eq_settings = state.get('last_eq_settings', eq_settings)
                is_eq_enabled = state.get('is_eq_enabled', is_eq_enabled)

                try:
                    threshold_sec = int(db_manager.get_setting('smart_resume_threshold_sec') or 300)
                    rewind_ms = int(db_manager.get_setting('smart_resume_rewind_ms') or 0)
                    last_played_str = state.get('last_played_at')

                    if rewind_ms > 0 and start_pos_ms > 0 and last_played_str:
                        last_played_dt = datetime.strptime(last_played_str, '%Y-%m-%d %H:%M:%S.%f')
                        diff_seconds = (datetime.now() - last_played_dt).total_seconds()

                        if diff_seconds > threshold_sec:
                            start_pos_ms = max(0, start_pos_ms - rewind_ms)
                            logging.info(f"Smart Rewind applied: {rewind_ms}ms back.")
                except Exception as e:
                    logging.warning(f"Could not apply smart rewind: {e}")

            root_path = details.get("root_path") if details else None
            first_stream_url = frame.book_files_data[0][1] if frame.book_files_data else None
            frame.book_chapters = self._load_remote_chapters(root_path, first_stream_url)
            file_index, start_pos_ms = self._apply_remote_progress_if_newer(
                root_path=root_path,
                local_state=state,
                local_file_index=file_index,
                local_start_pos_ms=start_pos_ms,
                file_durations_ms=frame.book_file_durations,
                first_stream_url=first_stream_url,
            )

            if frame.initial_seek_ms_override is not None:
                override_total_ms = max(0, int(frame.initial_seek_ms_override or 0))
                file_index, start_pos_ms = split_total_position_ms(frame.book_file_durations, override_total_ms)
                frame.initial_seek_ms_override = None
                logging.info(f"Applying explicit start position override: {override_total_ms}ms")

            if not (0 <= file_index < len(frame.book_files_data)):
                logging.warning(f"Saved file index {file_index} out of bounds. Resetting to 0.")
                file_index = 0
                start_pos_ms = 0

            frame.current_file_index = file_index

            try:
                frame.current_file_duration_ms = frame.book_file_durations[file_index]
                (frame.current_file_id, frame.current_file_path, _, _) = frame.book_files_data[file_index]
            except IndexError:
                raise ValueError(f"Critical index error: Could not retrieve file at index {file_index}")

            frame.start_pos_ms = start_pos_ms
            frame.current_target_rate = start_rate
            frame.previous_target_rate = frame.current_target_rate
            frame.current_eq_settings = eq_settings
            frame.is_eq_enabled = is_eq_enabled

            if frame.nvda_focus_label and frame.current_file_path:
                file_name = os.path.basename(frame.current_file_path)
                frame.nvda_focus_label.SetLabel(file_name)

            frame._update_audio_filters()

        except Exception as e:
            logging.error(f"Error loading book data: {e}", exc_info=True)
            wx.MessageBox(_("Error loading book data. Please check logs."), _("Load Error"),
                          wx.OK | wx.ICON_ERROR, parent=frame)
            wx.CallAfter(lambda: event_handlers.on_escape(frame, None))

    def start_playback(self):
        frame = self.frame
        if frame.is_exiting or not frame.engine:
            return

        frame.engine_to_frame_index_map.clear()
        file_paths_to_load = []

        for i, (file_id, path, file_index, duration) in enumerate(frame.book_files_data):
            file_paths_to_load.append(path)
            frame.engine_to_frame_index_map.append(i)

        if not file_paths_to_load:
            logging.error("start_playback: No files found in DB list.")
            wx.MessageBox(_("Error: No audio files found for this book."),
                          _("Playback Error"), wx.OK | wx.ICON_ERROR, parent=frame)
            wx.CallAfter(lambda: event_handlers.on_escape(frame, None))
            return

        try:
            new_start_index = frame.engine_to_frame_index_map.index(frame.current_file_index)
        except ValueError:
            logging.warning("Index mismatch. Resetting to start.")
            new_start_index = 0
            frame.current_file_index = frame.engine_to_frame_index_map[0]
            (frame.current_file_id, frame.current_file_path, _, _) = frame.book_files_data[0]
            frame.start_pos_ms = 0

        success = frame.engine.load_playlist(
            file_paths=file_paths_to_load,
            start_index=new_start_index,
            start_time_ms=frame.start_pos_ms,
            rate=frame.current_target_rate
        )

        if success:
            frame.engine.play()
            frame.is_playing = True
            if not frame.ui_timer.IsRunning():
                frame.ui_timer.Start(1000)
            if frame.nvda_focus_label and not frame.nvda_focus_label.IsBeingDeleted():
                frame.nvda_focus_label.SetFocus()
        else:
            logging.error("Engine failed to load playlist.")
            wx.MessageBox(_("Error: Could not load the audio file."),
                          _("Playback Error"), wx.OK | wx.ICON_ERROR, parent=frame)
            frame.is_playing = False
            wx.CallAfter(lambda: event_handlers.on_escape(frame, None))

    def _clear_current_book_state(self):
        frame = self.frame
        frame.book_id = -1
        frame.book_title = ""
        frame.book_files_data.clear()
        frame.book_file_durations.clear()
        frame.total_book_duration_ms = 0
        frame.current_file_index = 0
        frame.current_file_id = None
        frame.current_file_path = None
        frame.current_file_duration_ms = 0
        frame.is_playing = False
        frame.start_pos_ms = 0
        frame.current_target_rate = 1.0
        frame.previous_target_rate = 1.0
        frame.engine_to_frame_index_map.clear()
        frame.loop_point_a_ms = None
        frame.is_file_looping = False
        frame.save_state_counter = 0
        frame.current_eq_settings = "0,0,0,0,0,0,0,0,0,0"
        frame.is_eq_enabled = False
        frame.book_chapters = []
        frame.initial_seek_ms_override = None

    def load_new_book(self, new_book_id: int, new_book_title: str):
        frame = self.frame
        if frame.is_exiting:
            return

        logging.info(f"Switching to Book ID {new_book_id}...")

        if frame.engine:
            current_time = 0
            try:
                current_time = frame.engine.get_time()
            except Exception as e:
                logging.warning(f"Could not get time for saving old book: {e}")

            if current_time > 60000:
                if frame.parent_frame and hasattr(frame.parent_frame, 'update_history_list'):
                    wx.CallAfter(frame.parent_frame.update_history_list)

            event_handlers.save_playback_state(frame, final_time_ms=current_time)
            frame.engine.stop()
            
            if frame.ui_timer.IsRunning():
                frame.ui_timer.Stop()

        self._clear_current_book_state()
        frame.book_id = new_book_id
        frame.book_title = new_book_title
        
        self.load_book_data()
        self.start_playback()
