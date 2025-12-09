# frames/library/task_handlers.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
import logging
import sqlite3
import threading
import os
import json
import concurrent.futures
import wx.lib.newevent
import book_scanner

from database import db_manager
from db_layer.helpers import find_missing_books
from i18n import _
from nvda_controller import speak, LEVEL_CRITICAL, LEVEL_MINIMAL
from . import list_manager
from . import history_manager

METADATA_FILENAME_DIR = ".audioshelf_metadata.json"
METADATA_VERSION = 2


def _reset_busy_state(frame):
    """Resets the busy/processing state of the main frame."""
    frame.is_busy_processing = False
    if hasattr(frame, 'prune_menu_item') and frame.prune_menu_item:
        try:
            frame.prune_menu_item.Enable(True)
        except RuntimeError:
            pass
    if wx.IsBusy():
        wx.EndBusyCursor()


def _clean_path(path: str) -> str:
    """Removes the Windows long path prefix and normalizes separators."""
    if path.startswith("\\\\?\\"):
        path = path[4:]
    return os.path.normpath(path)


def on_add_book(frame, event):
    """Triggers the dialog to add a book directory."""
    if frame.is_busy_processing:
        speak(_("Already scanning. Please wait."), LEVEL_CRITICAL)
        return

    dlg = wx.DirDialog(frame, _("Choose a book folder to add..."),
                       style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
    if dlg.ShowModal() == wx.ID_OK:
        book_path = dlg.GetPath()
        shelf_id = 1
        if isinstance(frame.current_view_level, int):
            shelf_id = frame.current_view_level
        trigger_book_scan(frame, book_path, shelf_id)
    dlg.Destroy()


def on_add_single_file(frame, event):
    """Triggers the dialog to add a single audio file as a book."""
    if frame.is_busy_processing:
        speak(_("Already scanning. Please wait."), LEVEL_CRITICAL)
        return

    exts = ["*" + ext for ext in book_scanner.SUPPORTED_EXTENSIONS]
    wildcard_str = ";".join(exts)
    wildcard = f"{_('Audio Files')} ({wildcard_str})|{wildcard_str}|{_('All Files')} (*.*)|*.*"

    dlg = wx.FileDialog(frame, _("Choose an audio file..."),
                        wildcard=wildcard,
                        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
    if dlg.ShowModal() == wx.ID_OK:
        file_path = dlg.GetPath()
        shelf_id = 1
        if isinstance(frame.current_view_level, int):
            shelf_id = frame.current_view_level
        trigger_book_scan(frame, file_path, shelf_id)
    dlg.Destroy()


def trigger_book_scan(frame, book_path: str, shelf_id: int, is_batch: bool = False):
    """
    Initiates the background scan for a book.
    """
    if frame.is_busy_processing and not is_batch:
        speak(_("Already scanning. Please wait."), LEVEL_CRITICAL)
        return

    if not book_path or not os.path.exists(book_path):
        if not is_batch:
            speak(_("Invalid path or file does not exist."), LEVEL_CRITICAL)
        return

    book_name = os.path.basename(book_path)
    logging.info(f"Triggering scan for: {book_path}")

    if not is_batch:
        speak(_("Adding book..."), LEVEL_MINIMAL)

    frame.is_busy_processing = True
    if not is_batch:
        wx.BeginBusyCursor()

    try:
        thread = threading.Thread(target=_scan_book_worker_phase1,
                                  args=(frame, book_path, book_name, shelf_id, is_batch))
        thread.daemon = True
        thread.start()
    except Exception as e:
        logging.error(f"Failed to start scan thread for {book_path}: {e}", exc_info=True)
        if not is_batch:
            speak(_("Error starting scan."), LEVEL_CRITICAL)
            _reset_busy_state(frame)


def _scan_book_worker_phase1(frame, book_path, book_name, shelf_id, is_batch):
    """Phase 1 Worker: Fast scan."""
    try:
        file_list = book_scanner.scan_folder(book_path, fast_scan=True)
        wx.PostEvent(frame, frame.ScanResultEvent(
            book_path=book_path,
            book_name=book_name,
            file_list=file_list,
            shelf_id=shelf_id,
            is_batch=is_batch
        ))
    except Exception as e:
        logging.error(f"Error in Phase 1 scan thread for {book_path}: {e}", exc_info=True)
        wx.PostEvent(frame, frame.ScanResultEvent(
            book_path=book_path,
            book_name=book_name,
            file_list=None,
            shelf_id=1,
            is_batch=is_batch
        ))


def process_book_import(book_path, book_name, file_list, shelf_id):
    """
    Central logic to import a book, detecting and applying metadata if available.
    Returns (book_id, import_successful).
    """
    metadata_filepath = None
    if os.path.isdir(book_path):
        possible_meta = os.path.join(book_path, METADATA_FILENAME_DIR)
        if os.path.exists(possible_meta):
            metadata_filepath = possible_meta
    elif os.path.isfile(book_path):
        possible_meta_1 = book_path + ".json"
        base_name = os.path.splitext(book_path)[0]
        possible_meta_2 = base_name + ".json"
        if os.path.exists(possible_meta_1):
            metadata_filepath = possible_meta_1
        elif os.path.exists(possible_meta_2):
            metadata_filepath = possible_meta_2

    metadata = None
    if metadata_filepath:
        try:
            with open(metadata_filepath, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            if not isinstance(metadata, dict) or metadata.get('version', 0) > METADATA_VERSION:
                logging.warning("Metadata version mismatch or invalid format.")
                metadata = None
        except Exception as e:
            logging.error(f"Error reading metadata file: {e}")
            metadata = None

    if not metadata:
        book_id = db_manager.add_book(book_name, book_path, file_list, shelf_id)
        return book_id, False

    # Import with metadata
    try:
        imported_title = metadata.get('title', book_name)
        author = metadata.get('author')
        narrator = metadata.get('narrator')
        genre = metadata.get('genre')
        description = metadata.get('description')
        is_finished = metadata.get('is_finished', False)
        is_pinned = metadata.get('is_pinned', False)

        old_files_info = metadata.get('files', [])
        clean_book_path = _clean_path(book_path)
        current_relpath_to_index = {}
        is_dir_source = os.path.isdir(book_path)

        for fp, idx, dur in file_list:
            clean_fp = _clean_path(fp)
            try:
                if is_dir_source:
                    rel = os.path.relpath(clean_fp, clean_book_path).replace('\\', '/')
                else:
                    rel = os.path.basename(clean_fp)
                current_relpath_to_index[os.path.normcase(rel)] = idx
            except ValueError:
                continue

        index_map = {}
        found_files_count = 0

        if is_dir_source:
            old_relpath_to_index = {fi['relative_path']: fi['index'] for fi in old_files_info}
            for rel_p, old_idx in old_relpath_to_index.items():
                norm_rel_p = rel_p.replace('\\', '/')
                if os.path.normcase(norm_rel_p) in current_relpath_to_index:
                    index_map[old_idx] = current_relpath_to_index[os.path.normcase(norm_rel_p)]
                    found_files_count += 1
        else:
            if len(file_list) == 1:
                index_map[0] = 0
                found_files_count = 1

        logging.info(f"Import debug: Found {found_files_count} matching files.")

        if found_files_count == 0:
            logging.warning("No matching files found in metadata import. Fallback to normal add.")
            book_id = db_manager.add_book(book_name, book_path, file_list, shelf_id)
            return book_id, False

        new_book_id = db_manager.add_book(imported_title, book_path, file_list, shelf_id)
        if not new_book_id:
            return None, False

        with db_manager.conn:
            db_manager.conn.execute(
                "UPDATE books SET author=?, narrator=?, genre=?, description=?, is_finished=?, is_pinned=? WHERE id=?",
                (author, narrator, genre, description, 1 if is_finished else 0, 1 if is_pinned else 0, new_book_id)
            )
            if is_pinned:
                db_manager.book_repo.pin_book(new_book_id)

        playback_state = metadata.get('playback_state')
        if playback_state:
            old_last_idx = playback_state.get('last_file_index', 0)
            new_fi = index_map.get(old_last_idx, 0)
            
            db_manager.save_playback_state(
                new_book_id, 
                new_fi,
                playback_state.get('last_position_ms', 0), 
                playback_state.get('last_speed_rate', 1.0),
                playback_state.get('last_eq_settings', "0,0,0,0,0,0,0,0,0,0"),
                playback_state.get('is_eq_enabled', False), 
                0
            )

        for bm in metadata.get('bookmarks', []):
            old_idx = bm.get('file_index')
            if old_idx in index_map:
                db_manager.add_bookmark(
                    new_book_id, 
                    index_map[old_idx], 
                    bm.get('position_ms', 0),
                    bm.get('title', ''), 
                    bm.get('note', '')
                )

        return new_book_id, True

    except Exception as e:
        logging.error(f"Import logic failed: {e}", exc_info=True)
        return None, False


def on_scan_complete(frame, event: wx.lib.newevent.NewEvent):
    """Handles completion of Phase 1."""
    book_id_to_select = None
    shelf_id = getattr(event, 'shelf_id', 1)
    is_batch = getattr(event, 'is_batch', False)
    success = False

    try:
        if event.file_list is None:
            raise Exception("Scan worker thread failed.")

        if not event.file_list:
            if not is_batch:
                speak(_("No playable files found."), LEVEL_CRITICAL)
            return

        # Use the central processing function
        book_id, imported = process_book_import(event.book_path, event.book_name, event.file_list, shelf_id)

        if book_id:
            success = True
            book_id_to_select = book_id
            if imported and not is_batch:
                speak(_("Book added with imported data."), LEVEL_CRITICAL)
            elif not is_batch:
                speak(_("Book added. Analyzing metadata in background..."), LEVEL_MINIMAL)
            
            thread = threading.Thread(target=_background_duration_worker,
                                      args=(frame, book_id, event.file_list))
            thread.daemon = True
            thread.start()
        else:
            if not is_batch:
                speak(_("Error: Book already exists or import failed."), LEVEL_CRITICAL)

    except Exception as e:
        logging.error(f"Error during book add: {e}", exc_info=True)
        if not is_batch:
            speak(_("An error occurred while adding the book."), LEVEL_CRITICAL)

    finally:
        if is_batch:
            if success and hasattr(frame, 'batch_success_count'):
                frame.batch_success_count += 1
        else:
            _reset_busy_state(frame)
            list_manager.refresh_library_data(frame)
            
            if book_id_to_select:
                frame.current_view_level = shelf_id
                frame.current_filter = ""
                if hasattr(frame, 'search_ctrl'):
                    frame.search_ctrl.SetValue("")
                frame.last_library_focus_index = -1

            list_manager.populate_library_list(frame)
            history_manager.populate_history_list(frame, frame.shelves_data)

        if book_id_to_select:
            def select_new():
                if list_manager.select_item_by_id(frame, 'book', book_id_to_select):
                    logging.info(f"Auto-focused new book ID {book_id_to_select}")
            wx.CallAfter(select_new)


def _get_file_duration_task(args):
    """Helper for ThreadPoolExecutor to read single file duration."""
    db_id, path = args
    try:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return None
        from tinytag import TinyTag
        tag = TinyTag.get(path, image=False)
        if tag and tag.duration:
            return db_id, int(tag.duration * 1000)
    except Exception:
        pass
    return None


def _background_duration_worker(frame, book_id, file_list):
    """
    Phase 2 Worker: Calculates actual durations for files in parallel.
    """
    try:
        logging.info(f"Phase 2: Starting parallel background duration scan for Book ID {book_id}")
        db_files = db_manager.get_book_files(book_id)
        
        if len(db_files) != len(file_list):
            return

        tasks = []
        for i, (db_id, path, idx, dur) in enumerate(db_files):
            if dur == 0:
                tasks.append((db_id, path))

        if not tasks:
            return

        updates = []
        batch_size = 100
        max_workers = min(8, (os.cpu_count() or 4) + 4)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for result in executor.map(_get_file_duration_task, tasks):
                if result:
                    updates.append(result)
                if len(updates) >= batch_size:
                    db_manager.update_file_duration_batch(updates)
                    updates = []

        if updates:
            db_manager.update_file_duration_batch(updates)

        logging.info(f"Phase 2: Background metadata update complete for Book ID {book_id}")

    except Exception as e:
        logging.error(f"Background metadata worker failed for Book ID {book_id}: {e}", exc_info=True)


def _scan_book_update_worker(frame, book_id, new_path):
    """Background worker to scan for file updates (full scan)."""
    try:
        logging.debug(f"Update worker started for book {book_id} at {new_path}")
        file_list = book_scanner.scan_folder(new_path, fast_scan=False)
        wx.PostEvent(frame, frame.UpdateScanResultEvent(
            book_id=book_id,
            new_path=new_path,
            file_list=file_list
        ))
    except Exception as e:
        logging.error(f"Error in update scan thread for {new_path}: {e}", exc_info=True)
        wx.PostEvent(frame, frame.UpdateScanResultEvent(
            book_id=book_id,
            new_path=new_path,
            file_list=None
        ))


def on_scan_update_complete(frame, event: wx.lib.newevent.NewEvent):
    """Handles the completion of a location update scan."""
    try:
        if event.file_list is None:
            raise Exception("Update scan worker thread failed.")

        if not event.file_list:
            speak(_("No playable files found in new location."), LEVEL_CRITICAL)
            return

        db_manager.update_book_source(event.book_id, event.new_path, event.file_list)
        speak(_("Book location updated."), LEVEL_CRITICAL)

    except Exception as e:
        logging.error(f"Error during book update for {event.new_path}: {e}", exc_info=True)
        speak(_("An error occurred during update."), LEVEL_CRITICAL)

    finally:
        _reset_busy_state(frame)
        list_manager.refresh_library_data(frame)
        list_manager.populate_library_list(frame)
        history_manager.populate_history_list(frame, frame.shelves_data)


def on_clear_missing_books(frame, event):
    """Starts the process to find and remove missing books."""
    if frame.is_busy_processing:
        speak(_("Already processing. Please wait."), LEVEL_CRITICAL)
        return

    logging.info("Starting clear missing books process.")
    speak(_("Checking for missing books... Please wait."), LEVEL_MINIMAL)
    frame.is_busy_processing = True

    if hasattr(frame, 'prune_menu_item') and frame.prune_menu_item:
        frame.prune_menu_item.Enable(False)

    wx.BeginBusyCursor()
    try:
        all_books = db_manager.get_all_books_for_pruning()
        thread = threading.Thread(target=_find_missing_books_worker, args=(frame, all_books))
        thread.daemon = True
        thread.start()
    except Exception as e:
        logging.error("Error starting missing books thread", exc_info=True)
        speak(_("Error checking for missing books."), LEVEL_CRITICAL)
        _reset_busy_state(frame)


def _find_missing_books_worker(frame, all_books_data):
    """Background worker to check for path existence."""
    try:
        missing_books = find_missing_books(all_books_data)
        wx.PostEvent(frame, frame.MissingBooksResultEvent(missing_books=missing_books))
    except Exception as e:
        logging.error(f"Error in find_missing_books thread: {e}", exc_info=True)
        wx.PostEvent(frame, frame.MissingBooksResultEvent(missing_books=[]))


def on_missing_books_result(frame, event):
    """Handles the result of the missing books check."""
    logging.info("Missing books result received.")
    _reset_busy_state(frame)
    missing_books = event.missing_books

    if not missing_books:
        speak(_("No missing books found."), LEVEL_MINIMAL)
        return

    count = len(missing_books)
    msg = _("Found {0} books whose folders seem to be missing. Remove them from the library?").format(count)
    if count <= 5:
        titles = "\n - ".join([b[1] for b in missing_books])
        msg += "\n\n - " + titles

    if wx.MessageBox(msg, _("Clear Missing Books"), wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION | wx.YES_DEFAULT, parent=frame) == wx.YES:
        
        speak(_("Removing missing books..."), LEVEL_CRITICAL)
        wx.BeginBusyCursor()
        try:
            deleted_count = db_manager.prune_missing_books([b[0] for b in missing_books])
            speak(_("{0} books removed.").format(deleted_count), LEVEL_CRITICAL)
            
            list_manager.refresh_library_data(frame)
            list_manager.populate_library_list(frame)
            history_manager.populate_history_list(frame, frame.shelves_data)

        except Exception as e:
            logging.error(f"Error pruning books: {e}", exc_info=True)
            speak(_("Error removing missing books."), LEVEL_CRITICAL)
        finally:
            if wx.IsBusy(): wx.EndBusyCursor()
    else:
        speak(_("Clear missing books cancelled."), LEVEL_MINIMAL)
