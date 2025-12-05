# book_scanner.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import os
import re
import sys
import logging
import concurrent.futures
from typing import List, Tuple

try:
    from tinytag import TinyTag
except ImportError:
    print("CRITICAL: 'tinytag' library not found. Please install it: pip install tinytag")
    sys.exit(1)

SUPPORTED_EXTENSIONS = {
    '.mp3', '.m4a', '.m4b', '.aac', '.flac', '.ogg', '.oga', '.wav',
    '.wma', '.opus', '.aiff',
    '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv',
}


def _fix_long_path(path: str) -> str:
    """Ensures the path works on Windows even if it exceeds 260 characters."""
    if sys.platform == 'win32':
        path = os.path.abspath(path)
        if not path.startswith('\\\\?\\'):
            return f"\\\\?\\{path}"
    return os.path.abspath(path)


def natural_sort_key(s: str) -> List:
    """Generates a key for natural sorting of file paths."""
    segments = s.split(os.sep)
    final_key = []
    numeric_parts_regex = re.compile(r'(\d+)')

    for segment in segments:
        parts = [int(text) if text.isdigit() else text.lower()
                 for text in numeric_parts_regex.split(segment)]
        final_key.extend(parts)
        final_key.append('')

    if final_key:
        final_key.pop()
    return final_key


def _get_duration_with_tinytag(file_path: str) -> int:
    """Reads the duration of a media file in milliseconds using TinyTag."""
    try:
        if os.path.getsize(file_path) == 0:
            return 0
        tag = TinyTag.get(file_path, image=False)
        if tag and tag.duration:
            return int(tag.duration * 1000)
        return 0
    except Exception as e:
        logging.debug(f"Failed to read duration for {file_path}: {e}")
        return 0


def _recursive_scan(directory: str) -> List[str]:
    """Recursively scans a directory for supported media files."""
    file_paths = []
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.is_dir(follow_symlinks=False):
                    file_paths.extend(_recursive_scan(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    _, ext = os.path.splitext(entry.name)
                    if ext.lower() in SUPPORTED_EXTENSIONS:
                        file_paths.append(entry.path)
    except OSError as e:
        logging.error(f"Error scanning directory {directory}: {e}")
    return file_paths


def scan_folder(root_path: str, fast_scan: bool = False) -> List[Tuple[str, int, int]]:
    """
    Scans a directory or single file and retrieves metadata.

    Args:
        root_path: The path to the directory or single file.
        fast_scan: If True, returns 0 for duration to allow immediate UI loading.

    Returns:
        A list of tuples (full_path, index, duration_ms).
    """
    safe_root_path = _fix_long_path(root_path)
    playable_files_paths: List[str] = []

    if os.path.isfile(safe_root_path):
        _, ext = os.path.splitext(safe_root_path)
        if ext.lower() in SUPPORTED_EXTENSIONS:
            playable_files_paths.append(safe_root_path)
        else:
            logging.error(f"File '{safe_root_path}' is not a supported audio format.")
            return []
    elif os.path.isdir(safe_root_path):
        playable_files_paths = _recursive_scan(safe_root_path)
    else:
        logging.error(f"Path '{safe_root_path}' is not a valid directory or file.")
        return []

    playable_files_paths.sort(key=natural_sort_key)

    final_files_data: List[Tuple[str, int, int]] = []
    file_count = len(playable_files_paths)

    if file_count > 0:
        if fast_scan:
            logging.info(f"Fast scanning {file_count} files.")
            for i, path in enumerate(playable_files_paths):
                final_files_data.append((path, i, 0))
        else:
            cpu_count = os.cpu_count() or 4
            max_workers = min(16, cpu_count * 2)
            logging.info(f"Deep scanning {file_count} files using {max_workers} threads...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                durations = executor.map(_get_duration_with_tinytag, playable_files_paths)
                for i, (path, duration) in enumerate(zip(playable_files_paths, durations)):
                    final_files_data.append((path, i, duration))

    return final_files_data
