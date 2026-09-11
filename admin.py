import discord
import aiosqlite
import datetime
import pytz
from discord import app_commands
from discord.ext import commands
from leveling import FontView
from moderation import VerifyView
from verification import VerificationPanelView


class SetXPModal(discord.ui.Modal):
    amount = discord.ui.TextInput(
        label="XP Amount",
        placeholder="Enter the XP amount to set...",
        required=True
    )

    def __init__(self, admin_cog, member):
        super().__init__(title="Set Member XP")
        self.admin_cog = admin_cog
        self.member = member

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount.value)
            if amount < 0:
                return await interaction.response.send_message(
                    "⚠️ XP cannot be negative.",
                    ephemeral=True
                )
        except ValueError:
            return await interaction.response.send_message(
                "⚠️ Please enter a valid whole number for XP.",
                ephemeral=True
            )

        leveling_cog = self.admin_cog.bot.get_cog("Leveling")
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
                (self.member.id, amount, temp_level)
            )
            await db.commit()

        await leveling_cog._update_member_roles(self.member, temp_level)

        await interaction.response.send_message(
            f"✅ Set {self.member.name}'s XP to {amount} "
            f"(Level {temp_level}).",
            ephemeral=True
        )


class SetXPView(discord.ui.View):
    def __init__(self, admin_cog):
        super().__init__(timeout=120)
        self.admin_cog = admin_cog

        self.member_select = discord.ui.UserSelect(
            placeholder="Select the member...",
            min_values=1,
            max_values=1
        )
        self.member_select.callback = self.member_selected
        self.add_item(self.member_select)

    async def member_selected(self, interaction: discord.Interaction):
        member = self.member_select.values[0]
        await interaction.response.send_modal(
            SetXPModal(self.admin_cog, member)
        )


class SetLevelModal(discord.ui.Modal):
    level = discord.ui.TextInput(
        label="Level",
        placeholder="Enter the level to set...",
        required=True
    )

    def __init__(self, admin_cog, member):
        super().__init__(title="Set Member Level")
        self.admin_cog = admin_cog
        self.member = member

    async def on_submit(self, interaction: discord.Interaction):
        try:
            level = int(self.level.value)
            if level < 0:
                return await interaction.response.send_message(
                    "⚠️ Level cannot be negative.",
                    ephemeral=True
                )
        except ValueError:
            return await interaction.response.send_message(
                "⚠️ Please enter a valid whole number for level.",
                ephemeral=True
            )

        leveling_cog = self.admin_cog.bot.get_cog("Leveling")
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
                (self.member.id, new_xp, level)
            )
            await db.commit()

        await leveling_cog._update_member_roles(self.member, level)

        await interaction.response.send_message(
            f"✅ Set {self.member.mention} to **Level {level}** "
            f"({new_xp} XP).",
            ephemeral=True
        )


class SetLevelView(discord.ui.View):
    def __init__(self, admin_cog):
        super().__init__(timeout=120)
        self.admin_cog = admin_cog

        self.member_select = discord.ui.UserSelect(
            placeholder="Select the member...",
            min_values=1,
            max_values=1
        )
        self.member_select.callback = self.member_selected
        self.add_item(self.member_select)

    async def member_selected(self, interaction: discord.Interaction):
        member = self.member_select.values[0]
        await interaction.response.send_modal(
            SetLevelModal(self.admin_cog, member)
        )


class AddXPModal(discord.ui.Modal):
    amount = discord.ui.TextInput(
        label="XP Amount",
        placeholder="Enter the XP amount to add...",
        required=True
    )

    def __init__(self, admin_cog, member):
        super().__init__(title="Add Member XP")
        self.admin_cog = admin_cog
        self.member = member

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount.value)
            if amount < 0:
                return await interaction.response.send_message(
                    "⚠️ XP cannot be negative.",
                    ephemeral=True
                )
        except ValueError:
            return await interaction.response.send_message(
                "⚠️ Please enter a valid whole number for XP.",
                ephemeral=True
            )

        leveling_cog = self.admin_cog.bot.get_cog("Leveling")
        if leveling_cog is None:
            return await interaction.response.send_message(
                "❌ The leveling system is currently unavailable.",
                ephemeral=True
            )

        await leveling_cog.add_xp(self.member, amount)

        async with aiosqlite.connect(leveling_cog.db_path) as db:
            async with db.execute(
                "SELECT xp, level FROM users WHERE user_id = ?",
                (self.member.id,)
            ) as cursor:
                result = await cursor.fetchone()

        if result:
            new_xp, new_level = result
            await interaction.response.send_message(
                f"✅ Added {amount} XP to {self.member.mention}! "
                f"They now have **{new_xp} XP** (Level {new_level}).",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"✅ Added {amount} XP to {self.member.mention}!",
                ephemeral=True
            )


class AddXPView(discord.ui.View):
    def __init__(self, admin_cog):
        super().__init__(timeout=120)
        self.admin_cog = admin_cog

        self.member_select = discord.ui.UserSelect(
            placeholder="Select the member...",
            min_values=1,
            max_values=1
        )
        self.member_select.callback = self.member_selected
        self.add_item(self.member_select)

    async def member_selected(self, interaction: discord.Interaction):
        member = self.member_select.values[0]
        await interaction.response.send_modal(
            AddXPModal(self.admin_cog, member)
        )


class FortuneStreakModal(discord.ui.Modal):
    streak = discord.ui.TextInput(
        label="Fortune Streak",
        placeholder="Enter the streak to set...",
        required=True
    )

    def __init__(self, admin_cog, member):
        super().__init__(title="Set Fortune Streak")
        self.admin_cog = admin_cog
        self.member = member

    async def on_submit(self, interaction: discord.Interaction):
        try:
            streak = int(self.streak.value)
            if streak < 0:
                return await interaction.response.send_message(
                    "⚠️ Streak cannot be negative.",
                    ephemeral=True
                )
        except ValueError:
            return await interaction.response.send_message(
                "⚠️ Please enter a valid whole number for the streak.",
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
                    self.member.id,
                    streak,
                    current_date_et
                )
            )
            await db.commit()

        await interaction.response.send_message(
            f"✅ Restored {self.member.mention}'s fortune streak to "
            f"**{streak} day{'s' if streak != 1 else ''}**.",
            ephemeral=True
        )


class FortuneStreakView(discord.ui.View):
    def __init__(self, admin_cog):
        super().__init__(timeout=120)
        self.admin_cog = admin_cog

        self.member_select = discord.ui.UserSelect(
            placeholder="Select the member...",
            min_values=1,
            max_values=1
        )
        self.member_select.callback = self.member_selected
        self.add_item(self.member_select)

    async def member_selected(self, interaction: discord.Interaction):
        member = self.member_select.values[0]
        await interaction.response.send_modal(
            FortuneStreakModal(self.admin_cog, member)
        )


class ResetTypeSelect(discord.ui.Select):
    def __init__(self, admin_cog, member, admin_user_id):
        self.admin_cog = admin_cog
        self.member = member
        self.admin_user_id = admin_user_id

        options = [
            discord.SelectOption(
                label="XP & Level Only",
                value="xp",
                emoji="📈",
                description="Reset XP and Level; keep economy/profile data."
            ),
            discord.SelectOption(
                label="Complete Account Wipe",
                value="all",
                emoji="☢️",
                description="Permanently delete all Enceladus data."
            ),
        ]

        super().__init__(
            placeholder="Choose the reset type...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.admin_user_id:
            await interaction.response.send_message(
                "❌ This reset panel belongs to another administrator.",
                ephemeral=True
            )
            return

        reset_type = self.values[0]

        if reset_type == "xp":
            await interaction.response.send_message(
                content=(
                    f"⚠️ Reset **XP and Level only** for "
                    f"{self.member.mention}?\n\n"
                    f"💰 Stardust, inventory, pets, profile data, and "
                    f"other progress will remain untouched."
                ),
                view=ResetConfirmationView(
                    self.admin_cog,
                    self.member,
                    self.admin_user_id,
                    "xp"
                ),
                ephemeral=True
            )

        else:
            await interaction.response.send_message(
                content=(
                    f"☢️ **DANGER — COMPLETE ACCOUNT WIPE**\n\n"
                    f"This will permanently delete **ALL Enceladus data** "
                    f"for {self.member.mention}, including XP, Level, "
                    f"Stardust, profile data, inventory, and pets.\n\n"
                    f"This is a **dangerous** operation and **irreversible!**\n\n"
                    f"Are you ***absolutely*** sure?"
                ),
                view=ResetConfirmationView(
                    self.admin_cog,
                    self.member,
                    self.admin_user_id,
                    "all"
                ),
                ephemeral=True
            )

class ResetConfirmationView(discord.ui.View):
    def __init__(self, admin_cog, member, admin_user_id, reset_type):
        super().__init__(timeout=30)
        self.admin_cog = admin_cog
        self.member = member
        self.admin_user_id = admin_user_id
        self.reset_type = reset_type

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.admin_user_id:
            await interaction.response.send_message(
                "❌ This reset confirmation belongs to another administrator.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Confirm Reset",
        style=discord.ButtonStyle.danger
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        # Acknowledge the interaction immediately.
        await interaction.response.defer()

        leveling_cog = self.admin_cog.bot.get_cog("Leveling")

        if leveling_cog is None:
            await interaction.edit_original_response(
                content="❌ The leveling system is currently unavailable.",
                view=None
            )
            return

        if self.reset_type == "xp":
            async with aiosqlite.connect(leveling_cog.db_path) as db:
                await db.execute(
                    """
                    UPDATE users
                    SET xp = 0,
                        level = 0
                    WHERE user_id = ?
                    """,
                    (self.member.id,)
                )
                await db.commit()

            await leveling_cog._update_member_roles(
                self.member,
                0
            )

            await interaction.edit_original_response(
                content=(
                    f"♻️ **{self.member.name}**'s XP and Level "
                    f"have been reset to 0."
                ),
                view=None
            )

        else:
            from database import ECONOMY_DB_NAME

            async with aiosqlite.connect(leveling_cog.db_path) as db:
                await db.execute(
                    "ATTACH DATABASE ? AS economy",
                    (ECONOMY_DB_NAME,)
                )

                await db.execute(
                    "DELETE FROM economy.inventory WHERE user_id = ?",
                    (self.member.id,)
                )

                await db.execute(
                    "DELETE FROM economy.pets WHERE user_id = ?",
                    (self.member.id,)
                )

                await db.execute(
                    "DELETE FROM economy.users WHERE user_id = ?",
                    (self.member.id,)
                )

                await db.execute(
                    "DELETE FROM main.users WHERE user_id = ?",
                    (self.member.id,)
                )

                await db.commit()
                await db.execute("DETACH DATABASE economy")

            await interaction.edit_original_response(
                content=(
                    f"☢️ **{self.member.name}**'s Enceladus account "
                    f"has been completely wiped.\n"
                    f"XP, Level, economy, profile data, inventory, "
                    f"and pets were deleted."
                ),
                view=None
            )

        self.stop()

    @discord.ui.button(
        label="Cancel",
        style=discord.ButtonStyle.secondary
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            content="❌ Reset cancelled.",
            view=None
        )
        self.stop()


class ResetTypeView(discord.ui.View):
    def __init__(self, admin_cog, member, admin_user_id):
        super().__init__(timeout=120)
        self.add_item(
            ResetTypeSelect(
                admin_cog,
                member,
                admin_user_id
            )
        )


class ResetMemberView(discord.ui.View):
    def __init__(self, admin_cog, admin_user_id):
        super().__init__(timeout=120)
        self.admin_cog = admin_cog
        self.admin_user_id = admin_user_id

        self.member_select = discord.ui.UserSelect(
            placeholder="Select the member to reset...",
            min_values=1,
            max_values=1
        )
        self.member_select.callback = self.member_selected
        self.add_item(self.member_select)

    async def member_selected(self, interaction: discord.Interaction):
        member = self.member_select.values[0]

        await interaction.response.send_message(
            "♻️ **Reset**\n\n"
            "Now choose what kind of reset you want to perform.",
            view=ResetTypeView(
                self.admin_cog,
                member,
                self.admin_user_id
            ),
            ephemeral=True
        )


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
        command="Choose an administrative action."
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

        elif command.value == "setfortunestreak":
            await interaction.response.send_message(
                "🔥 **Set Fortune Streak**\n\n"
                "Select the member whose fortune streak you want to set below.",
                view=FortuneStreakView(self),
                ephemeral=True
            )

        elif command.value == "setxp":
            await interaction.response.send_message(
                "📈 **Set XP**\n\n"
                "Select the member whose XP you want to change below.",
                view=SetXPView(self),
                ephemeral=True
            )

        elif command.value == "setlevel":
            await interaction.response.send_message(
                "⭐ **Set Level**\n\n"
                "Select the member whose level you want to change below.",
                view=SetLevelView(self),
                ephemeral=True
            )

        elif command.value == "addxp":
            await interaction.response.send_message(
                "➕ **Add XP**\n\n"
                "Select the member who should receive XP below.",
                view=AddXPView(self),
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
            await interaction.response.send_message(
                "♻️ **Reset**\n\n"
                "Select the member whose data you want to reset below.",
                view=ResetMemberView(self, interaction.user.id),
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
