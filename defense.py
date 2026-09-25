import json
import random
import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

from database import ECONOMY_DB_NAME
from pets import get_active_pet_effects

DEFENSE_CAP = 0.70
DEFENSE_WEAPONS = {
    "stop_sign": {"name": "Stop Sign", "emoji": "🛑", "chance": 0.08, "desc": "A surprisingly sturdy traffic sign. Somehow useful in a fight."},
    "stick": {"name": "Stick", "emoji": "🪵", "chance": 0.04, "desc": "It's a stick. You picked it up. What did you expect?"},
    "wooden_sword": {"name": "Wooden Sword", "emoji": "🗡️", "chance": 0.10, "desc": "A humble wooden sword. Minecraft-approved adventuring equipment."},
    "wooden_shield": {"name": "Wooden Shield", "emoji": "🛡️", "chance": 0.07, "desc": "A basic wooden shield. Better than nothing!"},
    "wooden_spoon": {"name": "Wooden Spoon", "emoji": "🥄", "chance": 0.02, "desc": "A perfectly ordinary spoon. Surely this will protect you."},
    "heavy_wrench": {"name": "Suspiciously Heavy Wrench", "emoji": "🔧", "chance": 0.12, "desc": "Technically a maintenance tool. Technically."},
    "plasma_cutter": {"name": "Plasma Cutter", "emoji": "🔫", "chance": 0.25, "desc": "A precision plasma weapon recovered during the Halloween event. Cuts hazards apart before they reach you."},
}
DEFENSE_MESSAGES = {
    "stop_sign": "The Stop Sign said **STOP**. The hazard reluctantly complied.",
    "stick": "The Stick bravely stood between you and the hazard. Somehow, it worked.",
    "wooden_sword": "Your Wooden Sword intercepted the hazard! Minecraft logic prevails.",
    "wooden_shield": "Your Wooden Shield blocked the incoming hazard!",
    "wooden_spoon": "You raised the Wooden Spoon. The hazard reconsidered its life choices.",
    "heavy_wrench": "You swung the Heavy Wrench and sent the hazard packing!",
    "plasma_cutter": "The Plasma Cutter sliced through the incoming hazard before it could hit you!",
}

async def get_equipped_weapon(db, user_id):
    async with db.execute(
        "SELECT active_effects FROM users WHERE user_id = ?",
        (user_id,),
    ) as cursor:
        row = await cursor.fetchone()

    if not row:
        return None

    try:
        effects = json.loads(row[0] or "{}")
    except (TypeError, json.JSONDecodeError):
        effects = {}

    raw_weapon_id = effects.get("defense_weapon")
    return raw_weapon_id if isinstance(raw_weapon_id, str) and raw_weapon_id in DEFENSE_WEAPONS else None


async def get_defense_info(db, user_id):
    weapon_id = await get_equipped_weapon(db, user_id)

    weapon_chance = (
        DEFENSE_WEAPONS[weapon_id]["chance"]
        if weapon_id is not None
        else 0.0
    )

    pet_effects = await get_active_pet_effects(db, user_id)
    pet_chance = pet_effects.get("atomic_breath", 0.0)

    combined = min(
        DEFENSE_CAP,
        1 - ((1 - weapon_chance) * (1 - pet_chance)),
    )

    return weapon_id, weapon_chance, pet_chance, combined


async def roll_hazard_defense(db, user_id):
    weapon_id, weapon_chance, pet_chance, combined = await get_defense_info(db, user_id)
    if combined <= 0 or random.random() >= combined:
        return False, weapon_id, pet_chance, combined
    return True, weapon_id, pet_chance, combined

async def equip_weapon(db, user_id, weapon_id):
    if weapon_id not in DEFENSE_WEAPONS:
        return False, "Unknown defensive weapon."

    # Lock before checking ownership or modifying active_effects so the
    # ownership check and equip operation share the same atomic transaction.
    await db.execute("BEGIN IMMEDIATE")

    async with db.execute(
        "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
        (user_id, weapon_id),
    ) as cursor:
        row = await cursor.fetchone()

    if not row or (row[0] or 0) <= 0:
        await db.rollback()
        return False, "You don't own that defensive weapon."

    async with db.execute(
        "SELECT active_effects FROM users WHERE user_id = ?",
        (user_id,),
    ) as cursor:
        row = await cursor.fetchone()

    if not row:
        await db.rollback()
        return False, "You don't have an active station profile yet."

    try:
        effects = json.loads(row[0] or "{}")
    except (TypeError, json.JSONDecodeError):
        effects = {}

    effects["defense_weapon"] = weapon_id
    await db.execute(
        "UPDATE users SET active_effects = ? WHERE user_id = ?",
        (json.dumps(effects), user_id),
    )
    return True, None

class Defense(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.hybrid_group(name="defense", description="Manage your equipped defensive weapon.")
    async def defense(self, ctx):
        await ctx.defer()
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            weapon_id, weapon_chance, pet_chance, combined = await get_defense_info(db, ctx.author.id)
        embed = discord.Embed(title="🛡️ Defense System", color=discord.Color.blue())
        if weapon_id:
            weapon = DEFENSE_WEAPONS[weapon_id]
            embed.add_field(name="Equipped Weapon", value=f"{weapon['emoji']} **{weapon['name']}**\n{weapon['desc']}", inline=False)
            embed.add_field(name="Weapon Defense", value=f"**{weapon_chance * 100:.1f}%**", inline=True)
        else:
            embed.add_field(name="Equipped Weapon", value="None", inline=False)
        if pet_chance:
            embed.add_field(name="⚛️ Atomic Breath", value=f"**{pet_chance * 100:.1f}%**", inline=True)
        embed.add_field(name="Combined Defense", value=f"**{combined * 100:.1f}%** (cap {DEFENSE_CAP * 100:.0f}%)", inline=False)
        embed.set_footer(text="Defense prevents a scavenging hazard entirely. Hazard Reduction remains separate.")
        await ctx.send(embed=embed)

    @defense.command(name="view", description="View your currently equipped defense items.")
    async def defense_view(self, ctx):
        await self.defense(ctx)

    @defense.command(name="equip", description="Equip a defensive weapon you own.")
    @app_commands.describe(weapon_id="Choose a defensive weapon from your inventory.")
    async def equip(self, ctx, weapon_id: str):
        await ctx.defer()
        weapon_id = weapon_id.lower()
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            ok, error = await equip_weapon(db, ctx.author.id, weapon_id)
            if not ok: return await ctx.send(f"❌ {error}")
            await db.commit()
        weapon = DEFENSE_WEAPONS[weapon_id]
        await ctx.send(f"{ctx.author.mention} 🛡️ Equipped **{weapon['emoji']} {weapon['name']}**! Defense chance: **{weapon['chance'] * 100:.1f}%**.")

    @equip.autocomplete("weapon_id")
    async def weapon_autocomplete(self, interaction, current):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            async with db.execute("SELECT item_id, quantity FROM inventory WHERE user_id = ? AND quantity > 0", (interaction.user.id,)) as cursor:
                rows = await cursor.fetchall()
        current = current.lower().strip()
        return [app_commands.Choice(name=f"{DEFENSE_WEAPONS[i]['emoji']} {DEFENSE_WEAPONS[i]['name']} ({q}x)"[:100], value=i) for i,q in rows if i in DEFENSE_WEAPONS and (not current or current in DEFENSE_WEAPONS[i]['name'].lower())][:25]

async def setup(bot):
    await bot.add_cog(Defense(bot))
