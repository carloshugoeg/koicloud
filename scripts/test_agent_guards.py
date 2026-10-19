"""Behavior of the agent-mistake guards. Fixtures are the shapes that already shipped."""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import agent_guards  # noqa: E402  # scripts/ is not a package; path insert must come first


class TicketStateTest(unittest.TestCase):
    def test_en_curso_spelling_from_w2_07_review(self) -> None:
        findings = agent_guards.check_ticket(
            "docs/tickets/w2/W2-07-consola-sql.md",
            {"estado": "en_curso", "pr": "https://github.com/carloshugoeg/koicloud/pull/81"},
            {81: "open"},
        )
        self.assertEqual(findings[0].code, "ticket-estado")
        self.assertIn("en-curso", findings[0].fix)

    def test_underscore_revision_is_rejected(self) -> None:
        findings = agent_guards.check_ticket(
            "docs/tickets/w3/W3-12-admin-ponds-bitacora.md",
            {"estado": "en_revision", "pr": "#82"},
            {82: "merged"},
        )
        self.assertIn("en-revision", findings[0].fix)

    def test_hecho_while_pr_81_was_open(self) -> None:
        findings = agent_guards.check_ticket(
            "docs/tickets/w2/W2-07-consola-sql.md",
            {"estado": "hecho", "pr": "#81"},
            {81: "open"},
        )
        self.assertTrue(any("hecho" in item.fix and "open" in item.fix for item in findings))

    def test_hecho_with_empty_pr_like_w3_03(self) -> None:
        findings = agent_guards.check_ticket(
            "docs/tickets/w3/W3-03-recuperar-password.md",
            {"estado": "hecho", "pr": ""},
            {},
        )
        self.assertEqual(findings[0].code, "ticket-pr")

    def test_en_revision_after_merge(self) -> None:
        findings = agent_guards.check_ticket(
            "docs/tickets/w4/W4-07-mcp-tools-lectura.md",
            {"estado": "en-revision", "pr": "#86"},
            {86: "merged"},
        )
        self.assertIn("hecho", findings[0].fix)

    def test_merged_hecho_and_main_without_pr_pass(self) -> None:
        self.assertEqual(
            agent_guards.check_ticket(
                "docs/tickets/w1/W1-14-guion-demo.md",
                {"estado": "hecho", "pr": "main (scripts/demo-vivo.sh)"},
                {},
            ),
            [],
        )
        self.assertEqual(
            agent_guards.check_ticket(
                "docs/tickets/w3/W3-06-planes.md",
                {"estado": "hecho", "pr": "#46"},
                {46: "merged"},
            ),
            [],
        )

    def test_abierto_may_cite_a_groundwork_pr(self) -> None:
        self.assertEqual(
            agent_guards.check_ticket(
                "docs/tickets/w1/W1-13-infra-deploy.md",
                {"estado": "abierto", "pr": "https://github.com/carloshugoeg/koicloud/pull/39"},
                {39: "merged"},
            ),
            [],
        )


class PageAndTableTest(unittest.TestCase):
    def test_new_page_over_250_fails_and_frozen_page_may_not_grow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "apps/web/src/features/admin/users-page.tsx"
            page.parent.mkdir(parents=True)
            page.write_text("\n".join(["line"] * 251), encoding="utf-8")
            findings = agent_guards.check_pages(root, {})
            self.assertIn("250", findings[0].fix)

            frozen = root / "apps/web/src/features/uso/uso-page.tsx"
            frozen.parent.mkdir(parents=True)
            frozen.write_text("\n".join(["line"] * 419), encoding="utf-8")
            self.assertEqual(agent_guards.check_pages(root, {"apps/web/src/features/uso/uso-page.tsx": 419}), findings)
            frozen.write_text("\n".join(["line"] * 420), encoding="utf-8")
            grown = agent_guards.check_pages(
                root, {"apps/web/src/features/uso/uso-page.tsx": 419}
            )
            self.assertTrue(any("uso-page" in item.where for item in grown))

    def test_hand_built_table_outside_emit_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared = root / "apps/cli/koicloud_cli/commands/__init__.py"
            shared.parent.mkdir(parents=True)
            shared.write_text("table = Table(title=title)\n", encoding="utf-8")
            command = root / "apps/cli/koicloud_cli/commands/sql.py"
            command.write_text("    table = Table(title='Resultado SQL')\n", encoding="utf-8")
            findings = agent_guards.check_cli_tables(root)
            self.assertEqual(len(findings), 1)
            self.assertIn("emit_table", findings[0].fix)
            self.assertIn("sql.py", findings[0].where)


class PullRequestTest(unittest.TestCase):
    def test_empty_make_check_fence_from_pr_83(self) -> None:
        body = "\n".join(
            [
                "## Ticket",
                "## Qué cambia",
                "## Criterios de aceptación cubiertos",
                "## Cómo probé el caso feliz a mano",
                "## Salida de `make check-cli`",
                "```",
                "```",
                "## Decisiones tomadas",
                "## Dependencias nuevas",
                "## Checklist",
            ]
        )
        findings = agent_guards.check_pr_body(body)
        self.assertTrue(any(item.where == "make check" for item in findings))

    def test_missing_template_heading_from_pr_86(self) -> None:
        findings = agent_guards.check_pr_body("## Why\n## What changed\n")
        self.assertTrue(any("## Qué cambia" in item.fix for item in findings))

    def test_real_output_passes(self) -> None:
        body = "\n".join(
            [
                "## Ticket",
                "## Qué cambia",
                "## Criterios de aceptación cubiertos",
                "## Cómo probé el caso feliz a mano",
                "## Salida de `make check-cli`",
                "```",
                "ruff check .",
                "All checks passed",
                "12 passed in 0.4s",
                "```",
                "## Decisiones tomadas",
                "## Dependencias nuevas",
                "## Checklist",
            ]
        )
        self.assertEqual(agent_guards.check_pr_body(body), [])

    def test_rushed_lgtm_is_void(self) -> None:
        head = datetime(2026, 10, 19, 18, 0, tzinfo=timezone.utc)
        notes = [
            agent_guards.ReviewNote(
                "lgtm",
                "ship review: LGTM\n\nHead abcdef1",
                head + timedelta(minutes=9),
            )
        ]
        findings = agent_guards.check_lgtm_notes(notes, head)
        self.assertTrue(any("10 minutes" in item.fix for item in findings))

    def test_stale_head_lgtm_is_void(self) -> None:
        head = datetime(2026, 10, 19, 18, 0, tzinfo=timezone.utc)
        notes = [
            agent_guards.ReviewNote(
                "lgtm",
                "ship review: LGTM\n\nHead abcdef1",
                head - timedelta(minutes=1),
            )
        ]
        findings = agent_guards.check_lgtm_notes(notes, head)
        self.assertTrue(any("older than the head" in item.fix for item in findings))

    def test_lgtm_that_ignores_findings_is_void(self) -> None:
        head = datetime(2026, 10, 19, 18, 0, tzinfo=timezone.utc)
        notes = [
            agent_guards.ReviewNote(
                "changes",
                "ship review: changes needed\n\nHead: abcdef1\n\n1. Fix the guard.\n2. Add the ticket.\n",
                head + timedelta(minutes=12),
            ),
            agent_guards.ReviewNote(
                "lgtm",
                "ship review: LGTM\n\nLooks fine.",
                head + timedelta(minutes=20),
            ),
        ]
        findings = agent_guards.check_lgtm_notes(notes, head)
        self.assertTrue(any("2 findings" in item.fix for item in findings))

    def test_valid_lgtm_from_the_same_login_passes(self) -> None:
        head = datetime(2026, 10, 19, 18, 0, tzinfo=timezone.utc)
        notes = [
            agent_guards.ReviewNote(
                "changes",
                "ship review: changes needed\n\nHead: abcdef1\n\n1. Fix the guard.\n2. Add the ticket.\n",
                head + timedelta(minutes=12),
            ),
            agent_guards.ReviewNote(
                "lgtm",
                "ship review: LGTM\n\nHead abcdef1\n1. resolved\n2. addressed\n",
                head + timedelta(minutes=30),
            ),
        ]
        self.assertEqual(agent_guards.check_lgtm_notes(notes, head), [])


if __name__ == "__main__":
    unittest.main()
