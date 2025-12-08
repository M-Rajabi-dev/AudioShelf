# frames/library/hotkey_manager.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
import logging
from i18n import _
from nvda_controller import speak, LEVEL_CRITICAL, LEVEL_MINIMAL, cycle_verbosity
from database import db_manager
from . import (
    menu_handlers,
    task_handlers,
    list_manager,
    context_handlers,
    search_handlers
)

# Import IDs safely
try:
    from ..library_frame import (
        ID_ACCEL_SELECT_ALL, ID_ADD_BOOK, ID_ACCEL_NEW_SHELF, ID_ACCEL_REFRESH,
        ID_ADD_SINGLE_FILE
    )
except ImportError:
    ID_ACCEL_SELECT_ALL = wx.NewIdRef()
    ID_ADD_BOOK = wx.ID_OPEN
    ID_ADD_SINGLE_FILE = wx.NewIdRef()
    ID_ACCEL_NEW_SHELF = wx.ID_NEW
    ID_ACCEL_REFRESH = wx.ID_REFRESH

# ID Definitions
ID_ACCEL_FOCUS_SEARCH = wx.NewIdRef()
ID_ACCEL_PLAY_LAST = wx.NewIdRef()
ID_ACCEL_TOGGLE_PIN = wx.NewIdRef()
ID_ACCEL_FOCUS_LIBRARY = wx.NewIdRef()
ID_ACCEL_FOCUS_HISTORY = wx.NewIdRef()
ID_ACCEL_OPEN_SETTINGS = wx.NewIdRef()
ID_ACCEL_CYCLE_VERBOSITY = wx.NewIdRef()
ID_ACCEL_JUMP_ALL_BOOKS = wx.NewIdRef()
ID_ACCEL_JUMP_DEFAULT_SHELF = wx.NewIdRef()
ID_ACCEL_JUMP_PINNED = wx.NewIdRef()
ID_ACCEL_JUMP_FINISHED = wx.NewIdRef()

ID_ACCEL_SHELF_JUMPS = [wx.NewIdRef() for _ in range(7)]
ID_ACCEL_PLAY_PINNED_IDS = [wx.NewIdRef() for _ in range(9)]


def get_accelerator_entries() -> list:
    accel_entries = [
        (wx.ACCEL_CTRL, ord('F'), ID_ACCEL_FOCUS_SEARCH),
        (wx.ACCEL_CTRL, ord('L'), ID_ACCEL_PLAY_LAST),
        (wx.ACCEL_CTRL, ord('P'), ID_ACCEL_TOGGLE_PIN),
        (wx.ACCEL_CTRL, ord('B'), ID_ACCEL_FOCUS_LIBRARY),
        (wx.ACCEL_CTRL, ord('H'), ID_ACCEL_FOCUS_HISTORY),
        (wx.ACCEL_CTRL, ord('O'), ID_ADD_BOOK),
        (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('O'), ID_ADD_SINGLE_FILE),
        (wx.ACCEL_CTRL, ord('N'), ID_ACCEL_NEW_SHELF),
        (wx.ACCEL_NORMAL, wx.WXK_F5, ID_ACCEL_REFRESH),
        (wx.ACCEL_CTRL, ord('A'), ID_ACCEL_SELECT_ALL),
        (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('S'), ID_ACCEL_OPEN_SETTINGS),
        (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('V'), ID_ACCEL_CYCLE_VERBOSITY),
        (wx.ACCEL_ALT, ord('0'), ID_ACCEL_JUMP_ALL_BOOKS),
        (wx.ACCEL_ALT, ord('1'), ID_ACCEL_JUMP_DEFAULT_SHELF),
        (wx.ACCEL_ALT, ord('P'), ID_ACCEL_JUMP_PINNED),
        (wx.ACCEL_ALT, ord('9'), ID_ACCEL_JUMP_FINISHED),
    ]

    for i, hk_id in enumerate(ID_ACCEL_SHELF_JUMPS):
        key_num = i + 2
        accel_entries.append((wx.ACCEL_ALT, ord(str(key_num)), hk_id))

    for i, hk_id in enumerate(ID_ACCEL_PLAY_PINNED_IDS):
        key = ord(str(i + 1))
        accel_entries.append((wx.ACCEL_CTRL, key, hk_id))

    return accel_entries


def bind_hotkeys(frame):
    frame.Bind(wx.EVT_MENU, lambda event: on_focus_search(frame, event), id=ID_ACCEL_FOCUS_SEARCH)
    frame.Bind(wx.EVT_MENU, lambda event: on_play_last_book(frame, event), id=ID_ACCEL_PLAY_LAST)
    frame.Bind(wx.EVT_MENU, lambda event: on_toggle_pin(frame, event), id=ID_ACCEL_TOGGLE_PIN)
    frame.Bind(wx.EVT_MENU, lambda event: on_focus_library(frame, event), id=ID_ACCEL_FOCUS_LIBRARY)
    frame.Bind(wx.EVT_MENU, lambda event: on_focus_history(frame, event), id=ID_ACCEL_FOCUS_HISTORY)
    
    frame.Bind(wx.EVT_MENU, lambda event: task_handlers.on_add_book(frame, event), id=ID_ADD_BOOK)
    frame.Bind(wx.EVT_MENU, lambda event: task_handlers.on_add_single_file(frame, event), id=ID_ADD_SINGLE_FILE)
    frame.Bind(wx.EVT_MENU, lambda event: menu_handlers.on_create_shelf(frame, event), id=ID_ACCEL_NEW_SHELF)
    frame.Bind(wx.EVT_MENU, lambda event: menu_handlers.on_refresh_library(frame, event), id=ID_ACCEL_REFRESH)
    
    frame.Bind(wx.EVT_MENU, lambda event: list_manager.on_select_all(frame, event), id=ID_ACCEL_SELECT_ALL)
    frame.Bind(wx.EVT_MENU, lambda event: menu_handlers.on_settings(frame, event), id=ID_ACCEL_OPEN_SETTINGS)
    frame.Bind(wx.EVT_MENU, lambda event: on_cycle_verbosity(frame, event), id=ID_ACCEL_CYCLE_VERBOSITY)
    
    frame.Bind(wx.EVT_MENU, lambda event: list_manager.jump_to_all_books(frame), id=ID_ACCEL_JUMP_ALL_BOOKS)
    frame.Bind(wx.EVT_MENU, lambda event: on_jump_to_default_shelf(frame, event), id=ID_ACCEL_JUMP_DEFAULT_SHELF)
    frame.Bind(wx.EVT_MENU, lambda event: on_jump_to_pinned(frame, event), id=ID_ACCEL_JUMP_PINNED)
    frame.Bind(wx.EVT_MENU, lambda event: on_jump_to_finished(frame, event), id=ID_ACCEL_JUMP_FINISHED)

    for i, hk_id in enumerate(ID_ACCEL_SHELF_JUMPS):
        target_shelf_index = i + 1
        frame.Bind(wx.EVT_MENU, lambda event, idx=target_shelf_index: list_manager.jump_to_shelf_by_index(frame, idx), id=hk_id)

    for i, hk_id in enumerate(ID_ACCEL_PLAY_PINNED_IDS):
        frame.Bind(wx.EVT_MENU, lambda event, idx=i: on_play_pinned_book(frame, idx), id=hk_id)


def on_focus_search(frame, event):
    frame.search_ctrl.SetFocus()


def on_focus_library(frame, event):
    if frame.search_list.IsShown():
        search_handlers.on_search_cancel(frame, None)
    frame.library_list.SetFocus()


def on_focus_history(frame, event):
    if frame.search_list.IsShown():
        search_handlers.on_search_cancel(frame, None)
    frame.history_list.SetFocus()


def on_play_last_book(frame, event):
    last_book_data = db_manager.book_repo.get_reading_desk_book()
    if not last_book_data:
        speak(_("No playback history found."), LEVEL_MINIMAL)
        return

    book_id, book_title, shelf_id = last_book_data
    playlist_context = [(book_id, book_title)]
    current_playlist_index = 0

    speak(_("Playing last book: {0}").format(book_title), LEVEL_MINIMAL)
    frame.start_playback(book_id, playlist_context, current_playlist_index)


def on_toggle_pin(frame, event):
    source = context_handlers.get_source_from_focus(frame)
    if not source:
        return

    from .actions import action_utils
    focused_info = action_utils.get_focused_book_info(frame, source)
    
    if not focused_info:
        speak(_("Please select a book to pin or unpin."), LEVEL_MINIMAL)
        return

    focused_id, focused_title = focused_info
    selected_books = action_utils.get_selected_book_data_list(frame, source)
    
    if not selected_books:
        selected_books = [focused_info]

    should_pin = True
    try:
        details = db_manager.book_repo.get_book_details(focused_id)
        if details and details.get('is_pinned', False):
            should_pin = False
    except Exception as e:
        logging.error(f"Error checking pin state: {e}")
        return

    count = len(selected_books)
    success_count = 0

    try:
        for book_id, book_title in selected_books:
            try:
                if should_pin:
                    db_manager.book_repo.pin_book(book_id)
                else:
                    db_manager.book_repo.unpin_book(book_id)
                success_count += 1
            except Exception:
                pass

        action_str = _("pinned") if should_pin else _("unpinned")
        if count == 1:
            speak(_("{0} {1}.").format(focused_title, action_str), LEVEL_CRITICAL)
        else:
            speak(_("{0} books {1}.").format(success_count, action_str), LEVEL_CRITICAL)

        action_utils.refresh_all_views(frame)

    except Exception as e:
        logging.error(f"Error in bulk pin toggle: {e}", exc_info=True)
        speak(_("Error changing pin state."), LEVEL_CRITICAL)


def on_cycle_verbosity(frame, event):
    cycle_verbosity()


def on_play_pinned_book(frame, index: int):
    pinned_books = db_manager.book_repo.get_pinned_books()
    
    if index < 0 or index >= len(pinned_books):
        speak(_("No pinned book at position {0}.").format(index + 1), LEVEL_MINIMAL)
        return

    book_id, book_title, shelf_id = pinned_books[index]
    playlist_context = [(b[0], b[1]) for b in pinned_books]
    current_playlist_index = index

    speak(_("Playing pinned book: {0}").format(book_title), LEVEL_MINIMAL)
    frame.start_playback(book_id, playlist_context, current_playlist_index)


def on_jump_to_default_shelf(frame, event):
    list_manager.jump_to_shelf_by_index(frame, 0)


def on_jump_to_pinned(frame, event):
    if frame.search_list.IsShown():
        search_handlers.on_search_cancel(frame, None)

    if frame.current_view_level == 'virtual_pinned':
        speak(_("Already in Pinned Books"), LEVEL_MINIMAL)
        return

    if frame.current_view_level == 'root':
        frame.nav_stack_back.append(('root', frame.last_library_focus_index))
        frame.nav_stack_forward.clear()

    frame.current_view_level = 'virtual_pinned'
    frame.current_filter = ""
    frame.search_ctrl.SetValue("")
    list_manager.populate_library_list(frame, index_to_select=0)
    frame.library_list.SetFocus()
    speak(_("Pinned Books"), LEVEL_MINIMAL)


def on_jump_to_finished(frame, event):
    if frame.search_list.IsShown():
        search_handlers.on_search_cancel(frame, None)

    if frame.current_view_level == 'virtual_finished':
        speak(_("Already in Finished Books"), LEVEL_MINIMAL)
        return

    if frame.current_view_level == 'root':
        frame.nav_stack_back.append(('root', frame.last_library_focus_index))
        frame.nav_stack_forward.clear()

    frame.current_view_level = 'virtual_finished'
    frame.current_filter = ""
    frame.search_ctrl.SetValue("")
    list_manager.populate_library_list(frame, index_to_select=0)
    frame.library_list.SetFocus()
    speak(_("Finished Books"), LEVEL_MINIMAL)
