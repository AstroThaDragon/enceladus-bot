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

class EconomyShopCatalogMixin:
    get_db_path: Callable[[], str]
    JUNK_PRICES: dict[str, int]
    async def get_shop_sell_items(self, user_id, category):
            """Return owned sellable items for the interactive /shop sell UI."""
            async with aiosqlite.connect(self.get_db_path()) as db:
                async with db.execute(
                    """
                    SELECT item_id, quantity, item_type
                    FROM inventory
                    WHERE user_id = ? AND quantity > 0
                    ORDER BY item_id
                    """,
                    (user_id,),
                ) as cursor:
                    rows = await cursor.fetchall()
    
                async with db.execute(
                    "SELECT COALESCE(time_crystals, 0) FROM users WHERE user_id = ?",
                    (user_id,),
                ) as cursor:
                    time_crystal_row = await cursor.fetchone()
    
            time_crystal_quantity = time_crystal_row[0] if time_crystal_row else 0
    
            def is_collectible(item_id, info):
                # Location-based and Halloween collectibles all belong to the
                # Collectibles category. They must never be pulled into the
                # Halloween materials/supplies category just because they are
                # seasonal or location-specific.
                return (
                    item_id in LOCATION_BASED_COLLECTIBLES
                    or item_id in HALLOWEEN_COLLECTIBLE_IDS
                    or str(info.get("type", "")).lower() in {
                        "collectible", "location-based collectible"
                    }
                )
    
            def is_halloween_item(item_id, info, stored_type):
                item_type = str(info.get("type", ""))
                # Halloween is for seasonal sellables that are NOT collectibles:
                # materials/ingredients, Halloween space junk, candy/bags, and
                # other explicitly seasonal sellables such as the plasma cutter.
                if is_collectible(item_id, info):
                    return False
                return (
                    item_id in HALLOWEEN_SPACE_JUNK_IDS
                    or item_type == "Haunted Ingredient"
                    or bool(info.get("halloween_only"))
                    or item_id == "plasma_cutter"
                )
    
            def is_normal_collectible(item_id, info):
                return is_collectible(item_id, info)
    
            def is_space_junk(info, stored_type):
                return str(stored_type).lower() == "space_junk" or info.get("type") == "Space Junk"
    
            def is_sellable(item_id, info, stored_type):
                if not info:
                    return False
    
                # Permanent unlocks are never inventory sale items, even if a future
                # registry entry accidentally receives a sell_price.
                item_type = str(info.get("type", ""))
                if item_type in {"title", "background_voucher", "station_upgrade"}:
                    return False
    
                junk = is_space_junk(info, stored_type)
                if junk:
                    return item_id in self.JUNK_PRICES or get_halloween_sell_reward(item_id) is not None
    
                unit_price = int(info.get("sell_price", 0) or 0)
                if unit_price <= 0:
                    return False
    
                # Normal materials/collectibles are sellable by type. Upgrade
                # components are restricted to the actual craftable upgrade kits so
                # permanent station upgrades cannot leak into the sell UI.
                if item_type == "Upgrade Component":
                    return item_id in get_upgrade_kit_ids()
    
                return (
                    item_type in {
                        "Mineral", "Crafting Material", "Incubator Material", "Haunted Ingredient",
                        "Location-Based Collectible", "Collectible"
                    }
                    or item_id in SELLABLE_ITEM_IDS
                    or item_id == "astral_essence"
                )
    
            entries = []
    
            if category == "sell_all":
                for item_id, label in BULK_SELL_OPTIONS.items():
                    entries.append({
                        "id": item_id,
                        "name": label,
                        "description": "Open the confirmation screen for this bulk sale.",
                        "search": f"{item_id} {label}",
                        "info": {},
                        "owned": None,
                        "stored_type": None,
                    })
                return entries
    
            if category == "special" and time_crystal_quantity > 0:
                entries.append({
                    "id": "time_crystal",
                    "name": f"💎 Dilated Time Crystal",
                    "description": f"You own {time_crystal_quantity:,}.",
                    "search": "time_crystal dilated time crystal",
                    "info": ITEM_REGISTRY.get("time_crystal", {
                        "name": "💎 Dilated Time Crystal", "sell_price": 0
                    }),
                    "owned": time_crystal_quantity,
                    "stored_type": "special",
                })
    
            for item_id, owned_quantity, stored_type in rows:
                info = ITEM_REGISTRY.get(item_id)
                if not info:
                    continue
                if not is_sellable(item_id, info, stored_type):
                    continue
    
                junk = is_space_junk(info, stored_type)
                normal_collectible = is_normal_collectible(item_id, info)
                halloween = is_halloween_item(item_id, info, stored_type)
                halloween_collectible = normal_collectible
                item_type = str(info.get("type", ""))
    
                if category == "space_junk" and (
                    not junk or item_id in HALLOWEEN_SPACE_JUNK_IDS
                ):
                    continue
                if category == "collectibles" and not normal_collectible:
                    continue
                if category == "halloween" and not halloween:
                    continue
                if category == "materials" and (
                    item_type not in {"Mineral", "Crafting Material", "Incubator Material"}
                    or halloween_collectible
                    or item_id in HALLOWEEN_SPACE_JUNK_IDS
                ):
                    continue
                if category in SELL_ITEM_CATEGORY_IDS:
                    allowed_ids = SELL_ITEM_CATEGORY_IDS[category]
                    if category == "upgrade_kits":
                        allowed_ids = get_upgrade_kit_ids()
                    if item_id not in allowed_ids:
                        continue
    
                display_name = info.get("name", item_id)
                entries.append({
                    "id": item_id,
                    "name": display_name,
                    "description": f"You own {owned_quantity:,}.",
                    "search": f"{item_id} {display_name}",
                    "info": info,
                    "owned": owned_quantity,
                    "stored_type": stored_type,
                })
    
            entries.sort(key=lambda entry: entry["name"].lower())
            return entries

