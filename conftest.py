"""Pytest configuration file to ensure project root is on sys.path.

This allows test modules executed from subdirectories (e.g., tests/) to import
internal packages such as `app` without installing the project as a package.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
# Prepend project root to sys.path if not already present
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))