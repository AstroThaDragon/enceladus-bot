import asyncio
import aiosqlite
import datetime
import json
import random
import re
import time
from datetime import datetime, timedelta, time as dt_time
from typing import Any, Optional, Protocol, cast

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


class EconomyBankMixin(commands.Cog):
    DEFAULT_VAULT_CAPACITY: int

    def get_db_path(self) -> str:
        raise NotImplementedError

    async def ensure_schema(self, db: Any) -> Any:
        raise NotImplementedError


    @commands.hybrid_command(
        name="bank",
        aliases=["bal"],
        description="View your current Stardust balance and vaulted Stardust."
    )
    async def bank(self, ctx: commands.Context):
            """Show available Stardust and protected vault balance."""
            user_id = ctx.author.id
            db_path = self.get_db_path()
    
            async with aiosqlite.connect(db_path) as db:
                await self.ensure_schema(db)
    
                await db.execute(
                    """
                    INSERT OR IGNORE INTO users
                        (user_id, stardust, vault_stardust)
                    VALUES (?, 0, 0)
                    """,
                    (user_id,)
                )
                await db.commit()
    
                async with db.execute(
                    """
                    SELECT
                        COALESCE(stardust, 0),
                        COALESCE(vault_stardust, 0),
                        COALESCE(vault_capacity, ?)
                    FROM users
                    WHERE user_id = ?
                    """,
                    (self.DEFAULT_VAULT_CAPACITY, user_id)
                ) as cursor:
                    row = await cursor.fetchone()
    
            stardust = row[0] if row else 0
            vault = row[1] if row else 0
            vault_capacity = row[2] if row else self.DEFAULT_VAULT_CAPACITY
            total = stardust + vault
    
            embed = discord.Embed(
                title=f"🔐 {ctx.author.display_name}'s Stardust Vault",
                description=(
                    f"Your vault contains **{vault:,} Stardust**.\n\n"
                    "Stardust stored here is protected from normal spending.\n"
                    "Use `/deposit` to store more or `/withdraw` to take it back out."
                ),
                color=discord.Color.from_rgb(0, 229, 255)
            )
    
            embed.add_field(
                name="💫 Available to Spend",
                value=f"{stardust:,} Stardust",
                inline=True
            )
    
            embed.add_field(
                name="🔐 Protected in Vault",
                value=f"{vault:,} / {vault_capacity:,} Stardust",
                inline=True
            )
    
            embed.add_field(
                name="📊 Total Owned",
                value=f"{total:,} Stardust",
                inline=False
            )
    
            embed.set_footer(text="Enceladus Station Economy")
    
            await ctx.send(embed=embed)

    @commands.hybrid_command(name="deposit", description="Deposit your Stardust into the bank vault for safe keeping.")
    @app_commands.describe(amount="How much Stardust to store in the vault")
    async def bank_deposit(self, ctx: commands.Context, amount: int):
            """Deposit available Stardust into the protected vault."""
            if amount <= 0:
                return await ctx.send("⚠️ The deposit amount must be greater than 0.")
    
            user_id = ctx.author.id
            db_path = self.get_db_path()
    
            async with aiosqlite.connect(db_path) as db:
                await self.ensure_schema(db)
    
                # Ensure user exists
                await db.execute(
                    "INSERT OR IGNORE INTO users (user_id, stardust, vault_stardust) VALUES (?, 0, 0)",
                    (user_id,)
                )
                await db.commit()
    
                # Query current balances and vault capacity (if stored in DB, otherwise use constant)
                async with db.execute(
                    "SELECT COALESCE(stardust, 0), COALESCE(vault_stardust, 0) FROM users WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
    
                stardust, vault = row if row else (0, 0)
                vault_capacity = self.DEFAULT_VAULT_CAPACITY
    
                if amount > stardust:
                    return await ctx.send(
                        f"💸 You only have **{stardust:,} Stardust** available to deposit."
                    )
    
                if vault + amount > vault_capacity:
                    remaining_space = max(0, vault_capacity - vault)
                    return await ctx.send(
                        f"🔐 Your vault can only hold **{vault_capacity:,} Stardust**. "
                        f"You can deposit **{remaining_space:,}** Stardust."
                    )
    
                # Perform deposit update
                await db.execute(
                    "UPDATE users SET stardust = stardust - ?, vault_stardust = vault_stardust + ? WHERE user_id = ?",
                    (amount, amount, user_id)
                )
                await db.commit()
    
            await ctx.send(
                f"{ctx.author.mention} 🔐 Deposited **{amount:,} Stardust** into your vault. "
                f"Your vault now holds **{vault + amount:,} Stardust**."
            )

    @commands.hybrid_command(name="withdraw", description="Withdraw Stardust from your bank vault to spend.")
    @app_commands.describe(amount="How much Stardust to withdraw from the vault")
    async def bank_withdraw(self, ctx: commands.Context, amount: int):
            """Withdraw Stardust from the protected vault."""
            if amount <= 0:
                return await ctx.send("⚠️ The withdrawal amount must be greater than 0.")
    
            user_id = ctx.author.id
            db_path = self.get_db_path()
    
            async with aiosqlite.connect(db_path) as db:
                await self.ensure_schema(db)
                await db.execute(
                    "INSERT OR IGNORE INTO users (user_id, stardust, vault_stardust) VALUES (?, 0, 0)",
                    (user_id,)
                )
                await db.commit()
    
                await db.execute("BEGIN IMMEDIATE")
                async with db.execute(
                    "SELECT COALESCE(stardust, 0), COALESCE(vault_stardust, 0) FROM users WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
    
                stardust, vault = row if row else (0, 0)
    
                if amount > vault:
                    await db.rollback()
                    return await ctx.send(
                        f"🔐 You only have **{vault:,} Stardust** stored in your vault."
                    )
    
                await db.execute(
                    "UPDATE users SET stardust = ?, vault_stardust = ? WHERE user_id = ?",
                    (stardust + amount, vault - amount, user_id)
                )
                await db.commit()
    
            await ctx.send(
                f"{ctx.author.mention} 💫 Withdrew **{amount:,} Stardust** from your vault. "
                f"You now have **{stardust + amount:,} Stardust** available to spend."
            )

