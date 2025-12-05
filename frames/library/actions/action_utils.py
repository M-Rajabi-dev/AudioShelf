# frames/library/actions/action_utils.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import wx
import logging
from typing import List, Tuple, Optional
from i18n import _
from .. import list_manager
from .. import history_manager
from .. import search_handlers


def get_map_index(frame, source: str, item_index: int) -> int:
    """
    Resolves the correct data map index for a given list item index.
    Handles the difference between Standard ListCtrl and Virtual ListCtrl.

    Args:
        frame: The main LibraryFrame.
        source: The source list ('library', 'history', 'search').
        item_index: The visual index of the item.

    Returns:
        The internal map index, or -1 if invalid.
    """
    if item_index == -1:
        return -1

    if source == 'library':
        if frame.library_list.HasFlag(wx.LC_VIRTUAL):
            return item_index
        return frame.library_list.GetItemData(item_index)

    elif source == 'history':
        if frame.history_list.HasFlag(wx.LC_VIRTUAL):
            return item_index
        return frame.history_list.GetItemData(item_index)

    elif source == 'search':
        if frame.search_list.HasFlag(wx.LC_VIRTUAL):
            return item_index
        return frame.search_list.GetItemData(item_index)

    return -1


def get_focused_book_info(frame, source: str) -> Optional[Tuple[int, str]]:
    """
    Retrieves information for the currently focused book in the specified list.

    Args:
        frame: The main LibraryFrame.
        source: The source list identifier.

    Returns:
        A tuple (book_id, book_title) if a book is focused, otherwise None.
    """
    if source == 'library':
        focus_index = frame.last_library_focus_index
        if focus_index == -1:
            return None
        try:
            map_index = get_map_index(frame, source, focus_index)
            item_data = list_manager.get_data_from_index(map_index)
            
            if item_data:
                item_type, item_id = item_data
                if item_type == 'book':
                    if frame.library_list.HasFlag(wx.LC_VIRTUAL):
                        raw_label = list_manager.get_virtual_item_text(map_index, 0)
                    else:
                        raw_label = frame.library_list.GetItemText(focus_index)
                    
                    label = raw_label.rsplit(" [", 1)[0] if " [" in raw_label else raw_label
                    return item_id, label
        except Exception as e:
            logging.error(f"Error getting focused book info (library): {e}")

    elif source == 'history':
        focus_index = frame.last_history_focus_index
        data = history_manager.get_data_from_index(focus_index)
        if data:
            # data is (book_id, title, shelf_id)
            return data[0], data[1]

    elif source == 'search':
        focus_index = frame.last_search_focus_index
        data = search_handlers.get_data_from_index(focus_index)
        if data:
            # data is (book_id, title, shelf_id)
            return data[0], data[1]

    return None


def get_focused_shelf_info(frame) -> Optional[Tuple[int, str]]:
    """
    Retrieves information for the currently focused shelf in the library list.

    Returns:
        A tuple (shelf_id, shelf_name) if a shelf is focused, otherwise None.
    """
    focus_index = frame.last_library_focus_index
    if focus_index == -1:
        return None

    try:
        map_index = get_map_index(frame, 'library', focus_index)
        item_data = list_manager.get_data_from_index(map_index)
        
        if item_data:
            item_type, item_id = item_data
            if item_type == 'shelf':
                if frame.library_list.HasFlag(wx.LC_VIRTUAL):
                    raw_label = list_manager.get_virtual_item_text(map_index, 0)
                else:
                    raw_label = frame.library_list.GetItemText(focus_index)
                
                clean_label = raw_label.rsplit(" [", 1)[0] if " [" in raw_label else raw_label
                if " (" in clean_label and clean_label.endswith(")"):
                    clean_label = clean_label.rsplit(" (", 1)[0]
                
                return item_id, clean_label
    except Exception as e:
        logging.error(f"Error getting focused shelf info: {e}")

    return None


def get_selected_book_data_list(frame, source: str) -> List[Tuple[int, str]]:
    """
    Retrieves a list of data for all selected books in the specified list.

    Returns:
        A list of tuples (book_id, book_title).
    """
    selected_books = []
    ctrl = None

    if source == 'library':
        ctrl = frame.library_list
    elif source == 'history':
        ctrl = frame.history_list
    elif source == 'search':
        ctrl = frame.search_list
    else:
        return []

    try:
        item = ctrl.GetFirstSelected()
        while item != -1:
            book_data = None
            
            if source == 'library':
                map_index = get_map_index(frame, source, item)
                item_data = list_manager.get_data_from_index(map_index)
                
                if item_data:
                    item_type, item_id = item_data
                    if item_type == 'book':
                        if frame.library_list.HasFlag(wx.LC_VIRTUAL):
                            raw_label = list_manager.get_virtual_item_text(map_index, 0)
                        else:
                            raw_label = ctrl.GetItemText(item)
                        
                        label = raw_label.rsplit(" [", 1)[0] if " [" in raw_label else raw_label
                        book_data = (item_id, label)

            elif source == 'history':
                full_data = history_manager.get_data_from_index(item)
                if full_data:
                    book_data = (full_data[0], full_data[1])

            elif source == 'search':
                full_data = search_handlers.get_data_from_index(item)
                if full_data:
                    book_data = (full_data[0], full_data[1])

            if book_data:
                selected_books.append(book_data)
            
            item = ctrl.GetNextSelected(item)

    except Exception as e:
        logging.error(f"Error in get_selected_book_data_list for source {source}: {e}", exc_info=True)
        return []

    return selected_books


def get_selected_shelf_data_list(frame) -> List[Tuple[int, str]]:
    """
    Retrieves a list of data for all selected shelves in the library list.

    Returns:
        A list of tuples (shelf_id, shelf_name).
    """
    selected_shelves = []
    ctrl = frame.library_list

    try:
        item = ctrl.GetFirstSelected()
        while item != -1:
            map_index = get_map_index(frame, 'library', item)
            item_data = list_manager.get_data_from_index(map_index)
            
            if item_data:
                item_type, item_id = item_data
                if item_type == 'shelf':
                    if frame.library_list.HasFlag(wx.LC_VIRTUAL):
                        raw_label = list_manager.get_virtual_item_text(map_index, 0)
                    else:
                        raw_label = ctrl.GetItemText(item)
                    
                    clean_label = raw_label.rsplit(" [", 1)[0] if " [" in raw_label else raw_label
                    if " (" in clean_label and clean_label.endswith(")"):
                        clean_label = clean_label.rsplit(" (", 1)[0]
                    
                    selected_shelves.append((item_id, clean_label))
            
            item = ctrl.GetNextSelected(item)

    except Exception as e:
        logging.error(f"Error in get_selected_shelf_data_list: {e}")

    return selected_shelves


def refresh_all_views(frame):
    """
    Refreshes the library, history, and (if visible) search results lists.
    """
    list_manager.refresh_library_data(frame)
    list_manager.populate_library_list(frame)
    
    try:
        if hasattr(frame, 'update_history_list'):
            frame.update_history_list()
    except Exception:
        pass

    if frame.search_list.IsShown():
        search_handlers.refresh_search_results(frame)
