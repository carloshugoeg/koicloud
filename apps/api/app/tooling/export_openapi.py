from __future__ import annotations

import json
from pathlib import Path

from app.main import create_app


def export_openapi(target_path: Path | None = None) -> Path:
    app = create_app()
    document = app.openapi()

    if target_path is None:
        repo_root = Path(__file__).resolve().parents[4]
        target_path = repo_root / "packages" / "contracts" / "openapi.json"

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target_path


def main() -> None:
    path = export_openapi()
    print(path)


if __name__ == "__main__":
    main()
