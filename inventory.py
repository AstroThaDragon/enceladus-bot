import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import asyncio
import time
import json
from datetime import datetime, timedelta
import pytz
import random
from emojis import EMOJIS
from seasonal_updates.halloween import halloween as halloween_season
from seasonal_updates.halloween.halloween import halloween_channel_message, is_halloween_channel


# ---------------------------------------------------------------------------
# Halloween one-time collectible effects
# ---------------------------------------------------------------------------
# Edit this section to change the item name, response text, achievement ID,
# title reward, or enable future collectible effects.
#
# ``enabled`` controls whether the item can currently be used with /use.
# Keep future ideas disabled until their effect is implemented below.
HAUNTED_CRAFTED_USE_ITEMS = {
    "ghost_radio": {"name": "Ghost Radio", "emoji": "📻", "effect": "haunted_ghost_radio", "message": "📻 **Ghost Radio activated!** Your next Haunted run will tune into a transmission that overrides the normal encounter roll."},
    "mascot_tracker": {"name": "Mascot Tracker", "emoji": "📡", "effect": "haunted_mascot_tracker", "message": "📡 **Mascot Tracker activated!** Your next Haunted run has an improved chance of uncovering a Halloween collectible."},
    "room_314_key": {"name": "Room 314 Key", "emoji": "🗝️", "effect": "haunted_room_314_key", "message": "🗝️ **Room 314 Key ready!** Your next Endless Hotel run can unlock a shortcut through the impossible hotel."},
    "fog_lantern": {"name": "Fog Lantern", "emoji": "🏮", "effect": "haunted_fog_lantern", "message": "🏮 **Fog Lantern lit!** Your next Fogbound Town run will blunt supernatural Sanity loss."},
    "spectral_receiver": {"name": "Spectral Receiver", "emoji": "📡", "effect": "haunted_spectral_receiver", "message": "📡 **Spectral Receiver tuned!** Your next Haunted run has an improved collectible discovery chance."},
    "security_monitor": {"name": "Security Monitor", "emoji": "📺", "effect": "haunted_security_monitor", "message": "📺 **Security Monitor online!** Your next Haunted run gets one burst of protection from a Sanity hit."},
    "warding_sigil": {"name": "Warding Sigil", "emoji": "🕯️", "effect": "haunted_warding_sigil", "message": "🕯️ **Warding Sigil prepared!** It will completely block the first negative Sanity choice of your next Haunted run."},
    "mirror_ward": {"name": "Mirror Ward", "emoji": "🪞", "effect": "haunted_mirror_ward", "message": "🪞 **Mirror Ward prepared!** It will halve the first negative Sanity choice of your next Haunted run."},
    "dead_air_charm": {"name": "Dead-Air Charm", "emoji": "📡", "effect": "haunted_dead_air_charm", "message": "📡 **Dead-Air Charm prepared!** Your next Broadcast Station run will suppress part of its supernatural Sanity drain."},
    "empty_room_token": {"name": "Empty Room Token", "emoji": "🪙", "effect": "haunted_empty_room_token", "message": "🪙 **Empty Room Token prepared!** Your next Endless Hotel run will ignore its first negative Sanity choice."},
    "watchers_eye": {"name": "Watcher’s Eye", "emoji": "👁️", "effect": "haunted_watchers_eye", "message": "👁️ **Watcher’s Eye awakened!** Your next Haunted run will reveal a location-specific encounter instead of a random universal one at its first stage."},
    "containment_mark": {"name": "Containment Mark", "emoji": "⛓️", "effect": "haunted_containment_mark", "message": "⛓️ **Containment Mark prepared!** Your next Research Facility run will heavily reduce supernatural Sanity loss."},
    "yellow_halls_beacon": {"name": "Yellow Halls Beacon", "emoji": "💡", "effect": "haunted_yellow_halls_beacon", "message": "💡 **Yellow Halls Beacon prepared!** Your next Yellow Halls run will blunt supernatural Sanity loss."},
    "yellow_halls_unmarked_key": {"name": "Unmarked Door Key", "emoji": "🗝️", "effect": "haunted_yellow_halls_unmarked_key", "message": "🗝️ **Unmarked Door Key prepared!** Your next Yellow Halls run will ignore its first negative Sanity choice."},
    "highway_payphone_kit": {"name": "Payphone Repair Kit", "emoji": "☎️", "effect": "haunted_highway_payphone_kit", "message": "☎️ **Payphone Repair Kit prepared!** Your next Dead-End Highway run will force a strange roadside signal encounter."},
    "highway_motel_ward": {"name": "Motel Room Ward", "emoji": "🚪", "effect": "haunted_highway_motel_ward", "message": "🚪 **Motel Room Ward prepared!** Your next Dead-End Highway run will ignore its first negative Sanity choice."},
    "drowned_flood_lamp": {"name": "Flood Lamp", "emoji": "🔦", "effect": "haunted_drowned_flood_lamp", "message": "🔦 **Flood Lamp prepared!** Your next Drowned Station run will blunt supernatural Sanity loss."},
    "drowned_last_stop_ticket": {"name": "Last Stop Ticket", "emoji": "🎫", "effect": "haunted_drowned_last_stop_ticket", "message": "🎫 **Last Stop Ticket prepared!** Your next Drowned Station run can take a shorter route through the station."},
    "campground_static_filter": {"name": "Static Filter", "emoji": "📻", "effect": "haunted_campground_static_filter", "message": "📻 **Static Filter prepared!** Your next Silent Campground run will suppress some supernatural Sanity loss."},
    "campground_tendril_ward": {"name": "Tendril Ward", "emoji": "🖤", "effect": "haunted_campground_tendril_ward", "message": "🖤 **Tendril Ward prepared!** Your next Silent Campground run will make rare Halloween finds easier to uncover."},
}


HALLOWEEN_SPECIAL_USE_ITEMS = {
    "wine_cabinet": {
        "enabled": True,
        "name": "Cursed Wine Cabinet",
        "emoji": "🍷",
        "achievement_id": "halloween_wine_cabinet",
        "title_id": "title_seal_breaker",
        "use_message": (
            "**You slowly peel away the cracked wax, your fingers trembling as it breaks. The seal has been broken.**\n"
            "The wooden doors of the cabinet instantly slam open on their own with a horrifying, inhuman screench.\n"
            "A wave of freezing, rot-scented air hits you dead in the face, choking the breath right out of your throat.\n"
            "From the pitch-black hollow of the cabinet, a dozen overlapping, jagged voices whisper directly into your ear.'\n"
            "**The seal is broken. There's no turning back. You have unleashed something truly terrible.**"
        ),
        "knockout_message": (
            "**A pair of freezing, unseen hands wrap tightly around your neck...**\n"
            "The shadows in the corner of the room stretch across the floor, crawling up your legs and binding you in place.\n"
            "You try to scream, but the air in your lungs turn to ice. Your vision blurs into darkness.\n"
            "The last thing you hear before collapsing is the sound of heavy footsteps walking towards you...\n\n"
            "**You've lost all HP!** But you can revive for free, as I've given you a free revive!" # Effect: instant 100HP taken, but free revive given immediately. It alerts the user about it underneath all this
        ),
        "already_used_message": (
            "**You reach your hand into the empty cabinet, but your fingers only meet cold, splintered wood...**\n"
            "The air inside is hollow. The wax is ruined, and the hinges are completely destroyed.\n"
            "There is nothing left to let out...\n\n"
            "**It's too late. The box is empty. Whatever was trapped inside is already in the room with you now.**"
        ),
    },

    # -----------------------------------------------------------------------
    # FUTURE HALLOWEEN SPECIAL ITEMS — placeholders
    # -----------------------------------------------------------------------
    # Set ``enabled`` to True only after adding the item's effect handler in
    # _use_halloween_special_item_impl().
    "glitched_cartridge": {
        "enabled": True,
        "name": "Glitched Cartridge",
        "emoji": "👾",
        "achievement_id": "halloween_glitched_cartridge",
        "title_id": "title_drowned_in_code",
        "use_message": (
            "**You spot a nearby console, pop the cartridge into it and turn it on.**\n"
            "The audio violently glitches into a reversed, slowed-down melody. The save file screen flashes, showing a single slot labeled 'BEN.'\n"
            "Suddenly, a creepy, lifeless statue pops up behind your character in-game. You turn around.\n"
            "Its blank eyes staring through the screen directly at you. Text fills the screen, 'You shouldn't have done that.'\n"
            "The screen bursts with static and shuts off. The cartridge gets spit back out." # Effect: causes you to lose 15HP
        ),
        "already_used_message": (
            "You reach for the cartridge, but it's burning hot. From the cartridge is a muffled sound of someone drowning beneath deep water.\n"
            "Trying to use the cartridge again would mean letting it out."
        ),
    },
    "smile_photo": {
        "enabled": True,
        "name": "Hyper-realistic Dog Photo",
        "emoji": "🐶",
        "achievement_id": "halloween_smile_photo",
        "title_id": "title_spread_the_word",
        "use_message": (
            "**You flip the photograph over and inspect it.**\n"
            "Printed on the film is a husky-like dog in a dimly lit room, its jaw unhinged into a wide, bloody smile.\n"
            "The longer you stare, the louder a phantom scratching sound echoes against the walls around you.\n"
            "Your breathing turns rapid and panicked. You force yourself to look away.\n"
            "You shove the photo back into your inventory, but the terrifying grin stays perfectly clear in your mind." # No effect
        ),
        "already_used_message": (
            "You think about pulling the photograph out again.\n"
            "But the mere thought of it causes a sharp, splitting migraine. You can hear a faint, low growling coming from inside your inventory.\n"
            "You know that, if you look at that face one more time, you won't be able to ever look away again."
        ),
    },
    "red_pokeball": {
        "enabled": True,
        "name": "Glitched Red Pokeball",
        "emoji": "🔴",
        "achievement_id": "halloween_red_pokeball",
        "title_id": "title_red's_shadow",
        "use_message": (
            "**You throw the glitched red ball. It doesn't bounce.**\n"
            "It hits the floor with a wet, heavy thud. It pops open, spilling a pitch-black crimson mass across the ground.\n"
            "From the center of the distortion, the shadow silhouette of a silent, faceless trainer stares directly at you. You hear music dropping to a sickening, distorted crawl.\n"
            "The entity raises a hand, rewriting a piece of your reality... then retreats back into the capsule.\n"
            "The ball clicks shut." # No effect
        ),
        "already_used_message": (
            "You reach for the glitched ball, but it aggressively twitches in your hand.\n"
            "You hear a distorted voice call out to you...\n"
            "*'Y O U ' R E  S T A Y I N G  H E R E  W I T H  M E.'*\n"
            "You hear a faint scratching sound from the ball. If you let whatever is trapped in there out once more, it *isn't* going to go back in."
        ),
    },
    "hazmat_suit": {
        "enabled": True,
        "name": "Yellow Hazmat Suit",
        "emoji": "☢️",
        "achievement_id": "halloween_hazmat_suit",
        "title_id": "title_boundary_breaker",
        "use_message": (
            "**You put the suit on. It dampens the deafening hum, but not the dread you feel.**\n"
            "You suddenly slip through a tear in physics, walking among the endless yellow walls. It smells like damp carpet. Fluorescent lights all throughout.\n"
            "You turn a corner, catching a glimpse of a shadow that shouldn't be there. You panic.\n"
            "Suddenly, you get violently pulled backward, out of the maze and back to reality. You breathe a sigh of relief as you hit familiar ground. You take the suit off, and never look back." # Effect: causes you to lose 35HP
        ),
        "already_used_message": (
            "You reach for the zipper of the suit, but your hands begin to shake.\n"
            "The sound of humming lights and smell of damp carpet still lingers in your senses.\n"
            "A voice in your head whispers that, if you go back in there, the yellow walls won't let you leave a second time."
        ),
    },
    "glow_chalk": {
        "enabled": True,
        "name": "Glow-in-the-dark Chalk",
        "emoji": "🖊️",
        "achievement_id": "halloween_glow_chalk",
        "title_id": "title_otherworld_passenger",
        "use_message": (
            "**You grab the glowing chalk, find an elevator and go inside. You draw a glowing sigil right next to the panel.**\n"
            "You press the buttons in order: 4, 2, 6, 2, 10, 5.\n"
            "The elevator plunges into darkness on the 5th floor. The doors slide open. A pale woman steps in and stands right behind you.\n"
            "You stare straight at the floor, refusing to look at her as the elevator surges up to the 10th floor.\n"
            "The doors open to a pitch-black, decaying parallel world. You grab something valuable from the void, slam the door button, and escape back to your reality. You've escaped, but your hands are still shaking." # No effect
        ),
        "already_used_message": (
            "You reach for the chalk in your pocket, but the elevator panel suddenly glitches.\n"
            "The buttons flash a violent crimson red. The doors slide open on a random floor, revealing nothing but a pitch-black hallway stretching into an infinite void.\n"
            "A freezing cold whisper echoes up from the elevator shaft: 'YOU ALREADY LEFT YOUR SOUL HERE.'\n"
            "If you try to press another button right now, the doors will close and you will never find your way back home."
        ),
    },
    "ouija_board": {
        "enabled": True,
        "name": "A Ouija Board",
        "emoji": EMOJIS["ouija_board"],
        "achievement_id": "halloween_ouija_board",
        "title_id": "title_spirit_communicator",
        "use_message": (
            "👻 **You use the ouija board...**\n"
            "You ask if anyone is here with you...\n"
            "Nothing responds. But you feel a faint touch on your shoulder..." # Effect: causes you to lose 20HP
        ),
        "already_used_message": (
            "👻 You already used a ouija board once.\n"
            "Probably a bad idea to do it again.\n"
            "This time, something might come back with you..."
        ),
    },
    "marker": {
        "enabled": True,
        "name": "Unknown Alien Artifact",
        "emoji": "👽",
        "achievement_id": "halloween_marker",
        "title_id": "title_unitologist",
        "use_message": (
            "**You hold the artifact and hear faint whispers.**\n"
            "They crowd your mind, making you see things... hallucinate.\n"
            "You then hear the words 'Make Us Whole' repeat over... and over... and over..." # Effect: causes you to lose 10HP
        ),
        "already_used_message": (
            "You already gazed upon the artifact.\n"
            "You'll never unhear those words again."
        ),
    },
    "tails_doll": {
        "enabled": True,
        "name": "A Doll of Tails",
        "emoji": EMOJIS["doll_gem"],
        "achievement_id": "halloween_tails",
        "background_id": "background_glowing_gem",
        "use_message": (
            "**You hold the doll. The ship turns pitch dark.**\n"
            "The gem on its head starts to glow bright. You hear a faint song coming from it...\n" # Effect: causes you to lose 25HP
            "🎶 Can you feel the sunshine? 🎶"
        ),
        "already_used_message": (
            "You already interacted with the doll.\n"
            "You feel like next time, it may not end well."
        ),
    },
    "hacked_phone": {
        "enabled": True,
        "name": "Hacked Phone",
        "emoji": "📱",
        "achievement_id": "halloween_malo",
        "background_id": "background_malo",
        "use_message": (
            "**You hold the phone and see an app labeled 'MalO ver1.0.0'**\n"
            "You open the camera and take a photo of yourself...\n"
            "In the photo, you spot a skull-faced wolf, directly behind you. You look back, it's no longer there." # No effect
        ),
        "already_used_message": (
            "You already took a photo with the device.\n"
            "You feel as if, if you kept using it, it may invade your mind."
        ),
    },
}

# Discord application-command autocomplete names do not reliably render
# custom-emoji markup such as <:emoji_name:123456789>. Use a Unicode fallback
# in the picker while keeping the real custom emoji everywhere else.
USE_AUTOCOMPLETE_EMOJI_FALLBACKS = {
    "cosmic_insurance": "📋",
    "drone_battery": "🔋",
    "drone_power_cell": "⚡",
    "drone_quantum_battery": "⚛️",
    "fate_anchor": "⚓",
    "fuel_refill": "⚛️",
    "fuel_stabilizer": "🛢️",
    "hazard_shield": "🛡️",
    "laser_charge_cell": "🔋",
    "laser_power_cell": "⚡",
    "lucky_scanner": "📡",
    "ore_magnet": "🧲",
    "prototype_drill_bit": "⚙️",
    "quantum_battery": "⚛️",
    "station_rations": "🥫",
}


def get_use_autocomplete_emoji(item_id, emoji):
    """Return an emoji string safe to display in a slash-command choice name."""
    if isinstance(emoji, str) and emoji.startswith(("<:", "<a:")):
        return USE_AUTOCOMPLETE_EMOJI_FALLBACKS.get(item_id, "📦")
    return emoji or "📦"

# Master Item Registry used across inventory, shop, and exploration
ITEM_REGISTRY = {
    # Currencies & Consumables
    "laser_charge_cell": {"name": "Laser Charge Cell", "emoji": EMOJIS.get("laser_charge_cell", "🔋"), "max_quantity": 10, "type": "Consumable", "desc": "Restores 2 mining laser charges."},
    "laser_power_cell": {"name": "Laser Power Cell", "emoji": EMOJIS.get("laser_power_cell", "⚡"), "max_quantity": 10, "type": "Consumable", "desc": "Restores 5 mining laser charges."},
    "fuel_refill": {"name": "Laser Quantum Cell", "emoji": EMOJIS.get("fuel_refill", "⚛️"), "max_quantity": 5, "type": "Consumable", "desc": "Instantly refills your starship mining laser to its current maximum charges."},
    "drone_battery": {"name": "Drone Battery Pack", "emoji": EMOJIS.get("drone_battery", "🔋"), "max_quantity": 10, "type": "Consumable", "desc": "Restores 2 scavenge charges."},
    "drone_power_cell": {"name": "Drone Power Cell", "emoji": EMOJIS.get("drone_power_cell", "⚡"), "max_quantity": 10, "type": "Consumable", "desc": "Restores 5 scavenge charges."},
    "drone_quantum_battery": {"name": "Drone Quantum Battery", "emoji": EMOJIS.get("drone_quantum_battery", "⚛️"), "max_quantity": 5, "type": "Consumable", "desc": "Fully restores your scavenging drone to its current maximum charges."},
    "pet_snack": {"name": "Pet Treat", "emoji": EMOJIS.get("pet_snack", "🍪"), "max_quantity": 99, "type": "Pet Treat", "desc": "A tasty treat that gives your active pet a chunk of Pet XP."},
    "normal_egg": {"name": "Pet Egg", "emoji": "🥚", "max_quantity": 10, "type": "Pet Egg", "desc": "A mysterious egg containing a normal station pet. Incubate for 12 hours."},
    "arcade_token": {"name": "Arcade Token", "emoji": EMOJIS["arcade_token"], "max_quantity": 1000, "type": "Currency", "desc": "A shiny token for '/minigames` and more in the future!"},
    "time_crystal": {"name": "Dilated Time Crystal", "emoji": EMOJIS.get("time_crystal", "💎"), "max_quantity": 4, "type": "Consumable", "desc": "Bends time backwards to restore a fortune streak missed yesterday."},
    "nanite_patch": {"name": "Nanite Stim-Patch", "emoji": EMOJIS.get("nanite_patch", "🩹"), "max_quantity": 50, "type": "Consumable", "desc": "Quickly knits minor planetary surface wounds. Restores +35 HP."},
    "medkit": {"name": "Field Trauma Medkit", "emoji": EMOJIS.get("medkit", "🧰"), "max_quantity": 25, "type": "Consumable", "desc": "Standard planetary survival trauma kit. Restores +100 HP."},
    "makeshift_medkit": {"name": "Makeshift Medkit", "emoji": EMOJIS.get("makeshift_medkit", "🩹"), "max_quantity": 25, "type": "Consumable", "desc": "A hastily assembled field kit made from scavenged medical supplies. Restores +60 HP."},
    "full_revive": {"name": "Emergency Full Revival", "emoji": EMOJIS.get("full_revive", "⚕️"), "max_quantity": 10, "type": "Healing", "desc": "Immediately revives an unconscious explorer at full HP."},
    "revive_kit": {"name": "Emergency Revival Kit", "emoji": EMOJIS.get("revive_kit", "💉"), "max_quantity": 25, "type": "Consumable", "desc": "Rare salvage that revives an unconscious explorer with 50% HP."},
    "revive": {"name": "Revival Kit", "emoji": EMOJIS.get("revive", "⚕️"), "max_quantity": 25, "type": "Consumable", "desc": "A basic revival item"},
    "fuel_stabilizer": {"name": "Fuel Stabilizer", "emoji": EMOJIS.get("fuel_stabilizer", "🛢️"), "max_quantity": 5, "type": "Consumable", "desc": "Makes the next mining run cost no fuel charge."},
    "station_rations": {"name": "Station Rations", "emoji": EMOJIS.get("station_rations", "🥫"), "max_quantity": 99, "type": "Consumable", "desc": "Restores 15 HP."},
    "hazard_shield": {"name": "Hazard Shield", "emoji": EMOJIS.get("hazard_shield", "🛡️"), "max_quantity": 5, "type": "Consumable", "desc": "Blocks the next scavenging hazard."},
    "lucky_scanner": {"name": "Deep-Space Scanner", "emoji": EMOJIS.get("lucky_scanner", "📡"), "max_quantity": 5, "type": "Consumable", "desc": "Improves rare-find odds on the next scavenging run."},
    "ore_magnet": {"name": "Ore Magnet", "emoji": EMOJIS.get("ore_magnet", "🧲"), "max_quantity": 5, "type": "Consumable", "desc": "Guarantees a titanium ore find on the next mining run."},
    "prototype_drill_bit": {"name": "Prototype Drill Bit", "emoji": EMOJIS.get("prototype_drill_bit", "⚙️"), "max_quantity": 5, "type": "Consumable", "desc": "Boosts Stardust from the next mining run."},
    "cosmic_insurance": {"name": "Cosmic Insurance", "emoji": EMOJIS.get("cosmic_insurance", "📋"), "max_quantity": 5, "type": "Consumable", "desc": "Prevents a knockout from the next scavenging hazard."},
    "fate_anchor": {"name": "Fate Anchor", "emoji": EMOJIS.get("fate_anchor", "⚓"), "max_quantity": 5, "type": "Consumable", "desc": "Protects one missed fortune streak day."},

    # Legendary Loot
    "astral_core": {"name": "Astral Core", "emoji": "🌌", "max_quantity": 5, "type": "Special", "desc": "A mysterious crystalline core recovered from deep space. Required to craft higher-tier exploration upgrades."},
    "astral_essence": {"name": "Astral Essence", "emoji": "✨", "max_quantity": 99, "type": "Special", "desc": "A concentrated fragment of strange stellar energy used to fuse duplicate pets and hunt for rare pet variants."},
    "quantum_battery": {"name": "Quantum Battery", "emoji": EMOJIS.get("quantum_battery", "⚛️"), "max_quantity": 5, "type": "Consumable", "desc": "Adds 5 mining laser charges and 5 scavenging drone charges, then triples Stardust from your next mining or scavenging run."},

    # Materials & Minerals
    "titanium_chunk": {"name": "Titanium Ore Chunk", "emoji": EMOJIS["titanium_chunk"], "max_quantity": 99, "sell_price": 15, "type": "Mineral", "desc": "High-purity raw titanium extracted from deep sector asteroids."},
    "iron_ore": {"name": "Iron Ore", "emoji": EMOJIS["iron_ore"], "max_quantity": 99, "sell_price": 3, "type": "Mineral", "desc": "Raw iron extracted from asteroid rock."},
    "copper_ore": {"name": "Copper Ore", "emoji": EMOJIS["copper_ore"], "max_quantity": 99, "sell_price": 5, "type": "Mineral", "desc": "Conductive copper-bearing ore from asteroid deposits."},
    "aluminum_ore": {"name": "Aluminum Ore", "emoji": EMOJIS["aluminum_ore"], "max_quantity": 99, "sell_price": 4, "type": "Mineral", "desc": "Lightweight aluminum ore recovered from asteroid deposits."},
    "circuit_board": {"name": "Circuit Board", "emoji": EMOJIS["circuit_board"], "max_quantity": 99, "sell_price": 20, "type": "Crafting Material", "desc": "Recovered electronics useful for building exploration equipment."},
    "glue": {"name": "Industrial Glue", "emoji": EMOJIS["glue"], "max_quantity": 99, "sell_price": 6, "type": "Crafting Material", "desc": "Heavy-duty adhesive salvaged from abandoned station supplies."},
    "scrap_metal": {"name": "Scrap Metal", "emoji": EMOJIS["scrap_metal"], "max_quantity": 99, "sell_price": 3, "type": "Crafting Material", "desc": "Useful metal recovered from wreckage."},
    "nuts_bolts": {"name": "Nuts & Bolts", "emoji": EMOJIS["nuts_bolts"], "max_quantity": 99, "sell_price": 4, "type": "Crafting Material", "desc": "Assorted fasteners salvaged from abandoned equipment."},
    "wiring": {"name": "Wiring", "emoji": EMOJIS["wiring"], "max_quantity": 99, "sell_price": 5, "type": "Crafting Material", "desc": "Usable electrical wiring salvaged from damaged equipment."},

    # Defensive Weapons
    "stop_sign": {"name": "Stop Sign", "emoji": "🛑", "max_quantity": 1, "type": "Defense Weapon", "desc": "A surprisingly sturdy traffic sign. Provides a small chance to prevent a scavenging hazard."},
    "stick": {"name": "Stick", "emoji": "🪵", "max_quantity": 1, "type": "Defense Weapon", "desc": "It's a stick. Somehow, it helps."},
    "wooden_sword": {"name": "Wooden Sword", "emoji": "🗡️", "max_quantity": 1, "type": "Defense Weapon", "desc": "A humble wooden sword with a small defensive chance."},
    "wooden_shield": {"name": "Wooden Shield", "emoji": "🛡️", "max_quantity": 1, "type": "Defense Weapon", "desc": "A basic wooden shield that can prevent incoming hazards."},
    "wooden_spoon": {"name": "Wooden Spoon", "emoji": "🥄", "max_quantity": 1, "type": "Defense Weapon", "desc": "A perfectly ordinary spoon. Surely this will protect you."},
    "heavy_wrench": {"name": "Suspiciously Heavy Wrench", "emoji": "🔧", "max_quantity": 1, "type": "Defense Weapon", "desc": "Technically a maintenance tool. Technically."},
    "plasma_cutter": {"name": "Plasma Cutter", "emoji": "🔫", "max_quantity": 1, "type": "Defense Weapon", "desc": "A precision plasma weapon recovered during the Halloween event. Provides a strong chance to prevent scavenging hazards."},

    # Upgrade Kits
    # The unsuffixed component IDs are retained as legacy compatibility items.
    # New crafting uses tier-specific IDs so each upgrade level gets the correct part.
    "reinforced_laser_parts": {"name": "Reinforced Laser Parts (Legacy)", "emoji": EMOJIS["reinforced_laser_parts"], "max_quantity": 5, "type": "Upgrade Component", "desc": "Legacy reinforced laser parts. These can still be used as a fallback for upgrades created before tiered parts were introduced."},
    "reinforced_laser_parts_1": {"name": "Reinforced Laser Parts", "emoji": EMOJIS["reinforced_laser_parts"], "max_quantity": 5, "type": "Upgrade Component", "desc": "Tier I precision-built parts used for the first mining laser upgrade."},
    "reinforced_laser_parts_2": {"name": "Reinforced Laser Parts II", "emoji": EMOJIS["reinforced_laser_parts"], "max_quantity": 5, "type": "Upgrade Component", "desc": "Tier II precision-built parts used for the second mining laser upgrade."},
    "reinforced_laser_parts_3": {"name": "Reinforced Laser Parts III", "emoji": EMOJIS["reinforced_laser_parts"], "max_quantity": 5, "type": "Upgrade Component", "desc": "Tier III precision-built parts used for the third mining laser upgrade."},
    "reinforced_laser_parts_4": {"name": "Reinforced Laser Parts IV", "emoji": EMOJIS["reinforced_laser_parts"], "max_quantity": 5, "type": "Upgrade Component", "desc": "Tier IV precision-built parts used for the fourth mining laser upgrade."},
    "reinforced_laser_parts_5": {"name": "Reinforced Laser Parts V", "emoji": EMOJIS["reinforced_laser_parts"], "max_quantity": 5, "type": "Upgrade Component", "desc": "Tier V precision-built parts used for the fifth mining laser upgrade."},
    "drone_upgrade_kit": {"name": "Drone Upgrade Kit (Legacy)", "emoji": EMOJIS["drone_upgrade_kit"], "max_quantity": 5, "type": "Upgrade Component", "desc": "Legacy drone upgrade kits. These can still be used as a fallback for upgrades created before tiered kits were introduced."},
    "drone_upgrade_kit_1": {"name": "Drone Upgrade Kit", "emoji": EMOJIS["drone_upgrade_kit"], "max_quantity": 5, "type": "Upgrade Component", "desc": "Tier I kit used for the first scavenging drone upgrade."},
    "drone_upgrade_kit_2": {"name": "Drone Upgrade Kit II", "emoji": EMOJIS["drone_upgrade_kit"], "max_quantity": 5, "type": "Upgrade Component", "desc": "Tier II kit used for the second scavenging drone upgrade."},
    "drone_upgrade_kit_3": {"name": "Drone Upgrade Kit III", "emoji": EMOJIS["drone_upgrade_kit"], "max_quantity": 5, "type": "Upgrade Component", "desc": "Tier III kit used for the third scavenging drone upgrade."},
    "drone_upgrade_kit_4": {"name": "Drone Upgrade Kit IV", "emoji": EMOJIS["drone_upgrade_kit"], "max_quantity": 5, "type": "Upgrade Component", "desc": "Tier IV kit used for the fourth scavenging drone upgrade."},
    "drone_upgrade_kit_5": {"name": "Drone Upgrade Kit V", "emoji": EMOJIS["drone_upgrade_kit"], "max_quantity": 5, "type": "Upgrade Component", "desc": "Tier V kit used for the fifth scavenging drone upgrade."},
    "astral_power_core": {"name": "Astral Power Core", "emoji": EMOJIS["astral_power_core"], "max_quantity": 5, "type": "Upgrade Component", "desc": "A stabilized Astral Core assembly for advanced upgrades."},
    "nanite_retrofit_kit": {"name": "Nanite Retrofit Kit", "emoji": EMOJIS["nanite_retrofit_kit"], "max_quantity": 5, "type": "Upgrade Component", "desc": "A precision nanite package required to install higher-tier exploration upgrades."},
    "salvage_rig_kit": {"name": "Salvage Rig Kit (Legacy)", "emoji": EMOJIS.get("salvage_rig_kit", "♻️"), "max_quantity": 5, "type": "Upgrade Component", "desc": "Legacy salvage rig kits. These can still be used as a fallback for upgrades created before tiered kits were introduced."},
    "salvage_rig_kit_1": {"name": "Salvage Rig Kit", "emoji": EMOJIS.get("salvage_rig_kit", "♻️"), "max_quantity": 5, "type": "Upgrade Component", "desc": "Tier I kit used for the first salvage rig upgrade."},
    "salvage_rig_kit_2": {"name": "Salvage Rig Kit II", "emoji": EMOJIS.get("salvage_rig_kit", "♻️"), "max_quantity": 5, "type": "Upgrade Component", "desc": "Tier II kit used for the second salvage rig upgrade."},
    "salvage_rig_kit_3": {"name": "Salvage Rig Kit III", "emoji": EMOJIS.get("salvage_rig_kit", "♻️"), "max_quantity": 5, "type": "Upgrade Component", "desc": "Tier III kit used for the third salvage rig upgrade."},
    "salvage_rig_kit_4": {"name": "Salvage Rig Kit IV", "emoji": EMOJIS.get("salvage_rig_kit", "♻️"), "max_quantity": 5, "type": "Upgrade Component", "desc": "Tier IV kit used for the fourth salvage rig upgrade."},
    "salvage_rig_kit_5": {"name": "Salvage Rig Kit V", "emoji": EMOJIS.get("salvage_rig_kit", "♻️"), "max_quantity": 5, "type": "Upgrade Component", "desc": "Tier V kit used for the fifth salvage rig upgrade."},

    # Medical Supplies
    "gauze": {"name": "Sterile Gauze", "emoji": EMOJIS["gauze"], "max_quantity": 99, "type": "Medical Supply", "desc": "Clean bandage material recovered from abandoned medical stations."},
    "medical_alcohol": {"name": "Medical Alcohol", "emoji": EMOJIS["alcohol"], "max_quantity": 99, "type": "Medical Supply", "desc": "Medical-grade alcohol useful for disinfecting wounds and equipment."},
    "bandaids": {"name": "Bandaids", "emoji": EMOJIS["bandaid"], "max_quantity": 99, "type": "Medical Supply", "desc": "Basic adhesive bandages recovered from abandoned medical supplies."},
    "antiseptic_ointment": {"name": "Antiseptic Ointment", "emoji": EMOJIS["ointment"], "max_quantity": 99, "type": "Medical Supply", "desc": "Antiseptic ointment useful for treating minor wounds."},

    # Haunted Exploration ingredients
    "ectoplasm": {"name": "Ectoplasm", "emoji": "🫧", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A cold, translucent residue left behind by something that should not exist."},
    "medical_residue": {"name": "Strange Medical Residue", "emoji": "🧪", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "An unsettling substance scraped from abandoned medical equipment."},
    "grave_dust": {"name": "Grave Dust", "emoji": "🪦", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "Fine dust gathered from forgotten graves. It feels unnaturally cold."},
    "bone_fragment": {"name": "Bone Fragment", "emoji": "🦴", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A small fragment of bone recovered from somewhere it definitely should not have been."},
    "black_wax": {"name": "Black Ritual Wax", "emoji": "🕯️", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "Dark wax that refuses to fully harden, even in the cold."},
    "cursed_fabric": {"name": "Cursed Fabric", "emoji": "🧵", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A scrap of old fabric that seems to shift when nobody is watching."},
    "consecrated_salt": {"name": "Consecrated Salt", "emoji": "🧂", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "Salt recovered from an abandoned sanctuary. It gives off a faint warmth."},
    "ritual_chalk": {"name": "Ritual Chalk", "emoji": "🖍️", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "Chalk used to mark symbols that are better left unexplained."},
    "witchroot": {"name": "Witchroot", "emoji": "🌿", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A twisted root from the Witch's Woods with a faintly sweet smell."},
    "mooncap_mushroom": {"name": "Mooncap Mushroom", "emoji": "🍄", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A pale mushroom that only seems to grow where moonlight should not reach."},
    "bloodstained_gauze": {"name": "Bloodstained Gauze", "emoji": "🩸", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "Old gauze carrying stains that look disturbingly fresh."},
    "cracked_syringe": {"name": "Cracked Syringe", "emoji": "💉", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A damaged syringe recovered from a room nobody remembers entering."},
    "spectral_thread": {"name": "Spectral Thread", "emoji": "🧵", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A nearly invisible strand that slips through ordinary fabric."},
    "wilted_bloom": {"name": "Wilted Grave Bloom", "emoji": "🥀", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A dead flower that remains strangely fragrant long after it should have rotted."},
    "funeral_thread": {"name": "Funeral Thread", "emoji": "🧵", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "Dark thread taken from an old burial shroud."},
    "grave_marker_shard": {"name": "Grave Marker Shard", "emoji": "🪨", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A chipped piece of stone bearing a name that has almost faded away."},
    "broken_doll_piece": {"name": "Broken Doll Piece", "emoji": "🪆", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A piece of an old doll. It always seems to be facing the wrong way."},
    "attic_mothwing": {"name": "Attic Moth Wing", "emoji": "🦋", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A dusty wing from a moth that should have been far too large."},
    "dusty_looking_glass": {"name": "Dusty Looking-Glass Shard", "emoji": "🪞", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A mirror shard whose reflection lags just a little behind reality."},
    "bell_fragment": {"name": "Bell Fragment", "emoji": "🔔", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A fragment from an old church bell that faintly rings when held."},
    "incense_resin": {"name": "Old Incense Resin", "emoji": "🫙", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A hardened aromatic resin found beside an abandoned altar."},
    "cracked_holy_water_vial": {"name": "Cracked Holy Water Vial", "emoji": "💧", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A chipped vial containing a few drops of strangely warm water."},
    "nightshade_berry": {"name": "Nightshade Berry", "emoji": "🫐", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A dark berry that seems to absorb the light around it."},
    "spider_lily": {"name": "Spider Lily", "emoji": "🌺", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A pale woodland flower growing where the ground feels unnaturally cold."},
    "glowmoss": {"name": "Glowmoss", "emoji": "🟢", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "Soft moss with a faint green glow that brightens in darkness."},

    # Space Junk
    "space_pizza": {"name": "Dehydrated Space Pizza", "emoji": "🍕", "max_quantity": 99, "type": "Space Junk", "desc": "Slightly freezer-burned."},
    "floppy_disk": {"name": "Ancient Alien Floppy Disk", "emoji": "💾", "max_quantity": 99, "type": "Space Junk", "desc": "Contains mysterious code."},
    "meteorite": {"name": "Suspiciously Warm Meteorite Chunk", "emoji": "🪨", "max_quantity": 99, "type": "Space Junk", "desc": "Glows faintly."},
    "rubber_duck": {"name": "Rubber Duck in a Micro-Spacesuit", "emoji": "🐤", "max_quantity": 99, "type": "Space Junk", "desc": "How cute! Ready for zero-gravity bath time."},
    "rusty_gear": {"name": "Tarnished Station Gear", "emoji": "⚙️", "max_quantity": 99, "type": "Space Junk", "desc": "Still turns, but squeaks."},
    "tape_deck": {"name": "Broken Cassette Player", "emoji": "📼", "max_quantity": 99, "type": "Space Junk", "desc": "Plays static."},
    "alien_artifact": {"name": "Miniature Alien Artifact", "emoji": "🛸", "max_quantity": 99, "type": "Space Junk", "desc": "Glows faintly."},
    "space_boot": {"name": "Singular Space Boot", "emoji": "🥾", "max_quantity": 99, "type": "Space Junk", "desc": "Wonder where the other one went..."},
    "cosmic_coin": {"name": "Cosmic Coin", "emoji": "🪙", "max_quantity": 99, "type": "Space Junk", "desc": "Give it a flip!"},
    "holo_poster": {"name": "Faded Holographic Poster", "emoji": "🖼️", "max_quantity": 99, "type": "Space Junk", "desc": "Features an unknown alien band."},
    "broken_laser": {"name": "Broken Laser Pistol", "emoji": "🔫", "max_quantity": 99, "type": "Space Junk", "desc": "Sparks occasionally."},
    "lost_logbook": {"name": "Waterlogged Starship Logbook", "emoji": "📓", "max_quantity": 99, "type": "Space Junk", "desc": "Completely unreadable."},
    "left_sock": {"name": "Left Sock", "emoji": "🧦", "max_quantity": 99, "type": "Space Junk", "desc": "The right one is missing."},
    "warp_mug": {"name": "Leaky Thermal Mug", "emoji": "☕", "max_quantity": 99, "type": "Space Junk", "desc": "Holds coffee across space-time, leaks in 3D."},
    "space_pudding": {"name": "Expired Pudding", "emoji": "🍮", "max_quantity": 99, "type": "Space Junk", "desc": "Tastes like dark matter."},
    "tangled_cables": {"name": "Quantum Cable Knot", "emoji": "🔌", "max_quantity": 99, "type": "Space Junk", "desc": "Physically impossible to untangle."},
    "screaming_crystal": {"name": "Screaming Crystal", "emoji": "💎", "max_quantity": 99, "type": "Space Junk", "desc": "Relentlessly sings 80s synth-pop."},
    "moon_cheese": {"name": "Chunk of Moon Cheese", "emoji": "🧀", "max_quantity": 99, "type": "Space Junk", "desc": "Smells like sharp cheddar."},
    "golden_spatula": {"name": "Golden Spatula", "emoji": "🍳", "max_quantity": 99, "type": "Space Junk", "desc": "Maybe SpongeBob had it?"},
    "parking_ticket": {"name": "Cosmic Parking Ticket", "emoji": "📜", "max_quantity": 99, "type": "Space Junk", "desc": "Overdue by 400 years! That's a big fine..."},
    "floating_plant": {"name": "Suspicious Houseplant", "emoji": "🪴", "max_quantity": 99, "type": "Space Junk", "desc": "Stares at you when you turn around..."},
    "tinted_visor": {"name": "Broken Solar Visor", "emoji": "🕶️", "max_quantity": 99, "type": "Space Junk", "desc": "Now just regular 3D glasses."},
    "purring_lint": {"name": "Ball of Space Lint", "emoji": "🧶", "max_quantity": 99, "type": "Space Junk", "desc": "It purrs when you touch it."},
    "pet_rock": {"name": "Asteroid Pet Rock", "emoji": "🪨", "max_quantity": 99, "type": "Space Junk", "desc": "Includes tiny glued-on googly eyes."},
    "haunted_circuit": {"name": "Haunted Circuit Board", "emoji": "⚡", "max_quantity": 99, "type": "Space Junk", "desc": "Sparks every time you whisper near it."},
    "space_taco": {"name": "Cosmic Taco", "emoji": "🌮", "max_quantity": 99, "type": "Space Junk", "desc": "The salsa is surprisingly unaffected by zero-G."},
    "rusty_wrench": {"name": "Rusty Wrench", "emoji": "🔧", "max_quantity": 99, "type": "Space Junk", "desc": "Still works, but squeaks a lot."},
    "alien_fossil": {"name": "Alien Fossil Fragment", "emoji": "🦴", "max_quantity": 99, "type": "Space Junk", "desc": "Looks like it could bite back."},
    "big_red_button": {"name": "A Big Red Button", "emoji": "🔴", "max_quantity": 99, "type": "Space Junk", "desc": "Labeled 'do not press', but you pressed it anyway. It did nothing..."},
    "antique_compass": {"name": "Antique Compass", "emoji": "🧭", "max_quantity": 99, "type": "Space Junk", "desc": "Points to the nearest space anomaly, which is currently a black hole."},
    "broken_clock": {"name": "Broken Clock", "emoji": "⏰", "max_quantity": 99, "type": "Space Junk", "desc": "Stuck at 3:00AM. Witching hour... spooky."},
    "perplexing_painting": {"name": "Perplexing Painting", "emoji": "🖌️", "max_quantity": 99, "type": "Space Junk", "desc": "The eyes seem to follow you..."},
    "cosmic_banana": {"name": "Cosmic Banana", "emoji": "🍌", "max_quantity": 99, "type": "Space Junk", "desc": "Peels itself, but tastes like stardust."},

    # Background Vouchers
    "neon_grid": {"name": "Background Voucher: Neon Grid", "emoji": "🌆", "max_quantity": 1, "type": "Voucher", "desc": "Unlocks the Cyberpunk Neon Grid profile card."},
    "deep_void": {"name": "Background Voucher: Deep Void", "emoji": "🌌", "max_quantity": 1, "type": "Voucher", "desc": "Unlocks the Deep Void galaxy profile card."},
    "solaris_ring": {"name": "Background Voucher: Solaris Ring", "emoji": "☀️", "max_quantity": 1, "type": "Voucher", "desc": "Unlocks the Solaris Ring star system profile card."},

    # Profile Titles
    "title_outer_rim_wanderer": {"name": "Outer Rim Wanderer", "emoji": "🏷️", "max_quantity": 1, "type": "Title","desc": "A title for explorers who venture beyond the station."},
    "title_starborn": {"name": "Starborn", "emoji": "✨", "max_quantity": 1, "type": "Title", "desc": "A prestigious title for those touched by the stars."},
    "title_voidfarer": {"name": "Voidfarer", "emoji": "🌌", "max_quantity": 1, "type": "Title", "desc": "A title for those brave enough to chart the endless void."},
    "title_patient_zero": {"name": "Patient Zero", "emoji": "🏥", "max_quantity": 1, "type": "Title", "desc": "A permanent title earned by uncovering every rare discovery in the Abandoned Asylum."},
    "title_housebroken": {"name": "Housebroken", "emoji": "🏚️", "max_quantity": 1, "type": "Title", "desc": "A permanent title earned by uncovering every rare discovery in the Haunted House."},
    "title_into_the_woods": {"name": "Into the Woods", "emoji": "🌲", "max_quantity": 1, "type": "Title", "desc": "A permanent title earned by uncovering every rare discovery in Witch's Woods."},
    "title_playtime_is_over": {"name": "Playtime Is Over", "emoji": "🧸", "max_quantity": 1, "type": "Title", "desc": "A permanent title earned by uncovering every rare discovery in the Toy Workshop."},
    "title_no_vacancy": {"name": "No Vacancy", "emoji": "🏨", "max_quantity": 1, "type": "Title", "desc": "A permanent title earned by uncovering every rare discovery in the Endless Hotel."},
    "title_it_saw_you_too": {"name": "It Saw You Too", "emoji": "🧪", "max_quantity": 1, "type": "Title", "desc": "A permanent title earned by uncovering every rare discovery in the Research Facility."},
    "title_lost_actually": {"name": "Lost, Actually", "emoji": "🟨", "max_quantity": 1, "type": "Title", "desc": "A permanent title earned by uncovering every rare discovery in the Yellow Halls."},
    "title_mind_the_water": {"name": "Mind the Water", "emoji": "🌊", "max_quantity": 1, "type": "Title", "desc": "A permanent title earned by uncovering every rare discovery in the Drowned Station."},
    "title_haunted_explorer": {"name": "Haunted Explorer", "emoji": "👁️", "max_quantity": 1, "type": "Title", "desc": "A title for those who discovered something they probably should not have."},
    "title_something_is_very_wrong": {"name": "Something Is Very Wrong", "emoji": "👁️", "max_quantity": 1, "type": "Title", "desc": "A title earned by discovering something impossible."},
    "title_worth_it": {"name": "Worth It", "emoji": "🩸", "max_quantity": 1, "type": "Title", "desc": "A title for surviving a discovery that really hurt."},
    "title_unwell": {"name": "Unwell", "emoji": "🫥", "max_quantity": 1, "type": "Title", "desc": "A title earned after a discovery pushes you to 0 Sanity."},
    "title_the_other_side": {"name": "The Other Side", "emoji": "👁️", "max_quantity": 1, "type": "Title", "desc": "A title for discovering something while completely insane."},
    "title_i_shouldnt_have_looked": {"name": "I Shouldn't Have Looked", "emoji": "🕳️", "max_quantity": 1, "type": "Title", "desc": "A title for discovering every rare Haunted discovery."},
    "title_practiced_alchemist": {"name": "Practiced Alchemist", "emoji": "🧪", "max_quantity": 1, "type": "Title", "desc": "A title for brewing Haunted items."},
    "title_alchemist": {"name": "Alchemist", "emoji": "🧪", "max_quantity": 1, "type": "Title", "desc": "A title for crafting five Haunted Cauldron items."},
    "title_improvised_engineer": {"name": "Improvised Engineer", "emoji": "🛠️", "max_quantity": 1, "type": "Title", "desc": "A title for assembling your first Haunted Workshop item."},
    "title_haunted_handyman": {"name": "Haunted Handyman", "emoji": "🛠️", "max_quantity": 1, "type": "Title", "desc": "A title for assembling five Haunted Workshop items."},
    "title_occult_hobbyist": {"name": "Occult Hobbyist", "emoji": "🕯️", "max_quantity": 1, "type": "Title", "desc": "A title for performing your first Haunted ritual."},
    "title_occultist": {"name": "Occultist", "emoji": "🕯️", "max_quantity": 1, "type": "Title", "desc": "A title for performing five Haunted rituals."},
    "title_horror_enthusiast": {"name": "Horror Enthusiast", "emoji": "👻", "max_quantity": 1, "type": "Title", "desc": "A permanent title earned by collecting every Halloween Space Junk collectible."},
    "title_candy_nommer": {"name": "Candy Nommer", "emoji": "🍫", "max_quantity": 1, "type": "Title", "desc": "A permanent title for consuming over 250 pieces of candy/trick or treat bags. Diabeetus."},
    "title_seal_breaker": {"name": "Seal Breaker", "emoji": "🍷", "max_quantity": 1, "type": "Title", "desc": "A permanent title earned by breaking the seal on the Cursed Wine Cabinet."},

    
    "mascot_fabric": {"name": "Mascot Fabric", "emoji": "🧵", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "Faded fabric torn from an old mascot costume."},
    "blackened_grease": {"name": "Blackened Grease", "emoji": "🛢️", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "Thick grease with a burnt smell that never quite leaves your hands."},
    "mechanical_parts": {"name": "Mechanical Parts", "emoji": "⚙️", "max_quantity": 99, "sell_price": 10, "type": "Crafting Material", "desc": "Useful gears, springs, brackets, and other salvaged machine parts."},
    "stuffing": {"name": "Old Stuffing", "emoji": "☁️", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "Dusty stuffing pulled from something that should have stayed stitched shut."},
    "bent_toy_parts": {"name": "Bent Toy Parts", "emoji": "🧸", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "Plastic and metal pieces from a broken toy that seems to have been recently handled."},
    "faded_paint": {"name": "Faded Paint", "emoji": "🎨", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "Peeling paint with colors that look wrong under dim light."},
    "plastic_eye": {"name": "Plastic Eye", "emoji": "👁️", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A toy eye that always seems to be looking just slightly to the side of you."},
    "radio_components": {"name": "Radio Components", "emoji": "📻", "max_quantity": 99, "sell_price": 10, "type": "Crafting Material", "desc": "Salvaged knobs, coils, speakers, and other broadcast hardware."},
    "damaged_vhs_tape": {"name": "Damaged VHS Tape", "emoji": "📼", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A warped tape whose label has been completely rubbed away."},
    "burnt_capacitor": {"name": "Burnt Capacitor", "emoji": "🔋", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A scorched capacitor that still carries a faint static charge."},
    "recorded_static": {"name": "Recorded Static", "emoji": "📡", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A recording of pure static that occasionally contains a voice."},
    "bent_key": {"name": "Bent Hotel Key", "emoji": "🗝️", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A brass room key bent almost in half. The room number keeps changing."},
    "hotel_carpet_thread": {"name": "Hotel Carpet Thread", "emoji": "🧵", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "Thread pulled from an ancient hotel carpet. It smells faintly damp."},
    "old_guest_receipt": {"name": "Old Guest Receipt", "emoji": "🧾", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A receipt for a guest who apparently checked in tomorrow."},
    "flickering_bulb": {"name": "Flickering Bulb", "emoji": "💡", "max_quantity": 99, "sell_price": 10, "type": "Crafting Material", "desc": "A dying bulb that flickers even when disconnected."},
    "dusty_cleaning_rag": {"name": "Dusty Cleaning Rag", "emoji": "🧹", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A cleaning rag carrying dust from somewhere that has no visible floor."},
    "condensed_fog": {"name": "Condensed Fog", "emoji": "🌫️", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "Cold vapor sealed in a container. It moves against gravity."},
    "rusty_pipe": {"name": "Rusty Pipe", "emoji": "🪈", "max_quantity": 99, "sell_price": 10, "type": "Crafting Material", "desc": "A corroded length of pipe with something dark dried inside."},
    "cracked_brick": {"name": "Cracked Brick", "emoji": "🧱", "max_quantity": 99, "sell_price": 10, "type": "Crafting Material", "desc": "A chunk of masonry from a street that doesn't appear on any map."},
    "damaged_battery": {"name": "Damaged Battery", "emoji": "🔋", "max_quantity": 99, "sell_price": 10, "type": "Crafting Material", "desc": "A partially discharged battery recovered from abandoned equipment."},
    "chemical_sample": {"name": "Unknown Chemical Sample", "emoji": "🧪", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A sealed sample whose color changes when nobody is looking."},
    "broken_lab_glass": {"name": "Broken Lab Glass", "emoji": "🔬", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A shard of laboratory glass with a residue that glows faintly."},
    "contaminated_gloves": {"name": "Contaminated Gloves", "emoji": "🧤", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "Protective gloves stained by an experiment that is better left unidentified."},
    "unknown_biological_residue": {"name": "Unknown Biological Residue", "emoji": "🫀", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A sample collected from somewhere it absolutely should not have been."},

    # Haunted Exploration — The Yellow Halls
    "yellow_wallpaper_scrap": {"name": "Yellow Wallpaper Scrap", "emoji": "🟨", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A peeling strip of old yellow wallpaper. The damp backing feels strangely warm."},
    "damp_carpet_fiber": {"name": "Damp Carpet Fiber", "emoji": "🧵", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A thread pulled from the perpetually damp carpet. It smells faintly of mildew and something older."},
    "frayed_electrical_wire": {"name": "Frayed Electrical Wire", "emoji": "🔌", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A length of exposed wire pulled from a wall that should not have had wiring behind it."},
    "unmarked_key": {"name": "Unmarked Key", "emoji": "🗝️", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A plain metal key with no number, label, or obvious lock. It is always slightly warm."},
    "strange_fluorescent_tube": {"name": "Strange Fluorescent Tube", "emoji": "💡", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A humming fluorescent tube that continues glowing long after it has been removed from the ceiling."},
    "yellow_hall_light_cover": {"name": "Yellowed Light Cover", "emoji": "🔲", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A brittle fluorescent light cover stained the same sickly yellow as the halls."},

    # Haunted Exploration — The Dead-End Highway
    "rusted_road_sign": {"name": "Rusted Road Sign", "emoji": "🛣️", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A corroded piece of highway signage. The destination printed on it does not exist on any map."},
    "damaged_payphone_part": {"name": "Damaged Payphone Part", "emoji": "☎️", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A broken component from a roadside payphone. It still carries a faint dial tone."},
    "old_road_map": {"name": "Old Road Map", "emoji": "🗺️", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A weathered highway map with several roads drawn in that do not appear on the original."},
    "contaminated_fuel_can": {"name": "Contaminated Fuel Can", "emoji": "⛽", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "An old fuel can containing a dark, oily residue that moves when the can is still."},
    "rusty_car_part": {"name": "Rusty Car Part", "emoji": "🔩", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A corroded piece of an abandoned vehicle. You cannot quite identify which part of the car it came from."},
    "motel_key": {"name": "Motel Key", "emoji": "🗝️", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A tarnished motel key stamped with a room number that seems to change when you blink."},

    # Haunted Exploration — The Drowned Station
    "waterlogged_transit_ticket": {"name": "Waterlogged Transit Ticket", "emoji": "🎫", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A soaked transit ticket from a station whose name has been scratched away."},
    "corroded_train_part": {"name": "Corroded Train Part", "emoji": "🚇", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A rusted fragment of a train that spent far too long beneath the water."},
    "flooded_flashlight": {"name": "Flooded Flashlight", "emoji": "🔦", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A waterlogged flashlight that should be useless, yet its bulb occasionally flickers."},
    "damaged_conductor": {"name": "Damaged Conductor's Badge", "emoji": "🎟️", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A corroded conductor's badge bearing a name that has almost completely dissolved."},
    "contaminated_water_sample": {"name": "Contaminated Water Sample", "emoji": "💧", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "Dark station water sealed in a vial. Something moves inside when the vial is shaken."},
    "submerged_key": {"name": "Submerged Station Key", "emoji": "🗝️", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A heavy key recovered from the flooded tracks. The lock it belongs to is nowhere in sight."},

    # Haunted Exploration — The Silent Campground
    "static_damaged_radio": {"name": "Static-Damaged Radio", "emoji": "📻", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A battered handheld radio that produces static even when switched off."},
    "distorted_photograph": {"name": "Distorted Photograph", "emoji": "📷", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A photograph whose background contains shapes that were not visible when the picture was taken."},
    "strange_notebook_page": {"name": "Strange Notebook Page", "emoji": "📓", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A torn page covered in frantic notes about something standing between the trees."},
    "corrupted_video_tape": {"name": "Corrupted Video Tape", "emoji": "📼", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A damaged recording that occasionally shows a tall figure where nobody was standing."},
    "damaged_antenna": {"name": "Damaged Antenna", "emoji": "📡", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A bent antenna covered in scratches. Radios behave strangely whenever it is nearby."},
    "blackened_tree_bark": {"name": "Blackened Tree Bark", "emoji": "🌲", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A piece of bark from a tree with no visible source. It is cold despite being dry."},
    "unidentified_black_tendril": {"name": "Unidentified Black Tendril", "emoji": "🖤", "max_quantity": 99, "sell_price": 10, "type": "Haunted Ingredient", "desc": "A thin, rubbery black strand that seems to twitch when nobody is looking directly at it."},
}

# Seasonal Space Junk is registered here so it automatically appears in /inventory
# while its event module remains the place where the seasonal definitions live.
for _item_id, _name, _emoji, _desc, _stardust, _candy in halloween_season.HALLOWEEN_SPACE_JUNK:
    ITEM_REGISTRY[_item_id] = {
        "name": _name,
        "emoji": _emoji,
        "max_quantity": 99,
        "type": "Space Junk",
        "desc": _desc,
    }

del _item_id, _name, _emoji, _desc

# Seasonal Halloween crafting/healing items are registered separately from
# Space Junk so they can be used normally without becoming collectibles.
ITEM_REGISTRY.update(halloween_season.HALLOWEEN_ITEMS)

async def add_inventory_item(db, user_id, item_id, item_type, amount=1):
    """
    Add an item while respecting the item's max_quantity from ITEM_REGISTRY.

    Returns:
        (added_amount, new_quantity, max_quantity)
    """
    item_info = ITEM_REGISTRY.get(item_id, {})
    max_quantity = item_info.get("max_quantity", 10)

    async with db.execute(
        "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
        (user_id, item_id)
    ) as cursor:
        row = await cursor.fetchone()

    current_quantity = (row[0] or 0) if row else 0
    space_remaining = max(0, max_quantity - current_quantity)
    added_amount = min(amount, space_remaining)
    new_quantity = current_quantity + added_amount

    if added_amount > 0:
        if row:
            await db.execute(
                """
                UPDATE inventory
                SET quantity = ?
                WHERE user_id = ? AND item_id = ?
                """,
                (new_quantity, user_id, item_id)
            )
        else:
            await db.execute(
                """
                INSERT INTO inventory
                    (user_id, item_id, item_type, quantity)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, item_id, item_type, added_amount)
            )

    return added_amount, new_quantity, max_quantity

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db_path(self):
        """Return the separate Station economy database."""
        from database import ECONOMY_DB_NAME
        return ECONOMY_DB_NAME

    async def ensure_effect_schema(self, db):
        async with db.execute("PRAGMA table_info(users)") as cursor:
            columns = {row[1] async for row in cursor}
        if "active_effects" not in columns:
            await db.execute("ALTER TABLE users ADD COLUMN active_effects TEXT DEFAULT '{}'")
            await db.commit()

    async def get_charge_caps(self, user_id):
        """Return the user's current mining/scavenging charge capacities.

        Exploration upgrades can raise the default 10-charge capacity, so
        consumable charge restores must use the same upgrade source as
        /mine and /scavenge instead of hard-coding 10.
        """
        default_caps = {"mining": 10, "scavenging": 10}
        upgrade_cog = self.bot.get_cog("Upgrades")

        if upgrade_cog is None:
            return default_caps

        try:
            mining_effects = await upgrade_cog.get_effects(user_id, "mining")
            scavenging_effects = await upgrade_cog.get_effects(user_id, "scavenging")

            return {
                "mining": max(1, int(mining_effects.get("max_charges", 10))),
                "scavenging": max(1, int(scavenging_effects.get("max_charges", 10))),
            }
        except Exception:
            # /use should remain functional even if the upgrade cog is
            # temporarily unavailable or an older profile has malformed data.
            return default_caps

    async def title_autocomplete(self, interaction: discord.Interaction, current: str):
        """Show the user's owned profile titles in the Discord autocomplete menu."""
        user_id = interaction.user.id
        current = current.lower().strip()

        from database import ECONOMY_DB_NAME

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            async with db.execute(
                """
                SELECT item_id
                FROM inventory
                WHERE user_id = ? AND item_type = 'title'
                ORDER BY item_id
                """,
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()

        choices = []

        # Allow the user to remove their currently equipped title.
        if not current or "none" in current:
            choices.append(
                app_commands.Choice(
                    name="❌ Unequip current title",
                    value="none"
                )
            )

        for (item_id,) in rows:
            # Convert IDs such as title_outer_rim_wanderer
            # into readable names such as Outer Rim Wanderer.
            display_name = item_id.removeprefix("title_").replace("_", " ").title()

            if current and current not in display_name.lower() and current not in item_id.lower():
                continue

            choices.append(
                app_commands.Choice(
                    name=f"🏷️ {display_name}",
                    value=item_id
                )
            )

        return choices[:25]

    @commands.hybrid_group(
        name="equip",
        description="Equip an unlocked Station cosmetic."
    )
    async def equip(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send(
                "Use `/equip title` to equip one of your unlocked profile titles."
            )

    @equip.command(
        name="title",
        description="Equip one of your unlocked profile titles."
    )
    @app_commands.describe(title="Choose a title you own.")
    @app_commands.autocomplete(title=title_autocomplete)
    async def equip_title(self, ctx: commands.Context, title: str):
        await ctx.defer()
        user_id = ctx.author.id
        title = title.lower().strip()

        # Reuse the same per-user lock used by /use, /mine, and /scavenge.
        exploration_cog = self.bot.get_cog("Exploration")

        if exploration_cog is not None:
            lock = exploration_cog._user_locks.setdefault(user_id, asyncio.Lock())
        else:
            if not hasattr(self, "_user_locks"):
                self._user_locks = {}
            lock = self._user_locks.setdefault(user_id, asyncio.Lock())

        async with lock:
            from database import ECONOMY_DB_NAME

            async with aiosqlite.connect(ECONOMY_DB_NAME) as db:

                # Unequip the current title.
                if title == "none":
                    await db.execute(
                        "UPDATE users SET equipped_title = '' WHERE user_id = ?",
                        (user_id,)
                    )
                    await db.commit()

                    return await ctx.send(
                        f"{ctx.author.mention} ❌ **Title unequipped.** Your profile is now title-free."
                    )

                # Make sure the player actually owns this title.
                async with db.execute(
                    """
                    SELECT 1
                    FROM inventory
                    WHERE user_id = ?
                      AND item_id = ?
                      AND item_type = 'title'
                      AND quantity > 0
                    """,
                    (user_id, title)
                ) as cursor:
                    owned = await cursor.fetchone()

                if not owned:
                    return await ctx.send(
                        "🔒 **You don't own that title!** "
                        "Purchase it from the rotating shop first."
                    )

                await db.execute(
                    "UPDATE users SET equipped_title = ? WHERE user_id = ?",
                    (title, user_id)
                )
                await db.commit()

            display_name = title.removeprefix("title_").replace("_", " ").title()

            await ctx.send(
                f"{ctx.author.mention} 🏷️ **Title Equipped!** Your profile title is now "
                f"**{display_name}**."
            )

    @commands.hybrid_command(name="inventory", description="Open your station storage locker to view collected items and vouchers.")
    async def inventory(self, ctx: commands.Context):
        await ctx.defer()
        user_id = ctx.author.id

        async with aiosqlite.connect(self.get_db_path()) as db:
            async with db.execute("""
                SELECT item_id, item_type, quantity FROM inventory
                WHERE user_id = ? AND item_id NOT IN ('time_crystal', 'nanite_patch', 'medkit', 'arcade_token')
            """, (user_id,)) as cursor:
                inv_rows = await cursor.fetchall()
            async with db.execute("PRAGMA table_info(users)") as cursor:
                columns = [row[1] async for row in cursor]
            user_items = []
            if all(col in columns for col in ["time_crystals", "nanite_patchs", "medkits"]):
                async with db.execute("SELECT time_crystals, nanite_patchs, medkits FROM users WHERE user_id = ?", (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        tc, nanites, medkits = row[0] or 0, row[1] or 0, row[2] or 0
                        if tc > 0: user_items.append(("time_crystal", tc))
                        if nanites > 0: user_items.append(("nanite_patch", nanites))
                        if medkits > 0: user_items.append(("medkit", medkits))
            if "arcade_coins" in columns:
                async with db.execute("SELECT COALESCE(arcade_coins, 0) FROM users WHERE user_id = ?", (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0] > 0:
                        user_items.append(("arcade_token", min(row[0], 1000)))

        if not inv_rows and not user_items:
            return await ctx.send("📦 **Your storage locker is completely empty!** Head out with `/mine` or `/scavenge` to fill it up!")

        categories = {"Space Junk": [], "Mineral": [], "Crafting Material": [], "Medical Supply": [], "Upgrade Component": [], "Defense Weapon": [], "Consumable": [], "Pet Treat": [], "Pet Egg": [], "Healing": [], "Haunted Ingredient": [], "Voucher": [], "Currency": []}
        for item_id, count in user_items:
            info = ITEM_REGISTRY.get(item_id)
            if info:
                cat = info.get("type", "Consumable")
                categories.setdefault(cat, []).append(f"{info['emoji']} **{info['name']}** ({count}/{info.get('max_quantity', 10)})\n└ *{info['desc']}*")
        for item_id, item_type, quantity in inv_rows:
            info = ITEM_REGISTRY.get(item_id, {"name": item_id, "emoji": "📦", "type": "Space Junk", "desc": "A weird salvage find."})
            cat = info.get("type", "Space Junk")
            categories.setdefault(cat, []).append(f"{info['emoji']} **{info['name']}** ({quantity or 0}/{info.get('max_quantity', 10)})\n└ *{info['desc']}*")

        names = {"Space Junk":"Space Junk","Mineral":"Minerals","Crafting Material":"Crafting Materials","Medical Supply":"Medical Supplies","Upgrade Component":"Upgrade Components","Defense Weapon":"Defense Weapons","Consumable":"Consumables","Pet Treat":"Pet Treats","Pet Egg":"Pet Eggs","Healing":"Healing","Haunted Ingredient":"Haunted Ingredients","Voucher":"Vouchers","Currency":"Currencies"}
        pages=[]
        for cat, items in categories.items():
            if not items: continue
            chunks=[]; current=""
            for item in items:
                if current and len(current)+len(item)+1 > 1000:
                    chunks.append(current); current=item
                else: current=f"{current}\n{item}" if current else item
            if current: chunks.append(current)
            for i, chunk in enumerate(chunks):
                display=names.get(cat,cat); suffix=f" ({i+1}/{len(chunks)})" if len(chunks)>1 else ""
                e=discord.Embed(title=f"📦 {ctx.author.display_name}'s Storage Locker", description=f"**{display}**", color=discord.Color.from_rgb(0,229,255))
                e.add_field(name=f"✨ Items{suffix}", value=chunk, inline=False); pages.append(e)

        class InventoryView(discord.ui.View):
            def __init__(self, owner_id, embeds):
                super().__init__(timeout=300); self.owner_id=owner_id; self.embeds=embeds; self.current_page=0
            def current_embed(self):
                e=self.embeds[self.current_page]; e.set_footer(text=f"Page {self.current_page+1}/{len(self.embeds)} • Sell unwanted salvage with /shop sell"); return e
            async def interaction_check(self, interaction):
                if interaction.user.id != self.owner_id:
                    await interaction.response.send_message("❌ This inventory menu belongs to someone else.", ephemeral=True); return False
                return True
            @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
            async def previous(self, interaction, button):
                self.current_page=(self.current_page-1)%len(self.embeds); await interaction.response.edit_message(embed=self.current_embed(), view=self)
            @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
            async def next(self, interaction, button):
                self.current_page=(self.current_page+1)%len(self.embeds); await interaction.response.edit_message(embed=self.current_embed(), view=self)

        view=InventoryView(ctx.author.id,pages)
        await ctx.send(embed=view.current_embed(), view=view)

    async def use_item_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ):
        """Show items that /use supports, with the user's owned quantity."""
        current = (current or "").lower().strip()

        # Healing items stay exclusively in /heal. Revival items stay in /revive.
        usable_items = {
            "fuel_refill",
            "laser_charge_cell",
            "laser_power_cell",
            "drone_battery",
            "drone_power_cell",
            "drone_quantum_battery",
            "fuel_stabilizer",
            "station_rations",
            "hazard_shield",
            "lucky_scanner",
            "ore_magnet",
            "prototype_drill_bit",
            "cosmic_insurance",
            "fate_anchor",
            "quantum_battery",
            *[item_id for item_id, config in HALLOWEEN_SPECIAL_USE_ITEMS.items() if config.get("enabled")],
            *HAUNTED_CRAFTED_USE_ITEMS.keys(),
            *[
                item_id
                for item_id, info in ITEM_REGISTRY.items()
                if info.get("type") == "Haunted Potion"
            ],
        }

        # Only show items the user actually owns.  /use is an inventory
        # action, so the autocomplete should not offer the entire catalog.
        quantities = {}
        try:
            async with aiosqlite.connect(self.get_db_path()) as db:
                async with db.execute(
                    """
                    SELECT item_id, quantity
                    FROM inventory
                    WHERE user_id = ?
                      AND quantity > 0
                    """,
                    (interaction.user.id,)
                ) as cursor:
                    quantities = {
                        item_id: quantity
                        for item_id, quantity in await cursor.fetchall()
                    }
        except Exception:
            # If the inventory database cannot be read, do not expose the
            # global item catalog. Returning no choices is safer and avoids
            # suggesting items the user may not own.
            return []

        choices = []
        for item_id, quantity in quantities.items():
            if item_id not in usable_items:
                continue

            info = ITEM_REGISTRY.get(item_id)
            if not info:
                continue

            display_name = info["name"]
            search_text = f"{display_name} {item_id}".lower()
            if current and current not in search_text:
                continue

            choices.append(
                app_commands.Choice(
                    name=f"{get_use_autocomplete_emoji(item_id, info.get('emoji'))} {display_name} (x{quantity})",
                    value=item_id
                )
            )

        choices.sort(key=lambda choice: choice.name.lower())
        return choices[:25]

    @commands.hybrid_command(name="use", description="Use a consumable from your inventory.")
    @app_commands.rename(item_id="item")
    @app_commands.describe(item_id="Choose an item from your inventory.")
    @app_commands.autocomplete(item_id=use_item_autocomplete)
    async def use_item(self, ctx: commands.Context, item_id: str):
        await ctx.defer()

        user_id = ctx.author.id

        # Reuse Exploration's per-user lock so /use, /mine, and /scavenge
        # cannot modify the same user's state simultaneously.
        exploration_cog = self.bot.get_cog("Exploration")

        if exploration_cog is not None:
            lock = exploration_cog._user_locks.setdefault(user_id, asyncio.Lock())
        else:
            if not hasattr(self, "_user_locks"):
                self._user_locks = {}
            lock = self._user_locks.setdefault(user_id, asyncio.Lock())

        try:
            async with lock:
                return await self._use_item_impl(ctx, item_id)
        except Exception:
            # Keep /use from silently timing out if an unexpected item/database
            # error occurs. The traceback still goes to the bot's error logger.
            import logging
            logging.getLogger(__name__).exception("Error while using item")
            return await ctx.send(
                "❌ Something went wrong while using that item. Please try again."
            )


    async def _use_halloween_special_item_impl(self, db, user_id, item_id, item_row, user):
        """Handle one-time Halloween collectible effects inside the active DB transaction."""
        config = HALLOWEEN_SPECIAL_USE_ITEMS.get(item_id)
        if not isinstance(config, dict) or not config.get("enabled"):
            return None

        # A collectible effect is permanently one-use per user. This is
        # deliberately separate from inventory quantity: finding another copy
        # later does not reset the used state.
        await db.execute("""
            CREATE TABLE IF NOT EXISTS used_collectibles (
                user_id INTEGER NOT NULL,
                collectible_id TEXT NOT NULL,
                used_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, collectible_id)
            )
        """)

        async with db.execute(
            "SELECT 1 FROM used_collectibles WHERE user_id = ? AND collectible_id = ?",
            (user_id, item_id),
        ) as cursor:
            already_used = await cursor.fetchone()

        if already_used:
            return {
                "success": False,
                "message": config.get(
                    "already_used_message",
                    "🚫 This item has already been used.",
                ),
            }

        hp = user[0] or 0
        max_hp = user[1] or 100
        effect_note = ""
        knockout_message = config.get("knockout_message")
        knocked_out_until = ""

        exploration_cog = self.bot.get_cog("Exploration")
        if exploration_cog is not None:
            game_date = exploration_cog.game_date()
        else:
            game_date = datetime.now(pytz.timezone("US/Eastern")).date()

        def set_knockout():
            nonlocal knocked_out_until
            knocked_out_until = (game_date + timedelta(days=1)).isoformat()

        async def apply_damage(amount):
            """Apply fixed damage and use the normal exploration knockout state."""
            nonlocal hp, effect_note
            amount = max(0, int(amount))

            if hp <= 0:
                return

            hp = max(0, hp - amount)
            await db.execute(
                """
                UPDATE users
                SET hp = ?, knocked_out_until = ?
                WHERE user_id = ?
                """,
                (hp, knocked_out_until, user_id),
            )

            if hp <= 0:
                set_knockout()
                await db.execute(
                    """
                    UPDATE users
                    SET hp = 0, knocked_out_until = ?
                    WHERE user_id = ?
                    """,
                    (knocked_out_until, user_id),
                )
                if knockout_message:
                    effect_note = f"\\n\\n💀 {knockout_message}"
                else:
                    effect_note = (
                        f"\\n\\n💀 **You've been knocked unconscious.**"
                        f"\\nYou lost **{amount:,} HP**."
                    )
            else:
                effect_note = (
                    f"\\n\\n❤️ **-{amount} HP**"
                    f"\\nCurrent Health: **{hp}/{max_hp} HP**"
                )

        if hp <= 0:
            return {
                "success": False,
                "message": (
                    "💀 You're already unconscious. You can't use this "
                    "collectible until you've recovered."
                ),
            }

        # -------------------------------------------------------------------
        # Explicit item effects. Keep these branches boring and obvious:
        # the config contains the story, while the handler contains gameplay.
        # -------------------------------------------------------------------
        if item_id == "wine_cabinet":
            set_knockout()
            await db.execute(
                """
                UPDATE users
                SET hp = 0, knocked_out_until = ?
                WHERE user_id = ?
                """,
                (knocked_out_until, user_id),
            )

            # The cabinet is supposed to leave the player unconscious but
            # immediately provide a free full revival item.
            await db.execute(
                """
                INSERT INTO inventory (user_id, item_id, item_type, quantity)
                VALUES (?, 'full_revive', 'Healing', 1)
                ON CONFLICT(user_id, item_id)
                DO UPDATE SET quantity = MIN(quantity + 1, 10)
                """,
                (user_id,),
            )
            effect_note = (
                f"\\n\\n💀 {config.get('knockout_message', 'You have been knocked unconscious.')}"
                f"\\n🎁 **A free Emergency Full Revival was added to your inventory.**"
            )

        elif item_id == "glitched_cartridge":
            await apply_damage(15)

        elif item_id == "smile_photo":
            pass

        elif item_id == "red_pokeball":
            pass

        elif item_id == "hazmat_suit":
            await apply_damage(35)

        elif item_id == "twigs_bundle":
            # No gameplay effect has been specified in the current config.
            pass

        elif item_id == "glow_chalk":
            pass

        elif item_id == "ouija_board":
            await apply_damage(20)

        elif item_id == "marker":
            await apply_damage(10)

        elif item_id == "tails_doll":
            await apply_damage(25)

        elif item_id == "hacked_phone":
            pass

        else:
            return {
                "success": False,
                "message": "⚠️ This Halloween item has not had its effect implemented yet.",
            }

        # Permanently record the one-time use before the transaction commits.
        await db.execute(
            "INSERT INTO used_collectibles (user_id, collectible_id) VALUES (?, ?)",
            (user_id, item_id),
        )

        return {
            "success": True,
            "message": config.get("use_message", "You used the item.") + effect_note,
            "achievement_id": config.get("achievement_id"),
            "title_id": config.get("title_id"),
            "background_id": config.get("background_id"),
            "knocked_out_until": knocked_out_until,
            "consume": True,
        }

    async def _use_item_impl(self, ctx: commands.Context, item_id: str):
        user_id = ctx.author.id
        item_id = item_id.lower().strip()

        valid = {
            "fuel_refill",
            "laser_charge_cell",
            "laser_power_cell",
            "drone_battery",
            "drone_power_cell",
            "drone_quantum_battery",
            "fuel_stabilizer",
            "station_rations",
            "hazard_shield",
            "lucky_scanner",
            "ore_magnet",
            "prototype_drill_bit",
            "cosmic_insurance",
            "fate_anchor",
            "quantum_battery",
            *[item_id for item_id, config in HALLOWEEN_SPECIAL_USE_ITEMS.items() if config.get("enabled")],
            *HAUNTED_CRAFTED_USE_ITEMS.keys(),
        }

        if item_id not in valid:
            return await ctx.send(
                "❌ That item cannot be used here. Use `/revive` for an Emergency Revival Kit."
            )

        item_info = ITEM_REGISTRY.get(item_id, {})
        is_halloween_item = (
            item_id in HALLOWEEN_SPECIAL_USE_ITEMS
            or item_id in HAUNTED_CRAFTED_USE_ITEMS
            or item_info.get("type") == "Haunted Potion"
        )
        if is_halloween_item and not is_halloween_channel(ctx.channel):
            return await ctx.send(halloween_channel_message())

        async with aiosqlite.connect(self.get_db_path()) as db:
            await self.ensure_effect_schema(db)
            await db.execute("BEGIN IMMEDIATE")

            async with db.execute(
                """
                SELECT quantity
                FROM inventory
                WHERE user_id = ? AND item_id = ?
                """,
                (user_id, item_id)
            ) as cursor:
                row = await cursor.fetchone()

            if not row or (row[0] or 0) <= 0:
                item_info = ITEM_REGISTRY.get(item_id)

                if item_info:
                    item_name = item_info["name"]
                    item_emoji = item_info.get("emoji", "📦")
                    item_display = f"{item_emoji} **{item_name}**"
                else:
                    item_display = f"`{item_id}`"

                return await ctx.send(
                    f"❌ You do not have {item_display} in your inventory."
                )

            async with db.execute(
                """
                SELECT hp, max_hp, mining_charges, scavenge_charges,
                       last_mined, last_scavenged, active_effects
                FROM users
                WHERE user_id = ?
                """,
                (user_id,)
            ) as cursor:
                user = await cursor.fetchone()

            if not user:
                return await ctx.send(
                    "❌ Profile not found! Explore Enceladus first."
                )

            hp, max_hp, mining, scavenging, last_mined, last_scavenged, effects_raw = user
            effects = json.loads(effects_raw or "{}")

            # Seasonal Workshop/Ritual items use the same persistent active-effect
            # system as the normal consumables, but their effects are consumed by
            # Haunted Exploration rather than Mine/Scavenge.
            if item_id in HAUNTED_CRAFTED_USE_ITEMS:
                config = HAUNTED_CRAFTED_USE_ITEMS[item_id]
                effect_key = config["effect"]
                if effects.get(effect_key):
                    return await ctx.send(
                        f"⚠️ **{config['name']}** is already prepared. Start a Haunted run first."
                    )

                effects[effect_key] = True
                await db.execute(
                    "UPDATE users SET active_effects = ? WHERE user_id = ?",
                    (json.dumps(effects), user_id),
                )
                if row[0] > 1:
                    await db.execute(
                        "UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_id = ?",
                        (user_id, item_id),
                    )
                else:
                    await db.execute(
                        "DELETE FROM inventory WHERE user_id = ? AND item_id = ?",
                        (user_id, item_id),
                    )

                await db.commit()
                return await ctx.send(
                    f"{ctx.author.mention} {config['message']}"
                )

            # Haunted Cauldron potions are registered by cauldron.py into the
            # shared ITEM_REGISTRY.  Their effect metadata lives on the registry
            # entry so inventory.py does not need to import cauldron.py (which
            # would create a circular import).
            potion_info = ITEM_REGISTRY.get(item_id, {})
            potion_effect = potion_info.get("haunted_effect")
            if potion_info.get("type") == "Haunted Potion" and isinstance(potion_effect, dict):
                effect_type = str(potion_effect.get("type") or "")
                amount = int(potion_effect.get("amount", 1) or 1)

                if effect_type == "sanity_restore":
                    # Calming/Restorative potions apply immediately.  Refresh
                    # continuous Sanity regeneration first, then add the potion
                    # amount and cap at 100.  The small schema bootstrap keeps
                    # the potion usable even before the user has entered Haunted
                    # Exploration for the first time.
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
                    now = time.time()
                    async with db.execute(
                        "SELECT sanity, sanity_updated_at FROM haunted_profiles WHERE user_id = ?",
                        (user_id,),
                    ) as cursor:
                        sanity_row = await cursor.fetchone()

                    if sanity_row:
                        current_sanity = max(0.0, min(100.0, float(sanity_row[0])))
                        updated_at = float(sanity_row[1] or now)
                        elapsed = max(0.0, now - updated_at)
                        current_sanity = min(100.0, current_sanity + elapsed * 100.0 / (6 * 60 * 60))
                    else:
                        current_sanity = 100.0

                    restored = max(0.0, min(100.0, current_sanity + float(amount)) - current_sanity)
                    new_sanity = min(100.0, current_sanity + float(amount))

                    if sanity_row:
                        await db.execute(
                            "UPDATE haunted_profiles SET sanity = ?, sanity_updated_at = ? WHERE user_id = ?",
                            (new_sanity, now, user_id),
                        )
                    else:
                        await db.execute(
                            """
                            INSERT INTO haunted_profiles
                                (user_id, sanity, sanity_updated_at, haunted_attempts, attempts_date)
                            VALUES (?, ?, ?, 20, '')
                            """,
                            (user_id, new_sanity, now),
                        )

                    if row[0] > 1:
                        await db.execute(
                            "UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_id = ?",
                            (user_id, item_id),
                        )
                    else:
                        await db.execute(
                            "DELETE FROM inventory WHERE user_id = ? AND item_id = ?",
                            (user_id, item_id),
                        )

                    await db.commit()
                    return await ctx.send(
                        f"{ctx.author.mention} {potion_info['emoji']} **{potion_info['name']} consumed!**\n"
                        f"🧠 Restored **+{restored:.0f} Sanity** — now at **{new_sanity:.0f}/100**."
                    )

                effect_keys = {
                    "run_protection": "haunted_potion_run_protection",
                    "encounter_insight": "haunted_potion_encounter_insight",
                    "rare_encounter_bias": "haunted_potion_rare_encounter_bias",
                    "sanity_guard": "haunted_potion_sanity_guard",
                    "curse_protection": "haunted_potion_curse_protection",
                }
                effect_key = effect_keys.get(effect_type)
                if effect_key:
                    if effects.get(effect_key):
                        return await ctx.send(
                            f"⚠️ **{potion_info['name']}** is already prepared. Start a Haunted run first."
                        )

                    effects[effect_key] = amount
                    await db.execute(
                        "UPDATE users SET active_effects = ? WHERE user_id = ?",
                        (json.dumps(effects), user_id),
                    )
                    if row[0] > 1:
                        await db.execute(
                            "UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_id = ?",
                            (user_id, item_id),
                        )
                    else:
                        await db.execute(
                            "DELETE FROM inventory WHERE user_id = ? AND item_id = ?",
                            (user_id, item_id),
                        )

                    await db.commit()
                    effect_messages = {
                        "run_protection": "🛡️ Its protection will apply to your next Haunted run.",
                        "encounter_insight": "👁️ Your perception will be sharpened during your next Haunted run.",
                        "rare_encounter_bias": "🎃 Strange encounters should be easier to notice on your next Haunted run.",
                        "sanity_guard": "🧠 Its ward will soften supernatural Sanity loss on your next Haunted run.",
                        "curse_protection": "🛡️ It will block the first negative Sanity choice of your next Haunted run.",
                    }
                    return await ctx.send(
                        f"{ctx.author.mention} {potion_info['emoji']} **{potion_info['name']} prepared!**\n"
                        f"{effect_messages.get(effect_type, 'Its effect is ready for your next Haunted run.')}"
                    )

            # Halloween Space Junk effects are handled separately from the normal
            # consumable/effect system because their use can be permanently one-time.
            if item_id in HALLOWEEN_SPECIAL_USE_ITEMS:
                special_result = await self._use_halloween_special_item_impl(
                    db, user_id, item_id, row, user
                )
                if special_result is not None:
                    if not special_result.get("success"):
                        return await ctx.send(special_result["message"])

                    # The physical collectible is consumed in this same transaction.
                    if row[0] > 1:
                        await db.execute(
                            "UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_id = ?",
                            (user_id, item_id),
                        )
                    else:
                        await db.execute(
                            "DELETE FROM inventory WHERE user_id = ? AND item_id = ?",
                            (user_id, item_id),
                        )

                    # Grant the permanent achievement/title using the same transaction.
                    achievement_cog = self.bot.get_cog("Achievements")
                    achievement_unlocked = False
                    if achievement_cog and special_result.get("achievement_id"):
                        achievement_unlocked = await achievement_cog.unlock_special_item_achievement(
                            user_id=user_id,
                            achievement_id=special_result["achievement_id"],
                            title_id=special_result.get("title_id"),
                            db=db,
                        )

                    # Some special collectibles reward a profile background
                    # instead of a title. Store it directly in the user's
                    # permanent unlocked-background list.
                    background_unlocked = False
                    background_id = special_result.get("background_id")
                    if background_id:
                        async with db.execute(
                            "SELECT unlocked_backgrounds FROM users WHERE user_id = ?",
                            (user_id,),
                        ) as cursor:
                            background_row = await cursor.fetchone()

                        try:
                            unlocked_backgrounds = json.loads(
                                background_row[0]
                                if background_row and background_row[0]
                                else '["default"]'
                            )
                            if not isinstance(unlocked_backgrounds, list):
                                unlocked_backgrounds = ["default"]
                        except (TypeError, ValueError):
                            unlocked_backgrounds = ["default"]

                        if "default" not in unlocked_backgrounds:
                            unlocked_backgrounds.insert(0, "default")

                        if background_id not in unlocked_backgrounds:
                            unlocked_backgrounds.append(background_id)
                            await db.execute(
                                "UPDATE users SET unlocked_backgrounds = ? WHERE user_id = ?",
                                (json.dumps(unlocked_backgrounds), user_id),
                            )
                            background_unlocked = True

                    await db.commit()

                    unlock_note = ""
                    if achievement_unlocked:
                        achievement_name = special_result.get("achievement_id", "Unknown").replace(
                            "halloween_", ""
                        ).replace("_", " ").title()
                        unlock_note += (
                            f"\\n\\n🏆 **Achievement Unlocked: {achievement_name}!**"
                        )

                    title_id = special_result.get("title_id")

                    if isinstance(title_id, str):
                        title_info = ITEM_REGISTRY.get(title_id, {})
                        title_name = title_info.get(
                            "name",
                            title_id.removeprefix("title_").replace("_", " ").title(),
                        )

                        if achievement_unlocked:
                            unlock_note += (
                                f"\n🏅 **Title Unlocked: {title_name}** — "
                                f"use `/equip title` to equip it."
                            )

                    background_id = special_result.get("background_id")

                    if isinstance(background_id, str):
                        background_name = (
                            background_id.removeprefix("background_")
                            .replace("_", " ")
                            .title()
                        )

                        if background_unlocked:
                            unlock_note += (
                                f"\n🖼️ **Background Unlocked: {background_name}** — "
                                f"use `/background` to equip it."
                            )

                    return await ctx.send(
                        f"{ctx.author.mention} {special_result['message']}{unlock_note}"
                    )

            effects = json.loads(effects_raw or "{}")
            message = ""

            charge_caps = await self.get_charge_caps(user_id)
            max_mining_charges = charge_caps["mining"]
            max_scavenge_charges = charge_caps["scavenging"]

            if item_id == "laser_charge_cell":
                if (mining or 0) >= max_mining_charges:
                    return await ctx.send(
                        f"⚠️ Your mining laser charges are already full (`{max_mining_charges}/{max_mining_charges}`)!"
                    )

                mining = min(max_mining_charges, (mining or 0) + 2)

                await db.execute(
                    "UPDATE users SET mining_charges = ? WHERE user_id = ?",
                    (mining, user_id)
                )

                message = f"🔋 Mining laser charges restored to **{mining}/{max_mining_charges}**."

            elif item_id == "laser_power_cell":
                if (mining or 0) >= max_mining_charges:
                    return await ctx.send(
                        f"⚠️ Your mining laser charges are already full (`{max_mining_charges}/{max_mining_charges}`)!"
                    )

                mining = min(max_mining_charges, (mining or 0) + 5)

                await db.execute(
                    "UPDATE users SET mining_charges = ? WHERE user_id = ?",
                    (mining, user_id)
                )

                message = f"⚡ Mining laser charges restored to **{mining}/{max_mining_charges}**."

            elif item_id == "fuel_refill":
                if (mining or 0) >= max_mining_charges:
                    return await ctx.send(
                        f"⚠️ Your mining laser charges are already full (`{max_mining_charges}/{max_mining_charges}`)!"
                    )

                mining = max_mining_charges

                await db.execute(
                    "UPDATE users SET mining_charges = ? WHERE user_id = ?",
                    (mining, user_id)
                )

                message = f"🌌 Mining laser fully recharged to **{max_mining_charges}/{max_mining_charges}**."

            elif item_id == "drone_battery":
                if (scavenging or 0) >= max_scavenge_charges:
                    return await ctx.send(
                        f"⚠️ Your scavenge drone charges are already full (`{max_scavenge_charges}/{max_scavenge_charges}`)!"
                    )

                scavenging = min(max_scavenge_charges, (scavenging or 0) + 2)

                await db.execute(
                    "UPDATE users SET scavenge_charges = ? WHERE user_id = ?",
                    (scavenging, user_id)
                )

                message = f"🔋 Scavenge drone charges restored to **{scavenging}/{max_scavenge_charges}**."

            elif item_id == "drone_power_cell":
                if (scavenging or 0) >= max_scavenge_charges:
                    return await ctx.send(
                        f"⚠️ Your scavenge drone charges are already full (`{max_scavenge_charges}/{max_scavenge_charges}`)!"
                    )

                scavenging = min(max_scavenge_charges, (scavenging or 0) + 5)

                await db.execute(
                    "UPDATE users SET scavenge_charges = ? WHERE user_id = ?",
                    (scavenging, user_id)
                )

                message = f"⚡ Scavenge drone charges restored to **{scavenging}/{max_scavenge_charges}**."

            elif item_id == "drone_quantum_battery":
                if (scavenging or 0) >= max_scavenge_charges:
                    return await ctx.send(
                        f"⚠️ Your scavenge drone charges are already full (`{max_scavenge_charges}/{max_scavenge_charges}`)!"
                    )

                scavenging = max_scavenge_charges

                await db.execute(
                    "UPDATE users SET scavenge_charges = ? WHERE user_id = ?",
                    (scavenging, user_id)
                )

                message = f"🌌 Scavenge drone fully recharged to **{max_scavenge_charges}/{max_scavenge_charges}**."

            elif item_id == "station_rations":
                if (hp or 0) <= 0:
                    return await ctx.send(
                        "💀 Rations cannot revive an unconscious explorer."
                    )

                old_hp = hp or 0
                hp = min(max_hp or 100, old_hp + 15)
                restored = hp - old_hp

                if restored <= 0:
                    return await ctx.send(
                        "⚠️ Your HP is already full!"
                    )

                await db.execute(
                    "UPDATE users SET hp = ? WHERE user_id = ?",
                    (hp, user_id)
                )

                message = (
                    f"🥫 **Station Rations Used!** Restored **{restored} HP**. "
                    f"Current health: **{hp}/{max_hp or 100}**."
                )

            elif item_id == "quantum_battery":
                if effects.get("quantum_battery"):
                    return await ctx.send(
                        "⚠️ You already have a Quantum Battery active! "
                        "Use `/mine` or `/scavenge` first."
                    )

                current_mining = mining or 0
                current_scavenge = scavenging or 0
                new_mining = min(max_mining_charges, current_mining + 5)
                new_scavenge = min(max_scavenge_charges, current_scavenge + 5)
                mining_added = new_mining - current_mining
                scavenge_added = new_scavenge - current_scavenge

                effects["quantum_battery"] = True

                await db.execute(
                    "UPDATE users SET mining_charges = ?, scavenge_charges = ?, active_effects = ? WHERE user_id = ?",
                    (new_mining, new_scavenge, json.dumps(effects), user_id)
                )

                message = (
                    "⚛️ **Quantum Battery Activated!**\n"
                    f"🔫 Mining laser: **+{mining_added}** charges → **{new_mining}/{max_mining_charges}**\n"
                    f"🤖 Scavenging drone: **+{scavenge_added}** charges → **{new_scavenge}/{max_scavenge_charges}**\n"
                    "✨ Your next mining or scavenging run will produce **3x Stardust**!"
                )

            else:
                if effects.get(item_id):
                    labels = {
                        "fuel_stabilizer": "Fuel Stabilizer",
                        "hazard_shield": "Hazard Shield",
                        "lucky_scanner": "Deep-Space Scanner",
                        "ore_magnet": "Ore Magnet",
                        "prototype_drill_bit": "Prototype Drill Bit",
                        "cosmic_insurance": "Cosmic Insurance",
                        "fate_anchor": "Fate Anchor",
                    }

                    return await ctx.send(
                        f"⚠️ **{labels.get(item_id, item_id.replace('_', ' ').title())}** "
                        "is already active! Use the affected action first."
                    )

                effects[item_id] = True

                await db.execute(
                    "UPDATE users SET active_effects = ? WHERE user_id = ?",
                    (json.dumps(effects), user_id)
                )

                labels = {
                    "fuel_stabilizer": "next mining run costs no charge",
                    "hazard_shield": "next scavenging hazard is blocked",
                    "lucky_scanner": "next scavenging run has improved rare-find odds",
                    "ore_magnet": "next mining run guarantees titanium ore",
                    "prototype_drill_bit": "next mining run earns bonus Stardust",
                    "cosmic_insurance": "next knockout is prevented",
                    "fate_anchor": "next missed fortune streak is protected",
                }

                message = (
                    f"✅ **{item_id.replace('_', ' ').title()} activated:** "
                    f"your {labels[item_id]}."
                )

            # Consume exactly one item after a successful use.
            if row[0] > 1:
                await db.execute(
                    """
                    UPDATE inventory
                    SET quantity = quantity - 1
                    WHERE user_id = ? AND item_id = ?
                    """,
                    (user_id, item_id)
                )
            else:
                await db.execute(
                    """
                    DELETE FROM inventory
                    WHERE user_id = ? AND item_id = ?
                    """,
                    (user_id, item_id)
                )

            await db.commit()

        await ctx.send(f"{ctx.author.mention} {message}")

    @commands.hybrid_command(name="status", description="View your health, exploration charges, and cooldowns.")
    async def status(self, ctx: commands.Context):
        await ctx.defer()
        user_id = ctx.author.id
        now = time.time()

        async with aiosqlite.connect(self.get_db_path()) as db:
            async with db.execute(
                "SELECT hp, max_hp, mining_charges, scavenge_charges, last_mined, last_scavenged, knocked_out_until, active_effects FROM users WHERE user_id = ?",
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            return await ctx.send("❌ No station profile found yet. Run `/mine` or `/scavenge` first!")

        hp, max_hp, mining, scavenging, last_mined, last_scavenged, knocked_out_until, effects_raw = row

        # Use the same upgrade-derived capacities as /mine and /scavenge.
        # /mine and /scavenge perform the actual database reset when used.
        charge_caps = await self.get_charge_caps(user_id)
        max_mining_charges = charge_caps["mining"]
        max_scavenge_charges = charge_caps["scavenging"]
        eastern = pytz.timezone("US/Eastern")
        current_date = datetime.now(eastern).date()

        last_mined_date = (
            datetime.fromtimestamp(last_mined, tz=eastern).date()
            if last_mined
            else None
        )

        last_scavenged_date = (
            datetime.fromtimestamp(last_scavenged, tz=eastern).date()
            if last_scavenged
            else None
        )

        if last_mined_date != current_date:
            mining = max_mining_charges

        if last_scavenged_date != current_date:
            scavenging = max_scavenge_charges

        def cooldown(last_used):
            remaining = max(0, int(30 * 60 - (now - (last_used or 0))))
            if remaining == 0:
                return "Ready"

            minutes = remaining // 60
            seconds = remaining % 60
            return f"{minutes}m {seconds}s"

        embed = discord.Embed(title=f"📟 {ctx.author.display_name}'s Expedition Status", color=discord.Color.teal())
        hp_value = hp or 0
        max_hp_value = max_hp or 100

        if hp_value <= 0:
            health_status = "💀 **Unconscious**"
        else:
            health_status = "🟢 **Conscious**"

        embed.add_field(
            name="❤️ Health",
            value=f"`{hp_value}/{max_hp_value}` HP\n{health_status}",
            inline=True
        )
        embed.add_field(name="⛏️ Mining", value=f"`{mining or 0}/{max_mining_charges}` charges\n{cooldown(last_mined)}", inline=True)
        embed.add_field(name="🛠️ Scavenging", value=f"`{scavenging or 0}/{max_scavenge_charges}` charges\n{cooldown(last_scavenged)}", inline=True)
        # Haunted Sanity is only shown while the Halloween event is active.
        # Keep the Haunted import local to avoid the inventory/haunted import cycle.
        if halloween_season.is_active():
            try:
                from seasonal_updates.halloween.haunted import (
                    get_or_create_profile,
                    sanity_percent,
                )

                async with aiosqlite.connect(self.get_db_path()) as haunted_db:
                    haunted_profile = await get_or_create_profile(
                        haunted_db,
                        user_id,
                    )
                    sanity_value = sanity_percent(haunted_profile["sanity"])

                sanity_label = (
                    "💀 **Critical**"
                    if sanity_value <= 25
                    else "🟡 **Unsteady**"
                    if sanity_value <= 50
                    else "🟢 **Stable**"
                )
                embed.add_field(
                    name="🧠 Sanity",
                    value=f"`{sanity_value}/100`\n{sanity_label}",
                    inline=True,
                )
            except Exception:
                pass

        if (hp or 0) <= 0:
            recovery_date = knocked_out_until or "revived"

            embed.add_field(
                name="💀 Recovery",
                value=(
                    f"Unconscious until `{recovery_date}`\n"
                    f"💉 Use `/revive` to check your available revival options."
                ),
                inline=False
            )
        effects = json.loads(effects_raw or "{}")

        # Defense equipment is stored in active_effects, but it is actual
        # equipment rather than a temporary effect. Resolve it through the
        # defense system so /status shows the real weapon name and chance.
        from defense import get_defense_info, DEFENSE_WEAPONS, DEFENSE_CAP

        async with aiosqlite.connect(self.get_db_path()) as defense_db:
            weapon_id, weapon_chance, pet_chance, combined_defense = await get_defense_info(
                defense_db, user_id
            )

        if weapon_id:
            weapon = DEFENSE_WEAPONS[weapon_id]
            defense_value = (
                f"{weapon['emoji']} **{weapon['name']}**"
                + chr(10)
                + f"🛡️ Weapon Protection: **{weapon_chance * 100:.1f}%**"
                + chr(10)
                + f"🛡️ Combined Defense: **{combined_defense * 100:.1f}%** "
                + f"(cap {DEFENSE_CAP * 100:.0f}%)"
            )
        else:
            defense_value = (
                "None equipped"
                + chr(10)
                + f"🛡️ Combined Defense: **{combined_defense * 100:.1f}%** "
                + f"(cap {DEFENSE_CAP * 100:.0f}%)"
            )

        embed.add_field(
            name="🛡️ Defense",
            value=defense_value,
            inline=False,
        )

        # defense_weapon is equipment state, not a generic active effect.
        other_effects = {
            name: value
            for name, value in effects.items()
            if name != "defense_weapon"
        }
        if other_effects:
            embed.add_field(
                name="✨ Active Effects",
                value=chr(10).join(
                    f"• {name.replace('_', ' ').title()}" for name in other_effects
                ),
                inline=False,
            )

        embed.set_footer(text="Use /inventory for items, /shop rotating for today's offers, and /revive if unconscious.")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Inventory(bot))
