# media_types.py
# Copyright (c) 2025-2026 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import os
from typing import Iterable, Optional, Sequence, Tuple
from urllib.parse import unquote, urlparse

AUDIO_VIDEO_EXTENSIONS = {
    ".mp3", ".m4a", ".m4b", ".aac", ".flac", ".ogg", ".oga", ".wav",
    ".wma", ".opus", ".aiff",
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".webma",
}

# Audiobookshelf-supported ebook/comic extensions.
EBOOK_EXTENSIONS = {
    ".epub", ".pdf", ".mobi", ".azw3", ".cbr", ".cbz", ".nfo", ".txt", ".opf", ".abs",
}

SUPPORTED_MEDIA_EXTENSIONS = AUDIO_VIDEO_EXTENSIONS | EBOOK_EXTENSIONS


def get_extension(path_or_url: Optional[str]) -> str:
    if not path_or_url:
        return ""

    parsed = urlparse(str(path_or_url))
    raw_path = parsed.path if parsed.scheme else str(path_or_url)
    raw_path = unquote(raw_path)
    return os.path.splitext(raw_path)[1].lower()


def is_audio_media(path_or_url: Optional[str]) -> bool:
    return get_extension(path_or_url) in AUDIO_VIDEO_EXTENSIONS


def is_ebook_media(path_or_url: Optional[str]) -> bool:
    return get_extension(path_or_url) in EBOOK_EXTENSIONS


def classify_file_path(path_or_url: Optional[str]) -> str:
    if is_audio_media(path_or_url):
        return "audio"
    if is_ebook_media(path_or_url):
        return "ebook"
    return "unknown"


def infer_book_type_from_file_rows(files: Sequence[Tuple[int, str, int, int]] | Sequence[Tuple[str, int, int]]) -> str:
    has_audio = False
    has_ebook = False

    for row in files:
        if not row:
            continue
        if len(row) >= 2:
            file_path = row[1] if isinstance(row[0], int) else row[0]
        else:
            continue

        kind = classify_file_path(file_path)
        if kind == "audio":
            has_audio = True
        elif kind == "ebook":
            has_ebook = True

    if has_audio:
        return "audio"
    if has_ebook:
        return "ebook"
    return "audio"


def filter_files_by_book_type(file_list: Iterable[Tuple[str, int, int]], book_type: str) -> list[Tuple[str, int, int]]:
    target_type = "ebook" if str(book_type).lower() == "ebook" else "audio"
    filtered = []
    for file_path, file_index, duration_ms in file_list:
        if classify_file_path(file_path) == target_type:
            filtered.append((file_path, file_index, duration_ms))

    # Reindex in natural order expected by the DB.
    normalized = []
    for idx, (file_path, _old_idx, old_dur) in enumerate(filtered):
        duration_ms = 0 if target_type == "ebook" else int(old_dur or 0)
        normalized.append((file_path, idx, duration_ms))
    return normalized
