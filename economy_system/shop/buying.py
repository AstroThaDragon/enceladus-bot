import asyncio
import aiosqlite
import datetime
import json
import random
import re
import time
from datetime import datetime, timedelta, time as dt_time
from typing import Any, Optional, cast, Callable

import discord
from discord import app_commands
from discord.ext import commands, tasks
import pytz

from emojis import EMOJIS
from seasonal_updates.halloween.halloween import is_active as halloween_is_active
from seasonal_updates.halloween.halloween import HALLOWEEN_SPACE_JUNK, get_sell_reward as get_halloween_sell_reward
from seasonal_updates.halloween.halloween import get_collectibles as get_halloween_collectibles
from inventory import ITEM_REGISTRY
from collectibles import LOCATION_BASED_COLLECTIBLES
from pets.core import get_pet_definition
from error_handler import log_task_error

from ..data import *
from .views import ShopTransactionView, ShopView



class EconomyShopBuyingHost:
    """Type contract for services supplied by the composed Economy cog."""

    DEFAULT_VAULT_CAPACITY: int
    MAX_VAULT_CAPACITY: int
    ROTATING_ITEMS: dict[str, dict[str, Any]]
    SHOP_ITEMS: dict[str, dict[str, Any]]
    SHOP_LIMITS: dict[str, tuple[int, str]]

    daily_rotation: Callable[[], list[str]]
    get_db_path: Callable[[], str]
    rotation_date: Callable[[], str]
    purchase_period_key: Callable[[str], str]

    async def ensure_schema(self, db: Any) -> None:
        raise NotImplementedError

    async def record_shop_purchase(
        self, db: Any, user_id: int, item_id: str, quantity: int
    ) -> None:
        raise NotImplementedError


class EconomyShopBuyingMixin(EconomyShopBuyingHost):
    async def shop(self, ctx: commands.Context):
            """Shop command group."""
            await ctx.send(
                "🛒 Choose a shop option: **list**, **buy**, **sell**, or **rotating**."
            )

    async def shop_list(
            self,
            ctx: commands.Context,
            category: str = "healing",
        ):
            """Display the shop catalog."""
            view = ShopView(self, ctx.author.id)
            embed = view.build_embed(category)
            await ctx.send(embed=embed, view=view)

    async def shop_buy(self, ctx: commands.Context):
            """Open the interactive Category → Item → Quantity → Confirm buy flow."""
            view = ShopTransactionView(self, ctx.author.id, "buy")
            embed = view._build_category_embed()
            await ctx.send(embed=embed, view=view)

    async def shop_sell(self, ctx: commands.Context):
            """Open the interactive Category → Item → Quantity → Confirm sell flow."""
            view = ShopTransactionView(self, ctx.author.id, "sell")
            embed = view._build_category_embed()
            await ctx.send(embed=embed, view=view)

    async def shop_rotating(self, ctx: commands.Context):
            """Display today's rotating shop with direct purchase buttons."""
            view = ShopView(self, ctx.author.id, category="daily")
            embed = view.build_embed("daily")
            embed.set_footer(text="Choose an offer below to buy it • Offers rotate at midnight Eastern time.")
            await ctx.send(embed=embed, view=view)

    async def buy(self, ctx: commands.Context, item_id: str, quantity: int = 1):
            await ctx.defer()
            user_id = ctx.author.id
            item_id = item_id.lower()
    
            if quantity < 1 or quantity > 99:
                return await ctx.send("❌ Quantity must be between **1 and 99**.")
    
            rotating_item = self.ROTATING_ITEMS.get(item_id)
            is_permanent_item = item_id in self.SHOP_ITEMS
    
            if not is_permanent_item and rotating_item is None:
                return await ctx.send(
                    "❌ Invalid item ID! Check available items using `/shop`."
                )
    
            # Rotation-only items must be featured today. Permanent items may also
            # appear in ROTATING_ITEMS and receive the Daily Offer discount.
            if not is_permanent_item:
                if rotating_item is None:
                    return await ctx.send("❌ That rotating item could not be loaded.")
                if item_id not in self.daily_rotation():
                    return await ctx.send(
                        "⏳ That item is not in today's rotating market. "
                        "Check `/shop` and select 🔄️ Daily Offers for the current offers."
                    )
    
            item: dict[str, Any] | None = self.SHOP_ITEMS.get(item_id)
            if item is None:
                if rotating_item is None:
                    return await ctx.send("❌ That item could not be loaded from the shop catalog.")
                item = rotating_item
    
            # The fallback above guarantees that ``item`` is populated.
            # Keep the invariant explicit for static type checkers.
            assert item is not None

            # Permanent items receive 15% off when featured in today's Daily Offers.
            # Rotating-only items keep their normal listed price.
            is_daily_offer = item_id in self.daily_rotation()
    
            if is_daily_offer and is_permanent_item:
                base_unit_cost = int(item["cost"] * 0.85)
            else:
                base_unit_cost = item["cost"]
    
            cost = base_unit_cost * quantity
    
            db_path = self.get_db_path()
    
            async with aiosqlite.connect(db_path) as db:
    
                # Run schema/migration work before starting the purchase transaction.
                await self.ensure_schema(db)
                await db.commit()
    
                from inventory import ITEM_REGISTRY, add_inventory_item
    
                item_info = ITEM_REGISTRY.get(item_id)
    
                # Permanent station upgrades live on the users table rather than
                # the inventory registry. They are handled below and return before
                # any inventory-registry-only code is reached.
    
                # These items are stored directly on the users table.
                legacy_columns = {
                    "time_crystal": "time_crystals",
                    "nanite_patch": "nanite_patchs",
                    "medkit": "medkits",
                }
    
                # Lock before reading inventory, balance, or purchase-limit state.
                # All critical reads and writes now share one atomic snapshot.
                await db.execute("BEGIN IMMEDIATE")
    
                # Some rotation-only catalog entries do not carry their own
                # type metadata. Fall back to the master inventory definition
                # instead of indexing the key directly and raising KeyError.
                item_type = item.get("type")
                if item_type is None and item_info is not None:
                    item_type = item_info.get("type")
    
                if item_type == "station_upgrade":
                    if quantity != 1:
                        await db.rollback()
                        return await ctx.send(
                            "🛠️ Station upgrades can only be purchased **one at a time**."
                        )
    
                    async with db.execute(
                        "SELECT COALESCE(stardust, 0), COALESCE(incubator_slots, 1), "
                        "COALESCE(vault_capacity, ?) FROM users WHERE user_id = ?",
                        (self.DEFAULT_VAULT_CAPACITY, user_id),
                    ) as cursor:
                        upgrade_row = await cursor.fetchone()
    
                    if not upgrade_row:
                        await db.rollback()
                        return await ctx.send(
                            "❌ You don't have an active station profile yet. "
                            "Run `/profile` or `/mine` first!"
                        )
    
                    stardust, incubator_slots, vault_capacity = upgrade_row
    
                    if item_id == "incubator_2" and incubator_slots >= 2:
                        await db.rollback()
                        return await ctx.send(
                            "🥚 You already have Incubator Tube II unlocked."
                        )
    
                    if item_id == "incubator_3" and incubator_slots >= 3:
                        await db.rollback()
                        return await ctx.send(
                            "🥚 You already have Incubator Tube III unlocked."
                        )
    
                    if item_id == "incubator_3" and incubator_slots < 2:
                        await db.rollback()
                        return await ctx.send(
                            "⚠️ Unlock Incubator Tube II before purchasing Tube III."
                        )
    
                    if item_id == "vault_expansion" and vault_capacity >= self.MAX_VAULT_CAPACITY:
                        await db.rollback()
                        return await ctx.send(
                            "🔐 Your Stardust vault is already at its 500,000 Stardust maximum."
                        )
    
                    if stardust < cost:
                        await db.rollback()
                        return await ctx.send(
                            f"💸 **Insufficient Stardust!** You have **{stardust:,}** "
                            f"Stardust, but this upgrade costs **{cost:,}**."
                        )
    
                    if item_id == "incubator_2":
                        await db.execute(
                            "UPDATE users SET stardust = stardust - ?, incubator_slots = 2 WHERE user_id = ?",
                            (cost, user_id),
                        )
                    elif item_id == "incubator_3":
                        await db.execute(
                            "UPDATE users SET stardust = stardust - ?, incubator_slots = 3 WHERE user_id = ?",
                            (cost, user_id),
                        )
                    else:
                        await db.execute(
                            "UPDATE users SET stardust = stardust - ?, vault_capacity = ? WHERE user_id = ?",
                            (cost, self.MAX_VAULT_CAPACITY, user_id),
                        )
    
                    await self.record_shop_purchase(db, user_id, item_id, 1)
                    await db.commit()
    
                    return await ctx.send(
                        f"{ctx.author.mention} 🛠️ **Upgrade Purchased!** "
                        f"**{item['name']}** is now unlocked for **{cost:,} Stardust**."
                    )
    
                # Every non-upgrade purchase reaches this point only if the item
                # exists in the master inventory registry. Narrow the Optional
                # value here so Pylance can safely type-check all later uses.
                if item_info is None:
                    await db.rollback()
                    return await ctx.send(
                        "❌ This item is not registered in the master item registry."
                    )
    
                max_stack = item_info.get("max_quantity", 1)
    
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
    
                from pets import get_active_pet_effects
                pet_effects = await get_active_pet_effects(db, user_id)
    
                # Void Merchant's normal shop discount stacks on top of an existing
                # Daily Offer discount. Its level-5 free-purchase effect is a
                # one-purchase-per-day proc and is claimed inside this same lock.
                shop_discount = max(0.0, min(0.99, float(pet_effects.get("shop_discount", 0.0))))
                unit_cost = max(1, int(base_unit_cost * (1 - shop_discount)))
                cost = unit_cost * quantity
                free_purchase = False
    
                free_chance = float(pet_effects.get("shop_free_purchase", 0.0))
                if free_chance > 0:
                    today_key = self.rotation_date()
                    async with db.execute(
                        "SELECT 1 FROM pet_effect_usage WHERE user_id = ? AND effect_id = ? AND period_key = ?",
                        (user_id, "void_merchant_free_purchase", today_key),
                    ) as cursor:
                        free_used = await cursor.fetchone()
    
                    if not free_used and random.random() < free_chance:
                        await db.execute(
                            "INSERT INTO pet_effect_usage (user_id, effect_id, period_key) VALUES (?, ?, ?)",
                            (user_id, "void_merchant_free_purchase", today_key),
                        )
                        cost = 0
                        free_purchase = True
    
                if stardust < cost:
                    await db.rollback()
                    return await ctx.send(
                        f"💸 **Insufficient Stardust!** You have **{stardust:,}** "
                        f"Stardust, but this item costs **{cost:,}**."
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
                if item_type == "background_voucher" and quantity != 1:
                    await db.rollback()
                    return await ctx.send(
                        "🖼️ Background vouchers can only be purchased **one at a time**."
                    )
    
                # Process purchase based on item type.
                new_stardust = stardust - cost
    
                if rotating_item is not None:
                    item = rotating_item
                    item_type = rotating_item.get("type", "consumable")
    
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
    
                    price_note = (
                        "🕳️ **Void Merchant:** This purchase was completely free!"
                        if free_purchase else
                        f"for **{cost:,} Stardust**!"
                    )
                    if item_type == "title":
                        return await ctx.send(
                            f"🏷️ **Title Unlocked!** You purchased **{item['name']}** "
                            + price_note
                        )
    
                    return await ctx.send(
                        f"{ctx.author.mention} 🔄 **Purchase Successful!** Added **{quantity}x "
                        f"{item['name']}** to your inventory "
                        + price_note
                    )
    
                if item_type == "revive":
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
                        f"{ctx.author.mention} ⚕️ **Purchase Successful!** Added **{quantity}x "
                        f"{item['name']}** to your inventory for "
                        f"**{cost:,} Stardust**!"
                    )
    
                if item_type == "consumable" and item_id in {
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
                        f"{ctx.author.mention} 🔋 **Purchase Successful!** Added **{quantity}x "
                        f"{item['name']}** to your inventory for "
                        f"**{cost:,} Stardust**!"
                    )
    
                if item_type == "consumable" and item_id == "pet_snack":
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
                        f"{ctx.author.mention} 🧬 **Purchase Successful!** Added **{quantity}x {item['name']}** "
                        f"to your inventory for **{cost:,} Stardust**!"
                    )
                if item_id == "astral_essence":
                    added_amount, new_quantity, max_quantity = await add_inventory_item(
                        db,
                        user_id,
                        item_id,
                        "special",
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
                        f"{ctx.author.mention} ✨ **Purchase Successful!** Added **{quantity}x "
                        f"{item['name']}** to your inventory for **{cost:,} Stardust**!"
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
                        f"{ctx.author.mention} 💎 **Purchase Successful!** Added **{quantity}x "
                        f"{item['name']}** to your inventory for "
                        f"**{cost:,} Stardust**!\n"
                        f"If you miss a fortune streak, use `/usecrystal` to repair it."
                    )
    
                if item_type == "background_voucher":
                    # A redeemed voucher permanently unlocks its background.
                    # Check that unlock list before charging Stardust so users can
                    # never buy another copy of a background they already own.
                    async with db.execute(
                        "SELECT unlocked_backgrounds FROM users WHERE user_id = ?",
                        (user_id,)
                    ) as cursor:
                        unlock_row = await cursor.fetchone()
    
                    unlocked_backgrounds = ["default"]
                    if unlock_row and unlock_row[0]:
                        try:
                            parsed = json.loads(unlock_row[0])
                            if isinstance(parsed, list):
                                unlocked_backgrounds = parsed
                        except (TypeError, json.JSONDecodeError):
                            pass
    
                    if item_id in unlocked_backgrounds:
                        await db.rollback()
                        return await ctx.send(
                            "⚠️ You already unlocked this background! "
                            "You can select it with `/background` **after** redeeming with `/voucher`."
                        )
    
                    # Also prevent buying a duplicate voucher while the original
                    # unredeemed voucher is still in the user's inventory.
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
                        f"{ctx.author.mention} 🌟 **Purchase Successful!** Unlocked "
                        f"**{item['name']}** for **{cost:,} Stardust**!"
                    )
    
                if item_type == "heal":
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
                        f"{ctx.author.mention} 🛒 **Purchase Successful!** Added **{quantity}x {item['name']}** "
                        f"to your inventory for **{cost:,} Stardust**!"
                    )
    
                await db.rollback()
    
            await ctx.send("❌ An error occurred processing your transaction.")

