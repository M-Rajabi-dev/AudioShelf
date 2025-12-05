# frames/player/controls.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import wx
import logging
from i18n import _
from nvda_controller import speak, LEVEL_CRITICAL, LEVEL_MINIMAL, cycle_verbosity
from . import (
    event_handlers,
    playback_logic,
    volume_logic,
    seek_logic,
    speed_logic,
    loop_logic,
    actions_logic,
    navigation
)


def on_key_down(frame, event: wx.KeyEvent):
    """
    Central keyboard event handler for the PlayerFrame.
    Dispatches key presses to specific logic modules based on key codes and modifiers.

    Args:
        frame: The parent PlayerFrame instance.
        event: The wx.KeyEvent to process.
    """
    if not frame.engine:
        event.Skip()
        return

    keycode = event.GetKeyCode()
    ctrl_down = event.ControlDown()
    shift_down = event.ShiftDown()
    alt_down = event.AltDown()

    # Play/Pause/Stop
    if keycode == wx.WXK_SPACE:
        if shift_down:
            playback_logic.stop_playback(frame)
        elif not ctrl_down and not alt_down:
            playback_logic.toggle_play_pause(frame)

    # Volume
    elif keycode == wx.WXK_UP:
        volume_logic.change_volume(frame, 5)
    elif keycode == wx.WXK_DOWN:
        volume_logic.change_volume(frame, -5)
    elif keycode == ord('M'):
        volume_logic.toggle_mute(frame)

    # Seeking
    elif keycode == wx.WXK_LEFT:
        if ctrl_down:
            seek_amount = seek_logic._get_seek_amount('long_seek_backward_ms', 300000)
            seek_logic.seek_relative(frame, -seek_amount)
        else:
            seek_logic.seek_backward_setting(frame)
    elif keycode == wx.WXK_RIGHT:
        if ctrl_down:
            seek_amount = seek_logic._get_seek_amount('long_seek_forward_ms', 300000)
            seek_logic.seek_relative(frame, seek_amount)
        else:
            seek_logic.seek_forward_setting(frame)

    # Speed Logic
    elif keycode == ord('J'):
        if shift_down:
            speed_logic.change_speed_snapping(frame, 0.5)
        else:
            speed_logic.change_speed(frame, 0.1)
    elif keycode == ord('H'):
        if shift_down:
            speed_logic.change_speed_snapping(frame, -0.5)
        else:
            speed_logic.change_speed(frame, -0.1)
    elif keycode == ord('K'):
        speed_logic.toggle_reset_speed(frame)

    # Navigation (File / Library / Bookmark)
    elif keycode == wx.WXK_PAGEDOWN:
        if ctrl_down:
            navigation.goto_next_book_in_library(frame)
        elif shift_down:
            navigation.goto_next_bookmark(frame)
        else:
            # Manual navigation: Do NOT trigger End of Book logic
            playback_logic.play_next_file(frame, manual=True)
            
    elif keycode == wx.WXK_PAGEUP:
        if ctrl_down:
            navigation.goto_prev_book_in_library(frame)
        elif shift_down:
            navigation.goto_prev_bookmark(frame)
        else:
            playback_logic.play_prev_file(frame)

    # File Navigation (Home/End/Restart)
    elif keycode == wx.WXK_HOME:
        seek_logic.restart_file(frame)
    elif keycode == wx.WXK_END:
        end_pos = max(0, frame.current_file_duration_ms - 1000)
        seek_logic.seek_absolute(frame, end_pos, speak_time=False)
        speak(_("End of file"), LEVEL_MINIMAL)
    elif keycode == wx.WXK_BACK:
        if shift_down:
            seek_logic.seek_to_end_minus_30(frame)
        elif ctrl_down:
            seek_logic.seek_to_middle(frame)
        elif not alt_down:
            seek_logic.restart_file(frame)

    # Bookmark Actions
    elif keycode == ord('B'):
        if ctrl_down:
            frame.dialog_manager.on_show_bookmarks()
        elif shift_down:
            frame.dialog_manager.on_add_bookmark()
        elif not alt_down:
            actions_logic.quick_bookmark(frame)

    # A-B Loop
    elif keycode == ord('S'):
        loop_logic.set_loop_start(frame)
    elif keycode == ord('D'):
        loop_logic.clear_loop(frame)
    elif keycode == ord('A'):
        loop_logic.set_loop_end(frame)

    # File Loop
    elif keycode == ord('R'):
        loop_logic.toggle_file_loop(frame)

    # Sleep Timer
    elif keycode == ord('T'):
        if ctrl_down:
            frame.dialog_manager.on_show_sleep_timer()
        elif shift_down:
            actions_logic.cancel_sleep_timer(frame)
        elif alt_down:
            frame.info_manager.announce_sleep_timer()
        else:
            actions_logic.quick_sleep_timer(frame)

    # Info Announcements
    elif keycode == ord('I'):
        if ctrl_down:
            frame.info_manager.announce_info()
        elif alt_down:
            frame.info_manager.announce_remaining_file_time()
        elif shift_down:
            frame.info_manager.announce_adjusted_remaining_file_time()
        else:
            frame.info_manager.announce_time(True)
    elif keycode == ord('O'):
        if alt_down:
            frame.info_manager.announce_total_remaining_time()
        elif shift_down:
            frame.info_manager.announce_adjusted_total_remaining_time()
        elif not ctrl_down:
            frame.info_manager.announce_total_elapsed_time()

    # Dialogs / Exit
    elif keycode == ord('G'):
        if ctrl_down:
            frame.dialog_manager.on_goto_file()
        else:
            frame.dialog_manager.on_goto()
    elif keycode == ord('F'):
        frame.dialog_manager.on_show_files()
    elif keycode == wx.WXK_ESCAPE:
        event_handlers.on_escape(frame)

    # Equalizer
    elif keycode == ord('E'):
        if ctrl_down:
            frame.on_show_equalizer()
        elif not shift_down and not alt_down:
            new_state = not frame.is_eq_enabled
            frame.on_eq_enabled_changed(new_state)
            state_str = _("On") if new_state else _("Off")
            speak(_("Equalizer {0}").format(state_str), LEVEL_CRITICAL)

    # Verbosity
    elif keycode == ord('V') and ctrl_down and shift_down:
        cycle_verbosity()

    # Pinned Books (1-9)
    elif ctrl_down and (ord('1') <= keycode <= ord('9')):
        index = keycode - ord('1')
        navigation.play_pinned_book_by_index(frame, index)

    else:
        event.Skip()
