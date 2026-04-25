#!/usr/bin/env python
"""Wrapper to start the API server with correct env."""
import os
import sys

# Set env BEFORE any imports
os.environ["DATABASE_URL"] = "postgresql+psycopg://esdata:testpass@localhost:5434/esdata"

# Add apps/api to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from uvicorn import Config, Server
from main import app

config = Config(app=app, host="0.0.0.0", port=8001, log_level="info")
server = Server(config=config)
server.run()
