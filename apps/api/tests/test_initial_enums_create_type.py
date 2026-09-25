import importlib.util
from pathlib import Path

from sqlalchemy.dialects.postgresql import ENUM


def test_initial_enums_do_not_recreate_on_create_table() -> None:
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0001_initial.py"
    spec = importlib.util.spec_from_file_location("initial_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    enums = [
        value
        for value in vars(module).values()
        if isinstance(value, ENUM)
    ]
    assert enums, "0001_initial must declare postgresql.ENUM types"
    missing = [enum.name for enum in enums if enum.create_type]
    assert missing == [], f"create_table would recreate: {missing}"
