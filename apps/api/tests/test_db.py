import sys
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import InvalidRequestError

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def test_session_close_is_terminal():
    from db import SessionLocal

    session = SessionLocal()
    session.close()

    with pytest.raises(InvalidRequestError, match="permanently closed"):
        session.execute(text("SELECT 1"))
