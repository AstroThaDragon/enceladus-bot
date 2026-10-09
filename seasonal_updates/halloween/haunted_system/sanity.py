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
    recovered, _ = calculate_sanity_state(
        sanity, updated_at, current_time, regen_multiplier
    )
    return recovered


def calculate_sanity_state(sanity, updated_at, current_time=None, regen_multiplier=1.0):
    """Return Sanity and its recovery anchor after applying six-hour steps.

    Sanity rises to at least half after one recovery interval and to full after
    two. The returned timestamp preserves time elapsed toward the next step.
    """
    if current_time is None:
        current_time = now()
    sanity = max(0.0, min(float(sanity), SANITY_MAX))
    updated_at = float(updated_at or current_time)
    elapsed = max(0.0, current_time - updated_at)
    multiplier = max(0.0, float(regen_multiplier))
    if multiplier == 0 or sanity >= SANITY_MAX:
        return sanity, current_time if sanity >= SANITY_MAX else updated_at

    interval = SANITY_REGEN_SECONDS / multiplier
    steps = int(elapsed // interval)
    if steps <= 0:
        return sanity, updated_at

    halfway = SANITY_MAX / 2
    if sanity >= halfway and steps >= 1:
        return float(SANITY_MAX), current_time

    if sanity < halfway and steps >= 2:
        return float(SANITY_MAX), current_time

    recovered = max(sanity, halfway)
    return recovered, updated_at + interval


def sanity_percent(sanity):
    return max(0, min(100, int(round(float(sanity)))))


def is_insane(sanity):
    return float(sanity) <= 0
