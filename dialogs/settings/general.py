# dialogs/settings/general.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import wx
from database import db_manager
from i18n import _, SUPPORTED_LANGUAGES

SETTING_LANGUAGE = 'language'
SETTING_CHECK_UPDATES = 'check_updates_on_startup'


class TabPanel(wx.Panel):
    """
    The "General" settings tab.
    Handles application language selection and startup update checks.
    """

    def __init__(self, parent):
        super(TabPanel, self).__init__(parent)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        lang_box = wx.StaticBox(self, label=_("Language"))
        lang_box_sizer = wx.StaticBoxSizer(lang_box, wx.VERTICAL)

        lang_label = wx.StaticText(self, label=_("Application Language:"))

        lang_choices = [_("English (en)")]
        lang_codes = SUPPORTED_LANGUAGES

        self.lang_map = dict(zip(lang_choices, lang_codes))
        self.lang_map_rev = dict(zip(lang_codes, lang_choices))

        self.lang_combo = wx.ComboBox(self, choices=lang_choices, style=wx.CB_READONLY)

        lang_box_sizer.Add(lang_label, 0, wx.ALL, 8)
        lang_box_sizer.Add(self.lang_combo, 0, wx.EXPAND | wx.ALL, 8)

        self.lang_restart_label = wx.StaticText(self, label=_("Language changes require an application restart."))
        lang_box_sizer.Add(self.lang_restart_label, 0, wx.ALL, 8)

        main_sizer.Add(lang_box_sizer, 0, wx.EXPAND | wx.ALL, 10)

        update_box = wx.StaticBox(self, label=_("Updates"))
        update_box_sizer = wx.StaticBoxSizer(update_box, wx.VERTICAL)

        self.update_checkbox = wx.CheckBox(self, label=_("Automatically check for updates on startup"))
        update_box_sizer.Add(self.update_checkbox, 0, wx.ALL | wx.EXPAND, 8)

        main_sizer.Add(update_box_sizer, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(main_sizer)

        self.current_lang_on_load = 'en'
        self.selected_lang_code = 'en'

        self._load_settings()

    def _load_settings(self):
        """Loads settings from the database."""
        current_lang = db_manager.get_setting(SETTING_LANGUAGE) or 'en'
        self.lang_combo.SetValue(self.lang_map_rev.get(current_lang, _("English (en)")))

        self.current_lang_on_load = current_lang
        self.selected_lang_code = current_lang

        check_updates = db_manager.get_setting(SETTING_CHECK_UPDATES)
        is_checked = (check_updates == 'True' or check_updates is None)
        self.update_checkbox.SetValue(is_checked)

    def save_settings(self):
        """Saves settings to the database."""
        selected_lang_display = self.lang_combo.GetValue()
        self.selected_lang_code = self.lang_map.get(selected_lang_display, 'en')
        db_manager.set_setting(SETTING_LANGUAGE, self.selected_lang_code)

        update_val = 'True' if self.update_checkbox.GetValue() else 'False'
        db_manager.set_setting(SETTING_CHECK_UPDATES, update_val)

    def get_current_language_on_load(self) -> str:
        """Returns the language code that was active when the tab was initialized."""
        return self.current_lang_on_load

    def get_selected_language(self) -> str:
        """Returns the language code selected by the user."""
        return self.selected_lang_code