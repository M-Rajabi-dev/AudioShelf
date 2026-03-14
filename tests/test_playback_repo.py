import sqlite3
import unittest

from db_layer.playback_repo import PlaybackRepository


class PlaybackRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute(
            """
            CREATE TABLE books (
                id INTEGER PRIMARY KEY,
                title TEXT,
                last_played_timestamp TEXT
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE reading_state (
                book_id INTEGER PRIMARY KEY,
                char_offset INTEGER DEFAULT 0,
                total_chars INTEGER DEFAULT 0,
                last_read_at TIMESTAMP
            )
            """
        )
        self.conn.execute("INSERT INTO books (id, title) VALUES (1, 'Book')")
        self.repo = PlaybackRepository(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_save_and_get_reading_state(self):
        self.repo.save_reading_state(book_id=1, char_offset=123, total_chars=1000)
        state = self.repo.get_reading_state(1)
        self.assertIsNotNone(state)
        self.assertEqual(state["char_offset"], 123)
        self.assertEqual(state["total_chars"], 1000)
        self.assertTrue(state["last_read_at"])

    def test_save_reading_state_updates_last_played_timestamp(self):
        self.repo.save_reading_state(book_id=1, char_offset=50, total_chars=500)
        row = self.conn.execute("SELECT last_played_timestamp FROM books WHERE id = 1").fetchone()
        self.assertIsNotNone(row)
        self.assertTrue(row[0])


if __name__ == "__main__":
    unittest.main()
