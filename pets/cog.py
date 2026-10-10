"""The Discord Cog that wires the pet system together."""

import asyncio
import random
import time
from typing import cast

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands, tasks

from error_handler import log_task_error

from database import ECONOMY_DB_NAME
from inventory import add_inventory_item, ITEM_REGISTRY
from seasonal_updates.halloween.halloween import is_active as halloween_is_active
from .variants import (
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
    PetCollectionView, PetCategoryView, IncubatorMainView, IncubatorTubeSelectView,
    IncubatorStartView, IncubatorHatchView,
)
from .management import PetManagementMixin
from .fusion import PetFusionMixin
from .incubator import (PetIncubatorMixin, INCUBATOR_UPGRADE_CAPS, UPGRADE_COSTS, UPGRADE_LABELS, UPGRADE_DESCRIPTIONS, SPEED_REDUCTIONS, DETECTION_BONUSES, LUCK_OCCURRENCE_BONUSES, _get_upgrade_cost)

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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS incubator_upgrades (
                user_id INTEGER NOT NULL,
                tube_id INTEGER NOT NULL,
                speed INTEGER NOT NULL DEFAULT 0,
                detection INTEGER NOT NULL DEFAULT 0,
                luck INTEGER NOT NULL DEFAULT 0,
                analysis INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, tube_id)
            )
        """)
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
        egg_ids = ["normal_egg", "halloween_egg", "glitched_egg"]
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
            return list(await cursor.fetchall())


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


    async def _incubator_action_data(self, user_id):
        """Return the currently owned eggs, open tubes, and ready eggs for UI menus."""
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            slots = await self._get_incubator_slots(db, user_id)
            eggs = await self._owned_eggs(db, user_id)
            rows = await self._incubator_rows(db, user_id)

        occupied = {int(row[5]) for row in rows}
        empty_tubes = [tube_id for tube_id in range(1, slots + 1) if tube_id not in occupied]
        now = time.time()
        ready_eggs = [row for row in rows if float(row[3]) <= now]
        return eggs, empty_tubes, ready_eggs


    async def _egg_autocomplete(self, interaction, current):
        current = (current or "").lower().strip()
        choices = []
        for egg_id in ("normal_egg", "halloween_egg", "glitched_egg"):
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
        namespace = getattr(interaction, "namespace", None)
        action = getattr(namespace, "action", None)
        action = str(action).lower().strip() if action else ""
        selected_tube = getattr(namespace, "tube", None)
        try:
            selected_tube = int(selected_tube) if selected_tube is not None else None
        except (TypeError, ValueError):
            selected_tube = None

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            if action == "hatch":
                rows = await self._incubator_rows(db, interaction.user.id)
                if selected_tube is not None:
                    egg_ids = [row[1] for row in rows if int(row[5]) == selected_tube]
                else:
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


    def _pet_embed(self, ctx, pet, page, total, bundle_count=1):
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

        pet_name_line = f"{pet['emoji']} **{pet['name']}**"
        if pet["nickname"]:
            pet_name_line += f" • {display_name}"
        if bundle_count > 1:
            pet_name_line += f" • **{bundle_count} Duplicates**"

        embed = discord.Embed(
            title=f"🐾 {ctx.author.display_name}'s Pet",
            description=(
                f"{pet_name_line}\n"
                + (f"-# Original: {pet['name']}\n" if pet["nickname"] and bundle_count <= 1 else "")
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
            if pet_type_id not in PETS and pet_type_id not in HALLOWEEN_PETS and pet_type_id not in GLITCHED_PETS:
                continue

            definition = get_pet_definition(pet_type_id, variant_id)
            if not definition:
                continue

            # Fusion ignores level and nickname. A favorite pet may be selected
            # as the target, but a favorite pet is never an eligible duplicate.
            target_type_key = str(pet_type_id or "").strip().lower()
            target_variant_key = str(variant_id or "").strip().lower()
            matching_duplicates = 0
            for other_id, other_type, other_stage, _nickname, _level, other_variant_id, _fusion, other_favorite in rows:
                other_type_key = str(other_type or other_stage or "").strip().lower()
                other_variant_key = str(other_variant_id or "").strip().lower()
                favorite_key = str(other_favorite or "").strip().lower()
                if (
                    other_id != pet_id
                    and other_type_key == target_type_key
                    and other_variant_key == target_variant_key
                    and favorite_key not in {"1", "true", "yes", "on"}
                ):
                    matching_duplicates += 1

            display_name = nickname or definition["name"]
            level = int(level or 1)
            fusion = int(fusion_level or 0)
            search = f"{display_name} {definition['name']} {pet_type_id} {pet_id} {level} {fusion} {variant_id or ''}".lower()
            if current and current not in search:
                continue

            variant_label = f" • {variant_id}" if variant_id else ""
            duplicate_requirement = 2 if (pet_type_id in HALLOWEEN_PETS or pet_type_id in GLITCHED_PETS) else 5
            duplicate_label = f"{min(matching_duplicates, duplicate_requirement)}/{duplicate_requirement} Duplicates"
            choices.append(
                app_commands.Choice(
                    name=(
                        f"{definition['emoji']} {display_name}{variant_label}"
                        f" • Lvl {level}"
                        f" • Fusion {fusion}/5"
                        f" • {duplicate_label}"
                    )[:100],
                    value=str(pet_id),
                )
            )
        return choices[:25]


    @commands.hybrid_group(
        name="fusion",
        description="Fuse pets or learn how Pet Fusion works.",
    )
    async def fusion(self, ctx: commands.Context):
        """Pet Fusion command group."""
        await ctx.send(
            "🧬 Choose a Fusion option: **fuse** to fuse a pet or **info** to learn how Fusion works."
        )


    @fusion.command(
        name="info",
        description="Learn how Pet Fusion works.",
    )
    async def pet_fusion_info(self, ctx: commands.Context):
        """Explain the Pet Fusion system."""
        embed = discord.Embed(
            title="🧬 Pet Fusion",
            description=(
                "Fusion strengthens a pet by consuming matching, non-favorited duplicates "
                "of the same pet and variant. **Normal/Glitched pets require 5; Halloween pets require 2.** "
                "Each Fusion level increases that pet's passive strength."
            ),
            color=discord.Color.blurple(),
        )

        embed.add_field(
            name="🔧 How Fusion Works",
            value=(
                "• Choose the pet you want to keep.\n"
                "• You need **5 matching duplicates** for Normal/Glitched pets or **2** for Halloween pets.\n"
                "• The duplicates must have the **same variant** as the target.\n"
                "• Duplicates marked as **Favorite** cannot be consumed.\n"
                "• Haunted location pets are unique companions and cannot be fused."
            ),
            inline=False,
        )

        fusion_lines = []
        for level, cost in FUSION_COSTS.items():
            fusion_lines.append(
                f"**Fusion {level}/5** — Pet Level **{FUSION_LEVEL_GATES[level]}+** • "
                f"**{cost['stardust']:,}** Stardust • **{cost['essence']}** ✨ Essence • "
                f"Passive **+{level * 2}%**"
            )

        embed.add_field(
            name="📈 Fusion Levels & Costs",
            value="\n".join(fusion_lines),
            inline=False,
        )

        embed.add_field(
            name="✨ Rare Variant Discovery",
            value=(
                "Every fusion also has a chance to discover a rare variant. "
                "The chance increases as the target's Fusion level rises:\n"
                "• Fusion 1 attempt: **3%**\n"
                "• Fusion 2 attempt: **3.5%**\n"
                "• Fusion 3 attempt: **4%**\n"
                "• Fusion 4 attempt: **4.5%**\n"
                "• Fusion 5 attempt: **5%**\n"
                "• Variant Hunt after Fusion 5: **7.5%**"
            ),
            inline=False,
        )

        embed.add_field(
            name="🧬 Fusion 5+ — Variant Hunts",
            value=(
                "Once a pet reaches **Fusion 5**, further attempts no longer increase its passive. "
                "They instead become **Variant Hunts**, costing **15,000 Stardust** and **3 Astral Essence** "
                "while consuming the same duplicate requirement as the pet's category (5 Normal/Glitched, 2 Halloween)."
            ),
            inline=False,
        )

        embed.add_field(
            name="🎉 If You Discover a Variant",
            value=(
                "**Infuse** keeps the current pet's Level, XP, Fusion, and passive progression.\n"
                "**Keep Separate** creates the discovered variant as a fresh **Level 1** pet."
            ),
            inline=False,
        )

        embed.set_footer(text="Use /fusion and select a pet to perform a Fusion.")
        return await ctx.send(embed=embed)


    @fusion.command(
        name="fuse",
        description="Fuse a pet using its required matching duplicates.",
    )
    @app_commands.describe(
        pet="Choose the pet to fuse."
    )
    @app_commands.autocomplete(pet=_pet_fuse_autocomplete)
    async def pet_fuse(self, ctx: commands.Context, pet: str):
        await ctx.defer()
        try:
            target_pet_id = int(pet)
        except (TypeError, ValueError):
            return await ctx.send("❌ That pet selection is invalid.")

        preview, error = await self._get_fusion_preview(ctx.author.id, target_pet_id)
        if error:
            return await ctx.send(error)

        variant_text = f" • {preview['target_variant_id']}" if preview["target_variant_id"] else ""
        duplicate_lines = []
        for duplicate in preview["duplicates"]:
            definition = get_pet_definition(preview["pet_type"], duplicate["variant_id"])
            name = definition["name"] if definition else preview["target_name"]
            duplicate_lines.append(
                f"• {name}{variant_text if duplicate['variant_id'] == preview['target_variant_id'] else ''} — Level {duplicate['level']}"
            )

        fusion_label = (
            f"Fusion {preview['target_fusion']}/5 → Fusion {preview['next_fusion']}/5"
            if preview["target_fusion"] < 5
            else "Variant Hunt"
        )
        content = (
            f"🧬 **Confirm Pet Fusion**\n\n"
            f"You are about to use **{preview['target_emoji']} {preview['target_name']}**{variant_text} "
            f"(Level **{preview['target_level']}** • {fusion_label}).\n\n"
            f"**Pets being fused:**\n"
            + "\n".join(duplicate_lines)
            + "\n\n────────────────────────\n\n"
            f"**Cost:** **{preview['cost']['stardust']:,} Stardust** • **{preview['cost']['essence']} Astral Essence**\n\n"
            "🔒 **Favorite a pet to protect it.** Favorited pets can never be released or consumed by Fusion. "
            "The target pet may be favorited; only the pets listed above will be consumed.\n\n"
            "⚠️ **These pets will be permanently consumed.**"
        )
        return await ctx.send(content, view=PostFusionConfirmView(self, ctx, preview))


    def _pet_collection_category(self, pet):
        """Return the user-facing /pets category for an owned pet."""
        pet_type = pet.get("pet_type")
        if pet_type in HAUNTED_PETS:
            return "haunted"
        if pet_type in HALLOWEEN_PETS:
            return "halloween"
        if pet_type in GLITCHED_PETS:
            return "glitched"
        return "normal"


    def _pet_group_key(self, pet):
        """Group inventory copies by the same pet, variant, and level."""
        return (
            pet.get("pet_type") or pet.get("pet_stage") or "",
            pet.get("variant_id") or "",
            int(pet.get("level") or 1),
        )


    def _bundle_count_for_pet(self, pets, pet):
        """Return the total owned copies matching this pet and variant."""
        key = self._pet_group_key(pet)
        return sum(1 for other in pets if self._pet_group_key(other) == key)


    def _group_owned_pets(self, pets, category):
        """Return grouped collection entries while preserving individual pet IDs."""
        filtered = [pet for pet in pets if self._pet_collection_category(pet) == category]
        groups = {}
        for pet in filtered:
            groups.setdefault(self._pet_group_key(pet), []).append(pet)

        entries = []
        for key, members in groups.items():
            # Prefer the active copy as the representative so opening a group
            # from /pets naturally lands on the currently equipped pet.
            representative = next((pet for pet in members if pet["is_active"]), members[0])
            entries.append({
                "pet": representative,
                "members": members,
                "count": len(members),
                "key": key,
            })

        entries.sort(
            key=lambda entry: (
                not entry["pet"]["is_active"],
                entry["pet"]["name"].lower(),
                int(entry["pet"]["level"] or 1),
                entry["pet"].get("variant_id") or "",
            )
        )
        return entries


    def _pet_collection_embed(self, ctx, pets):
        active = next((pet for pet in pets if pet["is_active"]), None)
        if active:
            active_name = active["nickname"] or active["name"]
            active_variant = ""
            if active.get("variant_id"):
                variant = get_variant_info(active["pet_type"], active["variant_id"])
                if variant:
                    active_variant = f"\n{variant['emoji']} **Variant:** {variant['name']}"
            active_text = (
                f"{active['emoji']} **{active_name}**\n"
                f"📈 Level **{active['level']}** • XP **{active['xp']}**"
                f"{active_variant}"
            )
        else:
            active_text = "No active companion is equipped. Choose a pet below and use **Equip Pet** to set one."

        category_meta = (
            ("normal", "🥚 Normal Eggs"),
            ("glitched", "💾 Glitched Eggs"),
            ("halloween", "🎃 Halloween Eggs"),
            ("haunted", "👻 Haunted Pets"),
        )
        lines = [label for _category, label in category_meta]

        embed = discord.Embed(
            title=f"🐾 {ctx.author.display_name}'s Pet Collection",
            description=(
                "⭐ **Active Companion**\n"
                f"{active_text}\n\n"
                "Choose a category below. Matching pets at the same level are bundled together.\n\n"
                + "\n\n".join(lines)
            ),
            color=discord.Color.from_rgb(120, 140, 160),
        )
        embed.set_footer(text="Different variants and levels remain separate entries.")
        return embed


    def _pet_category_embed(self, ctx, pets, category, page, page_count):
        labels = {
            "normal": "🥚 Normal Eggs",
            "glitched": "💾 Glitched Eggs",
            "halloween": "🎃 Halloween Eggs",
            "haunted": "👻 Haunted Pets",
        }
        entries = self._group_owned_pets(pets, category)
        per_page = 20
        start = page * per_page
        visible = entries[start:start + per_page]
        lines = []
        for entry in visible:
            pet = entry["pet"]
            marker = "⭐ " if any(member["is_active"] for member in entry["members"]) else ""
            count_text = f" • {entry['count']} Duplicates" if entry["count"] > 1 else ""
            lines.append(
                f"{marker}{pet['emoji']} **{pet['name']}** — Lv. **{pet['level']}**{count_text}"
            )

        description = (
            "Matching pets are bundled when the pet, variant, and level match. "
            "Different variants and levels remain separate.\n\n"
            + ("\n".join(lines) if lines else "No pets in this category yet.")
        )
        embed = discord.Embed(
            title=f"{labels.get(category, '🐾 Pet Collection')}",
            description=description,
            color=discord.Color.from_rgb(120, 140, 160),
        )
        embed.set_footer(text=f"Page {page + 1}/{page_count} • Select a pet group to manage a copy.")
        return embed


    @commands.hybrid_command(name="pets", description="View and manage your pets.")
    async def pets(self, ctx: commands.Context):
        await ctx.defer()
        pets = await self._get_owned_pets(ctx.author.id)
        if not pets:
            embed = discord.Embed(
                title=f"🐾 {ctx.author.display_name}'s Pet",
                description=(
                    "You don't have any pets yet!\n\n"
                    "🥚 Eggs can be discovered during scavenging.\n"
                    "⏳ Use `/incubator` and tap **Start Incubation** to hatch one."
                ),
                color=discord.Color.from_rgb(120, 140, 160),
            )
            return await ctx.send(embed=embed)

        # The old /pets experience is the landing screen again: show the
        # currently active companion first, then let the normal pet controls
        # handle navigation through the rest of the collection.
        index = next((i for i, pet in enumerate(pets) if pet["is_active"]), 0)
        view = PetManagementView(self, ctx.author.id, ctx, pets, index)
        bundle_count = self._bundle_count_for_pet(pets, pets[index])
        await ctx.send(embed=self._pet_embed(ctx, pets[index], index, len(pets), bundle_count=bundle_count), view=view)


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
            bundle_count = self._bundle_count_for_pet(pets, pets[index])
            await message.edit(embed=self._pet_embed(ctx, pets[index], index, len(pets), bundle_count=bundle_count), view=view)
        except discord.HTTPException:
            pass


    async def _incubator_main_embed(self, user_id, display_name=None):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            slots = await self._get_incubator_slots(db, user_id)
            rows = await self._incubator_rows(db, user_id)
            eggs = await self._owned_eggs(db, user_id)
            upgrades_by_slot = {
                slot_id: await self._get_incubator_upgrades(db, user_id, slot_id)
                for slot_id in range(1, slots + 1)
            }

        self._incubator_slots_cache = getattr(self, "_incubator_slots_cache", {})
        self._incubator_slots_cache[user_id] = slots
        by_slot = {int(row[5]): row for row in rows}
        title = f"🥚 {display_name}'s Pet Incubation Bay" if display_name else "🥚 Pet Incubation Bay"
        embed = discord.Embed(title=title, color=discord.Color.from_rgb(120, 140, 160))
        tube_titles = ["🧪 TUBE I", "🔬 TUBE II", "🧬 TUBE III"]

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

            upgrades = upgrades_by_slot[slot_id]
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
                    f"⏱️ Speed **Lv. {upgrades['speed']}/{INCUBATOR_UPGRADE_CAPS[slot_id]['speed']}** • "
                    f"✨ Detection **Lv. {upgrades['detection']}/{INCUBATOR_UPGRADE_CAPS[slot_id]['detection']}**\n"
                    f"🍀 Luck **Lv. {upgrades['luck']}/{INCUBATOR_UPGRADE_CAPS[slot_id]['luck']}** • "
                    f"🔬 Analysis **Lv. {upgrades['analysis']}/{INCUBATOR_UPGRADE_CAPS[slot_id]['analysis']}**\n"
                    "Use the **Start Incubation** button below to begin."
                )
                embed.add_field(name=tube_titles[slot_id - 1], value=tube_art, inline=True)
                continue

            _incubator_id, egg_id, started_at, ready_at, _notified, _slot_id = row
            info = ITEM_REGISTRY.get(egg_id, {"name": egg_id, "emoji": "🥚"})
            remaining = max(0, int(ready_at - time.time()))
            duration = max(1, int(ready_at - started_at))
            progress = max(0.0, min(1.0, 1 - (remaining / duration)))
            filled_rows = round(progress * 2)
            liquid = ["▓▓▓▓▓▓" if row_index >= 2 - filled_rows else "░░░░░░" for row_index in range(2)]

            if remaining <= 0:
                status = "✨ **READY TO HATCH!**"
                instruction = "Tap **Hatch** below to reveal your new companion."
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
                f"{instruction}\n\n"
                f"⏱️ Speed **Lv. {upgrades['speed']}/{INCUBATOR_UPGRADE_CAPS[slot_id]['speed']}** • "
                f"✨ Detection **Lv. {upgrades['detection']}/{INCUBATOR_UPGRADE_CAPS[slot_id]['detection']}**\n"
                f"🍀 Luck **Lv. {upgrades['luck']}/{INCUBATOR_UPGRADE_CAPS[slot_id]['luck']}** • "
                f"🔬 Analysis **Lv. {upgrades['analysis']}/{INCUBATOR_UPGRADE_CAPS[slot_id]['analysis']}**"
            )
            embed.add_field(name=tube_titles[slot_id - 1], value=tube_art[:1024], inline=True)

            analysis_lines = self._analysis_lines(
                egg_id,
                upgrades["analysis"],
                upgrades["detection"],
                upgrades["luck"],
            )
            if analysis_lines:
                embed.add_field(
                    name=f"🔬 Tube {slot_id} Analysis",
                    value="\n".join(analysis_lines)[:1024],
                    inline=False,
                )

        if eggs:
            egg_lines = []
            for egg_id, quantity in eggs.items():
                info = ITEM_REGISTRY.get(egg_id)
                if info:
                    egg_lines.append(f"{info['emoji']} **{info['name']}** ×{quantity}")
            if egg_lines:
                embed.add_field(name="🥚 Eggs in Storage", value="\n".join(egg_lines), inline=False)

        embed.set_footer(text=f"Unlocked tubes: {slots}/3 • Base incubation time: 12 hours")
        return embed

    async def _incubator_upgrade_tubes_embed(self, user_id):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            slots = await self._get_incubator_slots(db, user_id)
            rows = [(tube_id, await self._get_incubator_upgrades(db, user_id, tube_id)) for tube_id in range(1, slots + 1)]
        self._incubator_slots_cache = getattr(self, "_incubator_slots_cache", {})
        self._incubator_slots_cache[user_id] = slots
        embed = discord.Embed(
            title="🔧 Upgrade Tubes",
            description="Select an unlocked incubator tube to view and upgrade its systems.",
            color=discord.Color.from_rgb(120, 140, 160),
        )
        for tube_id, levels in rows:
            caps = INCUBATOR_UPGRADE_CAPS[tube_id]
            embed.add_field(
                name=f"{('🧪', '🔬', '🧬')[tube_id - 1]} Tube {tube_id}",
                value=(
                    f"⏱️ Speed: **{levels['speed']}/{caps['speed']}**\n"
                    f"✨ Detection: **{levels['detection']}/{caps['detection']}**\n"
                    f"🍀 Luck: **{levels['luck']}/{caps['luck']}**\n"
                    f"🔬 Analysis: **{levels['analysis']}/{caps['analysis']}**"
                ),
                inline=True,
            )
        embed.set_footer(text="Each tube is independent. Upgrade paths can be improved separately.")
        return embed

    async def _incubator_tube_upgrade_embed(self, user_id, tube_id):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            levels = await self._get_incubator_upgrades(db, user_id, tube_id)
        caps = INCUBATOR_UPGRADE_CAPS[tube_id]
        embed = discord.Embed(
            title=f"{('🧪', '🔬', '🧬')[tube_id - 1]} Tube {tube_id} — Upgrades",
            description="Select an upgrade path to view its effect and next-level requirements.",
            color=discord.Color.from_rgb(120, 140, 160),
        )
        for category in ("speed", "detection", "luck", "analysis"):
            emoji, label = UPGRADE_LABELS[category]
            embed.add_field(
                name=f"{emoji} {label}",
                value=f"Level **{levels[category]}/{caps[category]}**\n{UPGRADE_DESCRIPTIONS[category]}",
                inline=True,
            )
        embed.set_footer(text="Back returns to tube selection.")
        return embed

    async def _incubator_upgrade_detail_embed(self, user_id, tube_id, category, error=None, success=None):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            levels = await self._get_incubator_upgrades(db, user_id, tube_id)
            async with db.execute("SELECT stardust FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
            stardust = int(row[0] or 0) if row else 0
            owned = {}
            item_ids = {value[0] for value in UPGRADE_COSTS[category].values()} | {"astral_essence"}
            for item_id in item_ids:
                async with db.execute(
                    "SELECT COALESCE(SUM(quantity), 0) FROM inventory WHERE user_id = ? AND item_id = ?",
                    (user_id, item_id),
                ) as cursor:
                    item_row = await cursor.fetchone()
                owned[item_id] = int(item_row[0] or 0) if item_row else 0

        emoji, label = UPGRADE_LABELS[category]
        current = levels[category]
        cap = INCUBATOR_UPGRADE_CAPS[tube_id][category]
        embed = discord.Embed(title=f"{emoji} {label}", color=discord.Color.from_rgb(120, 140, 160))
        if success:
            embed.description = f"✅ **Upgrade Complete!**\n\nTube {tube_id}'s **{label}** is now **Level {success['level']}**."
        elif error:
            embed.description = error
        else:
            embed.description = UPGRADE_DESCRIPTIONS[category]
        embed.add_field(name="Current Level", value=f"**{current}/{cap}**", inline=True)

        if current < cap:
            next_level = current + 1
            # Use the tube-specific cost calculation here so the preview matches
            # the actual upgrade requirements for this tube. UPGRADE_COSTS contains
            # the base material amount/cost; _get_upgrade_cost applies the tube's
            # material scaling and Stardust multiplier.
            material_id, material_amount, essence_amount, cost = _get_upgrade_cost(
                tube_id, category, next_level
            )
            material_info = ITEM_REGISTRY.get(material_id, {"name": material_id, "emoji": "📦"})
            req = f"{material_info['emoji']} **{material_info['name']} ×{material_amount}**\n"
            if essence_amount:
                req += f"✨ **Astral Essence ×{essence_amount}**\n"
            req += f"💰 **{cost:,} Stardust**"
            embed.add_field(name=f"Next Level — {next_level}", value=req, inline=True)
            have = f"{material_info['emoji']} **{owned.get(material_id, 0)}** / {material_amount}\n"
            if essence_amount:
                have += f"✨ **{owned.get('astral_essence', 0)}** / {essence_amount}\n"
            have += f"💰 **{stardust:,}** / {cost:,}"
            embed.add_field(name="Your Inventory", value=have, inline=True)

            if category == "speed":
                embed.add_field(
                    name="Effect",
                    value=(
                        f"Level {next_level}: **{SPEED_REDUCTIONS[next_level] * 100:.2f}% shorter incubation**\n"
                        f"A 12-hour egg would take about **{12 * (1 - SPEED_REDUCTIONS[next_level]):.2f} hours**."
                    ),
                    inline=False,
                )
            elif category == "detection":
                embed.add_field(name="Effect", value=f"Level {next_level}: **+{DETECTION_BONUSES[next_level] * 100:.2f} percentage points** to variant occurrence.", inline=False)
            elif category == "luck":
                embed.add_field(
                    name="Effect",
                    value=f"Level {next_level}: **+{LUCK_OCCURRENCE_BONUSES[next_level] * 100:.2f} percentage points** to occurrence, plus stronger weighting toward higher-weight variants.",
                    inline=False,
                )
            else:
                unlocked = {
                    1: "Egg type", 2: "Possible pet count", 3: "Hatch distribution",
                    4: "Whether variants are possible", 5: "Current variant chance",
                    6: "Possible pet pool", 7: "Pet identities and relative rarity",
                    8: "Hatch distribution / configured probabilities", 9: "Variant pool and relative weighting",
                    10: "Full Advanced Analysis",
                }
                embed.add_field(name="Effect", value=f"Level {next_level} reveals: **{unlocked[next_level]}**", inline=False)
        else:
            embed.add_field(name="Maximum", value="✨ This upgrade path is fully mastered for this tube.", inline=False)
        return embed

    @commands.hybrid_command(
        name="incubator",
        description="View and manage your pet egg incubators.",
    )
    async def incubator(self, ctx: commands.Context):
        """View the incubator bay and manage eggs with buttons."""
        await ctx.defer()
        embed = await self._incubator_main_embed(ctx.author.id, ctx.author.display_name)
        await ctx.send(embed=embed, view=IncubatorMainView(self, ctx.author.id))


    @tasks.loop(minutes=1)
    async def incubator_checker(self):
        """Notify users when their 12-hour incubation finishes."""
        try:
            async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
                await self.ensure_schema(db)
                now = time.time()

                async with db.execute(
                    """
                    SELECT incubator_id, user_id, egg_id, slot_id
                    FROM pet_incubators
                    WHERE ready_at <= ? AND notified = 0
                    """,
                    (now,),
                ) as cursor:
                    rows = await cursor.fetchall()

                for incubator_id, user_id, egg_id, slot_id in rows:
                    channel = self.bot.get_channel(INCUBATOR_NOTIFICATION_CHANNEL_ID)
                    if channel is None:
                        try:
                            channel = await self.bot.fetch_channel(
                                INCUBATOR_NOTIFICATION_CHANNEL_ID
                            )
                        except Exception as e:
                            await log_task_error(self.bot, "incubator_checker / fetch channel", e, context=f"channel_id={INCUBATOR_NOTIFICATION_CHANNEL_ID}")
                            channel = None

                    if channel is None:
                        # Keep the notification pending so a later checker run
                        # can try again if the channel becomes available.
                        continue

                    if not isinstance(channel, discord.abc.Messageable):
                        continue

                    try:
                        info = ITEM_REGISTRY.get(
                            egg_id, {"name": egg_id, "emoji": "🥚"}
                        )
                        await channel.send(
                            f"<@{user_id}> 🔔 {info['emoji']} "
                            f"**Your pet egg is ready to hatch!**\n"
                            f"Your **{info['name']}** in **Tube {slot_id}** has finished incubating.\n\n"
                            "Use the **Hatch** button on `/incubator` to reveal your new companion! 🐣"
                        )
                    except Exception as e:
                        await log_task_error(self.bot, "incubator_checker / send notification", e, context=f"user_id={user_id}, egg_id={egg_id}, slot_id={slot_id}")
                        # Keep the notification pending if the channel/message
                        # cannot be sent right now.
                        continue

                    await db.execute(
                        "UPDATE pet_incubators SET notified = 1 WHERE incubator_id = ?",
                        (incubator_id,),
                    )

                await db.commit()
        except Exception as e:
            await log_task_error(self.bot, "incubator_checker (caught error)", e)
            # The notification loop must never take the bot down.
            return


    @incubator_checker.before_loop
    async def before_incubator_checker(self):
        await self.bot.wait_until_ready()

