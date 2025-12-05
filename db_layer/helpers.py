# db_layer/helpers.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import os
import logging
from typing import List, Tuple, Optional


def get_book_size_on_disk(book_path: Optional[str]) -> Optional[int]:
    """
    Calculates the total size of all files within a book's root path.

    Args:
        book_path: The absolute path to the book's directory.

    Returns:
        The total size in bytes, or None if the path is invalid or an error occurs.
    """
    if not book_path or not os.path.isdir(book_path):
        return None

    total_size = 0
    try:
        for dirpath, _, filenames in os.walk(book_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.isfile(fp) and not os.path.islink(fp):
                    try:
                        total_size += os.path.getsize(fp)
                    except OSError:
                        pass  # Skip files we cannot read
    except Exception as e:
        logging.error(f"Error calculating book size for {book_path}: {e}", exc_info=True)
        return None

    return total_size


def find_missing_books(all_books: List[Tuple[int, str, str]]) -> List[Tuple[int, str]]:
    """
    Checks which books have invalid or missing root paths on the disk.

    Args:
        all_books: A list of tuples containing (book_id, title, root_path).

    Returns:
        A list of tuples (book_id, title) for books that are missing from the disk.
    """
    missing_books = []
    try:
        for book_id, title, root_path in all_books:
            if not os.path.isdir(root_path):
                missing_books.append((book_id, title))
        return missing_books
    except Exception as e:
        logging.error(f"Error finding missing books: {e}", exc_info=True)
        return []