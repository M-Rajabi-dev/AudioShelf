# frames/player_frame.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
import os
import logging
from typing import List, Tuple, Optional
import wx.lib.newevent

from nvda_controller import set_app_focus_status
from database import db_manager
from i18n import _
from utils import SleepTimer
from playback.engine_factory import create_engine

from .player import (
    controls,
    dialog_manager,
    info,
    event_handlers,
    hotkey_manager,
    playback_logic,
    volume_logic,
    seek_logic,
    book_loader,
    equalizer_frame
)
from .player.hotkey_manager import (
    VK_MEDIA_PLAY_PAUSE, VK_MEDIA_NEXT_TRACK, VK_MEDIA_PREV_TRACK,
    VK_VOLUME_UP, VK_VOLUME_DOWN, VK_VOLUME_MUTE,
    VK_BROWSER_BACK, VK_BROWSER_FORWARD
)

# Custom Event
DurationUpdateEvent, EVT_DURATION_UPDATE = wx.lib.newevent.NewEvent()


class PlayerFrame(wx.Frame):
    """
    The main player window handling media playback, UI updates, and user input.
    Acts as the central coordinator for various player sub-modules.
    """

    def __init__(self,
                 parent: wx.Frame,
                 book_id: int,
                 library_playlist: List[Tuple[int, str]],
                 current_playlist_index: int):
        """
        Initializes the PlayerFrame.
        """
        style = wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX)
        super(PlayerFrame, self).__init__(parent, title="", style=style, size=(400, 150))

        self.parent_frame = parent
        self.book_id = book_id
        self.library_playlist = library_playlist
        self.current_playlist_index = current_playlist_index

        try:
            _id, title = self.library_playlist[self.current_playlist_index]
            self.book_title = title
        except (IndexError, ValueError):
            logging.error(f"PlayerFrame: Invalid playlist index {self.current_playlist_index}.")
            self.book_title = _("Unknown Book")

        # Player State
        self.book_files_data: List[Tuple[int, str, int, int]] = []
        self.book_file_durations: List[int] = []
        self.total_book_duration_ms: int = 0
        
        self.current_file_index: int = 0
        self.current_file_id: Optional[int] = None
        self.current_file_path: Optional[str] = None
        self.current_file_duration_ms: int = 0
        
        self.is_playing: bool = False
        self.start_pos_ms: int = 0
        self.current_target_rate: float = 1.0
        self.previous_target_rate: float = 1.0
        self.is_exiting: bool = False
        
        self.engine_to_frame_index_map: List[int] = []
        self.loop_point_a_ms: Optional[int] = None
        self.is_file_looping: bool = False
        self.save_state_counter: int = 0
        self.last_pause_time: float = 0.0

        # Audio State
        self.current_eq_settings: str = "0,0,0,0,0,0,0,0,0,0"
        self.is_eq_enabled: bool = False
        self.current_nr_mode: int = 0

        # Managers
        self.equalizer_frame_instance: Optional[wx.Frame] = None
        self.sleep_timer_manager: Optional[SleepTimer] = None
        self.hotkey_manager: Optional[hotkey_manager.HotkeyManager] = None
        self.book_loader: Optional[book_loader.BookLoader] = None
        self.DurationUpdateEvent = DurationUpdateEvent

        self._init_ui()
        self._init_engine()
        self._init_managers()
        self._bind_events()

        # Load Data
        self.book_loader.load_book_data()

    def _init_ui(self):
        """Sets up the visual elements of the player."""
        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour(wx.Colour(0, 0, 0))

        self.title_text = wx.StaticText(self.panel, label=self.book_title, style=wx.ALIGN_CENTER_HORIZONTAL)
        self.time_text = wx.StaticText(self.panel, label="00:00:00 / 00:00:00", style=wx.ALIGN_CENTER_HORIZONTAL)

        font = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        self.title_text.SetFont(font)
        self.time_text.SetFont(font)

        self.title_text.SetForegroundColour(wx.Colour(255, 255, 255))
        self.time_text.SetForegroundColour(wx.Colour(255, 255, 255))

        # Invisible label for NVDA focus management
        self.nvda_focus_label = wx.StaticText(self.panel, label="", size=(0, 0))

        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_sizer.Add(self.title_text, 1, wx.EXPAND | wx.ALL, 10)
        panel_sizer.Add(self.time_text, 1, wx.EXPAND | wx.ALL, 10)
        panel_sizer.Add(self.nvda_focus_label, 0, wx.ALL, 0)

        self.panel.SetSizer(panel_sizer)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.panel, 1, wx.EXPAND)
        self.SetSizer(main_sizer)
        self.CentreOnParent()

    def _init_engine(self):
        """Initializes the playback engine (MPV)."""
        self.engine = None
        try:
            self.engine = create_engine(hwnd=self.panel.GetHandle())
            try:
                vol_str = db_manager.get_setting('master_volume')
                vol = int(vol_str) if vol_str else 100
                self.engine.set_volume(vol)
            except Exception as e:
                logging.warning(f"Failed to apply master volume: {e}")
        except (RuntimeError, ValueError, ImportError, NotImplementedError) as e:
            logging.critical(f"Playback engine initialization failed: {e}", exc_info=True)
            wx.MessageBox(str(e), _("Playback Engine Error"), wx.OK | wx.ICON_ERROR, parent=self)
            wx.CallAfter(lambda: event_handlers.on_escape(self, None))

    def _init_managers(self):
        """Initializes helper managers."""
        self.dialog_manager = dialog_manager.DialogManager(self)
        self.info_manager = info.InfoManager(self)
        try:
            self.sleep_timer_manager = SleepTimer(self)
        except Exception as e:
            logging.error(f"Failed to initialize SleepTimer: {e}", exc_info=True)
            self.sleep_timer_manager = None
        
        self.book_loader = book_loader.BookLoader(self)

    def _bind_events(self):
        """Binds all events (UI, Engine, Hotkeys)."""
        self.nvda_focus_label.Bind(wx.EVT_CHAR_HOOK, lambda event: controls.on_key_down(self, event))

        if self.engine:
            self.engine.attach_event("on_end_reached",
                                     lambda event: wx.CallAfter(event_handlers.on_engine_end_reached, self, event))
            self.engine.attach_event("on_file_changed",
                                     lambda event, index: wx.CallAfter(event_handlers.on_engine_file_changed, self,
                                                                       event, index))

        self.Bind(wx.EVT_CLOSE, lambda event: event_handlers.on_escape(self, event))

        # Setup Global Hotkeys
        self.hotkey_manager = hotkey_manager.HotkeyManager(self)
        key_function_map = {
            VK_MEDIA_PLAY_PAUSE: lambda: playback_logic.toggle_play_pause(self),
            VK_MEDIA_NEXT_TRACK: lambda: playback_logic.play_next_file(self, manual=True),
            VK_MEDIA_PREV_TRACK: lambda: playback_logic.play_prev_file(self),
            VK_VOLUME_UP: lambda: volume_logic.change_volume(self, 5),
            VK_VOLUME_DOWN: lambda: volume_logic.change_volume(self, -5),
            VK_VOLUME_MUTE: lambda: volume_logic.toggle_mute(self),
            VK_BROWSER_BACK: lambda: seek_logic.seek_backward_setting(self),
            VK_BROWSER_FORWARD: lambda: seek_logic.seek_forward_setting(self),
        }
        self.hotkey_manager.setup_hotkeys(key_function_map)
        self.Bind(wx.EVT_HOTKEY, self.hotkey_manager.on_hotkey_pressed)

        self.ui_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda event: event_handlers.on_ui_timer(self, event), self.ui_timer)
        self.Bind(EVT_DURATION_UPDATE, lambda event: event_handlers.on_duration_update(self, event))
        self.Bind(wx.EVT_ACTIVATE, self.on_activate)

        try:
            wx.GetApp().player_frame_instance = self
        except Exception as e:
            logging.error(f"Could not set player_frame_instance on app: {e}")

    def on_activate(self, event: wx.ActivateEvent):
        """Handles window activation to manage focus state for NVDA."""
        is_active = event.GetActive()
        if is_active:
            logging.debug("PlayerFrame activated. Setting NVDA focus status.")
            if self.nvda_focus_label and not self.nvda_focus_label.IsBeingDeleted():
                self.nvda_focus_label.SetFocus()
            wx.CallAfter(set_app_focus_status, True)
        else:
            logging.debug("PlayerFrame deactivated.")
            wx.CallAfter(set_app_focus_status, False)
        event.Skip()

    def start_playback(self):
        """Delegates start playback to the book loader."""
        self.book_loader.start_playback()

    def _update_audio_filters(self):
        """
        Constructs and applies the audio filter string.
        """
        if not self.engine:
            return

        internal_lavfi_filters: List[str] = []

        if self.is_eq_enabled and self.current_eq_settings:
            try:
                bands = self.current_eq_settings.split(',')
                frequencies = [60, 170, 310, 600, 1000, 3000, 6000, 12000, 14000, 16000]
                eq_bands_to_add: List[str] = []
                
                for i, gain in enumerate(bands):
                    if float(gain) != 0:
                        freq = frequencies[i]
                        eq_bands_to_add.append(f"equalizer=f={freq}:width_type=o:w=1:g={gain}")
                
                if eq_bands_to_add:
                    internal_lavfi_filters.extend(eq_bands_to_add)
            except Exception as e:
                logging.error(f"Error parsing EQ settings string: {e}")

        final_filter_string = ""
        if internal_lavfi_filters:
            final_filter_string = "lavfi=[" + ",".join(internal_lavfi_filters) + "]"

        try:
            self.engine.set_audio_filters(final_filter_string)
            logging.info(f"Audio filters updated: {final_filter_string}")
        except Exception as e:
            logging.error(f"CRITICAL: Failed to apply final filter string: {e}")

    def on_show_equalizer(self):
        """Opens or focuses the Equalizer window."""
        if self.equalizer_frame_instance:
            self.equalizer_frame_instance.Raise()
            self.equalizer_frame_instance.SetFocus()
            return

        try:
            self.equalizer_frame_instance = equalizer_frame.EqualizerFrame(
                parent=self,
                engine=self.engine,
                initial_settings=self.current_eq_settings,
                initial_enabled=self.is_eq_enabled
            )
            self.equalizer_frame_instance.Show()
        except Exception as e:
            logging.error(f"Failed to create EqualizerFrame: {e}", exc_info=True)

    def on_equalizer_changed(self, new_settings: str, new_enabled: bool):
        """Callback from EqualizerFrame when settings change."""
        self.current_eq_settings = new_settings
        self.is_eq_enabled = new_enabled
        self._update_audio_filters()

    def on_eq_enabled_changed(self, new_enabled: bool):
        """Toggles the Equalizer on/off."""
        self.is_eq_enabled = new_enabled
        self._update_audio_filters()
