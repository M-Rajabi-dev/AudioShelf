# dialogs/sleep_timer_dialog.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import wx
from i18n import _
from typing import List, Tuple, Dict, Any


class SleepTimerDialog(wx.Dialog):
    """
    A dialog that allows the user to set a sleep timer with a
    specific duration, end-action, and OS action behavior.
    """

    OS_ACTION_KEYS = ['sleep', 'hibernate', 'shutdown']

    def __init__(self, parent, default_duration_minutes: int, default_action_key: str, default_os_action_mode: str):
        """
        Args:
            parent: The parent window (PlayerFrame).
            default_duration_minutes: The pre-selected duration.
            default_action_key: The pre-selected action.
            default_os_action_mode: The pre-selected OS mode.
        """
        super(SleepTimerDialog, self).__init__(parent, title=_("Sleep Timer"))

        self.panel = wx.Panel(self)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Duration
        time_label = wx.StaticText(self.panel, label=_("&Duration:"))

        self.time_choices_data = self._generate_time_choices()
        time_labels = [label for label, value in self.time_choices_data]
        self.time_choice = wx.Choice(self.panel, choices=time_labels)

        time_values = [value for label, value in self.time_choices_data]
        try:
            default_time_index = time_values.index(default_duration_minutes)
        except ValueError:
            default_time_index = 0
        self.time_choice.SetSelection(default_time_index)

        self.main_sizer.Add(time_label, 0, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 10)
        self.main_sizer.Add(self.time_choice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Action
        action_label = wx.StaticText(self.panel, label=_("&Action:"))

        self.action_choices_data = self._generate_action_choices()
        self.action_keys_list = list(self.action_choices_data.keys())
        action_labels = list(self.action_choices_data.values())
        self.action_choice = wx.Choice(self.panel, choices=action_labels)

        try:
            default_action_index = self.action_keys_list.index(default_action_key)
        except ValueError:
            default_action_index = 0
        self.action_choice.SetSelection(default_action_index)

        self.main_sizer.Add(action_label, 0, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 10)
        self.main_sizer.Add(self.action_choice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # OS Action Mode
        self.os_action_label = wx.StaticText(self.panel, label=_("OS Action &Confirmation:"))

        self.os_mode_choices_data = {
            'silent': _("Silent (Execute immediately)"),
            'confirm': _("Confirm before executing"),
            'timed': _("Show timed confirmation (2 min)")
        }
        self.os_mode_keys_list = list(self.os_mode_choices_data.keys())
        os_mode_labels = list(self.os_mode_choices_data.values())

        self.os_action_box = wx.RadioBox(
            self.panel,
            choices=os_mode_labels,
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS
        )

        try:
            default_os_mode_index = self.os_mode_keys_list.index(default_os_action_mode)
        except ValueError:
            default_os_mode_index = 0
        self.os_action_box.SetSelection(default_os_mode_index)

        self.main_sizer.Add(self.os_action_label, 0, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 10)
        self.main_sizer.Add(self.os_action_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Save Default
        self.save_default_checkbox = wx.CheckBox(self.panel, label=_("&Save as default for Quick Timer"))
        self.main_sizer.Add(self.save_default_checkbox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Buttons
        button_sizer = wx.StdDialogButtonSizer()
        self.ok_button = wx.Button(self.panel, wx.ID_OK, _("&Start Timer"))
        self.cancel_button = wx.Button(self.panel, wx.ID_CANCEL, _("&Cancel"))

        button_sizer.AddButton(self.ok_button)
        button_sizer.AddButton(self.cancel_button)
        button_sizer.Realize()

        self.main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.panel.SetSizer(self.main_sizer)
        self.Fit()
        self.CentreOnParent()

        self.time_choice.SetFocus()
        self.SetDefaultItem(self.ok_button)

        self.ok_button.Bind(wx.EVT_BUTTON, self.on_ok)
        self.cancel_button.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.action_choice.Bind(wx.EVT_CHOICE, self._on_action_changed)

        self._toggle_os_action_box(self.get_data()['action_key'])

    def _generate_time_choices(self) -> List[Tuple[str, int]]:
        """Generates the list of duration options."""
        times = []
        for m in range(5, 61, 5):
            if m == 60:
                times.append((_("1 hour"), 60))
            else:
                times.append((_("{0} minutes").format(m), m))
        for m in range(70, 121, 10):
            if m == 120:
                times.append((_("2 hours"), 120))
            else:
                times.append((_("1 hour {0} minutes").format(m - 60), m))
        for m in range(150, 301, 30):
            h, mins = divmod(m, 60)
            if mins == 0:
                times.append((_("{0} hours").format(h), m))
            else:
                times.append((_("{0} hours {1} minutes").format(h, mins), m))
        return times

    def _generate_action_choices(self) -> Dict[str, str]:
        """Generates the dictionary of action keys and labels."""
        return {
            'pause': _("Pause playback"),
            'close_player': _("Close player"),
            'close_app': _("Close AudioShelf"),
            'sleep': _("Sleep computer"),
            'hibernate': _("Hibernate computer"),
            'shutdown': _("Shutdown computer")
        }

    def _on_action_changed(self, event: wx.Event):
        """Updates UI visibility based on the selected action."""
        selected_action_key = self.action_keys_list[self.action_choice.GetSelection()]
        self._toggle_os_action_box(selected_action_key)

    def _toggle_os_action_box(self, action_key: str):
        """Shows or hides the OS Action Mode box depending on the action type."""
        is_os_action = action_key in self.OS_ACTION_KEYS

        self.os_action_label.Show(is_os_action)
        self.os_action_box.Show(is_os_action)

        self.panel.Layout()
        self.Fit()

    def on_ok(self, event):
        """Closes the dialog with OK status."""
        self.EndModal(wx.ID_OK)

    def on_cancel(self, event):
        """Closes the dialog with Cancel status."""
        self.EndModal(wx.ID_CANCEL)

    def get_data(self) -> Dict[str, Any]:
        """Retrieves the selected configuration from the dialog."""
        selected_time_index = self.time_choice.GetSelection()
        selected_action_index = self.action_choice.GetSelection()
        selected_os_mode_index = self.os_action_box.GetSelection()

        duration_minutes = self.time_choices_data[selected_time_index][1]
        action_key = self.action_keys_list[selected_action_index]
        os_action_mode = self.os_mode_keys_list[selected_os_mode_index]

        save_as_default = self.save_default_checkbox.IsChecked()

        return {
            'duration_minutes': duration_minutes,
            'action_key': action_key,
            'save_as_default': save_as_default,
            'os_action_mode': os_action_mode
        }