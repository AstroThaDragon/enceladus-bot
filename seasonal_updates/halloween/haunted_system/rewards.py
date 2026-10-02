"""Existing Haunted completion reward rolls, kept separate from story content."""

import random

from inventory import add_inventory_item, ITEM_REGISTRY
from collectibles import record_collectible
from seasonal_updates.halloween import halloween as halloween_season

from .constants import (
    HAUNTED_COLLECTIBLE_CHANCES,
    HAUNTED_INGREDIENT_OVERFLOW_VALUES,
    HAUNTED_INGREDIENT_POOLS,
    HAUNTED_RARITY_EMOJIS,
    HAUNTED_RARITY_LABELS,
    HAUNTED_RARITY_WEIGHTS,
    HAUNTED_REWARD_RANGES,
)


def roll_haunted_rarity():
    rarities = list(HAUNTED_RARITY_WEIGHTS)
    weights = list(HAUNTED_RARITY_WEIGHTS.values())
    return random.choices(rarities, weights=weights, k=1)[0]


def _weighted_choice(values):
    return random.choice(values) if values else None


async def grant_haunted_completion_rewards(
    db,
    bot,
    user_id,
    location_id,
    collectible_bonus=0.0,
    ingredient_bonus=0.0,
    reward_bonus=0.0,
):
    """Grant the existing random completion rewards.

    Location materials intentionally remain random drops from the location's
    pool; the authored story never determines which material is awarded.
    """
    rarity = roll_haunted_rarity()
    ranges = HAUNTED_REWARD_RANGES[rarity]
    stardust = int(random.randint(*ranges["stardust"]) * (1 + max(0.0, float(reward_bonus))))
    candy = random.randint(*ranges["candy"])
    ingredient_amount = random.randint(*ranges["ingredients"])
    ingredient_amount = max(1, int(ingredient_amount * (1 + max(0.0, float(ingredient_bonus)))))
    ingredient_id = _weighted_choice(HAUNTED_INGREDIENT_POOLS.get(location_id, []))

    await db.execute(
        "UPDATE users SET stardust = COALESCE(stardust, 0) + ? WHERE user_id = ?",
        (stardust, user_id),
    )

    added_candy, _, _ = await add_inventory_item(db, user_id, "halloween_candy", "consumable", candy)
    candy_overflow = candy - added_candy
    overflow_stardust = candy_overflow * 2
    if overflow_stardust:
        await db.execute(
            "UPDATE users SET stardust = COALESCE(stardust, 0) + ? WHERE user_id = ?",
            (overflow_stardust, user_id),
        )

    added_ingredient = 0
    ingredient_overflow = 0
    if ingredient_id:
        ingredient_type = ITEM_REGISTRY.get(ingredient_id, {}).get("type", "Haunted Ingredient")
        added_ingredient, _, _ = await add_inventory_item(
            db, user_id, ingredient_id, ingredient_type, ingredient_amount
        )
        ingredient_overflow = ingredient_amount - added_ingredient
        ingredient_overflow_stardust = ingredient_overflow * HAUNTED_INGREDIENT_OVERFLOW_VALUES.get(ingredient_id, 10)
        if ingredient_overflow_stardust:
            await db.execute(
                "UPDATE users SET stardust = COALESCE(stardust, 0) + ? WHERE user_id = ?",
                (ingredient_overflow_stardust, user_id),
            )
    else:
        ingredient_overflow_stardust = 0

    collectible = None
    collectible_added = False
    collectible_chance = min(
        1.0,
        HAUNTED_COLLECTIBLE_CHANCES[rarity] + max(0.0, float(collectible_bonus)),
    )
    if random.random() < collectible_chance:
        collectible = random.choice(halloween_season.HALLOWEEN_SPACE_JUNK)
        collectible_id, collectible_name, collectible_emoji, collectible_desc, collectible_value, collectible_candy = collectible
        added_collectible, _, _ = await add_inventory_item(db, user_id, collectible_id, "space_junk", 1)
        if added_collectible:
            await record_collectible(db, bot, user_id, collectible_id, "Halloween")
            collectible_added = True
        else:
            await db.execute(
                "UPDATE users SET stardust = COALESCE(stardust, 0) + ? WHERE user_id = ?",
                (collectible_value, user_id),
            )

    await db.commit()
    return {
        "rarity": rarity,
        "rarity_label": HAUNTED_RARITY_LABELS[rarity],
        "rarity_emoji": HAUNTED_RARITY_EMOJIS[rarity],
        "stardust": stardust,
        "candy": added_candy,
        "candy_requested": candy,
        "candy_overflow": candy_overflow,
        "overflow_stardust": overflow_stardust,
        "ingredient_id": ingredient_id,
        "ingredient_name": ITEM_REGISTRY.get(ingredient_id or "", {}).get("name", ingredient_id or "Unknown"),
        "ingredient_emoji": ITEM_REGISTRY.get(ingredient_id or "", {}).get("emoji", "🧪"),
        "ingredient_added": added_ingredient,
        "ingredient_requested": ingredient_amount,
        "ingredient_overflow": ingredient_overflow,
        "ingredient_overflow_stardust": ingredient_overflow_stardust,
        "collectible": collectible if collectible_added else None,
        "collectible_found": collectible_added,
    }
