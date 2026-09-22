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
from inventory import add_inventory_item, ITEM_REGISTRY
from seasonal_updates.halloween.halloween import (
    CANDY_CHANCE as HALLOWEEN_CANDY_CHANCE,
    PLASTIC_CHANCE as HALLOWEEN_PLASTIC_CHANCE,
    TRICK_OR_TREAT_BAG_CHANCE as HALLOWEEN_BAG_CHANCE,
    PLASTIC_MIN as HALLOWEEN_PLASTIC_MIN,
    PLASTIC_MAX as HALLOWEEN_PLASTIC_MAX,
    HALLOWEEN_DAMAGE_MESSAGES,
    HALLOWEEN_KNOCKOUT_LINES,
    is_active as halloween_is_active,
    HALLOWEEN_PET_EGG_CHANCE,
    HALLOWEEN_PET_CANDY_CHANCE,
    halloween_channel_message,
    is_halloween_channel,
)
from pets import (
    add_pet_xp,
    get_active_pet_effects,
    get_haunted_exploration_pet_xp,
    grant_haunted_pet,
    NORMAL_EGG_CHANCE,
    roll_normal_exploration_pet_xp,
)
from defense import roll_hazard_defense
from seasonal_updates.halloween.haunted import (
    resolve_haunted_choice,
    HAUNTED_DAILY_ATTEMPTS,
    HAUNTED_LOCATIONS,
    SANITY_MAX,
    choose_encounter,
    clear_run,
    consume_attempt,
    get_active_run,
    get_or_create_profile,
    is_insane,
    sanity_percent,
    start_run,
    update_sanity,
    advance_run,
    grant_haunted_completion_rewards,
)

COOLDOWN_ALERT_CHANNEL_ID = 1548034265508356166

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


SCAVENGE_STARDUST_CACHE_CHANCE = 0.125
SCAVENGE_STARDUST_CACHE_MIN = 750
SCAVENGE_STARDUST_CACHE_MAX = 3500


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
        except Exception:
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
                                f"<@{user_id}> ⛏️ **Your mining cooldown is ready!** "
                                f"You can use `/mine` again."
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
                                f"<@{user_id}> 🔎 **Your scavenging cooldown is ready!** "
                                f"You can use `/scavenge` again."
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

        except Exception:
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
        return (
            f"{prefix}💀 **You are unconscious.** You can use `/revive` or buy `/shop buy full_revive` "
            f"to return now; otherwise you will recover at 50% HP on **{knocked_out_until}**."
        )

    @commands.hybrid_group(
        name="explore",
        description="Explore Enceladus and its seasonal locations.",
    )
    async def explore(self, ctx: commands.Context):
        """Root for exploration subcommands."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Use `/explore haunted` to enter the Haunted Exploration event!")

    @explore.command(
        name="haunted",
        description="Enter Haunted Exploration and choose a location.",
    )
    async def explore_haunted(self, ctx: commands.Context):
        if not is_halloween_channel(ctx.channel):
            return await ctx.send(halloween_channel_message())
        if not halloween_is_active():
            return await ctx.send(
                "🎃 **Haunted Exploration is currently dormant.**\n"
                "This event is only available during the Halloween event."
            )

        user_id = ctx.author.id
        lock = self._user_locks.setdefault(user_id, asyncio.Lock())
        async with lock:
            async with aiosqlite.connect(self.get_db_path()) as db:
                await self.ensure_schema(db)
                profile = await get_or_create_profile(db, user_id)

            embed = self._haunted_location_embed(ctx.author, profile)
            await ctx.send(embed=embed, view=HauntedLocationView(self))

    def _haunted_location_embed(self, member, profile):
        sanity = sanity_percent(profile["sanity"])
        state = "☠️ **INSANE**" if is_insane(profile["sanity"]) else "🧠 **Stable**"
        active = profile["active_location"]

        description = (
            "Something is wrong with this part of Enceladus. The corridors are too quiet, "
            "the shadows move when nobody is looking, and nobody can agree on where these places came from.\n\n"
            "Choose somewhere to explore. Each run is made of multiple stages, and your choices can affect your Sanity."
        )
        if active in HAUNTED_LOCATIONS:
            description += (
                f"\n\n⚠️ You currently have an active run in **{HAUNTED_LOCATIONS[active]['name']}** "
                f"(Stage {profile['active_stage']}/{profile['active_total_stages']}). Starting another run will replace it."
            )

        embed = discord.Embed(
            title="🎃 Haunted Exploration",
            description=description,
            color=discord.Color.dark_purple(),
        )
        embed.add_field(
            name="🧠 Sanity",
            value=f"**{sanity}/100**\n{state}\nRegenerates continuously over time.",
            inline=True,
        )
        embed.add_field(
            name="🎟️ Daily Attempts",
            value=f"**{profile['attempts']}/{HAUNTED_DAILY_ATTEMPTS}**",
            inline=True,
        )
        embed.add_field(
            name="📖 How it works",
            value="Choose a location, face encounters, make choices, or run away. Completing a run awards location-specific ingredients, Candy, Stardust, and a rarity-based chance at Halloween collectibles.",
            inline=False,
        )
        embed.set_footer(text=f"Explorer: {member.display_name} • Halloween event")
        return embed

    def _haunted_info_embed(self):
        embed = discord.Embed(
            title="📖 Haunted Exploration — Field Guide",
            description=(
                "Haunted Exploration is a multi-stage Halloween adventure. Pick a location and work your way "
                "through encounters by choosing what to do."
            ),
            color=discord.Color.dark_purple(),
        )
        embed.add_field(
            name="🧠 Sanity",
            value=(
                "Sanity starts at **100** and regenerates continuously. Some choices reduce it. "
                "At **0 Sanity**, you enter the **Insane** state."
            ),
            inline=False,
        )
        embed.add_field(
            name="🫥 Losing Your Grip",
            value=(
                "Low Sanity makes reality less reliable. Hallucinations can appear, encounters become more unstable, "
                "and at **0 Sanity** the world can become profoundly wrong. Insanity does not merely mean taking more damage."
            ),
            inline=False,
        )
        embed.add_field(
            name="🎟️ Attempts",
            value=(
                f"You get **{HAUNTED_DAILY_ATTEMPTS} attempts per day**. Starting an adventure consumes one attempt. "
                "The daily reset follows Eastern Time."
            ),
            inline=False,
        )
        embed.add_field(
            name="👻 Stages",
            value=(
                "Runs have multiple stages. Lower Sanity can make a run longer, and Insane runs are the longest. "
                "Your choices are the heart of the adventure."
            ),
            inline=False,
        )
        embed.add_field(
            name="🏃 Running Away",
            value=(
                "You can run away instead of taking an encounter choice. Most escapes work, but there is a small "
                "chance that something happens while you escape."
            ),
            inline=False,
        )
        embed.add_field(
            name="👻 Haunted Content",
            value="Phase 2 adds end-of-adventure rewards, location-specific ingredients, rarity, Candy, Stardust, and Haunted-only collectible discoveries. Phase 3 adds location-specific encounters, while universal encounters can still appear anywhere.",
            inline=False,
        )
        return embed

    async def _start_haunted_run(self, interaction: discord.Interaction, location_id: str):
        if not halloween_is_active():
            return await interaction.response.send_message(
                "🎃 **Haunted Exploration is currently dormant.**",
                ephemeral=True,
            )

        user_id = interaction.user.id
        lock = self._user_locks.setdefault(user_id, asyncio.Lock())
        async with lock:
            async with aiosqlite.connect(self.get_db_path()) as db:
                await self.ensure_schema(db)
                consumed, profile = await consume_attempt(db, user_id)
                if not consumed:
                    return await interaction.response.send_message(
                        "🎟️ **You're out of Haunted Exploration attempts for today.**\n"
                        "Come back after the daily reset.",
                        ephemeral=True,
                    )

                total_stages = await start_run(db, user_id, location_id, profile["sanity"])

            location = HAUNTED_LOCATIONS[location_id]
            await interaction.response.edit_message(
                content=f"{location['emoji']} **{location['name']}** selected.",
                embed=None,
                view=None,
            )
            await self._show_haunted_stage(interaction, location_id, 1, total_stages)

    async def _show_haunted_stage(self, interaction: discord.Interaction, location_id: str, stage: int, total_stages: int):
        user_id = interaction.user.id
        async with aiosqlite.connect(self.get_db_path()) as db:
            await self.ensure_schema(db)
            profile = await get_or_create_profile(db, user_id)
            async with db.execute("SELECT active_effects FROM users WHERE user_id = ?", (user_id,)) as cursor:
                effect_row = await cursor.fetchone()
            try:
                effects = json.loads(effect_row[0] or "{}") if effect_row else {}
                if not isinstance(effects, dict):
                    effects = {}
            except (TypeError, ValueError):
                effects = {}

            force_universal = bool(stage == 1 and effects.get("haunted_run_force_universal"))
            force_location = bool(stage == 1 and effects.get("haunted_run_force_location"))
            discovery_bonus = float(effects.get("haunted_run_discovery_bonus", 0.0))
            encounter = choose_encounter(
                location_id,
                profile["sanity"],
                force_universal=force_universal,
                force_location=force_location,
                discovery_bonus=discovery_bonus,
            )

            malo_warning = None
            malo_warning_chance = float(effects.get("haunted_run_malo_warning_chance", 0.0))
            if malo_warning_chance and random.random() < malo_warning_chance:
                dangerous = [
                    (index, choice)
                    for index, choice in enumerate(encounter.get("choices", []))
                    if (
                        (choice.get("risk", "medium") if isinstance(choice, dict) else "medium")
                        in {"high", "extreme"}
                    )
                ]
                if dangerous:
                    _, warned_choice = random.choice(dangerous)
                    warned_label = warned_choice.get("label", "one of the choices") if isinstance(warned_choice, dict) else warned_choice[0]
                    malo_warning = warned_label

            if force_universal:
                effects.pop("haunted_run_force_universal", None)
            if force_location:
                effects.pop("haunted_run_force_location", None)
            if force_universal or force_location:
                await db.execute(
                    "UPDATE users SET active_effects = ? WHERE user_id = ?",
                    (json.dumps(effects), user_id),
                )
                await db.commit()

        location = HAUNTED_LOCATIONS[location_id]
        sanity = sanity_percent(profile["sanity"])
        encounter_text = encounter["text"]
        if sanity <= 0:
            encounter_text = "🩸 **INSANITY**\n\n" + encounter_text
        elif sanity <= 25:
            encounter_text = "🫥 **Your grip on reality is slipping.**\n\n" + encounter_text
        embed = discord.Embed(
            title=f"{location['emoji']} {location['name']}",
            description=encounter_text,
            color=discord.Color.dark_red() if sanity <= 25 else discord.Color.dark_purple(),
        )
        embed.add_field(name="📍 Stage", value=f"**{stage}/{total_stages}**", inline=True)
        embed.add_field(name="🧠 Sanity", value=f"**{sanity}/100**", inline=True)

        if malo_warning:
            embed.add_field(
                name="👁️ MalO's Warning",
                value=(
                    f"MalO is staring at **{malo_warning}**.\n"
                    "*You are not entirely sure why.*"
                ),
                inline=False,
            )

        pet_discovery_message = None
        if encounter.get("discovery_id"):
            discovery_id = encounter["discovery_id"]
            achievements_cog = self.bot.get_cog("Achievements")
            if achievements_cog:
                await achievements_cog.record_haunted_discovery(
                    user_id,
                    discovery_id,
                    location_id,
                    sanity=profile["sanity"],
                    db=db,
                )

            pet_result = await grant_haunted_pet(db, user_id, location_id)
            if pet_result and pet_result.get("new"):
                pet_discovery_message = pet_result["message"]

            # Discovery records and pet rewards are part of the same stage setup.
            await db.commit()

        embed.set_footer(text="Choose carefully. Or run.")

        await interaction.followup.send(
            embed=embed,
            view=HauntedEncounterView(self, location_id, stage, total_stages, encounter),
        )
        if pet_discovery_message:
            await interaction.followup.send(pet_discovery_message)

    async def _resolve_haunted_choice(self, interaction: discord.Interaction, location_id: str, stage: int, total_stages: int, encounter, choice_index: int):
        user_id = interaction.user.id
        lock = self._user_locks.setdefault(user_id, asyncio.Lock())
        async with lock:
            async with aiosqlite.connect(self.get_db_path()) as db:
                await self.ensure_schema(db)
                run = await get_active_run(db, user_id)
                if not run or run["location_id"] != location_id or run["stage"] != stage:
                    return await interaction.response.send_message(
                        "⚠️ This encounter is no longer active. Start a new Haunted Exploration run.",
                        ephemeral=True,
                    )

                # The same choice can resolve differently each time.  Risk is
                # readable from the button style, but the exact Sanity swing is not.
                current_profile = await get_or_create_profile(db, user_id)
                choice, outcome = resolve_haunted_choice(
                    encounter,
                    choice_index,
                    current_profile["sanity"],
                )
                sanity_delta = int(outcome.get("sanity", 0))
                result_text = outcome.get("text", "Something happens.")

                async with db.execute("SELECT active_effects FROM users WHERE user_id = ?", (user_id,)) as cursor:
                    effect_row = await cursor.fetchone()
                try:
                    effects = json.loads(effect_row[0] or "{}") if effect_row else {}
                    if not isinstance(effects, dict):
                        effects = {}
                except (TypeError, ValueError):
                    effects = {}

                if sanity_delta < 0:
                    pet_protection = float(effects.get("haunted_run_negative_protection", 0.0))
                    if pet_protection and random.random() < pet_protection:
                        sanity_delta = 0
                        result_text += "\n\n🐾 **Your Haunted companion sensed the danger and intervened.**"
                    elif effects.pop("haunted_run_block_next_negative", False):
                        sanity_delta = 0
                        result_text += "\n\n🛡️ **A ward absorbed the supernatural backlash.**"
                    elif effects.pop("haunted_run_half_next_negative", False):
                        sanity_delta = int(sanity_delta / 2)
                        result_text += "\n\n🪞 **The Mirror Ward reflects part of the fear away.**"
                    elif effects.get("haunted_run_flat_protection"):
                        protection = int(effects.pop("haunted_run_flat_protection"))
                        sanity_delta = min(0, sanity_delta + protection)
                        result_text += "\n\n📺 **The Security Monitor warned you in time, cushioning the hit.**"

                    multiplier = float(effects.get("haunted_run_sanity_multiplier", 1.0))
                    if multiplier < 1.0 and sanity_delta < 0:
                        sanity_delta = int(sanity_delta * multiplier)

                await db.execute(
                    "UPDATE users SET active_effects = ? WHERE user_id = ?",
                    (json.dumps(effects), user_id),
                )

                new_sanity = await update_sanity(db, user_id, sanity_delta)

                # Global Haunted discovery achievements are evaluated after the
                # choice resolves, because some of them depend on the resulting
                # Sanity (for example, Worth It and Unwell).
                if encounter.get("discovery_id"):
                    achievements_cog = self.bot.get_cog("Achievements")
                    if achievements_cog:
                        await achievements_cog.mark_haunted_discovery_outcome(
                            user_id,
                            encounter["discovery_id"],
                            sanity_delta,
                            new_sanity,
                            db=db,
                        )

                # Collectible bonuses are resolved before advance_run clears the
                # run-scoped effects on completion.
                collectible_bonus = float(effects.get("haunted_run_collectible_bonus", 0.0))
                next_stage = await advance_run(db, user_id)
                reward = None
                if next_stage is None:
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
                    pet_xp_result = await add_pet_xp(
                        db,
                        user_id,
                        haunted_pet_xp_amount,
                    )

            await interaction.response.edit_message(view=None)

            if next_stage is None:
                assert reward is not None
                reward_lines = [
                    f"{reward['rarity_emoji']} **{reward['rarity_label']} Haul**",
                    f"✨ **+{reward['stardust']:,} Stardust**",
                    f"🍬 **+{reward['candy']} Halloween Candy**",
                    f"{reward['ingredient_emoji']} **+{reward['ingredient_added']} {reward['ingredient_name']}**",
                ]
                if pet_xp_result:
                    xp_line = f"🐾 **+{pet_xp_result['xp_added']} Pet XP**"
                    if haunted_home_bonus:
                        xp_line += f" *(+{haunted_home_bonus} home-location bonus)*"
                    if pet_xp_result["leveled_up"]:
                        xp_line += f" • 🎉 **Pet Level {pet_xp_result['new_level']}!**"
                    reward_lines.append(xp_line)
                if reward['candy_overflow']:
                    reward_lines.append(
                        f"📦 Candy overflow: **{reward['candy_overflow']}** → **+{reward['overflow_stardust']} Stardust**"
                    )
                if reward['ingredient_overflow']:
                    reward_lines.append(
                        f"📦 Ingredient overflow: **{reward['ingredient_overflow']}** → **+{reward['ingredient_overflow_stardust']} Stardust**"
                    )
                if reward['collectible_found'] and reward['collectible']:
                    collectible = reward['collectible']
                    reward_lines.append(
                        f"🎃 **Halloween Collectible Found:** {collectible[2]} **{collectible[1]}**"
                    )

                await interaction.followup.send(
                    f"✨ **Stage {stage} complete!**\n{result_text}\n\n"
                    f"🏁 You made it through **{total_stages} stages** of {HAUNTED_LOCATIONS[location_id]['name']}!\n"
                    f"🧠 Sanity: **{sanity_percent(new_sanity)}/100**\n\n"
                    "🎁 **Adventure Rewards**\n" + "\n".join(reward_lines)
                )
                return

            await interaction.followup.send(f"{result_text}")
            await self._show_haunted_stage(interaction, location_id, next_stage, total_stages)

    async def _run_away_haunted(self, interaction: discord.Interaction, location_id: str, stage: int, total_stages: int):
        user_id = interaction.user.id
        lock = self._user_locks.setdefault(user_id, asyncio.Lock())
        async with lock:
            async with aiosqlite.connect(self.get_db_path()) as db:
                await self.ensure_schema(db)
                run = await get_active_run(db, user_id)
                if not run or run["location_id"] != location_id or run["stage"] != stage:
                    return await interaction.response.send_message(
                        "⚠️ This encounter is no longer active. Start a new Haunted Exploration run.",
                        ephemeral=True,
                    )

                rare_escape = random.random() < 0.08
                if rare_escape:
                    sanity_loss = random.randint(4, 10)
                    new_sanity = await update_sanity(db, user_id, -sanity_loss)
                    escape_text = random.choice([
                        "You bolt for the exit. The door slams shut behind you by itself. Something follows you for three steps before disappearing.",
                        "You run. Your footsteps keep going after you stop. You decide not to investigate.",
                        "You make it out—then realize the hallway outside has one extra door. You do not go back.",
                    ])
                else:
                    new_sanity = await update_sanity(db, user_id, 0)
                    escape_text = random.choice([
                        "You decide you've had enough and make a very respectable tactical retreat.",
                        "Nope. Absolutely not. You turn around and leave.",
                        "You retreat before whatever is lurking here gets the chance to introduce itself.",
                    ])

                await clear_run(db, user_id)

            await interaction.response.edit_message(view=None)
            suffix = "\n\n⚠️ **Something happened while you escaped.**" if rare_escape else ""
            await interaction.followup.send(
                f"🏃 **You ran away.**\n{escape_text}{suffix}\n\n"
                f"🧠 Sanity: **{sanity_percent(new_sanity)}/100**\n"
                "No reward was earned from this run."
            )

    @commands.hybrid_command(name="heal", description="Use a healing item from your inventory to restore HP.")
    @app_commands.choices(item=[
        app_commands.Choice(name=f"{EMOJIS.get('nanite_patch', '🩹')} Nanite Stim-Patch (+35 HP)", value="nanite_patch"),
        app_commands.Choice(name=f"{EMOJIS.get('makeshift_medkit', '🩹')} Makeshift Medkit (+60 HP)", value="makeshift_medkit"),
        app_commands.Choice(name=f"{EMOJIS.get('medkit', '🧰')} Field Trauma Medkit (+100 HP)", value="medkit"),
        app_commands.Choice(name="🍬 Halloween Candy (+5 HP)", value="halloween_candy"),
        app_commands.Choice(name="🎃 Trick-or-Treat Bag (+25 HP)", value="trick_or_treat_bag")
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
            return await ctx.send("❌ Invalid healing item selected.")

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
                return await ctx.send("❌ Profile not found!")

            current_hp, max_hp, knocked_out_until = row[0] or 0, row[1] or 100, row[2] or ""

            if current_hp <= 0:
                return await ctx.send(self.knockout_message(knocked_out_until or "tomorrow", ctx.author.mention))

            if current_hp >= max_hp:
                return await ctx.send(
                    f"❤️ **Full Health!** You are already at max HP (**{max_hp}/{max_hp} HP**)."
                )

            if selected.get("inventory"):
                async with db.execute(
                    "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                    (user_id, item)
                ) as cursor:
                    item_row = await cursor.fetchone()
                item_count = item_row[0] if item_row else 0
                if item_count <= 0:
                    return await ctx.send(f"❌ You don't have any **{selected['name']}s** left!")
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
                    return await ctx.send(f"❌ You don't have any **{selected['name']}s** in your inventory!")
                async with db.execute(
                    f"SELECT {col_name} FROM users WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    count_row = await cursor.fetchone()
                item_count = count_row[0] if count_row else 0
                if item_count <= 0:
                    return await ctx.send(f"❌ You don't have any **{selected['name']}s** left!")
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
                    )
            await db.commit()

        action = "Chowed down on the candy! 🍬" if item == "halloween_candy" else ("You opened the bag and chowed down on candy! 🍬" if item == "trick_or_treat_bag" else f"Used {selected['name']}!")
        await ctx.send(
            f"{ctx.author.mention} {'🎃' if item in ('halloween_candy', 'trick_or_treat_bag') else '💉'} **{action}**\n"
            f"Restored **+{healed_by} HP**! Current Health: ❤️ **{new_hp}/{max_hp} HP** "
            f"*(Items Remaining: {new_count})*"
        )

    @commands.hybrid_command(
        name="cooldown_alerts",
        description="Toggle notifications when your mining and scavenging cooldowns finish."
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
                    "🔔 **Cooldown Alerts: ON**\n"
                    "You'll be pinged in the Exploration channel "
                    "when your mining or scavenging cooldown finishes!"
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
                "🔔 **Cooldown Alerts: ON**\n"
                "You'll be pinged in the Exploration channel "
                "when your mining or scavenging cooldown finishes!"
            )
        else:
            await ctx.send(
                "🔕 **Cooldown Alerts: OFF**\n"
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
                "💡 **Want a little heads-up from time-to-time?** You can use `/cooldown_alerts` "
                "to get pinged when your mining and/or scavenging cooldown finishes!"
            )

        return None



    @commands.hybrid_command(name="mine", description="Deploy your starship mining laser to scout for Stardust and rare loot!")
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
            pet_effects = await get_active_pet_effects(db, user_id)
            upgrade_cog = self.bot.get_cog("Upgrades")
            mining_upgrade = await upgrade_cog.get_effects(user_id, "mining") if upgrade_cog else {"level": 0, "max_charges": 10, "stardust_mult": 1.0, "rare_bonus": 0.0}
            # Space Dragon grants +3 maximum Mining charges at passive level 5.
            max_mining_charges = mining_upgrade["max_charges"] + pet_effects.get("extra_charge_count", 0)

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
                return await ctx.send(f"{ctx.author.mention} ⚠️ **Mining laser is recharging!** Next charge ready in **{hours}h {minutes}m**.")

            if charges <= 0 and not effects.get("fuel_stabilizer"):
                return await ctx.send(
                    f"{ctx.author.mention} 🚨 **Laser Depleted!** You are out of fuel charges. "
                    "Visit the station shop for an emergency refill or wait until daily reset."
                )

            # --- TIERED LOOT ROLL ---
            roll = 0.70 if effects.pop("ore_magnet", False) else random.random()
            if effects.pop("fuel_stabilizer", False):
                new_charges = charges
            elif pet_effects["charge_save"] and random.random() < pet_effects["charge_save"]:
                new_charges = charges
            else:
                new_charges = charges - 1
            
            pet_effects = await get_active_pet_effects(db, user_id)
            found_stardust = int(
                random.randint(50, 150)
                * mining_upgrade["stardust_mult"]
                * (
                    1
                    + pet_effects["stardust_bonus"]
                    + pet_effects.get("extra_charges", 0.0)
                )
            )

            if effects.pop("prototype_drill_bit", False):
                found_stardust = int(found_stardust * 1.5)

            if effects.pop("quantum_battery", False):
                found_stardust *= 3
                loot_bonus_note = "\n\n⚛️ **Quantum Battery:** Stardust tripled!"
            else:
                loot_bonus_note = ""

            new_stardust = stardust + found_stardust
            
            loot_description = (
                f"✨ **Stardust Collected:** **{found_stardust:,}**"
                f"{loot_bonus_note}"
            )

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

            if mining_material_findings:
                loot_description += (
                    "\n\n⛏️ **Minerals Recovered:** "
                    + " • ".join(mining_material_findings)
                )
            if mining_overflow_findings:
                loot_description += (
                    "\n\n📦 **Mineral Overflow:** "
                    + " • ".join(mining_overflow_findings)
                )

            # Halloween bonus resources are independent rolls during the active event.
            halloween_active = halloween_is_active()
            seasonal_findings = []
            if halloween_active and random.random() < HALLOWEEN_CANDY_CHANCE:
                candy_found = 1
                candy_doubled = False

                # Samhain's Trick-or-Treating passive can double the base candy haul.
                if (
                    pet_effects["candy_bonus"]
                    and random.random() < pet_effects["candy_bonus"]
                ):
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
                    candy_note = f"{EMOJIS.get('halloween_candy', '🍬')} Halloween Candy ×{added_candy}"
                    if candy_doubled:
                        candy_note += " (Samhain bonus!)"
                    seasonal_findings.append(candy_note)
                if overflow_candy > 0:
                    candy_overflow_stardust = overflow_candy * 2
                    new_stardust += candy_overflow_stardust
                    seasonal_findings.append(
                        f"📦 Candy Overflow ×{overflow_candy} → +{candy_overflow_stardust} Stardust"
                    )

            # Special pet candy is seasonal too, but is separate from ordinary Halloween Candy.
            if halloween_active and random.random() < HALLOWEEN_PET_CANDY_CHANCE:
                pet_candy_found = random.randint(1, 2)

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
                        f"🍬 Halloween Pet Candy ×{added_pet_candy}"
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
                            f"📦 Halloween Pet Candy Overflow ×{overflow_pet_candy} "
                            f"→ 🍪 Pet Treat ×{added_normal_treat}"
                        )
                    remaining_overflow = overflow_pet_candy - added_normal_treat
                    if remaining_overflow:
                        seasonal_findings.append(
                            f"📦 Pet Treat Inventory Full: {remaining_overflow} overflow "
                            f"could not be stored (cap {normal_treat_max})"
                        )

            if halloween_active and random.random() < HALLOWEEN_PLASTIC_CHANCE:
                plastic_found = random.randint(HALLOWEEN_PLASTIC_MIN, HALLOWEEN_PLASTIC_MAX)
                added_plastic, plastic_quantity, plastic_max = await add_inventory_item(
                    db, user_id, "halloween_plastic", "crafting_material", plastic_found
                )
                if added_plastic:
                    seasonal_findings.append(f"🧴 Halloween Plastic ×{added_plastic}")
                overflow_plastic = plastic_found - added_plastic
                if overflow_plastic:
                    new_stardust += overflow_plastic * 2
                    seasonal_findings.append(f"📦 Plastic Overflow ×{overflow_plastic} → +{overflow_plastic * 2} Stardust")

            if seasonal_findings:
                loot_description += "\n\n🎃 **Halloween Finds:** " + " • ".join(seasonal_findings)

            rarity_badge = "common"

            if roll < 0.40:
                # Tier 1: Common (Just Stardust)
                pass

            elif roll < 0.60:
                # Tier 2: Uncommon (Stardust + XP Data Shard)
                found_xp = random.randint(75, 200)
                loot_description += f"\n\n📊 **XP Data Shard:** **+{found_xp} XP**"
                rarity_badge = "uncommon"

                # Award XP globally through leveling.py
                leveling_cog = self.bot.get_cog("Leveling")
                if leveling_cog:
                    leveled_up, new_level = await leveling_cog.add_xp(ctx.author, found_xp)
                    if leveled_up:
                        loot_description += f"\n\n🎉 **Level Up!** Reached **Level {new_level}**!"

            elif roll < 0.75 + mining_upgrade["rare_bonus"]:
                # Tier 3: Rare Mineral (Titanium Ore Chunk)
                added_amount, new_quantity, max_quantity = await add_inventory_item(
                    db,
                    user_id,
                    "titanium_chunk",
                    "mineral",
                    1
                )

                if added_amount == 1:
                    loot_description += (
                        f"\n\n⛏️ **Rare Ore Extracted:** Refined a "
                        f"**Titanium Ore Chunk**! ({new_quantity}/{max_quantity})"
                    )
                else:
                    overflow_stardust = LOOT_OVERFLOW_VALUES.get("titanium_chunk", 75)
                    new_stardust += overflow_stardust

                    loot_description += (
                        f"\n\n📦 **Inventory Full:** Your Titanium Ore Chunk stack "
                        f"is already at **{max_quantity}/{max_quantity}**!"
                        f"\n\n✨ **Converted to:** **+{overflow_stardust:,} Stardust**"
                    )

                rarity_badge = "rare"

            elif roll < 0.90 + mining_upgrade["rare_bonus"]:
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
                    loot_description += (
                        f"\n\n🪙 **Holodeck Find:** Discovered a shiny "
                        f"**Arcade Token**! ({new_token_balance}/{token_max})"
                    )
                else:
                    overflow_stardust = LOOT_OVERFLOW_VALUES.get("arcade_token", 50)
                    new_stardust += overflow_stardust

                    loot_description += (
                        f"\n\n📦 **Inventory Full:** Your Arcade Token balance "
                        f"is already at **{token_max}/{token_max}**!"
                        f"\n\n✨ **Converted to:** **+{overflow_stardust:,} Stardust**"
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

                    loot_description += (
                        f"\n\n💎 **Rare Discovery:** Acquired a stable "
                        f"**Dilated Time Crystal**! "
                        f"({current_crystals + 1}/{max_quantity})"
                    )
                else:
                    overflow_stardust = LOOT_OVERFLOW_VALUES.get("time_crystal", 350)
                    new_stardust += overflow_stardust

                    loot_description += (
                        f"\n\n📦 **Inventory Full:** Your Dilated Time Crystal "
                        f"stack is already at **{max_quantity}/{max_quantity}**!"
                        f"\n\n✨ **Converted to:** **+{overflow_stardust:,} Stardust**"
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
                    loot_description += (
                        "\n🌟 **Legendary Find:** Recovered an "
                        f"**Astral Core**! ({new_quantity}/{max_quantity})"
                        "\n*Its purpose is currently unknown...*"
                    )
                else:
                    overflow_stardust = LOOT_OVERFLOW_VALUES.get("astral_core", 750)
                    new_stardust += overflow_stardust

                    loot_description += (
                        f"\n\n📦 **Inventory Full:** Your Astral Core stack "
                        f"is already at **{max_quantity}/{max_quantity}**!"
                        f"\n\n✨ **Converted to:** **+{overflow_stardust:,} Stardust**"
                        "\n*The mysterious core was too much for your inventory to contain.*"
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

        embed = discord.Embed(
            title=f"🌌 Starship Mining Log — {ctx.author.display_name}",
            description=(
                f"Laser beam fired into the debris field...\n\n"
                f"{loot_description}"
            ),
            color=colors.get(rarity_badge, discord.Color.blue())
        )
        cooldown_total_seconds = max(0, int(round(effective_cooldown)))
        cooldown_minutes, cooldown_seconds = divmod(cooldown_total_seconds, 60)
        cooldown_text = f"{cooldown_minutes}m" if cooldown_seconds == 0 else f"{cooldown_minutes}m {cooldown_seconds}s"
        embed.set_footer(text=f"Fuel Charges Remaining: {new_charges}/{max_mining_charges} • Cooldown: {cooldown_text}")
        mining_pet_charge_bonus = pet_effects.get("extra_charge_count", 0)
        mining_pet_stardust_bonus = pet_effects.get("extra_charges", 0.0)
        mining_pet_note = (
            f" • 🐉 Space Dragon: **+{mining_pet_charge_bonus} Max Charges**"
            if mining_pet_charge_bonus
            else ""
        )
        embed.add_field(
            name="🛠️ Mining Laser Upgrade",
            value=(f"Tier **{mining_upgrade['level']}/5** • Max Charges: **{max_mining_charges}**\n"
                   f"Stardust Bonus: **+{(mining_upgrade['stardust_mult'] - 1) * 100:.0f}%** • Rare Loot Bonus: **+{mining_upgrade['rare_bonus'] * 100:.1f}%**"
                   f"\nPet Stardust Bonus: **+{mining_pet_stardust_bonus * 100:.0f}%**{mining_pet_note}"),
            inline=False
        )

        if pet_xp_result:
            pet_xp_text = f"🐾 **Pet XP:** **+{pet_xp_result['xp_added']} XP**"
            if pet_xp_result["leveled_up"]:
                pet_xp_text += f" • 🎉 **Level {pet_xp_result['new_level']}!**"
            embed.add_field(
                name="🐾 Companion Progress",
                value=pet_xp_text,
                inline=False,
            )

        if random.random() < 0.25 and await self.daily_unclaimed(user_id):
            embed.add_field(
                name="📅 Daily Reminder",
                value="You didn't claim your daily yet! Use `/daily` to claim your Stardust reward!",
                inline=False
            )

        cooldown_reminder = await self.maybe_suggest_cooldown_alerts(ctx)
        if cooldown_reminder:
            embed.add_field(
                name="🔔 Cooldown Alerts",
                value=cooldown_reminder,
                inline=False
            )

        await ctx.send(content=ctx.author.mention, embed=embed)

    @commands.hybrid_command(name="scavenge", description="Search derelict wreckage for salvage, Stardust, and occasional rare finds!")
    async def scavenge(self, ctx: commands.Context):
        await ctx.defer()

        user_id = ctx.author.id
        lock = self._user_locks.setdefault(user_id, asyncio.Lock())

        async with lock:
            return await self._scavenge_impl(ctx)


    async def _scavenge_impl(self, ctx: commands.Context):
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
            pet_effects = await get_active_pet_effects(db, user_id)
            upgrade_cog = self.bot.get_cog("Upgrades")
            scavenging_upgrade = await upgrade_cog.get_effects(user_id, "scavenging") if upgrade_cog else {"level": 0, "max_charges": 10, "stardust_mult": 1.0, "rare_bonus": 0.0}
            salvage_upgrade = await upgrade_cog.get_effects(user_id, "salvage") if upgrade_cog else {"level": 0, "bonus_chance": 0.0}
            # Space Dragon grants +3 maximum Scavenging charges at passive level 5.
            max_scavenge_charges = scavenging_upgrade["max_charges"] + pet_effects.get("extra_charge_count", 0)
            scavenging_rare_bonus = scavenging_upgrade.get("rare_bonus", 0.0)
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
                return await ctx.send(f"{ctx.author.mention} ⚠️ **Scavenge drone is recharging!** Next run ready in **{hours}h {minutes}m**.")

            if charges <= 0:
                return await ctx.send(f"{ctx.author.mention} 🚨 **Drone Depleted!** You are out of scavenge charges. Visit the station shop for a recharge or wait until daily reset.")

            junk_items = {
                "space_pizza": "🍕 Dehydrated Space Pizza (slightly freezer-burned)",
                "floppy_disk": "💾 Ancient Alien Floppy Disk (contains mysterious code)",
                "meteorite": "🪨 Suspiciously Warm Meteorite Chunk (glows faintly)",
                "rubber_duck": "🐤 Rubber Duck in a Micro-Spacesuit (how cute!)",
                "rusty_gear": "⚙️ Tarnished Station Gear (still turns, but squeaks)",
                "tape_deck": "📼 Broken Cassette Player (plays static)",
                "alien_artifact": "🛸 Miniature Alien Artifact (glows faintly)",
                "space_boot": "🥾 Singular Space Boot (wonder where the other one went...)",
                "cosmic_coin": "🪙 Cosmic Coin (give it a flip!)",
                "holo_poster": "🖼️ Faded Holographic Poster of a Galactic Band",
                "broken_laser": "🔫 Broken Laser Pistol (sparks occasionally)",
                "lost_logbook": "📓 Waterlogged Starship Logbook (unreadable)",
                "left_sock": "🧦 Left Sock (the right one is missing)",
                "warp_mug": "☕ Leaky Thermal Mug (holds coffee across space-time, leaks in 3D)",
                "space_pudding": "🍮 Expired Pudding (tastes like dark matter)",
                "tangled_cables": "🔌 Quantum Cable Knot (physically impossible to untangle)",
                "screaming_crystal": "💎 Screaming Crystal (relentlessly sings 80s synth-pop)",
                "moon_cheese": "🧀 Chunk of Moon Cheese (smells like sharp cheddar)",
                "golden_spatula": "🍳 Golden Spatula (maybe SpongeBob had it?)",
                "parking_ticket": "📜 Cosmic Parking Ticket (overdue by 400 years! That's a big fine...)",
                "floating_plant": "🪴 Suspicious Houseplant (stares at you when you turn around...)",
                "tinted_visor": "🕶️ Broken Solar Visor (now just regular 3D glasses)",
                "purring_lint": "🧶 Ball of Space Lint (it purrs when you touch it?)",
                "pet_rock": "🪨 Asteroid Pet Rock (includes tiny glued-on googly eyes)",
                "haunted_circuit": "⚡ Haunted Circuit Board (sparks every time you whisper near it)",
                "space_taco": "🌮 Cosmic Taco (the salsa is surprisingly unaffected by zero-G)",
                "rusty_wrench": "🔧 Rusty Wrench (still works, but squeaks a lot)",
                "alien_fossil": "🦴 Alien Fossil Fragment (looks like it could bite back)",
                "big_red_button": "🔴 A Big Red Button (labeled 'do not press', but you pressed it anyway. It did nothing...)",
                "antique_compass": "🧭 Antique Compass (points to the nearest space anomaly, which is currently a black hole)",
                "broken_clock": "⏰ Broken Clock (stuck at 3:00AM. Witching hour... spooky)",
                "perplexing_painting": "🖌️ Perplexing Painting (the eyes seem to follow you, but it's a 2D image)",
                "cosmic_banana": "🍌 Cosmic Banana (peels itself, but tastes like stardust)"
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
                    "\n🌟 **Legendary Find:** Recovered a "
                    "**Quantum Battery**!"
                )

            elif loot_roll < (0.10 if lucky_scanner_active else 0.02) + pet_effects["rare_bonus"] + scavenging_rare_bonus:
                item_id = "revive_kit"
                item_name = f"{EMOJIS.get('revive_kit', '💉')} Emergency Revival Kit (rare)"
                item_type = "consumable"
                loot_rarity_note = ""

            elif loot_roll < (0.20 if lucky_scanner_active else 0.05) + pet_effects["rare_bonus"] + scavenging_rare_bonus:
                item_id = "laser_charge_cell"
                item_name = f"{EMOJIS.get('laser_charge_cell', '🔋')} Laser Charge Cell (rare)"
                item_type = "consumable"
                loot_rarity_note = ""

            elif loot_roll < (0.32 if lucky_scanner_active else 0.08) + pet_effects["rare_bonus"] + scavenging_rare_bonus:
                item_id = "drone_battery"
                item_name = f"{EMOJIS.get('drone_battery', '🔋')} Drone Battery Pack (rare)"
                item_type = "consumable"
                loot_rarity_note = ""

            else:
                # Halloween collectibles are exclusive to Haunted Exploration.
                # Scavenge keeps its normal Space Junk pool during the event.
                item_id, item_name = random.choice(list(junk_items.items()))
                item_type = "space_junk"
                loot_rarity_note = ""

            # Arcade Tokens are an independent bonus roll during scavenging.
            # This keeps the normal scavenging loot table intact instead of
            # replacing another find when a token appears.
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
                    loot_rarity_note += (
                        f"\n🪙 **Bonus Find:** Discovered an **Arcade Token**! "
                        f"({token_quantity}/{token_max})"
                    )
                else:
                    overflow_stardust = LOOT_OVERFLOW_VALUES.get("arcade_token", 50)
                    token_overflow_stardust = overflow_stardust
                    loot_rarity_note += (
                        f"\n📦 **Arcade Token Overflow:** Your token balance is already "
                        f"at **{token_max}/{token_max}**!"
                        f"\n✨ **Converted to:** **+{overflow_stardust:,} Stardust**"
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
                random.randint(45, 120)
                * scavenging_upgrade["stardust_mult"]
                * (
                    1
                    + pet_effects["stardust_bonus"]
                    + pet_effects.get("extra_charges", 0.0)
                )
            )

            if effects.pop("quantum_battery", False):
                found_stardust *= 3
                quantum_bonus_note = "\n⚛️ **Quantum Battery:** Stardust tripled!"
            else:
                quantum_bonus_note = ""

            cache_payout = 0
            cache_note = ""
            if random.random() < SCAVENGE_STARDUST_CACHE_CHANCE:
                cache_payout = random.randint(SCAVENGE_STARDUST_CACHE_MIN, SCAVENGE_STARDUST_CACHE_MAX)
                cache_note = f"\n\n🎁 **Stardust Cache Found!** **+{cache_payout:,} Stardust**"

            new_stardust = stardust + found_stardust + token_overflow_stardust + cache_payout

            # 30% Environmental Hazard Chance during Scavenging.
            damage_taken = 0
            hazard_note = ""
            force_hazard = effects.pop("force_hazard", False)
            if (force_hazard or random.random() < 0.30) and not effects.pop("hazard_shield", False):
                hazard, min_damage, max_damage, weight = random.choices(
                    self.SCAVENGE_HAZARDS,
                    weights=[entry[3] for entry in self.SCAVENGE_HAZARDS],
                    k=1,
                )[0]
                defended, defense_weapon_id, _atomic_breath_chance, _defense_chance = await roll_hazard_defense(db, user_id)
                if defended:
                    if defense_weapon_id:
                        from defense import DEFENSE_MESSAGES
                        defense_text = DEFENSE_MESSAGES.get(defense_weapon_id, "Your defensive weapon stopped the hazard!")
                    else:
                        defense_text = "☢️ **ATOMIC BREATH!** Your pet blasted the incoming hazard before it could reach you!"
                    hazard_note = f"\n\n🛡️ **Defense!** {defense_text}\n**0 HP damage taken.**"
                elif pet_effects["scavenge_hazard_avoidance"] and random.random() < pet_effects["scavenge_hazard_avoidance"]:
                    hazard_note = (
                        "\n\n🐾 **Pet Warning!** Your companion noticed the hazard a moment before it hit "
                        "and pulled you out of the way!\n**0 HP damage taken.**"
                    )
                elif halloween_is_active() and HALLOWEEN_DAMAGE_MESSAGES:
                    halloween_message, halloween_min_damage, halloween_max_damage = random.choice(HALLOWEEN_DAMAGE_MESSAGES)
                    hazard = halloween_message
                    damage_taken = max(1, int(random.randint(halloween_min_damage, halloween_max_damage) * (1 - pet_effects["hazard_reduction"])))
                    hazard_note = f"\n\n⚠️ **Hazard Warning!** You {hazard} and took **-{damage_taken} HP**."
                else:
                    damage_taken = max(1, int(random.randint(min_damage, max_damage) * (1 - pet_effects["hazard_reduction"])))
                    hazard_note = f"\n\n⚠️ **Hazard Warning!** You {hazard} and took **-{damage_taken} HP**."

            new_hp = max(0, hp - damage_taken)
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
                    hazard_note += (
                        f"\n\n🩺 **First Aid!** Your pet patched you up for **+{actual_recovery} HP**."
                    )

            if new_hp <= 0 and effects.pop("cosmic_insurance", False):
                new_hp = 1
                hazard_note += "\n\n📋 **Cosmic Insurance:** Your coverage kept you at **1 HP**."

            knocked_out_until = ""
            if new_hp <= 0:
                knocked_out_until = (self.game_date() + timedelta(days=1)).isoformat()
                knockout_lines = HALLOWEEN_KNOCKOUT_LINES if halloween_is_active() and HALLOWEEN_KNOCKOUT_LINES else self.KNOCKOUT_LINES
                hazard_note += f"\n\n💀 **Knockout Report:** {random.choice(knockout_lines)}"

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
            pet_findings = []
            bonus_overflow_findings = []

            # Some Haunted pets have a permanent, year-round scavenging passive
            # that can find an additional miscellaneous Space Junk item.
            if pet_effects["scavenge_bonus_loot"] and random.random() < pet_effects["scavenge_bonus_loot"]:
                bonus_item_id, bonus_item_name = random.choice(list(junk_items.items()))
                bonus_added, bonus_quantity, bonus_max = await add_inventory_item(
                    db, user_id, bonus_item_id, "space_junk", 1
                )
                if bonus_added:
                    pet_findings.append(
                        f"{bonus_item_name} ×{bonus_added} — **Pet Bonus Find**"
                    )
                else:
                    overflow_stardust = LOOT_OVERFLOW_VALUES.get(bonus_item_id, 10)
                    new_stardust += overflow_stardust
                    pet_findings.append(
                        f"{bonus_item_name} → Inventory Full (+{overflow_stardust:,} Stardust)"
                    )

            # Seasonal non-collectible resources remain available during Halloween.
            # Halloween collectibles themselves are exclusive to Haunted Exploration.
            halloween_active = halloween_is_active()

            # Pet eggs are independent bonus rolls and never replace normal loot.
            # Halloween and normal eggs each get their own roll, so both can be
            # found during the same scavenging run. Halloween eggs stop dropping
            # automatically when the event ends.
            egg_rolls = []
            if halloween_active and random.random() < HALLOWEEN_PET_EGG_CHANCE:
                egg_rolls.append("halloween_egg")
            if random.random() < NORMAL_EGG_CHANCE:
                egg_rolls.append("normal_egg")

            for egg_id in egg_rolls:
                egg_info = ITEM_REGISTRY.get(egg_id, {"name": egg_id, "emoji": "🥚"})
                added_egg, egg_quantity, egg_max = await add_inventory_item(
                    db, user_id, egg_id, "pet_egg", 1
                )
                if added_egg:
                    pet_findings.append(
                        f"{egg_info['emoji']} {egg_info['name']} ×{added_egg} — use `/incubator start {egg_id}`"
                    )
                else:
                    pet_findings.append(
                        f"{egg_info['emoji']} {egg_info['name']} → Inventory Full"
                    )

            # Halloween resources are independent bonus rolls and never replace normal loot.
            candy_doubled = False
            if halloween_active and random.random() < HALLOWEEN_CANDY_CHANCE:
                candy_found = 1

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
                    candy_note = f"{EMOJIS.get('halloween_candy', '🍬')} Halloween Candy ×{added_candy}"
                    if candy_doubled:
                        candy_note += " (Samhain bonus!)"
                    seasonal_findings.append(candy_note)
                if overflow_candy > 0:
                    candy_overflow_stardust = overflow_candy * 2
                    new_stardust += candy_overflow_stardust
                    seasonal_findings.append(
                        f"📦 Candy Overflow ×{overflow_candy} → +{candy_overflow_stardust} Stardust"
                    )

            if halloween_active and random.random() < HALLOWEEN_PLASTIC_CHANCE:
                plastic_found = random.randint(HALLOWEEN_PLASTIC_MIN, HALLOWEEN_PLASTIC_MAX)
                added_plastic, plastic_quantity, plastic_max = await add_inventory_item(
                    db, user_id, "halloween_plastic", "crafting_material", plastic_found
                )
                if added_plastic:
                    seasonal_findings.append(f"🧴 Halloween Plastic ×{added_plastic}")
                overflow_plastic = plastic_found - added_plastic
                if overflow_plastic:
                    new_stardust += overflow_plastic * 2
                    seasonal_findings.append(f"📦 Plastic Overflow ×{overflow_plastic} → +{overflow_plastic * 2} Stardust")

            # A Trick-or-Treat Bag is an especially rare direct seasonal find.
            if halloween_active and random.random() < HALLOWEEN_BAG_CHANCE:
                added_bag, bag_quantity, bag_max = await add_inventory_item(
                    db, user_id, "trick_or_treat_bag", "consumable", 1
                )
                if added_bag:
                    seasonal_findings.append(f"🎃 Trick-or-Treat Bag ×{added_bag}")
                else:
                    seasonal_findings.append("🎃 Trick-or-Treat Bag → Inventory Full")

            # Scavenging can recover multiple types of crafting material in one run.
            # Each successful material find yields 1–5 units.
            #
            # Salvage Rig bonus is a relative chance multiplier:
            # +10% turns a 20% base chance into 22%, while +65% turns it
            # into 33%. This keeps higher tiers meaningful without making
            # common materials nearly guaranteed.
            for material_id, material_name, chance in SCAVENGE_MATERIALS:
                effective_material_chance = min(1.0, chance * (1 + salvage_bonus_chance))
                if random.random() < effective_material_chance:
                    amount_found = random.randint(1, 5)
                    effective_scavenge_material_bonus = max(
                        pet_effects["material_bonus"],
                        pet_effects["scavenge_material_bonus"],
                    )
                    if effective_scavenge_material_bonus and random.random() < effective_scavenge_material_bonus:
                        amount_found += 1
                    added_material, material_quantity, material_max = await add_inventory_item(
                        db, user_id, material_id, "crafting_material", amount_found
                    )
                    overflow_amount = amount_found - added_material
                    if added_material:
                        salvage_material_findings.append(
                            f"{material_name} ×{added_material}"
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
                        if effective_scavenge_material_bonus and random.random() < effective_scavenge_material_bonus:
                            amount_found += 1
                        added_mineral, mineral_quantity, mineral_max = await add_inventory_item(
                            db, user_id, mineral_id, "mineral", amount_found
                        )
                        overflow_amount = amount_found - added_mineral
                        if added_mineral:
                            bonus_mineral_findings.append(
                                f"{mineral_name} ×{added_mineral}"
                            )
                        if overflow_amount > 0:
                            overflow_stardust = overflow_amount * MATERIAL_OVERFLOW_VALUES.get(mineral_id, 0)
                            new_stardust += overflow_stardust
                            bonus_overflow_findings.append(
                                f"{mineral_name} ×{overflow_amount} → +{overflow_stardust} Stardust"
                            )

            if added_amount == 1:
                loot_name_with_quantity = f"{item_name} ({new_quantity}/{max_quantity})"
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
                    f"{item_name}\n"
                    f"📦 **Inventory Full:** Stack is already "
                    f"**{max_quantity}/{max_quantity}**!"
                    f"\n✨ **Converted to:** **+{overflow_stardust:,} Stardust**"
                )

            # Group bonus discoveries into readable single-line sections rather than
            # repeating "Salvage Material:" / "Medical Supply:" for every item.
            bonus_sections = []
            if salvage_material_findings:
                bonus_sections.append(
                    "🧰 **Salvage Materials:** " + " • ".join(salvage_material_findings)
                )
            if medical_supply_findings:
                bonus_sections.append(
                    "🩹 **Medical Supplies:** " + " • ".join(medical_supply_findings)
                )
            if bonus_mineral_findings:
                bonus_sections.append(
                    "⛏️ **Bonus Minerals:** " + " • ".join(bonus_mineral_findings)
                )
            if seasonal_findings:
                bonus_sections.append(
                    "🎃 **Halloween Find:** " + " • ".join(seasonal_findings)
                )
            if pet_findings:
                bonus_sections.append(
                    "🐾 **Pet Find:** " + " • ".join(pet_findings)
                )
            if scavenge_charge_saved:
                bonus_sections.append(
                    "🐾 **Pet Bonus:** Your companion preserved this scavenging charge!"
                )
            if bonus_overflow_findings:
                bonus_sections.append(
                    "📦 **Overflow:** " + " • ".join(bonus_overflow_findings)
                )

            bonus_material_text = "\n\n" + "\n\n".join(bonus_sections) if bonus_sections else ""

            pet_xp_result = await add_pet_xp(db, user_id, roll_normal_exploration_pet_xp())

            await db.execute("""
                UPDATE users 
                SET scavenge_charges = ?, last_scavenged = ?, stardust = ?, hp = ?, knocked_out_until = ?, active_effects = ?
                WHERE user_id = ?
            """, (new_charges, current_time, new_stardust, new_hp, knocked_out_until, json.dumps(effects), user_id))

            await db.commit()

        status_text = f"❤️ **Health:** **{new_hp}/{max_hp} HP**" if new_hp > 0 else f"💀 **Knocked Out!** Use `/revive`, buy `/shop buy full_revive`, or recover at 50% HP on **{knocked_out_until}**."

        embed = discord.Embed(
            title=f"🛰️ Derelict Salvage Log — {ctx.author.display_name}",
            description=(
                f"Scavenge drone deployed into abandoned sector wreckage...\n\n"
                f"✨ **Found Stardust:** **{found_stardust:,}**"
                f"{quantum_bonus_note}"
                f"{cache_note}\n\n"
                f"🛸 **Salvaged Item:** **{loot_name_with_quantity}**"
                f"{loot_rarity_note}"
                f"{bonus_material_text}"
                f"{hazard_note}\n\n"
                f"{status_text}"
            ),
            color=discord.Color.dark_gold()
        )
        cooldown_total_seconds = max(0, int(round(effective_cooldown)))
        cooldown_minutes, cooldown_seconds = divmod(cooldown_total_seconds, 60)
        cooldown_text = f"{cooldown_minutes}m" if cooldown_seconds == 0 else f"{cooldown_minutes}m {cooldown_seconds}s"
        embed.set_footer(text=f"Drone Charges Remaining: {new_charges}/{max_scavenge_charges} • Cooldown: {cooldown_text}")
        scavenge_pet_charge_bonus = pet_effects.get("extra_charge_count", 0)
        scavenge_pet_stardust_bonus = pet_effects.get("extra_charges", 0.0)
        scavenge_pet_note = (
            f" • 🐉 Space Dragon: **+{scavenge_pet_charge_bonus} Max Charges**"
            if scavenge_pet_charge_bonus
            else ""
        )
        embed.add_field(
            name="🛠️ Scavenging Drone Upgrade",
            value=(f"Tier **{scavenging_upgrade['level']}/5** • Max Charges: **{max_scavenge_charges}**\n"
                   f"Stardust Bonus: **+{(scavenging_upgrade['stardust_mult'] - 1) * 100:.0f}%** • Rare Loot Bonus: **+{scavenging_upgrade['rare_bonus'] * 100:.1f}%**"
                   f"\nPet Stardust Bonus: **+{scavenge_pet_stardust_bonus * 100:.0f}%**{scavenge_pet_note}"),
            inline=False
        )
        embed.add_field(
            name="♻️ Salvage Rig Upgrade",
            value=(
                f"Tier **{salvage_upgrade['level']}/5** • Relative loot chance: **+{salvage_bonus_chance * 100:.0f}%**\n"
                "Applies to salvage materials, medical supplies, and bonus minerals.\n"
                "*The 8% bonus-mineral discovery gate is unchanged.*"
            ),
            inline=False
        )

        if pet_xp_result:
            pet_xp_text = f"🐾 **Pet XP:** **+{pet_xp_result['xp_added']} XP**"
            if pet_xp_result["leveled_up"]:
                pet_xp_text += f" • 🎉 **Level {pet_xp_result['new_level']}!**"
            embed.add_field(
                name="🐾 Companion Progress",
                value=pet_xp_text,
                inline=False,
            )

        if random.random() < 0.25 and await self.daily_unclaimed(user_id):
            embed.add_field(
                name="📅 Daily Reminder",
                value="You didn't claim your daily yet! Use `/daily` to claim your Stardust reward!",
                inline=False
            )

        cooldown_reminder = await self.maybe_suggest_cooldown_alerts(ctx)
        if cooldown_reminder:
            embed.add_field(
                name="🔔 Cooldown Alerts",
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
                    f"{ctx.author.mention} ❌ Profile not found! Explore Enceladus first."
                )

            hp, max_hp = user[0] or 0, user[1] or 100

            if hp > 0:
                return await ctx.send(
                    f"{ctx.author.mention} ⚠️ You are already conscious and do not need a revival."
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
                        "❌ This revival menu belongs to someone else.",
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
                            "❌ Profile not found!",
                            ephemeral=True
                        )

                    current_hp, max_hp = (
                        user_row[0] or 0,
                        user_row[1] or 100
                    )

                    if current_hp > 0:
                        return await interaction.followup.send(
                            "⚠️ You are already conscious!",
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
                            f"❌ You don't have an **{item_name}**!",
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
                        f"🚑 **Full Revival complete!**\n"
                        f"Your **{item_name}** restored you to "
                        f"❤️ **{recovered_hp}/{max_hp} HP**!"
                    )
                else:
                    message = (
                        f"💉 **Revival complete!**\n"
                        f"Your **{item_name}** restored you to "
                        f"❤️ **{recovered_hp}/{max_hp} HP**!"
                    )

                await interaction.edit_original_response(
                    content=message,
                    view=None
                )

        if not available:
            return await ctx.send(
                "❌ You don't have any revival items.\n"
                "You can buy an **Emergency Full Revival** from "
                "`/shop buy full_revive`, or recover automatically tomorrow."
            )

        embed = discord.Embed(
            title=f"💀 {ctx.author.display_name} — Revival Required",
            description=(
                "You are currently unconscious.\n\n"
                "Choose a revival method:"
            ),
            color=discord.Color.red()
        )

        revive_count = available.get("revive", 0)
        kit_count = available.get("revive_kit", 0)
        full_count = available.get("full_revive", 0)

        embed.add_field(
            name=f"{EMOJIS.get('revive', '⚕️')} Revival Kit",
            value=(
                "Restores **35% HP**\n"
                f"Owned: **{revive_count}**"
            ),
            inline=True
        )

        embed.add_field(
            name=f"{EMOJIS.get('revive_kit', '💉')} Emergency Revival Kit",
            value=(
                "Restores **50% HP**\n"
                f"Owned: **{kit_count}**"
            ),
            inline=True
        )

        embed.add_field(
            name=f"{EMOJIS.get('full_revive', '🚑')} Emergency Full Revival",
            value=(
                "Restores **100% HP**\n"
                f"Owned: **{full_count}**"
            ),
            inline=True
        )

        embed.set_footer(
            text="This revival menu will expire in 60 seconds."
        )

        await ctx.send(
            embed=embed,
            view=RevivalView()
        )

class HauntedLocationView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=90)
        self.cog = cog

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not is_halloween_channel(interaction.channel):
            await interaction.response.send_message(halloween_channel_message(), ephemeral=True)
            return False
        if not halloween_is_active():
            await interaction.response.send_message("🎃 Haunted Exploration is currently dormant.", ephemeral=True)
            return False
        return True

        for index, (location_id, location) in enumerate(HAUNTED_LOCATIONS.items()):
            self.add_item(HauntedLocationButton(self.cog, location_id, location, index))
        self.add_item(HauntedInfoButton(self.cog))


class HauntedLocationButton(discord.ui.Button):
    def __init__(self, cog, location_id, location, index):
        super().__init__(
            label=location["name"],
            emoji=location["emoji"],
            style=discord.ButtonStyle.secondary,
            row=index // 5,
        )
        self.cog = cog
        self.location_id = location_id

    async def callback(self, interaction: discord.Interaction):
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


class HauntedEncounterView(discord.ui.View):
    def __init__(self, cog, location_id, stage, total_stages, encounter):
        super().__init__(timeout=120)
        self.cog = cog
        self.location_id = location_id
        self.stage = stage
        self.total_stages = total_stages
        self.encounter = encounter

        for index, choice in enumerate(encounter["choices"]):
            label = choice.get("label", "Choose") if isinstance(choice, dict) else choice[0]
            risk = choice.get("risk", "medium") if isinstance(choice, dict) else "medium"
            self.add_item(HauntedChoiceButton(self.cog, self.location_id, self.stage, self.total_stages, self.encounter, index, label, risk))

        self.add_item(HauntedRunButton(self.cog, self.location_id, self.stage, self.total_stages))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not is_halloween_channel(interaction.channel):
            await interaction.response.send_message(halloween_channel_message(), ephemeral=True)
            return False
        if not halloween_is_active():
            await interaction.response.send_message("🎃 Haunted Exploration is currently dormant.", ephemeral=True)
            return False
        return True


class HauntedChoiceButton(discord.ui.Button):
    def __init__(self, cog, location_id, stage, total_stages, encounter, index, label, risk="medium"):
        styles = {
            "low": discord.ButtonStyle.secondary,
            "medium": discord.ButtonStyle.primary,
            "high": discord.ButtonStyle.danger,
            "extreme": discord.ButtonStyle.danger,
        }
        super().__init__(label=label, style=styles.get(risk, discord.ButtonStyle.secondary), row=0)
        self.cog = cog
        self.location_id = location_id
        self.stage = stage
        self.total_stages = total_stages
        self.encounter = encounter
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        await self.cog._resolve_haunted_choice(
            interaction,
            self.location_id,
            self.stage,
            self.total_stages,
            self.encounter,
            self.index,
        )


class HauntedRunButton(discord.ui.Button):
    def __init__(self, cog, location_id, stage, total_stages):
        super().__init__(
            label="Run Away",
            emoji="🏃",
            style=discord.ButtonStyle.danger,
            row=1,
        )
        self.cog = cog
        self.location_id = location_id
        self.stage = stage
        self.total_stages = total_stages

    async def callback(self, interaction: discord.Interaction):
        await self.cog._run_away_haunted(
            interaction,
            self.location_id,
            self.stage,
            self.total_stages,
        )


async def setup(bot):
    await bot.add_cog(Exploration(bot))
