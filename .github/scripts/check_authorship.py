#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

FORBIDDEN = re.compile(r'(co-authored-by:.*(cursor|antigravity|gemini|claude)|generated with)', re.I)
AUTHOR_LINE = re.compile(r'^- \*\*(W[1-4])\*\* \| .* \| `@[^`]+` \| .* \| `[^`]+` \|')
EMAIL_LINE = re.compile(r'`([^`]+@[^`]+)`')

# git log --format control bytes. Keep them as escapes so the source file stays valid Python
# if a checkout or patch ever mangles literal RS/US characters.
RECORD_SEP = "\x1e"
FIELD_SEP = "\x1f"


def load_allowed_emails(workstreams: Path) -> set[str]:
    emails: set[str] = set()
    for line in workstreams.read_text(encoding='utf-8').splitlines():
        if '@' in line and '`' in line:
            emails.update(match.group(1) for match in EMAIL_LINE.finditer(line))
    return emails


def git_log(base: str) -> list[dict[str, str]]:
    fmt = f"%H{FIELD_SEP}%an{FIELD_SEP}%ae{FIELD_SEP}%B{RECORD_SEP}"
    raw = subprocess.check_output(['git', 'log', f'{base}..HEAD', f'--format={fmt}'], text=True)
    commits: list[dict[str, str]] = []
    for chunk in raw.strip(RECORD_SEP).split(RECORD_SEP):
        if not chunk.strip():
            continue
        sha, name, email, body = chunk.split(FIELD_SEP, 3)
        commits.append({'sha': sha, 'name': name, 'email': email, 'body': body})
    return commits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True)
    ap.add_argument('--workstreams', default='docs/WORKSTREAMS.md')
    args = ap.parse_args()

    allowed = load_allowed_emails(Path(args.workstreams))
    if not allowed:
        print('::error::No allowed emails found in docs/WORKSTREAMS.md')
        return 1

    bad = False
    for commit in git_log(args.base):
        if commit['email'] not in allowed:
            print(f"::error::{commit['sha'][:7]} has unregistered author email {commit['email']}")
            bad = True
        if FORBIDDEN.search(commit['body']):
            print(f"::error::{commit['sha'][:7]} contains a forbidden tool trailer")
            bad = True
    if bad:
        return 1
    print('authorship OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
