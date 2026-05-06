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
        
        search_url = f"https://gamebanana.com/apiv11/Util/Search/Results?_sSearchString={search_query}&_nPage=1&_sModelName=Mod"
        
        # Upgraded headers to look like a standard Windows Chrome browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }

        async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as session:
            try:
                async with session.get(search_url) as response:
                    # Check if we actually got JSON back
                    if response.status == 200 and "application/json" in response.headers.get("Content-Type", ""):
                        data = await response.json()
                        
                        if not data.get('aResults'):
                            await interaction.followup.send(f"Skrrrrp. I couldn't find any mods for '{search_query}'.")
                            return

                        # Filter for FNF ID (8694)
                        results = data.get('aResults', [])
                        best_match = next((res for res in results if res.get('_idGameRow') == 8694), results[0])

                        mod_id = best_match['_idRow']
                        mod_name = best_match['_sName']
                        mod_url = f"https://gamebanana.com/mods/{mod_id}"
                        
                        view = discord.ui.View()
                        view.add_item(discord.ui.Button(label="Download on GameBanana!", url=mod_url, emoji="🎤"))

                        embed = discord.Embed(
                            title=f"🎤 Mod Found: {mod_name}",
                            description=f"Beep! I've found a match! Click the button below to see more.",
                            color=discord.Color.from_rgb(255, 0, 77)
                        )
                        
                        if '_aPreviewMedia' in best_match:
                            img_data = best_match['_aPreviewMedia']['_aImages'][0]
                            embed.set_image(url=f"{img_data['_sBaseUrl']}/{img_data['_sFile']}")

                        await interaction.followup.send(embed=embed, view=view)
                    else:
                        # If we get HTML instead of JSON, it means we're being blocked
                        await interaction.followup.send("GameBanana is blocking the connection. They think I'm a bot! Try again in a few minutes.")
            except Exception as e:
                await interaction.followup.send(f"The connection failed. Error: {e}")

    @app_commands.command(name="fnfsong", description="Get info on a specific FNF song!")
    async def fnfsong(self, interaction: discord.Interaction, song_name: str):
        await interaction.response.defer()
        
        search_url = f"https://gamebanana.com/apiv11/Util/Search/Results?_sSearchString={song_name}&_nPage=1&_sModelName=Mod"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }

        async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as session:
            try:
                async with session.get(search_url) as response:
                    if response.status == 200 and "application/json" in response.headers.get("Content-Type", ""):
                        data = await response.json()
                        
                        if not data.get('aResults'):
                            await interaction.followup.send(f"Skrrrrp. I couldn't find anything for '{song_name}'.")
                            return

                        results = data.get('aResults', [])
                        result = next((res for res in results if res.get('_idGameRow') == 8694), results[0])

                        name = result['_sName']
                        res_id = result['_idRow']
                        
                        embed = discord.Embed(
                            title=f"🎵 Song/Mod Info: {name}",
                            description=f"Beep! Found a match for **{song_name}**!",
                            color=discord.Color.from_rgb(255, 0, 77)
                        )
                        embed.add_field(name="Link", value=f"https://gamebanana.com/mods/{res_id}")
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.followup.send("I'm being blocked by the mod vault's security. Try again later!")
            except Exception as e:
                await interaction.followup.send(f"Search failed. Error: {e}")

    @app_commands.command(name="echo", description="Have Enceladus repeat after you!")
    @app_commands.describe(message="What should Enceladus say?", channel="Optional: Which channel should it speak in?")
    async def echo(self, interaction: discord.Interaction, message: str, channel: discord.TextChannel = None):
        target_channel = channel or interaction.channel
        await target_channel.send(message)
        await interaction.response.send_message(f"Echoed into {target_channel.mention}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))