# dialogs/bookmark_list_dialog.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
import os
import logging
from typing import Dict, Any, Optional

from database import db_manager
from i18n import _
from nvda_controller import speak, LEVEL_CRITICAL
from utils import format_time

ID_BOOKMARK_LIST = wx.NewIdRef()


class BookmarkListDialog(wx.Dialog):
    """
    A dialog that displays a list of bookmarks for a specific book.
    Allows the user to jump to a bookmark or delete it.
    """

    def __init__(self, parent, book_id: int):
        """
        Args:
            parent: The parent window.
            book_id: The ID of the book to show bookmarks for.
        """
        super(BookmarkListDialog, self).__init__(parent, title=_("Bookmarks"))

        self.panel = wx.Panel(self)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.book_id = book_id
        self.bookmark_data: Dict[int, Dict[str, Any]] = {}

        list_label = wx.StaticText(self.panel, label=_("&Bookmarks:"))

        self.bookmark_list = wx.ListCtrl(self.panel, id=ID_BOOKMARK_LIST, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.bookmark_list.InsertColumn(0, _("Title"), width=200)
        self.bookmark_list.InsertColumn(1, _("Time"), width=100)
        self.bookmark_list.InsertColumn(2, _("File"), width=150)
        self.bookmark_list.InsertColumn(3, _("Note"), width=250)

        self._load_bookmarks()

        self.main_sizer.Add(list_label, 0, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 10)
        self.main_sizer.Add(self.bookmark_list, 1, wx.EXPAND | wx.ALL, 10)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.go_button = wx.Button(self.panel, wx.ID_OK, _("&Go To Bookmark"))
        self.delete_button = wx.Button(self.panel, wx.ID_DELETE, _("&Delete Bookmark"))
        self.close_button = wx.Button(self.panel, wx.ID_CANCEL, _("&Close"))

        button_sizer.Add(self.go_button, 0, wx.ALL, 5)
        button_sizer.Add(self.delete_button, 0, wx.ALL, 5)
        button_sizer.AddStretchSpacer(1)
        button_sizer.Add(self.close_button, 0, wx.ALL, 5)

        self.main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.panel.SetSizer(self.main_sizer)
        self.SetSize((750, 400))
        self.CentreOnParent()

        self.bookmark_list.SetFocus()
        if self.bookmark_list.GetItemCount() > 0:
            self.bookmark_list.Focus(0)
            self.bookmark_list.Select(0)

        self.SetDefaultItem(self.go_button)

        self.go_button.Bind(wx.EVT_BUTTON, self.on_go)
        self.delete_button.Bind(wx.EVT_BUTTON, self.on_delete)
        self.close_button.Bind(wx.EVT_BUTTON, self.on_close)
        self.bookmark_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_go)
        self.bookmark_list.Bind(wx.EVT_KEY_DOWN, self.on_list_key)

    def _load_bookmarks(self):
        """Fetches bookmarks from the database and populates the list."""
        self.bookmark_list.DeleteAllItems()
        self.bookmark_data.clear()

        try:
            bookmarks = db_manager.get_bookmarks_for_book(self.book_id)

            for index, bm in enumerate(bookmarks):
                self.bookmark_data[index] = bm

                title = bm['title'] or _("(No Title)")
                time_str = format_time(bm['position_ms'])
                file_name = os.path.basename(bm['file_path'])
                note = bm['note'] or ""

                self.bookmark_list.InsertItem(index, title)
                self.bookmark_list.SetItem(index, 1, time_str)
                self.bookmark_list.SetItem(index, 2, file_name)
                self.bookmark_list.SetItem(index, 3, note)
                self.bookmark_list.SetItemData(index, index)

        except Exception as e:
            logging.error(f"Error loading bookmarks: {e}", exc_info=True)
            speak(_("Error loading bookmarks."), LEVEL_CRITICAL)

    def on_go(self, event):
        """Handles the action to jump to the selected bookmark."""
        selected_index = self._get_selected_list_index()
        if selected_index == -1:
            return
        self.EndModal(wx.ID_OK)

    def on_delete(self, event):
        """Handles the deletion of the selected bookmark."""
        selected_index = self._get_selected_list_index()
        if selected_index == -1:
            return

        item_index = self.bookmark_list.GetItemData(selected_index)
        bookmark_id = self.bookmark_data[item_index]['id']
        bookmark_title = self.bookmark_list.GetItemText(selected_index)

        msg = _("Are you sure you want to delete bookmark '{0}'?").format(bookmark_title)
        if wx.MessageBox(msg, _("Confirm Delete"), wx.YES_NO | wx.ICON_WARNING) == wx.YES:
            try:
                db_manager.delete_bookmark(bookmark_id)
                speak(_("Bookmark deleted."), LEVEL_CRITICAL)

                self._load_bookmarks()

                if self.bookmark_list.GetItemCount() > 0:
                    new_selection = min(selected_index, self.bookmark_list.GetItemCount() - 1)
                    self.bookmark_list.Focus(new_selection)
                    self.bookmark_list.Select(new_selection)
                else:
                    self.go_button.Disable()
                    self.delete_button.Disable()

            except Exception as e:
                logging.error(f"Error deleting bookmark: {e}", exc_info=True)
                speak(_("Error deleting bookmark."), LEVEL_CRITICAL)

    def on_close(self, event):
        """Closes the dialog."""
        self.EndModal(wx.ID_CANCEL)

    def _get_selected_list_index(self) -> int:
        """Returns the visual index of the selected item."""
        return self.bookmark_list.GetFirstSelected()

    def on_list_key(self, event: wx.KeyEvent):
        """Handles keyboard shortcuts within the list (Delete, Enter)."""
        keycode = event.GetKeyCode()

        if keycode == wx.WXK_DELETE:
            self.on_delete(None)
        elif keycode == wx.WXK_RETURN:
            self.on_go(None)
        else:
            event.Skip()

    def get_selected_bookmark_data(self) -> Optional[Dict[str, Any]]:
        """Retrieves the data dictionary for the selected bookmark."""
        selected_index = self._get_selected_list_index()
        if selected_index != -1:
            item_index = self.bookmark_list.GetItemData(selected_index)
            return self.bookmark_data[item_index]
        return None