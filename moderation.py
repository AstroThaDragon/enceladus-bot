import random
import string
import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio
import aiosqlite

MIN_ACCOUNT_AGE_DAYS = 30

VERIFY_CHANNEL_ID = 1296962529989361685
VERIFY_LOG_CHANNEL_ID = 1352834838478061608

UNVERIFIED_ROLE_ID = 1296962528546521130
VERIFIED_ROLE_ID = 593723369422192661

MOD_LOG_CHANNEL_ID = 1352095872812318760

VERIFICATION_DB_PATH = "/app/data/verification.db"


pending_codes = {}


def generate_code():
    letters = ''.join(random.choices(string.ascii_uppercase, k=4))
    numbers = ''.join(random.choices(string.digits, k=3))
    return f"{letters}-{numbers}"

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

        await interaction.response.send_message(
            "✅ I sent you a verification code in DMs!\n\n"
            "Once you receive it, return here and type:\n"
            "`-verifycode YOUR-CODE`\n\n"
            "Example:\n"
            "`-verifycode STAR-482`",
            ephemeral=True
        )


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(VerifyView(self))

        self.bot.loop.create_task(
            self.setup_verification_db()
        )

    async def setup_verification_db(self):
        async with aiosqlite.connect(VERIFICATION_DB_PATH) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS verification_strikes (
                    user_id INTEGER PRIMARY KEY,
                    strikes INTEGER DEFAULT 0
                )
                """
            )

            await db.commit()

    async def add_verification_strike(self, user_id):
        async with aiosqlite.connect(VERIFICATION_DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO verification_strikes (user_id, strikes)
                VALUES (?, 1)
                ON CONFLICT(user_id)
                DO UPDATE SET strikes = strikes + 1
                """,
                (user_id,)
            )

            async with db.execute(
                "SELECT strikes FROM verification_strikes WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()

            await db.commit()

        return row[0] if row else 1

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

    @commands.Cog.listener()
    async def on_member_join(self, member):

        account_age = discord.utils.utcnow() - member.created_at

        if account_age.days < MIN_ACCOUNT_AGE_DAYS:
            try:
                await member.send(
                    f"⚠️ You were removed from **{member.guild.name}** because your Discord account is less than "
                    f"**{MIN_ACCOUNT_AGE_DAYS} days old**.\n\n"
                    "This is an automatic safety measure to protect the server from raids, spam, scams, and throwaway accounts.\n\n"
                    "You may try joining again once your account is old enough. If you are **not** a bot, you can contact 'astrothadragon' and continue from there."
                )
            except discord.Forbidden:
                pass

            await member.kick(
                reason=f"Account younger than {MIN_ACCOUNT_AGE_DAYS} days."
            )

            return

        await asyncio.sleep(1800)  # 30 minutes

        guild = member.guild
        unverified_role = guild.get_role(UNVERIFIED_ROLE_ID)

        try:
            member = await guild.fetch_member(member.id)
        except discord.NotFound:
            return

        if not unverified_role or unverified_role not in member.roles:
            return

        strikes = await self.add_verification_strike(member.id)

        if strikes >= 3:
            action_text = (
                "🚫 You have reached the maximum number of verification strikes and have been banned from the server.\n\n"
                "If you believe this was a mistake, you may appeal by contacting the server owner at 'astrothadragon.'"
            )
        else:
            action_text = (
                "You may rejoin and try again, but repeated missed verifications will lead to a ban."
            )

        try:
            await member.send(
                f"⚠️ You were removed from **{guild.name}** because you did not verify within 30 minutes.\n\n"
                f"Verification strike: **{strikes}/3**\n\n"
                f"{action_text}"
            )
        except discord.Forbidden:
            pass

        if strikes >= 3:
            await member.ban(
                reason="Reached 3/3 verification timeout strikes."
            )
        else:
            await member.kick(
                reason=f"Did not verify within 30 minutes. Verification strike {strikes}/3."
            )

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def sendverifypanel(self, ctx):
        embed = discord.Embed(
            title="🔒 Server Verification",
            description=(
                "To gain access to The Cosmic Lair, click the button below.\n\n"
                "I, Enceladus, will DM you a code. Return here and type `-verifycode <YOUR-CODE>` to verify."
            ),
            color=discord.Color.blurple()
        )

        await ctx.send(
            embed=embed,
            view=VerifyView(self)
        )

    @commands.command()
    async def verifycode(self, ctx, code: str):
        member = ctx.author
        correct_code = pending_codes.get(member.id)

        if not correct_code:
            return await ctx.send(
                "❌ You do not currently have an active verification code.",
                delete_after=10
            )

        if code.strip().upper() != correct_code:
            return await ctx.send(
                "❌ Incorrect verification code. Check your DMs and try again.",
                delete_after=10
            )

        guild = ctx.guild

        verified_role = guild.get_role(VERIFIED_ROLE_ID)
        unverified_role = guild.get_role(UNVERIFIED_ROLE_ID)

        if verified_role:
            await member.add_roles(verified_role)

        if unverified_role and unverified_role in member.roles:
            await member.remove_roles(unverified_role)

        pending_codes.pop(member.id, None)

        await ctx.message.delete()

        await ctx.send(
            f"✅ {member.mention}, you're verified! Welcome to The Cosmic Lair!",
            delete_after=10
        )

        log_channel = guild.get_channel(VERIFY_LOG_CHANNEL_ID)

        if log_channel:
            await log_channel.send(
                f"✅ {member.mention} passed verification."
            )

        try:
            await member.send(
                "✅ You have successfully verified in **The Cosmic Lair**!"
            )
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.channel.id != VERIFY_CHANNEL_ID:
            return

        await asyncio.sleep(5)

        try:
            await message.delete()
        except discord.Forbidden:
            pass
        except discord.NotFound:
            pass

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