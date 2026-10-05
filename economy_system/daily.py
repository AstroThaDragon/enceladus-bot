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


class _EconomyDailyHost(Protocol):
    bot: Any

    def get_db_path(self) -> str:
        ...

    async def ensure_schema(self, db: Any) -> Any:
        ...

    midnight_hp_regeneration: Any

HP_REGEN_TIME = dt_time(
    hour=0,
    minute=0,
    tzinfo=pytz.timezone("US/Eastern"),
)

class EconomyDailyMixin:
    @tasks.loop(time=HP_REGEN_TIME)
    async def midnight_hp_regeneration(self: _EconomyDailyHost):
            """Restore 50 HP to every user at midnight Eastern Time."""
            db_path = self.get_db_path()
    
            async with aiosqlite.connect(db_path) as db:
                await self.ensure_schema(db)
                await db.execute(
                    """
                    UPDATE users
                    SET hp = CASE
                        WHEN COALESCE(hp, 100) <= 0 THEN 50
                        ELSE MIN(100, COALESCE(hp, 100) + 50)
                    END,
                    knocked_out_until = CASE
                        WHEN COALESCE(hp, 100) <= 0 THEN ''
                        ELSE knocked_out_until
                    END
                    """
                )
                await db.commit()

    @midnight_hp_regeneration.before_loop
    async def before_midnight_hp_regeneration(self: _EconomyDailyHost):
            await self.bot.wait_until_ready()

    @midnight_hp_regeneration.error
    async def midnight_hp_regeneration_error(self: _EconomyDailyHost, error):
            await log_task_error(
                self.bot,
                "Economy.midnight_hp_regeneration",
                error,
            )

    def cog_load(self):
            if not self.midnight_hp_regeneration.is_running():
                self.midnight_hp_regeneration.start()

    def cog_unload(self):
            self.midnight_hp_regeneration.cancel()

    async def daily(self: _EconomyDailyHost, ctx: commands.Context):
            """Claim the daily Stardust reward and build a consecutive-day streak."""
            user_id = ctx.author.id
            db_path = self.get_db_path()
            eastern = pytz.timezone("US/Eastern")
            today = datetime.now(eastern).date()
            today_str = today.isoformat()
            yesterday_str = (today - timedelta(days=1)).isoformat()
    
            async with aiosqlite.connect(db_path) as db:
                await self.ensure_schema(db)
    
                await db.execute(
                    """
                    INSERT OR IGNORE INTO users
                        (user_id, stardust, vault_stardust, daily_streak, last_daily)
                    VALUES (?, 0, 0, 0, '')
                    """,
                    (user_id,)
                )
                await db.commit()
    
                # Lock the row before checking/updating the claim so two nearly
                # simultaneous interactions cannot award the daily twice.
                await db.execute("BEGIN IMMEDIATE")
    
                async with db.execute(
                    """
                    SELECT COALESCE(stardust, 0), COALESCE(daily_streak, 0),
                        COALESCE(last_daily, '')
                    FROM users
                    WHERE user_id = ?
                    """,
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
    
                stardust, streak, last_daily = row if row else (0, 0, "")
    
                from pets import get_active_pet_effects
                pet_effects = await get_active_pet_effects(db, user_id)
    
                # Already claimed today.
                if last_daily == today_str:
                    await db.rollback()
    
                    daily_rewards = [500, 600, 700, 800, 900, 1000, 1150]
                    reward = daily_rewards[min(max(1, streak), len(daily_rewards)) - 1]
    
                    return await ctx.send(
                        f"{ctx.author.mention} 📅 **Daily already claimed!**\n"
                        f"You claimed **{reward:,} Stardust** today.\n"
                        f"🔥 Current streak: **{streak} day{'s' if streak != 1 else ''}**.\n"
                        "Come back tomorrow to keep your streak going!"
                    )
    
                # Determine whether the previous streak was broken.
                streak_was_reset = bool(
                    last_daily and last_daily != yesterday_str
                )
    
                # Solar Phoenix can automatically rescue one missed daily streak
                # once per calendar month at passive level 5. The rescue happens
                # before today's increment, so the player keeps the old streak.
                streak_rescued = False
                if (
                    streak_was_reset
                    and streak > 0
                    and pet_effects.get("streak_rescue")
                ):
                    month_key = today.strftime("%Y-%m")
                    async with db.execute(
                        "SELECT 1 FROM pet_effect_usage WHERE user_id = ? AND effect_id = ? AND period_key = ?",
                        (user_id, "solar_phoenix_streak_rescue", month_key),
                    ) as cursor:
                        rescue_used = await cursor.fetchone()
    
                    if not rescue_used:
                        await db.execute(
                            "INSERT INTO pet_effect_usage (user_id, effect_id, period_key) VALUES (?, ?, ?)",
                            (user_id, "solar_phoenix_streak_rescue", month_key),
                        )
                        streak_rescued = True
    
                # Continue the streak if yesterday was claimed, or if Solar Phoenix
                # rescued the missed day.
                if last_daily == yesterday_str or streak_rescued:
                    new_streak = max(1, streak) + 1
                else:
                    new_streak = 1
    
                # Use the displayed 1–7 day reward ladder. Streaks beyond day 7
                # continue at the day-7 reward until the ladder is expanded.
                daily_rewards = [500, 600, 700, 800, 900, 1000, 1150]
                reward = daily_rewards[min(new_streak, len(daily_rewards)) - 1]
    
                daily_bonus = float(pet_effects.get("daily_bonus", 0.0))
                reward = int(reward * (1 + daily_bonus))
    
                doubled = False
                double_chance = float(pet_effects.get("daily_double", 0.0))
                if double_chance and random.random() < double_chance:
                    reward *= 2
                    doubled = True
    
                new_stardust = stardust + reward
    
                await db.execute(
                    """
                    UPDATE users
                    SET stardust = ?, daily_streak = ?, last_daily = ?
                    WHERE user_id = ?
                    """,
                    (new_stardust, new_streak, today_str, user_id)
                )
                await db.commit()
    
            # Build the 1–7 day streak ladder.
            # We can expand this later when the economy gets larger.
            streak_rows = []
            rewards = [500, 600, 700, 800, 900, 1000, 1150]
    
            for day, day_reward in enumerate(rewards, start=1):
                mark = "✅" if new_streak >= day else "❌"
                label = f"{day} day" if day == 1 else f"{day} days"
    
                streak_rows.append(
                    f"{label:<7} {mark} **{day_reward:,} Stardust**"
                )
    
            reset_note = ""
            if streak_rescued:
                reset_note = (
                    "\n\n☀️ **Solar Phoenix rescued your daily streak!** "
                    "Your monthly streak rescue has been used."
                )
            elif streak_was_reset:
                reset_note = (
                    "\n\n⚠️ **Your daily streak was reset** because you missed a day. "
                    "You're starting a new streak today!"
                )
            if doubled:
                reset_note += "\n✨ **Solar Phoenix doubled today's payout!**"
    
            embed = discord.Embed(
                title="📅 Daily Stardust",
                description=(
                    "Claim your daily reward and build your streak!\n\n"
                    + "\n".join(streak_rows)
                    + f"\n\n🔥 **Current Streak:** "
                    f"{new_streak} day{'s' if new_streak != 1 else ''}"
                    + f"\n💫 **Today's Reward:** {reward:,} Stardust"
                    + f"\n💰 **Available Stardust:** {new_stardust:,}"
                    + reset_note
                ),
                color=discord.Color.from_rgb(0, 229, 255)
            )
    
            embed.set_footer(
                text="Come back tomorrow to keep your streak going!"
            )
    
            await ctx.send(
                content=ctx.author.mention,
                embed=embed
            )

    async def claim_legacy_bonus(self: _EconomyDailyHost, ctx: commands.Context):
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
    
            joined_at = ctx.author.joined_at if isinstance(ctx.author, discord.Member) else None
    
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
                f"{ctx.author.mention} 🎉 **Legacy Veteran Bonus Claimed!**\n"
                f"Thanks for being a server veteran! You received "
                f"✨ **{legacy_bonus:,} Stardust** as a thank-you for being "
                f"here before the **Frontier** update."
            )

    async def on_message(self: _EconomyDailyHost, message: discord.Message):
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

