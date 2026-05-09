# © 2026 The Cosmic Lair & AstroThaDragon. All Rights Reserved. 
# Unauthorized use of this code is prohibited.

import discord
from discord.ext import commands, tasks
import os
import random
from tags import tag_list
from dotenv import load_dotenv
from discord import app_commands
import aiohttp
import asyncio
import re
import sqlite3
from datetime import datetime, time, timezone, timedelta

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True 

bot = commands.Bot(command_prefix='-', intents=intents)
bot.remove_command('help')

# --- CONFIGURATION ---
DRAGON_IMAGE_URL = "https://media.discordapp.net/attachments/916221943101947914/1497326085099094209/IMG_20191102_191207_871.png?ex=69f50615&is=69f3b495&hm=eff466c1a7fa9296a8e2de3ed78ade6aa1c5d72dd7f81e60d6957f0891c29558&=&format=webp&quality=lossless"
DB_PATH = "levels.db" # Database where timers are stored

# Anti-double message protection
recent_joins = set()
recent_leaves = set()

# --- DATABASE INITIALIZATION ---
async def init_bump_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS bump_timer (id INTEGER PRIMARY KEY, remind_at TEXT, channel_id INTEGER)")
    cursor.execute("CREATE TABLE IF NOT EXISTS vaulted_messages (message_id INTEGER PRIMARY KEY)") 
    conn.commit()
    conn.close()

# --- STATUS ROTATOR SETUP ---
status_list = [
    "Watching over the Lair",
    "Searching for dragons 🐉", 
    "Processing reports...",
    "Scanning the cosmos 🌌",
    "Powered by stardust!",
    "Harvesting moon rocks",
    "Beep boop bop",
    "Playing FNF",
    "Watching SpongeBob",
    "Guarding the Astral Relic",
    "Chillin' and vibin' with the stars",
    "Calculating the meaning of life...",
    "Sipping on some cosmic tea ☕",
    "Waiting for the next big space event 🌠",
    "Just a bot, living in a cosmic world",
    "Looking up at the stars and wondering...",
    "Stargazing",
    "Quietly judging your memes"
]

@tasks.loop(minutes=15)
async def change_status():
    new_status = random.choice(status_list)
    await bot.change_presence(activity=discord.CustomActivity(name=new_status))

# --- BUMP PERSISTENCE LOOP ---
@tasks.loop(minutes=1)
async def check_bump_timer():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT remind_at, channel_id FROM bump_timer WHERE id = 1")
    row = cursor.fetchone()
    
    if row:
        remind_at = datetime.fromisoformat(row[0])
        # Compare current time (UTC) to saved time
        if datetime.now(timezone.utc) >= remind_at:
            channel = bot.get_channel(row[1])
            if channel:
                bump_role_id = "1295212860720418887"
                reminder_embed = discord.Embed(
                    description=(
                        f"*Sniffsniff..*\n\n"
                        f"*Sniff!!*\n"
                        f"It's time to bump once again! Please bump our server by typing /bump! "
                        f"It helps us a lot by gaining more members! <a:RedHearts:1109768412382642266> <:AstroHeart:927518108745343026> <a:PurpleHearts:1109768355390431323>"
                    ),
                    color=discord.Color.from_rgb(114, 0, 225)
                )
                await channel.send(content=f"<@&{bump_role_id}>", embed=reminder_embed)
            
            # Clean up the database once the reminder is sent
            cursor.execute("DELETE FROM bump_timer WHERE id = 1")
            conn.commit()
    conn.close()

# --- STARGAZING ALERTS SETUP ---
edt = timezone(timedelta(hours=-4))
scheduled_time = time(hour=12, minute=0, tzinfo=edt)

@tasks.loop(time=scheduled_time)
async def stargazing_alert():
    channel_id = 593416487499333653 
    channel = bot.get_channel(channel_id)
    
    if channel:
        # This URL converts the "In-The-Sky" event feed into JSON for your bot
        url = "https://api.rss2json.com/v1/api.json?rss_url=https%3A%2F%2Fin-the-sky.org%2Frss.php%3Ffeed%3Dupcoming"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Get the most recent upcoming event
                        item = data['items'][0]
                        title = item['title']
                        link = item['link']
                        # The description often has HTML, this clean-up helps
                        description = re.sub('<[^<]+?>', '', item['description'])[:300] + "..."

                        embed = discord.Embed(
                            title="🌌 🔭 Tonight's Cosmic Event!",
                            description=f"**{title}**\n\n{description}\n\n🔗 [View Event Details]({link})",
                            color=discord.Color.dark_purple()
                        )
                        # Space-themed thumbnail
                        embed.set_thumbnail(url="https://i.imgur.com/83S8Z6H.png")
                        embed.set_footer(text="Source: In-The-Sky.org | Keep looking up, Stargazers! 🔭")
                        
                        await channel.send(embed=embed)
        except Exception as e:
            print(f"Error in stargazing_alert loop: {e}")

# --- EVENTS ---
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    await init_bump_db() # Ensure bump table exists
    
    try:
        await bot.tree.sync()
    except Exception as e:
        print(f"Error syncing tree: {e}")
    
    if not change_status.is_running():
        change_status.start()
        
    if not stargazing_alert.is_running():
        stargazing_alert.start()

    if not check_bump_timer.is_running():
        check_bump_timer.start()
        
    print("Status rotator, Stargazing alerts, and Bump Persistence are now active!")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # --- 1. TAG LOGIC ---
    if message.content.startswith("-"):
        tag_name = message.content[1:].lower().strip()
        if tag_name in tag_list:
            content = tag_list[tag_name]
            if "images/" in content.lower():
                if "\n" in content:
                    parts = content.rsplit("\n", 1)
                    text_caption = parts[0].strip()
                    file_path = parts[1].strip()
                else:
                    text_caption = None
                    file_path = content.strip()

                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        await message.channel.send(content=text_caption, file=discord.File(f))
                    return 
            
            await message.channel.send(content)
            return 

    # --- 2. DISBOARD BUMP LOGIC (Updated for Persistence) ---
    if message.author.id == 302050872383242240:
        await asyncio.sleep(2)
        if message.embeds and "Bump done!" in (message.embeds[0].description or ""):
            description = message.embeds[0].description
            user_obj = None # We'll store the actual user here

            # 1. Try to get the user from the interaction metadata (most reliable)
            if message.interaction_metadata:
                user_obj = message.interaction_metadata.user
            
            # 2. Fallback: If no metadata, try to extract ID from the mention in description
            if not user_obj and "<@" in description:
                match = re.search(r"<@!?(\d+)>", description)
                if match:
                    user_id = int(match.group(1))
                    user_obj = message.guild.get_member(user_id)

            # Define mention string for your thanks_text
            user_mention = user_obj.mention if user_obj else "there"

            thanks_text = (
                f"Thank you so much for bumping our server, {user_mention}! It helps us a ton!! <:CoolEevee:1109771250634592306> 💜\n"
                f"You've earned **500 XP** for the server boost! You may come back in two hours to do it again! <a:DancingEevee:1109781719315398766>"
            )
            await message.channel.send(thanks_text)

            # --- ADD XP HERE ---
            if user_obj:
                # Reach into the Leveling cog from main.py
                leveling_cog = bot.get_cog('Leveling')
                if leveling_cog:
                    await leveling_cog.add_xp(user_obj, 500)
                else:
                    print("Leveling cog not found, couldn't award bump XP.")
            # -------------------
            
            # Save the reminder time (2 hours from now)
            remind_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO bump_timer (id, remind_at, channel_id) VALUES (1, ?, ?)", 
                           (remind_time, message.channel.id))
            conn.commit()
            conn.close()

    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    if member.id in recent_joins:
        return
    recent_joins.add(member.id)

    channel = bot.get_channel(1117377155496673330)
    if channel:
        count = member.guild.member_count
        if 11 <= (count % 100) <= 13:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(count % 10, 'th')
        ordinal_count = f"{count}{suffix}"
        
        content_text = f"Welcome to The Cosmic Lair, {member.mention}!! 💜"
        
        embed = discord.Embed(
            title="Hey there! Welcome to The Cosmic Lair! <a:PurpleHearts:1109768355390431323> <a:RedHearts:1109768412382642266>",
            description=(
                f"Before anything, please verify yourself over at <#1296962529989361685> "
                f"for full access to our server! Afterwards, please head over to <#593389789558865931> "
                f"to read our rules if you haven't already, then maybe check out <#927536823746580570> "
                f"for special roles while you're at it!\n\n"
                f"We also highly recommend checking out <#1484487011933884509> for our server's unique features, roles, bots, and channels!\n\n"
                f"Also, please be patient while our server grows; it may be a bit quiet at times!\n\n"
                f"We hope you enjoy your stay at The Cosmic Lair! Feel free to invite friends, we won't bite!"
            ),
            color=discord.Color.from_rgb(114, 0, 225)
        )
        embed.set_author(name=f"{member.name}", icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=DRAGON_IMAGE_URL)
        embed.set_footer(text=f"You are our {ordinal_count} member! Congrats!")
        
        await channel.send(content=content_text, embed=embed)

    await asyncio.sleep(10)
    recent_joins.discard(member.id)

@bot.event
async def on_member_remove(member):
    if member.id in recent_leaves:
        return
    recent_leaves.add(member.id)

    channel = bot.get_channel(1117377155496673330)
    if channel:
        count = member.guild.member_count
        content_text = f"Sorry to see you go, {member.name}!"
        
        embed = discord.Embed(
            title="We're sorry to see you go! :c",
            description=(
                f"It looks like {member.mention} has left the server. "
                f"We hope to see you again soon, and please be safe!"
            ),
            color=discord.Color.from_rgb(114, 0, 225)
        )
        embed.set_author(name=f"{member.name}", icon_url=member.display_avatar.url)
        embed.set_footer(text=f"We now have {count} members.")
        
        await channel.send(content=content_text, embed=embed)

    await asyncio.sleep(10)
    recent_leaves.discard(member.id)

@bot.event
async def on_member_update(before, after):
    if before.premium_since is None and after.premium_since is not None:
        channel = bot.get_channel(1117417170545160222)
        if channel:
            boost_count = after.guild.premium_subscription_count
            if boost_count < 2: next_level = 2 - boost_count
            elif boost_count < 7: next_level = 7 - boost_count
            else: next_level = 14 - boost_count

            content_text = f"Thank you, {after.mention}!"
            
            embed = discord.Embed(
                title="Wooo! We have a new booster! 💜",
                description=(
                    f"Thank you so much, {after.name}!! You have received our supporter role! "
                    f"We are now at {boost_count} boosts! 🐉❤️"
                ),
                color=discord.Color.from_rgb(114, 0, 225)
            )
            embed.set_author(name=f"{after.name}", icon_url=after.display_avatar.url)
            embed.set_footer(text=f"We only need {next_level} boosts till our next level!")
            
            await channel.send(content=content_text, embed=embed)

VAULT_CHANNEL_ID = 1496628909570265199
VAULT_THRESHOLD = 5
EXCLUDED_CHANNELS = [593389789558865931, 598883099987673088, 1484487011933884509, 1352415256584130590, 1306821711970435122, 935876805607444510, 1118027416443564042, 1491230190469120010, 1117412987788075038]  # Add channel IDs here
EXCLUDED_CATEGORIES = [1295664420294361179, 1353577090099712070, 593406939111751721, 593413698085978132, 1474514782605541537] # Add category IDs here

@bot.event
async def on_raw_reaction_add(payload):
    if str(payload.emoji) == "⭐": 
        channel = bot.get_channel(payload.channel_id)
        
        # NSFW & EXCLUSION CHECKS
        if channel.is_nsfw() or channel.id in EXCLUDED_CHANNELS or channel.category_id in EXCLUDED_CATEGORIES:
            return

        message = await channel.fetch_message(payload.message_id)
        
        # SELF-CHECK
        if payload.user_id == message.author.id:
            return 

        # --- FIX: Open Database Connection inside the event ---
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # DUPLICATE CHECK
        cursor.execute("SELECT message_id FROM vaulted_messages WHERE message_id = ?", (message.id,))
        if cursor.fetchone():
            conn.close() # Always close the connection before returning
            return 

        # Find the reaction count
        reaction = discord.utils.get(message.reactions, emoji=payload.emoji.name)
        
        if reaction and reaction.count >= VAULT_THRESHOLD:
            vault_channel = bot.get_channel(VAULT_CHANNEL_ID)
            
            embed = discord.Embed(
                description=message.content,
                color=discord.Color.gold(),
                timestamp=message.created_at
            )
            embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url)
            embed.add_field(name="Original", value=f"[Jump to Message]({message.jump_url})")
            
            if message.attachments:
                embed.set_image(url=message.attachments[0].url)
                
            embed.set_footer(text=f"ID: {message.id} • The Vault")
            
            await vault_channel.send(embed=embed)

            # RECORD THE POST
            cursor.execute("INSERT INTO vaulted_messages (message_id) VALUES (?)", (message.id,))
            conn.commit()
        
        # Close connection when done
        conn.close()

# --- COSMIC COMMANDS ---

@bot.tree.command(name="nasa", description="View NASA's Astronomy Picture of the Day!")
async def nasa(interaction: discord.Interaction):
    api_key = os.getenv('NASA_API_KEY', 'DEMO_KEY')
    url = f"https://api.nasa.gov/planetary/apod?api_key={api_key}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                title = data.get('title', 'Space Discovery')
                desc = data.get('explanation', '')
                img_url = data.get('url', '')
                media_type = data.get('media_type', '') 
                
                page_url = "https://apod.nasa.gov/apod/astropix.html"
                
                if len(desc) > 300:
                    desc = desc[:297] + "..."

                embed = discord.Embed(
                    title=f"🚀 {title}", 
                    description=f"{desc}\n\n🔗 [View on NASA APOD]({page_url})", 
                    color=discord.Color.blue()
                )
                
                if media_type == 'video':
                    embed.description += f"\n\n**Watch the video here:**\n{img_url}"
                else:
                    embed.set_image(url=img_url)
                
                embed.set_footer(text="Provided by NASA APOD API")
                await interaction.response.send_message(embed=embed)

@bot.tree.command(name="bing", description="View today's Bing wallpaper!")
async def bing(interaction: discord.Interaction):
    url = "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=en-US"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                img_path = data['images'][0]['url']
                img_url = f"https://www.bing.com{img_path}"
                copyright_info = data['images'][0]['copyright']
                copyright_link = data['images'][0]['copyrightlink']

                embed = discord.Embed(
                    title="🌍 Today's Bing Wallpaper", 
                    description=f"{copyright_info}\n\n🔗 [Explore Location]({copyright_link})", 
                    color=discord.Color.green()
                )
                embed.set_image(url=img_url)
                await interaction.response.send_message(embed=embed)

@bot.tree.command(name="moon", description="Check the current moon phase!")
async def moon(interaction: discord.Interaction):
    url = "https://wttr.in/?format=%m" 
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                phase_emoji = await response.text()
                await interaction.response.send_message(f"The current moon phase is: **{phase_emoji}**")
            else:
                await interaction.response.send_message("Can't see the moon right now! ☁️")

@bot.tree.command(name="weather", description="Get the current weather for a specific city!")
async def weather(interaction: discord.Interaction, city: str):
    url = f"https://wttr.in/{city}?format=3"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                weather_report = await response.text()
                await interaction.response.send_message(f"**Current Weather:**\n{weather_report}")
            else:
                await interaction.response.send_message(f"I couldn't find the weather for '{city}'. Is that a real place in the cosmos?")

@bot.tree.command(name="iss", description="Track the International Space Station's current location!")
async def iss(interaction: discord.Interaction):
    await interaction.response.defer()
    
    url = "https://api.wheretheiss.at/v1/satellites/25544"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    lat = data.get('latitude')
                    lon = data.get('longitude')
                    velocity = data.get('velocity')
                    
                    maps_url = f"https://www.google.com/maps?q={lat},{lon}&t=k"
                    
                    embed = discord.Embed(
                        title="🛰️ ISS Current Location",
                        description=f"The International Space Station is currently flying over:\n\n🔗 [View on Live Map]({maps_url})",
                        color=discord.Color.dark_blue()
                    )
                    embed.add_field(name="Latitude", value=f"{lat:.4f}", inline=True)
                    embed.add_field(name="Longitude", value=f"{lon:.4f}", inline=True)
                    embed.add_field(name="Velocity", value=f"{velocity:.2f} km/h", inline=False)
                    embed.set_footer(text="Data provided by 'Where the ISS at?'")
                    
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("I've lost contact with the satellite! 📡")
        except Exception as e:
            print(f"ISS Command Error: {e}")
            await interaction.followup.send("The tracking station is currently offline. Try again later!")

# --- COMMANDS ---
@bot.command()
async def qr(ctx, *, reason):
    staff_channel = bot.get_channel(1352834838478061608) 
    if staff_channel:
        jump_url = f"https://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{ctx.message.id}"
        report_msg = (
            f"⚠️ **New Quick Report!**\n"
            f"**User:** {ctx.author.mention} used `!qr` in {ctx.channel.mention}\n"
            f"**Reason:** {reason}\n"
            f"🔗 [Click here for the message that was reported.]({jump_url})"
        )
        await staff_channel.send(report_msg)
        await ctx.message.delete()
        await ctx.author.send("Your report has been sent to the staff. Thank you for helping The Cosmic Lair stay positive! 🌌💜")
    else:
        print("Error: Staff channel not found.")

@bot.command()
@commands.has_permissions(administrator=True)
async def resetbump(ctx):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bump_timer WHERE id = 1")
    conn.commit()
    conn.close()
    await ctx.send("Bump timer has been cleared from the database! 🔄")
    
@bot.hybrid_command(name="help", aliases=["protocols", "directory"], description="Displays the full directory of Enceladus' commands!")
async def help_command(ctx):
    """The central directory for all of Enceladus' station functions."""
    embed = discord.Embed(
        title="# 🛰️ Enceladus Command Directory",
        description="Use `/help` for Slash or `-protocols` for Prefix. All commands work below with `-` or `/`, so use whatever you prefer! 🌌",
        color=discord.Color.from_rgb(138, 43, 226)
    )

    embed.add_field(
        name="__ ⭐ Leveling & Social__",
        value=(
            "`/rank <member>` - View your level, XP, and rank card.\n"
            "`/customize <bar_color> [bg_url]` - Personalize your rank card aesthetics.\n"
            "`/hug <member>` - Give a warm, fuzzy cosmic hug.\n"
            "`/slap <member>` - Strike someone with a random object."
        ),
        inline=False
    )

    embed.add_field(
        name="__ 🎮 Fun & Cosmic Games__",
        value=(
            "`/relic <question>` - Consult the Astral Relic for answers.\n"
            "`/coinflip` - Supernova (Heads) or Black Hole (Tails)?\n"
            "`/roll <sides>` - Roll a die (2-20 sides).\n"
            "`/choose <opt1, opt2>` - Let the bot decide for you.\n"
            "`/mock <text>` - mAkE yOuR tExT lOoK lIkE tHiS.\n"
            "`/blackhole <text>` - Send a message into the void.\n"
            "`/spacedata` - Pull real-time data on a random celestial body.\n"
            "`/bing` - View today's Bing wallpaper.\n"
            "`/nasa` - See NASA's Astronomy Picture of the Day.\n"
            "`/moon` - Check the current moon phase.\n"
            "`/weather <city>` - Get the current weather for a city.\n"
            "`/iss` - Track the International Space Station's current location."
        ),
        inline=False
    )

    embed.add_field(
        name="__ 🎤 Rhythm & Search__",
        value=(
            "`/fnfmod <query>` - Search GameBanana for FNF mods.\n"
            "`/fnfsong <song>` - Find FNF tracks on YouTube."
        ),
        inline=False
    )

    embed.add_field(
        name="__ 🛠️ Server Tools__",
        value=(
            "`/echo <msg> [chan (optional)]` - Make Enceladus speak elsewhere.\n"
            "`-[tagname]` - View a saved community tag.\n"
            "`-list` - List all available community tags."
        ),
        inline=False
    )

    # Only shows this section if the user has Administrator permissions
    if ctx.author.guild_permissions.administrator:
        embed.add_field(
            name="__ 🛡️ Station Admin (Staff Only)__",
            value=(
                "`/setlevel <member> <level>` / `/setxp <member> <xp>` - Manually adjust user stats.\n"
                "`/sync_levels` - Calibrate levels based on roles.\n"
                "`/reset <member>` - Wipe all leveling progress for a member."
            ),
            inline=False
        )

    embed.set_footer(text="Enceladus' Station | Powered by the Astral Plane! 🌌")
    
    await ctx.send(embed=embed)

async def load_extensions():
    # This tells the bot to load your new leveling.py file
    await bot.load_extension('leveling')
    await bot.load_extension("fun")
    print("Fun Cog loaded!")

async def main():
    async with bot:
        token = os.getenv('DEV_TOKEN') or os.getenv('DISCORD_TOKEN') 
        
        await init_bump_db()
        await load_extensions()
        
        if token:
            await bot.start(token)
        else:
            print("❌ ERROR: No bot token found in environment variables!")

if __name__ == "__main__":
    asyncio.run(main())