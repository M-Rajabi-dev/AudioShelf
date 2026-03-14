# playback/abs_sync_utils.py
# Copyright (c) 2025-2026 Mehdi Rajabi
# License: GNU General Public License v3.0 (See LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from datetime import datetime
from typing import List, Optional, Tuple


def compute_total_position_ms(
        file_durations_ms: List[int],
        current_file_index: int,
        current_file_position_ms: int
) -> int:
    """
    Converts per-file playback position to a book-level absolute position.
    """
    if current_file_index < 0:
        return max(0, int(current_file_position_ms or 0))

    total = 0
    for i in range(min(current_file_index, len(file_durations_ms))):
        dur = int(file_durations_ms[i] or 0)
        if dur > 0:
            total += dur

    total += max(0, int(current_file_position_ms or 0))
    return max(0, total)


def split_total_position_ms(file_durations_ms: List[int], total_position_ms: int) -> Tuple[int, int]:
    """
    Converts a book-level absolute position into (file_index, position_in_file_ms).
    """
    total_position_ms = max(0, int(total_position_ms or 0))
    if not file_durations_ms:
        return 0, total_position_ms

    remaining = total_position_ms
    for idx, raw_dur in enumerate(file_durations_ms):
        dur = int(raw_dur or 0)
        if dur <= 0:
            continue
        if remaining < dur:
            return idx, remaining
        remaining -= dur

    last_idx = max(0, len(file_durations_ms) - 1)
    return last_idx, remaining


def parse_local_timestamp_to_epoch_ms(local_timestamp: Optional[str]) -> Optional[int]:
    if not local_timestamp:
        return None

    formats = [
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(local_timestamp, fmt)
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue

    return None


def should_prefer_remote_progress(
        remote_last_update_ms: Optional[int],
        local_last_update_ms: Optional[int],
        remote_total_position_ms: int,
        local_total_position_ms: int,
        epsilon_ms: int = 2000
) -> bool:
    """
    Decides if remote progress should overwrite local state.
    """
    remote_total_position_ms = max(0, int(remote_total_position_ms or 0))
    local_total_position_ms = max(0, int(local_total_position_ms or 0))

    if remote_last_update_ms and local_last_update_ms:
        if int(remote_last_update_ms) > int(local_last_update_ms) + int(epsilon_ms):
            return True
        if int(local_last_update_ms) > int(remote_last_update_ms) + int(epsilon_ms):
            return False

    if remote_total_position_ms > local_total_position_ms + int(epsilon_ms):
        return True
    return False
