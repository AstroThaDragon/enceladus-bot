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
        await interaction.response.defer()
        
        # New endpoint: Searching Submissions specifically. It's less likely to be blocked.
        search_url = "https://gamebanana.com/apiv11/Game/8694/Submissions"
        params = {
            "_sName": search_query,
            "_nPage": 1,
            "_perPage": 1
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.get(search_url, params=params, timeout=15) as response:
                    # Check if it's actually JSON before parsing
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" not in content_type:
                        return await interaction.followup.send("🚫 GameBanana's security wall is up. Please try again in a few minutes.")

                    data = await response.json()
                    
                    # This endpoint returns a list directly or a 'aRecords' key
                    results = data if isinstance(data, list) else data.get('aRecords', [])

                    if not results:
                        return await interaction.followup.send(f"❌ No FNF mods found for '{search_query}'.")

                    mod = results[0]
                    mod_id = mod.get('_idRow')
                    mod_name = mod.get('_sName')
                    
                    embed = discord.Embed(
                        title=f"🎤 Mod Found: {mod_name}",
                        url=f"https://gamebanana.com/mods/{mod_id}",
                        color=discord.Color.from_rgb(255, 0, 77)
                    )
                    
                    # Handle image - Submissions API uses _aPreviewMedia
                    preview = mod.get('_aPreviewMedia', {})
                    if preview and '_aImages' in preview:
                        img = preview['_aImages'][0]
                        embed.set_image(url=f"{img['_sBaseUrl']}/{img['_sFile']}")

                    view = discord.ui.View()
                    view.add_item(discord.ui.Button(label="View on GameBanana", url=f"https://gamebanana.com/mods/{mod_id}", emoji="🍌"))
                    
                    await interaction.followup.send(embed=embed, view=view)

            except Exception as e:
                print(f"DEBUG Error: {e}")
                await interaction.followup.send("🚫 The connection to GameBanana timed out.")

    @app_commands.command(name="fnfsong", description="Search for FNF music/audio!")
    async def fnfsong(self, interaction: discord.Interaction, song_name: str):
        # We'll use the same logic here as it's more robust
        await interaction.response.defer()
        search_url = "https://gamebanana.com/apiv11/Game/8694/Submissions"
        params = {"_sName": song_name, "_nPage": 1}
        headers = {"User-Agent": "Mozilla/5.0"}

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.get(search_url, params=params) as response:
                    if "application/json" not in response.headers.get("Content-Type", ""):
                        return await interaction.followup.send("🚫 Connection failed.")

                    data = await response.json()
                    results = data if isinstance(data, list) else data.get('aRecords', [])

                    if not results:
                        return await interaction.followup.send(f"❌ Couldn't find any songs named '{song_name}'.")

                    res = results[0]
                    mod_id = res['_idRow']
                    
                    embed = discord.Embed(
                        title=f"🎵 Result: {res['_sName']}",
                        description="Beep boop! Found a matching submission.",
                        url=f"https://gamebanana.com/mods/{mod_id}",
                        color=discord.Color.blue()
                    )
                    await interaction.followup.send(embed=embed)
            except Exception as e:
                await interaction.followup.send(f"🚫 Connection failed: {e}")

    @app_commands.command(name="echo", description="Have Enceladus repeat after you!")
    @app_commands.describe(message="What should Enceladus say?", channel="Optional: Which channel should it speak in?")
    async def echo(self, interaction: discord.Interaction, message: str, channel: discord.TextChannel = None):
        target_channel = channel or interaction.channel
        await target_channel.send(message)
        await interaction.response.send_message(f"Echoed into {target_channel.mention}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))