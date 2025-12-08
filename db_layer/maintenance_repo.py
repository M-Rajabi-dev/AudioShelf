# db_layer/maintenance_repo.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging
import sqlite3
from typing import List, Tuple


class MaintenanceRepository:
    """
    Manages library maintenance tasks including pruning missing books and clearing the library.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_all_books_for_pruning(self) -> List[Tuple[int, str, str]]:
        """
        Retrieves a list of all books to check if their source folders still exist.

        Returns:
            A list of tuples containing (book_id, title, root_path).
        """
        if self.conn is None:
            return []

        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT id, title, root_path FROM books")
            results = cur.fetchall()
            return [(row[0], row[1], row[2]) for row in results]
        except sqlite3.Error as e:
            logging.error(f"Error getting all books for pruning: {e}", exc_info=True)
            return []
        finally:
            if cur:
                cur.close()

    def prune_missing_books(self, missing_book_ids: List[int]) -> int:
        """
        Deletes the specified books from the database.

        Args:
            missing_book_ids: A list of book IDs to remove.

        Returns:
            The number of rows deleted.
        """
        if self.conn is None or not missing_book_ids:
            return 0

        cur = None
        try:
            with self.conn:
                placeholders = ', '.join('?' * len(missing_book_ids))
                query = f"DELETE FROM books WHERE id IN ({placeholders})"
                cur = self.conn.cursor()
                cur.execute(query, missing_book_ids)
                return cur.rowcount
        except sqlite3.Error as e:
            logging.error(f"Error pruning books: {e}", exc_info=True)
            raise
        finally:
            if cur:
                cur.close()

    def clear_library(self):
        """
        Deletes ALL books and ALL custom shelves from the database.
        The default shelf (ID 1) is preserved.
        """
        if self.conn is None:
            return
        try:
            logging.info("Starting full library clearance...")
            with self.conn:
                self.conn.execute("DELETE FROM books")
                self.conn.execute("DELETE FROM shelves WHERE id != 1")
            logging.info("Library cleared successfully.")
        except sqlite3.Error as e:
            logging.critical(f"CRITICAL Error clearing library: {e}", exc_info=True)
            raise