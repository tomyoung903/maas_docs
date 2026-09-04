#!/usr/bin/env python3
"""Build the per-document Git metadata used by the MaaS Docs catalog."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "docs" / "catalog-metadata.json"


def git(*args: str) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), *args],
        stderr=subprocess.PIPE,
    )


def head_html_blobs() -> dict[str, str]:
    entries: list[tuple[str, str]] = []
    output = git("ls-tree", "-r", "-z", "HEAD", "--", "docs")
    for raw_entry in output.split(b"\0"):
        if not raw_entry:
            continue
        metadata, raw_path = raw_entry.split(b"\t", 1)
        _mode, object_type, object_sha = metadata.decode().split()
        path = raw_path.decode()
        if (
            object_type == "blob"
            and path.endswith(".html")
            and path != "docs/index.html"
        ):
            entries.append((path.removeprefix("docs/"), object_sha))
    return dict(sorted(entries))


def indexed_html_blobs() -> dict[str, str]:
    entries: list[tuple[str, str]] = []
    output = git("ls-files", "--stage", "-z", "--", "docs")
    for raw_entry in output.split(b"\0"):
        if not raw_entry:
            continue
        metadata, raw_path = raw_entry.split(b"\t", 1)
        _mode, object_sha, stage = metadata.decode().split()
        path = raw_path.decode()
        if stage == "0" and path.endswith(".html") and path != "docs/index.html":
            entries.append((path.removeprefix("docs/"), object_sha))
    return dict(sorted(entries))


def last_changed_at(path: str) -> str:
    value = git(
        "log",
        "-1",
        "--format=%cI",
        "HEAD",
        "--",
        f"docs/{path}",
    ).decode().strip()
    if not value:
        raise RuntimeError(f"No commit timestamp found for docs/{path}")
    return value


def render_metadata() -> str:
    head_blobs = head_html_blobs()
    indexed_blobs = indexed_html_blobs()
    existing_documents: dict[str, object] = {}
    if OUTPUT_PATH.exists():
        try:
            existing_documents = json.loads(OUTPUT_PATH.read_text()).get("documents", {})
        except (json.JSONDecodeError, AttributeError):
            pass

    changed_now = datetime.now().astimezone().isoformat(timespec="seconds")
    documents = {}
    for path, sha in indexed_blobs.items():
        existing = existing_documents.get(path)
        if (
            isinstance(existing, dict)
            and existing.get("sha") == sha
            and isinstance(existing.get("changedAt"), str)
        ):
            changed_at = existing["changedAt"]
        elif head_blobs.get(path) == sha:
            changed_at = last_changed_at(path)
        else:
            changed_at = changed_now
        documents[path] = {"sha": sha, "changedAt": changed_at}

    payload = {"schemaVersion": 1, "documents": documents}
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build docs/catalog-metadata.json from the Git index and history."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the metadata does not match the current Git index",
    )
    args = parser.parse_args()

    rendered = render_metadata()
    if args.check:
        if not OUTPUT_PATH.exists() or OUTPUT_PATH.read_text() != rendered:
            print(f"{OUTPUT_PATH.relative_to(REPO_ROOT)} is out of date")
            return 1
        print(f"{OUTPUT_PATH.relative_to(REPO_ROOT)} is up to date")
        return 0

    OUTPUT_PATH.write_text(rendered)
    print(f"Wrote {len(json.loads(rendered)['documents'])} entries to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
