#!/usr/bin/env python3
"""把 The Reset Company 的当前状态转换为稳定的订阅日历。"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from icalendar import Alarm, Calendar, Event
from icalendar.prop import vText


UPSTREAM_URL = (
    "https://raw.githubusercontent.com/yuanlang12/"
    "The-Reset-Company/main/public/data/reset.json"
)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = PROJECT_ROOT / "data" / "current.json"
DEFAULT_ICS_PATH = PROJECT_ROOT / "public" / "calendar" / "codex-reset.ics"
KNOWN_STATES = {
    "scheduled",
    "announced",
    "rolling-out",
    "completed",
    "estimated",
    "none",
}
EXPECTED_SOURCE_AUTHOR = "thsottiaux"
STATE_SCHEMA_VERSION = 1
CALENDAR_PRODID = "-//Codex Reset Calendar//v0.1A//ZH-CN"


class SyncError(Exception):
    """同步失败，但正式状态和日历文件应保持不变。"""


class ValidationError(SyncError):
    """上游数据或本地状态不符合约定。"""


class FetchError(SyncError):
    """上游数据获取失败。"""


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_datetime(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} 必须是非空 ISO 时间字符串")
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError(f"{field_name} 不是有效 ISO 时间") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationError(f"{field_name} 必须包含时区")
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def validate_https_url(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("sourceUrl 必须是非空 HTTPS URL")
    normalized = value.strip()
    parsed = urlparse(normalized)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValidationError("sourceUrl 必须是有效 HTTPS URL")
    if "\r" in normalized or "\n" in normalized:
        raise ValidationError("sourceUrl 含非法换行")
    return normalized


def normalize_payload(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        raise ValidationError("上游 JSON 顶层必须是对象")
    schema_version = raw.get("schemaVersion")
    if isinstance(schema_version, bool) or schema_version != 1:
        raise ValidationError(f"不支持的 schemaVersion: {schema_version!r}")

    state = raw.get("state")
    if state not in KNOWN_STATES:
        raise ValidationError(f"未知 state: {state!r}")
    if "resetAt" not in raw:
        raise ValidationError("缺少必需字段 resetAt")

    reset_at_raw = raw["resetAt"]
    reset_at = None
    if reset_at_raw is not None:
        reset_at = parse_datetime(reset_at_raw, "resetAt")

    source_author = raw.get("sourceAuthor")
    if source_author is not None and source_author != EXPECTED_SOURCE_AUTHOR:
        raise ValidationError(
            f"sourceAuthor 必须是上游 Tibo 账号 {EXPECTED_SOURCE_AUTHOR!r}"
        )

    if state == "none" or reset_at is None:
        return None

    source_id = raw.get("sourceId")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValidationError("有事件时 sourceId 必须是非空字符串")
    source_id = source_id.strip()
    if source_id != raw["sourceId"] or any(char in source_id for char in "\r\n"):
        raise ValidationError("sourceId 不得含首尾空白或换行")

    confidence = raw.get("confidence", "unknown")
    if confidence is None:
        confidence = "unknown"
    if not isinstance(confidence, str) or not confidence.strip():
        raise ValidationError("confidence 必须是非空字符串或缺省")

    return {
        "state": state,
        "resetAt": format_utc(reset_at),
        "sourceId": source_id,
        "sourceUrl": validate_https_url(raw.get("sourceUrl")),
        "sourceAuthor": source_author or EXPECTED_SOURCE_AUTHOR,
        "confidence": confidence.strip(),
    }


def load_json_bytes(payload: bytes) -> Any:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError("上游内容不是 UTF-8") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationError("上游内容不是有效 JSON") from exc


def _validate_saved_state(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("stateSchemaVersion") != STATE_SCHEMA_VERSION:
        raise ValidationError("本地 current.json 版本无效")
    if "currentEvent" not in raw or "lastEventVersion" not in raw:
        raise ValidationError("本地 current.json 缺少必需字段")
    current_event = raw["currentEvent"]
    if current_event is not None and not isinstance(current_event, dict):
        raise ValidationError("本地 currentEvent 无效")
    if current_event is not None:
        required_event = {
            "state",
            "resetAt",
            "sourceId",
            "sourceUrl",
            "sourceAuthor",
            "confidence",
        }
        if set(current_event) != required_event:
            raise ValidationError("本地 currentEvent 字段无效")
        if current_event["state"] not in KNOWN_STATES - {"none"}:
            raise ValidationError("本地 currentEvent 状态无效")
        parse_datetime(current_event["resetAt"], "resetAt")
        validate_https_url(current_event["sourceUrl"])
        if current_event["sourceAuthor"] != EXPECTED_SOURCE_AUTHOR:
            raise ValidationError("本地 currentEvent 来源无效")
        if not isinstance(current_event["sourceId"], str) or not current_event["sourceId"]:
            raise ValidationError("本地 currentEvent sourceId 无效")
        if not isinstance(current_event["confidence"], str) or not current_event["confidence"]:
            raise ValidationError("本地 currentEvent confidence 无效")
    version = raw["lastEventVersion"]
    if version is not None:
        required = {"sourceId", "uid", "sequence", "modifiedAt"}
        if not isinstance(version, dict) or not required.issubset(version):
            raise ValidationError("本地 lastEventVersion 无效")
        if not isinstance(version["sequence"], int) or version["sequence"] < 0:
            raise ValidationError("本地 sequence 无效")
        parse_datetime(version["modifiedAt"], "modifiedAt")
        if version["uid"] != event_uid(version["sourceId"]):
            raise ValidationError("本地 UID 与 sourceId 不一致")
        if current_event is not None and version["sourceId"] != current_event["sourceId"]:
            raise ValidationError("本地事件与版本元数据不一致")
    return raw


def load_state(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError("无法读取有效的本地 current.json") from exc
    return _validate_saved_state(raw)


def event_uid(source_id: str) -> str:
    return f"codex-reset-{source_id}@codex-reset-calendar"


def build_next_state(
    previous: dict[str, Any] | None,
    current_event: dict[str, Any] | None,
    generated_at: datetime,
) -> tuple[dict[str, Any], bool]:
    if previous is not None and previous["currentEvent"] == current_event:
        return previous, False

    previous_version = previous["lastEventVersion"] if previous else None
    next_version = previous_version
    if current_event is not None:
        source_id = current_event["sourceId"]
        if previous_version and previous_version["sourceId"] == source_id:
            sequence = previous_version["sequence"] + 1
        else:
            sequence = 0
        next_version = {
            "sourceId": source_id,
            "uid": event_uid(source_id),
            "sequence": sequence,
            "modifiedAt": format_utc(generated_at),
        }

    return {
        "stateSchemaVersion": STATE_SCHEMA_VERSION,
        "currentEvent": current_event,
        "lastEventVersion": next_version,
    }, True


def build_description(event: dict[str, Any]) -> str:
    confidence = event["confidence"]
    confidence_line = f"置信度：{confidence}"
    if event["state"] == "estimated" or confidence != "high":
        confidence_line += "（可能为近似时间）"
    return "\n".join(
        [
            "Codex 用量重置时间提醒。",
            f"上游状态：{event['state']}",
            confidence_line,
            f"来源：Tibo (@{event['sourceAuthor']})",
            "非 OpenAI 官方日历；时间来自公开上游，可能存在同步延迟。",
        ]
    )


def build_calendar(state: dict[str, Any]) -> bytes:
    calendar = Calendar()
    calendar.add("prodid", CALENDAR_PRODID)
    calendar.add("version", "2.0")
    calendar.add("calscale", "GREGORIAN")
    calendar.add("x-wr-calname", "Codex 重置日历")

    current_event = state["currentEvent"]
    version = state["lastEventVersion"]
    if current_event is not None:
        if version is None or version["sourceId"] != current_event["sourceId"]:
            raise ValidationError("本地事件与版本元数据不一致")
        starts_at = parse_datetime(current_event["resetAt"], "resetAt")
        modified_at = parse_datetime(version["modifiedAt"], "modifiedAt")

        item = Event()
        item.add("uid", version["uid"])
        item.add("summary", "⚡ Codex Reset")
        item.add("dtstart", starts_at)
        item.add("dtend", starts_at + timedelta(minutes=5))
        item.add("dtstamp", modified_at)
        item.add("last-modified", modified_at)
        item.add("sequence", version["sequence"])
        item.add("description", build_description(current_event))
        item.add("url", current_event["sourceUrl"])
        item.add("transp", "TRANSPARENT")

        for trigger, label in (
            ("-PT15M", "Codex Reset 将在 15 分钟后开始"),
            ("PT0S", "Codex Reset 现在开始"),
        ):
            alarm = Alarm()
            alarm.add("action", "DISPLAY")
            alarm.add("description", label)
            alarm["TRIGGER"] = vText(trigger)
            item.add_component(alarm)
        calendar.add_component(item)

    return calendar.to_ical()


def serialize_state(state: dict[str, Any]) -> bytes:
    return (
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _stage_file(path: Path, content: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return temp_path


def commit_outputs(outputs: list[tuple[Path, bytes]]) -> list[Path]:
    changed = [
        (path, content)
        for path, content in outputs
        if not path.exists() or path.read_bytes() != content
    ]
    if not changed:
        return []

    staged: list[tuple[Path, Path]] = []
    originals: dict[Path, bytes | None] = {}
    replaced: list[Path] = []
    try:
        for path, content in changed:
            originals[path] = path.read_bytes() if path.exists() else None
            staged.append((path, _stage_file(path, content)))
        for path, temp_path in staged:
            os.replace(temp_path, path)
            replaced.append(path)
    except Exception:
        for path in reversed(replaced):
            original = originals[path]
            if original is None:
                path.unlink(missing_ok=True)
            else:
                rollback = _stage_file(path, original)
                os.replace(rollback, path)
        raise
    finally:
        for _, temp_path in staged:
            temp_path.unlink(missing_ok=True)
    return [path for path, _ in changed]


def synchronize_bytes(
    payload: bytes,
    state_path: Path = DEFAULT_STATE_PATH,
    ics_path: Path = DEFAULT_ICS_PATH,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    previous = load_state(state_path)
    current_event = normalize_payload(load_json_bytes(payload))
    next_state, semantic_change = build_next_state(
        previous, current_event, generated_at or utc_now()
    )
    state_bytes = serialize_state(next_state)
    ics_bytes = build_calendar(next_state)
    changed_paths = commit_outputs([(state_path, state_bytes), (ics_path, ics_bytes)])
    return {
        "changed": bool(changed_paths),
        "semanticChange": semantic_change,
        "changedPaths": [str(path) for path in changed_paths],
        "state": current_event["state"] if current_event else "none",
        "eventCount": 1 if current_event else 0,
        "sourceId": current_event["sourceId"] if current_event else None,
        "resetAt": current_event["resetAt"] if current_event else None,
    }


def fetch_upstream(
    url: str = UPSTREAM_URL,
    attempts: int = 3,
    timeout: float = 20,
    opener: Callable[..., Any] = urllib.request.urlopen,
    sleeper: Callable[[float], None] = time.sleep,
) -> bytes:
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "codex-reset-calendar/0.1A"},
            )
            with opener(request, timeout=timeout) as response:
                status = getattr(response, "status", 200)
                if status != 200:
                    if status == 429 or 500 <= status <= 599:
                        raise urllib.error.HTTPError(
                            url, status, "retryable upstream response", {}, None
                        )
                    raise FetchError(f"上游返回 HTTP {status}")
                return response.read()
        except urllib.error.HTTPError as exc:
            retryable = exc.code == 429 or 500 <= exc.code <= 599
            if not retryable:
                raise FetchError(f"上游返回 HTTP {exc.code}，不重试") from exc
            last_error: Exception = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
        except FetchError:
            raise
        if attempt < attempts:
            sleeper(0.25 * (2 ** (attempt - 1)))
    raise FetchError(f"获取上游失败，已尝试 {attempts} 次: {type(last_error).__name__}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-file",
        type=Path,
        help="从本地 JSON 读取；缺省时访问唯一生产上游",
    )
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_ICS_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        payload = args.input_file.read_bytes() if args.input_file else fetch_upstream()
        result = synchronize_bytes(payload, args.state_file, args.output)
    except (OSError, SyncError) as exc:
        print(f"sync_failed category={type(exc).__name__} message={exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
