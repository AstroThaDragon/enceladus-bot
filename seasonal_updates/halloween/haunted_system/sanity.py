"""Haunted Sanity calculations."""

from datetime import datetime
import time

import pytz

from .constants import SANITY_MAX, SANITY_REGEN_SECONDS


def now():
    return time.time()


def game_date():
    return datetime.now(pytz.timezone("US/Eastern")).date().isoformat()


def calculate_sanity(sanity, updated_at, current_time=None, regen_multiplier=1.0):
    if current_time is None:
        current_time = now()
    sanity = max(0.0, min(float(sanity), SANITY_MAX))
    updated_at = float(updated_at or current_time)
    elapsed = max(0.0, current_time - updated_at)
    rate = max(0.0, float(regen_multiplier)) / SANITY_REGEN_SECONDS
    return min(SANITY_MAX, sanity + elapsed * rate * SANITY_MAX)


def sanity_percent(sanity):
    return max(0, min(100, int(round(float(sanity)))))


def is_insane(sanity):
    return float(sanity) <= 0
