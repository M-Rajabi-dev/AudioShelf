# frames/library/menu_handlers.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
import logging
import os
import threading
import json
import shutil
import sys
import subprocess
import book_scanner

from database import db_manager, DB_FILE_PATH
from i18n import _
from nvda_controller import speak, LEVEL_CRITICAL, LEVEL_MINIMAL
from dialogs import settings_dialog, about_dialog, shortcuts_dialog, donate_dialog, user_guide_dialog
from dialogs.confirm_dialog import CheckboxConfirmDialog
from . import list_manager
from . import history_manager
from . import task_handlers

METADATA_FILENAME_DIR = ".audioshelf_metadata.json"
METADATA_VERSION = 2


def on_create_shelf(frame, event):
    """Creates a new shelf via dialog."""
    dlg = wx.TextEntryDialog(frame, _("Enter name for new shelf:"), _("Create New Shelf"))
    if dlg.ShowModal() == wx.ID_OK:
        shelf_name = dlg.GetValue().strip()
        if shelf_name:
            try:
                new_shelf_id = db_manager.shelf_repo.create_shelf(shelf_name)
                if new_shelf_id:
                    list_manager.refresh_library_data(frame)
                    list_manager.populate_library_list(frame)
                    
                    if list_manager.select_item_by_id(frame, 'shelf', new_shelf_id):
                        speak(_("Shelf created."), LEVEL_CRITICAL)
                    else:
                        speak(_("Shelf created."), LEVEL_CRITICAL)
                else:
                    speak(_("Error: A shelf with this name already exists."), LEVEL_CRITICAL)
            except Exception as e:
                logging.error(f"Error creating shelf: {e}", exc_info=True)
                speak(_("Error creating shelf."), LEVEL_CRITICAL)
    if dlg:
        dlg.Destroy()


def on_refresh_library(frame, event):
    """Refreshes the library data and UI list."""
    speak(_("Refreshing library."), LEVEL_MINIMAL)
    list_manager.refresh_library_data(frame)
    list_manager.populate_library_list(frame)
    history_manager.populate_history_list(frame, frame.shelves_data)


def on_settings(frame, event):
    """Opens settings dialog."""
    dlg = settings_dialog.SettingsDialog(frame)
    if dlg.ShowModal() == wx.ID_OK:
        logging.info("Settings saved. Refreshing library list UI.")
        list_manager.populate_library_list(frame)
    dlg.Destroy()


def on_quit(frame, event):
    frame.Close()


def on_about(frame, event):
    dlg = about_dialog.AboutDialog(frame)
    dlg.ShowModal()
    dlg.Destroy()


def on_shortcuts(frame, event):
    dlg = shortcuts_dialog.ShortcutsDialog(frame)
    dlg.ShowModal()
    dlg.Destroy()


def on_user_guide(frame, event):
    """Opens the comprehensive User Guide dialog."""
    dlg = user_guide_dialog.UserGuideDialog(frame)
    dlg.ShowModal()
    dlg.Destroy()


def on_donate(frame, event):
    dlg = donate_dialog.DonateDialog(frame)
    dlg.ShowModal()
    dlg.Destroy()


def on_open_logs(frame, event):
    """Opens the folder containing the application log file."""
    log_path = None
    for handler in logging.getLogger().handlers:
        if hasattr(handler, 'baseFilename'):
            log_path = handler.baseFilename
            break
            
    if not log_path or not os.path.exists(log_path):
        speak(_("Log file not found."), LEVEL_MINIMAL)
        return

    log_dir = os.path.dirname(log_path)
    
    try:
        if sys.platform == "win32":
            os.startfile(log_dir)
        elif sys.platform == "darwin":
            subprocess.Popen(['open', log_dir])
        else:
            subprocess.Popen(['xdg-open', log_dir])
        speak(_("Logs folder opened."), LEVEL_MINIMAL)
    except Exception as e:
        logging.error(f"Error opening logs folder: {e}")
        speak(_("Could not open logs folder."), LEVEL_CRITICAL)


def on_export_database(frame, event):
    """Exports the current database file to a user-selected location."""
    dlg = wx.FileDialog(
        frame, 
        message=_("Save Database Backup"),
        defaultFile="audioshelf_backup.db",
        wildcard="SQLite Database (*.db)|*.db",
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
    )
    
    if dlg.ShowModal() == wx.ID_OK:
        target_path = dlg.GetPath()
        try:
            if db_manager.conn:
                db_manager.conn.execute("PRAGMA wal_checkpoint(FULL);")
            
            shutil.copy2(DB_FILE_PATH, target_path)
            speak(_("Database exported successfully."), LEVEL_CRITICAL)
            logging.info(f"Database exported to: {target_path}")
        except Exception as e:
            logging.error(f"Error exporting database: {e}", exc_info=True)
            speak(_("Error exporting database."), LEVEL_CRITICAL)
            wx.MessageBox(_("Failed to export database.\nError: {0}").format(e), _("Error"), wx.OK | wx.ICON_ERROR)
    
    dlg.Destroy()


def on_import_database(frame, event):
    """
    Imports a database file, replacing the current one.
    Requires application restart.
    """
    msg = _("WARNING: Importing a database will overwrite your current library and settings.\n"
            "This action cannot be undone.\n\n"
            "The application will close immediately after import.\n"
            "Do you want to continue?")
            
    if wx.MessageBox(msg, _("Confirm Import"), wx.YES_NO | wx.ICON_WARNING) != wx.YES:
        return

    dlg = wx.FileDialog(
        frame, 
        message=_("Select Database Backup"),
        wildcard="SQLite Database (*.db)|*.db",
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
    )

    if dlg.ShowModal() == wx.ID_OK:
        source_path = dlg.GetPath()
        try:
            db_manager.close()
            shutil.copy2(source_path, DB_FILE_PATH)
            
            speak(_("Import successful. Application will close."), LEVEL_CRITICAL)
            wx.MessageBox(_("Database imported successfully.\nPlease restart AudioShelf."), _("Import Complete"), wx.OK)
            
            frame.Close(force=True)
            sys.exit(0)
            
        except Exception as e:
            logging.error(f"Error importing database: {e}", exc_info=True)
            speak(_("Error importing database."), LEVEL_CRITICAL)
            wx.MessageBox(_("Failed to import database.\nError: {0}").format(e), _("Error"), wx.OK | wx.ICON_ERROR)
            
            db_manager._establish_connection()

    dlg.Destroy()


def _batch_paste_worker(frame, paths: list, shelf_id: int):
    """
    Background worker to process pasted files/folders using the centralized logic.
    """
    success_count = 0
    fail_count = 0
    last_added_book_id = None
    books_to_update_background = []

    for path in paths:
        if not os.path.exists(path):
            continue

        book_name = os.path.basename(path)
        if len(paths) > 1:
            wx.CallAfter(lambda: speak(f"{_('Processing')} {book_name}...", LEVEL_MINIMAL))

        try:
            file_list = book_scanner.scan_folder(path, fast_scan=True)
            if not file_list:
                logging.warning(f"Batch paste: No files found in {path}")
                fail_count += 1
                continue

            # Use the unified import logic from task_handlers
            book_id, imported = task_handlers.process_book_import(path, book_name, file_list, shelf_id)

            if book_id:
                success_count += 1
                last_added_book_id = book_id
                books_to_update_background.append((book_id, file_list))
            else:
                logging.warning(f"Failed to add book (maybe exists): {book_name}")
                fail_count += 1

        except Exception as e:
            logging.error(f"Batch paste error for {path}: {e}", exc_info=True)
            fail_count += 1

    # Trigger background updates
    for b_id, f_list in books_to_update_background:
        threading.Thread(
            target=task_handlers._background_duration_worker,
            args=(frame, b_id, f_list),
            daemon=True
        ).start()

    def _finalize():
        task_handlers._reset_busy_state(frame)
        list_manager.refresh_library_data(frame)

        if last_added_book_id:
            frame.current_view_level = shelf_id
            frame.current_filter = ""
            if hasattr(frame, 'search_ctrl') and frame.search_ctrl:
                frame.search_ctrl.SetValue("")
            frame.last_library_focus_index = -1

        list_manager.populate_library_list(frame)
        
        if last_added_book_id:
            def select_new():
                list_manager.select_item_by_id(frame, 'book', last_added_book_id)
            wx.CallAfter(select_new)

        history_manager.populate_history_list(frame, frame.shelves_data)

        if success_count == 0 and fail_count == 0:
            speak(_("No valid items found."), LEVEL_MINIMAL)
        elif success_count > 0:
            if success_count == 1:
                msg = _("1 book added.")
            else:
                msg = _("{0} books added.").format(success_count)
            
            if fail_count > 0:
                msg += _(" ({0} failed)").format(fail_count)
            speak(msg, LEVEL_CRITICAL)
        elif fail_count > 0:
            speak(_("Failed to add {0} items."), LEVEL_CRITICAL)

    wx.CallAfter(_finalize)


def on_paste_book(frame, event):
    """Handles Paste (Ctrl+V) to add books from clipboard."""
    if frame.is_busy_processing:
        speak(_("Already scanning. Please wait."), LEVEL_CRITICAL)
        return

    clipboard = wx.Clipboard.Get()
    if not clipboard.Open():
        return

    try:
        data = wx.FileDataObject()
        if clipboard.GetData(data):
            filenames = data.GetFilenames()
            if filenames:
                logging.info(f"Paste book: Got {len(filenames)} items.")
                
                shelf_id = 1
                if isinstance(frame.current_view_level, int):
                    shelf_id = frame.current_view_level

                speak(_("Processing {0} items...").format(len(filenames)), LEVEL_MINIMAL)
                frame.is_busy_processing = True
                
                thread = threading.Thread(target=_batch_paste_worker,
                                          args=(frame, filenames, shelf_id))
                thread.daemon = True
                thread.start()
            else:
                speak(_("Clipboard empty."), LEVEL_MINIMAL)
        else:
            speak(_("Clipboard empty."), LEVEL_MINIMAL)
    except Exception as e:
        logging.error(f"Error paste: {e}", exc_info=True)
        speak(_("Error processing clipboard."), LEVEL_CRITICAL)
        task_handlers._reset_busy_state(frame)
    finally:
        clipboard.Close()


def on_clear_library(frame, event):
    """Clears the library using the safe checkbox confirmation."""
    
    msg = _("WARNING: This will remove ALL books, shelves, and history from AudioShelf.\n"
            "Your actual audio files on the disk will NOT be deleted.\n\n"
            "Are you sure you want to reset your library?")

    dlg = CheckboxConfirmDialog(
        parent=frame,
        title=_("Clear Library"),
        message=msg,
        check_label=_("Yes, remove all books and reset the library"),
        button_label=_("Clear Everything")
    )

    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        return
        
    dlg.Destroy()

# --- start cleaning operation ---
    speak(_("Clearing library..."), LEVEL_CRITICAL)
    wx.BeginBusyCursor()
    try:
        db_manager.clear_library()
        speak(_("Library cleared successfully."), LEVEL_CRITICAL)
        
        frame.current_view_level = 'root'
        list_manager.refresh_library_data(frame)
        list_manager.populate_library_list(frame)
        history_manager.populate_history_list(frame, frame.shelves_data)

    except Exception as e:
        logging.critical(f"Error clearing library: {e}", exc_info=True)
        speak(_("Error clearing library."), LEVEL_CRITICAL)
    finally:
        if wx.IsBusy(): wx.EndBusyCursor()