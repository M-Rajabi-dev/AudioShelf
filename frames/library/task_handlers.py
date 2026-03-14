# frames/library/task_handlers.py
# Copyright (c) 2025-2026 Mehdi Rajabi
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
from media_types import infer_book_type_from_file_rows, filter_files_by_book_type

from audiobookshelf_client import AudiobookshelfClient, AudiobookshelfError
from database import db_manager
from db_layer.helpers import find_missing_books, is_remote_source
from i18n import _
from nvda_controller import speak, LEVEL_CRITICAL, LEVEL_MINIMAL
from playback.abs_link_resolver import resolve_audiobookshelf_target
from . import list_manager
from . import history_manager

METADATA_FILENAME_DIR = ".audioshelf_metadata.json"
METADATA_VERSION = 2
SETTING_AUDIOBOOKSHELF_SERVER_URL = "audiobookshelf_server_url"
SETTING_AUDIOBOOKSHELF_API_KEY = "audiobookshelf_api_key"
SETTING_AUDIOBOOKSHELF_AUTO_UPLOAD = "audiobookshelf_auto_upload"
SETTING_AUDIOBOOKSHELF_UPLOAD_LIBRARY_ID = "audiobookshelf_upload_library_id"
SETTING_AUDIOBOOKSHELF_UPLOAD_FOLDER_ID = "audiobookshelf_upload_folder_id"
AUDIOBOOKSHELF_UPLOAD_TIMEOUT_SECONDS = 600


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


def _should_auto_upload_to_audiobookshelf() -> bool:
    flag = db_manager.get_setting(SETTING_AUDIOBOOKSHELF_AUTO_UPLOAD)
    if flag is None:
        return True
    return str(flag).strip().lower() not in {"false", "0", "no", "off"}


def _collect_local_file_paths_for_book(book_id: int) -> list[str]:
    file_rows = db_manager.get_book_files(book_id)
    file_paths = []
    for row in file_rows:
        if not row or len(row) < 2:
            continue
        path = row[1]
        if not path or is_remote_source(path):
            continue
        if os.path.isfile(path):
            file_paths.append(path)
    return file_paths


def schedule_audiobookshelf_auto_upload(frame, book_id: int, announce: bool):
    if not _should_auto_upload_to_audiobookshelf():
        logging.info(f"Audiobookshelf auto-upload skipped for book {book_id}: disabled in settings.")
        return

    root_path = db_manager.book_repo.get_book_path(book_id)
    if not root_path:
        logging.warning(f"Audiobookshelf auto-upload skipped for book {book_id}: missing root path.")
        return
    if is_remote_source(root_path):
        logging.info(f"Audiobookshelf auto-upload skipped for book {book_id}: remote source.")
        if announce:
            speak(_("Audiobookshelf upload skipped for remote source books."), LEVEL_MINIMAL)
        return

    server_url = (db_manager.get_setting(SETTING_AUDIOBOOKSHELF_SERVER_URL) or "").strip()
    api_key = (db_manager.get_setting(SETTING_AUDIOBOOKSHELF_API_KEY) or "").strip()
    if not server_url or not api_key:
        logging.info(f"Audiobookshelf auto-upload skipped for book {book_id}: server URL or API key not configured.")
        if announce:
            speak(_("Audiobookshelf upload skipped. Configure server URL and API key in settings."), LEVEL_CRITICAL)
        return

    logging.info(f"Audiobookshelf auto-upload queued for book {book_id}.")
    worker = threading.Thread(
        target=_audiobookshelf_auto_upload_worker,
        args=(book_id, server_url, api_key, announce),
        daemon=True
    )
    worker.start()


def _audiobookshelf_auto_upload_worker(book_id: int, server_url: str, api_key: str, announce: bool):
    try:
        details = db_manager.get_book_details(book_id) or {}
        title = str(details.get("title") or f"Book {book_id}").strip() or f"Book {book_id}"
        author = str(details.get("author") or "").strip() or None

        file_paths = _collect_local_file_paths_for_book(book_id)
        if not file_paths:
            logging.warning(f"Audiobookshelf auto-upload skipped for book {book_id}: no local files found.")
            if announce:
                wx.CallAfter(lambda: speak(_("Audiobookshelf upload skipped. No local files were found."), LEVEL_CRITICAL))
            return

        client = AudiobookshelfClient(server_url, api_key, timeout_seconds=AUDIOBOOKSHELF_UPLOAD_TIMEOUT_SECONDS)
        preferred_library_id = (db_manager.get_setting(SETTING_AUDIOBOOKSHELF_UPLOAD_LIBRARY_ID) or "").strip()
        preferred_folder_id = (db_manager.get_setting(SETTING_AUDIOBOOKSHELF_UPLOAD_FOLDER_ID) or "").strip()
        library_id, folder_id = client.resolve_upload_destination(preferred_library_id, preferred_folder_id)

        client.upload_library_item(
            title=title,
            author=author,
            series=None,
            file_paths=file_paths,
            library_id=library_id,
            folder_id=folder_id
        )
        try:
            client.trigger_library_scan(library_id)
        except AudiobookshelfError as scan_error:
            logging.warning(
                f"Audiobookshelf upload complete for book {book_id}, but library scan trigger failed: {scan_error}"
            )

        # Best-effort mapping so chapter/progress sync can work for local books that were just uploaded.
        try:
            linked_base_url, linked_item_id, linked_api_key = resolve_audiobookshelf_target(
                book_id=book_id,
                root_path=db_manager.book_repo.get_book_path(book_id),
                preferred_stream_url=file_paths[0] if file_paths else None,
                allow_lookup=True,
                timeout_seconds=15,
            )
            if linked_base_url and linked_item_id and linked_api_key:
                logging.info(
                    f"Audiobookshelf link stored for local book {book_id}: item={linked_item_id}, base={linked_base_url}"
                )
        except Exception as link_error:
            logging.warning(f"Audiobookshelf link resolve failed for local book {book_id}: {link_error}")

        logging.info(
            f"Audiobookshelf upload complete for book {book_id}: "
            f"title='{title}', library={library_id}, folder={folder_id}, files={len(file_paths)}"
        )
        if announce:
            wx.CallAfter(lambda: speak(_("Uploaded to Audiobookshelf server."), LEVEL_MINIMAL))
    except AudiobookshelfError as e:
        logging.warning(f"Audiobookshelf upload failed for book {book_id}: {e}")
        if announce:
            wx.CallAfter(lambda: speak(_("Audiobookshelf upload failed."), LEVEL_CRITICAL))
    except Exception as e:
        logging.error(f"Unexpected Audiobookshelf upload error for book {book_id}: {e}", exc_info=True)
        if announce:
            wx.CallAfter(lambda: speak(_("Audiobookshelf upload failed."), LEVEL_CRITICAL))


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
    """Triggers the dialog to add a single media file as a book."""
    if frame.is_busy_processing:
        speak(_("Already scanning. Please wait."), LEVEL_CRITICAL)
        return

    exts = ["*" + ext for ext in book_scanner.SUPPORTED_EXTENSIONS]
    wildcard_str = ";".join(exts)
    wildcard = f"{_('Supported Media Files')} ({wildcard_str})|{wildcard_str}|{_('All Files')} (*.*)|*.*"

    dlg = wx.FileDialog(frame, _("Choose a media file..."),
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
    normalized_file_list = list(file_list or [])
    book_type = infer_book_type_from_file_rows(normalized_file_list)
    filtered_file_list = filter_files_by_book_type(normalized_file_list, book_type)
    if filtered_file_list:
        normalized_file_list = filtered_file_list

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
        book_id = db_manager.add_book(
            book_name,
            book_path,
            normalized_file_list,
            shelf_id,
            book_type=book_type
        )
        return book_id, False

    # Import with metadata
    try:
        imported_title = metadata.get('title', book_name)
        imported_book_type = str(metadata.get('book_type') or book_type).strip().lower()
        if imported_book_type not in {"audio", "ebook"}:
            imported_book_type = book_type
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

        for fp, idx, dur in normalized_file_list:
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
            if len(normalized_file_list) == 1:
                index_map[0] = 0
                found_files_count = 1

        logging.info(f"Import debug: Found {found_files_count} matching files.")

        if found_files_count == 0:
            logging.warning("No matching files found in metadata import. Fallback to normal add.")
            book_id = db_manager.add_book(
                book_name,
                book_path,
                normalized_file_list,
                shelf_id,
                book_type=imported_book_type
            )
            return book_id, False

        new_book_id = db_manager.add_book(
            imported_title,
            book_path,
            normalized_file_list,
            shelf_id,
            book_type=imported_book_type
        )
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
                playback_state.get('is_eq_enabled', False)
            )

        reading_state = metadata.get('reading_state')
        if isinstance(reading_state, dict):
            db_manager.save_reading_state(
                new_book_id,
                reading_state.get('char_offset', 0),
                reading_state.get('total_chars', 0)
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
            schedule_audiobookshelf_auto_upload(frame, book_id, announce=not is_batch)
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
            logging.debug(
                f"Duration worker file count mismatch for book {book_id}: db={len(db_files)} scanned={len(file_list)}"
            )

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
