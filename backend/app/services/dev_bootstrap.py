from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from alembic.config import Config
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.db.session import SessionLocal
from app.services.importer import ImportBundle, import_bundle
from app.services.spreads import install_builtin_spreads

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CORPORA = (
    REPOSITORY_ROOT / "data" / "corpus" / "tarot" / "rws-1909" / "build" / "rws-import.json",
    REPOSITORY_ROOT / "data" / "corpus" / "iching" / "legge-ctext" / "build" / "iching-import.json",
    REPOSITORY_ROOT
    / "data"
    / "corpus"
    / "runes"
    / "elder-futhark"
    / "build"
    / "elder-futhark-import.json",
)


def migrate() -> None:
    config = Config(str(REPOSITORY_ROOT / "alembic.ini"))
    config.set_main_option(
        "script_location", str(REPOSITORY_ROOT / "backend" / "alembic").replace("%", "%%")
    )
    command.upgrade(config, "head")


def install_corpora() -> list[dict[str, Any]]:
    results = []
    with SessionLocal() as session:
        for path in CORPORA:
            bundle = ImportBundle.model_validate_json(path.read_text(encoding="utf-8"))
            results.append({"corpus": path.name, **import_bundle(session, bundle)})
    return results


def install_spreads() -> dict[str, int]:
    with SessionLocal() as session:
        return install_builtin_spreads(session)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate a development database and idempotently install bundled corpora."
    )
    parser.parse_args()
    try:
        migrate()
        result = {
            "migrations": "at head",
            "corpora": install_corpora(),
            "spreads": install_spreads(),
        }
    except (OSError, ValidationError, ValueError, IntegrityError) as exc:
        parser.exit(1, f"Development bootstrap failed: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
