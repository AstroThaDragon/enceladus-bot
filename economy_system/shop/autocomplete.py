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
from .catalog import BULK_SELL_OPTIONS


class EconomyShopAutocompleteMixin:
    daily_rotation: Callable[[], list[str]]
    get_db_path: Callable[[], str]
    SHOP_ITEMS: dict
    ROTATING_ITEMS: dict
    JUNK_PRICES: dict[str, int]
    
    async def shop_buy_autocomplete(
            self,
            interaction: discord.Interaction,
            current: str
        ):
            """Show shop items filtered by the selected buy category."""
            current = (current or "").lower().strip()
            category = getattr(interaction.namespace, "category", None)
    
            # Hybrid-command autocomplete can expose the raw command payload instead
            # of a populated namespace in some clients. Fall back to the option data.
            if not category and interaction.data:
                for option in interaction.data.get("options", []):
                    if option.get("name") == "category":
                        category = option.get("value")
                        break
    
            category = str(category or "healing")
    
            item_ids = list(SHOP_BUY_CATEGORY_ITEMS.get(category, []))
            if category == "daily":
                item_ids = list(self.daily_rotation())
    
            autocomplete_emojis = {
                "nanite_patch": "🩹", "medkit": "🧰", "revive": "⚕️", "full_revive": "⚕️",
                "laser_charge_cell": "🔋", "laser_power_cell": "⚡", "fuel_refill": "⚛️",
                "drone_battery": "🔋", "drone_power_cell": "⚡", "drone_quantum_battery": "⚛️",
                "pet_snack": "🍪", "time_crystal": "💎", "astral_essence": "✨", "quantum_coil": "🌀", "astral_lens": "🔭", "mutation_catalyst": "🧬", "analysis_module": "🔬",
                "neon_grid": "🌆", "deep_void": "🌌", "solaris_ring": "💫",
                "fuel_stabilizer": "🛢️", "hazard_shield": "🛡️", "lucky_scanner": "📡",
                "prototype_drill_bit": "⚙️",
            }
    
            choices = []
            seen = set()
            for item_id in item_ids:
                if item_id in seen:
                    continue
                info = self.SHOP_ITEMS.get(item_id) or self.ROTATING_ITEMS.get(item_id)
                if not info:
                    continue
                name = info.get("name", item_id)
                if name.startswith("<:") or name.startswith("<a:"):
                    closing = name.find(">")
                    if closing != -1:
                        name = name[closing + 1:].lstrip()
                display = f"{autocomplete_emojis.get(item_id, '📦')} {name}"
                if current and current not in display.lower() and current not in item_id.lower():
                    continue
                choices.append(app_commands.Choice(name=display[:100], value=item_id))
                seen.add(item_id)
    
            return choices[:25]

    async def shop_sell_autocomplete(
            self,
            interaction: discord.Interaction,
            current: str
        ):
            """Show owned sellable items filtered by the selected sell category."""
            user_id = interaction.user.id
            current = (current or "").lower().strip()
            # Read the category from the raw interaction payload first. Discord's
            # autocomplete namespace can lag behind what the user just changed,
            # especially on mobile. The raw option payload is the authoritative
            # value for the current autocomplete request.
            category = None
            if interaction.data:
                for option in interaction.data.get("options", []):
                    if option.get("name") == "category":
                        category = option.get("value")
                        break
    
            # Fall back to the namespace only when the payload did not include the
            # category at all. Never default to a Sell All category: when the user
            # clears the category, the item picker should clear too rather than
            # showing stale Sell All choices.
            if category is None:
                category = getattr(interaction.namespace, "category", None)
    
            if not category:
                return []
            category = str(category)
    
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
                return (
                    item_id in LOCATION_BASED_COLLECTIBLES
                    or item_id in HALLOWEEN_COLLECTIBLE_IDS
                    or str(info.get("type", "")).lower() in {
                        "collectible", "location-based collectible"
                    }
                )
    
            def is_halloween_collectible(item_id):
                return is_collectible(item_id, ITEM_REGISTRY.get(item_id, {}))
    
            def is_halloween_item(item_id, info, stored_type):
                if is_collectible(item_id, info):
                    return False
                item_type = str(info.get("type", ""))
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
    
            def display_choice(item_id, quantity, info):
                raw_emoji = str(info.get("emoji", ""))
                if raw_emoji.startswith("<:") or raw_emoji.startswith("<a:"):
                    raw_emoji = "📦"
                emoji = raw_emoji or ("🎃" if is_halloween_item(item_id, info, info.get("type")) else "📦")
                return f"{emoji} {info.get('name', item_id)} (x{quantity})"
    
            choices = []
    
            # The Sell All category always exposes every bulk action. Whether the
            # user currently owns matching items is checked when the option is used.
            # This keeps the command's category/options stable instead of making
            # choices appear and disappear based on inventory state.
            if category == "sell_all":
                bulk = [
                    app_commands.Choice(name=BULK_SELL_OPTIONS["all_junk"], value="all_junk"),
                    app_commands.Choice(name=BULK_SELL_OPTIONS["all_materials"], value="all_materials"),
                    app_commands.Choice(name=BULK_SELL_OPTIONS["all_halloween"], value="all_halloween"),
                ]
                for choice in bulk:
                    if not current or current in choice.name.lower():
                        choices.append(choice)
                return choices[:25]
    
            if category == "special" and time_crystal_quantity > 0:
                crystal_display = f"💎 Dilated Time Crystal (x{time_crystal_quantity})"
                if not current or current in crystal_display.lower() or "time_crystal" in current:
                    choices.append(app_commands.Choice(name=crystal_display[:100], value="time_crystal"))
    
            if category in {"space_junk", "collectibles", "halloween", "materials", *SELL_ITEM_CATEGORY_IDS.keys()}:
                for item_id, owned_quantity, stored_type in rows:
                    info = ITEM_REGISTRY.get(item_id)
                    if not info:
                        continue
                    if not is_sellable(item_id, info, stored_type):
                        continue
    
                    junk = is_space_junk(info, stored_type)
                    normal_collectible = is_normal_collectible(item_id, info)
                    halloween = is_halloween_item(item_id, info, stored_type)
                    halloween_collectible = is_halloween_collectible(item_id)
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
    
                    display = display_choice(item_id, owned_quantity, info)
                    search_text = f"{display} {item_id}".lower()
                    if current and current not in search_text:
                        continue
                    choices.append(app_commands.Choice(name=display[:100], value=item_id))
    
            choices.sort(key=lambda choice: choice.name.lower())
            return choices[:25]

    async def shop_item_autocomplete(
            self,
            interaction: discord.Interaction,
            current: str,
        ):
            """Compatibility router for older command registrations."""
            options = interaction.data.get("options", []) if interaction.data else []
            action = str(next((o.get("value") for o in options if o.get("name") == "action"), "buy"))
            if action == "sell":
                return await self.shop_sell_autocomplete(interaction, current)
            return await self.shop_buy_autocomplete(interaction, current)

