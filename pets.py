import asyncio
import random
import time
from typing import cast

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands, tasks

from database import ECONOMY_DB_NAME
from inventory import add_inventory_item, ITEM_REGISTRY
from seasonal_updates.halloween.halloween import is_active as halloween_is_active
from pet_variants import (
    ASTRAL_ESSENCE_ID, ASTRAL_ESSENCE_NAME, ASTRAL_ESSENCE_EMOJI,
    FUSION_COSTS, VARIANT_HUNT_COST, FUSION_LEVEL_GATES,
    HATCH_ESSENCE_CHANCE, RELEASE_ESSENCE_CHANCE,
    get_variant_info, get_variant_display, get_variant_ids_for_pet,
    roll_hatched_variant, roll_fusion_variant, build_variant_collectibles,
)


# ============================================================================
# PET CONFIGURATION
# ============================================================================
# This is intentionally kept very easy to edit.
#
# Add normal pets to PETS and Halloween pets to HALLOWEEN_PETS.
#
# Passive effect IDs currently supported:
#   stardust_bonus       -> percentage bonus to Stardust
#   material_bonus       -> chance to add +1 to a successful material find
#   rare_loot_bonus      -> percentage added to scavenging rare-loot thresholds
#   hazard_reduction     -> percentage reduction to scavenging hazard damage
#   charge_save          -> chance to avoid consuming an exploration charge
#   cooldown_reduction   -> percentage reduction to exploration cooldown
#   halloween_bonus      -> chance to gain an extra Halloween seasonal item
#   treat_xp_bonus       -> percentage bonus to Pet XP from treats
#   candy_bonus          -> chance to double Halloween Candy
#   scavenge_first_aid   -> chance to recover HP after a scavenging hazard
#   scavenge_hazard_avoidance -> chance to completely avoid a scavenging hazard
#   scavenge_charge_save -> chance to preserve a scavenging charge
#   scavenge_material_bonus -> chance to find an extra scavenging material unit
#   scavenge_bonus_loot  -> chance to find an extra miscellaneous scavenging item
#   extra_charges        -> Stardust bonus for mining/scavenging; at passive
#                           level 5 also grants +3 maximum charges to both
#                           exploration systems
#   dragonrider_success  -> percentage-point bonus to Dragonrider success chance
#   dragonrider_attempts -> at passive level 5 grants +1 Dragonrider attempt/day
#   minigame_payout      -> percentage bonus to non-Trivia minigame payouts
#   trickster_tokens     -> at passive level 5: +1 token on wins, -1 extra token on losses
#   shop_discount        -> percentage discount applied to shop prices
#   shop_free_purchase   -> at passive level 5: 20% chance to make one purchase/day free
#   daily_bonus          -> percentage bonus to the daily Stardust reward
#   daily_double         -> at passive level 5: 25% chance to double the daily payout
#   streak_rescue        -> at passive level 5: one automatic streak rescue/month
#
# "levels" contains the passive's strength at passive levels 1-5.
# Pets can continue leveling past 5, but passive strength stops increasing at 5
# so higher levels remain available for future/cosmetic systems.
# ============================================================================

PET_PASSIVE_MAX_LEVEL = 5

# Reusable definitions for the newer special passives. They are kept separate
# from individual pet entries so a pet can opt into one without duplicating
# the level tuning. Level 5 contains the former level-6 special effect.
SPECIAL_PASSIVE_DEFINITIONS = {
    "dragonrider_success": {
        "name": "Dragonrider Success+",
        "description": "Improves Dragonrider success chance. At passive level 5, grants 1 additional Dragonrider attempt per week.",
        "levels": [0.01, 0.02, 0.03, 0.04, 0.05],
    },
    "minigame_payout": {
        "name": "Minigame Payout+",
        "description": "Increases Stardust payouts from non-Trivia minigames.",
        "levels": [0.04, 0.08, 0.12, 0.16, 0.20],
    },
    "trickster_tokens": {
        "name": "Trickster Token",
        "description": "At passive level 5, winning a non-Trivia minigame grants 1 additional Arcade Token, while losing consumes 1 extra token.",
        "levels": [0.0, 0.0, 0.0, 0.0, 1.0],
    },
    "shop_discount": {
        "name": "Shop Discount+",
        "description": "Reduces Stardust prices in the station shop. At passive level 5, also has a 20% chance to make one purchase per day free.",
        "levels": [0.03, 0.06, 0.09, 0.12, 0.15],
    },
    "daily_bonus": {
        "name": "/daily Reward+",
        "description": "Increases the Stardust awarded by /daily. At passive level 5, has a 25% chance to double the payout and grants one automatic daily streak rescue per month.",
        "levels": [0.05, 0.10, 0.15, 0.20, 0.25],
    },
}

PETS = {
    # ------------------------------------------------------------------
    # NORMAL PET PLACEHOLDERS — edit these!
    # ------------------------------------------------------------------
    "space_cat": {
        "name": "Space Cat",
        "emoji": "🐱",
        "description": "An orange kitty that's somehow able to breath in space! *He only comes with one braincell, sorry.*",
        "egg": "normal_egg",
        "passive": {
            "id": "stardust_bonus",
            "name": "Lucky Paws",
            "description": "Finds a little extra Stardust during exploration.",
            "levels": [0.01, 0.02, 0.03, 0.04, 0.05],
        },
    },
    "cosmic_fox": {
        "name": "Cosmic Fox",
        "emoji": "🦊",
        "description": "A cute fox, but with cosmic colors, and somehow able to breathe in space!",
        "egg": "normal_egg",
        "passive": {
            "id": "material_bonus",
            "name": "Scavenger's Instinct",
            "description": "Sometimes finds an extra unit when recovering materials.",
            "levels": [0.02, 0.04, 0.06, 0.08, 0.10],
        },
    },
    "astronaut_turtle": {
        "name": "Astronaut Turtle",
        "emoji": "🐢",
        "description": "A little turtle with an astronaut helmet!",
        "egg": "normal_egg",
        "passive": {
            "id": "hazard_reduction",
            "name": "Heavy Shell",
            "description": "Reduces damage taken from scavenging hazards.",
            "levels": [0.02, 0.04, 0.06, 0.08, 0.10],
        },
    },
    "busted_drone": {
        "name": "Busted-up Drone",
        "emoji": "🛸",
        "description": "A busted up drone. Looks like it was in war. Still works... somewhat. It seems fond of you! (Likes to make little happy, beepy noises!)",
        "egg": "normal_egg",
        "passive": {
            "id": "charge_save",
            "name": "Helping Hand",
            "description": "The drone may be busted, but still wishes to help! Has a chance for you to not consume a charge for your laser or scavenging drone.",
            "levels": [0.05, 0.07, 0.10, 0.15, 0.20],
        },
    },
    "cosmic_owl": {
        "name": "Cosmic Owl",
        "emoji": "🦉",
        "description": "An abnormally large owl, coated in cosmic colors. Staring into its eyes is like gazing into space itself, giving you immense wisdom.",
        "egg": "normal_egg",
        "passive": {
            "id": "cooldown_reduction",
            "name": "Cosmic Wisdom",
            "description": "You gaze into the owls eyes... it fills you with wisdom. It now reduces the cooldown for your laser and scavenging drone!",
            "levels": [0.05, 0.10, 0.20, 0.25, 0.30],
        },
    },
    "glorpy": {
        "name": "Glorpy",
        "emoji": "👽",
        "description": "A bright green alien cat named Glorpy. It likes to glorp.",
        "egg": "normal_egg",
        "passive": {
            "id": "rare_loot_bonus",
            "name": "Zib Zib",
            "description": "Glorpy uses their magical alien powers to 'zib zib' more rare loot from explorations.",
            "levels": [0.007, 0.009, 0.012, 0.016, 0.020],
        },
    },
    "little_star": {
        "name": "Little Star",
        "emoji": "🌟",
        "description": "A bright, glowing little star that follows you around wherever you go!",
        "egg": "normal_egg",
        "passive": {
            "id": "stardust_bonus",
            "name": "Twinkle Twinkle Little Star",
            "description": "The little star seems rather fond of you! It will now give a chance to find extra Stardust!",
            "levels": [0.02, 0.04, 0.06, 0.08, 0.12],
        },
    },
    "meteor": {
        "name": "Friendly Meteor",
        "emoji": "☄️",
        "description": "A huge, glowing, yet suspiciously friendly meteor that follows you around! Still suspicious... but cute!",
        "egg": "normal_egg",
        "passive": {
            "id": "hazard_reduction",
            "name": "Meteor Shower",
            "description": "Your friendly meteor will sometimes have a chance to split itself into bits and shoot at the hazard, reducing some of the HP taken! *Still suspicious...*",
            "levels": [0.03, 0.06, 0.09, 0.12, 0.15],
        },
    },
    "space_dragon": {
        "name": "Space Dragon",
        "emoji": "🐲",
        "description": "A massive dragon with cosmic colors all over, looking like you're staring into space itself when gazing upon it!",
        "egg": "normal_egg",
        "passive": {
            "id": "extra_charges",
            "name": "Dragon's Magic",
            "description": "The large space dragon will now give you extra Stardust for Mining and Scavenging, and when maxed, will grant you 3 extra charges as well!",
            # Levels 1-5 provide +2%, +5%, +10%, +13%, +13% Stardust.
            # Level 5 additionally grants +3 maximum mining/scavenging charges.
            "levels": [0.02, 0.05, 0.10, 0.13, 0.13],
        },
    },
    "ethereal_cloud": {
        "name": "Ethereal Cloud",
        "emoji": "☁️",
        "description": "A big, floating cloud that roams around you! It smells like ozone, and occasionally drizzles specks of cosmic energy.",
        "egg": "normal_egg",
        "passive": {
            "id": "dragonrider_success",
            "name": "Helping Cloud",
            "description": "The cloud helps you with your Dragonrider Test! Increases your odds of successfully completing our test. At level 5, you get one extra attempt a week!",
            "levels": [0.01, 0.02, 0.03, 0.04, 0.05],
        },
    },
    "cosmic_trickster": {
        "name": "Cosmic Trickster",
        "emoji": "🥷",
        "description": "A ninja-like trickster, but cosmic! Maybe you shouldn't get on its bad side...",
        "egg": "normal_egg",
        "passive": {
            "id": "minigame_payout",
            "name": "Tricksters Gamble",
            "description": "The trickster seems fond of you! Thankfully... it now gives you the chance of increasing the amount of payout from minigames! At level 5, winning a non-trivia game gives you one extra Arcade Token! But losing consumes one additional Arcade Token...",
            "levels": [0.04, 0.08, 0.12, 0.16, 0.20],
        },
    },
    "void_merchant": {
        "name": "Void Merchant",
        "emoji": "🕳️",
        "description": "A tall, suspicious merchant. You cannot see its face, and it never speaks. Though, it seems helpful enough...",
        "egg": "normal_egg",
        "passive": {
            "id": "shop_discount",
            "name": "Merchant's Favor",
            "description": "It seems like the merchant helps you more than you'd expect! You now have a shop discount from the merchant depending on your level! At level 5, you have a 20% chance of getting your purchase free of charge! **Free purchase can only proc once per day.**",
            "levels": [0.03, 0.06, 0.09, 0.12, 0.15],
        },
    },
    "solar_phoenix": {
        "name": "Solar Phoenix",
        "emoji": "🐦‍🔥",
        "description": "A large phoenix made of pure solar energy. Its impossibly hot, even going close to it can cause fourth-degree burns without protective clothing!",
        "egg": "normal_egg",
        "passive": {
            "id": "daily_bonus",
            "name": "Burning Sun",
            "description": "The phoenix is rather helpful, despite being able to practically melt you like the sun! You now have Stardust increases to your /daily command! At level 5, you have a 25% chance to double the payout and grants one automatic daily streak rescue per month, for any streaks!",
            "levels": [0.05, 0.10, 0.15, 0.20, 0.25],
        },
    },
}

HALLOWEEN_PETS = {
    # ------------------------------------------------------------------
    # HALLOWEEN PET PLACEHOLDERS — edit these!
    # ------------------------------------------------------------------
    "pumpkin_pup": {
        "name": "Pumpkin Pup",
        "emoji": "🎃",
        "description": "A little puppy with a pumpkin on its head!",
        "egg": "halloween_egg",
        "passive": {
            "id": "stardust_bonus",
            "name": "Trickster's Luck",
            "description": "A spooky little bonus to Stardust from exploration.",
            "levels": [0.01, 0.02, 0.03, 0.04, 0.05],
        },
    },
    "black_cat": {
        "name": "Black Witchy Cat",
        "emoji": "🐈‍⬛",
        "description": "A black kitty with a witch hat! How adorable and spooky!",
        "egg": "halloween_egg",
        "passive": {
            "id": "rare_loot_bonus",
            "name": "Ghostly Luck",
            "description": "Slightly improves the chance of finding rare scavenging loot.",
            "levels": [0.005, 0.008, 0.011, 0.014, 0.017],
        },
    },
    "vampire_bat": {
        "name": "Vampire Bat",
        "emoji": "🦇",
        "description": "A fluttering bat who, for some reason, doesn't want to bite you. Maybe you taste bad, or it likes you!",
        "egg": "halloween_egg",
        "passive": {
            "id": "hazard_reduction",
            "name": "Nightmare Dodge",
            "description": "Reduces damage from scavenging hazards.",
            "levels": [0.02, 0.04, 0.06, 0.08, 0.15],
        },
    },
    "godzilla": {
        "name": "Godzilla",
        "emoji": "🦖",
        "description": "The King of Monsters himself, Godzilla! He'll blast through incoming hazards and protect you!",
        "egg": "halloween_egg",
        "passive": {
            "id": "atomic_breath",
            "name": "Atomic Breath",
            "description": "Godzilla can blast incoming scavenging hazards before they reach you with his Atomic Breath.",
            "levels": [0.15, 0.20, 0.25, 0.30, 0.35],
        },
    },
    "skeleton_dragon": {
        "name": "Skeleton Dragon",
        "emoji": "🐲",
        "description": "A big skeleton dragon! Undead never seemed so awesome and powerful!",
        "egg": "halloween_egg",
        "normal_passive": {
            "id": "scavenge_first_aid",
            "name": "Dragon's Blessing",
            "description": "After taking damage from a scavenging hazard, has a chance to recover a small amount of HP.",
            "levels": [0.05, 0.07, 0.09, 0.12, 0.15],
        },
        "passive": {
            "id": "halloween_bonus",
            "name": "Hallows Hoard",
            "description": "Improves the chance of finding an additonal Halloween-themed item by the dragon digging through its hoard.",
            "levels": [0.015, 0.025, 0.035, 0.040, 0.050],
        },
    },
    "samhain": {
        "name": "Samhain",
        "emoji": "🎃",
        "description": "A mysterious, sack-headed trick-or-treater who enforces the sacred rules of Halloween. If you refuse him a treat or blow out your Jack-o'-Lantern early, he'll make sure you face a terrifying trick.",
        "egg": "halloween_egg",
        "normal_passive": {
            "id": "scavenge_hazard_avoidance",
            "name": "Samhain Protection",
            "description": "Sam appreciates you loving Halloween, even when it's not! He has a chance for you to completely avoid a hazard.",
            "levels": [0.06, 0.08, 0.10, 0.14, 0.18],
        },
        "passive": {
            "id": "candy_bonus",
            "name": "Trick 'r Treat",
            "description": "Sam appreciates you loving Halloween! He has a chance for you to get extra candy!",
            "levels": [0.10, 0.20, 0.30, 0.40, 0.50],
        },
    },
    "flytrap": {
        "name": "The Feed Me",
        "emoji": "🪴",
        "description": "A demanding, fast-growing alien flytrap sitting in a cracked clay pot. It snaps its jaw impatiently whenever your skills are inactive!",
        "egg": "halloween_egg",
        "passive": {
            "id": "cooldown_reduction",
            "name": "Blood Rush",
            "description": "The plant's insatiable hunger drives you forward. It reduces the cooldown for your laser and scavenging drone!",
            "levels": [0.10, 0.15, 0.20, 0.30, 0.35],
        },
    },
}


# ============================================================================
# HAUNTED EXPLORATION PETS
# ============================================================================
# These companions are discovered directly while exploring their associated
# Haunted location. They are intentionally NOT part of either egg pool.
#
# The passive effects use the existing pet passive system so these pets work
# with the current exploration/pet UI immediately. The Haunted location and
# discovery text are stored here for Haunted Exploration to consume.
# ============================================================================

HAUNTED_PETS = {
    "the_patient": {
        "name": "The Patient",
        "emoji": "🩺",
        "description": "A pale little hospital patient who should have been discharged a very, very long time ago. They quietly follow you through the halls, occasionally looking toward rooms you haven't noticed yet.",
        "egg": None,
        "haunted_location": "asylum",
        "discovery_message": "You hear a soft hospital call button ring from an empty room. When you look inside, a small patient is sitting on the bed, watching you. They slowly climb down and walk over.\n\n**🐾 You discovered The Patient!**\nThe Patient is now in your pets inventory.",
        "normal_passive": {
            "id": "scavenge_first_aid",
            "name": "First Aid",
            "description": "After taking damage from a scavenging hazard, has a chance to recover a small amount of HP.",
            "levels": [0.03, 0.05, 0.07, 0.09, 0.12],
        },
        "passive": {
            "id": "haunted_sanity_reduction",
            "name": "Patient Instinct",
            "description": "The Patient reduces supernatural Sanity loss in the Abandoned Asylum.",
            "levels": [0.05, 0.08, 0.11, 0.14, 0.18],
        },
    },
    "graveyard_ghoul": {
        "name": "Graveyard Ghoul",
        "emoji": "👻",
        "description": "A small graveyard ghoul that crawled out from somewhere it absolutely should not have. It is surprisingly friendly.",
        "egg": None,
        "haunted_location": "graveyard",
        "discovery_message": "Something rustles beneath a freshly disturbed patch of earth. A little ghoul pokes its head out, looks at you, and gives an awkward wave.\n\n**🐾 You discovered Graveyard Ghoul!**\nGraveyard Ghoul is now in your pets inventory.",
        "normal_passive": {
            "id": "rare_loot_bonus",
            "name": "Grave Robber",
            "description": "Slightly improves the chance of finding rare scavenging loot.",
            "levels": [0.005, 0.008, 0.011, 0.014, 0.018],
        },
        "passive": {
            "id": "haunted_ingredient_bonus",
            "name": "Unearthed",
            "description": "The Graveyard Ghoul increases ingredient finds in the Forgotten Graveyard.",
            "levels": [0.05, 0.08, 0.12, 0.16, 0.2],
        },
    },
    "little_resident": {
        "name": "The Little Resident",
        "emoji": "🧸",
        "description": "A tiny ghost who insists that the Haunted House is their home. They seem mildly offended whenever you suggest otherwise.",
        "egg": None,
        "haunted_location": "haunted_house",
        "discovery_message": "You find a tiny figure sitting at the end of a hallway. You blink. It is closer. You blink again. It is holding out its hand.\n\n**🐾 You discovered The Little Resident!**\nThe Little Resident is now in your pets inventory.",
        "normal_passive": {
            "id": "scavenge_bonus_loot",
            "name": "Housekeeping",
            "description": "Sometimes finds an extra miscellaneous item while scavenging.",
            "levels": [0.02, 0.03, 0.04, 0.05, 0.07],
        },
        "passive": {
            "id": "haunted_reward_bonus",
            "name": "Houseguest",
            "description": "The Little Resident increases Stardust rewards in the Haunted House.",
            "levels": [0.03, 0.05, 0.07, 0.09, 0.12],
        },
    },
    "the_forgotten": {
        "name": "The Forgotten",
        "emoji": "👻",
        "description": "A ghostly member of a forgotten congregation, still wearing the remains of its old ceremonial robes. It never speaks. It simply watches.",
        "egg": None,
        "haunted_location": "church",
        "discovery_message": "The empty pews begin to creak one by one. At the altar stands a robed figure you are certain wasn't there a moment ago.\n\nIt turns toward you.\n\n**🐾 You discovered The Forgotten!**\nThe Forgotten is now in your pets inventory.",
        "normal_passive": {
            "id": "scavenge_hazard_avoidance",
            "name": "Watchful Spirit",
            "description": "Has a chance to completely avoid a scavenging hazard.",
            "levels": [0.03, 0.05, 0.07, 0.09, 0.12],
        },
        "passive": {
            "id": "haunted_negative_protection",
            "name": "Silent Warning",
            "description": "The Forgotten has a chance to negate a negative outcome in the Abandoned Church.",
            "levels": [0.05, 0.08, 0.11, 0.14, 0.18],
        },
    },
    "ghost_cat": {
        "name": "Ghost Cat",
        "emoji": "🐈",
        "description": "A translucent little cat that wanders through trees, walls, and occasionally your personal space. It seems completely comfortable being dead.",
        "egg": None,
        "haunted_location": "witch_woods",
        "discovery_message": "A soft meow comes from behind you. When you turn around, a ghostly cat is sitting there. It meows again, walks directly through a tree, and looks back at you as if you're the strange one.\n\n**🐾 You discovered Ghost Cat!**\nGhost Cat is now in your pets inventory.",
        "normal_passive": {
            "id": "scavenge_charge_save",
            "name": "Phantom Paws",
            "description": "Has a chance to preserve a scavenging charge after a run.",
            "levels": [0.04, 0.07, 0.10, 0.13, 0.17],
        },
        "passive": {
            "id": "haunted_discovery_bonus",
            "name": "Nine Lives",
            "description": "Ghost Cat increases rare-discovery chances in the Witch’s Woods.",
            "levels": [0.02, 0.03, 0.04, 0.05, 0.07],
        },
    },
    "broken_bear": {
        "name": "Broken Bear",
        "emoji": "🐻",
        "description": "A broken-down bear animatronic from the pizzeria. One eye flickers, its jaw hangs slightly crooked, and somehow it still wants to be your friend.",
        "egg": None,
        "haunted_location": "dilapidated_pizzeria",
        "discovery_message": "A metal footstep echoes from the darkened stage. A battered bear animatronic slowly steps into view. Its head twitches toward you.\n\nThen it waves.\n\n**🐾 You discovered Broken Bear!**\nBroken Bear is now in your pets inventory.",
        "normal_passive": {
            "id": "hazard_reduction",
            "name": "Security Protocol",
            "description": "Reduces damage taken from scavenging hazards.",
            "levels": [0.02, 0.04, 0.06, 0.08, 0.10],
        },
        "passive": {
            "id": "haunted_negative_protection",
            "name": "Security Sweep",
            "description": "Broken Bear has a chance to negate a negative outcome in the Dilapidated Pizzeria.",
            "levels": [0.05, 0.08, 0.11, 0.14, 0.18],
        },
    },
    "longarms": {
        "name": "Longarms",
        "emoji": "🧸",
        "description": "A large blue toy creature with an absurdly long reach, a cheerful face, and a habit of appearing where you absolutely did not leave it.",
        "egg": None,
        "haunted_location": "abandoned_toy_workshop",
        "discovery_message": "You hear something dragging across the factory floor.\n\nscrape... scrape... scrape...\n\nA large blue toy slowly steps out from between the machines. It stares at you for a moment, then gives an enthusiastic wave with one very long arm.\n\n**🐾 You discovered Longarms!**\nLongarms is now in your pets inventory.",
        "normal_passive": {
            "id": "scavenge_material_bonus",
            "name": "Long Reach",
            "description": "Sometimes finds an additional unit when recovering scavenging materials.",
            "levels": [0.02, 0.04, 0.06, 0.08, 0.10],
        },
        "passive": {
            "id": "haunted_ingredient_bonus",
            "name": "Long Reach",
            "description": "Longarms increases ingredient finds in the Abandoned Toy Workshop.",
            "levels": [0.05, 0.08, 0.12, 0.16, 0.2],
        },
    },
    "dead_air": {
        "name": "Dead-Air",
        "emoji": "📻",
        "description": "A strange little broadcast entity that emerged from the station's dead signal. It occasionally emits static when something nearby isn't quite right.",
        "egg": None,
        "haunted_location": "broadcast_station",
        "discovery_message": "Every monitor in the station suddenly switches to static. When the picture returns, a tiny figure is standing beside you on the screen.\n\nYou turn around. Nothing.\n\nThe static crackles again.\n\n**🐾 You discovered Dead-Air!**\nDead-Air is now in your pets inventory.",
        "normal_passive": {
            "id": "rare_loot_bonus",
            "name": "Signal Sweep",
            "description": "Slightly improves the chance of finding rare scavenging loot.",
            "levels": [0.005, 0.008, 0.011, 0.014, 0.018],
        },
        "passive": {
            "id": "haunted_discovery_bonus",
            "name": "Signal Boost",
            "description": "Dead-Air increases rare-discovery chances in the Abandoned Broadcast Station.",
            "levels": [0.02, 0.03, 0.04, 0.05, 0.07],
        },
    },
    "hotel_guest": {
        "name": "Hotel Guest",
        "emoji": "🧍",
        "description": "A quiet guest who appears to have been staying at the Endless Hotel for far too long. They never speak, but they always seem to know which way you're going.",
        "egg": None,
        "haunted_location": "endless_hotel",
        "discovery_message": "You turn a corner and find someone standing at the end of the hallway.\n\nYou turn another corner.\n\nThey're there again.\n\nWhen you finally stop running, they simply walk over and stand beside you.\n\n**🐾 You discovered Hotel Guest!**\nHotel Guest is now in your pets inventory.",
        "normal_passive": {
            "id": "cooldown_reduction",
            "name": "Know the Way",
            "description": "Slightly reduces the cooldown for normal exploration.",
            "levels": [0.03, 0.05, 0.08, 0.10, 0.12],
        },
        "passive": {
            "id": "haunted_stage_reduction",
            "name": "Late Checkout",
            "description": "Hotel Guest has a chance to remove one stage from an Endless Hotel run.",
            "levels": [0.1, 0.15, 0.2, 0.25, 0.3],
        },
    },
    "fogling": {
        "name": "Fogling",
        "emoji": "🌫️",
        "description": "A tiny creature made almost entirely of fog. It is difficult to tell where its body ends and the mist begins.",
        "egg": None,
        "haunted_location": "fogbound_town",
        "discovery_message": "A small shape forms beneath a streetlight. The fog gathers around it until two glowing eyes appear.\n\nIt waddles toward you and dissolves into mist around your feet.\n\nThen it reforms beside you.\n\n**🐾 You discovered Fogling!**\nFogling is now in your pets inventory.",
        "normal_passive": {
            "id": "scavenge_hazard_avoidance",
            "name": "Mistwalker",
            "description": "Has a chance to completely avoid a scavenging hazard.",
            "levels": [0.03, 0.05, 0.07, 0.09, 0.12],
        },
        "passive": {
            "id": "haunted_sanity_reduction",
            "name": "Into the Mist",
            "description": "Fogling reduces supernatural Sanity loss in Fogbound Town.",
            "levels": [0.05, 0.08, 0.11, 0.14, 0.18],
        },
    },
    "malo": {
        "name": "MalO",
        "emoji": "👁️",
        "description": "MalO. She looks exactly as she should. She follows you exactly as she should. The only problem is that you don't remember inviting her along.",
        "egg": None,
        "haunted_location": "derelict_research_facility",
        "discovery_message": "You find a terminal displaying **MalO ver1.0.0**.\n\nA photograph appears on the screen.\n\nThen another.\n\nIn each one, the figure is closer.\n\nThe newest photograph was taken just now.\n\nYou turn around.\n\nShe is already there.\n\n**👁️ You discovered MalO.**\n\nYou do not remember finding her. You remember seeing her. Then she was beside you.\n\n**MalO is now in your pets inventory.**\n\nYou do not remember putting her there.",
        "normal_passive": {
            "id": "scavenge_bonus_loot",
            "name": "Unwanted Assistance",
            "description": "Sometimes finds an extra miscellaneous item while scavenging.",
            "levels": [0.02, 0.03, 0.04, 0.05, 0.07],
        },
        "passive": {
            "id": "haunted_malo",
            "name": "Unknown Companion",
            "description": "MalO increases rare-discovery chances in the Research Facility and can warn you about dangerous choices.",
            "levels": [0.03, 0.05, 0.07, 0.09, 0.12],
        },
    },
    "patch": {
        "name": "Patch",
        "emoji": "🐾",
        "description": "A glitched animal that looks like reality forgot what an animal was supposed to look like. Patch has too many eyes, too many limbs, and absolutely no concern about any of it.",
        "egg": None,
        "haunted_location": "yellow_halls",
        "discovery_message": "You hear claws tapping somewhere behind you.\n\nYou turn around.\n\nSomething is standing in the hallway. It looks almost like an animal. Almost.\n\nIt has too many eyes. Too many legs. One of its limbs bends in a direction that makes no sense.\n\nIt tilts its head.\n\nThen it happily walks over.\n\n**🐾 You discovered Patch!**\nPatch is now in your pets inventory.",
        "normal_passive": {
            "id": "scavenge_material_bonus",
            "name": "Wrong Reality",
            "description": "Sometimes causes an additional unit of scavenging material to appear.",
            "levels": [0.02, 0.04, 0.06, 0.08, 0.10],
        },
        "passive": {
            "id": "haunted_negative_protection",
            "name": "Wrong Turn",
            "description": "Patch has a chance to negate a negative outcome in the Yellow Halls.",
            "levels": [0.05, 0.08, 0.11, 0.14, 0.18],
        },
    },
    "roadside_hitchhiker": {
        "name": "Roadside Hitchhiker",
        "emoji": "🚗",
        "description": "A silent hitchhiker who appears beside roads that should not exist. They never ask where you're going. They already seem to know.",
        "egg": None,
        "haunted_location": "dead_end_highway",
        "discovery_message": "You see someone standing beside the highway.\n\nYou slow down.\n\nThey raise a hand.\n\nThere is no road behind them.\n\nWhen you look again, they're sitting in your passenger seat.\n\nThey quietly point toward the road ahead.\n\n**🐾 You discovered Roadside Hitchhiker!**\nRoadside Hitchhiker is now in your pets inventory.",
        "normal_passive": {
            "id": "scavenge_bonus_loot",
            "name": "Roadside Find",
            "description": "Sometimes discovers bonus miscellaneous loot while scavenging.",
            "levels": [0.02, 0.03, 0.04, 0.05, 0.07],
        },
        "passive": {
            "id": "haunted_negative_protection",
            "name": "Wrong Way",
            "description": "The Roadside Hitchhiker has a chance to negate a negative outcome on the Dead-End Highway.",
            "levels": [0.05, 0.08, 0.11, 0.14, 0.18],
        },
    },
    "drowned_conductor": {
        "name": "Drowned Conductor",
        "emoji": "🚂",
        "description": "A soaked railway conductor who somehow remains perfectly composed despite being permanently underwater. They still seem determined to get you to the last stop.",
        "egg": None,
        "haunted_location": "drowned_station",
        "discovery_message": "A train whistle echoes through the flooded station. A conductor emerges from the dark water, checks an ancient watch, and looks directly at you.\n\nThey gesture for you to follow.\n\nYou probably shouldn't.\n\n**🐾 You discovered Drowned Conductor!**\nDrowned Conductor is now in your pets inventory.",
        "normal_passive": {
            "id": "scavenge_charge_save",
            "name": "Last Stop",
            "description": "Has a chance to preserve a scavenging charge after a run.",
            "levels": [0.04, 0.07, 0.10, 0.13, 0.17],
        },
        "passive": {
            "id": "haunted_sanity_reduction",
            "name": "Last Stop",
            "description": "The Drowned Conductor reduces supernatural Sanity loss in the Drowned Station.",
            "levels": [0.05, 0.08, 0.11, 0.14, 0.18],
        },
    },
    "the_watcher": {
        "name": "The Watcher",
        "emoji": "👁️",
        "description": "A tall, silent figure that watches from the trees. It never seems to blink. Somehow, it has decided that following you is preferable to watching from a distance.",
        "egg": None,
        "haunted_location": "silent_campground",
        "discovery_message": "You find a photograph on the ground.\n\nThe figure in the background is closer than it was in the previous photograph.\n\nYou hear a branch snap behind you.\n\nYou do not turn around.\n\nSomething quietly walks beside you anyway.\n\n**🐾 You discovered The Watcher!**\nThe Watcher is now in your pets inventory.\n\nYou still don't look behind you.",
        "normal_passive": {
            "id": "rare_loot_bonus",
            "name": "Never Alone",
            "description": "Slightly improves the chance of finding rare scavenging loot.",
            "levels": [0.005, 0.008, 0.011, 0.014, 0.018],
        },
        "passive": {
            "id": "haunted_discovery_bonus",
            "name": "Don’t Look Back",
            "description": "The Watcher increases rare-discovery chances in the Silent Campground.",
            "levels": [0.02, 0.03, 0.04, 0.05, 0.07],
        },
    },
}

ALL_PETS = {**PETS, **HALLOWEEN_PETS, **HAUNTED_PETS}

EGG_POOLS = {
    "normal_egg": [pet_id for pet_id, pet in PETS.items() if pet["egg"] == "normal_egg"],
    "halloween_egg": [
        pet_id for pet_id, pet in HALLOWEEN_PETS.items()
        if pet["egg"] == "halloween_egg"
    ],
}

# Pet progression tuning.
# Exploration grants a randomized amount of ordinary XP.
NORMAL_EXPLORATION_PET_XP_MIN = 10
NORMAL_EXPLORATION_PET_XP_MAX = 30
HAUNTED_EXPLORATION_PET_XP_MIN = 15
HAUNTED_EXPLORATION_PET_XP_MAX = 50
HAUNTED_HOME_PET_XP_BONUS = 10
PET_TREAT_XP = 50
HALLOWEEN_PET_CANDY_XP = 150

# Egg drops are independent bonus rolls during scavenging.
NORMAL_EGG_CHANCE = 0.085
HALLOWEEN_EGG_CHANCE = 1 / 35

INCUBATION_SECONDS = 12 * 60 * 60
INCUBATOR_NOTIFICATION_CHANNEL_ID = 1548034265508356166


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



class FeedTreatSelect(discord.ui.Select):
    def __init__(self, cog, user_id, pet_id, owned, parent_message, ctx):
        options = []
        for item_id, label, emoji in (
            ("pet_snack", "Pet Treat", "🍖"),
            ("halloween_pet_candy", "Halloween Pet Candy", "🎃"),
        ):
            quantity = owned.get(item_id, 0)
            if quantity <= 0:
                continue
            options.append(discord.SelectOption(
                label=f"{label} ×{quantity}",
                value=item_id,
                emoji=emoji,
                description="Feed this treat to the selected pet.",
            ))
        super().__init__(placeholder="Choose a treat...", min_values=1, max_values=1, options=options)
        self.cog = cog
        self.user_id = user_id
        self.pet_id = pet_id
        self.parent_message = parent_message
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This treat menu isn't for you.", ephemeral=True)
        result, error = await self.cog._feed_specific_pet(
            self.user_id,
            self.pet_id,
            self.values[0],
        )
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        if result is None:
            return await interaction.response.send_message(
                "❌ Feeding failed because no result was returned.",
                ephemeral=True,
            )
        pet = result["pet"]
        level_line = ""
        if result["leveled_up"]:
            level_line = (
                f"\n🎉 **Level Up!** Your pet reached **Level {result['new_level']}**!"
                f"\n✨ Passive is now **Level {result['passive_level']}/{PET_PASSIVE_MAX_LEVEL}**."
            )
        await interaction.response.send_message(
            f"{pet['emoji']} **{pet['nickname'] or pet['name']}** enjoyed the "
            f"**{result['treat']['name']}**!\n✨ **+{result['xp_amount']} Pet XP**{level_line}",
            ephemeral=True,
        )
        await self.cog._refresh_pet_view(self.parent_message, self.user_id, self.pet_id, ctx=self.ctx)


class FeedTreatView(discord.ui.View):
    def __init__(self, cog, user_id, pet_id, owned, parent_message, ctx):
        super().__init__(timeout=60)
        self.parent_message = parent_message
        self.add_item(FeedTreatSelect(cog, user_id, pet_id, owned, parent_message, ctx))


class ReleaseConfirmationView(discord.ui.View):
    def __init__(self, cog, user_id, pet, parent_message, ctx):
        super().__init__(timeout=30)
        self.cog = cog
        self.user_id = user_id
        self.pet_id = pet["pet_id"]
        self.pet = pet
        self.parent_message = parent_message
        self.ctx = ctx

    @discord.ui.button(label="Yes, Release Pet", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This confirmation isn't for you.", ephemeral=True)
        released = await self.cog._release_pet(self.user_id, self.pet_id)
        if not released:
            self.stop()
            return await interaction.response.edit_message(content="❌ That pet could not be released because it no longer exists.", view=None)
        if released.get("protected"):
            self.stop()
            return await interaction.response.edit_message(
                content="🔒 **This pet is favorited and protected!** Unfavorite it first if you really want to release it.",
                view=None,
            )
        self.stop()
        essence_line = "\n✨ **Astral Essence recovered!**" if released.get("essence_awarded") else ""
        await interaction.response.edit_message(
            content=(
                f"🔴 Released **{released['emoji']} {released['nickname'] or released['name']}** "
                f"(Level {released['level']}).{essence_line}\n\n"
                "This pet has been permanently removed from your collection."
            ),
            view=None,
        )
        await self.cog._refresh_pet_view(self.parent_message, self.user_id, self.pet_id, allow_missing=True, ctx=self.ctx)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This confirmation isn't for you.", ephemeral=True)
        self.stop()
        await interaction.response.edit_message(content="Release cancelled. 👍", view=None)



class RenamePetModal(discord.ui.Modal):
    def __init__(self, cog, user_id, pet_id, parent_message, ctx):
        super().__init__(title="Rename Pet", timeout=120)
        self.cog = cog
        self.user_id = user_id
        self.pet_id = pet_id
        self.parent_message = parent_message
        self.ctx = ctx

        self.name_input = discord.ui.TextInput(
            label="Pet Name",
            placeholder="Enter a new name (30 characters max)",
            max_length=30,
            required=False,
        )
        self.add_item(self.name_input)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "❌ This rename menu isn't for you.", ephemeral=True
            )

        new_name = str(self.name_input.value).strip()
        if len(new_name) > 30:
            return await interaction.response.send_message(
                "❌ Pet names can be at most **30 characters** long.",
                ephemeral=True,
            )

        renamed = await self.cog._rename_pet(self.user_id, self.pet_id, new_name)
        if not renamed:
            return await interaction.response.send_message(
                "❌ That pet no longer exists in your collection.",
                ephemeral=True,
            )

        display_name = renamed["nickname"] or renamed["name"]
        if renamed["nickname"]:
            message = (
                f"✏️ Pet renamed to **{display_name}**!\n"
                f"-# Original: {renamed['name']}"
            )
        else:
            message = f"✏️ **{renamed['name']}** is back to its original name."

        await interaction.response.send_message(message, ephemeral=True)
        await self.cog._refresh_pet_view(
            self.parent_message,
            self.user_id,
            self.pet_id,
            ctx=self.ctx,
        )


class PetStatsView(discord.ui.View):
    def __init__(self, cog, user_id, ctx, pets, index=0):
        super().__init__(timeout=600)
        self.cog = cog
        self.user_id = user_id
        self.ctx = ctx
        self.pets = pets
        self.index = index

    async def _ensure_owner(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This pet menu isn't for you.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="◀️ Back to Pets", style=discord.ButtonStyle.primary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return

        pets = await self.cog._get_owned_pets(self.user_id)
        if not pets:
            self.stop()
            embed = discord.Embed(
                title=f"🐾 {self.ctx.author.display_name}'s Pet Collection",
                description="Your collection is empty!",
                color=discord.Color.from_rgb(120, 140, 160),
            )
            return await interaction.response.edit_message(embed=embed, view=None)

        index = next(
            (i for i, pet in enumerate(pets) if pet["pet_id"] == self.pets[self.index]["pet_id"]),
            min(self.index, len(pets) - 1),
        )
        self.stop()
        view = PetManagementView(self.cog, self.user_id, self.ctx, pets, index)
        await interaction.response.edit_message(
            embed=self.cog._pet_embed(self.ctx, pets[index], index, len(pets)),
            view=view,
        )


class PetManagementView(discord.ui.View):
    def __init__(self, cog, user_id, ctx, pets, index=0):
        super().__init__(timeout=600)
        self.cog = cog
        self.user_id = user_id
        self.ctx = ctx
        self.pets = pets
        self.index = index
        self._sync_buttons()

    def _sync_buttons(self):
        previous = cast(discord.ui.Button, self.previous)
        next_button = cast(discord.ui.Button, self.next)
        equip = cast(discord.ui.Button, self.equip)
        favorite = cast(discord.ui.Button, self.favorite)

        previous.disabled = len(self.pets) <= 1
        next_button.disabled = len(self.pets) <= 1
        pet = self.pets[self.index]
        equip.label = "⭐ Unequip Pet" if pet["is_active"] else "⭐ Equip Pet"
        equip.style = discord.ButtonStyle.primary
        favorite.label = "🔓 Unfavorite" if pet["is_favorite"] else "🔒 Favorite"
        favorite.style = discord.ButtonStyle.primary

    async def _ensure_owner(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This pet menu isn't for you.", ephemeral=True)
            return False
        return True

    async def _refresh(self, interaction=None, message=None):
        self.pets = await self.cog._get_owned_pets(self.user_id)
        if not self.pets:
            self.stop()
            embed = discord.Embed(
                title=f"🐾 {self.ctx.author.display_name}'s Pet Collection",
                description="Your collection is empty!",
                color=discord.Color.from_rgb(120, 140, 160),
            )
            target = message or (interaction.message if interaction else None)
            if target:
                await target.edit(embed=embed, view=None)
            return
        self.index = min(self.index, len(self.pets) - 1)
        self._sync_buttons()
        target = message or (interaction.message if interaction else None)
        if target:
            await target.edit(embed=self.cog._pet_embed(self.ctx, self.pets[self.index], self.index, len(self.pets)), view=self)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary, row=2)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        self.index = (self.index - 1) % len(self.pets)
        self._sync_buttons()
        await interaction.response.edit_message(embed=self.cog._pet_embed(self.ctx, self.pets[self.index], self.index, len(self.pets)), view=self)

    @discord.ui.button(label="📊 Pet Stats", style=discord.ButtonStyle.primary, row=0)
    async def stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        pet = self.pets[self.index]
        await interaction.response.edit_message(
            embed=self.cog._pet_stats_embed(self.ctx, pet),
            view=PetStatsView(
                self.cog,
                self.user_id,
                self.ctx,
                self.pets,
                self.index,
            ),
        )

    @discord.ui.button(label="⭐ Equip Pet", style=discord.ButtonStyle.primary, row=0)
    async def equip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        pet = self.pets[self.index]
        if pet["is_active"]:
            changed = await self.cog._unequip_pet(self.user_id, pet["pet_id"])
            if not changed:
                return await interaction.response.send_message("❌ That pet is no longer equipped.", ephemeral=True)
            self.pets = await self.cog._get_owned_pets(self.user_id)
            self.index = next((i for i, p in enumerate(self.pets) if p["pet_id"] == pet["pet_id"]), self.index)
            self._sync_buttons()
            await interaction.response.edit_message(
                embed=self.cog._pet_embed(self.ctx, self.pets[self.index], self.index, len(self.pets)),
                view=self,
            )
        else:
            definition, error = await self.cog._equip_pet(self.user_id, pet["pet_id"])
            if error:
                return await interaction.response.send_message(error, ephemeral=True)
            self.pets = await self.cog._get_owned_pets(self.user_id)
            self.index = next((i for i, p in enumerate(self.pets) if p["pet_id"] == pet["pet_id"]), 0)
            self._sync_buttons()
            await interaction.response.edit_message(embed=self.cog._pet_embed(self.ctx, self.pets[self.index], self.index, len(self.pets)), view=self)

    @discord.ui.button(label="🔒 Favorite", style=discord.ButtonStyle.primary, row=1)
    async def favorite(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        pet = self.pets[self.index]
        favorited, error = await self.cog._set_pet_favorite(self.user_id, pet["pet_id"], not pet["is_favorite"])
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        self.pets = await self.cog._get_owned_pets(self.user_id)
        self.index = next((i for i, p in enumerate(self.pets) if p["pet_id"] == pet["pet_id"]), self.index)
        self._sync_buttons()
        await interaction.response.edit_message(
            embed=self.cog._pet_embed(self.ctx, self.pets[self.index], self.index, len(self.pets)),
            view=self,
        )

    @discord.ui.button(label="✏️ Rename Pet", style=discord.ButtonStyle.primary, row=1)
    async def rename(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        pet = self.pets[self.index]
        modal = RenamePetModal(
            self.cog,
            self.user_id,
            pet["pet_id"],
            interaction.message,
            self.ctx,
        )
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🔴 Release Pet", style=discord.ButtonStyle.danger, row=1)
    async def release(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        pet = self.pets[self.index]
        if pet["is_favorite"]:
            return await interaction.response.send_message(
                "🔒 **This pet is favorited and protected!** Unfavorite it first if you want to release it.",
                ephemeral=True,
            )
        await interaction.response.send_message(
            (
                f"⚠️ **Are you sure?**\n\n"
                f"You are about to permanently release **{pet['emoji']} {pet['nickname'] or pet['name']}**.\n"
                f"Level **{pet['level']}** • **{pet['xp']} XP**\n\n"
                f"This cannot be undone."
            ),
            view=ReleaseConfirmationView(self.cog, self.user_id, pet, interaction.message, self.ctx),
            ephemeral=True,
        )

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary, row=2)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        self.index = (self.index + 1) % len(self.pets)
        self._sync_buttons()
        await interaction.response.edit_message(embed=self.cog._pet_embed(self.ctx, self.pets[self.index], self.index, len(self.pets)), view=self)




class FusionVariantView(discord.ui.View):
    def __init__(self, cog, user_id, target_pet_id, base_pet_type, variant_id, ctx):
        super().__init__(timeout=120)
        self.cog = cog
        self.user_id = user_id
        self.target_pet_id = target_pet_id
        self.base_pet_type = base_pet_type
        self.variant_id = variant_id
        self.ctx = ctx

    async def _owner(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This fusion result isn't for you.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🧬 Infuse into Current Pet", style=discord.ButtonStyle.primary)
    async def infuse(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._owner(interaction):
            return
        result = await self.cog._infuse_variant(
            self.user_id, self.target_pet_id, self.base_pet_type, self.variant_id
        )
        self.stop()
        if result is None:
            return await interaction.response.edit_message(
                content="❌ That pet could no longer be found, so the variant was not infused.",
                view=None,
            )
        definition = get_pet_definition(self.base_pet_type, self.variant_id)
        if not definition:
            return await interaction.response.edit_message(
                content="❌ The variant definition could no longer be found.",
                view=None,
            )
        await interaction.response.edit_message(
            content=(
                f"🧬 **Variant Infused!**\n\n"
                f"{definition['emoji']} **{definition['name']}** is now your existing pet's form.\n"
                f"✨ Level, XP, Fusion, and passive progression were all preserved."
            ),
            view=None,
        )

    @discord.ui.button(label="📦 Keep as Separate Pet", style=discord.ButtonStyle.secondary)
    async def separate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._owner(interaction):
            return
        result = await self.cog._create_variant_pet(
            self.user_id, self.base_pet_type, self.variant_id
        )
        self.stop()
        if result is None:
            return await interaction.response.edit_message(
                content="❌ The variant could not be created as a separate pet.",
                view=None,
            )
        definition = get_pet_definition(self.base_pet_type, self.variant_id)
        if not definition:
            return await interaction.response.edit_message(
                content="❌ The variant definition could no longer be found.",
                view=None,
            )
        await interaction.response.edit_message(
            content=(
                f"📦 **Variant Kept Separately!**\n\n"
                f"{definition['emoji']} **{definition['name']}** was added to your pet collection at Level 1."
            ),
            view=None,
        )


class PostFusionConfirmView(discord.ui.View):
    def __init__(self, cog, ctx, target_pet_id):
        super().__init__(timeout=60)
        self.cog = cog
        self.ctx = ctx
        self.target_pet_id = target_pet_id

    @discord.ui.button(label="Yes, Continue", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ This fusion confirmation isn't for you.", ephemeral=True)
        self.stop()
        await interaction.response.defer()
        await self.cog._execute_pet_fusion(self.ctx, self.target_pet_id)
        try:
            await interaction.edit_original_response(view=None)
        except discord.HTTPException:
            pass

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ This fusion confirmation isn't for you.", ephemeral=True)
        self.stop()
        await interaction.response.edit_message(
            content="🧬 Fusion cancelled. Your pet and materials were not changed.",
            view=None,
        )


class Pets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # Start the background task once the cog is loaded onto the bot.
        self.incubator_checker.start()  # type: ignore[attr-defined]

    def cog_unload(self):
        if self.incubator_checker.is_running():  # type: ignore[attr-defined]
            self.incubator_checker.cancel()  # type: ignore[attr-defined]

    async def ensure_schema(self, db):
        """Add pet fields/tables without deleting existing pet data."""
        async with db.execute("PRAGMA table_info(pets)") as cursor:
            columns = {row[1] async for row in cursor}

        additions = {
            "pet_type": "TEXT DEFAULT ''",
            "is_active": "INTEGER DEFAULT 0",
            "is_favorite": "INTEGER DEFAULT 0",
            "variant_id": "TEXT DEFAULT ''",
            "fusion_level": "INTEGER DEFAULT 0",
        }

        for column, definition in additions.items():
            if column not in columns:
                await db.execute(
                    f"ALTER TABLE pets ADD COLUMN {column} {definition}"
                )

        # Preserve an old pet_stage value as the pet type when possible.
        await db.execute(
            """
            UPDATE pets
            SET pet_type = pet_stage
            WHERE COALESCE(pet_type, '') = ''
              AND COALESCE(pet_stage, '') != 'egg'
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS pet_incubators (
                incubator_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                egg_id TEXT NOT NULL,
                started_at REAL NOT NULL,
                ready_at REAL NOT NULL,
                notified INTEGER DEFAULT 0,
                slot_id INTEGER NOT NULL DEFAULT 1
            )
            """
        )

        async with db.execute("PRAGMA table_info(pet_incubators)") as cursor:
            incubator_columns = {row[1] async for row in cursor}

        if "slot_id" not in incubator_columns:
            await db.execute(
                "ALTER TABLE pet_incubators ADD COLUMN slot_id INTEGER NOT NULL DEFAULT 1"
            )

        async with db.execute("PRAGMA table_info(users)") as cursor:
            user_columns = {row[1] async for row in cursor}

        if "incubator_slots" not in user_columns:
            await db.execute(
                "ALTER TABLE users ADD COLUMN incubator_slots INTEGER DEFAULT 1"
            )

        await db.commit()

    def pet_display(self, pet):
        name = pet["nickname"] or pet["name"]
        return f"{pet['emoji']} **{name}**"

    def xp_bar(self, current, needed, length=12):
        if needed <= 0:
            return "━━━━━━━━━━━━"
        filled = max(0, min(length, int((current / needed) * length)))
        return "█" * filled + "░" * (length - filled)

    async def _owned_eggs(self, db, user_id):
        egg_ids = ["normal_egg", "halloween_egg"]
        placeholders = ",".join("?" for _ in egg_ids)
        async with db.execute(
            f"""
            SELECT item_id, quantity
            FROM inventory
            WHERE user_id = ?
              AND item_id IN ({placeholders})
              AND quantity > 0
            """,
            (user_id, *egg_ids),
        ) as cursor:
            return {row[0]: row[1] for row in await cursor.fetchall()}

    async def _incubator_rows(self, db, user_id):
        async with db.execute(
            """
            SELECT incubator_id, egg_id, started_at, ready_at, notified, slot_id
            FROM pet_incubators
            WHERE user_id = ?
            ORDER BY slot_id ASC, incubator_id ASC
            """,
            (user_id,),
        ) as cursor:
            return await cursor.fetchall()

    async def _incubator_row(self, db, user_id):
        rows = await self._incubator_rows(db, user_id)
        return rows[-1] if rows else None

    async def _get_incubator_slots(self, db, user_id):
        async with db.execute(
            "SELECT COALESCE(incubator_slots, 1) FROM users WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return max(1, min(3, int(row[0] if row else 1)))

    async def _egg_autocomplete(self, interaction, current):
        current = (current or "").lower().strip()
        choices = []
        for egg_id in ("normal_egg", "halloween_egg"):
            info = ITEM_REGISTRY.get(egg_id)
            if not info:
                continue
            if current and current not in f"{info['name']} {egg_id}".lower():
                continue
            choices.append(app_commands.Choice(
                name=f"{info['emoji']} {info['name']}",
                value=egg_id,
            ))
        return choices[:25]

    async def _incubator_egg_autocomplete(self, interaction, current):
        current = (current or "").lower().strip()
        action = getattr(getattr(interaction, "namespace", None), "action", None)
        action = str(action).lower().strip() if action else ""

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            if action == "hatch":
                rows = await self._incubator_rows(db, interaction.user.id)
                egg_ids = [row[1] for row in rows]
            else:
                owned = await self._owned_eggs(db, interaction.user.id)
                egg_ids = list(owned.keys())

        choices = []
        for egg_id in egg_ids:
            info = ITEM_REGISTRY.get(egg_id)
            if not info:
                continue
            if current and current not in f"{info['name']} {egg_id}".lower():
                continue
            choices.append(app_commands.Choice(
                name=f"{info['emoji']} {info['name']}",
                value=egg_id,
            ))
        return choices[:25]

    async def _pet_autocomplete(self, interaction, current):
        current = (current or "").lower().strip()
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            async with db.execute(
                """
                SELECT pet_id, pet_type, pet_stage, nickname, level, variant_id, fusion_level
                FROM pets
                WHERE user_id = ? AND COALESCE(pet_type, pet_stage) != 'egg'
                ORDER BY pet_id
                """,
                (interaction.user.id,),
            ) as cursor:
                rows = await cursor.fetchall()

        choices = []
        pet_counts = {}

        for pet_id, pet_type, pet_stage, nickname, level, variant_id, fusion_level in rows:
            pet_type_id = pet_type or pet_stage
            definition = get_pet_definition(pet_type_id, variant_id)
            if not definition:
                continue

            # Give duplicate pets a stable, human-readable number while
            # keeping the database pet_id as the actual autocomplete value.
            pet_counts[pet_type_id] = pet_counts.get(pet_type_id, 0) + 1
            duplicate_number = pet_counts[pet_type_id]

            display_name = nickname or definition["name"]
            search = (
                f"{display_name} {definition['name']} {pet_type_id} "
                f"{pet_id} {duplicate_number}"
            ).lower()
            if current and current not in search:
                continue

            choices.append(app_commands.Choice(
                name=(
                    f"{definition['emoji']} {display_name} "
                    f"• Lv. {level} • #{duplicate_number}"
                ),
                value=str(pet_id),
            ))

        return choices[:25]

    async def _treat_autocomplete(self, interaction, current):
        current = (current or "").lower().strip()
        treat_ids = ["pet_snack", "halloween_pet_candy"]
        choices = []

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            async with db.execute(
                """
                SELECT item_id, quantity
                FROM inventory
                WHERE user_id = ? AND item_id IN (?, ?) AND quantity > 0
                """,
                (interaction.user.id, *treat_ids),
            ) as cursor:
                owned = {row[0]: row[1] for row in await cursor.fetchall()}

        for item_id in treat_ids:
            info = ITEM_REGISTRY.get(item_id)
            if not info:
                continue
            search = f"{info['name']} {item_id}".lower()
            if current and current not in search:
                continue
            choices.append(app_commands.Choice(
                name=f"{info['emoji']} {info['name']} (x{owned.get(item_id, 0)})",
                value=item_id,
            ))

        return choices[:25]

    async def _get_owned_pets(self, user_id):
        """Return all recognized, non-egg pets owned by a user in stable order."""
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            async with db.execute(
                """
                SELECT pet_id, pet_type, pet_stage, nickname, level, xp, is_active, is_favorite, variant_id, fusion_level
                FROM pets
                WHERE user_id = ? AND COALESCE(pet_type, pet_stage) != 'egg'
                ORDER BY pet_id
                """,
                (user_id,),
            ) as cursor:
                rows = await cursor.fetchall()

        pets = []
        for pet_id, pet_type, pet_stage, nickname, level, xp, is_active, is_favorite, variant_id, fusion_level in rows:
            pet_type_id = pet_type or pet_stage
            definition = get_pet_definition(pet_type_id, variant_id)
            if not definition:
                continue
            pets.append({
                "pet_id": pet_id,
                "pet_type": pet_type_id,
                "variant_id": variant_id,
                "fusion_level": fusion_level or 0,
                "name": definition["name"],
                "emoji": definition["emoji"],
                "description": definition["description"],
                "nickname": nickname,
                "level": level or 1,
                "xp": xp or 0,
                "is_active": bool(is_active),
                "is_favorite": bool(is_favorite),
                "passive": definition.get("passive", {}),
                "normal_passive": definition.get("normal_passive", definition.get("passive", {})),
                "haunted_passive": definition.get("passive", {}) if definition.get("haunted_location") else {},
                "haunted_location": definition.get("haunted_location"),
            })
        return pets

    def _pet_stats_embed(self, ctx, pet):
        level = pet["level"]
        xp = pet["xp"]
        passive = pet.get("passive", {})
        normal_passive = pet.get("normal_passive", passive)
        haunted_passive = pet.get("haunted_passive", {})
        passive_level = passive_level_for_pet(level)
        passive_value = get_passive_value({"passive": passive, "level": level, "fusion_level": pet.get("fusion_level", 0)}, level)
        normal_value = get_passive_value({"passive": normal_passive, "level": level, "fusion_level": pet.get("fusion_level", 0)}, level)
        value_text = f"{passive_value * 100:.1f}%" if passive_value < 1 else f"{passive_value:.2f}"
        normal_value_text = f"{normal_value * 100:.1f}%" if normal_value < 1 else f"{normal_value:.2f}"

        if pet["pet_type"] in HAUNTED_PETS:
            source = "Haunted Exploration"
        elif passive.get("id") and pet["pet_type"] in HALLOWEEN_PETS:
            source = "Halloween Egg"
        else:
            source = "Normal Egg"

        embed = discord.Embed(
            title=f"📊 {pet['emoji']} {pet['nickname'] or pet['name']} — Stats",
            color=discord.Color.from_rgb(120, 140, 160),
        )
        embed.add_field(
            name="📈 Progression",
            value=(
                f"**Level:** {level}\n"
                f"**XP:** {xp}/{xp_needed_for_next_level(level)}\n"
                f"**Passive Level:** {passive_level}/{PET_PASSIVE_MAX_LEVEL}"
            ),
            inline=False,
        )

        has_dual_passive = bool(
            normal_passive
            and passive
            and normal_passive.get("id") != passive.get("id")
        )

        if has_dual_passive:
            embed.add_field(
                name=f"✨ Normal Passive — {normal_passive.get('name', 'Unknown')}",
                value=(
                    f"{normal_passive.get('description', 'No passive description.')}\n"
                    f"**Current Strength:** {normal_value_text}"
                ),
                inline=False,
            )

            if pet["pet_type"] in HAUNTED_PETS and haunted_passive:
                secondary_label = "👻 Haunted Passive"
                secondary_extra = (
                    f"\n**Location:** {pet.get('haunted_location', 'Associated Haunted location')}"
                )
            else:
                secondary_label = "🎃 Halloween Passive"
                secondary_extra = ""

            embed.add_field(
                name=f"{secondary_label} — {passive.get('name', 'Unknown')}",
                value=(
                    f"{passive.get('description', 'No passive description.')}\n"
                    f"**Current Strength:** {value_text}"
                    f"{secondary_extra}"
                ),
                inline=False,
            )
        else:
            embed.add_field(
                name=f"✨ {passive.get('name', 'Unknown Passive')}",
                value=(
                    f"{passive.get('description', 'No passive description.')}\n"
                    f"**Current Strength:** {value_text}"
                ),
                inline=False,
            )

        embed.add_field(
            name="🐣 Origin",
            value=f"**{source}**\n{'⭐ Equipped' if pet['is_active'] else 'Not equipped'}",
            inline=False,
        )
        embed.set_footer(text="Use ◀️ Back to return to your pet menu.")
        return embed

    def _pet_embed(self, ctx, pet, page, total):
        level = pet["level"]
        xp = pet["xp"]
        needed = xp_needed_for_next_level(level)
        passive = pet.get("passive", {})
        normal_passive = pet.get("normal_passive", passive)
        haunted_passive = pet.get("haunted_passive", {})
        passive_level = passive_level_for_pet(level)
        passive_value = get_passive_value({"passive": passive, "level": level, "fusion_level": pet.get("fusion_level", 0)}, level)
        normal_value = get_passive_value({"passive": normal_passive, "level": level, "fusion_level": pet.get("fusion_level", 0)}, level)
        value_text = f"{passive_value * 100:.1f}%" if passive_value < 1 else f"{passive_value:.2f}"
        normal_value_text = f"{normal_value * 100:.1f}%" if normal_value < 1 else f"{normal_value:.2f}"
        display_name = pet["nickname"] or pet["name"]
        active_text = "⭐ **ACTIVE COMPANION**" if pet["is_active"] else "Not currently equipped"

        embed = discord.Embed(
            title=f"🐾 {ctx.author.display_name}'s Pet",
            description=(
                f"{pet['emoji']} **{display_name}**\n"
                + (f"-# Original: {pet['name']}\n" if pet["nickname"] else "")
                + f"*{pet['description']}*\n\n"
                + ("🔒 **FAVORITED — PROTECTED FROM RELEASE**" if pet["is_favorite"] else "-# 🔒 Favorite this pet to lock it and prevent accidental release.")
                + f"\n{active_text}"
            ),
            color=discord.Color.from_rgb(120, 140, 160),
        )
        embed.add_field(
            name="📈 Level & XP",
            value=(
                f"**Level {level}**\n"
                f"`{self.xp_bar(xp, needed)}`\n"
                f"**{xp}/{needed} XP** to Level {level + 1}"
            ),
            inline=False,
        )
        if pet.get("variant_id"):
            variant = get_variant_info(pet["pet_type"], pet["variant_id"])
            if variant:
                embed.add_field(
                    name=f"{variant['emoji']} Variant",
                    value=f"**{variant['name']}**\n{variant['lore']}",
                    inline=False,
                )

        fusion_level = int(pet.get("fusion_level", 0) or 0)
        if fusion_level:
            bonus = fusion_level * 2
            embed.add_field(
                name="🧬 Fusion",
                value=(
                    f"**Fusion {fusion_level}/5** • Passive strength **+{bonus}%**\n"
                    "Further fusions after Fusion 5 only hunt for variants."
                ),
                inline=False,
            )
        has_dual_passive = bool(
            normal_passive
            and passive
            and normal_passive.get("id") != passive.get("id")
        )

        if has_dual_passive:
            embed.add_field(
                name=f"✨ Normal Passive — {normal_passive.get('name', 'Unknown')}",
                value=(
                    f"**Passive Level {passive_level}/{PET_PASSIVE_MAX_LEVEL}**\n"
                    f"{normal_passive.get('description', 'No passive description.')}\n"
                    f"Current strength: **{normal_value_text}**"
                ),
                inline=False,
            )

            if pet["pet_type"] in HAUNTED_PETS and haunted_passive:
                secondary_label = "👻 Haunted Passive"
                secondary_extra = (
                    f"\nOnly active in: **{pet.get('haunted_location', 'Associated Haunted location')}**"
                )
            else:
                secondary_label = "🎃 Halloween Passive"
                secondary_extra = ""

            embed.add_field(
                name=f"{secondary_label} — {passive.get('name', 'Unknown')}",
                value=(
                    f"**Passive Level {passive_level}/{PET_PASSIVE_MAX_LEVEL}**\n"
                    f"{passive.get('description', 'No passive description.')}\n"
                    f"Current strength: **{value_text}**"
                    f"{secondary_extra}"
                ),
                inline=False,
            )
        else:
            embed.add_field(
                name=f"✨ Passive — {passive.get('name', 'Unknown Passive')}",
                value=(
                    f"**Passive Level {passive_level}/{PET_PASSIVE_MAX_LEVEL}**\n"
                    f"{passive.get('description', 'No passive description.')}\n"
                    f"Current strength: **{value_text}**"
                ),
                inline=False,
            )
        embed.add_field(
            name="🍪 Treat XP",
            value=(
                f"🍖 Pet Treat — **+{PET_TREAT_XP} XP**\n"
                f"🎃 Halloween Pet Candy — **+{HALLOWEEN_PET_CANDY_XP} XP**"
            ),
            inline=False,
        )
        embed.add_field(
            name="🍽️ Feed Your Pet",
            value="Use **`/feed <pet> <treat> <quantity>`** to give this pet XP.",
            inline=False,
        )
        embed.set_footer(text=f"Pet {page + 1}/{total} • Pets can level beyond Passive Level 5; passive strength caps at 5 for now.")
        return embed

    async def _feed_specific_pet(self, user_id, pet_id, treat, quantity=1):
        xp_amounts = {
            "pet_snack": PET_TREAT_XP,
            "halloween_pet_candy": HALLOWEEN_PET_CANDY_XP,
        }
        if treat not in xp_amounts:
            return None, "❌ That isn't a valid pet treat."
        if not isinstance(quantity, int) or quantity < 1 or quantity > 99:
            return None, "❌ Quantity must be between **1** and **99**."

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")

            async with db.execute(
                """
                SELECT pet_id, pet_type, pet_stage, nickname, level, xp, is_active
                FROM pets
                WHERE user_id = ? AND pet_id = ?
                LIMIT 1
                """,
                (user_id, pet_id),
            ) as cursor:
                row = await cursor.fetchone()

            if not row or (row[1] or row[2]) == "egg":
                await db.rollback()
                return None, "❌ That pet no longer exists in your collection."

            definition = get_pet_definition(row[1] or row[2])
            if not definition:
                await db.rollback()
                return None, "❌ That pet is no longer configured."

            async with db.execute(
                "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                (user_id, treat),
            ) as cursor:
                treat_row = await cursor.fetchone()

            owned_quantity = int(treat_row[0])
            if owned_quantity < quantity:
                await db.rollback()
                return None, (
                    f"❌ You only have **{owned_quantity}** "
                    f"of **{ITEM_REGISTRY[treat]['name']}**, but you tried to use **{quantity}**."
                )

            pet = {
                "pet_id": row[0],
                "pet_type": row[1] or row[2],
                "name": definition["name"],
                "emoji": definition["emoji"],
                "description": definition["description"],
                "nickname": row[3],
                "level": row[4] or 1,
                "xp": row[5] or 0,
                "is_active": bool(row[6]),
                "passive": definition.get("passive", {}),
            }
            base_xp = xp_amounts[treat]
            old_level = pet["level"]
            new_level = old_level
            new_xp = pet["xp"]
            xp_amount = 0

            # Apply treats one at a time so a large quantity behaves exactly
            # like feeding the same treats individually, including passive
            # bonuses changing when the pet levels up.
            for _ in range(quantity):
                treat_bonus = 0.0
                if pet["passive"].get("id") == "treat_xp_bonus":
                    treat_bonus = get_passive_value(
                        {
                            "passive": pet["passive"],
                            "level": new_level,
                            "fusion_level": pet.get("fusion_level", 0),
                        },
                        new_level,
                    )
                single_xp = int(base_xp * (1 + treat_bonus))
                xp_amount += single_xp
                new_xp += single_xp
                while new_xp >= xp_needed_for_next_level(new_level):
                    new_xp -= xp_needed_for_next_level(new_level)
                    new_level += 1

            await db.execute(
                "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?",
                (quantity, user_id, treat),
            )
            await db.execute(
                "DELETE FROM inventory WHERE user_id = ? AND item_id = ? AND quantity <= 0",
                (user_id, treat),
            )

            await db.execute(
                "UPDATE pets SET level = ?, xp = ? WHERE pet_id = ? AND user_id = ?",
                (new_level, new_xp, pet_id, user_id),
            )
            await db.commit()

        return {
            "pet": pet,
            "treat": ITEM_REGISTRY[treat],
            "quantity": quantity,
            "xp_amount": xp_amount,
            "old_level": old_level,
            "new_level": new_level,
            "leveled_up": new_level > old_level,
            "passive_level": passive_level_for_pet(new_level),
        }, None

    @commands.hybrid_command(
        name="feed",
        description="Feed a pet treats to give it XP.",
    )
    @app_commands.describe(
        pet="Choose the pet to feed.",
        treat="Choose the treat to use.",
        quantity="How many treats to use (1-99).",
    )
    @app_commands.autocomplete(pet=_pet_autocomplete, treat=_treat_autocomplete)
    async def feed(
        self,
        ctx: commands.Context,
        pet: str,
        treat: str,
        quantity: int,
    ):
        await ctx.defer()

        try:
            pet_id = int(pet)
        except (TypeError, ValueError):
            return await ctx.send("❌ Please choose a valid pet from the autocomplete list.")

        result, error = await self._feed_specific_pet(
            ctx.author.id,
            pet_id,
            treat.lower().strip(),
            quantity,
        )
        if error:
            return await ctx.send(error)
        if result is None:
            return await ctx.send("❌ Feeding failed because no result was returned.")

        fed_pet = result["pet"]
        level_line = ""
        if result["leveled_up"]:
            level_line = (
                f"\n🎉 **Level Up!** Your pet reached **Level {result['new_level']}**!"
                f"\n✨ Passive is now **Level {result['passive_level']}/{PET_PASSIVE_MAX_LEVEL}**."
            )

        await ctx.send(
            f"{fed_pet['emoji']} **{fed_pet['nickname'] or fed_pet['name']}** enjoyed "
            f"**{result['quantity']}× {result['treat']['name']}**!\n"
            f"✨ **+{result['xp_amount']} Pet XP**{level_line}"
        )

    async def _equip_pet(self, user_id, pet_id):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")
            async with db.execute(
                "SELECT pet_type, pet_stage FROM pets WHERE user_id = ? AND pet_id = ? LIMIT 1",
                (user_id, pet_id),
            ) as cursor:
                row = await cursor.fetchone()
            if not row:
                await db.rollback()
                return None, "❌ That pet no longer exists in your collection."
            definition = get_pet_definition(row[0] or row[1])
            if not definition:
                await db.rollback()
                return None, "❌ That pet is no longer configured."
            await db.execute("UPDATE pets SET is_active = 0 WHERE user_id = ?", (user_id,))
            await db.execute("UPDATE pets SET is_active = 1 WHERE user_id = ? AND pet_id = ?", (user_id, pet_id))
            await db.commit()
        return definition, None

    async def _unequip_pet(self, user_id, pet_id):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute(
                "UPDATE pets SET is_active = 0 WHERE user_id = ? AND pet_id = ? AND is_active = 1",
                (user_id, pet_id),
            )
            changed = cursor.rowcount
            await db.commit()
        return changed > 0

    async def _rename_pet(self, user_id, pet_id, nickname):
        nickname = nickname.strip()
        if len(nickname) > 30:
            return None

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")
            async with db.execute(
                """
                SELECT pet_type, pet_stage
                FROM pets
                WHERE user_id = ? AND pet_id = ?
                LIMIT 1
                """,
                (user_id, pet_id),
            ) as cursor:
                row = await cursor.fetchone()

            if not row or (row[0] or row[1]) == "egg":
                await db.rollback()
                return None

            definition = get_pet_definition(row[0] or row[1])
            if not definition:
                await db.rollback()
                return None

            await db.execute(
                """
                UPDATE pets
                SET nickname = ?
                WHERE user_id = ? AND pet_id = ?
                """,
                (nickname, user_id, pet_id),
            )
            await db.commit()

        return {
            "pet_id": pet_id,
            "name": definition["name"],
            "nickname": nickname,
            "emoji": definition["emoji"],
        }

    async def _set_pet_favorite(self, user_id, pet_id, favorite):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")
            async with db.execute(
                "SELECT pet_type, pet_stage FROM pets WHERE user_id = ? AND pet_id = ? LIMIT 1",
                (user_id, pet_id),
            ) as cursor:
                row = await cursor.fetchone()
            if not row or (row[0] or row[1]) == "egg":
                await db.rollback()
                return False, "❌ That pet no longer exists in your collection."
            if not get_pet_definition(row[0] or row[1]):
                await db.rollback()
                return False, "❌ That pet is no longer configured."
            await db.execute(
                "UPDATE pets SET is_favorite = ? WHERE user_id = ? AND pet_id = ?",
                (1 if favorite else 0, user_id, pet_id),
            )
            await db.commit()
        return bool(favorite), None


    async def _release_pet(self, user_id, pet_id):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")
            async with db.execute(
                """
                SELECT pet_type, pet_stage, nickname, level, xp, is_active, is_favorite, variant_id, fusion_level
                FROM pets
                WHERE user_id = ? AND pet_id = ?
                LIMIT 1
                """,
                (user_id, pet_id),
            ) as cursor:
                row = await cursor.fetchone()
            if not row:
                await db.rollback()
                return None
            if row[6]:
                await db.rollback()
                return {"protected": True}
            pet_type = row[0] or row[1]
            variant_id = row[7] or None
            definition = get_pet_definition(pet_type, variant_id)
            if not definition:
                await db.rollback()
                return None

            essence_awarded = False
            if random.random() < RELEASE_ESSENCE_CHANCE:
                added_essence, _quantity, _max_quantity = await add_inventory_item(
                    db, user_id, ASTRAL_ESSENCE_ID, "special", 1
                )
                essence_awarded = added_essence > 0

            await db.execute(
                "DELETE FROM pets WHERE user_id = ? AND pet_id = ?",
                (user_id, pet_id),
            )
            await db.commit()
        return {
            "pet_id": pet_id,
            "name": definition["name"],
            "emoji": definition["emoji"],
            "nickname": row[2],
            "level": row[3] or 1,
            "xp": row[4] or 0,
            "is_active": bool(row[5]),
            "essence_awarded": essence_awarded,
        }

    async def _infuse_variant(self, user_id, pet_id, base_pet_type, variant_id):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")
            async with db.execute(
                "SELECT pet_type, variant_id FROM pets WHERE user_id = ? AND pet_id = ? LIMIT 1",
                (user_id, pet_id),
            ) as cursor:
                row = await cursor.fetchone()

            if not row or (row[0] or "") != base_pet_type:
                await db.rollback()
                return None

            await db.execute(
                "UPDATE pets SET variant_id = ? WHERE user_id = ? AND pet_id = ?",
                (variant_id, user_id, pet_id),
            )
            await db.commit()

        return True

    async def _create_variant_pet(self, user_id, base_pet_type, variant_id):
        definition = get_pet_definition(base_pet_type)
        variant_info = get_variant_info(base_pet_type, variant_id)
        if not definition or not variant_info:
            return None

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")

            await db.execute(
                """
                INSERT INTO pets
                    (user_id, pet_stage, pet_type, nickname, level, xp, is_active, is_favorite, variant_id, fusion_level)
                VALUES (?, ?, ?, '', 1, 0, 0, 0, ?, 0)
                """,
                (user_id, base_pet_type, base_pet_type, variant_id),
            )
            await db.commit()

        return True

    async def _pet_fuse_autocomplete(self, interaction, current):
        current = (current or "").lower().strip()

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            async with db.execute(
                """
                SELECT pet_id, pet_type, pet_stage, nickname, level, variant_id, fusion_level, is_favorite
                FROM pets
                WHERE user_id = ? AND COALESCE(pet_type, pet_stage) != 'egg'
                ORDER BY pet_id
                """,
                (interaction.user.id,),
            ) as cursor:
                rows = await cursor.fetchall()

        choices = []

        for pet_id, pet_type, pet_stage, nickname, level, variant_id, fusion_level, is_favorite in rows:
            pet_type_id = pet_type or pet_stage
            if pet_type_id not in PETS and pet_type_id not in HALLOWEEN_PETS:
                continue

            definition = get_pet_definition(pet_type_id, variant_id)
            if not definition:
                continue

            matching_duplicates = sum(
                1
                for other_id, other_type, other_stage, _nickname, _level, other_variant_id, _fusion, other_favorite in rows
                if other_id != pet_id
                and (other_type or other_stage) == pet_type_id
                and (other_variant_id or "") == (variant_id or "")
                and not other_favorite
            )

            if matching_duplicates < 5:
                continue

            display_name = nickname or definition["name"]
            fusion = int(fusion_level or 0)
            search = (
                f"{display_name} {definition['name']} {pet_type_id} "
                f"{pet_id} {fusion} {variant_id or ''}"
            ).lower()
            if current and current not in search:
                continue

            variant_label = f" • {variant_id}" if variant_id else ""
            choices.append(app_commands.Choice(
                name=(
                    f"{definition['emoji']} {display_name}"
                    f"{variant_label} • Fusion {fusion}/5 • {matching_duplicates} duplicates"
                )[:100],
                value=str(pet_id),
            ))

        return choices[:25]

    @commands.hybrid_command(
        name="pet_fuse",
        description="Fuse five matching duplicate pets to strengthen one or hunt for a rare variant.",
    )
    @app_commands.describe(pet="Choose the pet you want to fuse.")
    @app_commands.autocomplete(pet=_pet_fuse_autocomplete)
    async def pet_fuse(self, ctx: commands.Context, pet: str):
        await ctx.defer()
        try:
            target_pet_id = int(pet)
        except (TypeError, ValueError):
            return await ctx.send("❌ That pet selection is invalid.")

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            async with db.execute(
                "SELECT fusion_level, pet_type, variant_id FROM pets WHERE user_id = ? AND pet_id = ? LIMIT 1",
                (ctx.author.id, target_pet_id),
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            return await ctx.send("❌ You don't own that pet.")

        fusion_level = int(row[0] or 0)
        if fusion_level >= 5:
            definition = get_pet_definition(row[1] or "", row[2] or None)
            display = definition["name"] if definition else "this pet"
            return await ctx.send(
                f"🧬 **{display} has reached maximum Fusion 5.**\n\n"
                "Further fusions will **not** increase its passive bonus. "
                "They only give you another chance to discover a rare variant.\n\n"
                "This attempt will consume **5 matching duplicates**, **15,000 Stardust**, and **3 Astral Essence**.\n\n"
                "Continue?",
                view=PostFusionConfirmView(self, ctx, target_pet_id),
            )

        return await self._execute_pet_fusion(ctx, target_pet_id)

    async def _execute_pet_fusion(self, ctx: commands.Context, target_pet_id: int):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")

            async with db.execute(
                """
                SELECT pet_id, pet_type, nickname, level, xp, variant_id, fusion_level, is_favorite
                FROM pets
                WHERE user_id = ? AND pet_id = ?
                LIMIT 1
                """,
                (ctx.author.id, target_pet_id),
            ) as cursor:
                target = await cursor.fetchone()

            if not target:
                await db.rollback()
                return await ctx.send("❌ You don't own that pet.")

            pet_type = target[1] or ""
            if pet_type not in PETS and pet_type not in HALLOWEEN_PETS:
                await db.rollback()
                return await ctx.send(
                    "❌ This pet cannot be fused. Haunted location pets are unique companions."
                )

            level = int(target[3] or 1)
            fusion_level = int(target[6] or 0)
            variant_id = target[5] or ""

            if fusion_level < 5:
                next_fusion = fusion_level + 1
                required_level = FUSION_LEVEL_GATES[next_fusion]
                if level < required_level:
                    await db.rollback()
                    return await ctx.send(
                        f"🔒 **Fusion {next_fusion}** unlocks at **Level {required_level}**. "
                        f"This pet is currently **Level {level}**."
                    )
                cost = FUSION_COSTS[next_fusion]
                cost_label = f"Fusion {next_fusion}/5"
            else:
                next_fusion = 5
                cost = VARIANT_HUNT_COST
                cost_label = "Variant Hunt"

            async with db.execute(
                """
                SELECT pet_id
                FROM pets
                WHERE user_id = ?
                  AND pet_id != ?
                  AND pet_type = ?
                  AND COALESCE(variant_id, '') = ?
                  AND COALESCE(is_favorite, 0) = 0
                ORDER BY pet_id
                LIMIT 5
                """,
                (ctx.author.id, target_pet_id, pet_type, variant_id),
            ) as cursor:
                duplicate_rows = await cursor.fetchall()

            if len(duplicate_rows) < 5:
                await db.rollback()
                variant_text = " with the same variant" if variant_id else ""
                return await ctx.send(
                    f"❌ You need **5 non-favorited duplicates** of this pet{variant_text}. "
                    f"You currently have **{len(duplicate_rows)}/5** available."
                )

            async with db.execute(
                "SELECT COALESCE(stardust, 0) FROM users WHERE user_id = ?",
                (ctx.author.id,),
            ) as cursor:
                balance_row = await cursor.fetchone()
            stardust = int(balance_row[0] or 0) if balance_row else 0
            if stardust < cost["stardust"]:
                await db.rollback()
                return await ctx.send(
                    f"💸 **Insufficient Stardust!** {cost_label} costs **{cost['stardust']:,}** Stardust. "
                    f"You have **{stardust:,}**."
                )

            async with db.execute(
                "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                (ctx.author.id, ASTRAL_ESSENCE_ID),
            ) as cursor:
                essence_row = await cursor.fetchone()
            essence_owned = int(essence_row[0] or 0) if essence_row else 0
            if essence_owned < cost["essence"]:
                await db.rollback()
                return await ctx.send(
                    f"✨ **Not enough Astral Essence!** {cost_label} needs **{cost['essence']}** Essence. "
                    f"You have **{essence_owned}**."
                )

            await db.execute(
                "UPDATE users SET stardust = stardust - ? WHERE user_id = ?",
                (cost["stardust"], ctx.author.id),
            )
            await db.execute(
                """
                UPDATE inventory
                SET quantity = quantity - ?
                WHERE user_id = ? AND item_id = ?
                """,
                (cost["essence"], ctx.author.id, ASTRAL_ESSENCE_ID),
            )
            await db.execute(
                "DELETE FROM inventory WHERE user_id = ? AND item_id = ? AND quantity <= 0",
                (ctx.author.id, ASTRAL_ESSENCE_ID),
            )

            duplicate_ids = [row[0] for row in duplicate_rows]
            placeholders = ",".join("?" for _ in duplicate_ids)
            await db.execute(
                f"DELETE FROM pets WHERE user_id = ? AND pet_id IN ({placeholders})",
                [ctx.author.id, *duplicate_ids],
            )

            if fusion_level < 5:
                await db.execute(
                    "UPDATE pets SET fusion_level = ? WHERE user_id = ? AND pet_id = ?",
                    (next_fusion, ctx.author.id, target_pet_id),
                )

            discovered_variant = roll_fusion_variant(pet_type, fusion_level, exclude_variant=variant_id)
            if discovered_variant:
                from collectibles import record_collectible
                await record_collectible(
                    db, self.bot, ctx.author.id,
                    f"pet_variant:{pet_type}:{discovered_variant}",
                    category="Pet Variants",
                )

            await db.commit()

        target_definition = get_pet_definition(pet_type, variant_id)
        if not target_definition:
            return await ctx.send("❌ The fused pet definition could no longer be found.")

        if not discovered_variant:
            if fusion_level < 5:
                return await ctx.send(
                    f"🧬 **Fusion complete!** {target_definition['emoji']} **{target_definition['name']}** "
                    f"is now **Fusion {next_fusion}/5**.\n"
                    f"✨ Passive strength increased by **+2%**.\n\n"
                    f"Consumed **5 duplicates**, **{cost['stardust']:,} Stardust**, and **{cost['essence']} Astral Essence**."
                )
            return await ctx.send(
                f"🧬 **Variant Hunt complete!** No new variant was discovered this time.\n\n"
                f"Consumed **5 duplicates**, **{cost['stardust']:,} Stardust**, and **{cost['essence']} Astral Essence**."
            )

        variant_info = get_variant_info(pet_type, discovered_variant)
        variant_definition = get_pet_definition(pet_type, discovered_variant)
        if not variant_info or not variant_definition:
            return await ctx.send("❌ The discovered variant could no longer be loaded.")

        await ctx.send(
            content=(
                f"🎉 **RARE VARIANT DISCOVERED!**\n\n"
                f"{variant_info['emoji']} **{variant_definition['name']}**\n"
                f"> {variant_info['lore']}\n\n"
                "What would you like to do with it?\n"
                "🧬 **Infuse** preserves the current pet's Level, XP, Fusion, and passive progression.\n"
                "📦 **Keep Separate** creates a fresh Level 1 copy."
            ),
            view=FusionVariantView(
                self, ctx.author.id, target_pet_id, pet_type, discovered_variant, ctx
            ),
        )

    @commands.hybrid_command(name="pets", description="View and manage your pet collection.")
    async def pets(self, ctx: commands.Context):
        await ctx.defer()
        pets = await self._get_owned_pets(ctx.author.id)
        if not pets:
            embed = discord.Embed(
                title=f"🐾 {ctx.author.display_name}'s Pet Collection",
                description=(
                    "Your collection is empty!\n\n"
                    "🥚 Eggs can be discovered during scavenging.\n"
                    "⏳ Use `/incubator` with **Start incubation** to begin incubation."
                ),
                color=discord.Color.from_rgb(120, 140, 160),
            )
            return await ctx.send(embed=embed)

        view = PetManagementView(self, ctx.author.id, ctx, pets, 0)
        await ctx.send(embed=self._pet_embed(ctx, pets[0], 0, len(pets)), view=view)

    async def _refresh_pet_view(self, message, user_id, pet_id, allow_missing=False, ctx=None):
        if not message or ctx is None:
            return
        pets = await self._get_owned_pets(user_id)
        if not pets:
            embed = discord.Embed(
                title=f"🐾 {ctx.author.display_name}'s Pet Collection",
                description="Your collection is empty!",
                color=discord.Color.from_rgb(120, 140, 160),
            )
            try:
                await message.edit(embed=embed, view=None)
            except discord.HTTPException:
                pass
            return
        index = next((i for i, pet in enumerate(pets) if pet["pet_id"] == pet_id), min(len(pets) - 1, 0))
        view = PetManagementView(self, user_id, ctx, pets, index)
        try:
            await message.edit(embed=self._pet_embed(ctx, pets[index], index, len(pets)), view=view)
        except discord.HTTPException:
            pass

    @commands.hybrid_command(
        name="incubator",
        description="View and manage your pet egg incubators.",
    )
    @app_commands.describe(
        action="Choose Start to begin incubation or Hatch to claim a ready egg.",
        egg="Choose the egg to start or hatch.",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Start incubation", value="start"),
            app_commands.Choice(name="Hatch ready egg", value="hatch"),
        ]
    )
    @app_commands.autocomplete(egg=_incubator_egg_autocomplete)
    async def incubator(
        self,
        ctx: commands.Context,
        action: str | None = None,
        egg: str | None = None,
    ):
        """View the incubator bay, start an egg, or hatch a ready egg."""
        await ctx.defer()

        action = action.lower().strip() if action else None
        egg = egg.lower().strip() if egg else None

        if action == "start":
            if not egg:
                return await ctx.send("❌ Choose an egg to start incubating.")
            return await self._incubator_start(ctx, egg)

        if action == "hatch":
            if not egg:
                return await ctx.send("❌ Choose an egg to hatch.")
            return await self._incubator_hatch(ctx, egg)

        if action is not None:
            return await ctx.send("❌ Choose **Start** or **Hatch** as the incubator action.")

        if egg:
            return await ctx.send("❌ Choose **Start** or **Hatch** when providing an egg.")

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            slots = await self._get_incubator_slots(db, ctx.author.id)
            rows = await self._incubator_rows(db, ctx.author.id)
            eggs = await self._owned_eggs(db, ctx.author.id)

        by_slot = {int(row[5]): row for row in rows}
        embed = discord.Embed(
            title=f"🥚 {ctx.author.display_name}'s Pet Incubation Bay",
            color=discord.Color.from_rgb(120, 140, 160),
        )

        tube_titles = ["🧪 TUBE I", "🧪 TUBE II", "🧪 TUBE III"]

        for slot_id in range(1, 4):
            if slot_id > slots:
                tube_art = (
                    "```text\n"
                    "╭────────╮\n"
                    "│  🧪    │\n"
                    "│        │\n"
                    "│   🔒   │\n"
                    "│ LOCKED │\n"
                    "│        │\n"
                    "│        │\n"
                    "╰────────╯\n"
                    "```"
                    "🔒 **Locked**\n"
                    "Unlock in `/shop` → 🛠️ Upgrades"
                )
                embed.add_field(name=tube_titles[slot_id - 1], value=tube_art, inline=True)
                continue

            row = by_slot.get(slot_id)
            if not row:
                tube_art = (
                    "```text\n"
                    "╭────────╮\n"
                    "│  🧪    │\n"
                    "│        │\n"
                    "│   ·    │\n"
                    "│        │\n"
                    "│        │\n"
                    "│        │\n"
                    "╰────────╯\n"
                    "```"
                    "🟢 **Empty**\n"
                    "Use `/incubator` with **Start incubation** and choose an egg"
                )
                embed.add_field(name=tube_titles[slot_id - 1], value=tube_art, inline=True)
                continue

            _incubator_id, egg_id, _started_at, ready_at, _notified, _slot_id = row
            info = ITEM_REGISTRY.get(egg_id, {"name": egg_id, "emoji": "🥚"})
            remaining = max(0, int(ready_at - time.time()))

            # Fill the lower part of the tube as incubation progresses.
            progress = max(0.0, min(1.0, 1 - (remaining / INCUBATION_SECONDS)))
            filled_rows = round(progress * 2)
            liquid_rows = {
                "full": "▓▓▓▓▓▓",
                "empty": "░░░░░░",
            }
            liquid = []
            for row_index in range(2):
                liquid.append(
                    liquid_rows["full"] if row_index >= 2 - filled_rows else liquid_rows["empty"]
                )

            if remaining <= 0:
                status = "✨ **READY TO HATCH!**"
                instruction = f"Use `/incubator` with **Hatch ready egg** and choose **{egg_id}**"
            else:
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                seconds = remaining % 60
                status = f"⏳ **{hours}h {minutes}m {seconds}s**"
                instruction = "🔔 Alert when ready"

            tube_art = (
                "```text\n"
                "╭────────╮\n"
                "│  🧪    │\n"
                "│        │\n"
               f"│   {info['emoji']}   │\n"
                "│        │\n"
               f"│ {liquid[0]} │\n"
               f"│ {liquid[1]} │\n"
                "╰────────╯\n"
                "```"
                f"{info['emoji']} **{info['name']}**\n"
                f"{status}\n"
                f"{instruction}"
            )
            embed.add_field(name=tube_titles[slot_id - 1], value=tube_art, inline=True)

        if eggs:
            egg_lines = []
            for egg_id, quantity in eggs.items():
                info = ITEM_REGISTRY.get(egg_id)
                if info:
                    egg_lines.append(f"{info['emoji']} **{info['name']}** ×{quantity}")
            if egg_lines:
                embed.add_field(
                    name="🥚 Eggs in Storage",
                    value="\n".join(egg_lines),
                    inline=False,
                )

        embed.set_footer(text=f"Unlocked tubes: {slots}/3 • Incubation time: 12 hours")
        await ctx.send(embed=embed)

    async def _incubator_start(self, ctx: commands.Context, egg: str):
        egg = egg.lower().strip()

        if egg not in EGG_POOLS:
            return await ctx.send("❌ That isn't a valid pet egg.")

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")

            slots = await self._get_incubator_slots(db, ctx.author.id)
            rows = await self._incubator_rows(db, ctx.author.id)
            occupied_slots = {int(row[5]) for row in rows}
            available_slot = next(
                (slot_id for slot_id in range(1, slots + 1) if slot_id not in occupied_slots),
                None,
            )

            if available_slot is None:
                return await ctx.send(
                    "⏳ All unlocked incubator tubes are occupied! "
                    "Use `/incubator` to check their status."
                )

            async with db.execute(
                "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                (ctx.author.id, egg),
            ) as cursor:
                row = await cursor.fetchone()

            if not row or row[0] <= 0:
                return await ctx.send("❌ You don't have that egg in your inventory.")

            await db.execute(
                "UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_id = ?",
                (ctx.author.id, egg),
            )
            await db.execute(
                "DELETE FROM inventory WHERE user_id = ? AND item_id = ? AND quantity <= 0",
                (ctx.author.id, egg),
            )

            started = time.time()
            ready = started + INCUBATION_SECONDS
            await db.execute(
                """
                INSERT INTO pet_incubators
                    (user_id, egg_id, started_at, ready_at, notified, slot_id)
                VALUES (?, ?, ?, ?, 0, ?)
                """,
                (ctx.author.id, egg, started, ready, available_slot),
            )
            await db.commit()

        info = ITEM_REGISTRY[egg]
        await ctx.send(
            f"{ctx.author.mention} {info['emoji']} **{info['name']} is now incubating in Tube {available_slot}!**\n"
            "⏳ Incubation time: **12 hours**\n"
            "🔔 I'll alert you when it's ready to hatch!\n"
            f"Use `/incubator` with **Hatch ready egg** and choose **{egg}** when the timer finishes."
        )

    async def _incubator_hatch(self, ctx: commands.Context, egg: str):
        egg = egg.lower().strip()

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            rows = await self._incubator_rows(db, ctx.author.id)

            row = next((candidate for candidate in rows if candidate[1] == egg), None)
            if not row:
                return await ctx.send(
                    f"❌ None of your incubator tubes currently contains **{egg}**."
                )

            _incubator_id, stored_egg, _started_at, ready_at, _notified, slot_id = row

            if time.time() < ready_at:
                remaining = int(ready_at - time.time())
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                return await ctx.send(
                    f"⏳ That egg in **Tube {slot_id}** isn't ready yet! "
                    f"**{hours}h {minutes}m** remaining."
                )

            pool = EGG_POOLS.get(stored_egg, [])
            if not pool:
                return await ctx.send("❌ This egg currently has no pets configured.")

            pet_type = random.choice(pool)
            variant_id = roll_hatched_variant(pet_type)
            definition = get_pet_definition(pet_type, variant_id)
            if not definition:
                return await ctx.send("❌ This egg points to a pet that is not currently configured.")

            async with db.execute(
                "SELECT 1 FROM pets WHERE user_id = ? AND is_active = 1 LIMIT 1",
                (ctx.author.id,),
            ) as cursor:
                has_active = await cursor.fetchone()

            await db.execute(
                """
                INSERT INTO pets
                    (user_id, pet_stage, pet_type, nickname, level, xp, is_active, variant_id, fusion_level)
                VALUES (?, ?, ?, '', 1, 0, ?, ?, 0)
                """,
                (ctx.author.id, pet_type, pet_type, 0 if has_active else 1, variant_id or ""),
            )

            variant_discovered = False
            if variant_id:
                from collectibles import record_collectible
                await record_collectible(
                    db, self.bot, ctx.author.id,
                    f"pet_variant:{pet_type}:{variant_id}",
                    category="Pet Variants",
                )
                variant_discovered = True

            essence_awarded = False
            if random.random() < HATCH_ESSENCE_CHANCE:
                added_essence, _quantity, _max_quantity = await add_inventory_item(
                    db, ctx.author.id, ASTRAL_ESSENCE_ID, "special", 1
                )
                essence_awarded = added_essence > 0
            await db.execute(
                "DELETE FROM pet_incubators WHERE incubator_id = ?",
                (row[0],),
            )

            if stored_egg == "halloween_egg":
                achievements_cog = self.bot.get_cog("Achievements")
                if achievements_cog:
                    await achievements_cog.add_halloween_hatch_progress(
                        ctx.author.id,
                        db=db,
                    )

            await db.commit()

        active_note = (
            " It has been automatically equipped because you didn't have an active pet!"
            if not has_active else
            " Use `/pets` to manage and equip your new companion!"
        )
        discovery_lines = ""
        if variant_discovered:
            variant_info = get_variant_info(pet_type, variant_id)
            discovery_lines = (
                f"\n\n🎉 **RARE VARIANT DISCOVERED!** {variant_info['emoji']} **{variant_info['name']}**\n"
                f"> {variant_info['lore']}"
                if variant_info else ""
            )
        if essence_awarded:
            discovery_lines += "\n✨ **Astral Essence recovered!**"

        await ctx.send(
            f"{ctx.author.mention} 🐣 **EGG HATCHED!**\n\n"
            f"{definition['emoji']} **{definition['name']}**!\n"
            f"> *{definition['description']}*\n\n"
            f"✨ **Passive:** {definition['passive']['name']}\n"
            f"_{definition['passive']['description']}_\n\n"
            f"📈 **Level 1** • Passive Level **1/{PET_PASSIVE_MAX_LEVEL}**\n"
            f"🥚 Hatched from **Tube {slot_id}**\n"
            f"{active_note}{discovery_lines}"
        )

    @tasks.loop(minutes=1)
    async def incubator_checker(self):
        """Notify users when their 12-hour incubation finishes."""
        try:
            async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
                await self.ensure_schema(db)
                now = time.time()

                async with db.execute(
                    """
                    SELECT incubator_id, user_id, egg_id
                    FROM pet_incubators
                    WHERE ready_at <= ? AND notified = 0
                    """,
                    (now,),
                ) as cursor:
                    rows = await cursor.fetchall()

                for incubator_id, user_id, egg_id in rows:
                    channel = self.bot.get_channel(INCUBATOR_NOTIFICATION_CHANNEL_ID)
                    if channel is None:
                        try:
                            channel = await self.bot.fetch_channel(
                                INCUBATOR_NOTIFICATION_CHANNEL_ID
                            )
                        except Exception:
                            channel = None

                    if channel is None:
                        # Keep the notification pending so a later checker run
                        # can try again if the channel becomes available.
                        continue

                    try:
                        info = ITEM_REGISTRY.get(
                            egg_id, {"name": egg_id, "emoji": "🥚"}
                        )
                        await channel.send(
                            f"<@{user_id}> 🔔 {info['emoji']} "
                            f"**Your pet egg is ready to hatch!**\n"
                            f"Your **{info['name']}** has finished incubating.\n\n"
                            f"Use `/incubator` with **Hatch ready egg** and choose **{egg_id}** to reveal your new companion! 🐣"
                        )
                    except Exception:
                        # Keep the notification pending if the channel/message
                        # cannot be sent right now.
                        continue

                    await db.execute(
                        "UPDATE pet_incubators SET notified = 1 WHERE incubator_id = ?",
                        (incubator_id,),
                    )

                await db.commit()
        except Exception:
            # The notification loop must never take the bot down.
            return

    @incubator_checker.before_loop
    async def before_incubator_checker(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Pets(bot))
