import asyncio
import random
import time
from typing import cast

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands, tasks

from database import ECONOMY_DB_NAME
from inventory import add_inventory_item, ITEM_REGISTRY
from seasonal_updates.halloween import is_active as halloween_is_active


# ============================================================================
# PET CONFIGURATION
# ============================================================================
# This is intentionally kept very easy to edit.
#
# Add normal pets to PETS and Halloween pets to HALLOWEEN_PETS.
#
# Passive effect IDs currently supported:
#   stardust_bonus       -> percentage bonus to Stardust
#   material_bonus       -> chance to add +1 to a successful material find
#   rare_loot_bonus      -> percentage added to scavenging rare-loot thresholds
#   hazard_reduction     -> percentage reduction to scavenging hazard damage
#   charge_save          -> chance to avoid consuming an exploration charge
#   cooldown_reduction   -> percentage reduction to exploration cooldown
#   halloween_bonus      -> chance to gain an extra Halloween seasonal item
#   treat_xp_bonus       -> percentage bonus to Pet XP from treats
#   candy_bonus          -> chance to double Halloween Candy
#
# "levels" contains the passive's strength at passive levels 1-5.
# Pets can continue leveling past 5, but passive strength stops increasing at 5
# so higher levels remain available for future/cosmetic systems.
# ============================================================================

PET_PASSIVE_MAX_LEVEL = 5

PETS = {
    # ------------------------------------------------------------------
    # NORMAL PET PLACEHOLDERS — edit these!
    # ------------------------------------------------------------------
    "space_cat": {
        "name": "Space Cat",
        "emoji": "🐱",
        "description": "An orange kitty that's somehow able to breath in space! *He only comes with one braincell, sorry.*",
        "egg": "normal_egg",
        "passive": {
            "id": "stardust_bonus",
            "name": "Lucky Paws",
            "description": "Finds a little extra Stardust during exploration.",
            "levels": [0.01, 0.02, 0.03, 0.04, 0.05],
        },
    },
    "cosmic_fox": {
        "name": "Cosmic Fox",
        "emoji": "🦊",
        "description": "A cute fox, but with cosmic colors, and somehow able to breathe in space!",
        "egg": "normal_egg",
        "passive": {
            "id": "material_bonus",
            "name": "Scavenger's Instinct",
            "description": "Sometimes finds an extra unit when recovering materials.",
            "levels": [0.02, 0.04, 0.06, 0.08, 0.10],
        },
    },
    "astronaut_turtle": {
        "name": "Astronaut Turtle",
        "emoji": "🐢",
        "description": "A little turtle with an astronaut helmet!",
        "egg": "normal_egg",
        "passive": {
            "id": "hazard_reduction",
            "name": "Heavy Shell",
            "description": "Reduces damage taken from scavenging hazards.",
            "levels": [0.02, 0.04, 0.06, 0.08, 0.10],
        },
    },
    "busted_drone": {
        "name": "Busted-up Drone",
        "emoji": "🛸",
        "description": "A busted up drone. Looks like it was in war. Still works... somewhat. It seems fond of you! (Likes to make little happy, beepy noises!)",
        "egg": "normal_egg",
        "passive": {
            "id": "charge_save",
            "name": "Helping Hand",
            "description": "The drone may be busted, but still wishes to help! Has a chance for you to not consume a charge for your laser or scavenging drone.",
            "levels": [0.05, 0.07, 0.10, 0.15, 0.20],
        },
    },
    "cosmic_owl": {
        "name": "Cosmic Owl",
        "emoji": "🦉",
        "description": "An abnormally large owl, coated in cosmic colors. Staring into its eyes is like gazing into space itself, giving you immense wisdom.",
        "egg": "normal_egg",
        "passive": {
            "id": "cooldown_reduction",
            "name": "Cosmic Wisdom",
            "description": "You gaze into the owls eyes... it fills you with wisdom. It now reduces the cooldown for your laser and scavenging drone!",
            "levels": [0.05, 0.10, 0.20, 0.25, 0.30],
        },
    },
}

HALLOWEEN_PETS = {
    # ------------------------------------------------------------------
    # HALLOWEEN PET PLACEHOLDERS — edit these!
    # ------------------------------------------------------------------
    "pumpkin_pup": {
        "name": "Pumpkin Pup",
        "emoji": "🎃",
        "description": "A little puppy with a pumpkin on its head!",
        "egg": "halloween_egg",
        "passive": {
            "id": "stardust_bonus",
            "name": "Trickster's Luck",
            "description": "A spooky little bonus to Stardust from exploration.",
            "levels": [0.01, 0.02, 0.03, 0.04, 0.05],
        },
    },
    "black_cat": {
        "name": "Black Witchy Cat",
        "emoji": "🐈‍⬛",
        "description": "A black kitty with a witch hat! How adorable and spooky!",
        "egg": "halloween_egg",
        "passive": {
            "id": "rare_loot_bonus",
            "name": "Ghostly Luck",
            "description": "Slightly improves the chance of finding rare scavenging loot.",
            "levels": [0.005, 0.008, 0.011, 0.014, 0.017],
        },
    },
    "vampire_bat": {
        "name": "Vampire Bat",
        "emoji": "🦇",
        "description": "A fluttering bat who, for some reason, doesn't want to bite you. Maybe you taste bad, or it likes you!",
        "egg": "halloween_egg",
        "passive": {
            "id": "hazard_reduction",
            "name": "Nightmare Dodge",
            "description": "Reduces damage from scavenging hazards.",
            "levels": [0.02, 0.04, 0.06, 0.08, 0.15],
        },
    },
    "godzilla": {
        "name": "Godzilla",
        "emoji": "🦖",
        "description": "The King of Monsters himself, Godzilla! He'll blast through incoming hazards and protect you!",
        "egg": "halloween_egg",
        "passive": {
            "id": "atomic_breath",
            "name": "Atomic Breath",
            "description": "Godzilla can blast incoming scavenging hazards before they reach you with his Atomic Breath.",
            "levels": [0.15, 0.20, 0.25, 0.30, 0.35],
        },
    },
    "skeleton_dragon": {
        "name": "Skeleton Dragon",
        "emoji": "🐲",
        "description": "A big skeleton dragon! Undead never seemed so awesome and powerful!",
        "egg": "halloween_egg",
        "passive": {
            "id": "halloween_bonus",
            "name": "Hallows Hoard",
            "description": "Improves the chance of finding an additonal Halloween-themed item by the dragon digging through its hoard.",
            "levels": [0.015, 0.025, 0.035, 0.040, 0.050],
        },
    },
    "samhain": {
        "name": "Samhain",
        "emoji": "🎃",
        "description": "A mysterious, sack-headed trick-or-treater who enforces the sacred rules of Halloween. If you refuse him a treat or blow out your Jack-o'-Lantern early, he'll make sure you face a terrifying trick.",
        "egg": "halloween_egg",
        "passive": {
            "id": "candy_bonus",
            "name": "Trick 'r Treat",
            "description": "Sam appreciates you loving Halloween! He has a chance for you to get extra candy!",
            "levels": [0.10, 0.20, 0.30, 0.40, 0.50],
        },
    },
    "flytrap": {
        "name": "The Feed Me",
        "emoji": "🪴",
        "description": "A demanding, fast-growing alien flytrap sitting in a cracked clay pot. It snaps its jaw impatiently whenever your skills are inactive!",
        "egg": "halloween_egg",
        "passive": {
            "id": "cooldown_reduction",
            "name": "Blood Rush",
            "description": "The plant's insatiable hunger drives you forward. It reduces the cooldown for your laser and scavenging drone!",
            "levels": [0.10, 0.15, 0.20, 0.30, 0.35],
        },
    },
}

ALL_PETS = {**PETS, **HALLOWEEN_PETS}

EGG_POOLS = {
    "normal_egg": [pet_id for pet_id, pet in PETS.items() if pet["egg"] == "normal_egg"],
    "halloween_egg": [
        pet_id for pet_id, pet in HALLOWEEN_PETS.items()
        if pet["egg"] == "halloween_egg"
    ],
}

# Pet progression tuning.
# Exploration grants a small amount of ordinary XP.
PET_XP_PER_EXPLORATION = 5
PET_TREAT_XP = 25
HALLOWEEN_PET_CANDY_XP = 100

# Egg drops are independent bonus rolls during scavenging.
NORMAL_EGG_CHANCE = 0.15
HALLOWEEN_EGG_CHANCE = 1 / 35

INCUBATION_SECONDS = 12 * 60 * 60
INCUBATOR_NOTIFICATION_CHANNEL_ID = 1548034265508356166


def xp_needed_for_next_level(level: int) -> int:
    """XP needed to advance from the supplied level to the next one."""
    return 100 + max(0, level - 1) * 50


def passive_level_for_pet(level: int) -> int:
    return min(PET_PASSIVE_MAX_LEVEL, max(1, level))


def get_pet_definition(pet_type: str):
    return ALL_PETS.get(pet_type)


def get_passive_value(pet: dict, level: int | None = None) -> float:
    passive = pet.get("passive", {})
    values = passive.get("levels", [])
    if not values:
        return 0.0

    passive_level = passive_level_for_pet(level if level is not None else 1)
    index = min(len(values), passive_level) - 1
    return float(values[index])


async def get_active_pet(db, user_id: int):
    async with db.execute(
        """
        SELECT pet_id, pet_type, pet_stage, nickname, level, xp
        FROM pets
        WHERE user_id = ? AND is_active = 1
        ORDER BY pet_id DESC
        LIMIT 1
        """,
        (user_id,),
    ) as cursor:
        row = await cursor.fetchone()

    if not row:
        return None

    pet_id, pet_type, pet_stage, nickname, level, xp = row
    definition = get_pet_definition(pet_type or pet_stage)
    if not definition:
        return {
            "pet_id": pet_id,
            "pet_type": pet_type or pet_stage,
            "name": (pet_type or pet_stage or "Unknown Pet").replace("_", " ").title(),
            "emoji": "🐾",
            "description": "Unknown pet.",
            "nickname": nickname,
            "level": level or 1,
            "xp": xp or 0,
            "passive": {},
        }

    return {
        "pet_id": pet_id,
        "pet_type": pet_type,
        "name": definition["name"],
        "emoji": definition["emoji"],
        "description": definition["description"],
        "nickname": nickname,
        "level": level or 1,
        "xp": xp or 0,
        "passive": definition.get("passive", {}),
    }


async def get_active_pet_effects(db, user_id: int):
    """
    Return the active pet's currently effective passive values.

    This helper accepts an existing DB connection so exploration does not open
    another SQLite connection while it is already inside its transaction.
    """
    pet = await get_active_pet(db, user_id)
    if not pet:
        return {
            "level": 0,
            "passive_level": 0,
            "stardust_bonus": 0.0,
            "material_bonus": 0.0,
            "rare_bonus": 0.0,
            "hazard_reduction": 0.0,
            "charge_save": 0.0,
            "cooldown_reduction": 0.0,
            "halloween_bonus": 0.0,
            "treat_xp_bonus": 0.0,
            "atomic_breath": 0.0,
            "candy_bonus": 0.0,
        }

    passive = pet.get("passive", {})
    value = get_passive_value(pet, pet["level"])
    effect_id = passive.get("id")

    effects = {
        "level": pet["level"],
        "passive_level": passive_level_for_pet(pet["level"]),
        "stardust_bonus": 0.0,
        "material_bonus": 0.0,
        "rare_bonus": 0.0,
        "hazard_reduction": 0.0,
        "charge_save": 0.0,
        "cooldown_reduction": 0.0,
        "halloween_bonus": 0.0,
        "treat_xp_bonus": 0.0,
        "atomic_breath": 0.0,
        "candy_bonus": 0.0,
    }

    if effect_id == "stardust_bonus":
        effects["stardust_bonus"] = value
    elif effect_id == "material_bonus":
        effects["material_bonus"] = value
    elif effect_id == "rare_loot_bonus":
        effects["rare_bonus"] = value
    elif effect_id == "hazard_reduction":
        effects["hazard_reduction"] = value
    elif effect_id == "charge_save":
        effects["charge_save"] = value
    elif effect_id == "cooldown_reduction":
        effects["cooldown_reduction"] = value
    elif effect_id == "halloween_bonus":
        effects["halloween_bonus"] = value
    elif effect_id == "treat_xp_bonus":
        effects["treat_xp_bonus"] = value
    elif effect_id == "atomic_breath":
        effects["atomic_breath"] = value
    elif effect_id == "candy_bonus":
        effects["candy_bonus"] = value

    return effects


async def add_pet_xp(db, user_id: int, amount: int):
    """Add pet XP to the active pet and handle multiple level-ups."""
    if amount <= 0:
        return None

    pet = await get_active_pet(db, user_id)
    if not pet:
        return None

    old_level = pet["level"]
    new_level = old_level
    new_xp = pet["xp"] + amount

    while new_xp >= xp_needed_for_next_level(new_level):
        new_xp -= xp_needed_for_next_level(new_level)
        new_level += 1

    await db.execute(
        """
        UPDATE pets
        SET level = ?, xp = ?
        WHERE pet_id = ?
        """,
        (new_level, new_xp, pet["pet_id"]),
    )

    return {
        "old_level": old_level,
        "new_level": new_level,
        "xp_added": amount,
        "leveled_up": new_level > old_level,
        "passive_level": passive_level_for_pet(new_level),
        "xp": new_xp,
        "xp_needed": xp_needed_for_next_level(new_level),
    }



class FeedTreatSelect(discord.ui.Select):
    def __init__(self, cog, user_id, pet_id, owned, parent_message, ctx):
        options = []
        for item_id, label, emoji in (
            ("pet_snack", "Pet Treat", "🍖"),
            ("halloween_pet_candy", "Halloween Pet Candy", "🎃"),
        ):
            quantity = owned.get(item_id, 0)
            if quantity <= 0:
                continue
            options.append(discord.SelectOption(
                label=f"{label} ×{quantity}",
                value=item_id,
                emoji=emoji,
                description="Feed this treat to the selected pet.",
            ))
        super().__init__(placeholder="Choose a treat...", min_values=1, max_values=1, options=options)
        self.cog = cog
        self.user_id = user_id
        self.pet_id = pet_id
        self.parent_message = parent_message
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This treat menu isn't for you.", ephemeral=True)
        result, error = await self.cog._feed_specific_pet(self.user_id, self.pet_id, self.values[0])
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        pet = result["pet"]
        level_line = ""
        if result["leveled_up"]:
            level_line = (
                f"\n🎉 **Level Up!** Your pet reached **Level {result['new_level']}**!"
                f"\n✨ Passive is now **Level {result['passive_level']}/{PET_PASSIVE_MAX_LEVEL}**."
            )
        await interaction.response.send_message(
            f"{pet['emoji']} **{pet['nickname'] or pet['name']}** enjoyed the "
            f"**{result['treat']['name']}**!\n✨ **+{result['xp_amount']} Pet XP**{level_line}",
            ephemeral=True,
        )
        await self.cog._refresh_pet_view(self.parent_message, self.user_id, self.pet_id, ctx=self.ctx)


class FeedTreatView(discord.ui.View):
    def __init__(self, cog, user_id, pet_id, owned, parent_message, ctx):
        super().__init__(timeout=60)
        self.parent_message = parent_message
        self.add_item(FeedTreatSelect(cog, user_id, pet_id, owned, parent_message, ctx))


class ReleaseConfirmationView(discord.ui.View):
    def __init__(self, cog, user_id, pet, parent_message, ctx):
        super().__init__(timeout=30)
        self.cog = cog
        self.user_id = user_id
        self.pet_id = pet["pet_id"]
        self.pet = pet
        self.parent_message = parent_message
        self.ctx = ctx

    @discord.ui.button(label="Yes, Release Pet", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This confirmation isn't for you.", ephemeral=True)
        released = await self.cog._release_pet(self.user_id, self.pet_id)
        if not released:
            self.stop()
            return await interaction.response.edit_message(content="❌ That pet could not be released because it no longer exists.", view=None)
        if released.get("protected"):
            self.stop()
            return await interaction.response.edit_message(
                content="🔒 **This pet is favorited and protected!** Unfavorite it first if you really want to release it.",
                view=None,
            )
        self.stop()
        await interaction.response.edit_message(
            content=(
                f"🔴 Released **{released['emoji']} {released['nickname'] or released['name']}** "
                f"(Level {released['level']}).\n\nThis pet has been permanently removed from your collection."
            ),
            view=None,
        )
        await self.cog._refresh_pet_view(self.parent_message, self.user_id, self.pet_id, allow_missing=True, ctx=self.ctx)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This confirmation isn't for you.", ephemeral=True)
        self.stop()
        await interaction.response.edit_message(content="Release cancelled. 👍", view=None)



class RenamePetModal(discord.ui.Modal):
    def __init__(self, cog, user_id, pet_id, parent_message, ctx):
        super().__init__(title="Rename Pet", timeout=120)
        self.cog = cog
        self.user_id = user_id
        self.pet_id = pet_id
        self.parent_message = parent_message
        self.ctx = ctx

        self.name_input = discord.ui.TextInput(
            label="Pet Name",
            placeholder="Enter a new name (30 characters max)",
            max_length=30,
            required=False,
        )
        self.add_item(self.name_input)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "❌ This rename menu isn't for you.", ephemeral=True
            )

        new_name = str(self.name_input.value).strip()
        if len(new_name) > 30:
            return await interaction.response.send_message(
                "❌ Pet names can be at most **30 characters** long.",
                ephemeral=True,
            )

        renamed = await self.cog._rename_pet(self.user_id, self.pet_id, new_name)
        if not renamed:
            return await interaction.response.send_message(
                "❌ That pet no longer exists in your collection.",
                ephemeral=True,
            )

        display_name = renamed["nickname"] or renamed["name"]
        if renamed["nickname"]:
            message = (
                f"✏️ Pet renamed to **{display_name}**!\n"
                f"-# Original: {renamed['name']}"
            )
        else:
            message = f"✏️ **{renamed['name']}** is back to its original name."

        await interaction.response.send_message(message, ephemeral=True)
        await self.cog._refresh_pet_view(
            self.parent_message,
            self.user_id,
            self.pet_id,
            ctx=self.ctx,
        )


class PetManagementView(discord.ui.View):
    def __init__(self, cog, user_id, ctx, pets, index=0):
        super().__init__(timeout=600)
        self.cog = cog
        self.user_id = user_id
        self.ctx = ctx
        self.pets = pets
        self.index = index
        self._sync_buttons()

    def _sync_buttons(self):
        previous = cast(discord.ui.Button, self.previous)
        next_button = cast(discord.ui.Button, self.next)
        equip = cast(discord.ui.Button, self.equip)
        favorite = cast(discord.ui.Button, self.favorite)

        previous.disabled = len(self.pets) <= 1
        next_button.disabled = len(self.pets) <= 1
        pet = self.pets[self.index]
        equip.label = "Unequip Pet" if pet["is_active"] else "Equip Pet"
        equip.style = discord.ButtonStyle.secondary
        favorite.label = "🔓 Unfavorite" if pet["is_favorite"] else "🔒 Favorite"
        favorite.style = discord.ButtonStyle.primary

    async def _ensure_owner(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This pet menu isn't for you.", ephemeral=True)
            return False
        return True

    async def _refresh(self, interaction=None, message=None):
        self.pets = await self.cog._get_owned_pets(self.user_id)
        if not self.pets:
            self.stop()
            embed = discord.Embed(
                title=f"🐾 {self.ctx.author.display_name}'s Pet Collection",
                description="Your collection is empty!",
                color=discord.Color.from_rgb(120, 140, 160),
            )
            target = message or (interaction.message if interaction else None)
            if target:
                await target.edit(embed=embed, view=None)
            return
        self.index = min(self.index, len(self.pets) - 1)
        self._sync_buttons()
        target = message or (interaction.message if interaction else None)
        if target:
            await target.edit(embed=self.cog._pet_embed(self.ctx, self.pets[self.index], self.index, len(self.pets)), view=self)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary, row=2)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        self.index = (self.index - 1) % len(self.pets)
        self._sync_buttons()
        await interaction.response.edit_message(embed=self.cog._pet_embed(self.ctx, self.pets[self.index], self.index, len(self.pets)), view=self)

    @discord.ui.button(label="🟢 Feed Pet", style=discord.ButtonStyle.success, row=0)
    async def feed(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        pet = self.pets[self.index]
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            async with db.execute(
                "SELECT item_id, quantity FROM inventory WHERE user_id = ? AND item_id IN (?, ?) AND quantity > 0",
                (self.user_id, "pet_snack", "halloween_pet_candy"),
            ) as cursor:
                owned = {row[0]: row[1] for row in await cursor.fetchall()}
        options = [item for item in ("pet_snack", "halloween_pet_candy") if owned.get(item, 0) > 0]
        if not options:
            return await interaction.response.send_message("❌ You don't have any Pet Treats or Halloween Pet Candy.", ephemeral=True)
        await interaction.response.send_message(
            f"🍪 Choose a treat for **{pet['emoji']} {pet['nickname'] or pet['name']}**:",
            view=FeedTreatView(self.cog, self.user_id, pet["pet_id"], owned, interaction.message, self.ctx),
            ephemeral=True,
        )


    @discord.ui.button(label="📊 Pet Stats", style=discord.ButtonStyle.secondary, row=0)
    async def stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        pet = self.pets[self.index]
        passive = pet.get("passive", {})
        passive_level = passive_level_for_pet(pet["level"])
        passive_value = get_passive_value(pet, pet["level"])
        value_text = (
            f"{passive_value * 100:.1f}%"
            if passive_value < 1
            else f"{passive_value:.2f}"
        )
        source = (
            "Halloween Egg"
            if passive.get("id") and pet["pet_type"] in HALLOWEEN_PETS
            else "Normal Egg"
        )
        embed = discord.Embed(
            title=f"📊 {pet['emoji']} {pet['nickname'] or pet['name']} — Stats",
            color=discord.Color.from_rgb(120, 140, 160),
        )
        embed.add_field(
            name="📈 Progression",
            value=(
                f"**Level:** {pet['level']}\n"
                f"**XP:** {pet['xp']}/{xp_needed_for_next_level(pet['level'])}\n"
                f"**Passive Level:** {passive_level}/{PET_PASSIVE_MAX_LEVEL}"
            ),
            inline=False,
        )
        embed.add_field(
            name=f"✨ {passive.get('name', 'Unknown Passive')}",
            value=(
                f"{passive.get('description', 'No passive description.')}\n"
                f"**Current Strength:** {value_text}"
            ),
            inline=False,
        )
        embed.add_field(
            name="🐣 Origin",
            value=f"**{source}**\n{'⭐ Equipped' if pet['is_active'] else 'Not equipped'}",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


    @discord.ui.button(label="Equip Pet", style=discord.ButtonStyle.primary, row=0)
    async def equip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        pet = self.pets[self.index]
        if pet["is_active"]:
            changed = await self.cog._unequip_pet(self.user_id, pet["pet_id"])
            if not changed:
                return await interaction.response.send_message("❌ That pet is no longer equipped.", ephemeral=True)
            await interaction.response.edit_message(content=None, embed=self.cog._pet_embed(self.ctx, {**pet, "is_active": False}, self.index, len(self.pets)), view=self)
        else:
            definition, error = await self.cog._equip_pet(self.user_id, pet["pet_id"])
            if error:
                return await interaction.response.send_message(error, ephemeral=True)
            self.pets = await self.cog._get_owned_pets(self.user_id)
            self.index = next((i for i, p in enumerate(self.pets) if p["pet_id"] == pet["pet_id"]), 0)
            self._sync_buttons()
            await interaction.response.edit_message(embed=self.cog._pet_embed(self.ctx, self.pets[self.index], self.index, len(self.pets)), view=self)


    @discord.ui.button(label="🔒 Favorite", style=discord.ButtonStyle.primary, row=1)
    async def favorite(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        pet = self.pets[self.index]
        favorited, error = await self.cog._set_pet_favorite(self.user_id, pet["pet_id"], not pet["is_favorite"])
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        self.pets = await self.cog._get_owned_pets(self.user_id)
        self.index = next((i for i, p in enumerate(self.pets) if p["pet_id"] == pet["pet_id"]), self.index)
        self._sync_buttons()
        action = "favorited and locked" if favorited else "unfavorited and unlocked"
        await interaction.response.edit_message(
            embed=self.cog._pet_embed(self.ctx, self.pets[self.index], self.index, len(self.pets)),
            view=self,
        )

    @discord.ui.button(label="✏️ Rename Pet", style=discord.ButtonStyle.secondary, row=1)
    async def rename(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        pet = self.pets[self.index]
        modal = RenamePetModal(
            self.cog,
            self.user_id,
            pet["pet_id"],
            interaction.message,
            self.ctx,
        )
        await interaction.response.send_modal(modal)


    @discord.ui.button(label="🔴 Release Pet", style=discord.ButtonStyle.danger, row=1)
    async def release(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        pet = self.pets[self.index]
        if pet["is_favorite"]:
            return await interaction.response.send_message(
                "🔒 **This pet is favorited and protected!** Unfavorite it first if you want to release it.",
                ephemeral=True,
            )
        await interaction.response.send_message(
            (
                f"⚠️ **Are you sure?**\n\n"
                f"You are about to permanently release **{pet['emoji']} {pet['nickname'] or pet['name']}**.\n"
                f"Level **{pet['level']}** • **{pet['xp']} XP**\n\n"
                f"This cannot be undone."
            ),
            view=ReleaseConfirmationView(self.cog, self.user_id, pet, interaction.message, self.ctx),
            ephemeral=True,
        )

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary, row=2)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        self.index = (self.index + 1) % len(self.pets)
        self._sync_buttons()
        await interaction.response.edit_message(embed=self.cog._pet_embed(self.ctx, self.pets[self.index], self.index, len(self.pets)), view=self)


class Pets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # Start the background task once the cog is loaded onto the bot.
        self.incubator_checker.start()  # type: ignore[attr-defined]

    def cog_unload(self):
        if self.incubator_checker.is_running():  # type: ignore[attr-defined]
            self.incubator_checker.cancel()  # type: ignore[attr-defined]

    async def ensure_schema(self, db):
        """Add pet fields/tables without deleting existing pet data."""
        async with db.execute("PRAGMA table_info(pets)") as cursor:
            columns = {row[1] async for row in cursor}

        additions = {
            "pet_type": "TEXT DEFAULT ''",
            "is_active": "INTEGER DEFAULT 0",
            "is_favorite": "INTEGER DEFAULT 0",
        }

        for column, definition in additions.items():
            if column not in columns:
                await db.execute(
                    f"ALTER TABLE pets ADD COLUMN {column} {definition}"
                )

        # Preserve an old pet_stage value as the pet type when possible.
        await db.execute(
            """
            UPDATE pets
            SET pet_type = pet_stage
            WHERE COALESCE(pet_type, '') = ''
              AND COALESCE(pet_stage, '') != 'egg'
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS pet_incubators (
                incubator_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                egg_id TEXT NOT NULL,
                started_at REAL NOT NULL,
                ready_at REAL NOT NULL,
                notified INTEGER DEFAULT 0
            )
            """
        )

        await db.commit()

    def pet_display(self, pet):
        name = pet["nickname"] or pet["name"]
        return f"{pet['emoji']} **{name}**"

    def xp_bar(self, current, needed, length=12):
        if needed <= 0:
            return "━━━━━━━━━━━━"
        filled = max(0, min(length, int((current / needed) * length)))
        return "█" * filled + "░" * (length - filled)

    async def _owned_eggs(self, db, user_id):
        egg_ids = ["normal_egg", "halloween_egg"]
        placeholders = ",".join("?" for _ in egg_ids)
        async with db.execute(
            f"""
            SELECT item_id, quantity
            FROM inventory
            WHERE user_id = ?
              AND item_id IN ({placeholders})
              AND quantity > 0
            """,
            (user_id, *egg_ids),
        ) as cursor:
            return {row[0]: row[1] for row in await cursor.fetchall()}

    async def _incubator_row(self, db, user_id):
        async with db.execute(
            """
            SELECT incubator_id, egg_id, started_at, ready_at, notified
            FROM pet_incubators
            WHERE user_id = ?
            ORDER BY incubator_id DESC
            LIMIT 1
            """,
            (user_id,),
        ) as cursor:
            return await cursor.fetchone()

    async def _egg_autocomplete(self, interaction, current):
        current = (current or "").lower().strip()
        choices = []
        for egg_id in ("normal_egg", "halloween_egg"):
            info = ITEM_REGISTRY.get(egg_id)
            if not info:
                continue
            if current and current not in f"{info['name']} {egg_id}".lower():
                continue
            choices.append(app_commands.Choice(
                name=f"{info['emoji']} {info['name']}",
                value=egg_id,
            ))
        return choices[:25]

    async def _pet_autocomplete(self, interaction, current):
        current = (current or "").lower().strip()
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            async with db.execute(
                """
                SELECT pet_id, pet_type, pet_stage, nickname, level
                FROM pets
                WHERE user_id = ? AND COALESCE(pet_type, pet_stage) != 'egg'
                ORDER BY pet_id
                """,
                (interaction.user.id,),
            ) as cursor:
                rows = await cursor.fetchall()

        choices = []
        pet_counts = {}

        for pet_id, pet_type, pet_stage, nickname, level in rows:
            pet_type_id = pet_type or pet_stage
            definition = get_pet_definition(pet_type_id)
            if not definition:
                continue

            # Give duplicate pets a stable, human-readable number while
            # keeping the database pet_id as the actual autocomplete value.
            pet_counts[pet_type_id] = pet_counts.get(pet_type_id, 0) + 1
            duplicate_number = pet_counts[pet_type_id]

            display_name = nickname or definition["name"]
            search = (
                f"{display_name} {definition['name']} {pet_type_id} "
                f"{pet_id} {duplicate_number}"
            ).lower()
            if current and current not in search:
                continue

            choices.append(app_commands.Choice(
                name=(
                    f"{definition['emoji']} {display_name} "
                    f"• Lv. {level} • #{duplicate_number}"
                ),
                value=str(pet_id),
            ))

        return choices[:25]

    async def _treat_autocomplete(self, interaction, current):
        current = (current or "").lower().strip()
        treat_ids = ["pet_snack", "halloween_pet_candy"]
        choices = []

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            async with db.execute(
                """
                SELECT item_id, quantity
                FROM inventory
                WHERE user_id = ? AND item_id IN (?, ?) AND quantity > 0
                """,
                (interaction.user.id, *treat_ids),
            ) as cursor:
                owned = {row[0]: row[1] for row in await cursor.fetchall()}

        for item_id in treat_ids:
            info = ITEM_REGISTRY.get(item_id)
            if not info:
                continue
            search = f"{info['name']} {item_id}".lower()
            if current and current not in search:
                continue
            choices.append(app_commands.Choice(
                name=f"{info['emoji']} {info['name']} (x{owned.get(item_id, 0)})",
                value=item_id,
            ))

        return choices[:25]

    async def _get_owned_pets(self, user_id):
        """Return all recognized, non-egg pets owned by a user in stable order."""
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            async with db.execute(
                """
                SELECT pet_id, pet_type, pet_stage, nickname, level, xp, is_active, is_favorite
                FROM pets
                WHERE user_id = ? AND COALESCE(pet_type, pet_stage) != 'egg'
                ORDER BY pet_id
                """,
                (user_id,),
            ) as cursor:
                rows = await cursor.fetchall()

        pets = []
        for pet_id, pet_type, pet_stage, nickname, level, xp, is_active, is_favorite in rows:
            pet_type_id = pet_type or pet_stage
            definition = get_pet_definition(pet_type_id)
            if not definition:
                continue
            pets.append({
                "pet_id": pet_id,
                "pet_type": pet_type_id,
                "name": definition["name"],
                "emoji": definition["emoji"],
                "description": definition["description"],
                "nickname": nickname,
                "level": level or 1,
                "xp": xp or 0,
                "is_active": bool(is_active),
                "is_favorite": bool(is_favorite),
                "passive": definition.get("passive", {}),
            })
        return pets

    def _pet_embed(self, ctx, pet, page, total):
        level = pet["level"]
        xp = pet["xp"]
        needed = xp_needed_for_next_level(level)
        passive = pet.get("passive", {})
        passive_level = passive_level_for_pet(level)
        passive_value = get_passive_value(pet, level)
        value_text = f"{passive_value * 100:.1f}%" if passive_value < 1 else f"{passive_value:.2f}"
        display_name = pet["nickname"] or pet["name"]
        active_text = "⭐ **ACTIVE COMPANION**" if pet["is_active"] else "Not currently equipped"

        embed = discord.Embed(
            title=f"🐾 {ctx.author.display_name}'s Pet",
            description=(
                f"{pet['emoji']} **{display_name}**\n"
                + (f"-# Original: {pet['name']}\n" if pet["nickname"] else "")
                + f"*{pet['description']}*\n\n"
                + ("🔒 **FAVORITED — PROTECTED FROM RELEASE**" if pet["is_favorite"] else "-# 🔒 Favorite this pet to lock it and prevent accidental release.")
                + f"\n{active_text}"
            ),
            color=discord.Color.from_rgb(120, 140, 160),
        )
        embed.add_field(
            name="📈 Level & XP",
            value=(
                f"**Level {level}**\n"
                f"`{self.xp_bar(xp, needed)}`\n"
                f"**{xp}/{needed} XP** to Level {level + 1}"
            ),
            inline=False,
        )
        embed.add_field(
            name=f"✨ Passive — {passive.get('name', 'Unknown')}",
            value=(
                f"**Passive Level {passive_level}/{PET_PASSIVE_MAX_LEVEL}**\n"
                f"{passive.get('description', 'No passive description.')}\n"
                f"Current strength: **{value_text}**"
            ),
            inline=False,
        )
        embed.add_field(
            name="🍪 Treat XP",
            value=(
                f"🍖 Pet Treat — **+{PET_TREAT_XP} XP**\n"
                f"🎃 Halloween Pet Candy — **+{HALLOWEEN_PET_CANDY_XP} XP**"
            ),
            inline=False,
        )
        embed.set_footer(text=f"Pet {page + 1}/{total} • Pets can level beyond Passive Level 5; passive strength caps at 5 for now.")
        return embed

    async def _feed_specific_pet(self, user_id, pet_id, treat):
        xp_amounts = {
            "pet_snack": PET_TREAT_XP,
            "halloween_pet_candy": HALLOWEEN_PET_CANDY_XP,
        }
        if treat not in xp_amounts:
            return None, "❌ That isn't a valid pet treat."

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")

            async with db.execute(
                """
                SELECT pet_id, pet_type, pet_stage, nickname, level, xp, is_active
                FROM pets
                WHERE user_id = ? AND pet_id = ?
                LIMIT 1
                """,
                (user_id, pet_id),
            ) as cursor:
                row = await cursor.fetchone()

            if not row or (row[1] or row[2]) == "egg":
                await db.rollback()
                return None, "❌ That pet no longer exists in your collection."

            definition = get_pet_definition(row[1] or row[2])
            if not definition:
                await db.rollback()
                return None, "❌ That pet is no longer configured."

            async with db.execute(
                "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                (user_id, treat),
            ) as cursor:
                treat_row = await cursor.fetchone()

            if not treat_row or treat_row[0] <= 0:
                await db.rollback()
                return None, f"❌ You don't have any **{ITEM_REGISTRY[treat]['name']}**!"

            pet = {
                "pet_id": row[0],
                "pet_type": row[1] or row[2],
                "name": definition["name"],
                "emoji": definition["emoji"],
                "description": definition["description"],
                "nickname": row[3],
                "level": row[4] or 1,
                "xp": row[5] or 0,
                "is_active": bool(row[6]),
                "passive": definition.get("passive", {}),
            }
            base_xp = xp_amounts[treat]
            treat_bonus = 0.0
            if pet["passive"].get("id") == "treat_xp_bonus":
                treat_bonus = get_passive_value(pet, pet["level"])
            xp_amount = int(base_xp * (1 + treat_bonus))

            await db.execute(
                "UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_id = ?",
                (user_id, treat),
            )
            await db.execute(
                "DELETE FROM inventory WHERE user_id = ? AND item_id = ? AND quantity <= 0",
                (user_id, treat),
            )

            old_level = pet["level"]
            new_level = old_level
            new_xp = pet["xp"] + xp_amount
            while new_xp >= xp_needed_for_next_level(new_level):
                new_xp -= xp_needed_for_next_level(new_level)
                new_level += 1

            await db.execute(
                "UPDATE pets SET level = ?, xp = ? WHERE pet_id = ? AND user_id = ?",
                (new_level, new_xp, pet_id, user_id),
            )
            await db.commit()

        return {
            "pet": pet,
            "treat": ITEM_REGISTRY[treat],
            "xp_amount": xp_amount,
            "old_level": old_level,
            "new_level": new_level,
            "leveled_up": new_level > old_level,
            "passive_level": passive_level_for_pet(new_level),
        }, None

    async def _equip_pet(self, user_id, pet_id):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")
            async with db.execute(
                "SELECT pet_type, pet_stage FROM pets WHERE user_id = ? AND pet_id = ? LIMIT 1",
                (user_id, pet_id),
            ) as cursor:
                row = await cursor.fetchone()
            if not row:
                await db.rollback()
                return None, "❌ That pet no longer exists in your collection."
            definition = get_pet_definition(row[0] or row[1])
            if not definition:
                await db.rollback()
                return None, "❌ That pet is no longer configured."
            await db.execute("UPDATE pets SET is_active = 0 WHERE user_id = ?", (user_id,))
            await db.execute("UPDATE pets SET is_active = 1 WHERE user_id = ? AND pet_id = ?", (user_id, pet_id))
            await db.commit()
        return definition, None

    async def _unequip_pet(self, user_id, pet_id):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute(
                "UPDATE pets SET is_active = 0 WHERE user_id = ? AND pet_id = ? AND is_active = 1",
                (user_id, pet_id),
            )
            changed = cursor.rowcount
            await db.commit()
        return changed > 0

    async def _rename_pet(self, user_id, pet_id, nickname):
        nickname = nickname.strip()
        if len(nickname) > 30:
            return None

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")
            async with db.execute(
                """
                SELECT pet_type, pet_stage
                FROM pets
                WHERE user_id = ? AND pet_id = ?
                LIMIT 1
                """,
                (user_id, pet_id),
            ) as cursor:
                row = await cursor.fetchone()

            if not row or (row[0] or row[1]) == "egg":
                await db.rollback()
                return None

            definition = get_pet_definition(row[0] or row[1])
            if not definition:
                await db.rollback()
                return None

            await db.execute(
                """
                UPDATE pets
                SET nickname = ?
                WHERE user_id = ? AND pet_id = ?
                """,
                (nickname, user_id, pet_id),
            )
            await db.commit()

        return {
            "pet_id": pet_id,
            "name": definition["name"],
            "nickname": nickname,
            "emoji": definition["emoji"],
        }

    async def _set_pet_favorite(self, user_id, pet_id, favorite):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")
            async with db.execute(
                "SELECT pet_type, pet_stage FROM pets WHERE user_id = ? AND pet_id = ? LIMIT 1",
                (user_id, pet_id),
            ) as cursor:
                row = await cursor.fetchone()
            if not row or (row[0] or row[1]) == "egg":
                await db.rollback()
                return False, "❌ That pet no longer exists in your collection."
            if not get_pet_definition(row[0] or row[1]):
                await db.rollback()
                return False, "❌ That pet is no longer configured."
            await db.execute(
                "UPDATE pets SET is_favorite = ? WHERE user_id = ? AND pet_id = ?",
                (1 if favorite else 0, user_id, pet_id),
            )
            await db.commit()
        return bool(favorite), None


    async def _release_pet(self, user_id, pet_id):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")
            async with db.execute(
                """
                SELECT pet_type, pet_stage, nickname, level, xp, is_active, is_favorite
                FROM pets
                WHERE user_id = ? AND pet_id = ?
                LIMIT 1
                """,
                (user_id, pet_id),
            ) as cursor:
                row = await cursor.fetchone()
            if not row:
                await db.rollback()
                return None
            if row[6]:
                await db.rollback()
                return {"protected": True}
            pet_type = row[0] or row[1]
            definition = get_pet_definition(pet_type)
            if not definition:
                await db.rollback()
                return None
            await db.execute(
                "DELETE FROM pets WHERE user_id = ? AND pet_id = ?",
                (user_id, pet_id),
            )
            await db.commit()
        return {
            "pet_id": pet_id,
            "name": definition["name"],
            "emoji": definition["emoji"],
            "nickname": row[2],
            "level": row[3] or 1,
            "xp": row[4] or 0,
            "is_active": bool(row[5]),
        }

    @commands.hybrid_command(name="pets", description="View and manage your pet collection.")
    async def pets(self, ctx: commands.Context):
        await ctx.defer()
        pets = await self._get_owned_pets(ctx.author.id)
        if not pets:
            embed = discord.Embed(
                title=f"🐾 {ctx.author.display_name}'s Pet Collection",
                description=(
                    "Your collection is empty!\n\n"
                    "🥚 Eggs can be discovered during scavenging.\n"
                    "⏳ Use `/incubator start` to begin incubation."
                ),
                color=discord.Color.from_rgb(120, 140, 160),
            )
            return await ctx.send(embed=embed)

        view = PetManagementView(self, ctx.author.id, ctx, pets, 0)
        await ctx.send(embed=self._pet_embed(ctx, pets[0], 0, len(pets)), view=view)

    async def _refresh_pet_view(self, message, user_id, pet_id, allow_missing=False, ctx=None):
        if not message or ctx is None:
            return
        pets = await self._get_owned_pets(user_id)
        if not pets:
            embed = discord.Embed(
                title=f"🐾 {ctx.author.display_name}'s Pet Collection",
                description="Your collection is empty!",
                color=discord.Color.from_rgb(120, 140, 160),
            )
            try:
                await message.edit(embed=embed, view=None)
            except discord.HTTPException:
                pass
            return
        index = next((i for i, pet in enumerate(pets) if pet["pet_id"] == pet_id), min(len(pets) - 1, 0))
        view = PetManagementView(self, user_id, ctx, pets, index)
        try:
            await message.edit(embed=self._pet_embed(ctx, pets[index], index, len(pets)), view=view)
        except discord.HTTPException:
            pass

    @commands.hybrid_group(
        name="incubator",
        description="Manage your pet egg incubator.",
        invoke_without_command=True,
    )
    async def incubator(self, ctx: commands.Context):
        await ctx.defer()

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")
            row = await self._incubator_row(db, ctx.author.id)
            eggs = await self._owned_eggs(db, ctx.author.id)

        embed = discord.Embed(
            title=f"🥚 {ctx.author.display_name}'s Pet Incubator",
            color=discord.Color.from_rgb(120, 140, 160),
        )

        if row:
            _incubator_id, egg_id, started_at, ready_at, notified = row
            info = ITEM_REGISTRY.get(egg_id, {"name": egg_id, "emoji": "🥚"})
            remaining = max(0, int(ready_at - time.time()))

            if remaining <= 0:
                status = "✅ **READY TO HATCH!**"
                instruction = f"Use `/incubator hatch {egg_id}` to reveal your pet!"
            else:
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                status = f"⏳ **{hours}h {minutes}m remaining**"
                instruction = "The incubator will alert you when it's ready."

            embed.description = (
                f"{info['emoji']} **{info['name']}**\n"
                f"{status}\n\n{instruction}"
            )
        else:
            embed.description = (
                "The incubator is empty. 💤\n\n"
                "Find an egg during scavenging, then use `/incubator start <egg>`."
            )

        if eggs:
            egg_lines = []
            for egg_id, quantity in eggs.items():
                info = ITEM_REGISTRY.get(egg_id)
                if info:
                    egg_lines.append(f"{info['emoji']} **{info['name']}** ×{quantity}")
            embed.add_field(
                name="🥚 Eggs in Storage",
                value="\n".join(egg_lines),
                inline=False,
            )

        embed.set_footer(text="Incubation time: 12 hours • Eggs can be hatched after the seasonal event ends.")
        await ctx.send(embed=embed)

    @incubator.command(name="start", description="Put an egg into the incubator for 12 hours.")
    @app_commands.describe(egg="Choose an egg you own.")
    @app_commands.autocomplete(egg=_egg_autocomplete)
    async def incubator_start(self, ctx: commands.Context, egg: str):
        await ctx.defer()
        egg = egg.lower().strip()

        if egg not in EGG_POOLS:
            return await ctx.send("❌ That isn't a valid pet egg.")

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")

            existing = await self._incubator_row(db, ctx.author.id)
            if existing:
                remaining = max(0, int(existing[3] - time.time()))
                if remaining > 0:
                    return await ctx.send(
                        "⏳ Your incubator is already occupied! "
                        "Use `/incubator` to check its status."
                    )
                return await ctx.send(
                    "🥚 Your previous egg is ready to hatch! "
                    f"Use `/incubator hatch {existing[1]}` before starting another."
                )

            async with db.execute(
                "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                (ctx.author.id, egg),
            ) as cursor:
                row = await cursor.fetchone()

            if not row or row[0] <= 0:
                return await ctx.send("❌ You don't have that egg in your inventory.")

            await db.execute(
                "UPDATE inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_id = ?",
                (ctx.author.id, egg),
            )
            await db.execute(
                "DELETE FROM inventory WHERE user_id = ? AND item_id = ? AND quantity <= 0",
                (ctx.author.id, egg),
            )

            started = time.time()
            ready = started + INCUBATION_SECONDS
            await db.execute(
                """
                INSERT INTO pet_incubators
                    (user_id, egg_id, started_at, ready_at, notified)
                VALUES (?, ?, ?, ?, 0)
                """,
                (ctx.author.id, egg, started, ready),
            )
            await db.commit()

        info = ITEM_REGISTRY[egg]
        await ctx.send(
            f"{ctx.author.mention} {info['emoji']} **{info['name']} is now incubating!**\n"
            f"⏳ Incubation time: **12 hours**\n"
            "🔔 I'll alert you when it's ready to hatch!\n"
            f"Use `/incubator hatch {egg}` when the timer finishes."
        )

    @incubator.command(name="hatch", description="Hatch a ready egg and reveal the pet inside.")
    @app_commands.describe(egg="Choose the egg currently in your incubator.")
    @app_commands.autocomplete(egg=_egg_autocomplete)
    async def incubator_hatch(self, ctx: commands.Context, egg: str):
        await ctx.defer()
        egg = egg.lower().strip()

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            row = await self._incubator_row(db, ctx.author.id)

            if not row:
                return await ctx.send("❌ Your incubator is empty.")

            _incubator_id, stored_egg, started_at, ready_at, _notified = row

            if stored_egg != egg:
                return await ctx.send(
                    f"❌ Your incubator currently contains **{stored_egg}**, not **{egg}**."
                )

            if time.time() < ready_at:
                remaining = int(ready_at - time.time())
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                return await ctx.send(
                    f"⏳ That egg isn't ready yet! **{hours}h {minutes}m** remaining."
                )

            pool = EGG_POOLS.get(stored_egg, [])
            if not pool:
                return await ctx.send("❌ This egg currently has no pets configured.")

            pet_type = random.choice(pool)
            definition = get_pet_definition(pet_type)
            if not definition:
                return await ctx.send("❌ This egg points to a pet that is not currently configured.")

            async with db.execute(
                "SELECT 1 FROM pets WHERE user_id = ? AND is_active = 1 LIMIT 1",
                (ctx.author.id,),
            ) as cursor:
                has_active = await cursor.fetchone()

            await db.execute(
                """
                INSERT INTO pets
                    (user_id, pet_stage, pet_type, nickname, level, xp, is_active)
                VALUES (?, ?, ?, '', 1, 0, ?)
                """,
                (ctx.author.id, pet_type, pet_type, 0 if has_active else 1),
            )
            await db.execute(
                "DELETE FROM pet_incubators WHERE incubator_id = ?",
                (row[0],),
            )

            # Hatching a Halloween Egg permanently unlocks the Haunting Friend background.
            if stored_egg == "halloween_egg":
                achievements_cog = self.bot.get_cog("Achievements")
                if achievements_cog:
                    await achievements_cog.add_halloween_hatch_progress(
                        ctx.author.id,
                        db=db,
                    )

            await db.commit()

        active_note = (
            " It has been automatically equipped because you didn't have an active pet!"
            if not has_active else
            " Use `/pets` to manage and equip your new companion!"
        )

        await ctx.send(
            f"{ctx.author.mention} 🐣 **EGG HATCHED!**\n\n"
            f"{definition['emoji']} **{definition['name']}**!\n"
            f"> *{definition['description']}*\n\n"
            f"✨ **Passive:** {definition['passive']['name']}\n"
            f"_{definition['passive']['description']}_\n\n"
            f"📈 **Level 1** • Passive Level **1/{PET_PASSIVE_MAX_LEVEL}**\n"
            f"{active_note}"
        )

    @tasks.loop(minutes=1)
    async def incubator_checker(self):
        """Notify users when their 12-hour incubation finishes."""
        try:
            async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
                await self.ensure_schema(db)
                now = time.time()

                async with db.execute(
                    """
                    SELECT incubator_id, user_id, egg_id
                    FROM pet_incubators
                    WHERE ready_at <= ? AND notified = 0
                    """,
                    (now,),
                ) as cursor:
                    rows = await cursor.fetchall()

                for incubator_id, user_id, egg_id in rows:
                    channel = self.bot.get_channel(INCUBATOR_NOTIFICATION_CHANNEL_ID)
                    if channel is None:
                        try:
                            channel = await self.bot.fetch_channel(
                                INCUBATOR_NOTIFICATION_CHANNEL_ID
                            )
                        except Exception:
                            channel = None

                    if channel is None:
                        # Keep the notification pending so a later checker run
                        # can try again if the channel becomes available.
                        continue

                    try:
                        info = ITEM_REGISTRY.get(
                            egg_id, {"name": egg_id, "emoji": "🥚"}
                        )
                        await channel.send(
                            f"<@{user_id}> 🔔 {info['emoji']} "
                            f"**Your pet egg is ready to hatch!**\n"
                            f"Your **{info['name']}** has finished incubating.\n\n"
                            f"Use `/incubator hatch {egg_id}` to reveal your new companion! 🐣"
                        )
                    except Exception:
                        # Keep the notification pending if the channel/message
                        # cannot be sent right now.
                        continue

                    await db.execute(
                        "UPDATE pet_incubators SET notified = 1 WHERE incubator_id = ?",
                        (incubator_id,),
                    )

                await db.commit()
        except Exception:
            # The notification loop must never take the bot down.
            return

    @incubator_checker.before_loop
    async def before_incubator_checker(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Pets(bot))
