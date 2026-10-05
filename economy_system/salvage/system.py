import asyncio
import aiosqlite
import datetime
import json
import random
import re
import time
from datetime import datetime, timedelta, time as dt_time
from typing import Any, Optional, cast, Callable, Awaitable

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
from .autocomplete import EconomySalvageAutocompleteMixin


class EconomySalvageMixin(commands.Cog):
    # These members are supplied by the main Economy cog / other economy mixins.
    # Declaring them here keeps static type checkers aware of the host interface
    # without creating a runtime import cycle.
    bot: commands.Bot
    JUNK_PRICES: dict[str, int]
    get_db_path: Callable[[], str]

    async def salvage_item_autocomplete(self, interaction: discord.Interaction, current: str):
        return await EconomySalvageAutocompleteMixin.salvage_item_autocomplete(
            cast(EconomySalvageAutocompleteMixin, self), interaction, current
        )

    def get_junk_sell_reward(self, item_id) -> tuple[int, int]:
            """Return Stardust + Halloween Candy rewards for a junk item."""
            halloween_reward = get_halloween_sell_reward(item_id)
            if halloween_reward is not None:
                return (int(halloween_reward[0]), int(halloween_reward[1]))
            return (int(self.JUNK_PRICES.get(item_id, 25)), 0)

    def salvage_pool_for(self, item_id):
            """Return the material pool used when a Space Junk item is salvaged."""
            category = SALVAGE_CATEGORIES.get(item_id, "miscellaneous")
            return SALVAGE_POOLS[category]

    def roll_salvage_material(self, item_id):
            """Roll one guaranteed base material for a junk item."""
            pool = self.salvage_pool_for(item_id)
            return random.choices(
                [material_id for material_id, _weight in pool],
                weights=[weight for _material_id, weight in pool],
                k=1,
            )[0]

    async def add_salvage_material(self, db, user_id, material_id, amount):
            """Add salvage materials and convert inventory overflow into Stardust."""
            from inventory import add_inventory_item
    
            added, _quantity, _max_quantity = await add_inventory_item(
                db, user_id, material_id, "crafting_material", amount
            )
            overflow = amount - added
            overflow_stardust = overflow * SALVAGE_OVERFLOW_VALUES.get(material_id, 0)
            return added, overflow, overflow_stardust

    async def inventory_row_exists(self, db, user_id, item_id):
            async with db.execute(
                "SELECT 1 FROM inventory WHERE user_id = ? AND item_id = ? LIMIT 1",
                (user_id, item_id),
            ) as cursor:
                return await cursor.fetchone() is not None

    @commands.hybrid_command(
        name="salvage",
        description="Salvage Space Junk or upgrade kits for materials."
    )
    @app_commands.describe(item="Choose Space Junk to salvage, or salvage all of it.")
    @app_commands.autocomplete(item=salvage_item_autocomplete)
    async def salvage(self, ctx: commands.Context, item: str):
            await ctx.defer()
    
            user_id = ctx.author.id
            target_item = item.lower().strip()
            db_path = self.get_db_path()
    
            # Get the user's current Salvage Rig bonus chance.
            upgrade_cog = self.bot.get_cog("Upgrades")
            get_effects = getattr(upgrade_cog, "get_effects", None)

            if callable(get_effects):
                get_effects_typed = cast(
                    Callable[[int, str], Awaitable[dict]],
                    get_effects,
                )
                salvage_upgrade = await get_effects_typed(user_id, "salvage")
            else:
                salvage_upgrade = {"level": 0, "bonus_chance": 0.0}

            bonus_chance = salvage_upgrade.get("bonus_chance", 0.0)
    
            from inventory import ITEM_REGISTRY
            from crafting import RECIPES
    
            upgrade_kit_recipes = {
                recipe["result"]: recipe
                for recipe in RECIPES.values()
                if recipe["result"].startswith((
                    "reinforced_laser_parts_",
                    "drone_upgrade_kit_",
                    "salvage_rig_kit_",
                ))
                or recipe["result"] == "nanite_retrofit_kit"
            }
    
            async with aiosqlite.connect(db_path) as db:
                await db.execute("BEGIN IMMEDIATE")
    
                # Upgrade kits are salvaged back into their exact crafting recipe.
                # This path intentionally does not apply Salvage Rig bonus rolls.
                if target_item in upgrade_kit_recipes:
                    recipe = upgrade_kit_recipes[target_item]
                    async with db.execute(
                        "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ? AND quantity > 0",
                        (user_id, target_item),
                    ) as cursor:
                        kit_row = await cursor.fetchone()
    
                    if not kit_row:
                        await db.rollback()
                        return await ctx.send(
                            f"{ctx.author.mention} ❌ You don't have **{ITEM_REGISTRY.get(target_item, {}).get('name', target_item)}** to salvage."
                        )
    
                    # The kit is a single-use item. Make sure every returned material
                    # fits before changing anything so the recipe is returned in full.
                    capacity_missing = []
                    for material_id, amount in recipe["ingredients"].items():
                        async with db.execute(
                            "SELECT COALESCE(quantity, 0) FROM inventory WHERE user_id = ? AND item_id = ?",
                            (user_id, material_id),
                        ) as cursor:
                            row = await cursor.fetchone()
                        owned = row[0] if row else 0
                        max_quantity = ITEM_REGISTRY.get(material_id, {}).get("max_quantity", 10)
                        if owned + amount > max_quantity:
                            icon, name = SALVAGE_MATERIAL_NAMES.get(material_id, ("📦", material_id))
                            capacity_missing.append(
                                f"{icon} {name}: {owned}/{max_quantity} (needs room for +{amount})"
                            )
    
                    if capacity_missing:
                        await db.rollback()
                        return await ctx.send(
                            f"{ctx.author.mention} ❌ You don't have enough inventory space to salvage **{recipe['name']}** and receive all of its materials back.\n\n"
                            + "\n".join(capacity_missing)
                            + "\n\nFree up some material space and try again."
                        )
    
                    await db.execute(
                        "DELETE FROM inventory WHERE user_id = ? AND item_id = ? AND quantity <= 1",
                        (user_id, target_item),
                    )
    
                    for material_id, amount in recipe["ingredients"].items():
                        await db.execute(
                            "UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_id = ?",
                            (amount, user_id, material_id),
                        )
                        if not await self.inventory_row_exists(db, user_id, material_id):
                            await db.execute(
                                "INSERT INTO inventory (user_id, item_id, item_type, quantity) VALUES (?, ?, 'crafting_material', ?)",
                                (user_id, material_id, amount),
                            )
    
                    await db.commit()
    
                    material_lines = []
                    for material_id, amount in recipe["ingredients"].items():
                        icon, name = SALVAGE_MATERIAL_NAMES.get(material_id, ("📦", material_id))
                        material_lines.append(f"{icon} **{name} ×{amount}**")
    
                    embed = discord.Embed(
                        title="♻️ Upgrade Kit Salvaged!",
                        description=(
                            f"{ctx.author.mention}\n\n"
                            f"You salvaged **{recipe['name']}** and recovered its full crafting recipe.\n\n"
                            "🔧 **Materials Recovered:**\n"
                            + "\n".join(material_lines)
                        ),
                        color=discord.Color.from_rgb(0, 229, 255),
                    )
                    await ctx.send(embed=embed)
                    return
    
                if target_item == "all":
                    async with db.execute(
                        """
                        SELECT item_id, quantity
                        FROM inventory
                        WHERE user_id = ? AND item_type = 'space_junk' AND quantity > 0
                        """,
                        (user_id,)
                    ) as cursor:
                        junk_rows = await cursor.fetchall()
    
                    if not junk_rows:
                        await db.rollback()
                        return await ctx.send(f"{ctx.author.mention} 🎒 You don't have any Space Junk to salvage!")
    
                    totals = {}
                    item_count = 0
                    bonus_count = 0
    
                    for junk_id, quantity in junk_rows:
                        item_count += quantity
                        for _ in range(quantity):
                            material_id = self.roll_salvage_material(junk_id)
                            totals[material_id] = totals.get(material_id, 0) + 1
                            if bonus_chance > 0 and random.random() < bonus_chance:
                                bonus_material = self.roll_salvage_material(junk_id)
                                totals[bonus_material] = totals.get(bonus_material, 0) + 1
                                bonus_count += 1
    
                    await db.execute(
                        "DELETE FROM inventory WHERE user_id = ? AND item_type = 'space_junk'",
                        (user_id,)
                    )
    
                else:
                    async with db.execute(
                        """
                        SELECT quantity FROM inventory
                        WHERE user_id = ? AND item_id = ? AND item_type = 'space_junk'
                        """,
                        (user_id, target_item)
                    ) as cursor:
                        row = await cursor.fetchone()
    
                    if not row or (row[0] or 0) <= 0:
                        await db.rollback()
                        return await ctx.send(
                            f"{ctx.author.mention} ❌ You don't have **{ITEM_REGISTRY.get(target_item, {}).get('name', target_item)}** in your Space Junk inventory."
                        )
    
                    item_count = 1
                    bonus_count = 0
                    totals = {self.roll_salvage_material(target_item): 1}
                    if bonus_chance > 0 and random.random() < bonus_chance:
                        bonus_material = self.roll_salvage_material(target_item)
                        totals[bonus_material] = totals.get(bonus_material, 0) + 1
                        bonus_count = 1
    
                    quantity = row[0]
                    if quantity > 1:
                        await db.execute(
                            "UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_id = ? AND item_type = 'space_junk'",
                            (user_id, target_item)
                        )
                    else:
                        await db.execute(
                            "DELETE FROM inventory WHERE user_id = ? AND item_id = ? AND item_type = 'space_junk'",
                            (user_id, target_item)
                        )
    
                added_totals = {}
                overflow_stardust = 0
                for material_id, amount in totals.items():
                    added, overflow, overflow_value = await self.add_salvage_material(
                        db, user_id, material_id, amount
                    )
                    if added:
                        added_totals[material_id] = added
                    if overflow:
                        overflow_stardust += overflow_value
    
                if overflow_stardust:
                    await db.execute(
                        "UPDATE users SET stardust = COALESCE(stardust, 0) + ? WHERE user_id = ?",
                        (overflow_stardust, user_id)
                    )
    
                await db.commit()
    
            junk_name = "Space Junk" if target_item == "all" else ITEM_REGISTRY.get(target_item, {}).get("name", target_item)
            material_lines = []
            for material_id, amount in added_totals.items():
                icon, name = SALVAGE_MATERIAL_NAMES[material_id]
                material_lines.append(f"{icon} **{name} ×{amount}**")
    
            if not material_lines:
                material_lines.append("📦 Your material storage was full, so the salvage was converted to Stardust.")
    
            bonus_text = (
                f"\n✨ **Bonus materials:** +{bonus_count}"
                if bonus_count
                else ""
            )
            overflow_text = (
                f"\n📦 **Material Overflow:** +{overflow_stardust:,} Stardust"
                if overflow_stardust
                else ""
            )
            remaining_text = ""
            if target_item != "all":
                # We consumed one unit, so report the remaining amount from the pre-salvage quantity.
                remaining_text = f"\n📦 **Remaining:** {max(0, quantity - 1)}x"
    
            embed = discord.Embed(
                title="♻️ Salvage Complete!",
                description=(
                    f"{ctx.author.mention}\n\n"
                    f"You salvaged **{item_count}x {junk_name}**.\n\n"
                    "🔧 **Materials Recovered:**\n"
                    + "\n".join(material_lines)
                    + bonus_text
                    + overflow_text
                    + remaining_text
                ),
                color=discord.Color.from_rgb(0, 229, 255),
            )
            embed.set_footer(
                text=f"Salvage Rig Level {salvage_upgrade.get('level', 0)}/5 • Base salvage is guaranteed"
            )
            await ctx.send(embed=embed)

