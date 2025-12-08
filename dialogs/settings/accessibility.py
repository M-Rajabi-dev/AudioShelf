# dialogs/settings/accessibility.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
from database import db_manager
from i18n import _

SETTING_VERBOSITY = 'nvda_verbosity'
SETTING_GLOBAL_HOTKEY_FEEDBACK = 'global_hotkey_feedback'

VERBOSITY_LEVELS = {
    'full': _("Full"),
    'minimal': _("Minimal"),
    'silent': _("Silent")
}
VERBOSITY_LEVELS_REV = {v: k for k, v in VERBOSITY_LEVELS.items()}


class TabPanel(wx.Panel):
    """
    The "Accessibility" settings tab.
    Manages NVDA verbosity levels and global hotkey feedback options.
    """

    def __init__(self, parent):
        super(TabPanel, self).__init__(parent)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        nvda_box = wx.StaticBox(self, label=_("Screen Reader Feedback"))
        nvda_sizer = wx.StaticBoxSizer(nvda_box, wx.VERTICAL)

        self.verbosity_choices = list(VERBOSITY_LEVELS.values())
        self.verbosity_radio = wx.RadioBox(
            self,
            label=_("Feedback Level"),
            choices=self.verbosity_choices,
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS
        )

        nvda_sizer.Add(self.verbosity_radio, 0, wx.EXPAND | wx.ALL, 8)
        nvda_sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, 8)

        self.global_hotkey_checkbox = wx.CheckBox(
            self,
            label=_("Announce feedback for global media keys (e.g., Volume) even when the player is hidden.")
        )
        nvda_sizer.Add(self.global_hotkey_checkbox, 0, wx.ALL | wx.EXPAND, 8)

        main_sizer.Add(nvda_sizer, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(main_sizer)

        self._load_settings()

    def _load_settings(self):
        """Loads current accessibility settings from the database into the UI."""
        current_verbosity = db_manager.get_setting(SETTING_VERBOSITY) or 'full'
        display_verbosity = VERBOSITY_LEVELS.get(current_verbosity, _("Full"))
        self.verbosity_radio.SetStringSelection(display_verbosity)

        ghf_setting = db_manager.get_setting(SETTING_GLOBAL_HOTKEY_FEEDBACK)
        is_ghf_enabled = (ghf_setting == 'True' or ghf_setting is None)
        self.global_hotkey_checkbox.SetValue(is_ghf_enabled)

    def save_settings(self):
        """Saves the selected accessibility settings to the database."""
        selected_verbosity_display = self.verbosity_radio.GetStringSelection()
        selected_verbosity_code = VERBOSITY_LEVELS_REV.get(selected_verbosity_display, 'full')
        db_manager.set_setting(SETTING_VERBOSITY, selected_verbosity_code)

        ghf_value = 'True' if self.global_hotkey_checkbox.GetValue() else 'False'
        db_manager.set_setting(SETTING_GLOBAL_HOTKEY_FEEDBACK, ghf_value)