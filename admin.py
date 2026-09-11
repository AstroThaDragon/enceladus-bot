import discord
import aiosqlite
from discord import app_commands
from discord.ext import commands


class Admin(commands.GroupCog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="resetbump", description="Clear the server bump timer.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def resetbump(self, interaction: discord.Interaction):
        async with aiosqlite.connect("/app/data/levels.db") as db:
            await db.execute("DELETE FROM bump_timer WHERE id = 1")
            await db.commit()

        await interaction.response.send_message("Bump timer cleared! 🔄")


async def setup(bot):
    await bot.add_cog(Admin(bot))