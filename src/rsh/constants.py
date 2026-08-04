"""Immutable constants for the Robitaille–Slade Helix model."""
from __future__ import annotations

import math

PSI: float = math.sqrt(2.0 + math.sqrt(5.0))
KAPPA_MAX: float = math.sqrt(2.0) - 1.0
TAU_MIN_EXCLUSIVE: float = 0.0
TAU_MAX_EXCLUSIVE: float = 1.0
MODEL_NAME: str = "Robitaille-Slade-Helix"
VERSION: str = "2.0.0"
RECEIPT_DOMAIN: bytes = b"RSH-GEOMETRY-EVIDENCE-V2\0"
