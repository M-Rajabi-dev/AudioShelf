import unittest
from datetime import datetime

from playback.abs_sync_utils import (
    compute_total_position_ms,
    split_total_position_ms,
    parse_local_timestamp_to_epoch_ms,
    should_prefer_remote_progress,
)


class AbsSyncUtilsTests(unittest.TestCase):
    def test_compute_total_position_ms_aggregates_previous_tracks(self):
        self.assertEqual(
            compute_total_position_ms([1000, 2000, 3000], current_file_index=2, current_file_position_ms=500),
            3500,
        )

    def test_compute_total_position_ms_negative_index_falls_back_to_current_position(self):
        self.assertEqual(
            compute_total_position_ms([1000, 2000], current_file_index=-1, current_file_position_ms=700),
            700,
        )

    def test_split_total_position_ms_returns_track_and_offset(self):
        self.assertEqual(split_total_position_ms([1000, 2000, 3000], 2500), (1, 1500))

    def test_split_total_position_ms_beyond_total_returns_last_track(self):
        self.assertEqual(split_total_position_ms([1000, 2000], 5000), (1, 2000))

    def test_parse_local_timestamp_to_epoch_ms_supports_both_formats(self):
        dt = datetime(2026, 3, 13, 12, 34, 56, 123456)
        with_ms = dt.strftime("%Y-%m-%d %H:%M:%S.%f")
        without_ms = dt.strftime("%Y-%m-%d %H:%M:%S")

        self.assertEqual(parse_local_timestamp_to_epoch_ms(with_ms), int(dt.timestamp() * 1000))
        self.assertEqual(parse_local_timestamp_to_epoch_ms(without_ms), int(dt.replace(microsecond=0).timestamp() * 1000))
        self.assertIsNone(parse_local_timestamp_to_epoch_ms("not-a-date"))

    def test_should_prefer_remote_progress_prefers_newer_timestamp(self):
        self.assertTrue(
            should_prefer_remote_progress(
                remote_last_update_ms=5000,
                local_last_update_ms=1000,
                remote_total_position_ms=1000,
                local_total_position_ms=9000,
            )
        )

    def test_should_prefer_remote_progress_rejects_older_timestamp(self):
        self.assertFalse(
            should_prefer_remote_progress(
                remote_last_update_ms=1000,
                local_last_update_ms=5000,
                remote_total_position_ms=9000,
                local_total_position_ms=1000,
            )
        )

    def test_should_prefer_remote_progress_falls_back_to_position_when_timestamps_missing(self):
        self.assertTrue(
            should_prefer_remote_progress(
                remote_last_update_ms=None,
                local_last_update_ms=None,
                remote_total_position_ms=12000,
                local_total_position_ms=1000,
            )
        )
        self.assertFalse(
            should_prefer_remote_progress(
                remote_last_update_ms=None,
                local_last_update_ms=None,
                remote_total_position_ms=1000,
                local_total_position_ms=12000,
            )
        )


if __name__ == "__main__":
    unittest.main()
