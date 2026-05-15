import random
import string
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput


VERIFY_CHANNEL_ID = 1296962529989361685
VERIFY_LOG_CHANNEL_ID = 1352834838478061608

UNVERIFIED_ROLE_ID = 1296962528546521130
VERIFIED_ROLE_ID = 593723369422192661

MOD_LOG_CHANNEL_ID = 1352095872812318760


pending_codes = {}


def generate_code():
    letters = ''.join(random.choices(string.ascii_uppercase, k=4))
    numbers = ''.join(random.choices(string.digits, k=3))
    return f"{letters}-{numbers}"


class VerifyCodeModal(Modal):
    def __init__(self, cog, member):
        super().__init__(title="Enter Verification Code")

        self.cog = cog
        self.member = member

        self.code_input = TextInput(
            label="Verification Code",
            placeholder="Example: STAR-123",
            required=True,
            max_length=20
        )

        self.add_item(self.code_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.check_code(
            interaction,
            self.member,
            self.code_input.value
        )


class VerifyView(View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="Verify",
        style=discord.ButtonStyle.primary,
        emoji="🔒",
        custom_id="general_verify_button"
    )
    async def verify_button(self, interaction, button):
        member = interaction.user
        code = generate_code()

        pending_codes[member.id] = code

        try:
            await member.send(
                f"🔒 Your verification code for **{interaction.guild.name}** is:\n\n"
                f"**`{code}`**\n\n"
                "Go back to the server and enter this code."
            )
        except discord.Forbidden:
            return await interaction.response.send_message(
                "⚠️ I couldn't DM you. Please enable DMs from server members, then try again.",
                ephemeral=True
            )

        await interaction.response.send_modal(
            VerifyCodeModal(self.cog, member)
        )


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(VerifyView(self))

    @commands.command()
    async def qr(self, ctx, *, reason):
        staff_channel = self.bot.get_channel(1352834838478061608)

        if not staff_channel:
            return await ctx.send("⚠️ Staff report channel not found.")

        jump_url = f"https://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{ctx.message.id}"

        report_msg = (
            f"⚠️ **New Quick Report!**\n"
            f"**User:** {ctx.author.mention} used `-qr` in {ctx.channel.mention}\n"
            f"**Reason:** {reason}\n"
            f"🔗 [Jump to Message]({jump_url})"
        )

        await staff_channel.send(report_msg)

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        try:
            await ctx.author.send(
                "Your report has been sent to staff. Thank you for helping The Cosmic Lair stay positive! 🌌💜"
            )
        except discord.Forbidden:
            await ctx.send(
                "✅ Your report was sent, but I couldn't DM you.",
                delete_after=10
            )

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def sendverifypanel(self, ctx):
        embed = discord.Embed(
            title="🔒 Server Verification",
            description=(
                "To gain access to The Cosmic Lair, click the button below.\n\n"
                "Enceladus will DM you a code. Enter the code here to verify."
            ),
            color=discord.Color.blurple()
        )

        await ctx.send(
            embed=embed,
            view=VerifyView(self)
        )

    async def check_code(self, interaction, member, submitted_code):
        correct_code = pending_codes.get(member.id)

        if not correct_code:
            return await interaction.response.send_message(
                "❌ No verification code found. Please click Verify again.",
                ephemeral=True
            )

        if submitted_code.strip().upper() != correct_code:
            return await interaction.response.send_message(
                "❌ Incorrect code. Please check your DMs and try again.",
                ephemeral=True
            )

        guild = interaction.guild

        verified_role = guild.get_role(VERIFIED_ROLE_ID)
        unverified_role = guild.get_role(UNVERIFIED_ROLE_ID)

        if verified_role:
            await member.add_roles(verified_role)

        if unverified_role and unverified_role in member.roles:
            await member.remove_roles(unverified_role)

        pending_codes.pop(member.id, None)

        await interaction.response.send_message(
            "✅ You're verified! Welcome to The Cosmic Lair!",
            ephemeral=True
        )

        log_channel = guild.get_channel(VERIFY_LOG_CHANNEL_ID)

        if log_channel:
            await log_channel.send(
                f"✅ {member.mention} passed verification."
            )

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        log_channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)

        if not log_channel:
            return

        if before.channel == after.channel:
            return

        if before.channel is None and after.channel is not None:
            title = "🎙️ Voice Joined"
            desc = f"{member.mention} joined {after.channel.mention}"
            color = discord.Color.green()

        elif before.channel is not None and after.channel is None:
            title = "🔇 Voice Left"
            desc = f"{member.mention} left {before.channel.mention}"
            color = discord.Color.red()

        else:
            title = "🔁 Voice Moved"
            desc = f"{member.mention} moved from {before.channel.mention} to {after.channel.mention}"
            color = discord.Color.orange()

        embed = discord.Embed(
            title=title,
            description=desc,
            color=color,
            timestamp=discord.utils.utcnow()
        )

        embed.set_author(
            name=str(member),
            icon_url=member.display_avatar.url
        )

        embed.add_field(
            name="User ID",
            value=member.id,
            inline=False
        )

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        log_channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)

        if not log_channel:
            return

        embed = discord.Embed(
            title="🧵 Thread Created",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="Thread",
            value=thread.mention,
            inline=False
        )

        embed.add_field(
            name="Parent Channel",
            value=thread.parent.mention if thread.parent else "Unknown",
            inline=False
        )

        embed.add_field(
            name="Thread ID",
            value=thread.id,
            inline=False
        )

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread):
        log_channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)

        if not log_channel:
            return

        embed = discord.Embed(
            title="🗑️ Thread Deleted",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="Thread Name",
            value=thread.name,
            inline=False
        )

        embed.add_field(
            name="Parent Channel",
            value=thread.parent.mention if thread.parent else "Unknown",
            inline=False
        )

        embed.add_field(
            name="Thread ID",
            value=thread.id,
            inline=False
        )

        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_thread_update(self, before, after):
        log_channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)

        if not log_channel:
            return

        if before.archived != after.archived:

            status = "Archived" if after.archived else "Unarchived"

            color = (
                discord.Color.orange()
                if after.archived
                else discord.Color.green()
            )

            embed = discord.Embed(
                title=f"📦 Thread {status}",
                color=color,
                timestamp=discord.utils.utcnow()
            )

            embed.add_field(
                name="Thread",
                value=after.name,
                inline=False
            )

            embed.add_field(
                name="Parent Channel",
                value=after.parent.mention if after.parent else "Unknown",
                inline=False
            )

            embed.add_field(
                name="Thread ID",
                value=after.id,
                inline=False
            )

            await log_channel.send(embed=embed)

    async def create_thread_transcript(self, thread):
        messages = []

        async for message in thread.history(limit=None, oldest_first=True):
            content = message.content or ""

            if message.attachments:
                attachments = "\n".join(a.url for a in message.attachments)
                content += f"\n[Attachments]\n{attachments}"

            messages.append(
                f"[{message.created_at}] {message.author}: {content}"
            )

        transcript_text = "\n\n".join(messages)

        file_name = f"transcript-{thread.id}.txt"

        with open(file_name, "w", encoding="utf-8") as f:
            f.write(transcript_text)

        return file_name

async def setup(bot):
    await bot.add_cog(Moderation(bot))