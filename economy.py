from emojis import EMOJIS
import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import json
import random
from typing import Any
import datetime
import time
from datetime import datetime, timedelta
import pytz
from seasonal_updates.halloween.halloween import is_active as halloween_is_active
from seasonal_updates.halloween.halloween import HALLOWEEN_SPACE_JUNK, get_sell_reward as get_halloween_sell_reward

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

# Inventory items that can be sold individually through /shop_sell.
# Their Stardust values are defined by ITEM_REGISTRY in inventory.py.
SELLABLE_ITEM_IDS = {'cosmic_insurance', 'drone_battery', 'drone_power_cell', 'drone_quantum_battery', 'fate_anchor', 'fuel_refill', 'fuel_stabilizer', 'full_revive', 'hazard_shield', 'heavy_wrench', 'laser_charge_cell', 'laser_power_cell', 'lucky_scanner', 'makeshift_medkit', 'medkit', 'nanite_patch', 'ore_magnet', 'plasma_cutter', 'prototype_drill_bit', 'revive', 'revive_kit', 'station_rations', 'stick', 'stop_sign', 'wooden_shield', 'wooden_spoon', 'wooden_sword'}


class ShopCategorySelect(discord.ui.Select):
    def __init__(self, shop_view):
        self.shop_view = shop_view

        options = [
            discord.SelectOption(
                label="Healing",
                emoji="❤️",
                value="healing",
                description="Nanite patches, medkits, and revival items."
            ),
            discord.SelectOption(
                label="Recharge",
                emoji="🔋",
                value="recharge",
                description="Mining laser and scavenging drone recharge items."
            ),
            discord.SelectOption(
                label="Upgrades",
                emoji="🛠️",
                value="upgrades",
                description="Temporary equipment and exploration upgrades."
            ),
            discord.SelectOption(
                label="Pet Items",
                emoji="🐾",
                value="pet_items",
                description="Items for your station pet."
            ),
            discord.SelectOption(
                label="Special",
                emoji="✨",
                value="special",
                description="Rare and unusual station items."
            ),
            discord.SelectOption(
                label="Lottery",
                emoji="🎟️",
                value="lottery",
                description="Monthly Stardust lottery tickets."
            ),
            discord.SelectOption(
                label="Backgrounds",
                emoji="🖼️",
                value="backgrounds",
                description="Profile background vouchers."
            ),
            discord.SelectOption(
                label="Daily Offers",
                emoji="🔄",
                value="daily",
                description="Today's rotating station offers."
            ),
        ]

        super().__init__(
            placeholder="📂 Select a shop category...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.shop_view.user_id:
            return await interaction.response.send_message(
                "⚠️ This shop menu belongs to the person who opened it.",
                ephemeral=True
            )

        category = self.values[0]

        embed = self.shop_view.build_embed(category)

        await interaction.response.edit_message(
            embed=embed,
            view=self.shop_view
        )


class ShopView(discord.ui.View):
    def __init__(self, cog, user_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id

        self.add_item(ShopCategorySelect(self))

    def build_embed(self, category):
        cog = self.cog

        embed = discord.Embed(
            title="🛒 Enceladus Station Trading Post",
            color=discord.Color.from_rgb(0, 229, 255)
        )

        if category == "healing":
            embed.description = (
                "❤️ **Medical Supplies**\n"
                "Keep yourself alive out there, explorer."
            )

            item_ids = [
                "nanite_patch",
                "medkit",
                "revive",
                "full_revive",
            ]

        elif category == "recharge":
            embed.description = (
                "🔋 **Power & Recharge Supplies**\n"
                "Restore charges to your mining laser or scavenging drone."
            )

            item_ids = [
                "laser_charge_cell",
                "laser_power_cell",
                "fuel_refill",
                "drone_battery",
                "drone_power_cell",
                "drone_quantum_battery",
            ]

        elif category == "upgrades":
            embed.description = (
                "🛠️ **Station Upgrades**\n"
                "Permanent equipment and station expansions."
            )

            item_ids = [
                "incubator_2",
                "incubator_3",
                "vault_expansion",
                "fuel_stabilizer",
                "hazard_shield",
                "lucky_scanner",
                "prototype_drill_bit",
            ]

        elif category == "pet_items":
            embed.description = (
                "🐾 **Pet Supplies**\n"
                "Because even station companions need snacks."
            )

            item_ids = [
                "pet_snack",
            ]

        elif category == "special":
            embed.description = (
                "✨ **Special Items**\n"
                "Unusual technology with unusual consequences."
            )

            item_ids = [
                "time_crystal",
                "astral_essence",
            ]

        elif category == "lottery":
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

        elif category == "backgrounds":
            embed.description = (
                "🖼️ **Profile Backgrounds**\n"
                "Customize the look of your station profile."
            )

            item_ids = [
                "neon_grid",
                "deep_void",
                "solaris_ring",
            ]

        elif category == "daily":
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

                if is_permanent:
                    daily_cost = int(item["cost"] * 0.85)
                    price_text = (
                        f"💰 ~~{item['cost']:,}~~ → **{daily_cost:,} Stardust** 🔥\n"
                        "🏷️ **15% Daily Discount**"
                    )
                else:
                    daily_cost = item["cost"]
                    price_text = f"💰 Price: **{daily_cost:,} Stardust**"

                limit_text = cog.shop_limit_text(item_id)

                embed.add_field(
                    name=item["name"],
                    value=(
                        f"{price_text}\n"
                        f"📖 {item['desc']}\n"
                        f"📦 **Purchase Limit:** "
                        f"{limit_text.lstrip(' • Limit: ') if limit_text else 'None'}"
                    ),
                    inline=False
                )

            embed.set_footer(
                text="Use /shop_buy to purchase an item."
            )

            return embed

        else:
            item_ids = []

        for item_id in item_ids:
            item = cog.SHOP_ITEMS.get(item_id) or cog.ROTATING_ITEMS.get(item_id)

            if not item:
                continue

            limit_text = cog.shop_limit_text(item_id)

            embed.add_field(
                name=item["name"],
                value=(
                    f"💰 Price: **{item['cost']:,} Stardust**\n"
                    f"📖 {item['desc']}\n"
                    f"📦 **Purchase Limit:** "
                    f"{limit_text.lstrip(' • Limit: ') if limit_text else 'None'}"
                ),
                inline=False
            )

        embed.set_footer(
            text="Use /shop_buy to purchase an item."
        )

        return embed

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.DEFAULT_VAULT_CAPACITY = 250_000
        self.MAX_VAULT_CAPACITY = 500_000
        
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
        """Return the same three distinct offers for every user on a given day.

        Daily Offers feature permanent shop items or rotation-only items, but exclude
        backgrounds and titles. Rotation-only items receive no permanent-item discount.
        """
        excluded_types = {"background_voucher", "title", "station_upgrade"}
        eligible_items = []

        for item_id, item in self.SHOP_ITEMS.items():
            if item.get("type") not in excluded_types:
                eligible_items.append(item_id)

        for item_id, item in self.ROTATING_ITEMS.items():
            if item.get("halloween_only") and not halloween_is_active():
                continue
            if item.get("type") not in excluded_types and item_id not in eligible_items:
                eligible_items.append(item_id)

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

        
    @commands.hybrid_command(
        name="balance",
        aliases=["bal"],
        description="View your spendable Stardust, vault balance, and total."
    )
    async def balance(self, ctx: commands.Context):
        """Show your available Stardust, vault balance, and total."""
        user_id = ctx.author.id
        db_path = self.get_db_path()

        async with aiosqlite.connect(db_path) as db:
            await self.ensure_schema(db)
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, stardust, vault_stardust) VALUES (?, 0, 0)",
                (user_id,)
            )
            await db.commit()

            async with db.execute(
                "SELECT COALESCE(stardust, 0), COALESCE(vault_stardust, 0), COALESCE(vault_capacity, ?) FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()

        stardust = row[0] if row else 0
        vault = row[1] if row else 0
        total = stardust + vault

        embed = discord.Embed(
            title=f"💰 {ctx.author.display_name}'s Stardust Balance",
            description=(
                f"💫 **Available:** {stardust:,} Stardust\n"
                f"🔐 **Vault:** {vault:,} Stardust\n\n"
                f"📊 **Total owned:** {total:,} Stardust"
            ),
            color=discord.Color.from_rgb(0, 229, 255)
        )
        embed.add_field(
            name="🔐 Vault",
            value=(
                "Stardust stored here is protected from normal spending. "
                "Use `/bank deposit` to store Stardust and `/bank withdraw` to take it back out."
            ),
            inline=False
        )
        embed.set_footer(text="Enceladus Station Economy")

        await ctx.send(embed=embed)

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
                    COALESCE(last_daily, ''), COALESCE(hp, 100)
                FROM users
                WHERE user_id = ?
                """,
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()

            stardust, streak, last_daily, hp = row if row else (0, 0, "", 100)

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

            # Daily also restores +50 HP, regardless of current HP, capped at 100.
            # If the user was knocked out (0 HP), clearing knocked_out_until revives them.
            new_hp = min(100, hp + 50)

            await db.execute(
                """
                UPDATE users
                SET stardust = ?, daily_streak = ?, last_daily = ?,
                    hp = ?, knocked_out_until = ''
                WHERE user_id = ?
                """,
                (new_stardust, new_streak, today_str, new_hp, user_id)
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

    @commands.hybrid_command(name="bank", description="View your current Stardust balance and vaulted Stardust.")
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
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, stardust, vault_stardust) VALUES (?, 0, 0)",
                (user_id,)
            )
            await db.commit()

            await db.execute("BEGIN IMMEDIATE")
            async with db.execute(
                "SELECT COALESCE(stardust, 0), COALESCE(vault_stardust, 0) FROM users WHERE user_id = ?",
                (self.DEFAULT_VAULT_CAPACITY, user_id)
            ) as cursor:
                row = await cursor.fetchone()

            stardust, vault, vault_capacity = (
                row if row else (0, 0, self.DEFAULT_VAULT_CAPACITY)
            )

            if amount > stardust:
                await db.rollback()
                return await ctx.send(
                    f"💸 You only have **{stardust:,} Stardust** available to deposit."
                )

            if vault + amount > vault_capacity:
                await db.rollback()
                remaining_space = max(0, vault_capacity - vault)
                return await ctx.send(
                    f"🔐 Your vault can only hold **{vault_capacity:,} Stardust**. "
                    f"You can deposit **{remaining_space:,}** Stardust."
                )

            await db.execute(
                "UPDATE users SET stardust = ?, vault_stardust = ? WHERE user_id = ?",
                (stardust - amount, vault + amount, user_id)
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

    @commands.hybrid_command(
        name="shop",
        description="Open the Enceladus Station Trading Post."
    )
    async def shop(self, ctx: commands.Context):
        view = ShopView(self, ctx.author.id)

        embed = view.build_embed("healing")

        await ctx.send(
            embed=embed,
            view=view
        )

    async def shop_buy_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ):
        """Show items currently available in the station shop."""
        current = current.lower().strip()

        # Application-command autocomplete choices do not render Discord's
        # custom-emoji markup, so use normal Unicode emojis for the picker.
        autocomplete_emojis = {
            "nanite_patch": "🩹",
            "medkit": "🧰",
            "revive": "⚕️",
            "full_revive": "💉",
            "laser_charge_cell": "🔋",
            "laser_power_cell": "⚡",
            "fuel_refill": "⚛️",
            "drone_battery": "🔋",
            "drone_power_cell": "⚡",
            "drone_quantum_battery": "⚛️",
            "pet_snack": "🍪",
            "time_crystal": "💎",
            "astral_essence": "✨",
            "neon_grid": "🌆",
            "deep_void": "🌌",
            "solaris_ring": "💫",
            "fuel_stabilizer": "🛢️",
            "hazard_shield": "🛡️",
            "lucky_scanner": "📡",
            "prototype_drill_bit": "⚙️",
            "station_rations": "🥫",
            "ore_magnet": "🧲",
            "cosmic_insurance": "📋",
            "fate_anchor": "⚓",
            "revive_kit": "💉",
            "stop_sign": "🛑",
            "stick": "🪵",
            "wooden_sword": "🗡️",
            "wooden_shield": "🛡️",
            "wooden_spoon": "🥄",
            "heavy_wrench": "🔧",
            "plasma_cutter": "🔫",
            "title_outer_rim_wanderer": "🏷️",
            "title_starborn": "🏷️",
            "title_voidfarer": "🏷️",
        }

        def autocomplete_name(item_id, info):
            raw_name = info["name"]
            fallback_emoji = autocomplete_emojis.get(item_id, "📦")

            # The catalog's display names may contain custom Discord emoji
            # markup. For autocomplete, strip that markup and prepend a
            # renderable Unicode emoji instead.
            if raw_name.startswith("<:") or raw_name.startswith("<a:"):
                closing = raw_name.find(">")

                if closing != -1:
                    raw_name = raw_name[closing + 1:].lstrip()

            return f"{fallback_emoji} {raw_name}"

        available_items = []
        seen_items = set()

        # Permanent shop items.
        for item_id, info in self.SHOP_ITEMS.items():
            display_name = autocomplete_name(item_id, info)

            if current and current not in display_name.lower():
                continue

            available_items.append(
                app_commands.Choice(
                    name=display_name,
                    value=item_id
                )
            )
            seen_items.add(item_id)

        # Today's rotating-only items.
        for item_id in self.daily_rotation():
            if item_id in seen_items:
                continue

            info = self.ROTATING_ITEMS.get(item_id)
            if not info:
                continue

            display_name = autocomplete_name(item_id, info)

            if current and current not in display_name.lower():
                continue

            available_items.append(
                app_commands.Choice(
                    name=display_name,
                    value=item_id
                )
            )
            seen_items.add(item_id)

        available_items.sort(key=lambda choice: choice.name.lower())

        return available_items[:25]

    @commands.hybrid_command(name="shop_buy", description="Purchase an item from the station vendor catalog.")
    @app_commands.rename(item_id="item")
    @app_commands.describe(item_id="Choose an item to purchase.", quantity="How many would you like to buy? (1-99)")
    @app_commands.autocomplete(item_id=shop_buy_autocomplete)
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

            if item["type"] == "station_upgrade":
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
            if item["type"] == "background_voucher" and quantity != 1:
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

            if item["type"] == "revive":
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

            if item["type"] == "consumable" and item_id in {
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

            if item["type"] == "consumable" and item_id == "pet_snack":
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

            if item["type"] == "background_voucher":
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

            if item["type"] == "heal":
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

    @commands.hybrid_command(name="salvage", description="Scrap Space Junk for crafting materials.")
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

        async with aiosqlite.connect(db_path) as db:
            await db.execute("BEGIN IMMEDIATE")

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

    async def shop_sell_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ):
        """Show sellable items the user currently owns."""
        user_id = interaction.user.id
        current = current.lower().strip()

        from inventory import ITEM_REGISTRY

        async with aiosqlite.connect(self.get_db_path()) as db:
            async with db.execute(
                """
                SELECT item_id, quantity, item_type
                FROM inventory
                WHERE user_id = ?
                  AND quantity > 0
                ORDER BY item_id
                """,
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()

        # Application-command autocomplete does not reliably render Discord
        # custom-emoji markup, so use normal Unicode fallbacks for sell choices.
        sell_autocomplete_emojis = {
            # Materials / ores
            "iron_ore": "⛏️",
            "copper_ore": "🟠",
            "titanium_chunk": "⛏️",
            "aluminum_ore": "⬜",
            "circuit_board": "🟩",
            "glue": "🧴",
            "scrap_metal": "🔩",
            "nuts_bolts": "🔧",
            "wiring": "🧵",
            "time_crystal": "💎",
            # Haunted / seasonal materials
            "haunted_circuit": "⚡",
            "screaming_crystal": "💎",
            # Space Junk
            "space_pizza": "🍕",
            "floppy_disk": "💾",
            "meteorite": "☄️",
            "rubber_duck": "🦆",
            "rusty_gear": "⚙️",
            "tape_deck": "📼",
            "alien_artifact": "👽",
            "space_boot": "🥾",
            "holo_poster": "🖼️",
            "broken_laser": "🔧",
            "lost_logbook": "📓",
            "left_sock": "🧦",
            "warp_mug": "☕",
            "space_pudding": "🍮",
            "tangled_cables": "🪢",
            "moon_cheese": "🧀",
            "golden_spatula": "🥄",
            "parking_ticket": "🎫",
            "floating_plant": "🪴",
            "tinted_visor": "🕶️",
            "purring_lint": "🧶",
            "pet_rock": "🪨",
            "space_taco": "🌮",
            "rusty_wrench": "🔧",
            "alien_fossil": "🦴",
            "big_red_button": "🔴",
            "antique_compass": "🧭",
            "broken_clock": "🕰️",
            "perplexing_painting": "🖼️",
            "cosmic_banana": "🍌",
            "cosmic_coin": "🪙",
        }

        choices = []
        sellable_rows = []

        # Time Crystals are stored on the users table rather than the inventory
        # table, so add them to the sell list separately.
        async with aiosqlite.connect(self.get_db_path()) as db:
            async with db.execute(
                "SELECT COALESCE(time_crystals, 0) FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                time_crystal_row = await cursor.fetchone()

        time_crystal_quantity = time_crystal_row[0] if time_crystal_row else 0
        if time_crystal_quantity > 0:
            time_crystal_info = ITEM_REGISTRY.get("time_crystal", {})
            display_name = time_crystal_info.get("name", "Dilated Time Crystal")
            search_text = f"{display_name} time_crystal".lower()
            if not current or current in search_text:
                choices.append(
                    app_commands.Choice(
                        name=f"💎 {display_name} (x{time_crystal_quantity})",
                        value="time_crystal"
                    )
                )

        for item_id, owned_quantity, item_type in rows:
            info = ITEM_REGISTRY.get(item_id)
            if not info:
                continue

            # Space Junk can be sold using the existing normal buyback table
            # or the Halloween-specific Stardust + Candy reward.
            is_space_junk = str(item_type).lower() == "space_junk" or info.get("type") == "Space Junk"
            is_material = bool(info.get("sell_price")) and info.get("type") in {
                "Mineral",
                "Crafting Material",
                "Haunted Ingredient",
            }
            is_sellable_item = item_id in SELLABLE_ITEM_IDS and bool(info.get("sell_price"))

            if not is_space_junk and not is_material and not is_sellable_item:
                continue

            if is_space_junk:
                if (
                    item_id not in self.JUNK_PRICES
                    and get_halloween_sell_reward(item_id) is None
                ):
                    continue
            elif not info.get("sell_price"):
                continue

            sellable_rows.append((item_id, owned_quantity, info, is_space_junk))

        normal_junk_owned = any(
            is_space_junk and item_id in self.JUNK_PRICES
            for item_id, _quantity, _info, is_space_junk in sellable_rows
        )
        normal_material_owned = any(
            item_id in NORMAL_SELL_ALL_MATERIAL_IDS
            for item_id, _quantity, _info, _is_space_junk in sellable_rows
        )

        # Bulk options are deliberately separate so limited-time Halloween
        # Space Junk and Haunted ingredients can never be swept up accidentally.
        show_all = not current or "all" in current or "sell all" in current
        show_junk_all = show_all or "junk" in current or "space junk" in current
        show_material_all = show_all or "material" in current or "ore" in current

        if normal_junk_owned and show_junk_all:
            choices.append(
                app_commands.Choice(
                    name="🗑️ Sell All Space Junk",
                    value="all_junk"
                )
            )

        if normal_material_owned and show_material_all:
            choices.append(
                app_commands.Choice(
                    name="🔧 Sell All Ores & Materials",
                    value="all_materials"
                )
            )

        for item_id, owned_quantity, info, _is_space_junk in sellable_rows:
            display_name = info["name"]
            search_text = f"{display_name} {item_id}".lower()

            raw_emoji = str(info.get("emoji", ""))
            if raw_emoji.startswith("<:") or raw_emoji.startswith("<a:"):
                display_emoji = sell_autocomplete_emojis.get(item_id, "📦")
            else:
                display_emoji = raw_emoji or sell_autocomplete_emojis.get(item_id, "📦")
            if current and current not in search_text:
                continue

            choices.append(
                app_commands.Choice(
                    name=f"{display_emoji} {display_name} (x{owned_quantity})",
                    value=item_id
                )
            )

        bulk_choices = [
            choice for choice in choices
            if choice.value in {"all_junk", "all_materials"}
        ]
        item_choices = [
            choice for choice in choices
            if choice.value not in {"all_junk", "all_materials"}
        ]
        item_choices.sort(key=lambda choice: choice.name.lower())

        return (bulk_choices + item_choices)[:25]


    @commands.hybrid_command(
        name="shop_sell",
        description="Sell Time Crystals, materials, equipment, and Space Junk for Stardust."
    )
    @app_commands.describe(
        item="Choose an item to sell, sell all normal Space Junk, or sell all normal ores & materials.",
        quantity="How many to sell (1-99).",
    )
    @app_commands.autocomplete(item=shop_sell_autocomplete)
    async def sell(
        self,
        ctx: commands.Context,
        item: str,
        quantity: int = 1
    ):
        await ctx.defer()

        user_id = ctx.author.id
        target_item = item.lower().strip()
        db_path = self.get_db_path()

        if quantity < 1 or quantity > 99:
            return await ctx.send("❌ Quantity must be between **1 and 99**.")

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

                if quantity > owned_quantity:
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
                if unit_payout <= 0 or (
                    info.get("type") not in {
                        "Mineral",
                        "Crafting Material",
                        "Haunted Ingredient",
                    }
                    and target_item not in SELLABLE_ITEM_IDS
                ):
                    await db.rollback()
                    return await ctx.send("❌ That item cannot be sold.")

            if quantity > owned_quantity:
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

        joined_at = ctx.author.joined_at

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
