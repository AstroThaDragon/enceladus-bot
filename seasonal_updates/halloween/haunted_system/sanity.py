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
    """Return continuously regenerated Sanity and its recovery anchor.

    Sanity regenerates linearly over time: 50 Sanity takes three hours and
    100 Sanity takes six hours from zero.
    """
    if current_time is None:
        current_time = now()
    sanity = max(0.0, min(float(sanity), SANITY_MAX))
    updated_at = float(updated_at or current_time)
    elapsed = max(0.0, current_time - updated_at)
    multiplier = max(0.0, float(regen_multiplier))
    if multiplier == 0 or sanity >= SANITY_MAX:
        return sanity, current_time if sanity >= SANITY_MAX else updated_at

    # SANITY_REGEN_SECONDS is the time required to regenerate the full bar.
    regen_rate = (SANITY_MAX / SANITY_REGEN_SECONDS) * multiplier
    recovered = min(float(SANITY_MAX), sanity + (elapsed * regen_rate))

    if recovered >= SANITY_MAX:
        return float(SANITY_MAX), current_time

    return recovered, current_time


def sanity_percent(sanity):
    return max(0, min(100, int(round(float(sanity)))))


def is_insane(sanity):
    return float(sanity) <= 0
