import os
import sys

os.environ.setdefault("USE_MOCK_IBKR", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

sys.path.insert(0, os.path.abspath("backend"))
