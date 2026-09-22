"""Haunted Exploration foundation for Enceladus.

Phase 1 deliberately focuses on the exploration framework itself:
- Halloween event gating
- five selectable locations
- 20 daily attempts
- persistent Sanity with continuous regeneration
- an Insane state at 0 Sanity
- multi-stage runs with choice buttons
- running away, including rare escape outcomes
- a small universal encounter engine

Location-specific encounters, Halloween loot, collectibles, candy rewards, and
alchemy are intentionally left for later phases.
"""

from datetime import datetime
import random
import time
import json

import aiosqlite
import pytz

from inventory import add_inventory_item, ITEM_REGISTRY
from collectibles import record_collectible
from seasonal_updates.halloween import halloween as halloween_season
from pets import get_active_pet_effects

HAUNTED_DAILY_ATTEMPTS = 20
SANITY_MAX = 100
SANITY_REGEN_SECONDS = 6 * 60 * 60  # 100 Sanity over six hours.

HAUNTED_LOCATIONS = {
    "asylum": {
        "name": "Abandoned Asylum",
        "emoji": "🏥",
        "description": "A long-abandoned asylum drifting in the dark. The lights should not still be on.",
    },
    "graveyard": {
        "name": "Forgotten Graveyard",
        "emoji": "🪦",
        "description": "An impossible graveyard beneath a sky that does not belong to any known world.",
    },
    "haunted_house": {
        "name": "Haunted House",
        "emoji": "🏚️",
        "description": "A house that somehow exists inside the station's abandoned sector.",
    },
    "church": {
        "name": "Abandoned Church",
        "emoji": "⛪",
        "description": "A silent church with a door that appears to have been locked from the inside.",
    },
    "witch_woods": {
        "name": "Witch's Woods",
        "emoji": "🌲",
        "description": "Twisted woods where the trees seem to move whenever you stop watching them.",
    },
    "dilapidated_pizzeria": {
        "name": "Dilapidated Pizzeria", "emoji": "🍕",
        "description": "A faded family restaurant with a silent stage, dead arcade cabinets, and a security office that still has power.",
    },
    "abandoned_toy_workshop": {
        "name": "Abandoned Toy Workshop", "emoji": "🧸",
        "description": "A brightly painted factory where the conveyor belts stopped long ago, but something keeps moving between the aisles.",
    },
    "broadcast_station": {
        "name": "Abandoned Broadcast Station", "emoji": "📡",
        "description": "Every monitor shows the same empty hallway, even though the cameras point in different directions.",
    },
    "endless_hotel": {
        "name": "The Endless Hotel", "emoji": "🏨",
        "description": "A hotel whose corridors repeat forever. Room numbers change whenever you look away.",
    },
    "fogbound_town": {
        "name": "Fogbound Town", "emoji": "🌫️",
        "description": "A deserted town swallowed by fog so thick that the streetlights barely reach the ground.",
    },
    "derelict_research_facility": {
        "name": "Derelict Research Facility", "emoji": "🧪",
        "description": "A sealed research complex where the emergency lights still work and the experiments clearly did not end cleanly.",
    },
    "yellow_halls": {
        "name": "The Yellow Halls", "emoji": "🟨",
        "description": "Yellow wallpaper, damp carpet, humming fluorescent lights, and corridors that refuse to stay the same length.",
    },
    "dead_end_highway": {
        "name": "The Dead-End Highway", "emoji": "🛣️",
        "description": "An endless road under a dead night sky. The signs promise exits that the highway never seems to reach.",
    },
    "drowned_station": {
        "name": "The Drowned Station", "emoji": "🌊",
        "description": "A forgotten underground station slowly filling with dark water. Something keeps moving beneath the surface.",
    },
    "silent_campground": {
        "name": "The Silent Campground", "emoji": "🌲",
        "description": "A dead-silent campground where radios fill with static, tall figures watch from the trees, and recordings remember things you never did.",
    },

}

# Phase 1 encounter framework. Later phases can add location-specific tables
# without changing the run/choice machinery.
# Phase 2 reward data. Rewards are granted only when an adventure is fully completed.
HAUNTED_RARITY_WEIGHTS = {
    "common": 65,
    "uncommon": 25,
    "rare": 8,
    "legendary": 1.9,
    "void": 0.1,
}

HAUNTED_RARITY_LABELS = {
    "common": "Common",
    "uncommon": "Uncommon",
    "rare": "Rare",
    "legendary": "Legendary",
    "void": "Void",
}

HAUNTED_RARITY_EMOJIS = {
    "common": "⚪",
    "uncommon": "🟢",
    "rare": "🔵",
    "legendary": "🟣",
    "void": "⚫",
}

# Location-specific ingredients are intentionally separate from encounters.
# Phase 3 can build location-specific encounters without changing this table.
HAUNTED_INGREDIENT_POOLS = {
    "asylum": [
        "ectoplasm",
        "medical_residue",
        "bloodstained_gauze",
        "cracked_syringe",
        "spectral_thread",
    ],
    "graveyard": [
        "grave_dust",
        "bone_fragment",
        "wilted_bloom",
        "funeral_thread",
        "grave_marker_shard",
    ],
    "haunted_house": [
        "black_wax",
        "cursed_fabric",
        "broken_doll_piece",
        "attic_mothwing",
        "dusty_looking_glass",
    ],
    "church": [
        "consecrated_salt",
        "ritual_chalk",
        "bell_fragment",
        "incense_resin",
        "cracked_holy_water_vial",
    ],
    "witch_woods": [
        "witchroot",
        "mooncap_mushroom",
        "nightshade_berry",
        "spider_lily",
        "glowmoss",
    ],
    "dilapidated_pizzeria": ["circuit_board","nuts_bolts","wiring","scrap_metal","glue","mechanical_parts","mascot_fabric","blackened_grease"],
    "abandoned_toy_workshop": ["nuts_bolts","wiring","glue","scrap_metal","stuffing","bent_toy_parts","faded_paint","plastic_eye"],
    "broadcast_station": ["circuit_board","wiring","nuts_bolts","radio_components","damaged_vhs_tape","burnt_capacitor","recorded_static"],
    "endless_hotel": ["scrap_metal","wiring","glue","bent_key","hotel_carpet_thread","old_guest_receipt","flickering_bulb","dusty_cleaning_rag"],
    "fogbound_town": ["grave_dust","scrap_metal","rusty_pipe","cracked_brick","condensed_fog","bent_key","flickering_bulb"],
    "derelict_research_facility": ["circuit_board","wiring","nuts_bolts","damaged_battery","chemical_sample","broken_lab_glass","contaminated_gloves","unknown_biological_residue"],
    # Dedicated material pools for the newest Haunted locations.
    "yellow_halls": [
        "yellow_wallpaper_scrap",
        "damp_carpet_fiber",
        "frayed_electrical_wire",
        "unmarked_key",
        "strange_fluorescent_tube",
        "yellow_hall_light_cover",
    ],
    "dead_end_highway": [
        "rusted_road_sign",
        "damaged_payphone_part",
        "old_road_map",
        "contaminated_fuel_can",
        "rusty_car_part",
        "motel_key",
    ],
    "drowned_station": [
        "waterlogged_transit_ticket",
        "corroded_train_part",
        "flooded_flashlight",
        "damaged_conductor",
        "contaminated_water_sample",
        "submerged_key",
    ],
    "silent_campground": [
        "static_damaged_radio",
        "distorted_photograph",
        "strange_notebook_page",
        "corrupted_video_tape",
        "damaged_antenna",
        "blackened_tree_bark",
        "unidentified_black_tendril",
    ],

}

# Stardust granted when a location-specific Haunted ingredient cannot fit in inventory.
# Kept at the same 10-Stardust baseline used by existing Haunted ingredients.
HAUNTED_INGREDIENT_OVERFLOW_VALUES = {
    "yellow_wallpaper_scrap": 10,
    "damp_carpet_fiber": 10,
    "frayed_electrical_wire": 10,
    "unmarked_key": 10,
    "strange_fluorescent_tube": 10,
    "yellow_hall_light_cover": 10,
    "rusted_road_sign": 10,
    "damaged_payphone_part": 10,
    "old_road_map": 10,
    "contaminated_fuel_can": 10,
    "rusty_car_part": 10,
    "motel_key": 10,
    "waterlogged_transit_ticket": 10,
    "corroded_train_part": 10,
    "flooded_flashlight": 10,
    "damaged_conductor": 10,
    "contaminated_water_sample": 10,
    "submerged_key": 10,
    "static_damaged_radio": 10,
    "distorted_photograph": 10,
    "strange_notebook_page": 10,
    "corrupted_video_tape": 10,
    "damaged_antenna": 10,
    "blackened_tree_bark": 10,
    "unidentified_black_tendril": 10,
}


HAUNTED_REWARD_RANGES = {
    "common": {"stardust": (150, 275), "candy": (3, 6), "ingredients": (1, 2)},
    "uncommon": {"stardust": (250, 425), "candy": (5, 10), "ingredients": (2, 3)},
    "rare": {"stardust": (400, 700), "candy": (8, 14), "ingredients": (2, 4)},
    "legendary": {"stardust": (700, 1200), "candy": (14, 22), "ingredients": (3, 5)},
    "void": {"stardust": (1200, 2000), "candy": (25, 40), "ingredients": (4, 7)},
}

# A completed run can uncover one permanent Halloween collectible. Higher
# reward rarities make that discovery more likely, while keeping it separate
# from the ordinary ingredient/currency roll.
HAUNTED_COLLECTIBLE_CHANCES = {
    "common": 0.00,
    "uncommon": 0.04,
    "rare": 0.12,
    "legendary": 0.28,
    "void": 0.50,
}


def roll_haunted_rarity():
    """Return a weighted Haunted reward rarity."""
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
    """Grant the end-of-adventure reward and return a display payload."""
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

    added_candy, _, candy_max = await add_inventory_item(
        db, user_id, "halloween_candy", "consumable", candy
    )
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
        ingredient_type = ITEM_REGISTRY.get(ingredient_id, {}).get(
            "type", "Haunted Ingredient"
        )
        added_ingredient, _, ingredient_max = await add_inventory_item(
            db, user_id, ingredient_id, ingredient_type, ingredient_amount
        )
        ingredient_overflow = ingredient_amount - added_ingredient
        if ingredient_overflow:
            # Ingredient overflow is converted to a small Stardust amount rather
            # than silently deleting a successful reward.
            ingredient_overflow_stardust = ingredient_overflow * HAUNTED_INGREDIENT_OVERFLOW_VALUES.get(ingredient_id, 10)
            await db.execute(
                "UPDATE users SET stardust = COALESCE(stardust, 0) + ? WHERE user_id = ?",
                (ingredient_overflow_stardust, user_id),
            )
        else:
            ingredient_overflow_stardust = 0
    else:
        ingredient_max = 0
        ingredient_overflow_stardust = 0

    collectible = None
    collectible_added = False
    collectible_chance = min(1.0, HAUNTED_COLLECTIBLE_CHANCES[rarity] + max(0.0, float(collectible_bonus)))
    if random.random() < collectible_chance:
        collectible = random.choice(halloween_season.HALLOWEEN_SPACE_JUNK)
        collectible_id, collectible_name, collectible_emoji, collectible_desc, collectible_value, collectible_candy = collectible
        added_collectible, _, collectible_max = await add_inventory_item(
            db, user_id, collectible_id, "space_junk", 1
        )
        if added_collectible:
            # Inventory ownership and permanent collection progress are separate.
            # A repeat find can still be kept in inventory even if the permanent
            # collectible entry was already discovered previously.
            await record_collectible(
                db, bot, user_id, collectible_id, "Halloween"
            )
            collectible_added = True
        else:
            # If the inventory copy cannot be stored, convert its normal sell
            # value into Stardust but do not mark it permanently collected.
            await db.execute(
                "UPDATE users SET stardust = COALESCE(stardust, 0) + ? WHERE user_id = ?",
                (collectible_value, user_id),
            )
            collectible_added = False

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


UNIVERSAL_ENCOUNTERS = [
    {
        "text": "The corridor ahead is completely silent. Then something knocks three times from the other side of a sealed door.",
        "choices": [
            ("🚪 Open the door", "open", -8, "The door opens with a slow, reluctant groan."),
            ("🏃 Keep walking", "walk", 0, "You decide that whatever is behind that door can keep its secrets."),
            ("👂 Stop and listen", "listen", -4, "The knocking stops. Something on the other side seems to notice you."),
        ],
    },
    {
        "text": "Your footsteps stop echoing. You can still hear them, but the sound is coming from somewhere behind you.",
        "choices": [
            ("👀 Turn around", "turn", -7, "For a split second, you see movement at the end of the hall."),
            ("🚶 Keep moving", "walk", 0, "You refuse to give the footsteps the satisfaction of a reaction."),
            ("🤫 Stand completely still", "still", -3, "The extra footsteps slowly fade until only your breathing remains."),
        ],
    },
    {
        "text": "A faint voice whispers your name from somewhere nearby. It sounds exactly like you.",
        "choices": [
            ("🗣️ Answer it", "answer", -10, "The voice answers immediately. It says something you don't remember saying."),
            ("🏃 Ignore it and move", "ignore", 0, "You keep moving. The voice eventually stops following."),
            ("🔦 Search the room", "search", -5, "You find nothing, but one of the shadows is facing the wrong direction."),
        ],
    },
    {
        "text": "You find a hallway fork. One path is lit. The other is completely dark.",
        "choices": [
            ("💡 Take the lit path", "light", 0, "The light flickers as you pass, but the path remains clear."),
            ("🌑 Enter the darkness", "dark", -9, "The darkness feels strangely cold. Something brushes past your shoulder."),
            ("↩️ Turn back", "back", -2, "You back away from the fork and notice the hallway behind you looks different."),
        ],
    },
]



# ---------------------------------------------------------------------------
# Replayable choice outcomes + sanity hallucinations
# ---------------------------------------------------------------------------

def _choice_outcomes(label, key, risk, flavor, base_delta=None):
    """Build a weighted outcome pool.  No choice has one fixed result anymore."""
    risk = risk if risk in {"low", "medium", "high", "extreme"} else "medium"
    if base_delta is None:
        bases = {"low": -2, "medium": -5, "high": -9, "extreme": -14}
        base_delta = bases[risk]
    base_delta = int(base_delta)
    # Keep the old encounter's intent while adding a meaningful spread around it.
    if base_delta >= 0:
        outcomes = [
            (48, max(0, base_delta), f"{flavor} Nothing immediately goes wrong."),
            (32, min(5, base_delta + 1), f"{flavor} You feel unexpectedly steady."),
            (15, -max(2, abs(base_delta) // 2), f"{flavor} Something about the moment feels wrong."),
            (5, min(-3, base_delta - 6), "The room seems to notice that you made the choice."),
        ]
    else:
        magnitude = abs(base_delta)
        outcomes = [
            (12, min(3, -magnitude + 5), f"{flavor} For once, the danger passes almost harmlessly."),
            (45, base_delta, flavor),
            (30, base_delta - max(2, magnitude // 2), f"{flavor} The backlash is worse than expected."),
            (13, base_delta - max(8, magnitude), "Something impossible happens. For a second, the world seems to forget what shape it is supposed to have."),
        ]
    return {"label": label, "key": key, "risk": risk, "risk_label": risk.title(),
            "outcomes": [{"weight": w, "sanity": d, "text": t} for w, d, t in outcomes]}


def _legacy_to_random_choice(choice):
    label, key, delta, text = choice
    magnitude = abs(int(delta))
    if magnitude <= 3:
        risk = "low"
    elif magnitude <= 8:
        risk = "medium"
    elif magnitude <= 15:
        risk = "high"
    else:
        risk = "extreme"
    return _choice_outcomes(label, key, risk, text, int(delta))


def resolve_haunted_choice(encounter, choice_index, sanity):
    """Resolve one Haunted choice into a randomly weighted outcome.

    ``choose_encounter`` normally converts legacy tuple choices into the
    replayable dictionary format, but this helper also accepts the legacy
    format so older/custom encounter tables remain safe. ``sanity`` is kept
    in the signature because the caller already has the current profile and
    future sanity-sensitive choice resolution can use it without changing
    the exploration callback.
    """
    choices = encounter.get("choices", []) if isinstance(encounter, dict) else []
    if not choices:
        raise ValueError("Haunted encounter has no choices to resolve.")
    if not isinstance(choice_index, int) or not 0 <= choice_index < len(choices):
        raise IndexError("Invalid Haunted choice index.")

    choice = choices[choice_index]
    if not isinstance(choice, dict):
        choice = _legacy_to_random_choice(choice)

    outcomes = choice.get("outcomes", [])
    if not outcomes:
        # Defensive fallback for malformed/custom encounters.
        return choice, {
            "sanity": 0,
            "text": "Nothing happens. Somehow, that feels worse.",
        }

    valid_outcomes = [
        outcome for outcome in outcomes
        if isinstance(outcome, dict) and isinstance(outcome.get("weight"), (int, float))
    ]
    if not valid_outcomes:
        return choice, {
            "sanity": 0,
            "text": "Nothing happens. Somehow, that feels worse.",
        }

    selected = random.choices(
        valid_outcomes,
        weights=[max(0.0, float(outcome["weight"])) for outcome in valid_outcomes],
        k=1,
    )[0]
    return choice, selected


def _make_spooky_encounter(text, choices):
    """Compact helper for adding lots of bespoke scenes without huge boilerplate."""
    return {"text": text, "choices": [
        _choice_outcomes(label, key, risk, flavor, delta)
        for label, key, risk, flavor, delta in choices
    ]}

# Extra universal scenes: these can appear in any Haunted location.
UNIVERSAL_ENCOUNTERS.extend([
    _make_spooky_encounter("A light above you flickers in a perfect rhythm. Three short flashes. Two long ones. Then it spells your name in Morse code.", [
        ("💡 Count the flashes", "count", "medium", "You count carefully. The pattern changes when you reach the last letter.", -6),
        ("📸 Record it", "record", "high", "The recording contains a second set of flashes that you never saw.", -10),
        ("🚶 Ignore it", "ignore", "low", "You keep walking. The light continues flashing behind you.", 0),
    ]),
    _make_spooky_encounter("A door marked EXIT is standing open. Cold air pours through it, and you can hear your own footsteps on the other side.", [
        ("🚪 Go through", "exit", "extreme", "The other side looks exactly like where you were standing.", -14),
        ("👂 Listen", "listen", "medium", "Your footsteps stop. Something else's footsteps continue.", -5),
        ("↩️ Walk away", "away", "low", "You leave the exit alone. The door quietly closes.", 0),
    ]),
    _make_spooky_encounter("A vending machine hums in an empty corridor. Its display reads: THANK YOU FOR RETURNING.", [
        ("🥤 Press a button", "press", "medium", "A drink drops. The label has today's date and your name.", -6),
        ("🔌 Unplug it", "unplug", "high", "The machine keeps humming after the cord is in your hand.", -9),
        ("🚶 Leave it", "leave", "low", "You walk past. A can rolls after you and stops at your heel.", 0),
    ]),
    _make_spooky_encounter("Your shadow takes one extra step after you stop moving.", [
        ("👀 Watch it", "watch", "high", "It catches up to you and stands exactly where it should.", -8),
        ("🔦 Shine a light", "light", "medium", "The shadow disappears. Yours remains a second too long.", -5),
        ("🏃 Keep walking", "walk", "low", "You keep moving. The extra step never happens again. You think.", 0),
    ]),
    _make_spooky_encounter("A phone rings somewhere nearby. When you answer it, there is only the sound of a room you are not currently in.", [
        ("📞 Stay on the line", "stay", "high", "You hear yourself pick up another phone on the other end.", -10),
        ("🗣️ Ask who is calling", "ask", "medium", "A voice whispers, 'You are.'", -6),
        ("📵 Hang up", "hang", "low", "The ringing continues from somewhere much closer.", -1),
    ]),
    _make_spooky_encounter("You find a handwritten note on the floor: 'If you see yourself, do not let it know you noticed.'", [
        ("📜 Read the back", "back", "high", "The back says: 'Too late.'", -11),
        ("👀 Look around", "look", "medium", "You see nobody. You hear somebody breathe beside you.", -6),
        ("🚶 Keep moving", "move", "low", "You fold the note and leave it behind. It is in your pocket again a minute later.", -1),
    ]),
    _make_spooky_encounter("For a moment, every sound around you cuts out. Even your own breathing disappears.", [
        ("🤫 Wait", "wait", "medium", "The silence lasts just long enough for you to hear something whisper from inside your chest.", -9),
        ("👏 Make noise", "noise", "high", "Your clap echoes from somewhere far below you.", -7),
        ("🚶 Move", "move", "low", "Sound returns all at once. Something had been walking beside you.", -2),
    ]),
    _make_spooky_encounter("A familiar smell reaches you: home. Then you realize it is coming from behind a wall that should be solid.", [
        ("🧱 Search the wall", "wall", "high", "You find a warm doorknob embedded in the concrete.", -9),
        ("👃 Follow the smell", "follow", "medium", "The smell fades as soon as you move toward it.", -5),
        ("🚶 Leave it alone", "leave", "low", "You walk away. The smell follows for three more turns.", 0),
    ]),
])


# Extra encounters are intentionally separate so the original tables remain easy
# to read/edit. They are merged into the location pools when choose_encounter runs.
EXTRA_LOCATION_ENCOUNTERS = {
    "asylum": [
        _make_spooky_encounter("The intercom announces a patient's discharge. The patient is you.", [("📢 Answer", "answer", "high", "The speaker clicks on.", -8), ("🔌 Cut the wire", "cut", "medium", "The announcement continues.", -5), ("🚪 Keep walking", "walk", "low", "You refuse to listen.", -1)]),
        _make_spooky_encounter("A treatment room contains a mirror covered with a sheet. Something underneath the sheet is breathing.", [("🪞 Lift the sheet", "lift", "extreme", "You uncover the mirror.", -15), ("👂 Listen", "listen", "medium", "You listen to the breathing.", -5), ("🚪 Leave", "leave", "low", "You close the door.", -1)]),
        _make_spooky_encounter("A nurse's station computer is still logged in. The patient's next appointment is scheduled for you.", [("💻 Open the file", "open", "high", "You open the appointment.", -10), ("🗑️ Delete it", "delete", "medium", "You remove the appointment.", -4), ("🚶 Walk away", "away", "low", "You leave the terminal alone.", 0)]),
        _make_spooky_encounter("A row of observation windows fogs from the inside, one after another, toward you.", [("🔦 Check the last window", "check", "high", "You approach the final window.", -9), ("🏃 Run past", "run", "medium", "You hurry through the corridor.", -4), ("👁️ Watch", "watch", "extreme", "You wait for the last window to fog.", -13)]),
    ],
    "graveyard": [
        _make_spooky_encounter("A grave is open. Inside is a perfectly dry umbrella, still dripping rain.", [("☂️ Take it", "take", "medium", "You lift the umbrella.", -5), ("🪦 Inspect the grave", "inspect", "high", "You look inside.", -10), ("🚶 Leave", "leave", "low", "You walk past.", 0)]),
        _make_spooky_encounter("A mausoleum door is covered in scratches from the outside. One final scratch appears while you watch.", [("🚪 Open it", "open", "extreme", "You touch the handle.", -15), ("🖐️ Touch the scratches", "touch", "medium", "You run your fingers over the stone.", -5), ("🏃 Back away", "back", "low", "You retreat.", -1)]),
        _make_spooky_encounter("Every candle on a distant grave lights at once. There are no candles on that grave.", [("🕯️ Approach", "approach", "high", "You move toward the lights.", -9), ("🔦 Shine a light", "light", "medium", "You illuminate the grave.", -4), ("↩️ Turn away", "away", "low", "You refuse to investigate.", 0)]),
        _make_spooky_encounter("A voice from beneath the soil asks, very politely, whether you could close the gate behind you.", [("🗣️ Answer", "answer", "high", "You answer the voice.", -10), ("🚪 Check the gate", "gate", "medium", "You look toward the entrance.", -5), ("🏃 Leave", "leave", "low", "You decide the gate can stay open.", -1)]),
    ],
    "haunted_house": [
        _make_spooky_encounter("A hallway is filled with family photographs. In every one, the family is looking at something behind the camera.", [("📸 Inspect one", "inspect", "medium", "You study a photograph.", -6), ("🖼️ Turn one around", "turn", "high", "You flip the frame over.", -10), ("🚪 Leave", "leave", "low", "You leave the hallway.", 0)]),
        _make_spooky_encounter("A child's voice counts from upstairs. It reaches ten, then starts counting backward from twelve.", [("⬆️ Go upstairs", "up", "high", "You climb the stairs.", -10), ("📢 Call out", "call", "medium", "You answer the counting.", -5), ("🚪 Lock the door", "lock", "low", "You secure the nearest door.", -1)]),
        _make_spooky_encounter("The front door opens to reveal the exact room you just left.", [("🚪 Step through", "step", "extreme", "You cross the threshold.", -15), ("🔒 Shut it", "shut", "medium", "You close the door.", -4), ("🧭 Find another exit", "exit", "high", "You search the house for another way out.", -8)]),
        _make_spooky_encounter("Something runs across the ceiling above you. The ceiling is too low for anything to fit there.", [("👀 Look up", "look", "high", "You look directly overhead.", -9), ("🏃 Run", "run", "medium", "You sprint down the hall.", -5), ("🧍 Stay still", "still", "low", "You refuse to look up.", -2)]),
    ],
    "church": [
        _make_spooky_encounter("The organ plays one note. Then another. Together they form the first two notes of a song you know.", [("🎹 Approach the organ", "organ", "high", "You walk toward the organ.", -9), ("🎶 Listen", "listen", "medium", "You wait for the next note.", -4), ("🚪 Leave", "leave", "low", "You step away.", 0)]),
        _make_spooky_encounter("A row of empty pews creaks as if people are sitting down one by one.", [("🪑 Look between the pews", "look", "high", "You inspect the empty seats.", -9), ("🙏 Sit down", "sit", "medium", "You take a seat.", -5), ("🚶 Keep moving", "move", "low", "You continue toward the exit.", -1)]),
        _make_spooky_encounter("Holy water in the font ripples in the shape of fingerprints moving across the surface.", [("💧 Touch it", "touch", "high", "You touch the water.", -10), ("🔦 Watch", "watch", "medium", "You watch the ripples.", -4), ("🚶 Avoid it", "avoid", "low", "You step around the font.", 0)]),
        _make_spooky_encounter("A locked side door has a handwritten sign: \"DO NOT OPEN DURING THE SECOND BELL.\" The first bell rings.", [("🔑 Search for a key", "key", "medium", "You search the vestry.", -5), ("🚪 Test the door", "test", "high", "You put your hand on the handle.", -11), ("🏃 Leave", "leave", "low", "You decide not to wait for the second bell.", -1)]),
    ],
    "witch_woods": [
        _make_spooky_encounter("A trail of lanterns appears between the trees. Every lantern is lit, but none has a flame.", [("🏮 Follow them", "follow", "high", "You enter the lantern trail.", -10), ("🔦 Inspect one", "inspect", "medium", "You approach a lantern.", -5), ("🌲 Leave the trail", "leave", "low", "You stay among the trees.", 0)]),
        _make_spooky_encounter("You hear someone calling for help. The voice comes from a tree trunk.", [("🌳 Cut the bark", "cut", "extreme", "You touch the trunk.", -15), ("👂 Listen", "listen", "medium", "You put your ear against the bark.", -6), ("🏃 Walk away", "away", "low", "You leave the voice behind.", -1)]),
        _make_spooky_encounter("A circle of mushrooms has grown around your footprints. You did not make the circle.", [("🍄 Step inside", "step", "high", "You step into the ring.", -12), ("🔦 Examine it", "examine", "medium", "You inspect the mushrooms.", -5), ("🚶 Step around", "around", "low", "You avoid the circle.", 0)]),
        _make_spooky_encounter("The forest suddenly smells like smoke. A tiny cottage appears between two trees that were not there a moment ago.", [("🏚️ Approach", "approach", "high", "You walk toward the cottage.", -10), ("👃 Follow the smoke", "smoke", "medium", "You follow the smell.", -5), ("🏃 Run", "run", "low", "You move away quickly.", -2)]),
    ],
    "dilapidated_pizzeria": [
        _make_spooky_encounter("A birthday song starts in the dining room. The speakers announce the guest of honor as \"you.\"", [("🎂 Go to the dining room", "dining", "high", "You follow the music.", -10), ("🔌 Cut the power", "power", "medium", "You search for the breaker.", -5), ("🏃 Hide", "hide", "low", "You duck behind the counter.", -1)]),
        _make_spooky_encounter("The mascot's shadow crosses the wall. There is no mascot in the room.", [("🎭 Follow the shadow", "follow", "high", "You follow its direction.", -11), ("💡 Turn on the lights", "lights", "medium", "You flood the room with light.", -5), ("🚪 Leave", "leave", "low", "You exit the room.", 0)]),
        _make_spooky_encounter("A ticket dispenser prints one ticket: \"ADMIT ONE — RETURNING GUEST.\"", [("🎟️ Take the ticket", "ticket", "medium", "You take it.", -6), ("🗑️ Tear it up", "tear", "high", "You destroy the ticket.", -9), ("🚶 Leave it", "leave", "low", "You leave it in the dispenser.", 0)]),
        _make_spooky_encounter("A party room is decorated for a birthday that happened exactly one year from today.", [("🎈 Enter", "enter", "high", "You step inside.", -10), ("📅 Check the date", "date", "medium", "You inspect the decorations.", -5), ("🚪 Close the door", "close", "low", "You shut the party room.", -1)]),
    ],
    "abandoned_toy_workshop": [
        _make_spooky_encounter("A row of dolls whispers the same sentence: \"Which one are you?\"", [("🧸 Answer", "answer", "high", "You answer the dolls.", -10), ("👁️ Count them", "count", "medium", "You count the dolls.", -5), ("🚶 Leave", "leave", "low", "You walk away.", 0)]),
        _make_spooky_encounter("A wind-up toy walks toward you, stops, and points behind you.", [("↩️ Look behind you", "look", "high", "You turn around.", -11), ("🧸 Pick it up", "pick", "medium", "You lift the toy.", -5), ("🏃 Walk away", "away", "low", "You keep moving.", -1)]),
        _make_spooky_encounter("A factory speaker says: \"Assembly complete. One guest remains.\"", [("📢 Ask who the guest is", "ask", "high", "You speak toward the speaker.", -9), ("🔌 Shut it off", "shut", "medium", "You find the speaker controls.", -5), ("🚪 Leave", "leave", "low", "You head for the exit.", 0)]),
        _make_spooky_encounter("A toy train carries tiny passengers. Every passenger turns to face you as it passes.", [("🚂 Stop the train", "stop", "high", "You reach for the train.", -10), ("👀 Watch it pass", "watch", "medium", "You watch the passengers.", -5), ("🚶 Ignore it", "ignore", "low", "You keep walking.", 0)]),
    ],
    "broadcast_station": [
        _make_spooky_encounter("A monitor displays a live feed of the hallway. The timestamp is five minutes in the future.", [("📺 Watch it", "watch", "high", "You wait for the future feed to catch up.", -10), ("⏱️ Compare clocks", "compare", "medium", "You compare the timestamp.", -5), ("🔌 Turn it off", "off", "low", "You shut down the monitor.", 0)]),
        _make_spooky_encounter("The station's emergency tone sounds. The announcement that follows is only your breathing.", [("🎙️ Enter the booth", "booth", "high", "You follow the sound.", -11), ("🔊 Turn up the volume", "volume", "medium", "You increase the volume.", -5), ("🚪 Leave", "leave", "low", "You walk away.", -1)]),
        _make_spooky_encounter("A red light blinks above a locked studio: RECORDING IN PROGRESS. The room is empty.", [("🚪 Enter", "enter", "high", "You unlock the studio.", -10), ("🎧 Listen at the door", "listen", "medium", "You listen through the glass.", -5), ("🏃 Leave", "leave", "low", "You leave the studio alone.", 0)]),
        _make_spooky_encounter("The control console prints a single strip of paper: \"PLEASE STOP LISTENING TO YOURSELF.\"", [("📜 Read the rest", "read", "medium", "You pull the paper free.", -5), ("🖨️ Destroy the printer", "destroy", "high", "You attack the printer.", -9), ("🚶 Walk away", "away", "low", "You leave the message behind.", 0)]),
    ],
    "endless_hotel": [
        _make_spooky_encounter("A maid pushes a cart past you. Every room key on it is labeled 314.", [("🗝️ Take a key", "take", "high", "You reach for one key.", -10), ("🛎️ Ask where 314 is", "ask", "medium", "You ask the maid.", -5), ("🚶 Let her pass", "pass", "low", "You step aside.", 0)]),
        _make_spooky_encounter("The lobby directory now lists your name under \"Staff.\"", [("📖 Check the directory", "check", "medium", "You inspect the listing.", -6), ("🖊️ Cross it out", "cross", "high", "You remove your name.", -9), ("🚪 Leave the lobby", "leave", "low", "You ignore the directory.", 0)]),
        _make_spooky_encounter("A hallway sign says EXIT. Behind it is another hallway sign that says EXIT.", [("➡️ Follow the signs", "follow", "high", "You follow the exit signs.", -10), ("🔦 Inspect the walls", "inspect", "medium", "You inspect the signs.", -5), ("↩️ Turn around", "turn", "low", "You abandon the signs.", -1)]),
        _make_spooky_encounter("A guest leaves a room and whispers, \"Don't let the hotel learn your face.\"", [("🗣️ Ask what they mean", "ask", "high", "You stop the guest.", -9), ("👤 Hide your face", "hide", "medium", "You cover your face.", -5), ("🚶 Keep walking", "walk", "low", "You let the guest disappear.", 0)]),
    ],
    "fogbound_town": [
        _make_spooky_encounter("A traffic light changes colors despite having no power. It turns green when you stop.", [("🚦 Cross", "cross", "medium", "You cross the intersection.", -5), ("🔦 Inspect it", "inspect", "high", "You approach the signal.", -9), ("🚶 Wait", "wait", "low", "You wait for another signal.", 0)]),
        _make_spooky_encounter("A distant church bell rings. The fog briefly clears around a single empty chair in the street.", [("🪑 Approach the chair", "chair", "high", "You walk toward it.", -10), ("🔔 Follow the bell", "bell", "medium", "You follow the sound.", -5), ("🏃 Leave", "leave", "low", "You move away.", -1)]),
        _make_spooky_encounter("A mailbox contains a letter addressed to you. The return address is your current location.", [("✉️ Open it", "open", "high", "You open the letter.", -11), ("📮 Put it back", "back", "low", "You return the letter.", -1), ("🔥 Burn it", "burn", "medium", "You destroy the letter.", -5)]),
        _make_spooky_encounter("A car drives past with no driver. Its headlights stop on you and remain there.", [("🚗 Follow it", "follow", "high", "You follow the car.", -10), ("🔦 Watch it", "watch", "medium", "You watch the headlights.", -5), ("🏃 Hide", "hide", "low", "You step out of sight.", -1)]),
    ],
    "derelict_research_facility": [
        _make_spooky_encounter("A lab speaker repeats: \"Containment remains stable.\" Something heavy hits the other side of the wall.", [("🔬 Find the source", "source", "high", "You search the containment wing.", -10), ("🔊 Listen", "listen", "medium", "You wait for another impact.", -5), ("🚪 Leave", "leave", "low", "You walk away.", 0)]),
        _make_spooky_encounter("A microscope is focused on a slide labeled with today's date. The sample moves when you breathe.", [("🔬 Look through it", "look", "high", "You look into the microscope.", -10), ("🧪 Move the slide", "move", "medium", "You touch the slide.", -6), ("🚶 Step away", "away", "low", "You back away.", -1)]),
        _make_spooky_encounter("A red containment light turns green. The door behind you unlocks.", [("🚪 Open it", "open", "extreme", "You turn the handle.", -15), ("🔒 Lock it again", "lock", "high", "You reach for the controls.", -9), ("🏃 Run", "run", "medium", "You leave the area.", -5)]),
        _make_spooky_encounter("A research log ends mid-sentence: \"If the specimen starts using the doors, do not—\"", [("📖 Find the next page", "page", "high", "You search the desk.", -10), ("🗑️ Destroy the log", "destroy", "medium", "You tear the log apart.", -5), ("🚶 Leave", "leave", "low", "You leave the warning intact.", 0)]),
    ],
}

# Final location expansion. The encounter tables stay separate from the core run logic.
EXTRA_LOCATION_ENCOUNTERS_ADDITIONAL = {
    "asylum": [
        _make_spooky_encounter("The intercom crackles: 'Doctor, your patient is waiting.' A wheelchair rolls into view with nobody in it.", [("🪑 Stop it", "stop", "high", "The wheelchair stops. Its seat is still warm.", -9), ("📢 Answer the intercom", "answer", "medium", "A patient whispers your name through the speaker.", -6), ("🚶 Keep walking", "walk", "low", "You pass it. The wheels turn to follow you.", -1)]),
        _make_spooky_encounter("A row of locked treatment rooms all display the same patient number. It is the number on your badge.", [("🔐 Try one", "open", "high", "Every lock clicks at once.", -10), ("📋 Find the patient file", "file", "medium", "The file says you were admitted three years before you were born.", -7), ("🏃 Leave the corridor", "leave", "low", "You leave before any door opens.", 0)]),
    ],
    "graveyard": [
        _make_spooky_encounter("A funeral procession moves between the graves without making a sound. Every mourner carries an empty coffin key.", [("⚰️ Follow them", "follow", "high", "The procession vanishes behind a tomb. One key remains in your hand.", -10), ("🔑 Inspect a key", "key", "medium", "It is warm and engraved with your initials.", -6), ("🚶 Hide", "hide", "low", "The procession passes. The last mourner stops and looks directly at you.", -2)]),
        _make_spooky_encounter("A grave marker slowly rotates in the soil until it faces you. The date is tomorrow.", [("🪦 Read it", "read", "high", "The name is yours, but the handwriting is yours too.", -11), ("🌹 Cover it", "cover", "medium", "The marker sinks back into the earth.", -5), ("🏃 Run", "run", "low", "You run. The marker is facing you again when you look back.", -1)]),
    ],
    "haunted_house": [
        _make_spooky_encounter("A bedroom door is slightly open. Inside, a music box plays a melody you recognize from childhood.", [("🧸 Enter", "enter", "high", "The room is arranged exactly like a bedroom you remember.", -10), ("🎵 Listen", "listen", "medium", "The melody stops one note before the ending.", -5), ("🚪 Close it", "close", "low", "The door closes. A handprint appears on your side of the wood.", -2)]),
        _make_spooky_encounter("You hear footsteps upstairs. Then you remember there is no second floor.", [("⬆️ Look for the stairs", "stairs", "extreme", "A staircase is waiting behind a wall that was solid before.", -14), ("🔦 Check the ceiling", "ceiling", "high", "Something walks across the ceiling above you.", -9), ("🚶 Ignore it", "ignore", "low", "The footsteps stop. Then they start underneath you.", -2)]),
    ],
    "church": [
        _make_spooky_encounter("The church bell rings thirteen times. Every candle goes out except one beside an empty confession booth.", [("⛪ Enter the booth", "booth", "high", "A voice on the other side says, 'I know.'", -10), ("🕯️ Take the candle", "candle", "medium", "The flame burns black without producing smoke.", -6), ("🚪 Leave", "leave", "low", "The thirteenth bell rings again as you step outside.", -1)]),
        _make_spooky_encounter("A hymn begins from the choir loft. The lyrics describe what you are doing one sentence ahead of time.", [("🎶 Keep listening", "listen", "high", "The next verse describes your next choice.", -10), ("⬆️ Go to the loft", "loft", "extreme", "The choir stalls are empty except for one wet footprint.", -13), ("🏃 Leave the nave", "leave", "low", "The hymn follows you through the doorway.", -2)]),
    ],
    "witch_woods": [
        _make_spooky_encounter("A tree has a small wooden door in its trunk. Something inside knocks whenever you look away.", [("🚪 Open it", "open", "extreme", "The door opens into a room larger than the tree.", -15), ("👂 Knock back", "knock", "high", "Three knocks answer from every tree around you.", -9), ("🌲 Walk away", "away", "low", "You leave. The knocking follows at your exact walking pace.", -1)]),
        _make_spooky_encounter("A fox watches you from the trail. It opens its mouth and says your name in a human voice.", [("🦊 Approach", "approach", "high", "The fox is gone. Your own footprints now lead toward it.", -9), ("🗣️ Answer", "answer", "medium", "The fox repeats you perfectly from deeper in the woods.", -6), ("🏃 Back away", "back", "low", "You retreat without taking your eyes off it.", -2)]),
    ],
    "dilapidated_pizzeria": [
        _make_spooky_encounter("The arcade cabinets power on together. Every screen displays the same security camera feed: the room you are in, ten seconds from now.", [("🕹️ Watch", "watch", "high", "The future feed shows something entering behind you.", -10), ("🔌 Shut them down", "shutdown", "medium", "The cabinets go dark one by one. The last screen keeps watching.", -6), ("🏃 Leave", "leave", "low", "You leave before the feed catches up.", -1)]),
        _make_spooky_encounter("A mascot costume hangs from a hook. Its head slowly turns toward you without the body moving.", [("🎭 Inspect it", "inspect", "high", "There is breathing inside the costume.", -11), ("✂️ Cut the straps", "cut", "medium", "The costume collapses. Footsteps run away inside it.", -7), ("🚪 Leave", "leave", "low", "You close the door. Something knocks from the other side.", -2)]),
    ],
    "abandoned_toy_workshop": [
        _make_spooky_encounter("A child's drawing shows the workshop, including a tiny figure standing exactly where you are.", [("🖍️ Take the drawing", "take", "medium", "The figure on the page moves closer to the drawn doorway.", -7), ("👁️ Study it", "study", "high", "The drawing gains another figure behind you.", -10), ("🚶 Leave it", "leave", "low", "You walk away. Crayon footsteps appear behind you.", -1)]),
        _make_spooky_encounter("A toy telephone rings from inside a sealed crate. When you answer, a child whispers, 'I can hear you outside.'", [("📞 Talk", "talk", "high", "The child asks why you are pretending not to be inside.", -10), ("📦 Open the crate", "crate", "extreme", "The crate is empty except for a ringing phone.", -14), ("🚶 Walk away", "away", "low", "The ringing follows you through the workshop.", -2)]),
    ],
    "broadcast_station": [
        _make_spooky_encounter("The emergency broadcast tone starts. The screen reads: THIS MESSAGE IS FOR THE PERSON READING IT.", [("📺 Keep watching", "watch", "high", "The broadcast shows your current screen from an angle you cannot possibly be viewed from.", -11), ("📻 Change frequency", "frequency", "medium", "Every frequency is the same voice counting backward.", -6), ("🔌 Kill power", "power", "low", "The room goes dark. The emergency tone continues.", -3)]),
        _make_spooky_encounter("A reel-to-reel tape is labeled with the exact time. It is currently playing yesterday's version of this room.", [("📼 Listen", "listen", "high", "You hear yourself enter the room before you remember doing it.", -10), ("⏪ Rewind", "rewind", "medium", "The tape rewinds past the beginning into a recording of static breathing.", -7), ("🛑 Stop it", "stop", "low", "The tape stops. Your name is whispered from the empty booth.", -2)]),
    ],
    "endless_hotel": [
        _make_spooky_encounter("The elevator opens. Inside, every button is labeled 314.", [("🛗 Enter", "enter", "extreme", "The doors close before you press anything.", -14), ("🔢 Press one", "press", "high", "The elevator descends below the hotel's lowest possible floor.", -10), ("🚶 Walk away", "away", "low", "The elevator stays open behind you until you stop looking at it.", -2)]),
        _make_spooky_encounter("A guest stands at the end of the corridor holding a suitcase. When you blink, the suitcase is beside your feet.", [("🧳 Open it", "open", "high", "Inside is a hotel key and a receipt for a room you have never visited.", -9), ("👤 Approach the guest", "approach", "medium", "The guest is wearing your clothes and facing the wrong direction.", -7), ("🚪 Enter a room", "room", "low", "The door opens to a corridor that looks exactly like this one.", -2)]),
    ],
    "fogbound_town": [
        _make_spooky_encounter("A school bus rolls through the fog with no driver. Every seat is occupied by a motionless silhouette.", [("🚌 Flag it down", "bus", "high", "The doors open. Every silhouette turns toward you at once.", -11), ("🔦 Watch it pass", "watch", "medium", "The bus disappears, but its headlights remain in the fog.", -6), ("🏃 Hide", "hide", "low", "You duck away. A child's voice asks why you're hiding.", -2)]),
        _make_spooky_encounter("A traffic light changes from red to green even though there is no intersection. Something starts crossing the road anyway.", [("🚦 Watch it", "watch", "medium", "A line of people crosses without making footprints.", -7), ("🚶 Cross", "cross", "high", "You reach the other side, but the street is now behind you.", -10), ("🏠 Enter a building", "enter", "low", "You take shelter. The door locks from the outside.", -2)]),
    ],
    "derelict_research_facility": [
        _make_spooky_encounter("The facility's PA system announces a containment breach in a sector that was demolished years ago.", [("🚨 Investigate", "investigate", "high", "The corridor to the demolished sector is still here.", -10), ("🔒 Lock down", "lockdown", "medium", "Every door closes except the one behind you.", -7), ("🚪 Keep moving", "move", "low", "The announcement repeats with your name substituted for the sector.", -2)]),
        _make_spooky_encounter("A specimen tray contains a single glass vial labeled with a date that has not happened yet.", [("🧪 Inspect it", "inspect", "high", "The liquid moves toward your hand before you touch the vial.", -9), ("📋 Read the label", "read", "medium", "The label adds one word: 'again.'", -6), ("🚶 Leave it", "leave", "low", "You leave the tray untouched. The vial rolls after you.", -1)]),
    ],
    "yellow_halls": [
        _make_spooky_encounter("The fluorescent lights hum in perfect unison. Then one goes out. Then another. The darkness is moving toward you.", [("💡 Follow the darkness", "follow", "extreme", "You walk into the dark. The lights come back on behind you in a different hallway.", -15), ("🏃 Run", "run", "high", "You sprint until the hum returns. Your footprints are wet now.", -9), ("🧍 Stay still", "still", "medium", "The darkness stops one light away.", -6)]),
        _make_spooky_encounter("You turn a corner and find the same corner. The stain on the carpet is now closer to you.", [("↩️ Turn back", "back", "high", "The hallway behind you is the hallway you just left, but longer.", -10), ("🧭 Mark the wall", "mark", "medium", "Your mark appears twenty feet ahead before you make it.", -7), ("🚶 Keep walking", "walk", "low", "You keep walking. The carpet becomes dry beneath your feet.", -2)]),
        _make_spooky_encounter("A buzzing ceiling light contains a tiny sound like distant rain. When you look up, something taps from inside the fixture.", [("💡 Inspect it", "inspect", "high", "The tapping answers in the rhythm of your heartbeat.", -9), ("🔌 Break the light", "break", "extreme", "Glass falls upward.", -13), ("🚶 Ignore it", "ignore", "low", "You move on. The tapping follows through every light.", -1)]),
        _make_spooky_encounter("You find a room with a single chair. A handwritten note says: 'WAIT HERE UNTIL YOU HEAR THE OCEAN.'", [("🪑 Sit", "sit", "high", "The room slowly fills with the sound of waves.", -10), ("📜 Take the note", "note", "medium", "The note now says: 'TOO LATE.'", -7), ("🚪 Leave", "leave", "low", "You leave. You can still hear waves beneath the carpet.", -2)]),
        _make_spooky_encounter("A fluorescent light flickers. For one frame of darkness, the hallway is full of people standing shoulder to shoulder.", [("👁️ Wait for the next flicker", "wait", "high", "They are closer when the light returns.", -11), ("🏃 Run", "run", "medium", "You run. The fluorescent buzz follows without changing volume.", -7), ("🔦 Use your own light", "flashlight", "low", "Your flashlight works. The hallway is empty. You wish it weren't.", -3)]),
        _make_spooky_encounter("A carpeted hallway ends at a familiar door. You know what is behind it before you touch the handle.", [("🚪 Open it", "open", "extreme", "It opens onto your own room, except the lights are on and nobody is home.", -14), ("🗝️ Check the handle", "handle", "medium", "The handle is warm from the other side.", -6), ("↩️ Turn away", "away", "low", "You walk back. The door is now behind you.", -2)]),
        _make_spooky_encounter("The carpet squelches under your shoes. You look down and realize it is not wet; it is breathing.", [("👟 Step back", "back", "high", "The carpet exhales beneath your heel.", -9), ("🔦 Inspect it", "inspect", "extreme", "The pattern moves like thousands of tiny closed eyes.", -15), ("🏃 Run", "run", "medium", "You run until the carpet becomes dry again.", -6)]),
        _make_spooky_encounter("An EXIT sign hangs upside down. Beneath it is another EXIT sign. Beneath that is another.", [("⬆️ Follow the signs", "signs", "high", "Each sign leads to a smaller hallway with the same sign.", -10), ("🔨 Knock it down", "knock", "medium", "The sign hits the floor and immediately points at you.", -7), ("🚶 Ignore them", "ignore", "low", "You keep walking. The signs stop appearing.", 0)]),
    ],
    "dead_end_highway": [
        _make_spooky_encounter("A gas station appears ahead. Its sign says OPEN, but every pump display reads 0000.", [("⛽ Enter", "enter", "high", "The clerk behind the counter is facing the wall and quietly humming your ringtone.", -10), ("🔦 Check the pumps", "pumps", "medium", "One pump displays your current Sanity instead of a price.", -7), ("🚗 Keep driving", "drive", "low", "You pass it. Five miles later, it is beside the road again.", -1)]),
        _make_spooky_encounter("A hitchhiker stands beside the road. You pass them. Ten minutes later, they are standing farther ahead.", [("🚗 Stop", "stop", "high", "The passenger door opens before you unlock it.", -11), ("📻 Watch them", "watch", "medium", "They raise one hand. Your radio fills with static.", -6), ("🛣️ Keep driving", "drive", "low", "You refuse to stop. The hitchhiker appears in the rearview mirror anyway.", -2)]),
        _make_spooky_encounter("A road sign reads: NEXT EXIT — 1 MILE. Another identical sign appears every mile.", [("🛣️ Take the exit", "exit", "high", "The exit loops directly back onto the same road.", -9), ("🗺️ Check the map", "map", "medium", "The map has no roads except the one you are on.", -6), ("🚗 Keep going", "keep", "low", "The signs eventually stop. So do the stars.", -2)]),
        _make_spooky_encounter("You pass an abandoned car with its hazard lights blinking. There is a handprint on the inside of the windshield.", [("🚗 Stop and inspect", "inspect", "high", "The driver's seat is warm and the keys are still in the ignition.", -9), ("📻 Check the radio", "radio", "medium", "The radio is tuned to a recording of your own engine.", -7), ("🛣️ Drive past", "pass", "low", "You keep going. The hazard lights appear in your rearview mirror again.", -1)]),
        _make_spooky_encounter("A motel sign flickers: VACANCY. Then: NO VACANCY. Then: WELCOME BACK.", [("🏨 Get a room", "room", "extreme", "The clerk hands you a key without asking your name.", -13), ("🔑 Inspect the sign", "sign", "medium", "The letters rearrange into your license plate.", -7), ("🚗 Keep moving", "move", "low", "You drive on. The motel disappears when you check the mirror.", 0)]),
        _make_spooky_encounter("The highway lights stop for exactly one mile. In the darkness, something walks beside your car at the same speed.", [("🔦 Flash your lights", "flash", "high", "For a second, you illuminate a figure with far too many joints.", -10), ("🚗 Accelerate", "accelerate", "medium", "The footsteps match your new speed.", -8), ("🛑 Slow down", "slow", "low", "The footsteps continue after your car stops.", -4)]),
        _make_spooky_encounter("A payphone rings on the shoulder. The road sign beside it says NO SERVICE.", [("📞 Answer", "answer", "high", "The caller whispers road directions that lead somewhere you have already been.", -10), ("🔌 Check the line", "line", "medium", "The cord disappears into the pavement.", -7), ("🚗 Leave it", "leave", "low", "You drive away. The phone keeps ringing behind you.", -2)]),
        _make_spooky_encounter("You look at the odometer. The numbers are counting backward.", [("🔢 Watch it", "watch", "high", "The odometer reaches zero. The road keeps going.", -10), ("🛑 Pull over", "pull", "medium", "The car stops, but the road continues moving beneath you.", -8), ("🚗 Ignore it", "ignore", "low", "You keep driving. The odometer starts counting forward again.", -2)]),
    ],
    "drowned_station": [
        _make_spooky_encounter("A station announcement crackles overhead: 'The next train arrives in one minute.' The tracks are completely submerged.", [("🚇 Wait on the platform", "wait", "high", "A headlight appears beneath the water.", -11), ("📻 Listen to the announcement", "listen", "medium", "The announcement changes to your name.", -7), ("🏃 Leave the platform", "leave", "low", "You climb the stairs. Wet footprints appear above you.", -2)]),
        _make_spooky_encounter("Something bumps the platform from below. Then it bumps again. Then it knocks three times.", [("🔦 Look into the water", "look", "extreme", "Two pale shapes look back before vanishing into the dark.", -14), ("👂 Listen", "listen", "high", "The knocking matches your heartbeat.", -9), ("🚶 Step away", "away", "low", "The bumps follow the length of the platform.", -3)]),
        _make_spooky_encounter("A transit map is covered in destinations that do not exist. One station is circled: HERE.", [("🗺️ Trace the route", "trace", "high", "The route ends at a platform directly beneath you.", -10), ("✏️ Cross it out", "cross", "medium", "The ink spreads through the map like water.", -6), ("🚶 Leave it", "leave", "low", "You fold the map. A drop of water lands on your hand from nowhere.", -1)]),
        _make_spooky_encounter("A train door is visible through the flooded tunnel. It opens and closes without any train attached.", [("🚪 Approach", "approach", "extreme", "The doorway is standing upright in the water with nothing behind it.", -14), ("🔦 Shine a light", "light", "medium", "The beam reveals a passenger staring back from inside.", -8), ("🏃 Run", "run", "low", "You run up the stairs. Something wet follows for six steps.", -4)]),
        _make_spooky_encounter("The water level suddenly drops. The exposed floor is covered in footprints leading into a sealed tunnel.", [("👣 Follow them", "follow", "high", "The footprints are fresh. Yours appear beside them as you walk.", -10), ("🔒 Check the tunnel", "tunnel", "medium", "The sealed door is warm and wet from the other side.", -7), ("⬆️ Stay above ground", "stay", "low", "You wait. The water rises again without making a sound.", -2)]),
        _make_spooky_encounter("A drowned emergency phone rings beneath the water. The receiver floats upward toward your hand.", [("📞 Answer it", "answer", "extreme", "You hear yourself calling for help from underwater.", -15), ("🔦 Watch it", "watch", "high", "The receiver hangs in the air and rings beside your ear.", -10), ("🏃 Back away", "back", "low", "The phone sinks. The ringing continues below your feet.", -3)]),
        _make_spooky_encounter("A maintenance light flickers under the water. Something tall passes in front of it, far too deep to be standing there.", [("🔦 Track it", "track", "high", "It stops beneath you.", -11), ("🚇 Check the tunnel", "tunnel", "medium", "The water is perfectly still again.", -6), ("🏃 Leave", "leave", "low", "You leave before the light flickers again.", -2)]),
        _make_spooky_encounter("You find a dry newspaper floating on the water. The headline says: STATION CLOSED AFTER PASSENGERS VANISH.", [("📰 Read it", "read", "high", "The article describes you entering the station today.", -10), ("📅 Check the date", "date", "medium", "The date is tomorrow.", -7), ("🚶 Drop it", "drop", "low", "The newspaper floats back to your feet.", -1)]),
    ],
    "silent_campground": [
        _make_spooky_encounter("Your radio switches itself on. Nothing but static. Then, underneath it, a voice whispers: 'Do not look into the trees.'", [("📻 Increase the volume", "volume", "high", "The whisper becomes clearer. It is using your voice.", -10), ("🔌 Turn it off", "off", "medium", "The radio clicks off. Static continues from the trees.", -8), ("🌲 Look toward the trees", "trees", "extreme", "A very tall figure is standing between them. You are certain it was not there before.", -15)]),
        _make_spooky_encounter("A video camera on the ranger station porch is still recording. Its red light turns on when you approach.", [("📹 Check the footage", "footage", "high", "The footage shows you approaching the station from ten minutes ago. Something tall follows you.", -11), ("🔌 Unplug it", "unplug", "medium", "The camera keeps recording with no battery inside.", -7), ("🚶 Leave it", "leave", "low", "You walk away. The red light follows you through the trees.", -2)]),
        _make_spooky_encounter("A burst of static cuts through the forest. For half a second, several black shapes are visible between the trees.", [("📸 Take a picture", "photo", "high", "The picture contains one shape standing directly beside you.", -10), ("🔦 Sweep the trees", "sweep", "medium", "Your flashlight finds nothing. Something taps the back of your headlamp.", -7), ("🏕️ Return to camp", "camp", "low", "You retreat. The static follows you to the tents.", -3)]),
        _make_spooky_encounter("A trail camera flashes. You hear the shutter again even though the camera is facing away from you.", [("📷 Check the camera", "camera", "high", "Its screen shows you standing in the forest from above.", -10), ("🌲 Look up", "up", "extreme", "Black, branch-like limbs are wrapped around the trees overhead.", -14), ("🏃 Keep walking", "walk", "low", "You keep your eyes down. The camera flashes again behind you.", -2)]),
        _make_spooky_encounter("A ranger radio suddenly speaks through the static: 'There is a man standing at your campsite.'", [("📻 Ask where", "ask", "high", "The radio answers: 'Everywhere.'", -9), ("🏕️ Check the campsite", "camp", "extreme", "A very tall silhouette is standing between your tent and the fire ring.", -15), ("🚶 Stay on the trail", "stay", "low", "You refuse to return. Something follows you through the brush.", -4)]),
        _make_spooky_encounter("You find a notebook filled with drawings of the campground. Every page contains the same tall figure, closer each time.", [("📓 Turn the page", "page", "high", "The final drawing is a picture of you holding the notebook.", -11), ("🔥 Burn it", "burn", "medium", "The pages burn without heat. Static pours from the smoke.", -8), ("🚶 Leave it", "leave", "low", "You leave the notebook. It is back in your backpack moments later.", -2)]),
        _make_spooky_encounter("The forest goes completely silent. No insects. No wind. No birds. Then something enormous exhales behind the trees.", [("🔦 Search for it", "search", "extreme", "You see several long black limbs withdraw behind a trunk.", -14), ("🤫 Stay quiet", "quiet", "high", "A second breath comes from the other side of your body.", -10), ("🏃 Run", "run", "medium", "You run until the normal sounds return. You do not remember passing the same tree three times.", -7)]),
        _make_spooky_encounter("Your phone camera turns on by itself. The screen shows the campsite from behind you, but you are standing in front of the camera.", [("📱 Keep watching", "watch", "high", "The screen version of you turns around before you do.", -12), ("🔌 Shut the phone down", "shutdown", "medium", "The screen goes black. A white shape remains reflected in it.", -8), ("📵 Put it away", "away", "low", "You put the phone away. It vibrates once with no notification.", -3)]),
    ],
}
for _location_id, _encounters in EXTRA_LOCATION_ENCOUNTERS_ADDITIONAL.items():
    EXTRA_LOCATION_ENCOUNTERS.setdefault(_location_id, []).extend(_encounters)

LOW_SANITY_HALLUCINATIONS = [
    _make_spooky_encounter("The walls breathe. You know they are not supposed to. They do not seem to know that.", [("🫳 Touch the wall", "touch", "high", "You touch the breathing wall.", -10), ("🏃 Back away", "back", "low", "You retreat.", -2), ("👂 Listen", "listen", "medium", "You listen to the rhythm.", -6)]),
    _make_spooky_encounter("You see someone at the end of the corridor. They look exactly like you. Every time you blink, they are closer.", [("👋 Wave", "wave", "medium", "You raise a hand.", -5), ("🏃 Run", "run", "high", "You run the other way.", -10), ("🧍 Wait", "wait", "extreme", "You wait for them to reach you.", -15)]),
    _make_spooky_encounter("Your hands suddenly look covered in something dark. You blink. They are clean. You blink again.", [("🧼 Wash them", "wash", "low", "You scrub your hands.", -2), ("👀 Look closer", "look", "high", "You inspect your hands.", -10), ("🩸 Smell them", "smell", "medium", "You check for a scent.", -6)]),
    _make_spooky_encounter("A door appears where there was a wall. The sign says: \"THIS IS WHERE YOU LEFT YOURSELF.\"", [("🚪 Open it", "open", "extreme", "You open the impossible door.", -15), ("🪧 Read the sign", "read", "high", "You study the words.", -9), ("🚶 Ignore it", "ignore", "low", "You keep walking.", -1)]),
    _make_spooky_encounter("You hear your name from three directions. One voice is frightened. One is angry. One is laughing.", [("🗣️ Answer the frightened voice", "frightened", "medium", "You answer quietly.", -5), ("😡 Answer the angry voice", "angry", "high", "You answer the angry voice.", -10), ("😂 Answer the laughing voice", "laughing", "extreme", "You answer the laughter.", -16)]),
    _make_spooky_encounter("A person walks through a solid wall and tells you, \"You're not supposed to be awake yet.\"", [("🏃 Follow", "follow", "high", "You follow them.", -11), ("🧱 Touch the wall", "wall", "medium", "You inspect the wall.", -6), ("😶 Say nothing", "silent", "low", "You let them go.", -1)]),
]

LOW_SANITY_HALLUCINATIONS.extend([
    _make_spooky_encounter("You see a door where there was only a wall. You blink. The door is still there, but it is much closer.", [("🚪 Open it", "open", "high", "There is another hallway behind it. You can hear yourself walking inside.", -10), ("👁️ Keep watching", "watch", "medium", "The door slowly becomes part of the wall again.", -6), ("🚶 Walk away", "away", "low", "You refuse to acknowledge it. The doorknob rattles anyway.", -2)]),
    _make_spooky_encounter("Everyone around you is frozen. You are the only thing moving. Then one frozen figure turns its eyes toward you.", [("👀 Approach", "approach", "high", "The figure is suddenly standing behind you.", -11), ("🤫 Stay still", "still", "medium", "The world resumes. Nobody reacts to what happened.", -7), ("🏃 Run", "run", "high", "You run. The frozen crowd turns their heads in perfect unison.", -9)]),
    _make_spooky_encounter("You hear your name from three different directions. All three voices sound tired.", [("🗣️ Answer one", "answer", "high", "All three voices answer you at once.", -10), ("👂 Listen", "listen", "medium", "One voice whispers, 'Please stop making us do this.'", -7), ("🚶 Keep moving", "move", "low", "The voices follow for a while, then begin calling from inside your own head.", -4)]),
    _make_spooky_encounter("Your hands look unfamiliar for a second. When you blink, they are normal. There is dirt under the nails.", [("🖐️ Inspect them", "inspect", "medium", "The dirt contains tiny pieces of black bark.", -7), ("🧼 Clean them", "clean", "high", "The dirt washes off. The water comes out black.", -9), ("🚶 Ignore it", "ignore", "low", "You keep moving. The dirt returns when you stop looking.", -2)]),
    _make_spooky_encounter("You find a second version of the path you are on running parallel to the first. Someone is walking on it.", [("👤 Follow them", "follow", "high", "The other you notices and starts walking faster.", -12), ("📣 Call out", "call", "medium", "They turn. Their face is blurred by static.", -8), ("🚶 Stay on your path", "stay", "low", "You keep your distance. The parallel path eventually disappears.", -3)]),
    _make_spooky_encounter("A familiar room appears around you for one heartbeat. Then it is gone. Something in the room was smiling.", [("🔎 Search for it", "search", "high", "You find a familiar object that you did not bring with you.", -9), ("😶 Freeze", "freeze", "medium", "The room flickers back for another heartbeat.", -7), ("🏃 Run", "run", "low", "You leave the spot behind. Your footsteps briefly sound like someone else's.", -4)]),
    _make_spooky_encounter("Your reflection appears in a dark window. It raises one hand before you do.", [("🪟 Touch the glass", "touch", "extreme", "Your reflection presses back from the other side.", -14), ("👁️ Watch", "watch", "high", "It slowly turns its head toward something behind you.", -10), ("🚶 Walk away", "away", "low", "You leave. The reflection keeps watching through the glass.", -3)]),
    _make_spooky_encounter("You hear applause from somewhere nearby. When you stop, the applause stops. When you move, it resumes.", [("👏 Clap back", "clap", "high", "The applause becomes deafening and impossibly close.", -10), ("👂 Find the source", "find", "medium", "You find an empty room with hundreds of footprints facing you.", -8), ("🚶 Keep moving", "move", "low", "The applause follows until you reach the next stage.", -3)]),
])

INSANE_ENCOUNTERS = [
    _make_spooky_encounter("Every door in the room now has your name on it. One door is already open.", [("🚪 Enter the open door", "open", "extreme", "You step through.", -18), ("🔎 Find another way", "other", "high", "You search the room.", -12), ("🧍 Stay still", "still", "extreme", "You refuse to choose.", -20)]),
    _make_spooky_encounter("Someone is standing directly behind you. You know this because you can see their face reflected in your own eyes.", [("↩️ Turn around", "turn", "extreme", "You turn around.", -18), ("👁️ Close your eyes", "close", "high", "You close your eyes.", -10), ("🗣️ Ask their name", "name", "extreme", "You ask who is there.", -20)]),
    _make_spooky_encounter("The floor says: \"SANITY IS A DOOR.\" The words move when you look away.", [("👁️ Read it again", "read", "high", "You stare at the words.", -12), ("🧹 Smear them away", "smear", "extreme", "You try to erase them.", -18), ("🚪 Search for the door", "door", "extreme", "You search for something that should not exist.", -20)]),
    _make_spooky_encounter("You hear your own voice whisper, \"We're almost out of you.\"", [("🗣️ Answer", "answer", "extreme", "You answer yourself.", -20), ("🏃 Run", "run", "high", "You sprint away.", -12), ("🤫 Stay silent", "silent", "medium", "You refuse to respond.", -7)]),
]
INSANE_ENCOUNTERS.extend([
    _make_spooky_encounter("You find an exit. You open it. Outside is the same place, except a version of you is standing there waiting.", [("🗣️ Ask what happened", "ask", "extreme", "It says, 'You already know.'", -18), ("🚪 Close the door", "close", "high", "The other you puts a hand against the door from the other side.", -13), ("👁️ Step outside", "outside", "extreme", "The door disappears behind you.", -20)]),
    _make_spooky_encounter("The world briefly becomes a badly edited video. Objects jump between positions. Your own body skips forward a few seconds.", [("📹 Watch yourself", "watch", "extreme", "You see yourself make a choice you have not made yet.", -18), ("🧍 Stay still", "still", "high", "Everything catches up at once.", -14), ("🏃 Run", "run", "extreme", "The scene jumps. You are suddenly much farther away.", -20)]),
    _make_spooky_encounter("A voice calmly explains everything you have forgotten. The explanation is completely wrong.", [("👂 Listen", "listen", "high", "The voice describes a childhood you never had.", -15), ("🗣️ Correct it", "correct", "extreme", "The voice laughs because you used the wrong name.", -20), ("🚶 Walk away", "away", "medium", "The voice follows, now speaking from your own mouth.", -9)]),
    _make_spooky_encounter("There is a hallway filled with doors. Every door is labeled with a different version of your name.", [("🚪 Pick one", "pick", "high", "Behind it is a version of you who looks relieved to see you.", -17), ("🔎 Read the labels", "read", "medium", "One label simply says: ORIGINAL.", -12), ("🏃 Run", "run", "extreme", "The hallway gets longer every time you move.", -20)]),
    _make_spooky_encounter("You suddenly remember that you have been in this location for years. You also remember arriving five minutes ago.", [("🧠 Trust the memory", "trust", "high", "You remember a door that does not exist.", -15), ("📝 Write it down", "write", "medium", "Your handwriting writes a different memory than the one you remember.", -11), ("🚶 Ignore it", "ignore", "high", "You forget why you were standing there.", -13)]),
    _make_spooky_encounter("Every sound becomes a voice. Your footsteps say 'stop.' Your breathing says 'run.' The lights say your name.", [("👂 Listen", "listen", "extreme", "All three sounds suddenly agree on the same direction.", -19), ("🔇 Cover your ears", "cover", "high", "The voices continue from inside your skull.", -14), ("🏃 Run", "run", "extreme", "You run toward the voices.", -20)]),
    _make_spooky_encounter("A tall silhouette stands at the end of the corridor. You look away for one second. It is standing at the beginning instead.", [("👁️ Keep watching", "watch", "extreme", "It takes one step closer whenever you blink.", -19), ("🚶 Walk past it", "past", "high", "You pass it. It whispers your name from behind you.", -15), ("🏃 Run", "run", "extreme", "The corridor bends toward the silhouette.", -20)]),
    _make_spooky_encounter("You finally hear an exit alarm. The sound is coming from inside your chest.", [("🫀 Follow the sound", "follow", "extreme", "The alarm gets louder every time you breathe.", -20), ("🤫 Hold your breath", "breath", "high", "The alarm continues anyway.", -16), ("🚶 Keep walking", "walk", "medium", "The alarm becomes distant. You are not sure whether that is better.", -10)]),
])


def _now():
    return time.time()


def game_date():
    return datetime.now(pytz.timezone("US/Eastern")).date().isoformat()


async def ensure_haunted_schema(db):
    """Create Haunted Exploration state tables without touching existing schemas."""
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
            active_started_at REAL NOT NULL DEFAULT 0
        )
        """
    )
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


def calculate_sanity(sanity, updated_at, now=None, regen_multiplier=1.0):
    """Calculate continuous Sanity regeneration without requiring a cron job."""
    if now is None:
        now = _now()

    sanity = max(0.0, min(float(sanity), SANITY_MAX))
    updated_at = float(updated_at or now)
    elapsed = max(0.0, now - updated_at)
    rate = max(0.0, float(regen_multiplier)) / SANITY_REGEN_SECONDS
    return min(SANITY_MAX, sanity + elapsed * rate * SANITY_MAX)


def sanity_percent(sanity):
    return max(0, min(100, int(round(float(sanity)))))


def is_insane(sanity):
    return float(sanity) <= 0


def stage_count_for_sanity(sanity):
    """Return the variable stage count for a new haunted run."""
    sanity = float(sanity)
    if sanity <= 0:
        return random.randint(5, 7)
    if sanity < 50:
        return random.randint(4, 6)
    return random.randint(3, 5)


async def get_or_create_profile(db, user_id):
    today = game_date()
    now = _now()
    await ensure_haunted_schema(db)

    async with db.execute(
        """
        SELECT sanity, sanity_updated_at, haunted_attempts, attempts_date,
               active_location, active_stage, active_total_stages
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
            (user_id, now, HAUNTED_DAILY_ATTEMPTS, today),
        )
        await db.commit()
        return {
            "sanity": 100.0,
            "sanity_updated_at": now,
            "attempts": HAUNTED_DAILY_ATTEMPTS,
            "attempts_date": today,
            "active_location": "",
            "active_stage": 0,
            "active_total_stages": 0,
        }

    sanity, updated_at, attempts, attempts_date, active_location, active_stage, active_total = row
    current_sanity = calculate_sanity(sanity, updated_at, now)

    if attempts_date != today:
        attempts = HAUNTED_DAILY_ATTEMPTS
        attempts_date = today

    await db.execute(
        """
        UPDATE haunted_profiles
        SET sanity = ?, sanity_updated_at = ?, haunted_attempts = ?, attempts_date = ?
        WHERE user_id = ?
        """,
        (current_sanity, now, attempts, attempts_date, user_id),
    )
    await db.commit()

    return {
        "sanity": current_sanity,
        "sanity_updated_at": now,
        "attempts": attempts,
        "attempts_date": attempts_date,
        "active_location": active_location or "",
        "active_stage": active_stage or 0,
        "active_total_stages": active_total or 0,
    }


async def consume_attempt(db, user_id):
    """Atomically consume one daily attempt after refreshing the daily reset."""
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
    """Apply a Sanity change after accounting for regeneration since last access."""
    await ensure_haunted_schema(db)
    now = _now()
    async with db.execute(
        "SELECT sanity, sanity_updated_at FROM haunted_profiles WHERE user_id = ?",
        (user_id,),
    ) as cursor:
        row = await cursor.fetchone()

    if not row:
        sanity = SANITY_MAX
        updated_at = now
    else:
        sanity, updated_at = row
        sanity = calculate_sanity(sanity, updated_at, now, regen_multiplier)

    new_sanity = max(0.0, min(SANITY_MAX, sanity + float(delta)))
    await db.execute(
        "UPDATE haunted_profiles SET sanity = ?, sanity_updated_at = ? WHERE user_id = ?",
        (new_sanity, now, user_id),
    )
    return new_sanity


async def start_run(db, user_id, location_id, sanity):
    """Create/replace the user's active run and arm any matching Haunted effects."""
    total_stages = stage_count_for_sanity(sanity)
    now = _now()

    async with db.execute(
        "SELECT active_effects FROM users WHERE user_id = ?", (user_id,)
    ) as cursor:
        row = await cursor.fetchone()
    try:
        effects = json.loads(row[0] or "{}") if row else {}
        if not isinstance(effects, dict):
            effects = {}
    except (TypeError, ValueError):
        effects = {}

    # A new run replaces any previous run, so old run-scoped modifiers must not
    # leak into the new adventure. The original crafted-item flags remain until
    # they are actually matched to a location/run.
    for key in list(effects):
        if key.startswith("haunted_run_"):
            effects.pop(key, None)

    # Haunted pet abilities are location-bound. They remain on the pet forever,
    # but only arm when the active pet's associated Haunted location matches
    # the location being entered. Normal exploration passives are intentionally
    # handled separately by pets.py/exploration.py and are not gated here.
    pet_effects = await get_active_pet_effects(db, user_id)
    if pet_effects.get("haunted_location") == location_id:
        sanity_reduction = float(pet_effects.get("haunted_sanity_reduction", 0.0))
        if sanity_reduction > 0:
            effects["haunted_run_sanity_multiplier"] = min(
                float(effects.get("haunted_run_sanity_multiplier", 1.0)),
                max(0.0, 1.0 - sanity_reduction),
            )

        ingredient_bonus = float(pet_effects.get("haunted_ingredient_bonus", 0.0))
        if ingredient_bonus > 0:
            effects["haunted_run_ingredient_bonus"] = ingredient_bonus

        reward_bonus = float(pet_effects.get("haunted_reward_bonus", 0.0))
        if reward_bonus > 0:
            effects["haunted_run_reward_bonus"] = reward_bonus

        negative_protection = float(pet_effects.get("haunted_negative_protection", 0.0))
        if negative_protection > 0:
            effects["haunted_run_negative_protection"] = negative_protection

        discovery_bonus = float(pet_effects.get("haunted_discovery_bonus", 0.0))
        if discovery_bonus > 0:
            effects["haunted_run_discovery_bonus"] = discovery_bonus

        stage_reduction = float(pet_effects.get("haunted_stage_reduction", 0.0))
        if stage_reduction > 0 and random.random() < stage_reduction:
            total_stages = max(2, total_stages - 1)
            effects["haunted_run_stage_reduced"] = True

        malo_bonus = float(pet_effects.get("haunted_malo", 0.0))
        if malo_bonus > 0:
            effects["haunted_run_discovery_bonus"] = max(
                float(effects.get("haunted_run_discovery_bonus", 0.0)),
                malo_bonus,
            )
            effects["haunted_run_malo_warning_chance"] = malo_bonus

    # Haunted Cauldron potions become run-scoped effects here.  They are
    # consumed once when the next Haunted run starts, just like the crafted
    # Workshop/Ritual items.
    potion_protection = effects.pop("haunted_potion_run_protection", 0)
    if potion_protection:
        protection = max(0, int(potion_protection)) * 5
        effects["haunted_run_flat_protection"] = max(
            int(effects.get("haunted_run_flat_protection", 0)),
            protection,
        )

    potion_insight = effects.pop("haunted_potion_encounter_insight", 0)
    if potion_insight:
        effects["haunted_run_discovery_bonus"] = float(
            effects.get("haunted_run_discovery_bonus", 0.0)
        ) + (0.05 * float(potion_insight))

    potion_bias = effects.pop("haunted_potion_rare_encounter_bias", 0)
    if potion_bias:
        effects["haunted_run_discovery_bonus"] = float(
            effects.get("haunted_run_discovery_bonus", 0.0)
        ) + (0.05 * float(potion_bias))

    potion_guard = effects.pop("haunted_potion_sanity_guard", 0)
    if potion_guard:
        effects["haunted_run_sanity_multiplier"] = min(
            float(effects.get("haunted_run_sanity_multiplier", 1.0)),
            0.75,
        )

    if effects.pop("haunted_potion_curse_protection", False):
        effects["haunted_run_block_next_negative"] = True

    if effects.pop("haunted_ghost_radio", False):
        effects["haunted_run_force_universal"] = True
    if effects.pop("haunted_watchers_eye", False):
        effects["haunted_run_force_location"] = True
    if effects.pop("haunted_mascot_tracker", False):
        effects["haunted_run_collectible_bonus"] = effects.get("haunted_run_collectible_bonus", 0) + 0.15
    if effects.pop("haunted_spectral_receiver", False):
        effects["haunted_run_collectible_bonus"] = effects.get("haunted_run_collectible_bonus", 0) + 0.10
    if effects.pop("haunted_security_monitor", False):
        effects["haunted_run_flat_protection"] = 5

    if location_id == "endless_hotel" and effects.pop("haunted_room_314_key", False):
        total_stages = max(2, total_stages - 1)
    if location_id == "fogbound_town" and effects.pop("haunted_fog_lantern", False):
        effects["haunted_run_sanity_multiplier"] = min(
            float(effects.get("haunted_run_sanity_multiplier", 1.0)), 0.5
        )
    if location_id == "broadcast_station" and effects.pop("haunted_dead_air_charm", False):
        effects["haunted_run_sanity_multiplier"] = min(
            float(effects.get("haunted_run_sanity_multiplier", 1.0)), 0.5
        )
    if location_id == "endless_hotel" and effects.pop("haunted_empty_room_token", False):
        effects["haunted_run_block_next_negative"] = True
    if location_id == "derelict_research_facility" and effects.pop("haunted_containment_mark", False):
        effects["haunted_run_sanity_multiplier"] = min(
            float(effects.get("haunted_run_sanity_multiplier", 1.0)), 0.25
        )

    if location_id == "yellow_halls" and effects.pop("haunted_yellow_halls_beacon", False):
        effects["haunted_run_sanity_multiplier"] = min(
            float(effects.get("haunted_run_sanity_multiplier", 1.0)), 0.5
        )
    if location_id == "yellow_halls" and effects.pop("haunted_yellow_halls_unmarked_key", False):
        effects["haunted_run_block_next_negative"] = True

    if location_id == "dead_end_highway" and effects.pop("haunted_highway_payphone_kit", False):
        effects["haunted_run_force_universal"] = True
    if location_id == "dead_end_highway" and effects.pop("haunted_highway_motel_ward", False):
        effects["haunted_run_block_next_negative"] = True

    if location_id == "drowned_station" and effects.pop("haunted_drowned_flood_lamp", False):
        effects["haunted_run_sanity_multiplier"] = min(
            float(effects.get("haunted_run_sanity_multiplier", 1.0)), 0.5
        )
    if location_id == "drowned_station" and effects.pop("haunted_drowned_last_stop_ticket", False):
        total_stages = max(2, total_stages - 1)

    if location_id == "silent_campground" and effects.pop("haunted_campground_static_filter", False):
        effects["haunted_run_sanity_multiplier"] = min(
            float(effects.get("haunted_run_sanity_multiplier", 1.0)), 0.5
        )
    if location_id == "silent_campground" and effects.pop("haunted_campground_tendril_ward", False):
        effects["haunted_run_collectible_bonus"] = effects.get("haunted_run_collectible_bonus", 0) + 0.15
    if effects.pop("haunted_warding_sigil", False):
        effects["haunted_run_block_next_negative"] = True
    if effects.pop("haunted_mirror_ward", False):
        effects["haunted_run_half_next_negative"] = True

    await db.execute(
        """
        INSERT INTO haunted_runs
            (user_id, location_id, stage, total_stages, encounter_index, sanity_at_start, created_at)
        VALUES (?, ?, 1, ?, 0, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            location_id = excluded.location_id,
            stage = 1,
            total_stages = excluded.total_stages,
            encounter_index = 0,
            sanity_at_start = excluded.sanity_at_start,
            created_at = excluded.created_at
        """,
        (user_id, location_id, total_stages, float(sanity), now),
    )
    await db.execute(
        """
        UPDATE haunted_profiles
        SET active_location = ?, active_stage = 1, active_total_stages = ?, active_started_at = ?
        WHERE user_id = ?
        """,
        (location_id, total_stages, now, user_id),
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
        SELECT location_id, stage, total_stages, encounter_index, sanity_at_start, created_at
        FROM haunted_runs
        WHERE user_id = ?
        """,
        (user_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        return None
    return {
        "location_id": row[0],
        "stage": row[1],
        "total_stages": row[2],
        "encounter_index": row[3],
        "sanity_at_start": row[4],
        "created_at": row[5],
    }


async def advance_run(db, user_id):
    """Advance the active run and return the new stage, or None when finished."""
    run = await get_active_run(db, user_id)
    if not run:
        return None

    new_stage = run["stage"] + 1
    if new_stage > run["total_stages"]:
        await clear_run(db, user_id)
        return None

    await db.execute(
        "UPDATE haunted_runs SET stage = ?, encounter_index = encounter_index + 1 WHERE user_id = ?",
        (new_stage, user_id),
    )
    await db.execute(
        "UPDATE haunted_profiles SET active_stage = ? WHERE user_id = ?",
        (new_stage, user_id),
    )
    await db.commit()
    return new_stage


async def clear_run(db, user_id):
    await db.execute("DELETE FROM haunted_runs WHERE user_id = ?", (user_id,))
    await db.execute(
        """
        UPDATE haunted_profiles
        SET active_location = '', active_stage = 0, active_total_stages = 0, active_started_at = 0
        WHERE user_id = ?
        """,
        (user_id,),
    )
    async with db.execute("SELECT active_effects FROM users WHERE user_id = ?", (user_id,)) as cursor:
        row = await cursor.fetchone()
    if row:
        try:
            effects = json.loads(row[0] or "{}")
            if not isinstance(effects, dict):
                effects = {}
        except (TypeError, ValueError):
            effects = {}
        for key in list(effects):
            if key.startswith("haunted_run_"):
                effects.pop(key, None)
        await db.execute(
            "UPDATE users SET active_effects = ? WHERE user_id = ?",
            (json.dumps(effects), user_id),
        )
    await db.commit()


LOCATION_ENCOUNTERS = {
    "asylum": [
        {
            "text": "A hospital bed rolls slowly out of a dark treatment room. There is no one pushing it.",
            "choices": [
                ("🛏️ Inspect the bed", "inspect", -7, "The sheets are cold, but something beneath them is still warm."),
                ("🚪 Step around it", "avoid", 0, "You give the bed a wide berth. It rolls after you for several seconds before stopping."),
                ("🔦 Check the room", "room", -4, "The room is empty except for a wall covered in fresh handprints."),
            ],
        },
        {
            "text": "A flickering nurse-call light turns on above an empty room. Then another. Then another.",
            "choices": [
                ("🔔 Answer the call", "answer", -9, "The speaker crackles to life and whispers, \"Please don't leave me here.\""),
                ("🏃 Keep moving", "move", 0, "You keep walking while the call lights follow you down the hall."),
                ("👂 Listen at the door", "listen", -5, "You hear dozens of people breathing on the other side. The room is empty when you open it."),
            ],
        },
        {
            "text": "An old patient chart sits on a desk. The name field is blank, but the observations describe you perfectly.",
            "choices": [
                ("📋 Read the whole chart", "read", -10, "The final observation is dated tomorrow."),
                ("🔥 Burn the chart", "burn", -3, "The paper burns black, but the words remain floating in the air."),
                ("🚶 Leave it alone", "leave", 1, "You leave the chart untouched. Somehow, that feels like the right choice."),
            ],
        },
    ],
    "graveyard": [
        {
            "text": "A grave nearby has fresh soil piled over it. The stone reads only: \"YOU\".",
            "choices": [
                ("⛏️ Dig it up", "dig", -10, "The coffin is empty. Something has already climbed out."),
                ("🪦 Walk past", "pass", 0, "You keep your eyes forward. The grave remains silent."),
                ("🌹 Leave something behind", "tribute", -2, "You leave a small token. The wind immediately stops."),
            ],
        },
        {
            "text": "A line of pale footprints crosses the graveyard and disappears between two mausoleums.",
            "choices": [
                ("👣 Follow them", "follow", -8, "The footprints stop behind you. There are now twice as many."),
                ("🔦 Search the mausoleums", "search", -4, "You find a cracked lantern still burning with a blue flame."),
                ("↩️ Go the other way", "avoid", 1, "You deliberately avoid the trail. Something in the fog seems disappointed."),
            ],
        },
        {
            "text": "The cemetery bell rings once despite having no bell tower. Every nearby grave shifts slightly in the soil.",
            "choices": [
                ("🔔 Ring it back", "ring", -9, "A second bell answers from beneath the ground."),
                ("🧎 Stay still", "still", -2, "The movement stops. For a moment, the whole graveyard seems to hold its breath."),
                ("🏃 Run for the gate", "run", -5, "You make it to the gate before the ground settles again."),
            ],
        },
    ],
    "haunted_house": [
        {
            "text": "A child's toy rolls across the hallway and stops at your feet. Its music box begins playing by itself.",
            "choices": [
                ("🧸 Pick it up", "toy", -8, "The music stops the instant you touch it. Something whispers from upstairs."),
                ("🚪 Kick it aside", "kick", -3, "The toy rolls back into your path without making a sound."),
                ("🏃 Walk around it", "avoid", 1, "You refuse to interact with it. Probably wise."),
            ],
        },
        {
            "text": "Every portrait in the foyer is facing the wall. You hear several frames slowly turning behind you.",
            "choices": [
                ("🖼️ Look at the portraits", "portraits", -7, "The painted faces are all looking at you now."),
                ("🔦 Check the hallway", "hall", -2, "The hallway is empty, but one portrait is missing."),
                ("🚪 Leave the foyer", "leave", 0, "You leave before the portraits finish turning."),
            ],
        },
        {
            "text": "A staircase leads upward, but every step is covered in wet footprints that end at the ceiling.",
            "choices": [
                ("⬆️ Climb the stairs", "climb", -10, "The footprints begin appearing behind you as you climb."),
                ("🔎 Inspect the steps", "inspect", -4, "The footprints are upside down. You decide not to investigate further."),
                ("⬇️ Stay downstairs", "stay", 1, "You stay on solid ground. Something above you sighs in relief."),
            ],
        },
    ],
    "church": [
        {
            "text": "The altar candles ignite one by one, revealing a trail of ash leading toward the pulpit.",
            "choices": [
                ("🕯️ Follow the ash", "follow", -7, "The trail ends at an empty pulpit where a voice begins reciting your name."),
                ("🙏 Pray", "pray", 2, "The candles steady. For a brief moment, the church feels almost safe."),
                ("🚪 Leave the nave", "leave", 0, "You move away from the altar while the candles continue burning behind you."),
            ],
        },
        {
            "text": "A church bell rings from somewhere beneath the floorboards. Dust falls from the ceiling with every chime.",
            "choices": [
                ("🕳️ Search for the source", "search", -9, "You find a staircase that was not there before."),
                ("👂 Listen", "listen", -3, "The final chime sounds directly beneath your feet."),
                ("🏃 Get away from the floor", "away", 0, "You retreat toward the doorway as the bell finally goes silent."),
            ],
        },
        {
            "text": "A stained-glass window depicts five shadowy figures. One of them slowly turns its head toward you.",
            "choices": [
                ("👀 Keep watching", "watch", -8, "The figure smiles. The glass is still completely intact."),
                ("🙏 Look away", "lookaway", 1, "You turn away. When you look back, all five figures are facing forward again."),
                ("🪟 Touch the glass", "touch", -5, "The glass is warm, almost like skin."),
            ],
        },
    ],
    "witch_woods": [
        {
            "text": "A ring of mushrooms surrounds a tiny lantern glowing beneath the trees.",
            "choices": [
                ("🏮 Pick up the lantern", "lantern", -6, "The lantern lights itself and casts a shadow that does not belong to you."),
                ("🍄 Step through the ring", "mushrooms", -9, "The woods become completely silent until you step back out."),
                ("🌲 Walk around it", "avoid", 1, "You leave the strange little clearing untouched."),
            ],
        },
        {
            "text": "The trees begin whispering in unison. You cannot understand the words, but they are definitely speaking about you.",
            "choices": [
                ("👂 Listen closely", "listen", -8, "The whispers suddenly become clear: they are counting your heartbeats."),
                ("🗣️ Talk back", "answer", -10, "Every tree answers in your own voice."),
                ("🏃 Keep moving", "move", 0, "You walk faster. The whispering eventually fades behind you."),
            ],
        },
        {
            "text": "A crooked wooden sign points in three directions. All three arrows say: \"THIS WAY\".",
            "choices": [
                ("⬅️ Take the left path", "left", -3, "The path bends strangely, but you remain on solid ground."),
                ("⬆️ Take the middle path", "middle", -6, "The trees close behind you before opening into a moonlit clearing."),
                ("➡️ Take the right path", "right", 0, "You follow the right path and find a trail marker carved with an eye."),
            ],
        },
    ],
    "dilapidated_pizzeria": [
        {
            "text": "The dead stage lights flicker on one at a time. A mascot-shaped shadow is standing where the stage should be.",
            "choices": [
                ("🍕 Check the stage", "stage", -9, "The shadow is gone. The curtains are warm, as though something was standing behind them."),
                ("📹 Check the security monitors", "monitors", -4, "Every camera shows the same hallway. One camera shows you standing in it."),
                ("🚪 Leave the room", "leave", 1, "You back away. Behind you, something quietly taps on the glass."),
            ],
        },
        {
            "text": "A party room contains a single birthday cake. Its candles ignite by themselves, spelling out a number instead of a name.",
            "choices": [
                ("🎂 Blow them out", "blow", -7, "The flames vanish. For one second, you hear a child laugh from underneath the table."),
                ("🔢 Read the number", "read", -5, "The number matches the current date. You wish it didn't."),
                ("🏃 Don't touch it", "avoid", 0, "You leave it alone. One candle remains lit behind you."),
            ],
        },
        {
            "text": "The security office still has power. A monitor displays a grainy feed of the room you are currently standing in.",
            "choices": [
                ("📺 Watch the feed", "watch", -10, "The version of you on the monitor turns toward the camera before you do."),
                ("🔌 Pull the plug", "unplug", -2, "The screen goes black. Something in the hallway starts moving."),
                ("📷 Check another camera", "camera", -5, "The next camera shows an empty stage. The one after that shows you leaving the building."),
            ],
        },
    ],
    "abandoned_toy_workshop": [
        {
            "text": "A conveyor belt starts moving despite having no power. A row of unfinished toys slowly passes beneath the lights.",
            "choices": [
                ("🧸 Inspect a toy", "inspect", -8, "Its head turns toward you before you touch it."),
                ("🔌 Follow the conveyor", "follow", -5, "It leads into a room that should not fit inside the building."),
                ("🚪 Step away", "avoid", 0, "You step back. The conveyor keeps moving after you leave."),
            ],
        },
        {
            "text": "A wall of painted faces stares across the workshop. One of them has freshly painted eyes.",
            "choices": [
                ("👁️ Look closer", "look", -9, "The eyes blink once. The paint is still wet."),
                ("🎨 Cover the eyes", "cover", -3, "You smear paint across the face. Something laughs from inside the wall."),
                ("🏃 Keep walking", "walk", 1, "You refuse to look. The footsteps behind you stop when you stop."),
            ],
        },
        {
            "text": "A music box plays from an empty assembly table. Its melody stops whenever you breathe.",
            "choices": [
                ("🎵 Wind it", "wind", -6, "The melody resumes with a second instrument that wasn't there before."),
                ("📦 Open the box", "open", -11, "Inside is a tiny handwritten note containing your name."),
                ("🤫 Hold your breath", "breath", 0, "The music stops. Something whispers, 'Thank you.'"),
            ],
        },
    ],
    "broadcast_station": [
        {
            "text": "Every television in the control room shows the same empty hallway. Then one screen shows a door opening.",
            "choices": [
                ("📺 Watch the screen", "watch", -8, "The door on the screen opens into the room behind you."),
                ("📻 Tune the signal", "tune", -5, "A voice repeats your last thought back to you."),
                ("🔌 Kill the power", "power", 0, "The screens go dark. One remains lit, displaying the words: DON'T LOOK BACK."),
            ],
        },
        {
            "text": "A recording booth contains a microphone with a red light. The light turns on when you enter.",
            "choices": [
                ("🎙️ Speak into it", "speak", -10, "Your voice answers from somewhere deep inside the building."),
                ("👂 Listen", "listen", -6, "You hear yourself whispering a sentence you haven't said yet."),
                ("🚪 Leave the booth", "leave", 1, "The red light follows you through the glass for three seconds."),
            ],
        },
        {
            "text": "An old broadcast schedule lists a program called 'YOU ARE HERE.' Its airtime is five minutes from now.",
            "choices": [
                ("⏰ Wait for it", "wait", -12, "The broadcast begins. It shows you standing in the station."),
                ("📄 Tear up the schedule", "tear", -4, "The paper tears, but the schedule remains printed on your hands."),
                ("🏃 Leave before it starts", "leave", 0, "You leave. Somewhere behind you, an announcer says your name."),
            ],
        },
    ],
    "endless_hotel": [
        {
            "text": "The hallway is identical in both directions. Room 314 is on your left. You are certain it was on your right a moment ago.",
            "choices": [
                ("🚪 Enter 314", "enter", -10, "The room is empty except for a chair facing the wall. It is still rocking."),
                ("🗝️ Try the next room", "next", -4, "The number changes from 315 to 314 when you blink."),
                ("↩️ Turn around", "back", 0, "You walk back. The carpet pattern is different now."),
            ],
        },
        {
            "text": "A hotel bell rings from the lobby. You can see the elevator, but the lobby is nowhere behind it.",
            "choices": [
                ("🔔 Follow the bell", "follow", -9, "The bell rings again from directly behind you."),
                ("🛗 Take the elevator", "elevator", -6, "The elevator opens to the same floor you left."),
                ("🧭 Mark the wall", "mark", 1, "You carve a mark into the wall. Ten steps later, you find the same mark."),
            ],
        },
        {
            "text": "A room-service cart sits in the hallway. The silver lid is trembling.",
            "choices": [
                ("🍽️ Lift the lid", "lift", -11, "There is nothing underneath. Something knocks from inside the cart."),
                ("🛒 Push it away", "push", -3, "The cart rolls itself back to where it started."),
                ("🚪 Ignore it", "ignore", 0, "You walk past. The cart's wheels slowly turn to follow you."),
            ],
        },
    ],
    "fogbound_town": [
        {
            "text": "A streetlight flickers through the fog. Beneath it stands a person facing away from you.",
            "choices": [
                ("👋 Call out", "call", -10, "The figure turns. It has your clothes, but no face."),
                ("🌫️ Walk around", "around", -4, "You pass it. Its shadow moves in the opposite direction."),
                ("🏃 Run", "run", 0, "You run until the fog clears for a moment. The figure is gone."),
            ],
        },
        {
            "text": "A radio in an abandoned car crackles to life. It only says one sentence: 'You shouldn't be here.'",
            "choices": [
                ("📻 Answer the radio", "answer", -8, "The radio answers with your own voice."),
                ("🔧 Check the car", "check", -5, "The driver's seat is warm despite the car being abandoned."),
                ("🚶 Keep walking", "walk", 1, "The radio follows you through the fog even after the car disappears."),
            ],
        },
        {
            "text": "A row of houses sits silent. Every front door is open except one.",
            "choices": [
                ("🚪 Enter the closed house", "enter", -12, "The door opens into a hallway that looks exactly like your home."),
                ("🏠 Check an open house", "open", -6, "Inside, every clock is stopped at the same time."),
                ("🌫️ Stay in the street", "street", 0, "Something moves between the houses, but you never see it clearly."),
            ],
        },
    ],
    "derelict_research_facility": [
        {
            "text": "A containment chamber is cracked open. The warning lights insist that the room is occupied.",
            "choices": [
                ("🔬 Inspect the chamber", "inspect", -11, "The chamber is empty. Your reflection inside it is not."),
                ("🔒 Seal it", "seal", -4, "The door closes. Something knocks from the other side."),
                ("🚪 Keep moving", "move", 0, "You leave. The warning lights follow you down the corridor."),
            ],
        },
        {
            "text": "A lab terminal displays a list of test subjects. The final entry is today's date.",
            "choices": [
                ("💻 Open the record", "open", -10, "The record contains a detailed description of what you're doing right now."),
                ("🗑️ Delete it", "delete", -5, "The screen says DELETE FAILED. The cursor begins typing by itself."),
                ("🔌 Disconnect it", "disconnect", 1, "The terminal shuts down. Somewhere nearby, a machine starts breathing."),
            ],
        },
        {
            "text": "A sealed specimen container is labeled 'DO NOT EXPOSE TO LIGHT.' The emergency lights suddenly brighten.",
            "choices": [
                ("🔦 Cover the container", "cover", -7, "Something inside presses against the glass."),
                ("👁️ Look at it", "look", -14, "You cannot describe what you saw without remembering a different room."),
                ("🚪 Leave immediately", "leave", 0, "You leave the room. Behind you, the seal clicks open."),
            ],
        },
    ],

}

# ---------------------------------------------------------------------------

# Rare Haunted discoveries: permanent, replayable, and intentionally creepy.
HAUNTED_DISCOVERY_CHANCE = 0.06
HAUNTED_DISCOVERY_LOW_SANITY_CHANCE = 0.10
HAUNTED_DISCOVERY_INSANE_CHANCE = 0.14

def _make_discovery(discovery_id, title, text, choices):
    return {"discovery_id": discovery_id, "discovery_title": title, "text": text, "choices": [q for q in choices]}

RARE_DISCOVERIES = {
    'asylum': [
        _make_discovery('patient_in_room_13', 'Patient in Room 13', 'The call button in Room 13 rings. The room is empty. You walk away. It rings again—from the room you are standing in.', [
            _choice_outcomes('🔔 Answer the call', 'answer', 'high', 'The speaker whispers, “You took your time.”'),
            _choice_outcomes('🚪 Open Room 13', 'open', 'medium', 'The bed is empty. The pillow is still warm.'),
            _choice_outcomes('🏃 Keep walking', 'leave', 'low', 'The ringing follows you, one room closer each time.'),
        ]),
        _make_discovery('observation_window', 'Observation Window', 'Behind an observation window, a figure stands inside a padded room. It slowly points behind you. When you turn back, the room is empty.', [
            _choice_outcomes('👀 Look behind you', 'turn', 'high', 'Nothing is there. The figure is now reflected in the glass.'),
            _choice_outcomes('🪟 Watch the room', 'watch', 'medium', 'The figure returns only after you stop looking directly at it.'),
            _choice_outcomes('🚪 Leave', 'leave', 'low', 'You leave. Something taps on the glass from the other side.'),
        ]),
        _make_discovery('patient_list', 'Patient List', 'An old patient list contains your name. The admission date is tomorrow. The discharge date is blank.', [
            _choice_outcomes('📄 Read the file', 'read', 'high', 'The notes describe things you have done today—things that have not happened yet.'),
            _choice_outcomes('✏️ Cross your name out', 'cross', 'medium', 'The ink vanishes. Your name appears at the bottom of the page instead.'),
            _choice_outcomes('🏃 Put it down', 'leave', 'low', 'You drop the file. When you glance back, it is open to your name.'),
        ]),
    ],
    'graveyard': [
        _make_discovery('your_own_grave', 'Your Own Grave', 'A fresh grave bears your name. The death date is empty. The soil beside it is still damp.', [
            _choice_outcomes('🪦 Inspect the grave', 'inspect', 'high', 'Something beneath the soil knocks once.'),
            _choice_outcomes('🖐️ Touch the headstone', 'touch', 'medium', 'The stone is warm, like it has been waiting in sunlight.'),
            _choice_outcomes('🏃 Walk away', 'leave', 'low', 'You leave. Behind you, dirt shifts into the shape of a second footprint.'),
        ]),
        _make_discovery('grave_that_breathes', 'Grave That Breathes', 'You hear slow breathing beneath a sealed grave. It stops when you hold your breath.', [
            _choice_outcomes('👂 Listen closely', 'listen', 'high', 'The breathing resumes from directly beneath your feet.'),
            _choice_outcomes('🪦 Dig at the soil', 'dig', 'extreme', 'Your hands hit something that knocks back.'),
            _choice_outcomes('🤫 Hold your breath', 'hold', 'medium', 'The grave goes silent. Then something whispers your name.'),
        ]),
        _make_discovery('extra_grave', 'Extra Grave', 'You count the graves. There is one more than there was a moment ago. Its headstone is blank.', [
            _choice_outcomes('🔢 Count again', 'count', 'medium', 'There are two more now.'),
            _choice_outcomes('🪦 Approach it', 'approach', 'high', 'Scraping comes from behind you before you reach the stone.'),
            _choice_outcomes('🏃 Leave the cemetery', 'leave', 'low', 'You leave. The gate now stands much farther away.'),
        ]),
    ],
    'haunted_house': [
        _make_discovery('family_portrait', 'Family Portrait', 'A family portrait hangs crookedly. There is an extra person in it. Each time you look away, they move closer to the edge of the frame.', [
            _choice_outcomes('🖼️ Study the portrait', 'study', 'high', 'The extra person is no longer in the frame. They are standing behind the camera.'),
            _choice_outcomes('👁️ Look away', 'away', 'medium', 'You look back. The person is closer. They are smiling.'),
            _choice_outcomes('🏃 Leave the room', 'leave', 'low', 'The portrait follows you with its eyes.'),
        ]),
        _make_discovery('upstairs_footsteps', 'Upstairs Footsteps', 'Footsteps cross the ceiling above you. The house has no second floor.', [
            _choice_outcomes('👣 Follow the sound', 'follow', 'high', 'The footsteps stop directly above you. Then one step lands beside you.'),
            _choice_outcomes('🔦 Check the ceiling', 'check', 'medium', 'There is nothing above the ceiling except darkness.'),
            _choice_outcomes('🚪 Leave', 'leave', 'low', 'The footsteps follow you to the front door.'),
        ]),
        _make_discovery('bedroom_copy', 'Bedroom Copy', 'You open a door and find a perfect copy of your bedroom. A photograph on the desk shows you sleeping.', [
            _choice_outcomes('📷 Pick up the photo', 'photo', 'high', 'The photograph changes. You are now awake and looking at the camera.'),
            _choice_outcomes('🛏️ Check the bed', 'bed', 'medium', 'The blanket rises and falls as though someone is breathing underneath it.'),
            _choice_outcomes('🚪 Close the door', 'close', 'low', 'You shut it. Something knocks from your side of the door.'),
        ]),
    ],
    'church': [
        _make_discovery('confessional', 'Confessional', 'The confessional curtain moves on its own. A voice from inside says, “You already told me.”', [
            _choice_outcomes('⛪ Enter the booth', 'enter', 'high', 'The seat opposite you is warm.'),
            _choice_outcomes('🗣️ Ask what you told it', 'ask', 'medium', 'The voice recites a secret you have never spoken aloud.'),
            _choice_outcomes('🚪 Walk away', 'leave', 'low', 'The curtain opens behind you.'),
        ]),
        _make_discovery('bell', 'The Bell', 'The church bell rings despite its rope being cut. Then it rings again while you are standing beside it.', [
            _choice_outcomes('🔔 Touch the bell', 'touch', 'high', 'The metal is warm and something inside the bell whispers.'),
            _choice_outcomes('👀 Look up', 'look', 'medium', 'There is no bell in the tower. The sound continues.'),
            _choice_outcomes('🏃 Run outside', 'run', 'low', 'The bell stops the instant you cross the threshold.'),
        ]),
        _make_discovery('prayer', 'The Prayer', 'Every name in an old prayer book has been crossed out except yours. Beneath it: “Forgive them.”', [
            _choice_outcomes('📖 Read further', 'read', 'high', 'The next page is dated tomorrow.'),
            _choice_outcomes('✝️ Close the book', 'close', 'medium', 'A page turns itself behind your hand.'),
            _choice_outcomes('🔥 Burn it', 'burn', 'extreme', 'The page burns cold. The smoke spells your name.'),
        ]),
    ],
    'witch_woods': [
        _make_discovery('candle_circle', 'The Circle', 'Twelve candles surround a clearing. One has your name scratched into the wax.', [
            _choice_outcomes('🕯️ Extinguish it', 'extinguish', 'medium', 'The other eleven flames lean toward you.'),
            _choice_outcomes('🌲 Step inside', 'enter', 'high', 'The woods go silent. Something steps into the circle with you.'),
            _choice_outcomes('🏃 Leave it alone', 'leave', 'low', 'You back away. One candle follows you with its flame.'),
        ]),
        _make_discovery('giant_footprints', 'Giant Footprints', 'Enormous footprints appear behind you in the mud. They stop whenever you stop.', [
            _choice_outcomes('👣 Follow them', 'follow', 'high', 'The prints suddenly appear in front of you too.'),
            _choice_outcomes('🛑 Stop moving', 'stop', 'medium', 'The forest becomes silent. Something exhales behind you.'),
            _choice_outcomes('🏃 Run', 'run', 'high', 'The footprints keep pace without getting closer.'),
        ]),
        _make_discovery('black_water_cottage', 'Black Water Cottage', 'A crooked cottage sits beside a pool of black water. Something watches from the window. Your reflection shows the cottage from outside—with you standing inside it.', [
            _choice_outcomes('🪟 Look in the window', 'look', 'high', 'The thing inside raises a hand exactly when you do.'),
            _choice_outcomes('🌊 Look into the water', 'water', 'medium', 'The reflection blinks before you do.'),
            _choice_outcomes('🏃 Leave', 'leave', 'low', 'The cottage light turns on as you walk away.'),
        ]),
    ],
    'dilapidated_pizzeria': [
        _make_discovery('birthday_room', 'Birthday Room', 'A party room is decorated for a birthday. The cake has your name written on it. Every candle is already lit.', [
            _choice_outcomes('🎂 Blow out the candles', 'blow', 'high', 'The room goes dark. A child whispers, “Again.”'),
            _choice_outcomes('🔪 Cut the cake', 'cut', 'medium', 'The inside is completely empty except for a warm birthday card.'),
            _choice_outcomes('🚪 Leave', 'leave', 'low', 'The candles stay lit after the door closes.'),
        ]),
        _make_discovery('stage_head', 'The Stage', 'An animatronic head slowly turns toward you. A child’s voice whispers from directly behind you.', [
            _choice_outcomes('👀 Turn around', 'turn', 'high', 'There is nobody there. The head is now facing the door.'),
            _choice_outcomes('🤖 Approach the stage', 'approach', 'medium', 'The animatronic opens its mouth and says your name.'),
            _choice_outcomes('🏃 Run', 'run', 'low', 'The voice laughs softly as you leave.'),
        ]),
        _make_discovery('security_tape', 'Security Tape', 'A security recording shows “you” walking through the restaurant at 3:17 AM and staring directly into the camera.', [
            _choice_outcomes('📼 Watch the whole tape', 'watch', 'high', 'The recording continues past the time it should end.'),
            _choice_outcomes('⏩ Skip ahead', 'skip', 'medium', 'You see yourself standing behind the security desk.'),
            _choice_outcomes('📺 Turn it off', 'off', 'low', 'The screen goes black. Your reflection remains on it.'),
        ]),
    ],
    'abandoned_toy_workshop': [
        _make_discovery('prototype', 'The Prototype', 'A toy on a workbench is labeled: DO NOT ACTIVATE. Its eyes open when you read the label.', [
            _choice_outcomes('🔘 Press the button', 'press', 'extreme', 'The toy says your name in your own voice.'),
            _choice_outcomes('🧸 Inspect it', 'inspect', 'high', 'Its serial number is your birth date.'),
            _choice_outcomes('🚪 Walk away', 'leave', 'low', 'You hear tiny footsteps following you.'),
        ]),
        _make_discovery('assembly_line', 'Assembly Line', 'Every toy on the conveyor resembles you. The newest one is still warm.', [
            _choice_outcomes('🧸 Pick it up', 'pick', 'high', 'Its head turns toward the door before you do.'),
            _choice_outcomes('🔌 Stop the line', 'stop', 'medium', 'The conveyor stops. The toys keep moving their eyes.'),
            _choice_outcomes('🏃 Leave', 'leave', 'low', 'A new toy appears on the belt behind you.'),
        ]),
        _make_discovery('music_box', 'Music Box', 'A music box plays a melody of someone humming. The humming sounds exactly like your voice.', [
            _choice_outcomes('🎵 Wind it', 'wind', 'medium', 'The humming continues after the box stops.'),
            _choice_outcomes('📦 Open it', 'open', 'high', 'Inside is a tiny recording of you breathing.'),
            _choice_outcomes('🤫 Stay silent', 'silent', 'low', 'The melody changes to match your breathing.'),
        ]),
    ],
    'broadcast_station': [
        _make_discovery('impossible_camera', 'Broadcast', 'A dead television shows this room from an impossible camera angle. Something is standing behind you on the screen.', [
            _choice_outcomes('📺 Turn around', 'turn', 'high', 'The screen shows you turning around before you do.'),
            _choice_outcomes('👁️ Keep watching', 'watch', 'high', 'The figure on the screen gets closer.'),
            _choice_outcomes('🔌 Unplug it', 'unplug', 'medium', 'The television goes black. The reflection remains.'),
        ]),
        _make_discovery('channel_zero', 'Channel 0', 'A nonexistent channel displays your current hallway. The camera reaches your location. The screen goes black.', [
            _choice_outcomes('📡 Keep tuning', 'tune', 'high', 'A voice says, “You are watching the wrong side.”'),
            _choice_outcomes('📺 Wait', 'wait', 'medium', 'The screen shows an empty hallway. You are standing in it.'),
            _choice_outcomes('🔌 Turn it off', 'off', 'low', 'The television turns itself back on.'),
        ]),
        _make_discovery('emergency_broadcast', 'Emergency Broadcast', 'An emergency message says: “The person currently listening is not the person who entered.”', [
            _choice_outcomes('🎙️ Answer the broadcast', 'answer', 'high', 'The announcer repeats your name.'),
            _choice_outcomes('📻 Record it', 'record', 'medium', 'The recording contains your voice saying the message.'),
            _choice_outcomes('🏃 Leave', 'leave', 'low', 'The message continues after you leave the room.'),
        ]),
    ],
    'endless_hotel': [
        _make_discovery('room_314_future', 'Room 314', 'A key opens Room 314. The guest registry says you check in three minutes from now.', [
            _choice_outcomes('🗝️ Enter', 'enter', 'high', 'The room contains a suitcase with your name on it.'),
            _choice_outcomes('📖 Read the registry', 'read', 'medium', 'The next entry says you never checked out.'),
            _choice_outcomes('🚪 Close the door', 'close', 'low', 'The door locks from the inside.'),
        ]),
        _make_discovery('guestbook', 'Guestbook', 'The final guestbook entry reads: “If you’re reading this, you’re already one of us.” The ink is still wet.', [
            _choice_outcomes('📖 Touch the ink', 'touch', 'high', 'Your fingertip comes away with someone else’s handwriting on it.'),
            _choice_outcomes('✍️ Write your name', 'write', 'extreme', 'The book writes it for you.'),
            _choice_outcomes('🚪 Close the book', 'close', 'low', 'A new page turns itself.'),
        ]),
        _make_discovery('elevator_face', 'The Elevator', 'An elevator opens. Inside stands a person with your face. They turn their head as the doors close.', [
            _choice_outcomes('🛗 Enter', 'enter', 'extreme', 'The person smiles without moving their mouth.'),
            _choice_outcomes('👁️ Watch the doors', 'watch', 'high', 'The elevator mirror shows you standing inside.'),
            _choice_outcomes('🏃 Walk away', 'leave', 'low', 'The elevator bell rings behind you.'),
        ]),
    ],
    'fogbound_town': [
        _make_discovery('figure_in_fog', 'Figure in the Fog', 'A figure beneath a streetlight appears closer every time the fog shifts. It never seems to walk.', [
            _choice_outcomes('👋 Call to it', 'call', 'high', 'It answers in your voice.'),
            _choice_outcomes('🌫️ Approach', 'approach', 'high', 'The figure is suddenly standing behind you.'),
            _choice_outcomes('🏃 Walk away', 'leave', 'low', 'The streetlight goes dark one block at a time.'),
        ]),
        _make_discovery('diner_invitation', 'The Diner', 'A diner is freshly lit despite the town being abandoned. Food is still warm. Chairs pull themselves out for you.', [
            _choice_outcomes('🍽️ Sit down', 'sit', 'high', 'The chair slides back before you can touch it.'),
            _choice_outcomes('☕ Inspect the food', 'inspect', 'medium', 'The plate is empty except for a handwritten receipt with your name.'),
            _choice_outcomes('🚪 Leave', 'leave', 'low', 'The diner lights stay on behind you.'),
        ]),
        _make_discovery('future_tv', 'The House', 'A television shows your current Haunted run a few seconds ahead. The future version of you stops and looks directly at the screen.', [
            _choice_outcomes('📺 Keep watching', 'watch', 'high', 'Future-you mouths a word you cannot hear.'),
            _choice_outcomes('🔌 Turn it off', 'off', 'medium', 'The screen goes black. The reflection keeps moving.'),
            _choice_outcomes('🏃 Leave', 'leave', 'low', 'The television shows you leaving before you do.'),
        ]),
    ],
    'derelict_research_facility': [
        _make_discovery('experiment_17', 'Experiment 17', 'A research log describes Experiment 17. The final entry reads: “It has learned the door.”', [
            _choice_outcomes('📄 Read the whole log', 'read', 'high', 'The final page is dated today and describes you reading it.'),
            _choice_outcomes('🔒 Check the door', 'check', 'medium', 'The door handle is warm.'),
            _choice_outcomes('🏃 Leave', 'leave', 'low', 'The door clicks behind you.'),
        ]),
        _make_discovery('containment_chamber', 'The Containment Chamber', 'A containment chamber stands empty. Its walls are covered in fingerprints from the inside.', [
            _choice_outcomes('🔬 Enter the chamber', 'enter', 'extreme', 'The door shuts. A second set of footsteps begins inside.'),
            _choice_outcomes('🖐️ Examine the prints', 'prints', 'high', 'Some fingerprints are fresh.'),
            _choice_outcomes('🚪 Keep moving', 'leave', 'low', 'The chamber lights turn off as you pass.'),
        ]),
        _make_discovery('redacted_file', 'The Redacted File', 'Every page of a file is completely redacted except one sentence: “DO NOT LET IT KNOW YOU CAN SEE IT.”', [
            _choice_outcomes('📄 Read the sentence again', 'read', 'high', 'A second sentence appears: “Too late.”'),
            _choice_outcomes('✏️ Write a note', 'write', 'medium', 'The pen writes by itself: “It knows.”'),
            _choice_outcomes('🗃️ Put it back', 'leave', 'low', 'The file is already back in the cabinet when you turn around.'),
        ]),
        _make_discovery('malo_incident', 'MalO Incident', 'A terminal still has MalO ver1.0.0 installed. The photos show an empty hallway, then a figure, then the figure closer. A new photograph appears. It was taken just now.', [
            _choice_outcomes('📱 Open the newest photo', 'open', 'extreme', 'The image shows you from somewhere you cannot see.'),
            _choice_outcomes('📸 Check the older photos', 'photos', 'high', 'The figure is closer in every image.'),
            _choice_outcomes('🔌 Shut down the terminal', 'off', 'medium', 'The monitor dies. Your phone camera opens by itself.'),
        ]),
    ],
    'yellow_halls': [
        _make_discovery('unmarked_door', 'Unmarked Door', 'A door appears with no handle, hinges, or frame. When you knock, your own voice says, “Let me out.”', [
            _choice_outcomes('🚪 Knock again', 'knock', 'high', 'The voice answers from behind you.'),
            _choice_outcomes('👂 Listen', 'listen', 'medium', 'Something knocks back three times.'),
            _choice_outcomes('🏃 Leave', 'leave', 'low', 'The door is gone when you look back.'),
        ]),
        _make_discovery('wrong_hallway', 'Wrong Hallway', 'You loop back to a hallway you already crossed. Your previous self is standing there. It turns its head.', [
            _choice_outcomes('👋 Call out', 'call', 'high', 'Your other self smiles and keeps walking.'),
            _choice_outcomes('🏃 Run past', 'run', 'high', 'You pass yourself. You hear your own footsteps behind you.'),
            _choice_outcomes('↩️ Turn back', 'back', 'medium', 'The hallway behind you is no longer there.'),
        ]),
        _make_discovery('familiar_room', 'Familiar Room', 'You find a bedroom that looks almost exactly like yours. The clock runs backward. Your belongings are on the shelves. Something breathes beneath the blanket.', [
            _choice_outcomes('🛏️ Lift the blanket', 'lift', 'extreme', 'The bed is empty. The breathing continues.'),
            _choice_outcomes('⏰ Watch the clock', 'clock', 'high', 'The hands reverse until they point at you.'),
            _choice_outcomes('🚪 Leave', 'leave', 'low', 'The room door opens into another copy of the room.'),
        ]),
    ],
    'dead_end_highway': [
        _make_discovery('last_payphone', 'Last Payphone', 'A dead payphone rings. When you answer, the voice says, “You’re going the wrong way.” Then: “I’m you.”', [
            _choice_outcomes('☎️ Ask where to go', 'ask', 'high', 'The voice gives directions to the place you are standing.'),
            _choice_outcomes('📞 Hang up', 'hang', 'medium', 'The phone rings again immediately.'),
            _choice_outcomes('🏃 Leave', 'leave', 'low', 'The receiver swings gently after you walk away.'),
        ]),
        _make_discovery('passenger', 'The Passenger', 'An abandoned car has a locked passenger door. Something taps from inside. When you walk away, invisible footsteps follow.', [
            _choice_outcomes('🚗 Open the door', 'open', 'extreme', 'The passenger seat is empty. Something exhales beside you.'),
            _choice_outcomes('👂 Listen', 'listen', 'high', 'The tapping matches your heartbeat.'),
            _choice_outcomes('🏃 Run', 'run', 'medium', 'The footsteps run too.'),
        ]),
        _make_discovery('mile_zero', 'Mile 0', 'You pass a Mile 0 sign. Then another. Each time you look, your destination is farther away.', [
            _choice_outcomes('🪧 Inspect the sign', 'inspect', 'high', 'The distance number changes while you watch it.'),
            _choice_outcomes('🛣️ Keep driving', 'drive', 'medium', 'The road behind you disappears.'),
            _choice_outcomes('🔄 Turn around', 'turn', 'high', 'The sign now says Mile 0 in both directions.'),
        ]),
    ],
    'drowned_station': [
        _make_discovery('last_train', 'Last Train', 'An underwater train sits without tracks. Every passenger slowly turns toward you.', [
            _choice_outcomes('🚇 Board the train', 'board', 'extreme', 'The doors close before your feet touch the floor.'),
            _choice_outcomes('👁️ Look through the windows', 'look', 'high', 'The passengers are all staring at you.'),
            _choice_outcomes('🏃 Back away', 'leave', 'medium', 'The train horn sounds beneath the water.'),
        ]),
        _make_discovery('station_announcement', 'Announcement', 'An underwater speaker crackles: “Please remain on the platform. It has already seen you.”', [
            _choice_outcomes('📢 Answer the announcement', 'answer', 'high', 'The speaker repeats your name.'),
            _choice_outcomes('👂 Listen', 'listen', 'medium', 'Another voice whispers from the water.'),
            _choice_outcomes('🏃 Leave the platform', 'leave', 'low', 'The announcement follows you into the tunnel.'),
        ]),
        _make_discovery('drowned_platform', 'Drowned Platform', 'Hundreds of wet footprints cover the underwater platform. Every set leads out of the water. None lead back in.', [
            _choice_outcomes('👣 Follow them', 'follow', 'high', 'The footprints stop at your feet.'),
            _choice_outcomes('🌊 Look into the water', 'water', 'extreme', 'Something beneath you looks up.'),
            _choice_outcomes('🚪 Leave', 'leave', 'low', 'Wet footprints appear behind you as you walk.'),
        ]),
    ],
    'silent_campground': [
        _make_discovery('moving_photograph', 'Photograph', 'A photograph of the campground contains a tall figure between the trees. Each time you look again, it is closer.', [
            _choice_outcomes('📸 Look again', 'look', 'high', 'The figure is now standing beside the tent.'),
            _choice_outcomes('🖼️ Turn the photo over', 'turn', 'medium', 'A message is written on the back: “DON’T LOOK UP.”'),
            _choice_outcomes('🏃 Put it down', 'leave', 'low', 'The photograph is gone when you look back.'),
        ]),
        _make_discovery('ranger_notebook', 'Ranger’s Notebook', 'A ranger’s notebook contains entries about a figure getting closer. The last line says: “Don’t look toward the trees.” Branches move behind you.', [
            _choice_outcomes('📓 Read the last page', 'read', 'high', 'Fresh ink appears: “Too late.”'),
            _choice_outcomes('🌲 Look at the trees', 'look', 'extreme', 'The forest is empty. Something is standing much closer than the trees.'),
            _choice_outcomes('🏃 Keep your eyes forward', 'forward', 'medium', 'Something walks beside you without making a sound.'),
        ]),
        _make_discovery('camera', 'The Camera', 'A camera contains photos of things that were not there when you took them. The final photo shows you from directly behind. The camera is lying on the ground in front of you.', [
            _choice_outcomes('📷 Take the camera', 'take', 'high', 'The shutter clicks by itself.'),
            _choice_outcomes('👁️ Look at the final photo', 'photo', 'extreme', 'The figure in the photo is closer than the one behind you.'),
            _choice_outcomes('🏃 Leave it', 'leave', 'medium', 'A camera shutter clicks somewhere behind you.'),
        ]),
    ],
}


HAUNTED_IMPOSSIBLE_DISCOVERIES = {
    "observation_window", "your_own_grave", "family_portrait", "bedroom_copy", "confessional",
    "black_water_cottage", "security_tape", "prototype", "impossible_camera", "channel_zero",
    "future_tv", "containment_chamber", "redacted_file", "malo_incident", "wrong_hallway",
    "familiar_room", "passenger", "last_train", "drowned_platform", "moving_photograph", "camera",
}



def choose_encounter(location_id, sanity, force_universal=False, force_location=False, discovery_bonus=0.0):
    """Pick a replayable encounter, with increasingly unstable reality at low Sanity."""
    base_location = LOCATION_ENCOUNTERS.get(location_id, [])
    extra_location = EXTRA_LOCATION_ENCOUNTERS.get(location_id, [])
    location_encounters = base_location + extra_location
    sanity = max(0, min(SANITY_MAX, int(sanity)))

    # Rare discoveries are location-specific and deliberately uncommon. Crafted
    # forced encounters take priority so their guarantees remain meaningful.
    if not force_universal and not force_location:
        if sanity <= 0:
            discovery_chance = HAUNTED_DISCOVERY_INSANE_CHANCE
        elif sanity <= 40:
            discovery_chance = HAUNTED_DISCOVERY_LOW_SANITY_CHANCE
        else:
            discovery_chance = HAUNTED_DISCOVERY_CHANCE
        discovery_pool = RARE_DISCOVERIES.get(location_id, [])
        discovery_chance = min(1.0, discovery_chance + max(0.0, float(discovery_bonus)))
        if discovery_pool and random.random() < discovery_chance:
            return random.choice(discovery_pool)

    # At 0 Sanity, hallucinations become the dominant experience.  They are not
    # guaranteed every stage, but the player should absolutely feel the break.
    if sanity <= 0 and not force_universal and not force_location:
        if random.random() < 0.70:
            pool = INSANE_ENCOUNTERS
        else:
            pool = location_encounters or UNIVERSAL_ENCOUNTERS
    elif sanity <= 25 and not force_universal and not force_location and random.random() < 0.38:
        pool = LOW_SANITY_HALLUCINATIONS
    else:
        if sanity <= 20:
            universal_chance = 0.45
        elif sanity <= 40:
            universal_chance = 0.35
        elif sanity <= 60:
            universal_chance = 0.25
        else:
            universal_chance = 0.15
        if force_location and location_encounters:
            pool = location_encounters
        elif force_universal or not location_encounters or random.random() < universal_chance:
            pool = UNIVERSAL_ENCOUNTERS
        else:
            pool = location_encounters

    if len(pool) == 1:
        encounter = pool[0]
    else:
        instability = (SANITY_MAX - sanity) / SANITY_MAX
        weights = []
        for encounter in pool:
            choices = encounter.get("choices", [])
            if choices:
                impacts = []
                for choice in choices:
                    if isinstance(choice, dict):
                        impacts.extend(abs(int(o.get("sanity", 0))) for o in choice.get("outcomes", []))
                    else:
                        impacts.append(abs(int(choice[2])))
                max_impact = max(impacts or [0])
            else:
                max_impact = 0
            weights.append(1.0 + instability * max_impact)
        encounter = random.choices(pool, weights=weights, k=1)[0]

    # Convert the legacy tuple choices only when the encounter is actually used.
    # This keeps the existing tables readable while making every old choice
    # replayable too.
    normalized = []
    for choice in encounter.get("choices", []):
        normalized.append(choice if isinstance(choice, dict) else _legacy_to_random_choice(choice))
    if normalized != encounter.get("choices"):
        return {**encounter, "choices": normalized}
    return encounter
