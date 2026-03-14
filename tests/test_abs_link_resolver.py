import unittest
from unittest.mock import patch

from playback import abs_link_resolver as resolver


class _FakeClient:
    def __init__(self, libraries, items_by_library):
        self._libraries = libraries
        self._items_by_library = items_by_library

    def get_libraries(self):
        return self._libraries

    def get_library_items(self, library_id, page_size=200):
        _ = page_size
        return list(self._items_by_library.get(library_id, []))


class AbsLinkResolverTests(unittest.TestCase):
    def test_lookup_prefers_relpath_root_basename_match(self):
        client = _FakeClient(
            libraries=[{"id": "lib-1", "mediaType": "book"}],
            items_by_library={
                "lib-1": [
                    {
                        "id": "item-other",
                        "relPath": "Other Book",
                        "media": {"metadata": {"title": "Other Book", "authorName": "Someone"}},
                        "addedAt": 10,
                    },
                    {
                        "id": "item-target",
                        "relPath": "Harry Potter and the Chamber of Secrets (Full-Cast Edition) EAC3+Atmos 6ch - J.K. Rowling",
                        "media": {
                            "numChapters": 20,
                            "metadata": {
                                "title": "Harry Potter and the Chamber of Secrets (Full-Cast Edition)",
                                "authorName": "J.K. Rowling",
                            }
                        },
                        "addedAt": 11,
                    },
                ]
            },
        )

        item_id = resolver._lookup_item_id_for_local_book(
            client=client,
            title="Harry Potter and the Chamber of Secrets (Full-Cast Edition) EAC3+Atmos 6ch - J.K. Rowling",
            author="J.K. Rowling",
            root_path=r"F:\AudioDrama\Harry Potter and the Chamber of Secrets (Full-Cast Edition) EAC3+Atmos 6ch - J.K. Rowling",
        )
        self.assertEqual(item_id, "item-target")

    def test_resolve_uses_saved_link_for_local_book(self):
        book_id = 44
        link_key = f"audiobookshelf_book_link_{book_id}"

        def _get_setting(key):
            mapping = {
                link_key: '{"base_url":"https://books.example.com","item_id":"abc123"}',
                "audiobookshelf_api_key": "secret-key",
                "audiobookshelf_server_url": "https://books.example.com",
            }
            return mapping.get(key, "")

        with patch.object(resolver.db_manager, "get_setting", side_effect=_get_setting), \
                patch.object(resolver.db_manager, "set_setting") as set_setting_mock, \
                patch.object(resolver.db_manager, "get_book_files", return_value=[]):
            base_url, item_id, api_key = resolver.resolve_audiobookshelf_target(
                book_id=book_id,
                root_path=r"F:\AudioDrama\Some Local Book",
                preferred_stream_url=None,
                allow_lookup=False,
            )

        self.assertEqual(base_url, "https://books.example.com")
        self.assertEqual(item_id, "abc123")
        self.assertEqual(api_key, "secret-key")
        set_setting_mock.assert_not_called()

    def test_remember_audiobookshelf_link_writes_setting(self):
        with patch.object(resolver.db_manager, "set_setting") as set_setting_mock:
            resolver.remember_audiobookshelf_link(5, "https://books.example.com", "item-5")

        args = set_setting_mock.call_args[0]
        self.assertEqual(args[0], "audiobookshelf_book_link_5")
        self.assertIn('"base_url": "https://books.example.com"', args[1])
        self.assertIn('"item_id": "item-5"', args[1])


if __name__ == "__main__":
    unittest.main()
