# playback/engine_factory.py
# Copyright (c) 2025-2026 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging
import os
import sys
from i18n import _
from typing import Optional
from .base_engine import BasePlaybackEngine
from database import db_manager


def _get_dll_directory() -> str:
    """
    Determines the directory containing external DLLs (e.g., libmpv).
    Handles both frozen (PyInstaller) and standard Python environments.
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def create_engine(hwnd: Optional[int] = None) -> BasePlaybackEngine:
    """
    Factory function to initialize and return the playback engine.
    Defaults exclusively to the MPV engine.

    Args:
        hwnd: Optional window handle for video output.

    Returns:
        An instance of MpvEngine.

    Raises:
        RuntimeError: If the MPV engine cannot be initialized or dependencies are missing.
    """
    try:
        saved_engine = db_manager.get_setting('engine')
        if saved_engine and saved_engine.lower() != 'mpv':
            logging.info(f"Engine setting is '{saved_engine}', but only 'mpv' is available. Switching to MPV.")
    except Exception:
        pass

    logging.info("Initializing playback engine (MPV)...")

    try:
        dll_dir = _get_dll_directory()
        logging.info(f"Resolved DLL directory to: {dll_dir}")

        current_path = os.environ.get("PATH", "")
        if dll_dir not in current_path.split(os.pathsep):
            logging.info(f"Prepending MPV DLL directory to PATH: {dll_dir}")
            os.environ["PATH"] = dll_dir + os.pathsep + current_path
        else:
            logging.debug(f"MPV DLL directory already in PATH: {dll_dir}")

        from .mpv_engine import MpvEngine
        return MpvEngine(hwnd=hwnd)

    except ModuleNotFoundError as e:
        missing_name = getattr(e, "name", "")
        if missing_name == "mpv":
            logging.critical("MPV engine failed: python-mpv package is missing.", exc_info=True)
            raise RuntimeError(_(
                "The python-mpv package is missing. Install dependencies with: pip install -r requirements.txt"
            )) from e

        logging.critical("MPV engine failed due to missing Python module.", exc_info=True)
        raise RuntimeError(_("A required playback dependency is missing: {}").format(missing_name or e)) from e

    except ImportError as e:
        logging.critical("MPV engine failed: python-mpv is not installed or libmpv-2.dll failed to load.",
                         exc_info=True)
        raise RuntimeError(_("The playback engine (libmpv) is not installed or could not be loaded. Please reinstall the application.")) from e
    except Exception as e:
        logging.critical(f"Failed to initialize MpvEngine: {e}", exc_info=True)
        raise RuntimeError(_("An unexpected error occurred while initializing the playback engine: {}").format(e)) from e
