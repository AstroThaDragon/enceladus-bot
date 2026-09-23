import random
import string
import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import asyncio
import aiosqlite
from datetime import datetime, timedelta, timezone

SPOILER_REQUIRED_CHANNELS = {
    1519740977865162772 # selfies channel
}

MIN_ACCOUNT_AGE_DAYS = 30

# Automatically ban known repeat-name accounts on join.
# Numbers, underscores, spaces, punctuation, and other symbols are ignored.
NAME_BAN_PATTERNS = {
    "edeneva",
}


def normalize_name_for_ban(name):
    return "".join(char.lower() for char in name if char.isalnum())

VERIFY_CHANNEL_ID = 1296962529989361685
VERIFY_LOG_CHANNEL_ID = 1352834838478061608

UNVERIFIED_ROLE_ID = 1296962528546521130
VERIFIED_ROLE_ID = 593723369422192661

MOD_LOG_CHANNEL_ID = 1352095872812318760

VERIFY_MESSAGE_EXEMPT_ROLE_IDS = [
    891356074689560626,  # Owner
]

VERIFICATION_DB_PATH = "/app/data/verification.db"


pending_codes = {}


def generate_code():
    letter_count = random.randint(4, 8)
    number_count = random.randint(3, 6)
    letters = ''.join(random.choices(string.ascii_uppercase, k=letter_count))
    numbers = ''.join(random.choices(string.digits, k=number_count))
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

        # Keep the verification code persistent so a bot restart does not
        # invalidate an otherwise active verification. Reuse an existing
        # code when the button is clicked multiple times.
        async with self.cog.verification_lock:
            async with aiosqlite.connect(VERIFICATION_DB_PATH) as db:
                async with db.execute(
                    "SELECT code FROM pending_verifications WHERE user_id = ?",
                    (member.id,)
                ) as cursor:
                    row = await cursor.fetchone()

                code = row[0] if row and row[0] else generate_code()

                if row:
                    await db.execute(
                        "UPDATE pending_verifications SET code = ? WHERE user_id = ?",
                        (code, member.id)
                    )
                else:
                    await db.execute(
                        "INSERT INTO pending_verifications (user_id, code) VALUES (?, ?)",
                        (member.id, code)
                    )

                await db.commit()

            pending_codes[member.id] = code

        try:
            await member.send(
                f"🔒 Your verification code for **{interaction.guild.name}** is:\n\n"
                f"**`{code}`**\n\n"
                "Go back to the server and enter this code."
            )
        except discord.Forbidden:
            pending_codes.pop(member.id, None)
            return await interaction.response.send_message(
                "⚠️ **DM Delivery Failed!**\n"
                "I couldn't send you a verification code because your Direct Messages are disabled for this server.\n\n"
                "**How to fix:**\n"
                "1. Right-click or tap the server icon / header (**The Cosmic Lair**).\n"
                "2. Go to **Privacy Settings**.\n"
                "3. Enable **Direct Messages**.\n"
                "4. Click the **Verify** button again!",
                delete_after=10
            )

        await interaction.response.send_message(
            "✅ I sent you a verification code in DMs!\n\n"
            "Once you receive it, return here and type:\n"
            "`-verifycode YOUR-CODE`",
            delete_after=10
        )


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(VerifyView(self))
        self.verification_lock = asyncio.Lock()

    async def cog_load(self):
        # Discord.py awaits cog_load before the cog is considered loaded, so
        # the database is guaranteed to exist before the verification loop or
        # member events can use it.
        await self.setup_verification_db()
        self.check_pending_verifications.start()  # pyright: ignore[reportAttributeAccessIssue]

    def cog_unload(self):
        self.check_pending_verifications.cancel()  # pyright: ignore[reportAttributeAccessIssue]

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

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_verifications (
                    user_id INTEGER PRIMARY KEY,
                    join_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    code TEXT
                )
                """
            )

            # Migrate existing databases created before persistent verification
            # codes were added. SQLite raises OperationalError when the column
            # already exists, which is safe to ignore here.
            try:
                await db.execute(
                    "ALTER TABLE pending_verifications ADD COLUMN code TEXT"
                )
            except aiosqlite.OperationalError:
                pass

            await db.commit()

    async def get_channel_safe(self, channel_id):
        channel = self.bot.get_channel(channel_id)
        if channel:
            return channel

        try:
            return await self.bot.fetch_channel(channel_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None

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
        staff_channel = await self.get_channel_safe(1352834838478061608)

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

        # Catch known repeat-name accounts immediately on join.
        # This intentionally checks both the Discord username and display name
        # so added numbers/symbols do not bypass the filter.
        normalized_names = {
            normalize_name_for_ban(member.name),
            normalize_name_for_ban(member.display_name),
        }

        matched_pattern = next(
            (
                pattern
                for pattern in NAME_BAN_PATTERNS
                if normalize_name_for_ban(pattern) in normalized_names
            ),
            None,
        )

        if matched_pattern:
            try:
                await member.send(
                    f"⚠️ You were banned from **{member.guild.name}** because your username/display name matched a blocked account pattern."
                )
            except discord.Forbidden:
                pass

            try:
                await member.ban(
                    reason=f"Automatic ban: matched blocked name pattern '{matched_pattern}'."
                )
            except (discord.Forbidden, discord.HTTPException) as e:
                print(f"[NAME BAN ERROR] Could not ban {member} ({member.id}): {e}")
                return

            log_channel = await self.get_channel_safe(MOD_LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(
                    title="🚫 Automatic Name-Pattern Ban",
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow(),
                )
                embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
                embed.add_field(name="Username", value=member.name, inline=True)
                embed.add_field(name="Display Name", value=member.display_name, inline=True)
                embed.add_field(name="Matched Pattern", value=f"`{matched_pattern}`", inline=False)
                await log_channel.send(embed=embed)

            return

        account_age = discord.utils.utcnow() - member.created_at

        if account_age.days < MIN_ACCOUNT_AGE_DAYS:
            try:
                await member.send(
                    f"⚠️ You were removed from **{member.guild.name}** because your Discord account is less than "
                    f"**{MIN_ACCOUNT_AGE_DAYS} days old**.\n\n"
                    "This is an automatic safety measure to protect the server from raids, spam, scams, and throwaway accounts.\n\n"
                    "You may try joining again once your account is old enough. If you believe this was a mistake, you can contact @Enceladus#0496, or 'astrothadragon' and continue from there."
                )
            except discord.Forbidden:
                pass

            try:
                await member.kick(
                    reason=f"Account younger than {MIN_ACCOUNT_AGE_DAYS} days."
                )
            except (discord.Forbidden, discord.HTTPException) as e:
                print(f"[ACCOUNT AGE KICK ERROR] Could not kick {member} ({member.id}): {e}")

            return

        # Save the new member to the database to start their 30-minute timer.
        # Do not overwrite an existing code if the join event is delivered twice.
        async with self.verification_lock:
            async with aiosqlite.connect(VERIFICATION_DB_PATH) as db:
                await db.execute(
                    "INSERT OR IGNORE INTO pending_verifications (user_id) VALUES (?)",
                    (member.id,)
                )
                await db.commit()

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
    async def verifycode(self, ctx, *, code: str):
        member = ctx.author

        # Recover the code from SQLite if the bot restarted since it was sent.
        correct_code = pending_codes.get(member.id)
        if not correct_code:
            async with self.verification_lock:
                async with aiosqlite.connect(VERIFICATION_DB_PATH) as db:
                    async with db.execute(
                        "SELECT code FROM pending_verifications WHERE user_id = ?",
                        (member.id,)
                    ) as cursor:
                        row = await cursor.fetchone()
                correct_code = row[0] if row and row[0] else None
                if correct_code:
                    pending_codes[member.id] = correct_code

        if not correct_code:
            return await ctx.send(
                "❌ You do not currently have an active verification code. Click the **Verify** button to generate one!\n"
                "-# *(If you already clicked it, make sure your server DMs are turned ON so Enceladus can message you)*",
                delete_after=10
            )

        cleaned_code = code.strip().upper()

        # Alert if they typed a space instead of a dash
        if " " in cleaned_code and "-" not in cleaned_code:
            return await ctx.send(
                f"⚠️ {member.mention}, make sure to use a dash (`-`) between letters and numbers, not a space!\n"
                f"Example: `-verifycode {cleaned_code.replace(' ', '-')}`",
                delete_after=10
            )

        if cleaned_code != correct_code:
            return await ctx.send(
                "❌ Incorrect verification code. Check your DMs and try again.",
                delete_after=10
            )

        guild = ctx.guild

        async with self.verification_lock:
            # Re-check the stored code while holding the lock so the timeout
            # checker cannot process the same pending verification at the same time.
            async with aiosqlite.connect(VERIFICATION_DB_PATH) as db:
                async with db.execute(
                    "SELECT code FROM pending_verifications WHERE user_id = ?",
                    (member.id,)
                ) as cursor:
                    row = await cursor.fetchone()

            stored_code = row[0] if row and row[0] else correct_code
            if stored_code != correct_code:
                return await ctx.send(
                    "❌ Your verification code is no longer active. Click the **Verify** button to generate a new one!",
                    delete_after=10
                )

            verified_role = guild.get_role(VERIFIED_ROLE_ID)
            unverified_role = guild.get_role(UNVERIFIED_ROLE_ID)

            if verified_role:
                await member.add_roles(verified_role)

            if unverified_role and unverified_role in member.roles:
                await member.remove_roles(unverified_role)

            # STOP THE TIMER regardless of whether the unverified role was present.
            async with aiosqlite.connect(VERIFICATION_DB_PATH) as db:
                await db.execute(
                    "DELETE FROM pending_verifications WHERE user_id = ?",
                    (member.id,)
                )
                await db.commit()

            pending_codes.pop(member.id, None)

        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        await ctx.send(
            f"✅ {member.mention}, you're verified! Welcome to The Cosmic Lair!",
            delete_after=10
        )

        log_channel = await self.get_channel_safe(VERIFY_LOG_CHANNEL_ID)

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

    @verifycode.error
    async def verifycode_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"⚠️ {ctx.author.mention}, you forgot to include your code!\n"
                f"Format: `-verifycode YOUR-CODE`",
                delete_after=10
            )

    @commands.Cog.listener()
    async def on_message(self, message):

        # Enforce spoilered images and videos in designated channels.
        if message.author.bot:
            return

        if message.channel.id in SPOILER_REQUIRED_CHANNELS:
            has_unspoilered_media = any(
                attachment.content_type
                and (
                    attachment.content_type.startswith("image/")
                    or attachment.content_type.startswith("video/")
                )
                and not attachment.is_spoiler()
                for attachment in message.attachments
            )

            if has_unspoilered_media:
                try:
                    await message.delete()
                except (discord.Forbidden, discord.NotFound):
                    return

                try:
                    await message.channel.send(
                        f"⚠️ {message.author.mention}, your message was removed "
                        f"because images and videos in this channel must be marked "
                        f"as spoilers.\n"
                        f"Please repost the photo/video with Discord's spoiler "
                        f"option enabled.",
                        delete_after=30
                    )
                except discord.Forbidden:
                    pass

                return

        if (
            message.channel.id != VERIFY_CHANNEL_ID
            or message.author.bot
        ):
            return

        if any(role.id in VERIFY_MESSAGE_EXEMPT_ROLE_IDS for role in message.author.roles):
            return

        content = message.content.strip()
        content_lower = content.lower()

        # Check for common verification command mistakes before deleting the message
        user_code = pending_codes.get(message.author.id)
        is_just_code = False

        if user_code and content.upper() == user_code:
            is_just_code = True
        else:
            # Check for variable-length code patterns (4-8 letters, dash, 3-6 digits)
            parts = content.split("-")
            if len(parts) == 2 and parts[0].isalpha() and parts[1].isdigit():
                if 4 <= len(parts[0]) <= 8 and 3 <= len(parts[1]) <= 6:
                    is_just_code = True

        # 1. Typed just the code without command prefix
        if is_just_code:
            await message.channel.send(
                f"⚠️ {message.author.mention}, you typed the code without the command!\n"
                f"Format: `-verifycode {content.upper()}`",
                delete_after=10
            )

        # 2. Forgot the '-' prefix (e.g., "verifycode COSMIC-91823")
        elif content_lower.startswith("verifycode"):
            await message.channel.send(
                f"⚠️ {message.author.mention}, don't forget the `-` at the start!\n"
                f"Format: `-{content}`",
                delete_after=10
            )

        # 3. Added spaces or hyphens into the command name (e.g., "-verify code")
        elif content_lower.startswith(("-verify code", "-verify-code", "verify-code", "verify code")):
            await message.channel.send(
                f"⚠️ {message.author.mention}, the command must be written as `-verifycode` (one word, no spaces).\n"
                f"Example: `-verifycode YOUR-CODE`",
                delete_after=10
            )

        await asyncio.sleep(5)

        try:
            await message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        # If the channel hasn't changed (e.g., they just muted/unmuted), ignore it
        if before.channel == after.channel:
            return

        log_channel = await self.get_channel_safe(MOD_LOG_CHANNEL_ID)

        if not log_channel:
            return

        if before.channel is None and after.channel is not None:
            title = "🎙️ Voice Joined"
            desc = f"{member.mention} joined {after.channel.mention}"
            color = discord.Color.green()

        elif before.channel is not None and after.channel is None:
            title = "🔇 Voice Left"
            desc = f"{member.mention} left {before.channel.mention}"
            color = discord.Color.red()

        elif before.channel is not None and after.channel is not None:
            title = "🔁 Voice Moved"
            desc = f"{member.mention} moved from {before.channel.mention} to {after.channel.mention}"
            color = discord.Color.orange()
        else:
            return

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
        log_channel = await self.get_channel_safe(MOD_LOG_CHANNEL_ID)

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
        log_channel = await self.get_channel_safe(MOD_LOG_CHANNEL_ID)

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
        log_channel = await self.get_channel_safe(MOD_LOG_CHANNEL_ID)

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

    @tasks.loop(minutes=2)
    async def check_pending_verifications(self):
        async with self.verification_lock:
            async with aiosqlite.connect(VERIFICATION_DB_PATH) as db:
                async with db.execute(
                    "SELECT user_id, join_time FROM pending_verifications"
                ) as cursor:
                    rows = await cursor.fetchall()

            for user_id, join_time_str in rows:
                try:
                    join_time = datetime.strptime(
                        join_time_str, "%Y-%m-%d %H:%M:%S"
                    ).replace(tzinfo=timezone.utc)
                except (TypeError, ValueError):
                    print(
                        f"[VERIFICATION DB ERROR] Invalid join time for user {user_id}: "
                        f"{join_time_str!r}"
                    )
                    continue

                if (datetime.now(timezone.utc) - join_time) <= timedelta(minutes=30):
                    continue

                for guild in self.bot.guilds:
                    member = guild.get_member(user_id)
                    if not member:
                        continue

                    unverified_role = guild.get_role(UNVERIFIED_ROLE_ID)
                    if not unverified_role or unverified_role not in member.roles:
                        continue

                    strikes = await self.add_verification_strike(member.id)

                    if strikes >= 3:
                        action_text = (
                            "🚫 You have reached the maximum number of verification strikes "
                            "and have been banned from the server.\n\n"
                            "If you believe this was a mistake, you may appeal by contacting "
                            "@Enceladus#0496, or the server owner at 'astrothadragon.'"
                        )
                    else:
                        action_text = (
                            "You may rejoin and try again, but repeated missed verifications "
                            "will lead to a ban."
                        )

                    try:
                        await member.send(
                            f"⚠️ You were removed from **{guild.name}** because you did not verify within 30 minutes.\n\n"
                            f"Verification strike: **{strikes}/3**\n\n"
                            f"{action_text}"
                        )
                    except discord.Forbidden:
                        pass

                    try:
                        if strikes >= 3:
                            await member.ban(
                                reason="Reached 3/3 verification timeout strikes."
                            )
                        else:
                            await member.kick(
                                reason=(
                                    f"Did not verify within 30 minutes. "
                                    f"Verification strike {strikes}/3."
                                )
                            )
                    except (discord.Forbidden, discord.HTTPException) as e:
                        print(
                            f"[VERIFICATION TIMEOUT ERROR] Could not remove {member} "
                            f"({member.id}): {e}"
                        )
                        # Keep the pending record so a transient Discord failure can
                        # be retried on the next checker run.
                        continue

                    # Only clear the pending record after the removal succeeded.
                    async with aiosqlite.connect(VERIFICATION_DB_PATH) as db:
                        await db.execute(
                            "DELETE FROM pending_verifications WHERE user_id = ?",
                            (user_id,)
                        )
                        await db.commit()

                    pending_codes.pop(user_id, None)
                    break

async def setup(bot):
    await bot.add_cog(Moderation(bot))