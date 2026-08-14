from datetime import datetime, timezone
import unittest

from perpetuum_app import scheduler


class SchedulerTests(unittest.TestCase):
    def schedule(self, expression="*/5 0-5 * * *"):
        return {
            "version": 1,
            "timezone": "Asia/Shanghai",
            "enabled": True,
            "paused": False,
            "force_run": False,
            "cron": [expression],
        }

    def test_cron_matches_project_timezone(self):
        now = datetime(2026, 8, 5, 16, 10, tzinfo=timezone.utc)
        self.assertEqual(
            scheduler.matching_crons(self.schedule(), now),
            ["*/5 0-5 * * *"],
        )

    def test_cron_does_not_match_outside_range(self):
        now = datetime(2026, 8, 6, 2, 10, tzinfo=timezone.utc)
        self.assertEqual(scheduler.matching_crons(self.schedule(), now), [])

    def test_same_cron_minute_only_triggers_once(self):
        now = datetime(2026, 8, 5, 16, 10, tzinfo=timezone.utc)
        first = scheduler.project_trigger(self.schedule(), None, now)
        self.assertIsNotNone(first)
        second = scheduler.project_trigger(
            self.schedule(),
            first["cron_minute"],
            now,
        )
        self.assertIsNone(second)

    def test_force_run_ignores_cron_but_not_pause(self):
        schedule = self.schedule("0 12 * * *")
        schedule["force_run"] = True
        now = datetime(2026, 8, 5, 16, 10, tzinfo=timezone.utc)
        self.assertEqual(
            scheduler.project_trigger(schedule, None, now)["reason"],
            "manual",
        )
        schedule["paused"] = True
        self.assertIsNone(scheduler.project_trigger(schedule, None, now))

    def test_only_standard_five_field_cron_is_accepted(self):
        with self.assertRaisesRegex(ValueError, "标准五字段"):
            scheduler.validate_cron("0 0 0 * * *")

    def test_invalid_timezone_is_rejected(self):
        schedule = self.schedule()
        schedule["timezone"] = "Nowhere/Invalid"
        with self.assertRaisesRegex(ValueError, "无效时区"):
            scheduler.validate_project_schedule(schedule)


if __name__ == "__main__":
    unittest.main()
