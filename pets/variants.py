"""
Enceladus pet variant configuration.

This module intentionally contains variant presentation, rarity, and discovery
rules separately from pets.py so the large pet registry stays manageable.
"""

# ---------------------------------------------------------------------------
# Variant sets
# ---------------------------------------------------------------------------

NORMAL_VARIANTS = {
    "nebula": {
        "name": "Nebula",
        "emoji": "🌌",
        "lore": "Starlight and colorful nebular dust ripple across its body like a living deep-space cloud.",
    },
    "shiny": {
        "name": "Shiny",
        "emoji": "✨",
        "lore": "Its entire form gleams with an unusually brilliant, almost impossible sheen.",
    },
    "prismatic": {
        "name": "Prismatic",
        "emoji": "🌈",
        "lore": "Iridescent light fractures across its form, shifting through a whole spectrum whenever it moves.",
    },
    "void": {
        "name": "Void",
        "emoji": "🕳️",
        "lore": "Its colors have been swallowed by a strange darkness that seems deeper than empty space.",
    },
}

HALLOWEEN_VARIANTS = {
    "spectral": {
        "name": "Spectral",
        "emoji": "👻",
        "lore": "Its body has become translucent and ghostlike, trailing a cold supernatural mist.",
    },
    "blood_moon": {
        "name": "Blood Moon",
        "emoji": "🌕",
        "lore": "A deep crimson lunar glow surrounds it, painting every movement in eerie red light.",
    },
    "cursed": {
        "name": "Cursed",
        "emoji": "🔥",
        "lore": "Dark supernatural energy crawls across its form in flickering, unstable patterns.",
    },
    "undead": {
        "name": "Undead",
        "emoji": "☠️",
        "lore": "It looks like it has returned from somewhere it absolutely should not have returned from.",
    },
    "possessed": {
        "name": "Possessed",
        "emoji": "🕯️",
        "lore": "Something unseen seems to be sharing its body, occasionally moving before it does.",
    },
}

GODZILLA_VARIANTS = {
    "atomic": {
        "name": "Atomic Godzilla",
        "emoji": "🔵",
        "lore": "A brilliant blue atomic glow pulses beneath its scales, building with every breath.",
    },
    "burning_orange": {
        "name": "Burning Orange Godzilla",
        "emoji": "🟠",
        "lore": "Its body burns with a fierce orange heat, radiating the unmistakable fury of an overheated reactor.",
    },
    "purple": {
        "name": "Purple Godzilla",
        "emoji": "🟣",
        "lore": "A vivid violet energy courses through its body, giving its silhouette an otherworldly glow.",
    },
    "burning": {
        "name": "Burning Godzilla",
        "emoji": "🔴",
        "lore": "Its entire form radiates catastrophic crimson heat, as though its nuclear core is seconds from eruption.",
    },
    "evolved": {
        "name": "Evolved Godzilla",
        "emoji": "🩷",
        "lore": "Its energy has evolved into a brilliant magenta glow, making the enormous creature look almost alien.",
    },
    "shiny": {
        "name": "Shiny Godzilla",
        "emoji": "✨",
        "lore": "Even Godzilla's overwhelming presence has somehow been transformed into a dazzling, impossibly rare sheen.",
    },
}

SAMHAIN_VARIANTS = {
    "ghostly": {
        "name": "Ghostly Samhain",
        "emoji": "👻",
        "lore": "Its ancient silhouette flickers between the physical world and a pale spectral realm.",
    },
    "jack_o_lantern": {
        "name": "Jack-o'-Lantern Samhain",
        "emoji": "🎃",
        "lore": "Its ritual form burns with a carved pumpkin glow that illuminates the darkness around it.",
    },
    "bloodstained": {
        "name": "Bloodstained Samhain",
        "emoji": "🩸",
        "lore": "Old crimson stains mark its ritual garb, as though it has walked through centuries of forgotten ceremonies.",
    },
    "trickster": {
        "name": "Trickster Samhain",
        "emoji": "😈",
        "lore": "Its ancient demeanor gives way to a mischievous grin and an unmistakable taste for Halloween chaos.",
    },
    "ritual": {
        "name": "Ritual Samhain",
        "emoji": "🕯️",
        "lore": "Glowing ritual markings cover its body, suggesting a ceremony that is still somehow ongoing.",
    },
    "the_first": {
        "name": "The First Samhain",
        "emoji": "🎃",
        "lore": "This form feels impossibly ancient, like the very first shadow cast by the holiday itself.",
    },
    "shiny": {
        "name": "Shiny Samhain",
        "emoji": "✨",
        "lore": "Its ancient Halloween presence is wrapped in a brilliant shimmer that makes every ritual gesture sparkle.",
    },
}

FEED_ME_VARIANTS = {
    "bloodroot": {
        "name": "Bloodroot",
        "emoji": "🩸",
        "lore": "Deep crimson roots pulse through its body as if something beneath the soil is feeding it.",
    },
    "venomous": {
        "name": "Venomous",
        "emoji": "☠️",
        "lore": "Toxic colors spread across its leaves, accompanied by a faint warning shimmer around its edges.",
    },
    "carnivorous_rose": {
        "name": "Carnivorous Rose",
        "emoji": "🌹",
        "lore": "A beautiful rose has bloomed among its hungry tendrils, looking far too elegant for something so dangerous.",
    },
    "fungal": {
        "name": "Fungal",
        "emoji": "🍄",
        "lore": "Strange mushrooms and glowing fungal growths have overtaken its body without slowing its appetite.",
    },
    "watcher": {
        "name": "Watcher",
        "emoji": "👁️",
        "lore": "Unsettling eyes have opened among its leaves, following every movement with patient attention.",
    },
    "nightbloom": {
        "name": "Nightbloom",
        "emoji": "🌑",
        "lore": "Its flowers only open in darkness, revealing a beautiful glow that makes its hunger even harder to ignore.",
    },
    "shiny": {
        "name": "Shiny Feed Me",
        "emoji": "✨",
        "lore": "Its leaves and petals gleam with a bizarrely cheerful sparkle that does absolutely nothing to make it safer.",
    },
}

NORMAL_PET_TYPES = {
    "space_cat", "cosmic_fox", "astronaut_turtle", "busted_drone",
    "cosmic_owl", "glorpy", "little_star", "friendly_meteor",
    "space_dragon", "ethereal_cloud", "cosmic_trickster", "void_merchant",
}

HALLOWEEN_PET_TYPES = {
    "pumpkin_pup", "black_witchy_cat", "vampire_bat", "godzilla",
    "skeleton_dragon", "samhain", "the_feed_me",
}

GLITCHED_VARIANTS = {
    "kolossos_bloodied": {
        "name": "Bloodied",
        "emoji": "🩸",
        "lore": "Dark crimson stains cover its scales and claws, as though it has only just returned from a brutal hunt. Its red accents appear deeper and more intense against its bloodied hide.",
    },
    "kolossos_void": {
        "name": "Void",
        "emoji": "🕳️",
        "lore": "Its scales have become almost completely black, swallowing surrounding light while faint red highlights flicker like distant stars trapped beneath the surface.",
    },
    "kolossos_glitched": {
        "name": "Glitched",
        "emoji": "⚠️",
        "lore": "Kolossos appears to be breaking apart between frames, with misaligned scales, RGB-shifted edges, static fragments, and sections of its body briefly replaced by corrupted textures.",
    },
    "tails_doll_crimson_gem": {
        "name": "Crimson Gem",
        "emoji": "💎",
        "lore": "Its signature gem burns with a vivid crimson glow, casting red light across its stitched body while its fur and seams take on deeper scarlet tones.",
    },
    "tails_doll_corrupted": {
        "name": "Corrupted Doll",
        "emoji": "🧸",
        "lore": "Its stitched body is warped by strange digital corruption, with uneven seams, broken textures, and tiny patches of static crawling across its fur and gem.",
    },
    "tails_doll_glitched": {
        "name": "Glitched",
        "emoji": "⚠️",
        "lore": "The doll flickers between corrupted frames, its stitching misaligned and portions of its body fragmented into colorful digital noise as though its model is failing to load.",
    },
    "endoskeleton_rustbound": {
        "name": "Rustbound",
        "emoji": "🦾",
        "lore": "Years of corrosion have eaten into its metal frame, leaving orange-brown rust, worn joints, and flaky plating across its exposed mechanical body.",
    },
    "endoskeleton_prototype": {
        "name": "Prototype",
        "emoji": "🔧",
        "lore": "Its unfinished frame exposes experimental components, loose wiring, and mismatched mechanical parts that make it look like a machine pulled straight from a testing lab.",
    },
    "endoskeleton_glitched": {
        "name": "Glitched",
        "emoji": "⚠️",
        "lore": "Its metal frame repeatedly snaps out of alignment, with duplicated limbs, floating components, and harsh digital artifacts appearing wherever its corrupted model fails to render correctly.",
    },
    "xenomorph_pale": {
        "name": "Pale",
        "emoji": "🤍",
        "lore": "Its normally dark exoskeleton has faded to a stark bone-white sheen, making its smooth head, claws, and elongated limbs stand out with an eerie clinical appearance.",
    },
    "xenomorph_royal": {
        "name": "Royal",
        "emoji": "👑",
        "lore": "A richer, imposing coloration covers its exoskeleton, while its crest and spines appear larger and more pronounced, giving the creature an unmistakably regal silhouette.",
    },
    "xenomorph_glitched": {
        "name": "Glitched",
        "emoji": "⚠️",
        "lore": "Its elongated body tears between frames, leaving duplicate silhouettes, jagged texture fragments, and bands of digital static trailing behind its movements.",
    },
    "missingno_error_404": {
        "name": "ERROR_404",
        "emoji": "🚫",
        "lore": "Its already-corrupted form has deteriorated further into broken textures and missing data, with empty spaces and malformed fragments appearing where parts of its body should be.",
    },
    "missingno_null": {
        "name": "NULL",
        "emoji": "⬛",
        "lore": "Most of its form has collapsed into an almost featureless black void, surrounded by fragmented purple geometry that seems to exist without a proper shape or texture.",
    },
    "missingno_glitched": {
        "name": "Glitched",
        "emoji": "⚠️",
        "lore": "MissingNo. has become almost impossible to render correctly, violently flickering between broken shapes, scrambled colors, and chunks of corrupted data that spill beyond its outline.",
    },
    "siren_lost_transmission": {
        "name": "Lost Transmission",
        "emoji": "📡",
        "lore": "Its body looks faded and out of sync, with damaged sirens, broken signal fragments, and faint static crawling across its frame as though an old broadcast is struggling to come through.",
    },
    "siren_dead_frequency": {
        "name": "Dead Frequency",
        "emoji": "📻",
        "lore": "Its body has darkened almost to black, its sirens look worn and damaged, and a lingering layer of visual static surrounds it like the remains of a transmission that has gone silent.",
    },
    "siren_glitched": {
        "name": "Glitched",
        "emoji": "⚠️",
        "lore": "Its towering frame violently desynchronizes, with sirens shifting position, sections of its body splitting into static, and fragments of corrupted broadcast imagery appearing around it.",
    },
}

GLITCHED_PET_TYPES = {
    "kolossos",
    "mini_tails_doll",
    "endoskeleton",
    "mini_xenomorph",
    "missingno",
    "mini_siren_head",
}

GLITCHED_VARIANT_IDS = {
    "kolossos": ("kolossos_bloodied", "kolossos_void", "kolossos_glitched"),
    "mini_tails_doll": ("tails_doll_crimson_gem", "tails_doll_corrupted", "tails_doll_glitched"),
    "endoskeleton": ("endoskeleton_rustbound", "endoskeleton_prototype", "endoskeleton_glitched"),
    "mini_xenomorph": ("xenomorph_pale", "xenomorph_royal", "xenomorph_glitched"),
    "missingno": ("missingno_error_404", "missingno_null", "missingno_glitched"),
    "mini_siren_head": ("siren_lost_transmission", "siren_dead_frequency", "siren_glitched"),
}

SPECIAL_VARIANTS = {
    "godzilla": GODZILLA_VARIANTS,
    "samhain": SAMHAIN_VARIANTS,
    "the_feed_me": FEED_ME_VARIANTS,
}

# ---------------------------------------------------------------------------
# Rarity
# ---------------------------------------------------------------------------

# These are total chances to discover any variant when hatching. Individual
# variants are weighted inside the pool, so Shiny/Nebula remain the rarest.
HATCH_VARIANT_CHANCE = {
    "normal": 0.020,
    "halloween": 0.040,
    "glitched": 0.040,
}

HATCH_VARIANT_WEIGHTS = {
    "normal": {
        "nebula": 1,
        "shiny": 1,
        "prismatic": 5,
        "void": 3,
    },
    "halloween": {
        "spectral": 5,
        "blood_moon": 4,
        "cursed": 6,
        "undead": 5,
        "possessed": 1,
    },
    "glitched": {
        "kolossos_bloodied": 5,
        "kolossos_void": 4,
        "kolossos_glitched": 1,
        "tails_doll_crimson_gem": 5,
        "tails_doll_corrupted": 4,
        "tails_doll_glitched": 1,
        "endoskeleton_rustbound": 5,
        "endoskeleton_prototype": 4,
        "endoskeleton_glitched": 1,
        "xenomorph_pale": 5,
        "xenomorph_royal": 4,
        "xenomorph_glitched": 1,
        "missingno_error_404": 5,
        "missingno_null": 4,
        "missingno_glitched": 1,
        "siren_lost_transmission": 5,
        "siren_dead_frequency": 4,
        "siren_glitched": 1,
    },
}

SPECIAL_HATCH_VARIANT_WEIGHTS = {
    "godzilla": {
        "atomic": 5,
        "burning_orange": 4,
        "purple": 4,
        "burning": 3,
        "evolved": 2,
        "shiny": 1,
    },
    "samhain": {
        "ghostly": 5,
        "jack_o_lantern": 5,
        "bloodstained": 4,
        "trickster": 4,
        "ritual": 3,
        "the_first": 2,
        "shiny": 1,
    },
    "the_feed_me": {
        "bloodroot": 5,
        "venomous": 5,
        "carnivorous_rose": 4,
        "fungal": 4,
        "watcher": 3,
        "nightbloom": 2,
        "shiny": 1,
    },
}

# Fusion variant discovery becomes a little more likely as the target gets
# more Fusion progress. Fusion 5+ uses the final value.
FUSION_VARIANT_CHANCES = {
    0: 0.030,
    1: 0.035,
    2: 0.040,
    3: 0.045,
    4: 0.050,
    5: 0.075,
}

# Astral Essence sources. Keeping these here makes balancing easy without
# touching the core pet logic.
MINING_ESSENCE_CHANCE = 0.015
HATCH_ESSENCE_CHANCE = 0.020
RELEASE_ESSENCE_CHANCE = 0.050

ASTRAL_ESSENCE_ID = "astral_essence"
ASTRAL_ESSENCE_NAME = "Astral Essence"
ASTRAL_ESSENCE_EMOJI = "✨"

FUSION_COSTS = {
    1: {"stardust": 5_000, "essence": 2},
    2: {"stardust": 10_000, "essence": 4},
    3: {"stardust": 20_000, "essence": 6},
    4: {"stardust": 35_000, "essence": 8},
    5: {"stardust": 50_000, "essence": 10},
}
VARIANT_HUNT_COST = {"stardust": 15_000, "essence": 3}

FUSION_LEVEL_GATES = {
    1: 5,
    2: 10,
    3: 15,
    4: 20,
    5: 25,
}

def variant_set_for_pet(pet_type):
    if pet_type in SPECIAL_VARIANTS:
        return SPECIAL_VARIANTS[pet_type]
    if pet_type in NORMAL_PET_TYPES:
        return NORMAL_VARIANTS
    if pet_type in HALLOWEEN_PET_TYPES:
        return HALLOWEEN_VARIANTS
    if pet_type in GLITCHED_PET_TYPES:
        return {variant_id: GLITCHED_VARIANTS[variant_id] for variant_id in GLITCHED_VARIANT_IDS[pet_type]}
    return {}

def variant_category_for_pet(pet_type):
    if pet_type in NORMAL_PET_TYPES:
        return "normal"
    if pet_type in HALLOWEEN_PET_TYPES:
        return "halloween"
    if pet_type in GLITCHED_PET_TYPES:
        return "glitched"
    return None

def get_variant_info(pet_type, variant_id):
    if not variant_id:
        return None
    return variant_set_for_pet(pet_type).get(variant_id)

def get_variant_ids_for_pet(pet_type):
    return list(variant_set_for_pet(pet_type).keys())

def get_variant_display(pet_type, base_name, variant_id):
    info = get_variant_info(pet_type, variant_id)
    if not info:
        return base_name, None, None

    variant_name = info["name"]
    if base_name.lower().replace("the ", "") in variant_name.lower():
        display_name = variant_name
    else:
        clean_base = base_name[4:] if base_name.startswith("The ") else base_name
        display_name = f"{variant_name} {clean_base}"
    return display_name, info["emoji"], info["lore"]

def get_fusion_variant_chance(fusion_level):
    return FUSION_VARIANT_CHANCES.get(min(5, max(0, fusion_level)), FUSION_VARIANT_CHANCES[5])

def get_variant_roll_pool(pet_type):
    if pet_type in SPECIAL_VARIANTS:
        return SPECIAL_HATCH_VARIANT_WEIGHTS.get(pet_type, {})

    if pet_type in GLITCHED_PET_TYPES:
        ids = GLITCHED_VARIANT_IDS.get(pet_type, ())
        weights = HATCH_VARIANT_WEIGHTS.get("glitched", {})
        return {variant_id: weights[variant_id] for variant_id in ids if variant_id in weights}

    category = variant_category_for_pet(pet_type)
    if category is None:
        return {}

    return HATCH_VARIANT_WEIGHTS.get(category, {})

def roll_hatched_variant(pet_type):
    """Return a rare variant ID for a freshly hatched base pet, or None."""
    pool = get_variant_roll_pool(pet_type)
    if not pool:
        return None

    import random
    if pet_type in GLITCHED_PET_TYPES:
        category = "glitched"
    else:
        category = "halloween" if pet_type in HALLOWEEN_PET_TYPES else "normal"
    chance = HATCH_VARIANT_CHANCE.get(category, 0.0)
    if random.random() >= chance:
        return None

    return random.choices(
        list(pool.keys()),
        weights=list(pool.values()),
        k=1,
    )[0]

def roll_fusion_variant(pet_type, fusion_level, exclude_variant=None):
    """Return a variant ID from a fusion roll, or None."""
    pool = get_variant_roll_pool(pet_type)
    if exclude_variant:
        pool = {key: weight for key, weight in pool.items() if key != exclude_variant}
    if not pool:
        return None
    import random
    if random.random() >= get_fusion_variant_chance(fusion_level):
        return None
    return random.choices(
        list(pool.keys()),
        weights=list(pool.values()),
        k=1,
    )[0]

PET_DISPLAY_NAMES = {
    "space_cat": "Space Cat",
    "cosmic_fox": "Cosmic Fox",
    "astronaut_turtle": "Astronaut Turtle",
    "busted_drone": "Busted-up Drone",
    "cosmic_owl": "Cosmic Owl",
    "glorpy": "Glorpy",
    "little_star": "Little Star",
    "friendly_meteor": "Friendly Meteor",
    "space_dragon": "Space Dragon",
    "ethereal_cloud": "Ethereal Cloud",
    "cosmic_trickster": "Cosmic Trickster",
    "void_merchant": "Void Merchant",
    "pumpkin_pup": "Pumpkin Pup",
    "black_witchy_cat": "Black Witchy Cat",
    "vampire_bat": "Vampire Bat",
    "godzilla": "Godzilla",
    "skeleton_dragon": "Skeleton Dragon",
    "samhain": "Samhain",
    "the_feed_me": "The Feed Me",
}


def build_variant_collectibles():
    """Return collectible tuples: (id, name, emoji, description)."""
    entries = []
    for pet_type in sorted(NORMAL_PET_TYPES | HALLOWEEN_PET_TYPES | GLITCHED_PET_TYPES):
        for variant_id, info in variant_set_for_pet(pet_type).items():
            collectible_id = f"pet_variant:{pet_type}:{variant_id}"
            base_name = PET_DISPLAY_NAMES.get(pet_type, pet_type.replace("_", " ").title())
            display_name, _emoji, _lore = get_variant_display(pet_type, base_name, variant_id)
            name = display_name
            description = (
                f"Discover the {info['name']} variant of this pet. "
                f"{info['lore']}"
            )
            entries.append((collectible_id, name, info["emoji"], description))
    return entries
