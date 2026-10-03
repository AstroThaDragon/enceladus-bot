from emojis import EMOJIS
import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import aiosqlite
import json
import random
import re
from typing import Any, Optional
import datetime
import time
from datetime import datetime, timedelta, time as dt_time
import pytz
from seasonal_updates.halloween.halloween import is_active as halloween_is_active
from seasonal_updates.halloween.halloween import HALLOWEEN_SPACE_JUNK, get_sell_reward as get_halloween_sell_reward
from seasonal_updates.halloween.halloween import get_collectibles as get_halloween_collectibles
from inventory import ITEM_REGISTRY
from collectibles import LOCATION_BASED_COLLECTIBLES

HALLOWEEN_COLLECTIBLE_IDS = {
    item_id for item_id, *_ in get_halloween_collectibles()
}

from pets.core import get_pet_definition
from error_handler import log_task_error

HALLOWEEN_SPACE_JUNK_IDS = {
    item_id for item_id, *_ in HALLOWEEN_SPACE_JUNK
}


# Space Junk salvage pools. Each junk item always yields exactly one base
# material at Level 0. Higher Salvage Rig levels add a chance for one extra
# material from the same pool. Weights within each pool are normalized by
# random.choices, so they do not need to add to exactly 1.
SALVAGE_POOLS = {
    "electronics": [("wiring", 50), ("circuit_board", 30), ("copper_ore", 20)],
    "mechanical": [("scrap_metal", 45), ("nuts_bolts", 35), ("iron_ore", 20)],
    "structural": [("scrap_metal", 45), ("iron_ore", 35), ("aluminum_ore", 20)],
    "mineral": [("iron_ore", 50), ("copper_ore", 30), ("aluminum_ore", 18), ("titanium_chunk", 2)],
    "miscellaneous": [("scrap_metal", 50), ("glue", 30), ("nuts_bolts", 20)],
    "valuable": [("circuit_board", 35), ("wiring", 30), ("copper_ore", 25), ("aluminum_ore", 10)],
}

SALVAGE_CATEGORIES = {
    # Electronics / powered equipment
    "floppy_disk": "electronics",
    "tape_deck": "electronics",
    "alien_artifact": "electronics",
    "tangled_cables": "electronics",
    "broken_laser": "electronics",
    "haunted_circuit": "electronics",
    "big_red_button": "electronics",
    "broken_clock": "electronics",

    # Mechanical hardware / tools
    "rusty_gear": "mechanical",
    "space_boot": "mechanical",
    "tinted_visor": "mechanical",
    "rusty_wrench": "mechanical",
    "warp_mug": "mechanical",

    # Structural / mineral-heavy wreckage
    "meteorite": "mineral",
    "pet_rock": "mineral",
    "alien_fossil": "mineral",

    # Valuable / specialized oddities
    "cosmic_coin": "valuable",
    "screaming_crystal": "valuable",
    "golden_spatula": "valuable",
    "antique_compass": "valuable",
    "perplexing_painting": "valuable",

    # Everything else is mostly generic salvageable material.
    "space_pizza": "miscellaneous",
    "rubber_duck": "miscellaneous",
    "holo_poster": "miscellaneous",
    "lost_logbook": "miscellaneous",
    "left_sock": "miscellaneous",
    "space_pudding": "miscellaneous",
    "moon_cheese": "miscellaneous",
    "parking_ticket": "miscellaneous",
    "floating_plant": "miscellaneous",
    "purring_lint": "miscellaneous",
    "space_taco": "miscellaneous",
    "cosmic_banana": "miscellaneous",
}

SALVAGE_MATERIAL_NAMES = {
    "iron_ore": (EMOJIS.get("iron_ore", "⛏️"), "Iron Ore"),
    "copper_ore": (EMOJIS.get("copper_ore", "🟠"), "Copper Ore"),
    "titanium_chunk": (EMOJIS.get("titanium_chunk", "⛏️"), "Titanium Ore Chunk"),
    "aluminum_ore": (EMOJIS.get("aluminum_ore", "⬜"), "Aluminum Ore"),
    "circuit_board": (EMOJIS.get("circuit_board", "🟩"), "Circuit Board"),
    "glue": (EMOJIS.get("glue", "🧴"), "Industrial Glue"),
    "scrap_metal": (EMOJIS.get("scrap_metal", "🔩"), "Scrap Metal"),
    "nuts_bolts": (EMOJIS.get("nuts_bolts", "🔧"), "Nuts & Bolts"),
    "wiring": (EMOJIS.get("wiring", "🧵"), "Wiring"),
}

SALVAGE_OVERFLOW_VALUES = {
    "iron_ore": 3, "copper_ore": 5, "titanium_chunk": 15, "aluminum_ore": 4,
    "circuit_board": 20, "glue": 6, "scrap_metal": 3, "nuts_bolts": 4, "wiring": 5,
}


# Normal station materials that are safe to include in the bulk
# "Sell All Ores & Materials" option. Haunted/Halloween materials are
# intentionally excluded so seasonal crafting stock is never bulk-sold.
NORMAL_SELL_ALL_MATERIAL_IDS = {
    "titanium_chunk",
    "iron_ore",
    "copper_ore",
    "aluminum_ore",
    "circuit_board",
    "glue",
    "scrap_metal",
    "nuts_bolts",
    "wiring",
}

# Inventory items that can be sold individually through /shop.
# Their Stardust values are defined by ITEM_REGISTRY in inventory.py.
SELLABLE_ITEM_IDS = {'cosmic_insurance', 'drone_battery', 'drone_power_cell', 'drone_quantum_battery', 'fate_anchor', 'fuel_refill', 'fuel_stabilizer', 'full_revive', 'hazard_shield', 'heavy_wrench', 'laser_charge_cell', 'laser_power_cell', 'lucky_scanner', 'makeshift_medkit', 'medkit', 'nanite_patch', 'ore_magnet', 'plasma_cutter', 'prototype_drill_bit', 'revive', 'revive_kit', 'station_rations', 'stick', 'stop_sign', 'wooden_shield', 'wooden_spoon', 'wooden_sword',
                     }


SHOP_BUY_CATEGORY_ITEMS = {
    "healing": ["nanite_patch", "medkit", "revive", "full_revive"],
    "recharge": [
        "laser_charge_cell", "laser_power_cell", "fuel_refill",
        "drone_battery", "drone_power_cell", "drone_quantum_battery",
    ],
    "upgrades": [
        "incubator_2", "incubator_3", "vault_expansion",
        "fuel_stabilizer", "hazard_shield", "lucky_scanner", "prototype_drill_bit",
    ],
    "pet_items": ["pet_snack"],
    "special": ["time_crystal", "astral_essence"],
    "lottery": ["lottery_ticket"],
    "backgrounds": ["neon_grid", "deep_void", "solaris_ring"],
}

SHOP_BUY_CATEGORY_CHOICES = [
    ("❤️ Healing", "healing"),
    ("🔋 Recharge", "recharge"),
    ("🛠️ Upgrades", "upgrades"),
    ("🐾 Pet Items", "pet_items"),
    ("✨ Special", "special"),
    ("🎟️ Lottery", "lottery"),
    ("🖼️ Backgrounds", "backgrounds"),
]

SHOP_SELL_CATEGORY_CHOICES = [
    ("🧹 Sell All", "sell_all"),
    ("🗑️ Space Junk", "space_junk"),
    ("🔧 Ores & Materials", "materials"),
    ("❤️ Healing", "healing"),
    ("🧪 Consumables", "consumables"),
    ("🛠️ Upgrade Kits", "upgrade_kits"),
    ("🛡️ Defense Weapons", "defense_weapons"),
    ("🎃 Collectibles", "collectibles"),
    ("👻 Halloween", "halloween"),
    ("✨ Special Items", "special"),
]

# Individually sellable inventory is grouped by what the item actually does,
# rather than dumping uncategorized items into a generic "Other" bucket.
SELL_ITEM_CATEGORY_IDS = {
    "healing": {
        "nanite_patch", "medkit", "revive", "revive_kit", "full_revive",
        "makeshift_medkit", "station_rations",
    },
    "consumables": {
        "laser_charge_cell", "laser_power_cell", "fuel_refill",
        "drone_battery", "drone_power_cell", "drone_quantum_battery",
        # Temporary utility items are consumables, not upgrade kits.
        "fuel_stabilizer", "hazard_shield", "lucky_scanner", "ore_magnet",
        "prototype_drill_bit", "cosmic_insurance", "fate_anchor",
    },
    "upgrade_kits": set(),  # Populated dynamically from crafting recipes below.
    "defense_weapons": {
        "stop_sign", "stick", "wooden_sword", "wooden_shield",
        "wooden_spoon", "heavy_wrench", "plasma_cutter",
    },
    "special": {
        "time_crystal",
    },
}

def get_upgrade_kit_ids():
    """Return the actual craftable upgrade-kit item IDs."""
    try:
        from crafting import RECIPES
    except ImportError:
        return set()

    return {
        recipe["result"]
        for recipe in RECIPES.values()
        if recipe.get("result", "").startswith((
            "reinforced_laser_parts_",
            "drone_upgrade_kit_",
            "salvage_rig_kit_",
        ))
        or recipe.get("result") == "nanite_retrofit_kit"
    }


BULK_SELL_OPTIONS = {
    "all_junk": "🗑️ Sell All Space Junk",
    "all_materials": "🔧 Sell All Ores & Materials",
    "all_halloween": "🎃 Sell All Halloween Collectibles",
}


class ShopInteractionContext:
    """Small adapter that lets the existing buy/sell methods reply to an interaction."""

    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.author = interaction.user

    async def defer(self):
        if not self.interaction.response.is_done():
            await self.interaction.response.defer()

    async def send(self, *args, **kwargs):
        return await self.interaction.followup.send(*args, wait=True, **kwargs)


SHOP_CATEGORY_INFO = {
    "healing": ("❤️", "Healing", "Medical supplies and revival items."),
    "recharge": ("🔋", "Recharge", "Mining laser and scavenging drone power."),
    "upgrades": ("🛠️", "Upgrades", "Permanent equipment and station expansions."),
    "pet_items": ("🐾", "Pet Items", "Items for your station companion."),
    "special": ("✨", "Special", "Rare and unusual station items."),
    "lottery": ("🎟️", "Lottery", "Monthly Stardust lottery tickets."),
    "backgrounds": ("🖼️", "Backgrounds", "Profile background vouchers."),
    "__search__": ("🔎", "Search Results", "Search across the available shop items."),
    "__rotating__": ("🔄️", "Daily Offers", "Today's rotating station offers."),
    "sell_all": ("🧹", "Sell All", "Bulk-sale actions for eligible inventory."),
    "space_junk": ("🗑️", "Space Junk", "Sell normal space junk for Stardust."),
    "materials": ("🔧", "Ores & Materials", "Sell ores and normal crafting materials."),
    "collectibles": ("🎃", "Collectibles", "Sell discovered collectible items."),
    "halloween": ("👻", "Halloween", "Sell eligible seasonal items."),
    "healing": ("❤️", "Healing", "Medical supplies and revival items."),
    "consumables": ("🧪", "Consumables", "Usable supplies for exploration and station equipment."),
    "upgrade_kits": ("🛠️", "Upgrade Kits", "Actual crafted kits used for permanent upgrades."),
    "defense_weapons": ("🛡️", "Defense Weapons", "Items that can help protect you from scavenging hazards."),
    "special": ("✨", "Special Items", "Rare or unusual individually sellable items."),
}


class ShopCategorySelect(discord.ui.Select):
    def __init__(self, shop_view):
        self.shop_view = shop_view
        if shop_view.mode == "buy":
            categories = SHOP_BUY_CATEGORY_CHOICES
        else:
            categories = SHOP_SELL_CATEGORY_CHOICES

        options = []
        for name, value in categories:
            emoji, label, description = SHOP_CATEGORY_INFO.get(
                value, (None, name, "Shop category")
            )
            options.append(
                discord.SelectOption(
                    label=label,
                    emoji=emoji,
                    value=value,
                    description=description[:100],
                )
            )

        super().__init__(
            placeholder="📂 Choose a category...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        if not await self.shop_view.check_owner(interaction):
            return
        self.shop_view.category = self.values[0]
        self.shop_view.page = 0
        self.shop_view.search_query = ""
        self.shop_view.selected_item = None
        self.shop_view.quantity = 1
        await self.shop_view.show_item_picker(interaction)


class ShopItemButton(discord.ui.Button):
    """Select one of the items currently showcased on the embed."""

    def __init__(self, shop_view, entry, row=0):
        self.shop_view = shop_view
        self.item_id = entry["id"]
        label = shop_view._strip_emoji_name(entry.get("name", self.item_id))
        # Keep the button readable on mobile while the full item name remains
        # visible in the embed above it.
        super().__init__(
            label=label[:80],
            style=discord.ButtonStyle.secondary,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction):
        if not await self.shop_view.check_owner(interaction):
            return

        self.shop_view.selected_item = self.item_id
        self.shop_view.quantity = 1
        self.shop_view.quantity_input = "1"

        if self.shop_view.mode == "sell" and self.item_id in BULK_SELL_OPTIONS:
            return await self.shop_view.show_bulk_sale(interaction)

        if self.shop_view.mode == "buy" and self.item_id == "lottery_ticket":
            return await interaction.response.send_modal(ShopLotteryModal(self.shop_view))

        await self.shop_view.show_quantity(interaction)


class ShopSearchModal(discord.ui.Modal, title="🔎 Search Shop Items"):
    search = discord.ui.TextInput(
        label="Search",
        placeholder="Type an item name or keyword...",
        required=False,
        max_length=100,
    )

    def __init__(self, shop_view):
        super().__init__()
        self.shop_view = shop_view

    async def on_submit(self, interaction: discord.Interaction):
        if not await self.shop_view.check_owner(interaction):
            return
        self.shop_view.search_query = str(self.search.value or "").strip().lower()
        self.shop_view.page = 0
        if self.shop_view.category is None:
            self.shop_view.category = "__search__"
        await self.shop_view.show_item_picker(interaction)


class ShopLotteryModal(discord.ui.Modal, title="🎟️ Lottery Ticket"):
    number1 = discord.ui.TextInput(label="Number 1", placeholder="1–99", required=True, max_length=2)
    number2 = discord.ui.TextInput(label="Number 2", placeholder="1–99", required=True, max_length=2)
    number3 = discord.ui.TextInput(label="Number 3", placeholder="1–99", required=True, max_length=2)
    number4 = discord.ui.TextInput(label="Number 4", placeholder="1–99", required=True, max_length=2)
    number5 = discord.ui.TextInput(label="Number 5", placeholder="1–99", required=True, max_length=2)

    def __init__(self, shop_view):
        super().__init__()
        self.shop_view = shop_view

    async def on_submit(self, interaction: discord.Interaction):
        if not await self.shop_view.check_owner(interaction):
            return

        lottery = self.shop_view.cog.bot.get_cog("Lottery")
        if lottery is None:
            return await interaction.response.send_message(
                "❌ The lottery system is currently unavailable.",
                ephemeral=True,
            )

        try:
            raw_numbers = (
                int(str(self.number1.value).strip()),
                int(str(self.number2.value).strip()),
                int(str(self.number3.value).strip()),
                int(str(self.number4.value).strip()),
                int(str(self.number5.value).strip()),
            )
        except ValueError:
            return await interaction.response.send_message(
                "❌ All five lottery numbers must be whole numbers from **1 to 99**.",
                ephemeral=True,
            )

        numbers = lottery.normalize_numbers(raw_numbers)
        if numbers is None:
            return await interaction.response.send_message(
                "❌ Your ticket must contain **5 different whole numbers from 1 to 99**.",
                ephemeral=True,
            )

        success, message = await lottery.purchase_ticket(interaction.user.id, numbers)
        await interaction.response.send_message(message, ephemeral=True)


class ShopQuantityModal(discord.ui.Modal, title="🔢 Custom Quantity"):
    quantity = discord.ui.TextInput(
        label="Quantity",
        placeholder="Enter a number...",
        required=True,
        min_length=1,
        max_length=4,
    )

    def __init__(self, shop_view):
        super().__init__()
        self.shop_view = shop_view

    async def on_submit(self, interaction: discord.Interaction):
        if not await self.shop_view.check_owner(interaction):
            return

        raw = str(self.quantity.value).strip()
        try:
            value = int(raw)
        except ValueError:
            return await interaction.response.send_message(
                "❌ Quantity must be a whole number.",
                ephemeral=True,
            )

        if value < 1 or value > 99:
            return await interaction.response.send_message(
                "❌ Quantity must be between **1 and 99**.",
                ephemeral=True,
            )

        if self.shop_view.mode == "sell":
            owned = self.shop_view.get_selected_owned_quantity()
            if owned is not None and value > owned:
                return await interaction.response.send_message(
                    f"❌ You only own **{owned:,}** of that item.",
                    ephemeral=True,
                )

        self.shop_view.quantity = value
        self.shop_view.quantity_input = str(value)
        await self.shop_view.show_quantity(interaction)


class ShopQuantityButton(discord.ui.Button):
    def __init__(self, shop_view, label, value, emoji=None, style=discord.ButtonStyle.secondary):
        super().__init__(label=label, emoji=emoji, style=style, row=0)
        self.shop_view = shop_view
        self.value = value

    async def callback(self, interaction: discord.Interaction):
        if not await self.shop_view.check_owner(interaction):
            return

        if self.value == "custom":
            return await interaction.response.send_modal(ShopQuantityModal(self.shop_view))

        if self.value == "max":
            owned = self.shop_view.get_selected_owned_quantity()
            if not owned:
                return await interaction.response.send_message(
                    "❌ You don't own any of that item.", ephemeral=True
                )
            self.shop_view.quantity = owned
            self.shop_view.quantity_input = "max"
        else:
            value = int(self.value)
            if self.shop_view.mode == "sell":
                owned = self.shop_view.get_selected_owned_quantity()
                if owned is not None and value > owned:
                    return await interaction.response.send_message(
                        f"❌ You only own **{owned:,}** of that item.", ephemeral=True
                    )
            self.shop_view.quantity = value
            self.shop_view.quantity_input = str(value)

        await self.shop_view.show_quantity(interaction)


class ShopTransactionView(discord.ui.View):
    """Reusable Category → Item → Quantity → Confirm shop flow."""

    # Five items fit cleanly across one Discord button row. The embed above
    # them contains the full item details, while the buttons simply select the
    # item being acted on.
    PAGE_SIZE = 5

    def __init__(self, cog, user_id, mode):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        self.mode = mode
        self.category = None
        self.page = 0
        self.search_query = ""
        self.selected_item = None
        self.quantity = 1
        self.quantity_input = "1"
        self.item_entries = []
        self.finished = False
        self.message = None
        self._build_category_view()

    async def check_owner(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "⚠️ This shop menu belongs to the person who opened it.",
                ephemeral=True,
            )
            return False
        return True

    def _build_category_view(self):
        self.clear_items()
        self.add_item(ShopCategorySelect(self))

        search = discord.ui.Button(
            label="Search",
            emoji="🔎",
            style=discord.ButtonStyle.primary,
            row=1,
        )

        async def search_callback(interaction):
            if not await self.check_owner(interaction):
                return
            await interaction.response.send_modal(ShopSearchModal(self))

        search.callback = search_callback
        self.add_item(search)

    def _category_title(self):
        emoji, label, _ = SHOP_CATEGORY_INFO.get(
            self.category, ("📂", "Shop", "")
        )
        return f"{emoji} {label}"

    def _get_buy_items(self):
        if self.category == "__rotating__":
            return list(self.cog.daily_rotation())
        if self.category == "__search__":
            item_ids = []
            for category, category_items in SHOP_BUY_CATEGORY_ITEMS.items():
                if category == "daily":
                    continue
                item_ids.extend(category_items)
            return list(dict.fromkeys(item_ids))
        return list(SHOP_BUY_CATEGORY_ITEMS.get(self.category, []))

    async def _get_sell_items(self):
        if self.category == "__search__":
            entries = []
            for category in SHOP_SELL_CATEGORY_CHOICES:
                entries.extend(await self.cog.get_shop_sell_items(self.user_id, category[1]))
            seen = set()
            unique = []
            for entry in entries:
                if entry["id"] in seen:
                    continue
                seen.add(entry["id"])
                unique.append(entry)
            return unique
        return await self.cog.get_shop_sell_items(self.user_id, self.category)

    def _filter_entries(self, entries):
        query = self.search_query
        if not query:
            return entries
        return [
            entry for entry in entries
            if query in str(entry["search"]).lower()
        ]

    async def _get_entries(self):
        if self.mode == "buy":
            entries = []
            for item_id in self._get_buy_items():
                if item_id == "lottery_ticket":
                    lottery = self.cog.bot.get_cog("Lottery")
                    ticket_cost = int(getattr(lottery, "TICKET_COST", 100)) if lottery else 100
                    info = {
                        "name": "Lottery Ticket",
                        "cost": ticket_cost,
                        "type": "lottery",
                        "desc": (
                            "Choose 5 different numbers from 1–99. "
                            "Use the ticket button to enter your numbers. "
                            "Maximum 25 active tickets per cycle."
                        ),
                    }
                else:
                    info = self.cog.SHOP_ITEMS.get(item_id) or self.cog.ROTATING_ITEMS.get(item_id)
                if not info:
                    continue
                entries.append({
                    "id": item_id,
                    "name": info.get("name", item_id),
                    "description": info.get("desc", ""),
                    "search": f"{item_id} {info.get('name', '')}",
                    "info": info,
                    "owned": None,
                })
        else:
            entries = await self._get_sell_items()
        return self._filter_entries(entries)

    def _entry_for_item(self, item_id):
        for entry in self.item_entries:
            if entry["id"] == item_id:
                return entry
        return None

    def get_selected_owned_quantity(self):
        entry = self._entry_for_item(self.selected_item)
        return entry.get("owned") if entry else None

    @staticmethod
    def _strip_emoji_name(name):
        # Discord custom emoji markup is not reliably rendered in button labels.
        # Keep normal Unicode emoji, but strip <:name:id> / <a:name:id> markup.
        cleaned = re.sub(r"<a?:[A-Za-z0-9_~]+:\d+>\s*", "", str(name or ""))
        return cleaned.strip() or "Item"

    def _build_category_embed(self):
        title = "🛒 Buy Items" if self.mode == "buy" else "🛒 Sell Items"

        if self.mode == "buy":
            categories = SHOP_BUY_CATEGORY_CHOICES
            footer = "Choose a category to browse the station shop."
        else:
            categories = SHOP_SELL_CATEGORY_CHOICES
            footer = "Choose a category to browse your sellable inventory."

        category_lines = []
        for name, value in categories:
            emoji, label, description = SHOP_CATEGORY_INFO.get(
                value, ("📂", name, "Shop category")
            )
            category_lines.append(f"{emoji} **{label}** — {description}")

        description = (
            "Choose a category to continue.\n\n"
            "**Available Categories**\n"
            + "\n".join(category_lines)
        )

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.from_rgb(0, 229, 255),
        )
        embed.set_footer(text=footer)
        return embed

    async def show_category(self, interaction):
        self.category = None
        self.page = 0
        self.search_query = ""
        self.selected_item = None
        self.quantity = 1
        self.quantity_input = "1"
        self._build_category_view()

        # A category return can happen after other async shop work. Defer the
        # component interaction immediately so Discord does not time out while
        # the response is being edited.
        if not interaction.response.is_done():
            await interaction.response.defer()

        await interaction.edit_original_response(
            embed=self._build_category_embed(),
            view=self,
        )

    async def show_item_picker(self, interaction):
        self.clear_items()
        entries = await self._get_entries()
        self.item_entries = entries

        total_pages = max(1, (len(entries) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.page = min(max(self.page, 0), total_pages - 1)
        start = self.page * self.PAGE_SIZE
        page_entries = entries[start:start + self.PAGE_SIZE]

        title = "🛒 Buy Items" if self.mode == "buy" else "🛒 Sell Items"
        page_text = f"Page {self.page + 1}/{total_pages}"
        if self.search_query:
            page_text += f" • Search: `{self.search_query}`"

        description = (
            f"Choose an item to {'buy' if self.mode == 'buy' else 'sell'}.\n\n"
            f"**{page_text}**\n"
            f"{len(entries):,} item{'s' if len(entries) != 1 else ''} available."
        )

        embed = discord.Embed(
            title=f"{title} — {self._category_title()}",
            description=description,
            color=discord.Color.from_rgb(0, 229, 255),
        )

        if page_entries:
            for entry in page_entries:
                info = entry.get("info") or {}
                item_name = str(entry.get("name", entry.get("id", "Item")))

                if self.mode == "buy":
                    price = int(info.get("cost", 0) or 0)
                    if entry["id"] in self.cog.SHOP_ITEMS and entry["id"] in self.cog.daily_rotation():
                        daily_price = int(price * 0.85)
                        detail = (
                            f"💰 ~~{price:,}~~ → **{daily_price:,} Stardust**\n"
                            "🏷️ **15% Daily Discount**"
                        )
                    else:
                        detail = f"💰 **{price:,} Stardust**"
                    if info.get("desc"):
                        detail += f"\n📖 {info['desc']}"
                else:
                    owned = int(entry.get("owned", 0) or 0)
                    stored_type = entry.get("stored_type") or info.get("type")
                    if str(stored_type).lower() == "space_junk" or info.get("type") == "Space Junk":
                        payout, candy = self.cog.get_junk_sell_reward(entry["id"])
                        price_line = f"💰 **{int(payout):,} Stardust each**"
                        if candy:
                            price_line += f" + 🍬 **{int(candy)} Candy**"
                    else:
                        payout = int(info.get("sell_price", 0) or 0)
                        price_line = f"💰 **{payout:,} Stardust each**"
                    detail = f"📦 You own: **{owned:,}**\n{price_line}"

                embed.add_field(
                    name=item_name,
                    value=detail,
                    inline=False,
                )

            # The buttons correspond exactly to the items displayed above.
            # Full names/details stay in the embed so long names never need to
            # be crammed into a select-menu popup.
            for entry in page_entries:
                self.add_item(ShopItemButton(self, entry, row=0))
        else:
            embed.description += "\n\n❌ No items match that search."

        previous = discord.ui.Button(
            label="Previous",
            emoji="◀️",
            style=discord.ButtonStyle.secondary,
            disabled=self.page <= 0,
            row=1,
        )
        next_button = discord.ui.Button(
            label="Next",
            emoji="▶️",
            style=discord.ButtonStyle.secondary,
            disabled=self.page >= total_pages - 1,
            row=1,
        )
        search = discord.ui.Button(
            label="Search",
            emoji="🔎",
            style=discord.ButtonStyle.primary,
            row=2,
        )
        categories = discord.ui.Button(
            label="Categories",
            emoji="↩️",
            style=discord.ButtonStyle.secondary,
            row=2,
        )

        async def previous_callback(i):
            if not await self.check_owner(i):
                return
            self.page -= 1
            await self.show_item_picker(i)

        async def next_callback(i):
            if not await self.check_owner(i):
                return
            self.page += 1
            await self.show_item_picker(i)

        async def search_callback(i):
            if not await self.check_owner(i):
                return
            await i.response.send_modal(ShopSearchModal(self))

        async def categories_callback(i):
            if not await self.check_owner(i):
                return
            await self.show_category(i)

        previous.callback = previous_callback
        next_button.callback = next_callback
        search.callback = search_callback
        categories.callback = categories_callback
        self.add_item(previous)
        self.add_item(next_button)
        self.add_item(search)
        self.add_item(categories)

        embed.set_footer(
            text="Items are shown above • Use the item buttons to select one, or Search to filter."
        )

        await interaction.response.edit_message(embed=embed, view=self)

    def _get_selected_info(self):
        entry = self._entry_for_item(self.selected_item)
        if entry:
            return entry["info"]
        return self.cog.SHOP_ITEMS.get(self.selected_item) or self.cog.ROTATING_ITEMS.get(self.selected_item) or ITEM_REGISTRY.get(self.selected_item)

    def _buy_unit_price(self):
        info = self._get_selected_info() or {}
        price = int(info.get("cost", 0) or 0)
        if self.selected_item in self.cog.SHOP_ITEMS and self.selected_item in self.cog.daily_rotation():
            price = int(price * 0.85)
        return price

    def _sell_unit_price(self):
        info = self._get_selected_info() or {}
        entry = self._entry_for_item(self.selected_item)
        stored_type = entry.get("stored_type") if entry else info.get("type")
        if str(stored_type).lower() == "space_junk" or info.get("type") == "Space Junk":
            payout, _ = self.cog.get_junk_sell_reward(self.selected_item)
            return int(payout)
        return int(info.get("sell_price", 0) or 0)

    async def show_quantity(self, interaction):
        self.clear_items()
        info = self._get_selected_info() or {}
        entry = self._entry_for_item(self.selected_item) or {}
        name = info.get("name", self.selected_item)

        if self.mode == "buy":
            unit_price = self._buy_unit_price()
            total = unit_price * self.quantity
            lines = [
                f"💰 Price: **{unit_price:,} Stardust each**",
                f"🧮 Quantity: **{self.quantity:,}**",
                f"💸 Total: **{total:,} Stardust**",
            ]
            if self.selected_item in self.cog.SHOP_ITEMS and self.selected_item in self.cog.daily_rotation():
                lines.insert(1, "🏷️ **15% Daily Discount**")
        else:
            unit_price = self._sell_unit_price()
            owned = entry.get("owned", 0)
            total = unit_price * self.quantity
            lines = [
                f"📦 You own: **{owned:,}**",
                f"💰 Sell price: **{unit_price:,} Stardust each**",
                f"🧮 Quantity: **{self.quantity:,}**",
                f"💸 Total: **{total:,} Stardust**",
            ]

        embed = discord.Embed(
            title=f"{name}",
            description="\n".join(lines) + "\n\nChoose a quantity, then confirm the transaction.",
            color=discord.Color.from_rgb(0, 229, 255),
        )
        embed.set_footer(text="Custom lets you enter a quantity up to 99.")

        presets = [("1", "1", "1️⃣"), ("10", "10", "🔟")]
        if self.mode == "buy":
            # "2️⃣5️⃣" is two emoji sequences combined, which Discord rejects
            # as a single button emoji (error 50035 / Invalid emoji).
            presets.append(("25", "25", None))
        else:
            presets.append(("Max", "max", "📦"))
        for label, value, emoji in presets:
            self.add_item(ShopQuantityButton(self, label, value, emoji=emoji))
        self.add_item(ShopQuantityButton(self, "Custom", "custom", emoji="🔢"))

        back = discord.ui.Button(label="Back", emoji="◀️", style=discord.ButtonStyle.secondary, row=1)
        confirm = discord.ui.Button(label="Confirm", emoji="✅", style=discord.ButtonStyle.success, row=1)

        async def back_callback(i):
            if not await self.check_owner(i):
                return
            await self.show_item_picker(i)

        async def confirm_callback(i):
            if not await self.check_owner(i):
                return
            await self.confirm_transaction(i)

        back.callback = back_callback
        confirm.callback = confirm_callback
        self.add_item(back)
        self.add_item(confirm)
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_bulk_sale(self, interaction):
        rows, total_stardust, total_candy, item_count, lines = await self.cog._bulk_sale_preview(
            self.user_id, self.selected_item
        )
        if not rows:
            return await interaction.response.edit_message(
                content="❌ **Nothing to sell!** You don't currently have any items covered by this Sell All option.",
                embed=None,
                view=self,
            )

        preview = "\n".join(lines[:12])
        if len(lines) > 12:
            preview += f"\n…and {len(lines) - 12} more."
        candy_preview = f"\n🍬 **Halloween Candy:** +{total_candy}" if total_candy else ""
        embed = discord.Embed(
            title="⚠️ Confirm Bulk Sale",
            description=(
                f"You are about to sell **{item_count} items** for approximately "
                f"✨ **{total_stardust:,} Stardust**.{candy_preview}\n\n"
                f"**Items included:**\n{preview}\n\n"
                "📚 **Collection Note:** Collectibles are permanently recorded in your collection once discovered. "
                "Selling the physical items does **not** remove them from your collection.\n\n"
                "This cannot be undone. Choose **Yes, Sell All** or **Cancel**."
            ),
            color=discord.Color.orange(),
        )
        view = SellAllConfirmView(self.cog, self.user_id, self.selected_item)
        await interaction.response.edit_message(embed=embed, content=None, view=view)

    async def confirm_transaction(self, interaction):
        if self.finished:
            return await interaction.response.send_message(
                "⚠️ This transaction has already been submitted.", ephemeral=True
            )
        if not self.selected_item:
            return await interaction.response.send_message("❌ No item selected.", ephemeral=True)

        self.finished = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        # The existing transaction methods contain the full purchase/sale
        # accounting logic. The adapter lets them respond to this interaction
        # without duplicating that logic in the UI.
        ctx = ShopInteractionContext(interaction)
        if self.mode == "buy":
            await self.cog.buy(ctx, self.selected_item, self.quantity)
        else:
            await self.cog.sell(ctx, self.selected_item, self.quantity_input)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True


class ShopListCategorySelect(discord.ui.Select):
    def __init__(self, shop_view):
        self.shop_view = shop_view
        options = [
            discord.SelectOption(label="Healing", emoji="❤️", value="healing"),
            discord.SelectOption(label="Recharge", emoji="🔋", value="recharge"),
            discord.SelectOption(label="Upgrades", emoji="🛠️", value="upgrades"),
            discord.SelectOption(label="Pet Items", emoji="🐾", value="pet_items"),
            discord.SelectOption(label="Special", emoji="✨", value="special"),
            discord.SelectOption(label="Lottery", emoji="🎟️", value="lottery"),
            discord.SelectOption(label="Backgrounds", emoji="🖼️", value="backgrounds"),
        ]
        super().__init__(placeholder="📂 Select a shop category...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.shop_view.user_id:
            return await interaction.response.send_message(
                "⚠️ This shop menu belongs to the person who opened it.", ephemeral=True
            )
        category = self.values[0]
        await interaction.response.edit_message(
            embed=self.shop_view.build_embed(category), view=self.shop_view
        )


class RotatingShopBuyButton(discord.ui.Button):
    """Buy button for one of today's rotating offers."""

    def __init__(self, cog, user_id, item_id, item, row=1):
        self.cog = cog
        self.user_id = user_id
        self.item_id = item_id
        self.item = item

        # Button labels cannot safely contain Discord custom-emoji markup.
        # Reuse the shop's normal name cleaner so custom emojis are removed
        # while ordinary Unicode emoji remain valid.
        label = ShopTransactionView._strip_emoji_name(
            item.get("name", item_id)
        )
        label = f"Buy {label}"

        super().__init__(
            label=label[:80],
            style=discord.ButtonStyle.success,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "⚠️ This rotating shop belongs to the person who opened it.",
                ephemeral=True,
            )

        # Reuse the normal transaction flow so rotating purchases get the same
        # quantity selection, purchase-limit checks, balance checks, and
        # confirmation behavior as /shop buy.
        view = ShopTransactionView(self.cog, self.user_id, "buy")
        view.category = "__rotating__"
        view.selected_item = self.item_id
        view.quantity = 1
        view.quantity_input = "1"
        view.item_entries = [{
            "id": self.item_id,
            "name": self.item.get("name", self.item_id),
            "description": self.item.get("desc", ""),
            "search": f"{self.item_id} {self.item.get('name', '')}",
            "info": self.item,
            "owned": None,
        }]
        await view.show_quantity(interaction)


class ShopView(discord.ui.View):
    """Legacy /shop catalog view plus the interactive daily rotating shop."""

    def __init__(self, cog, user_id, category=None):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        self.category = category

        if category == "daily":
            self._add_daily_buttons()
        else:
            self.add_item(ShopListCategorySelect(self))

    def _add_daily_buttons(self):
        for item_id in self.cog.daily_rotation():
            item = self.cog.ROTATING_ITEMS.get(item_id)
            if not item:
                continue
            self.add_item(
                RotatingShopBuyButton(
                    self.cog,
                    self.user_id,
                    item_id,
                    item,
                    row=1,
                )
            )

    def build_embed(self, category):
        # Preserve the existing /shop list catalog behavior while the new
        # transaction UI handles /shop buy and /shop sell.
        cog = self.cog
        embed = discord.Embed(
            title="🛒 Enceladus Station Trading Post",
            color=discord.Color.from_rgb(0, 229, 255)
        )
        if category == "daily":
            embed.description = (
                "🔄 **Daily Rotating Offers**\n"
                f"Today's station market — **{cog.rotation_date()}**\n\n"
                "These offers rotate at midnight Eastern time."
            )
            for item_id in cog.daily_rotation():
                item = cog.SHOP_ITEMS.get(item_id) or cog.ROTATING_ITEMS.get(item_id)
                if not item:
                    continue
                is_permanent = item_id in cog.SHOP_ITEMS
                daily_cost = int(item["cost"] * 0.85) if is_permanent else item["cost"]
                price_text = (
                    f"💰 ~~{item['cost']:,}~~ → **{daily_cost:,} Stardust** 🔥\n🏷️ **15% Daily Discount**"
                    if is_permanent else f"💰 Price: **{daily_cost:,} Stardust**"
                )
                limit_text = cog.shop_limit_text(item_id)
                embed.add_field(
                    name=item["name"],
                    value=f"{price_text}\n📖 {item['desc']}\n📦 **Purchase Limit:** {limit_text.lstrip(' • Limit: ') if limit_text else 'None'}",
                    inline=False,
                )
            return embed

        if category == "lottery":
            embed.description = (
                "🎟️ **Monthly Lottery**\n"
                "Choose your own five numbers from 1–99 and enter the monthly drawing."
            )
            embed.add_field(
                name="🎟️ Lottery Ticket",
                value=(
                    "💰 Price: **100 Stardust** per ticket\n"
                    "🔢 Choose **5 different numbers from 1–99**\n"
                    "📦 Maximum: **25 active tickets** per user per cycle\n"
                    "🏆 Top prize: **10,000 Stardust** for matching all 5\n\n"
                    "Use `/lottery buy` to choose your numbers and purchase a ticket.\n\n"
                    "NOTE: Lotteries are only available when a staff member opens one. Wait until it's announced!"
                ),
                inline=False,
            )
            embed.set_footer(text="Use /lottery to view the current drawing and your tickets.")
            return embed

        item_ids = list(SHOP_BUY_CATEGORY_ITEMS.get(category, []))
        descriptions = {
            "healing": "❤️ **Medical Supplies**\nKeep yourself alive out there, explorer.",
            "recharge": "🔋 **Power & Recharge Supplies**\nRestore charges to your mining laser or scavenging drone.",
            "upgrades": "🛠️ **Station Upgrades**\nPermanent equipment and station expansions.",
            "pet_items": "🐾 **Pet Supplies**\nBecause even station companions need snacks.",
            "special": "✨ **Special Items**\nUnusual technology with unusual consequences.",
            "backgrounds": "🖼️ **Profile Backgrounds**\nCustomize the look of your station profile.",
        }
        embed.description = descriptions.get(category, "Choose a shop category.")
        for item_id in item_ids:
            item = cog.SHOP_ITEMS.get(item_id) or cog.ROTATING_ITEMS.get(item_id)
            if not item:
                continue
            limit_text = cog.shop_limit_text(item_id)
            embed.add_field(
                name=item["name"],
                value=f"💰 Price: **{item['cost']:,} Stardust**\n📖 {item['desc']}\n📦 **Purchase Limit:** {limit_text.lstrip(' • Limit: ') if limit_text else 'None'}",
                inline=False,
            )
        return embed


class SellAllConfirmView(discord.ui.View):
    """Confirmation controls for bulk inventory sales."""

    def __init__(self, cog, owner_id, sale_kind):
        super().__init__(timeout=60)
        self.cog = cog
        self.owner_id = owner_id
        self.sale_kind = sale_kind
        self.finished = False

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "⚠️ This sale confirmation belongs to someone else.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self):
        if self.finished:
            return
        for child in self.children:
            child.disabled = True

    @discord.ui.button(label="Yes, Sell All", emoji="✅", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.finished:
            return
        self.finished = True
        for child in self.children:
            child.disabled = True
        await self.cog._confirm_bulk_sale(interaction, self.sale_kind, self)

    @discord.ui.button(label="Cancel", emoji="❌", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.finished:
            return
        self.finished = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content="❌ **Sale cancelled.** Nothing was sold.",
            embed=None,
            view=self,
        )


class Economy(commands.Cog):
    HP_REGEN_TIME = dt_time(
        hour=0,
        minute=0,
        tzinfo=pytz.timezone("US/Eastern")
    )

    def __init__(self, bot):
        self.bot = bot
        self.DEFAULT_VAULT_CAPACITY = 250_000
        self.MAX_VAULT_CAPACITY = 500_000
        self._give_locks = {}
        
        # Define shop catalog
        self.SHOP_ITEMS = {
            "nanite_patch": {
                "name": f"{EMOJIS.get('nanite_patch', '🩹')} Nanite Stim-Patch",
                "cost": 400,
                "type": "heal",
                "heal_amount": 35,
                "desc": "Quickly knits minor planetary surface wounds. Restores +35 HP."
            },
            "medkit": {
                "name": f"{EMOJIS.get('medkit', '🧰')} Field Trauma Medkit",
                "cost": 750,
                "type": "heal",
                "heal_amount": 100,
                "desc": "Standard planetary survival trauma kit. Restores +100 HP."
            },
            "revive": {
                "name": f"{EMOJIS.get('revive', '⚕️')} Revival Kit",
                "cost": 350,
                "type": "revive",
                "desc": "Immediately revives an unconscious explorer at 35% HP."
            },
            "full_revive": {
                "name": f"{EMOJIS.get('full_revive', '⚕️')} Emergency Full Revival",
                "cost": 800,
                "type": "revive",
                "desc": "Immediately revives an unconscious explorer at full HP."
            },
            "laser_charge_cell": {
                "name": f"{EMOJIS.get('laser_charge_cell', '🔋')} Laser Charge Cell",
                "cost": 400,
                "type": "consumable",
                "desc": "Restores 2 mining laser charges."
            },
            "laser_power_cell": {
                "name": f"{EMOJIS.get('laser_power_cell', '⚡')} Laser Power Cell",
                "cost": 750,
                "type": "consumable",
                "desc": "Restores 5 mining laser charges."
            },
            "fuel_refill": {
                "name": f"{EMOJIS.get('fuel_refill', '⚛️')} Laser Quantum Cell",
                "cost": 1200,
                "type": "consumable",
                "desc": "Instantly refills your mining laser to 10/10 charges."
            },
            "drone_battery": {
                "name": f"{EMOJIS.get('drone_battery', '🔋')} Drone Battery Pack",
                "cost": 400,
                "type": "consumable",
                "desc": "Restores 2 scavenge charges."
            },
            "drone_power_cell": {
                "name": f"{EMOJIS.get('drone_power_cell', '⚡')} Drone Power Cell",
                "cost": 750,
                "type": "consumable",
                "desc": "Restores 5 scavenge charges."
            },
            "drone_quantum_battery": {
                "name": f"{EMOJIS.get('drone_quantum_battery', '⚛️')} Drone Quantum Battery",
                "cost": 1200,
                "type": "consumable",
                "desc": "Instantly refills your scavenging drone to 10/10 charges."
            },
            "pet_snack": {
                "name": f"{EMOJIS.get('pet_snack', '🍪')} Pet Treat",
                "cost": 200,
                "type": "consumable",
                "desc": "A tasty treat for your station pet. Gives your active pet +25 Pet XP."
            },
            "time_crystal": {
                "name": f"{EMOJIS.get('time_crystal', '💎')} Dilated Time Crystal",
                "cost": 3500,
                "type": "special",
                "desc": "Bends time backwards to restore a fortune streak missed yesterday (Max 2 uses/month)."
            },
            "astral_essence": {
                "name": "✨ Astral Essence",
                "cost": 5000,
                "type": "special",
                "desc": "A concentrated fragment of stellar energy used to fuse duplicate pets and hunt for rare pet variants."
            },
            "neon_grid": {
                "name": "🌆 Background Voucher: Neon Grid",
                "cost": 4000,
                "type": "background_voucher",
                "desc": "Unlocks the 'Cyberpunk Neon Grid City' background photo for your /profile card."
            },
            "deep_void": {
                "name": "🌌 Background Voucher: Deep Void",
                "cost": 4500,
                "type": "background_voucher",
                "desc": "Unlocks the 'Deep Void' background photo for your /profile card."
            },
            "solaris_ring": {
                "name": "💫 Background Voucher: Solaris Ring",
                "cost": 5000,
                "type": "background_voucher",
                "desc": "Unlocks the 'Solaris Ring' background photo for your /profile card."
            },
            "fuel_stabilizer": {
                "name": f"{EMOJIS.get('fuel_stabilizer', '🛢️')} Fuel Stabilizer", "cost": 800, "type": "consumable",
                "desc": "Makes your next mining run cost no fuel charge."
            },
            "hazard_shield": {
                "name": f"{EMOJIS.get('hazard_shield', '🛡️')} Hazard Shield", "cost": 1000, "type": "consumable",
                "desc": "Blocks the next scavenging hazard."
            },
            "lucky_scanner": {
                "name": f"{EMOJIS.get('lucky_scanner', '📡')} Deep-Space Scanner", "cost": 700, "type": "consumable",
                "desc": "Improves rare-find odds on your next scavenging run."
            },
            "prototype_drill_bit": {
                "name": f"{EMOJIS.get('prototype_drill_bit', '⚙️')} Prototype Drill Bit", "cost": 1000, "type": "consumable",
                "desc": "Boosts Stardust from your next mining run."
            },
            "incubator_2": {
                "name": "🥚 Incubator Tube II",
                "cost": 50_000,
                "type": "station_upgrade",
                "desc": "Unlocks a second pet egg incubator tube."
            },
            "incubator_3": {
                "name": "🥚 Incubator Tube III",
                "cost": 125_000,
                "type": "station_upgrade",
                "desc": "Unlocks a third pet egg incubator tube."
            },
            "vault_expansion": {
                "name": "🔐 Vault Expansion",
                "cost": 150_000,
                "type": "station_upgrade",
                "desc": "Raises your Stardust vault capacity to the 500,000 Stardust maximum."
            },
        }
        # Stardust buyback values for space junk items
        self.JUNK_PRICES = {
            "space_pizza": 30,
            "floppy_disk": 50,
            "meteorite": 85,
            "rubber_duck": 50,
            "rusty_gear": 15,
            "tape_deck": 45,
            "alien_artifact": 80,
            "space_boot": 25,
            "cosmic_coin": 120,
            "holo_poster": 35,
            "broken_laser": 20,
            "lost_logbook": 20,
            "left_sock": 10,
            "warp_mug": 30,
            "space_pudding": 10,
            "tangled_cables": 25,
            "screaming_crystal": 100,
            "moon_cheese": 60,
            "golden_spatula": 120,
            "parking_ticket": 10,
            "floating_plant": 70,
            "tinted_visor": 25,
            "purring_lint": 30,
            "pet_rock": 40,
            "haunted_circuit": 120,
            "space_taco": 35,
            "rusty_wrench": 25,
            "alien_fossil": 75,
            "big_red_button": 10,
            "antique_compass": 30,
            "broken_clock": 30,
            "perplexing_painting": 80,
            "cosmic_banana": 20
        }

        # Add future daily offers here.  Each player sees the same three offers
        # for the whole Eastern-time day.
        self.ROTATING_ITEMS = {
            "fuel_stabilizer": {"name": f"{EMOJIS.get('fuel_stabilizer', '🛢️')} Fuel Stabilizer", "cost": 800, "desc": "Makes your next mining run cost no fuel charge."},
            "station_rations": {"name": f"{EMOJIS.get('station_rations', '🥫')} Station Rations", "cost": 150, "desc": "Restores a modest 15 HP."},
            "hazard_shield": {"name": f"{EMOJIS.get('hazard_shield', '🛡️')} Hazard Shield", "cost": 1000, "desc": "Blocks the next scavenging hazard."},
            "lucky_scanner": {"name": f"{EMOJIS.get('lucky_scanner', '📡')} Deep-Space Scanner", "cost": 700, "desc": "Improves rare-find odds on your next scavenging run."},
            "ore_magnet": {"name": f"{EMOJIS.get('ore_magnet', '🧲')} Ore Magnet", "cost": 500, "desc": "Guarantees a titanium ore find on your next mining run."},
            "prototype_drill_bit": {"name": f"{EMOJIS.get('prototype_drill_bit', '⚙️')} Prototype Drill Bit", "cost": 1000, "desc": "Boosts Stardust from your next mining run."},
            "cosmic_insurance": {"name": f"{EMOJIS.get('cosmic_insurance', '📋')} Cosmic Insurance", "cost": 800, "desc": "Prevents a knockout from your next scavenging hazard."},
            "fate_anchor": {"name": f"{EMOJIS.get('fate_anchor', '⚓')} Fate Anchor", "cost": 2250, "desc": "Protects one missed fortune streak day."},
            "revive_kit": {"name": f"{EMOJIS.get('revive_kit', '💉')} Emergency Revival Kit", "cost": 1500, "desc": "Revives an unconscious explorer at 50% HP."},
            "stop_sign": {"name": "🛑 Stop Sign", "cost": 250, "type": "defense_weapon", "desc": "Lethal Company-inspired station debris. 8% chance to prevent a scavenging hazard."},
            "stick": {"name": "🪵 Stick", "cost": 450, "type": "defense_weapon", "desc": "Undertale-inspired weapon. 4% chance to prevent a scavenging hazard."},
            "wooden_sword": {"name": "🗡️ Wooden Sword", "cost": 800, "type": "defense_weapon", "desc": "Minecraft-inspired starter weapon. 10% chance to prevent a scavenging hazard."},
            "wooden_shield": {"name": "🛡️ Wooden Shield", "cost": 650, "type": "defense_weapon", "desc": "Minecraft-inspired starter shield. 7% chance to prevent a scavenging hazard."},
            "wooden_spoon": {"name": "🥄 Wooden Spoon", "cost": 300, "type": "defense_weapon", "desc": "A mighty station kitchen utensil. 2% chance to prevent a scavenging hazard."},
            "heavy_wrench": {"name": "🔧 Suspiciously Heavy Wrench", "cost": 2000, "type": "defense_weapon", "desc": "A maintenance tool that doubles as a weapon. 12% chance to prevent a scavenging hazard."},
            "plasma_cutter": {"name": "🔫 Plasma Cutter", "cost": 6000, "type": "defense_weapon", "halloween_only": True, "desc": "Halloween-only Dead Space-inspired weapon. 25% chance to prevent a scavenging hazard."},
            "title_outer_rim_wanderer": {"name": "🏷️ Title: Outer Rim Wanderer", "cost": 750, "type": "title", "desc": "A title for explorers who venture beyond the station."},
            "title_starborn": {"name": "🏷️ Title: Starborn", "cost": 750, "type": "title", "desc": "A prestigious title for those touched by the stars."},
            "title_voidfarer": {"name": "🏷️ Title: Voidfarer", "cost": 750, "type": "title", "desc": "For those brave enough to chart the endless void."},
        }

        # Purchase limits for shop items.
        # Format: item_id: (maximum_quantity, period)
        # Periods: daily, weekly, monthly, lifetime
        self.SHOP_LIMITS = {
            # Permanent shop
            "nanite_patch": (10, "daily"),
            "medkit": (5, "daily"),
            "full_revive": (2, "weekly"),
            "laser_charge_cell": (5, "daily"),
            "laser_power_cell": (3, "daily"),
            "fuel_refill": (2, "daily"),
            "drone_battery": (5, "daily"),
            "drone_power_cell": (3, "daily"),
            "drone_quantum_battery": (2, "daily"),
            "pet_snack": (30, "daily"),
            "time_crystal": (2, "monthly"),
            "astral_essence": (10, "weekly"),

            # Rotating shop
            "fuel_stabilizer": (5, "daily"),
            "station_rations": (15, "daily"),
            "hazard_shield": (5, "daily"),
            "lucky_scanner": (5, "daily"),
            "ore_magnet": (5, "daily"),
            "prototype_drill_bit": (5, "daily"),
            "cosmic_insurance": (5, "daily"),
            "fate_anchor": (3, "daily"),
            "revive_kit": (3, "daily"),
            "incubator_2": (1, "lifetime"),
            "incubator_3": (1, "lifetime"),
            "vault_expansion": (1, "lifetime"),
            "stop_sign": (1, "lifetime"),
            "stick": (1, "lifetime"),
            "wooden_sword": (1, "lifetime"),
            "wooden_shield": (1, "lifetime"),
            "wooden_spoon": (1, "lifetime"),
            "heavy_wrench": (1, "lifetime"),
            "plasma_cutter": (1, "lifetime"),

            # Rotating titles are permanent unlocks.
            "title_outer_rim_wanderer": (1, "lifetime"),
            "title_starborn": (1, "lifetime"),
            "title_voidfarer": (1, "lifetime"),
        }

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

        for item_id, item in self.ROTATING_ITEMS.items():
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
        limit_info = self.SHOP_LIMITS.get(item_id)

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
        limit_info = self.SHOP_LIMITS.get(item_id)

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
                f"ALTER TABLE users ADD COLUMN vault_capacity INTEGER DEFAULT {self.DEFAULT_VAULT_CAPACITY}"
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

        
    @tasks.loop(time=HP_REGEN_TIME)
    async def midnight_hp_regeneration(self):
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
    async def before_midnight_hp_regeneration(self):
        await self.bot.wait_until_ready()

    @midnight_hp_regeneration.error
    async def midnight_hp_regeneration_error(self, error):
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

    @commands.hybrid_command(
        name="daily",
        description="Claim your daily Stardust reward and build your streak! Rewards max out at 1,150 Stardust."
    )
    async def daily(self, ctx: commands.Context):
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

        choices = []
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

    @staticmethod
    def _give_item_excluded(item_id, info):
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

    @commands.hybrid_command(
        name="give",
        description="Give another member one of your pets or transferable items.",
    )
    @app_commands.describe(
        member="The member you want to give something to.",
        pet="An owned pet to transfer. Leave blank when giving an item.",
        item="An owned transferable item to give. Leave blank when giving a pet or Stardust.",
        stardust="How much Stardust to give. Leave blank when giving a pet or item.",
        quantity="How many of the selected item to give (default: 1).",
    )
    @app_commands.autocomplete(pet=give_pet_autocomplete, item=give_item_autocomplete)
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
                    "Mineral", "Crafting Material", "Haunted Ingredient",
                    "Location-Based Collectible", "Collectible"
                }
                or item_id in SELLABLE_ITEM_IDS
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
            if not is_sellable(item_id, info, stored_type):
                continue

            junk = is_space_junk(info, stored_type)
            normal_collectible = is_normal_collectible(item_id, info)
            halloween = is_halloween_item(item_id, info, stored_type)
            halloween_collectible = normal_collectible
            item_type = str(info.get("type", ""))

            if category == "space_junk" and not junk:
                continue
            if category == "collectibles" and not normal_collectible:
                continue
            if category == "halloween" and not halloween:
                continue
            if category == "materials" and (
                item_type not in {"Mineral", "Crafting Material"}
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

        category = category or "healing"

        item_ids = list(SHOP_BUY_CATEGORY_ITEMS.get(category, []))
        if category == "daily":
            item_ids = list(self.daily_rotation())

        autocomplete_emojis = {
            "nanite_patch": "🩹", "medkit": "🧰", "revive": "⚕️", "full_revive": "⚕️",
            "laser_charge_cell": "🔋", "laser_power_cell": "⚡", "fuel_refill": "⚛️",
            "drone_battery": "🔋", "drone_power_cell": "⚡", "drone_quantum_battery": "⚛️",
            "pet_snack": "🍪", "time_crystal": "💎", "astral_essence": "✨",
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
                    "Mineral", "Crafting Material", "Haunted Ingredient",
                    "Location-Based Collectible", "Collectible"
                }
                or item_id in SELLABLE_ITEM_IDS
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
                if not is_sellable(item_id, info, stored_type):
                    continue

                junk = is_space_junk(info, stored_type)
                normal_collectible = is_normal_collectible(item_id, info)
                halloween = is_halloween_item(item_id, info, stored_type)
                halloween_collectible = is_halloween_collectible(item_id)
                item_type = str(info.get("type", ""))

                if category == "space_junk" and not junk:
                    continue
                if category == "collectibles" and not normal_collectible:
                    continue
                if category == "halloween" and not halloween:
                    continue
                if category == "materials" and (
                    item_type not in {"Mineral", "Crafting Material"}
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
        action = next((o.get("value") for o in options if o.get("name") == "action"), "buy")
        if action == "sell":
            return await self.shop_sell_autocomplete(interaction, current)
        return await self.shop_buy_autocomplete(interaction, current)

    @commands.hybrid_group(
        name="shop",
        description="Browse the station shop and manage your purchases.",
    )
    async def shop(self, ctx: commands.Context):
        """Shop command group."""
        await ctx.send(
            "🛒 Choose a shop option: **list**, **buy**, **sell**, or **rotating**."
        )


    @shop.command(
        name="list",
        description="View the station shop catalog.",
    )
    @app_commands.describe(
        category="Optional shop category to open directly.",
    )
    @app_commands.choices(
        category=[
            app_commands.Choice(name="❤️ Healing", value="healing"),
            app_commands.Choice(name="🔋 Recharge", value="recharge"),
            app_commands.Choice(name="🛠️ Upgrades", value="upgrades"),
            app_commands.Choice(name="🐾 Pet Items", value="pet_items"),
            app_commands.Choice(name="✨ Special", value="special"),
            app_commands.Choice(name="🎟️ Lottery", value="lottery"),
            app_commands.Choice(name="🖼️ Backgrounds", value="backgrounds"),
        ]
    )
    async def shop_list(
        self,
        ctx: commands.Context,
        category: str = "healing",
    ):
        """Display the shop catalog."""
        view = ShopView(self, ctx.author.id)
        embed = view.build_embed(category)
        await ctx.send(embed=embed, view=view)


    @shop.command(
        name="buy",
        description="Open the interactive shop and buy an item.",
    )
    async def shop_buy(self, ctx: commands.Context):
        """Open the interactive Category → Item → Quantity → Confirm buy flow."""
        view = ShopTransactionView(self, ctx.author.id, "buy")
        embed = view._build_category_embed()
        await ctx.send(embed=embed, view=view)


    @shop.command(
        name="sell",
        description="Open the interactive inventory shop and sell an item.",
    )
    async def shop_sell(self, ctx: commands.Context):
        """Open the interactive Category → Item → Quantity → Confirm sell flow."""
        view = ShopTransactionView(self, ctx.author.id, "sell")
        embed = view._build_category_embed()
        await ctx.send(embed=embed, view=view)


    @shop.command(
        name="rotating",
        description="View today's rotating shop offers.",
    )
    async def shop_rotating(self, ctx: commands.Context):
        """Display today's rotating shop with direct purchase buttons."""
        view = ShopView(self, ctx.author.id, category="daily")
        embed = view.build_embed("daily")
        embed.set_footer(text="Choose an offer below to buy it • Offers rotate at midnight Eastern time.")
        await ctx.send(embed=embed, view=view)


    async def buy(self, ctx: commands.Context, item_id: str, quantity: int = 1):
        await ctx.defer()
        user_id = ctx.author.id
        item_id = item_id.lower()

        if quantity < 1 or quantity > 99:
            return await ctx.send("❌ Quantity must be between **1 and 99**.")

        rotating_item = self.ROTATING_ITEMS.get(item_id)
        is_permanent_item = item_id in self.SHOP_ITEMS

        if not is_permanent_item and rotating_item is None:
            return await ctx.send(
                "❌ Invalid item ID! Check available items using `/shop`."
            )

        # Rotation-only items must be featured today. Permanent items may also
        # appear in ROTATING_ITEMS and receive the Daily Offer discount.
        if not is_permanent_item:
            if rotating_item is None:
                return await ctx.send("❌ That rotating item could not be loaded.")
            if item_id not in self.daily_rotation():
                return await ctx.send(
                    "⏳ That item is not in today's rotating market. "
                    "Check `/shop` and select 🔄️ Daily Offers for the current offers."
                )

        item: dict[str, Any] | None = self.SHOP_ITEMS.get(item_id)
        if item is None:
            if rotating_item is None:
                return await ctx.send("❌ That item could not be loaded from the shop catalog.")
            item = rotating_item

        # Permanent items receive 15% off when featured in today's Daily Offers.
        # Rotating-only items keep their normal listed price.
        is_daily_offer = item_id in self.daily_rotation()

        if is_daily_offer and is_permanent_item:
            base_unit_cost = int(item["cost"] * 0.85)
        else:
            base_unit_cost = item["cost"]

        cost = base_unit_cost * quantity

        db_path = self.get_db_path()

        async with aiosqlite.connect(db_path) as db:
            
            # Run schema/migration work before starting the purchase transaction.
            await self.ensure_schema(db)
            await db.commit()

            from inventory import ITEM_REGISTRY, add_inventory_item

            item_info = ITEM_REGISTRY.get(item_id)

            # Permanent station upgrades live on the users table rather than
            # the inventory registry. They are handled below and return before
            # any inventory-registry-only code is reached.

            # These items are stored directly on the users table.
            legacy_columns = {
                "time_crystal": "time_crystals",
                "nanite_patch": "nanite_patchs",
                "medkit": "medkits",
            }

            # Lock before reading inventory, balance, or purchase-limit state.
            # All critical reads and writes now share one atomic snapshot.
            await db.execute("BEGIN IMMEDIATE")

            # Some rotation-only catalog entries do not carry their own
            # type metadata. Fall back to the master inventory definition
            # instead of indexing the key directly and raising KeyError.
            item_type = item.get("type")
            if item_type is None and item_info is not None:
                item_type = item_info.get("type")

            if item_type == "station_upgrade":
                if quantity != 1:
                    await db.rollback()
                    return await ctx.send(
                        "🛠️ Station upgrades can only be purchased **one at a time**."
                    )

                async with db.execute(
                    "SELECT COALESCE(stardust, 0), COALESCE(incubator_slots, 1), "
                    "COALESCE(vault_capacity, ?) FROM users WHERE user_id = ?",
                    (self.DEFAULT_VAULT_CAPACITY, user_id),
                ) as cursor:
                    upgrade_row = await cursor.fetchone()

                if not upgrade_row:
                    await db.rollback()
                    return await ctx.send(
                        "❌ You don't have an active station profile yet. "
                        "Run `/profile` or `/mine` first!"
                    )

                stardust, incubator_slots, vault_capacity = upgrade_row

                if item_id == "incubator_2" and incubator_slots >= 2:
                    await db.rollback()
                    return await ctx.send(
                        "🥚 You already have Incubator Tube II unlocked."
                    )

                if item_id == "incubator_3" and incubator_slots >= 3:
                    await db.rollback()
                    return await ctx.send(
                        "🥚 You already have Incubator Tube III unlocked."
                    )

                if item_id == "incubator_3" and incubator_slots < 2:
                    await db.rollback()
                    return await ctx.send(
                        "⚠️ Unlock Incubator Tube II before purchasing Tube III."
                    )

                if item_id == "vault_expansion" and vault_capacity >= self.MAX_VAULT_CAPACITY:
                    await db.rollback()
                    return await ctx.send(
                        "🔐 Your Stardust vault is already at its 500,000 Stardust maximum."
                    )

                if stardust < cost:
                    await db.rollback()
                    return await ctx.send(
                        f"💸 **Insufficient Stardust!** You have **{stardust:,}** "
                        f"Stardust, but this upgrade costs **{cost:,}**."
                    )

                if item_id == "incubator_2":
                    await db.execute(
                        "UPDATE users SET stardust = stardust - ?, incubator_slots = 2 WHERE user_id = ?",
                        (cost, user_id),
                    )
                elif item_id == "incubator_3":
                    await db.execute(
                        "UPDATE users SET stardust = stardust - ?, incubator_slots = 3 WHERE user_id = ?",
                        (cost, user_id),
                    )
                else:
                    await db.execute(
                        "UPDATE users SET stardust = stardust - ?, vault_capacity = ? WHERE user_id = ?",
                        (cost, self.MAX_VAULT_CAPACITY, user_id),
                    )

                await self.record_shop_purchase(db, user_id, item_id, 1)
                await db.commit()

                return await ctx.send(
                    f"{ctx.author.mention} 🛠️ **Upgrade Purchased!** "
                    f"**{item['name']}** is now unlocked for **{cost:,} Stardust**."
                )

            # Every non-upgrade purchase reaches this point only if the item
            # exists in the master inventory registry. Narrow the Optional
            # value here so Pylance can safely type-check all later uses.
            if item_info is None:
                await db.rollback()
                return await ctx.send(
                    "❌ This item is not registered in the master item registry."
                )

            max_stack = item_info.get("max_quantity", 1)

            if item_id in legacy_columns:
                column = legacy_columns[item_id]

                async with db.execute(
                    f"SELECT {column} FROM users WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()

                current_quantity = (row[0] or 0) if row else 0

            else:
                async with db.execute(
                    "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                    (user_id, item_id)
                ) as cursor:
                    inventory_row = await cursor.fetchone()

                current_quantity = (inventory_row[0] or 0) if inventory_row else 0

            if current_quantity + quantity > max_stack:
                await db.rollback()
                return await ctx.send(
                    f"📦 **Inventory Full!** You can only hold **{max_stack}x** "
                    f"**{item_info['name']}**.\n"
                    f"You currently have **{current_quantity}x**."
                )

            # Check user's Stardust balance and current health state.
            async with db.execute(
                "SELECT stardust, mining_charges, hp, max_hp "
                "FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                await db.rollback()
                return await ctx.send(
                    "❌ You don't have an active station profile yet. "
                    "Run `/profile` or `/mine` first!"
                )

            stardust, charges, hp, max_hp = row

            from pets import get_active_pet_effects
            pet_effects = await get_active_pet_effects(db, user_id)

            # Void Merchant's normal shop discount stacks on top of an existing
            # Daily Offer discount. Its level-5 free-purchase effect is a
            # one-purchase-per-day proc and is claimed inside this same lock.
            shop_discount = max(0.0, min(0.99, float(pet_effects.get("shop_discount", 0.0))))
            unit_cost = max(1, int(base_unit_cost * (1 - shop_discount)))
            cost = unit_cost * quantity
            free_purchase = False

            free_chance = float(pet_effects.get("shop_free_purchase", 0.0))
            if free_chance > 0:
                today_key = self.rotation_date()
                async with db.execute(
                    "SELECT 1 FROM pet_effect_usage WHERE user_id = ? AND effect_id = ? AND period_key = ?",
                    (user_id, "void_merchant_free_purchase", today_key),
                ) as cursor:
                    free_used = await cursor.fetchone()

                if not free_used and random.random() < free_chance:
                    await db.execute(
                        "INSERT INTO pet_effect_usage (user_id, effect_id, period_key) VALUES (?, ?, ?)",
                        (user_id, "void_merchant_free_purchase", today_key),
                    )
                    cost = 0
                    free_purchase = True

            if stardust < cost:
                await db.rollback()
                return await ctx.send(
                    f"💸 **Insufficient Stardust!** You have **{stardust:,}** "
                    f"Stardust, but this item costs **{cost:,}**."
                )

            # ─────────────────────────────────────────────
            # SHOP PURCHASE LIMIT
            # ─────────────────────────────────────────────
            limit_info = self.SHOP_LIMITS.get(item_id)

            if limit_info:
                max_quantity, period = limit_info
                period_key = self.purchase_period_key(period)

                async with db.execute(
                    """
                    SELECT quantity
                    FROM shop_purchase_limits
                    WHERE user_id = ?
                      AND item_id = ?
                      AND period_key = ?
                    """,
                    (user_id, item_id, period_key)
                ) as cursor:
                    limit_row = await cursor.fetchone()

                purchased_quantity = (limit_row[0] or 0) if limit_row else 0
                remaining = max_quantity - purchased_quantity

                if quantity > remaining:
                    await db.rollback()

                    if remaining <= 0:
                        return await ctx.send(
                            f"🚫 **Purchase Limit Reached!** "
                            f"You've already bought the maximum **{max_quantity}x** "
                            f"**{item['name']}** allowed {period}."
                        )

                    return await ctx.send(
                        f"🚫 **Purchase Limit Exceeded!** "
                        f"You can only buy **{remaining} more** "
                        f"**{item['name']}** this {period}."
                    )

            # Backgrounds are individual permanent unlocks.
            # They cannot be purchased in bulk.
            if item_type == "background_voucher" and quantity != 1:
                await db.rollback()
                return await ctx.send(
                    "🖼️ Background vouchers can only be purchased **one at a time**."
                )

            # Process purchase based on item type.
            new_stardust = stardust - cost

            if rotating_item is not None:
                item = rotating_item
                item_type = rotating_item.get("type", "consumable")

                # Titles are permanent unlocks.
                if item_type == "title":
                    if quantity != 1:
                        await db.rollback()
                        return await ctx.send(
                            "🏷️ Titles can only be purchased **once.**"
                        )

                    async with db.execute(
                        "SELECT 1 FROM inventory WHERE user_id = ? AND item_id = ?",
                        (user_id, item_id)
                    ) as cursor:
                        already_owned = await cursor.fetchone()

                    if already_owned:
                        await db.rollback()
                        return await ctx.send(
                            "⚠️ You already own this title!"
                        )

                # Add the item through the master inventory helper so the
                # registry stack limit is enforced inside the locked transaction.
                added_amount, new_quantity, max_quantity = await add_inventory_item(
                    db,
                    user_id,
                    item_id,
                    item_type,
                    quantity
                )

                if added_amount != quantity:
                    await db.rollback()
                    return await ctx.send(
                        f"📦 **Inventory Full!** You can only hold **{max_quantity}x** "
                        f"**{item['name']}**.\n"
                        f"You currently have **{new_quantity}x**."
                    )

                await db.execute(
                    "UPDATE users SET stardust = ? WHERE user_id = ?",
                    (new_stardust, user_id)
                )

                # Record this purchase against the item's current limit period.
                limit_info = self.SHOP_LIMITS.get(item_id)

                if limit_info:
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

                await db.commit()

                price_note = (
                    "🕳️ **Void Merchant:** This purchase was completely free!"
                    if free_purchase else
                    f"for **{cost:,} Stardust**!"
                )
                if item_type == "title":
                    return await ctx.send(
                        f"🏷️ **Title Unlocked!** You purchased **{item['name']}** "
                        + price_note
                    )

                return await ctx.send(
                    f"{ctx.author.mention} 🔄 **Purchase Successful!** Added **{quantity}x "
                    f"{item['name']}** to your inventory "
                    + price_note
                )

            if item_type == "revive":
                added_amount, new_quantity, max_quantity = await add_inventory_item(
                    db,
                    user_id,
                    item_id,
                    "consumable",
                    quantity
                )

                if added_amount != quantity:
                    await db.rollback()
                    return await ctx.send(
                        f"📦 **Inventory Full!** You can only hold **{max_quantity}x** "
                        f"**{item['name']}**.\n"
                        f"You currently have **{new_quantity}x**."
                    )

                await db.execute(
                    "UPDATE users SET stardust = ? WHERE user_id = ?",
                    (new_stardust, user_id)
                )

                await self.record_shop_purchase(
                    db, user_id, item_id, quantity
                )

                await db.commit()

                return await ctx.send(
                    f"{ctx.author.mention} ⚕️ **Purchase Successful!** Added **{quantity}x "
                    f"{item['name']}** to your inventory for "
                    f"**{cost:,} Stardust**!"
                )

            if item_type == "consumable" and item_id in {
                "fuel_refill",
                "laser_charge_cell",
                "laser_power_cell",
                "drone_battery",
                "drone_power_cell",
                "drone_quantum_battery",
            }:
                await db.execute(
                    """
                    INSERT INTO inventory (user_id, item_id, item_type, quantity)
                    VALUES (?, ?, 'consumable', ?)
                    ON CONFLICT(user_id, item_id) DO UPDATE SET
                        item_type = excluded.item_type,
                        quantity = quantity + excluded.quantity
                    """,
                    (user_id, item_id, quantity)
                )

                await db.execute(
                    "UPDATE users SET stardust = ? WHERE user_id = ?",
                    (new_stardust, user_id)
                )

                await self.record_shop_purchase(
                    db, user_id, item_id, quantity
                )

                await db.commit()

                return await ctx.send(
                    f"{ctx.author.mention} 🔋 **Purchase Successful!** Added **{quantity}x "
                    f"{item['name']}** to your inventory for "
                    f"**{cost:,} Stardust**!"
                )

            if item_type == "consumable" and item_id == "pet_snack":
                added_amount, new_quantity, max_quantity = await add_inventory_item(
                    db,
                    user_id,
                    item_id,
                    "consumable",
                    quantity
                )

                if added_amount != quantity:
                    await db.rollback()
                    return await ctx.send(
                        f"📦 **Inventory Full!** You can only hold **{max_quantity}x** "
                        f"**{item['name']}**.\n"
                        f"You currently have **{new_quantity}x**."
                    )

                await db.execute(
                    "UPDATE users SET stardust = ? WHERE user_id = ?",
                    (new_stardust, user_id)
                )

                await self.record_shop_purchase(
                    db, user_id, item_id, quantity
                )

                await db.commit()

                return await ctx.send(
                    f"{ctx.author.mention} 🧬 **Purchase Successful!** Added **{quantity}x {item['name']}** "
                    f"to your inventory for **{cost:,} Stardust**!"
                )
            if item_id == "astral_essence":
                added_amount, new_quantity, max_quantity = await add_inventory_item(
                    db,
                    user_id,
                    item_id,
                    "special",
                    quantity
                )

                if added_amount != quantity:
                    await db.rollback()
                    return await ctx.send(
                        f"📦 **Inventory Full!** You can only hold **{max_quantity}x** "
                        f"**{item['name']}**.\n"
                        f"You currently have **{new_quantity}x**."
                    )

                await db.execute(
                    "UPDATE users SET stardust = ? WHERE user_id = ?",
                    (new_stardust, user_id)
                )

                await self.record_shop_purchase(
                    db, user_id, item_id, quantity
                )

                await db.commit()

                return await ctx.send(
                    f"{ctx.author.mention} ✨ **Purchase Successful!** Added **{quantity}x "
                    f"{item['name']}** to your inventory for **{cost:,} Stardust**!"
                )

            if item_id == "time_crystal":
                max_stack = item_info.get("max_quantity", 10)

                async with db.execute(
                    "SELECT COALESCE(time_crystals, 0) FROM users WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()

                current_quantity = row[0] if row else 0

                if current_quantity + quantity > max_stack:
                    await db.rollback()
                    return await ctx.send(
                        f"📦 **Inventory Full!** You can only hold **{max_stack}x** "
                        f"**{item['name']}**.\n"
                        f"You currently have **{current_quantity}x**."
                    )

                await db.execute(
                    """
                    UPDATE users
                    SET stardust = ?,
                        time_crystals = COALESCE(time_crystals, 0) + ?
                    WHERE user_id = ?
                    """,
                    (new_stardust, quantity, user_id)
                )

                await self.record_shop_purchase(
                    db, user_id, item_id, quantity
                )

                await db.commit()

                return await ctx.send(
                    f"{ctx.author.mention} 💎 **Purchase Successful!** Added **{quantity}x "
                    f"{item['name']}** to your inventory for "
                    f"**{cost:,} Stardust**!\n"
                    f"If you miss a fortune streak, use `/usecrystal` to repair it."
                )

            if item_type == "background_voucher":
                # A redeemed voucher permanently unlocks its background.
                # Check that unlock list before charging Stardust so users can
                # never buy another copy of a background they already own.
                async with db.execute(
                    "SELECT unlocked_backgrounds FROM users WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    unlock_row = await cursor.fetchone()

                unlocked_backgrounds = ["default"]
                if unlock_row and unlock_row[0]:
                    try:
                        parsed = json.loads(unlock_row[0])
                        if isinstance(parsed, list):
                            unlocked_backgrounds = parsed
                    except (TypeError, json.JSONDecodeError):
                        pass

                if item_id in unlocked_backgrounds:
                    await db.rollback()
                    return await ctx.send(
                        "⚠️ You already unlocked this background! "
                        "You can select it with `/background` **after** redeeming with `/voucher`."
                    )

                # Also prevent buying a duplicate voucher while the original
                # unredeemed voucher is still in the user's inventory.
                async with db.execute(
                    "SELECT 1 FROM inventory "
                    "WHERE user_id = ? AND item_id = ?",
                    (user_id, item_id)
                ) as cursor:
                    already_owned = await cursor.fetchone()

                if already_owned:
                    await db.rollback()
                    return await ctx.send(
                        "⚠️ You already own this background voucher!"
                    )

                await db.execute(
                    """
                    INSERT INTO inventory
                        (user_id, item_id, item_type, quantity)
                    VALUES (?, ?, 'background_voucher', 1)
                    """,
                    (user_id, item_id)
                )

                await db.execute(
                    "UPDATE users SET stardust = ? WHERE user_id = ?",
                    (new_stardust, user_id)
                )

                await self.record_shop_purchase(
                    db, user_id, item_id, quantity
                )

                await db.commit()

                return await ctx.send(
                    f"{ctx.author.mention} 🌟 **Purchase Successful!** Unlocked "
                    f"**{item['name']}** for **{cost:,} Stardust**!"
                )

            if item_type == "heal":
                # Item key format:
                # medkit -> medkits
                # nanite_patch -> nanite_patchs
                col_name = f"{item_id}s"

                max_stack = item_info.get("max_quantity", 10)

                # Ensure inventory column exists dynamically.
                async with db.execute("PRAGMA table_info(users)") as cursor:
                    rows = await cursor.fetchall()

                existing_cols = {row[1] for row in rows}

                if col_name not in existing_cols:
                    await db.execute(
                        f"ALTER TABLE users ADD COLUMN "
                        f"{col_name} INTEGER DEFAULT 0"
                    )

                async with db.execute(
                    f"SELECT COALESCE({col_name}, 0) FROM users WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()

                current_quantity = row[0] if row else 0

                if current_quantity + quantity > max_stack:
                    await db.rollback()
                    return await ctx.send(
                        f"📦 **Inventory Full!** You can only hold **{max_stack}x** "
                        f"**{item['name']}**.\n"
                        f"You currently have **{current_quantity}x**."
                    )

                await db.execute(
                    f"""
                    UPDATE users
                    SET stardust = ?,
                        {col_name} = COALESCE({col_name}, 0) + ?
                    WHERE user_id = ?
                    """,
                    (new_stardust, quantity, user_id)
                )

                await self.record_shop_purchase(
                    db, user_id, item_id, quantity
                )

                await db.commit()

                return await ctx.send(
                    f"{ctx.author.mention} 🛒 **Purchase Successful!** Added **{quantity}x {item['name']}** "
                    f"to your inventory for **{cost:,} Stardust**!"
                )

            await db.rollback()

        await ctx.send("❌ An error occurred processing your transaction.")

    def get_junk_sell_reward(self, item_id):
        """Return Stardust + Halloween Candy rewards for a junk item."""
        halloween_reward = get_halloween_sell_reward(item_id)
        if halloween_reward is not None:
            return halloween_reward
        return (self.JUNK_PRICES.get(item_id, 25), 0)

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

    @commands.hybrid_command(name="salvage", description="Salvage Space Junk or upgrade kits for materials.")
    @app_commands.describe(item="Choose Space Junk to salvage, or salvage all of it.")
    @app_commands.autocomplete(item=salvage_item_autocomplete)
    async def salvage(self, ctx: commands.Context, item: str):
        await ctx.defer()

        user_id = ctx.author.id
        target_item = item.lower().strip()
        db_path = self.get_db_path()

        # Get the user's current Salvage Rig bonus chance.
        upgrade_cog = self.bot.get_cog("Upgrades")
        salvage_upgrade = (
            await upgrade_cog.get_effects(user_id, "salvage")
            if upgrade_cog
            else {"level": 0, "bonus_chance": 0.0}
        )
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

    async def _get_bulk_sale_rows(self, db, user_id, sale_kind):
        """Return sellable inventory rows for a bulk sale kind."""
        async with db.execute(
            "SELECT item_id, quantity, item_type FROM inventory WHERE user_id = ? AND quantity > 0 ORDER BY item_id",
            (user_id,),
        ) as cursor:
            rows = await cursor.fetchall()

        def is_junk(item_id, info, stored_type):
            return str(stored_type).lower() == "space_junk" or info.get("type") == "Space Junk"

        def is_halloween_collectible(item_id, info):
            # Bulk Halloween sales are intentionally limited to collectible
            # items only. Halloween materials, candy, bags, and seasonal
            # equipment must never be swept into this option.
            return (
                item_id in LOCATION_BASED_COLLECTIBLES
                or item_id in HALLOWEEN_COLLECTIBLE_IDS
            )

        result = []
        for item_id, quantity, stored_type in rows:
            info = ITEM_REGISTRY.get(item_id)
            if not info:
                continue
            junk = is_junk(item_id, info, stored_type)
            halloween_collectible = is_halloween_collectible(item_id, info)
            collectible = (item_id in HALLOWEEN_COLLECTIBLE_IDS or item_id in LOCATION_BASED_COLLECTIBLES
                           or str(info.get("type", "")).lower() == "collectible")
            item_type = str(info.get("type", ""))

            if junk:
                sellable = item_id in self.JUNK_PRICES or get_halloween_sell_reward(item_id) is not None
            else:
                sellable = bool(int(info.get("sell_price", 0) or 0)) and (
                    item_type in {"Mineral", "Crafting Material", "Haunted Ingredient", "Location-Based Collectible", "Collectible"}
                    or item_id in SELLABLE_ITEM_IDS
                )
            if not sellable:
                continue

            if sale_kind == "all_junk":
                if not junk or item_id in HALLOWEEN_SPACE_JUNK_IDS or item_id not in self.JUNK_PRICES:
                    continue
            elif sale_kind == "all_materials":
                if item_id not in NORMAL_SELL_ALL_MATERIAL_IDS:
                    continue
            elif sale_kind == "all_halloween":
                if not halloween_collectible:
                    continue
            else:
                continue

            result.append((item_id, quantity, info, stored_type))
        return result

    async def _bulk_sale_preview(self, user_id, sale_kind):
        async with aiosqlite.connect(self.get_db_path()) as db:
            rows = await self._get_bulk_sale_rows(db, user_id, sale_kind)

        total_stardust = 0
        total_candy = 0
        item_count = 0
        lines = []
        for item_id, quantity, info, stored_type in rows:
            if str(stored_type).lower() == "space_junk" or info.get("type") == "Space Junk":
                payout, candy = self.get_junk_sell_reward(item_id)
            else:
                payout, candy = int(info.get("sell_price", 0) or 0), 0
            total_stardust += payout * quantity
            total_candy += candy * quantity
            item_count += quantity
            lines.append(f"{info.get('emoji', '📦')} **{info.get('name', item_id)} ×{quantity}**")

        return rows, total_stardust, total_candy, item_count, lines

    async def _confirm_bulk_sale(self, interaction, sale_kind, view):
        """Execute a previously confirmed bulk sale using a fresh DB snapshot."""
        user_id = interaction.user.id
        db_path = self.get_db_path()

        await interaction.response.defer()

        async with aiosqlite.connect(db_path) as db:
            await db.execute("BEGIN IMMEDIATE")
            rows = await self._get_bulk_sale_rows(db, user_id, sale_kind)
            if not rows:
                await db.rollback()
                return await interaction.edit_original_response(
                    content="❌ **Nothing to sell.** Your inventory changed before the confirmation was completed.",
                    embed=None,
                    view=view,
                )

            total_stardust = 0
            total_candy = 0
            item_count = 0
            sold_lines = []
            for item_id, quantity, info, stored_type in rows:
                if str(stored_type).lower() == "space_junk" or info.get("type") == "Space Junk":
                    payout, candy = self.get_junk_sell_reward(item_id)
                else:
                    payout, candy = int(info.get("sell_price", 0) or 0), 0
                total_stardust += payout * quantity
                total_candy += candy * quantity
                item_count += quantity
                sold_lines.append(f"{info.get('emoji', '📦')} {info.get('name', item_id)} ×{quantity}")

            for item_id, _quantity, _info, _stored_type in rows:
                await db.execute(
                    "DELETE FROM inventory WHERE user_id = ? AND item_id = ?",
                    (user_id, item_id),
                )

            await db.execute(
                "UPDATE users SET stardust = COALESCE(stardust, 0) + ? WHERE user_id = ?",
                (total_stardust, user_id),
            )

            candy_added = 0
            candy_overflow = 0
            if total_candy > 0:
                from inventory import add_inventory_item
                candy_added, _, _ = await add_inventory_item(
                    db, user_id, "halloween_candy", "consumable", total_candy
                )
                candy_overflow = total_candy - candy_added
                if candy_overflow > 0:
                    overflow_payout = candy_overflow * 5
                    total_stardust += overflow_payout
                    await db.execute(
                        "UPDATE users SET stardust = COALESCE(stardust, 0) + ? WHERE user_id = ?",
                        (overflow_payout, user_id),
                    )

            await db.commit()

        preview = "\n".join(sold_lines[:12])
        if len(sold_lines) > 12:
            preview += f"\n…and {len(sold_lines) - 12} more."

        candy_text = f"\n🍬 **Halloween Candy:** +{candy_added}" if candy_added else ""
        overflow_text = (
            f"\n📦 **Candy Overflow:** {candy_overflow} converted to ✨ **{candy_overflow * 5:,} Stardust**"
            if candy_overflow else ""
        )
        await interaction.edit_original_response(
            content=(
                f"{interaction.user.mention} 🛍️ **Salvage Vendor:** Sold **{item_count} items** "
                f"for ✨ **{total_stardust:,} Stardust**!{candy_text}{overflow_text}\n\n"
                f"**Items Sold:**\n{preview}"
            ),
            embed=None,
            view=view,
        )


    async def sell(
        self,
        ctx: commands.Context,
        item: str,
        quantity: str = "1"
    ):
        await ctx.defer()

        user_id = ctx.author.id
        target_item = item.lower().strip()
        db_path = self.get_db_path()

        # Regular sales accept either a number (1–99) or `max`, which means
        # sell the entire quantity currently owned of the selected item.
        quantity_input = str(quantity).strip().lower()
        if quantity_input == "max":
            quantity_is_max = True
            quantity = None
        else:
            try:
                quantity = int(quantity_input)
            except (TypeError, ValueError):
                return await ctx.send(
                    "❌ Quantity must be a number between **1 and 99**, or **`max`** to sell all you own."
                )
            quantity_is_max = False
            if quantity < 1 or quantity > 99:
                return await ctx.send(
                    "❌ Quantity must be between **1 and 99**, or **`max`** to sell all you own."
                )

        if target_item in BULK_SELL_OPTIONS:
            rows, total_stardust, total_candy, item_count, lines = await self._bulk_sale_preview(user_id, target_item)
            if not rows:
                return await ctx.send("🎒 **Nothing to sell!** You don't currently have any items covered by that Sell All option.")

            preview = "\n".join(lines[:12])
            if len(lines) > 12:
                preview += f"\n…and {len(lines) - 12} more."
            candy_preview = f"\n🍬 **Halloween Candy:** +{total_candy}" if total_candy else ""
            embed = discord.Embed(
                title="⚠️ Confirm Bulk Sale",
                description=(
                    f"You are about to sell **{item_count} items** for approximately "
                    f"✨ **{total_stardust:,} Stardust**.{candy_preview}\n\n"
                    f"**Items included:**\n{preview}\n\n"
                    "📚 **Collection Note:** Collectibles are permanently recorded in your collection once discovered. Selling the physical items does **not** remove them from your collection.\n\nThis cannot be undone. Choose **Yes, Sell All** or **Cancel**."
                ),
                color=discord.Color.orange(),
            )
            view = SellAllConfirmView(self, user_id, target_item)
            return await ctx.send(embed=embed, view=view)

        from inventory import ITEM_REGISTRY, add_inventory_item

        async with aiosqlite.connect(db_path) as db:
            # Lock the database before reading inventory so concurrent sell
            # requests cannot both cash out the same inventory.
            await db.execute("BEGIN IMMEDIATE")

            # ------------------------------------------------------------------
            # Option A: Sell all NORMAL Space Junk.
            # Halloween Space Junk is intentionally excluded.
            # ------------------------------------------------------------------
            if target_item == "all_junk":
                async with db.execute(
                    """
                    SELECT item_id, quantity
                    FROM inventory
                    WHERE user_id = ?
                      AND item_type = 'space_junk'
                      AND item_id IN ({})
                      AND quantity > 0
                    """.format(",".join("?" * len(self.JUNK_PRICES))),
                    (user_id, *self.JUNK_PRICES.keys())
                ) as cursor:
                    junk_rows = await cursor.fetchall()

                # Halloween Space Junk is seasonal and intentionally excluded
                # from the bulk "Sell All Space Junk" option.
                junk_rows = [
                    (item_id, quantity)
                    for item_id, quantity in junk_rows
                    if item_id not in HALLOWEEN_SPACE_JUNK_IDS
                ]


                if not junk_rows:
                    await db.rollback()
                    return await ctx.send(
                        "🎒 **Inventory Empty!** You don't have any normal Space Junk to sell."
                    )

                total_payout = sum(
                    self.JUNK_PRICES[item_id] * quantity
                    for item_id, quantity in junk_rows
                )
                item_count = sum(quantity for _, quantity in junk_rows)

                for item_id, _quantity in junk_rows:
                    await db.execute(
                        """
                        DELETE FROM inventory
                        WHERE user_id = ?
                          AND item_id = ?
                        """,
                        (user_id, item_id),
                    )

                await db.execute(
                    "UPDATE users SET stardust = stardust + ? WHERE user_id = ?",
                    (total_payout, user_id)
                )
                await db.commit()

                return await ctx.send(
                    f"{ctx.author.mention} 🛍️ **Salvage Vendor:** Sold **{item_count} items** "
                    f"for a total of ✨ **{total_payout:,} Stardust**!"
                )

            # ------------------------------------------------------------------
            # Option B: Sell all NORMAL ores & crafting materials.
            # Haunted Ingredients and Halloween materials are excluded.
            # ------------------------------------------------------------------
            if target_item == "all_materials":
                placeholders = ",".join("?" * len(NORMAL_SELL_ALL_MATERIAL_IDS))
                material_ids = tuple(NORMAL_SELL_ALL_MATERIAL_IDS)

                async with db.execute(
                    f"""
                    SELECT item_id, quantity
                    FROM inventory
                    WHERE user_id = ?
                      AND item_id IN ({placeholders})
                      AND quantity > 0
                    """,
                    (user_id, *material_ids)
                ) as cursor:
                    material_rows = await cursor.fetchall()

                if not material_rows:
                    await db.rollback()
                    return await ctx.send(
                        "🎒 **Inventory Empty!** You don't have any normal ores or materials to sell."
                    )

                total_payout = 0
                item_count = 0
                sold_lines = []
                for item_id, owned_quantity in material_rows:
                    info = ITEM_REGISTRY.get(item_id, {})
                    unit_price = int(info.get("sell_price", 0) or 0)
                    if unit_price <= 0:
                        continue
                    total_payout += unit_price * owned_quantity
                    item_count += owned_quantity
                    sold_lines.append(
                        f"{info.get('emoji', '📦')} {info.get('name', item_id)} ×{owned_quantity}"
                    )

                if not sold_lines:
                    await db.rollback()
                    return await ctx.send(
                        "🎒 **Nothing Sellable!** You don't have any priced normal ores or materials."
                    )

                await db.execute(
                    f"""
                    DELETE FROM inventory
                    WHERE user_id = ?
                      AND item_id IN ({placeholders})
                    """,
                    (user_id, *material_ids)
                )
                await db.execute(
                    "UPDATE users SET stardust = stardust + ? WHERE user_id = ?",
                    (total_payout, user_id)
                )
                await db.commit()

                preview = "\n".join(sold_lines[:12])
                if len(sold_lines) > 12:
                    preview += f"\n…and {len(sold_lines) - 12} more."

                return await ctx.send(
                    f"{ctx.author.mention} 🛍️ **Salvage Vendor:** Sold **{item_count} items** "
                    f"for ✨ **{total_payout:,} Stardust**!\n\n"
                    f"🔧 **Materials Sold:**\n{preview}"
                )

            # ------------------------------------------------------------------
            # Option C: Sell a selected quantity of one sellable item.
            # Time Crystals are stored on users.time_crystals, not inventory.
            # ------------------------------------------------------------------
            if target_item == "time_crystal":
                async with db.execute(
                    "SELECT COALESCE(time_crystals, 0) FROM users WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    time_crystal_row = await cursor.fetchone()

                owned_quantity = time_crystal_row[0] if time_crystal_row else 0
                if owned_quantity <= 0:
                    await db.rollback()
                    return await ctx.send("❌ You don't have any **Dilated Time Crystals** to sell.")

                if quantity_is_max:
                    quantity = owned_quantity
                elif quantity > owned_quantity:
                    await db.rollback()
                    return await ctx.send(
                        f"❌ You only have **{owned_quantity}x** **Dilated Time Crystals** in your inventory."
                    )

                unit_payout = int(ITEM_REGISTRY.get("time_crystal", {}).get("sell_price", 0) or 0)
                if unit_payout <= 0:
                    await db.rollback()
                    return await ctx.send("❌ Dilated Time Crystals do not currently have a sell price.")
                payout = unit_payout * quantity
                remaining = owned_quantity - quantity

                await db.execute(
                    "UPDATE users SET time_crystals = ? WHERE user_id = ?",
                    (remaining, user_id)
                )
                await db.execute(
                    "UPDATE users SET stardust = stardust + ? WHERE user_id = ?",
                    (payout, user_id)
                )
                await db.commit()

                return await ctx.send(
                    f"{ctx.author.mention} 🛍️ **Salvage Vendor:** Sold **{quantity}x Dilated Time Crystal** "
                    f"for ✨ **{payout:,} Stardust**!\n"
                    f"📦 **Remaining:** **{remaining}x**"
                )

            async with db.execute(
                """
                SELECT quantity, item_type
                FROM inventory
                WHERE user_id = ?
                  AND item_id = ?
                  AND quantity > 0
                """,
                (user_id, target_item)
            ) as cursor:
                row = await cursor.fetchone()

            info = ITEM_REGISTRY.get(target_item)
            if not row or not info:
                await db.rollback()
                return await ctx.send(
                    f"❌ You don't have `{target_item}` in your inventory, or it isn't sellable."
                )

            owned_quantity, stored_item_type = row
            is_space_junk = (
                str(stored_item_type).lower() == "space_junk"
                or info.get("type") == "Space Junk"
            )

            if is_space_junk:
                if (
                    target_item not in self.JUNK_PRICES
                    and get_halloween_sell_reward(target_item) is None
                ):
                    await db.rollback()
                    return await ctx.send("❌ That Space Junk item cannot be sold.")
                unit_payout, unit_candy_reward = self.get_junk_sell_reward(target_item)
            else:
                unit_payout = int(info.get("sell_price", 0) or 0)
                unit_candy_reward = 0
                item_type = str(info.get("type", ""))
                is_non_sellable_unlock = item_type in {
                    "title", "background_voucher", "station_upgrade"
                }
                is_upgrade_kit = item_type == "Upgrade Component" and target_item in get_upgrade_kit_ids()

                if unit_payout <= 0 or is_non_sellable_unlock or (
                    item_type not in {
                        "Mineral",
                        "Crafting Material",
                        "Haunted Ingredient",
                        "Location-Based Collectible",
                        "Collectible",
                    }
                    and not is_upgrade_kit
                    and target_item not in SELLABLE_ITEM_IDS
                ):
                    await db.rollback()
                    return await ctx.send("❌ That item cannot be sold.")

            if quantity_is_max:
                quantity = owned_quantity
            elif quantity > owned_quantity:
                await db.rollback()
                return await ctx.send(
                    f"❌ You only have **{owned_quantity}x** of **{info['name']}** in your inventory."
                )

            payout = unit_payout * quantity
            candy_reward = unit_candy_reward * quantity
            remaining = owned_quantity - quantity

            if remaining > 0:
                await db.execute(
                    """
                    UPDATE inventory
                    SET quantity = ?
                    WHERE user_id = ? AND item_id = ?
                    """,
                    (remaining, user_id, target_item)
                )
            else:
                await db.execute(
                    "DELETE FROM inventory WHERE user_id = ? AND item_id = ?",
                    (user_id, target_item)
                )

            await db.execute(
                "UPDATE users SET stardust = stardust + ? WHERE user_id = ?",
                (payout, user_id)
            )

            candy_added = 0
            candy_overflow = 0
            if candy_reward > 0:
                candy_added, _, _ = await add_inventory_item(
                    db, user_id, "halloween_candy", "consumable", candy_reward
                )
                candy_overflow = candy_reward - candy_added
                if candy_overflow > 0:
                    overflow_payout = candy_overflow * 5
                    payout += overflow_payout
                    await db.execute(
                        "UPDATE users SET stardust = stardust + ? WHERE user_id = ?",
                        (overflow_payout, user_id)
                    )

            await db.commit()

            candy_text = f" and 🍬 **{candy_added} Halloween Candy**" if candy_added else ""
            overflow_text = (
                f"\n📦 **Candy Overflow:** {candy_overflow} converted to ✨ **{candy_overflow * 5:,} Stardust**"
                if candy_overflow else ""
            )

            await ctx.send(
                f"{ctx.author.mention} 🛍️ **Salvage Vendor:** Sold **{quantity}x {info['name']}** "
                f"for ✨ **{payout:,} Stardust**{candy_text}!\n"
                f"📦 **Remaining:** **{remaining}x**"
                f"{overflow_text}"
            )


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

    @commands.hybrid_command(name="item", description="Inspect an item from the station catalog.")
    @app_commands.describe(category="Choose an item category.", item="Choose an item to inspect.")
    @app_commands.autocomplete(category=item_category_autocomplete, item=item_autocomplete)
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

    @commands.hybrid_command(name="claimlegacy", description="Claim your one-time Stardust bonus for being in the server before the **Frontier** update!")
    async def claim_legacy_bonus(self, ctx: commands.Context):
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

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
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

async def setup(bot):
    await bot.add_cog(Economy(bot))
