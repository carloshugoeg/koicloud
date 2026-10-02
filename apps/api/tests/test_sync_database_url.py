from app.core.config import to_sync_database_url


def test_asyncpg_url_becomes_psycopg() -> None:
    assert (
        to_sync_database_url("postgresql+asyncpg://koi:koi@localhost:5432/koicloud_test")
        == "postgresql+psycopg://koi:koi@localhost:5432/koicloud_test"
    )


def test_asyncpg_ssl_query_becomes_sslmode() -> None:
    assert (
        to_sync_database_url(
            "postgresql+asyncpg://koi:koi@localhost:5432/koicloud_test?ssl=require"
        )
        == "postgresql+psycopg://koi:koi@localhost:5432/koicloud_test?sslmode=require"
    )


def test_already_sync_url_is_unchanged() -> None:
    url = "postgresql+psycopg://koi:koi@localhost:5432/koicloud_test"
    assert to_sync_database_url(url) == url
