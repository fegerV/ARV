"""Pytest configuration and fixtures. Ensures project root is on sys.path for app imports."""

import sys
from pathlib import Path

# Add project root to PYTHONPATH for 'from app import ...' to work
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
