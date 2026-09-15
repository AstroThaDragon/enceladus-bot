import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

from database import ECONOMY_DB_NAME

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
    "gauze": ("🧻", "Sterile Gauze"),
    "medical_alcohol": ("🧴", "Medical Alcohol"),
    "bandaids": ("🩹", "Bandaids"),
    "antiseptic_ointment": ("🧪", "Antiseptic Ointment"),
    "astral_core": ("🌌", "Astral Core"),
    "nanite_retrofit_kit": ("🧬", "Nanite Retrofit Kit"),
}

RECIPES = {
    "laser_parts_1": {"name": "Reinforced Laser Parts", "emoji": "🛠️", "result": "reinforced_laser_parts", "ingredients": {"iron_ore": 5, "copper_ore": 3, "scrap_metal": 3, "wiring": 3}},
    "laser_parts_2": {"name": "Reinforced Laser Parts II", "emoji": "🛠️", "result": "reinforced_laser_parts", "ingredients": {"iron_ore": 10, "copper_ore": 6, "titanium_chunk": 3, "aluminum_ore": 3, "circuit_board": 3, "wiring": 5}},
    "laser_parts_3": {"name": "Reinforced Laser Parts III", "emoji": "🛠️", "result": "reinforced_laser_parts", "ingredients": {"iron_ore": 15, "copper_ore": 9, "titanium_chunk": 5, "aluminum_ore": 5, "circuit_board": 6, "wiring": 8}},
    "laser_parts_4": {"name": "Reinforced Laser Parts IV", "emoji": "🛠️", "result": "reinforced_laser_parts", "ingredients": {"iron_ore": 20, "copper_ore": 12, "titanium_chunk": 8, "aluminum_ore": 8, "circuit_board": 10, "wiring": 12, "nuts_bolts": 7}},
    "laser_parts_5": {"name": "Reinforced Laser Parts V", "emoji": "🛠️", "result": "reinforced_laser_parts", "ingredients": {"iron_ore": 30, "copper_ore": 18, "titanium_chunk": 12, "aluminum_ore": 12, "circuit_board": 15, "wiring": 18, "astral_core": 1}},

    
    "drone_kit_1": {"name": "Drone Upgrade Kit", "emoji": "🛸", "result": "drone_upgrade_kit", "ingredients": {"scrap_metal": 5, "nuts_bolts": 5, "wiring": 3, "glue": 2}},
    "drone_kit_2": {"name": "Drone Upgrade Kit II", "emoji": "🛸", "result": "drone_upgrade_kit", "ingredients": {"scrap_metal": 10, "nuts_bolts": 8, "wiring": 6, "aluminum_ore": 3, "circuit_board": 3, "glue": 4}},
    "drone_kit_3": {"name": "Drone Upgrade Kit III", "emoji": "🛸", "result": "drone_upgrade_kit", "ingredients": {"scrap_metal": 15, "nuts_bolts": 12, "wiring": 9, "aluminum_ore": 5, "circuit_board": 6, "copper_ore": 4, "glue": 6}},
    "drone_kit_4": {"name": "Drone Upgrade Kit IV", "emoji": "🛸", "result": "drone_upgrade_kit", "ingredients": {"scrap_metal": 20, "nuts_bolts": 18, "wiring": 12, "aluminum_ore": 8, "circuit_board": 10, "titanium_chunk": 6, "glue": 9}},
    "drone_kit_5": {"name": "Drone Upgrade Kit V", "emoji": "🛸", "result": "drone_upgrade_kit", "ingredients": {"scrap_metal": 30, "nuts_bolts": 25, "wiring": 18, "aluminum_ore": 12, "circuit_board": 15, "titanium_chunk": 10, "glue": 14, "astral_core": 1}},


    "nanite_retrofit_kit": {"name": "Nanite Retrofit Kit", "emoji": "🧬", "result": "nanite_retrofit_kit", "ingredients": {"scrap_metal": 15, "wiring": 10, "circuit_board": 6, "glue": 4, "titanium_chunk": 3}},
    "astral_power_core": {"name": "Astral Power Core", "emoji": "🌌", "result": "astral_power_core", "ingredients": {"astral_core": 1, "titanium_chunk": 5, "copper_ore": 4, "circuit_board": 5, "wiring": 6}},

    
    "makeshift_medkit": {"name": "Makeshift Medkit", "emoji": "🩹", "result": "makeshift_medkit", "ingredients": {"bandaids": 3, "gauze": 2, "medical_alcohol": 1, "antiseptic_ointment": 1}},
}

CHOICES = [app_commands.Choice(name=f"{r['emoji']} {r['name']}", value=k) for k, r in RECIPES.items()]


class Crafting(commands.Cog):
    """Craftable components and field supplies used by station systems."""

    def __init__(self, bot):
        self.bot = bot

    async def ensure_inventory(self, db):
        await db.execute(
            """CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER NOT NULL,
                item_id TEXT NOT NULL,
                item_type TEXT NOT NULL DEFAULT 'crafting_material',
                quantity INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, item_id)
            )"""
        )
        await db.commit()

    async def owned(self, db, user_id):
        async with db.execute("SELECT item_id, quantity FROM inventory WHERE user_id = ?", (user_id,)) as cursor:
            return {item_id: quantity for item_id, quantity in await cursor.fetchall()}

    def recipe_embed(self, recipe, owned):
        lines = [f"{recipe['emoji']} **{recipe['name']}**", "", "**Materials Required:**"]
        for item_id, amount in recipe["ingredients"].items():
            icon, name = MATERIAL_NAMES[item_id]
            have = owned.get(item_id, 0)
            mark = "✅" if have >= amount else "❌"
            lines.append(f"{mark} {icon} {name} ×{amount}  *(you have {have})*")
        destination = "Use `/heal` to restore HP." if recipe["result"] == "makeshift_medkit" else "These crafted parts are used by `/upgrade`."
        lines += ["", f"🔨 **Produces:** {recipe['emoji']} {recipe['name']} ×1", "", destination]
        return discord.Embed(title="🔨 Crafting", description="\n".join(lines), color=discord.Color.from_rgb(0, 229, 255))

    @commands.hybrid_command(name="craft", description="Craft components used for permanent exploration upgrades.")
    @app_commands.describe(recipe="Choose an upgrade component to craft.")
    @app_commands.choices(recipe=CHOICES)
    async def craft(self, ctx, recipe: str):
        await ctx.defer()
        data = RECIPES.get(recipe)
        if not data:
            return await ctx.send("❌ That recipe does not exist.")

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_inventory(db)
            await db.execute("BEGIN IMMEDIATE")
            owned = await self.owned(db, ctx.author.id)
            missing = []
            for item_id, amount in data["ingredients"].items():
                if owned.get(item_id, 0) < amount:
                    icon, name = MATERIAL_NAMES[item_id]
                    missing.append(f"{icon} {name} ×{amount - owned.get(item_id, 0)}")
            if missing:
                await db.rollback()
                return await ctx.send(f"{ctx.author.mention} ❌ You're missing:\n" + "\n".join(missing))

            for item_id, amount in data["ingredients"].items():
                await db.execute("UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?", (amount, ctx.author.id, item_id))
            await db.execute(
                "INSERT INTO inventory (user_id, item_id, item_type, quantity) VALUES (?, ?, 'upgrade_component', 1) ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + 1",
                (ctx.author.id, data["result"]),
            )
            await db.commit()

        embed = discord.Embed(
            title="🔨 Crafting Complete!",
            description=(
                f"{ctx.author.mention}\n\nYou crafted **{data['emoji']} {data['name']} ×1**!\n\n"
                + ("Use `/heal` to patch yourself up when needed." if data["result"] == "makeshift_medkit" else "Use `/upgrade` when you have the Stardust and remaining materials needed for the next upgrade.")
            ),
            color=discord.Color.from_rgb(0, 229, 255),
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Crafting(bot))
