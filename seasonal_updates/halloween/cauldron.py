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


# ---------------------------------------------------------------------------
# Haunted Cauldron
# ---------------------------------------------------------------------------
# Seasonal crafting lives here rather than in the normal crafting.py module.
# Add future recipes to CAULDRON_RECIPES without changing the core system.
#
# Recipe structure:
#   name       - display name
#   emoji      - display emoji
#   ingredients- Haunted Ingredient IDs and quantities
#   result     - inventory item ID
#   result_type- inventory item type
#   description- player-facing recipe description
#
# Potion effects are stored as metadata for the Haunted system to consume.
# This keeps cauldron.py responsible for brewing while haunted.py remains
# responsible for actually running encounters.
# ---------------------------------------------------------------------------

CAULDRON_RECIPES = {
    "calming_draught": {
        "name": "Calming Draught",
        "emoji": "🧪",
        "ingredients": {
            "ectoplasm": 2,
            "consecrated_salt": 2,
            "mooncap_mushroom": 1,
        },
        "result": "calming_draught",
        "result_type": "Haunted Potion",
        "description": "A soothing spectral brew that restores Sanity when consumed.",
        "effect": {
            "type": "sanity_restore",
            "amount": 25,
        },
    },
    "warding_incense": {
        "name": "Warding Incense",
        "emoji": "🕯️",
        "ingredients": {
            "black_wax": 2,
            "ritual_chalk": 2,
            "witchroot": 1,
        },
        "result": "warding_incense",
        "result_type": "Haunted Potion",
        "description": "Burn it before a Haunted run to ward off some of the worst things lurking within.",
        "effect": {
            "type": "run_protection",
            "encounter_protection": 1,
        },
    },
    "third_eye_tonic": {
        "name": "Third-Eye Tonic",
        "emoji": "👁️",
        "ingredients": {
            "medical_residue": 1,
            "grave_dust": 2,
            "cursed_fabric": 1,
            "mooncap_mushroom": 1,
        },
        "result": "third_eye_tonic",
        "result_type": "Haunted Potion",
        "description": "A disturbing tonic that sharpens your perception of the supernatural.",
        "effect": {
            "type": "encounter_insight",
            "amount": 1,
        },
    },

    "gravekeepers_elixir": {
        "name": "Gravekeeper's Elixir",
        "emoji": "⚰️",
        "ingredients": {
            "grave_dust": 2,
            "bone_fragment": 1,
            "witchroot": 2,
        },
        "result": "gravekeepers_elixir",
        "result_type": "Haunted Potion",
        "description": "A cold, earthy draught that steadies the nerves of those who walk among the dead.",
        "effect": {
            "type": "sanity_restore",
            "amount": 35,
        },
    },
    "hexbreaker_tonic": {
        "name": "Hexbreaker Tonic",
        "emoji": "🔮",
        "ingredients": {
            "consecrated_salt": 2,
            "black_wax": 1,
            "ritual_chalk": 2,
        },
        "result": "hexbreaker_tonic",
        "result_type": "Haunted Potion",
        "description": "A sharp, bitter tonic infused with protective ritual components.",
        "effect": {
            "type": "curse_protection",
            "amount": 1,
        },
    },
    "phantom_breath": {
        "name": "Phantom's Breath",
        "emoji": "🌫️",
        "ingredients": {
            "ectoplasm": 2,
            "cursed_fabric": 2,
            "glowmoss": 1,
        },
        "result": "phantom_breath",
        "result_type": "Haunted Potion",
        "description": "A ghostly vapor sealed inside a tiny bottle. Its fumes make the unseen easier to notice.",
        "effect": {
            "type": "encounter_insight",
            "amount": 2,
        },
    },
    "witches_remedy": {
        "name": "Witch's Remedy",
        "emoji": "🌿",
        "ingredients": {
            "witchroot": 2,
            "spider_lily": 1,
            "mooncap_mushroom": 2,
        },
        "result": "witches_remedy",
        "result_type": "Haunted Potion",
        "description": "A surprisingly soothing herbal mixture prepared from plants that should probably not be medicinal.",
        "effect": {
            "type": "sanity_restore",
            "amount": 50,
        },
    },
    "bellward_brew": {
        "name": "Bellward Brew",
        "emoji": "🔔",
        "ingredients": {
            "bell_fragment": 1,
            "incense_resin": 2,
            "consecrated_salt": 2,
        },
        "result": "bellward_brew",
        "result_type": "Haunted Potion",
        "description": "A resonant brew said to keep hostile spirits at a cautious distance.",
        "effect": {
            "type": "run_protection",
            "encounter_protection": 2,
        },
    },
    "nightmare_nectar": {
        "name": "Nightmare Nectar",
        "emoji": "🌙",
        "ingredients": {
            "nightshade_berry": 2,
            "cursed_fabric": 1,
            "attic_mothwing": 2,
        },
        "result": "nightmare_nectar",
        "result_type": "Haunted Potion",
        "description": "Sweet at first taste, deeply unsettling afterward. It heightens the drinker's sensitivity to strange events.",
        "effect": {
            "type": "rare_encounter_bias",
            "amount": 1,
        },
    },
    "spectral_solvent": {
        "name": "Spectral Solvent",
        "emoji": "🫧",
        "ingredients": {
            "medical_residue": 2,
            "ectoplasm": 2,
            "incense_resin": 1,
        },
        "result": "spectral_solvent",
        "result_type": "Haunted Potion",
        "description": "A volatile mixture capable of dissolving traces of spiritual residue.",
        "effect": {
            "type": "sanity_guard",
            "amount": 1,
        },
    },
}

# Register brewed items with the shared inventory registry so they can
# appear in /inventory and obey normal quantity limits.
for _recipe in CAULDRON_RECIPES.values():
    ITEM_REGISTRY.setdefault(
        _recipe["result"],
        {
            "name": _recipe["name"],
            "emoji": _recipe["emoji"],
            "max_quantity": 10,
            "type": _recipe["result_type"],
            "desc": _recipe["description"],
            "haunted_effect": dict(_recipe.get("effect", {})),
        },
    )

CAULDRON_FLAVOR_TEXT = {
    "calming_draught": [
        "The cauldron settles into a gentle simmer. For once, whatever is inside seems almost peaceful.",
        "The brew glows softly as the final ingredient dissolves. The whispers around the cauldron fade to a distant murmur.",
    ],
    "warding_incense": [
        "The wax hisses as the mixture takes shape. The candles around you suddenly burn a little steadier.",
        "A thin ring of smoke curls from the cauldron and refuses to cross the edge of your workspace.",
    ],
    "third_eye_tonic": [
        "The mixture briefly opens what looks suspiciously like an eye. It blinks once. You decide that's probably fine.",
        "The tonic clears to a glassy violet. For a moment, you can see something standing behind you. Then it's gone.",
    ],
    "gravekeepers_elixir": [
        "The brew sinks into a deep, earthy black. The cauldron gives a quiet knock from somewhere beneath the surface.",
        "A chill rolls across the room as the elixir finishes. The smell of fresh-turned soil lingers in the air.",
    ],
    "hexbreaker_tonic": [
        "The mixture snaps with tiny sparks as the final ward takes hold. Whatever curse was watching seems to look away.",
        "A bitter green flame dances across the brew before vanishing without a trace.",
    ],
    "phantom_breath": [
        "The vapor coils upward, briefly forming the outline of a face before slipping into the bottle.",
        "Cold mist spills over the rim. Something unseen exhales back at you from inside the cauldron.",
    ],
    "witches_remedy": [
        "The herbs turn the brew a surprisingly comforting green. The cauldron smells almost normal. Almost.",
        "The mixture gives one final bubble and releases a warm herbal scent... followed by a faint whisper in an unknown language.",
    ],
    "bellward_brew": [
        "The bell fragment sinks beneath the surface. A deep chime echoes from somewhere behind you, but the cauldron is completely still.",
        "A single clear bell tone rings as the brew settles. Nothing nearby appears to have moved.",
    ],
    "nightmare_nectar": [
        "The cauldron gurgles as the nightshade dissolves. For a moment, its surface reflects a moon that isn't in the sky.",
        "The nectar comes together with an unsettling sweetness. Something in the room suddenly feels much closer than before.",
    ],
    "spectral_solvent": [
        "The mixture turns transparent, revealing pale shapes drifting beneath the surface before they dissolve away.",
        "The solvent gives off a cold blue shimmer. The residue around the cauldron briefly disappears entirely.",
    ],
}

CAULDRON_RESULT_ITEMS = {
    recipe["result"]: recipe
    for recipe in CAULDRON_RECIPES.values()
}


def recipe_ingredient_name(item_id: str) -> str:
    data = ITEM_REGISTRY.get(item_id, {})
    return str(data.get("name", item_id.replace("_", " ").title()))


def recipe_ingredient_emoji(item_id: str) -> str:
    data = ITEM_REGISTRY.get(item_id, {})
    return str(data.get("emoji", "🧪"))


def format_recipe(recipe: dict, owned: dict[str, int] | None = None) -> str:
    owned = owned or {}
    lines = [
        f"{recipe['emoji']} **{recipe['name']}**",
        recipe["description"],
        "",
        "**Ingredients:**",
    ]

    for item_id, amount in recipe["ingredients"].items():
        emoji = recipe_ingredient_emoji(item_id)
        name = recipe_ingredient_name(item_id)
        have = owned.get(item_id, 0)
        mark = "✅" if have >= amount else "❌"
        lines.append(f"{mark} {emoji} {name} ×{amount} *(you have {have})*")

    lines.extend(
        [
            "",
            f"**Produces:** {recipe['emoji']} {recipe['name']} ×1",
        ]
    )
    return "\n".join(lines)


class CauldronView(discord.ui.View):
    def __init__(self, cog: "Cauldron", owner_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ This cauldron belongs to someone else.",
                ephemeral=True,
            )
            return False
        if not is_halloween_channel(interaction.channel):
            await interaction.response.send_message(halloween_channel_message(), ephemeral=True)
            return False
        if not halloween_is_active():
            await interaction.response.send_message(
                "🎃 The Cauldron is dormant outside the Halloween season.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(
        label="Brew",
        emoji="🧪",
        style=discord.ButtonStyle.primary,
    )
    async def brew_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.cog.show_brew_menu(interaction)

    @discord.ui.button(
        label="Recipes",
        emoji="📖",
        style=discord.ButtonStyle.secondary,
    )
    async def recipes_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.cog.show_recipe_book(interaction)

    @discord.ui.button(
        label="Ingredients",
        emoji="🎒",
        style=discord.ButtonStyle.secondary,
    )
    async def ingredients_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.cog.show_ingredients(interaction)

    @discord.ui.button(
        label="Close",
        emoji="✖️",
        style=discord.ButtonStyle.danger,
    )
    async def close_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        for child in self.children:
            if isinstance(child, (discord.ui.Button, discord.ui.Select)):
                child.disabled = True
        await interaction.response.edit_message(view=self)


class RecipeSelect(discord.ui.Select):
    def __init__(self, cog: "Cauldron", owner_id: int):
        self.cog = cog
        self.owner_id = owner_id

        options = [
            discord.SelectOption(
                label=recipe["name"],
                value=recipe_id,
                emoji=recipe["emoji"],
                description="Brew this recipe",
            )
            for recipe_id, recipe in CAULDRON_RECIPES.items()
        ]

        super().__init__(
            placeholder="Choose a brew...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ This brewing menu belongs to someone else.",
                ephemeral=True,
            )
            return

        if not halloween_is_active():
            await interaction.response.send_message(
                "🎃 The Cauldron is dormant outside the Halloween season.",
                ephemeral=True,
            )
            return

        recipe_id = self.values[0]
        await self.cog.brew(interaction, recipe_id)


class RecipeSelectView(discord.ui.View):
    def __init__(self, cog: "Cauldron", owner_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.owner_id = owner_id
        self.add_item(RecipeSelect(cog, owner_id))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ This brewing menu belongs to someone else.", ephemeral=True)
            return False
        if not is_halloween_channel(interaction.channel):
            await interaction.response.send_message(halloween_channel_message(), ephemeral=True)
            return False
        if not halloween_is_active():
            await interaction.response.send_message("🎃 The Cauldron is dormant outside the Halloween season.", ephemeral=True)
            return False
        return True


class SeasonalCraftingView(discord.ui.View):
    def __init__(self, cauldron, owner_id: int):
        super().__init__(timeout=300)
        self.cauldron = cauldron
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ This seasonal crafting menu belongs to someone else.",
                ephemeral=True,
            )
            return False
        if not is_halloween_channel(interaction.channel):
            await interaction.response.send_message(halloween_channel_message(), ephemeral=True)
            return False
        if not halloween_is_active():
            await interaction.response.send_message(
                "🎃 Seasonal Crafting is dormant outside the Halloween season.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Witch's Cauldron", emoji="🧙", style=discord.ButtonStyle.primary, row=0)
    async def cauldron_button(self, interaction, button):
        await self.cauldron.show_cauldron_menu(interaction)

    @discord.ui.button(label="Haunted Workshop", emoji="🔧", style=discord.ButtonStyle.secondary, row=0)
    async def workshop_button(self, interaction, button):
        cog = self.cauldron.bot.get_cog("Workshop")
        if cog:
            await cog.show_menu(interaction)
        else:
            await interaction.response.send_message("❌ The Haunted Workshop is not loaded.", ephemeral=True)

    @discord.ui.button(label="Ritual Table", emoji="🕯️", style=discord.ButtonStyle.secondary, row=0)
    async def ritual_button(self, interaction, button):
        cog = self.cauldron.bot.get_cog("RitualTable")
        if cog:
            await cog.show_menu(interaction)
        else:
            await interaction.response.send_message("❌ The Ritual Table is not loaded.", ephemeral=True)

    @discord.ui.button(label="Close", emoji="❌", style=discord.ButtonStyle.danger, row=1)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            if isinstance(child, (discord.ui.Button, discord.ui.Select)):
                child.disabled = True
        await interaction.response.edit_message(view=self)


class Cauldron(commands.Cog):
    """Seasonal Halloween Cauldron and Haunted potion brewing."""

    def __init__(self, bot):
        self.bot = bot

    async def show_seasonal_hub(self, interaction):
        embed = discord.Embed(
            title="🎃 Seasonal Crafting",
            description=(
                "The Halloween crafting stations are all gathered in one place.\n\n"
                "🧙 **Witch's Cauldron** — Brew tonics, elixirs, incense, and other strange mixtures.\n"
                "🔧 **Haunted Workshop** — Assemble devices, tools, and salvaged machinery.\n"
                "🕯️ **Ritual Table** — Create wards, charms, and occult objects."
            ),
            color=discord.Color.dark_purple(),
        )
        embed.set_footer(text="Halloween Seasonal System")
        view = SeasonalCraftingView(self, interaction.user.id)
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)

    async def show_cauldron_menu(self, interaction):
        embed = discord.Embed(
            title="🧙 The Witch's Cauldron",
            description=(
                "*Something bubbles ominously inside...*\n\n"
                "Turn your Haunted Ingredients into strange brews and ritual mixtures."
            ),
            color=discord.Color.dark_purple(),
        )
        embed.set_footer(text="Halloween Seasonal System")
        await interaction.response.edit_message(
            embed=embed,
            view=CauldronView(self, interaction.user.id),
        )

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

    async def owned(self, db, user_id: int) -> dict[str, int]:
        async with db.execute(
            "SELECT item_id, quantity FROM inventory WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            return {
                item_id: quantity
                for item_id, quantity in await cursor.fetchall()
            }

    async def show_cauldron(
        self,
        interaction: discord.Interaction,
        *,
        ephemeral: bool = False,
    ):
        if not halloween_is_active():
            message = "🎃 The Cauldron is dormant outside the Halloween season."
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=ephemeral)
            else:
                await interaction.response.send_message(message, ephemeral=ephemeral)
            return

        embed = discord.Embed(
            title="🧙 The Witch's Cauldron",
            description=(
                "*Something bubbles ominously inside...*\n"
                "*Something beneath the surface knocks three times.*\n\n"
                "Turn your Haunted Ingredients into strange brews and "
                "ritual supplies.\n\n"
                "🧪 **Brew** — Choose something to make\n"
                "📖 **Recipes** — Browse every known recipe\n"
                "🎒 **Ingredients** — Check your Haunted Ingredients"
            ),
            color=discord.Color.dark_purple(),
        )
        embed.set_footer(text="Halloween Seasonal System")

        view = CauldronView(self, interaction.user.id)

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, view=view, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(
                embed=embed,
                view=view,
                ephemeral=ephemeral,
            )

    async def show_brew_menu(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🧪 Brew at the Cauldron",
            description=(
                "*The liquid inside bubbles without any heat.*\n\n"
                "Choose a recipe below. Your ingredients are checked again "
                "when you brew, so you cannot spend the same ingredients twice."
            ),
            color=discord.Color.dark_purple(),
        )

        view = RecipeSelectView(self, interaction.user.id)
        await interaction.response.edit_message(embed=embed, view=view)

    async def show_recipe_book(self, interaction: discord.Interaction):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_inventory(db)
            owned = await self.owned(db, interaction.user.id)

        pages = []
        for recipe in CAULDRON_RECIPES.values():
            pages.append(format_recipe(recipe, owned))

        embed = discord.Embed(
            title="📖 Cauldron Recipe Book",
            description="\n\n".join(pages),
            color=discord.Color.dark_purple(),
        )
        await interaction.response.edit_message(
            embed=embed,
            view=CauldronView(self, interaction.user.id),
        )

    async def show_ingredients(self, interaction: discord.Interaction):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_inventory(db)
            owned = await self.owned(db, interaction.user.id)

        lines = []
        for item_id in sorted(
            {
                ingredient
                for recipe in CAULDRON_RECIPES.values()
                for ingredient in recipe["ingredients"]
            }
        ):
            quantity = owned.get(item_id, 0)
            if quantity <= 0:
                continue
            lines.append(
                f"{recipe_ingredient_emoji(item_id)} "
                f"**{recipe_ingredient_name(item_id)}** ×{quantity}"
            )

        if not lines:
            description = (
                "You don't have any of the ingredients needed for the "
                "currently known recipes.\n\n"
                "Head into **Haunted Exploration** and search the locations "
                "for more ingredients!"
            )
        else:
            description = "\n".join(lines)

        embed = discord.Embed(
            title="🎒 Haunted Ingredients",
            description=description,
            color=discord.Color.dark_purple(),
        )
        await interaction.response.edit_message(
            embed=embed,
            view=CauldronView(self, interaction.user.id),
        )

    async def brew(self, interaction: discord.Interaction, recipe_id: str):
        recipe = CAULDRON_RECIPES.get(recipe_id)
        if recipe is None:
            await interaction.response.send_message(
                "❌ That cauldron recipe doesn't exist.",
                ephemeral=True,
            )
            return

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_inventory(db)
            await db.execute("BEGIN IMMEDIATE")

            owned = await self.owned(db, interaction.user.id)

            missing = []
            for item_id, amount in recipe["ingredients"].items():
                have = owned.get(item_id, 0)
                if have < amount:
                    missing.append(
                        f"{recipe_ingredient_emoji(item_id)} "
                        f"{recipe_ingredient_name(item_id)} ×{amount - have}"
                    )

            if missing:
                await db.rollback()
                await interaction.response.send_message(
                    "❌ **You're missing:**\n" + "\n".join(missing),
                    ephemeral=True,
                )
                return

            for item_id, amount in recipe["ingredients"].items():
                await db.execute(
                    """
                    UPDATE inventory
                    SET quantity = quantity - ?
                    WHERE user_id = ? AND item_id = ?
                    """,
                    (amount, interaction.user.id, item_id),
                )

            # Respect the existing inventory system's normal max-quantity
            # handling for the brewed item. The helper handles overflow.
            await db.commit()

        # add_inventory_item owns the inventory-capacity/overflow logic.
        # Use a fresh connection after committing ingredient consumption so
        # its own transaction remains isolated.
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            added, _new_quantity, _max_quantity = await add_inventory_item(
                db,
                interaction.user.id,
                recipe["result"],
                recipe["result_type"],
                1,
            )
            await db.commit()

        # If the potion itself is already at its inventory cap, refund the
        # consumed ingredients rather than silently destroying them.
        if added < 1:
            async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
                await db.execute("BEGIN IMMEDIATE")
                for item_id, amount in recipe["ingredients"].items():
                    await db.execute(
                        """
                        UPDATE inventory
                        SET quantity = quantity + ?
                        WHERE user_id = ? AND item_id = ?
                        """,
                        (amount, interaction.user.id, item_id),
                    )
                await db.commit()

            await interaction.response.send_message(
                f"❌ Your **{recipe['name']}** inventory is full. "
                "Your ingredients were returned.",
                ephemeral=True,
            )
            return

        import random
        flavor = random.choice(CAULDRON_FLAVOR_TEXT.get(recipe_id, ["The cauldron gives a final, unsettling bubble as the brew settles."]))
        description = (
            f"*{flavor}*\n\n"
            f"You brewed **{recipe['emoji']} {recipe['name']} ×1**!\n\n"
            f"{recipe['description']}\n\n"
            f"🧪 **Effect:** `{recipe['effect']['type']}`"
        )

        achievements_cog = self.bot.get_cog("Achievements")
        if achievements_cog:
            await achievements_cog.add_haunted_crafting_progress(interaction.user.id, "cauldron")

        embed = discord.Embed(
            title="🧙 Brew Complete!",
            description=description,
            color=discord.Color.dark_purple(),
        )
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    @commands.hybrid_command(
        name="seasonal_crafting",
        description="Open the Halloween Seasonal Crafting hub.",
    )
    async def seasonal_crafting(self, ctx: commands.Context):
        if not is_halloween_channel(ctx.channel):
            await ctx.send(halloween_channel_message())
            return
        if not halloween_is_active():
            await ctx.send(
                "🎃 Seasonal Crafting is dormant right now. "
                "Come back during the Halloween event."
            )
            return

        await ctx.defer()
        embed = discord.Embed(
            title="🎃 Seasonal Crafting",
            description=(
                "The Halloween crafting stations are all gathered in one place.\n\n"
                "🧙 **Witch's Cauldron** — Brew strange mixtures.\n"
                "🔧 **Haunted Workshop** — Assemble salvaged devices and tools.\n"
                "🕯️ **Ritual Table** — Create wards, charms, and occult objects."
            ),
            color=discord.Color.dark_purple(),
        )
        embed.set_footer(text="Halloween Seasonal System")
        await ctx.send(
            embed=embed,
            view=SeasonalCraftingView(self, ctx.author.id),
        )

    @commands.hybrid_command(
        name="cauldron",
        description="Open the Halloween Witch's Cauldron.",
    )
    async def cauldron(self, ctx: commands.Context):
        if not is_halloween_channel(ctx.channel):
            await ctx.send(halloween_channel_message())
            return
        if not halloween_is_active():
            await ctx.send(
                "🎃 The Witch's Cauldron is dormant right now. "
                "Come back during the Halloween season."
            )
            return

        await ctx.defer()
        embed = discord.Embed(
            title="🧙 The Witch's Cauldron",
            description=(
                "*Something bubbles ominously inside...*\n\n"
                "Turn your Haunted Ingredients into strange brews and "
                "ritual supplies.\n\n"
                "🧪 **Brew** — Choose something to make\n"
                "📖 **Recipes** — Browse every known recipe\n"
                "🎒 **Ingredients** — Check your Haunted Ingredients"
            ),
            color=discord.Color.dark_purple(),
        )
        embed.set_footer(text="Halloween Seasonal System")
        await ctx.send(
            embed=embed,
            view=CauldronView(self, ctx.author.id),
        )


async def setup(bot):
    await bot.add_cog(Cauldron(bot))
