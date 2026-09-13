import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import random
import datetime
import time
from datetime import datetime
import pytz

class ShopCategorySelect(discord.ui.Select):
    def __init__(self, shop_view):
        self.shop_view = shop_view

        options = [
            discord.SelectOption(
                label="Healing",
                emoji="❤️",
                value="healing",
                description="Nanite patches, medkits, and revival items."
            ),
            discord.SelectOption(
                label="Recharge",
                emoji="🔋",
                value="recharge",
                description="Mining laser and scavenging drone recharge items."
            ),
            discord.SelectOption(
                label="Upgrades",
                emoji="🛠️",
                value="upgrades",
                description="Temporary equipment and exploration upgrades."
            ),
            discord.SelectOption(
                label="Pet Items",
                emoji="🐾",
                value="pet_items",
                description="Items for your station pet."
            ),
            discord.SelectOption(
                label="Special",
                emoji="✨",
                value="special",
                description="Rare and unusual station items."
            ),
            discord.SelectOption(
                label="Backgrounds",
                emoji="🖼️",
                value="backgrounds",
                description="Profile background vouchers."
            ),
            discord.SelectOption(
                label="Daily Offers",
                emoji="🔄",
                value="daily",
                description="Today's rotating station offers."
            ),
        ]

        super().__init__(
            placeholder="📂 Select a shop category...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.shop_view.user_id:
            return await interaction.response.send_message(
                "⚠️ This shop menu belongs to the person who opened it.",
                ephemeral=True
            )

        category = self.values[0]

        embed = self.shop_view.build_embed(category)

        await interaction.response.edit_message(
            embed=embed,
            view=self.shop_view
        )


class ShopView(discord.ui.View):
    def __init__(self, cog, user_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id

        self.add_item(ShopCategorySelect(self))

    def build_embed(self, category):
        cog = self.cog

        embed = discord.Embed(
            title="🛒 Enceladus Station Trading Post",
            color=discord.Color.from_rgb(0, 229, 255)
        )

        if category == "healing":
            embed.description = (
                "❤️ **Medical Supplies**\n"
                "Keep yourself alive out there, explorer."
            )

            item_ids = [
                "nanite_patch",
                "medkit",
                "revive",
                "full_revive",
            ]

        elif category == "recharge":
            embed.description = (
                "🔋 **Power & Recharge Supplies**\n"
                "Restore charges to your mining laser or scavenging drone."
            )

            item_ids = [
                "laser_charge_cell",
                "laser_power_cell",
                "fuel_refill",
                "drone_battery",
                "drone_power_cell",
                "drone_quantum_battery",
            ]

        elif category == "upgrades":
            embed.description = (
                "🛠️ **Station Upgrades**\n"
                "Special equipment to improve your next expedition."
            )

            item_ids = [
                item_id
                for item_id in cog.daily_rotation()
                if item_id in {
                    "fuel_stabilizer",
                    "hazard_shield",
                    "lucky_scanner",
                    "ore_magnet",
                    "prototype_drill_bit",
                    "cosmic_insurance",
                    "fate_anchor",
                    "stardust_cache",
                }
            ]

        elif category == "pet_items":
            embed.description = (
                "🐾 **Pet Supplies**\n"
                "Because even station companions need snacks."
            )

            item_ids = [
                "pet_snack",
            ]

        elif category == "special":
            embed.description = (
                "✨ **Special Items**\n"
                "Unusual technology with unusual consequences."
            )

            item_ids = [
                "time_crystal",
            ]

        elif category == "backgrounds":
            embed.description = (
                "🖼️ **Profile Backgrounds**\n"
                "Customize the look of your station profile."
            )

            item_ids = [
                "neon_grid",
                "deep_void",
                "solaris_ring",
            ]

        elif category == "daily":
            embed.description = (
                "🔄 **Daily Rotating Offers**\n"
                f"Today's station market — **{cog.rotation_date()}**\n\n"
                "These offers rotate at midnight Eastern time."
            )

            for item_id in cog.daily_rotation():
                item = cog.SHOP_ITEMS.get(item_id) or cog.ROTATING_ITEMS.get(item_id)
                if not item:
                    continue

                is_permanent = item_id in cog.SHOP_ITEMS

                if is_permanent:
                    daily_cost = int(item["cost"] * 0.85)
                    price_text = (
                        f"💰 ~~{item['cost']:,}~~ → **{daily_cost:,} Stardust** 🔥\n"
                        "🏷️ **15% Daily Discount**"
                    )
                else:
                    daily_cost = item["cost"]
                    price_text = f"💰 Price: **{daily_cost:,} Stardust**"

                limit_text = cog.shop_limit_text(item_id)

                embed.add_field(
                    name=item["name"],
                    value=(
                        f"{price_text}\n"
                        f"📖 {item['desc']}\n"
                        f"📦 **Purchase Limit:** "
                        f"{limit_text.lstrip(' • Limit: ') if limit_text else 'None'}"
                    ),
                    inline=False
                )

            embed.set_footer(
                text="Use /shop_buy to purchase an item."
            )

            return embed

        else:
            item_ids = []

        for item_id in item_ids:
            item = cog.SHOP_ITEMS.get(item_id) or cog.ROTATING_ITEMS.get(item_id)

            if not item:
                continue

            limit_text = cog.shop_limit_text(item_id)

            embed.add_field(
                name=item["name"],
                value=(
                    f"💰 Price: **{item['cost']:,} Stardust**\n"
                    f"📖 {item['desc']}\n"
                    f"📦 **Purchase Limit:** "
                    f"{limit_text.lstrip(' • Limit: ') if limit_text else 'None'}"
                ),
                inline=False
            )

        embed.set_footer(
            text="Use /shop_buy to purchase an item."
        )

        return embed

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
                "desc": "Immediately revives an unconscious explorer at 35% HP."
            },
            "full_revive": {
                "name": "⚕️ Emergency Full Revival",
                "cost": 800,
                "type": "revive",
                "desc": "Immediately revives an unconscious explorer at full HP."
            },
            "laser_charge_cell": {
                "name": "🔋 Laser Charge Cell",
                "cost": 400,
                "type": "consumable",
                "desc": "Restores 2 mining laser charges."
            },
            "laser_power_cell": {
                "name": "⚡ Laser Power Cell",
                "cost": 750,
                "type": "consumable",
                "desc": "Restores 5 mining laser charges."
            },
            "fuel_refill": {
                "name": "⚛️ Laser Quantum Cell",
                "cost": 1200,
                "type": "consumable",
                "desc": "Instantly refills your mining laser to 10/10 charges."
            },
            "drone_battery": {
                "name": "🔋 Drone Battery Pack",
                "cost": 400,
                "type": "consumable",
                "desc": "Restores 2 scavenge charges."
            },
            "drone_power_cell": {
                "name": "⚡ Drone Power Cell",
                "cost": 750,
                "type": "consumable",
                "desc": "Restores 5 scavenge charges."
            },
            "drone_quantum_battery": {
                "name": "⚛️ Drone Quantum Battery",
                "cost": 1200,
                "type": "consumable",
                "desc": "Instantly refills your scavenging drone to 10/10 charges."
            },
            "pet_snack": {
                "name": "🧬 Cosmic Bio-Feed (Pet Snack)",
                "cost": 200,
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
            "laser_charge_cell": (5, "daily"),
            "laser_power_cell": (3, "daily"),
            "fuel_refill": (2, "daily"),
            "drone_battery": (5, "daily"),
            "drone_power_cell": (3, "daily"),
            "drone_quantum_battery": (2, "daily"),
            "pet_snack": (30, "daily"),
            "time_crystal": (2, "monthly"),

            # Rotating shop
            "fuel_stabilizer": (5, "daily"),
            "station_rations": (15, "daily"),
            "hazard_shield": (5, "daily"),
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
        """Return the same three distinct offers for every user on a given day.

        Daily Offers can feature any normal shop item, including permanent
        shop items and rotating items, but exclude backgrounds and titles.
        """
        excluded_types = {"background_voucher", "title"}
        eligible_items = []

        for item_id, item in self.SHOP_ITEMS.items():
            if item.get("type") not in excluded_types:
                eligible_items.append(item_id)

        for item_id, item in self.ROTATING_ITEMS.items():
            if item.get("type") not in excluded_types and item_id not in eligible_items:
                eligible_items.append(item_id)

        generator = random.Random(f"enceladus-rotation-{self.rotation_date()}")
        return generator.sample(eligible_items, k=3)

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

    async def record_shop_purchase(self, db, user_id, item_id, quantity):
        """Record a successful shop purchase against the item's current limit period."""
        limit_info = self.SHOP_LIMITS.get(item_id)

        if not limit_info:
            return

        max_quantity, period = limit_info
        period_key = self.purchase_period_key(period)

        await db.execute(
            """
            INSERT INTO shop_purchase_limits
                (user_id, item_id, period_key, quantity)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, item_id, period_key)
            DO UPDATE SET quantity = quantity + excluded.quantity
            """,
            (
                user_id,
                item_id,
                period_key,
                quantity
            )
        )

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

        
    @commands.hybrid_command(
        name="shop",
        description="Open the Enceladus Station Trading Post."
    )
    async def shop(self, ctx: commands.Context):
        view = ShopView(self, ctx.author.id)

        embed = view.build_embed("healing")

        await ctx.send(
            embed=embed,
            view=view
        )

    async def shop_buy_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ):
        """Show items currently available in the station shop."""
        current = current.lower().strip()

        available_items = []
        seen_items = set()

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
            seen_items.add(item_id)

        # Today's rotating-only items.
        for item_id in self.daily_rotation():
            if item_id in seen_items:
                continue

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
            seen_items.add(item_id)

        available_items.sort(key=lambda choice: choice.name.lower())

        return available_items[:25]

    @commands.hybrid_command(
        name="shop_buy",
        description="Purchase an item from the station vendor catalog."
    )
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
                "Check `/shop` and select 🔄️ Daily Offers for the current offers."
            )

        item = self.SHOP_ITEMS.get(item_id) or rotating_item

        if item is None:
            return await ctx.send("❌ That item could not be loaded from the shop catalog.")

        # Permanent items receive 15% off when featured in today's Daily Offers.
        # Rotating-only items keep their normal listed price.
        is_daily_offer = item_id in self.daily_rotation()
        is_permanent_item = item_id in self.SHOP_ITEMS

        if is_daily_offer and is_permanent_item:
            unit_cost = int(item["cost"] * 0.85)
        else:
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

            # Lock the database before checking inventory, balance, and
            # purchase limits so the entire purchase is atomic.
            await db.execute("BEGIN IMMEDIATE")

            if current_quantity + quantity > max_stack:
                await db.rollback()
                return await ctx.send(
                    f"📦 **Inventory Full!** You can only hold **{max_stack}x** "
                    f"**{item_info['name']}**.\n"
                    f"You currently have **{current_quantity}x**."
                )

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

                # Record this purchase against the item's current limit period.
                limit_info = self.SHOP_LIMITS.get(item_id)

                if limit_info:
                    max_quantity, period = limit_info
                    period_key = self.purchase_period_key(period)

                    await db.execute(
                        """
                        INSERT INTO shop_purchase_limits
                            (user_id, item_id, period_key, quantity)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(user_id, item_id, period_key)
                        DO UPDATE SET quantity = quantity + excluded.quantity
                        """,
                        (
                            user_id,
                            item_id,
                            period_key,
                            quantity
                        )
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

                await self.record_shop_purchase(
                    db, user_id, item_id, quantity
                )

                await db.commit()

                return await ctx.send(
                    f"⚕️ **Purchase Successful!** Added **{quantity}x "
                    f"{item['name']}** to your inventory for "
                    f"**{cost:,} Stardust**!"
                )

            if item["type"] == "consumable" and item_id in {
                "fuel_refill",
                "laser_charge_cell",
                "laser_power_cell",
                "drone_battery",
                "drone_power_cell",
                "drone_quantum_battery",
            }:
                await db.execute(
                    """
                    INSERT INTO inventory (user_id, item_id, item_type, quantity)
                    VALUES (?, ?, 'consumable', ?)
                    ON CONFLICT(user_id, item_id) DO UPDATE SET
                        item_type = excluded.item_type,
                        quantity = quantity + excluded.quantity
                    """,
                    (user_id, item_id, quantity)
                )

                await db.execute(
                    "UPDATE users SET stardust = ? WHERE user_id = ?",
                    (new_stardust, user_id)
                )

                await self.record_shop_purchase(
                    db, user_id, item_id, quantity
                )

                await db.commit()

                return await ctx.send(
                    f"🔋 **Purchase Successful!** Added **{quantity}x "
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

                await self.record_shop_purchase(
                    db, user_id, item_id, quantity
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

                await self.record_shop_purchase(
                    db, user_id, item_id, quantity
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

                await self.record_shop_purchase(
                    db, user_id, item_id, quantity
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

                await self.record_shop_purchase(
                    db, user_id, item_id, quantity
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

    @commands.hybrid_command(
        name="shop_sell",
        description="Sell salvaged space junk from your inventory for Stardust."
    )
    @app_commands.describe(
        item="The junk item ID to sell, or 'all' to sell every piece of space junk."
    )
    async def sell(self, ctx: commands.Context, item: str):
        await ctx.defer()

        user_id = ctx.author.id
        target_item = item.lower().strip()
        db_path = self.get_db_path()

        async with aiosqlite.connect(db_path) as db:

            # Option A: Sell ALL space junk
            if target_item == "all":
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
                    junk_rows = await cursor.fetchall()

                if not junk_rows:
                    return await ctx.send(
                        "🎒 **Inventory Empty!** You don't have any space junk to sell."
                    )

                total_payout = sum(
                    self.JUNK_PRICES.get(item_id, 25) * quantity
                    for item_id, quantity in junk_rows
                )

                item_count = sum(quantity for _, quantity in junk_rows)

                await db.execute(
                    """
                    DELETE FROM inventory
                    WHERE user_id = ?
                      AND item_type = 'space_junk'
                    """,
                    (user_id,)
                )

                await db.execute(
                    """
                    UPDATE users
                    SET stardust = stardust + ?
                    WHERE user_id = ?
                    """,
                    (total_payout, user_id)
                )

                await db.commit()

                return await ctx.send(
                    f"🛍️ **Salvage Vendor:** Sold **{item_count} items** "
                    f"for a total of ✨ **{total_payout:,} Stardust**!"
                )

            # Option B: Sell ONE unit of a specific junk item
            async with db.execute(
                """
                SELECT quantity
                FROM inventory
                WHERE user_id = ?
                  AND item_id = ?
                  AND item_type = 'space_junk'
                """,
                (user_id, target_item)
            ) as cursor:
                row = await cursor.fetchone()

            if not row or (row[0] or 0) <= 0:
                return await ctx.send(
                    f"❌ You don't have `{target_item}` in your space junk inventory!"
                )

            quantity = row[0] or 0
            payout = self.JUNK_PRICES.get(target_item, 25)

            if quantity > 1:
                await db.execute(
                    """
                    UPDATE inventory
                    SET quantity = quantity - 1
                    WHERE user_id = ?
                      AND item_id = ?
                      AND item_type = 'space_junk'
                    """,
                    (user_id, target_item)
                )
            else:
                await db.execute(
                    """
                    DELETE FROM inventory
                    WHERE user_id = ?
                      AND item_id = ?
                      AND item_type = 'space_junk'
                    """,
                    (user_id, target_item)
                )

            await db.execute(
                """
                UPDATE users
                SET stardust = stardust + ?
                WHERE user_id = ?
                """,
                (payout, user_id)
            )

            await db.commit()

            remaining = quantity - 1

            await ctx.send(
                f"🛍️ **Salvage Vendor:** Sold **1x `{target_item}`** "
                f"for ✨ **{payout:,} Stardust**!\n"
                f"📦 **Remaining:** `{remaining}x`"
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
            ("🗑️ Space Junk A-M", "junk_am"),
            ("🗑️ Space Junk N-Z", "junk_nz"),
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
                "revive",
                "revive_kit",
                "full_revive",
            },

            "upgrades": {
                "fuel_stabilizer",
                "station_rations",
                "hazard_shield",
                "lucky_scanner",
                "ore_magnet",
                "prototype_drill_bit",
                "cosmic_insurance",
                "fate_anchor",
                "stardust_cache",
            },

            "consumables": {
                "laser_charge_cell",
                "laser_power_cell",
                "fuel_refill",
                "drone_battery",
                "drone_power_cell",
                "drone_quantum_battery",
                "quantum_battery",
                "time_crystal",
            },

            "pet_items": {
                "pet_snack",
            },

            "special": {
                "astral_core",
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

            if now - last_reward < 180:
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
