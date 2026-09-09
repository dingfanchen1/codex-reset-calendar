from __future__ import annotations

import io
import tempfile
import unittest
import urllib.error
from pathlib import Path

from scripts import pages_release


class Response(io.BytesIO):
    def __init__(self, content: bytes, status: int = 200) -> None:
        super().__init__(content)
        self.status = status

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class PagesReleaseCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.local_path = root / "public" / "calendar" / "codex-reset.ics"
        self.local_path.parent.mkdir(parents=True)
        self.local_path.write_bytes(b"calendar-v1")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_public_tree_contains_only_production_calendar(self) -> None:
        result = pages_release.validate_public_tree(self.local_path.parents[1])

        self.assertEqual(result["files"], ["calendar/codex-reset.ics"])

    def test_public_tree_rejects_unexpected_file(self) -> None:
        secret = self.local_path.parents[1] / "debug.log"
        secret.write_text("must not publish", encoding="utf-8")

        with self.assertRaisesRegex(pages_release.PagesReleaseError, "debug.log"):
            pages_release.validate_public_tree(self.local_path.parents[1])

    def test_first_publish_404_requests_deployment(self) -> None:
        def opener(request: object, timeout: float) -> Response:
            raise urllib.error.HTTPError("https://example.test", 404, "missing", {}, None)

        result = pages_release.check_page(
            self.local_path, "https://example.test/calendar.ics", opener=opener
        )

        self.assertEqual(result["status"], "missing")
        self.assertTrue(result["shouldDeploy"])

    def test_unchanged_online_calendar_skips_deployment(self) -> None:
        result = pages_release.check_page(
            self.local_path,
            "https://example.test/calendar.ics",
            opener=lambda request, timeout: Response(b"calendar-v1"),
        )

        self.assertEqual(result["status"], "match")
        self.assertFalse(result["shouldDeploy"])

    def test_online_mismatch_retries_deployment_even_without_local_change(self) -> None:
        result = pages_release.check_page(
            self.local_path,
            "https://example.test/calendar.ics",
            opener=lambda request, timeout: Response(b"older-deployment"),
        )

        self.assertEqual(result["status"], "mismatch")
        self.assertTrue(result["shouldDeploy"])

    def test_transient_online_failure_retries_then_recovers(self) -> None:
        calls = 0
        sleeps: list[float] = []

        def opener(request: object, timeout: float) -> Response:
            nonlocal calls
            calls += 1
            if calls < 3:
                raise urllib.error.HTTPError(
                    "https://example.test", 503, "temporary", {}, None
                )
            return Response(b"calendar-v1")

        result = pages_release.check_page(
            self.local_path,
            "https://example.test/calendar.ics",
            opener=opener,
            sleeper=sleeps.append,
        )

        self.assertEqual(result["status"], "match")
        self.assertEqual(result["attempts"], 3)
        self.assertEqual(sleeps, [0.25, 0.25])

    def test_non_retryable_online_error_fails_immediately(self) -> None:
        calls = 0

        def opener(request: object, timeout: float) -> Response:
            nonlocal calls
            calls += 1
            raise urllib.error.HTTPError(
                "https://example.test", 403, "forbidden", {}, None
            )

        with self.assertRaisesRegex(pages_release.PagesReleaseError, "不重试"):
            pages_release.check_page(
                self.local_path,
                "https://example.test/calendar.ics",
                opener=opener,
                sleeper=lambda _: None,
            )
        self.assertEqual(calls, 1)

    def test_post_deploy_verification_waits_for_matching_content(self) -> None:
        responses = iter([b"older-deployment", b"calendar-v1"])
        sleeps: list[float] = []

        result = pages_release.check_page(
            self.local_path,
            "https://example.test/calendar.ics",
            require_match=True,
            attempts=2,
            opener=lambda request, timeout: Response(next(responses)),
            sleeper=sleeps.append,
        )

        self.assertEqual(result["status"], "match")
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(sleeps, [0.25])

    def test_post_deploy_verification_fails_if_content_stays_old(self) -> None:
        with self.assertRaisesRegex(pages_release.PagesReleaseError, "mismatch"):
            pages_release.check_page(
                self.local_path,
                "https://example.test/calendar.ics",
                require_match=True,
                attempts=2,
                opener=lambda request, timeout: Response(b"older-deployment"),
                sleeper=lambda _: None,
            )


if __name__ == "__main__":
    unittest.main()
