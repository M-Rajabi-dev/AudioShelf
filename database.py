# database.py
# Copyright (c) 2025 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import sqlite3
import os
import logging
import sys
import datetime
import threading
from typing import List, Tuple, Optional, Dict, Any

from db_layer.settings_repo import SettingsRepository
from db_layer.playback_repo import PlaybackRepository
from db_layer.book_repo import BookRepository
from db_layer.shelf_repo import ShelfRepository
from db_layer.maintenance_repo import MaintenanceRepository
from db_layer.ui_state_repo import UiStateRepository
from db_layer.equalizer_repo import EqualizerRepository
from db_layer.schema import ALL_TABLES

DB_NAME = "AudioShelf.db"
APP_NAME = "AudioShelf"
PORTABLE_MARKER_FILE = ".portable"
LOCAL_DATA_DIR_NAME = "user_data"


def _get_db_path_for_os() -> str:
    """
    Determines the database file path.
    Checks for portable mode markers first, then falls back to OS-specific standard data directories.
    """
    if getattr(sys, 'frozen', False):
        app_path = os.path.dirname(sys.executable)
    else:
        app_path = os.path.dirname(os.path.abspath(__file__))

    is_portable_loose = os.path.exists(os.path.join(app_path, PORTABLE_MARKER_FILE))

    is_portable_bundled = False
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        if os.path.exists(os.path.join(sys._MEIPASS, PORTABLE_MARKER_FILE)):
            is_portable_bundled = True

    if is_portable_loose or is_portable_bundled:
        data_dir = os.path.join(app_path, LOCAL_DATA_DIR_NAME)
    else:
        if sys.platform == "win32":
            local_app_data_path = os.getenv('LOCALAPPDATA')
            if local_app_data_path:
                data_dir = os.path.join(local_app_data_path, APP_NAME)
            else:
                data_dir = os.path.join(os.path.expanduser("~"), f".{APP_NAME}_local")
        elif sys.platform == "darwin":
            data_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', APP_NAME)
        else:
            xdg_data_home = os.getenv('XDG_DATA_HOME')
            if xdg_data_home:
                data_dir = os.path.join(xdg_data_home, APP_NAME)
            else:
                data_dir = os.path.join(os.path.expanduser('~'), '.local', 'share', APP_NAME)

    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, DB_NAME)


DB_FILE_PATH = _get_db_path_for_os()


class DatabaseManager:
    """
    Singleton Facade for managing SQLite database interactions.
    Delegates specific data operations to specialized repositories.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_file=DB_FILE_PATH):
        if self._initialized:
            return

        self.db_file = db_file
        self.conn = None
        self.db_lock = threading.RLock()

        self.settings_repo: Optional[SettingsRepository] = None
        self.playback_repo: Optional[PlaybackRepository] = None
        self.book_repo: Optional[BookRepository] = None
        self.shelf_repo: Optional[ShelfRepository] = None
        self.maintenance_repo: Optional[MaintenanceRepository] = None
        self.ui_state_repo: Optional[UiStateRepository] = None
        self.eq_repo: Optional[EqualizerRepository] = None

        self.default_settings = {
            'language': 'en',
            'nvda_verbosity': 'minimal',
            'seek_forward_ms': '30000',
            'seek_backward_ms': '10000',
            'pause_on_dialog': 'True',
            'end_of_book_action': 'close',
            'long_seek_forward_ms': '300000',
            'long_seek_backward_ms': '300000',
            'quick_timer_duration_minutes': '30',
            'quick_timer_action': 'pause',
            'engine': 'mpv',
            'global_hotkey_feedback': 'False',
            'resume_on_jump': 'True',
            'resume_rewind_ms': '5000',
            'smart_resume_threshold_sec': '300',
            'smart_resume_rewind_ms': '10000',
            'master_volume': '100',
        }

        self.default_eq_presets = {
            "Flat": "0,0,0,0,0,0,0,0,0,0",
            "Vocal Clarity": "-4,-2,0,-1,0,3,1,0,0,-1",
            "Fullness": "-2,1,3,0,-1,1,0,-2,-2,-3",
            "Reduce Boominess": "-6,-4,-2,0,0,2,1,0,0,0",
            "De-Esser": "0,0,0,0,0,1,-3,-4,-2,0"
        }

        self._establish_connection()
        self._initialized = True

    def _establish_connection(self):
        """Initializes the DB connection, tables, and repositories."""
        if self.conn is not None:
            return

        self.conn = self._create_connection()

        if self.conn:
            self._enable_wal_mode()
            self._enable_foreign_keys()
            self._setup_tables()
            self._initialize_defaults()

            self.settings_repo = SettingsRepository(self.conn, self.default_settings)
            self.playback_repo = PlaybackRepository(self.conn)
            self.book_repo = BookRepository(self.conn)
            self.shelf_repo = ShelfRepository(self.conn)
            self.maintenance_repo = MaintenanceRepository(self.conn)
            self.ui_state_repo = UiStateRepository(self.conn)
            self.eq_repo = EqualizerRepository(self.conn, self.default_eq_presets)
        else:
            self._initialized = False

    def _create_connection(self) -> Optional[sqlite3.Connection]:
        """Creates a thread-safe connection to the SQLite database."""
        try:
            conn = sqlite3.connect(self.db_file, check_same_thread=False)
            logging.info(f"Successfully connected to database: {self.db_file}")
            return conn
        except sqlite3.Error as e:
            logging.error(f"Error connecting to database: {e}")
            return None

    def _enable_wal_mode(self):
        """Enables Write-Ahead Logging (WAL) mode for concurrency."""
        try:
            with self.conn:
                self.conn.execute("PRAGMA journal_mode=WAL;")
                self.conn.execute("PRAGMA synchronous=NORMAL;")
            logging.info("Database WAL mode enabled.")
        except sqlite3.Error as e:
            logging.error(f"Error enabling WAL mode: {e}")

    def _enable_foreign_keys(self):
        """Enforces foreign key constraints."""
        try:
            with self.conn:
                self.conn.execute("PRAGMA foreign_keys = ON;")
        except sqlite3.Error as e:
            logging.error(f"Error enabling foreign keys: {e}")

    def _setup_tables(self):
        """Creates tables and applies schema updates/migrations."""
        try:
            with self.conn:
                for table_sql in ALL_TABLES:
                    self.conn.execute(table_sql)

            cur = self.conn.cursor()

            cur.execute("PRAGMA table_info(playable_files)")
            file_columns = [col[1] for col in cur.fetchall()]
            if 'duration_ms' not in file_columns:
                logging.info("Schema Update: Adding 'duration_ms' to 'playable_files'.")
                with self.conn:
                    self.conn.execute("ALTER TABLE playable_files ADD COLUMN duration_ms INTEGER DEFAULT 0")

            cur.execute("PRAGMA table_info(books)")
            book_columns = [col[1] for col in cur.fetchall()]

            new_book_columns = {
                'author': 'TEXT',
                'narrator': 'TEXT',
                'genre': 'TEXT',
                'description': 'TEXT',
                'date_added': 'TIMESTAMP',
                'last_played_timestamp': 'TIMESTAMP',
                'is_pinned': 'BOOLEAN DEFAULT 0',
                'pin_order': 'INTEGER DEFAULT 0'
            }

            with self.conn:
                date_added_was_missing = 'date_added' not in book_columns

                for col_name, col_type in new_book_columns.items():
                    if col_name not in book_columns:
                        logging.info(f"Schema Update: Adding '{col_name}' to 'books' table.")
                        self.conn.execute(f"ALTER TABLE books ADD COLUMN {col_name} {col_type}")

                if date_added_was_missing:
                    logging.info("Schema Update: Populating 'date_added' for existing books.")
                    now = datetime.datetime.now()
                    self.conn.execute("UPDATE books SET date_added = ? WHERE date_added IS NULL", (now,))

            cur.execute("PRAGMA table_info(playback_state)")
            playback_columns = [col[1] for col in cur.fetchall()]

            new_playback_columns = {
                'last_eq_settings': 'TEXT DEFAULT "0,0,0,0,0,0,0,0,0,0"',
                'is_eq_enabled': 'BOOLEAN DEFAULT 0',
                'last_nr_mode': 'INTEGER DEFAULT 0'
            }

            with self.conn:
                for col_name, col_type in new_playback_columns.items():
                    if col_name not in playback_columns:
                        logging.info(f"Schema Update: Adding '{col_name}' to 'playback_state' table.")
                        self.conn.execute(f"ALTER TABLE playback_state ADD COLUMN {col_name} {col_type}")

            cur.execute("PRAGMA table_info(books)")
            updated_book_columns = [col[1] for col in cur.fetchall()]

            if 'is_finished' not in updated_book_columns:
                logging.info("Schema Update: Adding 'is_finished' column to 'books' table.")
                with self.conn:
                    self.conn.execute("ALTER TABLE books ADD COLUMN is_finished BOOLEAN DEFAULT 0")

        except sqlite3.Error as e:
            logging.error(f"Error during schema setup: {e}", exc_info=True)
        finally:
            if 'cur' in locals() and cur:
                cur.close()

    def _initialize_defaults(self):
        """Populates the database with default data if missing."""
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT OR IGNORE INTO shelves (id, name, sort_order) VALUES (1, 'Default Shelf', 0)"
                )
                self.conn.executemany(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    self.default_settings.items()
                )
        except sqlite3.Error as e:
            logging.error(f"Error initializing defaults: {e}")

    def get_setting(self, key: str) -> Optional[str]:
        if self.conn is None:
            self._establish_connection()
            if self.conn is None:
                return self.default_settings.get(key)
        return self.settings_repo.get_setting(key)

    def set_setting(self, key: str, value: str):
        if self.conn is None:
            self._establish_connection()
            if self.conn is None:
                logging.error(f"Cannot set setting '{key}', DB connection failed.")
                return
        with self.db_lock:
            self.settings_repo.set_setting(key, value)

    def add_book(self, title: str, root_path: str, file_list: List[Tuple[str, int, int]], shelf_id: int = 1) -> \
            Optional[int]:
        with self.db_lock:
            return self.book_repo.add_book(title, root_path, file_list, shelf_id)

    def get_book_files(self, book_id: int) -> List[Tuple[int, str, int, int]]:
        return self.book_repo.get_book_files(book_id)

    def delete_book(self, book_id: int):
        with self.db_lock:
            return self.book_repo.delete_book(book_id)

    def get_book_path(self, book_id: int) -> Optional[str]:
        return self.book_repo.get_book_path(book_id)

    def update_book_source(self, book_id: int, new_root_path: str, new_file_list: List[Tuple[str, int, int]]):
        with self.db_lock:
            return self.book_repo.update_book_source(book_id, new_root_path, new_file_list)

    def rename_book(self, book_id: int, new_name: str):
        with self.db_lock:
            return self.book_repo.rename_book(book_id, new_name)

    def get_book_shelf(self, book_id: int) -> Optional[int]:
        return self.book_repo.get_book_shelf(book_id)

    def get_book_details(self, book_id: int) -> Optional[Dict[str, Any]]:
        return self.book_repo.get_book_details(book_id)

    def get_shelves_and_books(self) -> List[Tuple[int, str, List[Tuple[int, str]]]]:
        return self.shelf_repo.get_shelves_and_books()

    def create_shelf(self, name: str) -> Optional[int]:
        with self.db_lock:
            return self.shelf_repo.create_shelf(name)

    def move_book_to_shelf(self, book_id: int, new_shelf_id: int):
        with self.db_lock:
            return self.shelf_repo.move_book_to_shelf(book_id, new_shelf_id)

    def delete_shelf(self, shelf_id: int):
        with self.db_lock:
            return self.shelf_repo.delete_shelf(shelf_id)

    def rename_shelf(self, shelf_id: int, new_name: str):
        with self.db_lock:
            return self.shelf_repo.rename_shelf(shelf_id, new_name)

    def get_shelf_details(self, shelf_id: int) -> Optional[Dict[str, Any]]:
        return self.shelf_repo.get_shelf_details(shelf_id)

    def get_playback_state(self, book_id: int) -> Optional[Dict[str, Any]]:
        return self.playback_repo.get_playback_state(book_id)

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
        with self.db_lock:
            return self.playback_repo.save_playback_state(
                book_id, file_index, position_ms, speed_rate,
                eq_settings, is_eq_enabled, nr_mode
            )

    def add_bookmark(self, book_id: int, file_index: int, position_ms: int, title: str, note: str) -> Optional[int]:
        with self.db_lock:
            return self.playback_repo.add_bookmark(book_id, file_index, position_ms, title, note)

    def get_bookmarks_for_book(self, book_id: int) -> List[Dict[str, Any]]:
        return self.playback_repo.get_bookmarks_for_book(book_id)

    def delete_bookmark(self, bookmark_id: int):
        with self.db_lock:
            return self.playback_repo.delete_bookmark(bookmark_id)

    def update_file_duration(self, file_id: int, duration_ms: int):
        with self.db_lock:
            return self.book_repo.update_file_duration(file_id, duration_ms)

    def update_file_duration_batch(self, updates: List[Tuple[int, int]]):
        """
        Updates durations for multiple files in a single transaction.

        Args:
            updates: List of (file_id, duration_ms).
        """
        if self.conn is None:
            return
        with self.db_lock:
            self.book_repo.update_file_duration_batch(updates)

    def get_all_books_for_pruning(self) -> List[Tuple[int, str, str]]:
        return self.maintenance_repo.get_all_books_for_pruning()

    def prune_missing_books(self, missing_book_ids: List[int]) -> int:
        with self.db_lock:
            return self.maintenance_repo.prune_missing_books(missing_book_ids)

    def clear_library(self):
        with self.db_lock:
            return self.maintenance_repo.clear_library()

    def get_ui_item_state(self, key: str) -> Tuple[bool, bool]:
        if self.conn is None or self.ui_state_repo is None:
            self._establish_connection()
            if self.conn is None or self.ui_state_repo is None:
                logging.error(f"Cannot get UI state for '{key}', DB connection failed.")
                is_hidden_default = False
                if key.startswith("virtual_"):
                    is_expanded_default = (key not in ["virtual_all_books"])
                else:
                    is_expanded_default = False
                return is_hidden_default, is_expanded_default
        return self.ui_state_repo.get_item_state(key)

    def set_ui_item_state(self, key: str, is_hidden: Optional[bool], is_expanded: Optional[bool]):
        if self.conn is None or self.ui_state_repo is None:
            self._establish_connection()
            if self.conn is None or self.ui_state_repo is None:
                logging.error(f"FATAL: Cannot set UI state for '{key}', DB connection failed.")
                return

        with self.db_lock:
            self.ui_state_repo.set_item_state(key, is_hidden, is_expanded)

    def get_all_hidden_items(self) -> List[str]:
        if self.conn is None or self.ui_state_repo is None:
            self._establish_connection()
            if self.conn is None or self.ui_state_repo is None:
                logging.error("Cannot get hidden items list, DB connection failed.")
                return []
        return self.ui_state_repo.get_all_hidden_items()

    def get_eq_presets(self) -> List[Dict[str, Any]]:
        if self.conn is None or self.eq_repo is None:
            self._establish_connection()
            if self.conn is None or self.eq_repo is None:
                logging.error("Cannot get EQ presets, DB connection failed.")
                return []
        return self.eq_repo.get_all_presets()

    def save_eq_preset(self, name: str, settings: str) -> Optional[int]:
        if self.conn is None or self.eq_repo is None:
            self._establish_connection()
            if self.conn is None or self.eq_repo is None:
                logging.error("Cannot save EQ preset, DB connection failed.")
                return None
        with self.db_lock:
            return self.eq_repo.save_preset(name, settings)

    def delete_eq_preset(self, preset_id: int):
        if self.conn is None or self.eq_repo is None:
            self._establish_connection()
            if self.conn is None or self.eq_repo is None:
                logging.error("Cannot delete EQ preset, DB connection failed.")
                return
        with self.db_lock:
            return self.eq_repo.delete_preset(preset_id)

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            logging.info("Database connection closed.")
        self.conn = None
        self._initialized = False
        self.__class__._instance = None
        logging.debug("DatabaseManager singleton instance reset.")


db_manager = DatabaseManager()