# dialogs/settings_dialog.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import wx
import logging
from i18n import _
from nvda_controller import speak, LEVEL_CRITICAL

from .settings import general
from .settings import playback
from .settings import accessibility
from .settings import sleeptimer
from .settings import library_view


class SettingsDialog(wx.Dialog):
    """
    The main settings dialog container.
    Holds the notebook tabs for different setting categories and delegates saving.
    """

    def __init__(self, parent):
        super(SettingsDialog, self).__init__(parent, title=_("Settings"))

        self.panel = wx.Panel(self)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook = wx.Notebook(self.panel)

        # General Tab
        self.general_panel = general.TabPanel(self.notebook)
        self.notebook.AddPage(self.general_panel, _("General"))

        # Playback Tab
        self.playback_panel = playback.TabPanel(self.notebook)
        self.notebook.AddPage(self.playback_panel, _("Playback"))

        # Sleep Timer Tab
        self.sleeptimer_panel = sleeptimer.TabPanel(self.notebook)
        self.notebook.AddPage(self.sleeptimer_panel, _("Sleep Timer"))

        # Accessibility Tab
        self.accessibility_panel = accessibility.TabPanel(self.notebook)
        self.notebook.AddPage(self.accessibility_panel, _("Accessibility"))

        # Library View Tab
        self.view_panel = library_view.TabPanel(self.notebook)
        self.notebook.AddPage(self.view_panel, _("Library View"))

        self.main_sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 10)

        button_sizer = wx.StdDialogButtonSizer()
        self.save_button = wx.Button(self.panel, wx.ID_SAVE, _("&Save"))
        self.cancel_button = wx.Button(self.panel, wx.ID_CANCEL, _("&Cancel"))
        button_sizer.AddButton(self.save_button)
        button_sizer.AddButton(self.cancel_button)
        button_sizer.Realize()

        self.main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 10)

        self.panel.SetSizer(self.main_sizer)
        self.main_sizer.Fit(self)
        self.SetMinSize(self.GetSize())
        self.CentreOnParent()

        self.SetDefaultItem(self.save_button)

        self.save_button.Bind(wx.EVT_BUTTON, self.on_save)
        self.cancel_button.Bind(wx.EVT_BUTTON, self.on_cancel)

    def on_save(self, event):
        """Delegates the save action to each tab panel and handles language restart prompts."""
        try:
            lang_before = self.general_panel.get_current_language_on_load()

            self.general_panel.save_settings()
            self.playback_panel.save_settings()
            self.accessibility_panel.save_settings()
            self.sleeptimer_panel.save_settings()
            self.view_panel.save_settings()

            speak(_("Settings saved."), LEVEL_CRITICAL)

            lang_after = self.general_panel.get_selected_language()
            if lang_after != lang_before:
                speak(_("Language change detected. Please restart the application."), LEVEL_CRITICAL)
                wx.MessageBox(
                    _("Language changes will take effect after you restart AudioShelf."),
                    _("Restart Required"),
                    wx.OK | wx.ICON_INFORMATION
                )

            self.EndModal(wx.ID_OK)

        except Exception as e:
            logging.error(f"Error saving settings: {e}", exc_info=True)
            speak(_("Error saving settings."), LEVEL_CRITICAL)
            self.EndModal(wx.ID_ABORT)

    def on_cancel(self, event):
        """Closes the dialog without saving."""
        self.EndModal(wx.ID_CANCEL)