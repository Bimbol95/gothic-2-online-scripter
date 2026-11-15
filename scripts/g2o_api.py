#!/usr/bin/env python3
"""Search the local, versioned Gothic 2 Online API snapshots."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator


SKILL_DIR = Path(__file__).resolve().parents[1]
API_DIR = SKILL_DIR / "references" / "g2o-api"


def api_files() -> list[Path]:
    return sorted(
        (path for path in API_DIR.glob("*.json") if path.stem not in {"versions", "sources"}),
        key=lambda path: tuple(int(part) for part in path.stem.split(".")),
        reverse=True,
    )


def load_api(version: str) -> Any:
    path = API_DIR / f"{version}.json"
    if not path.is_file():
        available = ", ".join(item.stem for item in api_files()) or "none"
        raise SystemExit(
            f"No local API snapshot for G2O {version}. Available: {available}. "
            "Refresh only when appropriate with scripts/sync_reference_docs.py."
        )
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def identity(record: dict[str, Any]) -> str | None:
    name = record.get("name")
    if isinstance(name, str):
        return name
    definition = record.get("definition")
    if isinstance(definition, dict) and isinstance(definition.get("name"), str):
        return definition["name"]
    return None


def record_side(record: dict[str, Any], inherited: str | None) -> str | None:
    side = record.get("side")
    if isinstance(side, str):
        return side
    definition = record.get("definition")
    if isinstance(definition, dict) and isinstance(definition.get("side"), str):
        return definition["side"]
    return inherited


def walk_records(
    node: Any,
    path: tuple[str, ...] = (),
    inherited_side: str | None = None,
    inherited_owner: str | None = None,
) -> Iterator[dict[str, Any]]:
    if isinstance(node, dict):
        side = record_side(node, inherited_side)
        name = identity(node)
        if name is not None:
            yield {
                "path": ".".join(path),
                "owner": inherited_owner,
                "name": name,
                "side": side,
                "record": node,
            }

        child_owner = name or inherited_owner

        for key, value in node.items():
            if key == "definition":
                continue
            yield from walk_records(value, path + (str(key),), side, child_owner)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk_records(value, path + (str(index),), inherited_side, inherited_owner)


def searchable_text(item: dict[str, Any]) -> str:
    return "\n".join(
        (
            item["name"],
            item["owner"] or "",
            item["path"],
            json.dumps(item["record"], ensure_ascii=False, sort_keys=True),
        )
    ).casefold()


def search_records(
    data: Any,
    query: str,
    exact: bool,
    side: str | None,
) -> Iterable[dict[str, Any]]:
    needle = query.casefold()
    for item in walk_records(data):
        if side and item["side"] != side:
            continue
        if exact:
            qualified_name = (
                f"{item['owner']}.{item['name']}" if item["owner"] else item["name"]
            )
            matched = item["name"].casefold() == needle or qualified_name.casefold() == needle
        else:
            matched = needle in searchable_text(item)
        if matched:
            yield item


def print_summary(item: dict[str, Any]) -> None:
    record = item["record"]
    declaration = record.get("declaration")
    if not isinstance(declaration, str):
        definition = record.get("definition")
        declaration = definition.get("declaration") if isinstance(definition, dict) else None

    qualified_name = f"{item['owner']}.{item['name']}" if item["owner"] else item["name"]
    fields = [qualified_name, f"path={item['path'] or '<root>'}"]
    if item["side"]:
        fields.append(f"side={item['side']}")
    if declaration:
        fields.append(f"declaration={declaration}")
    print(" | ".join(fields))


def command_available(_: argparse.Namespace) -> int:
    files = api_files()
    if not files:
        print("No local G2O API snapshots found.", file=sys.stderr)
        return 1
    for path in files:
        print(path.stem)
    return 0


def command_verify(_: argparse.Namespace) -> int:
    manifest_path = API_DIR / "sources.json"
    if not manifest_path.is_file():
        print("No sources manifest found.", file=sys.stderr)
        return 1

    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    failures: list[str] = []
    entries = manifest.get("files", {})
    for relative_name, metadata in entries.items():
        path = (API_DIR / relative_name).resolve()
        if not path.is_file():
            failures.append(f"missing: {relative_name}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        expected = metadata.get("sha256")
        if actual != expected:
            failures.append(f"hash mismatch: {relative_name}")

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print(f"Verified {len(entries)} authoritative reference files.")
    return 0


def command_search(args: argparse.Namespace) -> int:
    results = list(search_records(load_api(args.version), args.query, args.exact, args.side))
    if not results:
        print(f"No matches for {args.query!r} in G2O {args.version}.", file=sys.stderr)
        return 1

    shown = results[: args.limit]
    if args.json:
        print(json.dumps(shown, ensure_ascii=False, indent=2))
    else:
        for item in shown:
            print_summary(item)

    if len(results) > len(shown):
        print(f"Showing {len(shown)} of {len(results)} matches.", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    available = subparsers.add_parser("available", help="list locally available G2O versions")
    available.set_defaults(handler=command_available)

    verify = subparsers.add_parser("verify", help="verify downloaded reference hashes")
    verify.set_defaults(handler=command_verify)

    search = subparsers.add_parser("search", help="search one exact G2O version")
    search.add_argument("version", help="G2O version, for example 0.3.9")
    search.add_argument("query", help="symbol name or text to find")
    search.add_argument("--exact", action="store_true", help="match the symbol name exactly")
    search.add_argument("--side", choices=("client", "server", "shared"), help="filter by side")
    search.add_argument("--limit", type=int, default=20, help="maximum matches to print")
    search.add_argument("--json", action="store_true", help="print complete matching records as JSON")
    search.set_defaults(handler=command_search)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "limit", 1) < 1:
        parser.error("--limit must be at least 1")
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())

