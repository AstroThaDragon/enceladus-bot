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
            """Return the same three daily offers for every user on a given day.

            Two offers are drawn from eligible regular/rotating shop inventory, while
            exactly one offer is always a defensive weapon. Permanent shop items receive
            the Daily Offer discount in the buying/UI layers; rotating-only items and
            defensive weapons keep their normal listed price.

            The result is deterministic for the current Eastern-time date, so every user
            sees the same offers throughout the day and the set changes at midnight
            Eastern time. Defensive weapons are selected from a stable date-based cycle,
            so the same weapon cannot appear on consecutive days.
            """
            rotation_date = datetime.now(pytz.timezone("US/Eastern")).date()
            date_key = rotation_date.isoformat()

            excluded_types = {"background_voucher", "title", "station_upgrade"}
            # These are listed under the Upgrades buy category but are temporary
            # consumables and are intentionally allowed in the Daily Offers pool.
            temporary_upgrade_consumables = {
                "fuel_stabilizer",
                "hazard_shield",
                "lucky_scanner",
                "prototype_drill_bit",
            }
            excluded_upgrade_ids = (
                set(SHOP_BUY_CATEGORY_ITEMS.get("upgrades", ()))
                - temporary_upgrade_consumables
            )

            # Regular shop inventory: consumables, healing items, recharge items,
            # pet items, and special purchasable items are eligible. Actual station
            # upgrades, tickets, vouchers, and titles are not.
            regular_pool = []
            for item_id, item in SHOP_ITEMS.items():
                if item.get("halloween_only") and not halloween_is_active():
                    continue
                if item.get("type") in excluded_types:
                    continue
                if item_id in excluded_upgrade_ids:
                    continue
                if item_id == "lottery_ticket":
                    continue
                regular_pool.append(item_id)

            # Existing rotating-only utilities remain eligible. Defensive weapons are
            # selected separately so the daily shop always contains exactly one weapon.
            rotating_pool = []
            for item_id, item in ROTATING_ITEMS.items():
                if item.get("halloween_only") and not halloween_is_active():
                    continue
                if item.get("type") in excluded_types:
                    continue
                if item.get("type") == "defense_weapon":
                    continue
                rotating_pool.append(item_id)

            offer_pool = sorted(set(regular_pool + rotating_pool))

            # Use one stable global weapon order and advance one position per day.
            # Inactive seasonal weapons are skipped, which also prevents a repeat when
            # the Halloween weapon enters or leaves the active pool.
            all_weapon_ids = sorted(
                item_id
                for item_id, item in ROTATING_ITEMS.items()
                if item.get("type") == "defense_weapon"
            )
            active_weapon_ids = [
                item_id
                for item_id in all_weapon_ids
                if not (
                    ROTATING_ITEMS[item_id].get("halloween_only")
                    and not halloween_is_active()
                )
            ]

            generator = random.Random(f"enceladus-rotation-{date_key}")

            weapon_id = None
            if active_weapon_ids:
                if all_weapon_ids:
                    start_index = rotation_date.toordinal() % len(all_weapon_ids)
                    for offset in range(len(all_weapon_ids)):
                        candidate = all_weapon_ids[
                            (start_index + offset) % len(all_weapon_ids)
                        ]
                        if candidate in active_weapon_ids:
                            weapon_id = candidate
                            break

            regular_offers = (
                generator.sample(offer_pool, k=2)
                if len(offer_pool) >= 2
                else offer_pool[:]
            )

            if weapon_id is not None and weapon_id not in regular_offers:
                return regular_offers + [weapon_id]

            return regular_offers

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

