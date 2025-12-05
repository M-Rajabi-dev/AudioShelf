# nvda_controller.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import ctypes
import os
import sys
import logging
from database import db_manager
from i18n import _

VERBOSITY_SILENT = 'silent'
VERBOSITY_MINIMAL = 'minimal'
VERBOSITY_FULL = 'full'

LEVEL_CRITICAL = 'critical'
LEVEL_MINIMAL = 'minimal'
LEVEL_FULL = 'full'

is_app_window_focussed = False


def set_app_focus_status(is_focussed: bool):
    """Updates the global focus state of the application."""
    global is_app_window_focussed
    is_app_window_focussed = is_focussed
    logging.debug(f"Application focus state set to: {is_focussed}")


def _get_dll_path() -> str:
    """Determines the absolute path to the NVDA controller DLL."""
    dll_filename = "nvdaControllerClient.dll"
    if getattr(sys, 'frozen', False):
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, dll_filename)


DLL_PATH = _get_dll_path()
_client_lib = None
is_nvda_running = False

try:
    _client_lib = ctypes.windll.LoadLibrary(DLL_PATH)
    if _client_lib.nvdaController_testIfRunning() == 0:
        is_nvda_running = True
    else:
        logging.warning("NVDA controller loaded, but NVDA is not running.")
        is_nvda_running = False
except (OSError, AttributeError) as e:
    logging.critical(f"CRITICAL ERROR: Could not load nvdaControllerClient.dll at '{DLL_PATH}'. Details: {e}")


def speak(text: str, level: str = LEVEL_MINIMAL, interrupt: bool = True):
    """
    Speaks text via NVDA.
    
    Args:
        text: String to speak.
        level: Importance level.
        interrupt: If True, cancels previous speech immediately.
    """
    if not _client_lib or not is_nvda_running:
        return

    try:
        # Handle interrupt regardless of verbosity level or focus
        # This ensures snappy feel (e.g. stopping long previous speech on action)
        if interrupt:
            _client_lib.nvdaController_cancelSpeech()

        if not is_app_window_focussed:
            ghf_setting = db_manager.get_setting('global_hotkey_feedback')
            is_ghf_enabled = (ghf_setting == 'True' or ghf_setting is None)
            if not is_ghf_enabled and level != LEVEL_CRITICAL:
                return

        verbosity_setting = db_manager.get_setting('nvda_verbosity') or VERBOSITY_FULL
        
        is_allowed = False
        if verbosity_setting == VERBOSITY_FULL:
            is_allowed = True
        elif verbosity_setting == VERBOSITY_MINIMAL:
            is_allowed = (level == LEVEL_MINIMAL or level == LEVEL_CRITICAL)
        elif verbosity_setting == VERBOSITY_SILENT:
            is_allowed = (level == LEVEL_CRITICAL)

        if is_allowed:
            _client_lib.nvdaController_speakText(text)

    except Exception as e:
        logging.error(f"Error in nvda_controller.speak(): {e}")


def cancel_speech():
    """Immediately silences NVDA speech."""
    if not _client_lib or not is_nvda_running:
        return
    try:
        _client_lib.nvdaController_cancelSpeech()
    except Exception as e:
        logging.error(f"Error in nvda_controller.cancel_speech(): {e}")


def braille_message(text: str):
    """Sends a message to the connected Braille display."""
    if not _client_lib or not is_nvda_running:
        return
    try:
        _client_lib.nvdaController_brailleMessage(text)
    except Exception as e:
        logging.error(f"Error in nvda_controller.braille_message(): {e}")


def get_pause_on_dialog_setting() -> bool:
    """Retrieves the 'Pause on Dialog' user preference."""
    try:
        setting = db_manager.get_setting('pause_on_dialog')
        return setting == 'True'
    except Exception:
        return True


def cycle_verbosity():
    """Cycles the NVDA verbosity setting."""
    current = db_manager.get_setting('nvda_verbosity') or VERBOSITY_FULL
    
    if current == VERBOSITY_FULL:
        new_setting = VERBOSITY_MINIMAL
        display_text = _("Minimal")
    elif current == VERBOSITY_MINIMAL:
        new_setting = VERBOSITY_SILENT
        display_text = _("Silent")
    else:
        new_setting = VERBOSITY_FULL
        display_text = _("Full")

    db_manager.set_setting('nvda_verbosity', new_setting)
    speak(_("Verbosity: {0}").format(display_text), LEVEL_CRITICAL)
