# frames/player/playback_logic.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
import logging
import time
from typing import TYPE_CHECKING

from database import db_manager
from i18n import _
from nvda_controller import speak, LEVEL_FULL, LEVEL_MINIMAL

if TYPE_CHECKING:
    from ..player_frame import PlayerFrame


def _get_end_of_book_action() -> str:
    """Retrieves user preference for end of book action."""
    try:
        action = db_manager.get_setting('end_of_book_action')
        if action not in ['stop', 'loop', 'close']:
            return 'stop'
        return action
    except Exception as e:
        logging.error(f"Error reading end_of_book_action: {e}")
        return 'stop'


def _should_resume_on_jump() -> bool:
    """Checks if 'Resume on Jump' setting is enabled."""
    try:
        setting = db_manager.get_setting('resume_on_jump')
        return setting == 'True' or setting is None
    except Exception:
        return True


def _refresh_parent_ui(frame: 'PlayerFrame'):
    """Refreshes the main library list to show status changes."""
    if frame.parent_frame and hasattr(frame.parent_frame, 'library_list'):
        from ..library import list_manager
        wx.CallAfter(list_manager.refresh_library_data, frame.parent_frame)
        wx.CallAfter(list_manager.populate_library_list, frame.parent_frame)


def toggle_play_pause(frame: 'PlayerFrame'):
    """
    Toggles the playback state.
    Handles Smart Resume logic.
    """
    if not frame.engine:
        return

    if frame.engine.get_length() == 0:
        try:
            frame.engine.playlist_jump(frame.engine_to_frame_index_map.index(frame.current_file_index))
            frame.engine.set_time(0)
        except Exception:
            pass

    if frame.engine.is_playing():
        frame.engine.pause()
        frame.is_playing = False
        if frame.ui_timer.IsRunning():
            frame.ui_timer.Stop()
        frame.last_pause_time = time.time()
        speak(_("Paused"), LEVEL_FULL)
    else:
        try:
            dur = frame.current_file_duration_ms
            pos = frame.engine.get_time()
            if dur > 0 and (dur - pos) < 1000:
                frame.engine.set_time(0)
        except Exception:
            pass

        if frame.last_pause_time > 0:
            try:
                current_time = time.time()
                pause_duration = current_time - frame.last_pause_time
                
                threshold_str = db_manager.get_setting('smart_resume_threshold_sec')
                rewind_str = db_manager.get_setting('smart_resume_rewind_ms')
                
                threshold_sec = int(threshold_str) if threshold_str else 300
                rewind_ms = int(rewind_str) if rewind_str else 10000

                if pause_duration > threshold_sec and rewind_ms > 0:
                    current_pos = frame.engine.get_time()
                    new_pos = max(0, current_pos - rewind_ms)
                    frame.engine.set_time(new_pos)
                    speak(_("Smart Resume: {0} seconds back").format(rewind_ms // 1000), LEVEL_MINIMAL)
            except Exception as e:
                logging.error(f"Error in Smart Resume logic: {e}")
            frame.last_pause_time = 0.0

        frame.engine.play()
        frame.is_playing = True
        if not frame.ui_timer.IsRunning():
            frame.ui_timer.Start(1000)
        speak(_("Playing"), LEVEL_FULL)


def play_next_file(frame: 'PlayerFrame', manual: bool = False):
    """
    Advances to the next file.
    
    Args:
        manual: If True, indicates user pressed Next key.
                If False, indicates auto-advance (EOF).
    """
    from . import event_handlers

    if not frame.engine:
        return

    was_playing = frame.is_playing

    # Check if we are at the end of the playlist
    if frame.current_file_index + 1 >= len(frame.book_files_data):
        if manual:
            # User pressed PageDown at the last file -> Just notify
            speak(_("End of book"), LEVEL_MINIMAL)
            return
        else:
            # Auto-advance (EOF reached) -> Execute End of Book logic
            try:
                db_manager.book_repo.set_book_finished(frame.book_id, True)
                _refresh_parent_ui(frame)
            except Exception as e:
                logging.error(f"Error marking book finished: {e}")

            action = _get_end_of_book_action()
            logging.info(f"End of book reached (Auto). Action: {action}")

            # Reset to first file
            frame.current_file_index = 0
            try:
                frame.engine.playlist_jump(0)
                frame.engine.play()
                frame.engine.set_time(0)
                frame.engine.pause()
            except Exception:
                pass
            
            event_handlers.save_playback_state(frame, final_time_ms=0, is_periodic=False)

            if action == 'loop':
                speak(_("End of book. Looping."), LEVEL_MINIMAL)
                if not was_playing and _should_resume_on_jump():
                    wx.CallLater(100, toggle_play_pause, frame)
            elif action == 'close':
                speak(_("End of book. Closing."), LEVEL_MINIMAL)
                wx.CallLater(100, event_handlers.on_escape, frame)
            else:  # stop
                speak(_("End of book"), LEVEL_MINIMAL)
                frame.is_playing = False
                if frame.ui_timer.IsRunning():
                    frame.ui_timer.Stop()
                frame.last_pause_time = 0.0
                frame.info_manager.announce_time(False)
            return

    # Normal next file
    frame.engine.playlist_next()
    if not was_playing and _should_resume_on_jump():
        wx.CallLater(100, toggle_play_pause, frame)


def play_prev_file(frame: 'PlayerFrame'):
    """Moves playback to the previous file."""
    if not frame.engine:
        return

    was_playing = frame.is_playing

    if frame.current_file_index <= 0:
        speak(_("Start of book"), LEVEL_MINIMAL)
        return

    frame.engine.playlist_previous()
    if not was_playing and _should_resume_on_jump():
        wx.CallLater(100, toggle_play_pause, frame)


def stop_playback(frame: 'PlayerFrame'):
    """
    Stops playback, resets position to 0, but keeps file loaded.
    """
    from . import event_handlers

    if not frame.engine:
        return

    frame.engine.play()
    frame.engine.set_time(0)
    frame.engine.pause()

    frame.is_playing = False
    if frame.ui_timer.IsRunning():
        frame.ui_timer.Stop()

    frame.last_pause_time = 0.0

    try:
        event_handlers.save_playback_state(frame, final_time_ms=0, is_periodic=False)
        speak(_("Stopped."), LEVEL_MINIMAL)
    except Exception as e:
        logging.error(f"Error saving state during stop: {e}", exc_info=True)

    frame.info_manager.announce_time(False)
