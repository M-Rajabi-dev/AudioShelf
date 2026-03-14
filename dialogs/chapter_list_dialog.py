# dialogs/chapter_list_dialog.py
# Copyright (c) 2025-2026 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
from typing import List, Dict, Any
from i18n import _
from utils import format_time


class ChapterListDialog(wx.Dialog):
    """
    Displays audiobook chapters and lets the user jump directly to one.
    """

    def __init__(self, parent, chapters: List[Dict[str, Any]], current_time_ms: int):
        super(ChapterListDialog, self).__init__(parent, title=_("Chapter List"))

        self.panel = wx.Panel(self)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.chapters = chapters or []

        list_label = wx.StaticText(self.panel, label=_("&Chapters:"))
        self.main_sizer.Add(list_label, 0, wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT, 10)

        choices = []
        for idx, chapter in enumerate(self.chapters):
            title = str(chapter.get("title") or "").strip() or _("Chapter {0}").format(idx + 1)
            start_ms = max(0, int(chapter.get("start_ms") or 0))
            choices.append(_("{0}. {1} ({2})").format(idx + 1, title, format_time(start_ms)))

        self.chapter_list_box = wx.ListBox(self.panel, choices=choices, style=wx.LB_SINGLE)
        self.main_sizer.Add(self.chapter_list_box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        selected_index = self._find_current_chapter_index(current_time_ms)
        if 0 <= selected_index < len(choices):
            self.chapter_list_box.SetSelection(selected_index)

        button_sizer = wx.StdDialogButtonSizer()
        self.go_button = wx.Button(self.panel, wx.ID_OK, _("&Go to Chapter"))
        self.cancel_button = wx.Button(self.panel, wx.ID_CANCEL, _("&Cancel"))
        button_sizer.AddButton(self.go_button)
        button_sizer.AddButton(self.cancel_button)
        button_sizer.Realize()

        self.main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.panel.SetSizer(self.main_sizer)
        self.SetSize((600, 380))
        self.CentreOnParent()

        self.chapter_list_box.SetFocus()
        self.SetDefaultItem(self.go_button)

        self.go_button.Bind(wx.EVT_BUTTON, self.on_go)
        self.cancel_button.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.chapter_list_box.Bind(wx.EVT_LISTBOX_DCLICK, self.on_go)
        self.chapter_list_box.Bind(wx.EVT_KEY_DOWN, self.on_list_key)

    def _find_current_chapter_index(self, current_time_ms: int) -> int:
        if not self.chapters:
            return wx.NOT_FOUND

        current_time_ms = max(0, int(current_time_ms or 0))
        selected = 0
        for idx, chapter in enumerate(self.chapters):
            start_ms = max(0, int(chapter.get("start_ms") or 0))
            end_ms = max(start_ms, int(chapter.get("end_ms") or start_ms))
            if start_ms <= current_time_ms < end_ms:
                return idx
            if current_time_ms >= start_ms:
                selected = idx
        return selected

    def on_go(self, event):
        self.EndModal(wx.ID_OK)

    def on_cancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def on_list_key(self, event: wx.KeyEvent):
        if event.GetKeyCode() == wx.WXK_RETURN:
            if self.chapter_list_box.GetSelection() != wx.NOT_FOUND:
                self.on_go(None)
            else:
                event.Skip()
        else:
            event.Skip()

    def get_selected_index(self) -> int:
        return self.chapter_list_box.GetSelection()
