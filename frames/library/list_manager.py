# frames/library/list_manager.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
import logging
from typing import List, Tuple, Optional, Any
from database import db_manager
from i18n import _
from nvda_controller import speak, LEVEL_CRITICAL, LEVEL_MINIMAL


class LibraryListManager:
    """
    Manages the data and UI population for the library list.
    Encapsulates the list state to avoid global variables.
    """

    def __init__(self):
        # Stores tuples of (display_label, item_type, item_id)
        self._items: List[Tuple[str, str, Any]] = []

    def get_data_from_index(self, index: int) -> Optional[Tuple[str, Any]]:
        """
        Retrieves (item_type, item_id) for a given list index.
        """
        try:
            label, item_type, item_id = self._items[index]
            return item_type, item_id
        except IndexError:
            logging.error(f"ListManager: Index {index} out of range.")
            return None

    def get_virtual_item_text(self, index: int, column: int) -> str:
        """Callback for Virtual ListCtrl to retrieve item text."""
        try:
            if 0 <= index < len(self._items):
                return self._items[index][0]
            return ""
        except Exception:
            return ""

    def refresh_library_data(self, frame):
        """
        Fetches the latest library data from the database and updates
        the frame's internal data stores.
        """
        try:
            frame.pinned_books = db_manager.book_repo.get_pinned_books()
            frame.shelves_data = db_manager.shelf_repo.get_shelves_and_books()
            frame.all_books_data = db_manager.book_repo.get_all_books()
            frame.finished_books = db_manager.book_repo.get_finished_books()
        except Exception as e:
            logging.error(f"Error fetching library data: {e}", exc_info=True)
            speak(_("Error loading library data."), LEVEL_CRITICAL)
            frame.shelves_data = []
            frame.pinned_books = []
            frame.all_books_data = []
            frame.finished_books = []

    def _is_virtual_shelf_hidden(self, key: str) -> bool:
        """Checks if a virtual shelf section is hidden."""
        try:
            is_hidden, _ignored = db_manager.get_ui_item_state(key)
            return is_hidden
        except Exception as e:
            logging.error(f"Error reading UI state for {key}: {e}")
            return False

    def _get_ordered_shelf_list(self, frame) -> List[Tuple[Any, str]]:
        """Returns a flattened list of navigable containers."""
        ordered_shelves = []
        if not self._is_virtual_shelf_hidden("virtual_pinned"):
            ordered_shelves.append(('virtual_pinned', _("Pinned Books")))
        for (sid, sname, _ignored) in frame.shelves_data:
            ordered_shelves.append((sid, sname))
        if not self._is_virtual_shelf_hidden("virtual_all_books"):
            ordered_shelves.append(('virtual_all_books', _("All Books")))
        if not self._is_virtual_shelf_hidden("virtual_finished"):
            ordered_shelves.append(('virtual_finished', _("Finished Books")))
        return ordered_shelves

    def populate_library_list(self, frame, index_to_select: int = -1):
        """
        Rebuilds the library list UI based on the current view level.
        """
        if frame.IsBeingDeleted() or not frame.library_list:
            return

        is_virtual = frame.library_list.HasFlag(wx.LC_VIRTUAL)
        frame.library_list.Freeze()

        if not is_virtual:
            frame.library_list.DeleteAllItems()
        else:
            frame.library_list.SetItemCount(0)

        self._items.clear()
        current_level = frame.current_view_level
        filter_lower = frame.current_filter.lower()
        items_added = 0

        finished_book_ids = set()
        if hasattr(frame, 'finished_books') and frame.finished_books:
            finished_book_ids = {b[0] for b in frame.finished_books}

        def add_item(label: str, item_type: str, item_id: Any):
            self._items.append((label, item_type, item_id))

        def get_display_label(b_title: str, b_id: int, suffix: str = "") -> str:
            final_label = b_title
            if b_id in finished_book_ids:
                final_label += f" [{_('Finished')}]"
            if suffix:
                final_label += f" {suffix}"
            return final_label

        try:
            if current_level == 'root':
                # Pinned Books
                if not self._is_virtual_shelf_hidden("virtual_pinned"):
                    for book_id, book_title, shelf_id in frame.pinned_books:
                        if filter_lower and filter_lower not in book_title.lower():
                            continue
                        label = get_display_label(book_title, book_id, suffix=f"[{_('Pinned')}]")
                        add_item(label, 'book', book_id)
                        items_added += 1

                # Shelves
                for (shelf_id, shelf_name, books) in frame.shelves_data:
                    shelf_matches = not filter_lower or filter_lower in shelf_name.lower()
                    book_matches = False
                    if not shelf_matches:
                        for (book_id, book_title) in books:
                            if filter_lower in book_title.lower():
                                book_matches = True
                                break
                    if shelf_matches or book_matches:
                        label = f"{shelf_name} ({len(books)}) [{_('Shelf')}]"
                        add_item(label, 'shelf', shelf_id)
                        items_added += 1

                # Virtual Shelves
                if not self._is_virtual_shelf_hidden("virtual_all_books"):
                    count = len(frame.all_books_data)
                    if not filter_lower or filter_lower in _("All Books").lower():
                        label = f"{_('All Books')} ({count}) [{_('Virtual Shelf')}]"
                        add_item(label, 'virtual_shelf', 'virtual_all_books')
                        items_added += 1

                if not self._is_virtual_shelf_hidden("virtual_finished"):
                    count = len(frame.finished_books) if hasattr(frame, 'finished_books') else 0
                    if not filter_lower or filter_lower in _("Finished Books").lower():
                        label = f"{_('Finished Books')} ({count}) [{_('Virtual Shelf')}]"
                        add_item(label, 'virtual_shelf', 'virtual_finished')
                        items_added += 1

            else:
                # Inside a shelf
                books_list_tuples = []
                if isinstance(current_level, int):
                    shelf_id_to_show = int(current_level)
                    for (shelf_id, shelf_name, books) in frame.shelves_data:
                        if shelf_id == shelf_id_to_show:
                            books_list_tuples = books
                            break
                elif current_level == 'virtual_all_books':
                    books_list_tuples = [(b[0], b[1]) for b in frame.all_books_data]
                elif current_level == 'virtual_pinned':
                    books_list_tuples = [(b[0], b[1]) for b in frame.pinned_books]
                elif current_level == 'virtual_finished':
                    books_list_tuples = [(b[0], b[1]) for b in frame.finished_books] if hasattr(frame, 'finished_books') else []

                for (book_id, book_title) in books_list_tuples:
                    if filter_lower and filter_lower not in book_title.lower():
                        continue
                    label = get_display_label(book_title, book_id)
                    add_item(label, 'book', book_id)
                    items_added += 1

            if is_virtual:
                frame.library_list.SetItemCount(items_added)
                frame.library_list.Refresh()
            else:
                for i, (label, _unused_type, _unused_id) in enumerate(self._items):
                    frame.library_list.InsertItem(i, label)
                    frame.library_list.SetItemData(i, i)

            if filter_lower:
                speak(_("{0} items found.").format(items_added), LEVEL_MINIMAL)

            if items_added > 0:
                target_index = 0
                if index_to_select != -1:
                    target_index = index_to_select
                elif frame.last_library_focus_index != -1:
                    target_index = frame.last_library_focus_index

                target_index = max(0, min(target_index, items_added - 1))

                frame.library_list.SetItemState(target_index,
                                                wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
                                                wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
                frame.last_library_focus_index = target_index
                frame.library_list.Focus(target_index)
                frame.library_list.EnsureVisible(target_index)

        except Exception as e:
            logging.error(f"Error populating library list: {e}", exc_info=True)
        finally:
            frame.library_list.Thaw()
            frame.library_list.SetColumnWidth(0, wx.LIST_AUTOSIZE)

    def select_item_by_id(self, frame, target_type: str, target_id: Any) -> bool:
        """Selects and focuses an item in the list by its ID."""
        found_index = -1
        for i, (_, item_type, item_id) in enumerate(self._items):
            if item_type == target_type and item_id == target_id:
                found_index = i
                break

        if found_index != -1:
            sel = frame.library_list.GetFirstSelected()
            while sel != -1:
                frame.library_list.Select(sel, False)
                sel = frame.library_list.GetNextSelected(sel)

            frame.library_list.SetItemState(found_index,
                                            wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
                                            wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
            frame.library_list.Focus(found_index)
            frame.library_list.EnsureVisible(found_index)
            frame.last_library_focus_index = found_index
            return True
        return False

    def on_select_all(self, frame, event):
        """Selects all items in the list."""
        if not frame.library_list:
            return
        count = frame.library_list.GetItemCount()
        for i in range(count):
            frame.library_list.Select(i, True)
        speak(_("Selected all items."), LEVEL_MINIMAL)

    def on_item_activated(self, frame, event: wx.ListEvent):
        """Handles item activation (Enter/Double-click)."""
        item_index = event.GetIndex()
        if frame.library_list.HasFlag(wx.LC_VIRTUAL):
            map_index = item_index
        else:
            map_index = frame.library_list.GetItemData(item_index)

        item_data = self.get_data_from_index(map_index)
        if not item_data:
            return

        item_type, item_id = item_data

        if item_type in ('shelf', 'virtual_shelf'):
            logging.info(f"Drilling down into shelf: {item_id}")
            frame.nav_stack_back.append((frame.current_view_level, item_index))
            frame.nav_stack_forward.clear()
            frame.current_view_level = item_id
            frame.current_filter = ""
            frame.search_ctrl.SetValue("")
            self.populate_library_list(frame, index_to_select=0)
            frame.library_list.SetFocus()

        elif item_type == 'book':
            logging.info(f"Activating book_id: {item_id}")
            playlist_context = []
            current_playlist_index = -1
            counter = 0

            # Build playlist from current view
            for i, (label, d_type, d_id) in enumerate(self._items):
                if d_type == 'book':
                    clean_title = label.rsplit(" [", 1)[0] if " [" in label else label
                    playlist_context.append((d_id, clean_title))
                    if d_id == item_id:
                        current_playlist_index = counter
                    counter += 1

            if playlist_context:
                frame.start_playback(
                    book_id=item_id,
                    library_playlist=playlist_context,
                    current_playlist_index=current_playlist_index
                )

    def navigate_to_shelf(self, frame, direction: int):
        """Handles cyclic shelf navigation (Ctrl+PageUp/Down)."""
        ordered_shelves = self._get_ordered_shelf_list(frame)
        if not ordered_shelves:
            speak(_("No shelves available."), LEVEL_MINIMAL)
            return

        current_id = frame.current_view_level
        if current_id == 'root':
            idx = frame.library_list.GetFirstSelected()
            if idx == -1: idx = 0
            count = frame.library_list.GetItemCount()
            new_idx = (idx + direction) % count
            frame.library_list.Select(idx, False)
            frame.library_list.Select(new_idx, True)
            frame.library_list.Focus(new_idx)
            frame.library_list.EnsureVisible(new_idx)
            speak(frame.library_list.GetItemText(new_idx), LEVEL_MINIMAL)
            return

        current_idx = -1
        for i, (sid, name) in enumerate(ordered_shelves):
            if sid == current_id:
                current_idx = i
                break
        if current_idx == -1:
            current_idx = 0

        count = len(ordered_shelves)
        new_idx = (current_idx + direction) % count
        sid, name = ordered_shelves[new_idx]
        self._switch_to_shelf(frame, sid, name)

    def jump_to_shelf_by_index(self, frame, target_index: int):
        """Directly jumps to the Nth available container."""
        ordered_shelves = self._get_ordered_shelf_list(frame)
        if 0 <= target_index < len(ordered_shelves):
            sid, name = ordered_shelves[target_index]
            if frame.current_view_level == sid:
                speak(_("Already in {0}").format(name), LEVEL_MINIMAL)
                return
            if frame.current_view_level == 'root':
                frame.nav_stack_back.append(('root', frame.last_library_focus_index))
                frame.nav_stack_forward.clear()
            self._switch_to_shelf(frame, sid, name)
        else:
            speak(_("Shelf {0} not found.").format(target_index + 1), LEVEL_MINIMAL)

    def jump_to_all_books(self, frame):
        """Directly opens 'All Books'."""
        if frame.current_view_level == 'virtual_all_books':
            speak(_("Already in All Books"), LEVEL_MINIMAL)
            return
        if frame.current_view_level == 'root':
            frame.nav_stack_back.append(('root', frame.last_library_focus_index))
            frame.nav_stack_forward.clear()
        self._switch_to_shelf(frame, 'virtual_all_books', _("All Books"))

    def _switch_to_shelf(self, frame, shelf_id, shelf_name):
        """Helper to switch the view to a specific shelf."""
        frame.current_view_level = shelf_id
        frame.current_filter = ""
        frame.search_ctrl.SetValue("")
        self.populate_library_list(frame, index_to_select=0)
        frame.library_list.SetFocus()
        speak(f"{shelf_name}", LEVEL_MINIMAL)

    def on_list_focus_changed(self, frame, event: wx.ListEvent):
        """Updates status bar on focus change."""
        item_index = event.GetIndex()
        if item_index == wx.NOT_FOUND:
            event.Skip()
            return

        frame.last_library_focus_index = item_index
        map_index = item_index if frame.library_list.HasFlag(wx.LC_VIRTUAL) else frame.library_list.GetItemData(
            item_index)

        item_data = self.get_data_from_index(map_index)
        if not item_data:
            frame.SetStatusText("")
            return

        item_type, item_id = item_data
        title = self.get_virtual_item_text(map_index, 0) if frame.library_list.HasFlag(
            wx.LC_VIRTUAL) else frame.library_list.GetItemText(item_index)

        status = ""
        if item_type in ['shelf', 'virtual_shelf']:
            status = title
        elif item_type == 'book':
            clean_title = title.rsplit(" [", 1)[0] if " [" in title else title
            status = _("Book: {0}").format(clean_title)

        frame.SetStatusText(status)
        event.Skip()

    def on_list_char_hook(self, frame, event: wx.KeyEvent):
        """Handles keyboard shortcuts within the library list."""
        # Late import to avoid circular dependency issues during refactor
        from . import context_actions
        from . import menu_handlers

        keycode = event.GetKeyCode()
        ctrl_down = event.ControlDown()
        alt_down = event.AltDown()
        shift_down = event.ShiftDown()

        if alt_down and keycode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            context_actions.on_context_properties(frame, None, source='library')
            return

        if keycode == wx.WXK_SPACE:
            focused_index = frame.library_list.GetFocusedItem()
            if focused_index != -1:
                is_selected = frame.library_list.IsSelected(focused_index)
                if ctrl_down:
                    frame.library_list.Select(focused_index, not is_selected)
                elif not is_selected:
                    frame.library_list.Select(focused_index, True)
            return

        elif keycode == wx.WXK_BACK or (alt_down and keycode == wx.WXK_LEFT):
            if frame.nav_stack_back:
                logging.info("Navigating back.")
                current_focus_index = frame.last_library_focus_index
                (previous_level, index_to_restore) = frame.nav_stack_back.pop()
                frame.nav_stack_forward.append((frame.current_view_level, current_focus_index))
                frame.current_view_level = previous_level
                frame.current_filter = ""
                frame.search_ctrl.SetValue("")
                self.populate_library_list(frame, index_to_select=index_to_restore)
                frame.library_list.SetFocus()
            else:
                speak(_("Already at root level."), LEVEL_MINIMAL)
            return

        elif alt_down and keycode == wx.WXK_RIGHT:
            if frame.nav_stack_forward:
                logging.info("Navigating forward.")
                current_focus_index = frame.last_library_focus_index
                (next_level, index_to_restore) = frame.nav_stack_forward.pop()
                frame.nav_stack_back.append((frame.current_view_level, current_focus_index))
                frame.current_view_level = next_level
                frame.current_filter = ""
                frame.search_ctrl.SetValue("")
                self.populate_library_list(frame, index_to_select=index_to_restore)
                frame.library_list.SetFocus()
            else:
                speak(_("No forward history."), LEVEL_MINIMAL)
            return

        elif keycode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            focused_index = frame.library_list.GetFirstSelected()
            if focused_index != -1:
                evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_ACTIVATED)
                evt.SetIndex(focused_index)
                self.on_item_activated(frame, evt)
            return

        elif keycode == wx.WXK_DELETE:
            focused_index = frame.library_list.GetFocusedItem()
            if focused_index != -1:
                map_index = focused_index if frame.library_list.HasFlag(
                    wx.LC_VIRTUAL) else frame.library_list.GetItemData(focused_index)
                item_data = self.get_data_from_index(map_index)
                if item_data:
                    item_type, item_id = item_data
                    if item_type == 'book':
                        if shift_down:
                            context_actions.on_context_delete_computer(frame, None, source='library')
                        else:
                            context_actions.on_context_delete_book(frame, None, source='library')
                    elif item_type == 'shelf':
                        context_actions.on_context_delete_shelf(frame, None, source='library')
            return

        elif keycode == wx.WXK_F2:
            focused_index = frame.library_list.GetFocusedItem()
            if focused_index != -1:
                map_index = focused_index if frame.library_list.HasFlag(
                    wx.LC_VIRTUAL) else frame.library_list.GetItemData(focused_index)
                item_data = self.get_data_from_index(map_index)
                if item_data:
                    item_type, item_id = item_data
                    if item_type == 'book':
                        context_actions.on_context_rename_book(frame, None, source='library')
                    elif item_type == 'shelf':
                        context_actions.on_context_rename_shelf(frame, None, source='library')
            return

        elif keycode == wx.WXK_F5:
            menu_handlers.on_refresh_library(frame, None)
            return

        elif alt_down and keycode == wx.WXK_PAGEUP:
            self.navigate_to_shelf(frame, direction=-1)
            return

        elif alt_down and keycode == wx.WXK_PAGEDOWN:
            self.navigate_to_shelf(frame, direction=1)
            return

        event.Skip()


# Singleton instance for backward compatibility
manager = LibraryListManager()

# Module-level aliases mapping to the singleton instance
refresh_library_data = manager.refresh_library_data
populate_library_list = manager.populate_library_list
get_virtual_item_text = manager.get_virtual_item_text
select_item_by_id = manager.select_item_by_id
jump_to_shelf_by_index = manager.jump_to_shelf_by_index
jump_to_all_books = manager.jump_to_all_books
on_item_activated = manager.on_item_activated
on_list_char_hook = manager.on_list_char_hook
on_list_focus_changed = manager.on_list_focus_changed
on_select_all = manager.on_select_all
get_data_from_index = manager.get_data_from_index
_get_data_from_index = manager.get_data_from_index
