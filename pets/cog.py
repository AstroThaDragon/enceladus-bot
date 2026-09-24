"""The Discord Cog that wires the pet system together."""

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
from seasonal_updates.halloween.halloween import is_active as halloween_is_active
from pet_variants import (
    ASTRAL_ESSENCE_ID, ASTRAL_ESSENCE_NAME, ASTRAL_ESSENCE_EMOJI,
    FUSION_COSTS, VARIANT_HUNT_COST, FUSION_LEVEL_GATES,
    HATCH_ESSENCE_CHANCE, RELEASE_ESSENCE_CHANCE,
    get_variant_info, get_variant_display, get_variant_ids_for_pet,
    roll_hatched_variant, roll_fusion_variant, build_variant_collectibles,
)

from .config import *
from .core import *
from .views import (
    FeedTreatSelect, FeedTreatView, ReleaseConfirmationView, RenamePetModal,
    PetStatsView, PetManagementView, FusionVariantView, PostFusionConfirmView,
)
from .management import PetManagementMixin
from .fusion import PetFusionMixin
from .incubator import PetIncubatorMixin

class Pets(PetManagementMixin, PetFusionMixin, PetIncubatorMixin, commands.Cog):
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
            "variant_id": "TEXT DEFAULT ''",
            "fusion_level": "INTEGER DEFAULT 0",
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
                notified INTEGER DEFAULT 0,
                slot_id INTEGER NOT NULL DEFAULT 1
            )
            """
        )

        async with db.execute("PRAGMA table_info(pet_incubators)") as cursor:
            incubator_columns = {row[1] async for row in cursor}

        if "slot_id" not in incubator_columns:
            await db.execute(
                "ALTER TABLE pet_incubators ADD COLUMN slot_id INTEGER NOT NULL DEFAULT 1"
            )

        async with db.execute("PRAGMA table_info(users)") as cursor:
            user_columns = {row[1] async for row in cursor}

        if "incubator_slots" not in user_columns:
            await db.execute(
                "ALTER TABLE users ADD COLUMN incubator_slots INTEGER DEFAULT 1"
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


    async def _incubator_rows(self, db, user_id):
        async with db.execute(
            """
            SELECT incubator_id, egg_id, started_at, ready_at, notified, slot_id
            FROM pet_incubators
            WHERE user_id = ?
            ORDER BY slot_id ASC, incubator_id ASC
            """,
            (user_id,),
        ) as cursor:
            return await cursor.fetchall()


    async def _incubator_row(self, db, user_id):
        rows = await self._incubator_rows(db, user_id)
        return rows[-1] if rows else None


    async def _get_incubator_slots(self, db, user_id):
        async with db.execute(
            "SELECT COALESCE(incubator_slots, 1) FROM users WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return max(1, min(3, int(row[0] if row else 1)))


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


    async def _incubator_egg_autocomplete(self, interaction, current):
        current = (current or "").lower().strip()
        action = getattr(getattr(interaction, "namespace", None), "action", None)
        action = str(action).lower().strip() if action else ""

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            if action == "hatch":
                rows = await self._incubator_rows(db, interaction.user.id)
                egg_ids = [row[1] for row in rows]
            else:
                owned = await self._owned_eggs(db, interaction.user.id)
                egg_ids = list(owned.keys())

        choices = []
        for egg_id in egg_ids:
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
                SELECT pet_id, pet_type, pet_stage, nickname, level, variant_id, fusion_level
                FROM pets
                WHERE user_id = ? AND COALESCE(pet_type, pet_stage) != 'egg'
                ORDER BY pet_id
                """,
                (interaction.user.id,),
            ) as cursor:
                rows = await cursor.fetchall()

        choices = []
        pet_counts = {}

        for pet_id, pet_type, pet_stage, nickname, level, variant_id, fusion_level in rows:
            pet_type_id = pet_type or pet_stage
            definition = get_pet_definition(pet_type_id, variant_id)
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
                SELECT pet_id, pet_type, pet_stage, nickname, level, xp, is_active, is_favorite, variant_id, fusion_level
                FROM pets
                WHERE user_id = ? AND COALESCE(pet_type, pet_stage) != 'egg'
                ORDER BY pet_id
                """,
                (user_id,),
            ) as cursor:
                rows = await cursor.fetchall()

        pets = []
        for pet_id, pet_type, pet_stage, nickname, level, xp, is_active, is_favorite, variant_id, fusion_level in rows:
            pet_type_id = pet_type or pet_stage
            definition = get_pet_definition(pet_type_id, variant_id)
            if not definition:
                continue
            pets.append({
                "pet_id": pet_id,
                "pet_type": pet_type_id,
                "variant_id": variant_id,
                "fusion_level": fusion_level or 0,
                "name": definition["name"],
                "emoji": definition["emoji"],
                "description": definition["description"],
                "nickname": nickname,
                "level": level or 1,
                "xp": xp or 0,
                "is_active": bool(is_active),
                "is_favorite": bool(is_favorite),
                "passive": definition.get("passive", {}),
                "normal_passive": definition.get("normal_passive", definition.get("passive", {})),
                "haunted_passive": definition.get("passive", {}) if definition.get("haunted_location") else {},
                "haunted_location": definition.get("haunted_location"),
            })
        return pets


    def _pet_stats_embed(self, ctx, pet):
        level = pet["level"]
        xp = pet["xp"]
        passive = pet.get("passive", {})
        normal_passive = pet.get("normal_passive", passive)
        haunted_passive = pet.get("haunted_passive", {})
        passive_level = passive_level_for_pet(level)
        passive_value = get_passive_value({"passive": passive, "level": level, "fusion_level": pet.get("fusion_level", 0)}, level)
        normal_value = get_passive_value({"passive": normal_passive, "level": level, "fusion_level": pet.get("fusion_level", 0)}, level)
        value_text = f"{passive_value * 100:.1f}%" if passive_value < 1 else f"{passive_value:.2f}"
        normal_value_text = f"{normal_value * 100:.1f}%" if normal_value < 1 else f"{normal_value:.2f}"

        if pet["pet_type"] in HAUNTED_PETS:
            source = "Haunted Exploration"
        elif passive.get("id") and pet["pet_type"] in HALLOWEEN_PETS:
            source = "Halloween Egg"
        else:
            source = "Normal Egg"

        embed = discord.Embed(
            title=f"📊 {pet['emoji']} {pet['nickname'] or pet['name']} — Stats",
            color=discord.Color.from_rgb(120, 140, 160),
        )
        embed.add_field(
            name="📈 Progression",
            value=(
                f"**Level:** {level}\n"
                f"**XP:** {xp}/{xp_needed_for_next_level(level)}\n"
                f"**Passive Level:** {passive_level}/{PET_PASSIVE_MAX_LEVEL}"
            ),
            inline=False,
        )

        has_dual_passive = bool(
            normal_passive
            and passive
            and normal_passive.get("id") != passive.get("id")
        )

        if has_dual_passive:
            embed.add_field(
                name=f"✨ Normal Passive — {normal_passive.get('name', 'Unknown')}",
                value=(
                    f"{normal_passive.get('description', 'No passive description.')}\n"
                    f"**Current Strength:** {normal_value_text}"
                ),
                inline=False,
            )

            if pet["pet_type"] in HAUNTED_PETS and haunted_passive:
                secondary_label = "👻 Haunted Passive"
                secondary_extra = (
                    f"\n**Location:** {pet.get('haunted_location', 'Associated Haunted location')}"
                )
            else:
                secondary_label = "🎃 Halloween Passive"
                secondary_extra = ""

            embed.add_field(
                name=f"{secondary_label} — {passive.get('name', 'Unknown')}",
                value=(
                    f"{passive.get('description', 'No passive description.')}\n"
                    f"**Current Strength:** {value_text}"
                    f"{secondary_extra}"
                ),
                inline=False,
            )
        else:
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
        embed.set_footer(text="Use ◀️ Back to return to your pet menu.")
        return embed


    def _pet_embed(self, ctx, pet, page, total):
        level = pet["level"]
        xp = pet["xp"]
        needed = xp_needed_for_next_level(level)
        passive = pet.get("passive", {})
        normal_passive = pet.get("normal_passive", passive)
        haunted_passive = pet.get("haunted_passive", {})
        passive_level = passive_level_for_pet(level)
        passive_value = get_passive_value({"passive": passive, "level": level, "fusion_level": pet.get("fusion_level", 0)}, level)
        normal_value = get_passive_value({"passive": normal_passive, "level": level, "fusion_level": pet.get("fusion_level", 0)}, level)
        value_text = f"{passive_value * 100:.1f}%" if passive_value < 1 else f"{passive_value:.2f}"
        normal_value_text = f"{normal_value * 100:.1f}%" if normal_value < 1 else f"{normal_value:.2f}"
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
        if pet.get("variant_id"):
            variant = get_variant_info(pet["pet_type"], pet["variant_id"])
            if variant:
                embed.add_field(
                    name=f"{variant['emoji']} Variant",
                    value=f"**{variant['name']}**\n{variant['lore']}",
                    inline=False,
                )

        fusion_level = int(pet.get("fusion_level", 0) or 0)
        if fusion_level:
            bonus = fusion_level * 2
            embed.add_field(
                name="🧬 Fusion",
                value=(
                    f"**Fusion {fusion_level}/5** • Passive strength **+{bonus}%**\n"
                    "Further fusions after Fusion 5 only hunt for variants."
                ),
                inline=False,
            )
        has_dual_passive = bool(
            normal_passive
            and passive
            and normal_passive.get("id") != passive.get("id")
        )

        if has_dual_passive:
            embed.add_field(
                name=f"✨ Normal Passive — {normal_passive.get('name', 'Unknown')}",
                value=(
                    f"**Passive Level {passive_level}/{PET_PASSIVE_MAX_LEVEL}**\n"
                    f"{normal_passive.get('description', 'No passive description.')}\n"
                    f"Current strength: **{normal_value_text}**"
                ),
                inline=False,
            )

            if pet["pet_type"] in HAUNTED_PETS and haunted_passive:
                secondary_label = "👻 Haunted Passive"
                secondary_extra = (
                    f"\nOnly active in: **{pet.get('haunted_location', 'Associated Haunted location')}**"
                )
            else:
                secondary_label = "🎃 Halloween Passive"
                secondary_extra = ""

            embed.add_field(
                name=f"{secondary_label} — {passive.get('name', 'Unknown')}",
                value=(
                    f"**Passive Level {passive_level}/{PET_PASSIVE_MAX_LEVEL}**\n"
                    f"{passive.get('description', 'No passive description.')}\n"
                    f"Current strength: **{value_text}**"
                    f"{secondary_extra}"
                ),
                inline=False,
            )
        else:
            embed.add_field(
                name=f"✨ Passive — {passive.get('name', 'Unknown Passive')}",
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
        embed.add_field(
            name="🍽️ Feed Your Pet",
            value="Use **`/feed <pet> <treat> <quantity>`** to give this pet XP.",
            inline=False,
        )
        embed.set_footer(text=f"Pet {page + 1}/{total} • Pets can level beyond Passive Level 5; passive strength caps at 5 for now.")
        return embed


    @commands.hybrid_command(
        name="feed",
        description="Feed a pet treats to give it XP.",
    )
    @app_commands.describe(
        pet="Choose the pet to feed.",
        treat="Choose the treat to use.",
        quantity="How many treats to use (1-99).",
    )
    @app_commands.autocomplete(pet=_pet_autocomplete, treat=_treat_autocomplete)
    async def feed(
        self,
        ctx: commands.Context,
        pet: str,
        treat: str,
        quantity: int,
    ):
        await ctx.defer()

        try:
            pet_id = int(pet)
        except (TypeError, ValueError):
            return await ctx.send("❌ Please choose a valid pet from the autocomplete list.")

        result, error = await self._feed_specific_pet(
            ctx.author.id,
            pet_id,
            treat.lower().strip(),
            quantity,
        )
        if error:
            return await ctx.send(error)
        if result is None:
            return await ctx.send("❌ Feeding failed because no result was returned.")

        fed_pet = result["pet"]
        level_line = ""
        if result["leveled_up"]:
            level_line = (
                f"\n🎉 **Level Up!** Your pet reached **Level {result['new_level']}**!"
                f"\n✨ Passive is now **Level {result['passive_level']}/{PET_PASSIVE_MAX_LEVEL}**."
            )

        await ctx.send(
            f"{fed_pet['emoji']} **{fed_pet['nickname'] or fed_pet['name']}** enjoyed "
            f"**{result['quantity']}× {result['treat']['name']}**!\n"
            f"✨ **+{result['xp_amount']} Pet XP**{level_line}"
        )


    async def _pet_fuse_autocomplete(self, interaction, current):
        current = (current or "").lower().strip()

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            async with db.execute(
                """
                SELECT pet_id, pet_type, pet_stage, nickname, level, variant_id, fusion_level, is_favorite
                FROM pets
                WHERE user_id = ? AND COALESCE(pet_type, pet_stage) != 'egg'
                ORDER BY pet_id
                """,
                (interaction.user.id,),
            ) as cursor:
                rows = await cursor.fetchall()

        choices = []

        for pet_id, pet_type, pet_stage, nickname, level, variant_id, fusion_level, is_favorite in rows:
            pet_type_id = pet_type or pet_stage

            if pet_type_id not in PETS and pet_type_id not in HALLOWEEN_PETS:
                continue

            definition = get_pet_definition(pet_type_id, variant_id)
            if not definition:
                continue

            # Count matching, non-favorited duplicates available to consume.
            matching_duplicates = sum(
                1
                for (
                    other_id,
                    other_type,
                    other_stage,
                    _nickname,
                    _level,
                    other_variant_id,
                    _fusion,
                    other_favorite,
                ) in rows
                if other_id != pet_id
                and (other_type or other_stage) == pet_type_id
                and (other_variant_id or "") == (variant_id or "")
                and not other_favorite
            )

            display_name = nickname or definition["name"]
            level = int(level or 1)
            fusion = int(fusion_level or 0)

            search = (
                f"{display_name} {definition['name']} {pet_type_id} "
                f"{pet_id} {level} {fusion} {variant_id or ''}"
            ).lower()

            if current and current not in search:
                continue

            variant_label = f" • {variant_id}" if variant_id else ""

            if matching_duplicates >= 5:
                duplicate_label = "5/5 duplicates"
            else:
                duplicate_label = f"{matching_duplicates}/5 duplicates"

            choices.append(
                app_commands.Choice(
                    name=(
                        f"{definition['emoji']} {display_name}"
                        f"{variant_label}"
                        f" • Lv. {level}"
                        f" • Fusion {fusion}/5"
                        f" • {duplicate_label}"
                    )[:100],
                    value=str(pet_id),
                )
            )

        return choices[:25]


    @commands.hybrid_command(
        name="fusion",
        description="Select a pet to receive a Fusion level using 5 matching duplicates.",
    )
    @app_commands.describe(
        pet="Choose the pet that will receive the Fusion level. You need 5 matching duplicates."
    )
    @app_commands.autocomplete(pet=_pet_fuse_autocomplete)
    async def pet_fuse(self, ctx: commands.Context, pet: str):
        await ctx.defer()
        try:
            target_pet_id = int(pet)
        except (TypeError, ValueError):
            return await ctx.send("❌ That pet selection is invalid.")

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            async with db.execute(
                "SELECT fusion_level, pet_type, variant_id FROM pets WHERE user_id = ? AND pet_id = ? LIMIT 1",
                (ctx.author.id, target_pet_id),
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            return await ctx.send("❌ You don't own that pet.")

        fusion_level = int(row[0] or 0)
        if fusion_level >= 5:
            definition = get_pet_definition(row[1] or "", row[2] or None)
            display = definition["name"] if definition else "this pet"
            return await ctx.send(
                f"🧬 **{display} has reached maximum Fusion 5.**\n\n"
                "Further fusions will **not** increase its passive bonus. "
                "They only give you another chance to discover a rare variant.\n\n"
                "This attempt will consume **5 matching duplicates**, **15,000 Stardust**, and **3 Astral Essence**.\n\n"
                "Continue?",
                view=PostFusionConfirmView(self, ctx, target_pet_id),
            )

        return await self._execute_pet_fusion(ctx, target_pet_id)


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
                    "⏳ Use `/incubator` with **Start incubation** to begin incubation."
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


    @commands.hybrid_command(
        name="incubator",
        description="View and manage your pet egg incubators.",
    )
    @app_commands.describe(
        action="Choose Start to begin incubation or Hatch to claim a ready egg.",
        egg="Choose the egg to start or hatch.",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Start incubation", value="start"),
            app_commands.Choice(name="Hatch ready egg", value="hatch"),
        ]
    )
    @app_commands.autocomplete(egg=_incubator_egg_autocomplete)
    async def incubator(
        self,
        ctx: commands.Context,
        action: str | None = None,
        egg: str | None = None,
    ):
        """View the incubator bay, start an egg, or hatch a ready egg."""
        await ctx.defer()

        action = action.lower().strip() if action else None
        egg = egg.lower().strip() if egg else None

        if action == "start":
            if not egg:
                return await ctx.send("❌ Choose an egg to start incubating.")
            return await self._incubator_start(ctx, egg)

        if action == "hatch":
            if not egg:
                return await ctx.send("❌ Choose an egg to hatch.")
            return await self._incubator_hatch(ctx, egg)

        if action is not None:
            return await ctx.send("❌ Choose **Start** or **Hatch** as the incubator action.")

        if egg:
            return await ctx.send("❌ Choose **Start** or **Hatch** when providing an egg.")

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            slots = await self._get_incubator_slots(db, ctx.author.id)
            rows = await self._incubator_rows(db, ctx.author.id)
            eggs = await self._owned_eggs(db, ctx.author.id)

        by_slot = {int(row[5]): row for row in rows}
        embed = discord.Embed(
            title=f"🥚 {ctx.author.display_name}'s Pet Incubation Bay",
            color=discord.Color.from_rgb(120, 140, 160),
        )

        tube_titles = ["🧪 TUBE I", "🧪 TUBE II", "🧪 TUBE III"]

        for slot_id in range(1, 4):
            if slot_id > slots:
                tube_art = (
                    "```text\n"
                    "╭────────╮\n"
                    "│  🧪    │\n"
                    "│        │\n"
                    "│   🔒   │\n"
                    "│ LOCKED │\n"
                    "│        │\n"
                    "│        │\n"
                    "╰────────╯\n"
                    "```"
                    "🔒 **Locked**\n"
                    "Unlock in `/shop` → 🛠️ Upgrades"
                )
                embed.add_field(name=tube_titles[slot_id - 1], value=tube_art, inline=True)
                continue

            row = by_slot.get(slot_id)
            if not row:
                tube_art = (
                    "```text\n"
                    "╭────────╮\n"
                    "│  🧪    │\n"
                    "│        │\n"
                    "│   ·    │\n"
                    "│        │\n"
                    "│        │\n"
                    "│        │\n"
                    "╰────────╯\n"
                    "```"
                    "🟢 **Empty**\n"
                    "Use `/incubator` with **Start incubation** and choose an egg"
                )
                embed.add_field(name=tube_titles[slot_id - 1], value=tube_art, inline=True)
                continue

            _incubator_id, egg_id, _started_at, ready_at, _notified, _slot_id = row
            info = ITEM_REGISTRY.get(egg_id, {"name": egg_id, "emoji": "🥚"})
            remaining = max(0, int(ready_at - time.time()))

            # Fill the lower part of the tube as incubation progresses.
            progress = max(0.0, min(1.0, 1 - (remaining / INCUBATION_SECONDS)))
            filled_rows = round(progress * 2)
            liquid_rows = {
                "full": "▓▓▓▓▓▓",
                "empty": "░░░░░░",
            }
            liquid = []
            for row_index in range(2):
                liquid.append(
                    liquid_rows["full"] if row_index >= 2 - filled_rows else liquid_rows["empty"]
                )

            if remaining <= 0:
                status = "✨ **READY TO HATCH!**"
                instruction = f"Use `/incubator` with **Hatch ready egg** and choose **{egg_id}**"
            else:
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                seconds = remaining % 60
                status = f"⏳ **{hours}h {minutes}m {seconds}s**"
                instruction = "🔔 Alert when ready"

            tube_art = (
                "```text\n"
                "╭────────╮\n"
                "│  🧪    │\n"
                "│        │\n"
               f"│   {info['emoji']}   │\n"
                "│        │\n"
               f"│ {liquid[0]} │\n"
               f"│ {liquid[1]} │\n"
                "╰────────╯\n"
                "```"
                f"{info['emoji']} **{info['name']}**\n"
                f"{status}\n"
                f"{instruction}"
            )
            embed.add_field(name=tube_titles[slot_id - 1], value=tube_art, inline=True)

        if eggs:
            egg_lines = []
            for egg_id, quantity in eggs.items():
                info = ITEM_REGISTRY.get(egg_id)
                if info:
                    egg_lines.append(f"{info['emoji']} **{info['name']}** ×{quantity}")
            if egg_lines:
                embed.add_field(
                    name="🥚 Eggs in Storage",
                    value="\n".join(egg_lines),
                    inline=False,
                )

        embed.set_footer(text=f"Unlocked tubes: {slots}/3 • Incubation time: 12 hours")
        await ctx.send(embed=embed)


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
                            f"Use `/incubator` with **Hatch ready egg** and choose **{egg_id}** to reveal your new companion! 🐣"
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

