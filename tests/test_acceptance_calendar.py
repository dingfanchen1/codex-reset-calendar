from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from icalendar import Calendar

from scripts import acceptance_calendar


FIRST_TIME = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)


class AcceptanceCalendarTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.state_path = root / "acceptance" / "data" / "current.json"
        self.ics_path = root / "acceptance" / "public" / "calendar" / "test.ics"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def event(self, source_id: str, reset_at: str) -> dict[str, object]:
        return acceptance_calendar._test_event(reset_at, source_id, FIRST_TIME)

    def components(self) -> list[object]:
        calendar = Calendar.from_ical(self.ics_path.read_bytes())
        return [item for item in calendar.walk() if item.name == "VEVENT"]

    def test_test_calendar_is_clearly_labeled_and_keeps_two_alarms(self) -> None:
        acceptance_calendar.generate(
            self.event("test-1", "2026-09-09T15:00:00Z"),
            self.state_path,
            self.ics_path,
            FIRST_TIME,
        )

        calendar = Calendar.from_ical(self.ics_path.read_bytes())
        self.assertEqual(str(calendar["X-WR-CALNAME"]), acceptance_calendar.TEST_LABEL)
        event = self.components()[0]
        self.assertEqual(str(event["SUMMARY"]), acceptance_calendar.TEST_LABEL)
        self.assertIn("非真实 Reset", str(event["DESCRIPTION"]))
        alarms = [item for item in event.subcomponents if item.name == "VALARM"]
        self.assertEqual(len(alarms), 2)

    def test_reschedule_reuses_uid_and_increments_sequence(self) -> None:
        acceptance_calendar.generate(
            self.event("test-1", "2026-09-09T15:00:00Z"),
            self.state_path,
            self.ics_path,
            FIRST_TIME,
        )
        first = self.components()[0]

        acceptance_calendar.generate(
            self.event("test-1", "2026-09-09T16:00:00Z"),
            self.state_path,
            self.ics_path,
            datetime(2026, 9, 9, 12, 30, tzinfo=timezone.utc),
        )
        second = self.components()[0]

        self.assertEqual(str(first["UID"]), str(second["UID"]))
        self.assertEqual(second.decoded("SEQUENCE"), 1)

    def test_new_source_replaces_then_clear_keeps_subscription_container(self) -> None:
        acceptance_calendar.generate(
            self.event("test-1", "2026-09-09T15:00:00Z"),
            self.state_path,
            self.ics_path,
            FIRST_TIME,
        )
        acceptance_calendar.generate(
            self.event("test-2", "2026-09-09T17:00:00Z"),
            self.state_path,
            self.ics_path,
            datetime(2026, 9, 9, 12, 30, tzinfo=timezone.utc),
        )
        self.assertIn("test-2", str(self.components()[0]["UID"]))

        acceptance_calendar.generate(
            None,
            self.state_path,
            self.ics_path,
            datetime(2026, 9, 9, 13, tzinfo=timezone.utc),
        )

        self.assertEqual(self.components(), [])
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertIsNone(state["currentEvent"])
        self.assertIn(b"BEGIN:VCALENDAR", self.ics_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
