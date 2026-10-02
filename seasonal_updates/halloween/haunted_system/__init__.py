"""Haunted Exploration 2.0.

The public functions are re-exported here so the legacy
``seasonal_updates.halloween.haunted`` module can remain a thin compatibility
facade while the implementation lives in maintainable modules.
"""

from .constants import *  # noqa: F401,F403
from .discoveries import RARE_DISCOVERIES, HAUNTED_IMPOSSIBLE_DISCOVERIES
from .engine import get_scene, render_scene, resolve_choice
from .rewards import grant_haunted_completion_rewards, roll_haunted_rarity
from .sanity import calculate_sanity, game_date, is_insane, sanity_percent
from .state import (
    advance_story,
    clear_run,
    consume_attempt,
    ensure_haunted_schema,
    get_active_run,
    get_or_create_profile,
    start_run,
    update_sanity,
)
from .stories import STORIES, get_story

__all__ = [
    "HAUNTED_DAILY_ATTEMPTS",
    "HAUNTED_LOCATIONS",
    "SANITY_MAX",
    "SANITY_REGEN_SECONDS",
    "RARE_DISCOVERIES",
    "HAUNTED_IMPOSSIBLE_DISCOVERIES",
    "get_scene",
    "render_scene",
    "resolve_choice",
    "grant_haunted_completion_rewards",
    "roll_haunted_rarity",
    "calculate_sanity",
    "game_date",
    "is_insane",
    "sanity_percent",
    "advance_story",
    "clear_run",
    "consume_attempt",
    "ensure_haunted_schema",
    "get_active_run",
    "get_or_create_profile",
    "start_run",
    "update_sanity",
    "STORIES",
    "get_story",
]
