# dialogs/goto_dialog.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import wx
import re
from typing import Optional
from i18n import _
from nvda_controller import speak, LEVEL_MINIMAL

# Regex patterns for time parsing
TIME_PATTERN = re.compile(r'^(?:(\d+):)?(?:(\d+):)?(\d+)$')
PERCENT_PATTERN = re.compile(r'^(\d{1,3})\s*%$')


class GoToDialog(wx.Dialog):
    """
    A dialog that allows the user to enter a specific time (HH:MM:SS)
    or a percentage (e.g., 50%) to jump to within the current track.
    """

    def __init__(self, parent, total_duration_ms: int):
        """
        Args:
            parent: The parent window.
            total_duration_ms: The total duration of the current file in milliseconds.
        """
        super(GoToDialog, self).__init__(parent, title=_("Go To..."))

        self.panel = wx.Panel(self)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.total_duration_ms = total_duration_ms

        instructions = _("Enter time (e.g., 1:30:10, 45:20, or 300) or percentage (e.g., 50%).")
        instructions_label = wx.StaticText(self.panel, label=instructions)

        self.time_text = wx.TextCtrl(self.panel)

        self.main_sizer.Add(instructions_label, 0, wx.ALL | wx.EXPAND, 10)
        self.main_sizer.Add(self.time_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        button_sizer = wx.StdDialogButtonSizer()
        self.ok_button = wx.Button(self.panel, wx.ID_OK, _("&Go"))
        self.cancel_button = wx.Button(self.panel, wx.ID_CANCEL, _("&Cancel"))

        button_sizer.AddButton(self.ok_button)
        button_sizer.AddButton(self.cancel_button)
        button_sizer.Realize()

        self.main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.panel.SetSizer(self.main_sizer)
        self.main_sizer.Fit(self)
        self.CentreOnParent()

        self.time_text.SetFocus()
        self.SetDefaultItem(self.ok_button)

        self.ok_button.Bind(wx.EVT_BUTTON, self.on_go)
        self.cancel_button.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.time_text.Bind(wx.EVT_KEY_DOWN, self.on_text_key)

    def on_go(self, event):
        """Validates input and closes the dialog with OK status if valid."""
        if self.get_time_in_ms() is not None:
            self.EndModal(wx.ID_OK)
        else:
            speak(_("Invalid format."), LEVEL_MINIMAL)
            wx.MessageBox(
                _("Invalid format. Please enter time as HH:MM:SS or percentage as 50%."),
                _("Invalid Input"),
                wx.OK | wx.ICON_ERROR
            )
            self.time_text.SetFocus()
            self.time_text.SelectAll()

    def on_cancel(self, event):
        """Closes the dialog with Cancel status."""
        self.EndModal(wx.ID_CANCEL)

    def on_text_key(self, event: wx.KeyEvent):
        """Handles Enter key press in the text control."""
        if event.GetKeyCode() == wx.WXK_RETURN:
            self.on_go(None)
        else:
            event.Skip()

    def get_time_in_ms(self) -> Optional[int]:
        """
        Parses the user input and calculates the target time in milliseconds.

        Returns:
            The target time in ms, or None if the input format is invalid.
        """
        input_str = self.time_text.GetValue().strip()

        # Check for percentage
        percent_match = PERCENT_PATTERN.match(input_str)
        if percent_match:
            percent = int(percent_match.group(1))
            if 0 <= percent <= 100:
                return (self.total_duration_ms * percent) // 100
            else:
                return None

        # Check for time format
        time_match = TIME_PATTERN.match(input_str)
        if time_match:
            groups = time_match.groups()

            hours = int(groups[0] or 0)
            minutes = int(groups[1] or 0)
            seconds = int(groups[2] or 0)

            # Handle MM:SS format (where groups[0] is None)
            if groups[0] is None and groups[1] is not None:
                hours = 0
                minutes = int(groups[1])
                seconds = int(groups[2])
            # Handle SS format (where groups[0] and [1] are None)
            elif groups[0] is None and groups[1] is None:
                hours = 0
                minutes = 0
                seconds = int(groups[2])

            total_seconds = (hours * 3600) + (minutes * 60) + seconds
            return total_seconds * 1000

        return None