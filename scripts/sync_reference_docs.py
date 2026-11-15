#!/usr/bin/env python3
"""Refresh the skill's authoritative G2O API and CEF JSON references."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


SKILL_DIR = Path(__file__).resolve().parents[1]
REFERENCE_DIR = SKILL_DIR / "references"
API_DIR = REFERENCE_DIR / "g2o-api"
CEF_DIR = REFERENCE_DIR / "cef"

VERSIONS_URL = "https://gothic-online.gitlab.io/platform/docs/versions.json"
API_URL = "https://gothic-online.gitlab.io/platform/docs/{version}/api.json"
CEF_INDEX_URL = "https://gothic-online.gitlab.io/modules/cef/search/search_index.json"
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def fetch_json(url: str) -> tuple[bytes, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "gothic-2-online-scripter/1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read()
    return payload, json.loads(payload.decode("utf-8-sig"))


def version_strings(node: Any) -> Iterator[str]:
    if isinstance(node, str) and VERSION_PATTERN.fullmatch(node):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from version_strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from version_strings(value)


def write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def source_entry(url: str, payload: bytes) -> dict[str, Any]:
    return {
        "url": url,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="append", dest="versions", help="sync only this version")
    args = parser.parse_args()

    versions_payload, versions_data = fetch_json(VERSIONS_URL)
    documented_versions = list(dict.fromkeys(version_strings(versions_data)))
    if not documented_versions:
        raise SystemExit("The versions document did not contain any semantic versions.")

    requested = args.versions or documented_versions
    unknown = [version for version in requested if version not in documented_versions]
    if unknown:
        raise SystemExit(f"Versions absent from authoritative index: {', '.join(unknown)}")

    write_bytes(API_DIR / "versions.json", versions_payload)
    sources: dict[str, Any] = {
        "refreshed_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": {
            "versions.json": source_entry(VERSIONS_URL, versions_payload),
        },
    }

    for version in requested:
        url = API_URL.format(version=version)
        payload, _ = fetch_json(url)
        filename = f"{version}.json"
        write_bytes(API_DIR / filename, payload)
        sources["files"][filename] = source_entry(url, payload)
        print(f"synced G2O {version}")

    cef_payload, _ = fetch_json(CEF_INDEX_URL)
    write_bytes(CEF_DIR / "search_index.json", cef_payload)
    sources["files"]["../cef/search_index.json"] = source_entry(CEF_INDEX_URL, cef_payload)

    manifest = json.dumps(sources, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    write_bytes(API_DIR / "sources.json", manifest)
    print("synced CEF search index")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
