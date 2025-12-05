# db_layer/ui_state_repo.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import logging
import sqlite3
from typing import Dict, Optional, Tuple, List


class UiStateRepository:
    """
    Manages persistent UI state, such as whether specific shelves or sections
    are hidden or expanded in the library view.
    Uses an in-memory cache to minimize database reads during UI rendering.
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._state_cache: Dict[str, Tuple[bool, bool]] = {}
        self._load_state_to_cache()

    def _load_state_to_cache(self):
        """Loads all UI state records from the database into the internal cache."""
        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT item_key, is_hidden, is_expanded FROM ui_state")
            results = cur.fetchall()

            for row in results:
                key, is_hidden, is_expanded = row
                self._state_cache[key] = (bool(is_hidden), bool(is_expanded))

        except sqlite3.Error as e:
            logging.error(f"Error loading UI state into cache: {e}", exc_info=True)
            self._state_cache = {}
        finally:
            if cur:
                cur.close()

    def get_item_state(self, key: str) -> Tuple[bool, bool]:
        """
        Retrieves the state (is_hidden, is_expanded) for a specific UI item.
        If the state is not found in the cache, intelligent defaults are returned.

        Args:
            key: The unique identifier for the UI item.

        Returns:
            A tuple containing (is_hidden, is_expanded).
        """
        cached_val = self._state_cache.get(key)
        if cached_val is not None:
            return cached_val

        is_hidden_default = False
        if key.startswith("virtual_"):
            is_expanded_default = (key not in ["virtual_all_books"])
        else:
            is_expanded_default = False

        return is_hidden_default, is_expanded_default

    def set_item_state(self, key: str, is_hidden: Optional[bool], is_expanded: Optional[bool]):
        """
        Updates the state of a UI item in the database and the cache.
        Supports partial updates; pass None to keep the current value.

        Args:
            key: The unique identifier for the UI item.
            is_hidden: The new hidden state, or None.
            is_expanded: The new expanded state, or None.
        """
        if self.conn is None:
            logging.warning(f"UiStateRepository: Attempted to set state for '{key}' with no DB connection.")
            return

        try:
            current_hidden, current_expanded = self.get_item_state(key)

            new_hidden = is_hidden if is_hidden is not None else current_hidden
            new_expanded = is_expanded if is_expanded is not None else current_expanded

            with self.conn:
                self.conn.execute(
                    """
                    INSERT OR REPLACE INTO ui_state 
                    (item_key, is_hidden, is_expanded) 
                    VALUES (?, ?, ?)
                    """,
                    (key, new_hidden, new_expanded)
                )

            self._state_cache[key] = (new_hidden, new_expanded)

        except sqlite3.Error as e:
            logging.error(f"Error setting UI state for {key}: {e}", exc_info=True)

    def get_all_hidden_items(self) -> List[str]:
        """
        Queries the database directly for a list of all items that are currently hidden.

        Returns:
            A list of item keys where is_hidden is True.
        """
        if self.conn is None:
            logging.error("Cannot get hidden items, DB connection not established.")
            return []

        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT item_key FROM ui_state WHERE is_hidden = 1")
            results = cur.fetchall()
            return [row[0] for row in results]

        except sqlite3.Error as e:
            logging.error(f"Error querying hidden UI items: {e}", exc_info=True)
            return []
        finally:
            if cur:
                cur.close()