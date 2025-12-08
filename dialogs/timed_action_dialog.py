# dialogs/timed_action_dialog.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
from i18n import _
from nvda_controller import speak, LEVEL_CRITICAL


class TimedActionDialog(wx.Dialog):
    """
    A dialog that displays a countdown timer for a pending sensitive action
    (e.g., shutdown, sleep), allowing the user to cancel it.
    """

    DEFAULT_COUNTDOWN_SECONDS = 120

    def __init__(self, parent, action_label: str, countdown_seconds: int = DEFAULT_COUNTDOWN_SECONDS):
        """
        Args:
            parent: The parent window.
            action_label: The text describing the action (e.g., "Shutdown computer").
            countdown_seconds: The duration in seconds before the action executes automatically.
        """
        super(TimedActionDialog, self).__init__(parent, title=_("Action Confirmation"))

        self.panel = wx.Panel(self)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.action_label_str = action_label
        self.remaining_seconds = countdown_seconds

        self.info_text = wx.StaticText(self.panel, label=_(
            "The sleep timer has expired. The following action will be performed:"
        ))

        self.action_text = wx.StaticText(self.panel, label=self.action_label_str)
        font = self.action_text.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        self.action_text.SetFont(font)

        self.countdown_text = wx.StaticText(self.panel, label=self._format_countdown_label())

        self.main_sizer.Add(self.info_text, 0, wx.EXPAND | wx.ALL, 15)
        self.main_sizer.Add(self.action_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)
        self.main_sizer.Add(self.countdown_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)

        self.cancel_button = wx.Button(self.panel, wx.ID_CANCEL, _("&Cancel Action"))

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.AddStretchSpacer()
        button_sizer.Add(self.cancel_button, 0, wx.ALIGN_CENTER)
        button_sizer.AddStretchSpacer()

        self.main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.panel.SetSizer(self.main_sizer)
        self.Fit()
        self.CentreOnParent()

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_timer_tick, self.timer)
        self.timer.Start(1000)

        self.cancel_button.SetFocus()

        speak(
            _("Confirmation required. Action: {0}. Press Cancel to stop.").format(self.action_label_str),
            LEVEL_CRITICAL
        )
        self._announce_time()

    def _format_countdown_label(self) -> str:
        """Returns the formatted time remaining string."""
        return _("Time remaining: {0} seconds").format(self.remaining_seconds)

    def _announce_time(self):
        """Speaks the remaining time at specific intervals (1m, 30s, <=10s)."""
        if self.remaining_seconds == 60:
            speak(_("1 minute remaining"), LEVEL_CRITICAL)
        elif self.remaining_seconds == 30:
            speak(_("30 seconds remaining"), LEVEL_CRITICAL)
        elif self.remaining_seconds <= 10:
            speak(f"{self.remaining_seconds}", LEVEL_CRITICAL)

    def _on_timer_tick(self, event: wx.Event):
        """Handles timer updates; closes dialog with OK if time runs out."""
        self.remaining_seconds -= 1

        if self.remaining_seconds <= 0:
            self.timer.Stop()
            self.EndModal(wx.ID_OK)
            return

        self.countdown_text.SetLabel(self._format_countdown_label())
        self._announce_time()

    def ShowModal(self) -> int:
        """Overrides ShowModal to ensure the timer stops upon closing."""
        try:
            return super(TimedActionDialog, self).ShowModal()
        finally:
            if self.timer.IsRunning():
                self.timer.Stop()