import sys
import os

# Ensure the backend/ directory is on sys.path so `from app.xxx import ...`
# works regardless of how pytest is invoked (locally or in CI).
sys.path.insert(0, os.path.dirname(__file__))
