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


WORKSHOP_RECIPES = {
    "ghost_radio": {
        "name": "Ghost Radio",
        "emoji": "📻",
        "ingredients": {
            "radio_components": 1,
            "circuit_board": 1,
            "wiring": 2,
            "ectoplasm": 1,
        },
        "result": "ghost_radio",
        "result_type": "Haunted Workshop",
        "description": "A battered radio that tunes into impossible transmissions and prepares a guaranteed signal encounter on your next Haunted run.",
    },
    "mascot_tracker": {
        "name": "Mascot Tracker",
        "emoji": "📡",
        "ingredients": {
            "circuit_board": 1,
            "mechanical_parts": 2,
            "mascot_fabric": 1,
            "recorded_static": 1,
        },
        "result": "mascot_tracker",
        "result_type": "Haunted Workshop",
        "description": "A crude motion detector that improves your chance of uncovering a Halloween collectible on your next Haunted run.",
    },
    "room_314_key": {
        "name": "Room 314 Key",
        "emoji": "🗝️",
        "ingredients": {
            "bent_key": 1,
            "old_guest_receipt": 1,
            "flickering_bulb": 1,
        },
        "result": "room_314_key",
        "result_type": "Haunted Workshop",
        "description": "A rebuilt hotel key that can unlock a shortcut through the impossible hotel on your next Endless Hotel run.",
    },
    "fog_lantern": {
        "name": "Fog Lantern",
        "emoji": "🏮",
        "ingredients": {
            "damaged_battery": 1,
            "flickering_bulb": 1,
            "condensed_fog": 2,
            "scrap_metal": 1,
        },
        "result": "fog_lantern",
        "result_type": "Haunted Workshop",
        "description": "A patched-together lantern that cuts supernatural Sanity loss in half on your next Fogbound Town run.",
    },
    "spectral_receiver": {
        "name": "Spectral Receiver",
        "emoji": "📡",
        "ingredients": {
            "radio_components": 2,
            "circuit_board": 1,
            "recorded_static": 2,
            "cursed_fabric": 1,
        },
        "result": "spectral_receiver",
        "result_type": "Haunted Workshop",
        "description": "A device that sharpens spectral signals and improves your chance of uncovering a Halloween collectible on your next Haunted run.",
    },
    "security_monitor": {
        "name": "Security Monitor",
        "emoji": "📺",
        "ingredients": {
            "circuit_board": 2,
            "wiring": 2,
            "mechanical_parts": 1,
            "damaged_vhs_tape": 1,
        },
        "result": "security_monitor",
        "result_type": "Haunted Workshop",
        "description": "A salvaged monitor that warns you of danger and cushions one Sanity hit during your next Haunted run.",
    },

    "yellow_halls_beacon": {
        "name": "Yellow Halls Beacon",
        "emoji": "💡",
        "ingredients": {
            "strange_fluorescent_tube": 1,
            "frayed_electrical_wire": 2,
            "yellow_wallpaper_scrap": 1,
        },
        "result": "yellow_halls_beacon",
        "result_type": "Haunted Workshop",
        "description": "A jury-rigged fluorescent beacon that cuts supernatural Sanity loss in half during your next Yellow Halls run.",
    },
    "highway_payphone_kit": {
        "name": "Payphone Repair Kit",
        "emoji": "☎️",
        "ingredients": {
            "damaged_payphone_part": 1,
            "old_road_map": 1,
            "rusty_car_part": 1,
        },
        "result": "highway_payphone_kit",
        "result_type": "Haunted Workshop",
        "description": "A bundle of salvaged parts that can coax a dead roadside payphone back to life during your next Dead-End Highway run.",
    },
    "drowned_flood_lamp": {
        "name": "Flood Lamp",
        "emoji": "🔦",
        "ingredients": {
            "flooded_flashlight": 1,
            "corroded_train_part": 1,
            "damaged_conductor": 1,
            "wiring": 1,
        },
        "result": "drowned_flood_lamp",
        "result_type": "Haunted Workshop",
        "description": "A sealed light built from drowned station hardware that cuts supernatural Sanity loss in half during your next Drowned Station run.",
    },
    "campground_static_filter": {
        "name": "Static Filter",
        "emoji": "📻",
        "ingredients": {
            "static_damaged_radio": 1,
            "damaged_antenna": 1,
            "corrupted_video_tape": 1,
            "circuit_board": 1,
        },
        "result": "campground_static_filter",
        "result_type": "Haunted Workshop",
        "description": "A crude signal filter that suppresses some of the things hiding inside the campground's static during your next Silent Campground run.",
    },
}

for _recipe in WORKSHOP_RECIPES.values():
    ITEM_REGISTRY.setdefault(
        _recipe["result"],
        {
            "name": _recipe["name"],
            "emoji": _recipe["emoji"],
            "max_quantity": 10,
            "type": _recipe["result_type"],
            "desc": _recipe["description"],
        },
    )


def ingredient_name(item_id):
    return ITEM_REGISTRY.get(item_id, {}).get("name", item_id.replace("_", " ").title())


def ingredient_emoji(item_id):
    return ITEM_REGISTRY.get(item_id, {}).get("emoji", "🔧")


def format_recipe(recipe, owned):
    lines = [f"{recipe['emoji']} **{recipe['name']}**", recipe["description"], "", "**Parts:**"]
    for item_id, amount in recipe["ingredients"].items():
        have = owned.get(item_id, 0)
        mark = "✅" if have >= amount else "❌"
        lines.append(
            f"{mark} {ingredient_emoji(item_id)} {ingredient_name(item_id)} ×{amount} "
            f"*(you have {have})*"
        )
    lines.append(f"\n**Produces:** {recipe['emoji']} {recipe['name']} ×1")
    return "\n".join(lines)


class WorkshopSelect(discord.ui.Select):
    def __init__(self, cog, owner_id):
        self.cog = cog
        self.owner_id = owner_id
        options = [
            discord.SelectOption(
                label=r["name"], value=rid, emoji=r["emoji"],
                description="Assemble this device",
            )
            for rid, r in WORKSHOP_RECIPES.items()
        ]
        super().__init__(placeholder="Choose something to assemble...", options=options)

    async def callback(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ This workshop belongs to someone else.", ephemeral=True)
            return
        if not halloween_is_active():
            await interaction.response.send_message("🎃 The Haunted Workshop is dormant outside Halloween.", ephemeral=True)
            return
        await self.cog.assemble(interaction, self.values[0])


class WorkshopView(discord.ui.View):
    def __init__(self, cog, owner_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.owner_id = owner_id
        self.add_item(WorkshopSelect(cog, owner_id))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ This workshop belongs to someone else.",
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
                "🎃 The Haunted Workshop is dormant outside Halloween.",
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


class Workshop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _owned(self, db, user_id):
        async with db.execute(
            "SELECT item_id, quantity FROM inventory WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            return {row[0]: row[1] for row in await cursor.fetchall()}

    async def show_menu(self, interaction):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            owned = await self._owned(db, interaction.user.id)
        embed = discord.Embed(
            title="🔧 Haunted Workshop",
            description=(
                "Bolts, wires, dead electronics, and things that definitely should not be plugged in.\n\n"
                "Choose something to assemble below."
            ),
            color=discord.Color.dark_purple(),
        )
        embed.add_field(
            name="📖 Available Blueprints",
            value="\n".join(
                f"{r['emoji']} **{r['name']}**"
                for r in WORKSHOP_RECIPES.values()
            ),
            inline=False,
        )
        await interaction.response.edit_message(
            embed=embed,
            view=WorkshopView(self, interaction.user.id),
        )

    async def assemble(self, interaction, recipe_id):
        recipe = WORKSHOP_RECIPES[recipe_id]
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await db.execute("BEGIN IMMEDIATE")
            owned = await self._owned(db, interaction.user.id)
            missing = [
                f"{ingredient_emoji(i)} {ingredient_name(i)} ×{a-owned.get(i,0)}"
                for i,a in recipe["ingredients"].items()
                if owned.get(i,0) < a
            ]
            if missing:
                await db.rollback()
                await interaction.response.send_message(
                    "❌ **Missing parts:**\n" + "\n".join(missing),
                    ephemeral=True,
                )
                return

            for item_id, amount in recipe["ingredients"].items():
                await db.execute(
                    "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?",
                    (amount, interaction.user.id, item_id),
                )

            added, _, _ = await add_inventory_item(
                db, interaction.user.id, recipe["result"], recipe["result_type"], 1
            )
            if added < 1:
                for item_id, amount in recipe["ingredients"].items():
                    await db.execute(
                        "UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_id = ?",
                        (amount, interaction.user.id, item_id),
                    )
                await db.commit()
                await interaction.response.send_message(
                    f"❌ Your **{recipe['name']}** inventory is full. Your parts were returned.",
                    ephemeral=True,
                )
                return

            await db.commit()

        achievements_cog = self.bot.get_cog("Achievements")
        if achievements_cog:
            await achievements_cog.add_haunted_crafting_progress(interaction.user.id, "workshop")

        await interaction.response.send_message(
            f"🔧 **Assembly complete!** You built **{recipe['emoji']} {recipe['name']} ×1**.",
            ephemeral=True,
        )

    @commands.hybrid_command(name="workshop", description="Open the Halloween Haunted Workshop.")
    async def workshop(self, ctx):
        if not is_halloween_channel(ctx.channel):
            await ctx.send(halloween_channel_message())
            return
        if not halloween_is_active():
            await ctx.send("🎃 The Haunted Workshop is dormant right now.")
            return
        await ctx.defer()
        embed = discord.Embed(
            title="🔧 Haunted Workshop",
            description="A workbench covered in scavenged parts. Something here has definitely been assembled before.",
            color=discord.Color.dark_purple(),
        )
        await ctx.send(
            embed=embed,
            view=WorkshopView(self, ctx.author.id),
        )


async def setup(bot):
    await bot.add_cog(Workshop(bot))
