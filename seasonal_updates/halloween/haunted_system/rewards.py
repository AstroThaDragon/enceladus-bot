"""Existing Haunted completion reward rolls, kept separate from story content."""

import random

from inventory import add_inventory_item, ITEM_REGISTRY
from collectibles import record_collectible
from seasonal_updates.halloween import halloween as halloween_season

from .constants import (
    HAUNTED_COLLECTIBLE_CHANCES,
    HAUNTED_INGREDIENT_OVERFLOW_VALUES,
    HAUNTED_INGREDIENT_POOLS,
    HAUNTED_INGREDIENT_TYPE_RANGES,
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
    from economy_system.data import OVERFLOW_SELL_RATE

    rarity = roll_haunted_rarity()
    ranges = HAUNTED_REWARD_RANGES[rarity]
    stardust = int(random.randint(*ranges["stardust"]) * (1 + max(0.0, float(reward_bonus))))
    candy = random.randint(*ranges["candy"])
    ingredient_amount = random.randint(*ranges["ingredients"])
    ingredient_amount = max(1, int(ingredient_amount * (1 + max(0.0, float(ingredient_bonus)))))

    # Roll multiple material TYPES from the selected location only. Higher
    # rarities can produce more types, while the total material quantity still
    # comes from the existing rarity range above.
    ingredient_pool = list(dict.fromkeys(HAUNTED_INGREDIENT_POOLS.get(location_id, [])))
    ingredient_rewards = []

    if ingredient_pool:
        min_types, max_types = HAUNTED_INGREDIENT_TYPE_RANGES.get(rarity, (1, 1))
        type_count = min(len(ingredient_pool), random.randint(min_types, max_types))

        # Sample without replacement so a multi-material reward actually gives
        # different materials when the location has enough unique options.
        selected_ingredients = random.sample(ingredient_pool, type_count)

        # Distribute the total rolled quantity across the selected materials,
        # guaranteeing at least one of each.
        remaining_amount = ingredient_amount
        for index, ingredient_id in enumerate(selected_ingredients):
            remaining_types = type_count - index - 1
            if remaining_types:
                amount = random.randint(1, remaining_amount - remaining_types)
            else:
                amount = remaining_amount

            remaining_amount -= amount
            ingredient_rewards.append({
                "ingredient_id": ingredient_id,
                "requested": amount,
            })

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
    ingredient_overflow_stardust = 0

    for reward in ingredient_rewards:
        ingredient_id = reward["ingredient_id"]
        requested = reward["requested"]
        ingredient_type = ITEM_REGISTRY.get(ingredient_id, {}).get("type", "Haunted Ingredient")

        added, _, _ = await add_inventory_item(
            db, user_id, ingredient_id, ingredient_type, requested
        )
        overflow = requested - added
        overflow_value = HAUNTED_INGREDIENT_OVERFLOW_VALUES.get(ingredient_id, 10)
        overflow_stardust = overflow * max(
            1, int(overflow_value * OVERFLOW_SELL_RATE)
        )

        added_ingredient += added
        ingredient_overflow += overflow
        ingredient_overflow_stardust += overflow_stardust

        reward.update({
            "name": ITEM_REGISTRY.get(ingredient_id, {}).get("name", ingredient_id),
            "emoji": ITEM_REGISTRY.get(ingredient_id, {}).get("emoji", "🧪"),
            "added": added,
            "overflow": overflow,
            "overflow_stardust": overflow_stardust,
        })

    if ingredient_overflow_stardust:
        await db.execute(
            "UPDATE users SET stardust = COALESCE(stardust, 0) + ? WHERE user_id = ?",
            (ingredient_overflow_stardust, user_id),
        )

    # Keep the legacy single-material fields populated with the first material
    # so existing callers remain compatible until their display is upgraded.
    primary_ingredient = ingredient_rewards[0] if ingredient_rewards else None
    ingredient_id = primary_ingredient["ingredient_id"] if primary_ingredient else None
    ingredient_amount = primary_ingredient["requested"] if primary_ingredient else 0
    ingredient_overflow = primary_ingredient["overflow"] if primary_ingredient else 0
    ingredient_overflow_stardust = sum(
        reward["overflow_stardust"] for reward in ingredient_rewards
    )

    collectible = None
    collectible_added = False
    collectible_first_discovery = False
    collectible_chance = min(
        1.0,
        HAUNTED_COLLECTIBLE_CHANCES[rarity] + max(0.0, float(collectible_bonus)),
    )
    if random.random() < collectible_chance:
        collectible = random.choice(halloween_season.HALLOWEEN_SPACE_JUNK)
        collectible_id, collectible_name, collectible_emoji, collectible_desc, collectible_value, collectible_candy = collectible
        added_collectible, _, _ = await add_inventory_item(db, user_id, collectible_id, "space_junk", 1)
        if added_collectible:
            collectible_first_discovery = await record_collectible(
                db, bot, user_id, collectible_id, "Halloween"
            )
            collectible_added = True
        else:
            await db.execute(
                "UPDATE users SET stardust = COALESCE(stardust, 0) + ? WHERE user_id = ?",
                (max(1, int(collectible_value * OVERFLOW_SELL_RATE)), user_id),
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
        "ingredients": ingredient_rewards,
        "ingredient_count": len(ingredient_rewards),
        "collectible": collectible if collectible_added else None,
        "collectible_found": collectible_added,
        "collectible_first_discovery": collectible_first_discovery,
    }
