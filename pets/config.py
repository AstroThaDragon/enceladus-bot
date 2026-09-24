"""Pet definitions and static configuration for Enceladus."""

PET_PASSIVE_MAX_LEVEL = 5


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


NORMAL_EXPLORATION_PET_XP_MIN = 10


NORMAL_EXPLORATION_PET_XP_MAX = 30


HAUNTED_EXPLORATION_PET_XP_MIN = 15


HAUNTED_EXPLORATION_PET_XP_MAX = 50


HAUNTED_HOME_PET_XP_BONUS = 10


PET_TREAT_XP = 50


HALLOWEEN_PET_CANDY_XP = 150


NORMAL_EGG_CHANCE = 0.085


HALLOWEEN_EGG_CHANCE = 1 / 35


INCUBATION_SECONDS = 12 * 60 * 60


INCUBATOR_NOTIFICATION_CHANNEL_ID = 1548034265508356166

