# audiobookshelf_client.py
# Copyright (c) 2025-2026 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import json
import http.client
import mimetypes
import os
import re
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen


class AudiobookshelfError(Exception):
    """Raised when an Audiobookshelf API operation fails."""


@dataclass
class AudiobookshelfTrack:
    stream_url: str
    filename: str
    duration_ms: int


@dataclass
class AudiobookshelfBookImport:
    item_id: str
    title: str
    book_type: str
    author: Optional[str]
    narrator: Optional[str]
    description: Optional[str]
    root_path: str
    files: List[Tuple[str, int, int]]
    tracks: List[AudiobookshelfTrack]


@dataclass
class AudiobookshelfChapter:
    start_ms: int
    end_ms: int
    title: str


class AudiobookshelfClient:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: int = 20):
        self.base_url = self._normalize_base_url(base_url)
        self.api_key = (api_key or "").strip()
        if not self.api_key:
            raise AudiobookshelfError("Audiobookshelf API key is required.")

        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _normalize_base_url(raw_url: str) -> str:
        url = (raw_url or "").strip()
        if not url:
            raise AudiobookshelfError("Audiobookshelf server URL is required.")

        if "://" not in url:
            url = f"http://{url}"

        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise AudiobookshelfError("Invalid Audiobookshelf server URL.")

        clean_path = parsed.path.rstrip("/")
        if clean_path.endswith("/api"):
            clean_path = clean_path[:-4]

        normalized = parsed._replace(path=clean_path, params="", query="", fragment="")
        return urlunparse(normalized).rstrip("/")

    def _api_url(self, endpoint: str) -> str:
        endpoint = endpoint.lstrip("/")
        return urljoin(self.base_url + "/", f"api/{endpoint}")

    def _request(
            self,
            method: str,
            endpoint: str,
            params: Optional[Dict[str, Any]] = None,
            payload: Optional[Dict[str, Any]] = None
    ) -> Any:
        url = self._api_url(endpoint)
        if params:
            query = urlencode(params, doseq=True)
            if query:
                url = f"{url}?{query}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode("utf-8")

        req = Request(url=url, data=body, method=method.upper(), headers=headers)

        try:
            with urlopen(req, timeout=self.timeout_seconds) as response:
                raw_text = response.read().decode("utf-8", errors="replace")
        except HTTPError as e:
            err_msg = e.reason or "Unknown API error"
            try:
                raw = e.read().decode("utf-8", errors="replace")
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    err_msg = parsed.get("error") or parsed.get("message") or err_msg
            except Exception:
                pass
            raise AudiobookshelfError(f"Audiobookshelf API error ({e.code}): {err_msg}") from e
        except URLError as e:
            raise AudiobookshelfError(f"Unable to reach Audiobookshelf server: {e.reason}") from e
        except Exception as e:
            raise AudiobookshelfError(f"Unexpected network error: {e}") from e

        if not raw_text:
            return {}

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as e:
            raise AudiobookshelfError("Received invalid JSON from Audiobookshelf server.") from e

    def get_media_progress(self, item_id: str) -> Optional[Dict[str, Any]]:
        if not item_id:
            return None
        try:
            data = self._request("GET", f"me/progress/{item_id}")
            return data if isinstance(data, dict) else None
        except AudiobookshelfError as e:
            if "(404)" in str(e):
                return None
            raise

    def update_media_progress(
            self,
            item_id: str,
            current_time_seconds: float,
            duration_seconds: float,
            is_finished: bool
    ) -> Dict[str, Any]:
        if not item_id:
            raise AudiobookshelfError("Invalid Audiobookshelf item id.")

        duration_seconds = max(0.0, float(duration_seconds or 0.0))
        current_time_seconds = max(0.0, float(current_time_seconds or 0.0))

        progress = 0.0
        if duration_seconds > 0:
            progress = min(1.0, current_time_seconds / duration_seconds)
        if is_finished:
            progress = 1.0

        payload = {
            "libraryItemId": item_id,
            "duration": duration_seconds,
            "progress": progress,
            "currentTime": current_time_seconds,
            "isFinished": bool(is_finished),
        }
        try:
            data = self._request("PATCH", f"me/progress/{item_id}", payload=payload)
            return data if isinstance(data, dict) else {}
        except AudiobookshelfError as e:
            # Some Audiobookshelf builds return plain-text/empty confirmation for PATCH.
            if "invalid json" in str(e).lower():
                return {}
            raise

    def get_item_details(self, item_id: str, expanded: int = 1) -> Dict[str, Any]:
        if not item_id:
            raise AudiobookshelfError("Invalid Audiobookshelf item id.")
        data = self._request("GET", f"items/{item_id}", params={"expanded": expanded})
        if not isinstance(data, dict):
            raise AudiobookshelfError("Unexpected response while loading item details.")
        return data

    def get_item_chapters(self, item_id: str) -> List[AudiobookshelfChapter]:
        item_data = self.get_item_details(item_id=item_id, expanded=1)
        return self._extract_chapters_from_item(item_data)

    def get_libraries(self) -> List[Dict[str, Any]]:
        data = self._request("GET", "libraries")
        if isinstance(data, dict):
            libraries = data.get("libraries", [])
        elif isinstance(data, list):
            libraries = data
        else:
            libraries = []

        return [lib for lib in libraries if isinstance(lib, dict)]

    def resolve_upload_destination(
            self,
            preferred_library_id: Optional[str] = None,
            preferred_folder_id: Optional[str] = None
    ) -> Tuple[str, str]:
        libraries = self.get_libraries()
        if not libraries:
            raise AudiobookshelfError("No Audiobookshelf libraries were found.")

        library_id = (preferred_library_id or "").strip()
        folder_id = (preferred_folder_id or "").strip()

        selected_library = None
        if library_id:
            for lib in libraries:
                if str(lib.get("id", "")).strip() == library_id:
                    selected_library = lib
                    break
            if selected_library is None:
                raise AudiobookshelfError("Configured Audiobookshelf upload library was not found.")
        else:
            book_like = []
            for lib in libraries:
                media_type = str(lib.get("mediaType") or "").strip().lower()
                if media_type in {"book", "books", "audiobook", "audiobooks"}:
                    book_like.append(lib)
            selected_library = book_like[0] if book_like else libraries[0]
            library_id = str(selected_library.get("id", "")).strip()

        if not library_id:
            raise AudiobookshelfError("Unable to determine Audiobookshelf upload library.")

        folders = selected_library.get("folders") if isinstance(selected_library, dict) else None
        folders = folders if isinstance(folders, list) else []

        selected_folder = None
        if folder_id:
            for folder in folders:
                if not isinstance(folder, dict):
                    continue
                if str(folder.get("id", "")).strip() == folder_id:
                    selected_folder = folder
                    break
            if selected_folder is None:
                raise AudiobookshelfError("Configured Audiobookshelf upload folder was not found in the selected library.")
        else:
            for folder in folders:
                if isinstance(folder, dict) and str(folder.get("id", "")).strip():
                    selected_folder = folder
                    break
            if selected_folder is None:
                raise AudiobookshelfError("Selected Audiobookshelf library has no upload folder.")
            folder_id = str(selected_folder.get("id", "")).strip()

        if not folder_id:
            raise AudiobookshelfError("Unable to determine Audiobookshelf upload folder.")

        return library_id, folder_id

    def get_library_items(self, library_id: str, page_size: int = 200) -> List[Dict[str, Any]]:
        all_items: List[Dict[str, Any]] = []
        page = 0

        while True:
            data = self._request(
                "GET",
                f"libraries/{library_id}/items",
                params={
                    "limit": page_size,
                    "page": page,
                    "minified": 1,
                    "sort": "media.metadata.title",
                    "desc": 0,
                }
            )

            if isinstance(data, dict):
                results = data.get("results", [])
                total = data.get("total")
            elif isinstance(data, list):
                results = data
                total = None
            else:
                results = []
                total = None

            page_items = [item for item in results if isinstance(item, dict)]
            if not page_items:
                break

            all_items.extend(page_items)

            if isinstance(total, int) and len(all_items) >= total:
                break
            if len(page_items) < page_size:
                break

            page += 1
            if page > 1000:
                break

        return all_items

    def trigger_library_scan(self, library_id: str) -> Dict[str, Any]:
        if not library_id:
            raise AudiobookshelfError("Audiobookshelf library ID is required for scanning.")
        try:
            data = self._request("POST", f"libraries/{library_id}/scan")
            return data if isinstance(data, dict) else {}
        except AudiobookshelfError as e:
            # Some Audiobookshelf builds respond with plain text confirmation (e.g. "OK").
            if "invalid json" in str(e).lower():
                return {}
            raise

    def build_book_import(self, item_id: str, item_hint: Optional[Dict[str, Any]] = None) -> AudiobookshelfBookImport:
        if not item_id:
            raise AudiobookshelfError("Invalid Audiobookshelf item id.")

        item_data = self.get_item_details(item_id=item_id, expanded=1)

        title = self._extract_title(item_data) or self._extract_title(item_hint) or f"Audiobookshelf Item {item_id}"
        author = self._extract_author(item_data) or self._extract_author(item_hint)
        narrator = self._extract_narrator(item_data) or self._extract_narrator(item_hint)
        description = self._extract_description(item_data) or self._extract_description(item_hint)

        book_type = "audio"
        tracks = self._extract_tracks_from_item(item_data)
        if not tracks:
            ebook_track = self._extract_ebook_track_from_item(item_data, item_id=item_id)
            if ebook_track:
                tracks = [ebook_track]
                book_type = "ebook"

        if not tracks:
            tracks = self._extract_tracks_from_play(item_id)
            book_type = "audio"

        if not tracks:
            raise AudiobookshelfError(f"Item '{title}' has no playable content.")

        files: List[Tuple[str, int, int]] = []
        normalized_tracks: List[AudiobookshelfTrack] = []
        for index, track in enumerate(tracks):
            stream_url = self._ensure_token_query(self._absolute_url(track.stream_url))
            safe_filename = self._safe_filename(track.filename, fallback_index=index)
            normalized_track = AudiobookshelfTrack(
                stream_url=stream_url,
                filename=safe_filename,
                duration_ms=max(0, int(track.duration_ms or 0))
            )
            normalized_tracks.append(normalized_track)
            files.append((stream_url, index, normalized_track.duration_ms))

        root_path = f"abs:{self.base_url}/item/{item_id}"

        return AudiobookshelfBookImport(
            item_id=item_id,
            title=title,
            book_type=book_type,
            author=author,
            narrator=narrator,
            description=description,
            root_path=root_path,
            files=files,
            tracks=normalized_tracks,
        )

    def download_tracks(self, tracks: List[AudiobookshelfTrack], target_dir: str) -> List[str]:
        if not target_dir:
            raise AudiobookshelfError("Target download directory is required.")

        os.makedirs(target_dir, exist_ok=True)
        local_paths: List[str] = []
        used_names = set()

        for index, track in enumerate(tracks):
            base_name = self._safe_filename(track.filename, fallback_index=index)
            file_name = self._dedupe_filename(base_name, used_names)
            used_names.add(file_name.lower())

            out_path = os.path.join(target_dir, file_name)
            if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
                self._download_file(track.stream_url, out_path)

            local_paths.append(out_path)

        return local_paths

    def upload_library_item(
            self,
            *,
            title: str,
            file_paths: List[str],
            library_id: str,
            folder_id: str,
            author: Optional[str] = None,
            series: Optional[str] = None
    ) -> Dict[str, Any]:
        if not file_paths:
            raise AudiobookshelfError("No files were provided for upload.")
        if not library_id:
            raise AudiobookshelfError("Audiobookshelf library ID is required for upload.")
        if not folder_id:
            raise AudiobookshelfError("Audiobookshelf folder ID is required for upload.")

        existing_paths = []
        for path in file_paths:
            if path and os.path.isfile(path):
                existing_paths.append(path)
        if not existing_paths:
            raise AudiobookshelfError("No local files were found for upload.")

        form_fields = {
            "title": (title or "").strip() or "Uploaded Book",
            "library": str(library_id).strip(),
            "folder": str(folder_id).strip(),
        }
        if author:
            form_fields["author"] = str(author).strip()
        if series:
            form_fields["series"] = str(series).strip()

        upload_url = self._api_url("upload")
        parsed = urlparse(upload_url)
        if parsed.scheme not in {"http", "https"}:
            raise AudiobookshelfError("Unsupported Audiobookshelf upload URL scheme.")

        boundary = f"----AudioShelfUpload{uuid.uuid4().hex}"

        def _field_header_bytes(name: str) -> bytes:
            return (
                f"--{boundary}\r\n"
                f"Content-Disposition: form-data; name=\"{name}\"\r\n\r\n"
            ).encode("utf-8")

        def _file_header_bytes(name: str, file_name: str, mime_type: str) -> bytes:
            return (
                f"--{boundary}\r\n"
                f"Content-Disposition: form-data; name=\"{name}\"; filename=\"{file_name}\"\r\n"
                f"Content-Type: {mime_type}\r\n\r\n"
            ).encode("utf-8")

        closing = f"--{boundary}--\r\n".encode("utf-8")

        total_length = 0
        for key, value in form_fields.items():
            value_bytes = str(value).encode("utf-8")
            total_length += len(_field_header_bytes(key)) + len(value_bytes) + 2

        for idx, file_path in enumerate(existing_paths):
            file_name = os.path.basename(file_path) or f"file_{idx}"
            mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
            total_length += len(_file_header_bytes(str(idx), file_name, mime_type))
            total_length += os.path.getsize(file_path)
            total_length += 2

        total_length += len(closing)

        conn = None
        try:
            if parsed.scheme == "https":
                conn = http.client.HTTPSConnection(parsed.hostname, parsed.port, timeout=self.timeout_seconds)
            else:
                conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=self.timeout_seconds)

            request_path = parsed.path or "/"
            if parsed.query:
                request_path = f"{request_path}?{parsed.query}"

            conn.putrequest("POST", request_path)
            conn.putheader("Authorization", f"Bearer {self.api_key}")
            conn.putheader("Accept", "application/json")
            conn.putheader("Content-Type", f"multipart/form-data; boundary={boundary}")
            conn.putheader("Content-Length", str(total_length))
            conn.endheaders()

            for key, value in form_fields.items():
                conn.send(_field_header_bytes(key))
                conn.send(str(value).encode("utf-8"))
                conn.send(b"\r\n")

            for idx, file_path in enumerate(existing_paths):
                file_name = os.path.basename(file_path) or f"file_{idx}"
                mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
                conn.send(_file_header_bytes(str(idx), file_name, mime_type))
                with open(file_path, "rb") as f:
                    while True:
                        chunk = f.read(1024 * 512)
                        if not chunk:
                            break
                        conn.send(chunk)
                conn.send(b"\r\n")

            conn.send(closing)

            response = conn.getresponse()
            status = int(response.status or 0)
            raw_text = response.read().decode("utf-8", errors="replace")

            if status < 200 or status >= 300:
                err_msg = response.reason or "Upload failed"
                try:
                    parsed_err = json.loads(raw_text) if raw_text else {}
                    if isinstance(parsed_err, dict):
                        err_msg = parsed_err.get("error") or parsed_err.get("message") or err_msg
                except Exception:
                    if raw_text.strip():
                        err_msg = raw_text.strip()
                raise AudiobookshelfError(f"Audiobookshelf upload failed ({status}): {err_msg}")

            if not raw_text:
                return {}
            try:
                parsed_ok = json.loads(raw_text)
                return parsed_ok if isinstance(parsed_ok, dict) else {"response": parsed_ok}
            except json.JSONDecodeError:
                return {"response": raw_text}
        except OSError as e:
            raise AudiobookshelfError(f"Unable to upload to Audiobookshelf server: {e}") from e
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass

    def _download_file(self, source_url: str, destination_path: str):
        tmp_path = destination_path + ".part"
        req = Request(
            url=source_url,
            method="GET",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        try:
            with urlopen(req, timeout=self.timeout_seconds) as response, open(tmp_path, "wb") as out:
                while True:
                    chunk = response.read(1024 * 512)
                    if not chunk:
                        break
                    out.write(chunk)
            os.replace(tmp_path, destination_path)
        except Exception as e:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            raise AudiobookshelfError(f"Failed to download track: {e}") from e

    def _extract_tracks_from_item(self, item_data: Dict[str, Any]) -> List[AudiobookshelfTrack]:
        media = item_data.get("media") if isinstance(item_data, dict) else None
        if not isinstance(media, dict):
            return []

        tracks = media.get("tracks")
        if not isinstance(tracks, list):
            return []

        entries: List[AudiobookshelfTrack] = []
        seen = set()

        for idx, track in enumerate(tracks):
            if not isinstance(track, dict):
                continue
            raw_url = track.get("contentUrl") or track.get("url")
            if not isinstance(raw_url, str):
                continue
            clean = raw_url.strip()
            if not clean or clean in seen:
                continue
            seen.add(clean)
            filename = self._filename_from_track(track, idx)
            duration_ms = int(float(track.get("duration", 0)) * 1000) if track.get("duration") else 0
            entries.append(AudiobookshelfTrack(stream_url=clean, filename=filename, duration_ms=duration_ms))

        return entries

    def _extract_ebook_track_from_item(self, item_data: Dict[str, Any], item_id: str) -> Optional[AudiobookshelfTrack]:
        media = item_data.get("media") if isinstance(item_data, dict) else None
        if not isinstance(media, dict):
            return None

        ebook_file = media.get("ebookFile")
        if not isinstance(ebook_file, dict):
            return None

        metadata = ebook_file.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}

        rel_path = str(metadata.get("relPath") or "").strip().replace("\\", "/")
        filename = str(metadata.get("filename") or "").strip()
        if not filename and rel_path:
            filename = rel_path.split("/")[-1].strip()

        ebook_format = str(ebook_file.get("ebookFormat") or media.get("ebookFormat") or "").strip().lower()
        if not filename:
            fallback_ext = f".{ebook_format}" if ebook_format else ".epub"
            filename = f"ebook{fallback_ext}"

        content_url = ""
        if rel_path:
            safe_rel = "/".join(quote(part) for part in rel_path.split("/") if part)
            if safe_rel:
                content_url = f"/s/item/{quote(item_id)}/{safe_rel}"

        if not content_url:
            safe_name = quote(filename)
            content_url = f"/s/item/{quote(item_id)}/{safe_name}"

        return AudiobookshelfTrack(stream_url=content_url, filename=filename, duration_ms=0)

    @staticmethod
    def _extract_chapters_from_item(item_data: Dict[str, Any]) -> List[AudiobookshelfChapter]:
        media = item_data.get("media") if isinstance(item_data, dict) else None
        if not isinstance(media, dict):
            return []

        raw_chapters = media.get("chapters")
        if not isinstance(raw_chapters, list):
            return []

        duration_ms = 0
        try:
            duration_ms = max(0, int(float(media.get("duration") or 0.0) * 1000))
        except (TypeError, ValueError):
            duration_ms = 0

        parsed: List[AudiobookshelfChapter] = []
        for idx, chapter in enumerate(raw_chapters):
            if not isinstance(chapter, dict):
                continue

            try:
                start_ms = max(0, int(float(chapter.get("start") or 0.0) * 1000))
            except (TypeError, ValueError):
                continue

            try:
                end_ms = max(start_ms, int(float(chapter.get("end") or 0.0) * 1000))
            except (TypeError, ValueError):
                end_ms = start_ms

            title = str(chapter.get("title") or "").strip() or f"Chapter {idx + 1}"
            parsed.append(AudiobookshelfChapter(start_ms=start_ms, end_ms=end_ms, title=title))

        if not parsed:
            return []

        parsed.sort(key=lambda c: c.start_ms)
        for idx, ch in enumerate(parsed):
            if ch.end_ms <= ch.start_ms:
                if idx + 1 < len(parsed):
                    ch.end_ms = max(ch.start_ms, parsed[idx + 1].start_ms)
                elif duration_ms > ch.start_ms:
                    ch.end_ms = duration_ms
                else:
                    ch.end_ms = ch.start_ms

        # Return only chapters with non-zero ranges when possible.
        non_empty = [c for c in parsed if c.end_ms > c.start_ms]
        return non_empty if non_empty else parsed

    def _extract_tracks_from_play(self, item_id: str) -> List[AudiobookshelfTrack]:
        playback = self._request(
            "POST",
            f"items/{item_id}/play",
            payload={
                "deviceInfo": {
                    "clientName": "AudioShelf",
                    "clientVersion": "1.0",
                    "manufacturer": "AudioShelf",
                    "model": "Desktop",
                    "osName": "Windows",
                },
                "forceDirectPlay": True,
            }
        )

        if not isinstance(playback, dict):
            return []

        tracks = playback.get("audioTracks")
        if not isinstance(tracks, list):
            tracks = []

        entries: List[AudiobookshelfTrack] = []
        seen = set()
        for idx, track in enumerate(tracks):
            if not isinstance(track, dict):
                continue
            raw_url = track.get("contentUrl") or track.get("url")
            if not isinstance(raw_url, str):
                continue
            clean = raw_url.strip()
            if not clean or clean in seen:
                continue
            seen.add(clean)
            filename = self._filename_from_track(track, idx)
            duration_ms = int(float(track.get("duration", 0)) * 1000) if track.get("duration") else 0
            entries.append(AudiobookshelfTrack(stream_url=clean, filename=filename, duration_ms=duration_ms))

        single_url = playback.get("contentUrl")
        if isinstance(single_url, str):
            single_clean = single_url.strip()
            if single_clean and single_clean not in seen:
                entries.append(AudiobookshelfTrack(stream_url=single_clean, filename="track_001.m4b", duration_ms=0))

        return entries

    def _absolute_url(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            return url
        if not url.startswith("/"):
            return urljoin(self.base_url + "/", url)

        base = urlparse(self.base_url)
        base_prefix = base.path.rstrip("/")
        if base_prefix and not url.startswith(base_prefix + "/"):
            return f"{base.scheme}://{base.netloc}{base_prefix}{url}"
        return f"{base.scheme}://{base.netloc}{url}"

    def _ensure_token_query(self, url: str) -> str:
        parsed = urlparse(url)
        params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if "token" not in params:
            params["token"] = self.api_key
        new_query = urlencode(params, doseq=True)
        return urlunparse(parsed._replace(query=new_query))

    @staticmethod
    def extract_token_from_stream_url(stream_url: Optional[str]) -> Optional[str]:
        if not stream_url:
            return None
        parsed = urlparse(stream_url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        token = query.get("token")
        token = token.strip() if isinstance(token, str) else ""
        return token or None

    @staticmethod
    def parse_remote_book_root(root_path: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        if not root_path or not str(root_path).startswith("abs:"):
            return None, None

        raw_url = str(root_path)[4:].strip()
        if not raw_url:
            return None, None

        parsed = urlparse(raw_url)
        marker = "/item/"
        idx = parsed.path.rfind(marker)
        if idx == -1:
            return None, None

        item_id = parsed.path[idx + len(marker):].strip("/")
        base_path = parsed.path[:idx].rstrip("/")
        base = parsed._replace(path=base_path, params="", query="", fragment="")
        base_url = urlunparse(base).rstrip("/")

        if not base_url or not item_id:
            return None, None
        return base_url, item_id

    def make_download_folder_name(self, title: str, item_id: str) -> str:
        safe_title = self._safe_path_component(title) or "Audiobook"
        short_id = item_id[:8] if item_id else "item"
        return f"{safe_title} [ABS-{short_id}]"

    @classmethod
    def _filename_from_track(cls, track: Dict[str, Any], index: int) -> str:
        metadata = track.get("metadata")
        if isinstance(metadata, dict):
            filename = metadata.get("filename") or metadata.get("relPath")
            if isinstance(filename, str) and filename.strip():
                return filename.strip().split("/")[-1].split("\\")[-1]

        title = track.get("title")
        if isinstance(title, str) and title.strip():
            base = cls._safe_path_component(title.strip())
            ext = ".m4b"
            return f"{base or 'track'}_{index + 1:03d}{ext}"

        return f"track_{index + 1:03d}.m4b"

    @classmethod
    def _safe_filename(cls, filename: str, fallback_index: int = 0) -> str:
        raw_name = (filename or "").strip()
        if not raw_name:
            raw_name = f"track_{fallback_index + 1:03d}.m4b"
        raw_name = raw_name.replace("/", "_").replace("\\", "_")
        base, ext = os.path.splitext(raw_name)
        safe_base = cls._safe_path_component(base) or f"track_{fallback_index + 1:03d}"
        safe_ext = cls._safe_extension(ext)
        return f"{safe_base}{safe_ext}"

    @staticmethod
    def _safe_extension(ext: str) -> str:
        clean = re.sub(r"[^A-Za-z0-9.]", "", ext or "").strip()
        if not clean:
            return ".m4b"
        if not clean.startswith("."):
            clean = "." + clean
        return clean[:12]

    @staticmethod
    def _safe_path_component(name: str) -> str:
        cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", (name or "").strip())
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
        return cleaned[:120]

    @staticmethod
    def _dedupe_filename(filename: str, used_lower_names: set) -> str:
        if filename.lower() not in used_lower_names:
            return filename
        stem, ext = os.path.splitext(filename)
        n = 2
        while True:
            candidate = f"{stem} ({n}){ext}"
            if candidate.lower() not in used_lower_names:
                return candidate
            n += 1

    @staticmethod
    def _metadata_from_item(item_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not isinstance(item_data, dict):
            return {}
        media = item_data.get("media")
        if not isinstance(media, dict):
            return {}
        metadata = media.get("metadata")
        return metadata if isinstance(metadata, dict) else {}

    @staticmethod
    def _normalize_text(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @classmethod
    def _join_name_list(cls, value: Any) -> Optional[str]:
        if isinstance(value, str):
            return cls._normalize_text(value)
        if not isinstance(value, list):
            return None

        names: List[str] = []
        for item in value:
            if isinstance(item, str):
                name = item.strip()
            elif isinstance(item, dict):
                name = str(item.get("name", "")).strip()
            else:
                name = ""
            if name:
                names.append(name)

        return ", ".join(names) if names else None

    @classmethod
    def _extract_title(cls, item_data: Optional[Dict[str, Any]]) -> Optional[str]:
        metadata = cls._metadata_from_item(item_data)
        title = metadata.get("title")
        if not title and isinstance(item_data, dict):
            title = item_data.get("title")
        return cls._normalize_text(title)

    @classmethod
    def _extract_author(cls, item_data: Optional[Dict[str, Any]]) -> Optional[str]:
        metadata = cls._metadata_from_item(item_data)
        author = metadata.get("authorName")
        if not author:
            author = cls._join_name_list(metadata.get("authors"))
        return cls._normalize_text(author) if isinstance(author, str) else author

    @classmethod
    def _extract_narrator(cls, item_data: Optional[Dict[str, Any]]) -> Optional[str]:
        metadata = cls._metadata_from_item(item_data)
        narrator = metadata.get("narratorName")
        if not narrator:
            narrator = cls._join_name_list(metadata.get("narrators"))
        return cls._normalize_text(narrator) if isinstance(narrator, str) else narrator

    @classmethod
    def _extract_description(cls, item_data: Optional[Dict[str, Any]]) -> Optional[str]:
        metadata = cls._metadata_from_item(item_data)
        return cls._normalize_text(metadata.get("description"))

