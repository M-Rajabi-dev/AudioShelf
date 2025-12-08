# frames/player/seek_logic.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging
from database import db_manager
from i18n import _
from nvda_controller import speak, LEVEL_MINIMAL, LEVEL_FULL
from utils import format_time, format_time_spoken


def _get_seek_amount(key: str, default_ms: int) -> int:
    """
    Retrieves a seek duration preference from the database.
    """
    try:
        setting_str = db_manager.get_setting(key)
        return int(setting_str)
    except Exception as e:
        logging.error(f"Error reading seek setting '{key}', falling back to {default_ms}ms: {e}")
        return default_ms


def seek_backward_setting(frame):
    """Seeks backward by the amount defined in user settings."""
    seek_amount = _get_seek_amount('seek_backward_ms', 10000)
    seek_relative(frame, -seek_amount)


def seek_forward_setting(frame):
    """Seeks forward by the amount defined in user settings."""
    seek_amount = _get_seek_amount('seek_forward_ms', 30000)
    seek_relative(frame, seek_amount)


def seek_relative(frame, ms: int):
    """
    Seeks playback relative to the current position.
    Announces the jump direction and amount.
    Only speaks in FULL verbosity mode to avoid clutter in MINIMAL mode.
    """
    if not frame.engine:
        logging.warning("seek_relative called but engine not ready.")
        return

    current_time = frame.engine.get_time()
    new_time = current_time + ms
    seek_absolute(frame, new_time, speak_time=False)

    # Use absolute value for duration message
    abs_ms = abs(ms)
    duration_str = format_time_spoken(abs_ms)

    if ms > 0:
        speak(_("{0} forward").format(duration_str), LEVEL_FULL)
    else:
        speak(_("{0} back").format(duration_str), LEVEL_FULL)

    # We don't auto-announce the new timestamp here to keep it clean,
    # unless user explicitly asks for time (via 'I' hotkey).
    # But updating the UI label is handled by seek_absolute -> announce_time(False)


def seek_absolute(frame, target_ms: int, speak_time: bool = True):
    """
    Seeks to a specific timestamp in the current file.
    """
    if not frame.engine:
        logging.warning("seek_absolute called but engine not ready.")
        return

    new_time = max(0, target_ms)
    if frame.current_file_duration_ms > 0:
        # Clamp to 1 second before the end to prevent accidental EOF
        new_time = min(new_time, frame.current_file_duration_ms - 1000)
        new_time = max(0, new_time)

    frame.engine.set_time(new_time)

    if speak_time:
        speak(_("Jumped to {0}").format(format_time(new_time)), LEVEL_FULL)

    frame.info_manager.announce_time(False)


def restart_file(frame):
    """Seeks to the beginning (00:00) of the current file."""
    speak(_("Restart file"), LEVEL_FULL)
    seek_absolute(frame, 0, speak_time=False)


def seek_to_middle(frame):
    """Jumps to the 50% mark of the current file."""
    if frame.current_file_duration_ms <= 0:
        speak(_("File duration not yet known."), LEVEL_MINIMAL)
        return

    target_ms = frame.current_file_duration_ms // 2
    speak(_("Jumping to 50 percent"), LEVEL_FULL)
    seek_absolute(frame, target_ms)


def seek_to_end_minus_30(frame):
    """Jumps to 30 seconds before the end of the current file."""
    if frame.current_file_duration_ms <= 0:
        speak(_("File duration not yet known."), LEVEL_MINIMAL)
        return

    target_ms = frame.current_file_duration_ms - 30000
    speak(_("Jumping to 30 seconds from end"), LEVEL_FULL)
    seek_absolute(frame, target_ms)
