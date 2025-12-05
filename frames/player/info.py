# frames/player/info.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import wx
import os
import logging
from i18n import _
from nvda_controller import speak, LEVEL_MINIMAL, LEVEL_CRITICAL
from utils import format_time


class InfoManager:
    """
    Manages updating the UI time display and announcing playback information
    (time, file status, sleep timer, etc.) via the screen reader.
    """

    def __init__(self, frame):
        self.frame = frame

    def announce_time(self, should_speak_time: bool):
        """
        Updates the time display label on the UI.
        Optionally speaks the current time (used by the 'I' hotkey).

        Args:
            should_speak_time: If True, triggers NVDA speech.
        """
        if self.frame.is_exiting or not self.frame.engine or self.frame.IsBeingDeleted() or not self.frame.time_text:
            return

        try:
            current_time = self.frame.engine.get_time()
            total_time = self.frame.current_file_duration_ms
            time_str = f"{format_time(current_time)} / {format_time(total_time if total_time > 0 else 0)}"
            
            wx.CallAfter(self._update_time_label, time_str)
            
            if should_speak_time:
                speak(time_str, LEVEL_CRITICAL)
        except Exception as e:
            logging.debug(f"Ignoring exception during announce_time: {e}")

    def _update_time_label(self, time_str: str):
        """Safely updates the time label on the main thread."""
        if self.frame and not self.frame.IsBeingDeleted() and self.frame.time_text:
            try:
                if self.frame.time_text.GetLabel() != time_str:
                    self.frame.time_text.SetLabel(time_str)
            except wx.PyDeadObjectError:
                logging.warning("Failed to update time label, object likely destroyed.")

    def announce_info(self):
        """Speaks the current book title and file name."""
        book_title = self.frame.book_title
        file_path = self.frame.current_file_path
        
        if not file_path:
            file_name = _("Unknown File")
        else:
            file_name = os.path.basename(file_path)
        
        speak(f"{_('Book')}: {book_title}. {file_name}", LEVEL_CRITICAL)

    def announce_file_only(self):
        """Speaks only the current file name (used on file change)."""
        file_path = self.frame.current_file_path
        
        if not file_path:
            file_name = _("Unknown File")
        else:
            file_name = os.path.basename(file_path)
        
        speak(f"{file_name}", LEVEL_MINIMAL)

    def announce_remaining_file_time(self):
        """Calculates and announces the time remaining in the current file."""
        if not self.frame.engine:
            return

        try:
            duration_ms = self.frame.current_file_duration_ms
            if duration_ms <= 0:
                speak(_("File duration not yet known."), LEVEL_CRITICAL)
                return

            current_time_ms = self.frame.engine.get_time()
            remaining_ms = duration_ms - current_time_ms
            if remaining_ms < 0:
                remaining_ms = 0
            
            speak(_("Time remaining: {0}").format(format_time(remaining_ms)), LEVEL_CRITICAL)
        except Exception as e:
            logging.error(f"Error announcing remaining file time: {e}", exc_info=True)

    def announce_adjusted_remaining_file_time(self):
        """
        Calculates and announces time remaining in the current file,
        adjusted for the current playback speed.
        """
        if not self.frame.engine:
            return

        try:
            duration_ms = self.frame.current_file_duration_ms
            current_rate = self.frame.current_target_rate

            if duration_ms <= 0:
                speak(_("File duration not yet known."), LEVEL_MINIMAL)
                return
            if current_rate == 0:
                speak(_("Playback speed is zero."), LEVEL_MINIMAL)
                return

            current_time_ms = self.frame.engine.get_time()
            real_remaining_ms = duration_ms - current_time_ms
            if real_remaining_ms < 0:
                real_remaining_ms = 0

            adjusted_remaining_ms = int(real_remaining_ms / current_rate)
            speak(_("Time remaining at current speed: {0}").format(format_time(adjusted_remaining_ms)),
                  LEVEL_CRITICAL)
        except Exception as e:
            logging.error(f"Error announcing adjusted remaining file time: {e}", exc_info=True)

    def get_timer_action_string(self, action_key: str) -> str:
        """Translates an internal action key into a human-readable string."""
        action_map = {
            'pause': _("Pause playback"),
            'close_player': _("Close player"),
            'close_app': _("Close AudioShelf"),
            'sleep': _("Sleep computer"),
            'hibernate': _("Hibernate computer"),
            'shutdown': _("Shutdown computer")
        }
        return action_map.get(action_key, _("Unknown action"))

    def announce_sleep_timer(self):
        """Announces the time remaining on the sleep timer and its configured action."""
        if not self.frame.sleep_timer_manager or not self.frame.sleep_timer_manager.is_active():
            speak(_("No active sleep timer."), LEVEL_MINIMAL)
            return

        try:
            remaining_sec = self.frame.sleep_timer_manager.get_remaining_seconds()
            action_key = self.frame.sleep_timer_manager.action_key

            if remaining_sec is None or remaining_sec < 0 or action_key is None:
                speak(_("No active sleep timer."), LEVEL_MINIMAL)
                return

            minutes, seconds = divmod(remaining_sec, 60)
            action_str = self.get_timer_action_string(action_key)
            
            msg = ""
            if minutes > 0:
                msg = _("{0} minutes {1} seconds remaining until: {2}").format(minutes, seconds, action_str)
            else:
                msg = _("{0} seconds remaining until: {1}").format(seconds, action_str)
            
            speak(msg, LEVEL_CRITICAL)
        except Exception as e:
            logging.error(f"Error announcing sleep timer: {e}", exc_info=True)

    def _calculate_total_elapsed_ms(self) -> int:
        """Calculates the total time elapsed since the beginning of the book."""
        if not self.frame.engine or not hasattr(self.frame, 'book_file_durations'):
            return 0

        total_elapsed_ms = 0
        current_file_index = self.frame.current_file_index

        if current_file_index > 0:
            try:
                total_elapsed_ms = sum(self.frame.book_file_durations[:current_file_index])
            except Exception as e:
                logging.error(f"Error summing previous file durations: {e}")

        total_elapsed_ms += self.frame.engine.get_time()
        return total_elapsed_ms

    def announce_total_elapsed_time(self):
        """Announces total elapsed time and total book duration."""
        if not hasattr(self.frame, 'total_book_duration_ms'):
            speak(_("Book duration data not available."), LEVEL_MINIMAL)
            return

        try:
            elapsed_ms = self._calculate_total_elapsed_ms()
            total_ms = self.frame.total_book_duration_ms
            speak(_("Elapsed: {0} / Total: {1}").format(
                format_time(elapsed_ms), format_time(total_ms)), LEVEL_CRITICAL)
        except Exception as e:
            logging.error(f"Error announcing total elapsed time: {e}", exc_info=True)

    def announce_total_remaining_time(self):
        """Announces the total time remaining in the entire book."""
        if not hasattr(self.frame, 'total_book_duration_ms'):
            speak(_("Book duration data not available."), LEVEL_MINIMAL)
            return

        try:
            elapsed_ms = self._calculate_total_elapsed_ms()
            total_ms = self.frame.total_book_duration_ms
            remaining_ms = total_ms - elapsed_ms
            if remaining_ms < 0:
                remaining_ms = 0
            
            speak(_("Total time remaining: {0}").format(format_time(remaining_ms)), LEVEL_CRITICAL)
        except Exception as e:
            logging.error(f"Error announcing total remaining time: {e}", exc_info=True)

    def announce_adjusted_total_remaining_time(self):
        """
        Announces total time remaining in the book, adjusted for the
        current playback speed.
        """
        if not hasattr(self.frame, 'total_book_duration_ms') or not hasattr(self.frame, 'current_target_rate'):
            speak(_("Book duration data not available."), LEVEL_MINIMAL)
            return

        try:
            current_rate = self.frame.current_target_rate
            if current_rate == 0:
                speak(_("Playback speed is zero."), LEVEL_MINIMAL)
                return

            elapsed_ms = self._calculate_total_elapsed_ms()
            total_ms = self.frame.total_book_duration_ms
            real_remaining_ms = total_ms - elapsed_ms
            if real_remaining_ms < 0:
                real_remaining_ms = 0

            adjusted_remaining_ms = int(real_remaining_ms / current_rate)
            speak(_("Total time remaining at current speed: {0}").format(
                format_time(adjusted_remaining_ms)), LEVEL_CRITICAL)
        except Exception as e:
            logging.error(f"Error announcing adjusted total remaining time: {e}", exc_info=True)
