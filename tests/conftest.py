import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def ensure_samples_exist():
    required = [
        "simple_text.pdf",
        "table_report.pdf",
        "two_column.pdf",
        "scanned_like.png",
        "nested_table.png",
        "invalid.txt",
    ]
    missing = [f for f in required if not (SAMPLES_DIR / f).exists()]
    if missing:
        import subprocess

        subprocess.run([sys.executable, str(SAMPLES_DIR / "generate_samples.py")], check=True)
