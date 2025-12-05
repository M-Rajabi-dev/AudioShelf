# frames/library/context_handlers.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import wx
from typing import Any
from database import db_manager
from i18n import _
from . import list_manager
from . import history_manager
from . import search_handlers


def get_source_from_focus(frame) -> str:
    """
    Determines the active list control based on the current window focus.
    """
    focused_window = frame.FindFocus()
    if focused_window == frame.library_list:
        return 'library'
    elif focused_window == frame.history_list:
        return 'history'
    elif focused_window == frame.search_list:
        return 'search'
    return 'library'


def show_context_menu_for_list(frame, event, source_type: str):
    """
    Displays the context menu for a specific list control.
    """
    ctrl = event.GetEventObject()
    pos = event.GetPosition()
    item_index = -1
    focus_attr = ''

    if source_type == 'library':
        focus_attr = 'last_library_focus_index'
    elif source_type == 'history':
        focus_attr = 'last_history_focus_index'
    elif source_type == 'search':
        focus_attr = 'last_search_focus_index'
    else:
        return

    if pos == wx.DefaultPosition or pos == wx.Point(-1, -1):
        item_index = getattr(frame, focus_attr, -1)
    else:
        client_pos = ctrl.ScreenToClient(pos)
        item_index, flags = ctrl.HitTest(client_pos)

    selected_count = ctrl.GetSelectedItemCount()

    if item_index == wx.NOT_FOUND:
        _build_view_menu(frame, selected_count=0)
        return

    item_data = None
    if source_type == 'library':
        try:
            if ctrl.HasFlag(wx.LC_VIRTUAL):
                map_index = item_index
            else:
                map_index = ctrl.GetItemData(item_index)
            item_data = list_manager.get_data_from_index(map_index)
        except Exception:
            pass

    elif source_type == 'history':
        data = history_manager.get_data_from_index(item_index)
        if data:
            item_data = ('book', data[0])

    elif source_type == 'search':
        data = search_handlers.get_data_from_index(item_index)
        if data:
            item_data = ('book', data[0])

    if not item_data:
        return

    if not ctrl.IsSelected(item_index):
        sel = ctrl.GetFirstSelected()
        while sel != -1:
            ctrl.Select(sel, False)
            sel = ctrl.GetNextSelected(sel)
        ctrl.Select(item_index, True)
        selected_count = 1

    ctrl.SetFocus()
    setattr(frame, focus_attr, item_index)

    item_type, item_id = item_data
    if item_type == 'book':
        _build_book_menu(frame, item_id, source_type, selected_count=selected_count)
    elif item_type in ('shelf', 'virtual_shelf'):
        _build_shelf_menu(frame, item_id, source_type, selected_count=selected_count)


def _build_book_menu(frame, book_id: int, source: str, selected_count: int):
    """Constructs the context menu for a book item."""
    from .. import library_frame as lf

    book_details = db_manager.book_repo.get_book_details(book_id)
    is_pinned = False
    is_finished = False
    
    if book_details:
        is_pinned = book_details.get('is_pinned', False)
        is_finished = book_details.get('is_finished', False)

    is_single_selection = (selected_count <= 1)
    menu = wx.Menu()

    play_item = wx.MenuItem(menu, lf.ID_TREE_PLAY, _("&Play Book"))
    try:
        play_item.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_EXECUTABLE_FILE, wx.ART_MENU))
    except Exception:
        pass
    menu.Append(play_item)

    if is_pinned:
        unpin_item = wx.MenuItem(menu, lf.ID_TREE_UNPIN_BOOK, _("&Unpin Book"))
        menu.Append(unpin_item)
    else:
        pin_item = wx.MenuItem(menu, lf.ID_TREE_PIN_BOOK, _("&Pin Book"))
        menu.Append(pin_item)

    menu.AppendSeparator()

    if is_finished:
        mark_unfin = wx.MenuItem(menu, lf.ID_MARK_UNFINISHED, _("Mark as &Unfinished"))
        menu.Append(mark_unfin)
    else:
        mark_fin = wx.MenuItem(menu, lf.ID_MARK_FINISHED, _("Mark as &Finished"))
        menu.Append(mark_fin)

    menu.AppendSeparator()

    rename_item = wx.MenuItem(menu, lf.ID_TREE_RENAME_BOOK, _("&Rename Book..."))
    rename_item.Enable(is_single_selection)
    menu.Append(rename_item)

    props_item = wx.MenuItem(menu, lf.ID_TREE_PROPERTIES, _("Properties..."))
    props_item.Enable(is_single_selection)
    menu.Append(props_item)

    if source == 'library' and frame.current_view_level == 'root' and not is_pinned:
        move_menu = wx.Menu()
        frame.shelf_menu_id_map.clear()
        
        for (shelf_id, shelf_name, _ignored) in frame.shelves_data:
            shelf_menu_id = wx.NewIdRef()
            move_shelf_item = wx.MenuItem(move_menu, shelf_menu_id, shelf_name)
            move_menu.Append(move_shelf_item)

            from . import context_actions
            frame.Bind(wx.EVT_MENU,
                       lambda event, sid=shelf_menu_id: context_actions.on_context_move_to_shelf(
                           frame, event, sid, source=source),
                       id=shelf_menu_id)
            frame.shelf_menu_id_map[shelf_menu_id.GetId()] = shelf_id

        move_menu.AppendSeparator()
        new_shelf_item = wx.MenuItem(move_menu, lf.ID_SHELF_MENU_NEW, _("Create New Shelf..."))
        move_menu.Append(new_shelf_item)
        menu.AppendSubMenu(move_menu, _("&Move to Shelf"))

    menu.AppendSeparator()

    open_loc = wx.MenuItem(menu, lf.ID_TREE_OPEN_LOCATION, _("Open Book Location"))
    open_loc.Enable(is_single_selection)
    menu.Append(open_loc)

    update_loc = wx.MenuItem(menu, lf.ID_TREE_UPDATE_LOCATION, _("Update Book Location..."))
    update_loc.Enable(is_single_selection)
    menu.Append(update_loc)

    export_item = wx.MenuItem(menu, lf.ID_TREE_EXPORT_DATA, _("Save Data to Source..."))
    export_item.Enable(is_single_selection)
    menu.Append(export_item)

    menu.AppendSeparator()

    del_lib = wx.MenuItem(menu, lf.ID_TREE_DELETE_BOOK, _("&Delete from Library"))
    menu.Append(del_lib)
    del_comp = wx.MenuItem(menu, lf.ID_TREE_DELETE_COMPUTER, _("Delete from Computer (Permanent)..."))
    menu.Append(del_comp)

    frame.PopupMenu(menu)
    menu.Destroy()


def _build_shelf_menu(frame, shelf_id: Any, source: str, selected_count: int):
    """Constructs the context menu for a shelf item."""
    if source != 'library':
        return

    from .. import library_frame as lf
    menu = wx.Menu()

    if isinstance(shelf_id, int) and shelf_id != 1:
        is_single_selection = (selected_count <= 1)
        rename_shelf = wx.MenuItem(menu, lf.ID_TREE_RENAME_SHELF, _("&Rename Shelf..."))
        rename_shelf.Enable(is_single_selection)
        menu.Append(rename_shelf)

        del_shelf = wx.MenuItem(menu, lf.ID_TREE_DELETE_SHELF, _("&Delete Empty Shelf"))
        menu.Append(del_shelf)

    _add_common_view_items(frame, menu)

    if menu.GetMenuItemCount() > 0:
        frame.PopupMenu(menu)
    menu.Destroy()


def _build_view_menu(frame, selected_count: int):
    """Constructs the default view menu."""
    menu = wx.Menu()
    _add_common_view_items(frame, menu)
    frame.PopupMenu(menu)
    menu.Destroy()


def _add_common_view_items(frame, menu: wx.Menu):
    """Helper to add standard view items."""
    from .. import library_frame as lf

    if menu.GetMenuItemCount() > 0:
        menu.AppendSeparator()

    add_item = wx.MenuItem(menu, lf.ID_ADD_BOOK, _("&Add Book..."))
    menu.Append(add_item)

    refresh_item = wx.MenuItem(menu, lf.ID_REFRESH_LIBRARY, _("&Refresh"))
    menu.Append(refresh_item)
