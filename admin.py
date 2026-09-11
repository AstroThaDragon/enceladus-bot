import discord
import aiosqlite
from discord import app_commands
from discord.ext import commands


class AdminMenu(discord.ui.Select):
    def __init__(self, cog):
        self.cog = cog

        options = [
            discord.SelectOption(
                label="Reset Bump Timer",
                description="Clear the server bump timer.",
                emoji="🔄",
                value="resetbump"
            ),
        ]

        super().__init__(
            placeholder="🛠️ Select an admin action...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "resetbump":
            await self.cog.resetbump_action(interaction)


class AdminMenuView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=120)
        self.add_item(AdminMenu(cog))


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="admin",
        description="Open the administrator control panel."
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def admin(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛠️ Administrator Control Panel",
            description="Select an administrative action from the menu below.",
            color=discord.Color.red()
        )

        await interaction.response.send_message(
            embed=embed,
            view=AdminMenuView(self),
            ephemeral=True
        )

    async def resetbump_action(self, interaction: discord.Interaction):
        async with aiosqlite.connect("/app/data/levels.db") as db:
            await db.execute("DELETE FROM bump_timer WHERE id = 1")
            await db.commit()

        await interaction.response.send_message(
            "Bump timer cleared! 🔄",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Admin(bot))