"""Locate the isolated *_test database (used by the test suite and eval scripts)."""

import os
import re
from pathlib import Path


def _env_file_value(key: str) -> str | None:
    env_file = Path(__file__).resolve().parents[1] / ".env"
    if not env_file.exists():
        return None
    for line in env_file.read_text().splitlines():
        match = re.match(rf"^\s*{key}\s*=\s*(.*)$", line)
        if match:
            return match.group(1).strip().strip("'\"")
    return None


def is_test_database(url: str) -> bool:
    return url.rsplit("/", 1)[-1].endswith("_test")


def test_database_url() -> str:
    if url := os.environ.get("TEST_DATABASE_URL"):
        return url
    base = os.environ.get("DATABASE_URL") or _env_file_value("DATABASE_URL")
    base = base or "postgresql://user:password@localhost:5432/lifeos"
    if is_test_database(base):
        return base
    return base + "_test"
