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
    get_hatched_variant_chance, get_effective_hatch_variant_weights, get_variant_roll_pool,
)
from typing import TYPE_CHECKING
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from achievements import Achievements
from .config import *
from .core import *

# ---------------------------------------------------------------------------
# Incubator upgrade system
# ---------------------------------------------------------------------------
INCUBATOR_UPGRADE_CAPS = {
    1: {"speed": 15, "detection": 15, "luck": 10, "analysis": 10},
    2: {"speed": 15, "detection": 15, "luck": 10, "analysis": 10},
    3: {"speed": 15, "detection": 15, "luck": 10, "analysis": 10},
}

SPEED_REDUCTIONS = {
    0: 0.00, 1: 0.05, 2: 0.10, 3: 0.15, 4: 0.20, 5: 0.25,
    6: 0.30, 7: 0.35, 8: 0.40, 9: 0.45, 10: 0.50,
    11: 0.54, 12: 0.58, 13: 0.61, 14: 0.64, 15: 2 / 3,
}
DETECTION_BONUSES = {level: level * 0.005 for level in range(16)}
LUCK_OCCURRENCE_BONUSES = {level: level * 0.001 for level in range(11)}

# Tube-specific Stardust pricing. Material and Astral Essence requirements remain unchanged.
INCUBATOR_COST_MULTIPLIERS = {
    1: 0.50,
    2: 1.00,
    3: 1.50,
}


# Tube-specific material requirements (Tube 1 / Tube 2 / Tube 3).
INCUBATOR_MATERIAL_COSTS = {
    "speed": {
        1: [1, 1, 2],
        2: [2, 3, 4],
        3: [3, 4, 5],
        4: [4, 6, 8],
        5: [6, 8, 10],
        6: [7, 10, 13],
        7: [9, 13, 17],
        8: [11, 16, 21],
        9: [13, 19, 25],
        10: [15, 22, 30],
        11: [18, 26, 34],
        12: [20, 30, 39],
        13: [23, 34, 45],
        14: [26, 38, 50],
        15: [30, 43, 57],
    },
    "detection": {
        1: [1, 1, 2],
        2: [2, 3, 4],
        3: [3, 4, 6],
        4: [4, 6, 8],
        5: [5, 8, 10],
        6: [7, 10, 13],
        7: [9, 13, 16],
        8: [11, 16, 20],
        9: [13, 19, 24],
        10: [15, 22, 28],
        11: [18, 26, 33],
        12: [21, 30, 38],
        13: [24, 34, 43],
        14: [27, 38, 49],
        15: [30, 42, 55],
    },
    "luck": {
        1: [1, 2, 2],
        2: [2, 4, 5],
        3: [4, 6, 8],
        4: [6, 9, 11],
        5: [8, 12, 15],
        6: [10, 15, 19],
        7: [13, 19, 24],
        8: [16, 23, 30],
        9: [20, 28, 36],
        10: [24, 34, 43],
    },
    "analysis": {
        1: [1, 1, 1],
        2: [1, 1, 2],
        3: [1, 2, 3],
        4: [2, 3, 4],
        5: [3, 4, 6],
        6: [4, 5, 7],
        7: [5, 7, 9],
        8: [6, 9, 11],
        9: [8, 11, 14],
        10: [10, 14, 18],
    },
}

def _get_upgrade_cost(tube_id, category, level):
    material_id, _base_material_amount, essence_amount, base_cost = UPGRADE_COSTS[category][level]
    tube_index = max(1, min(3, int(tube_id))) - 1
    material_amount = INCUBATOR_MATERIAL_COSTS[category][level][tube_index]
    multiplier = INCUBATOR_COST_MULTIPLIERS.get(int(tube_id), 1.0)
    cost = int(round(base_cost * multiplier))
    return material_id, material_amount, essence_amount, cost

UPGRADE_COSTS = {
    "speed": {
        1: ("quantum_coil", 1, 0, 3000), 2: ("quantum_coil", 2, 0, 6000),
        3: ("quantum_coil", 3, 1, 10000), 4: ("quantum_coil", 4, 1, 15000),
        5: ("quantum_coil", 6, 2, 22500), 6: ("quantum_coil", 7, 3, 32500),
        7: ("quantum_coil", 9, 4, 45000), 8: ("quantum_coil", 11, 5, 60000),
        9: ("quantum_coil", 13, 6, 80000), 10: ("quantum_coil", 15, 8, 105000),
        11: ("quantum_coil", 18, 10, 135000), 12: ("quantum_coil", 20, 12, 175000),
        13: ("quantum_coil", 23, 15, 225000), 14: ("quantum_coil", 26, 18, 285000),
        15: ("quantum_coil", 30, 22, 360000),
    },
    "detection": {
        1: ("astral_lens", 1, 0, 5000), 2: ("astral_lens", 2, 0, 10000),
        3: ("astral_lens", 3, 1, 17500), 4: ("astral_lens", 4, 1, 25000),
        5: ("astral_lens", 5, 2, 35000), 6: ("astral_lens", 7, 3, 50000),
        7: ("astral_lens", 9, 4, 70000), 8: ("astral_lens", 11, 5, 95000),
        9: ("astral_lens", 13, 6, 125000), 10: ("astral_lens", 15, 8, 165000),
        11: ("astral_lens", 18, 10, 215000), 12: ("astral_lens", 21, 12, 275000),
        13: ("astral_lens", 24, 15, 350000), 14: ("astral_lens", 27, 18, 450000),
        15: ("astral_lens", 30, 22, 575000),
    },
    "luck": {
        1: ("mutation_catalyst", 1, 0, 7500), 2: ("mutation_catalyst", 2, 0, 15000),
        3: ("mutation_catalyst", 4, 1, 25000), 4: ("mutation_catalyst", 6, 2, 35000),
        5: ("mutation_catalyst", 8, 3, 50000), 6: ("mutation_catalyst", 10, 4, 70000),
        7: ("mutation_catalyst", 13, 5, 95000), 8: ("mutation_catalyst", 16, 7, 125000),
        9: ("mutation_catalyst", 20, 9, 165000), 10: ("mutation_catalyst", 24, 12, 215000),
    },
    "analysis": {
        1: ("analysis_module", 1, 0, 2000), 2: ("analysis_module", 1, 0, 4000),
        3: ("analysis_module", 1, 0, 7500), 4: ("analysis_module", 2, 0, 12000),
        5: ("analysis_module", 3, 1, 18000), 6: ("analysis_module", 4, 1, 27500),
        7: ("analysis_module", 5, 2, 40000), 8: ("analysis_module", 6, 3, 57500),
        9: ("analysis_module", 8, 4, 80000), 10: ("analysis_module", 10, 5, 110000),
    },
}
UPGRADE_LABELS = {
    "speed": ("⏱️", "Incubation Speed"),
    "detection": ("✨", "Variant Detection"),
    "luck": ("🍀", "Mutation Luck"),
    "analysis": ("🔬", "Egg Analysis"),
}
UPGRADE_DESCRIPTIONS = {
    "speed": "Reduces the incubation time of eggs in this tube.",
    "detection": "Increases the chance that a hatch produces a variant.",
    "luck": "Improves variant quality and adds a smaller bonus to variant occurrence chance.",
    "analysis": "Reveals more information about eggs incubating in this tube.",
}

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
    async def _get_incubator_upgrades(self, db, user_id, tube_id):
        async with db.execute(
            "SELECT speed, detection, luck, analysis FROM incubator_upgrades WHERE user_id = ? AND tube_id = ?",
            (user_id, tube_id),
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return {"speed": 0, "detection": 0, "luck": 0, "analysis": 0}
        return {key: int(value or 0) for key, value in zip(("speed", "detection", "luck", "analysis"), row)}

    def _speed_multiplier(self, level):
        reduction = SPEED_REDUCTIONS.get(max(0, min(15, int(level))), 0.0)
        return max(1 / 3, 1.0 - reduction)

    def _analysis_lines(self, egg_id, level, detection_level=0, luck_level=0):
        if level <= 0:
            return []
        pool = EGG_POOLS.get(egg_id, [])
        lines = [f"🔬 **Analysis Lv. {level}**"]
        if level >= 1:
            egg_info = ITEM_REGISTRY.get(egg_id, {"name": egg_id})
            lines.append(f"• Egg type: **{egg_info.get('name', egg_id)}**")
        if level >= 2:
            lines.append(f"• Possible pet count: **{len(pool)}**")
        if level >= 3:
            lines.append("• Hatch distribution: **equal chance among configured base pets**")
        if level >= 4:
            variant_possible = any(get_variant_roll_pool(pet_type) for pet_type in pool)
            lines.append(f"• Variants possible: **{'Yes' if variant_possible else 'No'}**")
        if level >= 5 and pool:
            chances = [get_hatched_variant_chance(pet_type, detection_level, luck_level) for pet_type in pool]
            lines.append(f"• Current variant chance: **{max(chances) * 100:.2f}%**")
        if level >= 6:
            names = []
            for pet_type in pool:
                definition = get_pet_definition(pet_type)
                if definition:
                    names.append(f"{definition['emoji']} {definition['name']}")
            if names:
                lines.append("• Possible pet pool: " + ", ".join(names))
        if level >= 7:
            if pool:
                lines.append("• Pet identity odds: **equal among the configured pool**")
        if level >= 8 and pool:
            lines.append("• Hatch distribution: **each configured base pet currently has an equal 1/N chance**")
        if level >= 9:
            variant_ids = []
            for pet_type in pool:
                for variant_id in get_variant_roll_pool(pet_type):
                    if variant_id not in variant_ids:
                        variant_ids.append(variant_id)
            if variant_ids:
                weight_map = {}
                for pet_type in pool:
                    for variant_id, weight in get_effective_hatch_variant_weights(pet_type, luck_level).items():
                        weight_map[variant_id] = weight
                variant_ids.sort(key=lambda vid: (-weight_map.get(vid, 0), vid))
                lines.append("• Variant pool: " + ", ".join(variant_ids))
                lines.append("• Variant rarity: **relative weighting shown by the configured hatch weights**")
        if level >= 10:
            lines.append("• Full analysis: **all currently configured egg, pet, variant, and weighting information**")
        return lines

    async def _upgrade_incubator(self, user_id, tube_id, category, channel=None):
        category = str(category).lower()
        tube_id = int(tube_id)
        if category not in UPGRADE_COSTS or tube_id not in INCUBATOR_UPGRADE_CAPS:
            return {"ok": False, "message": "❌ That incubator upgrade is not configured."}

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")
            async with db.execute("SELECT incubator_slots, stardust FROM users WHERE user_id = ?", (user_id,)) as cursor:
                user_row = await cursor.fetchone()
            if not user_row:
                await db.rollback()
                return {"ok": False, "message": "❌ You don't have an active station profile yet."}
            slots, stardust = int(user_row[0] or 1), int(user_row[1] or 0)
            if tube_id > slots:
                await db.rollback()
                return {"ok": False, "message": f"🔒 Tube {tube_id} is not unlocked yet."}

            levels = await self._get_incubator_upgrades(db, user_id, tube_id)
            current = levels[category]
            cap = INCUBATOR_UPGRADE_CAPS[tube_id][category]
            if current >= cap:
                await db.rollback()
                return {"ok": False, "message": f"✨ **{UPGRADE_LABELS[category][1]}** is already at its maximum level for Tube {tube_id}."}

            next_level = current + 1
            material_id, material_amount, essence_amount, cost = _get_upgrade_cost(tube_id, category, next_level)
            requirements = [(material_id, material_amount)]
            if essence_amount:
                requirements.append(("astral_essence", essence_amount))

            missing = []
            for item_id, amount in requirements:
                async with db.execute(
                    "SELECT COALESCE(SUM(quantity), 0) FROM inventory WHERE user_id = ? AND item_id = ?",
                    (user_id, item_id),
                ) as cursor:
                    row = await cursor.fetchone()
                owned = int(row[0] or 0) if row else 0
                if owned < amount:
                    missing.append((item_id, amount - owned))
            if stardust < cost:
                missing.append(("stardust", cost - stardust))
            if missing:
                await db.rollback()
                bits = []
                for item_id, amount in missing:
                    if item_id == "stardust":
                        bits.append(f"✨ **{amount:,}** more Stardust")
                    else:
                        info = ITEM_REGISTRY.get(item_id, {"name": item_id, "emoji": "📦"})
                        bits.append(f"{info.get('emoji', '📦')} **{amount}** more {info.get('name', item_id)}")
                return {"ok": False, "message": "❌ You don't have the required materials.\n" + "\n".join(bits)}

            for item_id, amount in requirements:
                remaining = amount
                async with db.execute(
                    """SELECT rowid, quantity
                       FROM inventory
                       WHERE user_id = ? AND item_id = ?
                       ORDER BY rowid""",
                    (user_id, item_id),
                ) as cursor:
                    inventory_rows = await cursor.fetchall()

                for rowid, quantity in inventory_rows:
                    if remaining <= 0:
                        break

                    quantity = int(quantity or 0)
                    take = min(quantity, remaining)
                    if take <= 0:
                        continue

                    new_quantity = quantity - take
                    if new_quantity > 0:
                        await db.execute(
                            "UPDATE inventory SET quantity = ? WHERE rowid = ?",
                            (new_quantity, rowid),
                        )
                    else:
                        await db.execute(
                            "DELETE FROM inventory WHERE rowid = ?",
                            (rowid,),
                        )

                    remaining -= take

                if remaining > 0:
                    # This should be impossible because the requirement check
                    # above already verified the aggregate quantity. Keep the
                    # transaction safe if inventory changes unexpectedly.
                    await db.rollback()
                    return {
                        "ok": False,
                        "message": "❌ Your inventory changed while processing the upgrade. Please try again.",
                    }
            levels[category] = next_level
            await db.execute(
                """INSERT INTO incubator_upgrades (user_id, tube_id, speed, detection, luck, analysis)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, tube_id) DO UPDATE SET
                     speed = excluded.speed, detection = excluded.detection,
                     luck = excluded.luck, analysis = excluded.analysis""",
                (user_id, tube_id, levels["speed"], levels["detection"], levels["luck"], levels["analysis"]),
            )
            await db.execute("UPDATE users SET stardust = stardust - ? WHERE user_id = ?", (cost, user_id))
            await db.commit()

            achievements_cog = cast(Achievements | None, self.bot.get_cog("Achievements"))
            if achievements_cog:
                await achievements_cog.record_incubator_upgrade(user_id, tube_id, levels, db=db, channel=channel)
                await db.commit()

            return {
                "ok": True, "tube_id": tube_id, "category": category, "level": next_level,
                "levels": levels, "material_id": material_id, "material_amount": material_amount,
                "essence_amount": essence_amount, "cost": cost,
            }

    async def _incubator_start(self, ctx: commands.Context, egg: str, tube: int):
        egg = egg.lower().strip()
        try:
            tube = int(tube)
        except (TypeError, ValueError):
            return await ctx.send("❌ Please choose a valid incubator tube.")

        if egg not in EGG_POOLS:
            return await ctx.send("❌ That isn't a valid pet egg.")

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")

            slots = await self._get_incubator_slots(db, ctx.author.id)
            if tube < 1 or tube > slots:
                return await ctx.send(
                    f"🔒 **Tube {tube}** is not unlocked yet. "
                    f"You currently have **{slots}/3** tubes unlocked."
                )

            rows = await self._incubator_rows(db, ctx.author.id)
            occupied_slots = {int(row[5]) for row in rows}
            if tube in occupied_slots:
                return await ctx.send(
                    f"❌ **Tube {tube}** is already occupied. "
                    "Choose an empty unlocked tube instead."
                )

            available_slot = tube

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

            upgrades = await self._get_incubator_upgrades(db, ctx.author.id, available_slot)
            started = time.time()
            duration = max(1, int(round(INCUBATION_SECONDS * self._speed_multiplier(upgrades["speed"]))))
            ready = started + duration
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
            f"⏳ Incubation time: **{duration // 3600}h {(duration % 3600) // 60}m**\n"
            "🔔 I'll alert you when it's ready to hatch!\n"
            f"Use `/incubator` with **Hatch ready egg**, choose **Tube {available_slot}**, and select **{egg}** when the timer finishes."
        )


    async def _incubator_hatch(self, ctx: commands.Context, egg: str, tube: int):
        egg = egg.lower().strip()
        try:
            tube = int(tube)
        except (TypeError, ValueError):
            return await ctx.send("❌ Please choose a valid incubator tube.")

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            slots = await self._get_incubator_slots(db, ctx.author.id)
            if tube < 1 or tube > slots:
                return await ctx.send(
                    f"🔒 **Tube {tube}** is not unlocked yet. "
                    f"You currently have **{slots}/3** tubes unlocked."
                )

            rows = await self._incubator_rows(db, ctx.author.id)
            row = next((candidate for candidate in rows if int(candidate[5]) == tube), None)
            if not row:
                return await ctx.send(
                    f"❌ **Tube {tube}** is currently empty. There is no egg to hatch there."
                )

            if row[1] != egg:
                info = ITEM_REGISTRY.get(row[1], {"name": row[1], "emoji": "🥚"})
                return await ctx.send(
                    f"❌ **Tube {tube}** contains **{info['name']}**, not **{egg}**. "
                    f"Choose **{info['name']}** from the egg selection for Tube {tube}."
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
            upgrades = await self._get_incubator_upgrades(db, ctx.author.id, int(slot_id))
            variant_id = roll_hatched_variant(
                pet_type,
                detection_level=upgrades["detection"],
                luck_level=upgrades["luck"],
            )
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
                if achievements_cog := cast(
                    Achievements | None,
                    self.bot.get_cog("Achievements"),
                ):
                    add_variant_progress = getattr(
                        achievements_cog,
                        "add_variant_discovery_progress",
                        None,
                    )
                    if add_variant_progress is not None:
                        await add_variant_progress(
                            ctx.author.id,
                            pet_type,
                            variant_id,
                            db=db,
                            channel=ctx.channel,
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

            achievements_cog = cast(
                Achievements | None,
                self.bot.get_cog("Achievements"),
            )
            if achievements_cog:
                # The Halloween hatch achievement is specifically for Halloween Eggs.
                # Glitched Eggs have their own achievement chain.
                if stored_egg == "halloween_egg":
                    await achievements_cog.add_halloween_hatch_progress(
                        ctx.author.id,
                        db=db,
                        channel=ctx.channel,
                    )

                if stored_egg == "glitched_egg":
                    await achievements_cog.add_glitched_pet_progress(
                        ctx.author.id,
                        pet_type,
                        db=db,
                        channel=ctx.channel,
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

