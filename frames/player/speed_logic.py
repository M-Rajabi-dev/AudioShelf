# frames/player/speed_logic.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from decimal import Decimal, ROUND_HALF_UP, getcontext
from i18n import _
from nvda_controller import speak, LEVEL_MINIMAL

# Set precision for decimal calculations
getcontext().prec = 6


def change_speed(frame, delta: float):
    """
    Changes the playback speed by a fixed delta (e.g., 0.1).
    Clamps the rate between 0.5x and 3.0x.

    Args:
        frame: The PlayerFrame instance.
        delta: The amount to change the speed by.
    """
    current_rate = frame.current_target_rate
    current_rate_dec = Decimal(str(current_rate))
    delta_dec = Decimal(str(delta))

    frame.previous_target_rate = frame.current_target_rate
    new_rate_dec = current_rate_dec + delta_dec

    MIN_RATE_DEC = Decimal('0.5')
    MAX_RATE_DEC = Decimal('3.0')

    new_rate = None

    if MIN_RATE_DEC <= new_rate_dec <= MAX_RATE_DEC:
        new_rate = float(new_rate_dec.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP))
    else:
        if new_rate_dec > MAX_RATE_DEC and current_rate_dec < MAX_RATE_DEC:
            new_rate = float(MAX_RATE_DEC)
        elif new_rate_dec < MIN_RATE_DEC and current_rate_dec > MIN_RATE_DEC:
            new_rate = float(MIN_RATE_DEC)
        else:
            speak(_("Speed limit reached"), LEVEL_MINIMAL)
            frame.previous_target_rate = current_rate
            return

    if new_rate is not None:
        frame.engine.set_rate(new_rate)
        frame.current_target_rate = new_rate
        speak(_("Speed {0}x").format(new_rate), LEVEL_MINIMAL)


def change_speed_snapping(frame, delta: float):
    """
    Changes playback speed by a larger delta, snapping to the nearest 0.5x increment.
    Useful for quick speed adjustments (e.g., Shift+J).

    Args:
        frame: The PlayerFrame instance.
        delta: The approximate change amount (e.g., 0.5).
    """
    current_rate = frame.current_target_rate
    current_rate_dec = Decimal(str(current_rate))
    delta_dec = Decimal(str(delta))

    frame.previous_target_rate = frame.current_target_rate
    target_rate_dec = current_rate_dec + delta_dec
    snapped_rate_dec = (target_rate_dec * 2).quantize(Decimal('0'), rounding=ROUND_HALF_UP) / Decimal('2')

    MIN_RATE_DEC = Decimal('0.5')
    MAX_RATE_DEC = Decimal('3.0')

    new_rate = None

    if MIN_RATE_DEC <= snapped_rate_dec <= MAX_RATE_DEC:
        new_rate = float(snapped_rate_dec)
    else:
        new_rate = float(MAX_RATE_DEC if snapped_rate_dec > MAX_RATE_DEC else MIN_RATE_DEC)

    if new_rate == frame.current_target_rate:
        if (delta > 0 and current_rate == float(MAX_RATE_DEC)) or \
           (delta < 0 and current_rate == float(MIN_RATE_DEC)):
            speak(_("Speed limit reached"), LEVEL_MINIMAL)
        else:
            frame.engine.set_rate(new_rate)
            frame.current_target_rate = new_rate
            speak(_("Speed {0}x").format(new_rate), LEVEL_MINIMAL)
        return

    if new_rate is not None:
        frame.engine.set_rate(new_rate)
        frame.current_target_rate = new_rate
        speak(_("Speed {0}x").format(new_rate), LEVEL_MINIMAL)


def toggle_reset_speed(frame):
    """
    Toggles the playback speed between normal (1.0x) and the previously set speed.
    """
    if frame.current_target_rate == 1.0:
        restore_rate = frame.previous_target_rate
        if restore_rate == 1.0:
            restore_rate = 1.5

        frame.engine.set_rate(restore_rate)
        frame.current_target_rate = restore_rate
        speak(_("Speed restored to {0}x").format(restore_rate), LEVEL_MINIMAL)

    else:
        frame.previous_target_rate = frame.current_target_rate
        frame.engine.set_rate(1.0)
        frame.current_target_rate = 1.0
        speak(_("Speed reset to 1.0x"), LEVEL_MINIMAL)