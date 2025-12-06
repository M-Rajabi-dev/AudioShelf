# dialogs/user_guide_dialog.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import wx
from i18n import _

USER_GUIDE_TEXT = """
AudioShelf User Guide

--- 1. Introduction ---
AudioShelf is a dedicated audiobook manager for Windows. Unlike standard media players, it treats every book as a unique project. It remembers your exact playback position, volume, speed, and bookmarks for each book independently.

--- 2. Library & Organization ---
AudioShelf organizes your audiobooks into a structured library.

*   Adding Books: 
    - Use 'File > Add Book Folder' (Ctrl+O) to import a folder containing audio files.
    - Use 'File > Add Single File' (Ctrl+Shift+O) for single-file audiobooks.
    - You can also Paste books from your clipboard directly into the list.

*   Shelves: 
    Create custom shelves (Ctrl+N) to categorize your books (e.g., "Fiction", "History"). You can move books between shelves using the context menu (Right Click or Applications Key).

*   Pinning: 
    Press Ctrl+P on any book to "Pin" it. Pinned books appear at the top of the library for quick access.

*   Finished Books: 
    You can mark books as 'Finished' from the context menu. They will be visually distinguished but remain in your library.

*   Refresh:
    Press F5 to reload the library list and update any changes.

--- 3. Playback Controls ---
Once you press Enter on a book, the Player opens.

*   Basic Controls:
    - Play/Pause: Space
    - Stop (and reset to start): Shift + Space
    - Volume: Up/Down Arrows
    - Speed Control: J (Faster), H (Slower), K (Reset). Hold Shift for larger steps (0.5x).

*   Navigation:
    - Seek: Left/Right Arrows (Short jump), Ctrl+Left/Right (Long jump).
    - Next/Prev File: PageDown / PageUp.
    - Go To Time: Press 'G' to jump to a specific time or percentage.
    - Go To File: Press 'Ctrl+G' to jump to a specific file number.

--- 4. Advanced Features ---

*   Metadata Save (Save to Source): 
    AudioShelf can save your progress and bookmarks into a small file next to your audiobook (.json). This allows you to move your book folder to another computer without losing your listening history. (Right Click > Save Data to Source).

*   Sleep Timer: 
    Press 'T' to start a quick sleep timer. Press Ctrl+T to configure custom duration and action (e.g., Shutdown computer after playback).

*   Bookmarks: 
    - Press 'B' to quick-bookmark the current position instantly.
    - Press 'Shift+B' to add a bookmark with a custom Title and Note.
    - Press 'Ctrl+B' to view and manage your saved bookmarks.

*   Equalizer: 
    Press 'E' to toggle the Equalizer on/off. Press Ctrl+E to adjust 10 frequency bands or select presets like "Vocal Clarity".

--- 5. Accessibility ---
AudioShelf is optimized for screen readers, particularly NVDA.
- Most actions have hotkeys (Press F1 for a full list of shortcuts).
- The interface uses standard controls compatible with screen readers.
- You can adjust the verbosity of speech announcements in Settings > Accessibility.
"""

class UserGuideDialog(wx.Dialog):
    """
    Displays the comprehensive User Guide in a read-only text control.
    """

    def __init__(self, parent):
        super(UserGuideDialog, self).__init__(parent, title=_("User Guide"), size=(700, 600))
        self.panel = wx.Panel(self)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.text_ctrl = wx.TextCtrl(
            self.panel, 
            value=_(USER_GUIDE_TEXT), 
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.BORDER_SUNKEN | wx.TE_BESTWRAP
        )
        
        btn_sizer = wx.StdDialogButtonSizer()
        close_btn = wx.Button(self.panel, wx.ID_OK, _("&Close"))
        btn_sizer.AddButton(close_btn)
        btn_sizer.Realize()

        main_sizer.Add(self.text_ctrl, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.BOTTOM | wx.RIGHT, 10)

        self.panel.SetSizer(main_sizer)
        self.CentreOnParent()
        
        self.text_ctrl.SetFocus() 
        self.text_ctrl.SetInsertionPoint(0)
