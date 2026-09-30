import logging
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, time
from unittest import mock
from pathlib import Path

import config
from postman import AppTimeFormatter, is_within_active_period, parse_active_time, seconds_until_active_period


class ConfigTests(unittest.TestCase):
    def test_read_email_body_prefers_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            body_path = Path(tmpdir) / "email.txt"
            body_path.write_text("Hello from file", encoding="utf-8")

            self.assertEqual(config.read_email_body(body_path), "Hello from file")


class ActivePeriodTests(unittest.TestCase):
    def test_parse_active_time(self):
        self.assertEqual(parse_active_time("08:30", "TEST_TIME"), time(8, 30))

    def test_daytime_window(self):
        self.assertTrue(is_within_active_period(time(12, 0), time(8, 0), time(23, 0)))
        self.assertFalse(is_within_active_period(time(7, 59), time(8, 0), time(23, 0)))

    def test_overnight_window(self):
        self.assertTrue(is_within_active_period(time(23, 30), time(23, 0), time(8, 0)))
        self.assertTrue(is_within_active_period(time(7, 30), time(23, 0), time(8, 0)))
        self.assertFalse(is_within_active_period(time(12, 0), time(23, 0), time(8, 0)))

    def test_seconds_until_next_active_period(self):
        now = datetime(2026, 7, 25, 7, 30)
        self.assertEqual(seconds_until_active_period(now, time(8, 0), time(23, 0)), 1800)


class TimezoneOffsetTests(unittest.TestCase):
    TIMESTAMP = 1_700_000_000  # 2023-11-14 22:13:20 UTC

    def test_parse_timezone_offset(self):
        self.assertIsNone(config.parse_timezone_offset(None))
        self.assertIsNone(config.parse_timezone_offset("  "))
        self.assertEqual(config.parse_timezone_offset("3"), 3)
        self.assertEqual(config.parse_timezone_offset("+3"), 3)
        self.assertEqual(config.parse_timezone_offset("-5"), -5)
        self.assertEqual(config.parse_timezone_offset("5.5"), 5.5)

    def test_parse_timezone_offset_rejects_garbage(self):
        for bad in ("abc", "UTC+3", "15", "-13"):
            with self.assertRaises(ValueError, msg=bad):
                config.parse_timezone_offset(bad)

    def test_from_timestamp_uses_utc_plus_offset(self):
        cases = {3: datetime(2023, 11, 15, 1, 13, 20), -5: datetime(2023, 11, 14, 17, 13, 20),
                 0: datetime(2023, 11, 14, 22, 13, 20), 5.5: datetime(2023, 11, 15, 3, 43, 20)}
        for offset, expected in cases.items():
            with mock.patch.object(config, "TIMEZONE_OFFSET_HOURS", offset):
                self.assertEqual(config.from_timestamp(self.TIMESTAMP), expected, offset)

    def test_without_offset_system_time_is_kept(self):
        with mock.patch.object(config, "TIMEZONE_OFFSET_HOURS", None):
            self.assertEqual(config.from_timestamp(self.TIMESTAMP), datetime.fromtimestamp(self.TIMESTAMP))

    def test_now_follows_offset(self):
        with mock.patch.object(config, "TIMEZONE_OFFSET_HOURS", 3), mock.patch("config.time.time", return_value=self.TIMESTAMP):
            self.assertEqual(config.now(), datetime(2023, 11, 15, 1, 13, 20))

    def test_active_window_uses_offset_time(self):
        # 22:13 UTC is inside 08:00-23:00; the same moment is 01:13 in UTC+3, so mailing must wait until 08:00.
        active_from, active_to = time(8, 0), time(23, 0)
        for offset, expected_wait in ((0, 0), (3, (8 * 3600) - (1 * 3600 + 13 * 60 + 20))):
            with mock.patch.object(config, "TIMEZONE_OFFSET_HOURS", offset), mock.patch("config.time.time", return_value=self.TIMESTAMP):
                self.assertEqual(seconds_until_active_period(config.now(), active_from, active_to), expected_wait, offset)

    def test_log_formatter_uses_offset(self):
        record = logging.LogRecord("x", logging.INFO, __file__, 1, "hello", None, None)
        record.created, record.msecs = self.TIMESTAMP, 42
        with mock.patch.object(config, "TIMEZONE_OFFSET_HOURS", 3):
            line = AppTimeFormatter("%(asctime)s %(message)s").format(record)
        self.assertEqual(line, "2023-11-15 01:13:20,042 hello")

    def test_invalid_env_value_fails_fast_on_import(self):
        env = {**os.environ, "TIMEZONE_OFFSET": "abc"}
        result = subprocess.run([sys.executable, "-c", "import config"], cwd=Path(__file__).resolve().parent.parent,
                                env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("TIMEZONE_OFFSET", result.stderr)


if __name__ == "__main__":
    unittest.main()
