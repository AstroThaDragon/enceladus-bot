import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import random
import datetime
import time
from datetime import datetime
import pytz

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Define shop catalog
        self.SHOP_ITEMS = {
            "nanite_patch": {
                "name": "🩹 Nanite Stim-Patch",
                "cost": 400,
                "type": "heal",
                "heal_amount": 35,
                "desc": "Quickly knits minor planetary surface wounds. Restores +35 HP."
            },
            "medkit": {
                "name": "🧰 Field Trauma Medkit",
                "cost": 750,
                "type": "heal",
                "heal_amount": 100,
                "desc": "Standard planetary survival trauma kit. Restores +100 HP."
            },
            "revive": {
                "name": "⚕️ Revival Kit",
                "cost": 350,
                "type": "revive",
                "desc": "Immediately revives an unconscious explorer at 50% HP."
            },
            "full_revive": {
                "name": "⚕️ Emergency Full Revival",
                "cost": 600,
                "type": "revive",
                "desc": "Immediately revives an unconscious explorer at full HP."
            },
            "fuel_refill": {
                "name": "⚡ Emergency Fuel Cell",
                "cost": 700,
                "type": "consumable",
                "desc": "Instantly refills your starship mining laser back to 10/10 charges."
            },
            "pet_snack": {
                "name": "🧬 Cosmic Bio-Feed (Pet Snack)",
                "cost": 350,
                "type": "consumable",
                "desc": "Nutrient pack used to feed your station pet companion."
            },
            "time_crystal": {
                "name": "💎 Dilated Time Crystal",
                "cost": 3500,
                "type": "special",
                "desc": "Bends time backwards to restore a fortune streak missed yesterday (Max 2 uses/month)."
            },
            "neon_grid": {
                "name": "🌆 Background Voucher: Neon Grid",
                "cost": 4000,
                "type": "background_voucher",
                "desc": "Unlocks the 'Cyberpunk Neon Grid City' background photo for your /profile card."
            },
            "deep_void": {
                "name": "🌌 Background Voucher: Deep Void",
                "cost": 4500,
                "type": "background_voucher",
                "desc": "Unlocks the 'Deep Void' background photo for your /profile card."
            },
            "solaris_ring": {
                "name": "💫 Background Voucher: Solaris Ring",
                "cost": 5000,
                "type": "background_voucher",
                "desc": "Unlocks the 'Solaris Ring' background photo for your /profile card."
        }
    }
        # Stardust buyback values for space junk items
        self.JUNK_PRICES = {
            "space_pizza": 30,
            "floppy_disk": 50,
            "meteorite": 85,
            "rubber_duck": 50,
            "rusty_gear": 15,
            "tape_deck": 45,
            "alien_artifact": 80,
            "space_boot": 25,
            "cosmic_coin": 80,
            "holo_poster": 35,
            "broken_laser": 20,
            "lost_logbook": 20,
            "left_sock": 10,
            "warp_mug": 30,
            "space_pudding": 10,
            "tangled_cables": 25,
            "screaming_crystal": 100,
            "moon_cheese": 60,
            "golden_spatula": 120,
            "parking_ticket": 10,
            "floating_plant": 70,
            "tinted_visor": 25,
            "purring_lint": 30,
            "pet_rock": 40,
            "haunted_circuit": 90,
            "space_taco": 35,
            "rusty_wrench": 25,
            "alien_fossil": 75,
            "big_red_button": 10,
            "antique_compass": 30,
            "broken_clock": 20,
            "perplexing_painting": 80,
            "cosmic_banana": 5
        }

        # Add future daily offers here.  Each player sees the same three offers
        # for the whole Eastern-time day.
        self.ROTATING_ITEMS = {
            "fuel_stabilizer": {"name": "🛢️ Fuel Stabilizer", "cost": 800, "desc": "Makes your next mining run cost no fuel charge."},
            "station_rations": {"name": "🥫 Station Rations", "cost": 150, "desc": "Restores a modest 15 HP."},
            "hazard_shield": {"name": "🛡️ Hazard Shield", "cost": 1000, "desc": "Blocks the next scavenging hazard."},
            "drone_battery": {"name": "🔋 Drone Battery Pack", "cost": 900, "desc": "Restores two scavenge charges."},
            "lucky_scanner": {"name": "📡 Deep-Space Scanner", "cost": 700, "desc": "Improves rare-find odds on your next scavenging run."},
            "ore_magnet": {"name": "🧲 Ore Magnet", "cost": 500, "desc": "Guarantees a titanium ore find on your next mining run."},
            "prototype_drill_bit": {"name": "⚙️ Prototype Drill Bit", "cost": 1000, "desc": "Boosts Stardust from your next mining run."},
            "cosmic_insurance": {"name": "📋 Cosmic Insurance", "cost": 800, "desc": "Prevents a knockout from your next scavenging hazard."},
            "fate_anchor": {"name": "⚓ Fate Anchor", "cost": 2250, "desc": "Protects one missed fortune streak day."},
            "stardust_cache": {"name": "🎁 Contraband Stardust Cache", "cost": 2500, "desc": "Open it for an unpredictable Stardust payoff."},
            "revive_kit": {"name": "💉 Emergency Revival Kit", "cost": 1500, "desc": "Revives an unconscious explorer at 50% HP."},
            "title_outer_rim_wanderer": {"name": "🏷️ Title: Outer Rim Wanderer", "cost": 750, "type": "title", "desc": "A title for explorers who venture beyond the station."},
            "title_starborn": {"name": "🏷️ Title: Starborn", "cost": 750, "type": "title", "desc": "A prestigious title for those touched by the stars."},
            "title_voidfarer": {"name": "🏷️ Title: Voidfarer", "cost": 750, "type": "title", "desc": "For those brave enough to chart the endless void."},
        }

        # Purchase limits for shop items.
        # Format: item_id: (maximum_quantity, period)
        # Periods: daily, weekly, monthly, lifetime
        self.SHOP_LIMITS = {
            # Permanent shop
            "nanite_patch": (10, "daily"),
            "medkit": (5, "daily"),
            "full_revive": (2, "weekly"),
            "fuel_refill": (3, "daily"),
            "pet_snack": (30, "daily"),
            "time_crystal": (2, "monthly"),

            # Rotating shop
            "fuel_stabilizer": (5, "daily"),
            "station_rations": (15, "daily"),
            "hazard_shield": (5, "daily"),
            "drone_battery": (5, "daily"),
            "lucky_scanner": (5, "daily"),
            "ore_magnet": (5, "daily"),
            "prototype_drill_bit": (5, "daily"),
            "cosmic_insurance": (5, "daily"),
            "fate_anchor": (3, "daily"),
            "stardust_cache": (3, "daily"),
            "revive_kit": (3, "daily"),

            # Rotating titles are permanent unlocks.
            "title_outer_rim_wanderer": (1, "lifetime"),
            "title_starborn": (1, "lifetime"),
            "title_voidfarer": (1, "lifetime"),
        }

    def rotation_date(self):
        return datetime.now(pytz.timezone("US/Eastern")).date().isoformat()

    def daily_rotation(self):
        """Return the same three distinct offers for every user on a given day."""
        generator = random.Random(f"enceladus-rotation-{self.rotation_date()}")
        return generator.sample(list(self.ROTATING_ITEMS), k=3)

    def get_db_path(self):
        """Return the separate Station economy database."""
        from database import ECONOMY_DB_NAME
        return ECONOMY_DB_NAME

    def purchase_period_key(self, period):
        """Return the current Eastern-time period key for a shop limit."""
        now = datetime.now(pytz.timezone("US/Eastern"))

        if period == "daily":
            return f"daily:{now.date().isoformat()}"

        if period == "weekly":
            iso_year, iso_week, _ = now.isocalendar()
            return f"weekly:{iso_year}-W{iso_week:02d}"

        if period == "monthly":
            return f"monthly:{now.strftime('%Y-%m')}"

        if period == "lifetime":
            return "lifetime"

        return f"unknown:{now.date().isoformat()}"

    def shop_limit_text(self, item_id):
        """Return a human-readable purchase limit for a shop item."""
        limit_info = self.SHOP_LIMITS.get(item_id)

        if not limit_info:
            return ""

        limit, period = limit_info

        labels = {
            "daily": "per day",
            "weekly": "per week",
            "monthly": "per month",
            "lifetime": "per user",
        }

        return f" • Limit: {limit} {labels.get(period, period)}"

    async def ensure_schema(self, db):
        async with db.execute("PRAGMA table_info(users)") as cursor:
            rows = await cursor.fetchall()

        existing_columns = {row[1] for row in rows}

        if "time_crystals" not in existing_columns:
            await db.execute(
                "ALTER TABLE users ADD COLUMN time_crystals INTEGER DEFAULT 0"
            )

        if "tc_uses_this_month" not in existing_columns:
            await db.execute(
                "ALTER TABLE users ADD COLUMN tc_uses_this_month INTEGER DEFAULT 0"
            )

        if "tc_last_used_month" not in existing_columns:
            await db.execute(
                "ALTER TABLE users ADD COLUMN tc_last_used_month TEXT DEFAULT ''"
            )

        # Legacy claim tracker
        if "legacy_claimed" not in existing_columns:
            await db.execute(
                "ALTER TABLE users ADD COLUMN legacy_claimed INTEGER DEFAULT 0"
            )

        if "hp" not in existing_columns:
            await db.execute(
                "ALTER TABLE users ADD COLUMN hp INTEGER DEFAULT 100"
            )

        if "max_hp" not in existing_columns:
            await db.execute(
                "ALTER TABLE users ADD COLUMN max_hp INTEGER DEFAULT 100"
            )

        if "knocked_out_until" not in existing_columns:
            await db.execute(
                "ALTER TABLE users ADD COLUMN knocked_out_until TEXT DEFAULT ''"
            )

        if "last_chat_reward" not in existing_columns:
            await db.execute(
                "ALTER TABLE users ADD COLUMN last_chat_reward REAL DEFAULT 0"
            )

        # Shop purchase-limit tracking.
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS shop_purchase_limits (
                user_id INTEGER NOT NULL,
                item_id TEXT NOT NULL,
                period_key TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, item_id, period_key)
            )
            """
        )

        
    @commands.hybrid_group(name="shop", description="Browse and trade at the Enceladus Station Trading Post.")
    async def shop(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="🛒 Enceladus Station Trading Post",
                description="Use `/shop buy` to purchase items, or `/shop sell` to turn in salvaged space junk for Stardust.",
                color=discord.Color.from_rgb(0, 229, 255)
            )

            for item_id, details in self.SHOP_ITEMS.items():
                limit_text = self.shop_limit_text(item_id)

                embed.add_field(
                    name=details["name"],
                    value=(
                        f"💰 Price: **{details['cost']:,} Stardust**\n"
                        f"📖 {details['desc']}\n"
                        f"📦 **Purchase Limit:** {limit_text.lstrip(' • Limit: ') if limit_text else 'None'}"
                    ),
                    inline=False
                )

            rotation = self.daily_rotation()
            rotating_text = "\n".join(
                f"{self.ROTATING_ITEMS[item_id]['name']} — **{self.ROTATING_ITEMS[item_id]['cost']} Stardust**"
                for item_id in rotation
            )
            embed.add_field(
                name=f"🔄 Daily Rotating Offers — {self.rotation_date()}",
                value=f"Use `/shop rotating` for descriptions and `/shop buy` to purchase.\n{rotating_text}",
                inline=False,
            )

            embed.set_footer(text="Tip: Check your wallet balance using /profile")
            await ctx.send(embed=embed)

    @shop.command(name="rotating", description="View today's three rotating-shop offers.")
    async def rotating(self, ctx: commands.Context):
        rotation = self.daily_rotation()
        embed = discord.Embed(
            title=f"🔄 Daily Station Market — {self.rotation_date()}",
            description="These three offers rotate at midnight Eastern time for the entire station.",
            color=discord.Color.purple(),
        )
        for item_id in rotation:
            item = self.ROTATING_ITEMS[item_id]
            limit_text = self.shop_limit_text(item_id)

            embed.add_field(
                name=item["name"],
                value=(
                    f"💰 **{item['cost']:,} Stardust**\n"
                    f"{item['desc']}\n"
                    f"📦 **Purchase Limit:** {limit_text.lstrip(' • Limit: ') if limit_text else 'None'}"
                ),
                inline=False
            )
        await ctx.send(embed=embed)

    @shop.command(name="browse", description="Browse the permanent catalog and today's rotating offers.")
    async def browse(self, ctx: commands.Context):
        embed = discord.Embed(
            title="🛒 Enceladus Station Trading Post",
            description="Use `/shop buy` to purchase items., or `/shop sell` to sell salvage.",
            color=discord.Color.from_rgb(0, 229, 255),
        )
        for item_id, details in self.SHOP_ITEMS.items():
            embed.add_field(name=details["name"], value=f"💰 **{details['cost']} Stardust**\n{details['desc']}", inline=False)
        embed.set_footer(text="Use /shop rotating to view today's temporary offers.")
        await ctx.send(embed=embed)

    async def shop_buy_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ):
        """Show items currently available in the station shop."""
        current = current.lower().strip()

        available_items = []

        # Permanent shop items.
        for item_id, info in self.SHOP_ITEMS.items():
            display_name = info["name"]

            if current and current not in display_name.lower():
                continue

            available_items.append(
                app_commands.Choice(
                    name=display_name,
                    value=item_id
                )
            )

        # Today's rotating items.
        for item_id in self.daily_rotation():
            info = self.ROTATING_ITEMS.get(item_id)
            if not info:
                continue

            display_name = info["name"]

            if current and current not in display_name.lower():
                continue

            available_items.append(
                app_commands.Choice(
                    name=display_name,
                    value=item_id
                )
            )

        available_items.sort(key=lambda choice: choice.name.lower())

        return available_items[:25]

    @shop.command(name="buy", description="Purchase an item from the station vendor catalog.")
    @app_commands.describe(
        item_id="Choose an item to purchase.",
        quantity="How many would you like to buy? (1-99)"
    )
    @app_commands.autocomplete(item_id=shop_buy_autocomplete)
    async def buy(self, ctx: commands.Context, item_id: str, quantity: int = 1):
        await ctx.defer()
        user_id = ctx.author.id
        item_id = item_id.lower()

        if quantity < 1 or quantity > 99:
            return await ctx.send("❌ Quantity must be between **1 and 99**.")

        rotating_item = self.ROTATING_ITEMS.get(item_id)

        if item_id not in self.SHOP_ITEMS and not rotating_item:
            return await ctx.send(
                "❌ Invalid item ID! Check available items using `/shop`."
            )

        if rotating_item and item_id not in self.daily_rotation():
            return await ctx.send(
                "⏳ That item is not in today's rotating market. "
                "Check `/shop rotating` for the current offers."
            )

        item = self.SHOP_ITEMS.get(item_id) or rotating_item

        if item is None:
            return await ctx.send("❌ That item could not be loaded from the shop catalog.")

        unit_cost = item["cost"]
        cost = unit_cost * quantity

        db_path = self.get_db_path()

        async with aiosqlite.connect(db_path) as db:
            
            # Run schema/migration work before starting the purchase transaction.
            await self.ensure_schema(db)
            await db.commit()

            from inventory import ITEM_REGISTRY, add_inventory_item

            item_info = ITEM_REGISTRY.get(item_id)

            if not item_info:
                return await ctx.send(
                    "❌ This item is not registered in the master item registry."
                )

            max_stack = item_info.get("max_quantity", 10)

            # These items are stored directly on the users table.
            legacy_columns = {
                "time_crystal": "time_crystals",
                "nanite_patch": "nanite_patchs",
                "medkit": "medkits",
            }

            if item_id in legacy_columns:
                column = legacy_columns[item_id]

                async with db.execute(
                    f"SELECT {column} FROM users WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()

                current_quantity = (row[0] or 0) if row else 0

            else:
                async with db.execute(
                    "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                    (user_id, item_id)
                ) as cursor:
                    inventory_row = await cursor.fetchone()

                current_quantity = (inventory_row[0] or 0) if inventory_row else 0

            if current_quantity + quantity > max_stack:
                return await ctx.send(
                    f"📦 **Inventory Full!** You can only hold **{max_stack}x** "
                    f"**{item_info['name']}**.\n"
                    f"You currently have **{current_quantity}x**."
                )

            # Lock the database for the entire purchase transaction.
            # This prevents two simultaneous purchases from spending
            # the same Stardust balance.
            await db.execute("BEGIN IMMEDIATE")

            # Check user's Stardust balance and current health state.
            async with db.execute(
                "SELECT stardust, mining_charges, hp, max_hp "
                "FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                await db.rollback()
                return await ctx.send(
                    "❌ You don't have an active station profile yet. "
                    "Run `/profile` or `/mine` first!"
                )

            stardust, charges, hp, max_hp = row

            if stardust < cost:
                await db.rollback()
                return await ctx.send(
                    f"💸 **Insufficient Stardust!** You have `{stardust}` "
                    f"Stardust, but this item costs `{cost:,}`."
                )

            # ─────────────────────────────────────────────
            # SHOP PURCHASE LIMIT
            # ─────────────────────────────────────────────
            limit_info = self.SHOP_LIMITS.get(item_id)

            if limit_info:
                max_quantity, period = limit_info
                period_key = self.purchase_period_key(period)

                async with db.execute(
                    """
                    SELECT quantity
                    FROM shop_purchase_limits
                    WHERE user_id = ?
                      AND item_id = ?
                      AND period_key = ?
                    """,
                    (user_id, item_id, period_key)
                ) as cursor:
                    limit_row = await cursor.fetchone()

                purchased_quantity = (limit_row[0] or 0) if limit_row else 0
                remaining = max_quantity - purchased_quantity

                if quantity > remaining:
                    await db.rollback()

                    if remaining <= 0:
                        return await ctx.send(
                            f"🚫 **Purchase Limit Reached!** "
                            f"You've already bought the maximum **{max_quantity}x** "
                            f"**{item['name']}** allowed {period}."
                        )

                    return await ctx.send(
                        f"🚫 **Purchase Limit Exceeded!** "
                        f"You can only buy **{remaining} more** "
                        f"**{item['name']}** this {period}."
                    )

                added_amount, new_quantity, max_quantity = await add_inventory_item(
                    db,
                    user_id,
                    item_id,
                    item_info.get("type", item.get("type", "consumable")),
                    quantity
                )

                if added_amount != quantity:
                    await db.rollback()
                    return await ctx.send(
                        f"📦 **Inventory Full!** You can only hold **{max_quantity}x** "
                        f"**{item['name']}**.\n"
                        f"You currently have **{new_quantity}x**."
                    )

            # Backgrounds are individual permanent unlocks.
            # They cannot be purchased in bulk.
            if item["type"] == "background_voucher" and quantity != 1:
                await db.rollback()
                return await ctx.send(
                    "🖼️ Background vouchers can only be purchased **one at a time**."
                )

            # Process purchase based on item type.
            new_stardust = stardust - cost

            if rotating_item is not None:
                item = rotating_item
                item_type = item.get("type", "consumable")

                # Titles are permanent unlocks.
                if item_type == "title":
                    if quantity != 1:
                        await db.rollback()
                        return await ctx.send(
                            "🏷️ Titles can only be purchased **once.**"
                        )

                    async with db.execute(
                        "SELECT 1 FROM inventory WHERE user_id = ? AND item_id = ?",
                        (user_id, item_id)
                    ) as cursor:
                        already_owned = await cursor.fetchone()

                    if already_owned:
                        await db.rollback()
                        return await ctx.send(
                            "⚠️ You already own this title!"
                        )

                # Add the item through the master inventory helper so the
                # registry stack limit is enforced inside the locked transaction.
                added_amount, new_quantity, max_quantity = await add_inventory_item(
                    db,
                    user_id,
                    item_id,
                    item_type,
                    quantity
                )

                if added_amount != quantity:
                    await db.rollback()
                    return await ctx.send(
                        f"📦 **Inventory Full!** You can only hold **{max_quantity}x** "
                        f"**{item['name']}**.\n"
                        f"You currently have **{new_quantity}x**."
                    )

                await db.execute(
                    "UPDATE users SET stardust = ? WHERE user_id = ?",
                    (new_stardust, user_id)
                )

                await db.commit()

                if item_type == "title":
                    return await ctx.send(
                        f"🏷️ **Title Unlocked!** You purchased "
                        f"**{item['name']}** for **{cost:,} Stardust**!"
                    )

                return await ctx.send(
                    f"🔄 **Purchase Successful!** Added **{quantity}x "
                    f"{item['name']}** to your inventory for "
                    f"**{cost:,} Stardust**!"
                )

            if item["type"] == "revive":
                added_amount, new_quantity, max_quantity = await add_inventory_item(
                    db,
                    user_id,
                    item_id,
                    "consumable",
                    quantity
                )

                if added_amount != quantity:
                    await db.rollback()
                    return await ctx.send(
                        f"📦 **Inventory Full!** You can only hold **{max_quantity}x** "
                        f"**{item['name']}**.\n"
                        f"You currently have **{new_quantity}x**."
                    )

                await db.execute(
                    "UPDATE users SET stardust = ? WHERE user_id = ?",
                    (new_stardust, user_id)
                )

                await db.commit()

                return await ctx.send(
                    f"⚕️ **Purchase Successful!** Added **{quantity}x "
                    f"{item['name']}** to your inventory for "
                    f"**{cost:,} Stardust**!"
                )

            if item["type"] == "consumable" and item_id == "fuel_refill":
                added_amount, new_quantity, max_quantity = await add_inventory_item(
                    db,
                    user_id,
                    item_id,
                    "consumable",
                    quantity
                )

                if added_amount != quantity:
                    await db.rollback()
                    return await ctx.send(
                        f"📦 **Inventory Full!** You can only hold **{max_quantity}x** "
                        f"**{item['name']}**.\n"
                        f"You currently have **{new_quantity}x**."
                    )

                await db.execute(
                    "UPDATE users SET stardust = ? WHERE user_id = ?",
                    (new_stardust, user_id)
                )

                await db.commit()

                return await ctx.send(
                    f"⚡ **Purchase Successful!** Added **{quantity}x "
                    f"{item['name']}** to your inventory for "
                    f"**{cost:,} Stardust**!"
                )

            if item["type"] == "consumable" and item_id == "pet_snack":
                added_amount, new_quantity, max_quantity = await add_inventory_item(
                    db,
                    user_id,
                    item_id,
                    "consumable",
                    quantity
                )

                if added_amount != quantity:
                    await db.rollback()
                    return await ctx.send(
                        f"📦 **Inventory Full!** You can only hold **{max_quantity}x** "
                        f"**{item['name']}**.\n"
                        f"You currently have **{new_quantity}x**."
                    )

                await db.execute(
                    "UPDATE users SET stardust = ? WHERE user_id = ?",
                    (new_stardust, user_id)
                )

                await db.commit()

                return await ctx.send(
                    f"🧬 **Purchase Successful!** Added **{quantity}x {item['name']}** "
                    f"to your inventory for **{cost:,} Stardust**!"
                )
            if item_id == "time_crystal":
                max_stack = item_info.get("max_quantity", 10)

                async with db.execute(
                    "SELECT COALESCE(time_crystals, 0) FROM users WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()

                current_quantity = row[0] if row else 0

                if current_quantity + quantity > max_stack:
                    await db.rollback()
                    return await ctx.send(
                        f"📦 **Inventory Full!** You can only hold **{max_stack}x** "
                        f"**{item['name']}**.\n"
                        f"You currently have **{current_quantity}x**."
                    )

                await db.execute(
                    """
                    UPDATE users
                    SET stardust = ?,
                        time_crystals = COALESCE(time_crystals, 0) + ?
                    WHERE user_id = ?
                    """,
                    (new_stardust, quantity, user_id)
                )

                await db.commit()

                return await ctx.send(
                    f"💎 **Purchase Successful!** Added **{quantity}x "
                    f"{item['name']}** to your inventory for "
                    f"**{cost:,} Stardust**!\n"
                    f"If you miss a fortune streak, use `/usecrystal` to repair it."
                )

            if item["type"] == "background_voucher":
                async with db.execute(
                    "SELECT 1 FROM inventory "
                    "WHERE user_id = ? AND item_id = ?",
                    (user_id, item_id)
                ) as cursor:
                    already_owned = await cursor.fetchone()

                if already_owned:
                    await db.rollback()
                    return await ctx.send(
                        "⚠️ You already own this background voucher!"
                    )

                await db.execute(
                    """
                    INSERT INTO inventory
                        (user_id, item_id, item_type, quantity)
                    VALUES (?, ?, 'background_voucher', 1)
                    """,
                    (user_id, item_id)
                )

                await db.execute(
                    "UPDATE users SET stardust = ? WHERE user_id = ?",
                    (new_stardust, user_id)
                )

                await db.commit()

                return await ctx.send(
                    f"🌟 **Purchase Successful!** Unlocked "
                    f"**{item['name']}** for **{cost:,} Stardust**!"
                )

            if item["type"] == "heal":
                # Item key format:
                # medkit -> medkits
                # nanite_patch -> nanite_patchs
                col_name = f"{item_id}s"

                max_stack = item_info.get("max_quantity", 10)

                # Ensure inventory column exists dynamically.
                async with db.execute("PRAGMA table_info(users)") as cursor:
                    rows = await cursor.fetchall()

                existing_cols = {row[1] for row in rows}

                if col_name not in existing_cols:
                    await db.execute(
                        f"ALTER TABLE users ADD COLUMN "
                        f"{col_name} INTEGER DEFAULT 0"
                    )

                async with db.execute(
                    f"SELECT COALESCE({col_name}, 0) FROM users WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()

                current_quantity = row[0] if row else 0

                if current_quantity + quantity > max_stack:
                    await db.rollback()
                    return await ctx.send(
                        f"📦 **Inventory Full!** You can only hold **{max_stack}x** "
                        f"**{item['name']}**.\n"
                        f"You currently have **{current_quantity}x**."
                    )

                await db.execute(
                    f"""
                    UPDATE users
                    SET stardust = ?,
                        {col_name} = COALESCE({col_name}, 0) + ?
                    WHERE user_id = ?
                    """,
                    (new_stardust, quantity, user_id)
                )

                await db.commit()

                return await ctx.send(
                    f"🛒 **Purchase Successful!** Added **{quantity}x {item['name']}** "
                    f"to your inventory for **{cost:,} Stardust**!"
                )

            await db.rollback()

        await ctx.send("❌ An error occurred processing your transaction.")

    async def shop_sell_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ):
        """Show space junk the user currently owns and can sell."""
        user_id = interaction.user.id
        current = current.lower().strip()

        from inventory import ITEM_REGISTRY

        async with aiosqlite.connect(self.get_db_path()) as db:
            async with db.execute(
                """
                SELECT item_id, quantity
                FROM inventory
                WHERE user_id = ?
                  AND item_type = 'space_junk'
                  AND quantity > 0
                """,
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()

        choices = []

        # Always offer the option to sell all junk.
        if not current or "sell all" in current:
            choices.append(
                app_commands.Choice(
                    name="🗑️ Sell All Space Junk",
                    value="all"
                )
            )

        for item_id, quantity in rows:
            if item_id not in self.JUNK_PRICES:
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

    @shop.command(name="sell", description="Sell salvaged space junk from your inventory for Stardust.")
    @app_commands.describe(item="Choose the space junk you want to sell.")
    @app_commands.autocomplete(item=shop_sell_autocomplete)
    async def sell(self, ctx: commands.Context, item: str):
        await ctx.defer()

        user_id = ctx.author.id
        target_item = item.lower().strip()
        db_path = self.get_db_path()

        async with aiosqlite.connect(db_path) as db:
            # Ensure any required schema exists before the transaction.
            await self.ensure_schema(db)
            await db.commit()

            # Serialize the entire sale so two simultaneous sales cannot
            # both spend the same inventory quantity.
            await db.execute("BEGIN IMMEDIATE")

            # Option A: Sell ALL space junk
            if target_item == "all":
                async with db.execute(
                    "SELECT item_id, quantity "
                    "FROM inventory "
                    "WHERE user_id = ? AND item_type = 'space_junk' AND quantity > 0",
                    (user_id,)
                ) as cursor:
                    junk_rows = await cursor.fetchall()

                if not junk_rows:
                    await db.rollback()
                    return await ctx.send(
                        "🎒 **Inventory Empty!** You don't have any space junk to sell."
                    )

                total_payout = sum(
                    self.JUNK_PRICES.get(row[0], 25) * (row[1] or 1)
                    for row in junk_rows
                )
                item_count = sum(
                    row[1] or 1
                    for row in junk_rows
                )

                await db.execute(
                    "DELETE FROM inventory "
                    "WHERE user_id = ? AND item_type = 'space_junk'",
                    (user_id,)
                )

                await db.execute(
                    "UPDATE users "
                    "SET stardust = stardust + ? "
                    "WHERE user_id = ?",
                    (total_payout, user_id)
                )

                await db.commit()

                return await ctx.send(
                    f"🛍️ **Salvage Vendor:** Sold **{item_count} items** "
                    f"for a total of ✨ **{total_payout:,} Stardust**!"
                )

            # Option B: Sell a SINGLE specific junk item
            async with db.execute(
                "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ? AND item_type = 'space_junk'",
                (user_id, target_item)
            ) as cursor:
                row = await cursor.fetchone()

            if not row or (row[0] or 0) <= 0:
                return await ctx.send(f"❌ You don't have `{target_item}` in your space junk inventory!")

            payout = self.JUNK_PRICES.get(target_item, 25)
            new_quantity = (row[0] or 0) - 1

            if new_quantity > 0:
                await db.execute(
                    "UPDATE inventory SET quantity = ? WHERE user_id = ? AND item_id = ? AND item_type = 'space_junk'",
                    (new_quantity, user_id, target_item)
                )
            else:
                await db.execute(
                    "DELETE FROM inventory WHERE user_id = ? AND item_id = ? AND item_type = 'space_junk'",
                    (user_id, target_item)
                )

            await db.execute(
                "UPDATE users SET stardust = stardust + ? WHERE user_id = ?",
                (payout, user_id)
            )
            await db.commit()

        await ctx.send(
            f"🛍️ **Salvage Vendor:** Sold `{target_item}` "
            f"for ✨ **{payout} Stardust**!"
        )

    async def item_category_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ):
        """Show the available item catalog categories."""
        categories = [
            ("❤️ Healing", "healing"),
            ("🛠️ Upgrades", "upgrades"),
            ("🎒 Consumables", "consumables"),
            ("🐾 Pet Items", "pet_items"),
            ("✨ Special", "special"),
            ("🗑️ Space Junk A–M", "junk_am"),
            ("🗑️ Space Junk N–Z", "junk_nz"),
            ("💎 Minerals", "minerals"),
            ("🏷️ Titles", "titles"),
            ("🖼️ Backgrounds", "backgrounds"),
            ("🎟️ Vouchers", "vouchers"),
            ("🪙 Currency", "currency"),
        ]

        current = current.lower().strip()

        choices = [
            app_commands.Choice(name=name, value=value)
            for name, value in categories
            if not current or current in name.lower()
        ]

        return choices[:25]


    async def item_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ):
        """Show items belonging to the selected catalog category."""
        from inventory import ITEM_REGISTRY

        category = interaction.namespace.category
        current = current.lower().strip()

        category_map = {
            "healing": {
                "nanite_patch",
                "medkit",
                "full_revive",
                "revive_kit",
            },
            "upgrades": {
                "fuel_stabilizer",
                "hazard_shield",
                "drone_battery",
                "lucky_scanner",
                "ore_magnet",
                "prototype_drill_bit",
                "cosmic_insurance",
                "fate_anchor",
                "stardust_cache",
            },
            "consumables": {
                "fuel_refill",
            },
            "pet_items": {
                "pet_snack",
            },
            "special": {
                "time_crystal",
            },
            "junk_am": {
                "alien_artifact",
                "alien_fossil",
                "antique_compass",
                "big_red_button",
                "broken_clock",
                "broken_laser",
                "cosmic_banana",
                "cosmic_coin",
                "floating_plant",
                "floppy_disk",
                "golden_spatula",
                "haunted_circuit",
                "holo_poster",
                "left_sock",
                "lost_logbook",
                "meteorite",
                "moon_cheese",
            },
            "junk_nz": {
                "parking_ticket",
                "pet_rock",
                "perplexing_painting",
                "purring_lint",
                "rubber_duck",
                "rusty_gear",
                "rusty_wrench",
                "screaming_crystal",
                "space_boot",
                "space_pizza",
                "space_pudding",
                "space_taco",
                "tape_deck",
                "tangled_cables",
                "tinted_visor",
                "warp_mug",

            },
            "minerals": {
                "titanium_chunk",
            },
            "titles": {
                "title_outer_rim_wanderer",
                "title_starborn",
                "title_voidfarer",
            },
            "backgrounds": {
                "neon_grid",
                "deep_void",
                "solaris_ring",
            },
            "vouchers": {
                "neon_grid",
                "deep_void",
                "solaris_ring",
            },
            "currency": {
                "arcade_token",
            },
        }

        allowed_items = category_map.get(category, set())

        choices = []

        for item_id in allowed_items:
            info = ITEM_REGISTRY.get(item_id)
            if not info:
                continue

            display_name = info["name"]

            if current and current not in display_name.lower():
                continue

            choices.append(
                app_commands.Choice(
                    name=display_name,
                    value=item_id
                )
            )

        choices.sort(key=lambda choice: choice.name.lower())

        return choices[:25]

    @commands.hybrid_command(name="item", description="Inspect an item from the station catalog.")
    @app_commands.describe(
        category="Choose an item category.",
        item="Choose an item to inspect."
    )
    @app_commands.autocomplete(
        category=item_category_autocomplete,
        item=item_autocomplete
    )
    async def item_lookup(self, ctx: commands.Context, category: str, item: str):
        item_id = item.lower()
        from inventory import ITEM_REGISTRY

        if item_id not in ITEM_REGISTRY:
            return await ctx.send(
                "❌ I couldn't find that item. Please choose an item from the dropdown."
            )

        info = ITEM_REGISTRY[item_id]
        
        embed = discord.Embed(
            title=f"{info['emoji']} {info['name']}",
            description=f"**Category:** {info['type']}\n**Description:** {info['desc']}",
            color=discord.Color.from_rgb(120, 140, 160)
        )
        embed.set_footer(text="Enceladus Station Catalog")
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="claimlegacy",
        description="Claim your one-time Stardust bonus for being in the server before the **Frontier** update!"
    )
    async def claim_legacy_bonus(self, ctx: commands.Context):
        await ctx.defer()

        # This command only makes sense inside the server.
        if ctx.guild is None:
            return await ctx.send(
                "❌ This command can only be used **inside** The Cosmic Lair server."
            )

        user_id = ctx.author.id

        # September 10, 2026 is the Shop & Exploration update date.
        # Anyone who joined BEFORE that date is considered a server veteran.
        eastern = pytz.timezone("US/Eastern")
        cutoff_date = eastern.localize(datetime(2026, 9, 10))

        joined_at = ctx.author.joined_at

        if joined_at is None:
            return await ctx.send(
                "❌ I couldn't determine when you joined The Cosmic Lair server."
            )

        if joined_at >= cutoff_date:
            return await ctx.send(
                "⚠️ **Not Eligible!** "
                "Sorry! But the legacy veteran bonus is only available to members "
                "who joined the server before **September 10, 2026!**"
            )

        db_path = self.get_db_path()

        async with aiosqlite.connect(db_path) as db:
            await self.ensure_schema(db)
            await db.commit()

            # Lock the transaction so two simultaneous /claimlegacy
            # commands cannot both redeem the bonus.
            await db.execute("BEGIN IMMEDIATE")

            async with db.execute(
                """
                SELECT stardust, legacy_claimed
                FROM users
                WHERE user_id = ?
                """,
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                await db.rollback()
                return await ctx.send(
                    "❌ You don't have an active profile!"
                )

            current_stardust = row[0] or 0
            legacy_claimed = row[1] or 0

            if legacy_claimed:
                await db.rollback()
                return await ctx.send(
                    "⚠️ **Already Claimed!** "
                    "You've already redeemed your 5,000 Stardust "
                    "legacy veteran bonus."
                )

            legacy_bonus = 5000

            await db.execute(
                """
                UPDATE users
                SET stardust = ?,
                    legacy_claimed = 1
                WHERE user_id = ?
                """,
                (current_stardust + legacy_bonus, user_id)
            )

            await db.commit()

        await ctx.send(
            f"🎉 **Legacy Veteran Bonus Claimed!**\n"
            f"Thanks for being a server veteran! You received "
            f"✨ **{legacy_bonus:,} Stardust** as a thank-you for being "
            f"here before the **Frontier** update."
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        user_id = message.author.id
        now = time.time()
        reward = random.randint(5, 15)

        async with aiosqlite.connect(self.get_db_path()) as db:
            await self.ensure_schema(db)
            await db.commit()
            await db.execute("BEGIN IMMEDIATE")

            async with db.execute(
                "SELECT last_chat_reward FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                await db.execute(
                    """
                    INSERT INTO users (user_id, stardust, last_chat_reward)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, reward, now)
                )
                await db.commit()
                return

            last_reward = row[0] or 0

            if now - last_reward < 120:
                await db.rollback()
                return

            await db.execute(
                """
                UPDATE users
                SET stardust = COALESCE(stardust, 0) + ?,
                    last_chat_reward = ?
                WHERE user_id = ?
                """,
                (reward, now, user_id)
            )
            await db.commit()

async def setup(bot):
    await bot.add_cog(Economy(bot))
