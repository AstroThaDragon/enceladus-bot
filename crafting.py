import aiosqlite
import discord
from discord.ext import commands

from emojis import EMOJIS
from database import ECONOMY_DB_NAME
from upgrades import UPGRADE_DATA

MATERIAL_NAMES = {
    "iron_ore": (EMOJIS.get("iron_ore", "⛏️"), "Iron Ore"),
    "copper_ore": (EMOJIS.get("copper_ore", "🟠"), "Copper Ore"),
    "titanium_chunk": (EMOJIS.get("titanium_chunk", "⛏️"), "Titanium Ore Chunk"),
    "aluminum_ore": (EMOJIS.get("aluminum_ore", "⬜"), "Aluminum Ore"),
    "scrap_metal": (EMOJIS.get("scrap_metal", "🔩"), "Scrap Metal"),
    "nuts_bolts": (EMOJIS.get("nuts_bolts", "🔧"), "Nuts & Bolts"),
    "wiring": (EMOJIS.get("wiring", "🧵"), "Wiring"),
    "circuit_board": (EMOJIS.get("circuit_board", "🟩"), "Circuit Board"),
    "glue": (EMOJIS.get("glue", "🧴"), "Industrial Glue"),
    "gauze": (EMOJIS.get("gauze", "🧻"), "Sterile Gauze"),
    "medical_alcohol": (EMOJIS.get("alcohol", "🧴"), "Medical Alcohol"),
    "bandaids": (EMOJIS.get("bandaid", "🩹"), "Bandaids"),
    "antiseptic_ointment": (EMOJIS.get("ointment", "🧪"), "Antiseptic Ointment"),
    "halloween_candy": (EMOJIS.get("halloween_candy", "🍬"), "Halloween Candy"),
    "halloween_plastic": ("🧴", "Halloween Themed Plastic"),
    "astral_core": ("🌌", "Astral Core"),
    "nanite_retrofit_kit": (EMOJIS.get("nanite_retrofit", "🧬"), "Nanite Retrofit Kit"),
    "salvage_rig_kit": (EMOJIS.get("salvage_rig_kit", "♻️"), "Salvage Rig Kit"),
}

RECIPES = {
    "laser_parts_1": {"name": "Reinforced Laser Parts", "emoji": EMOJIS.get("reinforced_laser_parts", "🛠️"), "result": "reinforced_laser_parts_1", "ingredients": {"iron_ore": 5, "copper_ore": 3, "scrap_metal": 3, "wiring": 3}},
    "laser_parts_2": {"name": "Reinforced Laser Parts II", "emoji": EMOJIS.get("reinforced_laser_parts", "🛠️"), "result": "reinforced_laser_parts_2", "ingredients": {"iron_ore": 10, "copper_ore": 6, "titanium_chunk": 3, "aluminum_ore": 3, "circuit_board": 3, "wiring": 5}},
    "laser_parts_3": {"name": "Reinforced Laser Parts III", "emoji": EMOJIS.get("reinforced_laser_parts", "🛠️"), "result": "reinforced_laser_parts_3", "ingredients": {"iron_ore": 15, "copper_ore": 9, "titanium_chunk": 5, "aluminum_ore": 5, "circuit_board": 6, "wiring": 8}},
    "laser_parts_4": {"name": "Reinforced Laser Parts IV", "emoji": EMOJIS.get("reinforced_laser_parts", "🛠️"), "result": "reinforced_laser_parts_4", "ingredients": {"iron_ore": 20, "copper_ore": 12, "titanium_chunk": 8, "aluminum_ore": 8, "circuit_board": 10, "wiring": 12, "nuts_bolts": 7}},
    "laser_parts_5": {"name": "Reinforced Laser Parts V", "emoji": EMOJIS.get("reinforced_laser_parts", "🛠️"), "result": "reinforced_laser_parts_5", "ingredients": {"iron_ore": 30, "copper_ore": 18, "titanium_chunk": 12, "aluminum_ore": 12, "circuit_board": 15, "wiring": 18, "astral_core": 1}},

    
    "drone_kit_1": {"name": "Drone Upgrade Kit", "emoji": EMOJIS.get("drone_upgrade_kit", "🛸"), "result": "drone_upgrade_kit_1", "ingredients": {"scrap_metal": 5, "nuts_bolts": 5, "wiring": 3, "glue": 2}},
    "drone_kit_2": {"name": "Drone Upgrade Kit II", "emoji": EMOJIS.get("drone_upgrade_kit", "🛸"), "result": "drone_upgrade_kit_2", "ingredients": {"scrap_metal": 10, "nuts_bolts": 8, "wiring": 6, "aluminum_ore": 3, "circuit_board": 3, "glue": 4}},
    "drone_kit_3": {"name": "Drone Upgrade Kit III", "emoji": EMOJIS.get("drone_upgrade_kit", "🛸"), "result": "drone_upgrade_kit_3", "ingredients": {"scrap_metal": 15, "nuts_bolts": 12, "wiring": 9, "aluminum_ore": 5, "circuit_board": 6, "copper_ore": 4, "glue": 6}},
    "drone_kit_4": {"name": "Drone Upgrade Kit IV", "emoji": EMOJIS.get("drone_upgrade_kit", "🛸"), "result": "drone_upgrade_kit_4", "ingredients": {"scrap_metal": 20, "nuts_bolts": 18, "wiring": 12, "aluminum_ore": 8, "circuit_board": 10, "titanium_chunk": 6, "glue": 9}},
    "drone_kit_5": {"name": "Drone Upgrade Kit V", "emoji": EMOJIS.get("drone_upgrade_kit", "🛸"), "result": "drone_upgrade_kit_5", "ingredients": {"scrap_metal": 30, "nuts_bolts": 25, "wiring": 18, "aluminum_ore": 12, "circuit_board": 15, "titanium_chunk": 10, "glue": 14, "astral_core": 1}},


    "nanite_retrofit_kit": {"name": "Nanite Retrofit Kit", "emoji": EMOJIS.get("nanite_retrofit", "🧬"), "result": "nanite_retrofit_kit", "ingredients": {"scrap_metal": 15, "wiring": 10, "circuit_board": 6, "glue": 4, "titanium_chunk": 3}},
    "astral_power_core": {"name": "Astral Power Core", "emoji": EMOJIS.get("astral_power_core", "🌌"), "result": "astral_power_core", "ingredients": {"astral_core": 1, "titanium_chunk": 5, "copper_ore": 4, "circuit_board": 5, "wiring": 6}},

    
    "salvage_rig_kit_1": {"name": "Salvage Rig Kit", "emoji": EMOJIS.get("salvage_rig_kit", "♻️"), "result": "salvage_rig_kit_1", "ingredients": {"scrap_metal": 5, "nuts_bolts": 3, "wiring": 2}},
    "salvage_rig_kit_2": {"name": "Salvage Rig Kit II", "emoji": EMOJIS.get("salvage_rig_kit", "♻️"), "result": "salvage_rig_kit_2", "ingredients": {"scrap_metal": 10, "nuts_bolts": 6, "wiring": 4, "iron_ore": 3}},
    "salvage_rig_kit_3": {"name": "Salvage Rig Kit III", "emoji": EMOJIS.get("salvage_rig_kit", "♻️"), "result": "salvage_rig_kit_3", "ingredients": {"scrap_metal": 15, "nuts_bolts": 9, "wiring": 6, "circuit_board": 4, "aluminum_ore": 3}},
    "salvage_rig_kit_4": {"name": "Salvage Rig Kit IV", "emoji": EMOJIS.get("salvage_rig_kit", "♻️"), "result": "salvage_rig_kit_4", "ingredients": {"scrap_metal": 22, "nuts_bolts": 13, "wiring": 9, "circuit_board": 8, "aluminum_ore": 6, "copper_ore": 4}},
    "salvage_rig_kit_5": {"name": "Salvage Rig Kit V", "emoji": EMOJIS.get("salvage_rig_kit", "♻️"), "result": "salvage_rig_kit_5", "ingredients": {"scrap_metal": 30, "nuts_bolts": 18, "wiring": 14, "circuit_board": 12, "aluminum_ore": 10, "titanium_chunk": 5, "astral_core": 1}},

    
    "makeshift_medkit": {"name": "Makeshift Medkit", "emoji": EMOJIS.get("makeshift_medkit", "🩹"), "result": "makeshift_medkit", "ingredients": {"bandaids": 3, "gauze": 2, "medical_alcohol": 1, "antiseptic_ointment": 1}},
    "trick_or_treat_bag": {"name": "Trick-or-Treat Bag", "emoji": EMOJIS.get("trick_or_treat_bag", "🎃"), "result": "trick_or_treat_bag", "ingredients": {"halloween_candy": 25, "halloween_plastic": 10}},
}

# Discord command choice labels do not render custom emoji markup reliably.
# Use normal Unicode emoji in the dropdown while keeping the custom emoji markup
# for places where Discord can render it (such as regular messages/embeds).
# Tiered upgrade components must be crafted and applied in order.
# A player cannot craft tier N until tier N-1 has actually been installed.
TIERED_RECIPE_PROGRESSIONS = {
    "reinforced_laser_parts_": "mining",
    "drone_upgrade_kit_": "scavenging",
    "salvage_rig_kit_": "salvage",
}


def get_tiered_recipe_progression(recipe):
    """Return (system, tier) for a tiered upgrade recipe, or (None, None)."""
    result = recipe.get("result", "")

    for prefix, system in TIERED_RECIPE_PROGRESSIONS.items():
        if result.startswith(prefix):
            suffix = result[len(prefix):]
            if suffix.isdigit():
                return system, int(suffix)

    return None, None


RECIPE_EMOJI_FALLBACKS = {
    "reinforced_laser_parts": "🛠️",
    "drone_upgrade_kit": "🛸",
    "nanite_retrofit_kit": "🧬",
    "astral_power_core": "🌌",
    "salvage_rig_kit": "♻️",
    "makeshift_medkit": "🩹",
    "trick_or_treat_bag": "🎃",
}

MATERIAL_EMOJI_FALLBACKS = {
    "iron_ore": "⛏️",
    "copper_ore": "🟠",
    "titanium_chunk": "⛏️",
    "aluminum_ore": "⬜",
    "scrap_metal": "🔩",
    "nuts_bolts": "🔧",
    "wiring": "🧵",
    "circuit_board": "🟩",
    "glue": "🧴",
    "gauze": "🧻",
    "medical_alcohol": "🧴",
    "bandaids": "🩹",
    "antiseptic_ointment": "🧪",
    "halloween_candy": "🍬",
    "halloween_plastic": "🧴",
    "astral_core": "🌌",
    "reinforced_laser_parts": "🛠️",
    "drone_upgrade_kit": "🛸",
    "nanite_retrofit_kit": "🧬",
    "astral_power_core": "🌌",
    "salvage_rig_kit": "♻️",
}


def recipe_display_emoji(recipe):
    result = recipe["result"]
    if result.startswith("reinforced_laser_parts_"):
        return RECIPE_EMOJI_FALLBACKS["reinforced_laser_parts"]
    if result.startswith("drone_upgrade_kit_"):
        return RECIPE_EMOJI_FALLBACKS["drone_upgrade_kit"]
    if result.startswith("salvage_rig_kit_"):
        return RECIPE_EMOJI_FALLBACKS["salvage_rig_kit"]
    return RECIPE_EMOJI_FALLBACKS.get(result, "🔨")




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
        async with db.execute(
            "SELECT item_id, quantity FROM inventory WHERE user_id = ?", (user_id,)
        ) as cursor:
            return {item_id: quantity for item_id, quantity in await cursor.fetchall()}

    def recipe_embed(self, recipe, owned):
        lines = [f"{recipe['emoji']} **{recipe['name']}**", "", "**Materials Required:**"]
        for item_id, amount in recipe["ingredients"].items():
            icon, name = MATERIAL_NAMES[item_id]
            have = owned.get(item_id, 0)
            mark = "✅" if have >= amount else "❌"
            lines.append(f"{mark} {icon} {name} ×{amount}  *(you have {have})*")
        destination = (
            "Use `/heal` to restore HP."
            if recipe["result"] in {"makeshift_medkit", "trick_or_treat_bag"}
            else "These crafted parts are used by `/upgrade`."
        )
        lines += ["", f"🔨 **Produces:** {recipe['emoji']} {recipe['name']} ×1", "", destination]
        return discord.Embed(
            title="🔨 Crafting",
            description="\n".join(lines),
            color=discord.Color.from_rgb(0, 229, 255),
        )

    def recipe_book_embeds(self, owned):
        items = list(RECIPES.items())
        page_size = 3
        pages = []

        for start in range(0, len(items), page_size):
            chunk = items[start:start + page_size]
            sections = []
            for _recipe_id, recipe in chunk:
                lines = [f"{recipe_display_emoji(recipe)} **{recipe['name']}**"]
                for item_id, amount in recipe["ingredients"].items():
                    material_emoji, name = MATERIAL_NAMES[item_id]
                    have = owned.get(item_id, 0)
                    mark = "✅" if have >= amount else "❌"
                    lines.append(f"{mark} {material_emoji} {name} ×{amount} *(you have {have})*")
                sections.append("\n".join(lines))

            embed = discord.Embed(
                title="📖 Crafting Recipe Book",
                description="\n\n".join(sections),
                color=discord.Color.from_rgb(0, 229, 255),
            )
            pages.append(embed)

        return pages

    async def _send(self, target, *args, **kwargs):
        if isinstance(target, discord.Interaction):
            return await target.followup.send(*args, **kwargs)
        return await target.send(*args, **kwargs)

    async def perform_craft(self, ctx, recipe_id, quantity):
        data = RECIPES.get(recipe_id)
        if not data:
            return await self._send(ctx, "❌ That recipe does not exist.")

        if quantity < 1 or quantity > 10:
            return await self._send(ctx, "❌ Crafting quantity must be between **1 and 10**.")

        progression_system, progression_tier = get_tiered_recipe_progression(data)
        is_upgrade_component = (
            progression_system is not None
            or data["result"] in {"nanite_retrofit_kit", "astral_power_core"}
        )

        if is_upgrade_component and quantity != 1:
            return await self._send(ctx, 
                f"❌ **{data['name']}** can only be crafted **×1 at a time**."
            )

        if progression_system and isinstance(progression_tier, int) and progression_tier > 1:
            async with aiosqlite.connect(ECONOMY_DB_NAME) as progress_db:
                column = UPGRADE_DATA[progression_system]["column"]
                async with progress_db.execute(
                    f"SELECT COALESCE({column}, 0) FROM users WHERE user_id = ?",
                    (ctx.author.id,),
                ) as cursor:
                    row = await cursor.fetchone()

            current_level = row[0] if row else 0
            required_level = progression_tier - 1

            if current_level < required_level:
                info = UPGRADE_DATA[progression_system]
                prefix = next(
                    prefix
                    for prefix in TIERED_RECIPE_PROGRESSIONS
                    if data["result"].startswith(prefix)
                )
                previous_display = {
                    "reinforced_laser_parts_": "Reinforced Laser Parts",
                    "drone_upgrade_kit_": "Drone Upgrade Kit",
                    "salvage_rig_kit_": "Salvage Rig Kit",
                }[prefix]
                previous_display = f"{previous_display} {required_level}"

                return await self._send(ctx, 
                    f"{ctx.author.mention} 🚫 **Upgrade progression locked!**\n\n"
                    f"You must **craft and use {previous_display}** before you can "
                    f"craft **{data['name']}**.\n\n"
                    f"Current **{info['name']}** level: **{current_level}/5**\n"
                    f"Required level: **{required_level}/5**"
                )

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_inventory(db)
            await db.execute("BEGIN IMMEDIATE")
            owned = await self.owned(db, ctx.author.id)

            craftable = quantity
            for item_id, amount in data["ingredients"].items():
                craftable = min(craftable, owned.get(item_id, 0) // amount)

            if craftable < 1:
                missing = []
                for item_id, amount in data["ingredients"].items():
                    required = amount * quantity
                    have = owned.get(item_id, 0)
                    if have < required:
                        icon, name = MATERIAL_NAMES[item_id]
                        missing.append(f"{icon} {name} ×{required - have}")
                await db.rollback()
                return await self._send(ctx, 
                    f"{ctx.author.mention} ❌ You're missing:\n" + "\n".join(missing)
                )

            for item_id, amount in data["ingredients"].items():
                await db.execute(
                    "UPDATE inventory SET quantity = quantity - ? WHERE user_id = ? AND item_id = ?",
                    (amount * craftable, ctx.author.id, item_id),
                )

            await db.execute(
                "INSERT INTO inventory (user_id, item_id, item_type, quantity) VALUES (?, ?, 'upgrade_component', ?) "
                "ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + ?",
                (ctx.author.id, data["result"], craftable, craftable),
            )
            await db.commit()

        embed = discord.Embed(
            title="🔨 Crafting Complete!",
            description=(
                f"{ctx.author.mention}\n\nYou crafted **{data['emoji']} {data['name']} ×{craftable}**!"
                + (
                    f"\n\nYou requested **×{quantity}**, but only had enough materials for **×{craftable}**."
                    if craftable < quantity else ""
                )
                + "\n\n"
                + (
                    "Use `/heal` when you want to chow down on your Halloween treats!"
                    if data["result"] == "trick_or_treat_bag"
                    else "Use `/heal` to patch yourself up when needed."
                    if data["result"] == "makeshift_medkit"
                    else "Use `/upgrade` when you have the Stardust and remaining materials needed for the next upgrade."
                )
            ),
            color=discord.Color.from_rgb(0, 229, 255),
        )
        await self._send(ctx, embed=embed)

    async def show_crafting_menu(self, target, owner_id):
        view = CraftingView(self, owner_id)
        embed = discord.Embed(
            title="🔨 Crafting",
            description=(
                "Craft components, upgrade kits, and field supplies from collected materials.\n\n"
                "**Known Recipes**\n"
                f"{len(RECIPES)} recipes available.\n\n"
                "Choose an option below."
            ),
            color=discord.Color.from_rgb(0, 229, 255),
        )
        if hasattr(target, "response"):
            await target.response.edit_message(embed=embed, view=view)
        else:
            await target.send(embed=embed, view=view)

    @commands.hybrid_command(name="craft", description="Open the crafting station.")
    async def craft(self, ctx):
        await ctx.defer()
        await self.show_crafting_menu(ctx, ctx.author.id)


class CraftingView(discord.ui.View):
    def __init__(self, cog, owner_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.owner_id = owner_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ This crafting menu belongs to someone else.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="📖 Recipes", style=discord.ButtonStyle.primary)
    async def recipes_button(self, interaction, button):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.cog.ensure_inventory(db)
            owned = await self.cog.owned(db, self.owner_id)
        pages = self.cog.recipe_book_embeds(owned)
        view = CraftingRecipeBookView(self.cog, self.owner_id, pages)
        await interaction.response.edit_message(embed=pages[0], view=view)

    @discord.ui.button(label="🔨 Craft", style=discord.ButtonStyle.success)
    async def craft_button(self, interaction, button):
        view = CraftingSelectView(self.cog, self.owner_id)
        embed = discord.Embed(
            title="🔨 Craft",
            description="Choose a recipe to craft.",
            color=discord.Color.from_rgb(0, 229, 255),
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🎒 Materials", style=discord.ButtonStyle.secondary)
    async def materials_button(self, interaction, button):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.cog.ensure_inventory(db)
            owned = await self.cog.owned(db, self.owner_id)

        lines = []
        for item_id, (_emoji, name) in MATERIAL_NAMES.items():
            amount = owned.get(item_id, 0)
            if amount > 0:
                icon, _ = MATERIAL_NAMES[item_id]
                lines.append(f"{icon} **{name}** ×{amount}")

        description = "\n".join(lines) if lines else "You don't have any crafting materials yet."
        embed = discord.Embed(
            title="🎒 Crafting Materials",
            description=description,
            color=discord.Color.from_rgb(0, 229, 255),
        )
        await interaction.response.edit_message(embed=embed, view=CraftingMaterialsView(self.cog, self.owner_id))


class CraftingMaterialsView(discord.ui.View):
    def __init__(self, cog, owner_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.owner_id = owner_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ This crafting menu belongs to someone else.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="◀ Back", style=discord.ButtonStyle.secondary)
    async def back(self, interaction, button):
        await self.cog.show_crafting_menu(interaction, self.owner_id)


class CraftingRecipeBookView(discord.ui.View):
    def __init__(self, cog, owner_id, embeds):
        super().__init__(timeout=300)
        self.cog = cog
        self.owner_id = owner_id
        self.embeds = embeds
        self.current_page = 0

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ This crafting menu belongs to someone else.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction, button):
        self.current_page = (self.current_page - 1) % len(self.embeds)
        await interaction.response.edit_message(
            embed=self.embeds[self.current_page], view=self
        )

    @discord.ui.button(label="🔨 Craft", style=discord.ButtonStyle.success)
    async def craft(self, interaction, button):
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🔨 Craft",
                description="Choose a recipe to craft.",
                color=discord.Color.from_rgb(0, 229, 255),
            ),
            view=CraftingSelectView(self.cog, self.owner_id),
        )

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction, button):
        self.current_page = (self.current_page + 1) % len(self.embeds)
        await interaction.response.edit_message(
            embed=self.embeds[self.current_page], view=self
        )

    @discord.ui.button(label="◀ Back", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction, button):
        await self.cog.show_crafting_menu(interaction, self.owner_id)


class CraftingSelect(discord.ui.Select):
    def __init__(self, cog, owner_id):
        self.cog = cog
        self.owner_id = owner_id
        options = [
            discord.SelectOption(
                label=recipe["name"][:100],
                value=recipe_id,
                emoji=recipe_display_emoji(recipe),
            )
            for recipe_id, recipe in RECIPES.items()
        ]
        super().__init__(
            placeholder="Select a recipe...",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction):
        recipe_id = self.values[0]
        recipe = RECIPES[recipe_id]

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.cog.ensure_inventory(db)
            owned = await self.cog.owned(db, self.owner_id)

        embed = self.cog.recipe_embed(recipe, owned)
        is_upgrade_component = (
            get_tiered_recipe_progression(recipe)[0] is not None
            or recipe["result"] in {"nanite_retrofit_kit", "astral_power_core"}
        )
        view = CraftingRecipeActionView(
            self.cog, self.owner_id, recipe_id, is_upgrade_component
        )
        await interaction.response.edit_message(embed=embed, view=view)


class CraftingSelectView(discord.ui.View):
    def __init__(self, cog, owner_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.owner_id = owner_id
        self.add_item(CraftingSelect(cog, owner_id))

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ This crafting menu belongs to someone else.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="◀ Back", style=discord.ButtonStyle.secondary)
    async def back(self, interaction, button):
        await self.cog.show_crafting_menu(interaction, self.owner_id)


class CraftingRecipeActionView(discord.ui.View):
    def __init__(self, cog, owner_id, recipe_id, single_craft):
        super().__init__(timeout=300)
        self.cog = cog
        self.owner_id = owner_id
        self.recipe_id = recipe_id
        self.single_craft = single_craft

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ This crafting menu belongs to someone else.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="🔨 Craft", style=discord.ButtonStyle.success)
    async def craft(self, interaction, button):
        if self.single_craft:
            quantity = 1
            await interaction.response.defer()
            await self.cog.perform_craft(interaction, self.recipe_id, quantity)
            return

        modal = CraftQuantityModal(self.cog, self.recipe_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📖 Recipes", style=discord.ButtonStyle.primary)
    async def recipes(self, interaction, button):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.cog.ensure_inventory(db)
            owned = await self.cog.owned(db, self.owner_id)
        pages = self.cog.recipe_book_embeds(owned)
        await interaction.response.edit_message(
            embed=pages[0],
            view=CraftingRecipeBookView(self.cog, self.owner_id, pages),
        )

    @discord.ui.button(label="◀ Back", style=discord.ButtonStyle.secondary)
    async def back(self, interaction, button):
        view = CraftingSelectView(self.cog, self.owner_id)
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🔨 Craft",
                description="Choose a recipe to craft.",
                color=discord.Color.from_rgb(0, 229, 255),
            ),
            view=view,
        )


class CraftQuantityModal(discord.ui.Modal, title="Craft Quantity"):
    quantity = discord.ui.TextInput(
        label="Quantity",
        placeholder="Enter a quantity from 1 to 10",
        min_length=1,
        max_length=2,
        required=True,
    )

    def __init__(self, cog, recipe_id):
        super().__init__()
        self.cog = cog
        self.recipe_id = recipe_id

    async def on_submit(self, interaction):
        try:
            quantity = int(self.quantity.value)
        except ValueError:
            return await interaction.response.send_message(
                "❌ Quantity must be a whole number.", ephemeral=True
            )

        if quantity < 1 or quantity > 10:
            return await interaction.response.send_message(
                "❌ Crafting quantity must be between **1 and 10**.", ephemeral=True
            )

        await interaction.response.defer()
        await self.cog.perform_craft(interaction, self.recipe_id, quantity)


async def setup(bot):
    await bot.add_cog(Crafting(bot))
