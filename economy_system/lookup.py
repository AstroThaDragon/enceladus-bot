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


class EconomyLookupMixin:
    async def item_category_autocomplete(
            self,
            interaction: discord.Interaction,
            current: str
        ):
            """Show the available item catalog categories."""
            categories = [
                ("❤️ Healing", "healing"),
                ("🛠️ Upgrades", "upgrades"),
                ("🎒 Consumables", "consumables"),
                ("🐾 Pet Items", "pet_items"),
                ("✨ Special", "special"),
                ("🗑️ Space Junk A-M", "junk_am"),
                ("🗑️ Space Junk N-Z", "junk_nz"),
                ("💎 Minerals", "minerals"),
                ("🏷️ Titles", "titles"),
                ("🖼️ Backgrounds", "backgrounds"),
                ("🎟️ Vouchers", "vouchers"),
                ("🪙 Currency", "currency"),
            ]
    
            current = current.lower().strip()
    
            choices = [
                app_commands.Choice(name=name, value=value)
                for name, value in categories
                if not current or current in name.lower()
            ]
    
            return choices[:25]

    async def item_autocomplete(
            self,
            interaction: discord.Interaction,
            current: str
        ):
            """Show items belonging to the selected catalog category."""
            from inventory import ITEM_REGISTRY
    
            category = interaction.namespace.category
            current = current.lower().strip()
    
            category_map = {
                "healing": {
                    "nanite_patch",
                    "medkit",
                    "revive",
                    "revive_kit",
                    "full_revive",
                },
    
                "upgrades": {
                    "fuel_stabilizer",
                    "station_rations",
                    "hazard_shield",
                    "lucky_scanner",
                    "ore_magnet",
                    "prototype_drill_bit",
                    "cosmic_insurance",
                    "fate_anchor",
                },
    
                "consumables": {
                    "laser_charge_cell",
                    "laser_power_cell",
                    "fuel_refill",
                    "drone_battery",
                    "drone_power_cell",
                    "drone_quantum_battery",
                    "quantum_battery",
                    "time_crystal",
                },
    
                "pet_items": {
                    "pet_snack",
                },
    
                "special": {
                    "astral_core",
                    "astral_essence",
                },
    
                "junk_am": {
                    "alien_artifact",
                    "alien_fossil",
                    "antique_compass",
                    "big_red_button",
                    "broken_clock",
                    "broken_laser",
                    "cosmic_banana",
                    "cosmic_coin",
                    "floating_plant",
                    "floppy_disk",
                    "golden_spatula",
                    "haunted_circuit",
                    "holo_poster",
                    "left_sock",
                    "lost_logbook",
                    "meteorite",
                    "moon_cheese",
                },
    
                "junk_nz": {
                    "parking_ticket",
                    "pet_rock",
                    "perplexing_painting",
                    "purring_lint",
                    "rubber_duck",
                    "rusty_gear",
                    "rusty_wrench",
                    "screaming_crystal",
                    "space_boot",
                    "space_pizza",
                    "space_pudding",
                    "space_taco",
                    "tape_deck",
                    "tangled_cables",
                    "tinted_visor",
                    "warp_mug",
                },
    
                "minerals": {
                    "titanium_chunk",
                },
    
                "titles": {
                    "title_outer_rim_wanderer",
                    "title_starborn",
                    "title_voidfarer",
                },
    
                "backgrounds": {
                    "neon_grid",
                    "deep_void",
                    "solaris_ring",
                },
    
                "vouchers": {
                    "neon_grid",
                    "deep_void",
                    "solaris_ring",
                },
    
                "currency": {
                    "arcade_token",
                },
            }
    
            allowed_items = category_map.get(category)
    
            if allowed_items is None:
                allowed_items = ITEM_REGISTRY.keys()
    
            choices = []
    
            for item_id in allowed_items:
                info = ITEM_REGISTRY.get(item_id)
                if not info:
                    continue
    
                display_name = info["name"]
    
                if current and current not in display_name.lower():
                    continue
    
                choices.append(
                    app_commands.Choice(
                        name=display_name,
                        value=item_id
                    )
                )
    
            choices.sort(key=lambda choice: choice.name.lower())
    
            return choices[:25]

    async def item_lookup(self, ctx: commands.Context, category: str, item: str):
            item_id = item.lower()
            from inventory import ITEM_REGISTRY
    
            if item_id not in ITEM_REGISTRY:
                return await ctx.send(
                    "❌ I couldn't find that item. Please choose an item from the dropdown."
                )
    
            info = ITEM_REGISTRY[item_id]
    
            embed = discord.Embed(
                title=f"{info['emoji']} {info['name']}",
                description=f"**Category:** {info['type']}\n**Description:** {info['desc']}",
                color=discord.Color.from_rgb(120, 140, 160)
            )
            embed.set_footer(text="Enceladus Station Catalog")
            await ctx.send(embed=embed)

