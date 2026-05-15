import discord
from discord.ext import commands
from collections import defaultdict
import time


DM_LOG_CHANNEL_ID = 1352834838478061608  # staff/modmail channel

DM_COOLDOWN_SECONDS = 60
DM_MAX_MESSAGES = 3

dm_activity = defaultdict(list)

active_sessions = {}

SUPPORT_SESSION_SECONDS = 900  # 15 minutes

HELP_KEYWORDS = [
    "help",
    "support",
    "staff",
    "mod",
    "moderator",
    "report",
    "appeal",
    "appeals",
    "ban",
    "banned",
    "unban",
    "verification",
    "verify",
    "admin",
    "owner"
]

URGENT_KEYWORDS = [
    "raid",
    "scam",
    "threat",
    "dox",
    "doxx",
    "harass",
    "harassment"
]


class DMHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_rate_limited(self, user_id):
        now = time.time()

        recent_messages = [
            timestamp
            for timestamp in dm_activity[user_id]
            if now - timestamp < DM_COOLDOWN_SECONDS
        ]

        dm_activity[user_id] = recent_messages
        dm_activity[user_id].append(now)

        return len(dm_activity[user_id]) > DM_MAX_MESSAGES

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.guild is not None:
            return

        user = message.author
        content = message.content or ""
        lowered = content.lower()

        now = time.time()

        session_active = (
            user.id in active_sessions
            and now - active_sessions[user.id] < SUPPORT_SESSION_SECONDS
        )

        if session_active:
            active_sessions[user.id] = now

        if self.is_rate_limited(user.id):
            try:
                await user.send(
                    "⚠️ Please slow down a little. Your messages are still important, but I need a moment to process them!"
                )
            except discord.Forbidden:
                pass

            return

        log_channel = self.bot.get_channel(DM_LOG_CHANNEL_ID)

        should_forward = (
            session_active
            or any(word in lowered for word in HELP_KEYWORDS)
            or any(word in lowered for word in URGENT_KEYWORDS)
            or any(word in lowered for word in ["appeal", "appeals", "ban", "banned", "unban"])
        )

        if should_forward and log_channel:
            embed = discord.Embed(
                title="📨 New DM to Enceladus",
                color=discord.Color.blurple(),
                timestamp=discord.utils.utcnow()
            )

            embed.add_field(
                name="User",
                value=f"{user.mention} (`{user.id}`)",
                inline=False
            )

            if content:
                embed.add_field(
                    name="Message",
                    value=content[:1000],
                    inline=False
                )

            if message.attachments:
                attachments = "\n".join(a.url for a in message.attachments)
                embed.add_field(
                    name="Attachments",
                    value=attachments[:1000],
                    inline=False
                )

            if any(word in lowered for word in URGENT_KEYWORDS):
                embed.title = "🚨 Urgent DM to Enceladus"
                embed.color = discord.Color.red()

            await log_channel.send(embed=embed)

        if session_active:
            await user.send(
                "🌌 Added to your active support session. Your message has been forwarded to staff."
            )

        elif any(word in lowered for word in ["appeal", "appeals", "ban", "banned", "unban"]):
            active_sessions[user.id] = time.time()
            await user.send(
                "🌌 If this is about a ban or verification appeal, please reply here with:\n\n"
                "• Your Discord username\n"
                "• Why you were removed or banned\n"
                "• Any relevant screenshots/details\n"
                "• Whether this was related to verification, account age, or timeout strikes\n\n"
                "Your messages here will be forwarded to staff for the next 15 minutes."
            )

        elif any(word in lowered for word in HELP_KEYWORDS):
            active_sessions[user.id] = time.time()
            await user.send(
                "🌌 Thanks for reaching out. Your message has been forwarded to staff.\n\n"
                "If this is about verification, appeals, reports, or server support, please include as much detail as you can. Your messages here will be forwarded to staff for the next 15 minutes."
            )

        elif any(word in lowered for word in URGENT_KEYWORDS):
            active_sessions[user.id] = time.time()
            await user.send(
                "🚨 Your message looks urgent, so it has been forwarded to staff right away.\n\n"
                "Please stay safe and include any extra details that may help. Your messages here will be forwarded to staff for the next 15 minutes."
            )
            
        else:
            await user.send(
                "🌌 Hello! Message received!\n\n"
                "If you need help, reports, appeals, bans, or verification support, please say that clearly so I can forward it to staff."
            )

async def setup(bot):
    await bot.add_cog(DMHandler(bot))