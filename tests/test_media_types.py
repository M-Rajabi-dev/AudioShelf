import unittest

from media_types import filter_files_by_book_type, infer_book_type_from_file_rows


class MediaTypesTests(unittest.TestCase):
    def test_infer_book_type_prefers_audio_for_mixed_sets(self):
        rows = [
            (1, "C:/books/My Book/ch1.mp3", 0, 0),
            (2, "C:/books/My Book/book.epub", 1, 0),
        ]
        self.assertEqual(infer_book_type_from_file_rows(rows), "audio")

    def test_infer_book_type_detects_ebook(self):
        rows = [
            (1, "C:/books/My Book/book.epub", 0, 0),
        ]
        self.assertEqual(infer_book_type_from_file_rows(rows), "ebook")

    def test_filter_files_by_book_type_reindexes(self):
        files = [
            ("C:/books/My Book/ch1.mp3", 0, 1000),
            ("C:/books/My Book/ch2.mp3", 3, 2000),
            ("C:/books/My Book/book.epub", 4, 0),
        ]

        audio_files = filter_files_by_book_type(files, "audio")
        self.assertEqual(audio_files, [
            ("C:/books/My Book/ch1.mp3", 0, 1000),
            ("C:/books/My Book/ch2.mp3", 1, 2000),
        ])

        ebook_files = filter_files_by_book_type(files, "ebook")
        self.assertEqual(ebook_files, [
            ("C:/books/My Book/book.epub", 0, 0),
        ])


if __name__ == "__main__":
    unittest.main()
