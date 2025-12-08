# dialogs/settings/sleeptimer.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
import logging
from database import db_manager
from i18n import _

# Setting Keys
SETTING_QUICK_TIMER_DURATION = 'quick_timer_duration_minutes'
SETTING_QUICK_TIMER_ACTION = 'quick_timer_action'
SETTING_QUICK_TIMER_OS_MODE = 'quick_timer_os_action_mode'

# Action Choices
ACTION_CHOICES = {
    'pause': _("Pause playback"),
    'close_player': _("Close player"),
    'close_app': _("Close AudioShelf"),
    'sleep': _("Sleep computer"),
    'hibernate': _("Hibernate computer"),
    'shutdown': _("Shutdown computer")
}
ACTION_CHOICES_REV = {v: k for k, v in ACTION_CHOICES.items()}

# OS Mode Choices
OS_MODE_CHOICES = {
    'silent': _("Silent (Execute immediately)"),
    'confirm': _("Confirm before executing"),
    'timed': _("Show timed confirmation (2 min)")
}
OS_MODE_CHOICES_REV = {v: k for k, v in OS_MODE_CHOICES.items()}


class TabPanel(wx.Panel):
    """
    The "Sleep Timer" settings tab.
    Configures default values for the Quick Sleep Timer (triggered by 'T').
    """

    def __init__(self, parent):
        super(TabPanel, self).__init__(parent)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        timer_box = wx.StaticBox(self, label=_("Quick Sleep Timer Defaults (T Key)"))
        timer_sizer = wx.StaticBoxSizer(timer_box, wx.VERTICAL)

        grid_sizer = wx.FlexGridSizer(3, 2, 5, 5)
        grid_sizer.AddGrowableCol(1, 1)

        duration_label = wx.StaticText(self, label=_("Default Duration (minutes):"))
        self.duration_spin = wx.SpinCtrl(self, min=1, max=480, initial=30)

        grid_sizer.Add(duration_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        grid_sizer.Add(self.duration_spin, 1, wx.EXPAND | wx.ALL, 5)

        action_label = wx.StaticText(self, label=_("Default Action:"))
        self.action_choices_list = list(ACTION_CHOICES.values())
        self.action_combo = wx.ComboBox(self, choices=self.action_choices_list, style=wx.CB_READONLY)

        grid_sizer.Add(action_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        grid_sizer.Add(self.action_combo, 1, wx.EXPAND | wx.ALL, 5)

        os_mode_label = wx.StaticText(self, label=_("Default OS Action Mode:"))
        self.os_mode_choices_list = list(OS_MODE_CHOICES.values())
        self.os_mode_combo = wx.ComboBox(self, choices=self.os_mode_choices_list, style=wx.CB_READONLY)

        grid_sizer.Add(os_mode_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        grid_sizer.Add(self.os_mode_combo, 1, wx.EXPAND | wx.ALL, 5)

        timer_sizer.Add(grid_sizer, 1, wx.EXPAND | wx.ALL, 8)

        main_sizer.Add(timer_sizer, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(main_sizer)

        self._load_settings()

        self.action_combo.Bind(wx.EVT_CHOICE, self._on_action_changed)
        self._toggle_os_mode_control()

    def _safe_get_int_setting(self, key: str, default_val: int) -> int:
        """Safely retrieves an integer setting from the database."""
        try:
            return int(db_manager.get_setting(key))
        except (TypeError, ValueError, AttributeError):
            logging.warning(f"Could not parse int setting '{key}', using default {default_val}")
            return default_val

    def _toggle_os_mode_control(self):
        """Enables the OS Mode dropdown only if an OS-level action is selected."""
        selected_action_display = self.action_combo.GetValue()
        selected_action_key = ACTION_CHOICES_REV.get(selected_action_display)

        is_os_action = selected_action_key in ['sleep', 'hibernate', 'shutdown']
        self.os_mode_combo.Enable(is_os_action)

    def _on_action_changed(self, event):
        """Handles changes to the action dropdown."""
        self._toggle_os_mode_control()
        event.Skip()

    def _load_settings(self):
        """Loads current sleep timer settings from the database."""
        duration_min = self._safe_get_int_setting(SETTING_QUICK_TIMER_DURATION, 30)
        self.duration_spin.SetValue(duration_min)

        action_key = db_manager.get_setting(SETTING_QUICK_TIMER_ACTION) or 'pause'
        action_display = ACTION_CHOICES.get(action_key, ACTION_CHOICES['pause'])
        self.action_combo.SetValue(action_display)

        os_mode_key = db_manager.get_setting(SETTING_QUICK_TIMER_OS_MODE) or 'silent'
        os_mode_display = OS_MODE_CHOICES.get(os_mode_key, OS_MODE_CHOICES['silent'])
        self.os_mode_combo.SetValue(os_mode_display)

        self._toggle_os_mode_control()

    def save_settings(self):
        """Saves the selected sleep timer defaults to the database."""
        db_manager.set_setting(SETTING_QUICK_TIMER_DURATION, str(self.duration_spin.GetValue()))

        selected_action_display = self.action_combo.GetValue()
        selected_action_key = ACTION_CHOICES_REV.get(selected_action_display, 'pause')
        db_manager.set_setting(SETTING_QUICK_TIMER_ACTION, selected_action_key)

        selected_os_mode_display = self.os_mode_combo.GetValue()
        selected_os_mode_key = OS_MODE_CHOICES_REV.get(selected_os_mode_display, 'silent')
        db_manager.set_setting(SETTING_QUICK_TIMER_OS_MODE, selected_os_mode_key)