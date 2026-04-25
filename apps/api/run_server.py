#!/usr/bin/env python
import os
os.environ["DATABASE_URL"] = "postgresql+psycopg://esdata:testpass@localhost:5434/esdata"

import uvicorn
uvicorn.run("main:app", host="0.0.0.0", port=8000)
