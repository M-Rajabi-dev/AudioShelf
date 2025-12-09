# dialogs/shortcuts_dialog.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
from i18n import _


class ShortcutsDialog(wx.Dialog):
    def __init__(self, parent):
        super(ShortcutsDialog, self).__init__(parent, title=_("Keyboard Shortcuts"), size=(650, 600))

        self.panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        info_lbl = wx.StaticText(self.panel, label=_("List of all available keyboard shortcuts:"))
        main_sizer.Add(info_lbl, 0, wx.ALL, 10)

        self.list_ctrl = wx.ListCtrl(self.panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.list_ctrl.InsertColumn(0, _("Action"), width=400)
        self.list_ctrl.InsertColumn(1, _("Shortcut"), width=200)

        self._populate_list()

        main_sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        btn_sizer = wx.StdDialogButtonSizer()
        close_btn = wx.Button(self.panel, wx.ID_OK, _("&Close"))
        btn_sizer.AddButton(close_btn)
        btn_sizer.Realize()

        main_sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        self.panel.SetSizer(main_sizer)
        self.CentreOnParent()

        self.list_ctrl.SetFocus()
        self.SetDefaultItem(close_btn)

    def _add_item(self, action, shortcut):
        idx = self.list_ctrl.GetItemCount()
        self.list_ctrl.InsertItem(idx, action)
        self.list_ctrl.SetItem(idx, 1, shortcut)

    def _add_header(self, title):
        idx = self.list_ctrl.GetItemCount()
        self.list_ctrl.InsertItem(idx, f"--- {title} ---")
        self.list_ctrl.SetItem(idx, 1, "")

    def _populate_list(self):
        self._add_header(_("General & Library"))
        self._add_item(_("Add Book Folder"), "Ctrl + O")
        self._add_item(_("Add Single File"), "Ctrl + Shift + O")
        self._add_item(_("Paste Book from Clipboard"), "Ctrl + V")
        self._add_item(_("Create New Shelf"), "Ctrl + N")
        self._add_item(_("Refresh Library"), "F5")
        self._add_item(_("Rename Item"), "F2")
        self._add_item(_("Delete Item"), "Delete")
        self._add_item(_("Permanent Delete"), "Shift + Delete")
        self._add_item(_("Properties"), "Alt + Enter")
        self._add_item(_("Go Back / Up Level"), "Backspace / Alt + Left")
        self._add_item(_("Go Forward"), "Alt + Right")
        self._add_item(_("Settings"), "Ctrl + Shift + S")
        self._add_item(_("Cycle Verbosity"), "Ctrl + Shift + V")
        self._add_item(_("Search"), "Ctrl + F")
        self._add_item(_("Select All"), "Ctrl + A")
        self._add_item(_("Context Menu"), _("Apps Key / Right Click"))

        self._add_header(_("Navigation"))
        self._add_item(_("Focus Library List"), "Ctrl + B")
        self._add_item(_("Focus History List"), "Ctrl + H")
        self._add_item(_("Play Last Book"), "Ctrl + L")
        self._add_item(_("Toggle Pin (Selected)"), "Ctrl + P")
        self._add_item(_("Jump to All Books"), "Alt + 0")
        self._add_item(_("Jump to Default Shelf"), "Alt + 1")
        self._add_item(_("Jump to Custom Shelves"), "Alt + 2..8")
        self._add_item(_("Jump to Finished Books"), "Alt + 9")
        self._add_item(_("Jump to Pinned Books"), "Alt + P")
        self._add_item(_("Previous Shelf"), "Alt + PageUp")
        self._add_item(_("Next Shelf"), "Alt + PageDown")

        self._add_header(_("Player: Playback"))
        self._add_item(_("Play / Pause"), "Space")
        self._add_item(_("Stop (Reset to start)"), "Shift + Space")
        self._add_item(_("Previous File"), "PageUp")
        self._add_item(_("Next File"), "PageDown")
        self._add_item(_("Previous Book"), "Ctrl + PageUp")
        self._add_item(_("Next Book"), "Ctrl + PageDown")
        self._add_item(_("Previous Bookmark"), "Shift + PageUp")
        self._add_item(_("Next Bookmark"), "Shift + PageDown")
        self._add_item(_("Play Pinned Book (1-9)"), "Ctrl + 1..9")

        self._add_header(_("Player: Seeking"))
        self._add_item(_("Seek Forward (Short)"), _("Right Arrow"))
        self._add_item(_("Seek Backward (Short)"), _("Left Arrow"))
        self._add_item(_("Seek Forward (Long)"), _("Ctrl + Right Arrow"))
        self._add_item(_("Seek Backward (Long)"), _("Ctrl + Left Arrow"))
        self._add_item(_("Restart File"), "Home / Backspace")
        self._add_item(_("Go to End of File"), "End")
        self._add_item(_("Go to 50% of File"), "Ctrl + Backspace")
        self._add_item(_("Go to 30s before End"), "Shift + Backspace")
        self._add_item(_("Go To Time..."), "G")
        self._add_item(_("Show File List"), "F")
        self._add_item(_("Go To File Number..."), "Shift + F")

        self._add_header(_("Player: Audio"))
        self._add_item(_("Volume Up"), _("Up Arrow"))
        self._add_item(_("Volume Down"), _("Down Arrow"))
        self._add_item(_("Mute Toggle"), "M")
        self._add_item(_("Increase Speed (+0.1)"), "J")
        self._add_item(_("Decrease Speed (-0.1)"), "H")
        self._add_item(_("Increase Speed (+0.5)"), "Shift + J")
        self._add_item(_("Decrease Speed (-0.5)"), "Shift + H")
        self._add_item(_("Reset Speed"), "K")
        self._add_item(_("Toggle Equalizer"), "E")
        self._add_item(_("Open Equalizer"), "Ctrl + E")

        self._add_header(_("Player: Tools"))
        self._add_item(_("Add Quick Bookmark"), "B")
        self._add_item(_("Add Bookmark (Dialog)"), "Shift + B")
        self._add_item(_("Show Bookmarks"), "Ctrl + B")
        self._add_item(_("Set A-B Loop Start"), "S")
        self._add_item(_("Set A-B Loop End"), "A")
        self._add_item(_("Clear Loop"), "D")
        self._add_item(_("Toggle File Repeat"), "R")

        self._add_header(_("Player: Sleep Timer"))
        self._add_item(_("Start Quick Timer"), "T")
        self._add_item(_("Open Timer Dialog"), "Ctrl + T")
        self._add_item(_("Cancel Timer"), "Shift + T")
        self._add_item(_("Announce Timer"), "Alt + T")

        self._add_header(_("Player: Info Announcements"))
        self._add_item(_("Announce Current Time"), "I")
        self._add_item(_("Copy Current Time"), "Ctrl + I")
        self._add_item(_("Time Remaining (File)"), "Alt + I")
        self._add_item(_("Time Remaining (File, Speed Adjusted)"), "Shift + I")
        self._add_item(_("Total Elapsed / Duration"), "O")
        self._add_item(_("Total Remaining"), "Alt + O")
        self._add_item(_("Total Remaining (Speed Adjusted)"), "Shift + O")