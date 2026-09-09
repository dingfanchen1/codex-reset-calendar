from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from icalendar import Calendar

from scripts import sync_reset


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "reset_scheduled.json"
FIRST_GENERATED_AT = datetime(2026, 9, 8, 1, 45, tzinfo=timezone.utc)
SECOND_GENERATED_AT = datetime(2026, 9, 8, 2, 15, tzinfo=timezone.utc)


def payload(**changes: object) -> bytes:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    raw.update(changes)
    return json.dumps(raw, ensure_ascii=False).encode("utf-8")


class WorkspaceCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.state_path = root / "data" / "current.json"
        self.ics_path = root / "public" / "calendar" / "codex-reset.ics"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def sync(
        self,
        content: bytes | None = None,
        generated_at: datetime = FIRST_GENERATED_AT,
    ) -> dict[str, object]:
        return sync_reset.synchronize_bytes(
            content if content is not None else payload(),
            self.state_path,
            self.ics_path,
            generated_at,
        )

    def parsed_calendar(self) -> Calendar:
        return Calendar.from_ical(self.ics_path.read_bytes())

    def events(self) -> list[object]:
        return [
            component
            for component in self.parsed_calendar().walk()
            if component.name == "VEVENT"
        ]


class CalendarContractTests(WorkspaceCase):
    def test_normal_event_uses_utc_stable_uid_and_required_fields(self) -> None:
        result = self.sync()

        self.assertTrue(result["changed"])
        self.assertEqual(result["eventCount"], 1)
        calendar = self.parsed_calendar()
        self.assertEqual(str(calendar["X-WR-CALNAME"]), "Codex 重置日历")
        self.assertEqual(str(calendar["VERSION"]), "2.0")
        self.assertEqual(str(calendar["CALSCALE"]), "GREGORIAN")
        event = self.events()[0]
        self.assertEqual(str(event["SUMMARY"]), "⚡ Codex Reset")
        self.assertEqual(
            str(event["UID"]),
            "codex-reset-2097043464538264003@codex-reset-calendar",
        )
        self.assertEqual(event.decoded("DTSTART"), datetime(2026, 9, 8, 2, tzinfo=timezone.utc))
        self.assertEqual(event.decoded("DTEND"), datetime(2026, 9, 8, 2, 5, tzinfo=timezone.utc))
        self.assertEqual(event.decoded("DTSTAMP"), FIRST_GENERATED_AT)
        self.assertEqual(event.decoded("LAST-MODIFIED"), FIRST_GENERATED_AT)
        self.assertEqual(event.decoded("SEQUENCE"), 0)
        self.assertEqual(str(event["TRANSP"]), "TRANSPARENT")
        self.assertEqual(
            str(event["URL"]),
            "https://x.com/thsottiaux/status/2097043464538264003",
        )

    def test_calendar_is_utf8_crlf_folded_and_contains_chinese(self) -> None:
        self.sync(payload(confidence="medium"))
        content = self.ics_path.read_bytes()

        self.assertNotIn(b"\n", content.replace(b"\r\n", b""))
        for line in content.split(b"\r\n"):
            self.assertLessEqual(len(line), 75)
        decoded = content.decode("utf-8")
        self.assertIn("Codex Reset", decoded)
        description = str(self.events()[0]["DESCRIPTION"])
        self.assertIn("上游状态：scheduled", description)
        self.assertIn("可能为近似时间", description)
        self.assertIn("非 OpenAI 官方日历", description)

    def test_missing_confidence_is_unknown_and_not_promoted_to_high(self) -> None:
        raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        del raw["confidence"]
        self.sync(json.dumps(raw).encode("utf-8"))

        description = str(self.events()[0]["DESCRIPTION"])
        self.assertIn("置信度：unknown（可能为近似时间）", description)

    def test_two_display_alarms_have_exact_triggers(self) -> None:
        self.sync()
        event = self.events()[0]
        alarms = [component for component in event.subcomponents if component.name == "VALARM"]

        self.assertEqual(len(alarms), 2)
        self.assertEqual([str(alarm["ACTION"]) for alarm in alarms], ["DISPLAY", "DISPLAY"])
        raw = self.ics_path.read_text(encoding="utf-8")
        self.assertIn("TRIGGER:-PT15M", raw)
        self.assertIn("TRIGGER:PT0S", raw)

    def test_past_event_is_retained(self) -> None:
        self.sync(payload(resetAt="2020-01-01T00:00:00Z", state="completed"))
        event = self.events()[0]

        self.assertEqual(event.decoded("DTSTART"), datetime(2020, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(str(event["DESCRIPTION"]).splitlines()[1], "上游状态：completed")


class ChangeBehaviorTests(WorkspaceCase):
    def test_same_meaningful_input_keeps_every_byte_identical(self) -> None:
        first = self.sync()
        state_before = self.state_path.read_bytes()
        calendar_before = self.ics_path.read_bytes()

        second = self.sync(
            payload(
                lastCheckedAt="2026-09-09T09:09:09Z",
                sourceText="检查字段与帖子全文变化都应忽略",
                unrelatedField={"new": True},
            ),
            SECOND_GENERATED_AT,
        )

        self.assertTrue(first["changed"])
        self.assertFalse(second["changed"])
        self.assertFalse(second["semanticChange"])
        self.assertEqual(self.state_path.read_bytes(), state_before)
        self.assertEqual(self.ics_path.read_bytes(), calendar_before)

    def test_same_source_reschedule_increments_sequence_and_keeps_uid(self) -> None:
        self.sync()
        uid_before = str(self.events()[0]["UID"])

        self.sync(payload(resetAt="2026-09-08T03:00:00Z"), SECOND_GENERATED_AT)
        event = self.events()[0]

        self.assertEqual(str(event["UID"]), uid_before)
        self.assertEqual(event.decoded("SEQUENCE"), 1)
        self.assertEqual(event.decoded("LAST-MODIFIED"), SECOND_GENERATED_AT)

    def test_new_source_replaces_event_and_starts_sequence_zero(self) -> None:
        self.sync()
        self.sync(
            payload(
                sourceId="new-source-2",
                sourceUrl="https://x.com/thsottiaux/status/new-source-2",
            ),
            SECOND_GENERATED_AT,
        )

        events = self.events()
        self.assertEqual(len(events), 1)
        self.assertEqual(str(events[0]["UID"]), "codex-reset-new-source-2@codex-reset-calendar")
        self.assertEqual(events[0].decoded("SEQUENCE"), 0)

    def test_clear_keeps_container_and_last_version_then_reappearance_increments(self) -> None:
        self.sync()
        self.sync(payload(state="none", resetAt=None), SECOND_GENERATED_AT)

        self.assertEqual(self.events(), [])
        state_after_clear = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertIsNone(state_after_clear["currentEvent"])
        self.assertEqual(state_after_clear["lastEventVersion"]["sequence"], 0)
        self.assertIn(b"BEGIN:VCALENDAR", self.ics_path.read_bytes())

        self.sync(payload(), datetime(2026, 9, 8, 3, tzinfo=timezone.utc))
        self.assertEqual(self.events()[0].decoded("SEQUENCE"), 1)

    def test_initial_null_reset_creates_empty_calendar(self) -> None:
        self.sync(payload(state="announced", resetAt=None))

        self.assertEqual(self.events(), [])
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertIsNone(state["lastEventVersion"])


class FailureSafetyTests(WorkspaceCase):
    def assert_failure_preserves_outputs(self, bad_payload: bytes) -> None:
        self.sync()
        state_before = self.state_path.read_bytes()
        ics_before = self.ics_path.read_bytes()

        with self.assertRaises(sync_reset.ValidationError):
            self.sync(bad_payload, SECOND_GENERATED_AT)

        self.assertEqual(self.state_path.read_bytes(), state_before)
        self.assertEqual(self.ics_path.read_bytes(), ics_before)

    def test_unknown_version_preserves_previous_outputs(self) -> None:
        self.assert_failure_preserves_outputs(payload(schemaVersion=2))

    def test_unknown_state_preserves_previous_outputs(self) -> None:
        self.assert_failure_preserves_outputs(payload(state="mystery"))

    def test_timezone_less_datetime_preserves_previous_outputs(self) -> None:
        self.assert_failure_preserves_outputs(payload(resetAt="2026-09-08T02:00:00"))

    def test_invalid_json_preserves_previous_outputs(self) -> None:
        self.assert_failure_preserves_outputs(b"{broken-json")

    def test_invalid_source_author_preserves_previous_outputs(self) -> None:
        self.assert_failure_preserves_outputs(payload(sourceAuthor="someone-else"))

    def test_other_invalid_required_fields_preserve_previous_outputs(self) -> None:
        base = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        cases = []
        for missing in ("resetAt", "sourceId"):
            candidate = dict(base)
            del candidate[missing]
            cases.append(json.dumps(candidate).encode("utf-8"))
        cases.append(payload(sourceUrl="http://example.test/not-https"))

        for bad_payload in cases:
            with self.subTest(bad_payload=bad_payload):
                with tempfile.TemporaryDirectory() as temp_dir:
                    state_path = Path(temp_dir) / "current.json"
                    ics_path = Path(temp_dir) / "calendar.ics"
                    sync_reset.synchronize_bytes(payload(), state_path, ics_path, FIRST_GENERATED_AT)
                    state_before = state_path.read_bytes()
                    ics_before = ics_path.read_bytes()
                    with self.assertRaises(sync_reset.ValidationError):
                        sync_reset.synchronize_bytes(
                            bad_payload, state_path, ics_path, SECOND_GENERATED_AT
                        )
                    self.assertEqual(state_path.read_bytes(), state_before)
                    self.assertEqual(ics_path.read_bytes(), ics_before)

    def test_first_invalid_input_creates_no_output_files(self) -> None:
        with self.assertRaises(sync_reset.ValidationError):
            self.sync(payload(schemaVersion=2))
        self.assertFalse(self.state_path.exists())
        self.assertFalse(self.ics_path.exists())

    def test_corrupt_local_state_is_not_overwritten(self) -> None:
        self.state_path.parent.mkdir(parents=True)
        original = b'{"stateSchemaVersion":1,"currentEvent":{"broken":true}}\n'
        self.state_path.write_bytes(original)

        with self.assertRaises(sync_reset.ValidationError):
            self.sync()

        self.assertEqual(self.state_path.read_bytes(), original)
        self.assertFalse(self.ics_path.exists())

    def test_commit_failure_rolls_back_both_outputs(self) -> None:
        self.sync()
        state_before = self.state_path.read_bytes()
        ics_before = self.ics_path.read_bytes()
        real_replace = os.replace
        call_count = 0

        def fail_second_replace(source: object, destination: object) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise OSError("simulated second-file failure")
            real_replace(source, destination)

        with mock.patch("scripts.sync_reset.os.replace", side_effect=fail_second_replace):
            with self.assertRaises(OSError):
                self.sync(payload(resetAt="2026-09-08T03:00:00Z"), SECOND_GENERATED_AT)

        self.assertEqual(self.state_path.read_bytes(), state_before)
        self.assertEqual(self.ics_path.read_bytes(), ics_before)


class FetchTests(unittest.TestCase):
    class Response(io.BytesIO):
        status = 200

        def __enter__(self) -> "FetchTests.Response":
            return self

        def __exit__(self, *args: object) -> None:
            self.close()

    def test_network_error_retries_three_total_attempts(self) -> None:
        calls = 0
        sleeps: list[float] = []

        def opener(request: object, timeout: float) -> FetchTests.Response:
            nonlocal calls
            calls += 1
            self.assertEqual(timeout, 20)
            if calls < 3:
                raise urllib.error.URLError("temporary")
            return self.Response(b"{}")

        result = sync_reset.fetch_upstream(opener=opener, sleeper=sleeps.append)

        self.assertEqual(result, b"{}")
        self.assertEqual(calls, 3)
        self.assertEqual(sleeps, [0.25, 0.5])

    def test_non_retryable_http_error_stops_immediately(self) -> None:
        calls = 0

        def opener(request: object, timeout: float) -> FetchTests.Response:
            nonlocal calls
            calls += 1
            raise urllib.error.HTTPError("https://example.test", 404, "missing", {}, None)

        with self.assertRaises(sync_reset.FetchError):
            sync_reset.fetch_upstream(opener=opener, sleeper=lambda _: None)
        self.assertEqual(calls, 1)

    def test_direct_429_response_retries(self) -> None:
        calls = 0

        class RateLimitedResponse(self.Response):
            status = 429

        def opener(request: object, timeout: float) -> FetchTests.Response:
            nonlocal calls
            calls += 1
            if calls == 1:
                return RateLimitedResponse(b"rate limited")
            return self.Response(b"ok")

        result = sync_reset.fetch_upstream(opener=opener, sleeper=lambda _: None)
        self.assertEqual(result, b"ok")
        self.assertEqual(calls, 2)


if __name__ == "__main__":
    unittest.main()
