# frames/library/actions/book_actions.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import wx
import os
import sys
import subprocess
import shutil
import logging
import threading

from database import db_manager
from i18n import _
from nvda_controller import speak, LEVEL_CRITICAL, LEVEL_MINIMAL
from dialogs import properties_dialog
from dialogs.confirm_dialog import CheckboxConfirmDialog

from . import action_utils
from .. import list_manager
from .. import history_manager
from .. import search_handlers
from .. import task_handlers


def on_context_play(frame, event, source='library'):
    if source == 'library':
        evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_ACTIVATED)
        evt.SetIndex(frame.last_library_focus_index)
        list_manager.on_item_activated(frame, evt)
    elif source == 'history':
        evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_ACTIVATED)
        evt.SetIndex(frame.last_history_focus_index)
        history_manager.on_item_activated(frame, evt)
    elif source == 'search':
        evt = wx.ListEvent(wx.wxEVT_LIST_ITEM_ACTIVATED)
        evt.SetIndex(frame.last_search_focus_index)
        search_handlers.on_item_activated(frame, evt)


def on_context_rename_book(frame, event, source='library'):
    selected_books = action_utils.get_selected_book_data_list(frame, source)
    if len(selected_books) > 1:
        speak(_("Cannot rename multiple items at once."), LEVEL_CRITICAL)
        return

    book_info = action_utils.get_focused_book_info(frame, source)
    if not book_info:
        return

    book_id, current_name = book_info
    dlg = wx.TextEntryDialog(frame, _("Enter new name for book:"), _("Rename Book"), current_name)
    
    if dlg.ShowModal() == wx.ID_OK:
        new_name = dlg.GetValue().strip()
        if new_name and new_name != current_name:
            try:
                db_manager.book_repo.rename_book(book_id, new_name)
                speak(_("Book renamed."), LEVEL_CRITICAL)
                action_utils.refresh_all_views(frame)
            except Exception as e:
                logging.error(f"Error renaming book: {e}", exc_info=True)
                speak(_("Error renaming book."), LEVEL_CRITICAL)
    
    if dlg:
        dlg.Destroy()


def on_context_properties(frame, event, source='library'):
    selected_books = action_utils.get_selected_book_data_list(frame, source)
    if len(selected_books) > 1:
        speak(_("Cannot get properties for multiple items at once."), LEVEL_CRITICAL)
        return

    book_info = action_utils.get_focused_book_info(frame, source)
    if not book_info:
        return

    book_id, _ = book_info
    try:
        dlg = properties_dialog.PropertiesDialog(frame, book_id)
        dlg.ShowModal()
        dlg.Destroy()
    except Exception as e:
        logging.error(f"Error showing properties dialog: {e}", exc_info=True)
        speak(_("Error opening properties."), LEVEL_CRITICAL)


def on_context_open_location(frame, event, source='library'):
    selected_books = action_utils.get_selected_book_data_list(frame, source)
    if len(selected_books) > 1:
        speak(_("Cannot open location for multiple items at once."), LEVEL_CRITICAL)
        return

    book_info = action_utils.get_focused_book_info(frame, source)
    if not book_info:
        return

    book_id, _ = book_info
    book_path = db_manager.book_repo.get_book_path(book_id)

    if book_path and os.path.exists(book_path):
        try:
            if sys.platform == "win32":
                if os.path.isfile(book_path):
                    subprocess.Popen(['explorer', '/select,', book_path])
                else:
                    os.startfile(book_path)
            elif sys.platform == "darwin":
                subprocess.Popen(['open', book_path])
            else:
                subprocess.Popen(['xdg-open', book_path])
        except Exception as e:
            logging.error(f"Error opening folder: {e}", exc_info=True)
            speak(_("Could not open folder."), LEVEL_CRITICAL)
    else:
        speak(_("Book location not found."), LEVEL_CRITICAL)


def on_context_update_location(frame, event, source='library'):
    selected_books = action_utils.get_selected_book_data_list(frame, source)
    if len(selected_books) > 1:
        speak(_("Cannot update location for multiple items at once."), LEVEL_CRITICAL)
        return

    book_info = action_utils.get_focused_book_info(frame, source)
    if not book_info:
        return

    book_id, book_title = book_info
    if frame.is_busy_processing:
        speak(_("Already scanning. Please wait."), LEVEL_CRITICAL)
        return

    dlg = wx.DirDialog(frame, _("Choose the NEW location for book '{0}'...").format(book_title),
                       style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
    try:
        if dlg.ShowModal() == wx.ID_OK:
            new_path = dlg.GetPath()
            wx.BeginBusyCursor()
            speak(_("Scanning new location..."), LEVEL_MINIMAL)
            frame.is_busy_processing = True
            try:
                thread = threading.Thread(target=task_handlers._scan_book_update_worker,
                                          args=(frame, book_id, new_path))
                thread.daemon = True
                thread.start()
            except Exception as e:
                logging.error(f"Failed to start update scan thread for {new_path}: {e}", exc_info=True)
                speak(_("Error starting scan."), LEVEL_CRITICAL)
                task_handlers._reset_busy_state(frame)
    finally:
        if dlg:
            dlg.Destroy()


def on_context_delete_book(frame, event, source='library'):
    skip_confirm = wx.GetKeyState(wx.WXK_SHIFT)
    books_to_delete = action_utils.get_selected_book_data_list(frame, source)

    if not books_to_delete:
        focused_book = action_utils.get_focused_book_info(frame, source)
        if focused_book:
            books_to_delete = [focused_book]
        else:
            return

    count = len(books_to_delete)
    if not skip_confirm:
        if count == 1:
            msg = _("Are you sure you want to remove '{0}' from your library? (Files will NOT be deleted)").format(
                books_to_delete[0][1])
        else:
            msg = _("Are you sure you want to remove {0} books from your library? (Files will NOT be deleted)").format(
                count)
        
        if wx.MessageBox(msg, _("Confirm Remove"), wx.YES_NO | wx.ICON_WARNING | wx.NO_DEFAULT, parent=frame) != wx.YES:
            return
    else:
        logging.info(f"Quick Delete (Shift+Delete) activated for {count} books.")

    try:
        for (book_id, book_title) in books_to_delete:
            db_manager.book_repo.delete_book(book_id)
            logging.info(f"Deleted book: {book_title} (ID: {book_id})")

        if count == 1:
            speak(_("Book removed from library."), LEVEL_CRITICAL)
        else:
            speak(_("{0} books removed from library.").format(count), LEVEL_CRITICAL)
            
        action_utils.refresh_all_views(frame)

    except Exception as e:
        logging.error(f"Error deleting books: {e}", exc_info=True)
        speak(_("Error removing books."), LEVEL_CRITICAL)


def on_context_delete_computer(frame, event, source='library'):
    books_to_delete = action_utils.get_selected_book_data_list(frame, source)
    if not books_to_delete:
        focused_book = action_utils.get_focused_book_info(frame, source)
        if focused_book:
            books_to_delete = [focused_book]
        else:
            return

    count = len(books_to_delete)
    
# Create a warning message
    if count == 1:
        book_title = books_to_delete[0][1]
        msg = _("WARNING: You are about to permanently delete '{0}' and all its files from your computer.\nThis action CANNOT be undone.").format(book_title)
    else:
        msg = _("WARNING: You are about to permanently delete {0} books and all their files from your computer.\nThis action CANNOT be undone.").format(count)

# Show new dialog
    dlg = CheckboxConfirmDialog(
        parent=frame,
        title=_("Permanent Delete"),
        message=msg,
        check_label=_("I understand that these files will be deleted permanently"),
        button_label=_("Delete Files")
    )

    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        return
    
    dlg.Destroy()

    try:
        wx.BeginBusyCursor()
        speak(_("Deleting files..."), LEVEL_CRITICAL)
        
        deleted_count = 0
        failed_count = 0

        for (book_id, book_title) in books_to_delete:
            book_path = db_manager.book_repo.get_book_path(book_id)
            if book_path and os.path.exists(book_path):
                try:
                    if os.path.isfile(book_path):
                        os.remove(book_path)
                    else:
                        shutil.rmtree(book_path)
                    db_manager.book_repo.delete_book(book_id)
                    deleted_count += 1
                except Exception as e:
                    logging.error(f"Error deleting path {book_path}: {e}")
                    failed_count += 1
            else:
                db_manager.book_repo.delete_book(book_id)
                deleted_count += 1
                logging.warning(f"Path not found for {book_title}, removing from DB only.")

        if deleted_count > 0:
            speak(_("{0} books deleted permanently.").format(deleted_count), LEVEL_CRITICAL)
            
        if failed_count > 0:
            speak(_("{0} books failed to delete.").format(failed_count), LEVEL_CRITICAL)

        action_utils.refresh_all_views(frame)

    except Exception as e:
        logging.error(f"Error during permanent delete: {e}", exc_info=True)
        speak(_("Error deleting files."), LEVEL_CRITICAL)
    finally:
        if wx.IsBusy():
            wx.EndBusyCursor()


def _pin_book_logic(frame, book_id: int):
    try:
        db_manager.book_repo.pin_book(book_id)
    except Exception as e:
        logging.error(f"Error pinning book {book_id}: {e}", exc_info=True)
        raise


def _unpin_book_logic(frame, book_id: int):
    try:
        db_manager.book_repo.unpin_book(book_id)
    except Exception as e:
        logging.error(f"Error unpinning book {book_id}: {e}", exc_info=True)
        raise


def on_context_pin_book(frame, event, source='library'):
    books_to_pin = action_utils.get_selected_book_data_list(frame, source)
    if not books_to_pin:
        focused_book = action_utils.get_focused_book_info(frame, source)
        if focused_book:
            books_to_pin = [focused_book]
        else:
            return

    try:
        for (book_id, book_title) in books_to_pin:
            _pin_book_logic(frame, book_id)
        
        count = len(books_to_pin)
        if count == 1:
            speak(_("Book pinned."), LEVEL_CRITICAL)
        else:
            speak(_("{0} books pinned.").format(count), LEVEL_CRITICAL)
            
        action_utils.refresh_all_views(frame)
    except Exception:
        speak(_("Error pinning one or more books."), LEVEL_CRITICAL)


def on_context_unpin_book(frame, event, source='library'):
    books_to_unpin = action_utils.get_selected_book_data_list(frame, source)
    if not books_to_unpin:
        focused_book = action_utils.get_focused_book_info(frame, source)
        if focused_book:
            books_to_unpin = [focused_book]
        else:
            return

    try:
        for (book_id, book_title) in books_to_unpin:
            _unpin_book_logic(frame, book_id)
        
        count = len(books_to_unpin)
        if count == 1:
            speak(_("Book unpinned."), LEVEL_CRITICAL)
        else:
            speak(_("{0} books unpinned.").format(count), LEVEL_CRITICAL)
            
        action_utils.refresh_all_views(frame)
    except Exception:
        speak(_("Error unpinning one or more books."), LEVEL_CRITICAL)


def _set_finished_status_logic(frame, book_id: int, is_finished: bool):
    try:
        db_manager.book_repo.set_book_finished(book_id, is_finished)
    except Exception as e:
        logging.error(f"Error setting finished status {is_finished} for book {book_id}: {e}", exc_info=True)
        raise


def on_context_mark_finished(frame, event, source='library'):
    books_to_mark = action_utils.get_selected_book_data_list(frame, source)
    if not books_to_mark:
        focused_book = action_utils.get_focused_book_info(frame, source)
        if focused_book:
            books_to_mark = [focused_book]
        else:
            return

    try:
        for (book_id, book_title) in books_to_mark:
            _set_finished_status_logic(frame, book_id, True)
        
        count = len(books_to_mark)
        if count == 1:
            speak(_("Marked as finished."), LEVEL_CRITICAL)
        else:
            speak(_("{0} books marked as finished.").format(count), LEVEL_CRITICAL)
        
        action_utils.refresh_all_views(frame)
    except Exception:
        speak(_("Error updating book status."), LEVEL_CRITICAL)


def on_context_mark_unfinished(frame, event, source='library'):
    books_to_mark = action_utils.get_selected_book_data_list(frame, source)
    if not books_to_mark:
        focused_book = action_utils.get_focused_book_info(frame, source)
        if focused_book:
            books_to_mark = [focused_book]
        else:
            return

    try:
        for (book_id, book_title) in books_to_mark:
            _set_finished_status_logic(frame, book_id, False)
        
        count = len(books_to_mark)
        if count == 1:
            speak(_("Marked as unfinished."), LEVEL_CRITICAL)
        else:
            speak(_("{0} books marked as unfinished.").format(count), LEVEL_CRITICAL)
        
        action_utils.refresh_all_views(frame)
    except Exception:
        speak(_("Error updating book status."), LEVEL_CRITICAL)
