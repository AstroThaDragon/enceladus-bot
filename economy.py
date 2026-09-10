import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import random
from datetime import datetime
import pytz

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Define shop catalog
        self.SHOP_ITEMS = {
            "nanite_patch": {
                "name": "🩹 Nanite Stim-Patch",
                "cost": 150,
                "type": "heal",
                "heal_amount": 35,
                "desc": "Quickly knits minor planetary surface wounds. Restores +35 HP."
            },
            "medkit": {
                "name": "🧰 Field Trauma Medkit",
                "cost": 300,
                "type": "heal",
                "heal_amount": 100,
                "desc": "Standard planetary survival trauma kit. Restores +100 HP."
            },
            "full_revive": {
                "name": "⚕️ Emergency Full Revival",
                "cost": 1000,
                "type": "revive",
                "desc": "Immediately revives an unconscious explorer at full HP."
            },
            "fuel_refill": {
                "name": "⚡ Emergency Fuel Cell (5 Charges)",
                "cost": 250,
                "type": "consumable",
                "desc": "Instantly refills your starship mining laser back to 5/5 charges."
            },
            "pet_snack": {
                "name": "🧬 Cosmic Bio-Feed (Pet Snack)",
                "cost": 400,
                "type": "consumable",
                "desc": "Nutrient pack used to feed your station pet companion."
            },
            "time_crystal": {
                "name": "💎 Dilated Time Crystal",
                "cost": 2000,
                "type": "special",
                "desc": "Bends time backwards to restore a fortune streak missed yesterday (Max 2 uses/month)."
            },
            "neon_grid": {
                "name": "🌆 Background Voucher: Neon Grid",
                "cost": 1000,
                "type": "background_voucher",
                "desc": "Unlocks the Cyberpunk Neon Grid background preset for your /profile card."
            },
            "deep_void": {
                "name": "🌌 Background Voucher: Deep Void",
                "cost": 1200,
                "type": "background_voucher",
                "desc": "Unlocks the Deep Void galaxy background preset for your /profile card."
            }
        }

        # Stardust buyback values for space junk items
        self.JUNK_PRICES = {
            "space_pizza": 35,
            "floppy_disk": 50,
            "meteorite": 85,
            "rubber_duck": 40,
            "rusty_gear": 25,
            "tape_deck": 45,
            "alien_artifact": 75,
            "space_boot": 55,
            "cosmic_coin": 80,
            "holo_poster": 65,
            "broken_laser": 30,
            "lost_logbook": 20,
            "left_sock": 15,
            "warp_mug": 30,
            "space_pudding": 20,
            "tangled_cables": 35,
            "screaming_crystal": 100,
            "moon_cheese": 60,
            "alien_spatula": 40,
            "parking_ticket": 10,
            "floating_plant": 70,
            "tinted_visor": 25,
            "purring_lint": 50,
            "pet_rock": 30,
            "haunted_circuit": 90,
            "space_taco": 45
        }

        # Add future daily offers here.  Each player sees the same three offers
        # for the whole Eastern-time day.
        self.ROTATING_ITEMS = {
            "fuel_stabilizer": {"name": "🛢️ Fuel Stabilizer", "cost": 225, "desc": "Makes your next mining run cost no fuel charge."},
            "station_rations": {"name": "🥫 Station Rations", "cost": 60, "desc": "Restores a modest 15 HP."},
            "hazard_shield": {"name": "🛡️ Hazard Shield", "cost": 300, "desc": "Blocks the next scavenging hazard."},
            "drone_battery": {"name": "🔋 Drone Battery Pack", "cost": 350, "desc": "Restores two scavenge charges."},
            "lucky_scanner": {"name": "📡 Deep-Space Scanner", "cost": 425, "desc": "Improves rare-find odds on your next scavenging run."},
            "ore_magnet": {"name": "🧲 Ore Magnet", "cost": 500, "desc": "Guarantees a titanium ore find on your next mining run."},
            "prototype_drill_bit": {"name": "⚙️ Prototype Drill Bit", "cost": 275, "desc": "Boosts Stardust from your next mining run."},
            "time_warp_coupon": {"name": "⏳ Time Warp Coupon", "cost": 650, "desc": "Reduces one exploration cooldown by one hour."},
            "salvage_insurance": {"name": "📋 Salvage Insurance", "cost": 600, "desc": "Prevents a knockout from your next scavenging hazard."},
            "fate_anchor": {"name": "⚓ Fate Anchor", "cost": 750, "desc": "Protects one missed fortune streak day."},
            "stardust_cache": {"name": "🎁 Contraband Stardust Cache", "cost": 450, "desc": "Open it for an unpredictable Stardust payoff."},
            "revive_kit": {"name": "💉 Emergency Revival Kit", "cost": 700, "desc": "Revives an unconscious explorer at 50% HP."},
            "title_outer_rim_wanderer": {"name": "🏷️ Title: Outer Rim Wanderer", "cost": 750, "type": "title", "desc": "A title for explorers who venture beyond the station."},
            "title_starborn": {"name": "✨ Title: Starborn", "cost": 750, "type": "title", "desc": "A prestigious title for those touched by the stars."},
            "title_voidfarer": {"name": "🌌 Title: Voidfarer", "cost": 750, "type": "title", "desc": "For those brave enough to chart the endless void."},
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

        # Legacy payout column
        if "legacy_payout" not in existing_columns:
            await db.execute(
                "ALTER TABLE users ADD COLUMN legacy_payout INTEGER DEFAULT 0"
            )

        # Legacy payouts are initialized to 0 in the new economy database.
        # No snapshot migration is needed because this Station database
        # starts fresh and leveling data remains in levels.db.

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
    @commands.hybrid_group(name="shop", description="Browse and trade at the Enceladus Station Trading Post.")
    async def shop(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="🛒 Enceladus Station Trading Post",
                description="Use `/shop buy <item_id>` to purchase items, or `/shop sell <item>` to turn in salvaged junk for Stardust.",
                color=discord.Color.from_rgb(0, 229, 255)
            )

            for item_id, details in self.SHOP_ITEMS.items():
                embed.add_field(
                    name=f"{details['name']} (`{item_id}`)",
                    value=f"💰 Price: **{details['cost']} Stardust**\n📖 {details['desc']}",
                    inline=False
                )

            rotation = self.daily_rotation()
            rotating_text = "\n".join(
                f"{self.ROTATING_ITEMS[item_id]['name']} (`{item_id}`) — **{self.ROTATING_ITEMS[item_id]['cost']} Stardust**"
                for item_id in rotation
            )
            embed.add_field(
                name=f"🔄 Daily Rotating Offers — {self.rotation_date()}",
                value=f"Use `/shop rotating` for descriptions and `/shop buy <item_id>` to purchase.\n{rotating_text}",
                inline=False,
            )

            embed.set_footer(text="Tip: Check your wallet balance using /profile")
            await ctx.send(embed=embed)

    @shop.command(name="rotating", description="View today's three shared rotating-shop offers.")
    @commands.has_permissions(administrator=True)
    async def rotating(self, ctx: commands.Context):
        rotation = self.daily_rotation()
        embed = discord.Embed(
            title=f"🔄 Daily Station Market — {self.rotation_date()}",
            description="These three offers rotate at midnight Eastern time for the entire station.",
            color=discord.Color.purple(),
        )
        for item_id in rotation:
            item = self.ROTATING_ITEMS[item_id]
            embed.add_field(
                name=f"{item['name']} (`{item_id}`)",
                value=f"💰 **{item['cost']} Stardust**\n{item['desc']}",
                inline=False,
            )
        await ctx.send(embed=embed)

    @shop.command(name="browse", description="Browse the permanent catalog and today's rotating offers.")
    async def browse(self, ctx: commands.Context):
        embed = discord.Embed(
            title="🛒 Enceladus Station Trading Post",
            description="Use `/shop buy <item_id>` to purchase items, or `/shop sell <item>` to sell salvage.",
            color=discord.Color.from_rgb(0, 229, 255),
        )
        for item_id, details in self.SHOP_ITEMS.items():
            embed.add_field(name=f"{details['name']} (`{item_id}`)", value=f"💰 **{details['cost']} Stardust**\n{details['desc']}", inline=False)
        embed.set_footer(text="Use /shop rotating to view today's temporary offers.")
        await ctx.send(embed=embed)

    @shop.command(name="buy", description="Purchase an item from the station vendor catalog.")
    @app_commands.describe(item_id="The ID code of the item to buy")
    async def buy(self, ctx: commands.Context, item_id: str):
        await ctx.defer()
        user_id = ctx.author.id
        item_id = item_id.lower()

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

        item = self.SHOP_ITEMS.get(item_id, rotating_item)
        cost = item["cost"]

        db_path = self.get_db_path()

        async with aiosqlite.connect(db_path) as db:
            # Run schema/migration work before starting the purchase transaction.
            await self.ensure_schema(db)
            await db.commit()

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
                    f"Stardust, but this item costs `{cost}`."
                )

            # Process purchase based on item type.
            new_stardust = stardust - cost

            if rotating_item is not None:
                item = rotating_item
                item_type = item.get("type", "consumable")

                # Titles are unlocks, so don't allow the same title to be purchased twice.
                if item_type == "title":
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

                await db.execute(
                    """
                    INSERT INTO inventory (user_id, item_id, item_type, quantity)
                    VALUES (?, ?, ?, 1)
                    ON CONFLICT(user_id, item_id) DO UPDATE SET
                        item_type = excluded.item_type,
                        quantity = quantity + 1
                    """,
                    (user_id, item_id, item_type)
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
                    f"🔄 **Rotating-market purchase complete!** "
                    f"Added **{item['name']}** to your inventory for "
                    f"**{cost:,} Stardust**."
                )

            if item["type"] == "revive":
                if (hp or 0) > 0:
                    await db.rollback()
                    return await ctx.send(
                        "⚠️ You are conscious already—save a full revival "
                        "for when you are knocked out."
                    )

                await db.execute(
                    """
                    UPDATE users
                    SET stardust = ?, hp = ?, knocked_out_until = ''
                    WHERE user_id = ?
                    """,
                    (new_stardust, max_hp or 100, user_id)
                )

                await db.commit()

                return await ctx.send(
                    f"⚕️ **Full Revival Complete!** You are back on your feet "
                    f"with **{max_hp or 100}/{max_hp or 100} HP**."
                )

            if item["type"] == "consumable" and item_id == "fuel_refill":
                if charges >= 5:
                    await db.rollback()
                    return await ctx.send(
                        "⚠️ Your mining laser fuel charges are already full (`5/5`)!"
                    )

                await db.execute(
                    "UPDATE users SET stardust = ?, mining_charges = 5 "
                    "WHERE user_id = ?",
                    (new_stardust, user_id)
                )

                await db.commit()

                return await ctx.send(
                    f"⚡ **Purchase Successful!** Refilled your mining laser "
                    f"charges back to `5/5` for `{cost}` Stardust."
                )

            if item["type"] == "consumable" and item_id == "pet_snack":
                await db.execute(
                    """
                    INSERT INTO inventory (user_id, item_id, item_type, quantity)
                    VALUES (?, ?, 'consumable', 1)
                    ON CONFLICT(user_id, item_id) DO UPDATE SET
                        item_type = excluded.item_type,
                        quantity = quantity + 1
                    """,
                    (user_id, item_id)
                )

                await db.execute(
                    "UPDATE users SET stardust = ? WHERE user_id = ?",
                    (new_stardust, user_id)
                )

                await db.commit()

                return await ctx.send(
                    f"🧬 **Purchase Successful!** Added a Cosmic Bio-Feed "
                    f"to your inventory for `{cost}` Stardust."
                )

            if item_id == "time_crystal":
                # Schema is already ensured before the transaction.
                await db.execute(
                    """
                    UPDATE users
                    SET stardust = ?,
                        time_crystals = COALESCE(time_crystals, 0) + 1
                    WHERE user_id = ?
                    """,
                    (new_stardust, user_id)
                )

                await db.commit()

                return await ctx.send(
                    f"💎 **Purchase Successful!** You bought a "
                    f"**Dilated Time Crystal** for **{cost:,} Stardust**!\n"
                    f"If you miss a fortune streak, run `/usecrystal` to repair it."
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
                    f"🌟 **Purchase Successful!** Unlocked background "
                    f"voucher `{item_id}` for `{cost}` Stardust!"
                )

            if item["type"] == "heal":
                # Item key format:
                # medkit -> medkits
                # nanite_patch -> nanite_patchs
                col_name = f"{item_id}s"

                # Ensure inventory column exists dynamically.
                async with db.execute("PRAGMA table_info(users)") as cursor:
                    rows = await cursor.fetchall()

                existing_cols = {row[1] for row in rows}

                if col_name not in existing_cols:
                    await db.execute(
                        f"ALTER TABLE users ADD COLUMN "
                        f"{col_name} INTEGER DEFAULT 0"
                    )

                await db.execute(
                    f"""
                    UPDATE users
                    SET stardust = ?,
                        {col_name} = COALESCE({col_name}, 0) + 1
                    WHERE user_id = ?
                    """,
                    (new_stardust, user_id)
                )

                await db.commit()

                return await ctx.send(
                    f"✅ **Purchased!** You bought **1x {item['name']}** "
                    f"for **{cost:,} Stardust**!"
                )

            await db.rollback()

        await ctx.send("❌ An error occurred processing your transaction.")

    @shop.command(name="sell", description="Sell salvaged space junk from your inventory for Stardust.")
    @app_commands.describe(item="The junk item ID to sell, or 'all' to sell every piece of space junk.")
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
                    "WHERE user_id = ? AND item_type = 'space_junk'",
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
                "SELECT quantity "
                "FROM inventory "
                "WHERE user_id = ? AND item_id = ? AND item_type = 'space_junk'",
                (user_id, target_item)
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                await db.rollback()
                return await ctx.send(
                    f"❌ You don't have `{target_item}` in your space junk inventory!"
                )

            payout = self.JUNK_PRICES.get(target_item, 25)

            if (row[0] or 1) > 1:
                await db.execute(
                    "UPDATE inventory "
                    "SET quantity = quantity - 1 "
                    "WHERE user_id = ? AND item_id = ? AND item_type = 'space_junk'",
                    (user_id, target_item)
                )
            else:
                await db.execute(
                    "DELETE FROM inventory "
                    "WHERE user_id = ? AND item_id = ? AND item_type = 'space_junk'",
                    (user_id, target_item)
                )

            await db.execute(
                "UPDATE users "
                "SET stardust = stardust + ? "
                "WHERE user_id = ?",
                (payout, user_id)
            )

            await db.commit()

        await ctx.send(
            f"🛍️ **Salvage Vendor:** Sold `{target_item}` "
            f"for ✨ **{payout} Stardust**!"
        )

    @commands.hybrid_command(name="item", description="Inspect an item from the station database to check its properties.")
    async def item_lookup(self, ctx: commands.Context, item_id: str):
        item_id = item_id.lower()
        from inventory import ITEM_REGISTRY

        if item_id not in ITEM_REGISTRY:
            return await ctx.send(f"❌ Unknown item code `'{item_id}'`. Check the `/shop` or your `/inventory` for valid item IDs.")

        info = ITEM_REGISTRY[item_id]
        
        embed = discord.Embed(
            title=f"{info['emoji']} {info['name']}",
            description=f"**Category:** {info['type']}\n**Description:** {info['desc']}",
            color=discord.Color.from_rgb(120, 140, 160)
        )
        embed.set_footer(text=f"System Item ID: {item_id}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(
        name="claimlegacy",
        description="Claim your one-time Stardust snapshot payout from before the Shop & Exploration update!"
    )
    async def claim_legacy_bonus(self, ctx: commands.Context):
        await ctx.defer()

        user_id = ctx.author.id
        db_path = self.get_db_path()

        async with aiosqlite.connect(db_path) as db:
            # Ensure the legacy payout column and migration exist.
            await self.ensure_schema(db)
            await db.commit()

            # Lock the transaction so two simultaneous /claimlegacy
            # commands cannot both redeem the same payout.
            await db.execute("BEGIN IMMEDIATE")

            async with db.execute(
                """
                SELECT stardust, legacy_payout
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
            legacy_payout = row[1] or 0

            if legacy_payout <= 0:
                await db.rollback()
                return await ctx.send(
                    "⚠️ **Not Eligible or Already Claimed!** "
                    "Either you weren't Level 5+ when the update snapshot "
                    "was taken, or you've already redeemed your legacy payout."
                )

            # Add the snapshot payout and clear it in the same transaction.
            await db.execute(
                """
                UPDATE users
                SET stardust = ?,
                    legacy_payout = 0
                WHERE user_id = ?
                """,
                (current_stardust + legacy_payout, user_id)
            )

            await db.commit()

        await ctx.send(
            f"🎉 **Legacy Snapshot Claimed!**\n"
            f"Thanks for being a server veteran! Your pre-update level "
            f"snapshot rewarded you with ✨ **{legacy_payout:,} Stardust**!"
        )

async def setup(bot):
    await bot.add_cog(Economy(bot))
