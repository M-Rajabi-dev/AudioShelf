# frames/library/actions/metadata_actions.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import wx
import os
import json
import logging
from database import db_manager
from i18n import _
from nvda_controller import speak, LEVEL_CRITICAL, LEVEL_MINIMAL
from . import action_utils

METADATA_FILENAME_DIR = ".audioshelf_metadata.json"
METADATA_VERSION = 2


def on_context_export_data(frame, event, source='library'):
    """
    Saves book metadata (state, bookmarks, details) to a JSON file in the source location.
    Supports both directories and single files.
    """
    selected_books = action_utils.get_selected_book_data_list(frame, source)
    if len(selected_books) > 1:
        speak(_("Cannot save data for multiple items at once."), LEVEL_CRITICAL)
        return

    book_info = action_utils.get_focused_book_info(frame, source)
    if not book_info:
        return

    book_id, book_title = book_info
    speak(_("Saving data for {0}...").format(book_title), LEVEL_MINIMAL)
    wx.BeginBusyCursor()

    try:
        details = db_manager.book_repo.get_book_details(book_id)
        if not details:
            speak(_("Error: Book details not found."), LEVEL_CRITICAL)
            return

        root_path = details['root_path']
        if not os.path.exists(root_path):
            speak(_("Source location not found."), LEVEL_CRITICAL)
            return

        is_dir = os.path.isdir(root_path)
        if not is_dir:
            output_path = root_path + ".json"
        else:
            output_path = os.path.join(root_path, METADATA_FILENAME_DIR)

        playback_state = db_manager.playback_repo.get_playback_state(book_id)
        bookmarks = db_manager.playback_repo.get_bookmarks_for_book(book_id)
        files_db = db_manager.book_repo.get_book_files(book_id)

        files_export = []
        
        # Robust file path handling
        if is_dir:
            clean_root = os.path.normpath(root_path)
            for fid, fpath, findex, fduration in files_db:
                try:
                    # Try relative path
                    clean_fpath = os.path.normpath(fpath)
                    rel_path = os.path.relpath(clean_fpath, clean_root).replace('\\', '/')
                    files_export.append({"index": findex, "relative_path": rel_path})
                except ValueError:
                    # Fallback: just store basename if relpath fails (e.g. different drives)
                    # This is risky but better than empty list
                    logging.warning(f"Could not calculate relpath for {fpath}. Using basename.")
                    files_export.append({"index": findex, "relative_path": os.path.basename(fpath)})
        else:
            # For single file, we just store the file info, relative path is trivial
            files_export.append({"index": 0, "relative_path": os.path.basename(root_path)})

        bookmarks_export = []
        for bm in bookmarks:
            bookmarks_export.append({
                "file_index": bm["file_index"],
                "position_ms": bm["position_ms"],
                "title": bm.get("title", ""),
                "note": bm.get("note", "")
            })

        export_data = {
            "version": METADATA_VERSION,
            "db_id": book_id,
            "title": details.get('title'),
            "author": details.get('author'),
            "narrator": details.get('narrator'),
            "genre": details.get('genre'),
            "description": details.get('description'),
            "is_finished": bool(details.get('is_finished')),
            "is_pinned": bool(details.get('is_pinned')),
            "playback_state": playback_state if playback_state else {},
            "bookmarks": bookmarks_export,
            "files": files_export
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=4, ensure_ascii=False)

        logging.info(f"Successfully saved data for book {book_id} to {output_path}")
        speak(_("Book data saved to source."), LEVEL_CRITICAL)

    except Exception as e:
        logging.error(f"Error saving book data for ID {book_id}: {e}", exc_info=True)
        speak(_("Error saving data. Check logs."), LEVEL_CRITICAL)

    finally:
        if wx.IsBusy():
            wx.EndBusyCursor()
