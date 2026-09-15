import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

from database import ECONOMY_DB_NAME

MAX_LEVEL = 5

UPGRADE_DATA = {
    "mining": {
        "name": "Mining Laser",
        "emoji": "🔫",
        "column": "mining_upgrade",
        "levels": {
            1: {"cost": 2500, "component": "reinforced_laser_parts", "charges": 11, "stardust": 0.03, "rare": 0.005},
            2: {"cost": 7500, "component": "reinforced_laser_parts", "charges": 12, "stardust": 0.05, "rare": 0.010},
            3: {"cost": 20000, "component": "reinforced_laser_parts", "charges": 13, "stardust": 0.07, "rare": 0.015},
            4: {"cost": 50000, "component": "reinforced_laser_parts", "charges": 14, "stardust": 0.09, "rare": 0.020},
            5: {"cost": 125000, "component": "reinforced_laser_parts", "charges": 15, "stardust": 0.12, "rare": 0.025},
        },
    },
    "scavenging": {
        "name": "Scavenging Drone",
        "emoji": "🤖",
        "column": "scavenging_upgrade",
        "levels": {
            1: {"cost": 2500, "component": "drone_upgrade_kit", "charges": 11, "stardust": 0.03, "rare": 0.005},
            2: {"cost": 7500, "component": "drone_upgrade_kit", "charges": 12, "stardust": 0.05, "rare": 0.010},
            3: {"cost": 20000, "component": "drone_upgrade_kit", "charges": 13, "stardust": 0.07, "rare": 0.015},
            4: {"cost": 50000, "component": "drone_upgrade_kit", "charges": 14, "stardust": 0.09, "rare": 0.020},
            5: {"cost": 125000, "component": "drone_upgrade_kit", "charges": 15, "stardust": 0.12, "rare": 0.025},
        },
    },
}

# Raw materials required in addition to the crafted component.
# Requirements intentionally broaden and grow with each level.
UPGRADE_MATERIALS = {
    "mining": {
        1: {"iron_ore": 2, "copper_ore": 1},
        2: {"iron_ore": 3, "copper_ore": 2, "titanium_chunk": 1},
        3: {"iron_ore": 4, "copper_ore": 2, "titanium_chunk": 2, "wiring": 1},
        4: {"iron_ore": 5, "copper_ore": 3, "titanium_chunk": 2, "aluminum_ore": 1, "circuit_board": 1},
        5: {"iron_ore": 7, "copper_ore": 4, "titanium_chunk": 3, "aluminum_ore": 2, "circuit_board": 2, "wiring": 2},
    },
    "scavenging": {
        1: {"scrap_metal": 2, "nuts_bolts": 1},
        2: {"scrap_metal": 3, "nuts_bolts": 2, "wiring": 1},
        3: {"scrap_metal": 4, "nuts_bolts": 2, "wiring": 2, "circuit_board": 1},
        4: {"scrap_metal": 5, "nuts_bolts": 3, "wiring": 2, "circuit_board": 2, "glue": 1},
        5: {"scrap_metal": 7, "nuts_bolts": 4, "wiring": 3, "circuit_board": 3, "glue": 2, "titanium_chunk": 2},
    },
}

MATERIAL_NAMES = {
    "iron_ore": ("⛏️", "Iron Ore"),
    "copper_ore": ("🟠", "Copper Ore"),
    "titanium_chunk": ("⛏️", "Titanium Ore Chunk"),
    "aluminum_ore": ("⬜", "Aluminum Ore"),
    "scrap_metal": ("🔩", "Scrap Metal"),
    "nuts_bolts": ("🔧", "Nuts & Bolts"),
    "wiring": ("🧵", "Wiring"),
    "circuit_board": ("🟩", "Circuit Board"),
    "glue": ("🧴", "Industrial Glue"),
    "astral_core": ("🌌", "Astral Core"),
    "reinforced_laser_parts": ("🛠️", "Reinforced Laser Parts"),
    "drone_upgrade_kit": ("🤖", "Drone Upgrade Kit"),
    "astral_power_core": ("🌌", "Astral Power Core"),
}


class Upgrades(commands.Cog):
    """Permanent, resource-backed exploration upgrades."""

    def __init__(self, bot):
        self.bot = bot

    async def ensure_schema(self, db):
        async with db.execute("PRAGMA table_info(users)") as cursor:
            columns = {row[1] async for row in cursor}
        if "mining_upgrade" not in columns:
            await db.execute("ALTER TABLE users ADD COLUMN mining_upgrade INTEGER DEFAULT 0")
        if "scavenging_upgrade" not in columns:
            await db.execute("ALTER TABLE users ADD COLUMN scavenging_upgrade INTEGER DEFAULT 0")
        await db.commit()

    async def get_levels(self, user_id):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, stardust) VALUES (?, 0)",
                (user_id,),
            )
            await db.commit()
            async with db.execute(
                "SELECT COALESCE(stardust, 0), COALESCE(mining_upgrade, 0), COALESCE(scavenging_upgrade, 0) FROM users WHERE user_id = ?",
                (user_id,),
            ) as cursor:
                return await cursor.fetchone() or (0, 0, 0)

    async def get_effects(self, user_id, system):
        """Return the current upgrade effects for Exploration."""
        key = "mining_upgrade" if system == "mining" else "scavenging_upgrade"
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            async with db.execute(
                f"SELECT COALESCE({key}, 0) FROM users WHERE user_id = ?",
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()
        level = min(MAX_LEVEL, max(0, row[0] if row else 0))
        if level == 0:
            return {"level": 0, "max_charges": 10, "stardust_mult": 1.0, "rare_bonus": 0.0}
        data = UPGRADE_DATA[system]["levels"][level]
        return {
            "level": level,
            "max_charges": data["charges"],
            "stardust_mult": 1.0 + data["stardust"],
            "rare_bonus": data["rare"],
        }

    def material_text(self, materials):
        return "\n".join(
            f"{MATERIAL_NAMES[item][0]} {MATERIAL_NAMES[item][1]} ×{amount}"
            for item, amount in materials.items()
        )

    async def build_embed(self, user_id):
        stardust, mining_level, scavenging_level = await self.get_levels(user_id)
        embed = discord.Embed(
            title="⚙️ Exploration Upgrades",
            description="Permanent upgrades for your mining laser and scavenging drone.\n\nEach system has **5 levels**, and every upgrade requires both **Stardust and materials**.",
            color=discord.Color.from_rgb(0, 229, 255),
        )
        for system, level in (("mining", mining_level), ("scavenging", scavenging_level)):
            info = UPGRADE_DATA[system]
            if level >= MAX_LEVEL:
                data = info["levels"][MAX_LEVEL]
                value = (
                    f"**Level:** 5/5 ✨ MAX\n"
                    f"🔋 Max Charges: **{data['charges']}**\n"
                    f"💫 Stardust Output: **+{data['stardust'] * 100:.0f}%**\n"
                    f"🌟 Rare Loot Bonus: **+{data['rare'] * 100:.1f}%**"
                )
            else:
                next_level = level + 1
                data = info["levels"][next_level]
                mats = UPGRADE_MATERIALS[system][next_level]
                component = data["component"]
                comp_icon, comp_name = MATERIAL_NAMES[component]
                value = (
                    f"**Level:** {level}/5\n"
                    f"Next: **Level {next_level}**\n"
                    f"🔋 Max Charges: **{data['charges']}**\n"
                    f"💫 Stardust Output: **+{data['stardust'] * 100:.0f}%**\n"
                    f"🌟 Rare Loot Bonus: **+{data['rare'] * 100:.1f}%**\n\n"
                    f"💰 **{data['cost']:,} Stardust**\n"
                    f"{comp_icon} **{comp_name} ×1**\n"
                    f"{self.material_text(mats)}"
                    + ("\n🧬 **Nanite Retrofit Kit ×1**" if next_level == 5 else "")
                )
            embed.add_field(name=f"{info['emoji']} {info['name']}", value=value, inline=False)
        embed.set_footer(text=f"Available Stardust: {stardust:,} • Craft upgrade parts with /craft")
        return embed

    @commands.hybrid_command(name="upgrades", description="View your permanent mining and scavenging upgrades.")
    async def upgrades(self, ctx):
        await ctx.defer()
        await ctx.send(content=ctx.author.mention, embed=await self.build_embed(ctx.author.id))

    @commands.hybrid_command(name="upgrade", description="Purchase the next level of a permanent exploration upgrade.")
    @app_commands.describe(upgrade="Choose which exploration system to upgrade.")
    @app_commands.choices(upgrade=[
        app_commands.Choice(name="🔫 Mining Laser", value="mining"),
        app_commands.Choice(name="🤖 Scavenging Drone", value="scavenging"),
    ])
    async def upgrade(self, ctx, upgrade: str):
        await ctx.defer()
        if upgrade not in UPGRADE_DATA:
            return await ctx.send("❌ That upgrade does not exist.")

        info = UPGRADE_DATA[upgrade]
        column = info["column"]
        user_id = ctx.author.id

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.execute("BEGIN IMMEDIATE")
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, stardust) VALUES (?, 0)",
                (user_id,),
            )
            async with db.execute(
                f"SELECT COALESCE(stardust, 0), COALESCE({column}, 0) FROM users WHERE user_id = ?",
                (user_id,),
            ) as cursor:
                stardust, level = await cursor.fetchone()

            if level >= MAX_LEVEL:
                await db.rollback()
                return await ctx.send(f"{ctx.author.mention} ✨ **{info['name']}** is already maxed at Level 5!")

            next_level = level + 1
            data = info["levels"][next_level]
            required = dict(UPGRADE_MATERIALS[upgrade][next_level])
            component = data["component"]
            required[component] = required.get(component, 0) + 1
            if next_level == 5:
                required["nanite_retrofit_kit"] = 1

            if stardust < data["cost"]:
                await db.rollback()
                return await ctx.send(f"{ctx.author.mention} ❌ You need **{data['cost']:,} Stardust** for Level {next_level}. You have **{stardust:,}**.")

            missing = []
            for item_id, amount in required.items():
                async with db.execute(
                    "SELECT COALESCE(quantity, 0) FROM inventory WHERE user_id = ? AND item_id = ?",
                    (user_id, item_id),
                ) as cursor:
                    row = await cursor.fetchone()
                owned = row[0] if row else 0
                if owned < amount:
                    icon, name = MATERIAL_NAMES[item_id]
                    missing.append(f"{icon} {name} ×{amount - owned}")

            if missing:
                await db.rollback()
                return await ctx.send(
                    f"{ctx.author.mention} ❌ You're missing the materials for **{info['name']} Level {next_level}**:\n"
                    + "\n".join(missing)
                    + "\n\nUse `/craft` to make the required upgrade component."
                )

            for item_id, amount in required.items():
                await db.execute(
                    "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?",
                    (amount, user_id, item_id),
                )
            await db.execute(
                f"UPDATE users SET stardust = stardust - ?, {column} = ? WHERE user_id = ?",
                (data["cost"], next_level, user_id),
            )
            await db.commit()

        embed = discord.Embed(
            title="⬆️ Upgrade Complete!",
            description=(
                f"{ctx.author.mention}\n\n"
                f"{info['emoji']} **{info['name']}** is now **Level {next_level}/5**!\n\n"
                f"🔋 Max Charges: **{data['charges']}**\n"
                f"💫 Stardust Output: **+{data['stardust'] * 100:.0f}%**\n"
                f"🌟 Rare Loot Bonus: **+{data['rare'] * 100:.1f}%**\n\n"
                f"💰 Spent: **{data['cost']:,} Stardust**\n"
                "🧰 Required materials were consumed."
            ),
            color=discord.Color.from_rgb(0, 229, 255),
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Upgrades(bot))
