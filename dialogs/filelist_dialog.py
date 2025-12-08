# dialogs/filelist_dialog.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
import os
from typing import List, Tuple
from i18n import _


class FileListDialog(wx.Dialog):
    """
    A dialog that displays a list of all playable files for the current book,
    allowing the user to select one to jump to directly.
    """

    def __init__(self, parent, book_files: List[Tuple[int, str]], current_index: int):
        """
        Args:
            parent: The parent window (PlayerFrame).
            book_files: A list of tuples containing (file_id, file_path).
            current_index: The 0-based index of the currently playing file.
        """
        super(FileListDialog, self).__init__(parent, title=_("File List"))

        self.panel = wx.Panel(self)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        list_label = wx.StaticText(self.panel, label=_("&Files:"))

        # Display only filenames, not full paths
        self.file_names = [os.path.basename(path) for (fid, path) in book_files]

        self.file_list_box = wx.ListBox(self.panel, choices=self.file_names, style=wx.LB_SINGLE)
        self.file_list_box.SetSelection(current_index)

        self.main_sizer.Add(list_label, 0, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 10)
        self.main_sizer.Add(self.file_list_box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        button_sizer = wx.StdDialogButtonSizer()
        self.go_button = wx.Button(self.panel, wx.ID_OK, _("&Go to File"))
        self.cancel_button = wx.Button(self.panel, wx.ID_CANCEL, _("&Cancel"))

        button_sizer.AddButton(self.go_button)
        button_sizer.AddButton(self.cancel_button)
        button_sizer.Realize()

        self.main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.panel.SetSizer(self.main_sizer)
        self.SetSize((500, 350))
        self.CentreOnParent()

        self.file_list_box.SetFocus()

        self.go_button.Bind(wx.EVT_BUTTON, self.on_go)
        self.cancel_button.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.file_list_box.Bind(wx.EVT_LISTBOX_DCLICK, self.on_go)
        self.file_list_box.Bind(wx.EVT_KEY_DOWN, self.on_list_key)

        self.SetDefaultItem(self.go_button)

    def on_go(self, event):
        """Closes the dialog with OK status."""
        self.EndModal(wx.ID_OK)

    def on_cancel(self, event):
        """Closes the dialog with Cancel status."""
        self.EndModal(wx.ID_CANCEL)

    def on_list_key(self, event: wx.KeyEvent):
        """Handles Enter key on the list box to trigger selection."""
        keycode = event.GetKeyCode()

        if keycode == wx.WXK_RETURN:
            if self.file_list_box.GetSelection() != wx.NOT_FOUND:
                self.on_go(None)
            else:
                event.Skip()
        else:
            event.Skip()

    def get_selected_index(self) -> int:
        """Returns the index of the selected file."""
        return self.file_list_box.GetSelection()