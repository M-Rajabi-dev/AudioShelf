# utils.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import wx
import os
import sys
import logging
import datetime
import subprocess
from typing import Optional, List, TYPE_CHECKING
from i18n import _

if TYPE_CHECKING:
    from frames.player_frame import PlayerFrame


def format_time(ms: int) -> str:
    """
    Converts milliseconds to a formatted string (HH:MM:SS).
    """
    s = ms // 1000
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02}:{m:02}:{s:02}"


def format_time_spoken(ms: int) -> str:
    """
    Converts milliseconds to a spoken string (e.g., "5 minutes", "30 seconds").
    """
    seconds = ms // 1000
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []
    if hours > 0:
        parts.append(_("{0} hours").format(hours))
    if minutes > 0:
        parts.append(_("{0} minutes").format(minutes))
    if secs > 0 or (hours == 0 and minutes == 0):
        parts.append(_("{0} seconds").format(secs))
    
    return " ".join(parts)


class SleepTimer:
    """
    Manages the sleep timer logic, execution, and cancellation.
    """

    @property
    def OS_ACTION_KEYS(self) -> List[str]:
        return ['sleep', 'hibernate', 'shutdown']

    @property
    def OS_ACTION_LABELS(self) -> dict:
        from i18n import _
        return {
            'sleep': _("Sleep computer"),
            'hibernate': _("Hibernate computer"),
            'shutdown': _("Shutdown computer")
        }

    def __init__(self, player_frame: 'PlayerFrame'):
        self.frame = player_frame
        self.timer = wx.Timer(self.frame)
        self.frame.Bind(wx.EVT_TIMER, self._on_timer_fired, self.timer)
        self.action_key: Optional[str] = None
        self.os_action_mode: Optional[str] = 'silent'
        self.end_time: Optional[datetime.datetime] = None

    def start_timer(self, duration_minutes: int, action_key: str, os_action_mode: str) -> bool:
        """Starts the sleep timer."""
        try:
            self.cancel_timer()
            self.action_key = action_key
            self.os_action_mode = os_action_mode
            duration_ms = duration_minutes * 60 * 1000
            
            if duration_ms < 0:
                logging.warning(f"Invalid sleep timer duration: {duration_minutes} minutes.")
                return False

            now = datetime.datetime.now()
            self.end_time = now + datetime.timedelta(minutes=duration_minutes)

            # Cap duration to wx.Timer limit (approx 24 days)
            max_wx_duration = 2 ** 31 - 1
            if duration_ms > max_wx_duration:
                logging.warning(f"Timer duration {duration_minutes}m exceeds limit. Capping.")
                duration_ms = max_wx_duration

            self.timer.StartOnce(duration_ms)
            logging.info(f"Sleep timer started: Action '{self.action_key}' in {duration_minutes} minutes.")
            return True
        except Exception as e:
            logging.error(f"Error starting sleep timer: {e}", exc_info=True)
            return False

    def cancel_timer(self) -> bool:
        """Cancels the active sleep timer."""
        if not self.is_active():
            return False
        try:
            self.timer.Stop()
            self.action_key = None
            self.os_action_mode = None
            self.end_time = None
            logging.info("Sleep timer cancelled by user.")
            return True
        except Exception as e:
            logging.error(f"Error cancelling sleep timer: {e}", exc_info=True)
            return False

    def is_active(self) -> bool:
        """Checks if the sleep timer is currently running."""
        return self.timer.IsRunning() or self.end_time is not None

    def get_remaining_seconds(self) -> Optional[int]:
        """Calculates the remaining time in seconds."""
        if not self.is_active() or self.end_time is None:
            return None
        remaining_delta = self.end_time - datetime.datetime.now()
        remaining_seconds = int(remaining_delta.total_seconds())
        return max(0, remaining_seconds)

    def _on_timer_fired(self, event: wx.Event):
        action = self.action_key
        mode = self.os_action_mode
        self.action_key = None
        self.os_action_mode = 'silent'
        self.end_time = None

        if action:
            self._execute_action(action, mode)
        else:
            logging.warning("Sleep timer fired, but no action key was set.")

    def _execute_action(self, action_key: str, mode: Optional[str]):
        logging.info(f"Sleep timer fired. Executing action: '{action_key}'")
        
        if action_key == 'pause':
            if self.frame.engine and self.frame.is_playing:
                self.frame.engine.pause()
                self.frame.is_playing = False
                if self.frame.ui_timer.IsRunning():
                    self.frame.ui_timer.Stop()
            return
        
        elif action_key == 'close_player':
            wx.CallAfter(self.frame.on_escape)
            return
        
        elif action_key == 'close_app':
            main_app_frame = self.frame.parent_frame
            if main_app_frame:
                wx.CallAfter(main_app_frame.Close)
            else:
                wx.CallAfter(self.frame.on_escape)
            return

        if action_key not in self.OS_ACTION_KEYS:
            logging.warning(f"Unknown sleep timer action key: '{action_key}'")
            return

        if mode not in ['silent', 'confirm', 'timed']:
            mode = 'silent'

        command_args = self._get_os_command_args(action_key)
        if not command_args:
            logging.error(f"No command found for OS action: {action_key}")
            return

        action_label = self.OS_ACTION_LABELS.get(action_key, "Unknown Action")

        if mode == 'silent':
            self._run_os_command(command_args)
        elif mode == 'confirm':
            wx.CallAfter(self._run_confirm_dialog, command_args, action_label)
        elif mode == 'timed':
            wx.CallAfter(self._run_timed_dialog, command_args, action_label)

    def _run_confirm_dialog(self, command_args: list, action_label: str):
        from i18n import _
        result = wx.MessageBox(
            _("The sleep timer has expired. Proceed with action: {0}?").format(action_label),
            _("Confirm Action"),
            wx.YES_NO | wx.ICON_QUESTION,
            None
        )
        if result == wx.YES:
            self._run_os_command(command_args)
        else:
            logging.info("OS action cancelled by user in confirm dialog.")

    def _run_timed_dialog(self, command_args: list, action_label: str):
        try:
            from dialogs.timed_action_dialog import TimedActionDialog
        except ImportError as e:
            logging.error(f"Failed to import TimedActionDialog: {e}. Falling back to confirm dialog.")
            self._run_confirm_dialog(command_args, action_label)
            return

        dlg = TimedActionDialog(None, action_label=action_label)
        result = dlg.ShowModal()
        dlg.Destroy()

        if result == wx.ID_OK:
            self._run_os_command(command_args)
        else:
            logging.info("Timed dialog cancelled by user. OS action aborted.")

    def _run_os_command(self, command_args: List[str]):
        logging.info(f"Executing OS command: {' '.join(command_args)}")
        try:
            subprocess.run(command_args, check=False, shell=False)
        except Exception as e:
            logging.error(f"Failed to execute OS command: {e}", exc_info=True)

    def _get_os_command_args(self, action_key: str) -> Optional[List[str]]:
        """Returns the platform-specific command arguments for the action."""
        if action_key == 'shutdown':
            if sys.platform == "win32":
                return ["shutdown", "/s", "/t", "1"]
            elif sys.platform == "darwin":
                return ["shutdown", "-h", "now"]
            else:
                return ["shutdown", "-P", "now"]
        
        elif action_key == 'sleep':
            if sys.platform == "win32":
                # rundll32 method for sleep is common but hibernate might be safer if available
                return ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"]
            elif sys.platform == "darwin":
                return ["pmset", "sleepnow"]
            else:
                return ["systemctl", "suspend"]
        
        elif action_key == 'hibernate':
            if sys.platform == "win32":
                return ["shutdown", "/h"]
            elif sys.platform == "darwin":
                return ["pmset", "sleepnow"]
            else:
                return ["systemctl", "hibernate"]
        
        return None
