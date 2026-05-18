# dialogs/language_dialog.py
# Copyright (c) 2025-2026 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
import logging
from database import db_manager
from i18n import SUPPORTED_LANGUAGES, switch_language
from nvda_controller import speak, LEVEL_CRITICAL

class LanguageDialog(wx.Dialog):
    def __init__(self, parent):
        super(LanguageDialog, self).__init__(parent, title="Select Language", style=wx.DEFAULT_DIALOG_STYLE)

        self.panel = wx.Panel(self)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        instructions = "Please select your preferred language:"
        instructions_label = wx.StaticText(self.panel, label=instructions)
        self.main_sizer.Add(instructions_label, 0, wx.ALL | wx.EXPAND, 15)

        lang_choices = [
            "English (en)",
            "Italiano (it)",
            "فارسی (fa)",
            "Srpski (sr_Latn)",
            "Español (es)",
        ]
        
        lang_codes = SUPPORTED_LANGUAGES
        self.lang_map = dict(zip(lang_choices, lang_codes))

        self.lang_combo = wx.ComboBox(self.panel, choices=lang_choices, style=wx.CB_READONLY)
        
        current_lang = db_manager.get_setting('language') or 'en'
        for choice, code in self.lang_map.items():
            if code == current_lang:
                self.lang_combo.SetValue(choice)
                break
        else:
            self.lang_combo.SetSelection(0)

        self.main_sizer.Add(self.lang_combo, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)

        button_sizer = wx.StdDialogButtonSizer()
        self.ok_button = wx.Button(self.panel, wx.ID_OK, "OK")
        
        button_sizer.AddButton(self.ok_button)
        button_sizer.Realize()

        self.main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)

        self.panel.SetSizer(self.main_sizer)
        self.main_sizer.Fit(self)
        self.CentreOnParent()

        self.lang_combo.SetFocus()
        self.SetDefaultItem(self.ok_button)

        self.ok_button.Bind(wx.EVT_BUTTON, self.on_ok)
        
    def on_ok(self, event):
        selected_lang_display = self.lang_combo.GetValue()
        selected_lang_code = self.lang_map.get(selected_lang_display, 'en')
        
        try:
            switch_language(selected_lang_code)
            db_manager.set_setting('language_prompt_shown', 'True')
            speak("Language set successfully.", LEVEL_CRITICAL)
        except Exception as e:
            logging.error(f"Error switching language: {e}", exc_info=True)
            
        self.EndModal(wx.ID_OK)