# db_layer/schema.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

"""
Defines the SQL schema (CREATE TABLE and CREATE INDEX statements) for the database.
"""

CREATE_SHELVES_TABLE = """
CREATE TABLE IF NOT EXISTS shelves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    sort_order INTEGER DEFAULT 0
);
"""

CREATE_BOOKS_TABLE = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    root_path TEXT NOT NULL UNIQUE,
    shelf_id INTEGER NOT NULL,
    author TEXT,
    narrator TEXT,
    genre TEXT,
    description TEXT,
    date_added TIMESTAMP,
    last_played_timestamp TIMESTAMP,
    is_pinned BOOLEAN DEFAULT 0,
    pin_order INTEGER DEFAULT 0,
    is_finished BOOLEAN DEFAULT 0,
    FOREIGN KEY (shelf_id) REFERENCES shelves(id) ON DELETE RESTRICT
);
"""

CREATE_PLAYABLE_FILES_TABLE = """
CREATE TABLE IF NOT EXISTS playable_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    file_index INTEGER NOT NULL,
    duration_ms INTEGER DEFAULT 0,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    UNIQUE(file_path)
);
"""

CREATE_PLAYBACK_STATE_TABLE = """
CREATE TABLE IF NOT EXISTS playback_state (
    book_id INTEGER PRIMARY KEY,
    last_file_index INTEGER DEFAULT 0,
    last_position_ms INTEGER DEFAULT 0,
    last_speed_rate REAL DEFAULT 1.0,
    last_eq_settings TEXT DEFAULT "0,0,0,0,0,0,0,0,0,0",
    is_eq_enabled BOOLEAN DEFAULT 0,
    last_nr_mode INTEGER DEFAULT 0,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);
"""

CREATE_BOOKMARKS_TABLE = """
CREATE TABLE IF NOT EXISTS bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    file_index INTEGER NOT NULL,
    position_ms INTEGER NOT NULL,
    title TEXT,
    note TEXT,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);
"""

CREATE_SETTINGS_TABLE = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

CREATE_UI_STATE_TABLE = """
CREATE TABLE IF NOT EXISTS ui_state (
    item_key TEXT PRIMARY KEY,
    is_hidden BOOLEAN DEFAULT 0,
    is_expanded BOOLEAN DEFAULT 0
);
"""

CREATE_EQ_PRESETS_TABLE = """
CREATE TABLE IF NOT EXISTS eq_presets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    settings TEXT NOT NULL
);
"""

# Indexes
CREATE_INDEX_BOOKS_SHELF = """
CREATE INDEX IF NOT EXISTS idx_books_shelf_id ON books(shelf_id);
"""

CREATE_INDEX_BOOKS_PINNED = """
CREATE INDEX IF NOT EXISTS idx_books_pinned ON books(is_pinned, pin_order);
"""

CREATE_INDEX_BOOKS_FINISHED = """
CREATE INDEX IF NOT EXISTS idx_books_finished ON books(is_finished);
"""

CREATE_INDEX_BOOKS_HISTORY = """
CREATE INDEX IF NOT EXISTS idx_books_last_played ON books(last_played_timestamp DESC);
"""

CREATE_INDEX_FILES_BOOK_ID = """
CREATE INDEX IF NOT EXISTS idx_files_book_id ON playable_files(book_id, file_index);
"""

ALL_TABLES = [
    CREATE_SHELVES_TABLE,
    CREATE_BOOKS_TABLE,
    CREATE_PLAYABLE_FILES_TABLE,
    CREATE_PLAYBACK_STATE_TABLE,
    CREATE_BOOKMARKS_TABLE,
    CREATE_SETTINGS_TABLE,
    CREATE_UI_STATE_TABLE,
    CREATE_EQ_PRESETS_TABLE,
    # Indexes
    CREATE_INDEX_BOOKS_SHELF,
    CREATE_INDEX_BOOKS_PINNED,
    CREATE_INDEX_BOOKS_FINISHED,
    CREATE_INDEX_BOOKS_HISTORY,
    CREATE_INDEX_FILES_BOOK_ID
]