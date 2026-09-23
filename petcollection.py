import aiosqlite
import discord
from discord.ext import commands

from database import ECONOMY_DB_NAME
from pets import (
    PETS,
    HALLOWEEN_PETS,
    HAUNTED_PETS,
)
from pet_variants import (
    NORMAL_PET_TYPES,
    HALLOWEEN_PET_TYPES,
    variant_set_for_pet,
    get_variant_display,
)


PAGE_SIZE = 15


def _pet_entry(pet_type, definition):
    return {
        "id": f"pet:{pet_type}",
        "name": definition["name"],
        "emoji": definition["emoji"],
        "description": definition.get("description", ""),
        "pet_type": pet_type,
        "variant_id": None,
    }


def _variant_entry(pet_type, base_definition, variant_id, variant):
    display_name, display_emoji, lore = get_variant_display(
        pet_type,
        base_definition["name"],
        variant_id,
    )
    return {
        "id": f"pet_variant:{pet_type}:{variant_id}",
        "name": display_name,
        "emoji": display_emoji or variant["emoji"],
        "description": lore or variant.get("lore", ""),
        "pet_type": pet_type,
        "variant_id": variant_id,
    }


def build_collection_categories():
    """Build the complete pet encyclopedia from the live pet/variant registries."""
    categories = {}

    categories["🪐 Normal Pets"] = [
        _pet_entry(pet_type, PETS[pet_type])
        for pet_type in sorted(PETS)
    ]

    normal_variants = []
    for pet_type in sorted(NORMAL_PET_TYPES):
        definition = PETS.get(pet_type)
        if not definition:
            continue
        for variant_id, variant in variant_set_for_pet(pet_type).items():
            normal_variants.append(
                _variant_entry(pet_type, definition, variant_id, variant)
            )
    categories["✨ Normal Pet Variants"] = normal_variants

    categories["🎃 Halloween Pets"] = [
        _pet_entry(pet_type, HALLOWEEN_PETS[pet_type])
        for pet_type in sorted(HALLOWEEN_PETS)
    ]

    halloween_variants = []
    for pet_type in sorted(HALLOWEEN_PET_TYPES):
        definition = HALLOWEEN_PETS.get(pet_type)
        if not definition:
            continue
        for variant_id, variant in variant_set_for_pet(pet_type).items():
            halloween_variants.append(
                _variant_entry(pet_type, definition, variant_id, variant)
            )
    categories["🎃 Halloween Pet Variants"] = halloween_variants

    categories["👻 Haunted Pets"] = [
        _pet_entry(pet_type, HAUNTED_PETS[pet_type])
        for pet_type in sorted(HAUNTED_PETS)
    ]

    return categories


class PetCollection(commands.Cog):
    """Pokédex-style encyclopedia for every pet and pet variant."""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="petcollection",
        description="View the complete pet collection and variant encyclopedia.",
    )
    async def petcollection(self, ctx: commands.Context):
        await ctx.defer()
        user_id = ctx.author.id

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            async with db.execute(
                """
                SELECT pet_type, pet_stage, variant_id
                FROM pets
                WHERE user_id = ?
                  AND COALESCE(pet_type, pet_stage) != 'egg'
                """,
                (user_id,),
            ) as cursor:
                rows = await cursor.fetchall()

        owned_base = set()
        owned_variants = set()

        for pet_type, pet_stage, variant_id in rows:
            pet_type = pet_type or pet_stage
            if not pet_type:
                continue
            owned_base.add(pet_type)
            if variant_id:
                owned_variants.add((pet_type, variant_id))

        categories = build_collection_categories()
        pages = []

        for category, entries in categories.items():
            if not entries:
                continue

            if category.endswith("Variants"):
                found = sum(
                    1 for entry in entries
                    if (entry["pet_type"], entry["variant_id"]) in owned_variants
                )
            else:
                found = sum(
                    1 for entry in entries
                    if entry["pet_type"] in owned_base
                )

            total = len(entries)
            total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

            for start in range(0, total, PAGE_SIZE):
                chunk = entries[start:start + PAGE_SIZE]
                page_number = start // PAGE_SIZE + 1
                lines = []

                for entry in chunk:
                    if category.endswith("Variants"):
                        discovered = (
                            entry["pet_type"],
                            entry["variant_id"],
                        ) in owned_variants
                    else:
                        discovered = entry["pet_type"] in owned_base

                    if discovered:
                        lines.append(
                            f"{entry['emoji']} **{entry['name']}**"
                        )
                    else:
                        lines.append("❓ **???**")

                embed = discord.Embed(
                    title=f"🐾 {ctx.author.display_name}'s Pet Collection",
                    description=(
                        f"**{category}** • Part **{page_number}/{total_pages}**\n"
                        f"Collected: **{found}/{total}** "
                        f"({found / total * 100:.0f}%)\n\n"
                        + "\n\n".join(lines)
                        + "\n\nUndiscovered pets and variants remain hidden until you discover them."
                    ),
                    color=discord.Color.dark_purple(),
                )
                pages.append(embed)

        if not pages:
            return await ctx.send(
                "🐾 **There are no pets available in the collection yet!**"
            )

        class PetCollectionView(discord.ui.View):
            def __init__(self, owner_id, embeds):
                super().__init__(timeout=300)
                self.owner_id = owner_id
                self.embeds = embeds
                self.current_page = 0

            def current_embed(self):
                embed = self.embeds[self.current_page]
                embed.set_footer(
                    text=(
                        f"Page {self.current_page + 1}/{len(self.embeds)} "
                        "• Pet discoveries are permanent."
                    )
                )
                return embed

            async def interaction_check(self, interaction: discord.Interaction):
                if interaction.user.id != self.owner_id:
                    await interaction.response.send_message(
                        "❌ This pet collection belongs to someone else.",
                        ephemeral=True,
                    )
                    return False
                return True

            @discord.ui.button(
                label="◀",
                style=discord.ButtonStyle.secondary,
            )
            async def previous(self, interaction, button):
                self.current_page = (
                    self.current_page - 1
                ) % len(self.embeds)
                await interaction.response.edit_message(
                    embed=self.current_embed(),
                    view=self,
                )

            @discord.ui.button(
                label="▶",
                style=discord.ButtonStyle.secondary,
            )
            async def next(self, interaction, button):
                self.current_page = (
                    self.current_page + 1
                ) % len(self.embeds)
                await interaction.response.edit_message(
                    embed=self.current_embed(),
                    view=self,
                )

        view = PetCollectionView(user_id, pages)
        await ctx.send(embed=view.current_embed(), view=view)


async def setup(bot):
    await bot.add_cog(PetCollection(bot))
