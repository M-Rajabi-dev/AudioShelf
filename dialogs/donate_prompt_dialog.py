# dialogs/donate_prompt_dialog.py
# Copyright (c) 2025-2026 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
from i18n import _
from database import db_manager
from nvda_controller import speak, LEVEL_CRITICAL

class DonatePromptDialog(wx.Dialog):
    def __init__(self, parent):
        super(DonatePromptDialog, self).__init__(parent, title=_("Support AudioShelf"))
        
        self.panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        msg = _("Hi there! You have been using AudioShelf for a while now.\n\n"
                "This application is developed in my free time with a strong focus on accessibility. "
                "If you find it useful and it has made listening to audiobooks easier for you, "
                "would you consider supporting its continued development?")
        
        lbl = wx.StaticText(self.panel, label=msg)
        lbl.Wrap(450)
        vbox.Add(lbl, 1, wx.EXPAND | wx.ALL, 15)
        
        btn_sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.btn_donate = wx.Button(self.panel, label=_("Yes, show me how to donate!"))
        self.btn_later = wx.Button(self.panel, label=_("Not right now, remind me later"))
        self.btn_never = wx.Button(self.panel, label=_("No thanks, never ask me again"))
        
        btn_sizer.Add(self.btn_donate, 0, wx.EXPAND | wx.BOTTOM, 10)
        btn_sizer.Add(self.btn_later, 0, wx.EXPAND | wx.BOTTOM, 10)
        btn_sizer.Add(self.btn_never, 0, wx.EXPAND | wx.BOTTOM, 10)
        
        vbox.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 15)
        
        self.panel.SetSizer(vbox)
        vbox.Fit(self)
        self.Fit()
        self.CentreOnParent()
        
        self.btn_donate.SetFocus()
        self.SetDefaultItem(self.btn_donate)
        
        self.btn_donate.Bind(wx.EVT_BUTTON, self.on_donate)
        self.btn_later.Bind(wx.EVT_BUTTON, self.on_later)
        self.btn_never.Bind(wx.EVT_BUTTON, self.on_never)
        
    def on_donate(self, event):
        self.EndModal(wx.ID_YES)
        
    def on_later(self, event):
        self.EndModal(wx.ID_NO)
        
    def on_never(self, event):
        db_manager.set_setting('suppress_donate_prompt', 'True')
        speak(_("You won't be asked again."), LEVEL_CRITICAL)
        self.EndModal(wx.ID_CANCEL)