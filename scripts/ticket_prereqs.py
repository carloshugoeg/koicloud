#!/usr/bin/env python3
"""Next ready ticket + lint for stale CCR leftovers.

Usage:
  python3 scripts/ticket_prereqs.py next Jason
  python3 scripts/ticket_prereqs.py check
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TICKETS = ROOT / "docs" / "tickets"
LANDED = frozenset({"hecho", "cerrado"})
WS_FOR_NAME = (
    (("carlos", "hugo"), "w1"),
    (("jason",), "w2"),
    (("jous", "josh"), "w3"),
    (("diego",), "w4"),
)


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    meta: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta


def ticket_paths(ws: str | None = None) -> list[pathlib.Path]:
    roots = [TICKETS / ws] if ws else sorted(TICKETS.glob("w[0-9]"))
    files: list[pathlib.Path] = []
    for folder in roots:
        files.extend(sorted(p for p in folder.glob("W*.md") if p.name != "00-INDEX.md"))
    return files


def index_by_id() -> dict[str, tuple[pathlib.Path, dict[str, str]]]:
    found: dict[str, tuple[pathlib.Path, dict[str, str]]] = {}
    for path in ticket_paths():
        meta = parse_frontmatter(path.read_text(encoding="utf-8"))
        ticket_id = meta.get("id")
        if ticket_id:
            found[ticket_id] = (path, meta)
    return found


def depends_on_ids(meta: dict[str, str]) -> list[str]:
    raw = meta.get("depends_on", "").strip()
    if raw.lower() in {"", "none", "ninguna", "[]"}:
        return []
    return [part.strip().rstrip(",") for part in raw.split() if part.strip()]


def unmet_deps(
    meta: dict[str, str], by_id: dict[str, tuple[pathlib.Path, dict[str, str]]]
) -> list[tuple[str, str]]:
    missing: list[tuple[str, str]] = []
    for dep in depends_on_ids(meta):
        if dep not in by_id:
            missing.append((dep, "missing-file"))
            continue
        estado = by_id[dep][1].get("estado", "")
        if estado not in LANDED:
            missing.append((dep, estado or "unknown"))
    return missing


def workstream_for(name: str) -> str | None:
    lowered = name.lower()
    for prefixes, ws in WS_FOR_NAME:
        if any(lowered.startswith(prefix) for prefix in prefixes):
            return ws
    return None


def next_ready(name: str) -> int:
    ws = workstream_for(name)
    if ws is None:
        print(f"unknown-name {name}", file=sys.stderr)
        return 2
    by_id = index_by_id()
    waiting: list[str] = []
    for path in ticket_paths(ws):
        meta = parse_frontmatter(path.read_text(encoding="utf-8"))
        if meta.get("estado") != "abierto":
            continue
        gaps = unmet_deps(meta, by_id)
        if gaps:
            bits = ", ".join(f"{dep} ({why})" for dep, why in gaps)
            waiting.append(f"{meta.get('id', path.name)} depends on {bits}")
            continue
        rel = path.relative_to(ROOT).as_posix()
        print(rel)
        print(meta.get("id", ""))
        print(meta.get("rama", ""))
        print(meta.get("depends_on", ""))
        return 0
    if waiting:
        print("ESPERA")
        for line in waiting:
            print(line)
        return 0
    print("NONE")
    return 0


def check() -> int:
    errors: list[str] = []
    by_id = index_by_id()
    for path in ticket_paths():
        text = path.read_text(encoding="utf-8")
        meta = parse_frontmatter(text)
        rel = path.relative_to(ROOT).as_posix()
        for dep, why in unmet_deps(meta, by_id):
            if why == "missing-file":
                errors.append(f"{rel}: depends_on {dep} has no ticket file")
        for lineno, line in enumerate(text.splitlines(), 1):
            if "/olvide" in line or "/restablecer" in line:
                errors.append(
                    f"{rel}:{lineno}: forgot/reset routes are /forgot and /reset, not Spanish slugs"
                )
            if "verify?token=" in line and "No existe" not in line:
                errors.append(
                    f"{rel}:{lineno}: verify token is body JSON, not a query string"
                )
            if re.search(r"código `2`|exit `2`|código \*\*`2`\*\*", line) and (
                "no aplica" not in line.lower()
            ):
                errors.append(
                    f"{rel}:{lineno}: missing-session CLI exit is 1 (api-surface §5)"
                )
    if errors:
        print("ticket_prereqs FAIL")
        for item in errors:
            print(item)
        return 1
    print("ticket_prereqs OK")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "check":
        return check()
    if len(argv) >= 3 and argv[1] == "next":
        return next_ready(argv[2])
    print("Uso: python3 scripts/ticket_prereqs.py next <nombre>|check", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
