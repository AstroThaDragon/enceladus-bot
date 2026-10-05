from emojis import EMOJIS
from seasonal_updates.halloween.halloween import get_collectibles as get_halloween_collectibles
from seasonal_updates.halloween.halloween import HALLOWEEN_SPACE_JUNK

DEFAULT_VAULT_CAPACITY = 250_000

BULK_SELL_OPTIONS = {
    "all_junk": "🗑️ Sell All Space Junk",
    "all_materials": "🔧 Sell All Ores & Materials",
    "all_halloween": "🎃 Sell All Halloween Collectibles",
}

HALLOWEEN_COLLECTIBLE_IDS = {
    item_id for item_id, *_ in get_halloween_collectibles()
}

HALLOWEEN_SPACE_JUNK_IDS = {
    item_id for item_id, *_ in HALLOWEEN_SPACE_JUNK
}

SALVAGE_POOLS = {
    "electronics": [("wiring", 50), ("circuit_board", 30), ("copper_ore", 20)],
    "mechanical": [("scrap_metal", 45), ("nuts_bolts", 35), ("iron_ore", 20)],
    "structural": [("scrap_metal", 45), ("iron_ore", 35), ("aluminum_ore", 20)],
    "mineral": [("iron_ore", 50), ("copper_ore", 30), ("aluminum_ore", 18), ("titanium_chunk", 2)],
    "miscellaneous": [("scrap_metal", 50), ("glue", 30), ("nuts_bolts", 20)],
    "valuable": [("circuit_board", 35), ("wiring", 30), ("copper_ore", 25), ("aluminum_ore", 10)],
}

SALVAGE_CATEGORIES = {
    # Electronics / powered equipment
    "floppy_disk": "electronics",
    "tape_deck": "electronics",
    "alien_artifact": "electronics",
    "tangled_cables": "electronics",
    "broken_laser": "electronics",
    "haunted_circuit": "electronics",
    "big_red_button": "electronics",
    "broken_clock": "electronics",

    # Mechanical hardware / tools
    "rusty_gear": "mechanical",
    "space_boot": "mechanical",
    "tinted_visor": "mechanical",
    "rusty_wrench": "mechanical",
    "warp_mug": "mechanical",

    # Structural / mineral-heavy wreckage
    "meteorite": "mineral",
    "pet_rock": "mineral",
    "alien_fossil": "mineral",

    # Valuable / specialized oddities
    "cosmic_coin": "valuable",
    "screaming_crystal": "valuable",
    "golden_spatula": "valuable",
    "antique_compass": "valuable",
    "perplexing_painting": "valuable",

    # Everything else is mostly generic salvageable material.
    "space_pizza": "miscellaneous",
    "rubber_duck": "miscellaneous",
    "holo_poster": "miscellaneous",
    "lost_logbook": "miscellaneous",
    "left_sock": "miscellaneous",
    "space_pudding": "miscellaneous",
    "moon_cheese": "miscellaneous",
    "parking_ticket": "miscellaneous",
    "floating_plant": "miscellaneous",
    "purring_lint": "miscellaneous",
    "space_taco": "miscellaneous",
    "cosmic_banana": "miscellaneous",
}

SALVAGE_MATERIAL_NAMES = {
    "iron_ore": (EMOJIS.get("iron_ore", "⛏️"), "Iron Ore"),
    "copper_ore": (EMOJIS.get("copper_ore", "🟠"), "Copper Ore"),
    "titanium_chunk": (EMOJIS.get("titanium_chunk", "⛏️"), "Titanium Ore Chunk"),
    "aluminum_ore": (EMOJIS.get("aluminum_ore", "⬜"), "Aluminum Ore"),
    "circuit_board": (EMOJIS.get("circuit_board", "🟩"), "Circuit Board"),
    "glue": (EMOJIS.get("glue", "🧴"), "Industrial Glue"),
    "scrap_metal": (EMOJIS.get("scrap_metal", "🔩"), "Scrap Metal"),
    "nuts_bolts": (EMOJIS.get("nuts_bolts", "🔧"), "Nuts & Bolts"),
    "wiring": (EMOJIS.get("wiring", "🧵"), "Wiring"),
}

SALVAGE_OVERFLOW_VALUES = {
    "iron_ore": 3, "copper_ore": 5, "titanium_chunk": 15, "aluminum_ore": 4,
    "circuit_board": 20, "glue": 6, "scrap_metal": 3, "nuts_bolts": 4, "wiring": 5,
}

NORMAL_SELL_ALL_MATERIAL_IDS = {
    "titanium_chunk",
    "iron_ore",
    "copper_ore",
    "aluminum_ore",
    "circuit_board",
    "glue",
    "scrap_metal",
    "nuts_bolts",
    "wiring",
}

SELLABLE_ITEM_IDS = {'cosmic_insurance', 'drone_battery', 'drone_power_cell', 'drone_quantum_battery', 'fate_anchor', 'fuel_refill', 'fuel_stabilizer', 'full_revive', 'hazard_shield', 'heavy_wrench', 'laser_charge_cell', 'laser_power_cell', 'lucky_scanner', 'makeshift_medkit', 'medkit', 'nanite_patch', 'ore_magnet', 'plasma_cutter', 'prototype_drill_bit', 'revive', 'revive_kit', 'station_rations', 'stick', 'stop_sign', 'wooden_shield', 'wooden_spoon', 'wooden_sword',
                     }

SHOP_CATEGORY_INFO = {
    "healing": ("❤️", "Healing", "Medical supplies and revival items."),
    "recharge": ("🔋", "Recharge", "Mining laser and scavenging drone power."),
    "upgrades": ("🛠️", "Upgrades", "Permanent equipment and station expansions."),
    "pet_items": ("🐾", "Pet Items", "Items for your station companion."),
    "special": ("✨", "Special", "Rare and unusual station items."),
    "lottery": ("🎟️", "Lottery", "Monthly Stardust lottery tickets."),
    "backgrounds": ("🖼️", "Backgrounds", "Profile background vouchers."),
    "__search__": ("🔎", "Search Results", "Search across the available shop items."),
    "__rotating__": ("🔄️", "Daily Offers", "Today's rotating station offers."),
    "sell_all": ("🧹", "Sell All", "Bulk-sale actions for eligible inventory."),
    "space_junk": ("🗑️", "Space Junk", "Sell normal space junk for Stardust."),
    "materials": ("🔧", "Ores & Materials", "Sell ores and normal crafting materials."),
    "collectibles": ("🎃", "Collectibles", "Sell discovered collectible items."),
    "halloween": ("👻", "Halloween", "Sell eligible seasonal items."),
    "consumables": ("🧪", "Consumables", "Usable supplies for exploration and station equipment."),
    "upgrade_kits": ("🛠️", "Upgrade Kits", "Actual crafted kits used for permanent upgrades."),
    "defense_weapons": ("🛡️", "Defense Weapons", "Items that can help protect you from scavenging hazards."),
}

SHOP_BUY_CATEGORY_ITEMS = {
    "healing": ["nanite_patch", "medkit", "revive", "full_revive"],
    "recharge": [
        "laser_charge_cell", "laser_power_cell", "fuel_refill",
        "drone_battery", "drone_power_cell", "drone_quantum_battery",
    ],
    "upgrades": [
        "incubator_2", "incubator_3", "quantum_coil", "astral_lens", "mutation_catalyst", "analysis_module", "vault_expansion",
        "fuel_stabilizer", "hazard_shield", "lucky_scanner", "prototype_drill_bit",
    ],
    "pet_items": ["pet_snack"],
    "special": ["time_crystal", "astral_essence"],
    "lottery": ["lottery_ticket"],
    "backgrounds": ["neon_grid", "deep_void", "solaris_ring"],
}

SHOP_BUY_CATEGORY_CHOICES = [
    ("❤️ Healing", "healing"),
    ("🔋 Recharge", "recharge"),
    ("🛠️ Upgrades", "upgrades"),
    ("🐾 Pet Items", "pet_items"),
    ("✨ Special", "special"),
    ("🎟️ Lottery", "lottery"),
    ("🖼️ Backgrounds", "backgrounds"),
]

SHOP_SELL_CATEGORY_CHOICES = [
    ("🧹 Sell All", "sell_all"),
    ("🗑️ Space Junk", "space_junk"),
    ("🔧 Ores & Materials", "materials"),
    ("❤️ Healing", "healing"),
    ("🧪 Consumables", "consumables"),
    ("🛠️ Upgrade Kits", "upgrade_kits"),
    ("🛡️ Defense Weapons", "defense_weapons"),
    ("🎃 Collectibles", "collectibles"),
    ("👻 Halloween", "halloween"),
    ("✨ Special Items", "special"),
]

SELL_ITEM_CATEGORY_IDS = {
    "healing": {
        "nanite_patch", "medkit", "revive", "revive_kit", "full_revive",
        "makeshift_medkit", "station_rations",
    },
    "consumables": {
        "laser_charge_cell", "laser_power_cell", "fuel_refill",
        "drone_battery", "drone_power_cell", "drone_quantum_battery",
        # Temporary utility items are consumables, not upgrade kits.
        "fuel_stabilizer", "hazard_shield", "lucky_scanner", "ore_magnet",
        "prototype_drill_bit", "cosmic_insurance", "fate_anchor",
    },
    "upgrade_kits": set(),  # Populated dynamically from crafting recipes below.
    "defense_weapons": {
        "stop_sign", "stick", "wooden_sword", "wooden_shield",
        "wooden_spoon", "heavy_wrench", "plasma_cutter",
    },
    "special": {
        "time_crystal", "astral_essence",
    },
}

def get_upgrade_kit_ids():
    """Return the actual craftable upgrade-kit item IDs."""
    try:
        from crafting import RECIPES
    except ImportError:
        return set()

    return {
        recipe["result"]
        for recipe in RECIPES.values()
        if recipe.get("result", "").startswith((
            "reinforced_laser_parts_",
            "drone_upgrade_kit_",
            "salvage_rig_kit_",
        ))
        or recipe.get("result") == "nanite_retrofit_kit"
    }

SHOP_ITEMS = {
            "nanite_patch": {
                "name": f"{EMOJIS.get('nanite_patch', '🩹')} Nanite Stim-Patch",
                "cost": 400,
                "type": "heal",
                "heal_amount": 35,
                "desc": "Quickly knits minor planetary surface wounds. Restores +35 HP."
            },
            "medkit": {
                "name": f"{EMOJIS.get('medkit', '🧰')} Field Trauma Medkit",
                "cost": 750,
                "type": "heal",
                "heal_amount": 100,
                "desc": "Standard planetary survival trauma kit. Restores +100 HP."
            },
            "revive": {
                "name": f"{EMOJIS.get('revive', '⚕️')} Revival Kit",
                "cost": 350,
                "type": "revive",
                "desc": "Immediately revives an unconscious explorer at 35% HP."
            },
            "full_revive": {
                "name": f"{EMOJIS.get('full_revive', '⚕️')} Emergency Full Revival",
                "cost": 800,
                "type": "revive",
                "desc": "Immediately revives an unconscious explorer at full HP."
            },
            "laser_charge_cell": {
                "name": f"{EMOJIS.get('laser_charge_cell', '🔋')} Laser Charge Cell",
                "cost": 400,
                "type": "consumable",
                "desc": "Restores 2 mining laser charges."
            },
            "laser_power_cell": {
                "name": f"{EMOJIS.get('laser_power_cell', '⚡')} Laser Power Cell",
                "cost": 750,
                "type": "consumable",
                "desc": "Restores 5 mining laser charges."
            },
            "fuel_refill": {
                "name": f"{EMOJIS.get('fuel_refill', '⚛️')} Laser Quantum Cell",
                "cost": 1200,
                "type": "consumable",
                "desc": "Instantly refills your mining laser to 10/10 charges."
            },
            "drone_battery": {
                "name": f"{EMOJIS.get('drone_battery', '🔋')} Drone Battery Pack",
                "cost": 400,
                "type": "consumable",
                "desc": "Restores 2 scavenge charges."
            },
            "drone_power_cell": {
                "name": f"{EMOJIS.get('drone_power_cell', '⚡')} Drone Power Cell",
                "cost": 750,
                "type": "consumable",
                "desc": "Restores 5 scavenge charges."
            },
            "drone_quantum_battery": {
                "name": f"{EMOJIS.get('drone_quantum_battery', '⚛️')} Drone Quantum Battery",
                "cost": 1200,
                "type": "consumable",
                "desc": "Instantly refills your scavenging drone to 10/10 charges."
            },
            "pet_snack": {
                "name": f"{EMOJIS.get('pet_snack', '🍪')} Pet Treat",
                "cost": 200,
                "type": "consumable",
                "desc": "A tasty treat for your station pet. Gives your active pet +25 Pet XP."
            },
            "time_crystal": {
                "name": f"{EMOJIS.get('time_crystal', '💎')} Dilated Time Crystal",
                "cost": 3500,
                "type": "special",
                "desc": "Bends time backwards to restore a fortune streak missed yesterday (Max 2 uses/month)."
            },
            "astral_essence": {
                "name": "✨ Astral Essence",
                "cost": 5000,
                "type": "special",
                "desc": "A concentrated fragment of stellar energy used to fuse duplicate pets and hunt for rare pet variants."
            },
            "quantum_coil": {
                "name": "🌀 Quantum Coil",
                "cost": 10000,
                "type": "special",
                "desc": "A precision quantum component used to improve incubator incubation speed."
            },
            "astral_lens": {
                "name": "🔭 Astral Lens",
                "cost": 12500,
                "type": "special",
                "desc": "A finely tuned optical component used to improve incubator variant detection."
            },
            "mutation_catalyst": {
                "name": "🧬 Mutation Catalyst",
                "cost": 15000,
                "type": "special",
                "desc": "A volatile catalyst used to improve variant quality and mutation luck."
            },
            "analysis_module": {
                "name": "🔬 Analysis Module",
                "cost": 7500,
                "type": "special",
                "desc": "A specialized analysis unit that reveals increasingly detailed information about incubating eggs."
            },
            "neon_grid": {
                "name": "🌆 Background Voucher: Neon Grid",
                "cost": 4000,
                "type": "background_voucher",
                "desc": "Unlocks the 'Cyberpunk Neon Grid City' background photo for your /profile card."
            },
            "deep_void": {
                "name": "🌌 Background Voucher: Deep Void",
                "cost": 4500,
                "type": "background_voucher",
                "desc": "Unlocks the 'Deep Void' background photo for your /profile card."
            },
            "solaris_ring": {
                "name": "💫 Background Voucher: Solaris Ring",
                "cost": 5000,
                "type": "background_voucher",
                "desc": "Unlocks the 'Solaris Ring' background photo for your /profile card."
            },
            "fuel_stabilizer": {
                "name": f"{EMOJIS.get('fuel_stabilizer', '🛢️')} Fuel Stabilizer", "cost": 800, "type": "consumable",
                "desc": "Makes your next mining run cost no fuel charge."
            },
            "hazard_shield": {
                "name": f"{EMOJIS.get('hazard_shield', '🛡️')} Hazard Shield", "cost": 1000, "type": "consumable",
                "desc": "Blocks the next scavenging hazard."
            },
            "lucky_scanner": {
                "name": f"{EMOJIS.get('lucky_scanner', '📡')} Deep-Space Scanner", "cost": 700, "type": "consumable",
                "desc": "Improves rare-find odds on your next scavenging run."
            },
            "prototype_drill_bit": {
                "name": f"{EMOJIS.get('prototype_drill_bit', '⚙️')} Prototype Drill Bit", "cost": 1000, "type": "consumable",
                "desc": "Boosts Stardust from your next mining run."
            },
            "incubator_2": {
                "name": "🥚 Incubator Tube II",
                "cost": 50_000,
                "type": "station_upgrade",
                "desc": "Unlocks a second pet egg incubator tube."
            },
            "incubator_3": {
                "name": "🥚 Incubator Tube III",
                "cost": 125_000,
                "type": "station_upgrade",
                "desc": "Unlocks a third pet egg incubator tube."
            },
            "vault_expansion": {
                "name": "🔐 Vault Expansion",
                "cost": 150_000,
                "type": "station_upgrade",
                "desc": "Raises your Stardust vault capacity to the 500,000 Stardust maximum."
            },
        }

JUNK_PRICES = {
            "space_pizza": 30,
            "floppy_disk": 50,
            "meteorite": 85,
            "rubber_duck": 50,
            "rusty_gear": 15,
            "tape_deck": 45,
            "alien_artifact": 80,
            "space_boot": 25,
            "cosmic_coin": 120,
            "holo_poster": 35,
            "broken_laser": 20,
            "lost_logbook": 20,
            "left_sock": 10,
            "warp_mug": 30,
            "space_pudding": 10,
            "tangled_cables": 25,
            "screaming_crystal": 100,
            "moon_cheese": 60,
            "golden_spatula": 120,
            "parking_ticket": 10,
            "floating_plant": 70,
            "tinted_visor": 25,
            "purring_lint": 30,
            "pet_rock": 40,
            "haunted_circuit": 120,
            "space_taco": 35,
            "rusty_wrench": 25,
            "alien_fossil": 75,
            "big_red_button": 10,
            "antique_compass": 30,
            "broken_clock": 30,
            "perplexing_painting": 80,
            "cosmic_banana": 20
        }

ROTATING_ITEMS = {
            "fuel_stabilizer": {"name": f"{EMOJIS.get('fuel_stabilizer', '🛢️')} Fuel Stabilizer", "cost": 800, "desc": "Makes your next mining run cost no fuel charge."},
            "station_rations": {"name": f"{EMOJIS.get('station_rations', '🥫')} Station Rations", "cost": 150, "desc": "Restores a modest 15 HP."},
            "hazard_shield": {"name": f"{EMOJIS.get('hazard_shield', '🛡️')} Hazard Shield", "cost": 1000, "desc": "Blocks the next scavenging hazard."},
            "lucky_scanner": {"name": f"{EMOJIS.get('lucky_scanner', '📡')} Deep-Space Scanner", "cost": 700, "desc": "Improves rare-find odds on your next scavenging run."},
            "ore_magnet": {"name": f"{EMOJIS.get('ore_magnet', '🧲')} Ore Magnet", "cost": 500, "desc": "Guarantees a titanium ore find on your next mining run."},
            "prototype_drill_bit": {"name": f"{EMOJIS.get('prototype_drill_bit', '⚙️')} Prototype Drill Bit", "cost": 1000, "desc": "Boosts Stardust from your next mining run."},
            "cosmic_insurance": {"name": f"{EMOJIS.get('cosmic_insurance', '📋')} Cosmic Insurance", "cost": 800, "desc": "Prevents a knockout from your next scavenging hazard."},
            "fate_anchor": {"name": f"{EMOJIS.get('fate_anchor', '⚓')} Fate Anchor", "cost": 2250, "desc": "Protects one missed fortune streak day."},
            "revive_kit": {"name": f"{EMOJIS.get('revive_kit', '💉')} Emergency Revival Kit", "cost": 1500, "desc": "Revives an unconscious explorer at 50% HP."},
            "stop_sign": {"name": "🛑 Stop Sign", "cost": 250, "type": "defense_weapon", "desc": "Lethal Company-inspired station debris. 8% chance to prevent a scavenging hazard."},
            "stick": {"name": "🪵 Stick", "cost": 450, "type": "defense_weapon", "desc": "Undertale-inspired weapon. 4% chance to prevent a scavenging hazard."},
            "wooden_sword": {"name": "🗡️ Wooden Sword", "cost": 800, "type": "defense_weapon", "desc": "Minecraft-inspired starter weapon. 10% chance to prevent a scavenging hazard."},
            "wooden_shield": {"name": "🛡️ Wooden Shield", "cost": 650, "type": "defense_weapon", "desc": "Minecraft-inspired starter shield. 7% chance to prevent a scavenging hazard."},
            "wooden_spoon": {"name": "🥄 Wooden Spoon", "cost": 300, "type": "defense_weapon", "desc": "A mighty station kitchen utensil. 2% chance to prevent a scavenging hazard."},
            "heavy_wrench": {"name": "🔧 Suspiciously Heavy Wrench", "cost": 2000, "type": "defense_weapon", "desc": "A maintenance tool that doubles as a weapon. 12% chance to prevent a scavenging hazard."},
            "plasma_cutter": {"name": "🔫 Plasma Cutter", "cost": 6000, "type": "defense_weapon", "halloween_only": True, "desc": "Halloween-only Dead Space-inspired weapon. 25% chance to prevent a scavenging hazard."},
            "title_outer_rim_wanderer": {"name": "🏷️ Title: Outer Rim Wanderer", "cost": 750, "type": "title", "desc": "A title for explorers who venture beyond the station."},
            "title_starborn": {"name": "🏷️ Title: Starborn", "cost": 750, "type": "title", "desc": "A prestigious title for those touched by the stars."},
            "title_voidfarer": {"name": "🏷️ Title: Voidfarer", "cost": 750, "type": "title", "desc": "For those brave enough to chart the endless void."},
        }

SHOP_LIMITS = {
            # Permanent shop
            "nanite_patch": (10, "daily"),
            "medkit": (5, "daily"),
            "full_revive": (2, "weekly"),
            "laser_charge_cell": (5, "daily"),
            "laser_power_cell": (3, "daily"),
            "fuel_refill": (2, "daily"),
            "drone_battery": (5, "daily"),
            "drone_power_cell": (3, "daily"),
            "drone_quantum_battery": (2, "daily"),
            "pet_snack": (30, "daily"),
            "time_crystal": (2, "monthly"),
            "astral_essence": (10, "weekly"),

            # Rotating shop
            "fuel_stabilizer": (5, "daily"),
            "station_rations": (15, "daily"),
            "hazard_shield": (5, "daily"),
            "lucky_scanner": (5, "daily"),
            "ore_magnet": (5, "daily"),
            "prototype_drill_bit": (5, "daily"),
            "cosmic_insurance": (5, "daily"),
            "fate_anchor": (3, "daily"),
            "revive_kit": (3, "daily"),
            "incubator_2": (1, "lifetime"),
            "incubator_3": (1, "lifetime"),
            "vault_expansion": (1, "lifetime"),
            "stop_sign": (1, "lifetime"),
            "stick": (1, "lifetime"),
            "wooden_sword": (1, "lifetime"),
            "wooden_shield": (1, "lifetime"),
            "wooden_spoon": (1, "lifetime"),
            "heavy_wrench": (1, "lifetime"),
            "plasma_cutter": (1, "lifetime"),

            # Rotating titles are permanent unlocks.
            "title_outer_rim_wanderer": (1, "lifetime"),
            "title_starborn": (1, "lifetime"),
            "title_voidfarer": (1, "lifetime"),
        }
