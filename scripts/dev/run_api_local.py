#!/usr/bin/env python
import os
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "postgresql+psycopg://esdata:testpass@localhost:5434/esdata"

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "apps" / "api"))

import uvicorn
uvicorn.run("main:app", host="0.0.0.0", port=8000)
