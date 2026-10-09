"""Persistent Haunted run/profile state and safe additive DB migrations."""

import json
import random

from pets import get_active_pet_effects

from .constants import (
    HAUNTED_DAILY_ATTEMPTS,
    HAUNTED_LOCATION_PET_OPPORTUNITY_CHANCE,
    HAUNTED_LOCATION_ROTATION_SIZE,
    HAUNTED_STORY_VERSION,
    HAUNTED_LOCATIONS,
    SANITY_MAX,
)
from .sanity import calculate_sanity_state, game_date, now
from .stories import get_story


def _decode_json(raw, fallback):
    try:
        value = json.loads(raw or "")
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback
    return value


async def ensure_haunted_schema(db):
    """Create Haunted tables and add only new nullable/defaulted columns.

    Existing Haunted tables are never dropped, renamed, or rebuilt. The story
    migration is deliberately additive so the economy database remains intact.
    """
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS haunted_profiles (
            user_id INTEGER PRIMARY KEY,
            sanity REAL NOT NULL DEFAULT 100,
            sanity_updated_at REAL NOT NULL DEFAULT 0,
            haunted_attempts INTEGER NOT NULL DEFAULT 20,
            attempts_date TEXT NOT NULL DEFAULT '',
            active_location TEXT DEFAULT '',
            active_stage INTEGER NOT NULL DEFAULT 0,
            active_total_stages INTEGER NOT NULL DEFAULT 0,
            active_started_at REAL NOT NULL DEFAULT 0,
            location_order TEXT NOT NULL DEFAULT '[]',
            location_group INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    async with db.execute("PRAGMA table_info(haunted_profiles)") as cursor:
        profile_columns = {row[1] for row in await cursor.fetchall()}
    for column, definition in {
        "location_order": "TEXT NOT NULL DEFAULT '[]'",
        "location_group": "INTEGER NOT NULL DEFAULT 0",
    }.items():
        if column not in profile_columns:
            await db.execute(f"ALTER TABLE haunted_profiles ADD COLUMN {column} {definition}")

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS haunted_runs (
            user_id INTEGER PRIMARY KEY,
            location_id TEXT NOT NULL,
            stage INTEGER NOT NULL DEFAULT 1,
            total_stages INTEGER NOT NULL,
            encounter_index INTEGER NOT NULL DEFAULT 0,
            sanity_at_start REAL NOT NULL DEFAULT 100,
            created_at REAL NOT NULL
        )
        """
    )

    async with db.execute("PRAGMA table_info(haunted_runs)") as cursor:
        columns = {row[1] for row in await cursor.fetchall()}

    migrations = {
        "story_version": f"INTEGER NOT NULL DEFAULT {HAUNTED_STORY_VERSION}",
        "current_scene": "TEXT NOT NULL DEFAULT ''",
        "story_state": "TEXT NOT NULL DEFAULT '{}'",
    }
    for column, definition in migrations.items():
        if column not in columns:
            await db.execute(f"ALTER TABLE haunted_runs ADD COLUMN {column} {definition}")


def _location_group(order, group_index):
    start = group_index * HAUNTED_LOCATION_ROTATION_SIZE
    available = list(order[start:start + HAUNTED_LOCATION_ROTATION_SIZE])
    if len(available) < HAUNTED_LOCATION_ROTATION_SIZE:
        previous_start = max(0, start - HAUNTED_LOCATION_ROTATION_SIZE)
        previous = set(order[previous_start:start])
        fillers = [location_id for location_id in order if location_id not in previous and location_id not in available]
        available.extend(fillers[:HAUNTED_LOCATION_ROTATION_SIZE - len(available)])
    return available


async def _ensure_location_rotation(db, user_id, raw_order, group_index):
    location_ids = list(HAUNTED_LOCATIONS)
    order = _decode_json(raw_order, [])
    if (
        not isinstance(order, list)
        or len(order) != len(location_ids)
        or not all(isinstance(location_id, str) for location_id in order)
        or set(order) != set(location_ids)
    ):
        order = location_ids[:]
        random.shuffle(order)
        group_index = 0

    group_count = (len(order) + HAUNTED_LOCATION_ROTATION_SIZE - 1) // HAUNTED_LOCATION_ROTATION_SIZE
    try:
        group_index = int(group_index)
    except (TypeError, ValueError):
        group_index = 0
    group_index = max(0, min(group_count - 1, group_index))
    await db.execute(
        "UPDATE haunted_profiles SET location_order = ?, location_group = ? WHERE user_id = ?",
        (json.dumps(order), group_index, user_id),
    )
    return order, group_index, _location_group(order, group_index)


async def get_or_create_profile(db, user_id):
    today = game_date()
    current_time = now()
    await ensure_haunted_schema(db)

    async with db.execute(
        """
        SELECT sanity, sanity_updated_at, haunted_attempts, attempts_date,
               active_location, active_stage, active_total_stages,
               location_order, location_group
        FROM haunted_profiles
        WHERE user_id = ?
        """,
        (user_id,),
    ) as cursor:
        row = await cursor.fetchone()

    if not row:
        await db.execute(
            """
            INSERT INTO haunted_profiles
                (user_id, sanity, sanity_updated_at, haunted_attempts, attempts_date)
            VALUES (?, 100, ?, ?, ?)
            """,
            (user_id, current_time, HAUNTED_DAILY_ATTEMPTS, today),
        )
        await db.commit()
        order, group_index, available_locations = await _ensure_location_rotation(
            db, user_id, "[]", 0
        )
        await db.commit()
        return {
            "sanity": 100.0,
            "sanity_updated_at": current_time,
            "attempts": HAUNTED_DAILY_ATTEMPTS,
            "attempts_date": today,
            "active_location": "",
            "active_stage": 0,
            "active_total_stages": 0,
            "available_locations": available_locations,
            "location_order": order,
            "location_group": group_index,
        }

    (sanity, updated_at, attempts, attempts_date, active_location, active_stage,
     active_total, raw_location_order, location_group) = row
    current_sanity, sanity_anchor = calculate_sanity_state(
        sanity, updated_at, current_time
    )
    if attempts_date != today:
        attempts = HAUNTED_DAILY_ATTEMPTS
        attempts_date = today

    order, group_index, available_locations = await _ensure_location_rotation(
        db, user_id, raw_location_order, location_group
    )
    await db.execute(
        """
        UPDATE haunted_profiles
        SET sanity = ?, sanity_updated_at = ?, haunted_attempts = ?, attempts_date = ?
        WHERE user_id = ?
        """,
        (current_sanity, sanity_anchor, attempts, attempts_date, user_id),
    )
    await db.commit()

    return {
        "sanity": current_sanity,
        "sanity_updated_at": sanity_anchor,
        "attempts": attempts,
        "attempts_date": attempts_date,
        "active_location": active_location or "",
        "active_stage": active_stage or 0,
        "active_total_stages": active_total or 0,
        "available_locations": available_locations,
        "location_order": order,
        "location_group": group_index,
    }


async def consume_attempt(db, user_id):
    profile = await get_or_create_profile(db, user_id)
    if profile["attempts"] <= 0:
        return False, profile

    attempts = profile["attempts"] - 1
    await db.execute(
        "UPDATE haunted_profiles SET haunted_attempts = ? WHERE user_id = ?",
        (attempts, user_id),
    )
    await db.commit()
    profile["attempts"] = attempts
    return True, profile


async def update_sanity(db, user_id, delta, regen_multiplier=1.0):
    await ensure_haunted_schema(db)
    current_time = now()
    async with db.execute(
        "SELECT sanity, sanity_updated_at FROM haunted_profiles WHERE user_id = ?",
        (user_id,),
    ) as cursor:
        row = await cursor.fetchone()

    if not row:
        sanity = SANITY_MAX
        updated_at = current_time
    else:
        sanity, updated_at = row
        sanity, updated_at = calculate_sanity_state(
            sanity, updated_at, current_time, regen_multiplier
        )

    new_sanity = max(0.0, min(SANITY_MAX, sanity + float(delta)))
    sanity_anchor = updated_at if float(delta) == 0 else current_time
    await db.execute(
        "UPDATE haunted_profiles SET sanity = ?, sanity_updated_at = ? WHERE user_id = ?",
        (new_sanity, sanity_anchor, user_id),
    )
    return new_sanity


async def _read_effects(db, user_id):
    async with db.execute("SELECT active_effects FROM users WHERE user_id = ?", (user_id,)) as cursor:
        row = await cursor.fetchone()
    effects = _decode_json(row[0] if row else "{}", {})
    return effects if isinstance(effects, dict) else {}


async def start_run(db, user_id, location_id, sanity):
    story = get_story(location_id)
    if not story:
        raise KeyError(f"Unknown Haunted location: {location_id}")

    total_stages = story["scene_count"]
    current_time = now()
    effects = await _read_effects(db, user_id)

    # Starting a new run clears only previous Haunted run-scoped flags. Other
    # persistent effects used by mining/scavenging/etc. remain untouched.
    for key in list(effects):
        if key.startswith("haunted_run_"):
            effects.pop(key, None)

    pet_effects = await get_active_pet_effects(db, user_id)
    if pet_effects.get("haunted_location") == location_id:
        sanity_reduction = float(pet_effects.get("haunted_sanity_reduction", 0.0))
        if sanity_reduction > 0:
            effects["haunted_run_sanity_multiplier"] = min(
                float(effects.get("haunted_run_sanity_multiplier", 1.0)),
                max(0.0, 1.0 - sanity_reduction),
            )

        for key in (
            "haunted_ingredient_bonus",
            "haunted_reward_bonus",
            "haunted_negative_protection",
            "haunted_discovery_bonus",
        ):
            value = float(pet_effects.get(key, 0.0))
            if value > 0:
                effects[f"haunted_run_{key.removeprefix('haunted_')}"] = value

        stage_reduction = float(pet_effects.get("haunted_stage_reduction", 0.0))
        if stage_reduction > 0 and random.random() < stage_reduction:
            effects["haunted_run_stage_reduced"] = True

        malo_bonus = float(pet_effects.get("haunted_malo", 0.0))
        if malo_bonus > 0:
            effects["haunted_run_discovery_bonus"] = max(
                float(effects.get("haunted_run_discovery_bonus", 0.0)), malo_bonus
            )
            effects["haunted_run_malo_warning_chance"] = malo_bonus

    # Consume prepared Cauldron/Ritual/Workshop effects exactly once when the
    # next Haunted run starts, preserving the existing inventory contract.
    potion_protection = effects.pop("haunted_potion_run_protection", 0)
    if potion_protection:
        effects["haunted_run_flat_protection"] = max(
            int(effects.get("haunted_run_flat_protection", 0)),
            max(0, int(potion_protection)) * 5,
        )

    potion_insight = effects.pop("haunted_potion_encounter_insight", 0)
    if potion_insight:
        effects["haunted_run_discovery_bonus"] = float(
            effects.get("haunted_run_discovery_bonus", 0.0)
        ) + (0.05 * float(potion_insight))

    potion_collectible_bonus = effects.pop("haunted_potion_collectible_bonus", 0)
    if potion_collectible_bonus:
        effects["haunted_run_collectible_bonus"] = (
            float(effects.get("haunted_run_collectible_bonus", 0.0))
            + float(potion_collectible_bonus)
        )

    potion_bias = effects.pop("haunted_potion_rare_encounter_bias", 0)
    if potion_bias:
        effects["haunted_run_discovery_bonus"] = float(
            effects.get("haunted_run_discovery_bonus", 0.0)
        ) + (0.05 * float(potion_bias))

    if effects.pop("haunted_potion_sanity_guard", 0):
        effects["haunted_run_sanity_multiplier"] = min(
            float(effects.get("haunted_run_sanity_multiplier", 1.0)), 0.75
        )
    if effects.pop("haunted_potion_curse_protection", False):
        effects["haunted_run_block_next_negative"] = True

    if effects.pop("haunted_ghost_radio", False):
        effects["haunted_run_force_universal"] = True
    if effects.pop("haunted_watchers_eye", False):
        effects["haunted_run_force_location"] = True
        effects["haunted_run_watchers_eye"] = True
    if effects.pop("haunted_mascot_tracker", False):
        effects["haunted_run_collectible_bonus"] = float(effects.get("haunted_run_collectible_bonus", 0.0)) + 0.15
    if effects.pop("haunted_spectral_receiver", False):
        effects["haunted_run_collectible_bonus"] = float(effects.get("haunted_run_collectible_bonus", 0.0)) + 0.10
    if effects.pop("haunted_security_monitor", False):
        effects["haunted_run_flat_protection"] = 5

    if location_id == "endless_hotel" and effects.pop("haunted_room_314_key", False):
        effects["haunted_run_stage_reduced"] = True
    if location_id == "fogbound_town" and effects.pop("haunted_fog_lantern", False):
        effects["haunted_run_sanity_multiplier"] = min(float(effects.get("haunted_run_sanity_multiplier", 1.0)), 0.5)
    if location_id == "broadcast_station" and effects.pop("haunted_dead_air_charm", False):
        effects["haunted_run_sanity_multiplier"] = min(float(effects.get("haunted_run_sanity_multiplier", 1.0)), 0.5)
    if location_id == "endless_hotel" and effects.pop("haunted_empty_room_token", False):
        effects["haunted_run_block_next_negative"] = True
    if location_id == "derelict_research_facility" and effects.pop("haunted_containment_mark", False):
        effects["haunted_run_sanity_multiplier"] = min(float(effects.get("haunted_run_sanity_multiplier", 1.0)), 0.25)
    if location_id == "yellow_halls" and effects.pop("haunted_yellow_halls_beacon", False):
        effects["haunted_run_sanity_multiplier"] = min(float(effects.get("haunted_run_sanity_multiplier", 1.0)), 0.5)
    if location_id == "yellow_halls" and effects.pop("haunted_yellow_halls_unmarked_key", False):
        effects["haunted_run_block_next_negative"] = True
    if location_id == "dead_end_highway" and effects.pop("haunted_highway_payphone_kit", False):
        effects["haunted_run_force_universal"] = True
    if location_id == "dead_end_highway" and effects.pop("haunted_highway_motel_ward", False):
        effects["haunted_run_block_next_negative"] = True
    if location_id == "drowned_station" and effects.pop("haunted_drowned_flood_lamp", False):
        effects["haunted_run_sanity_multiplier"] = min(float(effects.get("haunted_run_sanity_multiplier", 1.0)), 0.5)
    if location_id == "drowned_station" and effects.pop("haunted_drowned_last_stop_ticket", False):
        effects["haunted_run_stage_reduced"] = True
    if location_id == "silent_campground" and effects.pop("haunted_campground_static_filter", False):
        effects["haunted_run_sanity_multiplier"] = min(float(effects.get("haunted_run_sanity_multiplier", 1.0)), 0.5)
    if location_id == "silent_campground" and effects.pop("haunted_campground_tendril_ward", False):
        effects["haunted_run_collectible_bonus"] = float(effects.get("haunted_run_collectible_bonus", 0.0)) + 0.15
    if effects.pop("haunted_warding_sigil", False):
        effects["haunted_run_block_next_negative"] = True
    if effects.pop("haunted_mirror_ward", False):
        effects["haunted_run_half_next_negative"] = True

    # Location pets are intentionally an opportunity rather than a guaranteed
    # encounter. The roll happens once when the run starts; the pet scene stays
    # in the route either way, while the engine swaps in a spooky non-pet
    # outcome when this run has no pet opportunity.
    pet_opportunity_available = random.random() < HAUNTED_LOCATION_PET_OPPORTUNITY_CHANCE

    skip_scenes = []
    shortcut_scene = story.get("shortcut_scene") if effects.get("haunted_run_stage_reduced") else None
    if shortcut_scene:
        skip_scenes.append(shortcut_scene)
    # Deduplicate while preserving story order. Shortcut items can shorten a
    # run, but pet availability never changes its displayed stage count.
    skip_scenes = list(dict.fromkeys(skip_scenes))
    total_stages = max(2, total_stages - len(skip_scenes))

    opening_variants = story.get("opening_variants") or []
    opening_variant = random.randrange(len(opening_variants)) if opening_variants else None
    scene_variants = {
        scene_id: random.randrange(len(variants) + 1)
        for scene_id, variants in (story.get("scene_variants") or {}).items()
        if variants
    }

    story_state = {
        "flags": {},
        "discoveries_found": [],
        "story_route": "alternate" if random.random() < 0.5 else "original",
        "opening_variant": opening_variant,
        "scene_variants": scene_variants,
        "pet_opportunity_available": pet_opportunity_available,
        "pet_opportunity_taken": False,
        "pet_discovery_message": None,
        "insane_opening": float(sanity) <= 0,
        "story_version": HAUNTED_STORY_VERSION,
    }
    if skip_scenes:
        story_state["skip_scenes"] = skip_scenes

    await db.execute(
        """
        INSERT INTO haunted_runs
            (user_id, location_id, stage, total_stages, encounter_index,
             sanity_at_start, created_at, story_version, current_scene, story_state)
        VALUES (?, ?, 1, ?, 0, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            location_id = excluded.location_id,
            stage = 1,
            total_stages = excluded.total_stages,
            encounter_index = 0,
            sanity_at_start = excluded.sanity_at_start,
            created_at = excluded.created_at,
            story_version = excluded.story_version,
            current_scene = excluded.current_scene,
            story_state = excluded.story_state
        """,
        (
            user_id,
            location_id,
            total_stages,
            float(sanity),
            current_time,
            HAUNTED_STORY_VERSION,
            story["opening_scene"],
            json.dumps(story_state),
        ),
    )
    await db.execute(
        """
        UPDATE haunted_profiles
        SET active_location = ?, active_stage = 1, active_total_stages = ?, active_started_at = ?
        WHERE user_id = ?
        """,
        (location_id, total_stages, current_time, user_id),
    )
    await db.execute(
        "UPDATE users SET active_effects = ? WHERE user_id = ?",
        (json.dumps(effects), user_id),
    )
    await db.commit()
    return total_stages


async def get_active_run(db, user_id):
    await ensure_haunted_schema(db)
    async with db.execute(
        """
        SELECT location_id, stage, total_stages, encounter_index, sanity_at_start,
               created_at, story_version, current_scene, story_state
        FROM haunted_runs
        WHERE user_id = ?
        """,
        (user_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        return None

    location_id, stage, total_stages, encounter_index, sanity_at_start, created_at, version, current_scene, raw_state = row
    story = get_story(location_id)
    if not story:
        return None

    state = _decode_json(raw_state, {})
    if not isinstance(state, dict):
        state = {}
    state.setdefault("scene_variants", {})

    # Additive compatibility migration for an in-progress pre-story run. We do
    # not delete it or consume another attempt; we map its current stage to the
    # closest authored scene and continue from there.
    if int(version or 0) < HAUNTED_STORY_VERSION or not current_scene:
        index = min(max(int(stage or 1) - 1, 0), len(story["scene_order"]) - 1)
        current_scene = story["scene_order"][index]
        total_stages = max(int(stage or 1), len(story["scene_order"]))
        state.setdefault("flags", {})
        state.setdefault("discoveries_found", [])
        state.setdefault("pet_opportunity_available", False)
        state.setdefault("pet_opportunity_taken", False)
        state.setdefault("pet_discovery_message", None)
        state.setdefault("skip_scenes", [])
        state["story_version"] = HAUNTED_STORY_VERSION
        await db.execute(
            """
            UPDATE haunted_runs
            SET story_version = ?, current_scene = ?, total_stages = ?, story_state = ?
            WHERE user_id = ?
            """,
            (HAUNTED_STORY_VERSION, current_scene, total_stages, json.dumps(state), user_id),
        )
        await db.execute(
            "UPDATE haunted_profiles SET active_total_stages = ? WHERE user_id = ?",
            (total_stages, user_id),
        )
        await db.commit()

    return {
        "location_id": location_id,
        "stage": int(stage),
        "total_stages": int(total_stages),
        "encounter_index": int(encounter_index or 0),
        "sanity_at_start": sanity_at_start,
        "created_at": created_at,
        "story_version": int(version or HAUNTED_STORY_VERSION),
        "current_scene": current_scene,
        "story_state": state,
    }


async def save_story_state(db, user_id, *, stage=None, current_scene=None, state=None):
    run = await get_active_run(db, user_id)
    if not run:
        return None
    new_stage = run["stage"] if stage is None else int(stage)
    new_scene = run["current_scene"] if current_scene is None else current_scene
    new_state = run["story_state"] if state is None else state
    await db.execute(
        """
        UPDATE haunted_runs
        SET stage = ?, current_scene = ?, story_state = ?, encounter_index = encounter_index + 1
        WHERE user_id = ?
        """,
        (new_stage, new_scene, json.dumps(new_state), user_id),
    )
    await db.execute(
        "UPDATE haunted_profiles SET active_stage = ? WHERE user_id = ?",
        (new_stage, user_id),
    )
    await db.commit()
    return new_stage


async def clear_run(db, user_id):
    async with db.execute(
        "SELECT location_id FROM haunted_runs WHERE user_id = ?", (user_id,)
    ) as cursor:
        active_run = await cursor.fetchone()

    if active_run:
        profile = await get_or_create_profile(db, user_id)
        next_group = profile["location_group"] + 1
        group_count = (
            len(profile["location_order"]) + HAUNTED_LOCATION_ROTATION_SIZE - 1
        ) // HAUNTED_LOCATION_ROTATION_SIZE
        order = profile["location_order"]
        if next_group >= group_count:
            previous_locations = set(profile["available_locations"])
            fresh_locations = [item for item in HAUNTED_LOCATIONS if item not in previous_locations]
            repeated_locations = [item for item in HAUNTED_LOCATIONS if item in previous_locations]
            random.shuffle(fresh_locations)
            random.shuffle(repeated_locations)
            order = fresh_locations + repeated_locations
            next_group = 0
        await db.execute(
            "UPDATE haunted_profiles SET location_order = ?, location_group = ? WHERE user_id = ?",
            (json.dumps(order), next_group, user_id),
        )

    await db.execute("DELETE FROM haunted_runs WHERE user_id = ?", (user_id,))
    await db.execute(
        """
        UPDATE haunted_profiles
        SET active_location = '', active_stage = 0, active_total_stages = 0, active_started_at = 0
        WHERE user_id = ?
        """,
        (user_id,),
    )
    effects = await _read_effects(db, user_id)
    for key in list(effects):
        if key.startswith("haunted_run_"):
            effects.pop(key, None)
    await db.execute(
        "UPDATE users SET active_effects = ? WHERE user_id = ?",
        (json.dumps(effects), user_id),
    )
    await db.commit()

async def advance_story(db, user_id, next_scene, state):
    """Persist the next authored scene, honoring a one-scene shortcut."""
    run = await get_active_run(db, user_id)
    if not run:
        return None

    story = get_story(run["location_id"])
    if not story:
        return None

    target = next_scene
    state = dict(state or {})

    # New runs can skip more than one authored scene (for example, the
    # location-pet scene plus a prepared shortcut). Keep the old skip_scene
    # field readable for compatibility with any older in-progress state.
    skip_scenes = list(state.get("skip_scenes") or [])
    legacy_skip = state.get("skip_scene")
    if legacy_skip and legacy_skip not in skip_scenes:
        skip_scenes.append(legacy_skip)

    while target in skip_scenes:
        try:
            index = story["scene_order"].index(target)
            if index + 1 < len(story["scene_order"]):
                skip_scenes.remove(target)
                target = story["scene_order"][index + 1]
            else:
                skip_scenes.remove(target)
                target = None
                break
        except ValueError:
            skip_scenes.remove(target)

    state["skip_scenes"] = skip_scenes
    state["skip_scene"] = None

    if target is None:
        return None
    if target not in story["scenes"]:
        raise KeyError(f"Haunted story points to missing scene {target!r}")

    new_stage = run["stage"] + 1
    if new_stage > run["total_stages"]:
        return None

    await db.execute(
        """
        UPDATE haunted_runs
        SET stage = ?, current_scene = ?, story_state = ?, encounter_index = encounter_index + 1
        WHERE user_id = ?
        """,
        (new_stage, target, json.dumps(state or {}), user_id),
    )
    await db.execute(
        "UPDATE haunted_profiles SET active_stage = ? WHERE user_id = ?",
        (new_stage, user_id),
    )
    await db.commit()
    return new_stage, target, state
