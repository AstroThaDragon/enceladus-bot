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

class Exploration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._user_locks = {}
        self.COOLDOWN_SECONDS = 30 * 60  # 30-minute cooldown
        self.SCAVENGE_HAZARDS = [
            # Minor hazards are common: funny setbacks, small damage.
            ("tripped over a strategically placed space wrench", 5, 10, 18),
            ("was judged by a maintenance Roomba and lost the argument", 5, 10, 18),
            ("bonked their helmet on a low-gravity ceiling sign", 6, 12, 16),
            ("got lightly zapped by a suspiciously cheerful control panel", 7, 12, 16),
            ("slipped on a patch of moon-cheese residue", 4, 9, 16),
            ("was startled by a toaster that insisted it was sentient", 5, 11, 14),
            ("got tangled in a cable that had clearly been waiting for this moment", 6, 12, 14),
            ("walked into a door that was technically open", 4, 8, 14),
            ("was pelted by an aggressively enthusiastic air filter", 5, 10, 12),
            ("lost a staring contest with a suspicious houseplant", 6, 11, 12),
            # Moderate hazards are the usual danger of wreckage exploration.
            ("inhaled sharp hull-debris dust", 12, 20, 14),
            ("was scraped by sharp alien metal", 12, 22, 14),
            ("triggered an electrical spark while searching wreckage", 14, 24, 12),
            ("was chased through a corridor by an overenthusiastic security drone", 15, 25, 10),
            ("fell through a floor panel that looked emotionally stable", 13, 23, 12),
            ("caught a blast of freezer-cold life-support exhaust", 12, 21, 12),
            ("activated a cleaning bot's 'deep clean' setting", 14, 24, 10),
            ("was sideswiped by a runaway supply crate", 15, 25, 10),
            ("opened a locker full of spring-loaded asteroid samples", 13, 22, 10),
            ("discovered that the abandoned ship still had its alarms set to rude", 14, 23, 10),
            ("briefly became the target of an antique defense turret's welcome sequence", 16, 25, 8),
            # Severe hazards are uncommon, but should make a run feel memorable.
            ("tried to pet a reactor leak and immediately regretted it", 24, 35, 5),
            ("lost a wrestling match with an unsecured cargo loader", 26, 38, 4),
            ("opened a door marked 'definitely not haunted'", 25, 40, 3),
            ("was introduced to a malfunctioning gravity plate at full enthusiasm", 24, 36, 5),
            ("accidentally attended a security drone's very personal laser presentation", 25, 38, 4),
            ("found the source of the ominous humming, and it found them back", 27, 40, 3),
            ("triggered an escape pod launch rehearsal without the escape pod", 23, 35, 4),
            ("attempted to outrun a decompression warning and lost on points", 26, 39, 3),
        ]
        self.KNOCKOUT_LINES = [
            "Station AI report: explorer status changed to *crispy but recoverable*.",
            "The station medic has added your name to the 'please stop touching things' list.",
            "A nearby drone recorded the incident for training purposes. Unfortunately, it was laughing.",
            "Your insurance provider has described this as 'an ambitious interpretation of safety protocol.'",
            "Enceladus Station would like to remind you that gravity is not a personal challenge.",
            "The wreckage won this round. It has been insufferable about it.",
            "Your emergency beacon activated itself out of professional concern.",
            "The station's accident report form has auto-filled your name. Again.",
            "A maintenance bot placed a tiny traffic cone beside you. Respectfully.",
            "The ship's computer has labeled this event: 'operator-adjacent malfunction.'",
            "A passing astronaut gave you a thumbs-up. It was not reassuring.",
            "Your helmet camera saved the footage under 'definitely_do_not_share.mp4'.",
            "The local ghost has filed a noise complaint about your landing.",
            "Station morale improved by 0.3%. The reason has been redacted.",
            "A janitorial drone swept around you and whispered, 'same.'",
            "The cargo loader has requested a rematch, which feels unnecessary.",
            "A safety poster peeled off the wall, sighed, and pointed at itself.",
            "Your distress signal was answered by hold music. Very dramatic hold music.",
            "The nearest vending machine dispensed a consolation pretzel.",
            "Medical bay has prepared a blanket, juice box, and a strongly worded pamphlet.",
            "The station AI has awarded you the badge: 'Unscheduled Floor Inspection.'",
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
            await db.execute("ALTER TABLE users ADD COLUMN scavenge_charges INTEGER DEFAULT 5")
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

    @commands.hybrid_command(name="mine", description="Deploy your starship mining laser to scout for stardust and rare loot.")
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

            elapsed = current_time - last_mined
            if charges < 10 and elapsed >= self.COOLDOWN_SECONDS:
                charges = min(10, charges + int(elapsed // self.COOLDOWN_SECONDS))
            if elapsed < self.COOLDOWN_SECONDS:
                remaining = int(self.COOLDOWN_SECONDS - elapsed)
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                return await ctx.send(f"⚠️ **Mining laser is recharging!** Next charge ready in **{hours}h {minutes}m**.")

            if charges <= 0:
                return await ctx.send("🚨 **Laser Depleted!** You are out of fuel charges. Visit the station shop for an emergency refill.")

            # --- TIERED LOOT ROLL ---
            roll = 0.70 if effects.pop("ore_magnet", False) else random.random()
            new_charges = charges if effects.pop("fuel_stabilizer", False) else charges - 1
            
            found_stardust = random.randint(35, 85)
            if effects.pop("prototype_drill_bit", False):
                found_stardust = int(found_stardust * 1.5)
            new_stardust = stardust + found_stardust
            
            loot_description = f"✨ **Stardust Collected:** `{found_stardust}`"
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
                await db.execute("""
                    INSERT INTO inventory (user_id, item_id, item_type, quantity)
                    VALUES (?, 'titanium_chunk', 'mineral', 1)
                    ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + 1
                """, (user_id,))
                
                loot_description += f"\n⛏️ **Rare Ore Extracted:** Refined a `Titanium Ore Chunk`!"
                rarity_badge = "rare"

            elif roll < 0.88:
                # Tier 4: Rare/Epic (Arcade Token for future minigames)
                await db.execute("""
                    INSERT INTO inventory (user_id, item_id, item_type, quantity)
                    VALUES (?, 'arcade_token', 'currency', 1)
                    ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + 1
                """, (user_id,))
                loot_description += f"\n🪙 **Holodeck Find:** Discovered a shiny **Arcade Token**!"
                rarity_badge = "rare"

            elif roll < 0.96:
                # Tier 5: Epic (Dilated Time Crystal)
                await db.execute("UPDATE users SET time_crystals = COALESCE(time_crystals, 0) + 1 WHERE user_id = ?", (user_id,))
                loot_description += f"\n💎 **Rare Discovery:** Acquired a stable **Dilated Time Crystal**!"
                rarity_badge = "epic"

            else:
                # Tier 6: Legendary (Secret Background Voucher)
                voucher_id = random.choice(["neon_grid", "deep_void", "solaris_ring"])
                await db.execute("""
                    INSERT INTO inventory (user_id, item_id, item_type, quantity)
                    VALUES (?, ?, 'background_voucher', 1)
                    ON CONFLICT(user_id, item_id) DO NOTHING
                """, (user_id, voucher_id))
                loot_description += f"\n🌟 **Legendary Find:** Unlocked blueprint voucher `[{voucher_id}]`!"
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
            description=f"Laser beam fired into the sector debris field...\n\n{loot_description}",
            color=colors.get(rarity_badge, discord.Color.blue())
        )
        embed.set_footer(text=f"Fuel Charges Remaining: {new_charges}/10 • Cooldown: 30m")
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="scavenge", description="Search derelict wreckage for salvage, Stardust, and occasional rare finds.")
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

            elapsed = current_time - last_scavenged
            if charges < 10 and elapsed >= self.COOLDOWN_SECONDS:
                charges = min(10, charges + int(elapsed // self.COOLDOWN_SECONDS))

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
                "alien_artifact": "🛸 Miniature Alien Artifact (Glows faintly)",
                "space_boot": "🥾 Single Space Boot",
                "cosmic_coin": "🪙 Cosmic Coin (Heads: Unknown, Tails: Mystery)",
                "holo_poster": "🖼️ Faded Holographic Poster of a Galactic Band",
                "broken_laser": "🔫 Broken Laser Pistol (sparks occasionally)",
                "lost_logbook": "📓 Waterlogged Starship Logbook (unreadable)",
                "left_sock": "🧦 Single Left Space Sock (the right one was lost to a wormhole)",
                "warp_mug": "☕ Leaky Thermal Mug (holds coffee across space-time, leaks in 3D)",
                "space_pudding": "🍮 Expired Void Pudding (tastes suspiciously like dark matter)",
                "tangled_cables": "🔌 Quantum Cable Knot (physically impossible to untangle)",
                "screaming_crystal": "💎 Screaming Crystal (relentlessly sings 80s synth-pop)",
                "moon_cheese": "🧀 Chunk of Moon Cheese (smells like sharp cheddar)",
                "alien_spatula": "🛸 Intergalactic Spatula (slightly sticky with cosmic grease)",
                "parking_ticket": "📜 Cosmic Parking Ticket (overdue by 400 light-years)",
                "floating_plant": "🪴 Suspicious Houseplant (directly stares at you when you turn around)",
                "tinted_visor": "🕶️ Broken Solar Visor (now just regular 3D glasses)",
                "purring_lint": "🧶 Ball of Space Lint (it purrs when you touch it)",
                "pet_rock": "🪨 Asteroid Pet Rock (includes tiny drawn-on googly eyes)",
                "haunted_circuit": "⚡ Haunted Circuit Board (sparks every time you whisper near it)",
                "space_taco": "🌮 Cosmic Taco (the salsa is surprisingly unaffected by zero-G)"
            }
            
            if random.random() < (0.25 if effects.pop("lucky_scanner", False) else 0.05):
                item_id = "revive_kit"
                item_name = "💉 Emergency Revival Kit (rare recovery salvage)"
                item_type = "consumable"
            else:
                item_id, item_name = random.choice(list(junk_items.items()))
                item_type = "space_junk"
            new_charges = charges - 1
            found_stardust = random.randint(15, 35)
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
            if new_hp <= 0 and effects.pop("salvage_insurance", False):
                new_hp = 1
                hazard_note += "\n📋 **Salvage Insurance:** Your emergency coverage kept you at **1 HP**."

            knocked_out_until = ""
            if new_hp <= 0:
                knocked_out_until = (self.game_date() + timedelta(days=1)).isoformat()
                hazard_note += f"\n💀 **Knockout Report:** {random.choice(self.KNOCKOUT_LINES)}"

            await db.execute("""
                INSERT INTO inventory (user_id, item_id, item_type, quantity)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(user_id, item_id) DO UPDATE SET
                    item_type = excluded.item_type,
                    quantity = quantity + 1
            """, (user_id, item_id, item_type))

            await db.execute("""
                UPDATE users 
                SET scavenge_charges = ?, last_scavenged = ?, stardust = ?, hp = ?, knocked_out_until = ?, active_effects = ?
                WHERE user_id = ?
            """, (new_charges, current_time, new_stardust, new_hp, knocked_out_until, json.dumps(effects), user_id))

            await db.commit()

        status_text = f"❤️ **Health:** `{new_hp}/{max_hp} HP`" if new_hp > 0 else f"💀 **Knocked Out!** Use `/revive`, buy `/shop buy full_revive`, or recover at 50% HP on **{knocked_out_until}**."

        embed = discord.Embed(
            title="🛠️ Derelict Salvage Log",
            description=f"Scavenge drone deployed into abandoned sector wreckage...\n\n✨ **Scrap Stardust:** `{found_stardust}`\n🛸 **Salvaged Item:** `{item_name}`{hazard_note}\n\n{status_text}",
            color=discord.Color.dark_gold()
        )
        embed.set_footer(text=f"Drone Charges Remaining: {new_charges}/10 • Cooldown: 30m")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="revive", description="Use an Emergency Revival Kit to return at half health.")
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
                return await ctx.send("❌ Profile not found! Explore Enceladus first.")

            hp, max_hp = user[0] or 0, user[1] or 100

            if hp > 0:
                return await ctx.send(
                    "⚠️ You are already conscious and do not need a revival."
                )

            async with db.execute(
                "SELECT quantity FROM inventory "
                "WHERE user_id = ? AND item_id = 'revive_kit'",
                (user_id,)
            ) as cursor:
                kit = await cursor.fetchone()

            if not kit or (kit[0] or 0) <= 0:
                return await ctx.send(
                    "❌ You do not have an Emergency Revival Kit. "
                    "Buy a full revival at `/shop buy full_revive`, or recover tomorrow."
                )

            if kit[0] > 1:
                await db.execute(
                    "UPDATE inventory SET quantity = quantity - 1 "
                    "WHERE user_id = ? AND item_id = 'revive_kit'",
                    (user_id,)
                )
            else:
                await db.execute(
                    "DELETE FROM inventory "
                    "WHERE user_id = ? AND item_id = 'revive_kit'",
                    (user_id,)
                )

            recovered_hp = max(1, (max_hp + 1) // 2)

            await db.execute(
                "UPDATE users SET hp = ?, knocked_out_until = '' WHERE user_id = ?",
                (recovered_hp, user_id)
            )

            await db.commit()

        await ctx.send(
            f"💉 **Revival complete!** Your Emergency Revival Kit restored you to "
            f"**{recovered_hp}/{max_hp} HP**."
        )
async def setup(bot):
    await bot.add_cog(Exploration(bot))
