import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiosqlite
import asyncio
import time
import random
import json
from datetime import datetime, timedelta
import pytz
from emojis import EMOJIS
from inventory import add_inventory_item, ITEM_REGISTRY, HALLOWEEN_SPECIAL_USE_ITEMS
from collectibles import record_collectible
from seasonal_updates.halloween.halloween import (
    MINING_CANDY_CHANCE as HALLOWEEN_MINING_CANDY_CHANCE,
    SCAVENGING_CANDY_CHANCE as HALLOWEEN_SCAVENGING_CANDY_CHANCE,
    PLASTIC_CHANCE as HALLOWEEN_PLASTIC_CHANCE,
    TRICK_OR_TREAT_BAG_CHANCE as HALLOWEEN_BAG_CHANCE,
    PLASTIC_MIN as HALLOWEEN_PLASTIC_MIN,
    PLASTIC_MAX as HALLOWEEN_PLASTIC_MAX,
    HALLOWEEN_DAMAGE_MESSAGES,
    HALLOWEEN_KNOCKOUT_LINES,
    is_active as halloween_is_active,
    HALLOWEEN_PET_EGG_CHANCE,
    GLITCHED_PET_EGG_CHANCE,
    HALLOWEEN_PET_CANDY_CHANCE,
    HALLOWEEN_SPACE_JUNK,
    halloween_channel_message,
    is_halloween_channel,
)
from error_handler import log_caught_error, log_task_error
from pets import (
    add_pet_xp,
    get_active_pet_effects,
    get_pet_passive_message,
    get_haunted_exploration_pet_xp,
    grant_haunted_pet,
    NORMAL_EGG_CHANCE,
    roll_normal_exploration_pet_xp,
)
from pets.variants import MINING_ESSENCE_CHANCE
from defense import roll_hazard_defense
from seasonal_updates.halloween.haunted import (
    HAUNTED_DAILY_ATTEMPTS,
    HAUNTED_LOCATIONS,
    SANITY_MAX,
    clear_run,
    consume_attempt,
    get_active_run,
    get_or_create_profile,
    is_insane,
    sanity_percent,
    start_run,
    update_sanity,
    grant_haunted_completion_rewards,
)
from seasonal_updates.halloween.haunted_system import advance_story, render_scene, resolve_choice

COOLDOWN_ALERT_CHANNEL_ID = 1548034265508356166

# Halloween Space Junk collectibles can very rarely be found while scavenging.
# This is intentionally much rarer than the normal Haunted Exploration
# collectible discovery chance.
SCAVENGE_HALLOWEEN_COLLECTIBLE_CHANCE = 0.040

MINING_MATERIALS = [
    ("iron_ore", "Iron Ore", 0.22),
    ("copper_ore", "Copper Ore", 0.12),
    ("titanium_chunk", "Titanium Ore Chunk", 0.04),
    ("aluminum_ore", "Aluminum Ore", 0.16),
]
SCAVENGE_MATERIALS = [
    ("circuit_board", "Circuit Board", 0.12),
    ("glue", "Industrial Glue", 0.18),
    ("scrap_metal", "Scrap Metal", 0.29),
    ("nuts_bolts", "Nuts & Bolts", 0.20),
    ("wiring", "Wiring", 0.24),
    # Incubator materials are uncommon salvage finds and use the same
    # independent material-roll system as the normal scavenging materials.
    ("quantum_coil", "Quantum Coil", 0.05),
    ("astral_lens", "Astral Lens", 0.05),
    ("mutation_catalyst", "Mutation Catalyst", 0.05),
    ("analysis_module", "Analysis Module", 0.05),
]
SCAVENGE_MEDICAL_SUPPLIES = [
    ("gauze", "Sterile Gauze", 0.20),
    ("medical_alcohol", "Medical Alcohol", 0.17),
    ("bandaids", "Bandaids", 0.15),
    ("antiseptic_ointment", "Antiseptic Ointment", 0.12),
]
SCAVENGE_BONUS_MINERALS = [
    ("iron_ore", "Iron Ore", 0.035),
    ("copper_ore", "Copper Ore", 0.020),
    ("aluminum_ore", "Aluminum Ore", 0.015),
    ("titanium_chunk", "Titanium Ore Chunk", 0.007),
]

MATERIAL_OVERFLOW_VALUES = {
    "iron_ore": 3,
    "copper_ore": 5,
    "aluminum_ore": 4,
    "titanium_chunk": 15,
    "scrap_metal": 3,
    "nuts_bolts": 4,
    "wiring": 5,
    "glue": 6,
    "circuit_board": 20,
    "quantum_coil": 2500,
    "astral_lens": 3125,
    "mutation_catalyst": 3750,
    "analysis_module": 1875,
}

LOOT_OVERFLOW_VALUES = {
    "titanium_chunk": 75, "arcade_token": 50, "time_crystal": 350, "astral_core": 750,
    "gauze": 5, "medical_alcohol": 5, "bandaids": 5, "antiseptic_ointment": 5,
    "quantum_battery": 800, "revive_kit": 200, "laser_charge_cell": 50, "drone_battery": 50,
    "space_pizza": 10, "floppy_disk": 10, "meteorite": 10, "rubber_duck": 10, "rusty_gear": 10,
    "tape_deck": 10, "alien_artifact": 10, "space_boot": 10, "cosmic_coin": 10, "holo_poster": 10,
    "broken_laser": 10, "lost_logbook": 10, "left_sock": 10, "warp_mug": 10, "space_pudding": 10,
    "tangled_cables": 10, "screaming_crystal": 10, "moon_cheese": 10, "golden_spatula": 60,
    "parking_ticket": 10, "floating_plant": 10, "tinted_visor": 10, "purring_lint": 10, "pet_rock": 10,
    "haunted_circuit": 10, "space_taco": 10, "rusty_wrench": 10, "alien_fossil": 10, "big_red_button": 10,
    "antique_compass": 10, "broken_clock": 10, "perplexing_painting": 10, "cosmic_banana": 10,
}


SCAVENGE_STARDUST_CACHE_CHANCE = 0.04
SCAVENGE_STARDUST_CACHE_MIN = 500
SCAVENGE_STARDUST_CACHE_MAX = 2500


# ============================================================================
# EXPLORATION TEXT
# ============================================================================
# This is the main editing area for user-facing Exploration text.
#
# The sections below cover the text presented by the Haunted Exploration,
# Mining, Scavenging, and Revival embeds, plus the reusable messages that feed
# those embeds. Dynamic values use {placeholders}; the code supplies those
# values when the message is displayed.
#
# Haunted story scene text and choice labels are intentionally NOT duplicated
# here. Those are authored in seasonal_updates/halloween/haunted_system.py so
# there is still one source of truth for the actual story.
#
# Mechanics, rewards, database behavior, and calculations remain below. You
# should normally only need to edit this section when changing wording.
# ============================================================================

EXPLORATION_SEPARATOR = "────────────────────────────"

EXPLORATION_TEXT = {
    "common": {
        "separator": EXPLORATION_SEPARATOR,
        "knockout_message": (
            "*You are unconscious!*\n\nYou can use `/revive` or use `/shop buy` "
            "and find a revive item. Otherwise, you will recover "
            "with 50HP at **{knocked_out_until}**"
        ),
        "cooldown_finished": (
            "<@{user_id}> **Your cooldown has ended!**\n"
            "You can now use `/{command}` again!"
        ),
        "daily_reminder": "*You didn't claim your daily yet!*\nUse `/daily` to claim your Stardust reward!",
    },
    "haunted": {
        "location_title": "*Lair of Frights - Haunted Exploration 👻*",
        "location_description": (
            "Enceladus opened a series of portals while searching for new places to explore for Halloween. "
            "Something came back through one of them. Whatever happened next left the portals - and Enceladus himself - changed.\n\n────────────────────────────\n\n"
            "The destinations beyond these portals are waiting. Choose one below and step through. "
            "Each location is a coherent multi-scene story with meaningful choices, secrets, and dangers."
        ),
        "active_run_note": (
            "\n\nYou currently have an active run in **{location_name}** "
            "(Stage {stage}/{total_stages}). Starting another run will replace it."
        ),
        "location_footer": "Choose a portal location to enter. | Lair of Frights 👻",
        "field_explorer": "*Explorer*",
        "field_sanity": "*Sanity*",
        "field_daily_attempts": "*Daily Attempts*",
        "sanity_field": "**{sanity}/100**\n{state}\nRegenerates continuously over time.",
        "info_title": "Haunted Exploration — Field Guide",
        "info_description": (
            "Haunted Exploration is a multi-stage Halloween adventure built around a series of portals opened by "
            "Enceladus. Each portal leads somewhere new - and not everything that comes through them is supposed to be there."
        ),
        "info_portals": (
            "Enceladus went searching for new locations for Halloween. While using portals to find new areas, "
            "**something came back through one of them.** It attacked. He tried to fight back... but to no avail."
        ),
        "info_corruption": (
            "Whatever came through the portal entered Enceladus's system, past his coding, and **corrupted him**. "
            "He comes and goes, sometimes able to fight through it—almost like he is possessed, but digitally. "
            "There is nothing we can do... **for now.**"
        ),
        "info_sometimes": (
            "There are moments when the corruption pushes through. Enceladus is not entirely himself. "
            "And sometimes... *something else comes out.*"
        ),
        "info_sanity": (
            "Sanity starts at **100** and regenerates continuously. Most choices reduce it. "
            "At **0 Sanity**, you enter **Insane** state."
        ),
        "info_grip": (
            "Low Sanity makes reality less reliable. The same story can be perceived differently, and at **0 Sanity** "
            "the opening perception can become profoundly wrong. Insanity does not randomly replace the story with unrelated encounters."
            "However, low Sanity or Insanity can cause better reward drops."
        ),
        "info_attempts": (
            "You get **{attempts} attempts per day**. Starting an adventure consumes one attempt, even if you run away. "
            "The daily reset is 12:00AM EST."
        ),
        "info_stages": (
            "Runs are authored multi-scene adventures. Your choices can show different discoveries, pet opportunities, and various story reactions."
        ),
        "info_running_away": (
            "You can run away instead of taking an encounter choice. Most escapes work, but there is a small "
            "chance that something happens while you escape. Running away stops you from earning rewards for that run, but you can always try again."
        ),
        "scene_title": "*{location_name} {emoji}*",
        "scene_result_prefix": "**What happened:**\n{result_text}\n\n" + EXPLORATION_SEPARATOR + "\n\n",
        "scene_explorer": "*Explorer*",
        "scene_scene": "*Scene*",
        "scene_sanity": "*Sanity*",
        "scene_sanity_insane": "***INSANITY***",
        "scene_sanity_unreliable": "***Reality is becoming unreliable...***",
        "scene_sanity_stable": "***Stable***",
        "malo_warning": "MalO is staring at **{choice}**.\n*You are not entirely sure why.*",
        "scene_footer": "Choose carefully. Or run.",
        "wrong_owner": (
            "**This Haunted Exploration isn't yours.**\n"
            "These buttons belong to another player's exploration run. You can start your own run with `/explore: haunted`!"
        ),
        "scene_unavailable": (
            "**This Haunted Exploration scene is no longer available.**\n"
            "The scene may have expired or already been advanced. Start a new Haunted Exploration run if needed."
        ),
        "run_unavailable": (
            "**This Haunted Exploration is no longer available.**\n"
            "The run may have expired or already been ended. Start a new Haunted Exploration run if needed."
        ),
        "dormant_short": "*Haunted Exploration is currently dormant until October. Please check back next Halloween!*",
        "dormant_long": (
            "**Haunted Exploration is currently dormant.**\n"
            "This event is only available during the Lair of Frights event in October. Please check back next Halloween!"
        ),
        "out_of_attempts": (
            "**You're out of Haunted Exploration attempts for today!**\n"
            "Come back after the daily reset at 12:00 AM EST!"
        ),
        "pet_already_found": (
            "**Something familiar appears**\n"
            "You recognize this companion. You've already befriended it, "
            "and it disappears back into the darkness, waiting for another to find it."
        ),
        "completion_description": (
            "**{mention} explored {location_name}.**\n\n"
            "**What happened**\n{result_text}\n\n"
            + EXPLORATION_SEPARATOR + "\n\n"
            "**Exploration complete**\n"
            "You've made it through! 🎉"
        ),
        "completion_explorer": "*Explorer*",
        "completion_story": "*Story*",
        "completion_sanity": "*Final Sanity*",
        "completion_rewards": "*Adventure rewards*\n────────────────────────────\n",
        "completion_pet": "**Location-based pet found!**",
        "completion_footer": "Exploration complete • The portals remain open for now...",
        "escape_rare": [
            "You bolt for the exit. The door slams shut behind you by itself. Something follows you for three steps before disappearing.",
            "You run. Your footsteps keep going after you stop. You decide not to investigate.",
            "You make it out—then realize the hallway outside has one extra door. You do not go back.",
        ],
        "escape_normal": [
            "You decide you've had enough and make a very respectable tactical retreat.",
            "Nope. Absolutely not. You turn around and leave.",
            "You retreat before whatever is lurking here gets the chance to introduce itself.",
        ],
        "escape_suffix": "\n\n**Something happened while you escaped...**",
        "escape_description": "**{mention} left the {location_name}.**\n\n{escape_text}{suffix}",
        "escape_explorer": "*Explorer*",
        "escape_run_ended": "*Run Ended*",
        "escape_sanity": "*Sanity*",
        "escape_rewards": "*Rewards*",
        "escape_no_reward": "No reward was earned from this run.",
        "escape_footer": "You've escaped. The portals remain open for now...",
        "reward_stardust": "**+{amount:,} Stardust** ✨",
        "reward_candy": "**+{amount} Halloween Candy** 🍬",
        "reward_ingredient": "{emoji} **+{amount} {name}**",
        "reward_pet_xp": "**+{amount} Pet XP** 🐾",
        "reward_pet_home_bonus": " *(+{amount} home-location bonus)*",
        "reward_pet_level": " • **Pet Level {level}!** 🎉",
        "reward_candy_overflow": "Candy overflow: **{amount}** → **+{stardust} Stardust**",
        "reward_ingredient_overflow": "Ingredient overflow: **{amount}** → **+{stardust} Stardust**",
        "reward_collectible": "**Halloween collectible found! {emoji} {name}** \n" + EXPLORATION_SEPARATOR + "\n*{description}*",
        "reward_usable_collectible": "**Usable collectible found!**\nUse `/use item: [item name]` to activate this collectible.",
    },
    "mining": {
        "title": "*Starship Mining Log - {display_name}* 🚀",
        "description": (
            "*Your laser beam fired into the debris field...*\n\n"
            + EXPLORATION_SEPARATOR + "\n\n"
            "Stardust collected: **{stardust:,}**{stardust_notes}"
            "{result_sections}"
        ),
        "footer": "Fuel charges remaining: {charges}/{max_charges} • Cooldown: {cooldown}",
        "pet_progress": "Companion progress",
        "pet_xp": "Pet XP: **+{xp}XP**",
        "pet_level": " • **Level {level}!** 🎉",
        "daily_name": "Daily reminder!",
        "daily_value": "You didn't claim your daily yet! Use `/daily` to claim your Stardust reward!",
        "cooldown_name": "Cooldown alerts",
    },
    "scavenging": {
        "title": "*Derelict Salvage Log - {display_name}* 🔩",
        "description": (
            "*Your scavenge drone has been deployed into abandoned sector wreckage...*\n\n"
            + EXPLORATION_SEPARATOR + "\n\n"
            "Stardust found: **{stardust:,}**{quantum_note}{cache_note}"
            "\n\n" + EXPLORATION_SEPARATOR + "\n\n"
            "Salvaged items: {loot}\n"
            "{materials_and_supplies}"
            "{special_findings}"
            "{hazard_note}"
            "\n\n" + EXPLORATION_SEPARATOR + "\n\n"
            "{status}"
        ),
        "footer": "*Drone charges remaining: {charges}/{max_charges} • Cooldown: {cooldown}*",
        "pet_progress": "Companion Progress 🐾",
        "pet_xp": "Pet XP: **+{xp}XP**",
        "pet_level": " • **Level {level}!** 🎉",
        "daily_name": "Daily reminder!",
        "daily_value": "You didn't claim your daily yet! Use `/daily` to claim your Stardust reward!",
        "cooldown_name": "Cooldown alerts",
        "health_status": "Health: **{hp}/{max_hp}HP**",
        "knocked_out_status": "*Knocked out!* Use `/revive`, buy `/shop buy`, or recover at 50%HP at **{until}**.",
        "materials": "Salvaged materials: {findings}",
    },
    "revival": {
        "title": "{mention} - Revival required!",
        "description": "You are currently unconscious.\n\nChoose a revival method:",
        "no_items": (
            "You don't have any revival items.\n"
            "You can buy an **Emergency Full Revival** from `/shop buy`, other revival kits, or recover automatically at 12:00AM EST."
        ),
        "already_conscious": "*{mention} You are already conscious and do not need a revival.*",
        "profile_missing": "{mention} Profile not found!",
        "expired_footer": "This revival menu will expire in 60 seconds.",
        "revive_kit_name": "Revival Kit",
        "revive_kit_value": "Restores **35%HP**\nOwned: **{count}**",
        "emergency_kit_name": "Emergency Revival Kit",
        "emergency_kit_value": "Restores **50%HP**\nOwned: **{count}**",
        "full_revive_name": "Emergency Full Revival",
        "full_revive_value": "Restores **100%HP**\nOwned: **{count}**",
    },
}


class Exploration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._user_locks = {}
        self.COOLDOWN_SECONDS = 30 * 60  # 30-minute cooldown
        self.SCAVENGE_HAZARDS = [
            # Minor hazards are common: funny setbacks, small damage.
            ("tripped over a strategically placed wrench", 5, 7, 10),
            ("were judged by a maintenance Roomba, lost the argument", 5, 7, 10),
            ("bonked your helmet on a ceiling sign", 6, 12, 16),
            ("got lightly zapped by a broken control panel", 7, 12, 16),
            ("slipped on a patch of moon-cheese residue", 4, 9, 14),
            ("were startled by a toaster that was still active after all this time, hit your head", 5, 11, 12),
            ("got tangled in a cable that had clearly been waiting for this VERY moment", 4, 7, 10),
            ("walked into a door without looking", 2, 4, 8),
            ("were pelted with dirty air by a faulty air filter", 5, 10, 12),
            ("lost a staring contest with a Suspicious Houseplant, it bonked you in the head", 6, 10, 12),
            # Moderate hazards are the usual danger of wreckage exploration.
            ("inhaled sharp hull-debris dust", 12, 20, 14),
            ("were scraped by sharp alien metal (probably need a tetanus shot now)", 15, 25, 20),
            ("triggered an electrical spark while searching wreckage", 15, 25, 10),
            ("were chased through a corridor by an overenthusiastic security drone, ran into a wall head-first", 15, 25, 10),
            ("fell through a floor panel that looked stable... but wasn't", 12, 25, 15),
            ("caught a blast of frigid-cold life-support exhaust, nearly got frostbite", 12, 21, 12),
            ("activated a cleaning bot's 'deep clean' setting, it ran you down in the process", 14, 24, 10),
            ("were sideswiped by a runaway supply crate sliding down a staircase", 15, 25, 10),
            ("opened a locker full of spring-loaded asteroid samples", 13, 22, 10),
            ("discovered that the abandoned ship still had its security system set to hostile", 14, 23, 10),
            ("briefly became the target of an old defense turret", 16, 25, 8),
            # Severe hazards are uncommon, but should make a run feel memorable.
            ("tried to go through a reactor leak and *immediately* regretted it", 24, 35, 10),
            ("lost a wrestling match with an unsecured cargo loader", 26, 38, 4),
            ("opened a door marked 'definitely not haunted'", 25, 40, 3),
            ("were introduced to a malfunctioning gravity plate", 24, 36, 5),
            ("accidentally attended a security drone's very personal laser presentation", 25, 38, 4),
            ("found the source of the ominous humming, and *it* found you back", 27, 40, 3),
            ("triggered an escape pod launch without the escape pod, nearly sucking you out into space", 23, 35, 4),
            ("attempted to outrun a hull decompression warning", 35, 40, 15),
        ]
        self.KNOCKOUT_LINES = [
            "Station AI Report: explorer status changed to 'crispy, but recoverable.'",
            "The station medic has added your name to the 'please stop touching things' list.",
            "A nearby drone recorded the incident for training purposes.",
            "Your insurance provider has described this as 'an ambitious interpretation of safety protocol.'",
            "Enceladus Station would like to remind you that gravity is not a personal challenge.",
            "The wreckage won this round. It has been insufferable about it.",
            "Your emergency beacon activated itself out of professional concern.",
            "The Station's accident report form has auto-filled your name. *Again.*",
            "A maintenance bot placed a tiny traffic cone beside you. Respectfully, of course.",
            "The ship's computer has labeled this event: 'operator-adjacent malfunction.'",
            "A passing astronaut gave you a thumbs-up. It was not reassuring. It was actually kinda sad.",
            "Your helmet camera saved the footage under 'please_do_not_share.mp4'.",
            "The local ghost has filed a noise complaint about your landing.",
            "Station morale improved by 0.3%. The reason has been redacted.",
            "A janitorial drone swept around you and whispered, 'same, bro.'",
            "The cargo loader has requested a rematch, which feels unnecessary.",
            "A safety poster peeled off the wall right next to you as you fainted.",
            "Your distress signal was answered by hold music. *Very dramatic* hold music.",
            "The nearest vending machine dispensed a consolation pretzel.",
            "Station's Medical Bay has prepared a blanket, a juice box, and a strongly worded pamphlet, while also calling you a 'weenie.'",
            "The Station AI has awarded you the badge: 'Unscheduled Floor Inspection.'",
            "Someone has added 'avoid haunted doors' to the next crew briefing.",
            "Your future self briefly appeared, shook their head, and vanished.",
        ]

    def cog_unload(self):
        getattr(self.cooldown_alert_checker, "cancel")()

    async def cog_load(self):
        getattr(self.cooldown_alert_checker, "start")()

    def get_db_path(self):
        """Return the separate Station economy database."""
        from database import ECONOMY_DB_NAME
        return ECONOMY_DB_NAME

    async def ensure_schema(self, db):
        """Ensures scavenging and health tracking columns exist in the database."""
        async with db.execute("PRAGMA table_info(users)") as cursor:
            existing_columns = {row[1] async for row in cursor}

        if "scavenge_charges" not in existing_columns:
            await db.execute("ALTER TABLE users ADD COLUMN scavenge_charges INTEGER DEFAULT 10")
        if "last_scavenged" not in existing_columns:
            await db.execute("ALTER TABLE users ADD COLUMN last_scavenged REAL DEFAULT 0")
        if "hp" not in existing_columns:
            await db.execute("ALTER TABLE users ADD COLUMN hp INTEGER DEFAULT 100")
        if "max_hp" not in existing_columns:
            await db.execute("ALTER TABLE users ADD COLUMN max_hp INTEGER DEFAULT 100")
        if "knocked_out_until" not in existing_columns:
            await db.execute("ALTER TABLE users ADD COLUMN knocked_out_until TEXT DEFAULT ''")
        if "active_effects" not in existing_columns:
            await db.execute("ALTER TABLE users ADD COLUMN active_effects TEXT DEFAULT '{}'")
        if "mining_alert_sent" not in existing_columns:
            await db.execute("ALTER TABLE users ADD COLUMN mining_alert_sent REAL DEFAULT 0")
        if "scavenge_alert_sent" not in existing_columns:
            await db.execute("ALTER TABLE users ADD COLUMN scavenge_alert_sent REAL DEFAULT 0")
        if "cooldown_alerts" not in existing_columns:
            await db.execute("ALTER TABLE users ADD COLUMN cooldown_alerts INTEGER DEFAULT 0")
        if "daily_streak" not in existing_columns:
            await db.execute("ALTER TABLE users ADD COLUMN daily_streak INTEGER DEFAULT 0")
        if "last_daily" not in existing_columns:
            await db.execute("ALTER TABLE users ADD COLUMN last_daily TEXT DEFAULT ''")

    async def daily_unclaimed(self, user_id):
        """Return True when the user has not claimed today's daily reward."""
        today = self.game_date().isoformat()
        try:
            async with aiosqlite.connect(self.get_db_path()) as db:
                await self.ensure_schema(db)
                async with db.execute(
                    "SELECT COALESCE(last_daily, '') FROM users WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
            return not row or row[0] != today
        except Exception as e:
            await log_caught_error(self.bot, e, "Exploration daily_unclaimed")
            # A reminder should never break a successful exploration result.
            return False

    @tasks.loop(seconds=60)
    async def cooldown_alert_checker(self):
        """Check for completed mining/scavenging cooldowns and notify opted-in users."""
        try:
            channel = self.bot.get_channel(COOLDOWN_ALERT_CHANNEL_ID)
            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(COOLDOWN_ALERT_CHANNEL_ID)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    return

            if channel is None:
                return

            db_path = self.get_db_path()
            current_time = time.time()

            async with aiosqlite.connect(db_path) as db:
                await self.ensure_schema(db)

                async with db.execute(
                    """
                    SELECT
                        user_id,
                        last_mined,
                        last_scavenged,
                        mining_alert_sent,
                        scavenge_alert_sent
                    FROM users
                    WHERE cooldown_alerts = 1
                      AND (
                          last_mined > 0
                          OR last_scavenged > 0
                      )
                    """
                ) as cursor:
                    users = await cursor.fetchall()

                for (
                    user_id,
                    last_mined,
                    last_scavenged,
                    mining_alert_sent,
                    scavenge_alert_sent
                ) in users:
                    # The actual exploration cooldown can be shortened by the
                    # user's active pet, so alerts must use the same effective
                    # cooldown as /mine and /scavenge.
                    pet_effects = await get_active_pet_effects(db, user_id)
                    effective_cooldown = self.COOLDOWN_SECONDS * (
                        1 - pet_effects.get("cooldown_reduction", 0.0)
                    )

                    # Mining cooldown
                    if (
                        last_mined
                        and current_time - last_mined >= effective_cooldown
                        and mining_alert_sent != last_mined
                    ):
                        try:
                            await channel.send(
EXPLORATION_TEXT["common"]["cooldown_finished"].format(user_id=user_id, command="mine")
                            )

                            await db.execute(
                                """
                                UPDATE users
                                SET mining_alert_sent = ?
                                WHERE user_id = ?
                                """,
                                (last_mined, user_id)
                            )

                        except (discord.Forbidden, discord.HTTPException):
                            pass

                    # Scavenging cooldown
                    if (
                        last_scavenged
                        and current_time - last_scavenged >= effective_cooldown
                        and scavenge_alert_sent != last_scavenged
                    ):
                        try:
                            await channel.send(
EXPLORATION_TEXT["common"]["cooldown_finished"].format(user_id=user_id, command="scavenge")
                            )

                            await db.execute(
                                """
                                UPDATE users
                                SET scavenge_alert_sent = ?
                                WHERE user_id = ?
                                """,
                                (last_scavenged, user_id)
                            )

                        except (discord.Forbidden, discord.HTTPException):
                            pass

                await db.commit()

        except Exception as e:
            await log_task_error(self.bot, "cooldown_alert_checker (caught error)", e)
            # Never let the background task die because of one unexpected error.
            pass

    @cooldown_alert_checker.before_loop
    async def before_cooldown_alert_checker(self):
        await self.bot.wait_until_ready()

    def game_date(self):
        return datetime.now(pytz.timezone("US/Eastern")).date()

    async def recover_if_new_day(self, db, user_id):
        """Wake a knocked-out explorer at half health once their recovery day arrives."""
        async with db.execute(
            "SELECT hp, max_hp, knocked_out_until FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return False

        hp, max_hp, knocked_out_until = row
        if (hp or 0) <= 0 and knocked_out_until and self.game_date().isoformat() >= knocked_out_until:
            recovered_hp = max(1, ((max_hp or 100) + 1) // 2)
            await db.execute(
                "UPDATE users SET hp = ?, knocked_out_until = '' WHERE user_id = ?",
                (recovered_hp, user_id),
            )
            await db.commit()
            return True
        return False

    def knockout_message(self, knocked_out_until, mention=None):
        prefix = f"{mention} " if mention else ""
        return prefix + EXPLORATION_TEXT["common"]["knockout_message"].format(
            knocked_out_until=knocked_out_until
        )

    @app_commands.command(
        name="explore",
        description="Explore Enceladus' seasonal portal locations.",
    )
    @app_commands.choices(
        event=[
            app_commands.Choice(name="Haunted", value="haunted"),
        ],
        action=[
            app_commands.Choice(name="Info", value="info"),
        ],
    )
    async def explore(
        self,
        interaction: discord.Interaction,
        event: str,
        action: str | None = None,
    ):
        if event == "haunted" and action == "info":
            if not is_halloween_channel(interaction.channel):
                return await interaction.response.send_message(
                    halloween_channel_message(),
                    ephemeral=True,
                )
            if not halloween_is_active():
                return await interaction.response.send_message(
                    EXPLORATION_TEXT["haunted"]["dormant_short"],
                    ephemeral=True,
                )

            await interaction.response.send_message(
                embed=self._haunted_info_embed(),
                ephemeral=True,
            )
            return

        if event == "haunted":
            if not is_halloween_channel(interaction.channel):
                return await interaction.response.send_message(
                    halloween_channel_message(),
                    ephemeral=True,
                )
            if not halloween_is_active():
                return await interaction.response.send_message(
                    EXPLORATION_TEXT["haunted"]["dormant_long"],
                    ephemeral=True,
                )

            user_id = interaction.user.id
            lock = self._user_locks.setdefault(user_id, asyncio.Lock())
            async with lock:
                async with aiosqlite.connect(self.get_db_path()) as db:
                    await self.ensure_schema(db)
                    profile = await get_or_create_profile(db, user_id)

                embed = self._haunted_location_embed(interaction.user, profile)
                await interaction.response.send_message(
                    embed=embed,
                    view=HauntedLocationView(self, interaction.user.id),
                )

    def _haunted_location_embed(self, member, profile):
        sanity = sanity_percent(profile["sanity"])
        state = "***INSANE***" if is_insane(profile["sanity"]) else "***Stable***"
        active = profile["active_location"]

        description = EXPLORATION_TEXT["haunted"]["location_description"]
        if active in HAUNTED_LOCATIONS:
            description += EXPLORATION_TEXT["haunted"]["active_run_note"].format(
                location_name=HAUNTED_LOCATIONS[active]["name"],
                stage=profile["active_stage"],
                total_stages=profile["active_total_stages"],
            )

        embed = discord.Embed(
            title=EXPLORATION_TEXT["haunted"]["location_title"],
            description=description,
            color=discord.Color.dark_purple(),
        )
        embed.add_field(
            name=EXPLORATION_TEXT["haunted"]["field_explorer"],
            value=member.mention,
            inline=True,
        )
        embed.add_field(
            name=EXPLORATION_TEXT["haunted"]["field_sanity"],
            value=EXPLORATION_TEXT["haunted"]["sanity_field"].format(sanity=sanity, state=state),
            inline=True,
        )
        embed.add_field(
            name=EXPLORATION_TEXT["haunted"]["field_daily_attempts"],
            value=f"**{profile['attempts']}/{HAUNTED_DAILY_ATTEMPTS}**",
            inline=True,
        )
        embed.set_footer(text=EXPLORATION_TEXT["haunted"]["location_footer"])
        return embed

    def _haunted_info_embed(self):
        embed = discord.Embed(
            title=EXPLORATION_TEXT["haunted"]["info_title"],
            description=EXPLORATION_TEXT["haunted"]["info_description"],
            color=discord.Color.dark_purple(),
        )
        embed.add_field(
            name="The Portals",
            value=EXPLORATION_TEXT["haunted"]["info_portals"],
            inline=False,
        )
        embed.add_field(
            name="The Corruption",
            value=EXPLORATION_TEXT["haunted"]["info_corruption"],
            inline=False,
        )
        embed.add_field(
            name="Sometimes...",
            value=EXPLORATION_TEXT["haunted"]["info_sometimes"],
            inline=False,
        )
        embed.add_field(
            name="*Sanity*",
            value=EXPLORATION_TEXT["haunted"]["info_sanity"],
            inline=False,
        )
        embed.add_field(
            name="*Losing Your Grip*",
            value=EXPLORATION_TEXT["haunted"]["info_grip"],
            inline=False,
        )
        embed.add_field(
            name="*Attempts*",
            value=EXPLORATION_TEXT["haunted"]["info_attempts"].format(attempts=HAUNTED_DAILY_ATTEMPTS),
            inline=False,
        )
        embed.add_field(
            name="*Stages*",
            value=EXPLORATION_TEXT["haunted"]["info_stages"],
            inline=False,
        )
        embed.add_field(
            name="*Running Away*",
            value=EXPLORATION_TEXT["haunted"]["info_running_away"],
            inline=False,
        )
        return embed

    async def _start_haunted_run(self, interaction: discord.Interaction, location_id: str):
        if not halloween_is_active():
            return await interaction.followup.send(
                EXPLORATION_TEXT["haunted"]["dormant_short"],
                ephemeral=True,
            )

        user_id = interaction.user.id
        lock = self._user_locks.setdefault(user_id, asyncio.Lock())
        async with lock:
            async with aiosqlite.connect(self.get_db_path()) as db:
                await self.ensure_schema(db)
                consumed, profile = await consume_attempt(db, user_id)
                if not consumed:
                    return await interaction.followup.send(
                        EXPLORATION_TEXT["haunted"]["out_of_attempts"],
                        ephemeral=True,
                    )
                total_stages = await start_run(db, user_id, location_id, profile["sanity"])

        await self._show_haunted_stage(interaction, location_id, 1, total_stages)

    async def _show_haunted_stage(
        self,
        interaction: discord.Interaction,
        location_id: str,
        stage: int,
        total_stages: int,
        result_text: str | None = None,
    ):
        user_id = interaction.user.id
        async with aiosqlite.connect(self.get_db_path()) as db:
            await self.ensure_schema(db)
            profile = await get_or_create_profile(db, user_id)
            run = await get_active_run(db, user_id)
            if not run or run["location_id"] != location_id or run["stage"] != stage:
                return await interaction.followup.send(
                    EXPLORATION_TEXT["haunted"]["scene_unavailable"],
                    ephemeral=True,
                )

            async with db.execute("SELECT active_effects FROM users WHERE user_id = ?", (user_id,)) as cursor:
                effect_row = await cursor.fetchone()
            try:
                effects = json.loads(effect_row[0] or "{}") if effect_row else {}
                if not isinstance(effects, dict):
                    effects = {}
            except (TypeError, ValueError, json.JSONDecodeError):
                effects = {}

            scene_data = render_scene(
                location_id,
                run["current_scene"],
                run["story_state"],
                profile["sanity"],
                active_effects=effects,
            )

            malo_warning = None
            malo_warning_chance = float(effects.get("haunted_run_malo_warning_chance", 0.0))
            if malo_warning_chance and random.random() < malo_warning_chance:
                dangerous = [
                    (index, choice)
                    for index, choice in enumerate(scene_data["choices"])
                    if choice.get("risk", "medium") in {"high", "extreme"}
                ]
                if dangerous:
                    _, warned_choice = random.choice(dangerous)
                    malo_warning = warned_choice.get("label", "one of the choices")

        location = HAUNTED_LOCATIONS[location_id]
        sanity = sanity_percent(profile["sanity"])
        scene_text = scene_data["text"]
        if result_text:
            scene_text = EXPLORATION_TEXT["haunted"]["scene_result_prefix"].format(result_text=result_text) + scene_text
        if sanity <= 0:
            color = discord.Color.dark_red()
            sanity_state = EXPLORATION_TEXT["haunted"]["scene_sanity_insane"]
        elif sanity <= 25:
            color = discord.Color.dark_red()
            sanity_state = EXPLORATION_TEXT["haunted"]["scene_sanity_unreliable"]
        else:
            color = discord.Color.dark_purple()
            sanity_state = EXPLORATION_TEXT["haunted"]["scene_sanity_stable"]

        embed = discord.Embed(
            title=EXPLORATION_TEXT["haunted"]["scene_title"].format(emoji=location["emoji"], location_name=location["name"]),
            description=scene_text,
            color=color,
        )
        embed.add_field(name=EXPLORATION_TEXT["haunted"]["scene_explorer"], value=interaction.user.mention, inline=True)
        embed.add_field(name=EXPLORATION_TEXT["haunted"]["scene_scene"], value=f"**{stage}/{total_stages}**", inline=True)
        embed.add_field(name=EXPLORATION_TEXT["haunted"]["scene_sanity"], value=f"**{sanity}/100**\n{sanity_state}", inline=True)

        if malo_warning:
            embed.add_field(
                name="MalO's Warning",
                value=EXPLORATION_TEXT["haunted"]["malo_warning"].format(choice=malo_warning),
                inline=False,
            )

        embed.set_footer(text=EXPLORATION_TEXT["haunted"]["scene_footer"])
        await interaction.edit_original_response(
            content=None,
            embed=embed,
            view=HauntedStoryView(
                self,
                user_id,
                location_id,
                stage,
                total_stages,
                run["current_scene"],
            ),
        )

    async def _resolve_haunted_choice(
        self,
        interaction: discord.Interaction,
        owner_id: int,
        location_id: str,
        stage: int,
        total_stages: int,
        scene_id: str,
        choice_index: int,
    ):
        if interaction.user.id != owner_id:
            return await interaction.followup.send(
                EXPLORATION_TEXT["haunted"]["wrong_owner"],
                ephemeral=True,
            )

        user_id = interaction.user.id
        lock = self._user_locks.setdefault(user_id, asyncio.Lock())
        async with lock:
            async with aiosqlite.connect(self.get_db_path()) as db:
                await self.ensure_schema(db)
                run = await get_active_run(db, user_id)
                if (
                    not run
                    or run["location_id"] != location_id
                    or run["stage"] != stage
                    or run["current_scene"] != scene_id
                    or run["total_stages"] != total_stages
                ):
                    return await interaction.followup.send(
                        EXPLORATION_TEXT["haunted"]["scene_unavailable"],
                        ephemeral=True,
                    )

                current_profile = await get_or_create_profile(db, user_id)
                choice, outcome, new_state, next_scene = resolve_choice(
                    location_id,
                    scene_id,
                    run["story_state"],
                    choice_index,
                )
                sanity_delta = int(outcome.get("sanity", 0))
                result_text = outcome.get("text", "Something happens.")

                async with db.execute("SELECT active_effects FROM users WHERE user_id = ?", (user_id,)) as cursor:
                    effect_row = await cursor.fetchone()
                try:
                    effects = json.loads(effect_row[0] or "{}") if effect_row else {}
                    if not isinstance(effects, dict):
                        effects = {}
                except (TypeError, ValueError, json.JSONDecodeError):
                    effects = {}

                if sanity_delta < 0:
                    pet_protection = float(effects.get("haunted_run_negative_protection", 0.0))
                    if pet_protection and random.random() < pet_protection:
                        sanity_delta = 0
                        result_text += "\n\n🐾 **Your Haunted companion sensed the danger and intervened.**"
                    elif effects.pop("haunted_run_block_next_negative", False):
                        sanity_delta = 0
                        result_text += "\n\n**A ward absorbed the supernatural backlash.**"
                    elif effects.pop("haunted_run_half_next_negative", False):
                        sanity_delta = int(sanity_delta * 0.5)
                        result_text += "\n\n**The Mirror Ward reflects part of the fear away.**"
                    elif effects.get("haunted_run_flat_protection"):
                        protection = int(effects.pop("haunted_run_flat_protection"))
                        sanity_delta = min(0, sanity_delta + protection)
                        result_text += "\n\n**The prepared device cushioned the Sanity loss.**"

                    multiplier = float(effects.get("haunted_run_sanity_multiplier", 1.0))
                    if multiplier < 1.0 and sanity_delta < 0:
                        sanity_delta = int(sanity_delta * multiplier)

                await db.execute(
                    "UPDATE users SET active_effects = ? WHERE user_id = ?",
                    (json.dumps(effects), user_id),
                )
                new_sanity = await update_sanity(db, user_id, sanity_delta)

                achievements_cog = self.bot.get_cog("Achievements")
                discovery_id = outcome.get("discovery_id")
                if discovery_id and achievements_cog:
                    await achievements_cog.record_haunted_discovery(
                        user_id,
                        discovery_id,
                        location_id,
                        sanity=new_sanity,
                        db=db,
                        channel=interaction.channel,
                    )
                    await achievements_cog.mark_haunted_discovery_outcome(
                        user_id,
                        discovery_id,
                        sanity_delta,
                        new_sanity,
                        db=db,
                        channel=interaction.channel,
                    )

                pet_discovery_message = run["story_state"].get("pet_discovery_message")
                if outcome.get("pet_discovery"):
                    pet_result = await grant_haunted_pet(db, user_id, location_id)
                    if pet_result:
                        if pet_result.get("new"):
                            pet_discovery_message = pet_result["message"]
                            new_state["pet_discovery_message"] = pet_discovery_message
                        else:
                            pet_discovery_message = (
                                EXPLORATION_TEXT["haunted"]["pet_already_found"]
                            )
                            new_state["pet_discovery_message"] = pet_discovery_message
                    new_state["pet_opportunity_taken"] = True

                await db.execute(
                    "UPDATE users SET active_effects = ? WHERE user_id = ?",
                    (json.dumps(effects), user_id),
                )

                is_complete = bool(outcome.get("end")) or next_scene is None
                reward = None
                pet_xp_result = None
                haunted_home_bonus = 0

                if is_complete:
                    collectible_bonus = float(effects.get("haunted_run_collectible_bonus", 0.0))
                    ingredient_bonus = float(effects.get("haunted_run_ingredient_bonus", 0.0))
                    reward_bonus = float(effects.get("haunted_run_reward_bonus", 0.0))
                    reward = await grant_haunted_completion_rewards(
                        db,
                        self.bot,
                        user_id,
                        location_id,
                        collectible_bonus=collectible_bonus,
                        ingredient_bonus=ingredient_bonus,
                        reward_bonus=reward_bonus,
                    )
                    haunted_pet_xp_amount, haunted_home_bonus = await get_haunted_exploration_pet_xp(
                        db,
                        user_id,
                        location_id,
                    )
                    pet_xp_result = await add_pet_xp(db, user_id, haunted_pet_xp_amount)
                    await clear_run(db, user_id)
                else:
                    advanced = await advance_story(db, user_id, next_scene, new_state)
                    if advanced is None:
                        raise RuntimeError(
                            f"Haunted story state disappeared while advancing {location_id}:{scene_id}"
                        )
                    new_stage, _, _ = advanced

            if is_complete:
                # Completion rewards are guaranteed when a Haunted run completes.
                # Narrow the Optional return value for static type checkers.
                assert reward is not None
                reward_lines = [
                    f"{reward['rarity_emoji']} **{reward['rarity_label']} Haul**",
                    f"**+{reward['stardust']:,} Stardust** ✨",
                    f"**+{reward['candy']} Halloween Candy** 🍬",
                    f"{reward['ingredient_emoji']} **+{reward['ingredient_added']} {reward['ingredient_name']}**",
                ]
                if pet_xp_result:
                    xp_line = f"🐾 **+{pet_xp_result['xp_added']} Pet XP**"
                    if haunted_home_bonus:
                        xp_line += f" *(+{haunted_home_bonus} home-location bonus)*"
                    if pet_xp_result["leveled_up"]:
                        xp_line += f" • 🎉 **Pet Level {pet_xp_result['new_level']}!**"
                    reward_lines.append(xp_line)
                if reward["candy_overflow"]:
                    reward_lines.append(
                        f"Candy overflow: **{reward['candy_overflow']}** → **+{reward['overflow_stardust']} Stardust**"
                    )
                if reward["ingredient_overflow"]:
                    reward_lines.append(
                        f"Ingredient overflow: **{reward['ingredient_overflow']}** → **+{reward['ingredient_overflow_stardust']} Stardust**"
                    )
                if reward["collectible_found"] and reward["collectible"]:
                    collectible = reward["collectible"]
                    reward_lines.extend([
                        "",
                        f"**Halloween collectible Found: {collectible[2]} {collectible[1]}** 🎃",
                        "━━━━━━━━━━━━━━━━━━━━━━━━",
                        f"*{collectible[3]}*",
                    ])

                    if reward.get("collectible_first_discovery"):
                        use_config = HALLOWEEN_SPECIAL_USE_ITEMS.get(collectible[0])
                        if isinstance(use_config, dict) and use_config.get("enabled"):
                            reward_lines.extend([
                                "",
                                f"**Usable collectible found!**",
                                f"Use `/use item: [item name]` to activate this collectible.",
                            ])

                reward_embed = discord.Embed(
                    title=f"{HAUNTED_LOCATIONS[location_id]['emoji']} {HAUNTED_LOCATIONS[location_id]['name']}",
                    description=EXPLORATION_TEXT["haunted"]["completion_description"].format(
                        mention=interaction.user.mention,
                        location_name=HAUNTED_LOCATIONS[location_id]["name"],
                        result_text=result_text,
                    ),
                    color=discord.Color.green(),
                )
                reward_embed.add_field(name=EXPLORATION_TEXT["haunted"]["completion_explorer"], value=interaction.user.mention, inline=True)
                reward_embed.add_field(name=EXPLORATION_TEXT["haunted"]["completion_story"], value=f"**{total_stages} scenes**", inline=True)
                reward_embed.add_field(name=EXPLORATION_TEXT["haunted"]["completion_sanity"], value=f"**{sanity_percent(new_sanity)}/100**", inline=True)
                reward_embed.add_field(name=EXPLORATION_TEXT["haunted"]["completion_rewards"], value="\n".join(reward_lines), inline=False)
                if pet_discovery_message:
                    reward_embed.add_field(name=EXPLORATION_TEXT["haunted"]["completion_pet"], value=pet_discovery_message, inline=False)
                reward_embed.set_footer(text=EXPLORATION_TEXT["haunted"]["completion_footer"])
                await interaction.edit_original_response(content=None, embed=reward_embed, view=None)
                return

            await self._show_haunted_stage(
                interaction,
                location_id,
                new_stage,
                total_stages,
                result_text=result_text,
            )

    async def _run_away_haunted(
        self,
        interaction: discord.Interaction,
        owner_id: int,
        location_id: str,
        stage: int,
        total_stages: int,
    ):
        if interaction.user.id != owner_id:
            return await interaction.followup.send(
                "**This Haunted Exploration isn't yours.**\n"
                "These buttons belong to another player's exploration run.",
                ephemeral=True,
            )

        user_id = interaction.user.id
        lock = self._user_locks.setdefault(user_id, asyncio.Lock())
        async with lock:
            async with aiosqlite.connect(self.get_db_path()) as db:
                await self.ensure_schema(db)
                run = await get_active_run(db, user_id)
                if not run or run["location_id"] != location_id or run["stage"] != stage or run["total_stages"] != total_stages:
                    return await interaction.followup.send(
                        EXPLORATION_TEXT["haunted"]["run_unavailable"],
                        ephemeral=True,
                    )

                pet_discovery_message = run["story_state"].get("pet_discovery_message")
                rare_escape = random.random() < 0.08
                if rare_escape:
                    sanity_loss = random.randint(4, 10)
                    new_sanity = await update_sanity(db, user_id, -sanity_loss)
                    escape_text = random.choice(EXPLORATION_TEXT["haunted"]["escape_rare"])
                else:
                    new_sanity = await update_sanity(db, user_id, 0)
                    escape_text = random.choice(EXPLORATION_TEXT["haunted"]["escape_normal"])
                await clear_run(db, user_id)

        suffix = EXPLORATION_TEXT["haunted"]["escape_suffix"] if rare_escape else ""
        location = HAUNTED_LOCATIONS[location_id]
        escape_embed = discord.Embed(
            title=EXPLORATION_TEXT["haunted"]["scene_title"].format(emoji=location["emoji"], location_name=location["name"]),
            description=EXPLORATION_TEXT["haunted"]["escape_description"].format(
                mention=interaction.user.mention,
                location_name=location["name"],
                escape_text=escape_text,
                suffix=suffix,
            ),
            color=discord.Color.orange(),
        )
        escape_embed.add_field(name=EXPLORATION_TEXT["haunted"]["escape_explorer"], value=interaction.user.mention, inline=True)
        escape_embed.add_field(name=EXPLORATION_TEXT["haunted"]["escape_run_ended"], value=f"Scene **{stage}/{total_stages}**", inline=True)
        escape_embed.add_field(name=EXPLORATION_TEXT["haunted"]["escape_sanity"], value=f"**{sanity_percent(new_sanity)}/100**", inline=True)
        escape_embed.add_field(name=EXPLORATION_TEXT["haunted"]["escape_rewards"], value=EXPLORATION_TEXT["haunted"]["escape_no_reward"], inline=False)
        if pet_discovery_message:
            escape_embed.add_field(name="*Location-based pet found!*", value=pet_discovery_message, inline=False)
        escape_embed.set_footer(text=EXPLORATION_TEXT["haunted"]["escape_footer"])
        await interaction.edit_original_response(content=None, embed=escape_embed, view=None)

    @commands.hybrid_command(name="heal", description="Use a healing item from your inventory to restore HP.")
    @app_commands.choices(item=[
        app_commands.Choice(name="Nanite Stim-Patch (+35 HP)", value="nanite_patch"),
        app_commands.Choice(name="Makeshift Medkit (+60 HP)", value="makeshift_medkit"),
        app_commands.Choice(name="Field Trauma Medkit (+100 HP)", value="medkit"),
        app_commands.Choice(name="Halloween Candy (+5 HP)", value="halloween_candy"),
        app_commands.Choice(name="Trick-or-Treat Bag (+25 HP)", value="trick_or_treat_bag")
    ])
    async def heal(self, ctx: commands.Context, item: str):
        await ctx.defer()

        user_id = ctx.author.id
        lock = self._user_locks.setdefault(user_id, asyncio.Lock())

        async with lock:
            return await self._heal_impl(ctx, item)

    async def _heal_impl(self, ctx: commands.Context, item: str):
        user_id = ctx.author.id

        heal_data = {
            "nanite_patch": {"name": "Nanite Stim-Patch", "col": "nanite_patchs", "amount": 35},
            "medkit": {"name": "Field Trauma Medkit", "col": "medkits", "amount": 100},
            "makeshift_medkit": {"name": "Makeshift Medkit", "inventory": True, "amount": 60},
            "halloween_candy": {"name": "Halloween Candy", "inventory": True, "amount": 5},
            "trick_or_treat_bag": {"name": "Trick-or-Treat Bag", "inventory": True, "amount": 25},
        }

        selected = heal_data.get(item)
        if not selected:
            return await ctx.send("Invalid healing item selected.")

        db_path = self.get_db_path()

        async with aiosqlite.connect(db_path) as db:
            await self.ensure_schema(db)
            await self.recover_if_new_day(db, user_id)

            async with db.execute(
                "SELECT hp, max_hp, knocked_out_until FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                return await ctx.send("Profile not found.")

            current_hp, max_hp, knocked_out_until = row[0] or 0, row[1] or 100, row[2] or ""

            if current_hp <= 0:
                return await ctx.send(self.knockout_message(knocked_out_until or "tomorrow", ctx.author.mention))

            if current_hp >= max_hp:
                return await ctx.send(
                    f"**You're already at full health!** (**{max_hp}/{max_hp} HP**)."
                )

            if selected.get("inventory"):
                async with db.execute(
                    "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                    (user_id, item)
                ) as cursor:
                    item_row = await cursor.fetchone()
                item_count = item_row[0] if item_row else 0
                if item_count <= 0:
                    return await ctx.send(f"You don't have any **{selected['name']}s** left!")
                new_count = item_count - 1
                await db.execute(
                    "UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_id = ?",
                    (user_id, item)
                )
            else:
                col_name = selected["col"]
                async with db.execute("PRAGMA table_info(users)") as cursor:
                    cols = {row[1] async for row in cursor}
                if col_name not in cols:
                    return await ctx.send(f"You don't have any **{selected['name']}s** in your inventory!")
                async with db.execute(
                    f"SELECT {col_name} FROM users WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    count_row = await cursor.fetchone()
                item_count = count_row[0] if count_row else 0
                if item_count <= 0:
                    return await ctx.send(f"You don't have any **{selected['name']}s** left!")
                new_count = item_count - 1
                await db.execute(
                    f"UPDATE users SET {col_name} = ? WHERE user_id = ?",
                    (new_count, user_id)
                )

            new_hp = min(max_hp, current_hp + selected["amount"])
            healed_by = new_hp - current_hp
            await db.execute(
                "UPDATE users SET hp = ? WHERE user_id = ?",
                (new_hp, user_id)
            )
            # Track Halloween candy consumption for achievements.
            if item in ("halloween_candy", "trick_or_treat_bag"):
                achievements_cog = self.bot.get_cog("Achievements")

                if achievements_cog:
                    # A Trick-or-Treat Bag represents the 25 candy pieces
                    # used to craft it, so opening one counts as 25 candy eaten.
                    candy_amount = 25 if item == "trick_or_treat_bag" else 1

                    await achievements_cog.add_candy_progress(
                        user_id,
                        candy_amount,
                        db=db,
                        channel=ctx.channel,
                    )
            await db.commit()

        action = "Chowed down on the candy! 🍬" if item == "halloween_candy" else ("You opened the bag and chowed down on candy! 🍬" if item == "trick_or_treat_bag" else f"Used {selected['name']}!")
        await ctx.send(
            f"{ctx.author.mention} {'🎃' if item in ('halloween_candy', 'trick_or_treat_bag') else '💉'} **{action}**\n"
            f"Restored **+{healed_by} HP**! Current health: **{new_hp}/{max_hp} HP** "
            f"*(Items Remaining: {new_count})*"
        )

    @commands.hybrid_command(
        name="cooldown_alerts",
        description="Toggle notifications when your mining and scavenging cooldowns finish. These are off by default."
    )
    async def cooldown_alerts(self, ctx: commands.Context):
        await ctx.defer()

        user_id = ctx.author.id
        db_path = self.get_db_path()

        async with aiosqlite.connect(db_path) as db:
            await self.ensure_schema(db)

            async with db.execute(
                """
                SELECT cooldown_alerts, last_mined, last_scavenged
                FROM users
                WHERE user_id = ?
                """,
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                await db.execute(
                    """
                    INSERT OR IGNORE INTO users (
                        user_id,
                        cooldown_alerts,
                        mining_alert_sent,
                        scavenge_alert_sent
                    )
                    VALUES (?, 1, 0, 0)
                    """,
                    (user_id,)
                )
                await db.commit()

                return await ctx.send(
                    "**Cooldown alerts on!**\n"
                    "You'll be pinged in the Exploration channel "
                    "when your mining or scavenging cooldown finishes.``"
                )

            current = bool(row[0])
            new_value = 0 if current else 1

            if new_value:
                # Mark the current cooldown state as already seen.
                # This prevents an immediate notification if the cooldown
                # was already finished before the user enabled alerts.
                await db.execute(
                    """
                    UPDATE users
                    SET cooldown_alerts = ?,
                        mining_alert_sent = COALESCE(last_mined, 0),
                        scavenge_alert_sent = COALESCE(last_scavenged, 0)
                    WHERE user_id = ?
                    """,
                    (new_value, user_id)
                )
            else:
                await db.execute(
                    """
                    UPDATE users
                    SET cooldown_alerts = ?
                    WHERE user_id = ?
                    """,
                    (new_value, user_id)
                )

            await db.commit()

        if new_value:
            await ctx.send(
                "**Cooldown alerts on!**\n"
                "You'll be pinged in the Exploration channel "
                "when your mining or scavenging cooldown finishes!"
            )
        else:
            await ctx.send(
                "**Cooldown alerts off**\n"
                "You won't receive mining or scavenging cooldown notifications."
            )

    async def maybe_suggest_cooldown_alerts(self, ctx):
        """Occasionally return a cooldown-alert suggestion for the result embed."""
        if random.random() > 0.10:
            return None

        user_id = ctx.author.id
        db_path = self.get_db_path()

        async with aiosqlite.connect(db_path) as db:
            await self.ensure_schema(db)

            async with db.execute(
                "SELECT cooldown_alerts FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()

        if row and not row[0]:
            return (
                "**Want a little heads-up from time-to-time?** You can use `/cooldown_alerts` "
                "to get pinged when your mining and/or scavenging cooldown finishes!"
            )

        return None



    @commands.hybrid_command(name="mine", description="Deploy your mining laser to scout for Stardust and rare loot!")
    async def mine(self, ctx: commands.Context):
        await ctx.defer()

        user_id = ctx.author.id
        lock = self._user_locks.setdefault(user_id, asyncio.Lock())

        async with lock:
            return await self._mine_impl(ctx)


    async def _mine_impl(self, ctx: commands.Context):
        user_id = ctx.author.id
        current_time = time.time()
        db_path = self.get_db_path()

        async with aiosqlite.connect(db_path) as db:
            await self.ensure_schema(db)
            await db.commit()

            # Recover knockout status before starting the mining transaction.
            await self.recover_if_new_day(db, user_id)

            async with db.execute(
                "SELECT mining_charges, last_mined, stardust, hp, knocked_out_until, active_effects FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                await db.execute("""
                    INSERT OR IGNORE INTO users (user_id, mining_charges, last_mined, stardust)
                    VALUES (?, 10, 0, 0)
                """, (user_id,))
                charges, last_mined, stardust, hp, knocked_out_until, effects_raw = 10, 0, 0, 100, "", "{}"
            else:
                charges, last_mined, stardust, hp, knocked_out_until, effects_raw = (
                    row[0] if row[0] is not None else 10,
                    row[1] or 0,
                    row[2] or 0,
                    row[3] if row[3] is not None else 100,
                    row[4] or "",
                    row[5] or "{}"
                )

            effects = json.loads(effects_raw)
            kolossos_next_loot_bonus = float(effects.pop("kolossos_next_loot_bonus", 0.0) or 0.0)
            pet_effects = await get_active_pet_effects(db, user_id)
            upgrade_cog = self.bot.get_cog("Upgrades")
            mining_upgrade = await upgrade_cog.get_effects(user_id, "mining") if upgrade_cog else {"level": 0, "max_charges": 10, "stardust_mult": 1.0, "rare_bonus": 0.0}
            # Space Dragon grants +3 maximum Mining charges at passive level 5.
            max_mining_charges = mining_upgrade["max_charges"] + pet_effects.get("extra_charge_count", 0)
            mining_rare_bonus = mining_upgrade.get("rare_bonus", 0.0) + kolossos_next_loot_bonus

            if hp <= 0:
                return await ctx.send(self.knockout_message(knocked_out_until or "tomorrow", ctx.author.mention))

            # Daily charge reset: charges refresh to 10 once per calendar day.
            current_date = self.game_date()
            last_mined_date = (
                datetime.fromtimestamp(
                    last_mined,
                    tz=pytz.timezone("US/Eastern")
                ).date()
                if last_mined > 0
                else None
            )

            if last_mined_date != current_date:
                charges = max_mining_charges
                await db.execute(
                    "UPDATE users SET mining_charges = ? WHERE user_id = ?",
                    (max_mining_charges, user_id)
                )
                await db.commit()

            elapsed = current_time - last_mined

            effective_cooldown = self.COOLDOWN_SECONDS * (
                1 - pet_effects["cooldown_reduction"]
            )

            if elapsed < effective_cooldown:
                remaining = int(effective_cooldown - elapsed)
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                return await ctx.send(f"{ctx.author.mention} **Your mining laser is recharging!** Next charge ready in **{hours}h {minutes}m**")

            if charges <= 0 and not effects.get("fuel_stabilizer"):
                return await ctx.send(
                    f"{ctx.author.mention} **Your laser is depleted!** You are out of fuel charges. "
                    "Visit the shop for a refill item, or wait until daily reset at 12:00AM EST!"
                )

            # --- TIERED LOOT ROLL ---
            roll = 0.70 if effects.pop("ore_magnet", False) else random.random()
            mining_charge_saved = False
            if effects.pop("fuel_stabilizer", False):
                new_charges = charges
            elif pet_effects["charge_save"] and random.random() < pet_effects["charge_save"]:
                new_charges = charges
                mining_charge_saved = True
            else:
                new_charges = charges - 1
            
            pet_effects = await get_active_pet_effects(db, user_id)
            found_stardust = int(
                random.randint(80, 550)
                * mining_upgrade["stardust_mult"]
                * (
                    1
                    + pet_effects["stardust_bonus"]
                    + pet_effects.get("extra_charges", 0.0)
                )
            )

            if effects.pop("prototype_drill_bit", False):
                found_stardust = int(found_stardust * 1.5)

            if pet_effects["stardust_bonus"]:
                pet_stardust_message = get_pet_passive_message(
                    pet_effects, "stardust_bonus"
                )
            else:
                pet_stardust_message = ""

            if effects.pop("quantum_battery", False):
                found_stardust *= 3
                loot_bonus_note = "\n\nQuantum Battery: **Stardust tripled!**"
            else:
                loot_bonus_note = ""

            new_stardust = stardust + found_stardust
            
            # Keep the already-generated passive flavor message so the same
            # trigger produces one consistent message instead of rolling the
            # random flavor line a second time during embed construction.
            mining_stardust_notes = []
            if loot_bonus_note:
                mining_stardust_notes.append(loot_bonus_note.lstrip("\n"))
            if pet_stardust_message:
                mining_stardust_notes.append(pet_stardust_message)
            if mining_charge_saved:
                charge_save_message = get_pet_passive_message(
                    pet_effects, "charge_save"
                )
                if charge_save_message:
                    mining_stardust_notes.append(charge_save_message)

            mining_item_findings = []
            mining_special_findings = []

            # Mining can uncover multiple types of raw mineral in one run.
            # Each successful find yields 1–5 units; Astral Core remains a separate
            # legendary roll and is intentionally always awarded one at a time.
            mining_material_findings = []
            mining_overflow_findings = []
            for material_id, material_name, chance in MINING_MATERIALS:
                if random.random() < chance:
                    amount_found = random.randint(1, 5)
                    if pet_effects["material_bonus"] and random.random() < pet_effects["material_bonus"]:
                        amount_found += 1
                        mining_special_findings.append(
                            get_pet_passive_message(pet_effects, "material_bonus")
                        )
                    added_material, material_quantity, material_max = await add_inventory_item(
                        db, user_id, material_id, "mineral", amount_found
                    )
                    overflow_amount = amount_found - added_material
                    if added_material:
                        mining_material_findings.append(
                            f"{material_name} ×{added_material}"
                        )
                    if overflow_amount > 0:
                        overflow_stardust = overflow_amount * MATERIAL_OVERFLOW_VALUES.get(material_id, 0)
                        new_stardust += overflow_stardust
                        mining_overflow_findings.append(
                            f"{material_name} ×{overflow_amount} → +{overflow_stardust} Stardust"
                        )

            # Material findings are rendered together in the final result layout.

            # MissingNo. rarely corrupts the reward data of the current activity.
            if pet_effects.get("missingno_error", 0.0) and random.random() < pet_effects.get("missingno_error", 0.0):
                glitch_roll = random.random()
                if glitch_roll < 0.70:
                    glitch_amount = random.randint(1, 5)
                    glitch_kind = "small"
                elif glitch_roll < 0.95:
                    glitch_amount = random.randint(10, 15)
                    glitch_kind = "major"
                else:
                    glitch_amount = random.randint(100, 500)
                    glitch_kind = "stardust"

                if glitch_kind == "stardust":
                    new_stardust += glitch_amount
                    mining_special_findings.append(
                        get_pet_passive_message(pet_effects, "missingno_error_stardust")
                        + f" **+{glitch_amount:,} Stardust**"
                    )
                else:
                    eligible_minerals = [
                        (material_id, material_name)
                        for material_id, material_name, _chance in MINING_MATERIALS
                    ]
                    glitch_item_id, glitch_item_name = random.choice(eligible_minerals)
                    added_glitch, _glitch_quantity, _glitch_max = await add_inventory_item(
                        db, user_id, glitch_item_id, "mineral", glitch_amount
                    )
                    overflow_glitch = glitch_amount - added_glitch
                    if added_glitch:
                        mining_special_findings.append(
                            get_pet_passive_message(
                                pet_effects,
                                "missingno_error_small" if glitch_kind == "small" else "missingno_error_major",
                            )
                            + f" **{glitch_item_name} ×{added_glitch}**"
                        )
                    if overflow_glitch > 0:
                        overflow_value = overflow_glitch * MATERIAL_OVERFLOW_VALUES.get(glitch_item_id, 0)
                        new_stardust += overflow_value
                        mining_special_findings.append(
                            f"Glitched overflow 📦 → **+{overflow_value:,} Stardust**"
                        )

            # Astral Essence is a separate rare mining discovery, independent of
            # the normal rarity table so it does not replace existing loot.
            if random.random() < MINING_ESSENCE_CHANCE:
                added_essence, essence_quantity, essence_max = await add_inventory_item(
                    db, user_id, "astral_essence", "special", 1
                )
                if added_essence:
                    mining_item_findings.append(
                        f"Astral Essence **({essence_quantity}/{essence_max})**"
                    )
                else:
                    new_stardust += 2500
                    mining_special_findings.append(
                        "Astral Essence overflow: **+2,500 Stardust**"
                    )

            # Halloween bonus resources are independent rolls during the active event.
            halloween_active = halloween_is_active()
            seasonal_findings = []
            if halloween_active and random.random() < HALLOWEEN_MINING_CANDY_CHANCE:
                candy_found = 1
                candy_doubled = False

                # Samhain's Trick-or-Treating passive can double the base candy haul.
                if (
                    pet_effects["candy_bonus"]
                    and random.random() < pet_effects["candy_bonus"]
                ):
                    candy_found *= 2
                    candy_doubled = True
                    seasonal_findings.append(
                        get_pet_passive_message(pet_effects, "candy_bonus")
                    )

                if (
                    pet_effects["halloween_bonus"]
                    and random.random() < pet_effects["halloween_bonus"]
                ):
                    candy_found += 1
                    seasonal_findings.append(
                        get_pet_passive_message(pet_effects, "halloween_bonus")
                    )

                added_candy, candy_quantity, candy_max = await add_inventory_item(
                    db, user_id, "halloween_candy", "consumable", candy_found
                )
                overflow_candy = candy_found - added_candy
                if added_candy:
                    candy_note = f"**{EMOJIS.get('halloween_candy', '🍬')} Halloween Candy ×{added_candy}**"
                    if candy_doubled:
                        candy_note += " (Samhain bonus!)"
                    seasonal_findings.append(candy_note)
                if overflow_candy > 0:
                    candy_overflow_stardust = overflow_candy * 2
                    new_stardust += candy_overflow_stardust
                    seasonal_findings.append(
                        f"Candy overflow: **×{overflow_candy} → +{candy_overflow_stardust} Stardust**"
                    )

            # Special pet candy is seasonal too, but is separate from ordinary Halloween Candy.
            if halloween_active and random.random() < HALLOWEEN_PET_CANDY_CHANCE:
                pet_candy_found = random.randint(1, 2)

                if (
                    pet_effects["halloween_bonus"]
                    and random.random() < pet_effects["halloween_bonus"]
                ):
                    pet_candy_found += 1
                    seasonal_findings.append(
                        get_pet_passive_message(pet_effects, "halloween_bonus")
                    )
                added_pet_candy, pet_candy_quantity, pet_candy_max = await add_inventory_item(
                    db, user_id, "halloween_pet_candy", "pet_treat", pet_candy_found
                )
                if added_pet_candy:
                    seasonal_findings.append(
                        f"**Halloween Pet Candy 🍬 ×{added_pet_candy}**"
                    )
                overflow_pet_candy = pet_candy_found - added_pet_candy
                if overflow_pet_candy:
                    # Halloween Pet Candy is a pet treat, so any overflow is
                    # converted 1:1 into ordinary Pet Treats instead of being lost.
                    added_normal_treat, _, normal_treat_max = await add_inventory_item(
                        db, user_id, "pet_snack", "pet_treat", overflow_pet_candy
                    )
                    if added_normal_treat:
                        seasonal_findings.append(
                            f"Halloween Pet Candy Overflow: **×{overflow_pet_candy} "
                            f"→ Pet Treat 🍪 ×{added_normal_treat}"
                        )
                    remaining_overflow = overflow_pet_candy - added_normal_treat
                    if remaining_overflow:
                        seasonal_findings.append(
                            f"Pet Treat stack full: **{remaining_overflow} overflow "
                            f"could not be stored (cap {normal_treat_max})"
                        )

            # Halloween Pet Candy is an independent seasonal bonus roll, matching Mining.
            if halloween_active and random.random() < HALLOWEEN_PET_CANDY_CHANCE:
                pet_candy_found = random.randint(1, 4)

                if (
                    pet_effects["halloween_bonus"]
                    and random.random() < pet_effects["halloween_bonus"]
                ):
                    pet_candy_found += 1

                added_pet_candy, pet_candy_quantity, pet_candy_max = await add_inventory_item(
                    db, user_id, "halloween_pet_candy", "pet_treat", pet_candy_found
                )
                if added_pet_candy:
                    seasonal_findings.append(
                        f"**Halloween Pet Candy 🍬 ×{added_pet_candy}**"
                    )

                overflow_pet_candy = pet_candy_found - added_pet_candy
                if overflow_pet_candy:
                    added_normal_treat, _, _ = await add_inventory_item(
                        db, user_id, "pet_snack", "pet_treat", overflow_pet_candy
                    )
                    remaining_overflow = overflow_pet_candy - added_normal_treat
                    if remaining_overflow:
                        seasonal_findings.append(
                            f"Halloween Pet Candy Overflow: **×{remaining_overflow} → Pet Treat stack full**"
                        )

            if halloween_active and random.random() < HALLOWEEN_PLASTIC_CHANCE:
                plastic_found = random.randint(HALLOWEEN_PLASTIC_MIN, HALLOWEEN_PLASTIC_MAX)
                added_plastic, plastic_quantity, plastic_max = await add_inventory_item(
                    db, user_id, "halloween_plastic", "crafting_material", plastic_found
                )
                if added_plastic:
                    seasonal_findings.append(f"**🧴 Halloween Plastic ×{added_plastic}**")
                overflow_plastic = plastic_found - added_plastic
                if overflow_plastic:
                    new_stardust += overflow_plastic * 2
                    seasonal_findings.append(f"**🧴 Plastic overflow: **×{overflow_plastic} → +{overflow_plastic * 2} Stardust**")

            seasonal_findings = [line for line in seasonal_findings if line]

            rarity_badge = "common"

            if roll < 0.40:
                # Tier 1: Common (Just Stardust)
                pass

            elif roll < 0.60:
                # Tier 2: Uncommon (Stardust + XP Data Shard)
                found_xp = random.randint(100, 500)
                mining_item_findings.append(f"XP Data Shard: **+{found_xp} XP**")
                rarity_badge = "uncommon"

                # Award XP globally through leveling.py
                leveling_cog = self.bot.get_cog("Leveling")
                if leveling_cog:
                    leveled_up, new_level = await leveling_cog.add_xp(ctx.author, found_xp)
                    if leveled_up:
                        mining_special_findings.append(f"**Level up!** You've reached **level {new_level}!**")

            elif roll < 0.75 + mining_rare_bonus:
                # Tier 3: Rare Mineral (Titanium Ore Chunk)
                added_amount, new_quantity, max_quantity = await add_inventory_item(
                    db,
                    user_id,
                    "titanium_chunk",
                    "mineral",
                    1
                )

                if added_amount == 1:
                    mining_item_findings.append(
                        f"Titanium Ore Chunk **({new_quantity}/{max_quantity})**"
                    )
                else:
                    overflow_stardust = LOOT_OVERFLOW_VALUES.get("titanium_chunk", 75)
                    new_stardust += overflow_stardust

                    mining_special_findings.append(
                        f"Titanium Ore Chunk stack full: **+{overflow_stardust:,} Stardust**"
                    )

                rarity_badge = "rare"

            elif roll < 0.90 + mining_rare_bonus:
                # Tier 4: Rare/Epic (Arcade Token for future minigames)
                async with db.execute(
                    "SELECT COALESCE(arcade_coins, 0) FROM users WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    token_row = await cursor.fetchone()

                token_balance = (token_row[0] or 0) if token_row else 0
                token_max = 1000

                if token_balance < token_max:
                    new_token_balance = token_balance + 1
                    await db.execute(
                        "UPDATE users SET arcade_coins = ? WHERE user_id = ?",
                        (new_token_balance, user_id)
                    )
                    mining_item_findings.append(
                        f"Arcade Token **({new_token_balance}/{token_max})**"
                    )
                else:
                    overflow_stardust = LOOT_OVERFLOW_VALUES.get("arcade_token", 50)
                    new_stardust += overflow_stardust

                    mining_special_findings.append(
                        f"Arcade Token stack full: **+{overflow_stardust:,} Stardust**"
                    )

                rarity_badge = "rare"

            elif roll < 0.96:
                # Tier 5: Epic (Dilated Time Crystal)
                from inventory import ITEM_REGISTRY

                max_quantity = ITEM_REGISTRY["time_crystal"].get("max_quantity", 10)

                async with db.execute(
                    "SELECT COALESCE(time_crystals, 0) FROM users WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    crystal_row = await cursor.fetchone()

                current_crystals = crystal_row[0] if crystal_row else 0

                if current_crystals < max_quantity:
                    await db.execute(
                        """
                        UPDATE users
                        SET time_crystals = COALESCE(time_crystals, 0) + 1
                        WHERE user_id = ?
                        """,
                        (user_id,)
                    )

                    mining_item_findings.append(
                        f"Dilated Time Crystal **({current_crystals + 1}/{max_quantity})**"
                    )
                else:
                    overflow_stardust = LOOT_OVERFLOW_VALUES.get("time_crystal", 350)
                    new_stardust += overflow_stardust

                    mining_special_findings.append(
                        f"Dilated Time Crystal stack full: **+{overflow_stardust:,} Stardust**"
                    )

                rarity_badge = "epic"

            else:
                # Tier 6: Legendary (Astral Core)
                added_amount, new_quantity, max_quantity = await add_inventory_item(
                    db,
                    user_id,
                    "astral_core",
                    "special",
                    1
                )

                if added_amount == 1:
                    mining_item_findings.append(
                        f"Astral Core **({new_quantity}/{max_quantity})**"
                    )
                else:
                    overflow_stardust = LOOT_OVERFLOW_VALUES.get("astral_core", 750)
                    new_stardust += overflow_stardust

                    mining_special_findings.append(
                        f"Astral Core stack full: **+{overflow_stardust:,} Stardust**"
                    )

                rarity_badge = "legendary"

            pet_xp_result = await add_pet_xp(db, user_id, roll_normal_exploration_pet_xp())

            await db.execute("""
                UPDATE users 
                SET mining_charges = ?, last_mined = ?, stardust = ?, active_effects = ?
                WHERE user_id = ?
            """, (new_charges, current_time, new_stardust, json.dumps(effects), user_id))

            await db.commit()

        colors = {
            "common": discord.Color.from_rgb(120, 140, 160),
            "uncommon": discord.Color.from_rgb(0, 229, 255),
            "rare": discord.Color.from_rgb(50, 205, 50),
            "epic": discord.Color.from_rgb(186, 85, 211),
            "legendary": discord.Color.from_rgb(255, 215, 0)
        }

        mining_sections = []
        if mining_item_findings:
            mining_sections.append(
                "Mined items: " + " • ".join(mining_item_findings)
            )
        if mining_material_findings or mining_overflow_findings:
            material_lines = []
            if mining_material_findings:
                material_lines.append(
                    " • ".join(f"**{finding}**" for finding in mining_material_findings)
                )
            if mining_overflow_findings:
                material_lines.append(
                    "Overflow: " + " • ".join(f"**{finding}**" for finding in mining_overflow_findings)
                )
            mining_sections.append(
                "Mined materials: " + "\n".join(material_lines)
            )
        all_mining_special_findings = [
            *seasonal_findings,
            *mining_special_findings,
        ]
        if all_mining_special_findings:
            mining_sections.append(
                "Special findings: " + " • ".join(all_mining_special_findings)
            )

        mining_result_sections = (
            "\n\n" + EXPLORATION_SEPARATOR + "\n\n"
            + "\n\n".join(mining_sections)
            if mining_sections
            else ""
        )
        mining_stardust_notes_text = (
            "\n" + "\n".join(mining_stardust_notes)
            if mining_stardust_notes
            else ""
        )

        embed = discord.Embed(
            title=EXPLORATION_TEXT["mining"]["title"].format(display_name=ctx.author.display_name),
            description=EXPLORATION_TEXT["mining"]["description"].format(
                stardust=found_stardust,
                stardust_notes=mining_stardust_notes_text,
                result_sections=mining_result_sections,
            ),
            color=colors.get(rarity_badge, discord.Color.blue())
        )
        cooldown_total_seconds = max(0, int(round(effective_cooldown)))
        cooldown_minutes, cooldown_seconds = divmod(cooldown_total_seconds, 60)
        cooldown_text = f"{cooldown_minutes}m" if cooldown_seconds == 0 else f"{cooldown_minutes}m {cooldown_seconds}s"
        embed.set_footer(text=EXPLORATION_TEXT["mining"]["footer"].format(charges=new_charges, max_charges=max_mining_charges, cooldown=cooldown_text))
        if pet_xp_result:
            pet_xp_text = EXPLORATION_TEXT["mining"]["pet_xp"].format(xp=pet_xp_result["xp_added"])
            if pet_xp_result["leveled_up"]:
                pet_xp_text += EXPLORATION_TEXT["mining"]["pet_level"].format(level=pet_xp_result["new_level"])
            embed.add_field(
                name=EXPLORATION_TEXT["mining"]["pet_progress"],
                value=pet_xp_text,
                inline=False,
            )

        if random.random() < 0.25 and await self.daily_unclaimed(user_id):
            embed.add_field(
                name=EXPLORATION_TEXT["mining"]["daily_name"],
                value=EXPLORATION_TEXT["mining"]["daily_value"],
                inline=False
            )

        cooldown_reminder = await self.maybe_suggest_cooldown_alerts(ctx)
        if cooldown_reminder:
            embed.add_field(
                name=EXPLORATION_TEXT["mining"]["cooldown_name"],
                value=cooldown_reminder,
                inline=False
            )

        await ctx.send(content=ctx.author.mention, embed=embed)

    @commands.hybrid_command(name="scavenge", description="Search derelict wreckage for salvage, Stardust, and occasional rare findings!")
    async def scavenge(self, ctx: commands.Context):
        await ctx.defer()

        user_id = ctx.author.id
        lock = self._user_locks.setdefault(user_id, asyncio.Lock())

        async with lock:
            return await self._scavenge_impl(ctx)


    async def _scavenge_impl(self, ctx: commands.Context):
        xenomorph_bonus_loot_pending = False
        user_id = ctx.author.id
        current_time = time.time()
        db_path = self.get_db_path()

        async with aiosqlite.connect(db_path) as db:
            await self.ensure_schema(db)
            await db.commit()
            await self.recover_if_new_day(db, user_id)

            async with db.execute("SELECT scavenge_charges, last_scavenged, stardust, hp, max_hp, knocked_out_until, active_effects FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()

            if not row:
                await db.execute("""
                    INSERT OR IGNORE INTO users (user_id, scavenge_charges, last_scavenged, stardust, hp, max_hp) 
                    VALUES (?, 10, 0, 0, 100, 100)
                """, (user_id,))
                await db.commit()
                charges, last_scavenged, stardust, hp, max_hp, knocked_out_until, effects_raw = 10, 0, 0, 100, 100, "", "{}"
            else:
                charges = row[0] if row[0] is not None else 10
                last_scavenged = row[1] if row[1] is not None else 0
                stardust = row[2] if row[2] is not None else 0
                hp = row[3] if row[3] is not None else 100
                max_hp = row[4] if row[4] is not None else 100
                knocked_out_until = row[5] or ""
                effects_raw = row[6] or "{}"
            effects = json.loads(effects_raw)
            kolossos_next_loot_bonus = float(effects.pop("kolossos_next_loot_bonus", 0.0) or 0.0)
            pet_effects = await get_active_pet_effects(db, user_id)
            upgrade_cog = self.bot.get_cog("Upgrades")
            scavenging_upgrade = await upgrade_cog.get_effects(user_id, "scavenging") if upgrade_cog else {"level": 0, "max_charges": 10, "stardust_mult": 1.0, "rare_bonus": 0.0}
            salvage_upgrade = await upgrade_cog.get_effects(user_id, "salvage") if upgrade_cog else {"level": 0, "bonus_chance": 0.0}
            # Space Dragon grants +3 maximum Scavenging charges at passive level 5.
            max_scavenge_charges = scavenging_upgrade["max_charges"] + pet_effects.get("extra_charge_count", 0)
            scavenging_rare_bonus = scavenging_upgrade.get("rare_bonus", 0.0)
            scavenging_rare_bonus += kolossos_next_loot_bonus
            salvage_bonus_chance = max(0.0, salvage_upgrade.get("bonus_chance", 0.0))

            # Daily charge reset: charges refresh to 10 once per calendar day.
            current_date = self.game_date()
            last_scavenged_date = (
                datetime.fromtimestamp(
                    last_scavenged,
                    tz=pytz.timezone("US/Eastern")
                ).date()
                if last_scavenged > 0
                else None
            )

            if last_scavenged_date != current_date:
                charges = max_scavenge_charges
                await db.execute(
                    "UPDATE users SET scavenge_charges = ? WHERE user_id = ?",
                    (max_scavenge_charges, user_id)
                )
                await db.commit()

            elapsed = current_time - last_scavenged

            effective_cooldown = self.COOLDOWN_SECONDS * (
                1 - pet_effects["cooldown_reduction"]
            )

            # Health Knockout Check
            if hp <= 0:
                return await ctx.send(self.knockout_message(knocked_out_until or "tomorrow", ctx.author.mention))

            if elapsed < effective_cooldown:
                remaining = int(effective_cooldown - elapsed)
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                return await ctx.send(f"{ctx.author.mention} **Your scavenge drone is recharging!** Next run ready in **{hours}h {minutes}m**.")

            if charges <= 0:
                return await ctx.send(f"{ctx.author.mention} **Your drone battery is depleted!** You are out of scavenge charges. Visit the shop for a recharge item, or wait until daily reset at 12:00AM EST.")

            junk_items = {
                "space_pizza": "Dehydrated Space Pizza (slightly freezer-burned) 🍕",
                "floppy_disk": "Ancient Alien Floppy Disk (contains mysterious code) 💾",
                "meteorite": "Suspiciously Warm Meteorite Chunk (glows faintly) ☄️",
                "rubber_duck": "Rubber Duck in a Micro-Spacesuit (how cute!) 🐤",
                "rusty_gear": "Tarnished Station Gear (still turns, but squeaks) ⚙️",
                "tape_deck": "Broken Cassette Player (plays static) 📼",
                "alien_artifact": "Miniature Alien Artifact (glows faintly) 🛸",
                "space_boot": "Singular Space Boot (wonder where the other one went...) 🥾",
                "cosmic_coin": "Cosmic Coin (give it a flip!) 🪙",
                "holo_poster": "Faded Holographic Poster of a Galactic Band 🖼️",
                "broken_laser": "Broken Laser Pistol (sparks occasionally) 🔫",
                "lost_logbook": "Waterlogged Starship Logbook (unreadable) 📓",
                "left_sock": "Left Sock (the right one is missing) 🧦",
                "warp_mug": "Leaky Thermal Mug (holds coffee across space-time, leaks in 3D) ☕",
                "space_pudding": "Expired Pudding (tastes like dark matter) 🍮",
                "tangled_cables": "Quantum Cable Knot (physically impossible to untangle) 🔌",
                "screaming_crystal": "Screaming Crystal (relentlessly sings 80s synth-pop) 💎",
                "moon_cheese": "Chunk of Moon Cheese (smells like sharp cheddar) 🧀",
                "golden_spatula": "Golden Spatula (maybe SpongeBob had it?) 🍳",
                "parking_ticket": "Cosmic Parking Ticket (overdue by 400 years! That's a big fine...) 📜",
                "floating_plant": "Suspicious Houseplant (stares at you when you turn around...) 🪴",
                "tinted_visor": "Broken Solar Visor (now just regular 3D glasses) 🕶️",
                "purring_lint": "Ball of Space Lint (it purrs when you touch it?) 🧶",
                "pet_rock": "Asteroid Pet Rock (includes tiny glued-on googly eyes) 🪨",
                "haunted_circuit": "Haunted Circuit Board (sparks every time you whisper near it) ⚡",
                "space_taco": "Cosmic Taco (the salsa is surprisingly unaffected by zero-G) 🌮",
                "rusty_wrench": "Rusty Wrench (still works, but squeaks a lot) 🔧",
                "alien_fossil": "Alien Fossil Fragment (looks like it could bite back) 🦴",
                "big_red_button": "A Big Red Button (labeled 'do not press', but you pressed it anyway. It did nothing...) 🔴",
                "antique_compass": "Antique Compass (points to the nearest space anomaly, which is currently a black hole) 🧭",
                "broken_clock": "Broken Clock (stuck at 3:00AM. Witching hour... spooky) ⏰",
                "perplexing_painting": "Perplexing Painting (the eyes seem to follow you, but it's a 2D image) 🖌️",
                "cosmic_banana": "Cosmic Banana (peels itself, but tastes like stardust) 🍌"
            }
            
            # --- TIERED SCAVENGING LOOT ROLL ---
            # Quantum Batteries have a 2% base chance.
            # The Deep-Space Scanner boosts that to 4%.
            # Quantum Batteries are exclusive to scavenging.
            loot_roll = random.random()
            lucky_scanner_active = effects.pop("lucky_scanner", False)

            if loot_roll >= (0.96 if lucky_scanner_active else 0.98):
                item_id = "quantum_battery"
                item_name = f"{EMOJIS.get('quantum_battery', '⚛️')} Quantum Battery (legendary)"
                item_type = "consumable"
                loot_rarity_note = (
                    "\nLegendary find: You've recovered a "
                    "**Quantum Battery**!"
                )

            elif loot_roll < (0.10 if lucky_scanner_active else 0.02) + pet_effects["rare_bonus"] + scavenging_rare_bonus:
                item_id = "revive_kit"
                item_name = f"{EMOJIS.get('revive_kit', '💉')} Emergency Revival Kit"
                item_type = "consumable"
                loot_rarity_note = ""

            elif loot_roll < (0.20 if lucky_scanner_active else 0.05) + pet_effects["rare_bonus"] + scavenging_rare_bonus:
                item_id = "laser_charge_cell"
                item_name = f"{EMOJIS.get('laser_charge_cell', '🔋')} Laser Charge Cell"
                item_type = "consumable"
                loot_rarity_note = ""

            elif loot_roll < (0.32 if lucky_scanner_active else 0.08) + pet_effects["rare_bonus"] + scavenging_rare_bonus:
                item_id = "drone_battery"
                item_name = f"{EMOJIS.get('drone_battery', '🔋')} Drone Battery Pack"
                item_type = "consumable"
                loot_rarity_note = ""

            else:
                # Normal scavenging keeps its existing Space Junk pool.
                # Halloween collectibles are handled separately as an independent
                # seasonal bonus roll below.
                item_id, item_name = random.choice(list(junk_items.items()))
                item_type = "space_junk"
                loot_rarity_note = ""

            # Arcade Tokens are an independent bonus roll during scavenging.
            # This keeps the normal scavenging loot table intact instead of
            # replacing another find when a token appears.
            bonus_discovery_findings = []
            scavenging_token_found = False
            token_overflow_stardust = 0
            if random.random() < 0.25:
                async with db.execute(
                    "SELECT COALESCE(arcade_coins, 0) FROM users WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    token_row = await cursor.fetchone()

                token_balance = (token_row[0] or 0) if token_row else 0
                token_max = 1000
                scavenging_token_found = True
                if token_balance < token_max:
                    token_quantity = token_balance + 1
                    await db.execute(
                        "UPDATE users SET arcade_coins = ? WHERE user_id = ?",
                        (token_quantity, user_id)
                    )
                    bonus_discovery_findings.append(
                        f"Arcade Token 🪙 **({token_quantity}/{token_max})**"
                    )
                else:
                    overflow_stardust = LOOT_OVERFLOW_VALUES.get("arcade_token", 50)
                    token_overflow_stardust = overflow_stardust
                    bonus_discovery_findings.append(
                        f"Arcade Token overflow: **+{overflow_stardust:,} Stardust**"
                    )

            effective_scavenge_charge_save = max(
                pet_effects["charge_save"],
                pet_effects["scavenge_charge_save"],
            )
            if effective_scavenge_charge_save and random.random() < effective_scavenge_charge_save:
                new_charges = charges
                scavenge_charge_saved = True
            else:
                new_charges = charges - 1
                scavenge_charge_saved = False
            found_stardust = int(
                random.randint(50, 450)
                * scavenging_upgrade["stardust_mult"]
                * (
                    1
                    + pet_effects["stardust_bonus"]
                    + pet_effects.get("extra_charges", 0.0)
                )
            )

            if effects.pop("quantum_battery", False):
                found_stardust *= 3
                quantum_bonus_note = "\nQuantum Battery: **Stardust tripled!**"
            else:
                quantum_bonus_note = ""

            cache_payout = 0
            cache_note = ""
            if random.random() < SCAVENGE_STARDUST_CACHE_CHANCE:
                cache_payout = random.randint(SCAVENGE_STARDUST_CACHE_MIN, SCAVENGE_STARDUST_CACHE_MAX)
                cache_note = f"\n\nStardust cache found: **+{cache_payout:,} Stardust**"

            new_stardust = stardust + found_stardust + token_overflow_stardust + cache_payout

            pet_findings = []

            if xenomorph_bonus_loot_pending:
                bonus_item_id, bonus_item_name = random.choice(list(junk_items.items()))
                bonus_amount = random.randint(1, 3)
                bonus_added, _bonus_quantity, _bonus_max = await add_inventory_item(
                    db, user_id, bonus_item_id, "space_junk", bonus_amount
                )
                if bonus_added:
                    pet_findings.append(
                        f"{get_pet_passive_message(pet_effects, 'xenomorph_bonus_loot')} **{bonus_item_name} ×{bonus_added}**"
                    )
                if bonus_amount > bonus_added:
                    overflow_value = (bonus_amount - bonus_added) * LOOT_OVERFLOW_VALUES.get(bonus_item_id, 10)
                    new_stardust += overflow_value
                    pet_findings.append(
                        f"**Xenomorph loot overflow:** **+{overflow_value:,} Stardust**"
                    )

            # 30% Environmental Hazard Chance during Scavenging.
            pet_tails_recovery = 0
            damage_taken = 0
            hazard_note = ""
            force_hazard = effects.pop("force_hazard", False)
            if (force_hazard or random.random() < 0.30) and not effects.pop("hazard_shield", False):
                hazard, min_damage, max_damage, weight = random.choices(
                    self.SCAVENGE_HAZARDS,
                    weights=[entry[3] for entry in self.SCAVENGE_HAZARDS],
                    k=1,
                )[0]
                defended, defense_weapon_id, _atomic_breath_chance, _defense_chance, defense_pet_effect_id = await roll_hazard_defense(db, user_id)
                if defended:
                    if defense_weapon_id:
                        from defense import DEFENSE_MESSAGES, DEFENSE_WEAPONS
                        defense_text = DEFENSE_MESSAGES.get(defense_weapon_id, "Your defensive weapon stopped the hazard!")
                        defense_name = DEFENSE_WEAPONS.get(defense_weapon_id, {}).get("name", "Defensive weapon")
                        hazard_note = f"\n\n**{defense_name} defense!** {defense_text}\n**0 HP damage taken.**"
                    else:
                        from defense import get_pet_defense_message
                        defense_text = get_pet_defense_message(defense_pet_effect_id)
                        defense_label = "Atomic Breath" if defense_pet_effect_id == "atomic_breath" else "Pet defense"
                        hazard_note = f"\n\n**{defense_label} defense!**\n{defense_text}\n**0 HP damage taken.**"
                elif pet_effects.get("tails_doll_red_gem", 0.0) and random.random() < pet_effects.get("tails_doll_red_gem", 0.0):
                    benefit_roll = random.random()
                    if benefit_roll < 0.34:
                        benefit = random.randint(25, 75)
                        new_stardust += benefit
                        benefit_text = f"**+{benefit} Stardust**"
                    elif benefit_roll < 0.67:
                        bonus_item_id, bonus_item_name = random.choice(list(junk_items.items()))
                        bonus_added, _bonus_quantity, _bonus_max = await add_inventory_item(
                            db, user_id, bonus_item_id, "space_junk", 1
                        )
                        if bonus_added:
                            benefit_text = f"**{bonus_item_name} ×{bonus_added}**"
                        else:
                            overflow_value = LOOT_OVERFLOW_VALUES.get(bonus_item_id, 10)
                            new_stardust += overflow_value
                            benefit_text = f"**+{overflow_value} Stardust** from overflow"
                    else:
                        recovery = random.randint(4, 8)
                        old_hp = hp
                        # This is a converted hazard, so the recovery can restore a little HP.
                        new_hp_preview = min(max_hp, hp + recovery)
                        benefit_text = f"**+{new_hp_preview - old_hp} HP**" if new_hp_preview > old_hp else "a small recovery"
                        # Apply immediately after hazard processing by carrying the target forward.
                        pet_tails_recovery = new_hp_preview - old_hp
                    tails_message = get_pet_passive_message(pet_effects, "tails_doll_red_gem")
                    if 'pet_tails_recovery' not in locals():
                        pet_tails_recovery = 0
                    hazard_note = f"\n\n{tails_message}\n**Hazard converted into:** {benefit_text}"
                elif pet_effects.get("kolossos_hunting_instinct", 0.0) and random.random() < pet_effects.get("kolossos_hunting_instinct", 0.0):
                    if random.random() < 0.40:
                        hazard_note = (
                            f"\n\n{get_pet_passive_message(pet_effects, 'kolossos_hunting_instinct')}\n"
                            "**Kolossos has completely negated the hazard.**\n"
                            "**Hunting Instinct:** Your next activity has a **+20% loot-finding chance**."
                        )
                        effects["kolossos_next_loot_bonus"] = 0.20
                    else:
                        base_damage = random.randint(min_damage, max_damage)
                        damage_taken = max(1, int(base_damage * 0.50 * (1 - pet_effects["hazard_reduction"])))
                        effects["kolossos_next_loot_bonus"] = 0.20
                        hazard_note = (
                            f"\n\n{get_pet_passive_message(pet_effects, 'kolossos_hunting_instinct')}\n"
                            f"**Hazard reduced to -{damage_taken} HP.**\n"
                            "**Hunting Instinct:** Your next activity has a **+20% loot-finding chance**."
                        )
                elif pet_effects.get("xenomorph_ambush", 0.0) and random.random() < pet_effects.get("xenomorph_ambush", 0.0):
                    if random.random() < 0.75:
                        hazard_note = (
                            f"\n\n{get_pet_passive_message(pet_effects, 'xenomorph_ambush')}\n"
                            "**The hazard was completely stopped in its tracks.**"
                        )
                    else:
                        base_damage = random.randint(min_damage, max_damage)
                        damage_taken = max(1, int(base_damage * 0.25 * (1 - pet_effects["hazard_reduction"])))
                        hazard_note = (
                            f"\n\n{get_pet_passive_message(pet_effects, 'xenomorph_ambush')}\n"
                            f"**Hazard reduced to -{damage_taken}HP.**"
                        )
                    if random.random() < 0.50:
                        xenomorph_bonus_loot_pending = True
                elif pet_effects.get("siren_false_signal", 0.0) and random.random() < pet_effects.get("siren_false_signal", 0.0):
                    warning_message = get_pet_passive_message(pet_effects, "siren_false_signal")
                    if random.random() < 0.40:
                        hazard_note = (
                            f"\n\n{warning_message}\n"
                            f"{get_pet_passive_message(pet_effects, 'siren_false_signal_avoid')}\n"
                            "**0 HP damage taken.**"
                        )
                    else:
                        hazard_note = f"\n\n{warning_message}\n**The warning came too late.**\n"
                        if halloween_is_active() and HALLOWEEN_DAMAGE_MESSAGES:
                            halloween_message, halloween_min_damage, halloween_max_damage = random.choice(HALLOWEEN_DAMAGE_MESSAGES)
                            hazard = halloween_message
                            damage_taken = max(1, int(random.randint(halloween_min_damage, halloween_max_damage) * (1 - pet_effects["hazard_reduction"])))
                        else:
                            damage_taken = max(1, int(random.randint(min_damage, max_damage) * (1 - pet_effects["hazard_reduction"])))
                        hazard_note += f"**You {hazard} and took -{damage_taken}HP.**"
                elif pet_effects["scavenge_hazard_avoidance"] and random.random() < pet_effects["scavenge_hazard_avoidance"]:
                    pet_warning = get_pet_passive_message(
                        pet_effects, "scavenge_hazard_avoidance"
                    )
                    hazard_note = (
                        f"\n\n{pet_warning}\n**0 HP damage taken.**"
                    )
                elif halloween_is_active() and HALLOWEEN_DAMAGE_MESSAGES:
                    halloween_message, halloween_min_damage, halloween_max_damage = random.choice(HALLOWEEN_DAMAGE_MESSAGES)
                    hazard = halloween_message
                    damage_taken = max(1, int(random.randint(halloween_min_damage, halloween_max_damage) * (1 - pet_effects["hazard_reduction"])))
                    hazard_note = f"\n\n**Hazard inflicted!** You {hazard} and took **-{damage_taken}HP**."
                else:
                    damage_taken = max(1, int(random.randint(min_damage, max_damage) * (1 - pet_effects["hazard_reduction"])))
                    hazard_note = f"\n\n**Hazard inflicted!** You {hazard} and took **-{damage_taken}HP**."

            new_hp = max(0, hp - damage_taken)
            if pet_tails_recovery > 0:
                new_hp = min(max_hp, new_hp + pet_tails_recovery)
            if (
                damage_taken > 0
                and pet_effects["scavenge_first_aid"]
                and random.random() < pet_effects["scavenge_first_aid"]
            ):
                recovered_hp = random.randint(4, 8)
                old_hp_after_hazard = new_hp
                new_hp = min(max_hp, new_hp + recovered_hp)
                actual_recovery = new_hp - old_hp_after_hazard
                if actual_recovery > 0:
                    pet_first_aid = get_pet_passive_message(
                        pet_effects, "scavenge_first_aid"
                    )
                    hazard_note += (
                        f"\n\n{pet_first_aid} **+{actual_recovery}HP**."
                    )

            if new_hp <= 0 and effects.pop("cosmic_insurance", False):
                new_hp = 1
                hazard_note += "\n\n**Cosmic Insurance:** Your coverage kept you at **1HP**. Pretty sure this isn't how insurance works..?"

            knocked_out_until = ""
            if new_hp <= 0:
                knocked_out_until = (self.game_date() + timedelta(days=1)).isoformat()
                knockout_lines = HALLOWEEN_KNOCKOUT_LINES if halloween_is_active() and HALLOWEEN_KNOCKOUT_LINES else self.KNOCKOUT_LINES
                hazard_note += f"\n\n**Knockout report:** {random.choice(knockout_lines)}"

            added_amount, new_quantity, max_quantity = await add_inventory_item(
                db,
                user_id,
                item_id,
                item_type,
                1
            )
            salvage_material_findings = []
            medical_supply_findings = []
            bonus_mineral_findings = []
            seasonal_findings = []
            bonus_overflow_findings = []

            # Some Haunted pets have a permanent, year-round scavenging passive
            # that can find an additional miscellaneous Space Junk item.
            if pet_effects["scavenge_bonus_loot"] and random.random() < pet_effects["scavenge_bonus_loot"]:
                pet_bonus_loot_message = get_pet_passive_message(
                    pet_effects, "scavenge_bonus_loot"
                )
                bonus_item_id, bonus_item_name = random.choice(list(junk_items.items()))
                bonus_added, bonus_quantity, bonus_max = await add_inventory_item(
                    db, user_id, bonus_item_id, "space_junk", 1
                )
                if bonus_added:
                    pet_findings.append(
                        f"{pet_bonus_loot_message} {bonus_item_name} ×{bonus_added}"
                    )
                else:
                    overflow_stardust = LOOT_OVERFLOW_VALUES.get(bonus_item_id, 10)
                    new_stardust += overflow_stardust
                    pet_findings.append(
                        f"{bonus_item_name} → Inventory Full (+{overflow_stardust:,} Stardust)"
                    )

            # MissingNo. rarely corrupts the current scavenging reward data.
            if pet_effects.get("missingno_error", 0.0) and random.random() < pet_effects.get("missingno_error", 0.0):
                glitch_roll = random.random()
                if glitch_roll < 0.70:
                    glitch_amount = random.randint(1, 5)
                    glitch_effect_id = "missingno_error_small"
                elif glitch_roll < 0.95:
                    glitch_amount = random.randint(10, 15)
                    glitch_effect_id = "missingno_error_major"
                else:
                    glitch_amount = random.randint(100, 500)
                    glitch_effect_id = "missingno_error_stardust"

                if glitch_effect_id == "missingno_error_stardust":
                    new_stardust += glitch_amount
                    pet_findings.append(
                        f"{get_pet_passive_message(pet_effects, glitch_effect_id)} **+{glitch_amount:,} Stardust**"
                    )
                else:
                    glitch_item_id, glitch_item_name = random.choice(list(junk_items.items()))
                    added_glitch, _glitch_quantity, _glitch_max = await add_inventory_item(
                        db, user_id, glitch_item_id, "space_junk", glitch_amount
                    )
                    if added_glitch:
                        pet_findings.append(
                            f"{get_pet_passive_message(pet_effects, glitch_effect_id)} **{glitch_item_name} ×{added_glitch}**"
                        )
                    overflow_glitch = glitch_amount - added_glitch
                    if overflow_glitch > 0:
                        overflow_value = overflow_glitch * LOOT_OVERFLOW_VALUES.get(glitch_item_id, 10)
                        new_stardust += overflow_value
                        pet_findings.append(
                            f"Glitched overflow → **+{overflow_value:,} Stardust**"
                        )

            # Seasonal Halloween resources are independent bonus rolls and never
            # replace the normal scavenging loot.
            halloween_active = halloween_is_active()

            # Halloween Space Junk collectibles can very rarely be uncovered while
            # scavenging. This is independent of the normal loot roll and is much
            # rarer than finding collectibles through Haunted Exploration.
            if halloween_active and random.random() < SCAVENGE_HALLOWEEN_COLLECTIBLE_CHANCE:
                (
                    collectible_id,
                    collectible_name,
                    collectible_emoji,
                    collectible_desc,
                    _collectible_stardust,
                    _collectible_candy,
                ) = random.choice(HALLOWEEN_SPACE_JUNK)
                added_collectible, collectible_quantity, collectible_max = await add_inventory_item(
                    db, user_id, collectible_id, "space_junk", 1
                )

                # Seasonal collectible discoveries are permanent. For usable
                # collectibles, only show the usage reminder the first time the
                # collectible is actually added/discovered for this user.
                first_discovery = False
                if added_collectible:
                    first_discovery = await record_collectible(
                        db, self.bot, user_id, collectible_id, category="Halloween", channel=ctx.channel
                    )

                collectible_lines = [
                    f"**Halloween collectible found! 👻 {collectible_emoji} {collectible_name}"
                    + (" → inventory full" if not added_collectible else "") + "**",
                    "━━━━━━━━━━━━━━━━━━━━━━━━",
                    f"*{collectible_desc}*",
                ]

                use_config = HALLOWEEN_SPECIAL_USE_ITEMS.get(collectible_id)
                if (
                    first_discovery
                    and isinstance(use_config, dict)
                    and use_config.get("enabled")
                ):
                    collectible_lines.extend([
                        "",
                        "**Usable collectible found!**",
                        "Use `/use item: [item name]` to activate this collectible.",
                    ])

                seasonal_findings.append("\n".join(collectible_lines))

            # Pet eggs are independent bonus rolls and never replace normal loot.
            # During Halloween, normal eggs are intentionally reduced to 3%
            # while the seasonal eggs become more common. After Halloween, the
            # normal egg automatically returns to its regular NORMAL_EGG_CHANCE.
            # Seasonal eggs automatically stop dropping when Halloween ends.
            egg_rolls = []
            if halloween_active:
                if random.random() < 0.03:
                    egg_rolls.append("normal_egg")
                if random.random() < 0.10:
                    egg_rolls.append("halloween_egg")
                if random.random() < 0.08:
                    egg_rolls.append("glitched_egg")
            elif random.random() < NORMAL_EGG_CHANCE:
                egg_rolls.append("normal_egg")

            for egg_id in egg_rolls:
                egg_info = ITEM_REGISTRY.get(egg_id, {"name": egg_id, "emoji": "🥚"})
                added_egg, egg_quantity, egg_max = await add_inventory_item(
                    db, user_id, egg_id, "pet_egg", 1
                )
                if added_egg:
                    pet_findings.append(
                        f"{egg_info['emoji']} **You've found a {egg_info['name']}!** — use `/incubator Start incubation:{egg_id} tube:` to hatch it!"
                    )
                else:
                    pet_findings.append(
                        f"{egg_info['emoji']} {egg_info['name']} → inventory full"
                    )

            # Halloween resources are independent bonus rolls and never replace normal loot.
            candy_doubled = False
            if halloween_active and random.random() < HALLOWEEN_SCAVENGING_CANDY_CHANCE:
                candy_found = random.randint(3, 15)

                # Sam's Trick-or-Treating passive can double the base candy haul.
                if pet_effects["candy_bonus"] and random.random() < pet_effects["candy_bonus"]:
                    candy_found *= 2
                    candy_doubled = True


                if (
                    pet_effects["halloween_bonus"]
                    and random.random() < pet_effects["halloween_bonus"]
                ):
                    candy_found += 1

                added_candy, candy_quantity, candy_max = await add_inventory_item(
                    db, user_id, "halloween_candy", "consumable", candy_found
                )
                overflow_candy = candy_found - added_candy
                if added_candy:
                    candy_note = f"**{EMOJIS.get('halloween_candy', '🍬')} Halloween Candy ×{added_candy}**"
                    if candy_doubled:
                        candy_note += " (Samhain bonus!)"
                    seasonal_findings.append(candy_note)
                if overflow_candy > 0:
                    candy_overflow_stardust = overflow_candy * 2
                    new_stardust += candy_overflow_stardust
                    seasonal_findings.append(
                        f"Candy overflow: **×{overflow_candy} → +{candy_overflow_stardust} Stardust**"
                    )

            if halloween_active and random.random() < HALLOWEEN_PLASTIC_CHANCE:
                plastic_found = random.randint(HALLOWEEN_PLASTIC_MIN, HALLOWEEN_PLASTIC_MAX)
                added_plastic, plastic_quantity, plastic_max = await add_inventory_item(
                    db, user_id, "halloween_plastic", "crafting_material", plastic_found
                )
                if added_plastic:
                    seasonal_findings.append(f"**Halloween Plastic ×{added_plastic}**")
                overflow_plastic = plastic_found - added_plastic
                if overflow_plastic:
                    new_stardust += overflow_plastic * 2
                    seasonal_findings.append(f"Plastic overflow: **×{overflow_plastic} → +{overflow_plastic * 2} Stardust**")

            # A Trick-or-Treat Bag is an especially rare direct seasonal find.
            if halloween_active and random.random() < HALLOWEEN_BAG_CHANCE:
                added_bag, bag_quantity, bag_max = await add_inventory_item(
                    db, user_id, "trick_or_treat_bag", "consumable", 1
                )
                if added_bag:
                    seasonal_findings.append(f"**Trick-or-Treat Bag ×{added_bag}**")
                else:
                    seasonal_findings.append(f"**Trick-or-Treat Bag** → inventory full")

            # Scavenging can recover multiple types of crafting material in one run.
            # Incubator materials yield 1–2 units and are capped at two
            # different incubator materials per run.
            #
            # Salvage Rig bonus is a relative chance multiplier:
            # +10% turns a 20% base chance into 22%, while +65% turns it
            # into 33%. This keeps higher tiers meaningful without making
            # common materials nearly guaranteed.
            incubator_material_ids = {
                "quantum_coil",
                "astral_lens",
                "mutation_catalyst",
                "analysis_module",
            }
            incubator_materials_found = 0
            material_rolls = list(SCAVENGE_MATERIALS)
            random.shuffle(material_rolls)
            for material_id, material_name, chance in material_rolls:
                is_incubator_material = material_id in incubator_material_ids
                if is_incubator_material and incubator_materials_found >= 2:
                    continue
                effective_material_chance = min(1.0, chance * (1 + salvage_bonus_chance))
                if random.random() < effective_material_chance:
                    if is_incubator_material:
                        amount_found = random.randint(1, 2)
                        incubator_materials_found += 1
                    else:
                        amount_found = random.randint(1, 5)
                    effective_scavenge_material_bonus = max(
                        pet_effects["material_bonus"],
                        pet_effects["scavenge_material_bonus"],
                    )
                    material_bonus_triggered = (
                        bool(effective_scavenge_material_bonus)
                        and random.random() < effective_scavenge_material_bonus
                    )
                    if material_bonus_triggered:
                        amount_found += random.randint(1, 3)
                    added_material, material_quantity, material_max = await add_inventory_item(
                        db, user_id, material_id, "crafting_material", amount_found
                    )
                    overflow_amount = amount_found - added_material
                    if added_material:
                        salvage_material_findings.append(
                            f"{material_name} ×{added_material}"
                        )
                    if material_bonus_triggered:
                        pet_findings.append(
                            get_pet_passive_message(pet_effects, "material_bonus")
                        )
                    if overflow_amount > 0:
                        overflow_stardust = overflow_amount * MATERIAL_OVERFLOW_VALUES.get(material_id, 0)
                        new_stardust += overflow_stardust
                        bonus_overflow_findings.append(
                            f"{material_name} ×{overflow_amount} → +{overflow_stardust} Stardust"
                        )

            # Scavengers can also recover individual medical supplies for makeshift kits.
            for supply_id, supply_name, chance in SCAVENGE_MEDICAL_SUPPLIES:
                effective_supply_chance = min(1.0, chance * (1 + salvage_bonus_chance))
                if random.random() < effective_supply_chance:
                    added_supply, supply_quantity, supply_max = await add_inventory_item(
                        db, user_id, supply_id, "medical_supply", 1
                    )
                    if added_supply:
                        medical_supply_findings.append(
                            f"{supply_name} ×{added_supply}"
                        )
                    else:
                        overflow_stardust = LOOT_OVERFLOW_VALUES.get(supply_id, 5)
                        new_stardust += overflow_stardust
                        bonus_overflow_findings.append(
                            f"{supply_name} → +{overflow_stardust} Stardust"
                        )

            # Very rarely, a scavenger can uncover multiple minerals as bonus finds.
            # These are independent rolls, so more than one type can appear.
            if random.random() < 0.08:
                for mineral_id, mineral_name, chance in SCAVENGE_BONUS_MINERALS:
                    effective_mineral_chance = min(1.0, chance * (1 + salvage_bonus_chance))
                    if random.random() < effective_mineral_chance:
                        amount_found = random.randint(1, 5)
                        effective_scavenge_material_bonus = max(
                            pet_effects["material_bonus"],
                            pet_effects["scavenge_material_bonus"],
                        )
                        material_bonus_triggered = (
                            bool(effective_scavenge_material_bonus)
                            and random.random() < effective_scavenge_material_bonus
                        )
                        if material_bonus_triggered:
                            amount_found += random.randint(1, 3)
                        added_mineral, mineral_quantity, mineral_max = await add_inventory_item(
                            db, user_id, mineral_id, "mineral", amount_found
                        )
                        overflow_amount = amount_found - added_mineral
                        if added_mineral:
                            bonus_mineral_findings.append(
                                f"{mineral_name} ×{added_mineral}"
                            )
                        if material_bonus_triggered:
                            pet_findings.append(
                                get_pet_passive_message(pet_effects, "material_bonus")
                            )
                        if overflow_amount > 0:
                            overflow_stardust = overflow_amount * MATERIAL_OVERFLOW_VALUES.get(mineral_id, 0)
                            new_stardust += overflow_stardust
                            bonus_overflow_findings.append(
                                f"{mineral_name} ×{overflow_amount} → +{overflow_stardust} Stardust"
                            )

            if added_amount == 1:
                loot_name_with_quantity = f"**{item_name} ({new_quantity}/{max_quantity})**"
            else:
                # ─────────────────────────────────────────────
                # SCAVENGE OVERFLOW VALUES
                # Adjust these Stardust values individually as desired.
                # ─────────────────────────────────────────────
                # Use the item's individual overflow value.
                # The fallback protects against a newly added loot item
                # accidentally having no configured overflow value.
                overflow_stardust = LOOT_OVERFLOW_VALUES.get(item_id, 10)

                new_stardust += overflow_stardust

                loot_name_with_quantity = (
                    f"**{item_name}**\n"
                    f"*Inventory full!* stack is already "
                    f"**{max_quantity}/{max_quantity}**!"
                    f"\n*It has been converted to:* **+{overflow_stardust:,} Stardust**"
                )

            # Group bonus discoveries into readable single-line sections rather than
            # repeating "Salvage Material:" / "Medical Supply:" for every item.
            pet_stardust_message = (
                get_pet_passive_message(pet_effects, "stardust_bonus")
                if pet_effects["stardust_bonus"]
                else ""
            )
            materials_and_supplies = []
            if salvage_material_findings:
                materials_and_supplies.extend(salvage_material_findings)
            if medical_supply_findings:
                materials_and_supplies.extend(medical_supply_findings)
            if bonus_mineral_findings:
                materials_and_supplies.extend(bonus_mineral_findings)

            special_findings = []
            if bonus_discovery_findings:
                special_findings.extend(bonus_discovery_findings)
            if loot_rarity_note:
                special_findings.extend(
                    line for line in loot_rarity_note.split("\n") if line
                )
            if pet_stardust_message:
                special_findings.append(pet_stardust_message)
            if pet_findings:
                special_findings.extend(line for line in pet_findings if line)
            if scavenge_charge_saved:
                charge_effect_id = (
                    "scavenge_charge_save"
                    if pet_effects["scavenge_charge_save"]
                    else "charge_save"
                )
                special_findings.append(get_pet_passive_message(pet_effects, charge_effect_id))
            if seasonal_findings:
                special_findings.extend(line for line in seasonal_findings if line)
            if bonus_overflow_findings:
                special_findings.extend(bonus_overflow_findings)

            materials_and_supplies_text = (
                "Salvaged materials & supplies: "
                + " • ".join(f"**{finding}**" for finding in materials_and_supplies)
                if materials_and_supplies
                else ""
            )
            special_findings_text = (
                "\n\n" + EXPLORATION_SEPARATOR + "\n\n"
                + "Special findings: " + " • ".join(special_findings)
                if special_findings
                else ""
            )

            pet_xp_result = await add_pet_xp(db, user_id, roll_normal_exploration_pet_xp())

            await db.execute("""
                UPDATE users 
                SET scavenge_charges = ?, last_scavenged = ?, stardust = ?, hp = ?, knocked_out_until = ?, active_effects = ?
                WHERE user_id = ?
            """, (new_charges, current_time, new_stardust, new_hp, knocked_out_until, json.dumps(effects), user_id))

            await db.commit()

        status_text = (
            EXPLORATION_TEXT["scavenging"]["health_status"].format(hp=new_hp, max_hp=max_hp)
            if new_hp > 0
            else EXPLORATION_TEXT["scavenging"]["knocked_out_status"].format(until=knocked_out_until)
        )

        embed = discord.Embed(
            title=EXPLORATION_TEXT["scavenging"]["title"].format(display_name=ctx.author.display_name),
            description=EXPLORATION_TEXT["scavenging"]["description"].format(
                stardust=found_stardust,
                quantum_note=f"*{quantum_bonus_note}*",
                cache_note=cache_note,
                loot=loot_name_with_quantity,
                rarity_note=loot_rarity_note,
                materials_and_supplies=materials_and_supplies_text,
                special_findings=special_findings_text,
                hazard_note=hazard_note,
                status=status_text,
            ),
            color=discord.Color.dark_gold()
        )
        cooldown_total_seconds = max(0, int(round(effective_cooldown)))
        cooldown_minutes, cooldown_seconds = divmod(cooldown_total_seconds, 60)
        cooldown_text = f"{cooldown_minutes}m" if cooldown_seconds == 0 else f"{cooldown_minutes}m {cooldown_seconds}s"
        embed.set_footer(text=EXPLORATION_TEXT["scavenging"]["footer"].format(charges=new_charges, max_charges=max_scavenge_charges, cooldown=cooldown_text))
        if pet_xp_result:
            pet_xp_text = EXPLORATION_TEXT["scavenging"]["pet_xp"].format(xp=pet_xp_result["xp_added"])
            if pet_xp_result["leveled_up"]:
                pet_xp_text += EXPLORATION_TEXT["scavenging"]["pet_level"].format(level=pet_xp_result["new_level"])
            embed.add_field(
                name=EXPLORATION_TEXT["scavenging"]["pet_progress"],
                value=pet_xp_text,
                inline=False,
            )

        if random.random() < 0.25 and await self.daily_unclaimed(user_id):
            embed.add_field(
                name=EXPLORATION_TEXT["scavenging"]["daily_name"],
                value=EXPLORATION_TEXT["scavenging"]["daily_value"],
                inline=False
            )

        cooldown_reminder = await self.maybe_suggest_cooldown_alerts(ctx)
        if cooldown_reminder:
            embed.add_field(
                name=EXPLORATION_TEXT["scavenging"]["cooldown_name"],
                value=cooldown_reminder,
                inline=False
            )

        await ctx.send(content=ctx.author.mention, embed=embed)

    @commands.hybrid_command(
        name="revive",
        description="Choose a revival item to return to consciousness."
    )
    async def revive(self, ctx: commands.Context):
        await ctx.defer()

        user_id = ctx.author.id
        lock = self._user_locks.setdefault(user_id, asyncio.Lock())

        async with lock:
            return await self._revive_impl(ctx)

    async def _revive_impl(self, ctx: commands.Context):
        user_id = ctx.author.id

        async with aiosqlite.connect(self.get_db_path()) as db:
            await self.ensure_schema(db)
            await self.recover_if_new_day(db, user_id)

            async with db.execute(
                "SELECT hp, max_hp FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                user = await cursor.fetchone()

            if not user:
                return await ctx.send(
                    f"{ctx.author.mention} Profile not found!"
                )

            hp, max_hp = user[0] or 0, user[1] or 100

            if hp > 0:
                return await ctx.send(
                    f"{ctx.author.mention} You are already conscious and do not need a revival."
                )

            async with db.execute(
                """
                SELECT item_id, quantity
                FROM inventory
                WHERE user_id = ?
                  AND item_id IN ('revive', 'revive_kit', 'full_revive')
                  AND quantity > 0
                """,
                (user_id,)
            ) as cursor:
                inventory_rows = await cursor.fetchall()

            available = {
                item_id: quantity
                for item_id, quantity in inventory_rows
            }

        # ─────────────────────────────────────────────
        # REVIVAL SELECTION VIEW
        # ─────────────────────────────────────────────

        exploration = self

        class RevivalView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)

                revive_button = discord.ui.Button(
                    label="Revival Kit",
                    emoji=EMOJIS.get("revive", "⚕️"),
                    style=discord.ButtonStyle.secondary,
                    disabled=available.get("revive", 0) <= 0
                )
                revive_button.callback = self.use_revive_kit
                self.add_item(revive_button)

                kit_button = discord.ui.Button(
                    label="Emergency Revival Kit",
                    emoji=EMOJIS.get("revive_kit", "💉"),
                    style=discord.ButtonStyle.primary,
                    disabled=available.get("revive_kit", 0) <= 0
                )
                kit_button.callback = self.use_emergency_kit
                self.add_item(kit_button)

                full_button = discord.ui.Button(
                    label="Emergency Full Revival",
                    emoji=EMOJIS.get("full_revive", "🚑"),
                    style=discord.ButtonStyle.success,
                    disabled=available.get("full_revive", 0) <= 0
                )
                full_button.callback = self.use_full
                self.add_item(full_button)

            async def use_revive_kit(self, interaction: discord.Interaction):
                await self.use_revive(interaction, "revive", 0.35)

            async def use_emergency_kit(self, interaction: discord.Interaction):
                await self.use_revive(interaction, "revive_kit", 0.50)

            async def use_full(self, interaction: discord.Interaction):
                await self.use_revive(interaction, "full_revive", 1.00)

            async def use_revive(
                self,
                interaction: discord.Interaction,
                item_id: str,
                heal_percent: float
            ):
                if interaction.user.id != user_id:
                    return await interaction.response.send_message(
                        "This revival menu belongs to someone else.",
                        ephemeral=True
                    )

                await interaction.response.defer()

                async with aiosqlite.connect(
                    exploration.get_db_path()
                ) as db:
                    await exploration.ensure_schema(db)

                    async with db.execute(
                        "SELECT hp, max_hp FROM users WHERE user_id = ?",
                        (user_id,)
                    ) as cursor:
                        user_row = await cursor.fetchone()

                    if not user_row:
                        return await interaction.followup.send(
                            "Profile not found!",
                            ephemeral=True
                        )

                    current_hp, max_hp = (
                        user_row[0] or 0,
                        user_row[1] or 100
                    )

                    if current_hp > 0:
                        return await interaction.followup.send(
                            "You are already conscious!",
                            ephemeral=True
                        )

                    async with db.execute(
                        """
                        SELECT quantity
                        FROM inventory
                        WHERE user_id = ?
                          AND item_id = ?
                        """,
                        (user_id, item_id)
                    ) as cursor:
                        item_row = await cursor.fetchone()

                    if not item_row or (item_row[0] or 0) <= 0:
                        item_name = {
                            "revive": "Revival Kit",
                            "revive_kit": "Emergency Revival Kit",
                            "full_revive": "Emergency Full Revival",
                        }.get(item_id, item_id)

                        return await interaction.followup.send(
                            f"You don't have an **{item_name}**!",
                            ephemeral=True
                        )

                    # Consume exactly one revival item.
                    if item_row[0] > 1:
                        await db.execute(
                            """
                            UPDATE inventory
                            SET quantity = quantity - 1
                            WHERE user_id = ?
                              AND item_id = ?
                            """,
                            (user_id, item_id)
                        )
                    else:
                        await db.execute(
                            """
                            DELETE FROM inventory
                            WHERE user_id = ?
                              AND item_id = ?
                            """,
                            (user_id, item_id)
                        )

                    if heal_percent >= 1.0:
                        recovered_hp = max_hp
                    else:
                        recovered_hp = max(
                            1,
                            (max_hp + 1) // 2
                        )

                    await db.execute(
                        """
                        UPDATE users
                        SET hp = ?,
                            knocked_out_until = ''
                        WHERE user_id = ?
                        """,
                        (recovered_hp, user_id)
                    )

                    await db.commit()

                item_name = {
                    "revive": "Revival Kit",
                    "revive_kit": "Emergency Revival Kit",
                    "full_revive": "Emergency Full Revival",
                }.get(item_id, item_id)

                if heal_percent >= 1.0:
                    message = (
                        f"**Full revival complete!**\n"
                        f"Your **{item_name}** restored you to "
                        f"❤️ **{recovered_hp}/{max_hp}HP**!"
                    )
                else:
                    message = (
                        f"**Revival complete!**\n"
                        f"Your **{item_name}** restored you to "
                        f"❤️ **{recovered_hp}/{max_hp}HP**!"
                    )

                await interaction.edit_original_response(
                    content=message,
                    view=None
                )

        if not available:
            return await ctx.send(
                "You don't have any revival items.\n"
                "You can buy an **Emergency Full Revival** from "
                "`/shop buy`, or recover automatically at 12:00AM EST."
            )

        embed = discord.Embed(
            title=EXPLORATION_TEXT["revival"]["title"].format(mention=ctx.author.mention),
            description=EXPLORATION_TEXT["revival"]["description"],
            color=discord.Color.red()
        )

        revive_count = available.get("revive", 0)
        kit_count = available.get("revive_kit", 0)
        full_count = available.get("full_revive", 0)

        embed.add_field(
            name=f"{EMOJIS.get('revive', '⚕️')} " + EXPLORATION_TEXT["revival"]["revive_kit_name"],
            value=EXPLORATION_TEXT["revival"]["revive_kit_value"].format(count=revive_count),
            inline=True
        )

        embed.add_field(
            name=f"{EMOJIS.get('revive_kit', '💉')} " + EXPLORATION_TEXT["revival"]["emergency_kit_name"],
            value=EXPLORATION_TEXT["revival"]["emergency_kit_value"].format(count=kit_count),
            inline=True
        )

        embed.add_field(
            name=f"{EMOJIS.get('full_revive', '🚑')} " + EXPLORATION_TEXT["revival"]["full_revive_name"],
            value=EXPLORATION_TEXT["revival"]["full_revive_value"].format(count=full_count),
            inline=True
        )

        embed.set_footer(
            text=EXPLORATION_TEXT["revival"]["expired_footer"]
        )

        await ctx.send(
            embed=embed,
            view=RevivalView()
        )

class HauntedLocationView(discord.ui.View):
    def __init__(self, cog, owner_id):
        super().__init__(timeout=90)
        self.cog = cog
        self.owner_id = owner_id

        for index, (location_id, location) in enumerate(HAUNTED_LOCATIONS.items()):
            self.add_item(HauntedLocationButton(self.cog, self.owner_id, location_id, location, index))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "**This Haunted Exploration isn't yours.**\n"
                "These buttons belong to another player's exploration run.",
                ephemeral=True,
            )
            return False

        if not is_halloween_channel(interaction.channel):
            await interaction.response.send_message(halloween_channel_message(), ephemeral=True)
            return False
        if not halloween_is_active():
            await interaction.response.send_message(EXPLORATION_TEXT["haunted"]["dormant_short"], ephemeral=True)
            return False
        return True


class HauntedLocationButton(discord.ui.Button):
    def __init__(self, cog, owner_id, location_id, location, index):
        super().__init__(
            label=location["name"],
            emoji=location["emoji"],
            style=discord.ButtonStyle.secondary,
            row=index // 5,
        )
        self.cog = cog
        self.owner_id = owner_id
        self.location_id = location_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "**This Haunted Exploration isn't yours.**\n"
                "These buttons belong to another player's exploration run.",
                ephemeral=True,
            )
            return

        # A Haunted run performs several database operations before the
        # adventure screen can be rendered. Acknowledge the button immediately
        # so Discord does not time out the interaction while that work runs.
        await interaction.response.defer()
        await self.cog._start_haunted_run(interaction, self.location_id)


class HauntedInfoButton(discord.ui.Button):
    def __init__(self, cog):
        super().__init__(
            label="Info",
            emoji="📖",
            style=discord.ButtonStyle.primary,
            row=3,
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=self.cog._haunted_info_embed(),
            ephemeral=True,
        )


class HauntedStoryView(discord.ui.View):
    def __init__(self, cog, owner_id, location_id, stage, total_stages, scene_id):
        super().__init__(timeout=600)
        self.cog = cog
        self.owner_id = owner_id
        self.location_id = location_id
        self.stage = stage
        self.total_stages = total_stages
        self.scene_id = scene_id

        # The scene is read from the authored story data so the button labels
        # are always the same labels shown by the engine.
        from seasonal_updates.halloween.haunted_system import get_scene
        _, scene = get_scene(location_id, scene_id)
        for index, choice in enumerate(scene["choices"]):
            label = choice.get("label", "Choose")
            risk = choice.get("risk", "medium")
            self.add_item(
                HauntedStoryChoiceButton(
                    self.cog,
                    self.owner_id,
                    self.location_id,
                    self.stage,
                    self.total_stages,
                    self.scene_id,
                    index,
                    label,
                    risk,
                )
            )

        self.add_item(
            HauntedRunButton(
                self.cog,
                self.owner_id,
                self.location_id,
                self.stage,
                self.total_stages,
                self.scene_id,
            )
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "**This Haunted Exploration isn't yours.**\n"
                "These buttons belong to another player's exploration run.",
                ephemeral=True,
            )
            return False

        if not is_halloween_channel(interaction.channel):
            await interaction.response.send_message(halloween_channel_message(), ephemeral=True)
            return False
        if not halloween_is_active():
            await interaction.response.send_message(EXPLORATION_TEXT["haunted"]["dormant_short"], ephemeral=True)
            return False
        return True


class HauntedStoryChoiceButton(discord.ui.Button):
    def __init__(self, cog, owner_id, location_id, stage, total_stages, scene_id, index, label, risk="medium"):
        styles = {
            "low": discord.ButtonStyle.secondary,
            "medium": discord.ButtonStyle.primary,
            "high": discord.ButtonStyle.danger,
            "extreme": discord.ButtonStyle.danger,
        }
        super().__init__(label=label, style=styles.get(risk, discord.ButtonStyle.secondary), row=0)
        self.cog = cog
        self.owner_id = owner_id
        self.location_id = location_id
        self.stage = stage
        self.total_stages = total_stages
        self.scene_id = scene_id
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "**This Haunted Exploration isn't yours.**\n"
                "These buttons belong to another player's exploration run.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        await self.cog._resolve_haunted_choice(
            interaction,
            self.owner_id,
            self.location_id,
            self.stage,
            self.total_stages,
            self.scene_id,
            self.index,
        )


class HauntedRunButton(discord.ui.Button):
    def __init__(self, cog, owner_id, location_id, stage, total_stages, scene_id):
        super().__init__(
            label="Run Away",
            emoji="🏃",
            style=discord.ButtonStyle.danger,
            row=1,
        )
        self.cog = cog
        self.owner_id = owner_id
        self.location_id = location_id
        self.stage = stage
        self.total_stages = total_stages
        self.scene_id = scene_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "**This Haunted Exploration isn't yours.**\n"
                "These buttons belong to another player's exploration run.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        await self.cog._run_away_haunted(
            interaction,
            self.owner_id,
            self.location_id,
            self.stage,
            self.total_stages,
        )


async def setup(bot):
    await bot.add_cog(Exploration(bot))
