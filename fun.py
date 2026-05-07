import discord
from discord.ext import commands
from discord import app_commands
import random
import aiohttp

class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.responses = [
            "Maybe someday.",
            "Nothing.",
            "Neither.",
            "I don't think so.",
            "No.",
            "Yes.",
            "Try asking again.",
            "Nah, fam.",
            "The stars say... no.",
            "Absolutely not.",
            "Follow the stardust.",
            "Ask the protogen later.",
            "The answer is hidden in the void.",
            "The cosmic winds whisper... maybe.",
            "The universe is undecided on that one.",
            "Ask again when the moon is full.",
            "You can count on it, bru.",
            "Absolutely, my guy.",
            "Even I don't know that one... and I'm from the astral plane.",
            "Should go ask your mom about that one, ngl.",
            "Do you really want to know the answer? The truth can be harsh, my dude.",
            "The truth is out there...",
            "Do you kiss your mother with that mouth? Maybe rethink it, fam.",
            "You know it, I know it, we all know it. The answer is yes. Definitely yes.",
            "You got it, my guy.",
            "Why are you asking me that? That's a bit sus, ngl.",
            "Signs point to yes.",
            "Looks like a yes from here, brodie.",
            "I don't even have an answer for that one, wtf.",
            "Someday, somehow, somewhere...",
            "I asked my mom about that. She said no.",
            "I asked my mom about that. She said yes!",
            "You know what? I'm just gonna say yes to that one, why not?",
            "The astral relic is feeling generous today. Yes!"
        ]

    @app_commands.command(name="relic", description="Consult the Astral Relic for an answer to your questions!")
    async def relic(self, interaction: discord.Interaction, question: str):
        answer = random.choice(self.responses)
        
        message = (
            f"🔮 **The Astral Relic stirs...**\n"
            f"> {question}\n"
            f"**Answer:** {answer}"
        )
        
        await interaction.response.send_message(message)

    @app_commands.command(name="jokes", description="Get a random joke to brighten your day!")
    async def jokes(self, interaction: discord.Interaction):
        joke_list = [
            "Why don't scientists trust atoms? Because they make up everything!",
            "What do you call a fake noodle? An impasta!",
            "Why did the dragon get hired? He was really good at 'firing' people! 🐉",
            "How does a penguin build its house? Igloos it together!",
            "What do you call a skeleton who won't work? Lazy bones!",
            "Why are dragons such good storytellers? Because they always have a long tail!",
            "What is an astronaut's favorite key on the keyboard? The spacebar!",
            "I'm on a seafood diet. I see food, I eat it!",
            "What do you call a well-balanced horse? Stable!",
            "How do you make an eggroll? Push it!",
            "What do you call a pile of cats? A meow-ntain!",
            "Why don't they play poker in the jungle? Too many cheetahs.",
            "What kind of tea is hard to swallow? Realitea.",
            "RIP to boiling water. You will be mist.",
            "Knock-knock! - Who's there? - Boo. - Boo who? - Why are you crying??",
            "Knock-knock! - Who's there? - Spell - Spell who? - W-H-O.",
            "Why did the scarecrow win an award? Because he was outstanding in his field!"
        ]
        
        random_joke = random.choice(joke_list) 
        await interaction.response.send_message(f"**Here's a goofy joke for ya!:**\n{random_joke}")

    @app_commands.command(name="fnfmod", description="Search for a Friday Night Funkin' mod on GameBanana!")
    async def fnfmod(self, interaction: discord.Interaction, search_query: str):
        # Using the direct web search URL to bypass API blocks
        formatted_query = search_query.replace(" ", "+")
        web_search_url = f"https://gamebanana.com/mods/search?_sSearchString={formatted_query}&_idGameRow=8694"
        
        embed = discord.Embed(
            title=f"🎤 Mod Found: {search_query}",
            description=f"Beep boop bop! Found a matching mod search for you! Click the button below to view the results on GameBanana!",
            color=discord.Color.from_rgb(255, 0, 77)
        )
        embed.set_thumbnail(url="https://images.gamebanana.com/static/img/favicon/favicon.png")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="View on GameBanana", 
            url=web_search_url, 
            style=discord.ButtonStyle.link,
            emoji="🍌"
        ))

        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="fnfsong", description="Search for an FNF song on YouTube!")
    async def fnfsong(self, interaction: discord.Interaction, song_name: str):
        # We add 'FNF' to the query to make sure the results are relevant
        formatted_query = (song_name + " FNF song").replace(" ", "+")
        youtube_search_url = f"https://www.youtube.com/results?search_query={formatted_query}"
        
        embed = discord.Embed(
            title=f"🎵 Result: {song_name}",
            description="Beep boop bop! Found a matching song search for you! Click the button below to view the results on YouTube!",
            color=discord.Color.red() # Changed to Red to match YouTube's branding
        )
        # Using a YouTube icon for the thumbnail
        embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/e/ef/Youtube_logo.png")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="Listen on YouTube", 
            url=youtube_search_url, 
            style=discord.ButtonStyle.link, 
            emoji="🎧" 
        ))

        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="echo", description="Have Enceladus repeat after you!")
    @app_commands.describe(message="What should Enceladus say?", channel="Optional: Which channel should it speak in?")
    async def echo(self, interaction: discord.Interaction, message: str, channel: discord.TextChannel = None):
        target_channel = channel or interaction.channel
        await target_channel.send(message)
        await interaction.response.send_message(f"Echoed into {target_channel.mention}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))