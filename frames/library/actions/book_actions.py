# frames/library/actions/book_actions.py
# Copyright (c) 2025-2026 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import wx
import os
import sys
import subprocess
import shutil
import logging
import threading
import re
from urllib.parse import urlparse, unquote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from database import db_manager
from i18n import _, ngettext
from nvda_controller import speak, LEVEL_CRITICAL, LEVEL_MINIMAL
from dialogs import properties_dialog
from dialogs.confirm_dialog import CheckboxConfirmDialog

from . import action_utils
from .. import list_manager
from .. import history_manager
from .. import search_handlers
from .. import task_handlers
from db_layer.helpers import is_remote_source
from .. import chapter_selector


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


def on_context_play_from_chapter(frame, event, source='library'):
    selected_books = action_utils.get_selected_book_data_list(frame, source)
    if len(selected_books) > 1:
        speak(_("Cannot open chapters for multiple books at once."), LEVEL_CRITICAL)
        return

    book_info = action_utils.get_focused_book_info(frame, source)
    if not book_info:
        return

    book_id, _book_title = book_info
    start_ms = chapter_selector.prompt_abs_chapter_start(
        parent=frame,
        book_id=book_id,
        current_total_position_ms=0,
        announce_if_unavailable=True
    )
    if start_ms is None:
        return

    frame.pending_initial_seek_book_id = book_id
    frame.pending_initial_seek_ms = start_ms
    on_context_play(frame, event, source=source)


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

    if is_remote_source(book_path):
        speak(_("This book is streamed from Audiobookshelf and has no local folder."), LEVEL_MINIMAL)
        return

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
    current_path = db_manager.book_repo.get_book_path(book_id)
    if is_remote_source(current_path):
        speak(_("Cannot update location for Audiobookshelf server items."), LEVEL_CRITICAL)
        return

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


def _safe_path_component(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", (name or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned[:120]


def _derive_item_short_id(root_path: str) -> str:
    if not root_path:
        return "item"
    marker = "/item/"
    idx = root_path.rfind(marker)
    if idx == -1:
        return "item"
    return root_path[idx + len(marker): idx + len(marker) + 8] or "item"


def _guess_filename_from_url(url: str, index: int) -> str:
    parsed = urlparse(url)
    raw_name = unquote(os.path.basename(parsed.path or "")).strip()
    if not raw_name:
        return f"track_{index + 1:03d}.m4b"

    stem, ext = os.path.splitext(raw_name)
    if not ext:
        ext = ".m4b"

    safe_stem = _safe_path_component(stem) or f"track_{index + 1:03d}"
    safe_ext = re.sub(r"[^A-Za-z0-9.]", "", ext) or ".m4b"
    if not safe_ext.startswith("."):
        safe_ext = "." + safe_ext
    return f"{safe_stem}{safe_ext[:10]}"


def _download_url_to_file(url: str, destination_path: str):
    tmp_path = destination_path + ".part"
    req = Request(url=url, method="GET")

    try:
        with urlopen(req, timeout=120) as response, open(tmp_path, "wb") as out:
            while True:
                chunk = response.read(1024 * 512)
                if not chunk:
                    break
                out.write(chunk)
        os.replace(tmp_path, destination_path)
    except (HTTPError, URLError, OSError) as e:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        raise RuntimeError(str(e)) from e


def on_context_download_from_server(frame, event, source='library'):
    if frame.is_busy_processing:
        speak(_("Already processing. Please wait."), LEVEL_CRITICAL)
        return

    selected_books = action_utils.get_selected_book_data_list(frame, source)
    if not selected_books:
        focused_book = action_utils.get_focused_book_info(frame, source)
        if focused_book:
            selected_books = [focused_book]
        else:
            return

    remote_books = []
    for (book_id, book_title) in selected_books:
        book_path = db_manager.book_repo.get_book_path(book_id)
        if is_remote_source(book_path):
            remote_books.append((book_id, book_title, book_path))

    if not remote_books:
        speak(_("No streamed server books selected."), LEVEL_MINIMAL)
        return

    default_dir = db_manager.get_setting("audiobookshelf_download_dir") or os.path.join(
        os.path.expanduser("~"), "Downloads", "AudioShelf"
    )
    dlg = wx.DirDialog(
        frame,
        _("Choose where downloaded books should be saved:"),
        defaultPath=default_dir,
        style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
    )
    try:
        if dlg.ShowModal() != wx.ID_OK:
            speak(_("Download cancelled."), LEVEL_MINIMAL)
            return
        download_root = dlg.GetPath().strip()
    finally:
        dlg.Destroy()

    if not download_root:
        speak(_("Download folder is required."), LEVEL_CRITICAL)
        return

    db_manager.set_setting("audiobookshelf_download_dir", download_root)

    frame.is_busy_processing = True
    wx.BeginBusyCursor()
    speak(_("Downloading {0} books...").format(len(remote_books)), LEVEL_MINIMAL)

    thread = threading.Thread(
        target=_download_remote_books_worker,
        args=(frame, remote_books, download_root),
        daemon=True
    )
    thread.start()


def _download_remote_books_worker(frame, remote_books, download_root):
    downloaded_count = 0
    failed_count = 0
    skipped_count = 0

    for (book_id, book_title, root_path) in remote_books:
        try:
            files_data = db_manager.get_book_files(book_id)
            if not files_data:
                skipped_count += 1
                continue

            short_id = _derive_item_short_id(root_path)
            safe_title = _safe_path_component(book_title) or f"Book_{book_id}"
            target_book_dir = os.path.join(download_root, f"{safe_title} [ABS-{short_id}]")
            os.makedirs(target_book_dir, exist_ok=True)

            new_file_list = []
            used_names = set()
            for row_index, (_file_id, file_url, file_index, duration_ms) in enumerate(files_data):
                filename = _guess_filename_from_url(file_url, row_index)
                stem, ext = os.path.splitext(filename)
                candidate = filename
                n = 2
                while candidate.lower() in used_names:
                    candidate = f"{stem} ({n}){ext}"
                    n += 1
                used_names.add(candidate.lower())

                local_path = os.path.join(target_book_dir, candidate)
                if not os.path.exists(local_path) or os.path.getsize(local_path) == 0:
                    _download_url_to_file(file_url, local_path)

                new_file_list.append((local_path, file_index, duration_ms or 0))

            new_file_list.sort(key=lambda x: x[1])
            db_manager.update_book_source(book_id, target_book_dir, new_file_list)
            downloaded_count += 1

        except Exception as e:
            logging.error(f"Failed to download book '{book_title}' (ID {book_id}): {e}", exc_info=True)
            failed_count += 1

    wx.CallAfter(_finalize_remote_download, frame, downloaded_count, failed_count, skipped_count)


def _finalize_remote_download(frame, downloaded_count, failed_count, skipped_count):
    task_handlers._reset_busy_state(frame)
    action_utils.refresh_all_views(frame)

    parts = []
    if downloaded_count:
        parts.append(_("{0} downloaded").format(downloaded_count))
    if skipped_count:
        parts.append(_("{0} skipped").format(skipped_count))
    if failed_count:
        parts.append(_("{0} failed").format(failed_count))

    if not parts:
        speak(_("No books were downloaded."), LEVEL_MINIMAL)
        return

    level = LEVEL_CRITICAL if (downloaded_count or failed_count) else LEVEL_MINIMAL
    speak(_("Download complete: {0}.").format(", ".join(parts)), level)


def on_context_delete_book(frame, event, source='library'):
    books_to_delete = action_utils.get_selected_book_data_list(frame, source)

    if not books_to_delete:
        focused_book = action_utils.get_focused_book_info(frame, source)
        if focused_book:
            books_to_delete = [focused_book]
        else:
            return

    count = len(books_to_delete)
    msg = ngettext(
        "Are you sure you want to remove '{0}' from your library? (Files will NOT be deleted)",
        "Are you sure you want to remove {0} books from your library? (Files will NOT be deleted)",
        count
    ).format(books_to_delete[0][1] if count == 1 else count)
    
    if wx.MessageBox(msg, _("Confirm Remove"), wx.YES_NO | wx.CANCEL | wx.ICON_WARNING | wx.YES_DEFAULT, parent=frame) != wx.YES:
        return

    try:
        for (book_id, book_title) in books_to_delete:
            db_manager.book_repo.delete_book(book_id)
            logging.info(f"Deleted book: {book_title} (ID: {book_id})")

        msg_success = ngettext(
            "Book removed from library.",
            "{0} books removed from library.",
            count
        ).format(count)
        speak(msg_success, LEVEL_CRITICAL)
            
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
    msg = ngettext(
        "WARNING: You are about to permanently delete '{0}' and all its files from your computer.\nThis action CANNOT be undone.",
        "WARNING: You are about to permanently delete {0} books and all their files from your computer.\nThis action CANNOT be undone.",
        count
    ).format(books_to_delete[0][1] if count == 1 else count)

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
            msg_success = ngettext(
                "{0} book deleted permanently.",
                "{0} books deleted permanently.",
                deleted_count
            ).format(deleted_count)
            speak(msg_success, LEVEL_CRITICAL)
            
        if failed_count > 0:
            msg_fail = ngettext(
                "{0} book failed to delete.",
                "{0} books failed to delete.",
                failed_count
            ).format(failed_count)
            speak(msg_fail, LEVEL_CRITICAL)

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
        msg = ngettext(
            "Book pinned.",
            "{0} books pinned.",
            count
        ).format(count)
        speak(msg, LEVEL_CRITICAL)
            
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
        msg = ngettext(
            "Book unpinned.",
            "{0} books unpinned.",
            count
        ).format(count)
        speak(msg, LEVEL_CRITICAL)
            
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
        msg = ngettext(
            "Marked as finished.",
            "{0} books marked as finished.",
            count
        ).format(count)
        speak(msg, LEVEL_CRITICAL)
        
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
        msg = ngettext(
            "Marked as unfinished.",
            "{0} books marked as unfinished.",
            count
        ).format(count)
        speak(msg, LEVEL_CRITICAL)
        
        action_utils.refresh_all_views(frame)
    except Exception:
        speak(_("Error updating book status."), LEVEL_CRITICAL)
