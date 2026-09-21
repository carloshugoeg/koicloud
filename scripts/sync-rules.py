#!/usr/bin/env python3
"""Genera .agents/rules/*.md (Antigravity) desde .cursor/rules/*.mdc (Cursor).

Los dos directorios contienen las mismas reglas de área; solo cambia el frontmatter.
Se edita la versión de Cursor y se corre `make sync-rules` (o este script) para
regenerar la de Antigravity. CI falla si el resultado no está commiteado.

`00-harness` NO se sincroniza: en Cursor es un puntero corto (Cursor lee AGENTS.md
completo por su cuenta) y en Antigravity es un resumen autosuficiente, porque el IDE
no garantiza la lectura de AGENTS.md y limita cada regla a 12 000 caracteres.

Uso: python3 scripts/sync-rules.py [dir_cursor] [dir_agents]
"""

from __future__ import annotations

import pathlib
import sys

SKIP = {"00-harness"}
LIMIT = 12_000  # límite de caracteres por regla en Antigravity


def parse(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        raise SystemExit("falta frontmatter YAML")
    _, front, body = text.split("---\n", 2)
    meta = {}
    for line in front.splitlines():
        if line.strip():
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta, body.lstrip("\n")


def convert(meta: dict[str, str], body: str) -> str:
    globs = meta.get("globs", "")
    always = meta.get("alwaysApply", "false") == "true"
    trigger = "glob" if globs else ("always_on" if always else "model_decision")
    lines = ["---", f"trigger: {trigger}"]
    if globs:
        lines.append(f"globs: {globs}")
    lines.append(f"description: {meta.get('description', '')}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body


def main() -> int:
    cursor_dir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".cursor/rules")
    agents_dir = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else ".agents/rules")
    agents_dir.mkdir(parents=True, exist_ok=True)

    failed = False
    for src in sorted(cursor_dir.glob("*.mdc")):
        if src.stem in SKIP:
            continue
        out = convert(*parse(src.read_text(encoding="utf-8")))
        if len(out) > LIMIT:
            print(f"ERROR {src.stem}: {len(out)} caracteres > {LIMIT}", file=sys.stderr)
            failed = True
            continue
        (agents_dir / f"{src.stem}.md").write_text(out, encoding="utf-8")
        print(f"ok {src.stem} ({len(out)} caracteres)")

    for hand in sorted(agents_dir.glob("*.md")):
        if hand.stem in SKIP and len(hand.read_text(encoding="utf-8")) > LIMIT:
            print(f"ERROR {hand.stem}: excede {LIMIT} caracteres", file=sys.stderr)
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
