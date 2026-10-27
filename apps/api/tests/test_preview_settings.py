"""Preview-only settings stay off by default."""

from app.core.config import Settings


def test_koi_preview_mock_defaults_false(monkeypatch) -> None:
    monkeypatch.delenv("KOI_PREVIEW_MOCK", raising=False)
    monkeypatch.delenv("KOI_DB_SCHEMA", raising=False)
    settings = Settings(
        database_url="postgresql+asyncpg://koicloud:koicloud@localhost:5432/koicloud",
    )
    assert settings.koi_preview_mock is False
    assert settings.koi_db_schema == ""
