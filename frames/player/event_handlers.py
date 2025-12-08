# frames/player/event_handlers.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
import logging
import os
from typing import Optional, TYPE_CHECKING

from database import db_manager
from nvda_controller import set_app_focus_status

if TYPE_CHECKING:
    from ..player_frame import PlayerFrame


def on_engine_file_changed(frame: 'PlayerFrame', event, new_engine_index: int):
    """
    Handles the 'on_file_changed' event from the engine.
    Updates the frame state, resets loops, and announces the new file.
    """
    if new_engine_index < 0 or frame.is_exiting:
        return

    # Reset Loop State
    if frame.loop_point_a_ms is not None:
        frame.loop_point_a_ms = None
    if frame.is_file_looping:
        frame.is_file_looping = False

    try:
        new_frame_index = frame.engine_to_frame_index_map[new_engine_index]
    except IndexError:
        logging.error(f"on_engine_file_changed: Invalid index {new_engine_index}")
        return

    logging.info(f"Engine file changed. Index: {new_frame_index}")
    frame.current_file_index = new_frame_index

    try:
        (frame.current_file_id,
         frame.current_file_path,
         _,
         _) = frame.book_files_data[frame.current_file_index]
    except IndexError:
        logging.error("Critical Error: Invalid file index in book data")
        return

    # Update NVDA focus label if applicable
    try:
        if frame.nvda_focus_label and frame.current_file_path:
            file_name = os.path.basename(frame.current_file_path)
            frame.nvda_focus_label.SetLabel(file_name)
    except Exception:
        pass

    # Update Duration
    try:
        frame.current_file_duration_ms = frame.book_file_durations[frame.current_file_index]
    except IndexError:
        frame.current_file_duration_ms = 0

    # Reset start position for next file
    if frame.start_pos_ms > 0:
        frame.start_pos_ms = 0



def on_engine_end_reached(frame: 'PlayerFrame', event):
    """Handles the end of the playlist."""
    # Local import to avoid circular dependency
    from . import playback_logic

    if frame.is_exiting:
        return
    wx.CallLater(100, playback_logic.play_next_file, frame)


def on_ui_timer(frame: 'PlayerFrame', event):
    """Fires periodically to update UI time labels and save state."""
    if frame.is_exiting or not frame.engine or frame.IsBeingDeleted():
        if frame.ui_timer.IsRunning():
            frame.ui_timer.Stop()
        return

    try:
        duration = frame.engine.get_length()
        if duration > 0:
            stored_duration = frame.current_file_duration_ms
            # Sync duration if significantly different
            if abs(duration - stored_duration) > 1000:
                frame.current_file_duration_ms = duration
                frame.book_file_durations[frame.current_file_index] = duration
                
                # Update internal tuple
                try:
                    (file_id, path, index, _) = frame.book_files_data[frame.current_file_index]
                    frame.book_files_data[frame.current_file_index] = (file_id, path, index, duration)
                except Exception:
                    pass

                frame.total_book_duration_ms = sum(frame.book_file_durations)
                
                # Update DB in background via event
                file_id_to_update = frame.current_file_id
                if file_id_to_update is not None:
                    wx.PostEvent(frame, frame.DurationUpdateEvent(
                        file_id=file_id_to_update,
                        duration_ms=duration
                    ))
    except Exception:
        pass

    frame.info_manager.announce_time(False)

    # Auto-save state logic
    if frame.is_playing:
        frame.save_state_counter += 1
        if frame.save_state_counter >= 30:
            save_playback_state(frame, final_time_ms=None, is_periodic=True)
            frame.save_state_counter = 0
    else:
        frame.save_state_counter = 0


def on_duration_update(frame: 'PlayerFrame', event):
    """Handles custom event to update file duration in the database."""
    try:
        db_manager.update_file_duration(event.file_id, event.duration_ms)
    except Exception as e:
        logging.error(f"Duration update failed: {e}")


def save_playback_state(frame: 'PlayerFrame', final_time_ms: Optional[int] = None, is_periodic: bool = False):
    """Saves current playback state to DB."""
    if frame.is_exiting and is_periodic:
        return

    if not frame.engine and final_time_ms is None and not frame.is_exiting:
        return

    current_time = 0
    current_rate = frame.current_target_rate

    if final_time_ms is not None:
        current_time = final_time_ms
    elif frame.engine:
        try:
            current_time = frame.engine.get_time()
        except Exception:
            pass

    try:
        db_manager.save_playback_state(
            book_id=frame.book_id,
            file_index=frame.current_file_index,
            position_ms=current_time,
            speed_rate=current_rate,
            eq_settings=frame.current_eq_settings,
            is_eq_enabled=frame.is_eq_enabled,
            nr_mode=0
        )
    except Exception as e:
        logging.error(f"Error saving state: {e}")


def on_escape(frame: 'PlayerFrame', event=None):
    """Handles closing of PlayerFrame."""
    if frame.is_exiting:
        return

    frame.is_exiting = True

    # Cleanup resources
    if hasattr(frame, 'hotkey_manager') and frame.hotkey_manager:
        frame.hotkey_manager.unregister_hotkeys()

    frame.ui_timer.Stop()

    if frame.equalizer_frame_instance:
        try:
            if not frame.equalizer_frame_instance.IsBeingDeleted():
                frame.equalizer_frame_instance.Destroy()
            frame.equalizer_frame_instance = None
        except Exception:
            pass

    if frame.sleep_timer_manager and frame.sleep_timer_manager.is_active():
        frame.sleep_timer_manager.cancel_timer()

    # Save final state
    current_time = 0
    if frame.engine:
        try:
            current_vol = frame.engine.get_volume()
            db_manager.set_setting('master_volume', str(current_vol))
            current_time = frame.engine.get_time()
            frame.engine.release()
        except Exception as e:
            logging.error(f"Error releasing engine: {e}")
        finally:
            frame.engine = None

    save_playback_state(frame, final_time_ms=current_time, is_periodic=False)

    # Update parent UI
    if frame.parent_frame and hasattr(frame.parent_frame, 'update_history_list'):
        wx.CallAfter(frame.parent_frame.update_history_list)

    try:
        wx.GetApp().player_frame_instance = None
    except Exception:
        pass

    wx.CallAfter(_show_parent, frame)
    wx.CallAfter(frame.Destroy)
    set_app_focus_status(False)


def _show_parent(frame: 'PlayerFrame'):
    """Restores parent LibraryFrame focus."""
    try:
        if frame.parent_frame and not frame.parent_frame.IsBeingDeleted():
            frame.parent_frame.Show()
            frame.parent_frame.Raise()
            
            # Attempt to restore focus to specific control
            target = getattr(frame.parent_frame, 'last_focused_control', None)
            if not target:
                target = getattr(frame.parent_frame, 'library_list', frame.parent_frame)
            
            if target and not target.IsBeingDeleted():
                target.SetFocus()
            else:
                frame.parent_frame.SetFocus()
    except Exception:
        pass
