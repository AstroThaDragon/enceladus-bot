import discord
import aiosqlite
import datetime
import pytz
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
    @app_commands.describe(
        command="Choose an administrative action.",
        member="The member to modify.",
        streak="The fortune streak to set.",
        amount="The XP amount to set."
    )
    @app_commands.choices(
        command=[
            app_commands.Choice(
                name="🔄 Reset Bump Timer",
                value="resetbump"
            ),
            app_commands.Choice(
                name="🔥 Set Fortune Streak",
                value="setfortunestreak"
            ),
            app_commands.Choice(
                name="📈 Set XP",
                value="setxp"
            ),
        ]
    )
    async def admin(
        self,
        interaction: discord.Interaction,
        command: app_commands.Choice[str],
        member: discord.Member = None,
        streak: int = None,
        amount: int = None
    ):
        if command.value == "resetbump":
            async with aiosqlite.connect("/app/data/levels.db") as db:
                await db.execute("DELETE FROM bump_timer WHERE id = 1")
                await db.commit()

            await interaction.response.send_message(
                "Bump timer cleared! 🔄",
                ephemeral=True
            )

        elif command.value == "setfortunestreak":
            if member is None:
                return await interaction.response.send_message(
                    "⚠️ Please select a member whose fortune streak you want to set.",
                    ephemeral=True
                )

            if streak is None:
                return await interaction.response.send_message(
                    "⚠️ Please enter the fortune streak amount you want to set.",
                    ephemeral=True
                )

            if streak < 0:
                return await interaction.response.send_message(
                    "⚠️ Streak cannot be negative.",
                    ephemeral=True
                )

            et_timezone = pytz.timezone("US/Eastern")
            now_et = datetime.datetime.now(et_timezone)
            current_date_et = now_et.strftime("%Y-%m-%d")

            async with aiosqlite.connect("/app/data/levels.db") as db:
                await db.execute(
                    """
                    INSERT INTO users (
                        user_id,
                        fortune_streak,
                        last_fortune_streak_date
                    )
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id)
                    DO UPDATE SET
                        fortune_streak = excluded.fortune_streak,
                        last_fortune_streak_date = excluded.last_fortune_streak_date
                    """,
                    (
                        member.id,
                        streak,
                        current_date_et
                    )
                )

                await db.commit()

            await interaction.response.send_message(
                f"✅ Restored {member.mention}'s fortune streak to "
                f"**{streak} day{'s' if streak != 1 else ''}**.",
                ephemeral=True
            )

        elif command.value == "setxp":
            if member is None:
                return await interaction.response.send_message(
                    "⚠️ Please select a member whose XP you want to set.",
                    ephemeral=True
                )

            if amount is None:
                return await interaction.response.send_message(
                    "⚠️ Please enter the XP amount you want to set.",
                    ephemeral=True
                )

            leveling_cog = self.bot.get_cog("Leveling")

            if leveling_cog is None:
                return await interaction.response.send_message(
                    "❌ The leveling system is currently unavailable.",
                    ephemeral=True
                )

            temp_level = 0
            while amount >= leveling_cog.get_xp_for_level(temp_level + 1):
                temp_level += 1

            async with aiosqlite.connect(leveling_cog.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO users (user_id, xp, level)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id)
                    DO UPDATE SET
                        xp = excluded.xp,
                        level = excluded.level
                    """,
                    (member.id, amount, temp_level)
                )
                await db.commit()

            await leveling_cog._update_member_roles(member, temp_level)

            await interaction.response.send_message(
                f"✅ Set {member.name}'s XP to {amount} "
                f"(Level {temp_level}).",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Admin(bot))