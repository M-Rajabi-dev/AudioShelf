# db_layer/playback_repo.py
# Copyright (c) 2025-2026 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging
import sqlite3
import datetime
from typing import Dict, Optional, List, Any
from i18n import _

class PlaybackRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_playback_state(self, book_id: int) -> Optional[Dict[str, Any]]:
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
                    last_played_at
                FROM playback_state 
                WHERE book_id = ?
                """,
                (book_id,)
            )
            row = cur.fetchone()
            if row:
                return {
                    "last_file_index": row[0],
                    "last_position_ms": row[1],
                    "last_speed_rate": row[2],
                    "last_eq_settings": row[3],
                    "is_eq_enabled": bool(row[4]),
                    "last_played_at": row[5]
                }
            return None
        except sqlite3.Error as e:
            logging.error(f"Error getting playback state: {e}", exc_info=True)
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
            is_eq_enabled: bool
    ):
        if self.conn is None:
            return
        try:
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            with self.conn:
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO playback_state
                    (
                        book_id, last_file_index, last_position_ms, last_speed_rate,
                        last_eq_settings, is_eq_enabled, last_played_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        book_id, file_index, position_ms, speed_rate,
                        eq_settings, is_eq_enabled, now
                    )
                )
                self.conn.execute(
                    "UPDATE books SET last_played_timestamp = ? WHERE id = ?",
                    (now, book_id)
                )
        except sqlite3.Error as e:
            logging.error(f"Error saving playback state: {e}", exc_info=True)

    def get_reading_state(self, book_id: int) -> Optional[Dict[str, Any]]:
        if self.conn is None:
            return None

        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT char_offset, total_chars, last_read_at
                FROM reading_state
                WHERE book_id = ?
                """,
                (book_id,)
            )
            row = cur.fetchone()
            if row:
                return {
                    "char_offset": int(row[0] or 0),
                    "total_chars": int(row[1] or 0),
                    "last_read_at": row[2]
                }
            return None
        except sqlite3.Error as e:
            logging.error(f"Error getting reading state: {e}", exc_info=True)
            return None
        finally:
            if cur:
                cur.close()

    def save_reading_state(self, book_id: int, char_offset: int, total_chars: int):
        if self.conn is None:
            return

        char_offset = max(0, int(char_offset or 0))
        total_chars = max(0, int(total_chars or 0))

        try:
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO reading_state (book_id, char_offset, total_chars, last_read_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(book_id) DO UPDATE SET
                        char_offset=excluded.char_offset,
                        total_chars=excluded.total_chars,
                        last_read_at=excluded.last_read_at
                    """,
                    (book_id, char_offset, total_chars, now)
                )
                self.conn.execute(
                    "UPDATE books SET last_played_timestamp = ? WHERE id = ?",
                    (now, book_id)
                )
        except sqlite3.Error as e:
            logging.error(f"Error saving reading state: {e}", exc_info=True)

    def add_bookmark(self, book_id: int, file_index: int, position_ms: int, title: str, note: str) -> Optional[int]:
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
                    "file_path": row[3] or _("File Missing?"),
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
        if self.conn is None:
            return
        try:
            with self.conn:
                self.conn.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
        except sqlite3.Error as e:
            logging.error(f"Error deleting bookmark: {e}", exc_info=True)
