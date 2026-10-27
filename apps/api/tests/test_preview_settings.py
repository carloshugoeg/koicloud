"""Preview schema setting stays empty by default."""

from app.core.config import Settings


def test_koi_db_schema_defaults_empty(monkeypatch) -> None:
    monkeypatch.delenv("KOI_DB_SCHEMA", raising=False)
    settings = Settings(
        database_url="postgresql+asyncpg://koicloud:koicloud@localhost:5432/koicloud",
    )
    assert settings.koi_db_schema == ""
    assert "koi_preview_mock" not in Settings.model_fields


def test_sidebar_and_scroll_regions_have_a11y_hooks() -> None:
    """Source guards for gate: contrast token + scrollable regions."""
    from pathlib import Path

    web = Path(__file__).resolve().parents[2] / "web" / "src"
    sidebar = (web / "app/layout/sidebar-nav.tsx").read_text()
    assert "text-ink-muted" in sidebar
    assert "text-ink-faint" not in sidebar

    agent = (web / "features/agent-access/agent-snippets.tsx").read_text()
    assert 'data-testid="agent-snippet"' in agent
    assert "tabIndex={0}" in agent
    assert 'aria-label="Snippet de conexión del agente"' in agent
    assert "AgentSnippets" in (web / "features/agent-access/agent-access-page.tsx").read_text()

    plans = (web / "features/plans/plans-page.tsx").read_text()
    assert 'aria-label="Comparativa de planes"' in plans
    assert "tabIndex={0}" in plans
