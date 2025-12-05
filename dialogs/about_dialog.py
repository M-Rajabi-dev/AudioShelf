# dialogs/about_dialog.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import wx
from i18n import _
from nvda_controller import speak, LEVEL_MINIMAL

APP_NAME = "AudioShelf"
import os
import sys

def get_app_version():
    try:
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            # Go up one level from dialogs folder
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        version_path = os.path.join(base_path, 'VERSION')
        with open(version_path, 'r') as f:
            return f.read().strip()
    except Exception:
        return "1.0.0"

APP_VERSION = get_app_version()
COPYRIGHT = "Copyright (c) 2025 Mehdi Rajabi. All rights reserved."
GITHUB_URL = "https://github.com/M-Rajabi-Dev/AudioShelf"
CONTACT_EMAIL = "mehdi.rajabi.dev@gmail.com"


class AboutDialog(wx.Dialog):
    """
    Displays application information including version, description, copyright,
    and provides buttons to copy contact/source links.
    """

    def __init__(self, parent):
        super(AboutDialog, self).__init__(parent, title=_("About AudioShelf"))
        self.panel = wx.Panel(self)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        name_font = wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        name_text = wx.StaticText(self.panel, label=APP_NAME)
        name_text.SetFont(name_font)

        ver_text = wx.StaticText(self.panel, label=_("Version {0}").format(APP_VERSION))

        desc_str = _(
            "A specialized audiobook manager designed for precision and accessibility.\n"
            "Unlike generic media players, AudioShelf treats every book as a unique entity, "
            "preserving its independent progress, history, and playback settings."
        )
        desc_text = wx.StaticText(self.panel, label=desc_str, style=wx.ALIGN_CENTER)
        desc_text.Wrap(400)

        copy_text = wx.StaticText(self.panel, label=COPYRIGHT)

        # Buttons Sizer
        links_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        btn_github = wx.Button(self.panel, label=_("Copy Source Link"))
        btn_github.Bind(wx.EVT_BUTTON, lambda e: self._copy_to_clipboard(GITHUB_URL, _("GitHub link")))
        
        btn_email = wx.Button(self.panel, label=_("Copy Email Address"))
        btn_email.Bind(wx.EVT_BUTTON, lambda e: self._copy_to_clipboard(CONTACT_EMAIL, _("Email address")))

        links_sizer.Add(btn_github, 0, wx.ALL, 5)
        links_sizer.Add(btn_email, 0, wx.ALL, 5)

        main_sizer.Add(name_text, 0, wx.ALIGN_CENTER | wx.TOP, 20)
        main_sizer.Add(ver_text, 0, wx.ALIGN_CENTER | wx.TOP, 5)
        main_sizer.Add(desc_text, 0, wx.ALIGN_CENTER | wx.ALL, 20)
        main_sizer.Add(copy_text, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        main_sizer.Add(wx.StaticLine(self.panel), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 20)
        main_sizer.Add(links_sizer, 0, wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, 15)

        btn_sizer = wx.StdDialogButtonSizer()
        close_btn = wx.Button(self.panel, wx.ID_OK, _("&Close"))
        btn_sizer.AddButton(close_btn)
        btn_sizer.Realize()

        main_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 15)

        self.panel.SetSizer(main_sizer)
        self.Fit()
        self.CentreOnParent()
        
        close_btn.SetFocus()
        self.SetDefaultItem(close_btn)

    def _copy_to_clipboard(self, text, name):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
            speak(_("{0} copied.").format(name), LEVEL_MINIMAL)
        else:
            speak(_("Failed to copy."), LEVEL_MINIMAL)
