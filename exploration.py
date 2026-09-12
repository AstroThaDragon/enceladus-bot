import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import asyncio
import time
import random
import json
from datetime import datetime, timedelta
import pytz
from inventory import add_inventory_item

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
            ("were scraped by sharp alien metal (probably need a tetnis shot now)", 15, 25, 20),
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

    def knockout_message(self, knocked_out_until):
        return (
            f"💀 **You are unconscious.** You can use `/revive` or buy `/shop buy full_revive` "
            f"to return now; otherwise you will recover at 50% HP on **{knocked_out_until}**."
        )

    @commands.hybrid_command(name="heal", description="Use a healing item from your inventory to restore HP.")
    @app_commands.choices(item=[
        app_commands.Choice(name="🩹 Nanite Stim-Patch (+35 HP)", value="nanite_patch"),
        app_commands.Choice(name="🧰 Field Trauma Medkit (+100 HP)", value="medkit")
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
            "medkit": {"name": "Field Trauma Medkit", "col": "medkits", "amount": 100}
        }

        selected = heal_data.get(item)
        if not selected:
            return await ctx.send("❌ Invalid healing item selected.")

        db_path = self.get_db_path()

        async with aiosqlite.connect(db_path) as db:
            await self.ensure_schema(db)
            await self.recover_if_new_day(db, user_id)

            col_name = selected["col"]
            async with db.execute("PRAGMA table_info(users)") as cursor:
                cols = {row[1] async for row in cursor}

            if col_name not in cols:
                return await ctx.send(f"❌ You don't have any **{selected['name']}s** in your inventory!")

            async with db.execute(
                f"SELECT hp, max_hp, {col_name}, knocked_out_until FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                return await ctx.send("❌ Profile not found!")

            current_hp, max_hp, item_count, knocked_out_until = (
                row[0] or 0,
                row[1] or 100,
                row[2] or 0,
                row[3] or ""
            )

            if current_hp <= 0:
                return await ctx.send(self.knockout_message(knocked_out_until or "tomorrow"))

            if item_count <= 0:
                return await ctx.send(f"❌ You don't have any **{selected['name']}s** left!")

            if current_hp >= max_hp:
                return await ctx.send(
                    f"❤️ **Full Health!** You are already at max HP (**{max_hp}/{max_hp} HP**)."
                )

            new_hp = min(max_hp, current_hp + selected["amount"])
            healed_by = new_hp - current_hp
            new_count = item_count - 1

            await db.execute(f"""
                UPDATE users
                SET hp = ?,
                    {col_name} = ?
                WHERE user_id = ?
            """, (new_hp, new_count, user_id))

            await db.commit()

        await ctx.send(
            f"💉 **Used {selected['name']}!**\n"
            f"Restored **+{healed_by} HP**! Current Health: ❤️ **{new_hp}/{max_hp} HP** "
            f"*(Items Remaining: {new_count})*"
        )

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

            if hp <= 0:
                return await ctx.send(self.knockout_message(knocked_out_until or "tomorrow"))

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
                charges = 10
                await db.execute(
                    "UPDATE users SET mining_charges = ? WHERE user_id = ?",
                    (10, user_id)
                )
                await db.commit()

            elapsed = current_time - last_mined

            if elapsed < self.COOLDOWN_SECONDS:
                remaining = int(self.COOLDOWN_SECONDS - elapsed)
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                return await ctx.send(f"⚠️ **Mining laser is recharging!** Next charge ready in **{hours}h {minutes}m**.")

            if charges <= 0 and not effects.get("fuel_stabilizer"):
                return await ctx.send(
                    "🚨 **Laser Depleted!** You are out of fuel charges. "
                    "Visit the station shop for an emergency refill or wait until daily reset."
                )

            # --- TIERED LOOT ROLL ---
            roll = 0.70 if effects.pop("ore_magnet", False) else random.random()
            new_charges = charges if effects.pop("fuel_stabilizer", False) else charges - 1
            
            found_stardust = random.randint(35, 85)

            if effects.pop("prototype_drill_bit", False):
                found_stardust = int(found_stardust * 1.5)

            if effects.pop("quantum_battery", False):
                found_stardust *= 3
                loot_bonus_note = "\n⚛️ **Quantum Battery:** Stardust tripled!"
            else:
                loot_bonus_note = ""

            new_stardust = stardust + found_stardust
            
            loot_description = (
                f"✨ **Stardust Collected:** `{found_stardust}`"
                f"{loot_bonus_note}"
            )
            rarity_badge = "common"

            if roll < 0.40:
                # Tier 1: Common (Just Stardust)
                pass

            elif roll < 0.60:
                # Tier 2: Uncommon (Stardust + XP Data Shard)
                found_xp = random.randint(75, 200)
                loot_description += f"\n📊 **XP Data Shard:** `+{found_xp} XP`"
                rarity_badge = "uncommon"

                # Award XP globally through leveling.py
                leveling_cog = self.bot.get_cog("Leveling")
                if leveling_cog:
                    leveled_up, new_level = await leveling_cog.add_xp(ctx.author, found_xp)
                    if leveled_up:
                        loot_description += f"\n🎉 **Level Up!** Reached **Level {new_level}**!"

            elif roll < 0.75:
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
                        f"\n⛏️ **Rare Ore Extracted:** Refined a "
                        f"`Titanium Ore Chunk`! ({new_quantity}/{max_quantity})"
                    )
                else:
                    overflow_stardust = 75
                    new_stardust += overflow_stardust

                    loot_description += (
                        f"\n📦 **Inventory Full:** Your Titanium Ore Chunk stack "
                        f"is already at **{max_quantity}/{max_quantity}**!"
                        f"\n✨ **Converted to:** `+{overflow_stardust} Stardust`"
                    )

                rarity_badge = "rare"

            elif roll < 0.88:
                # Tier 4: Rare/Epic (Arcade Token for future minigames)
                added_amount, new_quantity, max_quantity = await add_inventory_item(
                    db,
                    user_id,
                    "arcade_token",
                    "currency",
                    1
                )

                if added_amount == 1:
                    loot_description += (
                        f"\n🪙 **Holodeck Find:** Discovered a shiny "
                        f"**Arcade Token**! ({new_quantity}/{max_quantity})"
                    )
                else:
                    overflow_stardust = 50
                    new_stardust += overflow_stardust

                    loot_description += (
                        f"\n📦 **Inventory Full:** Your Arcade Token stack "
                        f"is already at **{max_quantity}/{max_quantity}**!"
                        f"\n✨ **Converted to:** `+{overflow_stardust} Stardust`"
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
                        f"\n💎 **Rare Discovery:** Acquired a stable "
                        f"**Dilated Time Crystal**! "
                        f"({current_crystals + 1}/{max_quantity})"
                    )
                else:
                    overflow_stardust = 350
                    new_stardust += overflow_stardust

                    loot_description += (
                        f"\n📦 **Inventory Full:** Your Dilated Time Crystal "
                        f"stack is already at **{max_quantity}/{max_quantity}**!"
                        f"\n✨ **Converted to:** `+{overflow_stardust} Stardust`"
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
                    overflow_stardust = 750
                    new_stardust += overflow_stardust

                    loot_description += (
                        f"\n📦 **Inventory Full:** Your Astral Core stack "
                        f"is already at **{max_quantity}/{max_quantity}**!"
                        f"\n✨ **Converted to:** `+{overflow_stardust} Stardust`"
                        "\n*The mysterious core was too much for your inventory to contain.*"
                    )

                rarity_badge = "legendary"

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
            title="🌌 Starship Mining Log",
            description=f"Laser beam fired into the debris field...\n\n{loot_description}",
            color=colors.get(rarity_badge, discord.Color.blue())
        )
        embed.set_footer(text=f"Fuel Charges Remaining: {new_charges}/10 • Cooldown: 30m")
        
        await ctx.send(embed=embed)

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
                charges = 10
                await db.execute(
                    "UPDATE users SET scavenge_charges = ? WHERE user_id = ?",
                    (10, user_id)
                )
                await db.commit()

            elapsed = current_time - last_scavenged

            # Health Knockout Check
            if hp <= 0:
                return await ctx.send(self.knockout_message(knocked_out_until or "tomorrow"))

            if elapsed < self.COOLDOWN_SECONDS:
                remaining = int(self.COOLDOWN_SECONDS - elapsed)
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                return await ctx.send(f"⚠️ **Scavenge drone is recharging!** Next run ready in **{hours}h {minutes}m**.")

            if charges <= 0:
                return await ctx.send("🚨 **Drone Depleted!** You are out of scavenge charges. Visit the station shop for a recharge.")

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
            # Legendary loot has a flat 4% chance.
            # Quantum Batteries are exclusive to scavenging.
            legendary_roll = random.random()

            if legendary_roll >= 0.96:
                item_id = "quantum_battery"
                item_name = "⚛️ Quantum Battery (legendary)"
                item_type = "consumable"
                loot_rarity_note = (
                    "\n🌟 **Legendary Find:** Recovered a "
                    "**Quantum Battery**!"
                )

            elif random.random() < (0.15 if effects.pop("lucky_scanner", False) else 0.02):
                item_id = "revive_kit"
                item_name = "💉 Emergency Revival Kit (rare)"
                item_type = "consumable"
                loot_rarity_note = ""

            else:
                item_id, item_name = random.choice(list(junk_items.items()))
                item_type = "space_junk"
                loot_rarity_note = ""
            new_charges = charges - 1
            found_stardust = random.randint(15, 35)

            if effects.pop("quantum_battery", False):
                found_stardust *= 3
                quantum_bonus_note = "\n⚛️ **Quantum Battery:** Stardust tripled!"
            else:
                quantum_bonus_note = ""

            new_stardust = stardust + found_stardust

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
                damage_taken = random.randint(min_damage, max_damage)
                hazard_note = f"\n⚠️ **Hazard Warning!** You {hazard} and took **-{damage_taken} HP**."

            new_hp = max(0, hp - damage_taken)
            if new_hp <= 0 and effects.pop("cosmic_insurance", False):
                new_hp = 1
                hazard_note += "\n📋 **Cosmic Insurance:** Your coverage kept you at **1 HP**."

            knocked_out_until = ""
            if new_hp <= 0:
                knocked_out_until = (self.game_date() + timedelta(days=1)).isoformat()
                hazard_note += f"\n💀 **Knockout Report:** {random.choice(self.KNOCKOUT_LINES)}"

            added_amount, new_quantity, max_quantity = await add_inventory_item(
                db,
                user_id,
                item_id,
                item_type,
                1
            )

            if added_amount == 1:
                loot_name_with_quantity = f"{item_name} ({new_quantity}/{max_quantity})"
            else:
                # ─────────────────────────────────────────────
                # SCAVENGE OVERFLOW VALUES
                # Adjust these Stardust values individually as desired.
                # ─────────────────────────────────────────────
                overflow_values = {
                    # Legendary / Rare
                    "quantum_battery": 800,
                    "revive_kit": 300,

                    # Space Junk
                    "space_pizza": 10,
                    "floppy_disk": 10,
                    "meteorite": 10,
                    "rubber_duck": 10,
                    "rusty_gear": 10,
                    "tape_deck": 10,
                    "alien_artifact": 10,
                    "space_boot": 10,
                    "cosmic_coin": 10,
                    "holo_poster": 10,
                    "broken_laser": 10,
                    "lost_logbook": 10,
                    "left_sock": 10,
                    "warp_mug": 10,
                    "space_pudding": 10,
                    "tangled_cables": 10,
                    "screaming_crystal": 10,
                    "moon_cheese": 10,
                    "golden_spatula": 10,
                    "parking_ticket": 10,
                    "floating_plant": 10,
                    "tinted_visor": 10,
                    "purring_lint": 10,
                    "pet_rock": 10,
                    "haunted_circuit": 10,
                    "space_taco": 10,
                    "rusty_wrench": 10,
                    "alien_fossil": 10,
                    "big_red_button": 10,
                    "antique_compass": 10,
                    "broken_clock": 10,
                    "perplexing_painting": 10,
                    "cosmic_banana": 10,
                }

                # Use the item's individual overflow value.
                # The fallback protects against a newly added loot item
                # accidentally having no configured overflow value.
                overflow_stardust = overflow_values.get(item_id, 10)

                new_stardust += overflow_stardust

                loot_name_with_quantity = (
                    f"{item_name}\n"
                    f"📦 **Inventory Full:** Stack is already "
                    f"**{max_quantity}/{max_quantity}**!"
                    f"\n✨ **Converted to:** `+{overflow_stardust} Stardust`"
                )

            await db.execute("""
                UPDATE users 
                SET scavenge_charges = ?, last_scavenged = ?, stardust = ?, hp = ?, knocked_out_until = ?, active_effects = ?
                WHERE user_id = ?
            """, (new_charges, current_time, new_stardust, new_hp, knocked_out_until, json.dumps(effects), user_id))

            await db.commit()

        status_text = f"❤️ **Health:** `{new_hp}/{max_hp} HP`" if new_hp > 0 else f"💀 **Knocked Out!** Use `/revive`, buy `/shop buy full_revive`, or recover at 50% HP on **{knocked_out_until}**."

        embed = discord.Embed(
            title="🛠️ Derelict Salvage Log",
            description=(
                f"Scavenge drone deployed into abandoned sector wreckage...\n\n"
                f"✨ **Found Stardust:** `{found_stardust}`"
                f"{quantum_bonus_note}\n"
                f"🛸 **Salvaged Item:** `{loot_name_with_quantity}`"
                f"{loot_rarity_note}"
                f"{hazard_note}\n\n"
                f"{status_text}"
            ),
            color=discord.Color.dark_gold()
        )
        embed.set_footer(text=f"Drone Charges Remaining: {new_charges}/10 • Cooldown: 30m")

        await ctx.send(embed=embed)

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
                    "❌ Profile not found! Explore Enceladus first."
                )

            hp, max_hp = user[0] or 0, user[1] or 100

            if hp > 0:
                return await ctx.send(
                    "⚠️ You are already conscious and do not need a revival."
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
                    emoji="⚕️",
                    style=discord.ButtonStyle.secondary,
                    disabled=available.get("revive", 0) <= 0
                )
                revive_button.callback = self.use_revive_kit
                self.add_item(revive_button)

                kit_button = discord.ui.Button(
                    label="Emergency Revival Kit",
                    emoji="💉",
                    style=discord.ButtonStyle.primary,
                    disabled=available.get("revive_kit", 0) <= 0
                )
                kit_button.callback = self.use_emergency_kit
                self.add_item(kit_button)

                full_button = discord.ui.Button(
                    label="Emergency Full Revival",
                    emoji="🚑",
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
                        item_name = (
                            "Emergency Revival Kit"
                            if item_id == "revive_kit"
                            else "Emergency Full Revival"
                        )

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

                item_name = (
                    "Emergency Revival Kit"
                    if item_id == "revive_kit"
                    else "Emergency Full Revival"
                )

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
            title="💀 Revival Required",
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
            name="⚕️ Revival Kit",
            value=(
                "Restores **35% HP**\n"
                f"Owned: **{revive_count}**"
            ),
            inline=True
        )

        embed.add_field(
            name="💉 Emergency Revival Kit",
            value=(
                "Restores **50% HP**\n"
                f"Owned: **{kit_count}**"
            ),
            inline=True
        )

        embed.add_field(
            name="🚑 Emergency Full Revival",
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
async def setup(bot):
    await bot.add_cog(Exploration(bot))
