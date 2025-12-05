# frames/player/actions_logic.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import logging
from database import db_manager
from i18n import _
from nvda_controller import speak, LEVEL_CRITICAL, LEVEL_MINIMAL
from utils import format_time


def quick_bookmark(frame):
    """
    Adds a bookmark at the current playback position immediately,
    using a default title based on the timestamp.
    """
    if not frame.engine:
        return

    try:
        current_time_ms = frame.engine.get_time()
        default_title = _("Quick Bookmark at {0}").format(format_time(current_time_ms))
        
        db_manager.add_bookmark(
            book_id=frame.book_id,
            file_index=frame.current_file_index,
            position_ms=current_time_ms,
            title=default_title,
            note=""
        )
        speak(_("Quick Bookmark added"), LEVEL_MINIMAL)
    except Exception as e:
        logging.error(f"Error adding quick bookmark: {e}", exc_info=True)
        speak(_("Error adding bookmark"), LEVEL_CRITICAL)


def quick_sleep_timer(frame):
    """
    Starts the sleep timer using the default duration and action
    settings defined in the configuration.
    """
    if not frame.sleep_timer_manager:
        speak(_("Error: Sleep Timer not available."), LEVEL_CRITICAL)
        return

    try:
        duration_str = db_manager.get_setting('quick_timer_duration_minutes')
        action_key = db_manager.get_setting('quick_timer_action')
        os_mode = db_manager.get_setting('quick_timer_os_action_mode')
        
        if not os_mode:
            os_mode = 'silent'
        
        duration = int(duration_str) if duration_str else 30
        success = frame.sleep_timer_manager.start_timer(duration, action_key, os_mode)
        
        if success:
            # Use public method on info_manager (needs update in info.py)
            action_str = frame.info_manager.get_timer_action_string(action_key)
            speak(_("Quick timer set for {0} minutes. Action: {1}").format(duration, action_str), LEVEL_CRITICAL)
        else:
            speak(_("Error starting quick timer."), LEVEL_CRITICAL)

    except Exception as e:
        logging.error(f"Error reading quick timer defaults: {e}", exc_info=True)
        speak(_("Error: Could not load quick timer settings."), LEVEL_CRITICAL)


def cancel_sleep_timer(frame):
    """Cancels the active sleep timer if one is running."""
    if not frame.sleep_timer_manager:
        return

    if frame.sleep_timer_manager.cancel_timer():
        speak(_("Sleep timer cancelled."), LEVEL_CRITICAL)
    else:
        speak(_("No active sleep timer to cancel."), LEVEL_MINIMAL)
