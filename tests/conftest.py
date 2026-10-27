"""Shared paths for the v0.1 matrix tests."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ATOMS = ROOT / "examples" / "atoms.yaml"
