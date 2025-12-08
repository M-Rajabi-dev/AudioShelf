# frames/player/navigation.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging
from typing import Dict, Any
from database import db_manager
from i18n import _
from nvda_controller import speak, LEVEL_CRITICAL, LEVEL_MINIMAL


def jump_to_bookmark(frame, data: Dict[str, Any]):
    """
    Jumps the playback engine to the file and position specified in the bookmark data.

    Args:
        frame: The parent PlayerFrame.
        data: A dictionary containing bookmark details ('file_index', 'position_ms').
    """
    if not data or not frame.engine:
        return

    target_frame_index = data['file_index']
    position_ms = data['position_ms']

    if not (0 <= target_frame_index < len(frame.book_files_data)):
        logging.error(f"Bookmark jump failed: Invalid frame index {target_frame_index}")
        speak(_("Error: Bookmark refers to a non-existent file."), LEVEL_CRITICAL)
        return

    try:
        target_engine_index = frame.engine_to_frame_index_map.index(target_frame_index)
    except ValueError:
        logging.warning(f"Bookmark jump failed: File index {target_frame_index} is missing from disk.")
        speak(_("Error: The file for this bookmark is missing."), LEVEL_CRITICAL)
        return
    except AttributeError:
        logging.error("Bookmark jump failed: engine_to_frame_index_map not found on frame.")
        return

    try:
        current_engine_index = frame.engine.get_current_file_index()
    except Exception as e:
        logging.error(f"Bookmark jump failed: Could not get current engine index: {e}")
        return

    if target_engine_index == current_engine_index:
        logging.info(f"Bookmark jump: Seeking to {position_ms}ms in same file (Index {target_frame_index})")
        frame.engine.set_time(position_ms)
    else:
        logging.info(
            f"Bookmark jump: Jumping to engine file {target_engine_index} (Frame index {target_frame_index}) and seeking to {position_ms}ms")
        if not frame.engine.playlist_jump(target_engine_index, position_ms):
            logging.error(f"Bookmark jump failed: playlist_jump({target_engine_index}) failed.")
            speak(_("Error: Could not jump to bookmark file."), LEVEL_CRITICAL)


def goto_next_bookmark(frame):
    """Finds and jumps to the next bookmark relative to the current playback position."""
    if not frame.engine:
        return

    try:
        current_time = frame.engine.get_time()
        bookmarks = db_manager.get_bookmarks_for_book(frame.book_id)

        if not bookmarks:
            speak(_("No bookmarks in this book."), LEVEL_MINIMAL)
            return

        time_buffer_ms = 1000
        for bm in bookmarks:
            is_after = False
            if bm['file_index'] > frame.current_file_index:
                is_after = True
            elif bm['file_index'] == frame.current_file_index and bm['position_ms'] > (current_time + time_buffer_ms):
                is_after = True

            if is_after:
                title = bm['title'] or _("(No Title)")
                speak(_("Next bookmark: {0}").format(title), LEVEL_MINIMAL)
                jump_to_bookmark(frame, bm)
                return

        speak(_("End of bookmarks reached."), LEVEL_MINIMAL)
    except Exception as e:
        logging.error(f"Error in goto_next_bookmark: {e}", exc_info=True)
        speak(_("Error finding next bookmark."), LEVEL_CRITICAL)


def goto_prev_bookmark(frame):
    """Finds and jumps to the previous bookmark relative to the current playback position."""
    if not frame.engine:
        return

    try:
        current_time = frame.engine.get_time()
        bookmarks = db_manager.get_bookmarks_for_book(frame.book_id)

        if not bookmarks:
            speak(_("No bookmarks in this book."), LEVEL_MINIMAL)
            return

        time_buffer_ms = 1000
        for bm in reversed(bookmarks):
            is_before = False
            if bm['file_index'] < frame.current_file_index:
                is_before = True
            elif bm['file_index'] == frame.current_file_index and bm['position_ms'] < (current_time - time_buffer_ms):
                is_before = True

            if is_before:
                title = bm['title'] or _("(No Title)")
                speak(_("Previous bookmark: {0}").format(title), LEVEL_MINIMAL)
                jump_to_bookmark(frame, bm)
                return

        speak(_("Start of bookmarks reached."), LEVEL_MINIMAL)
    except Exception as e:
        logging.error(f"Error in goto_prev_bookmark: {e}", exc_info=True)
        speak(_("Error finding previous bookmark."), LEVEL_CRITICAL)


def goto_next_book_in_library(frame):
    """Loads the next book from the current library playlist context."""
    if not frame.book_loader:
        logging.error("goto_next_book: frame.book_loader is not initialized.")
        return

    if not frame.library_playlist or len(frame.library_playlist) <= 1:
        speak(_("Only one book in list."), LEVEL_MINIMAL)
        return

    new_index = frame.current_playlist_index + 1
    if new_index >= len(frame.library_playlist):
        speak(_("End of library list reached."), LEVEL_MINIMAL)
        return

    try:
        new_book_id, new_book_title = frame.library_playlist[new_index]
        speak(_("Next book: {0}").format(new_book_title), LEVEL_CRITICAL)
        
        frame.current_playlist_index = new_index
        frame.book_loader.load_new_book(new_book_id, new_book_title)
    except IndexError:
        logging.error(f"goto_next_book: Index {new_index} out of bounds for library_playlist.")
        speak(_("Error switching book."), LEVEL_CRITICAL)
    except Exception as e:
        logging.error(f"Error in goto_next_book: {e}", exc_info=True)
        speak(_("Error switching book."), LEVEL_CRITICAL)


def goto_prev_book_in_library(frame):
    """Loads the previous book from the current library playlist context."""
    if not frame.book_loader:
        logging.error("goto_prev_book: frame.book_loader is not initialized.")
        return

    if not frame.library_playlist or len(frame.library_playlist) <= 1:
        speak(_("Only one book in list."), LEVEL_MINIMAL)
        return

    new_index = frame.current_playlist_index - 1
    if new_index < 0:
        speak(_("Start of library list reached."), LEVEL_MINIMAL)
        return

    try:
        new_book_id, new_book_title = frame.library_playlist[new_index]
        speak(_("Previous book: {0}").format(new_book_title), LEVEL_CRITICAL)
        
        frame.current_playlist_index = new_index
        frame.book_loader.load_new_book(new_book_id, new_book_title)
    except IndexError:
        logging.error(f"goto_prev_book: Index {new_index} out of bounds for library_playlist.")
        speak(_("Error switching book."), LEVEL_CRITICAL)
    except Exception as e:
        logging.error(f"Error in goto_prev_book: {e}", exc_info=True)
        speak(_("Error switching book."), LEVEL_CRITICAL)


def play_pinned_book_by_index(frame, index: int):
    """
    Plays a pinned book by its 0-based index.
    Updates the playlist context to be the list of pinned books.

    Args:
        frame: The parent PlayerFrame.
        index: The 0-based index of the pinned book to play.
    """
    if not frame.book_loader:
        return

    try:
        pinned_books = db_manager.book_repo.get_pinned_books()
        if index < 0 or index >= len(pinned_books):
            speak(_("No pinned book at position {0}.").format(index + 1), LEVEL_MINIMAL)
            return

        book_id, book_title, shelf_id = pinned_books[index]
        if book_id == frame.book_id:
            speak(_("Already playing: {0}").format(book_title), LEVEL_MINIMAL)
            return

        speak(_("Playing pinned book: {0}").format(book_title), LEVEL_MINIMAL)

        # Update context to pinned list
        new_playlist_context = [(b[0], b[1]) for b in pinned_books]
        frame.library_playlist = new_playlist_context
        frame.current_playlist_index = index
        
        frame.book_loader.load_new_book(book_id, book_title)

    except Exception as e:
        logging.error(f"Error in play_pinned_book_by_index: {e}", exc_info=True)
        speak(_("Error switching to pinned book."), LEVEL_CRITICAL)
