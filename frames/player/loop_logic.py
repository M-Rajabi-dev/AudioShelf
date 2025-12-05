# frames/player/loop_logic.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import logging
from i18n import _
from nvda_controller import speak, LEVEL_CRITICAL, LEVEL_MINIMAL


def set_loop_start(frame):
    """Sets the A-B loop start point (Point A) at the current playback time."""
    if not frame.engine:
        return
    current_time_ms = frame.engine.get_time()
    frame.loop_point_a_ms = current_time_ms
    speak(_("Loop start point set"), LEVEL_MINIMAL)


def set_loop_end(frame):
    """
    Sets the A-B loop end point (Point B) and activates the loop.
    Requires Point A to be set previously.
    """
    if not frame.engine:
        return
    if frame.loop_point_a_ms is None:
        speak(_("Error: Loop start point (S) not set"), LEVEL_CRITICAL)
        return

    point_a_ms = frame.loop_point_a_ms
    point_b_ms = frame.engine.get_time()

    if point_b_ms < point_a_ms:
        speak(_("Error: Loop end point must be after start point"), LEVEL_CRITICAL)
        return

    frame.engine.set_loop_a(point_a_ms)
    frame.engine.set_loop_b(point_b_ms)
    frame.engine.set_time(point_a_ms)
    speak(_("Loop activated"), LEVEL_MINIMAL)


def clear_loop(frame):
    """Deactivates and clears the A-B loop."""
    if not frame.engine:
        return
    frame.engine.clear_loop()
    frame.loop_point_a_ms = None
    speak(_("Loop deactivated"), LEVEL_MINIMAL)


def toggle_file_loop(frame):
    """Toggles the repeat mode for the current file."""
    if not frame.engine:
        return
    current_state = frame.is_file_looping
    new_state = not current_state
    frame.engine.set_loop_file(new_state)
    frame.is_file_looping = new_state

    if new_state:
        speak(_("Repeat file on"), LEVEL_MINIMAL)
    else:
        speak(_("Repeat file off"), LEVEL_MINIMAL)