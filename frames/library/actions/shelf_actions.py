# frames/library/actions/shelf_actions.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import wx
import logging
import sqlite3
from database import db_manager
from i18n import _
from nvda_controller import speak, LEVEL_CRITICAL, LEVEL_MINIMAL
from . import action_utils


def on_context_move_to_shelf(frame, event, shelf_menu_id, source='library'):
    """
    Moves selected book(s) to the target shelf identified by the menu ID.
    """
    if source != 'library':
        return

    books_to_move = action_utils.get_selected_book_data_list(frame, source)
    if not books_to_move:
        return

    menu_id = event.GetId() if shelf_menu_id is None else shelf_menu_id.GetId()
    new_shelf_id = frame.shelf_menu_id_map.get(menu_id)

    if new_shelf_id:
        try:
            for (book_id, book_title) in books_to_move:
                db_manager.shelf_repo.move_book_to_shelf(book_id, new_shelf_id)
            speak(_("Book(s) moved."), LEVEL_MINIMAL)
            action_utils.refresh_all_views(frame)
        except Exception as e:
            logging.error(f"Error moving books: {e}", exc_info=True)
            speak(_("Error moving books."), LEVEL_CRITICAL)


def on_context_move_to_new_shelf(frame, event, source='library'):
    """
    Creates a new shelf via dialog and moves selected book(s) to it.
    """
    if source != 'library':
        return

    books_to_move = action_utils.get_selected_book_data_list(frame, source)
    if not books_to_move:
        return

    dlg = wx.TextEntryDialog(frame, _("Enter name for new shelf:"), _("Create New Shelf"))
    if dlg.ShowModal() == wx.ID_OK:
        shelf_name = dlg.GetValue().strip()
        if shelf_name:
            try:
                new_shelf_id = db_manager.shelf_repo.create_shelf(shelf_name)
                if new_shelf_id:
                    for (book_id, book_title) in books_to_move:
                        db_manager.shelf_repo.move_book_to_shelf(book_id, new_shelf_id)
                    speak(_("Shelf created and book(s) moved."), LEVEL_CRITICAL)
                    action_utils.refresh_all_views(frame)
                else:
                    speak(_("Error: A shelf with this name already exists."), LEVEL_CRITICAL)
            except Exception as e:
                logging.error(f"Error creating shelf/moving books: {e}", exc_info=True)
                speak(_("Error creating shelf."), LEVEL_CRITICAL)
    if dlg:
        dlg.Destroy()


def on_context_rename_shelf(frame, event, source='library'):
    """
    Renames the currently focused shelf via a text entry dialog.
    """
    if source != 'library':
        return

    shelf_info = action_utils.get_focused_shelf_info(frame)
    if not shelf_info:
        return

    shelf_id, current_name = shelf_info
    if shelf_id == 1:
        speak(_("Cannot rename the Default Shelf."), LEVEL_CRITICAL)
        return

    dlg = wx.TextEntryDialog(frame, _("Enter new name for shelf:"), _("Rename Shelf"), current_name)
    if dlg.ShowModal() == wx.ID_OK:
        new_name = dlg.GetValue().strip()
        if new_name and new_name != current_name:
            try:
                db_manager.shelf_repo.rename_shelf(shelf_id, new_name)
                speak(_("Shelf renamed."), LEVEL_CRITICAL)
                action_utils.refresh_all_views(frame)
            except sqlite3.IntegrityError:
                speak(_("Error: A shelf with this name already exists."), LEVEL_CRITICAL)
            except Exception as e:
                logging.error(f"Error renaming shelf: {e}", exc_info=True)
                speak(_("Error renaming shelf."), LEVEL_CRITICAL)
    if dlg:
        dlg.Destroy()


def on_context_delete_shelf(frame, event, source='library'):
    """
    Deletes selected shelf/shelves. Only empty shelves can be deleted.
    Hold Shift to skip confirmation dialog (Quick Delete).
    """
    if source != 'library':
        return

    skip_confirm = wx.GetKeyState(wx.WXK_SHIFT)
    shelves_to_delete = action_utils.get_selected_shelf_data_list(frame)

    if not shelves_to_delete:
        focused_shelf = action_utils.get_focused_shelf_info(frame)
        if focused_shelf:
            shelves_to_delete = [focused_shelf]
        else:
            return

    valid_shelves = []
    for sid, sname in shelves_to_delete:
        if sid == 1:
            speak(_("Cannot delete the Default Shelf."), LEVEL_MINIMAL)
        else:
            valid_shelves.append((sid, sname))

    if not valid_shelves:
        return

    count = len(valid_shelves)
    if not skip_confirm:
        if count == 1:
            msg = _("Are you sure you want to delete shelf '{0}'? This only works if the shelf is empty.").format(
                valid_shelves[0][1])
        else:
            msg = _("Are you sure you want to delete {0} shelves? Only empty shelves will be deleted.").format(count)

        if wx.MessageBox(msg, _("Confirm Delete"), wx.YES_NO | wx.ICON_WARNING | wx.NO_DEFAULT, parent=frame) != wx.YES:
            return
    else:
        logging.info(f"Quick Delete (Shift+Delete) activated for {count} shelves.")

    deleted_count = 0
    failed_count = 0

    try:
        for sid, sname in valid_shelves:
            try:
                db_manager.shelf_repo.delete_shelf(sid)
                deleted_count += 1
            except sqlite3.IntegrityError:
                failed_count += 1  # Not empty
            except Exception as e:
                logging.error(f"Error deleting shelf {sid}: {e}")
                failed_count += 1

        if deleted_count > 0:
            if failed_count > 0:
                speak(_("{0} shelves deleted. {1} failed (not empty).").format(deleted_count, failed_count),
                      LEVEL_CRITICAL)
            else:
                speak(_("{0} shelves deleted.").format(deleted_count), LEVEL_CRITICAL)
            action_utils.refresh_all_views(frame)
        else:
            if failed_count > 0:
                speak(_("Could not delete shelves. Make sure they are empty."), LEVEL_CRITICAL)

    except Exception as e:
        logging.error(f"Error during shelf deletion: {e}", exc_info=True)
        speak(_("Error deleting shelves."), LEVEL_CRITICAL)
