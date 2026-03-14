# playback/abs_link_resolver.py
# Copyright (c) 2025-2026 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import json
import logging
import os
import re
from typing import Dict, Optional, Tuple

from audiobookshelf_client import AudiobookshelfClient, AudiobookshelfError
from database import db_manager

SETTING_AUDIOBOOKSHELF_SERVER_URL = "audiobookshelf_server_url"
SETTING_AUDIOBOOKSHELF_API_KEY = "audiobookshelf_api_key"
LINK_SETTING_PREFIX = "audiobookshelf_book_link_"


def _link_setting_key(book_id: int) -> str:
    return f"{LINK_SETTING_PREFIX}{int(book_id)}"


def _normalize_for_match(value: Optional[str]) -> str:
    text = str(value or "").strip().casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _is_book_like_library(lib: Dict) -> bool:
    media_type = str(lib.get("mediaType") or "").strip().lower()
    return media_type in {"book", "books", "audiobook", "audiobooks"}


def _item_metadata(item: Dict) -> Dict:
    if not isinstance(item, dict):
        return {}
    media = item.get("media")
    if not isinstance(media, dict):
        return {}
    metadata = media.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _item_title(item: Dict) -> str:
    metadata = _item_metadata(item)
    title = metadata.get("title")
    if not title and isinstance(item, dict):
        title = item.get("title")
    return str(title or "").strip()


def _item_author(item: Dict) -> str:
    metadata = _item_metadata(item)
    author = metadata.get("authorName")
    if isinstance(author, str) and author.strip():
        return author.strip()
    authors = metadata.get("authors")
    if isinstance(authors, list):
        names = []
        for entry in authors:
            if isinstance(entry, str) and entry.strip():
                names.append(entry.strip())
            elif isinstance(entry, dict):
                name = str(entry.get("name") or "").strip()
                if name:
                    names.append(name)
        if names:
            return ", ".join(names)
    return ""


def _item_rel_path(item: Dict) -> str:
    if not isinstance(item, dict):
        return ""
    rel_path = item.get("relPath")
    if rel_path:
        return str(rel_path)
    path = item.get("path")
    return str(path) if path else ""


def _get_saved_link(book_id: int) -> Tuple[Optional[str], Optional[str]]:
    raw = (db_manager.get_setting(_link_setting_key(book_id)) or "").strip()
    if not raw:
        return None, None

    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            base_url = str(data.get("base_url") or "").strip()
            item_id = str(data.get("item_id") or "").strip()
            if base_url and item_id:
                return base_url, item_id
    except Exception:
        pass

    # Backward-compatible fallback if old format was "base|item".
    if "|" in raw:
        base_url, item_id = raw.split("|", 1)
        base_url = base_url.strip()
        item_id = item_id.strip()
        if base_url and item_id:
            return base_url, item_id

    return None, None


def remember_audiobookshelf_link(book_id: int, base_url: str, item_id: str):
    base_url = str(base_url or "").strip()
    item_id = str(item_id or "").strip()
    if not base_url or not item_id:
        return
    payload = json.dumps({"base_url": base_url, "item_id": item_id}, ensure_ascii=True)
    db_manager.set_setting(_link_setting_key(book_id), payload)


def _score_item_candidate(
        item: Dict,
        title_norm: str,
        author_norm: str,
        root_base_norm: str
) -> int:
    score = 0

    rel_path = _item_rel_path(item).replace("\\", "/")
    rel_norm = _normalize_for_match(rel_path)
    rel_base_norm = _normalize_for_match(os.path.basename(rel_path.strip("/")))

    item_title_norm = _normalize_for_match(_item_title(item))
    item_author_norm = _normalize_for_match(_item_author(item))

    if root_base_norm:
        if root_base_norm == rel_base_norm:
            score += 240
        elif root_base_norm in rel_norm:
            score += 180

    if title_norm and item_title_norm:
        if title_norm == item_title_norm:
            score += 120
        elif title_norm in item_title_norm or item_title_norm in title_norm:
            score += 80

    if author_norm and item_author_norm:
        if author_norm == item_author_norm:
            score += 45
        elif author_norm in item_author_norm or item_author_norm in author_norm:
            score += 25

    media = item.get("media") if isinstance(item, dict) else None
    if isinstance(media, dict) and int(media.get("numChapters") or 0) > 0:
        score += 3

    return score


def _lookup_item_id_for_local_book(
        client: AudiobookshelfClient,
        title: Optional[str],
        author: Optional[str],
        root_path: Optional[str],
) -> Optional[str]:
    title_norm = _normalize_for_match(title)
    author_norm = _normalize_for_match(author)
    root_base_norm = _normalize_for_match(os.path.basename(str(root_path or "")))

    libraries = client.get_libraries()
    if not libraries:
        return None

    preferred_libraries = [lib for lib in libraries if isinstance(lib, dict) and _is_book_like_library(lib)]
    if not preferred_libraries:
        preferred_libraries = [lib for lib in libraries if isinstance(lib, dict)]

    best_item_id = None
    best_score = -1
    best_added_at = -1
    for lib in preferred_libraries:
        library_id = str(lib.get("id") or "").strip()
        if not library_id:
            continue
        try:
            items = client.get_library_items(library_id)
        except Exception:
            continue

        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("id") or "").strip()
            if not item_id:
                continue

            score = _score_item_candidate(
                item=item,
                title_norm=title_norm,
                author_norm=author_norm,
                root_base_norm=root_base_norm
            )
            if score <= 0:
                continue

            added_at = int(item.get("addedAt") or 0)
            if score > best_score or (score == best_score and added_at > best_added_at):
                best_item_id = item_id
                best_score = score
                best_added_at = added_at

    # Guardrail against weak/ambiguous matches.
    if best_score < 100:
        return None
    return best_item_id


def resolve_audiobookshelf_target(
        book_id: int,
        root_path: Optional[str] = None,
        preferred_stream_url: Optional[str] = None,
        allow_lookup: bool = False,
        timeout_seconds: int = 8
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    try:
        if root_path is None:
            root_path = db_manager.book_repo.get_book_path(book_id)
    except Exception:
        root_path = None

    base_url, item_id = AudiobookshelfClient.parse_remote_book_root(root_path)
    if base_url and item_id:
        remember_audiobookshelf_link(book_id, base_url, item_id)
    else:
        base_url, item_id = _get_saved_link(book_id)

    configured_server = (db_manager.get_setting(SETTING_AUDIOBOOKSHELF_SERVER_URL) or "").strip()
    if not base_url and configured_server:
        try:
            base_url = AudiobookshelfClient._normalize_base_url(configured_server)
        except Exception:
            base_url = None

    api_key = (db_manager.get_setting(SETTING_AUDIOBOOKSHELF_API_KEY) or "").strip()
    if not api_key and preferred_stream_url:
        api_key = AudiobookshelfClient.extract_token_from_stream_url(preferred_stream_url) or ""
    if not api_key:
        try:
            files = db_manager.get_book_files(book_id)
            first_stream = files[0][1] if files else None
            api_key = AudiobookshelfClient.extract_token_from_stream_url(first_stream) or ""
        except Exception:
            api_key = ""

    if base_url and item_id and api_key:
        return base_url, item_id, api_key

    if not allow_lookup or not base_url or not api_key:
        return None, None, None

    details = db_manager.get_book_details(book_id) or {}
    title = details.get("title")
    author = details.get("author")

    try:
        client = AudiobookshelfClient(base_url, api_key, timeout_seconds=timeout_seconds)
        matched_item_id = _lookup_item_id_for_local_book(
            client=client,
            title=title,
            author=author,
            root_path=root_path
        )
        if matched_item_id:
            remember_audiobookshelf_link(book_id, base_url, matched_item_id)
            logging.info(
                f"Audiobookshelf link resolved for local book {book_id}: item={matched_item_id}, base={base_url}"
            )
            return base_url, matched_item_id, api_key
    except AudiobookshelfError as e:
        logging.info(f"Audiobookshelf target lookup skipped for book {book_id}: {e}")
    except Exception as e:
        logging.warning(f"Audiobookshelf target lookup failed for book {book_id}: {e}")

    return None, None, None
