# frames/library/history_manager.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
import logging
from typing import List, Tuple, Optional
from database import db_manager
from i18n import _
from nvda_controller import speak, LEVEL_CRITICAL

HISTORY_LIMIT = 20


class HistoryManager:
    """
    Manages the history list data and UI population.
    Encapsulates history items to avoid global state.
    """

    def __init__(self):
        # Stores list of (book_id, title, shelf_id)
        self._items: List[Tuple[int, str, int]] = []

    def get_data_from_index(self, index: int) -> Optional[Tuple[int, str, int]]:
        """
        Safely retrieves data from the internal list based on the index.
        """
        try:
            return self._items[index]
        except IndexError:
            logging.error(f"HistoryManager: Index {index} out of range.")
            return None

    def get_virtual_item_text(self, index: int, column: int) -> str:
        """
        Callback for the Virtual ListCtrl to retrieve item text.
        """
        try:
            if 0 <= index < len(self._items):
                return self._items[index][1]
            return ""
        except Exception:
            return ""

    def populate_history_list(self, frame, shelves_data: List[Tuple[int, str, List]], index_to_select: int = -1):
        """
        Fetches the latest history from the database and repopulates the History ListCtrl.
        Maintains selection/focus if possible.
        """
        if not frame.history_list:
            return

        frame.history_list.Freeze()
        frame.history_list.SetItemCount(0)
        self._items.clear()
        items_added = 0

        try:
            # Fetch limited recent items
            history_books = db_manager.book_repo.get_history_books(limit=HISTORY_LIMIT)
            if history_books:
                for (book_id, title, shelf_id) in history_books:
                    self._items.append((book_id, title, shelf_id))
                    items_added += 1

                frame.history_list.SetItemCount(items_added)
                frame.history_list.Refresh()

        except Exception as e:
            logging.error(f"Error populating history list: {e}", exc_info=True)
            speak(_("Error loading history."), LEVEL_CRITICAL)
        finally:
            frame.history_list.Thaw()
            if items_added > 0:
                frame.history_list.SetColumnWidth(0, wx.LIST_AUTOSIZE)

        # Restore Focus/Selection
        if items_added > 0:
            target_index = 0
            if index_to_select != -1:
                target_index = index_to_select
            elif frame.last_history_focus_index != -1:
                target_index = frame.last_history_focus_index

            target_index = max(0, min(target_index, items_added - 1))

            frame.history_list.SetItemState(target_index,
                                            wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
                                            wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
            frame.last_history_focus_index = target_index

            # Only force focus if this list is the currently active control
            if frame.FindFocus() == frame.history_list:
                frame.history_list.Focus(target_index)

    def on_item_activated(self, frame, event: wx.ListEvent):
        """
        Handles the activation (Enter/Double Click) of a history item.
        Starts playback of the selected book within the context of the history list.
        """
        item_index = event.GetIndex()
        activated_book_data = self.get_data_from_index(item_index)

        if not activated_book_data:
            return

        book_id_to_play, book_title_to_play, _ = activated_book_data

        # Build playlist context from current history list
        playlist_context: List[Tuple[int, str]] = []
        for (bid, btitle, bshelf) in self._items:
            playlist_context.append((bid, btitle))

        if not playlist_context:
            speak(_("Error building history playlist."), LEVEL_CRITICAL)
            return

        current_playlist_index = -1
        for i, (book_id, title) in enumerate(playlist_context):
            if book_id == book_id_to_play:
                current_playlist_index = i
                break

        if current_playlist_index == -1:
            playlist_context.insert(0, (book_id_to_play, book_title_to_play))
            current_playlist_index = 0

        frame.start_playback(
            book_id=book_id_to_play,
            library_playlist=playlist_context,
            current_playlist_index=current_playlist_index
        )

    def on_list_selection_changed(self, frame, event: wx.ListEvent):
        """Updates the status bar when the selection in the history list changes."""
        item_index = event.GetIndex()
        frame.last_history_focus_index = item_index

        if item_index == wx.NOT_FOUND:
            frame.SetStatusText("")
            return

        selected_data = self.get_data_from_index(item_index)
        if not selected_data:
            return

        book_id, title, shelf_id = selected_data
        shelf_name = _("Unknown")

        # Try to find shelf name from frame data
        try:
            for (sid, sname, books_list) in getattr(frame, 'shelves_data', []):
                if sid == shelf_id:
                    shelf_name = sname
                    break
        except Exception:
            pass

        status_text = _("Book: {0} | In: {1}").format(title, shelf_name)
        frame.SetStatusText(status_text)
        event.Skip()

    def on_list_char_hook(self, frame, event: wx.KeyEvent):
        """
        Handles keyboard events for the History ListCtrl.
        """
        # Late import to avoid circular dependency
        from . import context_actions

        keycode = event.GetKeyCode()
        ctrl_down = event.ControlDown()

        if keycode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            focused_index = frame.history_list.GetFirstSelected()
            if focused_index != -1:
                evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_ACTIVATED)
                evt.SetIndex(focused_index)
                self.on_item_activated(frame, evt)
            return

        elif keycode == wx.WXK_SPACE:
            focused_index = frame.history_list.GetFocusedItem()
            if focused_index != -1:
                is_selected = frame.history_list.IsSelected(focused_index)
                if ctrl_down:
                    frame.history_list.Select(focused_index, not is_selected)
                elif not is_selected:
                    frame.history_list.Select(focused_index, True)
            return

        elif keycode == wx.WXK_DELETE:
            context_actions.on_context_delete_book(frame, None, source='history')
            return

        elif keycode == wx.WXK_F2:
            context_actions.on_context_rename_book(frame, None, source='history')
            return

        else:
            event.Skip()


# Singleton instance for backward compatibility
manager = HistoryManager()

# Module-level aliases
populate_history_list = manager.populate_history_list
get_virtual_item_text = manager.get_virtual_item_text
on_item_activated = manager.on_item_activated
on_list_selection_changed = manager.on_list_selection_changed
on_list_char_hook = manager.on_list_char_hook
get_data_from_index = manager.get_data_from_index
_get_book_data_by_index = manager.get_data_from_index  # Keep as alias for safety
