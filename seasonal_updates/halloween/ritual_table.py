import aiosqlite
import discord
from discord.ext import commands

from database import ECONOMY_DB_NAME
from inventory import ITEM_REGISTRY, add_inventory_item
from seasonal_updates.halloween.halloween import (
    halloween_channel_message,
    is_active as halloween_is_active,
    is_halloween_channel,
)


RITUAL_RECIPES = {
    "warding_sigil": {
        "name": "Warding Sigil",
        "emoji": "🕯️",
        "ingredients": {
            "ritual_chalk": 2,
            "consecrated_salt": 2,
            "grave_marker_shard": 1,
            "black_wax": 1,
        },
        "result": "warding_sigil",
        "description": "A ritual mark that completely blocks the first negative Sanity choice of your next Haunted run.",
    },
    "mirror_ward": {
        "name": "Mirror Ward",
        "emoji": "🪞",
        "ingredients": {
            "dusty_looking_glass": 1,
            "ritual_chalk": 2,
            "spectral_thread": 1,
            "glowmoss": 1,
        },
        "result": "mirror_ward",
        "description": "A reflective ward that halves the first negative Sanity choice of your next Haunted run.",
    },
    "dead_air_charm": {
        "name": "Dead-Air Charm",
        "emoji": "📡",
        "ingredients": {
            "recorded_static": 1,
            "black_wax": 1,
            "funeral_thread": 2,
            "incense_resin": 1,
        },
        "result": "dead_air_charm",
        "description": "A dead-air charm that suppresses part of the supernatural Sanity drain in your next Broadcast Station run.",
    },
    "empty_room_token": {
        "name": "Empty Room Token",
        "emoji": "🪙",
        "ingredients": {
            "bent_key": 1,
            "old_guest_receipt": 1,
            "grave_dust": 1,
            "ritual_chalk": 1,
        },
        "result": "empty_room_token",
        "description": "A ritual token that nullifies the first negative Sanity choice in your next Endless Hotel run.",
    },
    "watchers_eye": {
        "name": "Watcher's Eye",
        "emoji": "👁️",
        "ingredients": {
            "plastic_eye": 1,
            "dusty_looking_glass": 1,
            "ectoplasm": 2,
            "blackened_grease": 1,
        },
        "result": "watchers_eye",
        "description": "An occult focus that forces your next Haunted run to reveal a location-specific encounter at its first stage.",
    },
    "containment_mark": {
        "name": "Containment Mark",
        "emoji": "⛓️",
        "ingredients": {
            "unknown_biological_residue": 1,
            "consecrated_salt": 2,
            "grave_marker_shard": 1,
            "ritual_chalk": 2,
        },
        "result": "containment_mark",
        "description": "A containment mark that heavily reduces supernatural Sanity loss in your next Research Facility run.",
    },
}

for _recipe in RITUAL_RECIPES.values():
    ITEM_REGISTRY.setdefault(
        _recipe["result"],
        {
            "name": _recipe["name"],
            "emoji": _recipe["emoji"],
            "max_quantity": 10,
            "type": "Ritual Item",
            "desc": _recipe["description"],
        },
    )


def item_name(item_id):
    return ITEM_REGISTRY.get(item_id, {}).get("name", item_id.replace("_", " ").title())


def item_emoji(item_id):
    return ITEM_REGISTRY.get(item_id, {}).get("emoji", "🕯️")


class RitualSelect(discord.ui.Select):
    def __init__(self, cog, owner_id):
        self.cog = cog
        self.owner_id = owner_id
        options = [
            discord.SelectOption(label=r["name"], value=rid, emoji=r["emoji"], description="Perform this ritual")
            for rid, r in RITUAL_RECIPES.items()
        ]
        super().__init__(placeholder="Choose a ritual...", options=options)

    async def callback(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ This ritual table belongs to someone else.", ephemeral=True)
            return
        if not halloween_is_active():
            await interaction.response.send_message("🎃 The Ritual Table is dormant outside Halloween.", ephemeral=True)
            return
        await self.cog.perform(interaction, self.values[0])


class RitualView(discord.ui.View):
    def __init__(self, cog, owner_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.owner_id = owner_id
        self.add_item(RitualSelect(cog, owner_id))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ This ritual table belongs to someone else.",
                ephemeral=True,
            )
            return False
        if not is_halloween_channel(interaction.channel):
            await interaction.response.send_message(
                halloween_channel_message(),
                ephemeral=True,
            )
            return False
        if not halloween_is_active():
            await interaction.response.send_message(
                "🎃 The Ritual Table is dormant outside Halloween.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(
        label="Back",
        emoji="🎃",
        style=discord.ButtonStyle.secondary,
    )
    async def back_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        cauldron = self.cog.bot.get_cog("Cauldron")
        if cauldron:
            await cauldron.show_seasonal_hub(interaction)
        else:
            await interaction.response.send_message(
                "The seasonal crafting hub is unavailable.",
                ephemeral=True,
            )


class RitualTable(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _owned(self, db, user_id):
        async with db.execute(
            "SELECT item_id, quantity FROM inventory WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            return {row[0]: row[1] for row in await cursor.fetchall()}

    async def show_menu(self, interaction):
        embed = discord.Embed(
            title="🕯️ Ritual Table",
            description=(
                "The surface is covered in chalk marks, candle wax, and diagrams you do not remember drawing.\n\n"
                "Choose a ritual to perform."
            ),
            color=discord.Color.dark_purple(),
        )
        embed.add_field(
            name="📖 Known Rituals",
            value="\n".join(f"{r['emoji']} **{r['name']}**" for r in RITUAL_RECIPES.values()),
            inline=False,
        )
        await interaction.response.edit_message(
            embed=embed,
            view=RitualView(self, interaction.user.id),
        )

    async def perform(self, interaction, recipe_id):
        recipe = RITUAL_RECIPES[recipe_id]
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await db.execute("BEGIN IMMEDIATE")
            owned = await self._owned(db, interaction.user.id)
            missing = [
                f"{item_emoji(i)} {item_name(i)} ×{a-owned.get(i,0)}"
                for i,a in recipe["ingredients"].items()
                if owned.get(i,0) < a
            ]
            if missing:
                await db.rollback()
                await interaction.response.send_message(
                    "❌ **Missing ritual components:**\n" + "\n".join(missing),
                    ephemeral=True,
                )
                return

            for item_id, amount in recipe["ingredients"].items():
                await db.execute(
                    "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?",
                    (amount, interaction.user.id, item_id),
                )

            added, _, _ = await add_inventory_item(
                db, interaction.user.id, recipe["result"], "Ritual Item", 1
            )
            if added < 1:
                for item_id, amount in recipe["ingredients"].items():
                    await db.execute(
                        "UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_id = ?",
                        (amount, interaction.user.id, item_id),
                    )
                await db.commit()
                await interaction.response.send_message(
                    f"❌ Your **{recipe['name']}** inventory is full. Your components were returned.",
                    ephemeral=True,
                )
                return

            await db.commit()

        await interaction.response.send_message(
            f"🕯️ **Ritual complete.** You created **{recipe['emoji']} {recipe['name']} ×1**.\n\n"
            f"*{recipe['description']}*",
            ephemeral=True,
        )

    @commands.hybrid_command(name="ritual_table", description="Open the Halloween Ritual Table.")
    async def ritual_table(self, ctx):
        if not is_halloween_channel(ctx.channel):
            await ctx.send(halloween_channel_message())
            return
        if not halloween_is_active():
            await ctx.send("🎃 The Ritual Table is dormant right now.")
            return
        await ctx.defer()
        embed = discord.Embed(
            title="🕯️ Ritual Table",
            description="A place for things that are too strange for a workshop and too solid for a cauldron.",
            color=discord.Color.dark_purple(),
        )
        await ctx.send(embed=embed, view=RitualView(self, ctx.author.id))


async def setup(bot):
    await bot.add_cog(RitualTable(bot))
