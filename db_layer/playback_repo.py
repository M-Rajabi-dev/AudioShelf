# db_layer/playback_repo.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import logging
import sqlite3
import datetime
from typing import Dict, Optional, List, Any


class PlaybackRepository:
    """
    Manages database interactions for playback state and bookmarks.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_playback_state(self, book_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves the saved playback state (position, speed, audio settings) for a specific book.

        Args:
            book_id: The ID of the book.

        Returns:
            A dictionary containing playback state details, or None if not found.
        """
        if self.conn is None:
            return None

        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT 
                    last_file_index, 
                    last_position_ms, 
                    last_speed_rate,
                    last_eq_settings,
                    is_eq_enabled,
                    last_nr_mode
                FROM playback_state 
                WHERE book_id = ?
                """,
                (book_id,)
            )
            result = cur.fetchone()
            if result:
                return {
                    "last_file_index": result[0],
                    "last_position_ms": result[1],
                    "last_speed_rate": result[2],
                    "last_eq_settings": result[3],
                    "is_eq_enabled": bool(result[4]),
                    "last_nr_mode": result[5]
                }
            return None
        except sqlite3.Error as e:
            logging.warning(f"Error getting playback state: {e}", exc_info=True)
            return None
        finally:
            if cur:
                cur.close()

    def save_playback_state(
            self,
            book_id: int,
            file_index: int,
            position_ms: int,
            speed_rate: float,
            eq_settings: str,
            is_eq_enabled: bool,
            nr_mode: int
    ):
        """
        Saves the current playback state and updates the last played timestamp for the book.
        """
        if self.conn is None:
            return
        try:
            now = datetime.datetime.now()

            with self.conn:
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO playback_state
                    (
                        book_id, last_file_index, last_position_ms, last_speed_rate,
                        last_eq_settings, is_eq_enabled, last_nr_mode
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        book_id, file_index, position_ms, speed_rate,
                        eq_settings, is_eq_enabled, nr_mode
                    )
                )
                self.conn.execute(
                    "UPDATE books SET last_played_timestamp = ? WHERE id = ?",
                    (now, book_id)
                )
        except sqlite3.Error as e:
            logging.error(f"Error saving playback state/timestamp: {e}", exc_info=True)

    def add_bookmark(self, book_id: int, file_index: int, position_ms: int, title: str, note: str) -> Optional[int]:
        """
        Adds a new bookmark for a specific book and file position.

        Returns:
            The ID of the new bookmark, or None on failure.
        """
        if self.conn is None:
            return None

        cur = None
        try:
            with self.conn:
                cur = self.conn.cursor()
                cur.execute(
                    "INSERT INTO bookmarks (book_id, file_index, position_ms, title, note) VALUES (?, ?, ?, ?, ?)",
                    (book_id, file_index, position_ms, title, note)
                )
                return cur.lastrowid
        except sqlite3.Error as e:
            logging.error(f"Error adding bookmark: {e}", exc_info=True)
            return None
        finally:
            if cur:
                cur.close()

    def get_bookmarks_for_book(self, book_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves all bookmarks associated with a specific book.
        """
        if self.conn is None:
            return []

        query = """
        SELECT 
            b.id, b.book_id, b.file_index, pf.file_path, b.position_ms, b.title, b.note
        FROM bookmarks b
        LEFT JOIN playable_files pf ON b.book_id = pf.book_id AND b.file_index = pf.file_index
        WHERE b.book_id = ?
        ORDER BY b.file_index, b.position_ms
        """
        results = []
        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute(query, (book_id,))
            for row in cur.fetchall():
                results.append({
                    "id": row[0],
                    "book_id": row[1],
                    "file_index": row[2],
                    "file_path": row[3] or "File Missing?",
                    "position_ms": row[4],
                    "title": row[5],
                    "note": row[6]
                })
            return results
        except sqlite3.Error as e:
            logging.error(f"Error getting bookmarks for book: {e}", exc_info=True)
            return []
        finally:
            if cur:
                cur.close()

    def delete_bookmark(self, bookmark_id: int):
        """Deletes a specific bookmark by its ID."""
        if self.conn is None:
            return
        try:
            with self.conn:
                self.conn.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
        except sqlite3.Error as e:
            logging.error(f"Error deleting bookmark: {e}", exc_info=True)