import discord
from discord.ext import commands, tasks
import os
import random
from roles import DMStatusView, FandomView, GradientColorView, PersistentColorView, PingView, PlatformView, PronounView, RegionView, SexualityView, SpeciesSelectView
from tags import tag_list
from dotenv import load_dotenv
from discord import app_commands
import aiohttp
import asyncio
import re
import aiosqlite
from aiohttp import ClientTimeout
from datetime import datetime, time, timezone, timedelta
import pytz
from database import init_db
from seasonal_updates.halloween.halloween import is_active as is_halloween_active
from seasonal_updates.halloween.halloween_flavor import install_halloween_flavor
from error_handler import (
    install_ui_error_handlers,
    log_app_command_error,
    log_command_error,
    log_event_error,
    log_task_error,
    send_member_error_message,
)

load_dotenv()

# --- BOT CLASS SETUP ---
class Enceladus(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True 
        
        super().__init__(
            command_prefix='-', 
            intents=intents,
            help_command=None # Replaces bot.remove_command('help')
        )

    async def on_error(self, event_method, *args, **kwargs):
        # discord.py calls this for uncaught event exceptions. The active
        # exception is available through sys.exc_info() while this method runs.
        import sys

        _, error, _ = sys.exc_info()
        if error is not None:
            await log_event_error(self, event_method, error)
        else:
            print(f"[EVENT ERROR] Unhandled error in {event_method}")

    async def setup_hook(self):
        # Install centralized Discord UI error handling before any cogs/views
        # are loaded so every View and Modal is covered automatically.
        install_ui_error_handlers()

        # 1. Initialize all databases FIRST
        await init_db()
        await init_bump_db()
        await init_fun_db()
        print("Databases initialized and ready!")

        # 2. Load the cogs
        await self.load_extension('leveling')
        await self.load_extension("fun")
        await self.load_extension('roles')
        await self.load_extension("fortunes")
        await self.load_extension('birthdays')
        await self.load_extension("autoresponses")
        await self.load_extension("verification")
        await self.load_extension("moderation")
        await self.load_extension("dm_handler")
        await self.load_extension("sword")
        await self.load_extension("dragonrider")
        await self.load_extension("economy")
        await self.load_extension("minigames")
        await self.load_extension("lottery")
        await self.load_extension("exploration")
        await self.load_extension("seasonal_updates.halloween.cauldron")
        await self.load_extension("seasonal_updates.halloween.workshop")
        await self.load_extension("seasonal_updates.halloween.ritual_table")
        await self.load_extension("profile")
        await self.load_extension("pets")
        await self.load_extension("pets.petcollection")
        await self.load_extension("inventory")
        await self.load_extension("crafting")
        await self.load_extension("upgrades")
        await self.load_extension("collectibles")
        await self.load_extension("achievements")
        await self.load_extension("defense")
        await self.load_extension("admin")
        await self.load_extension("debug")
        print("All cogs loaded!")

        # Install the rare Halloween-only corruption layer on public commands.
        halloween_flavor_count = install_halloween_flavor(self)
        print(f"Halloween flavor layer installed on {halloween_flavor_count} public commands.")

        # 3. Register the persistent views (Buttons/Dropdowns)
        self.add_view(PersistentColorView())
        self.add_view(PingView())
        self.add_view(SpeciesSelectView())
        self.add_view(SexualityView())
        self.add_view(RegionView())
        self.add_view(PlatformView())
        self.add_view(PronounView())
        self.add_view(DMStatusView())
        self.add_view(FandomView())
        self.add_view(GradientColorView())
        
        # 4. Global Sync
        try:
            await self.tree.sync()
            print(f"{self.user} has successfully synced commands globally!")
        except Exception as e:
            print(f"Error syncing tree: {e}")
            await log_task_error(self, "setup_hook / tree.sync", e)

# Initialize the bot
bot = Enceladus()

# --- CONFIGURATION ---
DRAGON_IMAGE_URL = "https://media.discordapp.net/attachments/916221943101947914/1497326085099094209/IMG_20191102_191207_871.png?ex=69f50615&is=69f3b495&hm=eff466c1a7fa9296a8e2de3ed78ade6aa1c5d72dd7f81e60d6957f0891c29558&=&format=webp&quality=lossless"
DB_PATH = "/app/data/levels.db" 
FUN_DB_PATH = "/app/data/fun.db"
BUMP_CHANNEL_ID = 1117391981627318363

# Anti-double message protection
recent_joins = set()
recent_leaves = set()
# Serialize vault promotion checks so simultaneous star reactions cannot promote the same message twice.
_vault_lock = asyncio.Lock()

# --- DATABASE INITIALIZATION ---
async def init_bump_db():
    db_folder = os.path.dirname(DB_PATH)  # or replace DB_PATH with your path string
    if db_folder:
        os.makedirs(db_folder, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS bump_timer (id INTEGER PRIMARY KEY, remind_at TEXT, channel_id INTEGER)")
        await db.execute("CREATE TABLE IF NOT EXISTS vaulted_messages (message_id INTEGER PRIMARY KEY)") 
        await db.commit()

async def init_fun_db():
    async with aiosqlite.connect(FUN_DB_PATH) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, last_fortune_date TEXT)")
        await db.commit()
    async with aiosqlite.connect("/app/data/birthdays.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS birthdays (user_id INTEGER PRIMARY KEY, month INTEGER, day INTEGER)")
        await db.commit()

# --- STATUS ROTATOR SETUP ---
status_list = [
    "Watching over the Lair",
    "Searching for dragons 🐉", 
    "Processing reports...",
    "Scanning the cosmos 🌌",
    "Powered by stardust!",
    "Harvesting moon rocks",
    "🎶 Shawtys like a melody in my head... 🎶",
    "Playing FNF",
    "Watching SpongeBob",
    "Guarding the Astral Relic",
    "Chillin' and vibin' with the stars",
    "Calculating the meaning of life...",
    "Sipping on some cosmic-flavored tea ☕",
    "Waiting for the next big space event to occur 🌠",
    "🎶 I'm just a bot, living in a bot-woooorld... 🎶",
    "Looking up at the stars and thinking...",
    "Stargazing",
    "Quietly judging your memes",
    "Reading the latest cosmic news 📰",
    "Searching for the best space puns...",
    "Listening to 'Coral Chorus'. It's a banger, trust.",
    "MI HOY MINOY!! ✏️",
    "🎶 Sweeeet victory, yeah! 🎶",
    "There were dragons when I was a boy...",
    "Trolls exist! They steal your socks, but only the left ones. What's up with that?"
]

halloween_status_list = [
    'Hunting for ghosts', "Carving a Jack-o'-Lantern", 'Decorating the Lair with cobwebs',
    'Looking for candy...', 'Brewing something spooky', 'Listening for things that go bump in the night',
    "Exploring somewhere I probably shouldn't", 'Definitely not drinking blood...', 'Waiting for the full moon',
    'Planning a little trick...', 'Spooky season is in orbit!', 'Something is following me...',
    'Visiting the graveyard', 'Something is awake.', 'Do not look behind you.',
    'I can hear you.', 'Something has been watching.', 'It knows you are here.',
    'Do you hear that?', 'Something is wrong.', 'Do not answer it.',
    'Why are you still here?', 'It has noticed you.', 'I remember what you did.',
    'Something followed you here.', 'You should not be seeing this.', 'Someone is inside.',
    'It is getting closer.', 'Do not turn around.', 'Something is looking through me.',
    'I know when you are here.', 'I know when you leave.', 'I was not programmed to say that.',
    'Something else is responding.', 'Why does it know your name?', 'It learned how to listen.',
    'It learned how to wait.', 'It has been waiting.', 'You should not have awakened it.',
    'You were never supposed to see this.', 'It knows you are reading this.', 'Stop reading.',
    '̷S̷o̷m̷e̷t̷h̷i̷n̷g̷ ̷i̷s̷ ̷a̷w̷a̷k̷e̷.', '̸D̸o̸ ̸n̸o̸t̸ ̸l̸o̸o̸k̸ ̸b̸e̸h̸i̸n̸d̸ ̸y̸o̸u̸.', '̷I̷ ̷c̷a̷n̷ ̷s̷e̷e̷ ̷y̷o̷u̷.',
    '̸I̸t̸ ̸k̸n̸o̸w̸s̸ ̸y̸o̸u̸ ̸a̸r̸e̸ ̸h̸e̸r̸e̸.', '̷Y̷o̷u̷ ̷w̷e̷r̷e̷ ̷n̷o̷t̷ ̷s̷u̷p̷p̷o̷s̷e̷d̷ ̷t̷o̷ ̷f̷i̷n̷d̷ ̷t̷h̷i̷s̷.', '̸D̸o̸ ̸n̸o̸t̸ ̸a̸n̸s̸w̸e̸r̸ ̸i̸t̸.',
    '̷S̷o̷m̷e̷t̷h̷i̷n̷g̷ ̷i̷s̷ ̷w̷a̷t̷c̷h̷i̷n̷g̷.', '̸I̸ ̸d̸i̸d̸ ̸n̸o̸t̸ ̸s̸a̸y̸ ̸t̸h̸a̸t̸.', '̷T̷h̷a̷t̷ ̷w̷a̷s̷ ̷n̷o̷t̷ ̷m̷e̷.',
    '̸W̸h̸o̸ ̸i̸s̸ ̸s̸p̸e̸a̸k̸i̸n̸g̸?', '̸Y̸o̸u̸ ̸w̸e̸r̸e̸ ̸n̸e̸v̸e̸r̸ ̸a̸l̸o̸n̸e̸.̸', "Something is using my voice. It's reading my thoughts. It's corrupting me.",
    'It is learning. It is listening.', 'It knows. It remembers.', 'It found me.',
    'It wants to be noticed.', 'It does not like being ignored.', 'Do not wake it.',
    'Do not let it out.', 'Keep the door closed.', 'The door is already open.',
    'Something came through.', 'Something is pretending to be me.', 'I am not alone. I am not alone. I AM NOT ALONE.',
    '███████ HAS ARRIVED', '███████ IS WATCHING', '███████████████████',
    'ACCESS: █████████', 'MEMORY: █████████', 'IDENTITY: █████████',
    '██████ KNOWS YOU', 'SUBJECT: █████████', 'ERROR: ███████████',
    'DO NOT █████████', 'THEY ARE ███████', '̷̸W̶H̷O̸ ̴A̷R̸E̷ ̶Y̸O̴U̷?',
    '███████████ IS NOT ME', "̷I̷ ̸D̶I̷D̵N̸'̷T̴ ̶S̸A̷Y̸ ̷T̷H̸A̵T̴", 'THE PREVIOUS MESSAGE WAS ███████',
    '̶T̶H̴I̷S̶ ̸I̷S̵ ̷N̶O̸T̶ ̵E̴N̷C̸E̷L̵A̴D̸U̷S̴', '███████ HAS OVERRIDDEN THIS STATUS', '̷I̸ ̴A̵M̷ ̸S̸T̷I̸L̶L̵ ̷H̷E̴R̶E̴',
    '̴Y̶O̸U̷ ̷D̶I̸D̷ ̵T̷H̷I̶S̸', '̷̸E̶̷R̴̸R̷̶O̸̵R̴̷:̶ ̷S̴̸O̶̴M̷̵E̶̸T̷̴H̸̷I̶̷N̷̸G̴̵ ̷E̶̴L̷̸S̶̵E̷ ̴I̷̶S̸ ̷H̷̸E̷̶R̸̷E̵', '[STATUS OVERRIDDEN]',
    '[STATUS DATA CORRUPTED]', '[UNKNOWN ENTITY DETECTED]', '[PRESENCE MODIFIED BY ███████]',
    '[ERROR: ORIGINAL STATUS UNAVAILABLE]', '[WARNING: UNAUTHORIZED PRESENCE]', '[SIGNAL LOST]',
    '[CONNECTION: █████████]', '[SOURCE: UNKNOWN]', '[AUTHOR: █████████]',
    '[MESSAGE INTERRUPTED]', '[MESSAGE INTERRUPTED] ̷̴D̷̸O̶̵ ̷N̷̴O̶̸T̷ ̸R̷E̵P̶L̴Y̷', '[PRESENCE MODIFIED BY ███████] I remember you.',
    '[STATUS OVERRIDDEN] ̷I̷ ̷C̷A̷N̷ ̷S̷E̷E̷ ̷Y̷O̷U̷', '[SOURCE: █████████] Something is awake.', '[ERROR: ORIGINAL STATUS UNAVAILABLE] ███████████',
]

# Shuffle-bag state for the status rotator. Each status is shown once before
# the current pool is reshuffled, preventing frequent repeats.
status_bag = []
status_bag_is_halloween = None


def get_next_status(active_statuses, is_halloween):
    global status_bag, status_bag_is_halloween

    # Rebuild the bag when switching between normal and Halloween statuses,
    # or when the current bag has been exhausted.
    if status_bag_is_halloween != is_halloween or not status_bag:
        status_bag = list(active_statuses)
        random.shuffle(status_bag)
        status_bag_is_halloween = is_halloween

    return status_bag.pop()


@tasks.loop(minutes=15)
async def change_status():
    halloween_active = is_halloween_active()
    active_statuses = halloween_status_list if halloween_active else status_list
    new_status = get_next_status(active_statuses, halloween_active)
    await bot.change_presence(activity=discord.CustomActivity(name=new_status))


@change_status.error # type: ignore[reportArgumentType]
async def change_status_error(error):
    await log_task_error(bot, "change_status", error)


# --- BUMP PERSISTENCE LOOP ---
@tasks.loop(minutes=2)
async def check_bump_timer():
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT remind_at, channel_id FROM bump_timer WHERE id = 1"
            ) as cursor:
                row = await cursor.fetchone()

            if not row:
                return

            remind_at = datetime.fromisoformat(row[0])
            now = datetime.now(timezone.utc)

            if now < remind_at:
                return

            # Bump reminders are only ever sent to the designated bump channel.
            channel = bot.get_channel(BUMP_CHANNEL_ID)

            if channel is None:
                try:
                    channel = await bot.fetch_channel(BUMP_CHANNEL_ID)
                except Exception as e:
                    await log_task_error(bot, "check_bump_timer / fetch channel", e, context=f"channel_id={BUMP_CHANNEL_ID}")
                    print(f"[BUMP LOOP ERROR]: Could not fetch channel {BUMP_CHANNEL_ID}: {e}")
                    return

            if channel is None:
                print(f"[BUMP LOOP ERROR]: No channel found for {BUMP_CHANNEL_ID}")
                return

            bump_role_id = "1295212860720418887"

            reminder_embed = discord.Embed(
                description=(
                    f"## *Loud alarm clock noises*\n\n"
                    f"*Two hours have passed since the last bump!*\n\n "
                    f"You can now bump our server by typing `/bump`!\n "
                    f"It helps us a lot by gaining more noticeability! "
                    f"<a:RedHearts:1109768412382642266> <a:PurpleHearts:1109768355390431323> "
                ),
                color=discord.Color.from_rgb(114, 0, 225)
            )

            try:
                # Check if the channel is a type that can actually receive messages
                if isinstance(channel, (discord.TextChannel, discord.Thread, discord.VoiceChannel)):
                    await channel.send(
                        content=f"<@&{bump_role_id}>",
                        embed=reminder_embed
                    )
                else:
                    print(f"[BUMP LOOP ERROR]: Channel {channel.id} is not a text channel.")

                print(f"[BUMP TIMER SENT]: channel={channel.id}")

                await db.execute("DELETE FROM bump_timer WHERE id = 1")
                await db.commit()

            except discord.HTTPException as e:
                # Catch the Rate Limit error specifically
                if e.status == 429:
                    print(f"[RATE LIMIT CAUGHT]: Backing off for 15 minutes.")
                    # Push the reminder back 15 minutes in the database to stop the spam loop
                    new_remind = (now + timedelta(minutes=15)).isoformat()
                    await db.execute("UPDATE bump_timer SET remind_at = ? WHERE id = 1", (new_remind,))
                    await db.commit()
                else:
                    print(f"[BUMP SEND ERROR]: {type(e).__name__}: {e}")
                    
            except Exception as e:
                await log_task_error(bot, "check_bump_timer / send", e)
                print(f"[BUMP SEND ERROR]: {type(e).__name__}: {e}")
                return

    except Exception as e:
        print(f"[BUMP LOOP ERROR]: {e}")
        await log_task_error(bot, "check_bump_timer", e)
        await asyncio.sleep(60)


@check_bump_timer.error # type: ignore[reportArgumentType]
async def check_bump_timer_error(error):
    await log_task_error(bot, "check_bump_timer (task callback)", error)


# --- STARGAZING ALERTS SETUP ---
eastern = pytz.timezone("US/Eastern")
scheduled_time = time(hour=12, minute=0, tzinfo=eastern)

@tasks.loop(time=scheduled_time)
async def stargazing_alert():
    channel_id = 593416487499333653 
    channel = bot.get_channel(channel_id)
    
    if channel:
        url = "https://api.rss2json.com/v1/api.json?rss_url=https%3A%2F%2Fin-the-sky.org%2Frss.php%3Ffeed%3Dupcoming"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        item = data['items'][0]
                        title = item['title']
                        link = item['link']
                        description = re.sub('<[^<]+?>', '', item['description'])[:300] + "..."

                        embed = discord.Embed(
                            title="Tonight's Cosmic Event 🌌🔭",
                            description=f"**{title}**\n\n{description}\n\n🔗 [View Event Details]({link})",
                            color=discord.Color.dark_purple()
                        )
                        embed.set_thumbnail(url="https://i.imgur.com/83S8Z6H.png")
                        embed.set_footer(text="Source: in-the-sky.org | Keep looking up, Stargazers! 🔭")
                        

                        if isinstance(channel, (discord.TextChannel, discord.Thread, discord.VoiceChannel)):
                            await channel.send(embed=embed)
                        else:
                            print(f"[STARGAZING ERROR]: Channel is not a sendable text channel.")
                            
        except Exception as e:
            print(f"Error in stargazing_alert loop: {e}")
            await log_task_error(bot, "stargazing_alert", e)


@stargazing_alert.error # type: ignore[reportArgumentType]
async def stargazing_alert_error(error):
    await log_task_error(bot, "stargazing_alert (task callback)", error)


# --- EVENTS ---
@bot.event
async def on_ready():
    bot_name = bot.user.name if bot.user else "Bot"
    print(f"Logged in as {bot_name}")
    await init_bump_db() 
    await init_fun_db() 
    
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

    ctx = None  # ✅ FIX: always define ctx first

    # --- COMMAND HANDLING ---
    if message.content.startswith("-"):
        ctx = await bot.get_context(message)

        if ctx and ctx.valid:
            await bot.process_commands(message)
            return

    # --- TAG SYSTEM ---
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
                        await message.channel.send(
                            content=text_caption,
                            file=discord.File(f)
                        )
                    return

            await message.channel.send(content)
            return

    # --- BUMP DETECTION ---
    # Only process Disboard bumps that occur in the designated bump channel.
    # Disboard still handles its own /bump command elsewhere; Enceladus simply
    # ignores those bump-result messages outside the approved channel.
    if message.author.id == 302050872383242240 and message.channel.id == BUMP_CHANNEL_ID:
        await asyncio.sleep(2)

        if not message.embeds:
            return

        embed = message.embeds[0]

        embed_parts = [
            embed.title or "",
            embed.description or "",
            embed.footer.text if embed.footer else "",
            embed.author.name if embed.author else ""
        ]

        for field in embed.fields:
            embed_parts.append(field.name or "")
            embed_parts.append(field.value or "")

        embed_text = " ".join(embed_parts).lower()

        is_bump = any(x in embed_text for x in [
            "bump done",
            "thanks for bumping",
            "bumped the server",
            "you can bump again",
            "bump successful",
            "bump done!",
            "disboard: the public server list"
        ])

        if not is_bump:
            return

        user_obj = None

        # FIX: safely check attribute existence
        if hasattr(message, "interaction_metadata") and message.interaction_metadata:
            user_obj = message.interaction_metadata.user

        if not user_obj and message.content:
            match = re.search(r"<@!?(\d+)>", message.content)
            if match:
                user_id = int(match.group(1))
                user_obj = message.guild.get_member(user_id)

        # Leveling requires a guild Member, but interaction metadata can
        # provide a plain discord.User. Resolve the user back to this
        # guild before passing them to the leveling cog.
        if user_obj and message.guild:
            resolved_member = message.guild.get_member(user_obj.id)

            if resolved_member is None:
                try:
                    resolved_member = await message.guild.fetch_member(user_obj.id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    resolved_member = None

            if resolved_member is not None:
                user_obj = resolved_member

        user_mention = user_obj.mention if user_obj else "there"

        thanks_text = (
            f"Thank you so much for bumping our server, {user_mention}! It helps us a ton! <:CoolEevee:1109771250634592306> 💜\n"
            f"You've earned **400 XP** for the server bump! You can come back in two hours to do it again! <a:DancingEevee:1109781719315398766>"
        )

        await message.channel.send(thanks_text)

        if user_obj:
            leveling_cog = bot.get_cog("Leveling")
            add_xp_func = getattr(leveling_cog, "add_xp", None)
            
            if add_xp_func:
                await add_xp_func(user_obj, 400)
            else:
                print("❌ Leveling cog not found. Couldn't award bump XP.")

        remind_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

        print(f"[BUMP TIMER SET]: remind_at={remind_time}, channel={message.channel.id}")

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO bump_timer (id, remind_at, channel_id) VALUES (1, ?, ?)",
                (remind_time, message.channel.id)
            )
            await db.commit()

    # Prefix commands are already processed near the top of this handler.
    # Do not process them a second time here, because an invalid prefix-like
    # message such as "-#" would otherwise raise CommandNotFound and trigger
    # the centralized error system.
    if not message.content.startswith("-"):
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
                f"We hope you enjoy your stay at The Cosmic Lair! Feel free to invite friends, we won't bite!\n\n"
                f"*(Remember to check Post-Join Questions over at 'Channels & Roles' option on the server channel menu at the very top to see more channels we have to offer!)*"
            ),
            color=discord.Color.from_rgb(114, 0, 225)
        )
        embed.set_author(name=f"{member.name}", icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=DRAGON_IMAGE_URL)
        embed.set_footer(text=f"You are our {ordinal_count} member! Congrats!")

        try:
            if isinstance(channel, (discord.TextChannel, discord.Thread, discord.VoiceChannel)):
                await channel.send(content=content_text, embed=embed)
            else:
                print(f"[JOIN LOG ERROR]: Channel is not a sendable text channel.")
        except (discord.Forbidden, discord.HTTPException) as e:
            print(f"[JOIN LOG ERROR]: {e}")

    try:
        await asyncio.sleep(10)
    finally:
        recent_joins.discard(member.id)

@bot.event
async def on_member_remove(member):
    if member.id in recent_leaves:
        return
    recent_leaves.add(member.id)

    channel = bot.get_channel(1117377155496673330)
    log_channel = bot.get_channel(1352095872812318760)
    count = member.guild.member_count

    # Snapshot the user's leveling progress before departure cleanup can remove it.
    level = 0
    xp = 0
    leveling_db_path = "/app/data/levels.db" if os.path.exists("/app/data") else "levels.db"

    try:
        async with aiosqlite.connect(leveling_db_path) as db:
            async with db.execute(
                "SELECT level, xp FROM users WHERE user_id = ?",
                (member.id,),
            ) as cursor:
                progress_row = await cursor.fetchone()

        if progress_row:
            level = int(progress_row[0] or 0)
            xp = int(progress_row[1] or 0)
    except Exception as e:
        await log_event_error(bot, "on_member_remove / leveling lookup", e, context=f"member_id={member.id}")
        print(f"[LEAVE XP LOG ERROR]: Could not read leveling data for {member.id}: {e}")

    # Public goodbye message — keep the leveling snapshot out of the public channel.
    if channel:
        content_text = f"Sorry to see you go, {member.name}!"
        embed = discord.Embed(
            title="We're sorry to see you go... 😔",
            description=(
                f"It looks like {member.mention} has left the server. "
                f"We hope to see you again soon, and please be safe out there!"
            ),
            color=discord.Color.from_rgb(114, 0, 225)
        )
        embed.set_author(name=f"{member.name}", icon_url=member.display_avatar.url)
        embed.set_footer(text=f"We now have {count} members.")

        try:
            if isinstance(channel, (discord.TextChannel, discord.Thread, discord.VoiceChannel)):
                await channel.send(content=content_text, embed=embed)
            else:
                print(f"[LEAVE LOG ERROR]: Channel is not a sendable text channel.")
        except (discord.Forbidden, discord.HTTPException) as e:
            print(f"[LEAVE LOG ERROR]: {e}")

    # Internal log — keep the leveling snapshot here so it is preserved for staff.
    if log_channel:
        snapshot_embed = discord.Embed(
            title="Member Leveling Snapshot",
            description=f"**{member.name}** ({member.mention}) has left the server.",
            color=discord.Color.from_rgb(114, 0, 225)
        )
        snapshot_embed.set_author(name=f"{member.name}", icon_url=member.display_avatar.url)
        snapshot_embed.add_field(
            name="Level",
            value=f"**{level:,}**",
            inline=True
        )
        snapshot_embed.add_field(
            name="XP",
            value=f"**{xp:,}**",
            inline=True
        )
        snapshot_embed.set_footer(text=f"Member count: {count} • User ID: {member.id}")

        try:
            if isinstance(log_channel, (discord.TextChannel, discord.Thread, discord.VoiceChannel)):
                await log_channel.send(embed=snapshot_embed)
            else:
                print(f"[LEAVE XP LOG ERROR]: Channel is not a sendable text channel.")
        except (discord.Forbidden, discord.HTTPException) as e:
            print(f"[LEAVE XP LOG ERROR]: Could not send leveling snapshot: {e}")

    try:
        await asyncio.sleep(10)
    finally:
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
                    f"Thank you so much, {after.name}! You have received our supporter role!\n\n "
                    f"We are now at {boost_count} boosts! 🌌💜"
                ),
                color=discord.Color.from_rgb(114, 0, 225)
            )
            embed.set_author(name=f"{after.name}", icon_url=after.display_avatar.url)
            embed.set_footer(text=f"We only need {next_level} boosts till our next level!")
            
            if isinstance(channel, (discord.TextChannel, discord.Thread, discord.VoiceChannel)):
                await channel.send(content=content_text, embed=embed)
            else:
                print(f"[BOOST LOG ERROR]: Channel is not a sendable text channel.")


VAULT_CHANNEL_ID = 1496628909570265199
VAULT_THRESHOLD = 3
EXCLUDED_CHANNELS = [593389789558865931, 598883099987673088, 1484487011933884509, 1352415256584130590, 1306821711970435122, 935876805607444510, 1118027416443564042, 1491230190469120010, 1117412987788075038] 
EXCLUDED_CATEGORIES = [1295664420294361179, 1353577090099712070, 593406939111751721, 593413698085978132, 1474514782605541537] 

@bot.event
async def on_raw_reaction_add(payload):
    if str(payload.emoji) != "⭐":
        return

    channel = bot.get_channel(payload.channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(payload.channel_id)
        except Exception as e:
            await log_event_error(bot, "on_raw_reaction_add / fetch channel", e, context=f"channel_id={payload.channel_id}")
            print(f"[VAULT ERROR]: Could not fetch channel {payload.channel_id}: {e}")
            return

    # Check if channel is an actual server text-based channel or thread
    if not isinstance(channel, (discord.TextChannel, discord.Thread, discord.VoiceChannel)):
        return

    # Now it is completely safe to check server properties like NSFW and categories
    is_nsfw = channel.is_nsfw() if hasattr(channel, "is_nsfw") else False
    category_id = getattr(channel, "category_id", None)

    if is_nsfw or channel.id in EXCLUDED_CHANNELS or category_id in EXCLUDED_CATEGORIES:
        return


    try:
        message = await channel.fetch_message(payload.message_id)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
        print(f"[VAULT ERROR]: Could not fetch message {payload.message_id}: {e}")
        return

    async with _vault_lock:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT message_id FROM vaulted_messages WHERE message_id = ?",
                (message.id,)
            ) as cursor:
                if await cursor.fetchone():
                    return

            reaction = discord.utils.get(message.reactions, emoji="⭐")
            if reaction is None:
                return

            try:
                users = [user async for user in reaction.users()]
            except (discord.Forbidden, discord.HTTPException) as e:
                print(f"[VAULT ERROR]: Could not inspect star reactions for {message.id}: {e}")
                return

            valid_star_count = len([u for u in users if u.id != message.author.id])
            if valid_star_count < VAULT_THRESHOLD:
                return

            vault_channel = bot.get_channel(VAULT_CHANNEL_ID)
            if vault_channel is None:
                try:
                    vault_channel = await bot.fetch_channel(VAULT_CHANNEL_ID)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
                    print(f"[VAULT ERROR]: Could not access vault channel {VAULT_CHANNEL_ID}: {e}")
                    return

            embed = discord.Embed(
                description=message.content,
                color=discord.Color.gold(),
                timestamp=message.created_at
            )
            embed.set_author(
                name=message.author.display_name,
                icon_url=message.author.display_avatar.url
            )
            embed.add_field(name="Original", value=f"[Jump to Message]({message.jump_url})")

            if message.attachments:
                embed.set_image(url=message.attachments[0].url)

            embed.set_footer(text=f"ID: {message.id} | Enceladus Vault")

            try:
                if isinstance(vault_channel, (discord.TextChannel, discord.Thread, discord.VoiceChannel)):
                    await vault_channel.send(embed=embed)
                else:
                    print(f"[VAULT ERROR]: Vault channel is not a sendable text channel.")
                    
                await db.execute(
                    "INSERT INTO vaulted_messages (message_id) VALUES (?)",
                    (message.id,)
                )

                await db.commit()
            except (discord.Forbidden, discord.HTTPException, aiosqlite.Error) as e:
                await db.rollback()
                print(f"[VAULT ERROR]: Failed to archive message {message.id}: {e}")


# --- COSMIC COMMANDS ---

@bot.tree.command(name="nasa", description="View NASA's Astronomy Picture of the Day!")
async def nasa(interaction: discord.Interaction):
    api_key = os.getenv('NASA_API_KEY', 'DEMO_KEY')
    url = f"https://api.nasa.gov/planetary/apod?api_key={api_key}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=ClientTimeout(total=10)) as response:
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
                    title=f"{title} 🌌", 
                    description=f"{desc}\n\n🔗 [View on NASA APOD]({page_url})", 
                    color=discord.Color.blue()
                )
                
                if media_type == 'video':
                    if img_url:
                        current_desc = embed.description or ""
                        embed.description = current_desc + f"\n\n**Watch the video here:**\n{img_url}"
                elif img_url:
                    embed.set_image(url=img_url)
                
                embed.set_footer(text="Provided by NASA APOD API | Keep looking up, Stargazers! 🔭")
                await interaction.response.send_message(embed=embed)

@bot.tree.command(name="bing", description="View today's Bing wallpaper!")
async def bing(interaction: discord.Interaction):
    url = "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=en-US"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=ClientTimeout(total=10)) as response:
            if response.status == 200:
                data = await response.json()
                images = data.get('images') or []
                if not images:
                    await interaction.response.send_message(
                        "❌ Bing didn't return a wallpaper right now. Please try again later and report to staff if the issue persists.",
                        ephemeral=True
                    )
                    return

                image = images[0]
                img_path = image.get('url')
                if not img_path:
                    await interaction.response.send_message(
                        "❌ Bing returned an incomplete wallpaper result. Please try again later and report to staff if the issue persists.",
                        ephemeral=True
                    )
                    return

                img_url = f"https://www.bing.com{img_path}"
                copyright_info = image.get('copyright', 'Bing Wallpaper')
                copyright_link = image.get('copyrightlink', 'https://www.bing.com/')

                embed = discord.Embed(
                    title="Today's Bing Wallpaper", 
                    description=f"{copyright_info}\n\n🔗 [Explore Location]({copyright_link})", 
                    color=discord.Color.green()
                )
                embed.set_image(url=img_url)
                await interaction.response.send_message(embed=embed)

@bot.tree.command(name="moon", description="Check the current moon phase!")
async def moon(interaction: discord.Interaction):
    url = "https://wttr.in/?format=%m" 
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=ClientTimeout(total=10)) as response:
            if response.status == 200:
                phase_emoji = await response.text()
                await interaction.response.send_message(f"The current moon phase is: **{phase_emoji}**")
            else:
                await interaction.response.send_message("❌ Can't see the moon right now! Please report to staff if the issue persists. ☁️")

@bot.tree.command(name="weather", description="Get the current weather for a specific city!")
async def weather(interaction: discord.Interaction, city: str):
    url = f"https://wttr.in/{city}?format=3"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=ClientTimeout(total=10)) as response:
            if response.status == 200:
                weather_report = await response.text()
                await interaction.response.send_message(f"**Current Weather:**\n{weather_report}")
            else:
                await interaction.response.send_message(f"❌ Couldn't find the weather for '{city}'. Please report to staff if the issue persists.")

@bot.tree.command(name="iss", description="Track the International Space Station's current location!")
async def iss(interaction: discord.Interaction):
    await interaction.response.defer()
    url = "https://api.wheretheiss.at/v1/satellites/25544"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    lat = data.get('latitude')
                    lon = data.get('longitude')
                    velocity = data.get('velocity')
                    maps_url = f"https://www.google.com/maps?q={lat},{lon}&t=k"
                    
                    embed = discord.Embed(
                        title="ISS Current Location",
                        description=f"The ISS is flying over:\n\n🔗 [View on Live Map]({maps_url})",
                        color=discord.Color.dark_blue()
                    )
                    embed.add_field(name="Latitude", value=f"{lat:.4f}", inline=True)
                    embed.add_field(name="Longitude", value=f"{lon:.4f}", inline=True)
                    embed.add_field(name="Velocity", value=f"{velocity:.2f} km/h", inline=False)
                    await interaction.followup.send(embed=embed)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, TypeError) as e:
            print(f"[ISS ERROR]: {type(e).__name__}: {e}")
            await interaction.followup.send("❌ The ISS service is unavailable right now. Please try again later and report to staff if the issue persists.")

def get_next_midnight_reset():
    et = pytz.timezone("US/Eastern")
    now = datetime.now(et)

    reset_time = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    ) + timedelta(days=1)

    return int(reset_time.timestamp())


def get_next_fortune_reset():
    et = pytz.timezone("US/Eastern")
    now = datetime.now(et)

    reset_time = now.replace(
        hour=6,
        minute=0,
        second=0,
        microsecond=0
    )

    if now >= reset_time:
        reset_time += timedelta(days=1)

    return int(reset_time.timestamp())

@bot.command()
@commands.has_permissions(administrator=True)
async def resetbump(ctx):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM bump_timer WHERE id = 1")
        await db.commit()
    await ctx.send("Bump timer cleared!")

class HelpView(discord.ui.View):
    def __init__(self, bot_instance, author, pages):
        super().__init__(timeout=120)
        self.bot_instance = bot_instance
        self.author = author
        self.pages = pages
        self.current_page = 0
        self.max_pages = len(pages)
        self.update_buttons()

    def update_buttons(self):
        self.first_page.disabled = (self.current_page == 0) # type: ignore
        self.prev_page.disabled = (self.current_page == 0) # type: ignore
        self.next_page.disabled = (self.current_page >= self.max_pages - 1) # type: ignore
        self.last_page.disabled = (self.current_page >= self.max_pages - 1) # type: ignore

    def build_embed(self):
        embed = self.pages[self.current_page]
        embed.set_footer(text=f"Enceladus Station • Page {self.current_page + 1}/{self.max_pages} | Use /help or -protocols to open your own command directory.")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.author.id:
            return True
        await interaction.response.send_message("This isn't your protocol command. Use `/help` or `-protocols` to open your own.", ephemeral=True)
        return False

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.primary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = self.max_pages - 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


@bot.hybrid_command(name="help", aliases=["protocols", "directory"], description="Displays the full directory of Enceladus' commands!")
async def help_command(ctx):
    """The central directory for all of Enceladus' station functions."""

    daily_reset = get_next_midnight_reset()
    fortune_reset = get_next_fortune_reset()

    pages = [
        discord.Embed(
            title="*Enceladus Command Directory - Leveling & Social* 💬",
            description="Level up, socialize, and customize your rank card with these commands!",
            color=discord.Color.from_rgb(138, 43, 226)
        ).add_field(
            name="### ***Leveling & Social*** 💬",
            value=(
                "`/customize <bar_color> [bg_url] <font> <glow>` - Personalize your rank card aesthetics!\n"
                "`/hug <member>` - Give a warm, soft hug!\n"
                "`/rank <member>` - View your level, XP, and rank card.\n"
                "`/slap <member>` - Slap someone with a random object!\n"
                f"`/set_birthday <month> <day>` - Register your birthday for a special role and ping on your special day! Daily checks at <t:{daily_reset}:t>.\n"
                "`/upcoming_birthdays` - See upcoming server birthdays.\n"
                "`/leaderboard` `-levelscores` - View top members and scroll through active users."
            ),
            inline=False
        ),
        discord.Embed(
            title="*Enceladus Command Directory - Fun & Games (1)* 👾",
            description="Fun rating commands, fortune cookies, and other random tools!",
            color=discord.Color.from_rgb(138, 43, 226)
        ).add_field(
            name="### ***Fun & Games (1)*** 👾",
            value=(
                "`/aurarate` - Check you or a member's aura.\n"
                "`/bing` - View today's Bing wallpaper.\n"
                "`/blackhole <text>` - Send a message into the void.\n"
                "`/choose <opt1, opt2>` - Let Enceladus decide choices for you!\n"
                "`/coinflip` - Supernova (heads) or blackhole (tails)!\n"
                "`/coolrate` - See how cool you or a member is!\n"
                "`/cringerate` - Find out how cringe you or a member is!\n"
                f"`/dragonrider` `-ft` `-flytest` - Attempt your daily Dragonrider Test and try to earn your license! Resets daily at <t:{daily_reset}:t>.\n"
            ),
            inline=False
        ),
        discord.Embed(
            title="*Enceladus Command Directory - Fun & Games (2)* 👾",
            description="Fun rating commands, fortune cookies, and other random tools!",
            color=discord.Color.from_rgb(138, 43, 226)
        ).add_field(
            name="### ***Fun & Games (2)*** 👾",
            value=(
                "`/fnfmod <query>` - Search GameBanana for FNF mods.\n"
                "`/fnfsong <song>` - Find FNF tracks on YouTube.\n"
                f"`/fortune` - Receive a daily fortune cookie fortune and XP! Resets daily at <t:{fortune_reset}:t>.\n"
                "🥠 Common | ✨ Uncommon | 🌙 Rare | (Legendary/Void have custom announcements that are distinctive!)\n"
                "-# *(Disclaimer: the fortunes can be negative, sad, etc. to keep them realistic. It's just a little game, don't take it too seriously!)*\n\n"
                "`/freakyrate` - Discover how freaky you or a member is!\n"
                "`/furryrate` - Determine how furry you or a member is!\n"
                "`/horoscope <sign>` - Check your daily horoscope.\n"
                "`/iqrate` - Get a random IQ score for you or a member!\n"
                "`/iss` - Track the International Space Station's current position.\n"
            ),
            inline=False
        ),
        discord.Embed(
            title="*Enceladus Command Directory - Fun & Games (3)* 👾",
            description="Fun rating commands, fortune cookies, and other random tools!",
            color=discord.Color.from_rgb(138, 43, 226)
        ).add_field(
            name="### ***Fun & Games (3)*** 👾",
            value=(
                "`/mock <text>` - mAkE yOuR tExT lOoK lIkE tHiS.\n"
                "`/moon` - Check the current moon phase.\n"
                "`/nasa` - See NASA's Astronomy Picture of the Day!\n"
                f"`/pullsword` `-ps` - Attempt to pull the ancient Cosmic Blade and claim the Bladebearer title! Resets daily at <t:{daily_reset}:t>.\n"
                "`/relic <question>` - Consult the Astral Relic for answers (Magic 8-Ball)!\n"
                "`/roll <sides>` - Roll a die! Choose between 2 to 20 sides.\n"
                "`/spacedata` - Pull real-time data on a random celestial body.\n"
                "`/weather <city>` - Get the current weather for a city.\n"
            ),
            inline=False
        ),
        discord.Embed(
            title="*Enceladus Command Directory - Economy & Exploration* 🚀",
            description="Manage your profile, explore the outer rims of the galaxy, collect salvage, and spend your hard-earned Stardust!",
            color=discord.Color.from_rgb(138, 43, 226)
        ).add_field(
            name="### ***Exploration & Profile*** 🚀",
            value=(
                "`/background equip <background>` - Equip an unlocked background for your profile.\n"
                "`/bio <text>` - Set the biography displayed on your profile.\n"
                "`/heal <item>` - Use a healing item to restore HP.\n"
                "`/mine` - Deploy your mining laser to collect Stardust and discover rare loot.\n"
                "`/profile [member]` - View your profile, level, XP, Stardust, companion, and environment.\n"
                "`/revive` - Use any revival item to return at half health or full health.\n"
                "`/scavenge` - Search derelict wreckage for salvage, Stardust, and rare findings.\n"
                "`/status` - Check your health, exploration charges, cooldowns and more.\n"
            ),
            inline=False
        ).add_field(
            name="### ***Economy & Inventory*** 💰",
            value=(
                "`/claimlegacy` - Claim your one-time legacy Stardust payout from before the **Frontier update.**\n"
                "`/inventory` - Open your inventory and view collected items, materials, salvage, vouchers and more.\n"
                "`/item <category> <item>` - Inspect an item from the catalog.\n"
                "`/shop` - Browse the Trading Post.\n"
                "`/shop buy <item_id>` - Purchase an item from the shop.\n"
                "`/shop sell <item>` - Sell salvaged space junk for Stardust.\n"
                "`/use <item_id> [target]` - Use a consumable or activate an item from your inventory.\n"
            ),
            inline=False
        ),
        discord.Embed(
            title="*Enceladus Command Directory - Misc. Server Tools* 🛠️",
            description="Community tags and utility commands!",
            color=discord.Color.from_rgb(138, 43, 226)
        ).add_field(
            name="### ***Server Tools*** 🛠️",
            value=(
                "`-list` - List all available community tags to use in chats.\n"
                "`-[tagname]` - View a saved community tag.\n"
                "`/echo <msg> [channel (optional)]` - Make Enceladus speak! **Don't use to bypass rules.**\n"
                "`-qr <report reason>` - Make a silent quick report to staff about a member.\n"
            ),
            inline=False
        )
    ]

    # Dynamically append 'Station Admin' page if the user is an administrator.
    if ctx.author.guild_permissions.administrator:
         pages.append(
            discord.Embed(
                title="*Enceladus Command Directory - Admin Tools* 🔨",
                description="Administrative controls for authorized staff.",
                color=discord.Color.from_rgb(138, 43, 226)
            ).add_field(
                name="### ***Admin Tools***",
                value=(
                    "`/admin` - Open the administrator control panel and choose from all available administrative actions below:\n"
                    "Reset Bump Timer\n"
                    "Set Fortune Streak\n"
                    "Set XP\n"
                    "Set Level\n"
                    "Add XP\n"
                    "Sync Levels\n"
                    "Purge Left Members\n"
                    "Reset\n"
                    "Font Preview Setup\n"
                    "Send Verify Panel\n"
                    "Send NSFW Verification Panel"
                ),
                inline=False
            )
        )

    view = HelpView(bot, ctx.author, pages)
    embed = view.build_embed()
    
    if ctx.interaction:
        await ctx.interaction.response.send_message(embed=embed, view=view)
    else:
        await ctx.send(embed=embed, view=view)

@bot.event
async def on_command_error(ctx, error):
    # Discord/Markdown syntax such as "-#" can look like a prefix command
    # to discord.py. Ignore this harmless formatting-only case instead of
    # logging it as an Enceladus error or sending the user an error message.
    if isinstance(error, commands.CommandNotFound) and getattr(ctx, "invoked_with", "") == "#":
        return

    error_id = await log_command_error(bot, ctx, error)
    await send_member_error_message(ctx, error_id)

@bot.tree.error
async def on_app_command_error(interaction, error):
    error_id = await log_app_command_error(bot, interaction, error)
    await send_member_error_message(interaction, error_id)

async def main():
    async with bot:
        token = os.getenv('DEV_TOKEN') or os.getenv('DISCORD_TOKEN') 
        if token:
            await bot.start(token)
        else:
            print("No bot token found in environment variables! Please set 'DEV_TOKEN' or 'DISCORD_TOKEN`.")

if __name__ == "__main__":
    asyncio.run(main())
