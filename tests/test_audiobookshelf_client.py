import unittest
import os
import tempfile
from unittest.mock import patch

from audiobookshelf_client import AudiobookshelfClient, AudiobookshelfError


class AudiobookshelfClientTests(unittest.TestCase):
    def test_normalize_base_url_adds_scheme_and_strips_api_suffix(self):
        self.assertEqual(
            AudiobookshelfClient._normalize_base_url("books.example.com/api/"),
            "http://books.example.com",
        )

    def test_normalize_base_url_keeps_subpath(self):
        self.assertEqual(
            AudiobookshelfClient._normalize_base_url("https://example.com/abs"),
            "https://example.com/abs",
        )

    def test_extract_token_from_stream_url(self):
        url = "https://books.example.com/api/items/1/file?token=abc123&x=1"
        self.assertEqual(AudiobookshelfClient.extract_token_from_stream_url(url), "abc123")
        self.assertIsNone(AudiobookshelfClient.extract_token_from_stream_url("https://example.com/file.mp3"))

    def test_parse_remote_book_root(self):
        base_url, item_id = AudiobookshelfClient.parse_remote_book_root(
            "abs:https://books.example.com/abs/item/123456"
        )
        self.assertEqual(base_url, "https://books.example.com/abs")
        self.assertEqual(item_id, "123456")

    def test_parse_remote_book_root_invalid_input(self):
        self.assertEqual(AudiobookshelfClient.parse_remote_book_root("C:/Books"), (None, None))
        self.assertEqual(AudiobookshelfClient.parse_remote_book_root("abs:https://example.com/no-item"), (None, None))

    def test_get_media_progress_returns_none_on_404(self):
        client = AudiobookshelfClient("https://books.example.com", "key")
        with patch.object(client, "_request", side_effect=AudiobookshelfError("Audiobookshelf API error (404): Not found")):
            self.assertIsNone(client.get_media_progress("item1"))

    def test_get_media_progress_raises_for_other_errors(self):
        client = AudiobookshelfClient("https://books.example.com", "key")
        with patch.object(client, "_request", side_effect=AudiobookshelfError("Audiobookshelf API error (500): fail")):
            with self.assertRaises(AudiobookshelfError):
                client.get_media_progress("item1")

    def test_update_media_progress_payload(self):
        client = AudiobookshelfClient("https://books.example.com", "key")
        with patch.object(client, "_request", return_value={"ok": True}) as req:
            client.update_media_progress(
                item_id="item1",
                current_time_seconds=35.0,
                duration_seconds=140.0,
                is_finished=False,
            )

        req.assert_called_once()
        self.assertEqual(req.call_args.args[0], "PATCH")
        self.assertEqual(req.call_args.args[1], "me/progress/item1")
        payload = req.call_args.kwargs["payload"]
        self.assertEqual(payload["libraryItemId"], "item1")
        self.assertEqual(payload["duration"], 140.0)
        self.assertEqual(payload["currentTime"], 35.0)
        self.assertAlmostEqual(payload["progress"], 0.25)
        self.assertFalse(payload["isFinished"])

    def test_update_media_progress_marks_finished(self):
        client = AudiobookshelfClient("https://books.example.com", "key")
        with patch.object(client, "_request", return_value={"ok": True}) as req:
            client.update_media_progress(
                item_id="item1",
                current_time_seconds=1.0,
                duration_seconds=500.0,
                is_finished=True,
            )

        payload = req.call_args.kwargs["payload"]
        self.assertEqual(payload["progress"], 1.0)
        self.assertTrue(payload["isFinished"])

    def test_update_media_progress_ignores_invalid_json_response(self):
        client = AudiobookshelfClient("https://books.example.com", "key")
        with patch.object(client, "_request", side_effect=AudiobookshelfError("Received invalid JSON from Audiobookshelf server.")):
            result = client.update_media_progress(
                item_id="item1",
                current_time_seconds=12.0,
                duration_seconds=120.0,
                is_finished=False,
            )
        self.assertEqual(result, {})

    def test_extract_chapters_from_item(self):
        item = {
            "media": {
                "duration": 300.0,
                "chapters": [
                    {"start": 0, "end": 10.5, "title": "Intro"},
                    {"start": 10.5, "title": "Chapter Two"},
                    {"start": 30.0, "end": 45.0},
                ],
            }
        }
        chapters = AudiobookshelfClient._extract_chapters_from_item(item)
        self.assertEqual(len(chapters), 3)
        self.assertEqual(chapters[0].title, "Intro")
        self.assertEqual(chapters[0].start_ms, 0)
        self.assertEqual(chapters[0].end_ms, 10500)
        self.assertEqual(chapters[1].start_ms, 10500)
        self.assertEqual(chapters[1].end_ms, 30000)
        self.assertEqual(chapters[2].title, "Chapter 3")

    def test_get_item_chapters_calls_item_details(self):
        client = AudiobookshelfClient("https://books.example.com", "key")
        with patch.object(client, "get_item_details", return_value={"media": {"chapters": []}}) as get_details:
            chapters = client.get_item_chapters("item1")
        self.assertEqual(chapters, [])
        get_details.assert_called_once_with(item_id="item1", expanded=1)

    def test_build_book_import_for_ebook_item(self):
        client = AudiobookshelfClient("https://books.example.com", "key")
        item_data = {
            "media": {
                "metadata": {"title": "Ebook Title"},
                "ebookFormat": "epub",
                "ebookFile": {
                    "ebookFormat": "epub",
                    "metadata": {
                        "filename": "My Book.epub",
                        "relPath": "Books/My Book.epub",
                    },
                },
            },
        }
        with patch.object(client, "get_item_details", return_value=item_data):
            imported = client.build_book_import(item_id="item1")

        self.assertEqual(imported.book_type, "ebook")
        self.assertEqual(imported.title, "Ebook Title")
        self.assertEqual(len(imported.files), 1)
        self.assertEqual(imported.tracks[0].filename, "My Book.epub")
        self.assertIn("/s/item/item1/Books/My%20Book.epub", imported.files[0][0])
        self.assertIn("token=key", imported.files[0][0])

    def test_build_book_import_prefers_audio_tracks_when_available(self):
        client = AudiobookshelfClient("https://books.example.com", "key")
        item_data = {
            "media": {
                "metadata": {"title": "Hybrid Book"},
                "tracks": [
                    {
                        "title": "Track",
                        "contentUrl": "/s/item/item1/track1.m4b",
                        "duration": 12.0,
                    }
                ],
                "ebookFile": {
                    "ebookFormat": "epub",
                    "metadata": {
                        "filename": "Hybrid.epub",
                        "relPath": "Hybrid.epub",
                    },
                },
            },
        }
        with patch.object(client, "get_item_details", return_value=item_data):
            imported = client.build_book_import(item_id="item1")

        self.assertEqual(imported.book_type, "audio")
        self.assertTrue(imported.files[0][0].endswith("track1.m4b?token=key"))

    def test_resolve_upload_destination_prefers_configured_library_and_folder(self):
        client = AudiobookshelfClient("https://books.example.com", "key")
        libs = [
            {
                "id": "lib-1",
                "mediaType": "book",
                "folders": [{"id": "fol-1"}]
            },
            {
                "id": "lib-2",
                "mediaType": "book",
                "folders": [{"id": "fol-2"}]
            },
        ]
        with patch.object(client, "get_libraries", return_value=libs):
            lib_id, fol_id = client.resolve_upload_destination("lib-2", "fol-2")
        self.assertEqual(lib_id, "lib-2")
        self.assertEqual(fol_id, "fol-2")

    def test_resolve_upload_destination_falls_back_to_first_book_library(self):
        client = AudiobookshelfClient("https://books.example.com", "key")
        libs = [
            {
                "id": "lib-podcast",
                "mediaType": "podcast",
                "folders": [{"id": "fol-p"}]
            },
            {
                "id": "lib-book",
                "mediaType": "book",
                "folders": [{"id": "fol-b"}]
            },
        ]
        with patch.object(client, "get_libraries", return_value=libs):
            lib_id, fol_id = client.resolve_upload_destination()
        self.assertEqual(lib_id, "lib-book")
        self.assertEqual(fol_id, "fol-b")

    def test_trigger_library_scan_calls_request(self):
        client = AudiobookshelfClient("https://books.example.com", "key")
        with patch.object(client, "_request", return_value={"ok": True}) as req:
            resp = client.trigger_library_scan("lib-1")
        self.assertEqual(resp, {"ok": True})
        req.assert_called_once_with("POST", "libraries/lib-1/scan")

    def test_trigger_library_scan_accepts_plain_text_response(self):
        client = AudiobookshelfClient("https://books.example.com", "key")
        with patch.object(
            client,
            "_request",
            side_effect=AudiobookshelfError("Received invalid JSON from Audiobookshelf server.")
        ):
            resp = client.trigger_library_scan("lib-1")
        self.assertEqual(resp, {})

    def test_upload_library_item_validates_files(self):
        client = AudiobookshelfClient("https://books.example.com", "key")
        with self.assertRaises(AudiobookshelfError):
            client.upload_library_item(
                title="Book",
                file_paths=[],
                library_id="lib",
                folder_id="fol"
            )

    def test_upload_library_item_success_parses_json(self):
        client = AudiobookshelfClient("https://books.example.com", "key")

        with tempfile.TemporaryDirectory() as tmpdir:
            local_file = os.path.join(tmpdir, "book.txt")
            with open(local_file, "w", encoding="utf-8") as f:
                f.write("hello")

            class FakeResponse:
                status = 200
                reason = "OK"

                def read(self):
                    return b'{"success": true}'

            class FakeConnection:
                def __init__(self, *args, **kwargs):
                    self.sent = []

                def putrequest(self, *args, **kwargs):
                    return None

                def putheader(self, *args, **kwargs):
                    return None

                def endheaders(self):
                    return None

                def send(self, data):
                    self.sent.append(data)

                def getresponse(self):
                    return FakeResponse()

                def close(self):
                    return None

            with patch("http.client.HTTPSConnection", return_value=FakeConnection()):
                resp = client.upload_library_item(
                    title="Book",
                    file_paths=[local_file],
                    library_id="lib",
                    folder_id="fol",
                    author="Me"
                )
            self.assertEqual(resp.get("success"), True)


if __name__ == "__main__":
    unittest.main()
