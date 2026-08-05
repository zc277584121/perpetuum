from datetime import datetime
import unittest

from perpetuum_app import scheduler


class SchedulerTests(unittest.TestCase):
    def test_daily_window(self):
        self.assertTrue(
            scheduler.window_matches(
                "18:00-24:00",
                datetime(2026, 8, 5, 22, 0),
            )
        )
        self.assertFalse(
            scheduler.window_matches(
                "18:00-24:00",
                datetime(2026, 8, 5, 17, 59),
            )
        )

    def test_cross_midnight_window(self):
        self.assertTrue(
            scheduler.window_matches(
                "23:00-06:00",
                datetime(2026, 8, 6, 2, 0),
            )
        )
        self.assertFalse(
            scheduler.window_matches(
                "23:00-06:00",
                datetime(2026, 8, 6, 12, 0),
            )
        )

    def test_cross_midnight_uses_start_day(self):
        window = {"days": [2], "start": "23:00", "end": "06:00"}
        self.assertTrue(
            scheduler.window_matches(window, datetime(2026, 8, 6, 2, 0))
        )
        self.assertFalse(
            scheduler.window_matches(window, datetime(2026, 8, 7, 2, 0))
        )

    def test_force_run_ignores_window(self):
        entry = {
            "enabled": True,
            "paused": False,
            "force_run": True,
            "windows": ["18:00-19:00"],
        }
        self.assertTrue(
            scheduler.project_is_eligible(
                entry,
                datetime(2026, 8, 5, 10, 0),
            )
        )

    def test_paused_project_is_never_eligible(self):
        entry = {
            "enabled": True,
            "paused": True,
            "force_run": True,
            "windows": ["00:00-24:00"],
        }
        self.assertFalse(
            scheduler.project_is_eligible(
                entry,
                datetime(2026, 8, 5, 10, 0),
            )
        )


if __name__ == "__main__":
    unittest.main()
