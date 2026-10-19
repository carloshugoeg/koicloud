#!/usr/bin/env python3
"""CI guards for agent mistakes that already showed up more than once.

    python3 scripts/agent_guards.py tree
    python3 scripts/agent_guards.py pr
    python3 scripts/agent_guards.py comment

Ship review LGTM. The guard does not look at the commenter's login. A comment
whose first non-empty line is "ship review: LGTM" counts only when its
timestamp is at or after the head clock. An older LGTM does not count and
does not fail the job. With no LGTM on the current head, the guard passes.

A counted LGTM is void when either of these is true:

- Its timestamp is less than 10 minutes after the head clock.
- An earlier comment whose first line is "ship review: changes needed" lists
  numbered findings outside code fences, and this LGTM does not mention that
  review or does not mark every finding. A mention is the review's commit sha
  or the words "changes needed". A mark is one "resolved" or "addressed" word
  per numbered finding.

The guard fails when every counted LGTM is void. The cross-workstream label
is not checked here. Path ownership stays in check_ownership.py.

The head clock is the earliest created_at among GitHub Actions runs for that
sha whose event is pull_request, plus push runs whose head_branch is the
pull request branch. A push of the same sha on another branch does not start
the clock. If no such run exists, the guard fails closed.

A pull_request run only sees comments that already exist. A later comment
whose first non-empty line starts with "ship review:" runs
`python3 scripts/agent_guards.py comment` from
.github/workflows/guards-comment.yml. That waits until the pull_request ci
run for the sha is completed, then reruns the guards job. It posts its own
check run only when that ci run has completed and no guards job exists.
A failed rerun does not post a second check. GitHub reads issue_comment
workflows from the default branch.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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
LGTM_OPEN = re.compile(r"(?i)^ship review:\s*lgtm\b")
CHANGES_OPEN = re.compile(r"(?i)^ship review:\s*changes needed\b")
FINDING_LINE = re.compile(r"^\s*\d+\.\s+\S")
RESOLVED_WORD = re.compile(r"(?i)\b(?:resolved|addressed)\b")
SHA_TOKEN = re.compile(r"\b[0-9a-fA-F]{7,40}\b")
LGTM_MIN_DELAY = timedelta(minutes=10)
GUARDS_JOB_PENDING = frozenset({"queued", "in_progress", "waiting", "pending", "requested"})
RECHECK_WAIT_SECONDS = 300
RECHECK_POLL_SECONDS = 15
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
    skipped = {".venv", "site-packages", "__pycache__", ".git"}
    for path in sorted(cli.rglob("*.py")):
        if skipped.intersection(path.parts) or path == allowed:
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


@dataclass(frozen=True)
class ReviewNote:
    kind: str
    body: str
    created_at: datetime


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def first_line(body: str) -> str:
    for line in body.splitlines():
        if line.strip():
            return line.strip()
    return ""


def note_kind(body: str) -> str | None:
    line = first_line(body)
    if LGTM_OPEN.match(line):
        return "lgtm"
    if CHANGES_OPEN.match(line):
        return "changes"
    return None


def numbered_findings(body: str) -> int:
    count = 0
    inside_fence = False
    for line in body.splitlines():
        if line.strip().startswith("```"):
            inside_fence = not inside_fence
            continue
        if inside_fence:
            continue
        if FINDING_LINE.match(line):
            count += 1
    return count


def ship_review_comment(body: str) -> bool:
    return first_line(body).lower().startswith("ship review:")


def earliest_head_clock(runs: list[dict], branch: str | None = None) -> datetime | None:
    stamps: list[datetime] = []
    for run in runs:
        stamp = run.get("created_at")
        if not stamp:
            continue
        event = run.get("event")
        if event == "pull_request":
            stamps.append(parse_time(stamp))
        elif event == "push" and branch and run.get("head_branch") == branch:
            stamps.append(parse_time(stamp))
    if not stamps:
        return None
    return min(stamps)


def latest_completed_guards_job(jobs: list[dict]) -> int | None:
    found: list[tuple[datetime, int]] = []
    for job in jobs:
        if job.get("name") != "guards" or job.get("status") != "completed":
            continue
        stamp = job.get("completed_at")
        job_id = job.get("id")
        if not stamp or job_id is None:
            continue
        found.append((parse_time(stamp), int(job_id)))
    if not found:
        return None
    return max(found)[1]


def guards_job_pending(jobs: list[dict]) -> bool:
    return any(
        job.get("name") == "guards" and job.get("status") in GUARDS_JOB_PENDING
        for job in jobs
    )


def pull_request_ci_runs(runs: list[dict]) -> list[dict]:
    return [
        run
        for run in runs
        if run.get("event") == "pull_request" and run.get("name") == "ci"
    ]


def choose_recheck(jobs: list[dict], runs: list[dict] | None = None) -> tuple[str, int | None]:
    ci_runs = pull_request_ci_runs(runs or [])
    if not ci_runs or any(run.get("status") != "completed" for run in ci_runs):
        return "wait", None
    if guards_job_pending(jobs):
        return "wait", None
    job_id = latest_completed_guards_job(jobs)
    if job_id is not None:
        return "rerun", job_id
    if any(job.get("name") == "guards" for job in jobs):
        return "wait", None
    return "post", None


def mentions_review(lgtm_body: str, changes_body: str) -> bool:
    lowered = lgtm_body.lower()
    if "changes needed" in lowered:
        return True
    for sha in SHA_TOKEN.findall(changes_body):
        if sha.lower() in lowered:
            return True
    return False


def void_reason(note: ReviewNote, head_time: datetime, earlier: list[ReviewNote]) -> str | None:
    if note.created_at - head_time < LGTM_MIN_DELAY:
        return (
            "ship review: LGTM was posted less than 10 minutes after GitHub recorded the head. "
            "Wait 10 minutes after the earliest pull_request or push workflow run."
        )
    changes = [item for item in earlier if item.kind == "changes" and item.created_at < note.created_at]
    if not changes:
        return None
    latest = max(changes, key=lambda item: item.created_at)
    count = numbered_findings(latest.body)
    if count == 0:
        return None
    addressed = len(RESOLVED_WORD.findall(note.body))
    if not mentions_review(note.body, latest.body) or addressed < count:
        return (
            f"ship review: LGTM does not answer the earlier changes-needed review "
            f"({count} findings). Mention that review and write one resolved or "
            "addressed word per finding."
        )
    return None


def check_lgtm_notes(notes: list[ReviewNote], head_time: datetime) -> list[Finding]:
    on_head = [
        note for note in notes if note.kind == "lgtm" and note.created_at >= head_time
    ]
    if not on_head:
        return []
    reasons = [void_reason(note, head_time, notes) for note in on_head]
    if any(reason is None for reason in reasons):
        return []
    return [Finding("ship-review", "LGTM", reason) for reason in reasons if reason]


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


def fetch_pull_request(repo: str, number: int) -> tuple[str, list[ReviewNote], datetime]:
    owner, name = repo.split("/", 1)
    query = """
    query($owner: String!, $name: String!, $n: Int!) {
      repository(owner: $owner, name: $name) {
        pullRequest(number: $n) {
          body
          headRefOid
          headRefName
          comments(first: 100) { nodes { createdAt body } }
          reviews(first: 100) { nodes { createdAt submittedAt body } }
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
    notes: list[ReviewNote] = []
    for node in pull["comments"]["nodes"] + pull["reviews"]["nodes"]:
        kind = note_kind(node.get("body") or "")
        if kind is None:
            continue
        stamp = node.get("submittedAt") or node.get("createdAt")
        notes.append(ReviewNote(kind, node.get("body") or "", parse_time(stamp)))
    head_oid = pull["headRefOid"]
    return pull.get("body") or "", notes, fetch_head_clock(repo, head_oid, pull["headRefName"])


def fetch_workflow_runs(repo: str, sha: str) -> list[dict]:
    runs: list[dict] = []
    page = 1
    while page <= 20:
        raw = subprocess.check_output(
            [
                "gh",
                "api",
                f"repos/{repo}/actions/runs?head_sha={sha}&per_page=100&page={page}",
            ],
            text=True,
        )
        payload = json.loads(raw)
        batch = payload.get("workflow_runs") or []
        runs.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return runs


def fetch_head_clock(repo: str, sha: str, branch: str) -> datetime:
    clock = earliest_head_clock(fetch_workflow_runs(repo, sha), branch)
    if clock is None:
        raise SystemExit(
            "::error::No GitHub Actions pull_request run for the head, "
            "and no push run on the pull request branch. "
            "The guard clock is that run's created_at."
        )
    return clock


def pull_request_ci_jobs(repo: str, runs: list[dict]) -> list[dict]:
    jobs: list[dict] = []
    for run in runs:
        if run.get("event") != "pull_request" or run.get("name") != "ci" or run.get("id") is None:
            continue
        raw = subprocess.check_output(
            ["gh", "api", f"repos/{repo}/actions/runs/{run['id']}/jobs?per_page=100"],
            text=True,
        )
        jobs.extend(json.loads(raw).get("jobs") or [])
    return jobs


def fetch_head_identity(repo: str, number: int) -> tuple[str, str]:
    raw = subprocess.check_output(
        [
            "gh",
            "pr",
            "view",
            str(number),
            "--repo",
            repo,
            "--json",
            "headRefOid,headRepository,headRepositoryOwner",
        ],
        text=True,
    )
    payload = json.loads(raw)
    owner = payload["headRepositoryOwner"]["login"]
    name = payload["headRepository"]["name"]
    return payload["headRefOid"], f"{owner}/{name}"


def post_check_run(repo: str, sha: str, findings: list[Finding]) -> None:
    if findings:
        conclusion = "failure"
        title = "guards FAIL"
        summary = "\n".join(item.format() for item in findings)
    else:
        conclusion = "success"
        title = "guards OK"
        summary = "guards OK"
    subprocess.check_call(
        [
            "gh",
            "api",
            "--method",
            "POST",
            f"repos/{repo}/check-runs",
            "-f",
            "name=guards",
            "-f",
            f"head_sha={sha}",
            "-f",
            "status=completed",
            "-f",
            f"conclusion={conclusion}",
            "-f",
            f"output[title]={title}",
            "-f",
            f"output[summary]={summary}",
        ]
    )


def rerun_guards_job(repo: str, job_id: int) -> bool:
    result = subprocess.run(
        ["gh", "api", "--method", "POST", f"repos/{repo}/actions/jobs/{job_id}/rerun"],
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def recheck_comment(repo: str, number: int, body: str) -> int:
    if not ship_review_comment(body):
        print("guards comment skipped")
        return 0
    head_sha, head_repo = fetch_head_identity(repo, number)
    if head_repo != repo:
        print("guards comment skipped")
        return 0
    deadline = time.monotonic() + RECHECK_WAIT_SECONDS
    while True:
        runs = fetch_workflow_runs(repo, head_sha)
        jobs = pull_request_ci_jobs(repo, runs)
        action, job_id = choose_recheck(jobs, runs)
        if action == "wait" and time.monotonic() < deadline:
            time.sleep(RECHECK_POLL_SECONDS)
            continue
        if action == "wait":
            print("::error::The pull_request ci run did not finish in time. Not posting a second check.")
            return 1
        if action == "rerun" and job_id is not None:
            if rerun_guards_job(repo, job_id):
                print(f"guards rerun {job_id} {head_sha}")
                return 0
            print("::error::Could not rerun the guards job. Not posting a second check.")
            return 1
        if any(job.get("name") == "guards" for job in jobs):
            print("::error::A guards job already exists for this sha. Not posting a second check.")
            return 1
        findings = check_pull_request(repo, number)
        post_check_run(repo, head_sha, findings)
        print(f"guards check posted {head_sha}")
        return 0


def check_pull_request(repo: str, number: int) -> list[Finding]:
    body, notes, head_time = fetch_pull_request(repo, number)
    return check_pr_body(body) + check_lgtm_notes(notes, head_time)


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
    if command == "comment":
        number = os.environ.get("PR_NUMBER")
        if not number:
            print("PR_NUMBER is required", file=sys.stderr)
            return 2
        return recheck_comment(repo_slug(), int(number), os.environ.get("COMMENT_BODY", ""))
    print("Uso: python3 scripts/agent_guards.py tree|pr|comment", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
