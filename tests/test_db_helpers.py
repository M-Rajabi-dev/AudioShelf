import os
import tempfile
import unittest

from db_layer.helpers import find_missing_books, get_book_size_on_disk, is_remote_source


class DbHelpersTests(unittest.TestCase):
    def test_is_remote_source_detects_supported_schemes(self):
        self.assertTrue(is_remote_source("https://books.example.com/item/1"))
        self.assertTrue(is_remote_source("abs:https://books.example.com/item/1"))
        self.assertTrue(is_remote_source("audiobookshelf:https://books.example.com/item/1"))
        self.assertFalse(is_remote_source(r"C:\Audiobooks\Book1"))

    def test_get_book_size_on_disk_returns_none_for_remote(self):
        self.assertIsNone(get_book_size_on_disk("abs:https://books.example.com/item/1"))

    def test_get_book_size_on_disk_returns_total_bytes(self):
        with tempfile.TemporaryDirectory() as root:
            path1 = os.path.join(root, "a.bin")
            path2 = os.path.join(root, "b.bin")
            with open(path1, "wb") as f:
                f.write(b"a" * 10)
            with open(path2, "wb") as f:
                f.write(b"b" * 25)

            self.assertEqual(get_book_size_on_disk(root), 35)

    def test_find_missing_books_skips_remote_entries(self):
        with tempfile.TemporaryDirectory() as existing:
            all_books = [
                (1, "Remote", "abs:https://books.example.com/item/1"),
                (2, "Existing", existing),
                (3, "Missing", os.path.join(existing, "does-not-exist")),
            ]
            self.assertEqual(find_missing_books(all_books), [(3, "Missing")])


if __name__ == "__main__":
    unittest.main()
