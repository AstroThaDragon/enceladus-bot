import discord
from discord.ext import commands
import random

IGNORED_CHANNEL_IDS = [
    593397821835575306,
    1117377155496673330,
    1117391981627318363,
    598883099987673088,
    1036594500916756490,
    593410829857325056,
    1440166194866028666,
    1036596295353245726,
    1117403991266041906,
    1496628909570265199
]

AUTO_RESPONSES = {
    "good bot": [
        "Beep boop! 💜",
        "Cosmic appreciation detected! 🌌",
        "Thank youuu <3"
    ],

    "enceladus": [
        "You called? 🌠",
        "The stars are listening.",
        "Cosmic systems online ✨"
    ],

    "toaster": [
        "You called?",
        "I'm the toaster, I am here",
        "I'm here! Want a PopTart or somethin?"
    ],

    "toast": [
        "*Toaster noises*",
        "*DING*",
        "Want toast? I gotchu"
    ]
}


AUTO_REACTIONS = {
    "dragon": "🐉",
    "moon": "🌙",
    "star": "⭐",
    "fortune": "🥠",
    "cosmic": "🌌",
    "void": "🕳️",
    "proot": "🍞",
    "toaster": "🍞",
    "morning": "👋",
    "good morning": "👋",
    "good night": "🌙",
    "goodnight": "🌙"
}


class AutoResponses(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        if not message.content:
            return
        
        if message.channel.id in IGNORED_CHANNEL_IDS:
            return

        content = message.content.lower()

        if (
            "tenor.com" in content
            or "giphy.com" in content
            or "gif" in content
        ):
            return

        # --- AUTO RESPONSES ---
        for trigger, responses in AUTO_RESPONSES.items():
            if trigger in content:
                try:
                    await message.channel.send(
                        random.choice(responses)
                    )
                except:
                    pass

                break

        # --- AUTO REACTIONS ---
        for trigger, emoji in AUTO_REACTIONS.items():
            if trigger in content:
                try:
                    await message.add_reaction(emoji)
                except:
                    pass


async def setup(bot):
    await bot.add_cog(AutoResponses(bot))