"""
Enceladus — Thanksgiving Seasonal Collection
=============================================

Seasonal content definitions consumed by the Autumn/Thanksgiving runtime cog.

Intended location:
    seasonal_updates/autumn/thanksgiving.py

This file collects the Thanksgiving design decisions made during planning.
Before integrating it into Enceladus, compare its structures and IDs with the
existing Autumn, recipe, ingredient, pet, exploration, inventory, and passive
systems. Adapt schemas rather than assuming these dictionaries are drop-in
compatible with the live bot.

Event window:
    Shares the existing Autumn event activation window:
    November 1 at 12:00 AM through December 1 at 12:00 AM Eastern (end exclusive).
    Thanksgiving is NOT a separately activated event.

Important implementation notes:
- Existing /explore should offer Autumn Harvest and Thanksgiving Gathering
  while the Autumn event is active.
- Each exploration activity has its own 20-use counter, replenished every
  12 hours (two predictable refill cycles per day).
- Thanksgiving Gathering: 2–3 different ingredient types per successful run;
  each dropped type gives 1–3 units.
- Seasonal egg chance: 5% after successful seasonal exploration;
  10% after successful seasonal cooking.
- Pet treats can be crafted easily OR found during the corresponding seasonal
  scavenging activity. Treat actions do not roll for eggs.
- Exact drop weights, reward hooks, cooldown storage, pet-passive schema,
  pantry-staple handling, and inventory caps must be verified against the
  current codebase before implementation.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Event relationship and exploration configuration
# ---------------------------------------------------------------------------

EVENT_CONFIG = {
    "event_id": "autumn",
    "activation": {
        "start_month": 11,
        "start_day": 1,
        "end_month": 12,
        "end_day": 1,
        "timezone": "America/New_York",
        "inclusive": False,
    },
    "separate_thanksgiving_activation": False,
    "exploration_command": "explore",
}

EXPLORATION_ACTIVITIES = {
    "autumn_harvest": {
        "display_name": "Autumn Harvest",
        "reward_collection": "autumn",
        "uses_per_cycle": 20,
        "refill_interval_hours": 12,
        "separate_usage_counter": True,
    },
    "thanksgiving_gathering": {
        "display_name": "Thanksgiving Gathering",
        "reward_collection": "thanksgiving",
        "uses_per_cycle": 20,
        "refill_interval_hours": 12,
        "separate_usage_counter": True,
    },
}

# Two 12-hour refill cycles means up to 40 uses per activity in 24 hours.
# This is a design target; match the live bot's reset/cooldown architecture.


# ---------------------------------------------------------------------------
# Ingredients
# ---------------------------------------------------------------------------

# Rarity is intentionally gentle: most ingredients are Common, with a small
# Uncommon group. There are no Rare or Legendary Thanksgiving ingredients.
THANKSGIVING_INGREDIENTS = {
    "turkey_breast": {
        "name": "Turkey Breast",
        "emoji": "🦃",
        "rarity": "uncommon",
        "used_in": ["roasted_thanksgiving_turkey", "turkey_tenders"],
    },
    "potatoes": {
        "name": "Potatoes",
        "emoji": "🥔",
        "rarity": "common",
        "used_in": ["creamy_mashed_potatoes"],
    },
    "bread_cubes": {
        "name": "Bread Cubes",
        "emoji": "🍞",
        "rarity": "common",
        "used_in": ["herb_stuffing", "cranberry_paw_crunchies"],
    },
    "poultry_herb_blend": {
        "name": "Poultry Herb Blend",
        "emoji": "🌿",
        "rarity": "common",
        "used_in": [
            "roasted_thanksgiving_turkey",
            "herb_stuffing",
            "seasoned_roasted_carrots",
            "turkey_tenders",
        ],
    },
    "sweet_potatoes": {
        "name": "Sweet Potatoes",
        "emoji": "🍠",
        "rarity": "common",
        "used_in": ["sweet_potato_casserole", "pumpkin_harvest_bites"],
    },
    "mini_marshmallows": {
        "name": "Mini Marshmallows",
        "emoji": "🍡",
        "rarity": "uncommon",
        "used_in": ["sweet_potato_casserole"],
    },
    "cranberries": {
        "name": "Cranberries",
        "emoji": "🍒",
        "rarity": "common",
        "used_in": [
            "cranberry_sauce",
            "cranberry_spritzer",
            "cranberry_paw_crunchies",
        ],
    },
    "cream_cheese": {
        "name": "Cream Cheese",
        "emoji": "🧀",
        "rarity": "uncommon",
        "used_in": ["pumpkin_cheesecake"],
    },
    "fresh_corn": {
        "name": "Fresh Corn",
        "emoji": "🌽",
        "rarity": "common",
        "used_in": ["corn_on_the_cob"],
    },
    "fresh_carrots": {
        "name": "Fresh Carrots",
        "emoji": "🥕",
        "rarity": "common",
        "used_in": ["seasoned_roasted_carrots"],
    },
    "sparkling_water": {
        "name": "Sparkling Water",
        "emoji": "🫧",
        "rarity": "common",
        "used_in": ["cranberry_spritzer"],
    },
    "chocolate": {
        "name": "Chocolate",
        "emoji": "🍫",
        "rarity": "uncommon",
        "used_in": ["pumpkin_spice_hot_chocolate"],
    },
    "milk": {
        "name": "Milk",
        "emoji": "🥛",
        "rarity": "common",
        "used_in": [
            "creamy_mashed_potatoes",
            "herb_stuffing",
            "pumpkin_spice_hot_chocolate",
            "maple_cinnamon_latte",
        ],
    },
    "cheese": {"name": "Cheese", "emoji": "🧀", "rarity": "common", "used_in": ["thanksgiving_tower_pizza"]},
    "tomato_sauce": {"name": "Tomato Sauce", "emoji": "🍅", "rarity": "common", "used_in": ["thanksgiving_tower_pizza"]},
}

# Existing Autumn ingredients reused by Thanksgiving recipes/treats.
AUTUMN_INGREDIENTS_USED = {
    "pumpkin_puree": ["pumpkin_cheesecake", "pumpkin_spice_hot_chocolate",
                      "pumpkin_harvest_bites"],
    "maple_syrup": ["sweet_potato_casserole", "cranberry_sauce",
                    "cranberry_spritzer", "maple_cinnamon_latte"],
    "cinnamon_sticks": ["pumpkin_cheesecake", "pumpkin_spice_hot_chocolate",
                        "maple_cinnamon_latte"],
    "whipped_cream": ["pumpkin_cheesecake", "pumpkin_spice_hot_chocolate"],
    "coffee_beans": ["maple_cinnamon_latte"],
}

# Shared pantry staples discussed as non-scavengable recipe requirements.
# Verify whether the live cooking system supports pantry staples without
# inventory item IDs. These are not Thanksgiving Gathering drops.
PANTRY_STAPLES = ["butter", "salt", "sugar", "eggs"]


# ---------------------------------------------------------------------------
# Thanksgiving recipes
# Ingredient quantities are consumed per successful recipe.
# Collection names identify whether an ingredient is Thanksgiving, Autumn,
# or a shared pantry staple.
# ---------------------------------------------------------------------------

THANKSGIVING_RECIPES = {
    "roasted_thanksgiving_turkey": {
        "name": "Roasted Thanksgiving Turkey",
        "emoji": "🦃",
        "category": "food",
        "ingredients": {
            "turkey_breast": {"quantity": 3, "collection": "thanksgiving"},
            "poultry_herb_blend": {"quantity": 2, "collection": "thanksgiving"},
            "butter": {"quantity": 1, "collection": "pantry"},
        },
    },
    "creamy_mashed_potatoes": {
        "name": "Creamy Mashed Potatoes",
        "emoji": "🥔",
        "category": "food",
        "ingredients": {
            "potatoes": {"quantity": 3, "collection": "thanksgiving"},
            "milk": {"quantity": 1, "collection": "thanksgiving"},
            "butter": {"quantity": 1, "collection": "pantry"},
        },
    },
    "herb_stuffing": {
        "name": "Herb Stuffing",
        "emoji": "🍞",
        "category": "food",
        "ingredients": {
            "bread_cubes": {"quantity": 3, "collection": "thanksgiving"},
            "poultry_herb_blend": {"quantity": 1, "collection": "thanksgiving"},
            "milk": {"quantity": 1, "collection": "thanksgiving"},
        },
    },
    "sweet_potato_casserole": {
        "name": "Sweet Potato Casserole",
        "emoji": "🍠",
        "category": "food", "sweet": True, "dessert": True,
        "ingredients": {
            "sweet_potatoes": {"quantity": 3, "collection": "thanksgiving"},
            "mini_marshmallows": {"quantity": 2, "collection": "thanksgiving"},
            "maple_syrup": {"quantity": 1, "collection": "autumn"},
        },
    },
    "cranberry_sauce": {
        "name": "Cranberry Sauce",
        "emoji": "🍒",
        "category": "food", "sweet": True,
        "ingredients": {
            "cranberries": {"quantity": 3, "collection": "thanksgiving"},
            "maple_syrup": {"quantity": 1, "collection": "autumn"},
        },
    },
    "corn_on_the_cob": {
        "name": "Corn on the Cob",
        "emoji": "🌽",
        "category": "food",
        "ingredients": {
            "fresh_corn": {"quantity": 2, "collection": "thanksgiving"},
            "butter": {"quantity": 1, "collection": "pantry"},
        },
    },
    "seasoned_roasted_carrots": {
        "name": "Seasoned Roasted Carrots",
        "emoji": "🥕",
        "category": "food",
        "ingredients": {
            "fresh_carrots": {"quantity": 3, "collection": "thanksgiving"},
            "poultry_herb_blend": {"quantity": 1, "collection": "thanksgiving"},
            "butter": {"quantity": 1, "collection": "pantry"},
        },
    },
    "pumpkin_cheesecake": {
        "name": "Pumpkin Cheesecake",
        "emoji": "🍰",
        "category": "food", "sweet": True, "dessert": True,
        "ingredients": {
            "cream_cheese": {"quantity": 2, "collection": "thanksgiving"},
            "pumpkin_puree": {"quantity": 2, "collection": "autumn"},
            "whipped_cream": {"quantity": 1, "collection": "autumn"},
            "cinnamon_sticks": {"quantity": 1, "collection": "autumn"},
        },
    },
    "cranberry_spritzer": {
        "name": "Cranberry Spritzer",
        "emoji": "🍒",
        "category": "drink",
        "ingredients": {
            "cranberries": {"quantity": 2, "collection": "thanksgiving"},
            "sparkling_water": {"quantity": 2, "collection": "thanksgiving"},
            "maple_syrup": {"quantity": 1, "collection": "autumn"},
        },
    },
    "pumpkin_spice_hot_chocolate": {
        "name": "Pumpkin Spice Hot Chocolate",
        "emoji": "🎃",
        "category": "drink",
        "ingredients": {
            "chocolate": {"quantity": 2, "collection": "thanksgiving"},
            "milk": {"quantity": 2, "collection": "thanksgiving"},
            "pumpkin_puree": {"quantity": 1, "collection": "autumn"},
            "cinnamon_sticks": {"quantity": 1, "collection": "autumn"},
            "whipped_cream": {"quantity": 1, "collection": "autumn"},
        },
    },
    "maple_cinnamon_latte": {
        "name": "Maple Cinnamon Latte",
        "emoji": "☕",
        "category": "drink",
        "ingredients": {
            "coffee_beans": {"quantity": 2, "collection": "autumn"},
            "milk": {"quantity": 2, "collection": "thanksgiving"},
            "maple_syrup": {"quantity": 1, "collection": "autumn"},
            "cinnamon_sticks": {"quantity": 1, "collection": "autumn"},
        },
    },
    "thanksgiving_tower_pizza": {
        "name": "Thanksgiving Tower Pizza", "emoji": "🍕", "category": "food",
        "ingredients": {
            "bread_cubes": {"quantity": 3, "collection": "thanksgiving"},
            "turkey_breast": {"quantity": 2, "collection": "thanksgiving"},
            "cranberries": {"quantity": 1, "collection": "thanksgiving"},
            "poultry_herb_blend": {"quantity": 1, "collection": "thanksgiving"},
            "cheese": {"quantity": 2, "collection": "thanksgiving"},
            "tomato_sauce": {"quantity": 1, "collection": "thanksgiving"},
        },
        "secret_unlock": {"first_craft_pet": "peppino", "subsequent_pet": "peddito", "subsequent_chance": 0.10},
    },
}


# ---------------------------------------------------------------------------
# Pet treats
# All seasonal pet treats (the four existing Autumn treats plus these three)
# should be easy to craft OR occasionally found during the matching activity.
# Treat crafting/discovery does not trigger an egg roll.
# ---------------------------------------------------------------------------

THANKSGIVING_PET_TREATS = {
    "turkey_tenders": {
        "name": "Turkey Tenders",
        "emoji": "🦃",
        "ingredients": {
            "turkey_breast": {"quantity": 1, "collection": "thanksgiving"},
            "poultry_herb_blend": {"quantity": 1, "collection": "thanksgiving"},
        },
        "findable_from": "thanksgiving_gathering",
    },
    "pumpkin_harvest_bites": {
        "name": "Pumpkin Harvest Bites",
        "emoji": "🎃",
        "ingredients": {
            "sweet_potatoes": {"quantity": 1, "collection": "thanksgiving"},
            "pumpkin_puree": {"quantity": 1, "collection": "autumn"},
        },
        "findable_from": "thanksgiving_gathering",
    },
    "cranberry_paw_crunchies": {
        "name": "Cranberry Paw Crunchies",
        "emoji": "🐾",
        "description": "Cranberry-flavored crunchy biscuits shaped like little paws.",
        "ingredients": {
            "cranberries": {"quantity": 1, "collection": "thanksgiving"},
            "bread_cubes": {"quantity": 1, "collection": "thanksgiving"},
        },
        "findable_from": "thanksgiving_gathering",
    },
}

SEASONAL_PET_TREAT_RULES = {
    "craftable": True,
    "easy_to_craft": True,
    "findable_during_matching_seasonal_exploration": True,
    "finished_treat_discovery_chance": 0.02,  # Proposed 2% per successful run.
    "treat_discovery_selection": "uniform",
    "treat_actions_trigger_egg_roll": False,
    "finding_finished_treat_consumes_ingredients": False,
}


# ---------------------------------------------------------------------------
# Thanksgiving eggs and pet roster
# ---------------------------------------------------------------------------

THANKSGIVING_EGGS = {
    "harvest_egg": {
        "name": "Harvest Egg",
        "emoji": "🌾",
        "visual_direction": (
            "Warm golden-brown and cream, decorated with wheat, autumn leaves, "
            "and acorns."
        ),
        "pet_pool": [
            "little_gobbler",
            "cinnamon_roll_snail",
            "pumpkin_spiced_latte",
        ],
    },
    "feast_egg": {
        "name": "Feast Egg",
        "emoji": "🥧",
        "visual_direction": (
            "Cranberry red, pumpkin orange, and golden brown, with "
            "Thanksgiving/pastry-inspired decorations."
        ),
        "pet_pool": [
            "cranberry_chick",
            "pumpkin_pie_fox",
            "caramel_apple",
        ],
    },
}

THANKSGIVING_SCAVENGE_EGG_CHANCE = 0.09
THANKSGIVING_SCAVENGE_EGG_IDS = ("harvest_egg", "feast_egg")

THANKSGIVING_PETS = {
    "little_gobbler": {
        "name": "Little Gobbler",
        "emoji": "🦃",
        "rarity": "common",
        "egg": "harvest_egg",
        "description": "A tiny fluffy turkey with a big personality who gobbles at everything.",
        "passive": {
            "id": "happy_gobbling",
            "name": "Happy Gobbling",
            "description": (
                "Chance to discover an additional Thanksgiving ingredient "
                "during Thanksgiving Gathering."
            ),
            "levels": [0.03, 0.05, 0.07, 0.09, 0.12],
        },
    },
    "cinnamon_roll_snail": {
        "name": "Cinnamon Roll Snail",
        "emoji": "🐌",
        "rarity": "rare",
        "egg": "harvest_egg",
        "description": (
            "A sleepy, sweet snail with a cinnamon-roll shell and icing drizzle; "
            "almost always hungry."
        ),
        "passive": {
            "id": "sweet_tooth",
            "name": "Sweet Tooth",
            "description": (
                "Chance to produce an additional serving when successfully "
                "cooking a sweet food recipe from Autumn or Thanksgiving."
            ),
            "levels": [0.03, 0.06, 0.09, 0.12, 0.15],
        },
    },
    "pumpkin_spiced_latte": {
        "name": "Pumpkin Spiced Latte",
        "emoji": "☕",
        "rarity": "legendary",
        "egg": "harvest_egg",
        "description": (
            "An animated latte cup with whipped cream, cinnamon decorations, "
            "and a pumpkin charm."
        ),
        "passive": {
            "id": "baristas_blessing",
            "name": "Barista's Blessing",
            "description": (
                "Chance to discover an additional ingredient used in Autumn "
                "or Thanksgiving drinks while scavenging during the Autumn event."
            ),
            "levels": [0.05, 0.08, 0.11, 0.14, 0.18],
            "event_required": "autumn",
        },
    },
    "cranberry_chick": {
        "name": "Cranberry Chick",
        "emoji": "🐥",
        "rarity": "common",
        "egg": "feast_egg",
        "description": (
            "A round, fluffy cranberry-red little bird with tiny wings."
        ),
        "passive": {
            "id": "berry_picking",
            "name": "Berry Picking",
            "description": (
                "Chance to discover an additional Thanksgiving food ingredient "
                "during Thanksgiving Gathering; excludes drink-only ingredients."
            ),
            "levels": [0.02, 0.04, 0.06, 0.08, 0.10],
        },
    },
    "pumpkin_pie_fox": {
        "name": "Pumpkin Pie Fox",
        "emoji": "🦊",
        "rarity": "rare",
        "egg": "feast_egg",
        "description": (
            "A fluffy orange fox with cream-colored markings and a "
            "whipped-cream-like tuft."
        ),
        "passive": {
            "id": "sweet_rewards",
            "name": "Sweet Rewards",
            "description": (
                "Chance to receive one additional ingredient from the recipe "
                "ingredient list when successfully cooking a Thanksgiving dessert."
            ),
            "levels": [0.03, 0.05, 0.07, 0.09, 0.12],
        },
    },
    "caramel_apple": {
        "name": "Caramel Apple",
        "emoji": "🍎",
        "rarity": "legendary",
        "egg": "feast_egg",
        "description": (
            "A living caramel apple with glossy golden coating, a red apple "
            "underneath, and a green leaf."
        ),
        "passive": {
            "id": "sticky_fingers",
            "name": "Sticky Fingers",
            "description": (
                "Improves the chance of discovering Uncommon Thanksgiving "
                "ingredients during Thanksgiving Gathering."
            ),
            "levels": [0.03, 0.06, 0.09, 0.12, 0.15],
        },
    },
    "peppino": {"name": "Peppino", "emoji": "🍕", "rarity": "secret", "egg": None,
        "description": "A frantic pizza chef who somehow made it into the Thanksgiving collection.",
        "passive": {"id": "seasonal_none", "name": "No passive", "description": "A special collection companion.", "levels": [0,0,0,0,0]}},
    "peddito": {"name": "Peddito", "emoji": "👻", "rarity": "secret", "egg": None,
        "description": "A ghostly, eyeless Peppino lookalike in a pink hat and tank top, blue shirt, and red pants.",
        "passive": {"id": "seasonal_none", "name": "No passive", "description": "A special collection companion.", "levels": [0,0,0,0,0]}},
}

PET_PASSIVE_IMPLEMENTATION_RULES = {
    "equipped_pets_only": True,
    "respect_inventory_caps": True,
    "bonus_ingredient_amount": 1,
    "bonus_drops_can_trigger_themselves": False,
    "stacking": "VERIFY against existing bot rules before implementation",
    "equip_limits": "VERIFY against existing bot rules before implementation",
    "passive_schema": "VERIFY against existing pet schema before implementation",
}


# ---------------------------------------------------------------------------
# Seasonal egg reward rules — applies to BOTH Autumn and Thanksgiving eggs
# ---------------------------------------------------------------------------

SEASONAL_EGG_REWARDS = {
    "successful_exploration_chance": 0.05,
    "successful_cooking_chance": 0.10,
    "thanksgiving_egg_selection": {
        "harvest_egg": 0.50,
        "feast_egg": 0.50,
    },
    "autumn_egg_selection": "random from the three existing Autumn eggs",
    "duplicate_eggs_allowed": True,
    "one_roll_per_successful_cooking_action": True,
    "failed_actions_trigger_roll": False,
    "opening_menu_triggers_roll": False,
    "pet_treat_actions_trigger_roll": False,
    "egg_roll_independent_of_other_rewards": True,
}


# ---------------------------------------------------------------------------
# Thanksgiving Gathering reward configuration
# ---------------------------------------------------------------------------

THANKSGIVING_GATHERING_REWARDS = {
    "ingredient_pool": list(THANKSGIVING_INGREDIENTS),
    "ingredient_types_per_successful_run": {
        "minimum": 2,
        "maximum": 3,
    },
    "quantity_per_dropped_ingredient_type": {
        "minimum": 1,
        "maximum": 3,
    },
    "multiple_ingredient_types_can_drop": True,
    "rarity_behavior": {
        "common": "frequent",
        "uncommon": "less frequent but reasonably obtainable",
        "rare": "not used",
        "legendary": "not used",
    },
    "finished_pet_treat_chance": 0.02,
    "finished_pet_treat_pool": list(THANKSGIVING_PET_TREATS),
    "egg_chance": SEASONAL_EGG_REWARDS["successful_exploration_chance"],
    "egg_pool": list(THANKSGIVING_EGGS),
    "reward_categories_are_independent": True,
    "exact_ingredient_weights": {"common": 0.88, "uncommon": 0.12},
}


# ---------------------------------------------------------------------------
# Implementation checklist
# ---------------------------------------------------------------------------

IMPLEMENTATION_CHECKLIST = [
    "Inspect Autumn event activation and confirm November 1 at 12:00 AM through December 1 at 12:00 AM Eastern (end exclusive).",
    "Inspect existing /explore and add Autumn Harvest and Thanksgiving Gathering choices.",
    "Implement separate 20-use counters for each activity with 12-hour full refills.",
    "Inspect ingredient, recipe, cooking, crafting, and inventory schemas before mapping IDs.",
    "Ensure egg rolls happen only after successful seasonal exploration or cooking, once per action.",
    "Add Thanksgiving Gathering ingredient and finished-treat rewards; tune exact weights against current drop logic and inventory caps.",
    "Add three Thanksgiving treat recipes and treat discovery; align four Autumn treats with the same craft-or-find rules.",
    "Inspect pet passive schema, equip limits, stacking behavior, and reward hooks before implementing six passives.",
    "Ensure Harvest Egg and Feast Egg contain only their three Thanksgiving pets; leave Autumn egg pools intact.",
    "Verify pantry-staple handling for butter, salt, sugar, and eggs.",
    "Test event boundaries, timezone behavior, cooldown refills, reward independence, inventory caps, duplicate eggs, and passive triggers.",
    "Connect this module through the existing seasonal package structure.",
]

# End of planning reference.


THANKSGIVING_EXPLORATION_REWARDS = {"uses_per_cycle": 20, "refill_hours": 12, "egg_chance": 0.05, "treat_find_chance": 0.02}


# Stardust sale values for the Thanksgiving collection. Pantry staples are
# intentionally excluded because they are not inventory items.
THANKSGIVING_SELL_PRICES = {
    "turkey_breast": 45, "potatoes": 25, "bread_cubes": 20,
    "poultry_herb_blend": 30, "sweet_potatoes": 30,
    "mini_marshmallows": 35, "cranberries": 30, "cream_cheese": 40,
    "fresh_corn": 25, "fresh_carrots": 25, "sparkling_water": 20,
    "chocolate": 40, "milk": 20, "cheese": 30, "tomato_sauce": 25,
    "turkey_tenders": 100, "pumpkin_harvest_bites": 100,
    "cranberry_paw_crunchies": 100,
    "harvest_egg": 0, "feast_egg": 0,
    "roasted_thanksgiving_turkey": 300,
    "creamy_mashed_potatoes": 150, "herb_stuffing": 150,
    "sweet_potato_casserole": 190, "cranberry_sauce": 140,
    "corn_on_the_cob": 120, "seasoned_roasted_carrots": 130,
    "pumpkin_cheesecake": 260, "cranberry_spritzer": 170,
    "pumpkin_spice_hot_chocolate": 210, "maple_cinnamon_latte": 210,
    "thanksgiving_tower_pizza": 350,
}
