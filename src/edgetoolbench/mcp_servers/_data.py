"""Shared deterministic mock data helpers."""

from __future__ import annotations

import random
from datetime import date, timedelta


def seeded_random(seed: int = 0) -> random.Random:
    return random.Random(seed)


def generate_dates(start: date, count: int = 7) -> list[str]:
    """Generate a sequence of ISO date strings starting from `start`."""
    return [(start + timedelta(days=i)).isoformat() for i in range(count)]


def generate_id(prefix: str, num: int) -> str:
    """Generate a zero-padded ID like 'FL001', 'HT003'."""
    return f"{prefix}{num:03d}"
