# db_layer/shelf_repo.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import logging
import sqlite3
from collections import defaultdict
from typing import Dict, Optional, List, Any, Tuple


class ShelfRepository:
    """
    Manages database interactions for book shelves.
    Optimized to minimize database round-trips using bulk fetching.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_shelves_and_books(self) -> List[Tuple[int, str, List[Tuple[int, str]]]]:
        """
        Retrieves all shelves and their assigned books efficiently.

        Returns:
            A list of tuples, where each tuple contains:
            (shelf_id, shelf_name, list_of_books).
            The list_of_books is a list of (book_id, book_title).
        """
        if self.conn is None:
            logging.error("ShelfRepository: Cannot fetch shelves: DB connection not established.")
            return []

        shelves_data = []
        cur = None
        try:
            cur = self.conn.cursor()

            # 1. Fetch all shelves
            cur.execute("""
                SELECT id, name 
                FROM shelves 
                ORDER BY 
                    CASE WHEN id = 1 THEN 0 ELSE 1 END, 
                    sort_order, 
                    name
            """)
            all_shelves = cur.fetchall()

            # 2. Fetch all books (id, title, shelf_id)
            cur.execute("SELECT id, title, shelf_id FROM books ORDER BY title")
            all_books = cur.fetchall()

            # 3. Map books to shelves in memory
            books_by_shelf = defaultdict(list)
            for book_id, title, shelf_id in all_books:
                books_by_shelf[shelf_id].append((book_id, title))

            # 4. Construct final structure
            for shelf_id, shelf_name in all_shelves:
                books = books_by_shelf.get(shelf_id, [])
                shelves_data.append((shelf_id, shelf_name, books))

            return shelves_data

        except sqlite3.Error as e:
            logging.error(f"Error fetching shelves and books: {e}", exc_info=True)
            return []
        finally:
            if cur:
                cur.close()

    def create_shelf(self, name: str) -> Optional[int]:
        """
        Creates a new shelf with the given name.

        Args:
            name: The name of the new shelf.

        Returns:
            The ID of the new shelf, or None if creation failed.
        """
        if self.conn is None:
            return None

        cur = None
        try:
            with self.conn:
                cur = self.conn.cursor()
                cur.execute("INSERT INTO shelves (name) VALUES (?)", (name,))
                return cur.lastrowid
        except sqlite3.IntegrityError:
            logging.warning(f"Error: Shelf name '{name}' already exists.")
            return None
        except sqlite3.Error as e:
            logging.error(f"Error creating shelf: {e}", exc_info=True)
            return None
        finally:
            if cur:
                cur.close()

    def move_book_to_shelf(self, book_id: int, new_shelf_id: int):
        """Updates the shelf assignment for a specific book."""
        if self.conn is None:
            return
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE books SET shelf_id = ? WHERE id = ?",
                    (new_shelf_id, book_id)
                )
        except sqlite3.Error as e:
            logging.error(f"Error moving book: {e}", exc_info=True)

    def delete_shelf(self, shelf_id: int):
        """
        Deletes a shelf if it is empty.
        The Default Shelf (ID 1) cannot be deleted.

        Raises:
            sqlite3.IntegrityError: If the shelf contains books.
        """
        if self.conn is None:
            return

        if shelf_id == 1:
            logging.warning("Attempt to delete the Default Shelf denied.")
            return

        try:
            with self.conn:
                self.conn.execute("DELETE FROM shelves WHERE id = ?", (shelf_id,))
        except sqlite3.IntegrityError:
            logging.warning(f"Error: Cannot delete shelf. Shelf ID {shelf_id} is not empty.")
            raise
        except sqlite3.Error as e:
            logging.error(f"Error deleting shelf: {e}", exc_info=True)
            raise

    def rename_shelf(self, shelf_id: int, new_name: str):
        """
        Renames a specific shelf.
        The Default Shelf (ID 1) cannot be renamed.

        Raises:
            sqlite3.IntegrityError: If the new name already exists.
        """
        if self.conn is None:
            return

        if shelf_id == 1:
            logging.warning("Attempt to rename the Default Shelf denied.")
            return

        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE shelves SET name = ? WHERE id = ?",
                    (new_name, shelf_id)
                )
        except sqlite3.IntegrityError:
            logging.warning(f"Error: Shelf name '{new_name}' already exists.")
            raise
        except sqlite3.Error as e:
            logging.error(f"Error renaming shelf: {e}", exc_info=True)
            raise

    def get_shelf_details(self, shelf_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves details (e.g., name) for a specific shelf ID."""
        if self.conn is None:
            return None

        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT name FROM shelves WHERE id = ?", (shelf_id,))
            result = cur.fetchone()
            if result:
                return {"name": result[0]}
            return None
        except sqlite3.Error as e:
            logging.error(f"Error getting shelf details for ID {shelf_id}: {e}", exc_info=True)
            return None
        finally:
            if cur:
                cur.close()