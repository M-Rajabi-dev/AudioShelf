# frames/player/equalizer_frame.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
import logging
from typing import TYPE_CHECKING, List, Dict, Any
from database import db_manager
from i18n import _
from nvda_controller import speak, LEVEL_MINIMAL, LEVEL_CRITICAL

if TYPE_CHECKING:
    from ..player_frame import PlayerFrame
    from playback.base_engine import BasePlaybackEngine

# Constants
EQ_FREQUENCIES = [60, 170, 310, 600, 1000, 3000, 6000, 12000, 14000, 16000]
EQ_MIN_DB = -12
EQ_MAX_DB = 12

ID_SAVE_PRESET = wx.NewIdRef()
ID_DELETE_PRESET = wx.NewIdRef()
ID_RESET_EQ = wx.NewIdRef()

FLAT_SETTINGS_STR = "0,0,0,0,0,0,0,0,0,0"
CUSTOM_PRESET_LABEL = _("(Custom)")


class EqualizerFrame(wx.Frame):
    """
    The non-modal Equalizer Tool Window.
    Provides a 10-band equalizer interface with preset management.
    """

    def __init__(self,
                 parent: 'PlayerFrame',
                 engine: 'BasePlaybackEngine',
                 initial_settings: str,
                 initial_enabled: bool):
        """
        Initializes the Equalizer Frame.
        """
        style = wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX) | wx.FRAME_FLOAT_ON_PARENT
        super(EqualizerFrame, self).__init__(parent, title=_("Equalizer"), style=style, size=(600, 450))

        self.parent_frame = parent
        self.engine = engine
        self.sliders: List[wx.Slider] = []
        self.slider_labels: List[wx.StaticText] = []
        self.presets: List[Dict[str, Any]] = []
        self.is_loading_preset: bool = False
        self.current_settings_str = initial_settings

        self._build_ui()
        self._bind_events()
        self._load_presets()

        self.enable_checkbox.SetValue(initial_enabled)
        self._settings_to_sliders(initial_settings)
        self._toggle_slider_enable(initial_enabled)
        self._update_preset_selection(initial_settings)

        # Bind ESC key to close
        accel_tbl = wx.AcceleratorTable([
            (wx.ACCEL_NORMAL, wx.WXK_ESCAPE, wx.ID_CLOSE),
            (wx.ACCEL_NORMAL, wx.WXK_DELETE, ID_DELETE_PRESET)
        ])
        self.SetAcceleratorTable(accel_tbl)
        self.Bind(wx.EVT_MENU, self.on_close, id=wx.ID_CLOSE)

        self.CentreOnParent()
        self.FocusFirstControl()

    def _build_ui(self):
        """Constructs the main UI layout."""
        self.panel = wx.Panel(self, style=wx.TAB_TRAVERSAL)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        preset_panel = self._build_preset_panel(self.panel)
        main_sizer.Add(preset_panel, 0, wx.EXPAND | wx.ALL, 10)

        slider_panel = self._build_slider_panel(self.panel)
        main_sizer.Add(slider_panel, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        control_panel = self._build_control_panel(self.panel)
        main_sizer.Add(control_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.panel.SetSizer(main_sizer)
        self.Fit()
        self.SetMinSize(self.GetSize())

    def _build_preset_panel(self, parent: wx.Panel) -> wx.BoxSizer:
        """Builds the preset selection and management controls."""
        box = wx.StaticBox(parent, label=_("Presets"))
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

        grid = wx.FlexGridSizer(2, 2, 5, 5)
        grid.AddGrowableCol(1, 1)

        preset_label = wx.StaticText(parent, label=_("&Preset:"))
        self.preset_choice = wx.Choice(parent, choices=[_("Loading...")])

        grid.Add(preset_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        grid.Add(self.preset_choice, 1, wx.EXPAND | wx.ALL, 5)

        self.save_button = wx.Button(parent, ID_SAVE_PRESET, _("&Save As New Preset..."))
        self.delete_button = wx.Button(parent, ID_DELETE_PRESET, _("&Delete Selected Preset"))

        grid.Add(self.save_button, 0, wx.ALL, 5)
        grid.Add(self.delete_button, 0, wx.ALL, 5)

        sizer.Add(grid, 1, wx.EXPAND)
        return sizer

    def _build_slider_panel(self, parent: wx.Panel) -> wx.BoxSizer:
        """
        Builds the 10 sliders for EQ bands.
        Uses a layout of nested BoxSizers to ensure screen reader accessibility.
        """
        box = wx.StaticBox(parent, label=_("Bands"))
        wrapper_sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        slider_container_sizer = wx.BoxSizer(wx.HORIZONTAL)

        freq_labels_str = []
        for freq in EQ_FREQUENCIES:
            label_str = f"{freq}Hz" if freq < 1000 else f"{freq // 1000}kHz"
            freq_labels_str.append(label_str)

        for i in range(len(EQ_FREQUENCIES)):
            band_sizer = wx.BoxSizer(wx.VERTICAL)
            
            label = wx.StaticText(parent, label=freq_labels_str[i], style=wx.ALIGN_CENTER)
            band_sizer.Add(label, 0, wx.EXPAND | wx.BOTTOM, 5)

            slider = wx.Slider(
                parent,
                id=wx.NewIdRef(),
                value=0,
                minValue=EQ_MIN_DB,
                maxValue=EQ_MAX_DB,
                style=wx.SL_VERTICAL
            )
            slider.SetLabel(freq_labels_str[i])  # Accessible name
            band_sizer.Add(slider, 1, wx.EXPAND | wx.ALL, 5)
            self.sliders.append(slider)

            value_label = wx.StaticText(parent, label=_("0 dB"), style=wx.ALIGN_CENTER)
            band_sizer.Add(value_label, 0, wx.EXPAND | wx.TOP, 5)
            self.slider_labels.append(value_label)

            slider_container_sizer.Add(band_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        wrapper_sizer.Add(slider_container_sizer, 1, wx.EXPAND | wx.ALL, 10)
        return wrapper_sizer

    def _build_control_panel(self, parent: wx.Panel) -> wx.BoxSizer:
        """Builds the bottom control panel (Enable, Reset, Close)."""
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.enable_checkbox = wx.CheckBox(parent, label=_("&Enable Equalizer (E)"))
        self.reset_button = wx.Button(parent, ID_RESET_EQ, _("&Reset"))
        self.close_button = wx.Button(parent, wx.ID_CLOSE, _("&Close (Esc)"))

        sizer.Add(self.enable_checkbox, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        sizer.Add(self.reset_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        sizer.Add(self.close_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        return sizer

    def _bind_events(self):
        """Binds GUI events to handlers."""
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.close_button.Bind(wx.EVT_BUTTON, self.on_close)
        self.enable_checkbox.Bind(wx.EVT_CHECKBOX, self.on_toggle_enabled)
        self.reset_button.Bind(wx.EVT_BUTTON, self.on_reset)
        self.preset_choice.Bind(wx.EVT_CHOICE, self.on_preset_select)
        self.save_button.Bind(wx.EVT_BUTTON, self.on_save_preset)
        self.delete_button.Bind(wx.EVT_BUTTON, self.on_delete_preset)
        self.Bind(wx.EVT_MENU, self.on_delete_preset, id=ID_DELETE_PRESET)

        for slider in self.sliders:
            slider.Bind(wx.EVT_SCROLL_CHANGED, self.on_slider_change)

    def FocusFirstControl(self):
        """Sets focus to the preset choice."""
        self.preset_choice.SetFocus()

    def on_slider_change(self, event: wx.ScrollEvent):
        """Handles slider movement, updates labels, and applies filters."""
        if self.is_loading_preset:
            return

        self._update_filters_and_notify_parent()
        try:
            slider = event.GetEventObject()
            index = self.sliders.index(slider)
            value = slider.GetValue()
            label_text = f"{value:+} dB" if value != 0 else "0 dB"
            self.slider_labels[index].SetLabel(label_text)
        except (ValueError, IndexError):
            pass

    def on_toggle_enabled(self, event: wx.CommandEvent):
        """Toggles the EQ enabled state."""
        is_enabled = self.enable_checkbox.IsChecked()
        self._toggle_slider_enable(is_enabled)
        self.parent_frame.on_eq_enabled_changed(is_enabled)

    def on_reset(self, event: wx.CommandEvent):
        """Resets EQ to flat settings."""
        if self.is_loading_preset:
            return
        speak(_("Reset"), LEVEL_MINIMAL)
        self._settings_to_sliders(FLAT_SETTINGS_STR)
        self._update_filters_and_notify_parent()
        self._update_preset_selection(FLAT_SETTINGS_STR)

    def on_close(self, event: wx.CommandEvent):
        """Closes the EQ frame and updates parent reference."""
        if self.parent_frame and hasattr(self.parent_frame, 'equalizer_frame_instance'):
            self.parent_frame.equalizer_frame_instance = None
        self.Destroy()

    def _load_presets(self):
        """Loads presets from the database into the Choice control."""
        self.is_loading_preset = True
        try:
            self.presets = db_manager.get_eq_presets()
            self.preset_choice.Clear()
            preset_names = [p['name'] for p in self.presets]
            self.preset_choice.AppendItems(preset_names)
        except Exception as e:
            logging.error(f"Failed to load EQ presets: {e}", exc_info=True)
        finally:
            self.is_loading_preset = False

    def on_preset_select(self, event: wx.CommandEvent):
        """Applies settings from the selected preset."""
        self.is_loading_preset = True
        try:
            index = self.preset_choice.GetSelection()
            if index < 0 or index >= len(self.presets):
                self.is_loading_preset = False
                return

            preset = self.presets[index]
            settings = preset['settings']
            self._settings_to_sliders(settings)
            self._update_filters_and_notify_parent()
            speak(f"{preset['name']}", LEVEL_MINIMAL)
        except Exception as e:
            logging.error(f"Error loading preset: {e}")
        finally:
            self.is_loading_preset = False

    def on_save_preset(self, event: wx.CommandEvent):
        """Saves current slider values as a new preset."""
        current_settings = self._sliders_to_settings()
        dlg = wx.TextEntryDialog(self, _("Enter a name for this preset:"), _("Save Preset"))
        
        if dlg.ShowModal() == wx.ID_OK:
            name = dlg.GetValue().strip()
            if name:
                try:
                    new_id = db_manager.save_eq_preset(name, current_settings)
                    if new_id is None:
                        speak(_("Error: A preset with this name already exists."), LEVEL_CRITICAL)
                    else:
                        speak(_("Preset saved."), LEVEL_CRITICAL)
                        self._load_presets()
                        self._update_preset_selection(current_settings)
                except Exception as e:
                    logging.error(f"Error saving preset: {e}")
                    speak(_("Error saving preset."), LEVEL_CRITICAL)
        dlg.Destroy()

    def on_delete_preset(self, event: wx.CommandEvent):
        """Deletes the currently selected preset."""
        index = self.preset_choice.GetSelection()
        if index < 0 or index >= len(self.presets):
            speak(_("No preset selected to delete."), LEVEL_MINIMAL)
            return

        preset = self.presets[index]
        preset_id = preset['id']
        preset_name = preset['name']

        if preset_name in db_manager.default_eq_presets:
            speak(_("Cannot delete default presets."), LEVEL_CRITICAL)
            return

        msg = _("Are you sure you want to delete preset '{0}'?").format(preset_name)
        if wx.MessageBox(msg, _("Confirm Delete"), wx.YES_NO | wx.CANCEL | wx.ICON_WARNING | wx.YES_DEFAULT) == wx.YES:
            try:
                db_manager.delete_eq_preset(preset_id)
                speak(_("Preset deleted."), LEVEL_CRITICAL)
                self._load_presets()
                self._update_preset_selection(FLAT_SETTINGS_STR)
            except Exception as e:
                logging.error(f"Error deleting preset: {e}")
                speak(_("Error deleting preset."), LEVEL_CRITICAL)

    def _toggle_slider_enable(self, is_enabled: bool):
        """Enables or disables all slider and label controls."""
        for slider in self.sliders:
            slider.Enable(is_enabled)
        for label in self.slider_labels:
            label.Enable(is_enabled)

    def _settings_to_sliders(self, settings_str: str):
        """Parses a settings string and updates slider positions."""
        self.current_settings_str = settings_str
        try:
            values = [int(v) for v in settings_str.split(',')]
            if len(values) != len(self.sliders):
                raise ValueError("Settings string does not match slider count")

            for i, slider in enumerate(self.sliders):
                val = max(EQ_MIN_DB, min(EQ_MAX_DB, values[i]))
                slider.SetValue(val)
                label_text = f"{val:+} dB" if val != 0 else "0 dB"
                self.slider_labels[i].SetLabel(label_text)
        except Exception as e:
            logging.error(f"Error applying settings to sliders: {e}")

    def _sliders_to_settings(self) -> str:
        """Generates a settings string from current slider positions."""
        values = [str(s.GetValue()) for s in self.sliders]
        self.current_settings_str = ",".join(values)
        return self.current_settings_str

    def _update_filters_and_notify_parent(self):
        """Updates the engine via the parent frame with new settings."""
        if not self.engine:
            return

        settings_str = self._sliders_to_settings()
        self._update_preset_selection(settings_str)
        
        self.parent_frame.on_equalizer_changed(
            new_settings=settings_str,
            new_enabled=self.enable_checkbox.IsChecked()
        )

    def _update_preset_selection(self, settings_str: str):
        """Updates the preset dropdown to match current slider values."""
        if self.is_loading_preset:
            return

        found_match = False
        for i, preset in enumerate(self.presets):
            if preset['settings'] == settings_str:
                self.preset_choice.SetSelection(i)
                found_match = True
                break
        
        if not found_match:
            self.preset_choice.SetStringSelection(CUSTOM_PRESET_LABEL)
