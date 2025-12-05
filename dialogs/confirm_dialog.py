# dialogs/confirm_dialog.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import wx
from i18n import _

class CheckboxConfirmDialog(wx.Dialog):
    def __init__(self, parent, title, message, check_label, button_label):
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        
        self.panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        
# Warning message
        msg_text = wx.StaticText(self.panel, label=message)
        vbox.Add(msg_text, 1, wx.EXPAND | wx.ALL, 15)
        
# Confirmation checkbox
        self.checkbox = wx.CheckBox(self.panel, label=check_label)
        vbox.Add(self.checkbox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)
        
# Buttons
        btn_sizer = wx.StdDialogButtonSizer()
        self.action_btn = wx.Button(self.panel, wx.ID_OK, label=button_label)
        self.action_btn.Disable() 
        
        cancel_btn = wx.Button(self.panel, wx.ID_CANCEL, label=_("Cancel"))
        
        btn_sizer.AddButton(self.action_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        
        vbox.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        self.panel.SetSizer(vbox)
        vbox.Fit(self)
        self.Fit()
        self.CentreOnParent()
        
# Checkbox event
        self.checkbox.Bind(wx.EVT_CHECKBOX, self.on_check)
        
    def on_check(self, event):
# If checked, the button will be enabled
        self.action_btn.Enable(self.checkbox.GetValue())

