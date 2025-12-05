# dialogs/settings/playback.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import wx
import logging
from typing import List, Tuple, Dict
from database import db_manager
from i18n import _

# Setting Keys
SETTING_PAUSE_ON_DIALOG = 'pause_on_dialog'
SETTING_RESUME_ON_JUMP = 'resume_on_jump'
SETTING_END_OF_BOOK = 'end_of_book_action'
SETTING_SEEK_FWD = 'seek_forward_ms'
SETTING_SEEK_BWD = 'seek_backward_ms'
SETTING_LONG_SEEK_FWD = 'long_seek_forward_ms'
SETTING_LONG_SEEK_BWD = 'long_seek_backward_ms'
SETTING_RESUME_REWIND = 'resume_rewind_ms'
SETTING_SMART_RESUME_THRESHOLD = 'smart_resume_threshold_sec'
SETTING_SMART_RESUME_REWIND = 'smart_resume_rewind_ms'

# Options
EOD_ACTIONS = {
    'stop': _("Stop playback"),
    'loop': _("Loop (play from start)"),
    'close': _("Close the player")
}
EOD_ACTIONS_REV = {v: k for k, v in EOD_ACTIONS.items()}

REWIND_OPTIONS = [
    (0, _("Disabled")),
    (5000, _("5 seconds")),
    (10000, _("10 seconds")),
    (15000, _("15 seconds")),
    (30000, _("30 seconds")),
    (60000, _("1 minute")),
    (120000, _("2 minutes")),
    (300000, _("5 minutes")),
]

SMART_THRESHOLD_OPTIONS = [
    (60, _("1 minute")),
    (120, _("2 minutes")),
    (300, _("5 minutes")),
    (600, _("10 minutes")),
    (1800, _("30 minutes")),
    (3600, _("1 hour")),
    (0, _("Disabled")),
]

SMART_REWIND_OPTIONS = [
    (5000, _("5 seconds")),
    (10000, _("10 seconds")),
    (15000, _("15 seconds")),
    (20000, _("20 seconds")),
    (30000, _("30 seconds")),
]


class TabPanel(wx.Panel):
    """
    The "Playback" settings tab.
    Manages seeking behavior, auto-rewind options, end-of-book actions,
    and smart resume logic.
    """

    def __init__(self, parent):
        super(TabPanel, self).__init__(parent)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Playback Behavior Section
        playback_box = wx.StaticBox(self, label=_("Playback Behavior"))
        playback_box_sizer = wx.StaticBoxSizer(playback_box, wx.VERTICAL)

        self.pause_checkbox = wx.CheckBox(
            self,
            label=_("Automatically pause playback when a dialog window opens (e.g., Bookmark, File List).")
        )
        playback_box_sizer.Add(self.pause_checkbox, 0, wx.ALL | wx.EXPAND, 8)

        self.resume_on_jump_checkbox = wx.CheckBox(
            self,
            label=_("Automatically resume playback after a major jump (e.g., Go To, Next File) if player was paused.")
        )
        playback_box_sizer.Add(self.resume_on_jump_checkbox, 0, wx.ALL | wx.EXPAND, 8)

        playback_box_sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, 8)

        # Resume Rewind (On Load)
        rewind_sizer = wx.BoxSizer(wx.HORIZONTAL)
        rewind_label = wx.StaticText(self, label=_("When opening a book, rewind by:"))

        self.rewind_choices_str = [opt[1] for opt in REWIND_OPTIONS]
        self.rewind_values_int = [opt[0] for opt in REWIND_OPTIONS]

        self.rewind_combo = wx.ComboBox(self, choices=self.rewind_choices_str, style=wx.CB_READONLY)

        rewind_sizer.Add(rewind_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        rewind_sizer.Add(self.rewind_combo, 0, wx.ALIGN_CENTER_VERTICAL)

        playback_box_sizer.Add(rewind_sizer, 0, wx.ALL | wx.EXPAND, 8)
        playback_box_sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, 8)

        # Smart Resume
        smart_sizer = wx.FlexGridSizer(2, 2, 5, 5)
        smart_sizer.AddGrowableCol(1, 1)

        smart_thresh_label = wx.StaticText(self, label=_("Smart Resume: If paused for more than:"))
        self.smart_thresh_choices_str = [opt[1] for opt in SMART_THRESHOLD_OPTIONS]
        self.smart_thresh_values_int = [opt[0] for opt in SMART_THRESHOLD_OPTIONS]
        self.smart_thresh_combo = wx.ComboBox(self, choices=self.smart_thresh_choices_str, style=wx.CB_READONLY)

        smart_sizer.Add(smart_thresh_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        smart_sizer.Add(self.smart_thresh_combo, 0, wx.ALIGN_CENTER_VERTICAL)

        smart_rewind_label = wx.StaticText(self, label=_("Then automatically rewind by:"))
        self.smart_rewind_choices_str = [opt[1] for opt in SMART_REWIND_OPTIONS]
        self.smart_rewind_values_int = [opt[0] for opt in SMART_REWIND_OPTIONS]
        self.smart_rewind_combo = wx.ComboBox(self, choices=self.smart_rewind_choices_str, style=wx.CB_READONLY)

        smart_sizer.Add(smart_rewind_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        smart_sizer.Add(self.smart_rewind_combo, 0, wx.ALIGN_CENTER_VERTICAL)

        playback_box_sizer.Add(smart_sizer, 0, wx.ALL | wx.EXPAND, 8)
        playback_box_sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, 8)

        # End of Book Action
        self.eod_choices = list(EOD_ACTIONS.values())
        self.eod_radio = wx.RadioBox(
            self,
            label=_("When the end of a book is reached:"),
            choices=self.eod_choices,
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS
        )
        playback_box_sizer.Add(self.eod_radio, 0, wx.EXPAND | wx.ALL, 8)

        # Seek Times Section
        seek_box = wx.StaticBox(self, label=_("Seek Times"))
        seek_sizer = wx.StaticBoxSizer(seek_box, wx.VERTICAL)

        grid_sizer = wx.FlexGridSizer(4, 2, 5, 5)
        grid_sizer.AddGrowableCol(1, 1)

        seek_fwd_label = wx.StaticText(self, label=_("Short Seek Forward (→) (seconds):"))
        self.seek_fwd_spin = wx.SpinCtrl(self, min=1, max=300, initial=30)
        grid_sizer.Add(seek_fwd_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        grid_sizer.Add(self.seek_fwd_spin, 1, wx.EXPAND | wx.ALL, 5)

        seek_bwd_label = wx.StaticText(self, label=_("Short Seek Backward (←) (seconds):"))
        self.seek_bwd_spin = wx.SpinCtrl(self, min=1, max=300, initial=10)
        grid_sizer.Add(seek_bwd_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        grid_sizer.Add(self.seek_bwd_spin, 1, wx.EXPAND | wx.ALL, 5)

        long_seek_fwd_label = wx.StaticText(self, label=_("Long Seek Forward (Ctrl+→) (minutes):"))
        self.long_seek_fwd_spin = wx.SpinCtrl(self, min=1, max=30, initial=5)
        grid_sizer.Add(long_seek_fwd_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        grid_sizer.Add(self.long_seek_fwd_spin, 1, wx.EXPAND | wx.ALL, 5)

        long_seek_bwd_label = wx.StaticText(self, label=_("Long Seek Backward (Ctrl+←) (minutes):"))
        self.long_seek_bwd_spin = wx.SpinCtrl(self, min=1, max=30, initial=5)
        grid_sizer.Add(long_seek_bwd_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        grid_sizer.Add(self.long_seek_bwd_spin, 1, wx.EXPAND | wx.ALL, 5)

        seek_sizer.Add(grid_sizer, 1, wx.EXPAND | wx.ALL, 8)

        main_sizer.Add(playback_box_sizer, 0, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(seek_sizer, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(main_sizer)

        self._load_settings()

    def _safe_get_int_setting(self, key: str, default_val: int) -> int:
        """Safely retrieves an integer setting from the database."""
        try:
            return int(db_manager.get_setting(key))
        except (TypeError, ValueError, AttributeError):
            logging.warning(f"Could not parse int setting '{key}', using default {default_val}")
            return default_val

    def _load_settings(self):
        """Loads current playback settings from the database into the UI."""
        pause_setting = db_manager.get_setting(SETTING_PAUSE_ON_DIALOG)
        is_paused_on_dialog = (pause_setting == 'True')
        self.pause_checkbox.SetValue(is_paused_on_dialog)

        resume_setting = db_manager.get_setting(SETTING_RESUME_ON_JUMP)
        is_resume_enabled = (resume_setting == 'True' or resume_setting is None)
        self.resume_on_jump_checkbox.SetValue(is_resume_enabled)

        rewind_val = self._safe_get_int_setting(SETTING_RESUME_REWIND, 0)
        try:
            idx = self.rewind_values_int.index(rewind_val)
        except ValueError:
            idx = 0
        self.rewind_combo.SetSelection(idx)

        smart_thresh_val = self._safe_get_int_setting(SETTING_SMART_RESUME_THRESHOLD, 300)
        try:
            s_t_idx = self.smart_thresh_values_int.index(smart_thresh_val)
        except ValueError:
            s_t_idx = 2
        self.smart_thresh_combo.SetSelection(s_t_idx)

        smart_rewind_val = self._safe_get_int_setting(SETTING_SMART_RESUME_REWIND, 10000)
        try:
            s_r_idx = self.smart_rewind_values_int.index(smart_rewind_val)
        except ValueError:
            s_r_idx = 1
        self.smart_rewind_combo.SetSelection(s_r_idx)

        current_eod_action = db_manager.get_setting(SETTING_END_OF_BOOK) or 'stop'
        display_eod_action = EOD_ACTIONS.get(current_eod_action, _("Stop playback"))
        self.eod_radio.SetStringSelection(display_eod_action)

        seek_fwd_ms = self._safe_get_int_setting(SETTING_SEEK_FWD, 30000)
        self.seek_fwd_spin.SetValue(seek_fwd_ms // 1000)

        seek_bwd_ms = self._safe_get_int_setting(SETTING_SEEK_BWD, 10000)
        self.seek_bwd_spin.SetValue(seek_bwd_ms // 1000)

        long_seek_fwd_ms = self._safe_get_int_setting(SETTING_LONG_SEEK_FWD, 300000)
        self.long_seek_fwd_spin.SetValue(long_seek_fwd_ms // 60000)

        long_seek_bwd_ms = self._safe_get_int_setting(SETTING_LONG_SEEK_BWD, 300000)
        self.long_seek_bwd_spin.SetValue(long_seek_bwd_ms // 60000)

    def save_settings(self):
        """Saves the modified playback settings to the database."""
        pause_value = 'True' if self.pause_checkbox.GetValue() else 'False'
        db_manager.set_setting(SETTING_PAUSE_ON_DIALOG, pause_value)

        resume_value = 'True' if self.resume_on_jump_checkbox.GetValue() else 'False'
        db_manager.set_setting(SETTING_RESUME_ON_JUMP, resume_value)

        selected_idx = self.rewind_combo.GetSelection()
        if selected_idx != wx.NOT_FOUND:
            val_to_save = self.rewind_values_int[selected_idx]
            db_manager.set_setting(SETTING_RESUME_REWIND, str(val_to_save))

        s_t_idx = self.smart_thresh_combo.GetSelection()
        if s_t_idx != wx.NOT_FOUND:
            db_manager.set_setting(SETTING_SMART_RESUME_THRESHOLD, str(self.smart_thresh_values_int[s_t_idx]))

        s_r_idx = self.smart_rewind_combo.GetSelection()
        if s_r_idx != wx.NOT_FOUND:
            db_manager.set_setting(SETTING_SMART_RESUME_REWIND, str(self.smart_rewind_values_int[s_r_idx]))

        selected_eod_display = self.eod_radio.GetStringSelection()
        selected_eod_code = EOD_ACTIONS_REV.get(selected_eod_display, 'stop')
        db_manager.set_setting(SETTING_END_OF_BOOK, selected_eod_code)

        db_manager.set_setting(SETTING_SEEK_FWD, str(self.seek_fwd_spin.GetValue() * 1000))
        db_manager.set_setting(SETTING_SEEK_BWD, str(self.seek_bwd_spin.GetValue() * 1000))
        db_manager.set_setting(SETTING_LONG_SEEK_FWD, str(self.long_seek_fwd_spin.GetValue() * 60000))
        db_manager.set_setting(SETTING_LONG_SEEK_BWD, str(self.long_seek_bwd_spin.GetValue() * 60000))