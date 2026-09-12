import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import asyncio
import time
import json
import random
from datetime import datetime
import pytz
import random

# Master Item Registry used across inventory, shop, and exploration
ITEM_REGISTRY = {
    # Currencies & Consumables
    "fuel_refill": {"name": "Emergency Fuel Cell", "emoji": "⚡", "max_quantity": 5, "type": "Consumable", "desc": "Instantly refills your starship mining laser back to 10/10 charges."},
    "pet_snack": {"name": "Cosmic Bio-Feed", "emoji": "🧬", "max_quantity": 50, "type": "Consumable", "desc": "Nutrient pack for your station pet."},
    "arcade_token": {"name": "Arcade Token", "emoji": "🪙", "max_quantity": 100, "type": "Currency", "desc": "Shiny token for future station mini-games."},
    "time_crystal": {"name": "Dilated Time Crystal", "emoji": "💎", "max_quantity": 4, "type": "Consumable", "desc": "Bends time backwards to restore a fortune streak missed yesterday."},
    "nanite_patch": {"name": "Nanite Stim-Patch", "emoji": "🩹", "max_quantity": 50, "type": "Consumable", "desc": "Quickly knits minor planetary surface wounds. Restores +35 HP."},
    "medkit": {"name": "Field Trauma Medkit", "emoji": "🧰", "max_quantity": 25, "type": "Consumable", "desc": "Standard planetary survival trauma kit. Restores +100 HP."},
    "full_revive": {"name": "Emergency Full Revival", "emoji": "⚕️", "max_quantity": 10, "type": "Healing", "desc": "Immediately revives an unconscious explorer at full HP."},
    "revive_kit": {"name": "Emergency Revival Kit", "emoji": "💉", "max_quantity": 25, "type": "Consumable", "desc": "Rare salvage that revives an unconscious explorer with 50% HP."},
    "revive": {"name": "Revival Kit", "emoji": "⚕️", "max_quantity": 25, "type": "Consumable", "desc": "A basic revival item"},
    "fuel_stabilizer": {"name": "Fuel Stabilizer", "emoji": "🛢️", "max_quantity": 5, "type": "Consumable", "desc": "Makes the next mining run cost no fuel charge."},
    "station_rations": {"name": "Station Rations", "emoji": "🥫", "max_quantity": 99, "type": "Consumable", "desc": "Restores 15 HP."},
    "hazard_shield": {"name": "Hazard Shield", "emoji": "🛡️", "max_quantity": 5, "type": "Consumable", "desc": "Blocks the next scavenging hazard."},
    "drone_battery": {"name": "Drone Battery Pack", "emoji": "🔋", "max_quantity": 5, "type": "Consumable", "desc": "Restores two scavenge charges."},
    "lucky_scanner": {"name": "Deep-Space Scanner", "emoji": "📡", "max_quantity": 5, "type": "Consumable", "desc": "Improves rare-find odds on the next scavenging run."},
    "ore_magnet": {"name": "Ore Magnet", "emoji": "🧲", "max_quantity": 5, "type": "Consumable", "desc": "Guarantees a titanium ore find on the next mining run."},
    "prototype_drill_bit": {"name": "Prototype Drill Bit", "emoji": "⚙️", "max_quantity": 5, "type": "Consumable", "desc": "Boosts Stardust from the next mining run."},
    "cosmic_insurance": {"name": "Cosmic Insurance", "emoji": "📋", "max_quantity": 5, "type": "Consumable", "desc": "Prevents a knockout from the next scavenging hazard."},
    "fate_anchor": {"name": "Fate Anchor", "emoji": "⚓", "max_quantity": 5, "type": "Consumable", "desc": "Protects one missed fortune streak day."},
    "stardust_cache": {"name": "Contraband Stardust Cache", "emoji": "🎁", "max_quantity": 10, "type": "Consumable", "desc": "Opens for an unpredictable Stardust payoff."},

    # Legendary Loot
    "astral_core": {"name": "Astral Core", "emoji": "🌌", "max_quantity": 5, "type": "Special", "desc": "A mysterious crystalline core recovered from deep space. May be used in the future..."},
    "quantum_battery": {"name": "Quantum Battery", "emoji": "⚛️", "max_quantity": 5, "type": "Consumable", "desc": "Powers your next mining or scavenging run, tripling its Stardust yield."},

    # Minerals
    "titanium_chunk": {"name": "Titanium Ore Chunk", "emoji": "⛏️", "max_quantity": 50, "type": "Mineral", "desc": "High-purity raw titanium extracted from deep sector asteroids."},

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
    "perplexing_painting": {"name": "Perplexing Painting", "emoji": "🖌️", "max_quantity": 99, "type": "Space Junk", "desc": "The eyes seem to follow you, but it's a 2D image."},
    "cosmic_banana": {"name": "Cosmic Banana", "emoji": "🍌", "max_quantity": 99, "type": "Space Junk", "desc": "Peels itself, but tastes like stardust."},

    # Background Vouchers
    "neon_grid": {"name": "Background Voucher: Neon Grid", "emoji": "🌆", "max_quantity": 1, "type": "Voucher", "desc": "Unlocks the Cyberpunk Neon Grid profile card."},
    "deep_void": {"name": "Background Voucher: Deep Void", "emoji": "🌌", "max_quantity": 1, "type": "Voucher", "desc": "Unlocks the Deep Void galaxy profile card."},
    "solaris_ring": {"name": "Background Voucher: Solaris Ring", "emoji": "☀️", "max_quantity": 1, "type": "Voucher", "desc": "Unlocks the Solaris Ring star system profile card."},

    # Profile Titles
    "title_outer_rim_wanderer": {"name": "Outer Rim Wanderer", "emoji": "🏷️", "max_quantity": 1, "type": "Title","desc": "A title for explorers who venture beyond the station."},
    "title_starborn": {"name": "Starborn", "emoji": "✨", "max_quantity": 1, "type": "Title", "desc": "A prestigious title for those touched by the stars."},
    "title_voidfarer": {"name": "Voidfarer", "emoji": "🌌", "max_quantity": 1, "type": "Title", "desc": "A title for those brave enough to chart the endless void."}
}

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

            if current and current not in display_name.lower():
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
                        "❌ **Title unequipped.** Your profile is now title-free."
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
                f"🏷️ **Title Equipped!** Your profile title is now "
                f"**{display_name}**."
            )

    @commands.hybrid_command(name="inventory", description="Open your station storage locker to view collected items and vouchers.")
    async def inventory(self, ctx: commands.Context):
        await ctx.defer()
        user_id = ctx.author.id

        async with aiosqlite.connect(self.get_db_path()) as db:
            # 1. Fetch standard items from the inventory table
            async with db.execute("SELECT item_id, item_type, quantity FROM inventory WHERE user_id = ?", (user_id,)) as cursor:
                inv_rows = await cursor.fetchall()

            # 2. Fetch healing items and time crystals from the users table
            # (Failsafes added using PRAGMA to ensure columns exist before querying)
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

        if not inv_rows and not user_items:
            return await ctx.send("📦 **Your storage locker is completely empty!** Head out with `/mine` or `/scavenge` to fill it up!")

        embed = discord.Embed(
            title=f"📦 {ctx.author.display_name}'s Storage Locker",
            description="Here is a manifest of all salvaged artifacts, minerals, and vouchers in your inventory:",
            color=discord.Color.from_rgb(0, 229, 255)
        )

        categories = {"Space Junk": [], "Mineral": [], "Consumable": [], "Voucher": [], "Currency": []}

        # Format and append items tracked in the users table
        for item_id, count in user_items:
            item_info = ITEM_REGISTRY.get(item_id)
            if not item_info:
                continue

            cat = item_info.get("type", "Consumable")
            if cat not in categories:
                categories[cat] = []
            max_quantity = item_info.get("max_quantity", 10)
            categories[cat].append(
                f"{item_info['emoji']} **{item_info['name']}** "
                f"({count}/{max_quantity})\n"
                f"└ *{item_info['desc']}*"
            )

        # Format and append items tracked in the inventory table
        for item_id, item_type, quantity in inv_rows:
            item_info = ITEM_REGISTRY.get(item_id, {"name": item_id, "emoji": "📦", "type": "Space Junk", "desc": "A weird salvage find."})
            cat = item_info.get("type", "Space Junk")
            if cat not in categories:
                categories[cat] = []
            max_quantity = item_info.get("max_quantity", 10)
            categories[cat].append(
                f"{item_info['emoji']} **{item_info['name']}** "
                f"({quantity or 1}/{max_quantity})\n"
                f"└ *{item_info['desc']}*"
            )

        for cat_name, items in categories.items():
            if not items:
                continue

            chunks = []
            current_chunk = ""

            for item in items:
                if len(current_chunk) + len(item) + 1 > 1024:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = item
                else:
                    current_chunk = (
                        f"{current_chunk}\n{item}"
                        if current_chunk
                        else item
                    )

            if current_chunk:
                chunks.append(current_chunk)

            for index, chunk in enumerate(chunks):
                field_name = (
                    f"✨ {cat_name}s"
                    if len(chunks) == 1
                    else f"✨ {cat_name}s ({index + 1}/{len(chunks)})"
                )

                embed.add_field(
                    name=field_name,
                    value=chunk,
                    inline=False
                )

        embed.set_footer(text="Tip: Sell your unwanted salvage at the trading post using /shop sell")
        await ctx.send(embed=embed)

    async def use_item_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ):
        """Show items the user owns that can currently be used."""
        user_id = interaction.user.id
        current = current.lower().strip()

        # Items that /use currently supports.
        usable_items = {
            "fuel_refill",
            "fuel_stabilizer",
            "station_rations",
            "hazard_shield",
            "drone_battery",
            "lucky_scanner",
            "ore_magnet",
            "prototype_drill_bit",
            "cosmic_insurance",
            "fate_anchor",
            "stardust_cache",
            "quantum_battery",
        }

        async with aiosqlite.connect(self.get_db_path()) as db:
            async with db.execute(
                """
                SELECT item_id, quantity
                FROM inventory
                WHERE user_id = ?
                  AND quantity > 0
                """,
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()

        choices = []

        for item_id, quantity in rows:
            if item_id not in usable_items:
                continue

            info = ITEM_REGISTRY.get(item_id)
            if not info:
                continue

            display_name = info["name"]

            if current and current not in display_name.lower():
                continue

            choices.append(
                app_commands.Choice(
                    name=f"{info['emoji']} {display_name} (x{quantity})",
                    value=item_id
                )
            )

        choices.sort(key=lambda choice: choice.name.lower())

        return choices[:25]

    @commands.hybrid_command(name="use", description="Use a consumable from your inventory.")
    @app_commands.describe(
        item_id="Choose an item from your inventory."
    )
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
            # Fallback for unusual startup/test situations where Exploration
            # has not loaded yet.
            if not hasattr(self, "_user_locks"):
                self._user_locks = {}
            lock = self._user_locks.setdefault(user_id, asyncio.Lock())

        async with lock:
            return await self._use_item_impl(ctx, item_id)


    async def _use_item_impl(self, ctx: commands.Context, item_id: str):
        user_id = ctx.author.id
        item_id = item_id.lower().strip()
        valid = {
            "fuel_refill",
            "fuel_stabilizer",
            "station_rations",
            "hazard_shield",
            "drone_battery",
            "lucky_scanner",
            "ore_magnet",
            "prototype_drill_bit",
            "cosmic_insurance",
            "fate_anchor",
            "stardust_cache",
            "quantum_battery",
        }
        if item_id not in valid:
            return await ctx.send("❌ That item cannot be used here. Use `/revive` for an Emergency Revival Kit.")

        async with aiosqlite.connect(self.get_db_path()) as db:
            await self.ensure_effect_schema(db)
            async with db.execute("SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, item_id)) as cursor:
                row = await cursor.fetchone()
            if not row or (row[0] or 0) <= 0:
                return await ctx.send(f"❌ You do not have `{item_id}` in your inventory.")

            async with db.execute("SELECT hp, max_hp, mining_charges, scavenge_charges, last_mined, last_scavenged, active_effects FROM users WHERE user_id = ?", (user_id,)) as cursor:
                user = await cursor.fetchone()
            if not user:
                return await ctx.send("❌ Profile not found! Explore Enceladus first.")
            hp, max_hp, mining, scavenging, last_mined, last_scavenged, effects_raw = user
            effects = json.loads(effects_raw or "{}")
            message = ""

            if item_id == "fuel_refill":
                if (mining or 0) >= 10:
                    return await ctx.send("⚠️ Your mining laser fuel charges are already full (`10/10`)!")
                mining = 10
                await db.execute(
                    "UPDATE users SET mining_charges = ? WHERE user_id = ?",
                    (mining, user_id)
                )
                message = "⚡ **Fuel Cell Used!** Your mining laser is refilled to `10/10` charges."

            elif item_id == "station_rations":
                if (hp or 0) <= 0:
                    return await ctx.send("💀 Rations cannot revive an unconscious explorer.")

                old_hp = hp or 0
                hp = min(max_hp or 100, old_hp + 15)
                restored = hp - old_hp

                if restored <= 0:
                    return await ctx.send("⚠️ Your HP is already full!")

                await db.execute(
                    "UPDATE users SET hp = ? WHERE user_id = ?",
                    (hp, user_id)
                )

                message = (
                    f"🥫 **Station Rations Used!** Restored **{restored} HP**. "
                    f"Current health: **{hp}/{max_hp or 100}**."
                )

            elif item_id == "drone_battery":
                if (scavenging or 0) >= 10:
                    return await ctx.send(
                        "⚠️ Your scavenge drone charges are already full (`10/10`)!"
                    )

                scavenging = min(10, (scavenging or 0) + 2)
                await db.execute(
                    "UPDATE users SET scavenge_charges = ? WHERE user_id = ?",
                    (scavenging, user_id)
                )
                message = f"🔋 Drone charges restored to **{scavenging}/10**."
            elif item_id == "stardust_cache":
                payout = random.randint(150, 700)
                await db.execute(
                    "UPDATE users SET stardust = stardust + ? WHERE user_id = ?",
                    (payout, user_id)
                )
                message = f"🎁 Cache opened: **{payout:,} Stardust** recovered."

            elif item_id == "quantum_battery":
                if effects.get("quantum_battery"):
                    return await ctx.send(
                        "⚠️ You already have a Quantum Battery active! "
                        "Use `/mine` or `/scavenge` first."
                    )

                effects["quantum_battery"] = True
                await db.execute(
                    "UPDATE users SET active_effects = ? WHERE user_id = ?",
                    (json.dumps(effects), user_id)
                )
                message = (
                    "⚛️ **Quantum Battery Activated!**\n"
                    "Your next mining or scavenging run will produce "
                    "**3x Stardust**!"
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

            if row[0] > 1: await db.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_id = ?", (user_id, item_id))
            else: await db.execute("DELETE FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, item_id))
            await db.commit()
        await ctx.send(message)

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

        # Apply the daily 10/10 charge reset for display purposes too.
        # /mine and /scavenge perform the actual database reset when used.
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
            mining = 10

        if last_scavenged_date != current_date:
            scavenging = 10

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
        embed.add_field(name="⛏️ Mining", value=f"`{mining or 0}/10` charges\n{cooldown(last_mined)}", inline=True)
        embed.add_field(name="🛠️ Scavenging", value=f"`{scavenging or 0}/10` charges\n{cooldown(last_scavenged)}", inline=True)
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
        if effects:
            embed.add_field(name="✨ Active Effects", value="\n".join(f"• {name.replace('_', ' ').title()}" for name in effects), inline=False)
        embed.set_footer(text="Use /inventory for items, /shop rotating for today's offers, and /revive if unconscious.")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Inventory(bot))
