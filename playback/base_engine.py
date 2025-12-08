# playback/base_engine.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from abc import ABC, abstractmethod
from typing import Optional, Callable, Any, List


class BasePlaybackEngine(ABC):
    """
    Abstract Base Class defining the interface for the playback engine.
    Enforces a consistent API for the PlayerFrame to interact with the backend (MPV).
    """

    @abstractmethod
    def __init__(self, hwnd: Optional[int] = None):
        """
        Initializes the engine.

        Args:
            hwnd: Optional window handle for video output or message handling.
        """
        pass

    @abstractmethod
    def set_hwnd(self, hwnd: int):
        """Sets the window handle for the engine."""
        pass

    @abstractmethod
    def load_playlist(
            self,
            file_paths: List[str],
            start_index: int,
            start_time_ms: int,
            rate: float
    ) -> bool:
        """
        Loads a list of media files as the current playlist.

        Args:
            file_paths: List of absolute paths to media files.
            start_index: The 0-based index to start playback from.
            start_time_ms: The position in milliseconds to seek to immediately.
            rate: The initial playback speed.

        Returns:
            True if loading was successful, False otherwise.
        """
        pass

    @abstractmethod
    def play(self):
        """Starts or resumes playback."""
        pass

    @abstractmethod
    def pause(self):
        """Pauses playback."""
        pass

    @abstractmethod
    def stop(self):
        """Stops playback and clears the internal state/playlist."""
        pass

    @abstractmethod
    def is_playing(self) -> bool:
        """Checks if the engine is currently playing media."""
        pass

    @abstractmethod
    def get_time(self) -> int:
        """Returns the current playback position in milliseconds."""
        pass

    @abstractmethod
    def set_time(self, time_ms: int):
        """Seeks to a specific time in the current file."""
        pass

    @abstractmethod
    def get_length(self) -> int:
        """Returns the total duration of the current file in milliseconds."""
        pass

    @abstractmethod
    def get_rate(self) -> float:
        """Returns the current playback speed."""
        pass

    @abstractmethod
    def set_rate(self, rate: float):
        """Sets the playback speed."""
        pass

    # --- Playlist Navigation ---

    @abstractmethod
    def playlist_next(self) -> bool:
        """Jumps to the next item in the playlist."""
        pass

    @abstractmethod
    def playlist_previous(self) -> bool:
        """Jumps to the previous item in the playlist."""
        pass

    @abstractmethod
    def playlist_jump(self, index: int, start_time_ms: int = 0) -> bool:
        """Jumps to a specific index in the playlist."""
        pass

    @abstractmethod
    def get_current_file_index(self) -> Optional[int]:
        """Returns the 0-based index of the currently playing file."""
        pass

    # --- A-B Loop Methods ---

    @abstractmethod
    def set_loop_a(self, time_ms: int):
        """Sets the start point (A) for the A-B loop."""
        pass

    @abstractmethod
    def set_loop_b(self, time_ms: int):
        """Sets the end point (B) for the A-B loop and activates it."""
        pass

    @abstractmethod
    def clear_loop(self):
        """Deactivates and clears the A-B loop."""
        pass

    @abstractmethod
    def set_loop_file(self, loop: bool):
        """Enables or disables repeating the current file."""
        pass

    # --- Volume/Mute ---

    @abstractmethod
    def get_volume(self) -> int:
        """Returns the current volume (0-100)."""
        pass

    @abstractmethod
    def set_volume(self, volume: int):
        """Sets the volume (0-100)."""
        pass

    @abstractmethod
    def get_mute(self) -> bool:
        """Checks if the player is muted."""
        pass

    @abstractmethod
    def set_mute(self, mute: bool):
        """Sets the mute state."""
        pass

    # --- Audio Filters ---

    @abstractmethod
    def set_audio_filters(self, filter_string: str):
        """Applies a filter string (e.g. Equalizer) to the engine."""
        pass

    # --- Events ---

    @abstractmethod
    def attach_event(self, event_name: str, callback: Callable[..., Any]):
        """
        Attaches a callback function to a specific engine event.

        Args:
            event_name: The name of the event (e.g., "on_end_reached").
            callback: The function to call when the event fires.
        """
        pass

    @abstractmethod
    def release(self):
        """Releases all resources held by the engine (e.g., on application exit)."""
        pass