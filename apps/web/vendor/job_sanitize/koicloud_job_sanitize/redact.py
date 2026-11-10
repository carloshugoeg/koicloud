from __future__ import annotations

import re

MAX_CHARS = 500

# Password may contain @, /, and spaces; take everything up to the final @host.
_URI_PASSWORD = re.compile(
    r"(://[^/\s:]+:)(.+)(@(?:\[[0-9a-fA-F:]+\]|[^@/\s]+)(?::\d+)?(?:/\S*)?)"
)
_PGPASSWORD = re.compile(r"(?i)\bPGPASSWORD\s*=\s*.+$")
_JSON_PASSWORD = re.compile(r'(?i)("password"\s*:\s*")([^"]*)(")')
_SECRET_ASSIGN = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|token)\b\s*[=:]\s*(?:\".*?\"|.+)$"
)
_DROP_LINE = re.compile(r"(?i)^\s*(DETAIL:|CONTEXT:|Key\s*\()")
_TAB_DATA = re.compile(r"^\d+\t")
_SQL_DATA = re.compile(r"(?i)^\s*(INSERT\b|COPY\b|UPDATE\b|DELETE\b)")


def _cap(text: str) -> str:
    return text if len(text) <= MAX_CHARS else text[:MAX_CHARS]


def _scrub_secrets(line: str) -> str:
    line = _URI_PASSWORD.sub(r"\1[redacted]\3", line)
    line = _PGPASSWORD.sub("PGPASSWORD=[redacted]", line)
    line = _JSON_PASSWORD.sub(r"\1[redacted]\3", line)
    line = _SECRET_ASSIGN.sub(lambda match: f"{match.group(1)}=[redacted]", line)
    return line


def redact(raw: str) -> str:
    kept: list[str] = []
    for line in raw.splitlines():
        if _DROP_LINE.match(line) or _TAB_DATA.match(line) or _SQL_DATA.match(line):
            continue
        kept.append(_scrub_secrets(line))
    return _cap("\n".join(kept))


def log_text(raw: str) -> str:
    kept: list[str] = []
    for line in raw.splitlines():
        if _DROP_LINE.match(line) or _TAB_DATA.match(line) or _SQL_DATA.match(line):
            continue
        lowered = line.lower()
        marker_at = -1
        for marker in ("pg_dump:", "psql:"):
            found = lowered.find(marker)
            if found != -1:
                marker_at = found
                break
        if marker_at == -1 or "error" not in lowered[marker_at:]:
            continue
        kept.append(_scrub_secrets(line[marker_at:]))
    return _cap("\n".join(kept))


def filter_pg_dump_output(raw: str) -> str:
    kept = [line for line in raw.splitlines() if line.startswith("pg_dump:")]
    if kept:
        return _cap("\n".join(kept))
    # No pg_dump: lines: keep only client ERROR lines, never COPY/DETAIL payload.
    return log_text(raw)
