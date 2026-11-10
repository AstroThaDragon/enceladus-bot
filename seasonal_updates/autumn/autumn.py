"""
Autumn seasonal event data for Enceladus.

Seasonal Autumn event definitions integrated with Enceladus seasonal systems.
Before production use, compare this with the live bot's schemas and restore
original item descriptions, emojis, sell prices, and any additional settings.
The pet passive level format below is a planning format and may need adapting
to the bot's existing passive implementation.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

AUTUMN_TIMEZONE = ZoneInfo("America/New_York")
AUTUMN_START = (11, 1)
AUTUMN_END = (12, 1)


def is_autumn_active(now: datetime | None = None) -> bool:
    """Autumn runs November 1 at 12:00 AM through December 1 at 12:00 AM Eastern (end exclusive)."""
    if now is None:
        now = datetime.now(AUTUMN_TIMEZONE)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=AUTUMN_TIMEZONE)
    else:
        now = now.astimezone(AUTUMN_TIMEZONE)
    return (now.month, now.day) >= AUTUMN_START and (now.month, now.day) < AUTUMN_END


# Original names are preserved from planning. Exact original descriptions,
# emojis, and sell prices were not available; prices are None placeholders.
def _item(name, emoji, item_type, description):
    return {
        "name": name,
        "emoji": emoji,
        "type": item_type,
        "description": description,
        "sell_price": {"ingredient": 35, "treat": 160, "pet_treat": 100, "egg": 0}.get(item_type, 0),
    }


AUTUMN_ITEMS = {
    # Foods and drinks
    "pumpkin_spice_latte": _item("Pumpkin Spice Latte", "☕", "treat", "A cozy pumpkin-spiced autumn latte."),
    "caramel_apple_cider": _item("Caramel Apple Cider", "🍎", "treat", "Warm apple cider with a caramel finish."),
    "pumpkin_frappuccino": _item("Pumpkin Frappuccino", "🥤", "treat", "A chilled pumpkin-flavored seasonal drink."),
    "chai_latte": _item("Chai Latte", "🫖", "treat", "A comforting latte brewed with chai spices."),
    "pumpkin_pie": _item("Pumpkin Pie", "🥧", "treat", "A classic autumn pie with pumpkin filling."),
    "autumn_harvest_bisque": _item("Autumn Harvest Bisque", "🍲", "treat", "A warm, hearty autumn bisque."),
    "warm_chili": _item("Warm Chili", "🌶️", "treat", "A hearty bowl of warming chili."),
    "pumpkin_bread": _item("Pumpkin Bread", "🍞", "treat", "Soft pumpkin bread with warm spices."),
    "maple_pecan_pie": _item("Maple Pecan Pie", "🥧", "treat", "A sweet pie with pecans and maple."),
    "cinnamon_roll": _item("Cinnamon Roll", "🍥", "treat", "A soft roll swirled with cinnamon."),
    "apple_cider_donut": _item("Apple Cider Donut", "🍩", "treat", "An autumn donut with apple cider flavor."),
    "pumpkin_cookies": _item("Pumpkin Cookies", "🍪", "treat", "A batch of soft pumpkin cookies."),

    # Pet treats
    "pumpkin_treats": _item("Pumpkin Treats", "🎃", "pet_treat", "A tasty pumpkin treat for your companion."),
    "apple_chew_sticks": _item("Apple Chew Sticks", "🍎", "pet_treat", "Crunchy apple-flavored chew sticks."),
    "cinnamon_bone_biscuits": _item("Cinnamon Bone Biscuits", "🦴", "pet_treat", "Bone-shaped biscuits with cinnamon."),
    "leaf_shaped_cookies": _item("Leaf-Shaped Cookies", "🍁", "pet_treat", "Autumn leaf-shaped cookies for pets."),

    # Ingredients
    "pumpkin_puree": _item("Pumpkin Puree", "🎃", "ingredient", "Smooth pumpkin puree for seasonal recipes."),
    "apple_cider": _item("Apple Cider", "🍎", "ingredient", "Fresh apple cider for autumn recipes."),
    "cinnamon_sticks": _item("Cinnamon Sticks", "🪵", "ingredient", "Fragrant cinnamon sticks."),
    "maple_syrup": _item("Maple Syrup", "🍁", "ingredient", "Sweet maple syrup for autumn recipes."),
    "chai_tea_leaves": _item("Chai Tea Leaves", "🍃", "ingredient", "Aromatic leaves for brewing chai."),
    "nutmeg": _item("Nutmeg", "🌰", "ingredient", "A warm spice used in seasonal baking."),
    "cup_and_saucer_set": _item("Cup and Saucer Set", "🍵", "ingredient", "A little set for serving warm drinks."),
    "single_straw": _item("Single Straw", "🥤", "ingredient", "A straw for enjoying a seasonal cold drink."),
    "whipped_cream": _item("Whipped Cream", "🍦", "ingredient", "A fluffy topping for drinks and desserts."),
    "acorns": _item("Acorns", "🌰", "ingredient", "A handful of freshly gathered woodland acorns."),
    "coffee_beans": _item("Coffee Beans", "☕", "ingredient", "Freshly roasted coffee beans for Autumn drinks."),
    "flour": _item("Flour", "🌾", "ingredient", "A versatile baking staple for Autumn pastries."),
    "pecans": _item("Pecans", "🥜", "ingredient", "Fresh pecans for rich autumn desserts."),
    "beans": _item("Beans", "🫘", "ingredient", "Hearty beans for a warming pot of autumn chili."),

    # Eggs
    "golden_egg": _item("Golden Egg", "💛", "egg", "A rare golden egg said to hold an extraordinary companion."),
    "leaf_patterned_egg": _item("Leaf-Patterned Egg", "🍂", "egg", "An egg decorated with autumn leaf patterns."),
    "acorn_egg": _item("Acorn Egg", "🌰", "egg", "A woodland egg with an acorn-inspired design."),
}

AUTUMN_TREATS = {k: v for k, v in AUTUMN_ITEMS.items() if v["type"] == "treat"}
AUTUMN_PET_TREATS = {k: v for k, v in AUTUMN_ITEMS.items() if v["type"] == "pet_treat"}
AUTUMN_PET_TREAT_RECIPES = {
    "pumpkin_treats": {"pumpkin_puree": {"quantity": 1, "collection": "autumn"}},
    "apple_chew_sticks": {"apple_cider": {"quantity": 1, "collection": "autumn"}},
    "cinnamon_bone_biscuits": {"cinnamon_sticks": {"quantity": 1, "collection": "autumn"}},
    "leaf_shaped_cookies": {"maple_syrup": {"quantity": 1, "collection": "autumn"}},
}
for _treat_id, _ingredients in AUTUMN_PET_TREAT_RECIPES.items():
    AUTUMN_PET_TREATS[_treat_id]["ingredients"] = _ingredients
    AUTUMN_PET_TREATS[_treat_id]["findable_from"] = "autumn_harvest"
AUTUMN_INGREDIENTS = {k: v for k, v in AUTUMN_ITEMS.items() if v["type"] == "ingredient"}
AUTUMN_EGGS = {k: v for k, v in AUTUMN_ITEMS.items() if v["type"] == "egg"}


# Pet passive levels use dictionaries because several passives affect more
# than one statistic. Percentages are bonus amounts, not guaranteed chances.
# Verify/adapt this schema to the live pet system before integration.
AUTUMN_PETS = {
    "golden_fox": {
        "name": "Golden Fox", "emoji": "🦊",
        "description": "A fox with golden-tipped fur and bright amber eyes.",
        "egg": "golden_egg", "rarity": "common",
        "passive": {"id": "golden_paws", "name": "Golden Paws",
                    "description": "Finds extra Stardust while scavenging.",
                    "levels": [{"stardust_bonus": x} for x in (0.05, 0.12, 0.18, 0.24, 0.30)]},
    },
    "emberwing": {
        "name": "Emberwing", "emoji": "🔥",
        "description": "A small phoenix with fiery orange and golden feathers.",
        "egg": "golden_egg", "rarity": "uncommon",
        "passive": {"id": "blazing_spirit", "name": "Blazing Spirit",
                    "description": "Increases the chance of discovering rare materials while mining.",
                    "levels": [{"mining_rare_discovery_bonus": x} for x in (0.03, 0.06, 0.09, 0.12, 0.15)]},
    },
    "sunlit_stag": {
        "name": "Sunlit Stag", "emoji": "🦌",
        "description": "A graceful stag with softly glowing golden antlers.",
        "egg": "golden_egg", "rarity": "rare",
        "passive": {"id": "fortunes_favor", "name": "Fortune's Favor",
                    "description": "Grants additional XP and improves the odds of rarer fortunes.",
                    "levels": [{"xp_bonus": x, "fortune_rarity_weight_bonus": y}
                               for x, y in zip((.03, .06, .09, .12, .15), (.02, .04, .06, .08, .10))]},
    },
    "aurorion": {
        "name": "Aurorion", "emoji": "🐉",
        "description": "A golden celestial dragon with shimmering scales.",
        "egg": "golden_egg", "rarity": "legendary",
        "passive": {"id": "celestial_abundance", "name": "Celestial Abundance",
                    "description": "Grants a small bonus to Stardust, XP, and material rewards from scavenging and mining.",
                    "levels": [{"stardust_bonus": x, "xp_bonus": x, "material_quantity_bonus": x}
                               for x in (.02, .03, .04, .05, .07)]},
    },
    "red_squirrel": {
        "name": "Red Squirrel", "emoji": "🐿️",
        "description": "A fluffy red squirrel with a big bushy tail.",
        "egg": "leaf_patterned_egg", "rarity": "common",
        "passive": {"id": "acorn_collector", "name": "Acorn Collector",
                    "description": "Has a chance to discover additional Autumn ingredients while scavenging.",
                    "levels": [{"autumn_ingredient_discovery_bonus": x} for x in (.03, .06, .09, .12, .15)]},
    },
    "woodland_doe": {
        "name": "Woodland Doe", "emoji": "🦌",
        "description": "A gentle young doe with a chestnut coat, cream spots, and tiny autumn leaves near her ears.",
        "egg": "leaf_patterned_egg", "rarity": "uncommon",
        "passive": {"id": "natures_grace", "name": "Nature's Grace",
                    "description": "Increases Stardust rewards and improves the chance of discovering Autumn ingredients.",
                    "levels": [{"stardust_bonus": x, "autumn_ingredient_discovery_bonus": y}
                               for x, y in zip((.03, .06, .09, .12, .15), (.03, .05, .07, .09, .12))]},
    },
    "autumn_red_panda": {
        "name": "Autumn Red Panda", "emoji": "🐼",
        "description": "A fluffy red panda with russet-colored fur.",
        "egg": "leaf_patterned_egg", "rarity": "rare",
        "passive": {"id": "rustling_leaves", "name": "Rustling Leaves",
                    "description": "Improves the chance of discovering rare materials while scavenging.",
                    "levels": [{"scavenging_rare_discovery_bonus": x} for x in (.03, .06, .09, .12, .15)]},
    },
    "verdant_guardian": {
        "name": "Verdant Guardian", "emoji": "🌿",
        "description": "A magical forest spirit resembling a deer, adorned with autumn foliage.",
        "egg": "leaf_patterned_egg", "rarity": "legendary",
        "passive": {"id": "spirit_of_the_forest", "name": "Spirit of the Forest",
                    "description": "Improves rare-material discovery while scavenging and increases the quantity of rare materials found.",
                    "levels": [{"scavenging_rare_discovery_bonus": x, "rare_material_extra_quantity": q}
                               for x, q in zip((.03, .06, .09, .12, .15), (1, 1, 1, 2, 2))]},
    },
    "chipmunk": {
        "name": "Chipmunk", "emoji": "🐿️",
        "description": "A cheeky little woodland critter with chubby cheeks, a fluffy tail, and a love for acorns.",
        "egg": "acorn_egg", "rarity": "common",
        "passive": {"id": "pocket_sized_forager", "name": "Pocket-Sized Forager",
                    "description": "Finds bonus Stardust and Autumn ingredients, with a special knack for Acorns.",
                    "levels": [{"stardust_bonus": s, "autumn_ingredient_discovery_bonus": i, "acorn_discovery_bonus": a}
                               for s, i, a in zip((.02, .04, .06, .08, .10), (.03, .05, .07, .09, .12), (.10, .20, .30, .40, .50))]},
    },
    "woodland_buck": {
        "name": "Woodland Buck", "emoji": "🦌",
        "description": "A curious young buck with small budding antlers, warm brown fur, and a tiny acorn-shaped marking.",
        "egg": "acorn_egg", "rarity": "uncommon",
        "passive": {"id": "autumns_fortune", "name": "Autumn's Fortune",
                    "description": "Improves Autumn ingredient discovery and occasionally grants an additional scavenging reward.",
                    "levels": [{"autumn_ingredient_discovery_bonus": i, "extra_scavenge_reward_chance": r}
                               for i, r in zip((.03, .05, .07, .09, .12), (.02, .03, .04, .05, .06))]},
    },
    "tawny_owl": {
        "name": "Tawny Owl", "emoji": "🦉",
        "description": "A round little owl with cinnamon-colored feathers, big dark eyes, and a cream-colored belly.",
        "egg": "acorn_egg", "rarity": "rare",
        "passive": {"id": "autumn_watcher", "name": "Autumn Watcher",
                    "description": "Improves rare-material and Autumn ingredient discovery while scavenging and grants bonus Stardust.",
                    "levels": [{"scavenging_rare_discovery_bonus": r, "autumn_ingredient_discovery_bonus": i, "stardust_bonus": s}
                               for r, i, s in zip((.03, .06, .09, .12, .15), (.03, .05, .07, .09, .12), (.02, .04, .06, .08, .10))]},
    },
    "acorn_spirit": {
        "name": "Acorn Spirit", "emoji": "✨",
        "description": "A magical woodland creature with an acorn-shaped crown and glowing nature magic.",
        "egg": "acorn_egg", "rarity": "legendary",
        "passive": {"id": "acorns_blessing", "name": "Acorn's Blessing",
                    "description": "Greatly improves Acorn and Autumn ingredient discovery, increases scavenging rewards, and grants bonus XP.",
                    "levels": [{"autumn_ingredient_discovery_bonus": i, "acorn_discovery_bonus": a, "scavenging_reward_bonus": r, "xp_bonus": x}
                               for i, a, r, x in zip((.05, .08, .11, .14, .18), (.15, .25, .35, .45, .60), (.02, .04, .06, .08, .10), (.02, .03, .04, .05, .07))]},
    },
}

AUTUMN_PET_POOLS = {
    "golden_egg": ["golden_fox", "emberwing", "sunlit_stag", "aurorion"],
    "leaf_patterned_egg": ["red_squirrel", "woodland_doe", "autumn_red_panda", "verdant_guardian"],
    "acorn_egg": ["chipmunk", "woodland_buck", "tawny_owl", "acorn_spirit"],
}

# Independent egg rolls during Autumn scavenging, parallel to Halloween's
# normal-egg reduction and separate seasonal egg drops.
AUTUMN_SCAVENGE_EGG_CHANCE = 0.12
AUTUMN_SCAVENGE_NORMAL_EGG_CHANCE = 0.025


# Design decisions awaiting connection to the existing drop/reward code:
# - All three eggs are regular scavenging drops.
# - Golden Egg also drops from mining, at the same chance as scavenging.
# - Acorn Egg is common; Leaf-Patterned Egg is less common; Golden Egg is very rare.
# - Exact egg drop percentages have not yet been selected.
# - No special Autumn exploration encounter.
# - Thanksgiving content is part of Autumn, not a separate event activation.
# - Seasonal ingredient passive bonuses work only while Autumn is active.
# - Passive bonuses stack additively, subject to a cap to be chosen after code review.
# - Verdant Guardian's +1/+2 applies only after a rare material successfully drops.

# Explicit cooking metadata; seasonal finished foods remain inventory items.
# Autumn recipes use a deliberately compact ingredient pool. Pantry staples
# (butter, salt, sugar, and eggs) are not inventory items and are not consumed.
# Ingredient quantities are consumed for each successful craft.
AUTUMN_RECIPES = {
    "pumpkin_spice_latte": {
        "name": "Pumpkin Spice Latte", "emoji": "☕", "category": "drink",
        "sell_price": 190,
        "ingredients": {
            "pumpkin_puree": {"quantity": 1, "collection": "autumn"},
            "coffee_beans": {"quantity": 2, "collection": "autumn"},
            "cinnamon_sticks": {"quantity": 1, "collection": "autumn"},
            "whipped_cream": {"quantity": 1, "collection": "autumn"},
        },
    },
    "caramel_apple_cider": {
        "name": "Caramel Apple Cider", "emoji": "🍎", "category": "drink",
        "sell_price": 170,
        "ingredients": {
            "apple_cider": {"quantity": 2, "collection": "autumn"},
            "maple_syrup": {"quantity": 1, "collection": "autumn"},
            "cinnamon_sticks": {"quantity": 1, "collection": "autumn"},
        },
    },
    "pumpkin_frappuccino": {
        "name": "Pumpkin Frappuccino", "emoji": "🥤", "category": "drink",
        "sell_price": 200,
        "ingredients": {
            "pumpkin_puree": {"quantity": 1, "collection": "autumn"},
            "coffee_beans": {"quantity": 1, "collection": "autumn"},
            "whipped_cream": {"quantity": 1, "collection": "autumn"},
            "single_straw": {"quantity": 1, "collection": "autumn"},
        },
    },
    "chai_latte": {
        "name": "Chai Latte", "emoji": "🫖", "category": "drink",
        "sell_price": 180,
        "ingredients": {
            "chai_tea_leaves": {"quantity": 2, "collection": "autumn"},
            "nutmeg": {"quantity": 1, "collection": "autumn"},
            "whipped_cream": {"quantity": 1, "collection": "autumn"},
        },
    },
    "pumpkin_pie": {
        "name": "Pumpkin Pie", "emoji": "🥧", "category": "food",
        "sweet": True, "dessert": True, "sell_price": 240,
        "ingredients": {
            "pumpkin_puree": {"quantity": 2, "collection": "autumn"},
            "nutmeg": {"quantity": 1, "collection": "autumn"},
            "cinnamon_sticks": {"quantity": 1, "collection": "autumn"},
            "flour": {"quantity": 2, "collection": "autumn"},
            "sugar": {"quantity": 1, "collection": "pantry"},
            "eggs": {"quantity": 1, "collection": "pantry"},
        },
    },
    "autumn_harvest_bisque": {
        "name": "Autumn Harvest Bisque", "emoji": "🍲", "category": "food",
        "sell_price": 210,
        "ingredients": {
            "pumpkin_puree": {"quantity": 2, "collection": "autumn"},
            "acorns": {"quantity": 1, "collection": "autumn"},
            "nutmeg": {"quantity": 1, "collection": "autumn"},
            "whipped_cream": {"quantity": 1, "collection": "autumn"},
        },
    },
    "warm_chili": {
        "name": "Warm Chili", "emoji": "🌶️", "category": "food",
        "sell_price": 220,
        "ingredients": {
            "beans": {"quantity": 2, "collection": "autumn"},
            "pumpkin_puree": {"quantity": 1, "collection": "autumn"},
            "nutmeg": {"quantity": 1, "collection": "autumn"},
        },
    },
    "pumpkin_bread": {
        "name": "Pumpkin Bread", "emoji": "🍞", "category": "food",
        "sweet": True, "dessert": True, "sell_price": 220,
        "ingredients": {
            "pumpkin_puree": {"quantity": 1, "collection": "autumn"},
            "flour": {"quantity": 2, "collection": "autumn"},
            "cinnamon_sticks": {"quantity": 1, "collection": "autumn"},
            "maple_syrup": {"quantity": 1, "collection": "autumn"},
        },
    },
    "maple_pecan_pie": {
        "name": "Maple Pecan Pie", "emoji": "🥧", "category": "food",
        "sweet": True, "dessert": True, "sell_price": 260,
        "ingredients": {
            "maple_syrup": {"quantity": 2, "collection": "autumn"},
            "pecans": {"quantity": 2, "collection": "autumn"},
            "flour": {"quantity": 2, "collection": "autumn"},
            "nutmeg": {"quantity": 1, "collection": "autumn"},
            "eggs": {"quantity": 1, "collection": "pantry"},
        },
    },
    "cinnamon_roll": {
        "name": "Cinnamon Roll", "emoji": "🍥", "category": "food",
        "sweet": True, "dessert": True, "sell_price": 190,
        "ingredients": {
            "flour": {"quantity": 2, "collection": "autumn"},
            "cinnamon_sticks": {"quantity": 2, "collection": "autumn"},
            "maple_syrup": {"quantity": 1, "collection": "autumn"},
        },
    },
    "apple_cider_donut": {
        "name": "Apple Cider Donut", "emoji": "🍩", "category": "food",
        "sweet": True, "dessert": True, "sell_price": 190,
        "ingredients": {
            "apple_cider": {"quantity": 1, "collection": "autumn"},
            "flour": {"quantity": 2, "collection": "autumn"},
            "cinnamon_sticks": {"quantity": 1, "collection": "autumn"},
            "maple_syrup": {"quantity": 1, "collection": "autumn"},
        },
    },
    "pumpkin_cookies": {
        "name": "Pumpkin Cookies", "emoji": "🍪", "category": "food",
        "sweet": True, "dessert": True, "sell_price": 180,
        "ingredients": {
            "pumpkin_puree": {"quantity": 1, "collection": "autumn"},
            "flour": {"quantity": 2, "collection": "autumn"},
            "cinnamon_sticks": {"quantity": 1, "collection": "autumn"},
            "nutmeg": {"quantity": 1, "collection": "autumn"},
        },
    },
}

# Prices are in Stardust and are intentionally lower for raw ingredients than
# finished dishes, while remaining below the cost of their gathered inputs.
AUTUMN_SELL_PRICES = {
    "pumpkin_puree": 35, "apple_cider": 35, "cinnamon_sticks": 30,
    "maple_syrup": 40, "chai_tea_leaves": 30, "nutmeg": 30,
    "cup_and_saucer_set": 15, "single_straw": 10, "whipped_cream": 30,
    "acorns": 20, "coffee_beans": 40, "flour": 25, "pecans": 40, "beans": 25,
    "pumpkin_treats": 100, "apple_chew_sticks": 100,
    "cinnamon_bone_biscuits": 100, "leaf_shaped_cookies": 100,
    "golden_egg": 0, "leaf_patterned_egg": 0, "acorn_egg": 0,
    **{recipe_id: recipe["sell_price"] for recipe_id, recipe in AUTUMN_RECIPES.items()},
}
for _item_id, _price in AUTUMN_SELL_PRICES.items():
    if _item_id in AUTUMN_ITEMS:
        AUTUMN_ITEMS[_item_id]["sell_price"] = _price
    elif _item_id in AUTUMN_RECIPES:
        AUTUMN_ITEMS[_item_id]["sell_price"] = _price

# Keep ingredient discovery metadata in sync with the recipe book.
for _ingredient_id, _ingredient in AUTUMN_INGREDIENTS.items():
    _ingredient["used_in"] = [
        recipe_id for recipe_id, recipe in AUTUMN_RECIPES.items()
        if _ingredient_id in recipe["ingredients"]
    ]

AUTUMN_EXPLORATION_REWARDS = {"uses_per_cycle": 20, "refill_hours": 12, "egg_chance": 0.05, "treat_find_chance": 0.02}
