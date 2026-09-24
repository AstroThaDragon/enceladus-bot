"""Pet incubator start and hatch helpers."""

import random
import time

import aiosqlite
import discord
from discord.ext import commands

from typing import cast
from achievements import Achievements

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
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from achievements import Achievements
from .config import *
from .core import *

class PetIncubatorMixin:
    bot: commands.Bot

    if TYPE_CHECKING:
        async def ensure_schema(
            self,
            _db: aiosqlite.Connection,
        ) -> None:
            ...

        async def _get_incubator_slots(
            self,
            db: aiosqlite.Connection,
            user_id: int,
        ) -> int:
            ...

        async def _incubator_rows(
            self,
            db: aiosqlite.Connection,
            user_id: int,
        ) -> list:
            ...
    async def _incubator_start(self, ctx: commands.Context, egg: str):
        egg = egg.lower().strip()

        if egg not in EGG_POOLS:
            return await ctx.send("❌ That isn't a valid pet egg.")

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")

            slots = await self._get_incubator_slots(db, ctx.author.id)
            rows = await self._incubator_rows(db, ctx.author.id)
            occupied_slots = {int(row[5]) for row in rows}
            available_slot = next(
                (slot_id for slot_id in range(1, slots + 1) if slot_id not in occupied_slots),
                None,
            )

            if available_slot is None:
                return await ctx.send(
                    "⏳ All unlocked incubator tubes are occupied! "
                    "Use `/incubator` to check their status."
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
                    (user_id, egg_id, started_at, ready_at, notified, slot_id)
                VALUES (?, ?, ?, ?, 0, ?)
                """,
                (ctx.author.id, egg, started, ready, available_slot),
            )
            await db.commit()

        info = ITEM_REGISTRY[egg]
        await ctx.send(
            f"{ctx.author.mention} {info['emoji']} **{info['name']} is now incubating in Tube {available_slot}!**\n"
            "⏳ Incubation time: **12 hours**\n"
            "🔔 I'll alert you when it's ready to hatch!\n"
            f"Use `/incubator` with **Hatch ready egg** and choose **{egg}** when the timer finishes."
        )


    async def _incubator_hatch(self, ctx: commands.Context, egg: str):
        egg = egg.lower().strip()

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            rows = await self._incubator_rows(db, ctx.author.id)

            row = next((candidate for candidate in rows if candidate[1] == egg), None)
            if not row:
                return await ctx.send(
                    f"❌ None of your incubator tubes currently contains **{egg}**."
                )

            _incubator_id, stored_egg, _started_at, ready_at, _notified, slot_id = row

            if time.time() < ready_at:
                remaining = int(ready_at - time.time())
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                return await ctx.send(
                    f"⏳ That egg in **Tube {slot_id}** isn't ready yet! "
                    f"**{hours}h {minutes}m** remaining."
                )

            pool = EGG_POOLS.get(stored_egg, [])
            if not pool:
                return await ctx.send("❌ This egg currently has no pets configured.")

            pet_type = random.choice(pool)
            variant_id = roll_hatched_variant(pet_type)
            definition = get_pet_definition(pet_type, variant_id)
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
                    (user_id, pet_stage, pet_type, nickname, level, xp, is_active, variant_id, fusion_level)
                VALUES (?, ?, ?, '', 1, 0, ?, ?, 0)
                """,
                (ctx.author.id, pet_type, pet_type, 0 if has_active else 1, variant_id or ""),
            )

            variant_discovered = False
            if variant_id:
                from collectibles import record_collectible
                await record_collectible(
                    db, self.bot, ctx.author.id,
                    f"pet_variant:{pet_type}:{variant_id}",
                    category="Pet Variants",
                )
                variant_discovered = True

            essence_awarded = False
            if random.random() < HATCH_ESSENCE_CHANCE:
                added_essence, _quantity, _max_quantity = await add_inventory_item(
                    db, ctx.author.id, ASTRAL_ESSENCE_ID, "special", 1
                )
                essence_awarded = added_essence > 0
            await db.execute(
                "DELETE FROM pet_incubators WHERE incubator_id = ?",
                (row[0],),
            )

            if stored_egg == "halloween_egg":
                achievements_cog = cast(
                    Achievements | None,
                    self.bot.get_cog("Achievements"),
                )
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
        discovery_lines = ""
        if variant_discovered:
            variant_info = get_variant_info(pet_type, variant_id)
            discovery_lines = (
                f"\n\n🎉 **RARE VARIANT DISCOVERED!** {variant_info['emoji']} **{variant_info['name']}**\n"
                f"> {variant_info['lore']}"
                if variant_info else ""
            )
        if essence_awarded:
            discovery_lines += "\n✨ **Astral Essence recovered!**"

        await ctx.send(
            f"{ctx.author.mention} 🐣 **EGG HATCHED!**\n\n"
            f"{definition['emoji']} **{definition['name']}**!\n"
            f"> *{definition['description']}*\n\n"
            f"✨ **Passive:** {definition['passive']['name']}\n"
            f"_{definition['passive']['description']}_\n\n"
            f"📈 **Level 1** • Passive Level **1/{PET_PASSIVE_MAX_LEVEL}**\n"
            f"🥚 Hatched from **Tube {slot_id}**\n"
            f"{active_note}{discovery_lines}"
        )

