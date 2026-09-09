from __future__ import annotations

import unittest
from pathlib import Path


WORKFLOW_PATH = Path(__file__).parents[1] / ".github" / "workflows" / "sync-calendar.yml"


class WorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    def test_triggers_and_serialization_match_release_plan(self) -> None:
        for required in (
            'cron: "7,17,27,37,47,57 * * * *"',
            "workflow_dispatch:",
            "push:",
            "pull_request:",
            "branches: [main]",
            "cancel-in-progress: false",
        ):
            self.assertIn(required, self.workflow)

    def test_permissions_are_assigned_to_the_jobs_that_need_them(self) -> None:
        for required in (
            "contents: write",
            "pages: write",
            "id-token: write",
            "actions: read",
        ):
            self.assertIn(required, self.workflow)

    def test_production_sync_uses_fixed_source_and_explicit_commit_paths(self) -> None:
        self.assertIn("python scripts/sync_reset.py", self.workflow)
        self.assertNotIn("--input-file", self.workflow)
        self.assertIn("needs.test.outputs.source_sha", self.workflow)
        self.assertIn("git rev-parse origin/main", self.workflow)
        self.assertIn(
            "git add -- data/current.json public/calendar/codex-reset.ics",
            self.workflow,
        )
        self.assertNotIn("git add .", self.workflow)
        self.assertNotIn("git push --force", self.workflow)

    def test_pages_actions_are_immutable_and_public_root_is_explicit(self) -> None:
        for sha in (
            "3d3c42e5aac5ba805825da76410c181273ba90b1",
            "5fda3b95a4ea91299a34e894583c3862153e4b97",
            "fc324d3547104276b827a68afc52ff2a11cc49c9",
            "368f82528645a54fb793d4d04e342629a3f51346",
        ):
            self.assertIn(sha, self.workflow)
        self.assertIn("path: public", self.workflow)
        self.assertIn("validate-public --root public", self.workflow)

    def test_pull_requests_cannot_enter_production_jobs(self) -> None:
        self.assertGreaterEqual(
            self.workflow.count("if: github.event_name != 'pull_request'"), 4
        )


if __name__ == "__main__":
    unittest.main()
