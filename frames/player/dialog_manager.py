# frames/player/dialog_manager.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import wx
import logging
from database import db_manager
from i18n import _
from nvda_controller import speak, LEVEL_CRITICAL, LEVEL_MINIMAL, get_pause_on_dialog_setting
from utils import format_time
from dialogs import (
    bookmark_dialog,
    bookmark_list_dialog,
    goto_dialog,
    filelist_dialog,
    sleep_timer_dialog,
    goto_file_dialog
)
from . import navigation
from . import playback_logic


class DialogManager:
    """
    Manages the lifecycle of player-related dialogs.
    Handles automatic pausing/resuming of playback when dialogs open/close
    based on user settings.
    """

    def __init__(self, frame):
        self.frame = frame
        self.was_playing_before_dialog = False

    def _dialog_entry(self) -> bool:
        """
        Prepares the player for opening a modal dialog.
        Pauses playback if the 'Pause on Dialog' setting is enabled.
        """
        if not self.frame.engine:
            self.was_playing_before_dialog = False
            return False

        self.was_playing_before_dialog = self.frame.is_playing
        if get_pause_on_dialog_setting():
            if self.was_playing_before_dialog:
                self.frame.engine.pause()
                self.frame.is_playing = False
                if self.frame.ui_timer.IsRunning():
                    self.frame.ui_timer.Stop()
        return self.was_playing_before_dialog

    def _dialog_exit(self, was_playing_before: bool):
        """
        Restores player state after a dialog is closed.
        """
        if not self.frame.engine:
            return

        if get_pause_on_dialog_setting() and was_playing_before:
            if self.frame.is_playing:
                if not self.frame.ui_timer.IsRunning():
                    self.frame.ui_timer.Start(1000)
            elif not self.frame.engine.is_playing():
                self.frame.engine.play()
                self.frame.is_playing = True
                if not self.frame.ui_timer.IsRunning():
                    self.frame.ui_timer.Start(1000)

    def on_add_bookmark(self):
        """Opens the 'Add Bookmark' dialog."""
        was_playing = self._dialog_entry()
        current_time = self.frame.engine.get_time() if self.frame.engine else 0
        
        dlg = bookmark_dialog.BookmarkDialog(self.frame)
        result = dlg.ShowModal()
        
        if result == wx.ID_OK:
            data = dlg.get_data()
            try:
                db_manager.add_bookmark(
                    book_id=self.frame.book_id,
                    file_index=self.frame.current_file_index,
                    position_ms=current_time,
                    title=data['title'],
                    note=data['note']
                )
                speak(_("Bookmark added"), LEVEL_CRITICAL)
                # Logic imported from playback_logic doesn't need frame passed if we call it directly?
                # Wait, playback_logic functions take 'frame' as argument.
                # Checking if playback_logic._should_resume_on_jump() is available.
                # _should_resume_on_jump is internal there.
                # But wait, the original code called playback_logic.toggle_play_pause(self.frame).
                # That logic is fine. The internal helper _should_resume_on_jump is not exposed.
                # We should probably assume standard behavior or check setting directly.
                # Or better, let's check the setting here to avoid importing private method.
                
                resume_setting = db_manager.get_setting('resume_on_jump')
                should_resume = (resume_setting == 'True' or resume_setting is None)

                if not was_playing and should_resume:
                    playback_logic.toggle_play_pause(self.frame)
                    was_playing = True

            except Exception as e:
                logging.error(f"Error adding bookmark: {e}", exc_info=True)
                speak(_("Error adding bookmark"), LEVEL_CRITICAL)
        else:
            speak(_("Bookmark cancelled"), LEVEL_MINIMAL)
        
        dlg.Destroy()
        self._dialog_exit(was_playing)

    def on_show_bookmarks(self):
        """Opens the 'Bookmarks List' dialog."""
        was_playing = self._dialog_entry()
        dlg = bookmark_list_dialog.BookmarkListDialog(self.frame, self.frame.book_id)
        result = dlg.ShowModal()
        
        if result == wx.ID_OK:
            data = dlg.get_selected_bookmark_data()
            if data:
                speak(_("Jumping to bookmark"), LEVEL_MINIMAL)
                navigation.jump_to_bookmark(self.frame, data)
                
                resume_setting = db_manager.get_setting('resume_on_jump')
                should_resume = (resume_setting == 'True' or resume_setting is None)

                if not was_playing and should_resume:
                    wx.CallLater(100, playback_logic.toggle_play_pause, self.frame)
        
        dlg.Destroy()
        self._dialog_exit(was_playing)

    def on_goto(self):
        """Opens the 'Go To Time' dialog."""
        was_playing = self._dialog_entry()
        duration = self.frame.current_file_duration_ms
        dlg = goto_dialog.GoToDialog(self.frame, duration)
        result = dlg.ShowModal()
        
        if result == wx.ID_OK:
            target_ms = dlg.get_time_in_ms()
            if target_ms is not None:
                if self.frame.engine:
                    self.frame.engine.set_time(target_ms)
                    speak(_("Jumped to {0}").format(format_time(target_ms)), LEVEL_MINIMAL)
                    
                    resume_setting = db_manager.get_setting('resume_on_jump')
                    should_resume = (resume_setting == 'True' or resume_setting is None)

                    if not was_playing and should_resume:
                        playback_logic.toggle_play_pause(self.frame)
                        was_playing = True
        
        dlg.Destroy()
        self._dialog_exit(was_playing)

    def on_show_files(self):
        """Opens the 'File List' dialog."""
        was_playing = self._dialog_entry()
        dialog_file_list = [(fid, fpath) for fid, fpath, fidx, duration in self.frame.book_files_data]
        dlg = filelist_dialog.FileListDialog(self.frame, dialog_file_list, self.frame.current_file_index)
        result = dlg.ShowModal()
        
        if result == wx.ID_OK:
            selected_index = dlg.get_selected_index()
            if selected_index != wx.NOT_FOUND and selected_index != self.frame.current_file_index:
                try:
                    target_engine_index = self.frame.engine_to_frame_index_map.index(selected_index)
                    speak(_("Jumping to file"), LEVEL_MINIMAL)
                    self.frame.engine.playlist_jump(target_engine_index)
                    
                    resume_setting = db_manager.get_setting('resume_on_jump')
                    should_resume = (resume_setting == 'True' or resume_setting is None)

                    if not was_playing and should_resume:
                        wx.CallLater(100, playback_logic.toggle_play_pause, self.frame)
                
                except ValueError:
                    logging.warning(f"File list jump failed: File index {selected_index} is missing.")
                    speak(_("Error: The selected file is missing."), LEVEL_CRITICAL)
                except Exception as e:
                    logging.error(f"Error in on_show_files: {e}", exc_info=True)
                    speak(_("Error jumping to file."), LEVEL_CRITICAL)
        
        dlg.Destroy()
        self._dialog_exit(was_playing)

    def on_show_sleep_timer(self):
        """Opens the 'Sleep Timer' dialog."""
        if not self.frame.sleep_timer_manager:
            speak(_("Error: Sleep Timer not available."), LEVEL_CRITICAL)
            return

        try:
            duration_str = db_manager.get_setting('quick_timer_duration_minutes')
            default_duration = int(duration_str) if duration_str else 30
            default_action = db_manager.get_setting('quick_timer_action') or 'pause'
            default_os_mode = db_manager.get_setting('quick_timer_os_action_mode') or 'silent'
        except Exception as e:
            logging.warning(f"Could not read quick timer defaults: {e}")
            default_duration = 30
            default_action = 'pause'
            default_os_mode = 'silent'

        was_playing = self._dialog_entry()
        dlg = sleep_timer_dialog.SleepTimerDialog(
            self.frame,
            default_duration_minutes=default_duration,
            default_action_key=default_action,
            default_os_action_mode=default_os_mode
        )
        result = dlg.ShowModal()
        
        if result == wx.ID_OK:
            data = dlg.get_data()
            duration = data['duration_minutes']
            action = data['action_key']
            os_mode = data['os_action_mode']
            save_default = data['save_as_default']
            
            success = self.frame.sleep_timer_manager.start_timer(duration, action, os_mode)
            if success:
                speak(_("Sleep timer set for {0} minutes.").format(duration), LEVEL_CRITICAL)
            else:
                speak(_("Error starting timer."), LEVEL_CRITICAL)

            if save_default:
                try:
                    db_manager.set_setting('quick_timer_duration_minutes', str(duration))
                    db_manager.set_setting('quick_timer_action', action)
                    db_manager.set_setting('quick_timer_os_action_mode', os_mode)
                    speak(_("Quick timer defaults saved."), LEVEL_MINIMAL)
                except Exception as e:
                    logging.error(f"Failed to save quick timer defaults: {e}")
                    speak(_("Error saving defaults."), LEVEL_CRITICAL)
        else:
            speak(_("Sleep timer cancelled."), LEVEL_MINIMAL)
        
        dlg.Destroy()
        self._dialog_exit(was_playing)

    def on_goto_file(self):
        """Opens the 'Go To File Number' dialog."""
        was_playing = self._dialog_entry()
        file_count = len(self.frame.book_files_data)
        if file_count == 0:
            speak(_("No files loaded."), LEVEL_CRITICAL)
            self._dialog_exit(was_playing)
            return

        current_file_num = self.frame.current_file_index + 1
        dlg = goto_file_dialog.GoToFileDialog(
            self.frame,
            current_file_num=current_file_num,
            max_file_num=file_count
        )
        result = dlg.ShowModal()
        
        if result == wx.ID_OK:
            target_index = dlg.get_selected_index()
            if target_index == self.frame.current_file_index:
                speak(_("Already on file {0}.").format(target_index + 1), LEVEL_MINIMAL)
            else:
                try:
                    target_engine_index = self.frame.engine_to_frame_index_map.index(target_index)
                    speak(_("Jumping to file {0}").format(target_index + 1), LEVEL_MINIMAL)
                    self.frame.engine.playlist_jump(target_engine_index)
                    
                    resume_setting = db_manager.get_setting('resume_on_jump')
                    should_resume = (resume_setting == 'True' or resume_setting is None)

                    if not was_playing and should_resume:
                        wx.CallLater(100, playback_logic.toggle_play_pause, self.frame)
                
                except ValueError:
                    logging.warning(f"File list jump failed: File index {target_index} is missing.")
                    speak(_("Error: The selected file is missing."), LEVEL_CRITICAL)
                except Exception as e:
                    logging.error(f"Error in on_goto_file: {e}", exc_info=True)
                    speak(_("Error jumping to file."), LEVEL_CRITICAL)
        else:
            speak(_("Cancelled."), LEVEL_MINIMAL)
        
        dlg.Destroy()
        self._dialog_exit(was_playing)
