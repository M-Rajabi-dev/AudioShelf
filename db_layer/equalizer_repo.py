# db_layer/equalizer_repo.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import logging
import sqlite3
from typing import Dict, Optional, List, Any


class EqualizerRepository:
    """
    Manages database interactions for Equalizer presets.
    Handles both default (system) presets and user-defined presets.
    """

    def __init__(self, conn: sqlite3.Connection, default_presets: Dict[str, str]):
        self.conn = conn
        self.default_presets = default_presets
        self._initialize_default_presets()

    def _initialize_default_presets(self):
        """Populates the database with default EQ presets if they do not already exist."""
        if self.conn is None:
            return
        try:
            presets_data = [
                (name, settings)
                for name, settings in self.default_presets.items()
            ]
            with self.conn:
                self.conn.executemany(
                    "INSERT OR IGNORE INTO eq_presets (name, settings) VALUES (?, ?)",
                    presets_data
                )
        except sqlite3.Error as e:
            logging.error(f"Error initializing default EQ presets: {e}", exc_info=True)

    def get_all_presets(self) -> List[Dict[str, Any]]:
        """
        Retrieves all EQ presets from the database.
        Presets are sorted alphabetically, with 'Flat' always appearing first.

        Returns:
            A list of dictionaries, each containing 'id', 'name', and 'settings'.
        """
        if self.conn is None:
            return []

        results = []
        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT id, name, settings FROM eq_presets "
                "ORDER BY CASE WHEN name = 'Flat' THEN 0 ELSE 1 END, name"
            )
            for row in cur.fetchall():
                results.append({
                    "id": row[0],
                    "name": row[1],
                    "settings": row[2]
                })
            return results
        except sqlite3.Error as e:
            logging.error(f"Error getting all EQ presets: {e}", exc_info=True)
            return []
        finally:
            if cur:
                cur.close()

    def save_preset(self, name: str, settings: str) -> Optional[int]:
        """
        Saves a new user-defined preset to the database.

        Args:
            name: The unique name for the preset.
            settings: The 10-band equalizer settings string.

        Returns:
            The ID of the new preset if successful, or None if the name already exists.
        """
        if self.conn is None:
            return None

        cur = None
        try:
            with self.conn:
                cur = self.conn.cursor()
                cur.execute(
                    "INSERT INTO eq_presets (name, settings) VALUES (?, ?)",
                    (name, settings)
                )
                return cur.lastrowid
        except sqlite3.IntegrityError:
            logging.warning(f"Error saving EQ preset: Name '{name}' already exists.")
            return None
        except sqlite3.Error as e:
            logging.error(f"Error saving EQ preset: {e}", exc_info=True)
            return None
        finally:
            if cur:
                cur.close()

    def delete_preset(self, preset_id: int):
        """Deletes a preset from the database by its ID."""
        if self.conn is None:
            return
        try:
            with self.conn:
                self.conn.execute("DELETE FROM eq_presets WHERE id = ?", (preset_id,))
        except sqlite3.Error as e:
            logging.error(f"Error deleting EQ preset ID {preset_id}: {e}", exc_info=True)