# frames/library/menu_handlers.py
# Copyright (c) 2025-2026 Mehdi Rajabi
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

from audiobookshelf_client import AudiobookshelfClient, AudiobookshelfError
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
SETTING_AUDIOBOOKSHELF_UPLOAD_LIBRARY_ID = "audiobookshelf_upload_library_id"


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
            
    if wx.MessageBox(msg, _("Confirm Import"), wx.YES_NO | wx.CANCEL | wx.ICON_WARNING | wx.YES_DEFAULT) != wx.YES:
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
            wx.CallAfter(lambda: speak(_("Processing {0}...").format(book_name), LEVEL_MINIMAL))

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
                task_handlers.schedule_audiobookshelf_auto_upload(frame, book_id, announce=False)
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
            if fail_count > 0:
                if success_count == 1:
                    msg = _("1 book added ({0} failed).").format(fail_count)
                else:
                    msg = _("{0} books added ({1} failed).").format(success_count, fail_count)
            else:
                if success_count == 1:
                    msg = _("1 book added.")
                else:
                    msg = _("{0} books added.").format(success_count)
            speak(msg, LEVEL_CRITICAL)
        elif fail_count > 0:
            speak(_("Failed to add {0} items.").format(fail_count), LEVEL_CRITICAL)

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


def _abs_item_metadata(item):
    if not isinstance(item, dict):
        return {}
    media = item.get("media")
    if not isinstance(media, dict):
        return {}
    metadata = media.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _abs_item_title(item):
    metadata = _abs_item_metadata(item)
    title = metadata.get("title")
    if not title and isinstance(item, dict):
        title = item.get("title")
    title = str(title).strip() if title is not None else ""
    return title or _("Untitled Book")


def _abs_item_author(item):
    metadata = _abs_item_metadata(item)
    author = metadata.get("authorName")
    if isinstance(author, str) and author.strip():
        return author.strip()

    authors = metadata.get("authors")
    if isinstance(authors, list):
        names = []
        for entry in authors:
            if isinstance(entry, str) and entry.strip():
                names.append(entry.strip())
            elif isinstance(entry, dict):
                name = str(entry.get("name", "")).strip()
                if name:
                    names.append(name)
        if names:
            return ", ".join(names)

    return ""


def _abs_media_type(entry):
    if not isinstance(entry, dict):
        return ""
    media_type = entry.get("mediaType")
    if not media_type:
        media = entry.get("media")
        if isinstance(media, dict):
            media_type = media.get("mediaType")
    return str(media_type).strip().lower() if media_type is not None else ""


def _is_abs_book_like(entry):
    media_type = _abs_media_type(entry)
    return media_type in {"book", "books", "audiobook", "audiobooks"}


def _default_abs_library_index(book_libraries):
    configured_id = (db_manager.get_setting(SETTING_AUDIOBOOKSHELF_UPLOAD_LIBRARY_ID) or "").strip()
    if not configured_id:
        return 0 if len(book_libraries) == 1 else None

    for idx, lib in enumerate(book_libraries):
        if str(lib.get("id", "")).strip() == configured_id:
            return idx
    return 0 if len(book_libraries) == 1 else None


def on_import_audiobookshelf(frame, event):
    if frame.is_busy_processing:
        speak(_("Already scanning. Please wait."), LEVEL_CRITICAL)
        return

    server_default = db_manager.get_setting("audiobookshelf_server_url") or ""
    api_key_default = db_manager.get_setting("audiobookshelf_api_key") or ""
    url_dlg = wx.TextEntryDialog(
        frame,
        _("Enter your Audiobookshelf server URL (example: http://localhost:13378):"),
        _("Audiobookshelf Server"),
        server_default
    )
    try:
        if url_dlg.ShowModal() != wx.ID_OK:
            return
        server_url = url_dlg.GetValue().strip()
    finally:
        url_dlg.Destroy()

    if not server_url:
        speak(_("Server URL is required."), LEVEL_CRITICAL)
        return

    key_dlg = wx.TextEntryDialog(
        frame,
        _("Enter your Audiobookshelf API key:"),
        _("Audiobookshelf API Key"),
        api_key_default,
        wx.TextEntryDialogStyle | wx.TE_PASSWORD
    )
    try:
        if key_dlg.ShowModal() != wx.ID_OK:
            return
        api_key = key_dlg.GetValue().strip()
    finally:
        key_dlg.Destroy()

    if not api_key:
        speak(_("API key is required."), LEVEL_CRITICAL)
        return

    try:
        client = AudiobookshelfClient(server_url, api_key)
        logging.info(f"Audiobookshelf import: connecting to {server_url}")
        libraries = client.get_libraries()
        db_manager.set_setting("audiobookshelf_server_url", server_url)
        db_manager.set_setting("audiobookshelf_api_key", api_key)
    except AudiobookshelfError as e:
        logging.error(f"Audiobookshelf connection failed: {e}")
        speak(_("Could not connect to Audiobookshelf server."), LEVEL_CRITICAL)
        wx.MessageBox(str(e), _("Audiobookshelf Error"), wx.OK | wx.ICON_ERROR, parent=frame)
        return
    except Exception as e:
        logging.error(f"Unexpected Audiobookshelf error: {e}", exc_info=True)
        speak(_("Could not connect to Audiobookshelf server."), LEVEL_CRITICAL)
        wx.MessageBox(str(e), _("Audiobookshelf Error"), wx.OK | wx.ICON_ERROR, parent=frame)
        return

    if not libraries:
        speak(_("No libraries found on Audiobookshelf server."), LEVEL_CRITICAL)
        return

    book_libraries = [lib for lib in libraries if _is_abs_book_like(lib)]
    if not book_libraries:
        book_libraries = libraries

    library_labels = []
    for lib in book_libraries:
        name = str(lib.get("name", _("Unnamed Library"))).strip() or _("Unnamed Library")
        media_type = str(lib.get("mediaType", _("unknown"))).strip() or _("unknown")
        library_labels.append(f"{name} ({media_type})")

    selected_library_index = _default_abs_library_index(book_libraries)
    if selected_library_index is None:
        library_dlg = wx.SingleChoiceDialog(
            frame,
            _("Select an Audiobookshelf library:"),
            _("Audiobookshelf Libraries"),
            library_labels
        )
        try:
            if library_dlg.ShowModal() != wx.ID_OK:
                return
            selected_library_index = library_dlg.GetSelection()
        finally:
            library_dlg.Destroy()
    else:
        selected_label = library_labels[selected_library_index]
        logging.info(f"Audiobookshelf import: using default library {selected_label}")

    if selected_library_index < 0 or selected_library_index >= len(book_libraries):
        return

    selected_library = book_libraries[selected_library_index]
    library_id = str(selected_library.get("id", "")).strip()
    if not library_id:
        speak(_("Invalid library selection."), LEVEL_CRITICAL)
        return

    try:
        speak(_("Loading library items from Audiobookshelf..."), LEVEL_MINIMAL)
        items = client.get_library_items(library_id)
        logging.info(f"Audiobookshelf import: loaded {len(items)} items from library {library_id}")
    except AudiobookshelfError as e:
        logging.error(f"Failed to load Audiobookshelf items: {e}")
        speak(_("Could not load library items."), LEVEL_CRITICAL)
        wx.MessageBox(str(e), _("Audiobookshelf Error"), wx.OK | wx.ICON_ERROR, parent=frame)
        return

    if _is_abs_book_like(selected_library):
        filtered_items = [item for item in items if _is_abs_book_like(item) or not _abs_media_type(item)]
        if filtered_items:
            items = filtered_items

    if not items:
        speak(_("No books found in this Audiobookshelf library."), LEVEL_MINIMAL)
        return

    item_labels = []
    for item in items:
        title = _abs_item_title(item)
        author = _abs_item_author(item)
        item_labels.append(f"{title} - {author}" if author else title)

    books_dlg = wx.MultiChoiceDialog(
        frame,
        _("Select books to import into AudioShelf (use Space to check/uncheck):"),
        _("Import from Audiobookshelf"),
        item_labels
    )
    try:
        try:
            books_dlg.SetSelections(list(range(len(item_labels))))
        except Exception:
            pass

        if books_dlg.ShowModal() != wx.ID_OK:
            speak(_("Import cancelled."), LEVEL_MINIMAL)
            return
        selected_indices = list(books_dlg.GetSelections())
    finally:
        books_dlg.Destroy()

    if not selected_indices and len(items) == 1:
        selected_indices = [0]

    if not selected_indices:
        logging.info("Audiobookshelf import cancelled: no books selected after dialog.")
        speak(_("No books selected. Tip: use Space to check books before confirming."), LEVEL_CRITICAL)
        return

    selected_items = [items[i] for i in selected_indices if 0 <= i < len(items)]
    if not selected_items:
        speak(_("No books selected."), LEVEL_MINIMAL)
        return

    logging.info(f"Audiobookshelf import: selected {len(selected_items)} books")

    shelf_id = frame.current_view_level if isinstance(frame.current_view_level, int) else 1

    frame.is_busy_processing = True
    wx.BeginBusyCursor()
    speak(_("Importing {0} books from Audiobookshelf...").format(len(selected_items)), LEVEL_MINIMAL)

    worker = threading.Thread(
        target=_import_audiobookshelf_worker,
        args=(frame, client, selected_items, shelf_id),
        daemon=True
    )
    worker.start()


def _import_audiobookshelf_worker(frame, client, selected_items, shelf_id):
    added_count = 0
    duplicate_count = 0
    failed_count = 0
    last_added_book_id = None

    for item in selected_items:
        item_id = str(item.get("id", "")).strip() if isinstance(item, dict) else ""
        if not item_id:
            failed_count += 1
            continue

        try:
            imported_book = client.build_book_import(item_id=item_id, item_hint=item)
            book_id = db_manager.add_book(
                imported_book.title,
                imported_book.root_path,
                imported_book.files,
                shelf_id,
                book_type=imported_book.book_type
            )

            if not book_id:
                duplicate_count += 1
                continue

            if db_manager.conn:
                with db_manager.db_lock:
                    with db_manager.conn:
                        db_manager.conn.execute(
                            "UPDATE books SET author=?, narrator=?, description=? WHERE id=?",
                            (imported_book.author, imported_book.narrator, imported_book.description, book_id)
                        )

            added_count += 1
            last_added_book_id = book_id
            logging.info(f"Audiobookshelf import success: {imported_book.title} (ID={book_id})")
        except AudiobookshelfError as e:
            logging.error(f"Audiobookshelf import failed for item {item_id}: {e}")
            failed_count += 1
        except Exception as e:
            logging.error(f"Unexpected Audiobookshelf import error for item {item_id}: {e}", exc_info=True)
            failed_count += 1

    wx.CallAfter(
        _finalize_audiobookshelf_import,
        frame,
        shelf_id,
        added_count,
        duplicate_count,
        failed_count,
        last_added_book_id
    )


def _finalize_audiobookshelf_import(frame, shelf_id, added_count, duplicate_count, failed_count, last_added_book_id):
    task_handlers._reset_busy_state(frame)
    list_manager.refresh_library_data(frame)

    if added_count > 0:
        frame.current_view_level = shelf_id
        frame.current_filter = ""
        if hasattr(frame, 'search_ctrl') and frame.search_ctrl:
            frame.search_ctrl.SetValue("")
        frame.last_library_focus_index = -1

    list_manager.populate_library_list(frame)

    if last_added_book_id:
        list_manager.select_item_by_id(frame, 'book', last_added_book_id)

    history_manager.populate_history_list(frame, frame.shelves_data)

    if added_count == 0 and duplicate_count == 0 and failed_count == 0:
        speak(_("No books were imported."), LEVEL_MINIMAL)
        return

    parts = []
    if added_count:
        parts.append(_("{0} added").format(added_count))
    if duplicate_count:
        parts.append(_("{0} already existed").format(duplicate_count))
    if failed_count:
        parts.append(_("{0} failed").format(failed_count))

    summary = ", ".join(parts) if parts else _("No changes")
    level = LEVEL_CRITICAL if (added_count or duplicate_count or failed_count) else LEVEL_MINIMAL
    logging.info(
        f"Audiobookshelf import complete: added={added_count}, duplicate={duplicate_count}, failed={failed_count}, shelf={shelf_id}"
    )
    speak(_("Audiobookshelf import complete: {0}.").format(summary), level)


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

def on_whats_new(frame, event):
    """Opens the release notes / what's new dialog."""
    from dialogs.whats_new_dialog import WhatsNewDialog
    dlg = WhatsNewDialog(frame, show_donate=False)
    dlg.ShowModal()
    dlg.Destroy()
