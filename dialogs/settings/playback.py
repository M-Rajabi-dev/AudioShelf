# dialogs/settings/playback.py
# Copyright (c) 2025-2026 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
import logging
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
SETTING_SMART_RESUME_THRESHOLD = 'smart_resume_threshold_sec'
SETTING_SMART_RESUME_REWIND = 'smart_resume_rewind_ms'

# Options
EOD_ACTIONS = {
    'stop': _("Stop playback"),
    'loop': _("Loop (play from start)"),
    'close': _("Close the player")
}
EOD_ACTIONS_REV = {v: k for k, v in EOD_ACTIONS.items()}

MS_PER_SEC = 1000
MS_PER_MIN = 60000

SMART_THRESHOLD_OPTIONS = [
    (0, _("Always (Disabled Threshold)")),
    (60, _("{0} minute").format(1)),
    (120, _("{0} minutes").format(2)),
    (300, _("{0} minutes").format(5)),
    (600, _("{0} minutes").format(10)),
    (900, _("{0} minutes").format(15)),
    (1800, _("{0} minutes").format(30)),
    (3600, _("{0} hour").format(1)),
]

SMART_REWIND_OPTIONS = [(0, _("Disabled"))]
SMART_REWIND_OPTIONS += [(s * MS_PER_SEC, _("{0} seconds").format(s)) for s in [5, 10, 15, 20, 30]]
SMART_REWIND_OPTIONS += [(1 * MS_PER_MIN, _("{0} minute").format(1))]
SMART_REWIND_OPTIONS += [(m * MS_PER_MIN, _("{0} minutes").format(m)) for m in range(2, 11)]
SMART_REWIND_OPTIONS += [(15 * MS_PER_MIN, _("{0} minutes").format(15))]

class TabPanel(wx.Panel):
    def __init__(self, parent):
        super(TabPanel, self).__init__(parent)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Auto-Rewind Section
        rewind_box = wx.StaticBox(self, label=_("Auto-Rewind Settings"))
        rewind_box_sizer = wx.StaticBoxSizer(rewind_box, wx.VERTICAL)

        help_text = wx.StaticText(self, label=_("To help you remember the story, AudioShelf can jump back slightly after a break."))
        rewind_box_sizer.Add(help_text, 0, wx.ALL, 8)

        # Threshold Row
        thresh_sizer = wx.BoxSizer(wx.HORIZONTAL)
        thresh_label = wx.StaticText(self, label=_("Only if the break was longer than:"))
        self.smart_thresh_choices_str = [opt[1] for opt in SMART_THRESHOLD_OPTIONS]
        self.smart_thresh_values_int = [opt[0] for opt in SMART_THRESHOLD_OPTIONS]
        self.smart_thresh_combo = wx.ComboBox(self, choices=self.smart_thresh_choices_str, style=wx.CB_READONLY)
        thresh_sizer.Add(thresh_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        thresh_sizer.Add(self.smart_thresh_combo, 0, wx.ALIGN_CENTER_VERTICAL)
        rewind_box_sizer.Add(thresh_sizer, 0, wx.ALL, 8)

        # Amount Row
        amount_sizer = wx.BoxSizer(wx.HORIZONTAL)
        amount_label = wx.StaticText(self, label=_("Amount to jump back (Seconds):"))
        self.smart_rewind_choices_str = [opt[1] for opt in SMART_REWIND_OPTIONS]
        self.smart_rewind_values_int = [opt[0] for opt in SMART_REWIND_OPTIONS]
        self.smart_rewind_combo = wx.ComboBox(self, choices=self.smart_rewind_choices_str, style=wx.CB_READONLY)
        amount_sizer.Add(amount_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        amount_sizer.Add(self.smart_rewind_combo, 0, wx.ALIGN_CENTER_VERTICAL)
        rewind_box_sizer.Add(amount_sizer, 0, wx.ALL, 8)

        # Playback Behavior
        playback_box = wx.StaticBox(self, label=_("Playback Behavior"))
        playback_box_sizer = wx.StaticBoxSizer(playback_box, wx.VERTICAL)

        self.pause_checkbox = wx.CheckBox(self, label=_("Automatically pause playback when a dialog window opens."))
        playback_box_sizer.Add(self.pause_checkbox, 0, wx.ALL | wx.EXPAND, 8)

        self.resume_on_jump_checkbox = wx.CheckBox(self, label=_("Automatically resume playback after a major jump."))
        playback_box_sizer.Add(self.resume_on_jump_checkbox, 0, wx.ALL | wx.EXPAND, 8)

        self.eod_choices = list(EOD_ACTIONS.values())
        self.eod_radio = wx.RadioBox(self, label=_("When the end of a book is reached:"), choices=self.eod_choices, majorDimension=1, style=wx.RA_SPECIFY_COLS)
        playback_box_sizer.Add(self.eod_radio, 0, wx.EXPAND | wx.ALL, 8)

        # Seek Times
        seek_box = wx.StaticBox(self, label=_("Seek Times"))
        seek_sizer = wx.StaticBoxSizer(seek_box, wx.VERTICAL)
        grid_sizer = wx.FlexGridSizer(4, 2, 5, 5)
        grid_sizer.AddGrowableCol(1, 1)

        grid_sizer.Add(wx.StaticText(self, label=_("Short Seek Forward (Right Arrow) (seconds):")), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.seek_fwd_spin = wx.SpinCtrl(self, min=1, max=300, initial=30)
        grid_sizer.Add(self.seek_fwd_spin, 1, wx.EXPAND | wx.ALL, 5)

        grid_sizer.Add(wx.StaticText(self, label=_("Short Seek Backward (Left Arrow) (seconds):")), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.seek_bwd_spin = wx.SpinCtrl(self, min=1, max=300, initial=10)
        grid_sizer.Add(self.seek_bwd_spin, 1, wx.EXPAND | wx.ALL, 5)

        grid_sizer.Add(wx.StaticText(self, label=_("Long Seek Forward (Ctrl+Right) (minutes):")), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.long_seek_fwd_spin = wx.SpinCtrl(self, min=1, max=30, initial=5)
        grid_sizer.Add(self.long_seek_fwd_spin, 1, wx.EXPAND | wx.ALL, 5)

        grid_sizer.Add(wx.StaticText(self, label=_("Long Seek Backward (Ctrl+Left) (minutes):")), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.long_seek_bwd_spin = wx.SpinCtrl(self, min=1, max=30, initial=5)
        grid_sizer.Add(self.long_seek_bwd_spin, 1, wx.EXPAND | wx.ALL, 5)

        seek_sizer.Add(grid_sizer, 1, wx.EXPAND | wx.ALL, 8)

        main_sizer.Add(rewind_box_sizer, 0, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(playback_box_sizer, 0, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(seek_sizer, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(main_sizer)
        self._load_settings()

    def _safe_get_int_setting(self, key: str, default_val: int) -> int:
        try:
            return int(db_manager.get_setting(key))
        except (TypeError, ValueError, AttributeError):
            return default_val

    def _load_settings(self):
        self.pause_checkbox.SetValue(db_manager.get_setting(SETTING_PAUSE_ON_DIALOG) == 'True')
        self.resume_on_jump_checkbox.SetValue(db_manager.get_setting(SETTING_RESUME_ON_JUMP) != 'False')

        smart_thresh_val = self._safe_get_int_setting(SETTING_SMART_RESUME_THRESHOLD, 300)
        try:
            s_t_idx = self.smart_thresh_values_int.index(smart_thresh_val)
        except ValueError:
            s_t_idx = 3
        self.smart_thresh_combo.SetSelection(s_t_idx)

        smart_rewind_val = self._safe_get_int_setting(SETTING_SMART_RESUME_REWIND, 10000)
        try:
            s_r_idx = self.smart_rewind_values_int.index(smart_rewind_val)
        except ValueError:
            s_r_idx = 2
        self.smart_rewind_combo.SetSelection(s_r_idx)

        current_eod_action = db_manager.get_setting(SETTING_END_OF_BOOK) or 'stop'
        display_eod_action = EOD_ACTIONS.get(current_eod_action, EOD_ACTIONS['stop'])
        self.eod_radio.SetStringSelection(display_eod_action)

        self.seek_fwd_spin.SetValue(self._safe_get_int_setting(SETTING_SEEK_FWD, 30000) // 1000)
        self.seek_bwd_spin.SetValue(self._safe_get_int_setting(SETTING_SEEK_BWD, 10000) // 1000)
        self.long_seek_fwd_spin.SetValue(self._safe_get_int_setting(SETTING_LONG_SEEK_FWD, 300000) // 60000)
        self.long_seek_bwd_spin.SetValue(self._safe_get_int_setting(SETTING_LONG_SEEK_BWD, 300000) // 60000)

    def save_settings(self):
        db_manager.set_setting(SETTING_PAUSE_ON_DIALOG, str(self.pause_checkbox.GetValue()))
        db_manager.set_setting(SETTING_RESUME_ON_JUMP, str(self.resume_on_jump_checkbox.GetValue()))
        
        s_t_idx = self.smart_thresh_combo.GetSelection()
        if s_t_idx != wx.NOT_FOUND:
            db_manager.set_setting(SETTING_SMART_RESUME_THRESHOLD, str(self.smart_thresh_values_int[s_t_idx]))

        s_r_idx = self.smart_rewind_combo.GetSelection()
        if s_r_idx != wx.NOT_FOUND:
            db_manager.set_setting(SETTING_SMART_RESUME_REWIND, str(self.smart_rewind_values_int[s_r_idx]))

        selected_eod_display = self.eod_radio.GetStringSelection()
        db_manager.set_setting(SETTING_END_OF_BOOK, EOD_ACTIONS_REV.get(selected_eod_display, 'stop'))

        db_manager.set_setting(SETTING_SEEK_FWD, str(self.seek_fwd_spin.GetValue() * 1000))
        db_manager.set_setting(SETTING_SEEK_BWD, str(self.seek_bwd_spin.GetValue() * 1000))
        db_manager.set_setting(SETTING_LONG_SEEK_FWD, str(self.long_seek_fwd_spin.GetValue() * 60000))
        db_manager.set_setting(SETTING_LONG_SEEK_BWD, str(self.long_seek_bwd_spin.GetValue() * 60000))