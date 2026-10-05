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


class EconomySalvageAutocompleteMixin:
    get_db_path: Callable[[], str]
    
    async def salvage_item_autocomplete(self, interaction: discord.Interaction, current: str):
            """Show Space Junk the user currently owns and can salvage."""
            user_id = interaction.user.id
            current = current.lower().strip()
            from inventory import ITEM_REGISTRY
    
            async with aiosqlite.connect(self.get_db_path()) as db:
                async with db.execute(
                    """
                    SELECT item_id, quantity
                    FROM inventory
                    WHERE user_id = ? AND item_type = 'space_junk' AND quantity > 0
                    """,
                    (user_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
    
            choices = []
            if not current or "salvage all" in current:
                choices.append(app_commands.Choice(name="♻️ Salvage All Space Junk", value="all"))
    
            for item_id, quantity in rows:
                info = ITEM_REGISTRY.get(item_id)
                if not info:
                    continue
                if current and current not in info["name"].lower():
                    continue
                choices.append(
                    app_commands.Choice(
                        name=f"{info['emoji']} {info['name']} (x{quantity})",
                        value=item_id
                    )
                )
    
            # Upgrade kits can also be salvaged for their exact crafting recipe.
            from crafting import RECIPES
            upgrade_kit_ids = {
                recipe["result"]
                for recipe in RECIPES.values()
                if recipe["result"].startswith((
                    "reinforced_laser_parts_",
                    "drone_upgrade_kit_",
                    "salvage_rig_kit_",
                ))
                or recipe["result"] == "nanite_retrofit_kit"
            }
    
            async with aiosqlite.connect(self.get_db_path()) as db:
                placeholders = ", ".join("?" for _ in upgrade_kit_ids)
                async with db.execute(
                    f"""
                    SELECT item_id, quantity
                    FROM inventory
                    WHERE user_id = ?
                      AND item_id IN ({placeholders})
                      AND quantity > 0
                    """,
                    (user_id, *upgrade_kit_ids),
                ) as cursor:
                    kit_rows = await cursor.fetchall()
    
            for item_id, quantity in kit_rows:
                info = ITEM_REGISTRY.get(item_id)
                if not info:
                    continue
                if current and current not in info["name"].lower():
                    continue
                choices.append(
                    app_commands.Choice(
                        name=f"🧰 {info['name']} (x{quantity})",
                        value=item_id
                    )
                )
    
            choices.sort(key=lambda choice: choice.name.lower())
            return choices[:25]

