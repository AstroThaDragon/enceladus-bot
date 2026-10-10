"""Pet fusion execution helpers."""

import random
import time

import aiosqlite
import discord
from discord.ext import commands
from .views import FusionVariantView
from database import ECONOMY_DB_NAME
from inventory import add_inventory_item, ITEM_REGISTRY
from .variants import (
    ASTRAL_ESSENCE_ID, ASTRAL_ESSENCE_NAME, ASTRAL_ESSENCE_EMOJI,
    FUSION_COSTS, VARIANT_HUNT_COST, FUSION_LEVEL_GATES,
    HATCH_ESSENCE_CHANCE, RELEASE_ESSENCE_CHANCE,
    get_variant_info, get_variant_display, get_variant_ids_for_pet,
    GLITCHED_PET_TYPES,
    roll_hatched_variant, roll_fusion_variant, build_variant_collectibles,
)

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import discord
    import aiosqlite

from .config import *
from .core import *

class PetFusionMixin:
    bot: commands.Bot

    if TYPE_CHECKING:
        async def ensure_schema(
            self,
            db: aiosqlite.Connection,
        ) -> None:
            ...
    async def _get_fusion_preview(self, user_id: int, target_pet_id: int):
        """Return the exact unfavorited pets eligible for the next Fusion."""
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            async with db.execute(
                """
                SELECT pet_id, pet_type, pet_stage, nickname, level, variant_id,
                       fusion_level, is_favorite
                FROM pets
                WHERE user_id = ? AND pet_id = ?
                LIMIT 1
                """,
                (user_id, target_pet_id),
            ) as cursor:
                target = await cursor.fetchone()
            if not target:
                return None, "❌ You don't own that pet."

            pet_type = target[1] or target[2] or ""
            if pet_type not in PETS and pet_type not in HALLOWEEN_PETS and pet_type not in GLITCHED_PET_TYPES:
                return None, "❌ This pet cannot be fused. Haunted location pets are unique companions."

            level = int(target[4] or 1)
            fusion_level = int(target[6] or 0)
            variant_id = target[5] or ""
            if fusion_level < 5:
                next_fusion = fusion_level + 1
                required_level = FUSION_LEVEL_GATES[next_fusion]
                if level < required_level:
                    return None, f"🔒 **Fusion {next_fusion}** unlocks at **Level {required_level}**. This pet is currently **Level {level}**."
                cost = FUSION_COSTS[next_fusion]
                cost_label = f"Fusion {next_fusion}/5"
            else:
                next_fusion = 5
                cost = VARIANT_HUNT_COST
                cost_label = "Variant Hunt"

            duplicate_requirement = 2 if (pet_type in HALLOWEEN_PETS or pet_type in GLITCHED_PET_TYPES) else 5
            async with db.execute(
                f"""
                SELECT pet_id, pet_type, pet_stage, nickname, level, variant_id, fusion_level, is_favorite
                FROM pets
                WHERE user_id = ?
                  AND pet_id != ?
                  AND LOWER(TRIM(COALESCE(NULLIF(pet_type, ''), pet_stage, ''))) = LOWER(TRIM(?))
                  AND LOWER(TRIM(COALESCE(variant_id, ''))) = LOWER(TRIM(?))
                  AND CAST(COALESCE(is_favorite, 0) AS INTEGER) = 0
                ORDER BY pet_id
                LIMIT {duplicate_requirement}
                """,
                (user_id, target_pet_id, pet_type, variant_id),
            ) as cursor:
                duplicate_rows = list(await cursor.fetchall())

            if len(duplicate_rows) < duplicate_requirement:
                variant_text = " with the same variant" if variant_id else ""
                return None, f"❌ You need **{duplicate_requirement} non-favorited duplicates** of this pet{variant_text}. You currently have **{len(duplicate_rows)}/{duplicate_requirement}** available."

            definition = get_pet_definition(pet_type, variant_id)
            if not definition:
                return None, "❌ The selected pet definition could not be loaded."

            return {
                "target_pet_id": target_pet_id,
                "target_name": definition["name"],
                "target_emoji": definition["emoji"],
                "target_level": level,
                "target_fusion": fusion_level,
                "target_variant_id": variant_id,
                "pet_type": pet_type,
                "next_fusion": next_fusion,
                "cost": cost,
                "cost_label": cost_label,
                "duplicate_requirement": duplicate_requirement,
                "duplicates": [
                    {"pet_id": row[0], "nickname": row[3] or "", "level": int(row[4] or 1), "variant_id": row[5] or ""}
                    for row in duplicate_rows
                ],
            }, None

    async def _execute_pet_fusion(self, ctx: commands.Context, target_pet_id: int, duplicate_ids=None):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")

            async with db.execute(
                """
                SELECT pet_id, pet_type, pet_stage, nickname, level, xp, variant_id, fusion_level, is_favorite
                FROM pets
                WHERE user_id = ? AND pet_id = ?
                LIMIT 1
                """,
                (ctx.author.id, target_pet_id),
            ) as cursor:
                target = await cursor.fetchone()

            if not target:
                await db.rollback()
                return await ctx.send("❌ You don't own that pet.")

            pet_type = target[1] or target[2] or ""
            if pet_type not in PETS and pet_type not in HALLOWEEN_PETS and pet_type not in GLITCHED_PET_TYPES:
                await db.rollback()
                return await ctx.send(
                    "❌ This pet cannot be fused. Haunted location pets are unique companions."
                )

            level = int(target[4] or 1)
            fusion_level = int(target[7] or 0)
            variant_id = target[6] or ""

            if fusion_level < 5:
                next_fusion = fusion_level + 1
                required_level = FUSION_LEVEL_GATES[next_fusion]
                if level < required_level:
                    await db.rollback()
                    return await ctx.send(
                        f"🔒 **Fusion {next_fusion}** unlocks at **Level {required_level}**. "
                        f"This pet is currently **Level {level}**."
                    )
                cost = FUSION_COSTS[next_fusion]
                cost_label = f"Fusion {next_fusion}/5"
            else:
                next_fusion = 5
                cost = VARIANT_HUNT_COST
                cost_label = "Variant Hunt"

            duplicate_requirement = 2 if (pet_type in HALLOWEEN_PETS or pet_type in GLITCHED_PET_TYPES) else 5

            if duplicate_ids is not None:
                normalized_ids = [int(pet_id) for pet_id in duplicate_ids]
                if len(normalized_ids) != duplicate_requirement or len(set(normalized_ids)) != duplicate_requirement:
                    await db.rollback()
                    return await ctx.send("❌ The Fusion preview is no longer valid. Please run Fusion again.")

                placeholders = ",".join("?" for _ in normalized_ids)
                async with db.execute(
                    f"""
                    SELECT pet_id, pet_type, pet_stage, nickname, level, variant_id, fusion_level, is_favorite
                    FROM pets
                    WHERE user_id = ? AND pet_id IN ({placeholders})
                    """,
                    [ctx.author.id, *normalized_ids],
                ) as cursor:
                    duplicate_rows = list(await cursor.fetchall())

                by_id = {row[0]: row for row in duplicate_rows}
                valid = (
                    len(duplicate_rows) == duplicate_requirement
                    and all(
                        pet_id in by_id
                        and pet_id != target_pet_id
                        and str(by_id[pet_id][1] or by_id[pet_id][2] or "").strip().lower() == str(pet_type).strip().lower()
                        and str(by_id[pet_id][5] or "").strip().lower() == str(variant_id).strip().lower()
                        and int(by_id[pet_id][7] or 0) == 0
                        for pet_id in normalized_ids
                    )
                )
                if not valid:
                    await db.rollback()
                    return await ctx.send("🔒 **Fusion cancelled for safety.** One or more of the pets shown in the confirmation is no longer available or has been favorited. Nothing was consumed.")
                duplicate_rows = [by_id[pet_id] for pet_id in normalized_ids]
            else:
                async with db.execute(
                    f"""
                    SELECT pet_id, pet_type, pet_stage, nickname, level, variant_id, fusion_level, is_favorite
                    FROM pets
                    WHERE user_id = ?
                      AND pet_id != ?
                      AND LOWER(TRIM(COALESCE(NULLIF(pet_type, ''), pet_stage, ''))) = LOWER(TRIM(?))
                      AND LOWER(TRIM(COALESCE(variant_id, ''))) = LOWER(TRIM(?))
                      AND CAST(COALESCE(is_favorite, 0) AS INTEGER) = 0
                    ORDER BY pet_id
                    LIMIT {duplicate_requirement}
                    """,
                    (ctx.author.id, target_pet_id, pet_type, variant_id),
                ) as cursor:
                    duplicate_rows = list(await cursor.fetchall())

            if len(duplicate_rows) < duplicate_requirement:
                await db.rollback()
                variant_text = " with the same variant" if variant_id else ""
                return await ctx.send(
                    f"❌ You need **{duplicate_requirement} non-favorited duplicates** of this pet{variant_text}. "
                    f"You currently have **{len(duplicate_rows)}/{duplicate_requirement}** available."
                )

            async with db.execute(
                "SELECT COALESCE(stardust, 0) FROM users WHERE user_id = ?",
                (ctx.author.id,),
            ) as cursor:
                balance_row = await cursor.fetchone()
            stardust = int(balance_row[0] or 0) if balance_row else 0
            if stardust < cost["stardust"]:
                await db.rollback()
                return await ctx.send(
                    f"💸 **Insufficient Stardust!** {cost_label} costs **{cost['stardust']:,}** Stardust. "
                    f"You have **{stardust:,}**."
                )

            async with db.execute(
                "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                (ctx.author.id, ASTRAL_ESSENCE_ID),
            ) as cursor:
                essence_row = await cursor.fetchone()
            essence_owned = int(essence_row[0] or 0) if essence_row else 0
            if essence_owned < cost["essence"]:
                await db.rollback()
                return await ctx.send(
                    f"✨ **Not enough Astral Essence!** {cost_label} needs **{cost['essence']}** Essence. "
                    f"You have **{essence_owned}**."
                )

            await db.execute(
                "UPDATE users SET stardust = stardust - ? WHERE user_id = ?",
                (cost["stardust"], ctx.author.id),
            )
            await db.execute(
                """
                UPDATE inventory
                SET quantity = quantity - ?
                WHERE user_id = ? AND item_id = ?
                """,
                (cost["essence"], ctx.author.id, ASTRAL_ESSENCE_ID),
            )
            await db.execute(
                "DELETE FROM inventory WHERE user_id = ? AND item_id = ? AND quantity <= 0",
                (ctx.author.id, ASTRAL_ESSENCE_ID),
            )

            duplicate_ids = [row[0] for row in duplicate_rows]
            placeholders = ",".join("?" for _ in duplicate_ids)
            await db.execute(
                f"DELETE FROM pets WHERE user_id = ? AND pet_id IN ({placeholders})",
                [ctx.author.id, *duplicate_ids],
            )

            if fusion_level < 5:
                await db.execute(
                    "UPDATE pets SET fusion_level = ? WHERE user_id = ? AND pet_id = ?",
                    (next_fusion, ctx.author.id, target_pet_id),
                )

            discovered_variant = roll_fusion_variant(pet_type, fusion_level, exclude_variant=variant_id)
            if discovered_variant:
                from collectibles import record_collectible
                await record_collectible(
                    db, self.bot, ctx.author.id,
                    f"pet_variant:{pet_type}:{discovered_variant}",
                    category="Pet Variants",
                )
            achievements_cog = self.bot.get_cog("Achievements")
            if achievements_cog:
                add_variant_progress = getattr(
                    achievements_cog,
                    "add_variant_discovery_progress",
                    None,
                )
                if add_variant_progress is not None:
                    await add_variant_progress(
                        ctx.author.id,
                        pet_type,
                        discovered_variant,
                        db=db,
                        channel=ctx.channel,
                    )

            await db.commit()

        target_definition = get_pet_definition(pet_type, variant_id)
        if not target_definition:
            return await ctx.send("❌ The fused pet definition could no longer be found.")

        if not discovered_variant:
            if fusion_level < 5:
                return await ctx.send(
                    f"🧬 **Fusion complete!** {target_definition['emoji']} **{target_definition['name']}** "
                    f"is now **Fusion {next_fusion}/5**.\n"
                    f"✨ Passive strength increased by **+2%**.\n\n"
                    f"Consumed **{duplicate_requirement} duplicates**, **{cost['stardust']:,} Stardust**, and **{cost['essence']} Astral Essence**."
                )
            return await ctx.send(
                f"🧬 **Variant Hunt complete!** No new variant was discovered this time.\n\n"
                f"Consumed **{duplicate_requirement} duplicates**, **{cost['stardust']:,} Stardust**, and **{cost['essence']} Astral Essence**."
            )

        variant_info = get_variant_info(pet_type, discovered_variant)
        variant_definition = get_pet_definition(pet_type, discovered_variant)
        if not variant_info or not variant_definition:
            return await ctx.send("❌ The discovered variant could no longer be loaded.")

        await ctx.send(
            content=(
                f"🎉 **RARE VARIANT DISCOVERED!**\n\n"
                f"{variant_info['emoji']} **{variant_definition['name']}**\n"
                f"> {variant_info['lore']}\n\n"
                "What would you like to do with it?\n"
                "🧬 **Infuse** preserves the current pet's Level, XP, Fusion, and passive progression.\n"
                "📦 **Keep Separate** creates a fresh Level 1 copy."
            ),
            view=FusionVariantView(
                self, ctx.author.id, target_pet_id, pet_type, discovered_variant, ctx
            ),
        )

