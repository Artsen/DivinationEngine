from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DATABASE = REPOSITORY_ROOT / ".e2e-web-ui.db"
if DATABASE.parent != REPOSITORY_ROOT or DATABASE.name != ".e2e-web-ui.db":
    raise RuntimeError(f"unsafe E2E database path: {DATABASE}")
DATABASE.unlink(missing_ok=True)
os.environ["DIVINATION_DATABASE_URL"] = "sqlite:///./.e2e-web-ui.db"
sys.path.insert(0, str(REPOSITORY_ROOT / "backend"))

from app.services.dev_bootstrap import install_corpora, install_spreads, migrate  # noqa: E402

migrate()
install_corpora()
install_spreads()
uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
