import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

from database import ECONOMY_DB_NAME
from seasonal_updates.halloween.halloween import get_collectibles as get_halloween_collectibles

async def ensure_collectible_tables(db):
    await db.execute("""
        CREATE TABLE IF NOT EXISTS collectibles (
            user_id INTEGER NOT NULL,
            collectible_id TEXT NOT NULL,
            category TEXT NOT NULL,
            discovered_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, collectible_id)
        )
    """)


async def record_collectible(db, bot, user_id, collectible_id, category="Halloween"):
    """Permanently record a seasonal collectible inside an existing transaction."""
    await ensure_collectible_tables(db)
    cursor = await db.execute(
        "INSERT OR IGNORE INTO collectibles (user_id, collectible_id, category) VALUES (?, ?, ?)",
        (user_id, collectible_id, category),
    )
    added = cursor.rowcount > 0

    if added:
        achievements_cog = bot.get_cog("Achievements") if bot else None
        if achievements_cog:
            await achievements_cog.check_user_achievements(user_id, db=db)
    return added


class Collectibles(commands.Cog):
    """Permanent seasonal collection tracker."""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="collectibles",
        description="View your permanent seasonal collectible collection.",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Info", value="info"),
        ],
    )
    @app_commands.describe(
        action="Optional action to perform.",
        collectible="A collectible you have permanently discovered.",
    )
    async def collectibles(
        self,
        ctx: commands.Context,
        action: str | None = None,
        collectible: str | None = None,
    ):
        """View the permanent collection or inspect a discovered collectible."""

        # /collectibles info <collectible>
        if action == "info":
            user_id = ctx.author.id

            if not collectible:
                return await ctx.send(
                    "❌ **Choose a collectible to view.**\n"
                    "Use the collectible picker after selecting **Info**.",
                    ephemeral=True,
                )

            async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
                await ensure_collectible_tables(db)
                async with db.execute(
                    """
                    SELECT collectible_id
                    FROM collectibles
                    WHERE user_id = ?
                    """,
                    (user_id,),
                ) as cursor:
                    discovered = {row[0] for row in await cursor.fetchall()}

            entries = get_halloween_collectibles()
            collectible_map = {
                item_id: (name, emoji, desc)
                for item_id, name, emoji, desc in entries
            }

            if collectible not in discovered:
                return await ctx.send(
                    "❌ **You haven't discovered that collectible yet.**\n"
                    "Only collectibles you've found can be viewed here.",
                    ephemeral=True,
                )

            data = collectible_map.get(collectible)
            if not data:
                return await ctx.send(
                    "❌ **That collectible is no longer available in the current collection.**",
                    ephemeral=True,
                )

            name, emoji, description = data

            embed = discord.Embed(
                title=f"{emoji} {name}",
                description=description,
                color=discord.Color.dark_purple(),
            )
            embed.set_author(
                name=f"{ctx.author.display_name}'s Collectible",
                icon_url=ctx.author.display_avatar.url,
            )
            embed.set_footer(text="This discovery is permanent.")

            return await ctx.send(embed=embed, ephemeral=True)

        # /collectibles
        await ctx.defer()
        user_id = ctx.author.id

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await ensure_collectible_tables(db)
            async with db.execute(
                "SELECT collectible_id FROM collectibles WHERE user_id = ?",
                (user_id,),
            ) as cursor:
                owned = {row[0] for row in await cursor.fetchall()}

        categories = {
            "🎃 Halloween - Lair of Frights Items": get_halloween_collectibles(),
        }

        pages = []
        page_size = 15

        for category, entries in categories.items():
            if not entries:
                continue

            found = sum(1 for item_id, *_ in entries if item_id in owned)
            total = len(entries)
            total_pages = (total + page_size - 1) // page_size

            for start in range(0, total, page_size):
                chunk_entries = entries[start:start + page_size]
                page_number = start // page_size + 1
                lines = []

                for item_id, name, emoji, _desc in chunk_entries:
                    if item_id in owned:
                        lines.append(f"{emoji} **{name}**")
                    else:
                        lines.append("❓ **???**")

                embed = discord.Embed(
                    title=f"📚 {ctx.author.display_name}'s Collectibles",
                    description=(
                        f"**{category}** • Part **{page_number}/{total_pages}**\n"
                        f"Collected: **{found}/{total}** ({found / total * 100:.0f}%)\n\n"
                        + "\n\n".join(lines)
                        + "\n\nUndiscovered collectibles remain hidden until you find them."
                    ),
                    color=discord.Color.dark_purple(),
                )
                pages.append(embed)

        if not pages:
            return await ctx.send("📚 **There are no seasonal collectibles available yet!**")

        class CollectiblesView(discord.ui.View):
            def __init__(self, owner_id, embeds):
                super().__init__(timeout=300)
                self.owner_id = owner_id
                self.embeds = embeds
                self.current_page = 0

            def current_embed(self):
                embed = self.embeds[self.current_page]
                embed.set_footer(
                    text=f"Page {self.current_page + 1}/{len(self.embeds)} • Seasonal discoveries are permanent."
                )
                return embed

            async def interaction_check(self, interaction: discord.Interaction):
                if interaction.user.id != self.owner_id:
                    await interaction.response.send_message(
                        "❌ This collectibles menu belongs to someone else.", ephemeral=True
                    )
                    return False
                return True

            @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
            async def previous(self, interaction, button):
                self.current_page = (self.current_page - 1) % len(self.embeds)
                await interaction.response.edit_message(embed=self.current_embed(), view=self)

            @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
            async def next(self, interaction, button):
                self.current_page = (self.current_page + 1) % len(self.embeds)
                await interaction.response.edit_message(embed=self.current_embed(), view=self)

        view = CollectiblesView(user_id, pages)
        await ctx.send(embed=view.current_embed(), view=view)

    @collectibles.autocomplete("collectible")
    async def collectibles_collectible_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ):
        """Offer only collectibles this member has permanently discovered."""
        user_id = interaction.user.id

        try:
            async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
                await ensure_collectible_tables(db)
                async with db.execute(
                    """
                    SELECT collectible_id
                    FROM collectibles
                    WHERE user_id = ?
                    """,
                    (user_id,),
                ) as cursor:
                    discovered = {row[0] for row in await cursor.fetchall()}
        except Exception:
            return []

        current = (current or "").lower().strip()
        choices = []

        for item_id, name, emoji, _description in get_halloween_collectibles():
            if item_id not in discovered:
                continue

            search_text = f"{name} {item_id}".lower()
            if current and current not in search_text:
                continue

            choices.append(
                app_commands.Choice(
                    name=f"{emoji} {name}"[:100],
                    value=item_id,
                )
            )

            if len(choices) >= 25:
                break

        return choices


async def setup(bot):
    await bot.add_cog(Collectibles(bot))
