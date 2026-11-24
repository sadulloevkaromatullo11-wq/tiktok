import os
import tempfile
from pathlib import Path

_root = Path(tempfile.mkdtemp(prefix="minitok-"))
os.environ["VAR_DIR"] = str(_root)
os.environ["MEDIA_DIR"] = str(_root / "media")
os.environ["DATABASE_URL"] = "sqlite:///" + (_root / "test.db").as_posix()
os.environ["DEV_ALLOW_DEMO"] = "1"
os.environ["BOT_TOKEN"] = ""
os.environ["BOT_POLLING"] = "0"
os.environ["REDIS_URL"] = ""
os.environ["WEBAPP_URL"] = ""
os.environ["STORAGE"] = "local"

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


def auth(user_id: int = 1001) -> dict[str, str]:
    return {"Authorization": f"Demo {user_id}"}
