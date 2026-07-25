import tempfile
import unittest
from datetime import datetime, time
from pathlib import Path

import config
from postman import is_within_active_period, parse_active_time, seconds_until_active_period


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


if __name__ == "__main__":
    unittest.main()
