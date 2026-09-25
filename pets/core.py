"""Database-independent pet helpers and shared pet progression logic."""

import random

from .variants import (
    get_variant_info,
    get_variant_display,
)

from .config import (
    ALL_PETS, HAUNTED_PETS, PET_PASSIVE_MAX_LEVEL,
    NORMAL_EXPLORATION_PET_XP_MIN, NORMAL_EXPLORATION_PET_XP_MAX,
    HAUNTED_EXPLORATION_PET_XP_MIN, HAUNTED_EXPLORATION_PET_XP_MAX,
    HAUNTED_HOME_PET_XP_BONUS,
)

def xp_needed_for_next_level(level: int) -> int:
    """XP needed to advance from the supplied level to the next one."""
    return 250 + max(0, level - 1) * 100


def passive_level_for_pet(level: int) -> int:
    return min(PET_PASSIVE_MAX_LEVEL, max(1, level))


def get_pet_definition(pet_type: str, variant_id: str | None = None):
    definition = ALL_PETS.get(pet_type)
    if not definition or not variant_id:
        return definition
    variant = get_variant_info(pet_type, variant_id)
    if not variant:
        return definition
    merged = dict(definition)
    display_name, display_emoji, display_description = get_variant_display(
        pet_type, definition["name"], variant_id
    )
    merged["name"] = display_name
    merged["emoji"] = display_emoji or definition["emoji"]
    merged["description"] = display_description or definition["description"]
    merged["base_name"] = definition["name"]
    merged["variant_id"] = variant_id
    return merged


async def ensure_pet_variant_schema(db):
    """Ensure the small variant/fusion migration exists for shared pet helpers."""
    async with db.execute("PRAGMA table_info(pets)") as cursor:
        columns = {row[1] async for row in cursor}
    if "variant_id" not in columns:
        await db.execute("ALTER TABLE pets ADD COLUMN variant_id TEXT DEFAULT ''")
    if "fusion_level" not in columns:
        await db.execute("ALTER TABLE pets ADD COLUMN fusion_level INTEGER DEFAULT 0")


def get_haunted_pet_for_location(location_id: str):
    """Return the Haunted pet definition associated with a location."""
    for pet_id, pet in HAUNTED_PETS.items():
        if pet.get("haunted_location") == location_id:
            return pet_id, pet
    return None, None


def get_haunted_pet_discovery_message(pet_type: str) -> str:
    """Return the location pet's discovery text, with a safe fallback."""
    pet = HAUNTED_PETS.get(pet_type)
    if not pet:
        return ""
    return pet.get(
        "discovery_message",
        f"**🐾 You discovered {pet['name']}!**\n{pet['name']} is now in your pets inventory.",
    )


async def grant_haunted_pet(db, user_id: int, location_id: str):
    """Grant the unique Haunted pet for a location if the user does not own it."""
    await ensure_pet_variant_schema(db)
    pet_type, definition = get_haunted_pet_for_location(location_id)
    if not pet_type or not definition:
        return None

    async with db.execute(
        "SELECT pet_id FROM pets WHERE user_id = ? AND pet_type = ? LIMIT 1",
        (user_id, pet_type),
    ) as cursor:
        existing = await cursor.fetchone()

    if existing:
        return {
            "pet_type": pet_type,
            "name": definition["name"],
            "emoji": definition["emoji"],
            "new": False,
            "message": "",
        }

    async with db.execute(
        "SELECT pet_id FROM pets WHERE user_id = ? AND is_active = 1 LIMIT 1",
        (user_id,),
    ) as cursor:
        has_active = await cursor.fetchone()

    await db.execute(
        """
        INSERT INTO pets
            (user_id, pet_stage, pet_type, nickname, level, xp, is_active)
        VALUES (?, ?, ?, '', 1, 0, ?)
        """,
        (user_id, pet_type, pet_type, 0 if has_active else 1),
    )

    return {
        "pet_type": pet_type,
        "name": definition["name"],
        "emoji": definition["emoji"],
        "new": True,
        "message": get_haunted_pet_discovery_message(pet_type),
    }


PET_PASSIVE_DIALOGUES = {
    "stardust_bonus": [
        "found some extra Stardust hiding in the debris!",
        "sniffed out a little extra Stardust!",
        "helped uncover some bonus Stardust!",
    ],
    "material_bonus": [
        "found an extra chunk of material!",
        "dug up one more piece of useful material!",
        "spotted a little extra material hiding nearby!",
    ],
    "hazard_reduction": [
        "softened the hit and kept some damage off you!",
        "helped absorb part of the impact!",
        "took some of the sting out of the hazard!",
    ],
    "charge_save": [
        "saved your exploration charge!",
        "kept the equipment running without consuming a charge!",
        "somehow convinced the equipment to keep your charge!",
    ],
    "scavenge_charge_save": [
        "saved your scavenging charge!",
        "kept the drone powered without using a charge!",
        "somehow convinced the drone to keep your charge!",
    ],
    "scavenge_hazard_avoidance": [
        "spotted the hazard before it could hit you!",
        "pulled you safely out of the hazard's path!",
        "noticed something was wrong and got you clear!",
    ],
    "scavenge_first_aid": [
        "patched you up after the hazard!",
        "dug out some emergency first aid!",
        "gave you a quick field treatment!",
    ],
    "scavenge_bonus_loot": [
        "found an extra piece of salvage!",
        "dug up a bonus piece of space junk!",
        "spotted something extra worth hauling home!",
    ],
    "rare_loot_bonus": [
        "spotted a rare find hiding among the wreckage!",
        "noticed something valuable that you might have missed!",
        "helped uncover a rarer piece of salvage!",
    ],
    "candy_bonus": [
        "found some extra Halloween Candy!",
        "dug up a little extra Halloween Candy!",
        "somehow made the Halloween Candy haul bigger!",
    ],
    "halloween_bonus": [
        "found an extra Halloween item!",
        "uncovered an extra seasonal find!",
        "spotted one more Halloween goodie!",
    ],
    "atomic_breath": [
        "blasted the incoming hazard before it could reach you!",
        "vaporized the incoming hazard!",
        "incinerated the hazard on the spot!",
    ],
    "minigame_payout": [
        "boosted your minigame payout!",
        "sweetened your winnings!",
        "managed to squeeze a little extra Stardust out of the game!",
    ],
    "trickster_tokens": [
        "pulled a little trick and helped with your Arcade Tokens!",
        "performed some suspicious token magic!",
        "did something questionable with the Arcade Token supply!",
    ],
    "daily_bonus": [
        "helped brighten your daily Stardust reward!",
        "gave your daily reward a little celestial boost!",
        "added a little extra sparkle to today's Stardust!",
    ],
    "streak_rescue": [
        "rescued your broken daily streak!",
        "caught your missed day before it could break the streak!",
        "somehow convinced the station to forgive your missed daily!",
    ],
    "daily_double": [
        "doubled today's daily Stardust reward!",
        "made today's daily reward twice as generous!",
        "went absolutely overboard and doubled the daily payout!",
    ],
    "shop_discount": [
        "talked the merchant into giving you a better price!",
        "negotiated a discount with the station shop!",
        "convinced the merchant to knock some Stardust off the price!",
    ],
    "shop_free_purchase": [
        "pulled some suspicious merchant magic and made the purchase free!",
        "somehow convinced the merchant to let you have it for free!",
        "talked the shop into a completely free purchase!",
    ],
    "dragonrider_success": [
        "steadied you at just the right moment during the flight test!",
        "helped you pull off the maneuver that sealed the test!",
        "gave you a perfectly timed boost during the flight test!",
    ],
}


def get_pet_passive_message(pet_effects: dict, effect_id: str, **values) -> str:
    """Return a small companion reaction for a passive that actually helped."""
    pet_name = pet_effects.get("pet_nickname") or pet_effects.get("pet_name")
    if not pet_name:
        return ""
    lines = PET_PASSIVE_DIALOGUES.get(effect_id)
    if not lines:
        return ""
    emoji = pet_effects.get("pet_emoji", "🐾")
    line = random.choice(lines).format(**values)
    return f"{emoji} **{pet_name}** {line}"


def get_passive_value(pet: dict, level: int | None = None) -> float:
    passive = pet.get("passive", {})
    values = passive.get("levels", [])
    if not values:
        return 0.0

    passive_level = passive_level_for_pet(level if level is not None else 1)
    index = min(len(values), passive_level) - 1
    base_value = float(values[index])
    fusion_level = max(0, min(5, int(pet.get("fusion_level", pet.get("fusion", 0)) or 0)))
    return base_value * (1.0 + fusion_level * 0.02)


async def get_active_pet(db, user_id: int):
    await ensure_pet_variant_schema(db)
    async with db.execute(
        """
        SELECT pet_id, pet_type, pet_stage, nickname, level, xp, variant_id, fusion_level
        FROM pets
        WHERE user_id = ? AND is_active = 1
        ORDER BY pet_id DESC
        LIMIT 1
        """,
        (user_id,),
    ) as cursor:
        row = await cursor.fetchone()

    if not row:
        return None

    pet_id, pet_type, pet_stage, nickname, level, xp, variant_id, fusion_level = row
    base_pet_type = pet_type or pet_stage
    definition = get_pet_definition(base_pet_type, variant_id)
    if not definition:
        return {
            "pet_id": pet_id,
            "pet_type": base_pet_type,
            "variant_id": variant_id,
            "fusion_level": fusion_level or 0,
            "name": (base_pet_type or "Unknown Pet").replace("_", " ").title(),
            "emoji": "🐾",
            "description": "Unknown pet.",
            "nickname": nickname,
            "level": level or 1,
            "xp": xp or 0,
            "passive": {},
            "normal_passive": {},
            "haunted_passive": {},
            "haunted_location": None,
        }

    return {
        "pet_id": pet_id,
        "pet_type": base_pet_type,
        "variant_id": variant_id,
        "fusion_level": fusion_level or 0,
        "name": definition["name"],
        "emoji": definition["emoji"],
        "description": definition["description"],
        "nickname": nickname,
        "level": level or 1,
        "xp": xp or 0,
        "passive": definition.get("passive", {}),
        "normal_passive": definition.get("normal_passive", definition.get("passive", {})),
        "haunted_passive": definition.get("passive", {}) if definition.get("haunted_location") else {},
        "haunted_location": definition.get("haunted_location"),
    }


async def get_active_pet_effects(db, user_id: int):
    """
    Return the active pet's currently effective passive values.

    This helper accepts an existing DB connection so exploration does not open
    another SQLite connection while it is already inside its transaction.
    """
    pet = await get_active_pet(db, user_id)
    if not pet:
        return {
            "level": 0,
            "passive_level": 0,
            "pet_name": "",
            "pet_nickname": "",
            "pet_emoji": "🐾",
            "normal_effect_id": "",
            "stardust_bonus": 0.0,
            "material_bonus": 0.0,
            "rare_bonus": 0.0,
            "hazard_reduction": 0.0,
            "charge_save": 0.0,
            "cooldown_reduction": 0.0,
            "halloween_bonus": 0.0,
            "treat_xp_bonus": 0.0,
            "atomic_breath": 0.0,
            "candy_bonus": 0.0,
            "scavenge_first_aid": 0.0,
            "scavenge_hazard_avoidance": 0.0,
            "scavenge_charge_save": 0.0,
            "scavenge_material_bonus": 0.0,
            "scavenge_bonus_loot": 0.0,
            "extra_charges": 0.0,
            "extra_charge_count": 0,
            "dragonrider_success": 0.0,
            "dragonrider_extra_attempts": 0,
            "minigame_payout": 0.0,
            "trickster_tokens": 0,
            "shop_discount": 0.0,
            "shop_free_purchase": 0.0,
            "daily_bonus": 0.0,
            "daily_double": 0.0,
            "streak_rescue": 0,
            "haunted_sanity_reduction": 0.0,
            "haunted_ingredient_bonus": 0.0,
            "haunted_reward_bonus": 0.0,
            "haunted_negative_protection": 0.0,
            "haunted_discovery_bonus": 0.0,
            "haunted_stage_reduction": 0.0,
            "haunted_malo": 0.0,
            "haunted_location": None,
        }

    passive = pet.get("passive", {})
    value = get_passive_value(pet, pet["level"])
    effect_id = passive.get("id")

    effects = {
        "level": pet["level"],
        "passive_level": passive_level_for_pet(pet["level"]),
        "pet_name": pet.get("name", ""),
        "pet_nickname": pet.get("nickname") or "",
        "pet_emoji": pet.get("emoji", "🐾"),
        "normal_effect_id": "",
        "stardust_bonus": 0.0,
        "material_bonus": 0.0,
        "rare_bonus": 0.0,
        "hazard_reduction": 0.0,
        "charge_save": 0.0,
        "cooldown_reduction": 0.0,
        "halloween_bonus": 0.0,
        "treat_xp_bonus": 0.0,
        "atomic_breath": 0.0,
        "candy_bonus": 0.0,
        "scavenge_first_aid": 0.0,
        "scavenge_hazard_avoidance": 0.0,
        "scavenge_charge_save": 0.0,
        "scavenge_material_bonus": 0.0,
        "scavenge_bonus_loot": 0.0,
        "extra_charges": 0.0,
        "extra_charge_count": 0,
        "dragonrider_success": 0.0,
        "dragonrider_extra_attempts": 0,
        "minigame_payout": 0.0,
        "trickster_tokens": 0,
        "shop_discount": 0.0,
        "shop_free_purchase": 0.0,
        "daily_bonus": 0.0,
        "daily_double": 0.0,
        "streak_rescue": 0,
    }

    normal_passive = pet.get("normal_passive")
    if normal_passive:
        normal_value = get_passive_value({"passive": normal_passive, "level": pet["level"], "fusion_level": pet.get("fusion_level", 0)}, pet["level"])
        normal_effect_id = normal_passive.get("id")
    else:
        normal_value = value
        normal_effect_id = effect_id

    effects["normal_effect_id"] = normal_effect_id or ""

    if normal_effect_id == "stardust_bonus":
        effects["stardust_bonus"] = normal_value
    elif normal_effect_id == "material_bonus":
        effects["material_bonus"] = normal_value
    elif normal_effect_id == "rare_loot_bonus":
        effects["rare_bonus"] = normal_value
    elif normal_effect_id == "hazard_reduction":
        effects["hazard_reduction"] = normal_value
    elif normal_effect_id == "charge_save":
        effects["charge_save"] = normal_value
    elif normal_effect_id == "cooldown_reduction":
        effects["cooldown_reduction"] = normal_value
    elif normal_effect_id == "halloween_bonus":
        effects["halloween_bonus"] = normal_value
    elif normal_effect_id == "treat_xp_bonus":
        effects["treat_xp_bonus"] = normal_value
    elif normal_effect_id == "atomic_breath":
        effects["atomic_breath"] = normal_value
    elif normal_effect_id == "candy_bonus":
        effects["candy_bonus"] = normal_value
    elif normal_effect_id == "scavenge_first_aid":
        effects["scavenge_first_aid"] = normal_value
    elif normal_effect_id == "scavenge_hazard_avoidance":
        effects["scavenge_hazard_avoidance"] = normal_value
    elif normal_effect_id == "scavenge_charge_save":
        effects["scavenge_charge_save"] = normal_value
    elif normal_effect_id == "scavenge_material_bonus":
        effects["scavenge_material_bonus"] = normal_value
    elif normal_effect_id == "scavenge_bonus_loot":
        effects["scavenge_bonus_loot"] = normal_value

    elif normal_effect_id == "extra_charges":
        effects["extra_charges"] = normal_value
        if effects["passive_level"] >= PET_PASSIVE_MAX_LEVEL:
            effects["extra_charge_count"] = 3
    elif normal_effect_id == "dragonrider_success":
        effects["dragonrider_success"] = normal_value
        if effects["passive_level"] >= PET_PASSIVE_MAX_LEVEL:
            effects["dragonrider_extra_attempts"] = 1
    elif normal_effect_id == "minigame_payout":
        effects["minigame_payout"] = normal_value
    elif normal_effect_id == "trickster_tokens":
        if effects["passive_level"] >= PET_PASSIVE_MAX_LEVEL:
            effects["trickster_tokens"] = 1
    elif normal_effect_id == "shop_discount":
        effects["shop_discount"] = normal_value
        if effects["passive_level"] >= PET_PASSIVE_MAX_LEVEL:
            effects["shop_free_purchase"] = 0.20
    elif normal_effect_id == "daily_bonus":
        effects["daily_bonus"] = normal_value
        if effects["passive_level"] >= PET_PASSIVE_MAX_LEVEL:
            effects["daily_double"] = 0.25
            effects["streak_rescue"] = 1

    # Haunted passives remain separate and are consumed only by Haunted Exploration.
    haunted_passive = pet.get("passive", {}) if pet.get("haunted_location") else {}
    haunted_value = get_passive_value({"passive": haunted_passive, "level": pet["level"], "fusion_level": pet.get("fusion_level", 0)}, pet["level"]) if haunted_passive else 0.0
    haunted_effect_id = haunted_passive.get("id")
    if haunted_effect_id == "haunted_sanity_reduction":
        effects["haunted_sanity_reduction"] = haunted_value
    elif haunted_effect_id == "haunted_ingredient_bonus":
        effects["haunted_ingredient_bonus"] = haunted_value
    elif haunted_effect_id == "haunted_reward_bonus":
        effects["haunted_reward_bonus"] = haunted_value
    elif haunted_effect_id == "haunted_negative_protection":
        effects["haunted_negative_protection"] = haunted_value
    elif haunted_effect_id == "haunted_discovery_bonus":
        effects["haunted_discovery_bonus"] = haunted_value
    elif haunted_effect_id == "haunted_stage_reduction":
        effects["haunted_stage_reduction"] = haunted_value
    elif haunted_effect_id == "haunted_malo":
        effects["haunted_malo"] = haunted_value
    elif normal_effect_id == "haunted_sanity_reduction":
        effects["haunted_sanity_reduction"] = value
    elif normal_effect_id == "haunted_ingredient_bonus":
        effects["haunted_ingredient_bonus"] = value
    elif normal_effect_id == "haunted_reward_bonus":
        effects["haunted_reward_bonus"] = value
    elif normal_effect_id == "haunted_negative_protection":
        effects["haunted_negative_protection"] = value
    elif normal_effect_id == "haunted_discovery_bonus":
        effects["haunted_discovery_bonus"] = value
    elif normal_effect_id == "haunted_stage_reduction":
        effects["haunted_stage_reduction"] = value
    elif normal_effect_id == "haunted_malo":
        effects["haunted_malo"] = value

    effects["haunted_location"] = pet.get("haunted_location")
    return effects


def roll_normal_exploration_pet_xp() -> int:
    """Roll Pet XP awarded by a normal exploration."""
    return random.randint(
        NORMAL_EXPLORATION_PET_XP_MIN,
        NORMAL_EXPLORATION_PET_XP_MAX,
    )


def roll_haunted_exploration_pet_xp() -> int:
    """Roll the base Pet XP awarded by a Haunted Exploration."""
    return random.randint(
        HAUNTED_EXPLORATION_PET_XP_MIN,
        HAUNTED_EXPLORATION_PET_XP_MAX,
    )


async def get_haunted_exploration_pet_xp(
    db,
    user_id: int,
    location_id: str,
):
    """Roll Haunted Exploration Pet XP and apply the matching-pet bonus."""
    amount = roll_haunted_exploration_pet_xp()
    home_bonus = 0

    pet = await get_active_pet(db, user_id)
    if pet and pet.get("haunted_location") == location_id:
        home_bonus = HAUNTED_HOME_PET_XP_BONUS

    return amount + home_bonus, home_bonus


async def add_pet_xp(db, user_id: int, amount: int):
    """Add pet XP to the active pet and handle multiple level-ups."""
    if amount <= 0:
        return None

    pet = await get_active_pet(db, user_id)
    if not pet:
        return None

    old_level = pet["level"]
    new_level = old_level
    new_xp = pet["xp"] + amount

    while new_xp >= xp_needed_for_next_level(new_level):
        new_xp -= xp_needed_for_next_level(new_level)
        new_level += 1

    await db.execute(
        """
        UPDATE pets
        SET level = ?, xp = ?
        WHERE pet_id = ?
        """,
        (new_level, new_xp, pet["pet_id"]),
    )

    return {
        "old_level": old_level,
        "new_level": new_level,
        "xp_added": amount,
        "leveled_up": new_level > old_level,
        "passive_level": passive_level_for_pet(new_level),
        "xp": new_xp,
        "xp_needed": xp_needed_for_next_level(new_level),
    }

