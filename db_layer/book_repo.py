# db_layer/book_repo.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import logging
import sqlite3
from typing import Dict, Optional, List, Any, Tuple


class BookRepository:
    """
    Manages database interactions for books and their associated playable files.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add_book(self, title: str, root_path: str, file_list: List[Tuple[str, int, int]], shelf_id: int = 1) -> \
            Optional[int]:
        """
        Adds a new book and its files to the database.

        Args:
            title: The title of the book.
            root_path: The absolute path to the book's folder.
            file_list: A list of tuples (file_path, file_index, duration_ms).
            shelf_id: The ID of the shelf to add the book to.

        Returns:
            The new book ID if successful, None otherwise.
        """
        if self.conn is None:
            logging.error("BookRepository: Cannot add book: DB connection not established.")
            return None

        cur = None
        try:
            with self.conn:
                cur = self.conn.cursor()
                cur.execute(
                    "INSERT INTO books (title, root_path, shelf_id) VALUES (?, ?, ?)",
                    (title, root_path, shelf_id)
                )
                book_id = cur.lastrowid

                if book_id and file_list:
                    files_data = [
                        (book_id, file_path, file_index, duration_ms)
                        for file_path, file_index, duration_ms in file_list
                    ]
                    cur.executemany(
                        "INSERT INTO playable_files (book_id, file_path, file_index, duration_ms) VALUES (?, ?, ?, ?)",
                        files_data
                    )
                return book_id

        except sqlite3.IntegrityError as e:
            if "books.root_path" in str(e):
                logging.warning(f"Error: Book path '{root_path}' already exists.")
            elif "playable_files.file_path" in str(e):
                logging.error(f"Error: File path conflict for book '{title}': {e}")
            else:
                logging.error(f"Error adding book (IntegrityError): {e}", exc_info=True)
            return None
        except sqlite3.Error as e:
            logging.error(f"Error adding book transaction: {e}", exc_info=True)
            return None
        finally:
            if cur:
                cur.close()

    def get_book_files(self, book_id: int) -> List[Tuple[int, str, int, int]]:
        """Retrieves all playable files associated with a book."""
        if self.conn is None:
            return []

        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT id, file_path, file_index, duration_ms FROM playable_files WHERE book_id = ? ORDER BY file_index",
                (book_id,)
            )
            return cur.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error fetching book files: {e}", exc_info=True)
            return []
        finally:
            if cur:
                cur.close()

    def delete_book(self, book_id: int):
        """Deletes a book and its associated data from the database."""
        if self.conn is None:
            return
        try:
            with self.conn:
                self.conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        except sqlite3.Error as e:
            logging.error(f"Error deleting book: {e}", exc_info=True)

    def get_book_path(self, book_id: int) -> Optional[str]:
        """Retrieves the root path for a given book ID."""
        if self.conn is None:
            return None

        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT root_path FROM books WHERE id = ?", (book_id,))
            result = cur.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            logging.error(f"Error getting book path: {e}", exc_info=True)
            return None
        finally:
            if cur:
                cur.close()

    def update_book_source(self, book_id: int, new_root_path: str, new_file_list: List[Tuple[str, int, int]]):
        """Updates the root path and file list for an existing book."""
        if self.conn is None:
            return
        try:
            with self.conn:
                cur = self.conn.cursor()
                cur.execute("DELETE FROM playable_files WHERE book_id = ?", (book_id,))

                if new_file_list:
                    files_data = [
                        (book_id, file_index, file_path, duration_ms)
                        for file_path, file_index, duration_ms in new_file_list
                    ]
                    cur.executemany(
                        "INSERT INTO playable_files (book_id, file_index, file_path, duration_ms) VALUES (?, ?, ?, ?)",
                        files_data
                    )

                cur.execute(
                    "UPDATE books SET root_path = ? WHERE id = ?",
                    (new_root_path, book_id)
                )
        except sqlite3.Error as e:
            logging.error(f"Error in update_book_source transaction: {e}", exc_info=True)
            raise

    def rename_book(self, book_id: int, new_name: str):
        """Updates the title of a book."""
        if self.conn is None:
            return
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE books SET title = ? WHERE id = ?",
                    (new_name, book_id)
                )
        except sqlite3.Error as e:
            logging.error(f"Error renaming book: {e}", exc_info=True)
            raise

    def get_book_shelf(self, book_id: int) -> Optional[int]:
        """Retrieves the shelf ID for a given book."""
        if self.conn is None:
            return None

        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT shelf_id FROM books WHERE id = ?", (book_id,))
            result = cur.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            logging.error(f"Error getting book shelf: {e}", exc_info=True)
            return None
        finally:
            if cur:
                cur.close()

    def get_book_details(self, book_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves all column data for a specific book as a dictionary."""
        if self.conn is None:
            return None

        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT * FROM books WHERE id = ?", (book_id,))
            row = cur.fetchone()

            if row:
                col_names = [desc[0] for desc in cur.description]
                return dict(zip(col_names, row))

            return None
        except sqlite3.Error as e:
            logging.error(f"Error getting book details for ID {book_id}: {e}", exc_info=True)
            return None
        finally:
            if cur:
                cur.close()

    def update_file_duration(self, file_id: int, duration_ms: int):
        """Updates the duration of a specific file."""
        if self.conn is None:
            return
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE playable_files SET duration_ms = ? WHERE id = ?",
                    (duration_ms, file_id)
                )
            logging.debug(f"Updated duration for file_id {file_id} to {duration_ms}ms")
        except sqlite3.Error as e:
            logging.error(f"Error updating file duration for file_id {file_id}: {e}", exc_info=True)
            raise

    def update_file_duration_batch(self, updates: List[Tuple[int, int]]):
        """
        Updates durations for multiple files efficiently.

        Args:
            updates: List of (file_id, duration_ms).
        """
        if self.conn is None or not updates:
            return
        try:
            data_to_update = [(duration, file_id) for file_id, duration in updates]
            with self.conn:
                self.conn.executemany(
                    "UPDATE playable_files SET duration_ms = ? WHERE id = ?",
                    data_to_update
                )
        except sqlite3.Error as e:
            logging.error(f"Error batch updating file durations: {e}", exc_info=True)
            raise

    def get_reading_desk_book(self) -> Optional[Tuple[int, str, int]]:
        """Retrieves the most recently played book."""
        if self.conn is None:
            return None

        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT id, title, shelf_id FROM books
                WHERE last_played_timestamp IS NOT NULL
                ORDER BY last_played_timestamp DESC
                LIMIT 1
                """
            )
            result = cur.fetchone()
            return result if result else None
        except sqlite3.Error as e:
            logging.error(f"Error fetching reading desk book: {e}", exc_info=True)
            return None
        finally:
            if cur:
                cur.close()

    def get_history_books(self, limit: int = 50) -> List[Tuple[int, str, int]]:
        """
        Retrieves a list of recently played books.

        Args:
            limit: Maximum number of history items to return.
        """
        if self.conn is None:
            return []

        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT id, title, shelf_id FROM books
                WHERE last_played_timestamp IS NOT NULL
                ORDER BY last_played_timestamp DESC
                LIMIT ?
                """,
                (limit,)
            )
            return cur.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error fetching history books: {e}", exc_info=True)
            return []
        finally:
            if cur:
                cur.close()

    def search_books(self, term: str) -> List[Tuple[int, str, int]]:
        """Searches for books by title, author, or narrator."""
        if self.conn is None:
            return []

        search_query = f"%{term}%"
        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT id, title, shelf_id FROM books
                WHERE title LIKE ? OR author LIKE ? OR narrator LIKE ?
                ORDER BY title ASC
                """,
                (search_query, search_query, search_query)
            )
            return cur.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error searching books for term '{term}': {e}", exc_info=True)
            return []
        finally:
            if cur:
                cur.close()

    def get_all_books(self) -> List[Tuple[int, str, int]]:
        """Retrieves all books in the library, sorted by title."""
        if self.conn is None:
            return []

        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT id, title, shelf_id FROM books
                ORDER BY title ASC
                """
            )
            return cur.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error fetching all books: {e}", exc_info=True)
            return []
        finally:
            if cur:
                cur.close()

    def get_pinned_books(self) -> List[Tuple[int, str, int]]:
        """Retrieves all pinned books, sorted by user-defined pin order."""
        if self.conn is None:
            return []

        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT id, title, shelf_id FROM books
                WHERE is_pinned = 1
                ORDER BY pin_order ASC, title ASC
                """
            )
            return cur.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error fetching pinned books: {e}", exc_info=True)
            return []
        finally:
            if cur:
                cur.close()

    def pin_book(self, book_id: int):
        """Marks a book as pinned and assigns it a pin order."""
        if self.conn is None:
            return
        try:
            with self.conn:
                cur = self.conn.cursor()
                cur.execute("SELECT MAX(pin_order) FROM books")
                max_order = cur.fetchone()[0]
                new_order = (max_order or 0) + 1

                cur.execute(
                    "UPDATE books SET is_pinned = 1, pin_order = ? WHERE id = ?",
                    (new_order, book_id)
                )
        except sqlite3.Error as e:
            logging.error(f"Error pinning book {book_id}: {e}", exc_info=True)
            raise

    def unpin_book(self, book_id: int):
        """Unmarks a book as pinned."""
        if self.conn is None:
            return
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE books SET is_pinned = 0, pin_order = 0 WHERE id = ?",
                    (book_id,)
                )
        except sqlite3.Error as e:
            logging.error(f"Error unpinning book {book_id}: {e}", exc_info=True)
            raise

    def move_pinned_book_up(self, book_id: int):
        """Moves a pinned book up in the sort order."""
        if self.conn is None:
            return
        try:
            with self.conn:
                cur = self.conn.cursor()
                cur.execute("SELECT pin_order FROM books WHERE id = ?", (book_id,))
                current_order_row = cur.fetchone()
                if not current_order_row:
                    return
                current_order = current_order_row[0]

                cur.execute(
                    """
                    SELECT id, pin_order FROM books
                    WHERE is_pinned = 1 AND pin_order < ?
                    ORDER BY pin_order DESC
                    LIMIT 1
                    """,
                    (current_order,)
                )
                other_book = cur.fetchone()

                if other_book:
                    other_id, other_order = other_book
                    cur.execute("UPDATE books SET pin_order = ? WHERE id = ?", (other_order, book_id))
                    cur.execute("UPDATE books SET pin_order = ? WHERE id = ?", (current_order, other_id))

        except sqlite3.Error as e:
            logging.error(f"Error moving pinned book up {book_id}: {e}", exc_info=True)
            raise

    def move_pinned_book_down(self, book_id: int):
        """Moves a pinned book down in the sort order."""
        if self.conn is None:
            return
        try:
            with self.conn:
                cur = self.conn.cursor()
                cur.execute("SELECT pin_order FROM books WHERE id = ?", (book_id,))
                current_order_row = cur.fetchone()
                if not current_order_row:
                    return
                current_order = current_order_row[0]

                cur.execute(
                    """
                    SELECT id, pin_order FROM books
                    WHERE is_pinned = 1 AND pin_order > ?
                    ORDER BY pin_order ASC
                    LIMIT 1
                    """,
                    (current_order,)
                )
                other_book = cur.fetchone()

                if other_book:
                    other_id, other_order = other_book
                    cur.execute("UPDATE books SET pin_order = ? WHERE id = ?", (other_order, book_id))
                    cur.execute("UPDATE books SET pin_order = ? WHERE id = ?", (current_order, other_id))

        except sqlite3.Error as e:
            logging.error(f"Error moving pinned book down {book_id}: {e}", exc_info=True)
            raise

    def set_book_finished(self, book_id: int, is_finished: bool):
        """Updates the finished status of a book."""
        if self.conn is None:
            return
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE books SET is_finished = ? WHERE id = ?",
                    (1 if is_finished else 0, book_id)
                )
        except sqlite3.Error as e:
            logging.error(f"Error setting finished status for book {book_id}: {e}", exc_info=True)
            raise

    def get_finished_books(self) -> List[Tuple[int, str, int]]:
        """Retrieves all books marked as finished."""
        if self.conn is None:
            return []

        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT id, title, shelf_id FROM books
                WHERE is_finished = 1
                ORDER BY title ASC
                """
            )
            return cur.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error fetching finished books: {e}", exc_info=True)
            return []
        finally:
            if cur:
                cur.close()