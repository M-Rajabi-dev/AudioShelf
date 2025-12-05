# db_layer/settings_repo.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import logging
import sqlite3
from typing import Dict, Optional


class SettingsRepository:
    """
    Manages application settings, providing a caching layer over the database
    to minimize disk I/O for frequent reads.
    """

    def __init__(self, conn: sqlite3.Connection, default_settings: Dict[str, str]):
        self.conn = conn
        self.default_settings = default_settings
        self._settings_cache: Dict[str, str] = {}
        self._load_settings_to_cache()

    def _load_settings_to_cache(self):
        """Populates the internal settings cache from the database."""
        cur = None
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT key, value FROM settings")
            results = cur.fetchall()
            self._settings_cache = dict(results)
        except sqlite3.Error as e:
            logging.error(f"Error loading settings into cache: {e}", exc_info=True)
            self._settings_cache = self.default_settings.copy()
        finally:
            if cur:
                cur.close()

    def get_setting(self, key: str) -> Optional[str]:
        """
        Retrieves a setting value from the cache.
        If the key is not found in the DB, returns the default value.

        Args:
            key: The setting key.

        Returns:
            The setting value as a string, or None if not found.
        """
        return self._settings_cache.get(key, self.default_settings.get(key))

    def set_setting(self, key: str, value: str):
        """
        Updates a setting in both the database and the internal cache.

        Args:
            key: The setting key.
            value: The value to store.
        """
        if self.conn is None:
            logging.warning(f"SettingsRepository: Attempted to set setting '{key}' with no DB connection.")
            return

        try:
            str_value = str(value)
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    (key, str_value)
                )
            self._settings_cache[key] = str_value
            logging.info(f"Setting '{key}' updated.")
        except sqlite3.Error as e:
            logging.error(f"Error setting {key}: {e}", exc_info=True)