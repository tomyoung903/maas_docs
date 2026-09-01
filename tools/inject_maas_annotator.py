#!/usr/bin/env python3

import argparse
import html
import os
import re
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ASSET = DOCS / "assets" / "maas-annotator.js"
MARKER = "data-maas-annotator"
TAG_RE = re.compile(
    r"[ \t]*<script\b[^>]*\bdata-maas-annotator\b[^>]*>\s*</script>[ \t]*(?:\r?\n)?",
    re.IGNORECASE,
)


def page_key(path: Path) -> str:
    relative = PurePosixPath(path.relative_to(DOCS).as_posix())
    if relative.name == "index.html":
        parent = relative.parent.as_posix()
        return "/" if parent == "." else f"/{parent}/"
    return f"/{relative.as_posix()}"


def script_tag(path: Path) -> str:
    relative_asset = os.path.relpath(ASSET, path.parent).replace(os.sep, "/")
    key = html.escape(page_key(path), quote=True)
    return f'  <script defer src="{relative_asset}" {MARKER} data-page-key="{key}"></script>\n'


def expected_text(path: Path, source: str) -> str:
    cleaned = TAG_RE.sub("", source)
    closing = cleaned.lower().rfind("</body>")
    if closing < 0:
        raise ValueError(f"missing </body>: {path}")
    prefix = cleaned[:closing]
    separator = "" if prefix.endswith(("\n", "\r")) else "\n"
    return prefix + separator + script_tag(path) + cleaned[closing:]


def iter_pages():
    return sorted(DOCS.rglob("*.html"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject the MaaS Docs annotator loader into every HTML page.")
    parser.add_argument("--check", action="store_true", help="Report pages that are not exactly injected and exit nonzero.")
    args = parser.parse_args()

    changed = []
    for path in iter_pages():
        source = path.read_text(encoding="utf-8")
        expected = expected_text(path, source)
        if source == expected:
            continue
        changed.append(path)
        if not args.check:
            path.write_text(expected, encoding="utf-8")

    action = "need injection" if args.check else "injected"
    for path in changed:
        print(f"{action}: {path.relative_to(ROOT)}")
    print(f"pages={len(iter_pages())} changed={len(changed)} mode={'check' if args.check else 'write'}")
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
