#!/usr/bin/env python3
"""校验待发布目录，并比较或验证 GitHub Pages 上的 ICS。"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PUBLIC_ROOT = PROJECT_ROOT / "public"
DEFAULT_ICS_PATH = DEFAULT_PUBLIC_ROOT / "calendar" / "codex-reset.ics"
ALLOWED_PUBLIC_FILES = {Path("calendar/codex-reset.ics")}


class PagesReleaseError(Exception):
    """发布前检查或线上验证失败。"""


class RetryablePageError(PagesReleaseError):
    """线上请求暂时失败，可以有限重试。"""


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate_public_tree(root: Path = DEFAULT_PUBLIC_ROOT) -> dict[str, Any]:
    if not root.is_dir():
        raise PagesReleaseError(f"待发布目录不存在: {root}")

    links = sorted(
        str(path.relative_to(root)) for path in root.rglob("*") if path.is_symlink()
    )
    if links:
        raise PagesReleaseError(f"待发布目录不得包含符号链接: {', '.join(links)}")

    files = {
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    if files != ALLOWED_PUBLIC_FILES:
        missing = sorted(str(path) for path in ALLOWED_PUBLIC_FILES - files)
        unexpected = sorted(str(path) for path in files - ALLOWED_PUBLIC_FILES)
        details = []
        if missing:
            details.append(f"缺少: {', '.join(missing)}")
        if unexpected:
            details.append(f"不允许公开: {', '.join(unexpected)}")
        raise PagesReleaseError("；".join(details))

    calendar_path = root / "calendar" / "codex-reset.ics"
    content = calendar_path.read_bytes()
    if not content:
        raise PagesReleaseError("生产 ICS 不能为空文件")
    return {
        "files": ["calendar/codex-reset.ics"],
        "calendarSha256": sha256(content),
    }


def _fetch_once(
    url: str,
    timeout: float,
    opener: Callable[..., Any],
) -> bytes | None:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "codex-reset-calendar/0.1A",
            "Cache-Control": "no-cache",
        },
    )
    try:
        with opener(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if status == 404:
                return None
            if status == 429 or 500 <= status <= 599:
                raise RetryablePageError(f"线上返回 HTTP {status}")
            if status != 200:
                raise PagesReleaseError(f"线上返回 HTTP {status}，不重试")
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        if exc.code == 429 or 500 <= exc.code <= 599:
            raise RetryablePageError(f"线上返回 HTTP {exc.code}") from exc
        raise PagesReleaseError(f"线上返回 HTTP {exc.code}，不重试") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RetryablePageError(type(exc).__name__) from exc


def check_page(
    local_path: Path,
    url: str,
    *,
    require_match: bool = False,
    attempts: int = 3,
    timeout: float = 20,
    retry_delay: float = 0.25,
    opener: Callable[..., Any] = urllib.request.urlopen,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if attempts < 1:
        raise PagesReleaseError("attempts 必须至少为 1")
    try:
        local = local_path.read_bytes()
    except OSError as exc:
        raise PagesReleaseError(f"无法读取本地 ICS: {local_path}") from exc

    last_status = "unknown"
    last_remote: bytes | None = None
    last_error: RetryablePageError | None = None
    for attempt in range(1, attempts + 1):
        try:
            remote = _fetch_once(url, timeout, opener)
            last_remote = remote
            last_error = None
            if remote is None:
                status = "missing"
            elif remote == local:
                status = "match"
            else:
                status = "mismatch"
            last_status = status
            if status == "match" or not require_match:
                return {
                    "status": status,
                    "shouldDeploy": status != "match",
                    "attempts": attempt,
                    "localSha256": sha256(local),
                    "remoteSha256": sha256(remote) if remote is not None else None,
                }
        except RetryablePageError as exc:
            last_error = exc

        if attempt < attempts:
            sleeper(retry_delay)

    if last_error is not None:
        raise PagesReleaseError(
            f"线上请求在 {attempts} 次尝试后仍失败: {last_error}"
        ) from last_error
    remote_sha = sha256(last_remote) if last_remote is not None else "无"
    raise PagesReleaseError(
        f"部署后线上仍为 {last_status}；本地 SHA-256={sha256(local)}，"
        f"线上 SHA-256={remote_sha}"
    )


def _write_github_output(path: Path, result: dict[str, Any]) -> None:
    lines = [
        f"status={result['status']}",
        f"should_deploy={'true' if result['shouldDeploy'] else 'false'}",
        f"local_sha256={result['localSha256']}",
        f"remote_sha256={result['remoteSha256'] or ''}",
    ]
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    public = subparsers.add_parser("validate-public")
    public.add_argument("--root", type=Path, default=DEFAULT_PUBLIC_ROOT)

    for command in ("compare", "verify"):
        check = subparsers.add_parser(command)
        check.add_argument("--local", type=Path, default=DEFAULT_ICS_PATH)
        check.add_argument("--url", required=True)
        check.add_argument("--attempts", type=int, default=3)
        check.add_argument("--timeout", type=float, default=20)
        check.add_argument("--retry-delay", type=float, default=0.25)
        check.add_argument("--github-output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "validate-public":
            result = validate_public_tree(args.root)
        else:
            result = check_page(
                args.local,
                args.url,
                require_match=args.command == "verify",
                attempts=args.attempts,
                timeout=args.timeout,
                retry_delay=args.retry_delay,
            )
            if args.github_output:
                _write_github_output(args.github_output, result)
    except (OSError, PagesReleaseError) as exc:
        print(
            f"pages_check_failed category={type(exc).__name__} message={exc}",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
