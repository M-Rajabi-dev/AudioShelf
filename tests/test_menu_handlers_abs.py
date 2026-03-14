import unittest
from unittest.mock import patch

from frames.library import menu_handlers


class MenuHandlersAudiobookshelfDefaultLibraryTests(unittest.TestCase):
    def test_default_library_uses_configured_id(self):
        libs = [{"id": "lib-a"}, {"id": "lib-b"}]
        with patch.object(menu_handlers.db_manager, "get_setting", return_value="lib-b"):
            idx = menu_handlers._default_abs_library_index(libs)
        self.assertEqual(idx, 1)

    def test_default_library_returns_none_when_not_configured_and_multiple(self):
        libs = [{"id": "lib-a"}, {"id": "lib-b"}]
        with patch.object(menu_handlers.db_manager, "get_setting", return_value=""):
            idx = menu_handlers._default_abs_library_index(libs)
        self.assertIsNone(idx)

    def test_default_library_falls_back_to_only_library(self):
        libs = [{"id": "lib-only"}]
        with patch.object(menu_handlers.db_manager, "get_setting", return_value=""):
            idx = menu_handlers._default_abs_library_index(libs)
        self.assertEqual(idx, 0)

    def test_default_library_returns_none_when_configured_missing_and_multiple(self):
        libs = [{"id": "lib-a"}, {"id": "lib-b"}]
        with patch.object(menu_handlers.db_manager, "get_setting", return_value="lib-c"):
            idx = menu_handlers._default_abs_library_index(libs)
        self.assertIsNone(idx)


if __name__ == "__main__":
    unittest.main()
