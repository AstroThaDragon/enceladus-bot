import discord
from discord.ext import commands
from discord.ui import View, Select, Button, Modal, TextInput


VERIFICATION_CHANNEL_ID = 1297033393313288263
VERIFICATION_LOG_CHANNEL_ID = 1352834838478061608
PENDING_VERIFICATION_ROLE_ID = 1504001672576241665

VERIFICATION_TEAM_ROLE_ID = 1502764416356319413
OWNER_ID = 395453475284320268
ADMIN_ROLE_ID = 593718477831929858

ROLE_18_VERIFIED = 1353561740238913636
ROLE_NSFW = 593907668515815424
ROLE_NSFW_PLUS = 935884854753624115

APPLICATION_TYPES = {
    "18plus": {
        "label": "18+ Verification",
        "roles": [
            ROLE_18_VERIFIED
        ]
    },

    "nsfw": {
        "label": "NSFW Access",
        "roles": [
            ROLE_18_VERIFIED,
            ROLE_NSFW
        ]
    },

    "nsfw_plus": {
        "label": "NSFW+ Access",
        "roles": [
            ROLE_18_VERIFIED,
            ROLE_NSFW,
            ROLE_NSFW_PLUS
        ]
    }
}

class ReasonModal(Modal):
    def __init__(self, cog, member, application_key, approved):
        super().__init__(
            title="Verification Reason"
        )

        self.cog = cog
        self.member = member
        self.application_key = application_key
        self.approved = approved

        self.reason = TextInput(
            label="Reason",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )

        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.finish_verification(
            interaction=interaction,
            member=self.member,
            application_key=self.application_key,
            approved=self.approved,
            reason=self.reason.value
        )

class VerificationReviewView(View):
    def __init__(self, cog, member, application_key):
        super().__init__(timeout=None)

        self.cog = cog
        self.member = member
        self.application_key = application_key

    @discord.ui.button(
        label="Accept",
        style=discord.ButtonStyle.success,
        emoji="✅"
    )
    async def accept_button(self, interaction, button):
        await self.cog.finish_verification(
            interaction=interaction,
            member=self.member,
            application_key=self.application_key,
            approved=True,
            reason=None
        )

    @discord.ui.button(
        label="Accept w/ Reason",
        style=discord.ButtonStyle.success,
        emoji="📝"
    )
    async def accept_reason_button(self, interaction, button):
        await interaction.response.send_modal(
            ReasonModal(
                self.cog,
                self.member,
                self.application_key,
                True
            )
        )

    @discord.ui.button(
        label="Deny",
        style=discord.ButtonStyle.danger,
        emoji="❌"
    )
    async def deny_button(self, interaction, button):
        await self.cog.finish_verification(
            interaction=interaction,
            member=self.member,
            application_key=self.application_key,
            approved=False,
            reason=None
        )

    @discord.ui.button(
        label="Deny w/ Reason",
        style=discord.ButtonStyle.danger,
        emoji="📝"
    )
    async def deny_reason_button(self, interaction, button):
        await interaction.response.send_modal(
            ReasonModal(
                self.cog,
                self.member,
                self.application_key,
                False
            )
        )

class VerificationDropdown(Select):
    def __init__(self, cog):
        self.cog = cog

        options = [
            discord.SelectOption(
                label="18+ Verified",
                description="Gain the 18+ verified role.",
                emoji="🔞",
                value="18plus"
            ),
            discord.SelectOption(
                label="NSFW Access",
                description="Gain access to NSFW channels.",
                emoji="🌶️",
                value="nsfw"
            ),
            discord.SelectOption(
                label="NSFW+ Access",
                description="Gain access to 'spicier' NSFW channels.",
                emoji="🔥",
                value="nsfw_plus"
            )
        ]

        super().__init__(
            placeholder="Choose a verification type...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="verification_dropdown"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        member = interaction.user

        pending_role = guild.get_role(PENDING_VERIFICATION_ROLE_ID)

        if pending_role:
            await member.add_roles(pending_role)

        application_key = self.values[0]
        application_name = APPLICATION_TYPES[application_key]["label"]

        verification_channel = guild.get_channel(VERIFICATION_CHANNEL_ID)

        request_message = await verification_channel.send(
            f"<@&{VERIFICATION_TEAM_ROLE_ID}> <@{OWNER_ID}> <@&{ADMIN_ROLE_ID}>\n"
            f"**New Verification Request**\n\n"
            f"**User:** {member.mention}\n"
            f"**Application:** {application_name}\n\n"
            f"Open the attached thread to review this request."
        )

        safe_name = member.display_name.lower().replace(" ", "-")
        thread = await request_message.create_thread(
            name=f"verification-{safe_name}",
            auto_archive_duration=1440
        )

        await thread.add_user(member)

        await interaction.followup.send(
            f"✅ Your verification thread has been created. A staff member will be with you shortly: {thread.mention}",
            ephemeral=True
        )

        try:
            await member.send(
                f"✅ Your **{application_name}** request has been opened in **{guild.name}**.\n\n"
                f"Please continue in your verification thread here: {thread.mention}\n\n"
                "A verification team member will review your request as soon as possible."
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "⚠️ I couldn't DM you. Please check your Discord privacy settings, but your verification thread was still created.",
                ephemeral=True
            )
        except Exception as e:
            print(f"Verification DM failed: {e}")

        await thread.send(
            f"Welcome {member.mention}!\n\n"
            f"Please answer the questions below and upload your verification images here.\n\n"
            f"⚠️ **Cover sensitive information. Only DOB and photo should remain visible!**"
        )

        questions = [
            "1. Are you 18 years or older?",
            "2. Have you read our server rules?",
            (
                "3. Please provide a valid form of ID for verification, such as an ID, driver's license, "
                "passport, or another document that clearly shows your age and photo.\n\n"
                "Make sure your DOB and photo are visible. Take a selfie holding the ID near your face, "
                "and also hold a piece of paper with your current Discord username written on it. "
                "This helps confirm the photo belongs to you and was not taken from somewhere online.\n\n"
                "We do **NOT** allow ID numbers, addresses, or other sensitive details to be shown for your safety. "
                "Please edit or cover those details before uploading.\n\n"
                "If you do not agree to this process, please cancel the application now.\n\n"
                "-# *(The ID photo process is reviewed manually by staff for safety reasons. We do **not** keep photos on file; they are removed after acceptance or denial.)*"
            ),
            "4. Please upload your verification images here. These are reviewed by our staff team, not by a bot."
        ]

        await thread.send("\n".join(questions))

        await thread.send(
            "Staff review controls:",
            view=VerificationReviewView(
                self.cog,
                member,
                application_key
            )
        )

class VerificationPanelView(View):
    def __init__(self, cog):
        super().__init__(timeout=None)

        self.add_item(
            VerificationDropdown(cog)
        )

class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.bot.add_view(
            VerificationPanelView(self)
        )

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def sendverificationpanel(self, ctx):
        embed = discord.Embed(
            title="🔞 Verification Center",
            description=(
                "Select the type of verification you want below.\n\n"
                "Verification is manually reviewed by staff.\n"
                "Please follow all instructions carefully."
            ),
            color=discord.Color.red()
        )

        await ctx.send(
            embed=embed,
            view=VerificationPanelView(self)
        )

    async def finish_verification(
        self,
        interaction,
        member,
        application_key,
        approved,
        reason
    ):

        guild = interaction.guild

        log_channel = guild.get_channel(
            VERIFICATION_LOG_CHANNEL_ID
        )

        thread = interaction.channel

        if approved:
            roles_to_add = APPLICATION_TYPES[
                application_key
            ]["roles"]

            roles = []

            for role_id in roles_to_add:
                role = guild.get_role(role_id)

                if role:
                    roles.append(role)

            if roles:
                await member.add_roles(*roles)

            message = (
                f"✅ You have been approved for **{APPLICATION_TYPES[application_key]['label']}**."
            )

            if reason:
                message += f"\n\nReason:\n{reason}"

            try:
                await member.send(message)
            except:
                pass

            await interaction.response.send_message(
                f"✅ {member.mention} approved.")

            await log_channel.send(
                f"✅ {member.mention} approved for **{APPLICATION_TYPES[application_key]['label']}**"
            )

        else:
            message = (
                f"❌ Your verification request for **{APPLICATION_TYPES[application_key]['label']}** was denied."
            )

            if reason:
                message += f"\n\nReason:\n{reason}"

            try:
                await member.send(message)
            except:
                pass

            await interaction.response.send_message(
                f"❌ {member.mention} denied."
            )

            await log_channel.send(
                f"❌ {member.mention} denied for **{APPLICATION_TYPES[application_key]['label']}**"
            )

        member = await guild.fetch_member(member.id)
        pending_role = guild.get_role(PENDING_VERIFICATION_ROLE_ID)

        if pending_role and pending_role in member.roles:
            await member.remove_roles(pending_role)

        await thread.edit(
            archived=True,
            locked=True
        )

async def setup(bot):
    await bot.add_cog(Verification(bot))