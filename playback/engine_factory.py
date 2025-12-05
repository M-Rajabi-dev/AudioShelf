# playback/engine_factory.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import logging
import os
import sys
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

    except ImportError:
        logging.critical("MPV engine failed: python-mpv is not installed or libmpv-2.dll failed to load.",
                         exc_info=True)
        raise
    except Exception as e:
        logging.critical(f"Failed to initialize MpvEngine: {e}", exc_info=True)
        raise RuntimeError(f"Error initializing MPV: {e}") from e