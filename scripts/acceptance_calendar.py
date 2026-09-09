#!/usr/bin/env python3
"""生成与生产路径隔离、并明确标注的 iPhone 验收测试日历。"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

if __package__:
    from . import sync_reset
else:
    import sync_reset


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = PROJECT_ROOT / "acceptance" / "data" / "current.json"
DEFAULT_ICS_PATH = (
    PROJECT_ROOT / "acceptance" / "public" / "calendar" / "codex-reset-test.ics"
)
TEST_LABEL = "验收测试，非真实 Reset"
TEST_DESCRIPTION = "\n".join(
    [
        "验收测试，非真实 Reset。",
        "仅用于验证订阅日历的改期、替换、清空与双提醒。",
        "请勿将此事件视为 OpenAI 官方或生产 Reset 公告。",
    ]
)


def _test_event(reset_at: str, source_id: str, now: datetime) -> dict[str, Any]:
    starts_at = sync_reset.parse_datetime(reset_at, "resetAt")
    if starts_at < now + timedelta(hours=2):
        raise sync_reset.ValidationError("验收事件必须至少安排在当前时间两小时后")
    if not source_id or source_id.strip() != source_id or any(
        char in source_id for char in "\r\n"
    ):
        raise sync_reset.ValidationError("sourceId 必须是无首尾空白的非空字符串")
    return {
        "state": "scheduled",
        "resetAt": sync_reset.format_utc(starts_at),
        "sourceId": source_id,
        "sourceUrl": "https://github.com/",
        "sourceAuthor": sync_reset.EXPECTED_SOURCE_AUTHOR,
        "confidence": "high",
    }


def generate(
    current_event: dict[str, Any] | None,
    state_path: Path,
    ics_path: Path,
    generated_at: datetime,
) -> dict[str, Any]:
    previous = sync_reset.load_state(state_path)
    next_state, semantic_change = sync_reset.build_next_state(
        previous, current_event, generated_at
    )
    changed_paths = sync_reset.commit_outputs(
        [
            (state_path, sync_reset.serialize_state(next_state)),
            (
                ics_path,
                sync_reset.build_calendar(
                    next_state,
                    calendar_name=TEST_LABEL,
                    event_summary=TEST_LABEL,
                    description_override=TEST_DESCRIPTION,
                ),
            ),
        ]
    )
    return {
        "changed": bool(changed_paths),
        "semanticChange": semantic_change,
        "changedPaths": [str(path) for path in changed_paths],
        "eventCount": 1 if current_event else 0,
        "sourceId": current_event["sourceId"] if current_event else None,
        "resetAt": current_event["resetAt"] if current_event else None,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_ICS_PATH)
    subparsers = parser.add_subparsers(dest="command", required=True)

    event = subparsers.add_parser("event")
    event.add_argument("--reset-at", required=True)
    event.add_argument("--source-id", required=True)
    subparsers.add_parser("clear")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    generated_at = sync_reset.utc_now()
    try:
        current_event = (
            _test_event(args.reset_at, args.source_id, generated_at)
            if args.command == "event"
            else None
        )
        result = generate(
            current_event,
            args.state_file,
            args.output,
            generated_at,
        )
    except (OSError, sync_reset.SyncError) as exc:
        print(
            f"acceptance_calendar_failed category={type(exc).__name__} message={exc}",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
