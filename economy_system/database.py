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


class EconomyDatabaseMixin:
    def rotation_date(self):
            return datetime.now(pytz.timezone("US/Eastern")).date().isoformat()

    def daily_rotation(self):
            """Return the same three distinct rotating offers for every user on a given day.
    
            The daily market is drawn exclusively from ROTATING_ITEMS. Permanent shop
            inventory is intentionally not part of this pool. The result is deterministic
            for the current Eastern-time date, so every user sees the same three offers
            throughout the day and the set changes at midnight Eastern time.
            """
            excluded_types = {"background_voucher", "title", "station_upgrade"}
            eligible_items = []
    
            for item_id, item in ROTATING_ITEMS.items():
                if item.get("halloween_only") and not halloween_is_active():
                    continue
                if item.get("type") in excluded_types:
                    continue
                eligible_items.append(item_id)
    
            if len(eligible_items) < 3:
                return eligible_items
    
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
            limit_info = SHOP_LIMITS.get(item_id)
    
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
            limit_info = SHOP_LIMITS.get(item_id)
    
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
    
            if "vault_stardust" not in existing_columns:
                await db.execute(
                    "ALTER TABLE users ADD COLUMN vault_stardust INTEGER DEFAULT 0"
                )
    
            if "vault_capacity" not in existing_columns:
                await db.execute(
                    f"ALTER TABLE users ADD COLUMN vault_capacity INTEGER DEFAULT {DEFAULT_VAULT_CAPACITY}"
                )
    
            if "incubator_slots" not in existing_columns:
                await db.execute(
                    "ALTER TABLE users ADD COLUMN incubator_slots INTEGER DEFAULT 1"
                )
    
            # Daily Stardust reward tracking.
            if "daily_streak" not in existing_columns:
                await db.execute(
                    "ALTER TABLE users ADD COLUMN daily_streak INTEGER DEFAULT 0"
                )
    
            if "last_daily" not in existing_columns:
                await db.execute(
                    "ALTER TABLE users ADD COLUMN last_daily TEXT DEFAULT ''"
                )
    
            if "salvage_upgrade" not in existing_columns:
                await db.execute(
                    "ALTER TABLE users ADD COLUMN salvage_upgrade INTEGER DEFAULT 0"
                )
    
            # Permanently unlocked profile backgrounds.
            # Vouchers are consumed on redemption, so this list is the source of truth
            # for whether a background has already been unlocked.
            if "unlocked_backgrounds" not in existing_columns:
                await db.execute(
                    "ALTER TABLE users ADD COLUMN unlocked_backgrounds TEXT DEFAULT '[\"default\"]'"
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
    
            # Daily/monthly one-shot pet effects (Void Merchant / Solar Phoenix).
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS pet_effect_usage (
                    user_id INTEGER NOT NULL,
                    effect_id TEXT NOT NULL,
                    period_key TEXT NOT NULL,
                    PRIMARY KEY (user_id, effect_id, period_key)
                )
                """
            )

