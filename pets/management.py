"""Pet feeding, equipment, naming, favorite, release, and variant management helpers."""

import random
import time

import aiosqlite
import discord
from discord.ext import commands

from database import ECONOMY_DB_NAME
from inventory import add_inventory_item, ITEM_REGISTRY
from .variants import (
    ASTRAL_ESSENCE_ID, ASTRAL_ESSENCE_NAME, ASTRAL_ESSENCE_EMOJI,
    FUSION_COSTS, VARIANT_HUNT_COST, FUSION_LEVEL_GATES,
    HATCH_ESSENCE_CHANCE, RELEASE_ESSENCE_CHANCE,
    get_variant_info, get_variant_display, get_variant_ids_for_pet,
    roll_hatched_variant, roll_fusion_variant, build_variant_collectibles,
)
from typing import TYPE_CHECKING
from .config import *
from .core import *

class PetManagementMixin:
    bot: discord.Client

    if TYPE_CHECKING:
        async def ensure_schema(
            self,
            db: aiosqlite.Connection,
        ) -> None:
            ...
    async def _feed_specific_pet(self, user_id, pet_id, treat, quantity=1):
        xp_amounts = {
            "pet_snack": PET_TREAT_XP,
            "halloween_pet_candy": HALLOWEEN_PET_CANDY_XP,
        }
        if treat not in xp_amounts:
            return None, "❌ That isn't a valid pet treat."
        if not isinstance(quantity, int) or quantity < 1 or quantity > 99:
            return None, "❌ Quantity must be between **1** and **99**."

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

            owned_quantity = int(treat_row[0])
            if owned_quantity < quantity:
                await db.rollback()
                return None, (
                    f"❌ You only have **{owned_quantity}** "
                    f"of **{ITEM_REGISTRY[treat]['name']}**, but you tried to use **{quantity}**."
                )

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
            old_level = pet["level"]
            new_level = old_level
            new_xp = pet["xp"]
            xp_amount = 0

            # Apply treats one at a time so a large quantity behaves exactly
            # like feeding the same treats individually, including passive
            # bonuses changing when the pet levels up.
            for _ in range(quantity):
                treat_bonus = 0.0
                if pet["passive"].get("id") == "treat_xp_bonus":
                    treat_bonus = get_passive_value(
                        {
                            "passive": pet["passive"],
                            "level": new_level,
                            "fusion_level": pet.get("fusion_level", 0),
                        },
                        new_level,
                    )
                single_xp = int(base_xp * (1 + treat_bonus))
                xp_amount += single_xp
                new_xp += single_xp
                while new_xp >= xp_needed_for_next_level(new_level):
                    new_xp -= xp_needed_for_next_level(new_level)
                    new_level += 1

            await db.execute(
                "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?",
                (quantity, user_id, treat),
            )
            await db.execute(
                "DELETE FROM inventory WHERE user_id = ? AND item_id = ? AND quantity <= 0",
                (user_id, treat),
            )

            await db.execute(
                "UPDATE pets SET level = ?, xp = ? WHERE pet_id = ? AND user_id = ?",
                (new_level, new_xp, pet_id, user_id),
            )
            await db.commit()

        return {
            "pet": pet,
            "treat": ITEM_REGISTRY[treat],
            "quantity": quantity,
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
                SELECT pet_type, pet_stage, nickname, level, xp, is_active, is_favorite, variant_id, fusion_level
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
            variant_id = row[7] or None
            definition = get_pet_definition(pet_type, variant_id)
            if not definition:
                await db.rollback()
                return None

            essence_awarded = False
            if random.random() < RELEASE_ESSENCE_CHANCE:
                added_essence, _quantity, _max_quantity = await add_inventory_item(
                    db, user_id, ASTRAL_ESSENCE_ID, "special", 1
                )
                essence_awarded = added_essence > 0

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
            "essence_awarded": essence_awarded,
        }


    async def _infuse_variant(self, user_id, pet_id, base_pet_type, variant_id):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")
            async with db.execute(
                "SELECT pet_type, variant_id FROM pets WHERE user_id = ? AND pet_id = ? LIMIT 1",
                (user_id, pet_id),
            ) as cursor:
                row = await cursor.fetchone()

            if not row or (row[0] or "") != base_pet_type:
                await db.rollback()
                return None

            await db.execute(
                "UPDATE pets SET variant_id = ? WHERE user_id = ? AND pet_id = ?",
                (variant_id, user_id, pet_id),
            )
            await db.commit()

        return True


    async def _create_variant_pet(self, user_id, base_pet_type, variant_id):
        definition = get_pet_definition(base_pet_type)
        variant_info = get_variant_info(base_pet_type, variant_id)
        if not definition or not variant_info:
            return None

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")

            await db.execute(
                """
                INSERT INTO pets
                    (user_id, pet_stage, pet_type, nickname, level, xp, is_active, is_favorite, variant_id, fusion_level)
                VALUES (?, ?, ?, '', 1, 0, 0, 0, ?, 0)
                """,
                (user_id, base_pet_type, base_pet_type, variant_id),
            )
            await db.commit()

        return True

