# frames/player/info.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

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

    def _get_spoken_duration(self, ms):
        """Helper to convert ms to spoken string like '2 hours, 5 minutes'."""
        if ms < 0: ms = 0
        total_seconds = int(ms / 1000)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        parts = []
        
        # Handle Hours
        if hours > 0:
            label = "hour" if hours == 1 else "hours"
            parts.append(f"{hours} {label}")
        
        # Handle Minutes (Always show unless 0 and we have hours, but user wants detail)
        if minutes > 0:
            label = "minute" if minutes == 1 else "minutes"
            parts.append(f"{minutes} {label}")
            
        # Handle Seconds (Show if it's the only thing, or generally for precision)
        if seconds > 0 or not parts:
            label = "second" if seconds == 1 else "seconds"
            parts.append(f"{seconds} {label}")

        return ", ".join(parts)

    def announce_time(self, should_speak_time: bool):
        """
        Announces: You have listened to X of Y.
        """
        if self.frame.is_exiting or not self.frame.engine or self.frame.IsBeingDeleted() or not self.frame.time_text:
            return

        try:
            current_ms = self.frame.engine.get_time()
            total_ms = self.frame.current_file_duration_ms
            
            # Update visual label (Keep mathematical for visual, or change if you like)
            # For visuals, we stick to standard format usually, but here is the logic:
            time_str_visual = f"{format_time(current_ms)} / {format_time(total_ms if total_ms > 0 else 0)}"
            wx.CallAfter(self._update_time_label, time_str_visual)
            
            if should_speak_time:
                spoken_current = self._get_spoken_duration(current_ms)
                spoken_total = self._get_spoken_duration(total_ms)
                # Spoken: "You have listened to 5 minutes of 10 minutes"
                msg = _("You have listened to {0} of {1}").format(spoken_current, spoken_total)
                speak(msg, LEVEL_CRITICAL)
        except Exception as e:
            logging.debug(f"Ignoring exception during announce_time: {e}")

    def copy_current_time(self):
        if not self.frame.engine:
            return

        try:
            current_ms = self.frame.engine.get_time()
            time_str = format_time(current_ms)

            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(wx.TextDataObject(time_str))
                wx.TheClipboard.Close()
                speak(_("Time copied."), LEVEL_MINIMAL)
        except Exception as e:
            logging.error(f"Failed to copy time to clipboard: {e}")

    def _update_time_label(self, time_str: str):
        """Safely updates the time label on the main thread."""
        if self.frame and not self.frame.IsBeingDeleted() and self.frame.time_text:
            try:
                if self.frame.time_text.GetLabel() != time_str:
                    self.frame.time_text.SetLabel(time_str)
            except wx.PyDeadObjectError:
                logging.warning("Failed to update time label, object likely destroyed.")

    def announce_remaining_file_time(self):
        """
        Announces: X remaining of Y.
        """
        if not self.frame.engine:
            return

        try:
            total_ms = self.frame.current_file_duration_ms
            if total_ms <= 0:
                speak(_("File duration not yet known."), LEVEL_CRITICAL)
                return

            current_ms = self.frame.engine.get_time()
            remaining_ms = max(0, total_ms - current_ms)
            
            spoken_remaining = self._get_spoken_duration(remaining_ms)
            spoken_total = self._get_spoken_duration(total_ms)

            # Spoken: "5 minutes remaining of 10 minutes"
            speak(_("{0} remaining of {1}").format(spoken_remaining, spoken_total), LEVEL_CRITICAL)
        except Exception as e:
            logging.error(f"Error announcing remaining file time: {e}", exc_info=True)

    def announce_adjusted_remaining_file_time(self):
        """
        Announces remaining time adjusted by speed.
        """
        if not self.frame.engine:
            return

        try:
            total_ms = self.frame.current_file_duration_ms
            current_rate = self.frame.current_target_rate

            if total_ms <= 0:
                speak(_("File duration not yet known."), LEVEL_MINIMAL)
                return
            if current_rate == 0:
                speak(_("Playback speed is zero."), LEVEL_MINIMAL)
                return

            current_ms = self.frame.engine.get_time()
            real_remaining_ms = max(0, total_ms - current_ms)
            adjusted_remaining_ms = int(real_remaining_ms / current_rate)

            spoken_adjusted = self._get_spoken_duration(adjusted_remaining_ms)
            
            # Spoken: "3 minutes remaining at current speed"
            speak(_("{0} remaining at current speed").format(spoken_adjusted), LEVEL_CRITICAL)
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
        """Announces total elapsed vs total book duration verbally."""
        if not hasattr(self.frame, 'total_book_duration_ms'):
            speak(_("Book duration data not available."), LEVEL_MINIMAL)
            return

        try:
            elapsed_ms = self._calculate_total_elapsed_ms()
            total_ms = self.frame.total_book_duration_ms
            
            spoken_elapsed = self._get_spoken_duration(elapsed_ms)
            spoken_total = self._get_spoken_duration(total_ms)

            msg = _("You have listened to {0} of {1}").format(spoken_elapsed, spoken_total)
            speak(msg, LEVEL_CRITICAL)
        except Exception as e:
            logging.error(f"Error announcing total elapsed time: {e}", exc_info=True)

    def announce_total_remaining_time(self):
        """Announces total remaining time verbally."""
        if not hasattr(self.frame, 'total_book_duration_ms'):
            speak(_("Book duration data not available."), LEVEL_MINIMAL)
            return

        try:
            elapsed_ms = self._calculate_total_elapsed_ms()
            total_ms = self.frame.total_book_duration_ms
            remaining_ms = max(0, total_ms - elapsed_ms)
            
            spoken_remaining = self._get_spoken_duration(remaining_ms)
            spoken_total = self._get_spoken_duration(total_ms)

            msg = _("{0} remaining of {1}").format(spoken_remaining, spoken_total)
            speak(msg, LEVEL_CRITICAL)
        except Exception as e:
            logging.error(f"Error announcing total remaining time: {e}", exc_info=True)

    def announce_adjusted_total_remaining_time(self):
        """Announces adjusted total remaining time verbally."""
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
            real_remaining_ms = max(0, total_ms - elapsed_ms)
            adjusted_remaining_ms = int(real_remaining_ms / current_rate)
            
            spoken_adjusted = self._get_spoken_duration(adjusted_remaining_ms)

            speak(_("{0} remaining of book at current speed").format(spoken_adjusted), LEVEL_CRITICAL)
        except Exception as e:
            logging.error(f"Error announcing adjusted total remaining time: {e}", exc_info=True)