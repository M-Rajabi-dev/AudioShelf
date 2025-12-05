# dialogs/bookmark_dialog.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import wx
from i18n import _


class BookmarkDialog(wx.Dialog):
    """
    A dialog for adding or editing a bookmark, providing fields for title and notes.
    """

    def __init__(self, parent, title="", note=""):
        super(BookmarkDialog, self).__init__(parent, title=_("Add/Edit Bookmark"))

        self.panel = wx.Panel(self)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        title_label = wx.StaticText(self.panel, label=_("&Title (Optional):"))
        self.title_text = wx.TextCtrl(self.panel, value=title, style=wx.TE_PROCESS_ENTER)

        self.main_sizer.Add(title_label, 0, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 10)
        self.main_sizer.Add(self.title_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        note_label = wx.StaticText(self.panel, label=_("&Note (Optional):"))
        self.note_text = wx.TextCtrl(self.panel, value=note, style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER, size=(-1, 150))

        self.main_sizer.Add(note_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        self.main_sizer.Add(self.note_text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        button_sizer = wx.StdDialogButtonSizer()
        self.ok_button = wx.Button(self.panel, wx.ID_OK, _("&OK"))
        self.cancel_button = wx.Button(self.panel, wx.ID_CANCEL, _("&Cancel"))

        button_sizer.AddButton(self.ok_button)
        button_sizer.AddButton(self.cancel_button)
        button_sizer.Realize()

        self.main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.panel.SetSizer(self.main_sizer)
        self.title_text.SetFocus()

        self.main_sizer.Fit(self)
        self.SetMinSize(self.GetSize())
        self.CentreOnParent()

        self.SetDefaultItem(self.ok_button)

        self.ok_button.Bind(wx.EVT_BUTTON, self.on_ok)
        self.cancel_button.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.title_text.Bind(wx.EVT_TEXT_ENTER, self.on_ok)
        self.note_text.Bind(wx.EVT_KEY_DOWN, self.on_note_key_down)

    def on_note_key_down(self, event: wx.KeyEvent):
        """
        Handles key presses in the multiline note field.
        Enter submits the dialog; Ctrl+Enter inserts a new line.
        """
        if event.GetKeyCode() == wx.WXK_RETURN:
            if event.ControlDown():
                event.Skip()
            else:
                self.on_ok(None)
                return
        else:
            event.Skip()

    def on_ok(self, event):
        """Closes the dialog with OK status."""
        self.EndModal(wx.ID_OK)

    def on_cancel(self, event):
        """Closes the dialog with Cancel status."""
        self.EndModal(wx.ID_CANCEL)

    def get_data(self) -> dict:
        """Retrieves the entered data from the dialog fields."""
        return {
            "title": self.title_text.GetValue(),
            "note": self.note_text.GetValue()
        }