import discord
from discord.ext import commands
from discord import app_commands
import random
import aiohttp
import time
import asyncio

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
            title=f"🎤 Mods found for {search_query}!",
            description=f"Beep boop bop! Found a matching mod search for you! Click the button below to view the results on GameBanana!",
            color=discord.Color.from_rgb(255, 0, 77)
        )
        embed.set_thumbnail(url="https://asset.brandfetch.io/idR3RhicYy/idoLc-TS4z.png?updated=1715263930459")

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
            title=f"🎵 Songs found for {song_name}!",
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

    @commands.hybrid_command(name="slap", description="Slap a member with a random object!")
    async def slap(self, ctx, member: discord.Member):
        if member == self.bot.user:
            return await ctx.send(f"Nice try, {ctx.author.mention}, but I'm too fast for you! 😎")
        
        slap_objects = [
            "a large, smelly trout 🐟",
            "a massive rubber chicken 🐔",
            "a wet pool noodle 🏊",
            "a baguette 🥖",
            "a dictionary 📖",
            "their own hand ✋",
            "a keyboard ⌨️",
            "a tiny, squeaky hammer 🔨",
            "a giant foam finger 🖐️",
            "a fluffy pillow 🛏️",
            "a chancla 👡"
        ]
        
        random_object = random.choice(slap_objects)
        
        # Send the message
        await ctx.send(f"**{ctx.author.display_name}** slaps **{member.display_name}** across the face with {random_object}!")

    @commands.hybrid_command(name="coinflip", description="Consult the stars for a 50/50 outcome.")
    async def coinflip(self, ctx):
        """Flips a cosmic coin."""
        outcomes = [
            "✨ **SUPERNOVA**! The star explodes in brilliant light! (Heads)",
            "🕳️ **BLACK HOLE**! Light itself cannot escape the void. (Tails)"
        ]
        
        loading_msgs = [
            "Consulting the star charts...",
            "Checking the alignment of the planets...",
            "Peering into the cosmic void...",
            "Asking the moons of Saturn..."
        ]
        
        loading = random.choice(loading_msgs)
        result = random.choice(outcomes)
        
        await ctx.send(f"🌌 *{loading}*\n{result}")

    @commands.hybrid_command(name="blackhole", description="Suck a message into the void!")
    async def blackhole(self, ctx, text: str):
        distorted = " ".join(list(text)) # Spaced out
        await ctx.send(f"🕳️ **EVENT HORIZON REACHED**\n`{distorted}`\n*...aaaand it's gone forever.*")

    @commands.hybrid_command(name="hug", description="Give someone a warm, fuzzy hug!")
    async def hug(self, ctx, member: discord.Member):
        if member == ctx.author:
            return await ctx.send(f"You're hugging yourself? That's actually wholesome. {ctx.author.mention} gets a hug from... themselves! ❤️")
            
        await ctx.send(f"**{ctx.author.display_name}** gives **{member.display_name}** a big, warm hug!")

    @commands.hybrid_command(name="choose", description="Let the bot decide between multiple options!")
    async def choose(self, ctx, *, choices: str):
        options = [option.strip() for option in choices.split(",")]
        
        if len(options) < 2:
            return await ctx.send("Give me at least two options separated by a comma! (e.g., Pizza, Pasta)")
            
        await ctx.send(f"I've thought about it, and I choose: **{random.choice(options)}!**")

    @commands.hybrid_command(name="mock", description="mAkE yOuR tExT lOoK lIkE tHiS.")
    async def mock(self, ctx, *, text: str):
        mocked_text = "".join([char.upper() if i % 2 == 0 else char.lower() for i, char in enumerate(text)])
        
        emoji = "<:SpongeMock:1502200574945529896>" 
        
        await ctx.send(f"{emoji} <{ctx.author.display_name}> {mocked_text}")

    @commands.hybrid_command(name="roll", description="Roll a die (2-20 sides).")
    async def roll(self, ctx, sides: int = 6):
        """Rolls a die with a maximum of 20 sides."""
        if sides < 2:
            return await ctx.send("I can't roll a die with less than 2 sides, Einstein.")
        
        if sides > 20:
            return await ctx.send("Easy there, high roller! Max die size is **20**. 🎲")
        
        result = random.randint(1, sides)
        await ctx.send(f"🎲 **{ctx.author.display_name}** rolled a **D{sides}** and got: **{result}**")

    @commands.hybrid_command(name="spacefact", description="Pull real-time data on a random celestial body!")
    async def spacefact(self, ctx):
        url = "https://api.le-systeme-solaire.net/rest/bodies/"
        api_key = "99499df9-ede1-466d-8fcd-a7ee85201ffd"
        
        params = {"api_key": api_key} 

        await ctx.defer()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        body = random.choice(data['bodies'])
                        
                        name = body.get('englishName', 'Unknown Entity')
                        gravity = body.get('gravity', 'Unknown')
                        body_type = body.get('bodyType', 'Object')
                        
                        # --- Temperature Conversion ---
                        kelvin = body.get('avgTemp')
                        if kelvin and kelvin != 0:
                            celsius = round(kelvin - 273.15, 1)
                            temp_display = f"{kelvin} K ({celsius}°C)"
                        else:
                            temp_display = "Unknown"
                        
                        fact_msg = (
                            f"**Name:** {name}\n"
                            f"**Classification:** {body_type.capitalize()}\n"
                            f"**Surface Gravity:** {gravity} m/s²\n"
                            f"**Average Temp:** {temp_display}"
                        )

                        embed = discord.Embed(
                            title="🛰️ Deep Space Scan Result",
                            description=fact_msg,
                            color=discord.Color.blue()
                        )
                        embed.set_footer(text="Enceladus Station | Solar System Data")
                        
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send("📡 The API uplink rejected our key or is down.")
        except Exception as e:
            print(f"Space Error: {e}")
            await ctx.send("🌌 Something went wrong in the asteroid belt.")

async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))