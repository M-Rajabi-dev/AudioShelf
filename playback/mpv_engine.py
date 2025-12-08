# playback/mpv_engine.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import mpv
import logging
import os
import sys
from i18n import _
from typing import Optional, Callable, Any, Dict, List

from .base_engine import BasePlaybackEngine


class MpvEngine(BasePlaybackEngine):
    """
    Implementation of the playback engine using python-mpv (libmpv).
    """

    def __init__(self, hwnd: Optional[int] = None):
        """
        Initializes the MPV engine instance.
        """
        super().__init__(hwnd=hwnd)
        self.player: Optional[mpv.MPV] = None
        self._hwnd = hwnd
        self._event_callbacks: Dict[str, Callable[..., Any]] = {}

        self._is_advancing_from_eof: bool = False
        self._is_initial_load: bool = False
        self._pending_start_time_ms: int = 0

        try:
            logging.info("Initializing MPV Engine...")

            if getattr(sys, 'frozen', False):
                base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
            else:
                base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

            dll_name = "libmpv-2.dll"
            dll_path = os.path.join(base_path, dll_name)

            if not os.path.exists(dll_path):
                logging.warning(f"{dll_name} not found in application root. Relying on System PATH.")

            self.player = mpv.MPV(
                wid=str(self._hwnd) if self._hwnd else None,
                vo='null',
                video=False,
                input_vo_keyboard=False,
                input_default_bindings=False,
                loop_playlist='no',
                keep_open='yes',
                config=False,
                osd_level=0,
                terminal=False
            )

            self.player.event_callback('file-loaded')(self._on_file_loaded)
            logging.info("MPV Engine initialized successfully.")

        except Exception as e:
            logging.critical(f"Failed to initialize MPV Engine. Error: {e}", exc_info=True)
            self.player = None

            error_msg = str(e)
            if "module not found" in error_msg.lower() or "dll" in error_msg.lower():
                raise RuntimeError(_(
                    "Critical Error: The playback engine (libmpv-2.dll) is missing or incompatible.\nPlease reinstall the application.")) from e
            else:
                raise RuntimeError(
                    _("Error: The playback engine could not be initialized.\nDetails: {0}").format(e)) from e

    def _on_file_loaded(self, event):
        """Internal callback triggered when MPV finishes loading a file."""
        try:
            if self._is_initial_load:
                self._is_initial_load = False
                target_ms = self._pending_start_time_ms
                self._pending_start_time_ms = 0

                if self.player:
                    self.player.command('seek', target_ms / 1000.0, 'absolute')

            elif self._is_advancing_from_eof:
                self._is_advancing_from_eof = False
                if self.player:
                    self.player.command('seek', 0.0, 'absolute')

        except Exception as e:
            logging.error(f"Error in _on_file_loaded handler: {e}")

    def set_hwnd(self, hwnd: int):
        """Sets the window handle for MPV."""
        self._hwnd = hwnd
        if self.player:
            try:
                self.player.wid = str(hwnd)
            except Exception as e:
                logging.warning(f"Failed to set MPV HWND: {e}")

    def load_playlist(
            self,
            file_paths: List[str],
            start_index: int,
            start_time_ms: int,
            rate: float
    ) -> bool:
        """Loads a list of files into MPV's internal playlist."""
        if not self.player: return False
        if not file_paths: return False
        if not (0 <= start_index < len(file_paths)): return False

        try:
            self._is_initial_load = True
            self._pending_start_time_ms = start_time_ms

            self.player.speed = rate
            self.player.command('playlist-clear')

            for path in file_paths:
                self.player.command('loadfile', path, 'append')

            self.player.playlist_pos = start_index
            self.player.pause = True

            logging.info(f"MPV Engine: Playlist loaded ({len(file_paths)} files). Start Index: {start_index}")
            return True

        except Exception as e:
            logging.error(f"Error loading playlist into MPV: {e}", exc_info=True)
            self._is_initial_load = False
            return False

    def play(self):
        """Resumes playback."""
        if self.player:
            self.player.pause = False

    def pause(self):
        """Pauses playback."""
        if self.player:
            self.player.pause = True

    def stop(self):
        """Stops playback."""
        if self.player:
            self.player.stop()

    def is_playing(self) -> bool:
        """Checks if the engine is currently playing media."""
        if not self.player: return False
        try:
            return (not self.player.idle_active) and (not self.player.pause)
        except Exception:
            return False

    def get_time(self) -> int:
        """Returns current position in milliseconds."""
        if not self.player or self.player.time_pos is None: return 0
        return int(self.player.time_pos * 1000)

    def set_time(self, time_ms: int):
        """Seeks to the specified time in milliseconds."""
        if not self.player:
            return

        if self._is_initial_load:
            self._pending_start_time_ms = time_ms
            return

        try:
            self.player.command('seek', time_ms / 1000.0, 'absolute')
        except Exception as e:
            logging.error(f"Error executing MPV seek command: {e}")

    def get_length(self) -> int:
        """Returns duration in milliseconds."""
        if not self.player or self.player.duration is None: return 0
        return int(self.player.duration * 1000)

    def get_rate(self) -> float:
        """Returns current playback speed."""
        if not self.player: return 1.0
        return self.player.speed

    def set_rate(self, rate: float):
        """Sets playback speed."""
        if self.player:
            self.player.speed = rate

    def set_loop_a(self, time_ms: int):
        """Sets A-B loop start."""
        if self.player:
            self.player.ab_loop_a = time_ms / 1000.0

    def set_loop_b(self, time_ms: int):
        """Sets A-B loop end."""
        if self.player:
            self.player.ab_loop_b = time_ms / 1000.0

    def clear_loop(self):
        """Clears A-B loop."""
        if self.player:
            self.player.ab_loop_a = 'no'
            self.player.ab_loop_b = 'no'

    def set_loop_file(self, loop: bool):
        """Enables or disables file looping."""
        if self.player:
            self.player.loop_file = 'inf' if loop else 'no'

    def set_audio_filters(self, filter_string: str):
        """Applies audio filters (e.g., EQ) via the 'af' property."""
        if self.player:
            try:
                self.player.af = filter_string
            except Exception as e:
                logging.error(f"Failed to set audio filters ({filter_string}): {e}")

    def playlist_next(self) -> bool:
        """Skips to the next file."""
        if self.player:
            try:
                self.player.command('playlist-next')
                return True
            except Exception:
                return False
        return False

    def playlist_previous(self):
        """Skips to the previous file."""
        if self.player:
            try:
                self.player.command('playlist-prev')
                return True
            except Exception:
                return False
        return False

    def playlist_jump(self, index: int, start_time_ms: int = 0) -> bool:
        """Jumps to a specific playlist index."""
        if self.player:
            try:
                self._is_initial_load = True
                self._pending_start_time_ms = start_time_ms
                self.player.playlist_pos = index
                return True
            except Exception as e:
                logging.warning(f"Error setting playlist_pos to {index}: {e}")
                return False
        return False

    def get_current_file_index(self) -> Optional[int]:
        """Returns the current playlist index."""
        if self.player:
            try:
                return self.player.playlist_pos
            except Exception:
                return None
        return None

    def get_volume(self) -> int:
        """Returns volume (0-100)."""
        if not self.player: return 100
        return int(self.player.volume)

    def set_volume(self, volume: int):
        """Sets volume (0-100)."""
        if self.player:
            self.player.volume = max(0, min(100, volume))

    def get_mute(self) -> bool:
        """Returns mute state."""
        if not self.player: return False
        return self.player.mute

    def set_mute(self, mute: bool):
        """Sets mute state."""
        if self.player:
            self.player.mute = mute

    def attach_event(self, event_name: str, callback: Callable[..., Any]):
        """Attaches callbacks for engine events."""
        if not self.player: return

        if event_name == "on_end_reached":
            def _on_eof(prop_name, prop_value):
                if prop_value and self.player:
                    try:
                        pos = self.player.playlist_pos
                        count = self.player.playlist_count

                        if pos is not None and count is not None:
                            if pos == (count - 1):
                                callback(event_name)
                            else:
                                self._is_advancing_from_eof = True
                                self.player.command('playlist-next')
                    except Exception as e:
                        logging.error(f"Error in _on_eof callback: {e}")

            self._event_callbacks[event_name] = _on_eof
            self.player.observe_property('eof-reached', _on_eof)

        elif event_name == "on_file_changed":
            def _on_file_change(prop_name, prop_value):
                if prop_value is not None and self.player:
                    self.clear_loop()
                    self.player.loop_file = 'no'
                    callback(event_name, prop_value)

            self._event_callbacks[event_name] = _on_file_change
            self.player.observe_property('playlist-pos', _on_file_change)

        else:
            logging.warning(f"MpvEngine does not support the event: '{event_name}'")

    def release(self):
        """Releases MPV resources."""
        logging.info("Releasing MPV Engine resources...")
        if self.player:
            try:
                self.set_audio_filters("")
                self._event_callbacks.clear()
                self.player.stop()
                self.player.terminate()
            except Exception as e:
                logging.error(f"Error releasing MPV player: {e}")
            finally:
                self.player = None
        logging.info("MPV Engine resources released.")