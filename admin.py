import discord
import aiosqlite
import datetime
import pytz
from discord import app_commands
from discord.ext import commands
from leveling import ResetConfirm, FullResetConfirm, FontView
from moderation import VerifyView
from verification import VerificationPanelView


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
        level="The level to set.",
        reset_type="Choose what data to reset."
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
            app_commands.Choice(
            name="⭐ Set Level",
            value="setlevel"
            ),
            app_commands.Choice(
            name="➕ Add XP",
            value="addxp"
            ),
            app_commands.Choice(
            name="🔄 Sync Levels",
            value="sync_levels"
            ),
            app_commands.Choice(
            name="🧹 Purge Left Members",
            value="purge_left_members"
            ),
            app_commands.Choice(
            name="♻️ Reset",
            value="reset"
            ),
            app_commands.Choice(
            name="🖼️ Font Preview Setup",
            value="font_preview_setup"
            ),
            app_commands.Choice(
            name="🔒 Send Verify Panel",
            value="sendverifypanel"
            ),
            app_commands.Choice(
            name="🔞 Send NSFW Verification Panel",
            value="sendverificationpanel"
            ),
        ]
    )
    async def admin(
        self,
        interaction: discord.Interaction,
        command: app_commands.Choice[str],
        member: discord.Member = None,
        streak: int = None,
        amount: int = None,
        level: int = None,
        reset_type: app_commands.Choice[str] = None
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

        elif command.value == "setlevel":
            if member is None:
                return await interaction.response.send_message(
                    "⚠️ Please select a member whose level you want to set.",
                    ephemeral=True
                )

            if level is None:
                return await interaction.response.send_message(
                    "⚠️ Please enter the level you want to set.",
                    ephemeral=True
                )

            if level < 0:
                return await interaction.response.send_message(
                    "⚠️ Level cannot be negative.",
                    ephemeral=True
                )

            leveling_cog = self.bot.get_cog("Leveling")

            if leveling_cog is None:
                return await interaction.response.send_message(
                    "❌ The leveling system is currently unavailable.",
                    ephemeral=True
                )

            new_xp = leveling_cog.get_xp_for_level(level)

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
                    (member.id, new_xp, level)
                )
                await db.commit()

            await leveling_cog._update_member_roles(member, level)

            await interaction.response.send_message(
                f"✅ Set {member.mention} to **Level {level}** "
                f"({new_xp} XP).",
                ephemeral=True
            )

        elif command.value == "addxp":
            if member is None:
                return await interaction.response.send_message(
                    "⚠️ Please select a member to give XP to.",
                    ephemeral=True
                )

            if amount is None:
                return await interaction.response.send_message(
                    "⚠️ Please enter the amount of XP to add.",
                    ephemeral=True
                )

            leveling_cog = self.bot.get_cog("Leveling")

            if leveling_cog is None:
                return await interaction.response.send_message(
                    "❌ The leveling system is currently unavailable.",
                    ephemeral=True
                )

            await leveling_cog.add_xp(member, amount)

            async with aiosqlite.connect(leveling_cog.db_path) as db:
                async with db.execute(
                    "SELECT xp, level FROM users WHERE user_id = ?",
                    (member.id,)
                ) as cursor:
                    result = await cursor.fetchone()

            if result:
                new_xp, new_level = result

                await interaction.response.send_message(
                    f"✅ Added {amount} XP to {member.mention}! "
                    f"They now have **{new_xp} XP** (Level {new_level}).",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"✅ Added {amount} XP to {member.mention}!",
                    ephemeral=True
                )

        elif command.value == "sync_levels":
            await interaction.response.defer(ephemeral=True)

            leveling_cog = self.bot.get_cog("Leveling")

            if leveling_cog is None:
                return await interaction.followup.send(
                    "❌ The leveling system is currently unavailable.",
                    ephemeral=True
                )

            synced_count = 0

            async with aiosqlite.connect(leveling_cog.db_path) as db:
                for member in interaction.guild.members:
                    if member.bot:
                        continue

                    starting_level = 0

                    for level, role_id in sorted(
                        leveling_cog.level_roles.items(),
                        reverse=True
                    ):
                        if role_id != 0 and member.get_role(role_id):
                            starting_level = level
                            break

                    async with db.execute(
                        "SELECT level FROM users WHERE user_id = ?",
                        (member.id,)
                    ) as cursor:
                        result = await cursor.fetchone()

                    current_db_level = result[0] if result else -1

                    if starting_level > current_db_level:
                        xp = leveling_cog.get_xp_for_level(starting_level)

                        await db.execute(
                            """
                            INSERT INTO users (
                                user_id,
                                xp,
                                level,
                                bar_color,
                                bg_url
                            )
                            VALUES (?, ?, ?, '#8a2be2', 'default')
                            ON CONFLICT(user_id)
                            DO UPDATE SET
                                xp = excluded.xp,
                                level = excluded.level
                            """,
                            (
                                member.id,
                                xp,
                                starting_level
                            )
                        )

                        synced_count += 1

                await db.commit()

            await interaction.followup.send(
                f"✅ Sync complete! Calibrated {synced_count} members.",
                ephemeral=True
            )

        elif command.value == "purge_left_members":
            await interaction.response.defer(ephemeral=True)

            leveling_cog = self.bot.get_cog("Leveling")

            if leveling_cog is None:
                return await interaction.followup.send(
                    "❌ The leveling system is currently unavailable.",
                    ephemeral=True
                )

            from database import ECONOMY_DB_NAME

            async with aiosqlite.connect(leveling_cog.db_path) as db:
                await db.execute(
                    "ATTACH DATABASE ? AS economy",
                    (ECONOMY_DB_NAME,)
                )

                async with db.execute(
                    "SELECT user_id FROM main.users"
                ) as cursor:
                    rows = await cursor.fetchall()

                deleted_count = 0

                for row in rows:
                    user_id = row[0]

                    if interaction.guild.get_member(user_id) is None:
                        await db.execute(
                            "DELETE FROM economy.inventory WHERE user_id = ?",
                            (user_id,)
                        )

                        await db.execute(
                            "DELETE FROM economy.pets WHERE user_id = ?",
                            (user_id,)
                        )

                        await db.execute(
                            "DELETE FROM economy.users WHERE user_id = ?",
                            (user_id,)
                        )

                        await db.execute(
                            "DELETE FROM main.users WHERE user_id = ?",
                            (user_id,)
                        )

                        deleted_count += 1

                await db.commit()
                await db.execute("DETACH DATABASE economy")

            await interaction.followup.send(
                f"✅ Cleaned up {deleted_count} former members from the database!",
                ephemeral=True
            )

        elif command.value == "reset":
            if member is None:
                return await interaction.response.send_message(
                    "⚠️ Please select the member whose data you want to reset.",
                    ephemeral=True
                )

            if reset_type is None:
                return await interaction.response.send_message(
                    "⚠️ Please choose what type of reset you want to perform.",
                    ephemeral=True
                )

            if reset_type.value == "xp":
                await interaction.response.send_message(
                    content=(
                        f"⚠️ Reset **XP and Level only** for {member.mention}?\n"
                        f"💰 Stardust, inventory, pets, profile data, and other progress "
                        f"will remain untouched."
                    ),
                    view=ResetConfirm(self, member, interaction.user.id),
                    ephemeral=True
                )

            elif reset_type.value == "all":
                await interaction.response.send_message(
                    content=(
                        f"☢️ **DANGER — COMPLETE ACCOUNT WIPE**\n\n"
                        f"This will permanently delete **ALL Enceladus data** for "
                        f"{member.mention}, including XP, Level, Stardust, profile data, "
                        f"inventory, and pets. This is a **dangerous** operation and "
                        f"**irreversible!**\n\n"
                        f"Are you ***absolutely*** sure?"
                    ),
                    view=FullResetConfirm(self, member, interaction.user.id),
                    ephemeral=True
                )

        elif command.value == "font_preview_setup":
            leveling_cog = self.bot.get_cog("Leveling")

            if leveling_cog is None:
                return await interaction.response.send_message(
                    "❌ The leveling system is currently unavailable.",
                    ephemeral=True
                )

            embed = discord.Embed(
                title="Rank Card Font Previewer! 🌠",
                description=(
                    "Use the dropdown menu below to test out any of our custom "
                    "fonts available! It will generate a private preview card "
                    "just for you so you can see how your name and levels look "
                    "before choosing."
                ),
                color=discord.Color.purple()
            )

            await interaction.channel.send(
                embed=embed,
                view=FontView(leveling_cog)
            )

            await interaction.response.send_message(
                "✅ Font preview menu deployed!",
                ephemeral=True
            )

        elif command.value == "sendverifypanel":
            moderation_cog = self.bot.get_cog("Moderation")

            if moderation_cog is None:
                return await interaction.response.send_message(
                    "❌ The moderation system is currently unavailable.",
                    ephemeral=True
                )

            embed = discord.Embed(
                title="🔒 Server Verification",
                description=(
                    "To gain access to The Cosmic Lair, click the button below.\n\n"
                    "I, Enceladus, will DM you a code. Return here and type "
                    "`-verifycode <YOUR-CODE>` to verify."
                ),
                color=discord.Color.blurple()
            )

            await interaction.channel.send(
                embed=embed,
                view=VerifyView(moderation_cog)
            )

            await interaction.response.send_message(
                "✅ Server verification panel deployed!",
                ephemeral=True
            )

        elif command.value == "sendverificationpanel":
            verification_cog = self.bot.get_cog("Verification")

            if verification_cog is None:
                return await interaction.response.send_message(
                    "❌ The verification system is currently unavailable.",
                    ephemeral=True
                )

            embed = discord.Embed(
                title="🔞 Verification Center",
                description=(
                    "Select the type of verification you want below.\n\n"
                    "Verification is manually reviewed by staff.\n"
                    "Please follow all instructions carefully!\n\n"
                    "**Please note: You must be level 10 (Stellar Specialist) or higher to apply for NSFW and NSFW+ access.**"
                ),
                color=discord.Color.red()
            )

            await interaction.channel.send(
                embed=embed,
                view=VerificationPanelView(verification_cog)
            )

            await interaction.response.send_message(
                "✅ NSFW verification panel deployed!",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Admin(bot))