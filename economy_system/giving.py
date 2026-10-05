import asyncio
import aiosqlite
import datetime
import json
import random
import re
import time
from datetime import datetime, timedelta, time as dt_time
from typing import Any, Optional, cast

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

from .data import *


class EconomyGivingMixin:
    _give_locks: dict[int, asyncio.Lock]

    def get_db_path(self) -> str:
        raise NotImplementedError

    async def ensure_schema(self, db: aiosqlite.Connection) -> None:
        raise NotImplementedError
    
    async def give_item_autocomplete(
            self,
            interaction: discord.Interaction,
            current: str,
        ):
            """Show transferable items the giver currently owns."""
            current = (current or "").lower().strip()
            user_id = interaction.user.id
    
            async with aiosqlite.connect(self.get_db_path()) as db:
                async with db.execute(
                    """
                    SELECT item_id, quantity
                    FROM inventory
                    WHERE user_id = ? AND quantity > 0
                    ORDER BY item_id
                    """,
                    (user_id,),
                ) as cursor:
                    rows = await cursor.fetchall()
    
                async with db.execute(
                    "SELECT COALESCE(time_crystals, 0) FROM users WHERE user_id = ? LIMIT 1",
                    (user_id,),
                ) as cursor:
                    crystal_row = await cursor.fetchone()
    
            choices = []
    
            crystal_quantity = int(crystal_row[0] or 0) if crystal_row else 0
            if crystal_quantity > 0:
                crystal_name = "💎 Dilated Time Crystal"
                search_text = f"dilated time crystal time_crystal"
                if not current or current in search_text:
                    choices.append(
                        app_commands.Choice(
                            name=f"{crystal_name} (x{crystal_quantity})",
                            value="time_crystal",
                        )
                    )
            for item_id, quantity in rows:
                info = ITEM_REGISTRY.get(item_id)
                if not info or self._give_item_excluded(item_id, info):
                    continue
    
                display_name = info.get("name", item_id)
                search_text = f"{display_name} {item_id}".lower()
                if current and current not in search_text:
                    continue
    
                choices.append(
                    app_commands.Choice(
                        name=f"{info.get('emoji', '📦')} {display_name} (x{quantity})",
                        value=item_id,
                    )
                )
    
            return choices[:25]

    async def give_pet_autocomplete(
            self,
            interaction: discord.Interaction,
            current: str,
        ):
            """Show the giver's owned non-egg pets."""
            current = (current or "").lower().strip()
            user_id = interaction.user.id
    
            async with aiosqlite.connect(self.get_db_path()) as db:
                async with db.execute(
                    """
                    SELECT pet_id, pet_type, pet_stage, nickname, level, variant_id, fusion_level
                    FROM pets
                    WHERE user_id = ? AND COALESCE(pet_type, pet_stage) != 'egg'
                    ORDER BY pet_id
                    """,
                    (user_id,),
                ) as cursor:
                    rows = await cursor.fetchall()
    
            choices = []
            pet_counts = {}
    
            for pet_id, pet_type, pet_stage, nickname, level, variant_id, fusion_level in rows:
                pet_type_id = pet_type or pet_stage
                definition = get_pet_definition(pet_type_id, variant_id)
                if not definition:
                    continue
    
                pet_counts[pet_type_id] = pet_counts.get(pet_type_id, 0) + 1
                duplicate_number = pet_counts[pet_type_id]
                display_name = nickname or definition["name"]
                search_text = (
                    f"{display_name} {definition['name']} {pet_type_id} "
                    f"{pet_id} {duplicate_number} {level} {fusion_level}"
                ).lower()
    
                if current and current not in search_text:
                    continue
    
                choices.append(
                    app_commands.Choice(
                        name=(
                            f"{definition['emoji']} {display_name} "
                            f"• Lv. {level} • #{duplicate_number}"
                        ),
                        value=str(pet_id),
                    )
                )
    
            return choices[:25]

    def _give_item_excluded(self, item_id, info):
            """Return whether an inventory item is intentionally non-transferable."""
            item_type = str(info.get("type", "")).lower()
            name = str(info.get("name", "")).lower()
            item_id = str(item_id).lower()
    
            excluded_types = {
                "voucher",
                "title",
                "background",
                "collectible",
            }
    
            if item_type in excluded_types:
                return True
    
            # Upgrade components/kits and any future upgrade inventory entries.
            if "upgrade" in item_type or "upgrade" in item_id or "upgrade" in name:
                return True
    
            # Halloween Space Junk collectibles are registered as Space Junk rather
            # than as a separate Collectible type, so exclude their known IDs too.
            if item_id in HALLOWEEN_SPACE_JUNK_IDS:
                return True
    
            return False

    def _get_give_lock(self, user_id):
            return self._give_locks.setdefault(user_id, asyncio.Lock())

    async def give(
            self,
            ctx: commands.Context,
            member: discord.Member,
            pet: Optional[str] = None,
            item: Optional[str] = None,
            stardust: Optional[int] = None,
            quantity: int = 1,
        ):
            """Transfer Stardust, an owned pet, or a transferable inventory item to another member."""
            if member.id == ctx.author.id:
                return await ctx.send("❌ You cannot give something to yourself.")
    
            if member.bot:
                return await ctx.send("❌ You cannot give items or pets to bots.")
    
            selected_types = sum(value is not None for value in (pet, item, stardust))
            if selected_types > 1:
                return await ctx.send("❌ Choose **only one** of a pet, item, or Stardust to give.")
    
            if selected_types == 0:
                return await ctx.send("❌ Choose a **pet**, an **item**, or an amount of **Stardust** to give.")
    
            if stardust is not None and stardust < 1:
                return await ctx.send("❌ Stardust amount must be at least **1**.")
    
            if quantity < 1 or quantity > 99:
                return await ctx.send("❌ Quantity must be between **1 and 99**.")
    
            giver_id = ctx.author.id
            recipient_id = member.id
            lock_ids = sorted({giver_id, recipient_id})
            locks = [self._get_give_lock(user_id) for user_id in lock_ids]
    
            await ctx.defer()
    
            async with locks[0]:
                async with locks[1]:
                    async with aiosqlite.connect(self.get_db_path()) as db:
                        await self.ensure_schema(db)
                        await db.execute(
                            "INSERT OR IGNORE INTO users (user_id, stardust, vault_stardust) VALUES (?, 0, 0)",
                            (giver_id,),
                        )
                        await db.execute(
                            "INSERT OR IGNORE INTO users (user_id, stardust, vault_stardust) VALUES (?, 0, 0)",
                            (recipient_id,),
                        )
                        await db.commit()
    
                        await db.execute("BEGIN IMMEDIATE")
    
                        if stardust is not None:
                            async with db.execute(
                                "SELECT COALESCE(stardust, 0) FROM users WHERE user_id = ? LIMIT 1",
                                (giver_id,),
                            ) as cursor:
                                giver_stardust_row = await cursor.fetchone()
    
                            giver_stardust = int(giver_stardust_row[0] or 0) if giver_stardust_row else 0
                            if giver_stardust < stardust:
                                await db.rollback()
                                return await ctx.send(
                                    f"❌ You only have **{giver_stardust:,} Stardust**, but you tried to give **{stardust:,}**."
                                )
    
                            await db.execute(
                                "UPDATE users SET stardust = stardust - ? WHERE user_id = ?",
                                (stardust, giver_id),
                            )
                            await db.execute(
                                "UPDATE users SET stardust = stardust + ? WHERE user_id = ?",
                                (stardust, recipient_id),
                            )
                            await db.commit()
    
                            return await ctx.send(
                                f"{ctx.author.mention} 💫 gave {member.mention} "
                                f"**{stardust:,} Stardust**!"
                            )
    
                        if pet:
                            try:
                                pet_id = int(pet)
                            except (TypeError, ValueError):
                                await db.rollback()
                                return await ctx.send("❌ That pet selection is invalid.")
    
                            async with db.execute(
                                """
                                SELECT pet_id, pet_type, pet_stage, nickname, level, variant_id, fusion_level
                                FROM pets
                                WHERE user_id = ? AND pet_id = ?
                                  AND COALESCE(pet_type, pet_stage) != 'egg'
                                LIMIT 1
                                """,
                                (giver_id, pet_id),
                            ) as cursor:
                                pet_row = await cursor.fetchone()
    
                            if not pet_row:
                                await db.rollback()
                                return await ctx.send("❌ You do not own that pet.")
    
                            _, pet_type, pet_stage, nickname, level, variant_id, fusion_level = pet_row
                            pet_type_id = pet_type or pet_stage
                            definition = get_pet_definition(pet_type_id, variant_id)
                            if not definition:
                                await db.rollback()
                                return await ctx.send("❌ That pet can no longer be transferred because its definition is unavailable.")
    
                            # Haunted location pets are exclusive discoveries tied to
                            # their Haunted location. They remain visible in /give so
                            # players can select them, but they cannot be traded.
                            haunted_location = definition.get("haunted_location")
                            is_location_pet = bool(haunted_location) or str(pet_type_id).lower().startswith("haunted_")
                            if is_location_pet:
                                await db.rollback()
                                return await ctx.send(
                                    "🔒 **That pet is a Haunted Location Exclusive.**\n"
                                    "This companion was discovered in a specific Haunted location and "
                                    "cannot be traded or transferred to another member."
                                )
    
                            pet_name = nickname or definition["name"]
    
                            cursor = await db.execute(
                                """
                                UPDATE pets
                                SET user_id = ?, is_active = 0
                                WHERE user_id = ? AND pet_id = ?
                                  AND COALESCE(pet_type, pet_stage) != 'egg'
                                """,
                                (recipient_id, giver_id, pet_id),
                            )
    
                            if cursor.rowcount != 1:
                                await db.rollback()
                                return await ctx.send("❌ That pet could not be transferred. Please try again.")
    
                            await db.commit()
    
                            return await ctx.send(
                                f"{ctx.author.mention} 🎁 gave {member.mention} "
                                f"**{definition['emoji']} {pet_name}**!"
                            )
    
                        if item is None:
                            await db.rollback()
                            return await ctx.send("❌ Choose a **pet**, an **item**, or an amount of **Stardust** to give.")
    
                        item_id = item.lower().strip()
    
                        # Dilated Time Crystals live in users.time_crystals rather than
                        # the normal inventory table. Handle them separately so /give
                        # can transfer the actual crystal balance.
                        if item_id == "time_crystal":
                            async with db.execute(
                                "SELECT COALESCE(time_crystals, 0) FROM users WHERE user_id = ? LIMIT 1",
                                (giver_id,),
                            ) as cursor:
                                giver_crystal_row = await cursor.fetchone()
    
                            giver_crystals = int(giver_crystal_row[0] or 0) if giver_crystal_row else 0
                            if giver_crystals < quantity:
                                await db.rollback()
                                return await ctx.send(
                                    f"❌ You do not have **{quantity}x Dilated Time Crystal** to give."
                                )
    
                            async with db.execute(
                                "SELECT COALESCE(time_crystals, 0) FROM users WHERE user_id = ? LIMIT 1",
                                (recipient_id,),
                            ) as cursor:
                                recipient_crystal_row = await cursor.fetchone()
    
                            recipient_crystals = int(recipient_crystal_row[0] or 0) if recipient_crystal_row else 0
                            max_crystals = 4
                            if recipient_crystals + quantity > max_crystals:
                                available_space = max(0, max_crystals - recipient_crystals)
                                await db.rollback()
                                return await ctx.send(
                                    f"❌ {member.mention} can only hold **{available_space}x** more "
                                    f"**Dilated Time Crystals** (max **{max_crystals}x**)."
                                )
    
                            await db.execute(
                                "UPDATE users SET time_crystals = time_crystals - ? WHERE user_id = ?",
                                (quantity, giver_id),
                            )
                            await db.execute(
                                "UPDATE users SET time_crystals = time_crystals + ? WHERE user_id = ?",
                                (quantity, recipient_id),
                            )
                            await db.commit()
    
                            return await ctx.send(
                                f"{ctx.author.mention} 🎁 gave {member.mention} "
                                f"**{quantity}x 💎 Dilated Time Crystal**!"
                            )
    
                        info = ITEM_REGISTRY.get(item_id)
                        if not info or self._give_item_excluded(item_id, info):
                            await db.rollback()
                            return await ctx.send("❌ That item cannot be given to another member.")
    
                        async with db.execute(
                            """
                            SELECT quantity, item_type
                            FROM inventory
                            WHERE user_id = ? AND item_id = ?
                            LIMIT 1
                            """,
                            (giver_id, item_id),
                        ) as cursor:
                            giver_row = await cursor.fetchone()
    
                        if not giver_row or (giver_row[0] or 0) < quantity:
                            await db.rollback()
                            return await ctx.send(
                                f"❌ You do not have **{quantity}x {info['name']}** to give."
                            )
    
                        max_quantity = int(info.get("max_quantity", 10))
                        async with db.execute(
                            """
                            SELECT quantity
                            FROM inventory
                            WHERE user_id = ? AND item_id = ?
                            LIMIT 1
                            """,
                            (recipient_id, item_id),
                        ) as cursor:
                            recipient_row = await cursor.fetchone()
    
                        recipient_quantity = (recipient_row[0] or 0) if recipient_row else 0
                        if recipient_quantity + quantity > max_quantity:
                            available_space = max(0, max_quantity - recipient_quantity)
                            await db.rollback()
                            return await ctx.send(
                                f"❌ {member.mention} can only hold **{available_space}x** more "
                                f"**{info['name']}** (max **{max_quantity}x**)."
                            )
    
                        remaining = giver_row[0] - quantity
                        if remaining > 0:
                            await db.execute(
                                """
                                UPDATE inventory
                                SET quantity = ?
                                WHERE user_id = ? AND item_id = ?
                                """,
                                (remaining, giver_id, item_id),
                            )
                        else:
                            await db.execute(
                                "DELETE FROM inventory WHERE user_id = ? AND item_id = ?",
                                (giver_id, item_id),
                            )
    
                        if recipient_row:
                            await db.execute(
                                """
                                UPDATE inventory
                                SET quantity = quantity + ?
                                WHERE user_id = ? AND item_id = ?
                                """,
                                (quantity, recipient_id, item_id),
                            )
                        else:
                            await db.execute(
                                """
                                INSERT INTO inventory (user_id, item_id, item_type, quantity)
                                VALUES (?, ?, ?, ?)
                                """,
                                (recipient_id, item_id, giver_row[1] or info.get("type", "Item"), quantity),
                            )
    
                        await db.commit()
    
                        return await ctx.send(
                            f"{ctx.author.mention} 🎁 gave {member.mention} "
                            f"**{quantity}x {info.get('emoji', '📦')} {info['name']}**!"
                        )

