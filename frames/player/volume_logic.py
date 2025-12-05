# frames/player/volume_logic.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

from i18n import _
from nvda_controller import speak, LEVEL_MINIMAL, LEVEL_FULL


def change_volume(frame, delta: int):
    """
    Changes the playback volume by a fixed delta.
    Clamps the volume between 0 and 100.

    Args:
        frame: The PlayerFrame instance.
        delta: The amount to change (positive or negative).
    """
    current_vol = frame.engine.get_volume()
    new_vol = max(0, min(100, current_vol + delta))
    frame.engine.set_volume(new_vol)
    speak(f"{_('Volume')} {new_vol}%", LEVEL_FULL)


def toggle_mute(frame):
    """Toggles the mute state of the playback engine."""
    is_muted = frame.engine.get_mute()
    frame.engine.set_mute(not is_muted)
    speak(_("Mute On") if not is_muted else _("Mute Off"), LEVEL_MINIMAL)