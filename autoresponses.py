import discord
from discord.ext import commands
import random


AUTO_RESPONSES = {
    "good bot": [
        "Beep boop! 💜",
        "Cosmic appreciation detected! 🌌",
        "Thank youuu <3"
    ],

    "enceladus": [
        "You called? 🌠",
        "The stars are listening...",
        "Cosmic systems online ✨"
    ],

    "toaster": [
        "You called?",
        "I'm the toaster, I am here",
        "I'm here! Want a PopTart or somethin?"
    ],

    "toast": [
        "*Toaster noises*",
        "*DING*"
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
    "good night": "🌙"
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

        content = message.content.lower()

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