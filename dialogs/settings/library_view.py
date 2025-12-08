# dialogs/settings/library_view.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
import logging
from typing import Dict
from database import db_manager
from i18n import _

# Define UI State Keys mapping: (key, display_name_func)
VIRTUAL_SHELF_KEYS = [
    ("virtual_pinned", lambda: _("Pinned Books")),
    ("virtual_all_books", lambda: _("All Books")),
    ("virtual_finished", lambda: _("Finished Books")),
]


class TabPanel(wx.Panel):
    """
    The "Library View" settings tab.
    Allows the user to configure the visibility of virtual sections (e.g., Pinned, All Books)
    in the main library list.
    """

    def __init__(self, parent):
        super(TabPanel, self).__init__(parent)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.view_controls: Dict[str, wx.CheckBox] = {}

        view_box = wx.StaticBox(self, label=_("Root List Visibility"))
        view_box_sizer = wx.StaticBoxSizer(view_box, wx.VERTICAL)

        panel_sizer = wx.BoxSizer(wx.VERTICAL)

        for key, name_func in VIRTUAL_SHELF_KEYS:
            self._add_view_control(panel_sizer, key, name_func())

        view_box_sizer.Add(panel_sizer, 1, wx.EXPAND | wx.ALL, 8)

        main_sizer.Add(view_box_sizer, 1, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(main_sizer)

        self._load_settings()

    def _add_view_control(self, sizer: wx.BoxSizer, key: str, name: str):
        """
        Helper method to create and add a 'Show' checkbox for a specific section.

        Args:
            sizer: The sizer to add the checkbox to.
            key: The unique UI state key (e.g., 'virtual_pinned').
            name: The display name for the section.
        """
        label = _("Show '{0}' section").format(name)
        show_check = wx.CheckBox(self, label=label)

        sizer.Add(show_check, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.view_controls[key] = show_check

    def _load_settings(self):
        """Loads the current visibility settings from the database."""
        try:
            for key, checkbox in self.view_controls.items():
                is_hidden, _ = db_manager.get_ui_item_state(key)
                # Checkbox is "Show", so it is checked if is_hidden is False
                checkbox.SetValue(not is_hidden)
        except Exception as e:
            logging.error(f"Error loading Library View settings: {e}", exc_info=True)

    def save_settings(self):
        """Saves the user's visibility preferences to the database."""
        try:
            for key, checkbox in self.view_controls.items():
                is_hidden = not checkbox.GetValue()
                # Pass None for is_expanded to preserve existing expansion state
                db_manager.set_ui_item_state(key, is_hidden, is_expanded=None)
        except Exception as e:
            logging.error(f"Error saving Library View settings: {e}", exc_info=True)