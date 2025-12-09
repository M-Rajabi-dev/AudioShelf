# frames/library_frame.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
import logging
import wx.lib.newevent
from typing import List, Tuple, Callable, Optional

import updater
from database import db_manager
from i18n import _
from nvda_controller import set_app_focus_status

from .library import (
    list_manager,
    menu_handlers,
    search_handlers,
    context_handlers,
    task_handlers,
    history_manager,
    hotkey_manager,
    context_actions
)
from . import player_frame

# Custom Events
MissingBooksResultEvent, EVT_MISSING_BOOKS_RESULT = wx.lib.newevent.NewEvent()
ScanResultEvent, EVT_SCAN_COMPLETE = wx.lib.newevent.NewEvent()
UpdateScanResultEvent, EVT_UPDATE_SCAN_COMPLETE = wx.lib.newevent.NewEvent()

# Custom IDs
ID_ADD_BOOK = wx.NewIdRef()
ID_ADD_SINGLE_FILE = wx.NewIdRef()
ID_SETTINGS = wx.NewIdRef()
ID_CREATE_SHELF = wx.NewIdRef()
ID_REFRESH_LIBRARY = wx.NewIdRef()
ID_PRUNE_MISSING = wx.NewIdRef()
ID_CLEAR_LIBRARY = wx.NewIdRef()
ID_PASTE_BOOK = wx.NewIdRef()
ID_EXPORT_DB = wx.NewIdRef()
ID_IMPORT_DB = wx.NewIdRef()
ID_OPEN_LOGS = wx.NewIdRef()
ID_USER_GUIDE = wx.NewIdRef()

ID_TREE_PLAY = wx.NewIdRef()
ID_TREE_RENAME_BOOK = wx.NewIdRef()
ID_TREE_PROPERTIES = wx.NewIdRef()
ID_TREE_OPEN_LOCATION = wx.NewIdRef()
ID_TREE_UPDATE_LOCATION = wx.NewIdRef()
ID_TREE_EXPORT_DATA = wx.NewIdRef()
ID_TREE_DELETE_BOOK = wx.NewIdRef()
ID_TREE_DELETE_COMPUTER = wx.NewIdRef()

ID_SHELF_MENU_NEW = wx.NewIdRef()
ID_TREE_RENAME_SHELF = wx.NewIdRef()
ID_TREE_DELETE_SHELF = wx.NewIdRef()

ID_TREE_PIN_BOOK = wx.NewIdRef()
ID_TREE_UNPIN_BOOK = wx.NewIdRef()
ID_MARK_FINISHED = wx.NewIdRef()
ID_MARK_UNFINISHED = wx.NewIdRef()

ID_ACCEL_SELECT_ALL = wx.NewIdRef()

ID_HELP_SHORTCUTS = wx.NewIdRef()
ID_HELP_DONATE = wx.NewIdRef()
ID_HELP_CHECK_UPDATE = wx.NewIdRef()

ID_HISTORY_LIST = wx.NewIdRef()
ID_SEARCH_LIST = wx.NewIdRef()
ID_LIBRARY_LIST = wx.NewIdRef()


class VirtualLibraryList(wx.ListCtrl):
    """
    A virtual ListCtrl wrapper that delegates item text retrieval to a callback.
    """

    def __init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.DefaultSize,
                 style=0, item_callback: Optional[Callable[[int, int], str]] = None):
        super().__init__(parent, id, pos, size, style)
        self.item_callback = item_callback

    def OnGetItemText(self, item, column):
        if self.item_callback:
            try:
                return self.item_callback(item, column)
            except Exception:
                return ""
        return ""


class LibraryFrame(wx.Frame):
    """
    The main application window for AudioShelf.
    Manages the library view, history, search, navigation, and updates.
    """

    def __init__(self, parent, title: str):
        super(LibraryFrame, self).__init__(parent, title=title, size=(800, 600))
        self.panel = wx.Panel(self)

        # Data stores
        self.shelf_menu_id_map = {}
        self.current_filter = ""
        self.shelves_data = []
        self.pinned_books = []
        self.all_books_data: List[Tuple[int, str, int]] = []
        self.finished_books: List[Tuple[int, str, int]] = []

        self.current_view_level: str | int = 'root'
        self.is_busy_processing = False

        self.last_history_focus_index = -1
        self.last_search_focus_index = -1
        self.last_library_focus_index = -1
        self.last_focused_control = None

        self.nav_stack_back: List[Tuple[str | int, int]] = []
        self.nav_stack_forward: List[Tuple[str | int, int]] = []

        self.ScanResultEvent = ScanResultEvent
        self.UpdateScanResultEvent = UpdateScanResultEvent
        self.MissingBooksResultEvent = MissingBooksResultEvent

        self._init_ui()
        self._init_updater()
        self._bind_events()
        self._init_data()

    def _init_ui(self):
        """Initializes the UI components and layout."""
        self.CreateStatusBar(1)
        self.SetStatusText(_("Welcome to AudioShelf!"))

        vbox = wx.BoxSizer(wx.VERTICAL)

        # Search Bar
        search_label = wx.StaticText(self.panel, label=_("Search:"))
        self.search_ctrl = wx.SearchCtrl(self.panel, style=wx.TE_PROCESS_ENTER)
        self.search_ctrl.SetDescriptiveText(_("Type to filter books or shelves"))
        self.search_ctrl.SetLabel(_("Search:"))

        search_sizer = wx.BoxSizer(wx.HORIZONTAL)
        search_sizer.Add(search_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        search_sizer.Add(self.search_ctrl, 1, wx.EXPAND)
        vbox.Add(search_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # Main Content (Library + History)
        main_content_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Library List
        self.library_list = VirtualLibraryList(
            self.panel,
            id=ID_LIBRARY_LIST,
            style=wx.LC_REPORT | wx.LC_NO_HEADER | wx.LC_VIRTUAL,
            item_callback=list_manager.get_virtual_item_text
        )
        self.library_list.SetLabel(_("Library"))
        self.library_list.InsertColumn(0, _("Library"), width=wx.LIST_AUTOSIZE_USEHEADER)
        main_content_sizer.Add(self.library_list, 1, wx.EXPAND | wx.RIGHT, 5)

        # History List
        self.history_list = VirtualLibraryList(
            self.panel,
            id=ID_HISTORY_LIST,
            style=wx.LC_REPORT | wx.LC_NO_HEADER | wx.LC_VIRTUAL,
            item_callback=history_manager.get_virtual_item_text
        )
        self.history_list.SetLabel(_("History"))
        self.history_list.InsertColumn(0, _("History"), width=wx.LIST_AUTOSIZE_USEHEADER)
        main_content_sizer.Add(self.history_list, 1, wx.EXPAND | wx.LEFT, 5)

        vbox.Add(main_content_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Search Results List (Hidden by default)
        self.search_list = VirtualLibraryList(
            self.panel,
            id=ID_SEARCH_LIST,
            style=wx.LC_REPORT | wx.LC_NO_HEADER | wx.LC_VIRTUAL,
            item_callback=search_handlers.get_virtual_item_text
        )
        self.search_list.SetLabel(_("Search Results"))
        self.search_list.InsertColumn(0, _("Search Results"), width=wx.LIST_AUTOSIZE_USEHEADER)
        vbox.Add(self.search_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.search_list.Hide()

        self.panel.SetSizer(vbox)
        self._create_menu_bar()

        # Accelerator Table
        accel_entries = hotkey_manager.get_accelerator_entries()
        accel_entries.append((wx.ACCEL_CTRL, ord('V'), ID_PASTE_BOOK))
        accel_entries.append((wx.ACCEL_NORMAL, wx.WXK_F1, ID_HELP_SHORTCUTS))
        self.SetAcceleratorTable(wx.AcceleratorTable(accel_entries))

        self.Centre()

    def _init_updater(self):
        """Initializes the UpdateManager and schedules a startup check."""
        self.update_manager = updater.UpdateManager(self)
        self.Bind(updater.EVT_UPDATE_RESULT, self.on_update_result)
        self.Bind(updater.EVT_DOWNLOAD_RESULT, self.on_download_result)
        wx.CallLater(3000, self._trigger_startup_update)

    def _bind_events(self):
        """Binds all event handlers."""
        hotkey_manager.bind_hotkeys(self)

        # File Menu
        self.Bind(wx.EVT_MENU, lambda event: task_handlers.on_add_book(self, event), id=ID_ADD_BOOK)
        self.Bind(wx.EVT_MENU, lambda event: task_handlers.on_add_single_file(self, event), id=ID_ADD_SINGLE_FILE)
        self.Bind(wx.EVT_MENU, lambda event: menu_handlers.on_create_shelf(self, event), id=ID_CREATE_SHELF)
        self.Bind(wx.EVT_MENU, lambda event: menu_handlers.on_refresh_library(self, event), id=ID_REFRESH_LIBRARY)
        self.Bind(wx.EVT_MENU, lambda event: menu_handlers.on_quit(self, event), id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, lambda event: menu_handlers.on_paste_book(self, event), id=ID_PASTE_BOOK)

        # Tools Menu
        self.Bind(wx.EVT_MENU, lambda event: task_handlers.on_clear_missing_books(self, event), id=ID_PRUNE_MISSING)
        self.Bind(wx.EVT_MENU, lambda event: menu_handlers.on_clear_library(self, event), id=ID_CLEAR_LIBRARY)
        self.Bind(wx.EVT_MENU, lambda event: menu_handlers.on_export_database(self, event), id=ID_EXPORT_DB)
        self.Bind(wx.EVT_MENU, lambda event: menu_handlers.on_import_database(self, event), id=ID_IMPORT_DB)
        self.Bind(wx.EVT_MENU, lambda event: menu_handlers.on_settings(self, event), id=ID_SETTINGS)

        # Help Menu
        self.Bind(wx.EVT_MENU, lambda event: menu_handlers.on_user_guide(self, event), id=ID_USER_GUIDE)
        self.Bind(wx.EVT_MENU, lambda event: menu_handlers.on_shortcuts(self, event), id=ID_HELP_SHORTCUTS)
        self.Bind(wx.EVT_MENU, lambda event: menu_handlers.on_about(self, event), id=wx.ID_ABOUT)
        self.Bind(wx.EVT_MENU, lambda event: menu_handlers.on_donate(self, event), id=ID_HELP_DONATE)
        self.Bind(wx.EVT_MENU, self.on_check_update_menu, id=ID_HELP_CHECK_UPDATE)
        self.Bind(wx.EVT_MENU, lambda event: menu_handlers.on_open_logs(self, event), id=ID_OPEN_LOGS)

        # Library List Events
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda event: list_manager.on_item_activated(self, event),
                  self.library_list)
        self.Bind(wx.EVT_CHAR_HOOK, lambda event: list_manager.on_list_char_hook(self, event), self.library_list)
        self.Bind(wx.EVT_CONTEXT_MENU,
                  lambda event: context_handlers.show_context_menu_for_list(self, event, source_type='library'),
                  self.library_list)
        self.Bind(wx.EVT_LIST_ITEM_FOCUSED, lambda event: list_manager.on_list_focus_changed(self, event),
                  self.library_list)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda event: list_manager.on_list_focus_changed(self, event),
                  self.library_list)

        # History List Events
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda event: history_manager.on_item_activated(self, event),
                  self.history_list)
        self.Bind(wx.EVT_CHAR_HOOK, lambda event: history_manager.on_list_char_hook(self, event), self.history_list)
        self.Bind(wx.EVT_CONTEXT_MENU,
                  lambda event: context_handlers.show_context_menu_for_list(self, event, source_type='history'),
                  self.history_list)
        self.Bind(wx.EVT_LIST_ITEM_FOCUSED, lambda event: history_manager.on_list_selection_changed(self, event),
                  self.history_list)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda event: history_manager.on_list_selection_changed(self, event),
                  self.history_list)

        # Search List Events
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda event: search_handlers.on_item_activated(self, event),
                  self.search_list)
        self.Bind(wx.EVT_CHAR_HOOK, lambda event: search_handlers.on_list_char_hook(self, event), self.search_list)
        self.Bind(wx.EVT_CONTEXT_MENU,
                  lambda event: context_handlers.show_context_menu_for_list(self, event, source_type='search'),
                  self.search_list)
        self.Bind(wx.EVT_LIST_ITEM_FOCUSED, lambda event: search_handlers.on_list_selection_changed(self, event),
                  self.search_list)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda event: search_handlers.on_list_selection_changed(self, event),
                  self.search_list)

        # Search Control Events
        self.search_ctrl.Bind(wx.EVT_KEY_DOWN, lambda event: search_handlers.on_search_char_hook(self, event))
        self.Bind(wx.EVT_TEXT, lambda event: search_handlers.on_search(self, event), self.search_ctrl)
        self.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, lambda event: search_handlers.on_search_cancel(self, event),
                  self.search_ctrl)
        self.Bind(wx.EVT_TEXT_ENTER, lambda event: search_handlers.on_search_enter(self, event), self.search_ctrl)

        # Context Menu Actions
        self._bind_context_actions()

        # Main Frame Events
        self.Bind(wx.EVT_CLOSE, self.on_close_window)
        self.Bind(wx.EVT_ACTIVATE, self.on_activate)

        # Custom Events
        self.Bind(EVT_MISSING_BOOKS_RESULT, lambda event: task_handlers.on_missing_books_result(self, event))
        self.Bind(EVT_SCAN_COMPLETE, lambda event: task_handlers.on_scan_complete(self, event))
        self.Bind(EVT_UPDATE_SCAN_COMPLETE, lambda event: task_handlers.on_scan_update_complete(self, event))

    def _bind_context_actions(self):
        """Helper to bind context menu actions."""
        self.Bind(wx.EVT_MENU, lambda event: context_actions.on_context_play(self, event, source=context_handlers.get_source_from_focus(self)), id=ID_TREE_PLAY)
        self.Bind(wx.EVT_MENU, lambda event: context_actions.on_context_rename_book(self, event, source=context_handlers.get_source_from_focus(self)), id=ID_TREE_RENAME_BOOK)
        self.Bind(wx.EVT_MENU, lambda event: context_actions.on_context_properties(self, event, source=context_handlers.get_source_from_focus(self)), id=ID_TREE_PROPERTIES)
        self.Bind(wx.EVT_MENU, lambda event: context_actions.on_context_open_location(self, event, source=context_handlers.get_source_from_focus(self)), id=ID_TREE_OPEN_LOCATION)
        self.Bind(wx.EVT_MENU, lambda event: context_actions.on_context_update_location(self, event, source=context_handlers.get_source_from_focus(self)), id=ID_TREE_UPDATE_LOCATION)
        self.Bind(wx.EVT_MENU, lambda event: context_actions.on_context_export_data(self, event, source=context_handlers.get_source_from_focus(self)), id=ID_TREE_EXPORT_DATA)
        self.Bind(wx.EVT_MENU, lambda event: context_actions.on_context_delete_book(self, event, source=context_handlers.get_source_from_focus(self)), id=ID_TREE_DELETE_BOOK)
        self.Bind(wx.EVT_MENU, lambda event: context_actions.on_context_delete_computer(self, event, source=context_handlers.get_source_from_focus(self)), id=ID_TREE_DELETE_COMPUTER)
        self.Bind(wx.EVT_MENU, lambda event: context_actions.on_context_move_to_new_shelf(self, event, source='library'), id=ID_SHELF_MENU_NEW)
        self.Bind(wx.EVT_MENU, lambda event: context_actions.on_context_rename_shelf(self, event, source='library'), id=ID_TREE_RENAME_SHELF)
        self.Bind(wx.EVT_MENU, lambda event: context_actions.on_context_delete_shelf(self, event, source='library'), id=ID_TREE_DELETE_SHELF)
        self.Bind(wx.EVT_MENU, lambda event: context_actions.on_context_pin_book(self, event, source=context_handlers.get_source_from_focus(self)), id=ID_TREE_PIN_BOOK)
        self.Bind(wx.EVT_MENU, lambda event: context_actions.on_context_unpin_book(self, event, source=context_handlers.get_source_from_focus(self)), id=ID_TREE_UNPIN_BOOK)
        self.Bind(wx.EVT_MENU, lambda event: context_actions.on_context_mark_finished(self, event, source=context_handlers.get_source_from_focus(self)), id=ID_MARK_FINISHED)
        self.Bind(wx.EVT_MENU, lambda event: context_actions.on_context_mark_unfinished(self, event, source=context_handlers.get_source_from_focus(self)), id=ID_MARK_UNFINISHED)

    def _init_data(self):
        """Populates the lists with initial data."""
        list_manager.refresh_library_data(self)
        list_manager.populate_library_list(self)
        self.update_history_list()
        self.library_list.SetFocus()
        self.last_focused_control = self.library_list

    def update_history_list(self):
        """Refreshes the history list UI."""
        history_manager.populate_history_list(self, self.shelves_data)

    def _create_menu_bar(self):
        """Creates the application menu bar."""
        menu_bar = wx.MenuBar()

        # File Menu
        file_menu = wx.Menu()
        add_item = wx.MenuItem(file_menu, ID_ADD_BOOK, _("&Add Book Folder...\tCtrl+O"))
        file_menu.Append(add_item)
        add_single_item = wx.MenuItem(file_menu, ID_ADD_SINGLE_FILE, _("Add Single &File...\tCtrl+Shift+O"))
        file_menu.Append(add_single_item)
        create_shelf_item = wx.MenuItem(file_menu, ID_CREATE_SHELF, _("Create &New Shelf...\tCtrl+N"))
        file_menu.Append(create_shelf_item)
        refresh_item = wx.MenuItem(file_menu, ID_REFRESH_LIBRARY, _("&Refresh Library\tF5"))
        file_menu.Append(refresh_item)
        file_menu.AppendSeparator()
        exit_item = wx.MenuItem(file_menu, wx.ID_EXIT, _("&Exit\tAlt+F4"))
        file_menu.Append(exit_item)
        menu_bar.Append(file_menu, _("&File"))

        # Tools Menu
        tools_menu = wx.Menu()
        self.prune_menu_item = wx.MenuItem(tools_menu, ID_PRUNE_MISSING, _("Clear Missing Books..."))
        tools_menu.Append(self.prune_menu_item)
        
        clear_lib_item = wx.MenuItem(tools_menu, ID_CLEAR_LIBRARY, _("Clear Library..."))
        tools_menu.Append(clear_lib_item)
        
        tools_menu.AppendSeparator()
        
        export_db_item = wx.MenuItem(tools_menu, ID_EXPORT_DB, _("&Backup Database..."))
        tools_menu.Append(export_db_item)
        
        import_db_item = wx.MenuItem(tools_menu, ID_IMPORT_DB, _("&Import Database..."))
        tools_menu.Append(import_db_item)
        
        tools_menu.AppendSeparator()
        
        settings_item = wx.MenuItem(tools_menu, ID_SETTINGS, _("&Settings..."))
        tools_menu.Append(settings_item)
        menu_bar.Append(tools_menu, _("&Tools"))

        # Help Menu
        help_menu = wx.Menu()
        guide_item = wx.MenuItem(help_menu, ID_USER_GUIDE, _("&User Guide...\tShift+F1"))
        help_menu.Append(guide_item)
        shortcuts_item = wx.MenuItem(help_menu, ID_HELP_SHORTCUTS, _("&Keyboard Shortcuts...\tF1"))
        help_menu.Append(shortcuts_item)
        donate_item = wx.MenuItem(help_menu, ID_HELP_DONATE, _("&Donate..."))
        help_menu.Append(donate_item)
        help_menu.AppendSeparator()
        check_update_item = wx.MenuItem(help_menu, ID_HELP_CHECK_UPDATE, _("Check for &Updates..."))
        help_menu.Append(check_update_item)
        help_menu.AppendSeparator()
        logs_item = wx.MenuItem(help_menu, ID_OPEN_LOGS, _("Open &Logs Folder"))
        help_menu.Append(logs_item)
        help_menu.AppendSeparator()
        about_item = wx.MenuItem(help_menu, wx.ID_ABOUT, _("&About AudioShelf..."))
        help_menu.Append(about_item)
        menu_bar.Append(help_menu, _("&Help"))

        self.SetMenuBar(menu_bar)

    def start_playback(self, book_id: int, library_playlist: List[Tuple[int, str]], current_playlist_index: int):
        """
        Initiates playback for a specific book.
        Handles opening the player window and passing the context.
        """
        if not library_playlist or current_playlist_index == -1:
            logging.error("start_playback: Invalid playlist.")
            wx.MessageBox(_("Error starting playback."), _("Error"), wx.OK | wx.ICON_ERROR, parent=self)
            return

        logging.info(f"Starting playback for book_id: {book_id}")
        self.last_focused_control = wx.Window.FindFocus()
        if not self.last_focused_control:
            self.last_focused_control = self.library_list

        try:
            if hasattr(self, 'player') and self.player:
                try:
                    if not self.player.IsBeingDeleted():
                        self.player.Destroy()
                except Exception as e:
                    logging.warning(f"Ignoring error destroying previous player: {e}")
                self.player = None

            self.player = player_frame.PlayerFrame(
                parent=self,
                book_id=book_id,
                library_playlist=library_playlist,
                current_playlist_index=current_playlist_index
            )
            self.player.Show()
            self.Hide()
            self.player.start_playback()

        except Exception as e:
            logging.critical(f"Could not create PlayerFrame: {e}", exc_info=True)
            wx.MessageBox(_("Error opening player."), _("Player Error"), wx.OK | wx.ICON_ERROR, parent=self)
            self.Show()

    def on_activate(self, event: wx.ActivateEvent):
        """Handles window activation to manage focus state for NVDA."""
        if event.GetActive():
            wx.CallAfter(set_app_focus_status, True)
        event.Skip()

    def on_close_window(self, event):
        """Handles the application shutdown process."""
        logging.info("LibraryFrame.on_close_window: Starting shutdown process.")
        set_app_focus_status(False)
        try:
            if hasattr(self, 'library_list') and self.library_list and not self.library_list.IsBeingDeleted():
                self.library_list.Unbind(wx.EVT_LIST_ITEM_SELECTED)
            if hasattr(self, 'history_list') and self.history_list and not self.history_list.IsBeingDeleted():
                self.history_list.Unbind(wx.EVT_LIST_ITEM_SELECTED)
            if hasattr(self, 'search_list') and self.search_list and not self.search_list.IsBeingDeleted():
                self.search_list.Unbind(wx.EVT_LIST_ITEM_SELECTED)
        except Exception:
            pass
        event.Skip()

    # --- Update Handlers ---

    def on_check_update_menu(self, event):
        """Manually triggered update check from menu."""
        self.update_manager.check_for_updates(silent_if_up_to_date=False)

    def _trigger_startup_update(self):
        """Automatically triggers update check based on user settings."""
        check_updates = db_manager.get_setting('check_updates_on_startup')
        if check_updates == 'True' or check_updates is None:
            self.update_manager.check_for_updates(silent_if_up_to_date=True)
        else:
            logging.info("Startup update check disabled by user setting.")

    def on_update_result(self, event):
        """Handles the result of the update check."""
        if event.success and event.has_update:
            msg = _("A new version ({0}) is available.\nDo you want to download and install it now?").format(
                event.latest_version)
            if wx.MessageBox(msg, _("Update Available"), wx.YES_NO | wx.CANCEL | wx.ICON_INFORMATION, parent=self) == wx.YES:
                self.update_manager.download_and_install(event.download_url)
        elif not event.success and not event.silent:
            wx.MessageBox(_("Update check failed.\nError: {0}").format(event.error_msg), _("Error"),
                          wx.OK | wx.ICON_ERROR, parent=self)
        elif not event.has_update and not event.silent:
            wx.MessageBox(_("You are using the latest version."), _("No Update"), wx.OK | wx.ICON_INFORMATION,
                          parent=self)

    def on_download_result(self, event):
        """Handles the result of the installer download."""
        if event.success:
            self.update_manager.apply_update(event.path)
        else:
            wx.MessageBox(_("Download failed.\nError: {0}").format(event.error_msg), _("Error"), wx.OK | wx.ICON_ERROR,
                          parent=self)
