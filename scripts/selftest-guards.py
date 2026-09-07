#!/usr/bin/env python3
"""Convenient local test entrypoint; uses only the Python standard library."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT)
raise SystemExit(result.returncode)
