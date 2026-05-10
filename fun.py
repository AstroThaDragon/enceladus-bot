import discord
from discord.ext import commands
from discord import app_commands
import random
import aiohttp
import time
import asyncio
import datetime
import pytz
import aiosqlite

class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot, db_path: str):
        self.bot = bot
        self.db_path = db_path
        
        # Initialize table with the necessary column
        # Note: Since __init__ cannot be async, we create a task to run the setup
        self.bot.loop.create_task(self.initialize_db())

    async def initialize_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    last_fortune_date TEXT
                )
            """)
            
            # Migrating existing tables that might be missing the column
            try:
                await db.execute("ALTER TABLE users ADD COLUMN last_fortune_date TEXT;")
            except:
                # Column already exists
                pass
                
            await db.commit()

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
            "Why are you asking me that? That's a bit sys, ngl.",
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
            "🐟 a large, smelly fish",
            "🐔 a rubber chicken",
            "🏊 a foam pool noodle",
            "🥖 a baguette",
            "📖 a dictionary",
            "✋ their own hand",
            "⌨️ a keyboard",
            "🔨 a tiny, squeaky hammer",
            "🖐️ a giant foam finger",
            "🛏️ a fluffy pillow",
            "👡 a chancla",
            "🍕 a slice of pizza",
            "🧀 a block of cheese",
            "🍌 a ripe banana",
            "🧻 a roll of toilet paper",
            "🧸 a teddy bear",
            "🥞 a pancake",
            "🍩 a glazed donut",
            "👜 a purse",
            "🦯 a cane"
        ]
        
        random_object = random.choice(slap_objects)
        
        await ctx.send(f"**{ctx.author.mention}** slaps **{member.mention}** across the face with {random_object}!")

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
            return await ctx.send(f"You're hugging yourself? That's actually wholesome. {ctx.author.mention} gets a hug from... themselves! 💜")
            
        await ctx.send(f"**{ctx.author.mention}** gives **{member.mention}** a big, warm hug! How sweet! 💜")

    @commands.hybrid_command(name="choose", description="Let the bot decide between multiple options! Use commas to separate choices!")
    async def choose(self, ctx, *, choices: str):
        options = [option.strip() for option in choices.split(",")]
        
        if len(options) < 2:
            return await ctx.send("Give me at least two options separated by a comma! (e.g., Pizza, Pasta)")
            
        await ctx.send(f"I've thought about it, and I choose: **{random.choice(options)}!**")

    @commands.hybrid_command(name="mock", description="mAkE yOuR tExT lOoK lHiS.")
    async def mock(self, ctx, *, text: str):
        mocked_text = "".join([char.upper() if i % 2 == 0 else char.lower() for i, char in enumerate(text)])
        
        emoji = "<:SpongeMock:1502200574945529896>" 
        
        await ctx.send(f"{emoji} {ctx.author.mention} {mocked_text}")

    @commands.hybrid_command(name="roll", description="Roll a die (2-20 sides).")
    async def roll(self, ctx, sides: int = 6):
        """Rolls a die with a maximum of 20 sides."""
        if sides < 2:
            return await ctx.send("I can't roll a die with less than 2 sides, Einstein.")
        
        if sides > 20:
            return await ctx.send("Easy there, high roller! Max die size is **20**. 🎲")
        
        result = random.randint(1, sides)
        await ctx.send(f"🎲 **{ctx.author.mention}** rolled a **D{sides}** and got: **{result}**")

    @commands.hybrid_command(name="spacefact", description="Pull real-time data on a random celestial body!")
    async def spacefact(self, ctx):
        url = "https://api.le-systeme-solaire.net/rest/bodies/"
        api_key = "99499df9-ede1-466d-8fcd-a7ee85201ffd"
        
        headers = {
            "Authorization": f"Bearer {api_key}"
        }

        await ctx.defer()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Filter: Only keep objects that have gravity data or a discoverer 
                        # to avoid showing "empty" scan results.
                        bodies = [b for b in data['bodies'] if b.get('gravity') or b.get('discoveredBy')]
                        body = random.choice(bodies)
                        
                        name = body.get('englishName', 'Unknown Entity')
                        body_type = body.get('bodyType', 'Object')
                        gravity = body.get('gravity') or "Minimal"
                        discovered = body.get('discoveryDate') or "Pre-modern"
                        
                        # Get the parent body (Planet or Sun)
                        around_data = body.get('aroundPlanet')
                        around = around_data.get('planet').capitalize() if around_data else "The Sun"
                        planet_map = {
                            "Mercure": "Mercury",
                            "Vénus": "Venus",
                            "Terre": "Earth",
                            "Mars": "Mars",
                            "Jupiter": "Jupiter",
                            "Saturne": "Saturn",
                            "Uranus": "Uranus",
                            "Neptune": "Neptune"
                        }
                        around = planet_map.get(around, around)
                        
                        # Temperature formatting
                        kelvin = body.get('avgTemp')
                        if kelvin and kelvin != 0:
                            celsius = round(kelvin - 273.15, 1)
                            temp_display = f"{celsius}°C"
                        else:
                            temp_display = "Varies greatly"
                        
                        fact_msg = (
                            f"**Classification:** {body_type.capitalize()}\n"
                            f"**Orbiting:** {around}\n"
                            f"**Surface Gravity:** {gravity} m/s²\n"
                            f"**Surface Temp:** {temp_display}\n"
                            f"**Discovered:** {discovered}"
                        )

                        embed = discord.Embed(
                            title=f"🔭 Deep Space Scan",
                            description=f"**Name: {name}**\n{fact_msg}",
                            color=discord.Color.blue()
                        )
                        embed.set_footer(text="Enceladus' Station | Solar System Database")
                        await ctx.send(embed=embed)
                    else:
                        print(f"API Error Status: {response.status}")
                        await ctx.send("📡 The API uplink rejected our key or is down.")
        except Exception as e:
            print(f"Space Error: {e}")
            await ctx.send("🌌 Something went wrong in the asteroid belt.")
    
    @commands.hybrid_command(name="furryrate", description="Check the local fluff levels!")
    async def furryrate(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        percent = random.randint(0, 100)
        
        if percent == 0:
            status = "Purely human. Not a single tuft of fur found. 🚫"
        elif percent < 25:
            status = "Low levels of fluff. Maybe just a fan of The Lion King? 🦁"
        elif percent < 50:
            status = "Modern furry. Likely owns a tail or a pair of ears. Nothing crazy. 🐾"
        elif percent < 75:
            status = "High-Grade furry. Definitely has a FurAffinity account. FOX"
        elif percent < 100:
            status = "Maximum floof!! 100% pathOwOgen detected! 🐺"
        else:
            status = "ASCENDED! Is literally just a giant ball of fluff at this point. 🐶"

        await ctx.send(f"📊 **Furry Meter for {member.mention}:**\n**[{'█' * (percent // 10)}{'░' * (10 - (percent // 10))}]** {percent}%\n✨ **Diagnosis:** {status}")

    @commands.hybrid_command(name="freakyrate", description="Check the local freak-o-meter levels!")
    async def freakyrate(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        percent = random.randint(0, 100)
        
        if percent == 0:
            status = "Completely normal. Boringly standard. 🥱"
        elif percent < 25:
            status = "Slightly unhinged. You've thought about it. 🧐"
        elif percent < 50:
            status = "Certified weirdo. You're the reason we have rules. 🤨"
        elif percent < 75:
            status = "The freak is leaking. Dial it back a bit. 🫣"
        elif percent < 100:
            status = "FULL FREAK MODE. Seek immediate containment. ⛓️"
        else:
            status = "Freaky ahh 👅"

        bar = '█' * (percent // 10)
        empty = '░' * (10 - (percent // 10))

        await ctx.send(
            f"👅 **Freaky rate for {member.mention}:**\n"
            f"**[{bar}{empty}]** {percent}%\n"
            f"**Diagnosis:** {status}"
        )

    @commands.hybrid_command(name="iqrate", description="Measure your brain power (or lack thereof)!")
    async def iqrate(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        
        iq = random.randint(30, 160)

        if iq < 50:
            status = "Cold fall temperature IQ. You make rocks look smart. 🪨"
        elif iq < 70:
            status = "Room temperature IQ. Your brain is essentially a potato. 🥔"
        elif iq < 90:
            status = "Below average. You struggle with push doors. 🚪"
        elif iq < 110:
            status = "Perfectly average. You are a background character. 😐"
        elif iq < 130:
            status = "High intelligence. You actually read the terms of service. 📜"
        elif iq < 150:
            status = "Certified genius. You can solve a Rubik's cube in under a minute. 🧩"
        else:
            status = "OMNISCIENT. You can see the code of the universe. 👁️"

        bar = '█' * (iq // 16)
        empty = '░' * (10 - (iq // 16))

        await ctx.send(
            f"🧠 **IQ Analysis for {member.mention}:**\n"
            f"**[{bar}{empty}]** {iq} IQ\n"
            f"**Diagnosis:** {status}"
        )

    @commands.hybrid_command(name="aurarate", description="Calculate your current aura levels with a reason!")
    async def aurarate(self, ctx, member: discord.Member = None):
        member = member or ctx.author

        if random.random() < 0.05:
            aura = 0
            reason = random.choice([
                "stood perfectly still for 5 minutes",
                "looked at a wall and blinked",
                "blinked at the exact same time as everyone else",
                "drank a glass of room-temperature water",
                "existed in a state of pure neutrality",
                "took a perfectly average nap",
                "had a completely uneventful day",
                "had a perfectly balanced breakfast of toast and cereal",
                "walked in a straight line for 10 steps",
                "stared at a ceiling fan and felt nothing",
                "had a completely normal conversation about the weather",
                "sat in silence for 10 minutes and felt at ease",
                "performed a perfectly average dance move that neither impressed nor embarrassed anyone"
            ])
            status = "Neutral Aura. Perfectly balanced, as all things should be. ⚪"
            color = "⚪"
        else: 
            aura = random.randint(-10000, 10000)
        
        negative_reasons = [
            "tripped on a flat surface",
            "said 'you too' to the waiter",
            "posted a meme in the wrong channel",
            "got left on read by a bot",
            "accidentally liked a photo from 2016",
            "sneezed and nobody said bless you",
            "forgot your own password",
            "typed 'lol' while stone-faced",
            "called someone by the wrong name for an entire conversation",
            "choked on your own spit while talking",
            "had a hot mic while eating chips",
            "tried to lean on a table that wasn't there in VR",
            "replied 'here' when the teacher didn't call your name",
            "failed a vibe check from a Level 1 member",
            "forgot to unmute before a 5-minute rant",
            "got 'L + Ratio'd' by a literal child",
            "accidentally sent a message to the wrong person and it was awkward",
            "posted a meme that was already posted 5 minutes ago and got called out for it",
            "laughed at your own joke and nobody else did",
            "tried to do a cool dance move and just looked like you were having a seizure"
        ]
        
        positive_reasons = [
            "clutched a 1v4 in Fortnite and won",
            "actually used a coaster for your drink",
            "caught the phone before it hit the floor",
            "corrected the teacher and was right",
            "found a shiny Pokemon on the first encounter",
            "walked through an automatic door and it opened perfectly",
            "ordered water and got a free soda",
            "predicted the future in a dream",
            "fixed a bug on the first try",
            "made a joke that made the 'quiet person' laugh",
            "guest-starred in a popular streamer's video by accident",
            "plugged in a USB correctly on the first attempt",
            "carried the entire team while eating a sandwich",
            "somebody asked for the 'sauce' and you actually had the link",
            "dropped your phone but caught it with your foot",
            "typed 120 WPM without a single typo",
            "everyone in the voice call went quiet to hear your story",
            "you successfully argued with a moderator and won",
            "you found a $20 bill on the ground and nobody else saw it",
            "you got a notification that you were tagged in a meme and it was actually funny"
        ]

        if aura < 0:
            status = "Losing Aura. You're cooked, fam. 📉"
            reason = random.choice(negative_reasons)
            color = "🔴"
        else:
            status = "Gaining Aura. Main character energy. 📈"
            reason = random.choice(positive_reasons)
            color = "🟢"

        if aura < -9500: status = "Aura Debt. You **owe** the universe respect. Big oof. 💀"
        if aura > 9500: status = "**GIGACHAD AURA!** The universe bows to you. 🌌"

        await ctx.send(
            f"✨ **Aura Analysis for {member.mention}:**\n"
            f"**Current Aura:** `{aura:+,}`\n"
            f"**Reason:** You {reason} ( {aura:+,} aura )\n"
            f"**Status:** {status} {color}"
        )

    @commands.hybrid_command(name="cringerate", description="How much did you just make the chat physically recoil?")
    async def cringerate(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        percent = random.randint(0, 100)
        
        if percent == 0:
            reaction = "Pure Based Energy. Everyone is nodding in respect."
            status = "Unbelievably Based. 🗿"
        elif percent < 30:
            reaction = "A slight nose exhale. We'll allow it."
            status = "Low Level Cringe. Just a minor slip-up. 🤏"
        elif percent < 60:
            reaction = "The chat has gone silent. Someone is typing '...' as we speak."
            status = "Standard Cringe. Average Discord user behavior. 😬"
        elif percent < 85:
            reaction = "Visible shudders. People are closing the app to take a walk."
            status = "High-Grade Cringe. This is going in the 'hall of shame'. 💀"
        elif percent < 100:
            reaction = "Physical recoil. People are shielding their eyes and looking away. The second-hand embarrassment is fatal."
            status = "LETHAL CRINGE. This is the stuff of legends... and nightmares. 😬"
        else:
            reaction = "The universe has reset to 2008. You just posted 'ROFLCOPTER' and said swag."
            status = "CRINGE SINGULARITY. You have folded space-time. 🌌"

        bar = '█' * (percent // 10)
        empty = '░' * (10 - (percent // 10))

        await ctx.send(
            f"😬 **Cringe Analysis for {member.display_name}:**\n"
            f"**[{bar}{empty}]** {percent}%\n"
            f"**Reaction:** *{reaction}*\n"
            f"**Status:** {status}"
        )

    @commands.hybrid_command(name="coolrate", description="Check your ice-cold factor!")
    async def coolrate(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        percent = random.randint(0, 100)
        
        cool_traits = [
            "wearing sunglasses at night",
            "never looking at explosions",
            "always having the perfect reaction meme",
            "doing a kickflip on a fingerboard",
            "having a flawless kill streak",
            "typing without looking at the keyboard",
            "able to open a bottle with another bottle",
            "knowing exactly when the beat is going to drop",
            "always picking the best movie for group watch",
            "having a voice that sounds like a radio host",
            "the only one who actually knows the lyrics to the rap part",
            "able to spin a pen around your thumb",
            "the person everyone asks 'where did you get that?'",
            "the one who clutched the 1% boss health wipe",
            "able to cook a 5-star meal with just leftovers",
            "knowing a guy who knows a guy",
            "immune to second-hand embarrassment",
            "the undisputed champion of the staring contest"
        ]
        
        lame_traits = [
            "using 'XD' in every sentence",
            "clapping when the airplane lands",
            "reminding the teacher about the homework",
            "wearing socks with sandals",
            "unironically liking 'Baby Shark'",
            "tripping over your own shadow",
            "asking 'where is my hug?'",
            "still playing Flappy Bird in 2026",
            "saying 'swag' unironically",
            "posting 'first!' in the chat",
            "making a 'dad joke' and then saying 'I know, I'm a dad!' as if that makes it better",
            "saying 'cool story, bro' in response to literally any story",
            "using 'u' instead of 'you' in a non-texting context",
            "saying 'dab on the haters'",
            "using the term 'ratio' in 2026",
            "saying 'ROFL' in 2026",
            "reminding the group that 'actually, it's 11:59, not midnight'",
            "using your index fingers to type on a smartphone",
            "telling a joke and then explaining why it's funny",
            "wiping your forehead after a light jog",
            "asking for a 'bite' of someone else's water",
            "watching TikToks at full volume in a library",
            "unironically using the '🤓' emoji in an argument",
            "trying to high-five someone who is clearly waving at someone else"
        ]

        if percent < 40:
            status = "Lame. You're trying too hard. 🤓"
            trait = random.choice(lame_traits)
        elif percent < 85:
            status = "Average Joe. You're chill, but not legendary. 👍"
            trait = random.choice(cool_traits)
        elif percent < 100:
            status = "The Main Character. You own the room. 🔥"
            trait = random.choice(cool_traits)
        else:
            status = "COSMIC LEGEND. The stars literally want your autograph. 🌌"
            trait = "the absolute goat of the server"

        if percent == 0:
            status = "Absolute Zero. Negative drip detected. 🧊"
            trait = "the definition of a 'NPC'"

        bar = '█' * (percent // 10)
        empty = '░' * (10 - (percent // 10))

        await ctx.send(
            f"😎 **Coolness Analysis for {member.mention}:**\n"
            f"**[{bar}{empty}]** {percent}%\n"
            f"**Cool Factor:** You're {trait}.\n"
            f"**Status:** {status}"
        )

    @commands.hybrid_command(name="fortune", description="Open your daily cosmic fortune cookie!")
    async def fortune(self, ctx):
        user_id = ctx.author.id
        
        # 1. Get the current date in Eastern Time
        et_timezone = pytz.timezone("US/Eastern")
        current_date_et = datetime.datetime.now(et_timezone).strftime("%Y-%m-%d")

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT last_fortune_date FROM users WHERE user_id = ?", (user_id,)) as cursor:
                result = await cursor.fetchone()

            # If they've used it today already
            if result and result[0] == current_date_et:
                return await ctx.send("⏳ You've already opened your cookie for today! Come back after midnight **Eastern Time**.")

            # 3. Fortune Logic
            if random.random() < 0.01: 
                selected_fortune = "The cookie is empty. A hollow void stares back at you. Your aura is currently unstable. 💀"
                lucky_nums = "0, 0, 0, 0, 0"
            else:
                fortunes = [
                    "A dragon's hoard of wealth is in your future.",
                    "The stars suggest you'll find a $20 bill on the ground at some point today.",
                    "Your code will compile on the first try today.",
                    "Someone is admiring your vibe from across the server.",
                    "A supernova of luck is heading your way!",
                    "Your next meme will be legendary.",
                    "The cosmic winds whisper... exciting news is coming!",
                    "Your next game will be a masterpiece.",
                    "A mysterious benefactor will boost your next project.",
                    "Your next stream will break viewership records.",
                    "The astral relic is feeling generous today. Expect good fortune!",
                    "A cosmic event will align perfectly with your next big move.",
                    "Your next idea will be a game-changer.",
                    "Someone will compliment your profile picture today.",
                    "Your next message will get an unexpected amount of likes.",
                    "Your next joke will be the funniest thing in the chat.",
                    "Your next game night will be unforgettable.",
                    "A rare cosmic phenomenon will occur in your honor."
                ]
                selected_fortune = random.choice(fortunes)
                lucky_nums = ", ".join(map(str, random.sample(range(1, 99), 5)))

            await db.execute("""
                INSERT INTO users (user_id, last_fortune_date) 
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET last_fortune_date = excluded.last_fortune_date
            """, (user_id, current_date_et))
            await db.commit()

        await ctx.send(
            f"🥠 **{ctx.author.mention} pulls apart the cookie...**\n"
            f"> *\"{selected_fortune}\"*\n"
            f"🔮 **Lucky Numbers:** `{lucky_nums}`"
        )

    @app_commands.command(name="horoscope", description="Check your daily horoscope!")
    @app_commands.describe(sign="Choose your zodiac sign")
    @app_commands.choices(sign=[
        app_commands.Choice(name="♈ Aries", value="aries"),
        app_commands.Choice(name="♉ Taurus", value="taurus"),
        app_commands.Choice(name="♊ Gemini", value="gemini"),
        app_commands.Choice(name="♋ Cancer", value="cancer"),
        app_commands.Choice(name="♌ Leo", value="leo"),
        app_commands.Choice(name="♍ Virgo", value="virgo"),
        app_commands.Choice(name="♎ Libra", value="libra"),
        app_commands.Choice(name="♏ Scorpio", value="scorpio"),
        app_commands.Choice(name="♐ Sagittarius", value="sagittarius"),
        app_commands.Choice(name="♑ Capricorn", value="capricorn"),
        app_commands.Choice(name="♒ Aquarius", value="aquarius"),
        app_commands.Choice(name="♓ Pisces", value="pisces"),
    ])
    async def horoscope(self, interaction: discord.Interaction, sign: app_commands.Choice[str]):
        await interaction.response.defer()

        async with aiohttp.ClientSession() as session:
            url = f"https://horoscope-app-api.vercel.app/api/v1/get-horoscope/daily?sign={sign.value}&day=today"
            
            async with session.get(url) as response:
                if response.status == 200:
                    raw_data = await response.json()
                    horoscope_text = raw_data['data']['horoscope_data']
                    
                    embed = discord.Embed(
                        title=f"{sign.name} — Today's Reading", 
                        description=horoscope_text, 
                        color=0x6a0dad
                    )
                    embed.set_footer(text="The stars have spoken in The Cosmic Lair.")
                    
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("The cosmic vibrations are a bit distorted... (API Error)", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot, "fun.db"))