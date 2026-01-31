"""
Pytest configuration for vial-laybell integration tests.

Sets up Python path to allow importing from src/ without installation.
"""

import sys
from pathlib import Path

# Add src directory to Python path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
