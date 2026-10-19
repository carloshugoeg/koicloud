#!/usr/bin/env python3
"""CI guards for agent mistakes that already showed up more than once.

    python3 scripts/agent_guards.py tree
    python3 scripts/agent_guards.py pr
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import ticket_prereqs  # noqa: E402  # scripts/ is not a package; path insert must come first

VALID_ESTADO = frozenset(
    {"abierto", "en-curso", "en-revision", "hecho", "bloqueado", "cerrado"}
)
ESTADO_SPELLING = {
    "en_curso": "en-curso",
    "en_revision": "en-revision",
}
PAGE_CAP = 250
HEADINGS = (
    "## Ticket",
    "## Qué cambia",
    "## Criterios de aceptación cubiertos",
    "## Cómo probé el caso feliz a mano",
    "## Decisiones tomadas",
    "## Dependencias nuevas",
    "## Checklist",
)
CHECK_HEADING = re.compile(r"^## Salida de `make check[^`]*`\s*$", re.M)
FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
PR_NUMBER = re.compile(r"(?:pull/|#)(\d+)")
TABLE_CALL = re.compile(r"\bTable\(")
SHIP_REVIEW = re.compile(r"(?i)^ship review:")
OUTPUT_SIGNAL = re.compile(
    r"(passed|failed|error|ruff|pytest|tsc|vitest|pnpm|ticket_prereqs|\bOK\b|collected|Ran \d+ test)",
    re.I,
)


@dataclass(frozen=True)
class Finding:
    code: str
    where: str
    fix: str

    def format(self) -> str:
        return f"::error::{self.where}: {self.fix}"


def ticket_files(root: Path) -> list[Path]:
    found: list[Path] = []
    tickets = root / "docs" / "tickets"
    for folder in sorted(tickets.glob("w[1-4]")):
        for path in sorted(folder.glob("*.md")):
            if path.name == "00-INDEX.md":
                continue
            found.append(path)
    return found


def pr_numbers(value: str) -> list[int]:
    return [int(number) for number in PR_NUMBER.findall(value)]


def blank_pr(value: str) -> bool:
    return value.strip().lower() in {"", "none", "ninguna"}


def landed_on_main(value: str) -> bool:
    return bool(re.search(r"\bmain\b", value)) and not pr_numbers(value)


def check_ticket(rel: str, meta: dict[str, str], states: dict[int, str]) -> list[Finding]:
    estado = meta.get("estado", "")
    pr = meta.get("pr", "")
    if estado in ESTADO_SPELLING:
        spell = ESTADO_SPELLING[estado]
        return [
            Finding(
                "ticket-estado",
                rel,
                f"estado {estado} is not in docs/tickets/README.md. Write {spell}.",
            )
        ]
    if estado not in VALID_ESTADO:
        allowed = ", ".join(sorted(VALID_ESTADO))
        return [
            Finding(
                "ticket-estado",
                rel,
                f"estado {estado or '(empty)'} is not valid. Use one of: {allowed}.",
            )
        ]

    numbers = pr_numbers(pr)
    findings: list[Finding] = []
    if estado == "hecho":
        if blank_pr(pr):
            findings.append(
                Finding(
                    "ticket-pr",
                    rel,
                    "estado is hecho and pr: is empty. Fill pr: with the merged pull request.",
                )
            )
        elif not numbers and not landed_on_main(pr):
            findings.append(
                Finding(
                    "ticket-pr",
                    rel,
                    "estado is hecho. pr: must cite the merged pull request, or main when there was no PR.",
                )
            )
        for number in numbers:
            state = states.get(number)
            if state != "merged":
                seen = state or "unknown"
                findings.append(
                    Finding(
                        "ticket-estado",
                        rel,
                        f"estado is hecho but #{number} is {seen}. "
                        "Set hecho only after the PR merges. Use en-revision while it is open.",
                    )
                )
    elif estado == "en-revision":
        if not numbers:
            findings.append(
                Finding(
                    "ticket-pr",
                    rel,
                    "estado is en-revision and pr: has no pull request. Fill pr: with the open PR.",
                )
            )
        for number in numbers:
            state = states.get(number)
            if state != "open":
                seen = state or "unknown"
                findings.append(
                    Finding(
                        "ticket-estado",
                        rel,
                        f"estado is en-revision but #{number} is {seen}. "
                        "Set hecho after it merges, or abierto if it closed without merging.",
                    )
                )
    elif estado == "en-curso" and numbers:
        findings.append(
            Finding(
                "ticket-estado",
                rel,
                "a pull request is already linked. Set estado to en-revision, not en-curso.",
            )
        )
    return findings


def numbers_to_resolve(root: Path) -> set[int]:
    needed: set[int] = set()
    for path in ticket_files(root):
        meta = ticket_prereqs.parse_frontmatter(path.read_text(encoding="utf-8"))
        estado = meta.get("estado", "")
        if estado in {"hecho", "en-revision", "en-curso"}:
            needed.update(pr_numbers(meta.get("pr", "")))
    return needed


def check_tickets(root: Path, states: dict[int, str]) -> list[Finding]:
    findings: list[Finding] = []
    for path in ticket_files(root):
        rel = path.relative_to(root).as_posix()
        meta = ticket_prereqs.parse_frontmatter(path.read_text(encoding="utf-8"))
        findings.extend(check_ticket(rel, meta, states))
    return findings


def page_files(root: Path) -> list[Path]:
    features = root / "apps" / "web" / "src" / "features"
    return sorted(features.rglob("*page*.tsx"))


def load_baseline(path: Path) -> dict[str, int]:
    if not path.is_file():
        return {}
    parsed: dict[str, int] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        rel, _, count = line.partition(" ")
        parsed[rel] = int(count)
    return parsed


def check_pages(root: Path, baseline: dict[str, int]) -> list[Finding]:
    findings: list[Finding] = []
    for path in page_files(root):
        rel = path.relative_to(root).as_posix()
        lines = len(path.read_text(encoding="utf-8").splitlines())
        allowed = baseline.get(rel, PAGE_CAP)
        if lines <= allowed:
            continue
        if rel in baseline:
            fix = (
                f"{rel} has {lines} lines and is frozen at {allowed}. "
                "Move markup into a component. Do not grow the page."
            )
        else:
            fix = (
                f"{rel} has {lines} lines. A page is at most {PAGE_CAP} lines. "
                "Move markup into a component."
            )
        findings.append(Finding("page-lines", rel, fix))
    return findings


def check_cli_tables(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    cli = root / "apps" / "cli"
    allowed = cli / "koicloud_cli" / "commands" / "__init__.py"
    for path in sorted(cli.rglob("*.py")):
        if path == allowed:
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if TABLE_CALL.search(line):
                rel = path.relative_to(root).as_posix()
                findings.append(
                    Finding(
                        "cli-table",
                        f"{rel}:{lineno}",
                        "Build the table with emit_table from koicloud_cli.commands. Do not call Table().",
                    )
                )
    return findings


def check_pr_body(body: str) -> list[Finding]:
    findings: list[Finding] = []
    for heading in HEADINGS:
        if heading not in body:
            findings.append(
                Finding(
                    "pr-body",
                    heading,
                    f"PR body is missing {heading}. Fill .github/PULL_REQUEST_TEMPLATE.md.",
                )
            )
    match = CHECK_HEADING.search(body)
    if match is None:
        findings.append(
            Finding(
                "pr-body",
                "make check",
                "PR body is missing ## Salida de `make check-<área>`. Paste the unedited command output.",
            )
        )
        return findings
    rest = body[match.end() :]
    next_heading = re.search(r"^## ", rest, re.M)
    section = rest if next_heading is None else rest[: next_heading.start()]
    fenced = "\n".join(FENCE.findall(section)).strip()
    content_lines = [line for line in fenced.splitlines() if line.strip()]
    if len(content_lines) < 3 or OUTPUT_SIGNAL.search(fenced) is None:
        findings.append(
            Finding(
                "pr-body",
                "make check",
                "The make check fence is empty or only a summary. Paste the unedited command output.",
            )
        )
    return findings


def opens_ship_review(body: str) -> bool:
    for line in body.splitlines():
        if line.strip():
            return SHIP_REVIEW.match(line.strip()) is not None
    return False


def check_ship_reviews(author: str, comments: list[tuple[str, str]]) -> list[Finding]:
    findings: list[Finding] = []
    for login, body in comments:
        if login == author and opens_ship_review(body):
            findings.append(
                Finding(
                    "ship-review",
                    login,
                    "The PR author posted a comment that starts with 'ship review:'. "
                    "Someone else writes that review.",
                )
            )
            break
    return findings


def check_self_label(author: str, labelers: list[str]) -> list[Finding]:
    if author not in labelers:
        return []
    return [
        Finding(
            "cross-workstream",
            author,
            "The PR author added the cross-workstream label. "
            "The owning workstream adds it after approving the foreign paths. "
            "Without that label, check_ownership.py rejects the paths.",
        )
    ]


def check_tree(root: Path, states: dict[int, str] | None = None) -> list[Finding]:
    if states is None:
        states = fetch_states(repo_slug(), numbers_to_resolve(root))
    baseline = load_baseline(root / "scripts" / "page-line-baseline.txt")
    return (
        check_tickets(root, states)
        + check_pages(root, baseline)
        + check_cli_tables(root)
    )


def repo_slug() -> str:
    configured = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if configured:
        return configured
    url = subprocess.check_output(["git", "remote", "get-url", "origin"], text=True)
    match = re.search(r"github\.com[:/]([^/]+/[^/.]+)", url)
    if match is None:
        raise SystemExit("::error::Cannot tell which GitHub repo this checkout is")
    return match.group(1)


def fetch_states(repo: str, numbers: set[int]) -> dict[int, str]:
    states: dict[int, str] = {}
    for number in sorted(numbers):
        raw = subprocess.check_output(
            [
                "gh",
                "pr",
                "view",
                str(number),
                "--repo",
                repo,
                "--json",
                "state",
            ],
            text=True,
        )
        states[number] = json.loads(raw)["state"].lower()
    return states


def fetch_pull_request(repo: str, number: int) -> tuple[str, str, list[tuple[str, str]], list[str]]:
    owner, name = repo.split("/", 1)
    query = """
    query($owner: String!, $name: String!, $n: Int!) {
      repository(owner: $owner, name: $name) {
        pullRequest(number: $n) {
          author { login }
          body
          comments(first: 100) { nodes { author { login } body } }
          reviews(first: 100) { nodes { author { login } body } }
          timelineItems(first: 100, itemTypes: [LABELED_EVENT]) {
            nodes {
              ... on LabeledEvent { label { name } actor { login } }
            }
          }
        }
      }
    }
    """
    raw = subprocess.check_output(
        [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={query}",
            "-f",
            f"owner={owner}",
            "-f",
            f"name={name}",
            "-F",
            f"n={number}",
        ],
        text=True,
    )
    pull = json.loads(raw)["data"]["repository"]["pullRequest"]
    author = (pull.get("author") or {}).get("login") or ""
    comments: list[tuple[str, str]] = []
    for node in pull["comments"]["nodes"] + pull["reviews"]["nodes"]:
        login = (node.get("author") or {}).get("login") or ""
        comments.append((login, node.get("body") or ""))
    labelers: list[str] = []
    for node in pull["timelineItems"]["nodes"]:
        label = (node.get("label") or {}).get("name")
        if label == "cross-workstream":
            labelers.append((node.get("actor") or {}).get("login") or "")
    return author, pull.get("body") or "", comments, labelers


def check_pull_request(repo: str, number: int) -> list[Finding]:
    author, body, comments, labelers = fetch_pull_request(repo, number)
    return check_pr_body(body) + check_ship_reviews(author, comments) + check_self_label(author, labelers)


def report(findings: list[Finding]) -> int:
    if not findings:
        print("guards OK")
        return 0
    print("guards FAIL")
    for finding in findings:
        print(finding.format())
    return 1


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "tree"
    if command == "tree":
        return report(check_tree(ROOT))
    if command == "pr":
        number = int(os.environ.get("PR_NUMBER") or argv[2])
        return report(check_tree(ROOT) + check_pull_request(repo_slug(), number))
    print("Uso: python3 scripts/agent_guards.py tree|pr", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
