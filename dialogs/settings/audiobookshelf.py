# dialogs/settings/audiobookshelf.py
# Copyright (c) 2025-2026 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
from database import db_manager
from i18n import _

SETTING_AUDIOBOOKSHELF_SERVER_URL = 'audiobookshelf_server_url'
SETTING_AUDIOBOOKSHELF_API_KEY = 'audiobookshelf_api_key'
SETTING_AUDIOBOOKSHELF_AUTO_UPLOAD = 'audiobookshelf_auto_upload'
SETTING_AUDIOBOOKSHELF_UPLOAD_LIBRARY_ID = 'audiobookshelf_upload_library_id'
SETTING_AUDIOBOOKSHELF_UPLOAD_FOLDER_ID = 'audiobookshelf_upload_folder_id'


class TabPanel(wx.Panel):
    """
    Dedicated settings tab for Audiobookshelf server integration.
    """

    def __init__(self, parent):
        super(TabPanel, self).__init__(parent)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        abs_box = wx.StaticBox(self, label=_("AudioBookshelf"))
        abs_box_sizer = wx.StaticBoxSizer(abs_box, wx.VERTICAL)

        abs_server_label = wx.StaticText(self, label=_("Server URL:"))
        self.abs_server_ctrl = wx.TextCtrl(self)
        abs_box_sizer.Add(abs_server_label, 0, wx.ALL, 8)
        abs_box_sizer.Add(self.abs_server_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        abs_key_label = wx.StaticText(self, label=_("API Key:"))
        self.abs_api_key_ctrl = wx.TextCtrl(self, style=wx.TE_PASSWORD)
        abs_box_sizer.Add(abs_key_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        abs_box_sizer.Add(self.abs_api_key_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.abs_auto_upload_checkbox = wx.CheckBox(self, label=_("Upload newly added local books to Audiobookshelf"))
        abs_box_sizer.Add(self.abs_auto_upload_checkbox, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        abs_upload_library_label = wx.StaticText(self, label=_("Upload Library ID (optional):"))
        self.abs_upload_library_ctrl = wx.TextCtrl(self)
        abs_box_sizer.Add(abs_upload_library_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        abs_box_sizer.Add(self.abs_upload_library_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        abs_upload_folder_label = wx.StaticText(self, label=_("Upload Folder ID (optional):"))
        self.abs_upload_folder_ctrl = wx.TextCtrl(self)
        abs_box_sizer.Add(abs_upload_folder_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        abs_box_sizer.Add(self.abs_upload_folder_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        main_sizer.Add(abs_box_sizer, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(main_sizer)

        self._load_settings()

    def _load_settings(self):
        abs_server = db_manager.get_setting(SETTING_AUDIOBOOKSHELF_SERVER_URL) or ''
        abs_api_key = db_manager.get_setting(SETTING_AUDIOBOOKSHELF_API_KEY) or ''
        abs_auto_upload = db_manager.get_setting(SETTING_AUDIOBOOKSHELF_AUTO_UPLOAD)
        abs_upload_library = db_manager.get_setting(SETTING_AUDIOBOOKSHELF_UPLOAD_LIBRARY_ID) or ''
        abs_upload_folder = db_manager.get_setting(SETTING_AUDIOBOOKSHELF_UPLOAD_FOLDER_ID) or ''
        self.abs_server_ctrl.SetValue(abs_server)
        self.abs_api_key_ctrl.SetValue(abs_api_key)
        self.abs_auto_upload_checkbox.SetValue(False if abs_auto_upload == 'False' else True)
        self.abs_upload_library_ctrl.SetValue(abs_upload_library)
        self.abs_upload_folder_ctrl.SetValue(abs_upload_folder)

    def save_settings(self):
        db_manager.set_setting(SETTING_AUDIOBOOKSHELF_SERVER_URL, self.abs_server_ctrl.GetValue().strip())
        db_manager.set_setting(SETTING_AUDIOBOOKSHELF_API_KEY, self.abs_api_key_ctrl.GetValue().strip())
        db_manager.set_setting(
            SETTING_AUDIOBOOKSHELF_AUTO_UPLOAD,
            'True' if self.abs_auto_upload_checkbox.GetValue() else 'False'
        )
        db_manager.set_setting(SETTING_AUDIOBOOKSHELF_UPLOAD_LIBRARY_ID, self.abs_upload_library_ctrl.GetValue().strip())
        db_manager.set_setting(SETTING_AUDIOBOOKSHELF_UPLOAD_FOLDER_ID, self.abs_upload_folder_ctrl.GetValue().strip())
