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
        "description": "A battered radio that tunes into impossible transmissions. **Guarantees a signal encounter on your next Haunted run.**",
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
        "description": "A crude motion detector that makes Halloween collectibles **15 percentage points more likely to be found** on your next Haunted run.",
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
        "description": "A rebuilt hotel key that **shortens your next Endless Hotel run by 1 stage**.",
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
        "description": "A patched-together lantern that **halves supernatural Sanity loss** on your next Fogbound Town run.",
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
        "description": "A device that sharpens spectral signals, making Halloween collectibles **10 percentage points more likely to be found** on your next Haunted run.",
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
        "description": "A salvaged monitor that **absorbs up to 5 points of Sanity loss from one hit** during your next Haunted run.",
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
        "description": "A jury-rigged fluorescent beacon that **halves supernatural Sanity loss** during your next Yellow Halls run.",
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
        "description": "A bundle of salvaged parts that **forces a signal encounter** during your next Dead-End Highway run.",
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
        "description": "A sealed light built from drowned station hardware that **halves supernatural Sanity loss** during your next Drowned Station run.",
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
        "description": "A crude signal filter that **halves supernatural Sanity loss** during your next Silent Campground run.",
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


WORKSHOP_FLAVOR_TEXT = {
    "ghost_radio": [
        "You reconnect the wiring and give the radio a cautious tap. Static floods the speaker, followed by a voice that definitely wasn't there before.",
        "The radio crackles to life. Between bursts of static, someone quietly says your name.",
    ],
    "mascot_tracker": [
        "The tracker chirps once. Its display immediately points toward something moving where nothing should be.",
        "You tighten the last screw. The tracker locks onto a signal that keeps changing locations without moving.",
    ],
    "room_314_key": [
        "The rebuilt key clicks into place. Somewhere nearby, an elevator arrives at a floor that doesn't exist.",
        "The key turns smoothly. You hear a distant hotel door unlock, despite being nowhere near a hotel.",
    ],
    "fog_lantern": [
        "The lantern flickers on, cutting a clean hole through the fog. Something retreats just beyond its light.",
        "The repaired lantern burns with a pale glow. The surrounding mist seems reluctant to come any closer.",
    ],
    "spectral_receiver": [
        "The receiver hums as the final connection is made. A second voice appears beneath the static, speaking in reverse.",
        "The dial spins on its own before settling on a frequency that shouldn't exist.",
    ],
    "security_monitor": [
        "The monitor sputters to life. Its camera feed shows this room from an angle where no camera exists.",
        "The screen clears. For a second, the hallway feed shows someone standing behind you. When you turn around, nobody is there.",
    ],
    "yellow_halls_beacon": [
        "The fluorescent tube flickers twice before staying on. The endless yellow walls suddenly feel a little farther away.",
        "The beacon hums to life. Somewhere beyond the walls, something answers with another fluorescent buzz.",
    ],
    "highway_payphone_kit": [
        "The repaired parts fit together. The dead payphone rings immediately. You wisely let it ring.",
        "The payphone gives a burst of static before displaying a number that isn't on any map.",
    ],
    "drowned_flood_lamp": [
        "The lamp sputters through a final spark and shines through the gloom. Water drips from it, though the casing is sealed.",
        "The flood lamp comes alive with a cold beam. Somewhere in the darkness, something splashes away.",
    ],
    "campground_static_filter": [
        "The filter hums steadily as the static fades. For a moment, the silence sounds much worse.",
        "You finish the final connection. The radio clears just enough for a distant voice to whisper, 'Don't listen.'",
    ],
}

def ingredient_name(item_id):
    return ITEM_REGISTRY.get(item_id, {}).get("name", item_id.replace("_", " ").title())


def ingredient_emoji(item_id):
    return ITEM_REGISTRY.get(item_id, {}).get("emoji", "🔧")


def format_recipe(recipe, owned):
    lines = [f"{recipe['emoji']} **{recipe['name']}**", "**Parts:**"]
    for item_id, amount in recipe["ingredients"].items():
        have = owned.get(item_id, 0)
        mark = "✅" if have >= amount else "❌"
        lines.append(
            f"{mark} {ingredient_emoji(item_id)} {ingredient_name(item_id)} ×{amount} "
            f"*(you have {have})*"
        )
    lines.extend([
        f"\n**Produces:** {recipe['emoji']} {recipe['name']} ×1",
        f"🔧 **What it does:** {recipe['description']}",
    ])
    return "\n".join(lines)


class WorkshopSelect(discord.ui.Select):
    def __init__(self, cog, owner_id, quantity: int = 1):
        self.cog = cog
        self.owner_id = owner_id
        self.quantity = max(1, min(10, int(quantity)))
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
        await self.cog.assemble(interaction, self.values[0], self.quantity)


class WorkshopRecipeBookView(discord.ui.View):
    def __init__(self, cog, owner_id, pages, page=0):
        super().__init__(timeout=300)
        self.cog = cog
        self.owner_id = owner_id
        self.pages = pages
        self.page = page
        self._update_buttons()

    def _update_buttons(self):
        self.previous_button.disabled = self.page <= 0
        self.next_button.disabled = self.page >= len(self.pages) - 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ This recipe book belongs to someone else.", ephemeral=True)
            return False
        if not is_halloween_channel(interaction.channel):
            await interaction.response.send_message(halloween_channel_message(), ephemeral=True)
            return False
        if not halloween_is_active():
            await interaction.response.send_message("🎃 The Haunted Workshop is dormant outside Halloween.", ephemeral=True)
            return False
        return True

    async def _show(self, interaction):
        embed = discord.Embed(
            title="📖 Workshop Recipe Book",
            description=self.pages[self.page],
            color=discord.Color.dark_purple(),
        )
        embed.set_footer(text=f"Page {self.page + 1}/{len(self.pages)} • Halloween Seasonal System")
        self._update_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        await self._show(interaction)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        await self._show(interaction)

    @discord.ui.button(label="Back", emoji="🔧", style=discord.ButtonStyle.primary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.show_menu(interaction)


class WorkshopView(discord.ui.View):
    def __init__(self, cog, owner_id, quantity: int = 1):
        super().__init__(timeout=300)
        self.cog = cog
        self.owner_id = owner_id
        self.quantity = max(1, min(10, int(quantity)))
        self.add_item(WorkshopSelect(cog, owner_id, self.quantity))

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
        label="Recipes",
        emoji="📖",
        style=discord.ButtonStyle.primary,
    )
    async def recipes_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.cog.show_recipe_book(interaction)

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

    async def show_menu(self, interaction, quantity: int = 1):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            owned = await self._owned(db, interaction.user.id)
        embed = discord.Embed(
            title="🔧 Haunted Workshop",
            description=(
                "Bolts, wires, dead electronics, and things that definitely should not be plugged in.\n"
                "*Something in the static clicks when you get close.*\n\n"
                f"Choose something to assemble below. Batch size: **×{craftable}**."
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
            view=WorkshopView(self, interaction.user.id, quantity),
        )

    async def show_recipe_book(self, interaction):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            owned = await self._owned(db, interaction.user.id)

        recipes = [format_recipe(recipe, owned) for recipe in WORKSHOP_RECIPES.values()]
        pages = ["\n\n──────────────\n\n".join(recipes[i:i + 3]) for i in range(0, len(recipes), 3)]

        embed = discord.Embed(
            title="📖 Workshop Recipe Book",
            description=pages[0],
            color=discord.Color.dark_purple(),
        )
        embed.set_footer(text=f"Page 1/{len(pages)} • Halloween Seasonal System")
        await interaction.response.edit_message(
            embed=embed,
            view=WorkshopRecipeBookView(self, interaction.user.id, pages),
        )


    async def assemble(self, interaction, recipe_id, quantity: int = 1):
        recipe = WORKSHOP_RECIPES[recipe_id]
        quantity = max(1, min(10, int(quantity)))
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await db.execute("BEGIN IMMEDIATE")
            owned = await self._owned(db, interaction.user.id)

            missing = [
                f"{ingredient_emoji(i)} {ingredient_name(i)} ×{a * quantity - owned.get(i, 0)}"
                for i, a in recipe["ingredients"].items()
                if owned.get(i, 0) < a * quantity
            ]
            craftable = quantity
            for item_id, amount in recipe["ingredients"].items():
                craftable = min(craftable, owned.get(item_id, 0) // amount)

            result_info = ITEM_REGISTRY.get(recipe["result"], {})
            result_max = int(result_info.get("max_quantity", 10))
            current_result = owned.get(recipe["result"], 0)
            craftable = min(craftable, max(0, result_max - current_result))

            if craftable < 1:
                await db.rollback()
                if current_result >= result_max:
                    message = f"❌ Your **{recipe['name']}** inventory is full. You currently have **{current_result}/{result_max}**."
                else:
                    message = "❌ **Missing parts:**\n" + "\n".join(missing)
                await interaction.response.send_message(message, ephemeral=True)
                return

            for item_id, amount in recipe["ingredients"].items():
                await db.execute(
                    "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?",
                    (amount * craftable, interaction.user.id, item_id),
                )

            added, _, _ = await add_inventory_item(
                db, interaction.user.id, recipe["result"], recipe["result_type"], craftable
            )
            if added < craftable:
                refund = craftable - added
                for item_id, amount in recipe["ingredients"].items():
                    await db.execute(
                        "UPDATE inventory SET quantity = quantity + ? WHERE user_id = ? AND item_id = ?",
                        (amount * refund, interaction.user.id, item_id),
                    )
                craftable = added

            await db.commit()

        if craftable < 1:
            await interaction.response.send_message(
                f"❌ Your **{recipe['name']}** inventory is full. Your parts were returned.",
                ephemeral=True,
            )
            return

        achievements_cog = self.bot.get_cog("Achievements")
        if achievements_cog:
            for _ in range(craftable):
                await achievements_cog.add_haunted_crafting_progress(interaction.user.id, "workshop")

        import random
        flavor = random.choice(WORKSHOP_FLAVOR_TEXT.get(recipe_id, ["The finished device gives an unsettling little hum as it comes to life."]))
        await interaction.response.send_message(
            f"*{flavor}*\n\n"
            f"🔧 **Assembly complete!** You built **{recipe['emoji']} {recipe['name']} ×{craftable}**."
            + (f"\n\nYou requested **×{quantity}**, but only had enough materials for **×{craftable}**." if craftable < quantity else ""),
            ephemeral=True,
        )

