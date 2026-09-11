import discord
import aiosqlite
from discord import app_commands
from discord.ext import commands


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="admin",
        description="Open the administrator control panel."
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(
        command=[
            app_commands.Choice(
                name="🔄 Reset Bump Timer",
                value="resetbump"
            ),
        ]
    )
    async def admin(
        self,
        interaction: discord.Interaction,
        command: app_commands.Choice[str]
    ):
        if command.value == "resetbump":
            async with aiosqlite.connect("/app/data/levels.db") as db:
                await db.execute("DELETE FROM bump_timer WHERE id = 1")
                await db.commit()

            await interaction.response.send_message(
                "Bump timer cleared! 🔄",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Admin(bot))