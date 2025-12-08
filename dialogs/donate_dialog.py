# dialogs/donate_dialog.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
from i18n import _
from nvda_controller import speak, LEVEL_MINIMAL

# Crypto Addresses
CRYPTO_WALLETS = [
    ("USDT (TRC20)", "TBzrDuCt8PHAkKL8PLLNq8Co9PYZqVJ9b2"),
    ("Toncoin (TON)", "UQCu4zZ3u6dKNBPx1YJcnSs5g9bZM10BzYCqQ3v4T3PeDOXe"),
    ("Bitcoin (BTC)", "bc1qlvdxg9j8rmp5w7552ywsqqtkddt5p7dvwwa4j8"),
    ("Litecoin (LTC)", "ltc1q9xczsnpg9ewzt45evrld28urzfkja8gm2sca5r"),
]


class DonateDialog(wx.Dialog):
    """
    A dialog displaying cryptocurrency wallet addresses for donations.
    Allows users to easily copy addresses to the clipboard.
    """

    def __init__(self, parent):
        super(DonateDialog, self).__init__(parent, title=_("Support Development"), size=(550, 450))
        self.panel = wx.Panel(self)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        intro_lbl = wx.StaticText(self.panel, label=_(
            "If you find AudioShelf useful, you can support its development via cryptocurrency:"))
        main_sizer.Add(intro_lbl, 0, wx.ALL | wx.EXPAND, 15)

        wallets_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Scrollable window for wallets if list grows
        self.scrolled_window = wx.ScrolledWindow(self.panel, style=wx.VSCROLL)
        self.scrolled_window.SetScrollRate(0, 20)
        scroll_sizer = wx.BoxSizer(wx.VERTICAL)

        for name, address in CRYPTO_WALLETS:
            self._add_wallet_row(self.scrolled_window, scroll_sizer, name, address)

        self.scrolled_window.SetSizer(scroll_sizer)
        wallets_sizer.Add(self.scrolled_window, 1, wx.EXPAND)
        
        main_sizer.Add(wallets_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 15)

        btn_sizer = wx.StdDialogButtonSizer()
        close_btn = wx.Button(self.panel, wx.ID_OK, _("&Close"))
        btn_sizer.AddButton(close_btn)
        btn_sizer.Realize()

        main_sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 15)

        self.panel.SetSizer(main_sizer)
        self.Layout()
        self.CentreOnParent()
        
        close_btn.SetFocus()
        self.SetDefaultItem(close_btn)

    def _add_wallet_row(self, parent, sizer, name, address):
        """Adds a UI row containing the wallet label, address field, and copy button."""
        row_sizer = wx.BoxSizer(wx.VERTICAL)
        
        lbl = wx.StaticText(parent, label=name)
        font = lbl.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        lbl.SetFont(font)
        row_sizer.Add(lbl, 0, wx.BOTTOM, 5)

        input_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # Fixed: Removed wx.ALIGN_CENTER_VERTICAL which conflicts with wx.EXPAND
        text_ctrl = wx.TextCtrl(parent, value=address, style=wx.TE_READONLY)
        input_sizer.Add(text_ctrl, 1, wx.EXPAND | wx.RIGHT, 5)

        # Dynamic label for better accessibility and clarity
        btn_label = _("Copy {0} Address").format(name.split(' ')[0])
        copy_btn = wx.Button(parent, label=btn_label)
        copy_btn.Bind(wx.EVT_BUTTON, lambda e: self._on_copy(address, name))
        
        # Button doesn't need EXPAND, so ALIGN_CENTER_VERTICAL works here
        input_sizer.Add(copy_btn, 0, wx.ALIGN_CENTER_VERTICAL)
        
        row_sizer.Add(input_sizer, 0, wx.EXPAND | wx.BOTTOM, 15)
        sizer.Add(row_sizer, 0, wx.EXPAND | wx.ALL, 5)

    def _on_copy(self, text, name):
        """Copies the wallet address to the system clipboard and announces it."""
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
            speak(_("{0} address copied to clipboard.").format(name), LEVEL_MINIMAL)
        else:
            speak(_("Failed to open clipboard."), LEVEL_MINIMAL)
