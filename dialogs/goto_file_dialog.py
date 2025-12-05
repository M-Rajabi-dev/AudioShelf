# dialogs/goto_file_dialog.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import wx
import re
from i18n import _
from nvda_controller import speak, LEVEL_MINIMAL

NUMBER_PATTERN = re.compile(r'^\d+$')


class GoToFileDialog(wx.Dialog):
    """
    A dialog that allows the user to enter a file number (1-based) to jump to.
    """

    def __init__(self, parent, current_file_num: int, max_file_num: int):
        """
        Args:
            parent: The parent window.
            current_file_num: The 1-based index of the current file.
            max_file_num: The total number of files in the book.
        """
        super(GoToFileDialog, self).__init__(parent, title=_("Go to File Number"))

        self.panel = wx.Panel(self)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.max_file_num = max_file_num
        self.target_file_index: int = -1

        instructions = _("Enter file number (1 to {0}):").format(self.max_file_num)
        instructions_label = wx.StaticText(self.panel, label=instructions)

        self.file_num_text = wx.TextCtrl(self.panel, value=str(current_file_num))

        self.main_sizer.Add(instructions_label, 0, wx.ALL | wx.EXPAND, 10)
        self.main_sizer.Add(self.file_num_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

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

        self.file_num_text.SetFocus()
        self.file_num_text.SelectAll()

        self.SetDefaultItem(self.ok_button)

        self.ok_button.Bind(wx.EVT_BUTTON, self.on_go)
        self.cancel_button.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.file_num_text.Bind(wx.EVT_KEY_DOWN, self.on_text_key)

    def on_go(self, event):
        """Validates input and closes the dialog with OK status if valid."""
        if self._validate_input():
            self.EndModal(wx.ID_OK)
        else:
            speak(_("Invalid number."), LEVEL_MINIMAL)
            wx.MessageBox(
                _("Invalid format. Please enter a number between 1 and {0}.").format(self.max_file_num),
                _("Invalid Input"),
                wx.OK | wx.ICON_ERROR
            )
            self.file_num_text.SetFocus()
            self.file_num_text.SelectAll()

    def on_cancel(self, event):
        """Closes the dialog with Cancel status."""
        self.EndModal(wx.ID_CANCEL)

    def on_text_key(self, event: wx.KeyEvent):
        """Handles Enter key press in the text field."""
        if event.GetKeyCode() == wx.WXK_RETURN:
            self.on_go(None)
        else:
            event.Skip()

    def _validate_input(self) -> bool:
        """
        Validates that the input is a number within the valid range.
        Sets self.target_file_index (0-based) if valid.

        Returns:
            True if valid, False otherwise.
        """
        input_str = self.file_num_text.GetValue().strip()

        if not NUMBER_PATTERN.match(input_str):
            return False

        try:
            target_num_1_based = int(input_str)

            if not (1 <= target_num_1_based <= self.max_file_num):
                return False

            self.target_file_index = target_num_1_based - 1
            return True

        except Exception:
            return False

    def get_selected_index(self) -> int:
        """Returns the 0-based index of the selected file."""
        return self.target_file_index