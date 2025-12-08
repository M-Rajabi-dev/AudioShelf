# frames/library/search_handlers.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
import logging
import threading
import wx.lib.newevent
from typing import List, Tuple, Optional
from database import db_manager
from i18n import _
from nvda_controller import speak, LEVEL_MINIMAL, LEVEL_CRITICAL

SEARCH_DEBOUNCE_MS = 350
SearchResultEvent, EVT_SEARCH_RESULT = wx.lib.newevent.NewEvent()


class SearchManager:
    """
    Manages search functionality, including UI updates, background queries,
    and result storage.
    """

    def __init__(self):
        # Stores list of (book_id, title, shelf_id)
        self._items: List[Tuple[int, str, int]] = []
        self._search_timer: Optional[wx.Timer] = None
        self._search_generation: int = 0

    def get_data_from_index(self, index: int) -> Optional[Tuple[int, str, int]]:
        """Safely retrieves result data from the internal list."""
        try:
            return self._items[index]
        except IndexError:
            logging.error(f"SearchManager: Index {index} out of range.")
            return None

    def get_virtual_item_text(self, index: int, column: int) -> str:
        """Callback for Virtual ListCtrl."""
        try:
            if 0 <= index < len(self._items):
                return self._items[index][1]
            return ""
        except Exception:
            return ""

    def on_search(self, frame, event: wx.CommandEvent):
        """Handles text changes with debounce."""
        if self._search_timer:
            self._search_timer.Stop()

        self._search_timer = wx.Timer(frame)
        frame.Bind(wx.EVT_TIMER, lambda e: self._initiate_search(frame, index_to_select=0), self._search_timer)
        self._search_timer.StartOnce(SEARCH_DEBOUNCE_MS)
        event.Skip()

    def refresh_search_results(self, frame):
        """Re-runs the current search query."""
        if not frame.search_list.IsShown() or not frame.current_filter:
            return

        target_index = getattr(frame, 'last_search_focus_index', 0)
        if target_index == -1:
            target_index = 0
        self._initiate_search(frame, index_to_select=target_index)

    def _initiate_search(self, frame, index_to_select: int = 0):
        """Prepares and starts the background search thread."""
        self._search_timer = None
        term = frame.search_ctrl.GetValue()
        frame.current_filter = term

        if not term:
            self.on_search_cancel(frame, None)
            return

        if not hasattr(frame, '_is_search_event_bound'):
            frame.Bind(EVT_SEARCH_RESULT, self._on_search_result_ready)
            frame._is_search_event_bound = True

        self._search_generation += 1
        current_gen = self._search_generation

        if index_to_select == 0:
            speak(_("Searching..."), LEVEL_MINIMAL)

        thread = threading.Thread(
            target=self._search_worker,
            args=(frame, term, current_gen, index_to_select),
            daemon=True
        )
        thread.start()

    def _search_worker(self, frame, term: str, generation: int, index_to_select: int):
        """Background worker to execute the DB query."""
        try:
            results = db_manager.book_repo.search_books(term)
            wx.PostEvent(frame, SearchResultEvent(
                frame_ref=frame,
                results=results,
                generation=generation,
                index_to_select=index_to_select,
                term=term
            ))
        except Exception as e:
            logging.error(f"Search worker failed: {e}", exc_info=True)
            wx.PostEvent(frame, SearchResultEvent(
                frame_ref=frame,
                results=[],
                generation=generation,
                index_to_select=0,
                term=term,
                error=str(e)
            ))

    def _on_search_result_ready(self, event):
        """Handles the search results on the main UI thread."""
        frame = getattr(event, 'frame_ref', None) or event.GetEventObject()
        if not frame:
            return

        if event.generation != self._search_generation:
            return

        if hasattr(event, 'error'):
            speak(_("Error during search."), LEVEL_CRITICAL)
            return

        search_results = event.results
        target_index = event.index_to_select

        try:
            if not frame.search_list.IsShown():
                frame.library_list.Hide()
                frame.history_list.Hide()
                frame.search_list.Show()
                frame.panel.Layout()

            frame.search_list.Freeze()
            frame.search_list.SetItemCount(0)
            self._items.clear()
            items_added = 0

            if not search_results:
                speak(_("No books found."), LEVEL_MINIMAL)
            else:
                for (book_id, title, shelf_id) in search_results:
                    self._items.append((book_id, title, shelf_id))
                    items_added += 1

                frame.search_list.SetItemCount(items_added)
                frame.search_list.Refresh()

                if target_index == 0:
                    speak(_("{0} books found.").format(items_added), LEVEL_MINIMAL)

            if items_added > 0:
                target_index = max(0, min(target_index, items_added - 1))
                frame.search_list.SetItemState(target_index,
                                               wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
                                               wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
                frame.last_search_focus_index = target_index

        except Exception as e:
            logging.error(f"Error updating search UI: {e}", exc_info=True)
        finally:
            frame.search_list.Thaw()
            if items_added > 0:
                frame.search_list.SetColumnWidth(0, wx.LIST_AUTOSIZE)

    def on_search_cancel(self, frame, event):
        """Cancels search, clears text, and restores library view."""
        if self._search_timer:
            self._search_timer.Stop()
        self._search_timer = None

        frame.current_filter = ""
        frame.search_ctrl.ChangeValue("")

        if frame.search_list.IsShown():
            frame.search_list.Hide()
            frame.search_list.SetItemCount(0)
            self._items.clear()
            frame.library_list.Show()
            frame.history_list.Show()
            frame.panel.Layout()

            # Re-populate library list via alias (assuming manager pattern in list_manager)
            from . import list_manager
            list_manager.populate_library_list(frame)

        frame.library_list.SetFocus()
        if event:
            event.Skip()

    def on_search_char_hook(self, frame, event: wx.KeyEvent):
        """Handles keyboard events specifically for the search text control."""
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_ESCAPE:
            self.on_search_cancel(frame, None)
            return
        event.Skip()

    def on_search_enter(self, frame, event: wx.CommandEvent):
        """Handles Enter in search box."""
        if frame.search_list.IsShown() and frame.search_list.GetItemCount() > 0:
            frame.search_list.SetFocus()
            if frame.search_list.GetFirstSelected() == -1:
                frame.search_list.SetItemState(0, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
                                               wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
                frame.last_search_focus_index = 0

    def on_item_activated(self, frame, event: wx.ListEvent):
        """Starts playback from search result."""
        item_index = event.GetIndex()
        activated_book_data = self.get_data_from_index(item_index)

        if not activated_book_data:
            return

        book_id_to_play, book_title_to_play, _ = activated_book_data

        # Build context playlist
        playlist_context: List[Tuple[int, str]] = []
        for (bid, btitle, bshelf) in self._items:
            playlist_context.append((bid, btitle))

        if not playlist_context:
            speak(_("Error building search playlist."), LEVEL_CRITICAL)
            return

        current_playlist_index = -1
        for i, (book_id, title) in enumerate(playlist_context):
            if book_id == book_id_to_play:
                current_playlist_index = i
                break

        if current_playlist_index == -1:
            playlist_context.insert(0, (book_id_to_play, book_title_to_play))
            current_playlist_index = 0

        frame.start_playback(book_id_to_play, playlist_context, current_playlist_index)

    def on_list_selection_changed(self, frame, event: wx.ListEvent):
        """Updates status bar."""
        item_index = event.GetIndex()
        frame.last_search_focus_index = item_index

        if item_index == wx.NOT_FOUND:
            frame.SetStatusText("")
            return

        selected_data = self.get_data_from_index(item_index)
        if not selected_data:
            return

        book_id, title, shelf_id = selected_data
        shelf_name = _("Unknown")

        try:
            for (sid, sname, books_list) in getattr(frame, 'shelves_data', []):
                if sid == shelf_id:
                    shelf_name = sname
                    break
        except Exception:
            pass

        frame.SetStatusText(_("Book: {0} | In: {1}").format(title, shelf_name))
        event.Skip()

    def on_list_char_hook(self, frame, event: wx.KeyEvent):
        """Handles keyboard events for search list."""
        # Late import to avoid circular dependency
        from . import context_actions

        keycode = event.GetKeyCode()
        ctrl_down = event.ControlDown()

        if keycode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            focused_index = frame.search_list.GetFirstSelected()
            if focused_index != -1:
                evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_ACTIVATED)
                evt.SetIndex(focused_index)
                self.on_item_activated(frame, evt)
            return

        elif keycode == wx.WXK_SPACE:
            focused_index = frame.search_list.GetFocusedItem()
            if focused_index != -1:
                is_selected = frame.search_list.IsSelected(focused_index)
                if ctrl_down:
                    frame.search_list.Select(focused_index, not is_selected)
                elif not is_selected:
                    frame.search_list.Select(focused_index, True)
            return

        elif keycode == wx.WXK_ESCAPE:
            self.on_search_cancel(frame, None)
            return

        elif keycode == wx.WXK_DELETE:
            context_actions.on_context_delete_book(frame, None, source='search')
            return

        elif keycode == wx.WXK_F2:
            context_actions.on_context_rename_book(frame, None, source='search')
            return

        else:
            event.Skip()


# Singleton instance for backward compatibility
manager = SearchManager()

# Module-level aliases
on_search = manager.on_search
refresh_search_results = manager.refresh_search_results
on_search_cancel = manager.on_search_cancel
on_search_char_hook = manager.on_search_char_hook
on_search_enter = manager.on_search_enter
on_item_activated = manager.on_item_activated
on_list_selection_changed = manager.on_list_selection_changed
on_list_char_hook = manager.on_list_char_hook
get_virtual_item_text = manager.get_virtual_item_text
_get_book_data_by_index = manager.get_data_from_index
