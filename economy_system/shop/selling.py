import asyncio
import aiosqlite
import datetime
import json
import random
import re
import time
from datetime import datetime, timedelta, time as dt_time
from typing import Any, Callable, Optional, cast

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
from .views import SellAllConfirmView



class EconomyShopSellingMixin:

    JUNK_PRICES: dict
    get_db_path: Callable[[], str]
    get_junk_sell_reward: Callable[[str], tuple[int, int]]

    async def _get_bulk_sale_rows(self, db, user_id, sale_kind):
            """Return sellable inventory rows for a bulk sale kind."""
            async with db.execute(
                "SELECT item_id, quantity, item_type FROM inventory WHERE user_id = ? AND quantity > 0 ORDER BY item_id",
                (user_id,),
            ) as cursor:
                rows = await cursor.fetchall()
    
            def is_junk(item_id, info, stored_type):
                return str(stored_type).lower() == "space_junk" or info.get("type") == "Space Junk"
    
            def is_halloween_collectible(item_id, info):
                # Bulk Halloween sales are intentionally limited to collectible
                # items only. Halloween materials, candy, bags, and seasonal
                # equipment must never be swept into this option.
                return (
                    item_id in LOCATION_BASED_COLLECTIBLES
                    or item_id in HALLOWEEN_COLLECTIBLE_IDS
                )
    
            result = []
            for item_id, quantity, stored_type in rows:
                info = ITEM_REGISTRY.get(item_id)
                if not info:
                    continue
                junk = is_junk(item_id, info, stored_type)
                halloween_collectible = is_halloween_collectible(item_id, info)
                collectible = (item_id in HALLOWEEN_COLLECTIBLE_IDS or item_id in LOCATION_BASED_COLLECTIBLES
                               or str(info.get("type", "")).lower() == "collectible")
                item_type = str(info.get("type", ""))
    
                if junk:
                    sellable = item_id in self.JUNK_PRICES or get_halloween_sell_reward(item_id) is not None
                else:
                    sellable = bool(int(info.get("sell_price", 0) or 0)) and (
                        item_type in {"Mineral", "Crafting Material", "Haunted Ingredient", "Location-Based Collectible", "Collectible"}
                        or item_id in SELLABLE_ITEM_IDS
                    )
                if not sellable:
                    continue
    
                if sale_kind == "all_junk":
                    if not junk or item_id in HALLOWEEN_SPACE_JUNK_IDS or item_id not in self.JUNK_PRICES:
                        continue
                elif sale_kind == "all_materials":
                    if item_id not in NORMAL_SELL_ALL_MATERIAL_IDS:
                        continue
                elif sale_kind == "all_halloween":
                    if not halloween_collectible:
                        continue
                else:
                    continue
    
                result.append((item_id, quantity, info, stored_type))
            return result

    async def _bulk_sale_preview(self, user_id, sale_kind):
            async with aiosqlite.connect(self.get_db_path()) as db:
                rows = await self._get_bulk_sale_rows(db, user_id, sale_kind)
    
            total_stardust = 0
            total_candy = 0
            item_count = 0
            lines = []
            for item_id, quantity, info, stored_type in rows:
                if str(stored_type).lower() == "space_junk" or info.get("type") == "Space Junk":
                    payout, candy = self.get_junk_sell_reward(item_id)
                else:
                    payout, candy = int(info.get("sell_price", 0) or 0), 0
                total_stardust += payout * quantity
                total_candy += candy * quantity
                item_count += quantity
                lines.append(f"{info.get('emoji', '📦')} **{info.get('name', item_id)} ×{quantity}**")
    
            return rows, total_stardust, total_candy, item_count, lines

    async def _confirm_bulk_sale(self, interaction, sale_kind, view):
            """Execute a previously confirmed bulk sale using a fresh DB snapshot."""
            user_id = interaction.user.id
            db_path = self.get_db_path()
    
            await interaction.response.defer()
    
            async with aiosqlite.connect(db_path) as db:
                await db.execute("BEGIN IMMEDIATE")
                rows = await self._get_bulk_sale_rows(db, user_id, sale_kind)
                if not rows:
                    await db.rollback()
                    return await interaction.edit_original_response(
                        content="❌ **Nothing to sell.** Your inventory changed before the confirmation was completed.",
                        embed=None,
                        view=view,
                    )
    
                total_stardust = 0
                total_candy = 0
                item_count = 0
                sold_lines = []
                for item_id, quantity, info, stored_type in rows:
                    if str(stored_type).lower() == "space_junk" or info.get("type") == "Space Junk":
                        payout, candy = self.get_junk_sell_reward(item_id)
                    else:
                        payout, candy = int(info.get("sell_price", 0) or 0), 0
                    total_stardust += payout * quantity
                    total_candy += candy * quantity
                    item_count += quantity
                    sold_lines.append(f"{info.get('emoji', '📦')} {info.get('name', item_id)} ×{quantity}")
    
                for item_id, _quantity, _info, _stored_type in rows:
                    await db.execute(
                        "DELETE FROM inventory WHERE user_id = ? AND item_id = ?",
                        (user_id, item_id),
                    )
    
                await db.execute(
                    "UPDATE users SET stardust = COALESCE(stardust, 0) + ? WHERE user_id = ?",
                    (total_stardust, user_id),
                )
    
                candy_added = 0
                candy_overflow = 0
                if total_candy > 0:
                    from inventory import add_inventory_item
                    candy_added, _, _ = await add_inventory_item(
                        db, user_id, "halloween_candy", "consumable", total_candy
                    )
                    candy_overflow = total_candy - candy_added
                    if candy_overflow > 0:
                        overflow_payout = candy_overflow * 5
                        total_stardust += overflow_payout
                        await db.execute(
                            "UPDATE users SET stardust = COALESCE(stardust, 0) + ? WHERE user_id = ?",
                            (overflow_payout, user_id),
                        )
    
                await db.commit()
    
            preview = "\n".join(sold_lines[:12])
            if len(sold_lines) > 12:
                preview += f"\n…and {len(sold_lines) - 12} more."
    
            candy_text = f"\n🍬 **Halloween Candy:** +{candy_added}" if candy_added else ""
            overflow_text = (
                f"\n📦 **Candy Overflow:** {candy_overflow} converted to ✨ **{candy_overflow * 5:,} Stardust**"
                if candy_overflow else ""
            )
            await interaction.edit_original_response(
                content=(
                    f"{interaction.user.mention} 🛍️ **Salvage Vendor:** Sold **{item_count} items** "
                    f"for ✨ **{total_stardust:,} Stardust**!{candy_text}{overflow_text}\n\n"
                    f"**Items Sold:**\n{preview}"
                ),
                embed=None,
                view=view,
            )

    async def sell(
            self,
            ctx: commands.Context,
            item: str,
            quantity: str = "1"
        ):
            await ctx.defer()
    
            user_id = ctx.author.id
            target_item = item.lower().strip()
            db_path = self.get_db_path()
    
            # Regular sales accept either a number (1–99) or `max`, which means
            # sell the entire quantity currently owned of the selected item.
            quantity_input = str(quantity).strip().lower()
            quantity_amount: Optional[int] = None
            if quantity_input == "max":
                quantity_is_max = True
            else:
                try:
                    quantity_amount = int(quantity_input)
                except (TypeError, ValueError):
                    return await ctx.send(
                        "❌ Quantity must be a number between **1 and 99**, or **`max`** to sell all you own."
                    )
                quantity_is_max = False
                if quantity_amount is None or quantity_amount < 1 or quantity_amount > 99:
                    return await ctx.send(
                        "❌ Quantity must be between **1 and 99**, or **`max`** to sell all you own."
                    )
    
            if target_item in BULK_SELL_OPTIONS:
                rows, total_stardust, total_candy, item_count, lines = await self._bulk_sale_preview(user_id, target_item)
                if not rows:
                    return await ctx.send("🎒 **Nothing to sell!** You don't currently have any items covered by that Sell All option.")
    
                preview = "\n".join(lines[:12])
                if len(lines) > 12:
                    preview += f"\n…and {len(lines) - 12} more."
                candy_preview = f"\n🍬 **Halloween Candy:** +{total_candy}" if total_candy else ""
                embed = discord.Embed(
                    title="⚠️ Confirm Bulk Sale",
                    description=(
                        f"You are about to sell **{item_count} items** for approximately "
                        f"✨ **{total_stardust:,} Stardust**.{candy_preview}\n\n"
                        f"**Items included:**\n{preview}\n\n"
                        "📚 **Collection Note:** Collectibles are permanently recorded in your collection once discovered. Selling the physical items does **not** remove them from your collection.\n\nThis cannot be undone. Choose **Yes, Sell All** or **Cancel**."
                    ),
                    color=discord.Color.orange(),
                )
                view = SellAllConfirmView(self, user_id, target_item)
                return await ctx.send(embed=embed, view=view)
    
            from inventory import ITEM_REGISTRY, add_inventory_item
    
            async with aiosqlite.connect(db_path) as db:
                # Lock the database before reading inventory so concurrent sell
                # requests cannot both cash out the same inventory.
                await db.execute("BEGIN IMMEDIATE")
    
                # ------------------------------------------------------------------
                # Option A: Sell all NORMAL Space Junk.
                # Halloween Space Junk is intentionally excluded.
                # ------------------------------------------------------------------
                if target_item == "all_junk":
                    async with db.execute(
                        """
                        SELECT item_id, quantity
                        FROM inventory
                        WHERE user_id = ?
                          AND item_type = 'space_junk'
                          AND item_id IN ({})
                          AND quantity > 0
                        """.format(",".join("?" * len(self.JUNK_PRICES))),
                        (user_id, *self.JUNK_PRICES.keys())
                    ) as cursor:
                        junk_rows = await cursor.fetchall()
    
                    # Halloween Space Junk is seasonal and intentionally excluded
                    # from the bulk "Sell All Space Junk" option.
                    junk_rows = [
                        (item_id, quantity)
                        for item_id, quantity in junk_rows
                        if item_id not in HALLOWEEN_SPACE_JUNK_IDS
                    ]
    
    
                    if not junk_rows:
                        await db.rollback()
                        return await ctx.send(
                            "🎒 **Inventory Empty!** You don't have any normal Space Junk to sell."
                        )
    
                    total_payout = sum(
                        self.JUNK_PRICES[item_id] * quantity
                        for item_id, quantity in junk_rows
                    )
                    item_count = sum(quantity for _, quantity in junk_rows)
    
                    for item_id, _quantity in junk_rows:
                        await db.execute(
                            """
                            DELETE FROM inventory
                            WHERE user_id = ?
                              AND item_id = ?
                            """,
                            (user_id, item_id),
                        )
    
                    await db.execute(
                        "UPDATE users SET stardust = stardust + ? WHERE user_id = ?",
                        (total_payout, user_id)
                    )
                    await db.commit()
    
                    return await ctx.send(
                        f"{ctx.author.mention} 🛍️ **Salvage Vendor:** Sold **{item_count} items** "
                        f"for a total of ✨ **{total_payout:,} Stardust**!"
                    )
    
                # ------------------------------------------------------------------
                # Option B: Sell all NORMAL ores & crafting materials.
                # Haunted Ingredients and Halloween materials are excluded.
                # ------------------------------------------------------------------
                if target_item == "all_materials":
                    placeholders = ",".join("?" * len(NORMAL_SELL_ALL_MATERIAL_IDS))
                    material_ids = tuple(NORMAL_SELL_ALL_MATERIAL_IDS)
    
                    async with db.execute(
                        f"""
                        SELECT item_id, quantity
                        FROM inventory
                        WHERE user_id = ?
                          AND item_id IN ({placeholders})
                          AND quantity > 0
                        """,
                        (user_id, *material_ids)
                    ) as cursor:
                        material_rows = await cursor.fetchall()
    
                    if not material_rows:
                        await db.rollback()
                        return await ctx.send(
                            "🎒 **Inventory Empty!** You don't have any normal ores or materials to sell."
                        )
    
                    total_payout = 0
                    item_count = 0
                    sold_lines = []
                    for item_id, owned_quantity in material_rows:
                        info = ITEM_REGISTRY.get(item_id, {})
                        unit_price = int(info.get("sell_price", 0) or 0)
                        if unit_price <= 0:
                            continue
                        total_payout += unit_price * owned_quantity
                        item_count += owned_quantity
                        sold_lines.append(
                            f"{info.get('emoji', '📦')} {info.get('name', item_id)} ×{owned_quantity}"
                        )
    
                    if not sold_lines:
                        await db.rollback()
                        return await ctx.send(
                            "🎒 **Nothing Sellable!** You don't have any priced normal ores or materials."
                        )
    
                    await db.execute(
                        f"""
                        DELETE FROM inventory
                        WHERE user_id = ?
                          AND item_id IN ({placeholders})
                        """,
                        (user_id, *material_ids)
                    )
                    await db.execute(
                        "UPDATE users SET stardust = stardust + ? WHERE user_id = ?",
                        (total_payout, user_id)
                    )
                    await db.commit()
    
                    preview = "\n".join(sold_lines[:12])
                    if len(sold_lines) > 12:
                        preview += f"\n…and {len(sold_lines) - 12} more."
    
                    return await ctx.send(
                        f"{ctx.author.mention} 🛍️ **Salvage Vendor:** Sold **{item_count} items** "
                        f"for ✨ **{total_payout:,} Stardust**!\n\n"
                        f"🔧 **Materials Sold:**\n{preview}"
                    )
    
                # ------------------------------------------------------------------
                # Option C: Sell a selected quantity of one sellable item.
                # Time Crystals are stored on users.time_crystals, not inventory.
                # ------------------------------------------------------------------
                if target_item == "time_crystal":
                    async with db.execute(
                        "SELECT COALESCE(time_crystals, 0) FROM users WHERE user_id = ?",
                        (user_id,)
                    ) as cursor:
                        time_crystal_row = await cursor.fetchone()
    
                    owned_quantity = time_crystal_row[0] if time_crystal_row else 0
                    if owned_quantity <= 0:
                        await db.rollback()
                        return await ctx.send("❌ You don't have any **Dilated Time Crystals** to sell.")
    
                    if quantity_is_max:
                        quantity_amount = owned_quantity
                    elif quantity_amount is None or quantity_amount > owned_quantity:
                        await db.rollback()
                        return await ctx.send(
                            f"❌ You only have **{owned_quantity}x** **Dilated Time Crystals** in your inventory."
                        )
    
                    if quantity_amount is None:
                        await db.rollback()
                        return await ctx.send("❌ A valid sale quantity could not be determined.")
    
                    unit_payout = int(ITEM_REGISTRY.get("time_crystal", {}).get("sell_price", 0) or 0)
                    if unit_payout <= 0:
                        await db.rollback()
                        return await ctx.send("❌ Dilated Time Crystals do not currently have a sell price.")
                    payout = unit_payout * quantity_amount
                    remaining = owned_quantity - quantity_amount
    
                    await db.execute(
                        "UPDATE users SET time_crystals = ? WHERE user_id = ?",
                        (remaining, user_id)
                    )
                    await db.execute(
                        "UPDATE users SET stardust = stardust + ? WHERE user_id = ?",
                        (payout, user_id)
                    )
                    await db.commit()
    
                    return await ctx.send(
                        f"{ctx.author.mention} 🛍️ **Salvage Vendor:** Sold **{quantity_amount}x Dilated Time Crystal** "
                        f"for ✨ **{payout:,} Stardust**!\n"
                        f"📦 **Remaining:** **{remaining}x**"
                    )
    
                async with db.execute(
                    """
                    SELECT quantity, item_type
                    FROM inventory
                    WHERE user_id = ?
                      AND item_id = ?
                      AND quantity > 0
                    """,
                    (user_id, target_item)
                ) as cursor:
                    row = await cursor.fetchone()
    
                info = ITEM_REGISTRY.get(target_item)
                if not row or not info:
                    await db.rollback()
                    return await ctx.send(
                        f"❌ You don't have `{target_item}` in your inventory, or it isn't sellable."
                    )
    
                owned_quantity, stored_item_type = row
                is_space_junk = (
                    str(stored_item_type).lower() == "space_junk"
                    or info.get("type") == "Space Junk"
                )
    
                if is_space_junk:
                    if (
                        target_item not in self.JUNK_PRICES
                        and get_halloween_sell_reward(target_item) is None
                    ):
                        await db.rollback()
                        return await ctx.send("❌ That Space Junk item cannot be sold.")
                    unit_payout, unit_candy_reward = self.get_junk_sell_reward(target_item)
                else:
                    unit_payout = int(info.get("sell_price", 0) or 0)
                    unit_candy_reward = 0
                    item_type = str(info.get("type", ""))
                    is_non_sellable_unlock = item_type in {
                        "title", "background_voucher", "station_upgrade"
                    }
                    is_upgrade_kit = item_type == "Upgrade Component" and target_item in get_upgrade_kit_ids()
    
                    if unit_payout <= 0 or is_non_sellable_unlock or (
                        item_type not in {
                            "Mineral",
                            "Crafting Material",
                            "Haunted Ingredient",
                            "Location-Based Collectible",
                            "Collectible",
                        }
                        and not is_upgrade_kit
                        and target_item not in SELLABLE_ITEM_IDS
                    ):
                        await db.rollback()
                        return await ctx.send("❌ That item cannot be sold.")
    
                if quantity_is_max:
                    quantity_amount = owned_quantity
                elif quantity_amount is None or quantity_amount > owned_quantity:
                    await db.rollback()
                    return await ctx.send(
                        f"❌ You only have **{owned_quantity}x** of **{info['name']}** in your inventory."
                    )
    
                if quantity_amount is None:
                    await db.rollback()
                    return await ctx.send("❌ A valid sale quantity could not be determined.")
    
                payout = unit_payout * quantity_amount
                candy_reward = unit_candy_reward * quantity_amount
                remaining = owned_quantity - quantity_amount
    
                if remaining > 0:
                    await db.execute(
                        """
                        UPDATE inventory
                        SET quantity = ?
                        WHERE user_id = ? AND item_id = ?
                        """,
                        (remaining, user_id, target_item)
                    )
                else:
                    await db.execute(
                        "DELETE FROM inventory WHERE user_id = ? AND item_id = ?",
                        (user_id, target_item)
                    )
    
                await db.execute(
                    "UPDATE users SET stardust = stardust + ? WHERE user_id = ?",
                    (payout, user_id)
                )
    
                candy_added = 0
                candy_overflow = 0
                if candy_reward > 0:
                    candy_added, _, _ = await add_inventory_item(
                        db, user_id, "halloween_candy", "consumable", candy_reward
                    )
                    candy_overflow = candy_reward - candy_added
                    if candy_overflow > 0:
                        overflow_payout = candy_overflow * 5
                        payout += overflow_payout
                        await db.execute(
                            "UPDATE users SET stardust = stardust + ? WHERE user_id = ?",
                            (overflow_payout, user_id)
                        )
    
                await db.commit()
    
                candy_text = f" and 🍬 **{candy_added} Halloween Candy**" if candy_added else ""
                overflow_text = (
                    f"\n📦 **Candy Overflow:** {candy_overflow} converted to ✨ **{candy_overflow * 5:,} Stardust**"
                    if candy_overflow else ""
                )
    
                await ctx.send(
                    f"{ctx.author.mention} 🛍️ **Salvage Vendor:** Sold **{quantity_amount}x {info['name']}** "
                    f"for ✨ **{payout:,} Stardust**{candy_text}!\n"
                    f"📦 **Remaining:** **{remaining}x**"
                    f"{overflow_text}"
                )

