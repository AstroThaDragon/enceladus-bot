import os
import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import random
import time
from easy_pil import Editor, Canvas, Font, load_image_async
import json
from typing import Optional
import io
import aiohttp
from PIL import Image

class ResetConfirm(discord.ui.View):
    def __init__(self, cog, member):
        super().__init__(timeout=30)
        self.cog = cog
        self.member = member

    @discord.ui.button(label="Confirm Reset", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with aiosqlite.connect(self.cog.db_path) as db:
            await db.execute("DELETE FROM users WHERE user_id = ?", (self.member.id,))
            await db.commit()
        await interaction.response.edit_message(content=f"♻️ **{self.member.name}** has been reset to Level 0.", view=None)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Reset cancelled.", view=None)
        self.stop()

async def load_custom_image(url):
    async with aiohttp.ClientSession() as session:
        # This 'User-Agent' makes the bot look like a real person to Imgur
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.read()
                return io.BytesIO(data)
            else:
                print(f"Image Load Failed: Status {response.status}")
                return None

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # --- Fixed Database Pathing ---
        # We check for the absolute path first to ensure we are in the Railway Volume
        if os.path.exists('/app/data'):
            self.db_path = '/app/data/levels.db'
            print(f"LevelingCog: Using PRODUCTION database at {self.db_path}")
        else:
            self.db_path = 'levels.db'
            print(f"LevelingCog: Using LOCAL database at {self.db_path}")

        # ... (rest of your configuration stays exactly the same)

        # --- CONFIGURATION ---
        self.ANNOUNCEMENT_CHANNEL_ID = 1306602160527507456 
        self.BOOSTER_ROLE_ID = 927505358736470047          
        self.WATCHLIST_ROLE_ID = 928584760748564570       
        
        self.NO_XP_CHANNELS = [1117403991266041906, 593398659530489858, 1306821711970435122, 1496628909570265199, 1473398974508437645, 1352415256584130590, 1117391981627318363, 1512300086057631925, 1510687468842782720, 1306602160527507456] 
        self.NO_XP_CATEGORIES = [593406939111751721, 593413698085978132]

        self.level_roles = {
            100: 1296961266627121223, 95: 1501609710573453324, 90: 1501609557804187781, 
            85: 1501609375318675657, 80: 1501609179566313522, 75: 1501608976507211920, 
            70: 1501608777613312020, 65: 1501608443356643328, 60: 1501608145582031000, 
            55: 1501607815893094552, 50: 1296959776667730143, 45: 1296959689367617660, 
            40: 1296959665455890483, 35: 1296959633436708897, 30: 1296959584820264980, 
            25: 1295861213695311935, 20: 1295861175388475463, 15: 1295861144996806726, 
            10: 1295861102483210260, 5: 1295861061995597844, 1: 1295860897532608615,
            0: 1501969001792798841
        }

        self.cooldowns = {}

    async def cog_load(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('PRAGMA journal_mode=WAL')
            await db.execute('''CREATE TABLE IF NOT EXISTS users 
                            (user_id INTEGER PRIMARY KEY, 
                             xp INTEGER DEFAULT 0, 
                             level INTEGER DEFAULT 0,
                             bar_color TEXT DEFAULT '#8a2be2',
                             bg_url TEXT DEFAULT 'default')''')

            try:
                await db.execute("ALTER TABLE users ADD COLUMN bar_color TEXT DEFAULT '#8a2be2'")
            except:
                pass 

            try:
                await db.execute("ALTER TABLE users ADD COLUMN bg_url TEXT DEFAULT 'default'")
            except:
                pass

            try:
                await db.execute("ALTER TABLE users ADD COLUMN font_choice TEXT DEFAULT 'comic'")
            except:
                pass

            try:
                await db.execute("ALTER TABLE users ADD COLUMN booster_glow TEXT DEFAULT 'on'")
            except:
                pass
                
            await db.commit()

    def get_xp_for_level(self, level):
        """
        The 'Infinite Slide' Formula. 
        One equation for Level 1-100. 
        Zero tier jumps, just a perfectly smooth difficulty curve.
        """
        if level <= 0: return 0
        
        # Total XP = (68 * L^2) + (150 * L) - 93
        # Level 1 starts at 125 XP.
        # Level 100 ends at 694,907 XP (~24.8k messages).
        return (68 * (level**2)) + (150 * level) - 93

    async def _update_member_roles(self, member, new_level):
        guild = member.guild
        new_role_id = None
        
        is_milestone = new_level in self.level_roles
        
        for lvl, rid in sorted(self.level_roles.items(), reverse=True):
            if new_level >= lvl:
                new_role_id = rid
                break

        if new_role_id is not None:
            new_role = guild.get_role(new_role_id)
            if new_role and new_role not in member.roles:
                await member.add_roles(new_role)
                
                # ONLY send the announcement if they hit the exact milestone level
                if is_milestone and new_level > 0:
                    announcement_channel = self.bot.get_channel(self.ANNOUNCEMENT_CHANNEL_ID)
                    if announcement_channel:
                        await announcement_channel.send(
                            f"🌌 **Congratulations, {member.mention}!** "
                            f"You've reached level {new_level} and earned the **{new_role.name}** role! Keep soaring! 🚀"
                        )
            
            roles_to_remove = [
                guild.get_role(rid) for lvl, rid in self.level_roles.items() 
                if rid != new_role_id and guild.get_role(rid) in member.roles
            ]
            if roles_to_remove:
                await member.remove_roles(*[r for r in roles_to_remove if r])

    async def add_xp(self, member: discord.Member, amount: int):
        """Internal helper to award XP from external events like Bumping."""
        if member.bot: return

        user_id = member.id
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT xp, level FROM users WHERE user_id = ?", (user_id,)) as cursor:
                result = await cursor.fetchone()

            if result is None:
                # If they aren't in the DB yet, start them at Level 0 + the reward
                xp, level = amount, 0
                await db.execute("INSERT INTO users (user_id, xp, level) VALUES (?, ?, ?)", (user_id, xp, level))
            else:
                xp, level = result
                new_xp = xp + amount
                
                # Level up logic
                temp_level = level
                while new_xp >= self.get_xp_for_level(temp_level + 1):
                    temp_level += 1
                
                if temp_level > level:
                    await self._update_member_roles(member, temp_level)
                    await db.execute("UPDATE users SET xp = ?, level = ? WHERE user_id = ?", (new_xp, temp_level, user_id))
                else:
                    await db.execute("UPDATE users SET xp = ? WHERE user_id = ?", (new_xp, user_id))
            
            await db.commit()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot: return
        # Automatically give Level 0 role on join
        await self._update_member_roles(member, 0)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        if message.channel.id in self.NO_XP_CHANNELS or message.channel.category_id in self.NO_XP_CATEGORIES: return
        if message.author.get_role(self.WATCHLIST_ROLE_ID): return

        user_id = message.author.id
        current_time = time.time()
        if user_id in self.cooldowns and current_time - self.cooldowns[user_id] < 60: return 
        self.cooldowns[user_id] = current_time

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT xp, level FROM users WHERE user_id = ?", (user_id,)) as cursor:
                result = await cursor.fetchone()

            if result is None:
                starting_level = 0
                for level, role_id in sorted(self.level_roles.items(), reverse=True):
                    if role_id != 0 and message.author.get_role(role_id):
                        starting_level = level
                        break 
                xp, level = self.get_xp_for_level(starting_level), starting_level
                await db.execute("INSERT INTO users (user_id, xp, level) VALUES (?, ?, ?)", (user_id, xp, level))
            else:
                xp, level = result

            base_xp = random.randint(20, 50)
            if message.author.get_role(self.BOOSTER_ROLE_ID):
                base_xp = int(base_xp * 1.15) 
            
            new_xp = xp + base_xp
            temp_level = level
            while new_xp >= self.get_xp_for_level(temp_level + 1):
                temp_level += 1
            new_level = temp_level

            if new_level > level:
                await self._update_member_roles(message.author, new_level)
                await db.execute("UPDATE users SET xp = ?, level = ? WHERE user_id = ?", (new_xp, new_level, user_id))
            else:
                await db.execute("UPDATE users SET xp = ? WHERE user_id = ?", (new_xp, user_id))
            await db.commit()

    @commands.hybrid_command(name="rank", description="Check your or another member's level!")
    async def rank(self, ctx, member: discord.Member = None):
        await ctx.defer() 
        member = member or ctx.author
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT xp, level, bar_color, bg_url, fortune_streak, font_choice, booster_glow FROM users WHERE user_id = ?", 
                    (member.id,)
                ) as cursor:
                    result = await cursor.fetchone()
            
            if not result: return await ctx.send("This user hasn't earned any XP yet!")

            xp, level, bar_color, bg_url, fortune_streak, font_choice, booster_glow = result
            streak_number = fortune_streak or 0 # Default to 0 if null
            
            xp_start = self.get_xp_for_level(level)
            xp_end = self.get_xp_for_level(level + 1)
            
            # Math for the progress within the current level
            xp_within_level = xp - xp_start
            needed_for_level = xp_end - xp_start
            
            # Calculate percentage as a decimal (0.0 to 1.0)
            if needed_for_level > 0:
                percentage = xp_within_level / needed_for_level
            else:
                percentage = 0

            # CLAMP: This prevents the bar from breaking if the math goes weird
            percentage = max(0, min(percentage, 1))

            current_role_name = "No Rank"
            for lvl, rid in sorted(self.level_roles.items(), reverse=True):
                if rid == 0: continue
                role = member.get_role(rid)
                if role:
                    current_role_name = role.name
                    break

            dragon_rank = "0"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("https://draconova-production.up.railway.app/leaderboard", timeout=5) as response:
                        if response.status == 200:
                            data = await response.json()
                            for i, entry in enumerate(data):
                                if str(entry.get('user_id')) == str(member.id):
                                    dragon_rank = str(i + 1)
                                    break
            except: pass

            try:
                if bg_url and bg_url != 'default':
                    bg_data = await load_custom_image(bg_url)
                    if bg_data:
                        background = Editor(bg_data).resize((900, 270))
                    else:
                        background = Editor(Canvas((900, 270), color="#23272a"))
                elif os.path.exists("images/rank_template.png"):
                    background = Editor("images/rank_template.png")
                else:
                    background = Editor(Canvas((900, 270), color="#23272a"))
            except Exception as e:
                print(f"Background Error: {e}")
                background = Editor(Canvas((900, 270), color="#23272a"))

            avatar_image = await load_image_async(member.display_avatar.replace(format="png", size=256).url)
            avatar = Editor(avatar_image).resize((150, 150)).circle_image()
            background.paste(avatar, (50, 60))

            STARBORN_ROLE_ID = 1496031062218772510 
            OWNER_ROLE_ID = 891356074689560626    
            ADMIN_ROLE_ID = 593718477831929858    
            MOD_ROLE_ID = 1036583011405266974      

            badge_size = (45, 45)

            try:
                # 1. Starborn Icon (Top Left of Avatar)
                if member.get_role(STARBORN_ROLE_ID) and os.path.exists("icons/starborn_icon.png"):
                    starborn_icon = Editor("icons/starborn_icon.png").resize(badge_size)
                    # Coordinates place it slightly overlapping the top-left edge of the PFP
                    background.paste(starborn_icon, (30, 40)) 

                # 2. Staff Hierarchy (Bottom Left of Avatar)
                # The if/elif chain ensures only ONE of these ever shows up in this spot
                if member.get_role(OWNER_ROLE_ID) and os.path.exists("icons/owner_icon.png"):
                    owner_icon = Editor("icons/owner_icon.png").resize(badge_size)
                    # Coordinates place it slightly overlapping the bottom-left edge of the PFP
                    background.paste(owner_icon, (30, 170)) 
                elif member.get_role(ADMIN_ROLE_ID) and os.path.exists("icons/admin_icon.png"):
                    admin_icon = Editor("icons/admin_icon.png").resize(badge_size)
                    background.paste(admin_icon, (30, 170))
                elif member.get_role(MOD_ROLE_ID) and os.path.exists("icons/mod_icon.png"):
                    mod_icon = Editor("icons/mod_icon.png").resize(badge_size)
                    background.paste(mod_icon, (30, 170))

                # 3. Watchlist Icon (Top Center of Avatar, Invisible if unearned)
                if member.get_role(self.WATCHLIST_ROLE_ID) and os.path.exists("icons/watchlist_icon.png"):
                    watchlist_icon = Editor("icons/watchlist_icon.png").resize(badge_size)
                    # X=102 perfectly centers it over the 150px avatar. Y=10 tucks it right above.
                    background.paste(watchlist_icon, (102, 10))

            except Exception as e:
                print(f"Error drawing avatar badges: {e}")
            
            # 1. Set the default fallback path
            active_font_path = "fonts/ComicRelief-Regular.ttf"
            
            # 2. Route the path based on what they picked in the dropdown
            if font_choice == "bangers":
                active_font_path = "fonts/Bangers-Regular.ttf" 
            elif font_choice == "bytesized":
                active_font_path = "fonts/Bytesized-Regular.ttf"
            elif font_choice == "caveat":
                active_font_path = "fonts/Caveat-Regular.ttf"
            elif font_choice == "chewy":
                active_font_path = "fonts/Chewy-Regular.ttf"
            elif font_choice == "crafty":
                active_font_path = "fonts/CraftyGirls-Regular.ttf"
            elif font_choice == "creepster":
                active_font_path = "fonts/Creepster-Regular.ttf"
            elif font_choice == "dancing_script":
                active_font_path = "fonts/DancingScript-Regular.ttf"
            elif font_choice == "germania":
                active_font_path = "fonts/GermaniaOne-Regular.ttf"
            elif font_choice == "griffy":
                 active_font_path = "fonts/Griffy-Regular.ttf"
            elif font_choice == "henny_penny":
                active_font_path = "fonts/HennyPenny-Regular.ttf"
            elif font_choice == "lavishly_yours":
                active_font_path = "fonts/LavishlyYours-Regular.ttf"
            elif font_choice == "libertinus_math":
                active_font_path = "fonts/LibertinusMath-Regular.ttf"
            elif font_choice == "lobster_two":
                active_font_path = "fonts/LobsterTwo-Regular.ttf"
            elif font_choice == "medieval":
                active_font_path = "fonts/MedievalSharp-Regular.ttf"
            elif font_choice == "christmas":
                active_font_path = "fonts/MountainsOfChristmas-Regular.ttf"
            elif font_choice == "nosifer":
                active_font_path = "fonts/Nosifer-Regular.ttf"
            elif font_choice == "open_sans":
                active_font_path = "fonts/OpenSans-Regular.ttf"
            elif font_choice == "pixelify_sans":
                active_font_path = "fonts/PixelifySans-Regular.ttf"
            elif font_choice == "roboto":
                active_font_path = "fonts/Roboto-Regular.ttf"
            elif font_choice == "rye":
                active_font_path = "fonts/Rye-Regular.ttf"
            elif font_choice == "schoolbell":
                active_font_path = "fonts/Schoolbell-Regular.ttf"
            elif font_choice == "shadows_night":
                active_font_path = "fonts/ShadowsIntoNight-Regular.ttf"
            elif font_choice == "smokum":
                active_font_path = "fonts/Smokum-Regular.ttf"
            elif font_choice == "ubuntu":
                active_font_path = "fonts/Ubuntu-Regular.ttf"
                
            # 3. Apply the chosen path to all your sizes
            font_large = Font(active_font_path, size=45)
            font_medium = Font(active_font_path, size=32)
            font_small = Font(active_font_path, size=22)
            font_tiny = Font(active_font_path, size=20)
            
            st_col, st_width = (0, 0, 0), 2

            # --- TOP LEFT ICONS LOGIC (IMAGE BASED) ---
            # Moved to X: 230 (aligned left with your text) and Y: 45 (right above the role name)
            current_icon_x = 230 
            icon_y = 45
            icon_spacing = 60 # Increased spacing to accommodate bigger icons
            icon_size = (45, 45) # Bumped up from 30x30!
            
            SWORD_ROLE_ID = 1505077643567956069
            DRAGON_ROLE_ID = 1505083974509269074

            try:
                # Helper function to safely lower opacity of unearned icons by 70%
                def get_icon(path, earned):
                    img = Image.open(path).convert("RGBA")
                    if not earned:
                        r, g, b, a = img.split()
                        a = a.point(lambda p: p * 0.3) # 0.3 = 30% visible
                        img.putalpha(a)
                    return Editor(img).resize(icon_size)

                # 1. Sword Icon
                if os.path.exists("icons/sword_icon.png"):
                    has_sword = bool(member.get_role(SWORD_ROLE_ID))
                    sword_icon = get_icon("icons/sword_icon.png", has_sword)
                    background.paste(sword_icon, (current_icon_x, icon_y))
                    current_icon_x += icon_spacing
                        
                # 2. Dragon Icon
                if os.path.exists("icons/dragon_icon.png"):
                    has_dragon = bool(member.get_role(DRAGON_ROLE_ID))
                    dragon_icon = get_icon("icons/dragon_icon.png", has_dragon)
                    background.paste(dragon_icon, (current_icon_x, icon_y))
                    current_icon_x += icon_spacing
                        
                cookie_x = current_icon_x

                # 3. Cookie Icon (Pasted first, always solid)
                if os.path.exists("icons/cookie_icon.png"):
                    cookie_icon = Editor("icons/cookie_icon.png").resize(icon_size)
                    background.paste(cookie_icon, (cookie_x, icon_y))
                    
                    # Shifted closer to the cookie (changed from +50 to +40)
                    text_x = cookie_x + 40 
                    
                    # 4. Fire Icon (Scaled exactly to 45x45 to match the cookie)
                    if streak_number >= 3 and os.path.exists("icons/fire_icon.png"):
                        fire_icon = Editor("icons/fire_icon.png").resize((45, 45))
                        # Adjusted the Y-offset to tuck it nicely next to the cookie
                        background.paste(fire_icon, (text_x, icon_y - 18))

                    # 5. Streak Number Text (Layered directly on top of the fire)
                    # Centered nicely within the new 45px flame
                    background.text((text_x + 22, icon_y - 0), f"{streak_number}", font=font_tiny, color="white", align="center", stroke_width=st_width, stroke_fill=st_col)

                # 6. Booster Icon (Below Progress Bar, Transparent if unearned)
                if os.path.exists("icons/booster_icon.png"):
                    has_booster = bool(member.get_role(self.BOOSTER_ROLE_ID))
                    
                    # Custom smaller size (35x35) for the booster badge
                    img = Image.open("icons/booster_icon.png").convert("RGBA")
                    if not has_booster:
                        r, g, b, a = img.split()
                        a = a.point(lambda p: p * 0.3)
                        img.putalpha(a)
                    booster_icon = Editor(img).resize((35, 35))
                    
                    # Moved down to Y=232 so it clears the expanded glowing border
                    background.paste(booster_icon, (230, 232))
                        
            except Exception as e:
                print(f"Error drawing rank card icons: {e}")

            # --- STANDARD RANK CARD TEXT ---
            background.text((550, 50), "Rank", font=font_small, color="white", stroke_width=st_width, stroke_fill=st_col)
            background.text((610, 42), f"#{dragon_rank}", font=font_large, color="white", stroke_width=st_width, stroke_fill=st_col)
            background.text((750, 50), "Level", font=font_small, color="#a97dd1", stroke_width=st_width, stroke_fill=st_col)
            background.text((820, 42), f"{level}", font=font_large, color="#a97dd1", stroke_width=st_width, stroke_fill=st_col)
            background.text((230, 130), f"{member.name}", font=font_medium, color="white", stroke_width=st_width, stroke_fill=st_col)
            background.text((230, 95), f"{current_role_name}", font=font_small, color="#d3d3d3", stroke_width=st_width, stroke_fill=st_col)

            # --- PROGRESS BAR (BOOSTER GLOW VS NORMAL OUTLINE) ---

            # Check if they are a booster AND have their toggle set to 'on'
            is_glowing = member.get_role(self.BOOSTER_ROLE_ID) and (booster_glow == 'on')

            if is_glowing:
                # 1. Booster Glow Enabled: High-intensity vibrant cosmic glow
                background.rectangle((223, 178), width=614, height=49, fill=(160, 32, 240, 140), radius=15)
                background.rectangle((225, 180), width=610, height=45, fill=(0, 242, 254, 180), radius=13)
                background.rectangle((227, 182), width=606, height=41, fill=(255, 0, 128, 220), radius=11)
            else:
                # 2. Regular Members OR Boosters with Glow Turned Off: Clean default black outline
                background.rectangle((228, 183), width=604, height=39, fill="black", radius=12)

            # 3. Progress Bar Background (The empty dark gray track)
            background.rectangle((230, 185), width=600, height=35, fill="#3d3d3d", radius=10)

            # 4. The actual progress (the colored part)
            if percentage > 0:
                bar_width = int(600 * percentage)
                if bar_width > 0:
                    background.rectangle((230, 185), width=max(bar_width, 20), height=35, fill=bar_color, radius=10)
            
            # --- XP TEXT LOGIC ---
            # Top Text: XP earned in this level / Total XP needed to finish this level
            background.text((830, 155), f"Next level: {xp_within_level} / {needed_for_level} XP", font=font_small, color="white", align="right", stroke_width=st_width, stroke_fill=st_col)
            
            # Bottom Text: Total lifetime XP currently held
            background.text((830, 238), f"Total: {xp} XP", font=font_small, color="#d3d3d3", align="right", stroke_width=st_width, stroke_fill=st_col)

            await ctx.send(file=discord.File(fp=background.image_bytes, filename="rank.png"))
        except Exception as e:
            print(f"Error: {e}")
            await ctx.send("There was an error generating the rank card.")

    @commands.hybrid_command(name="customize", description="Change your rank card bar color, background, font, or booster glow!")
    @app_commands.rename(color_hex="color", background_url="background", font_choice="font", glow_toggle="glow")
    @app_commands.describe( 
        color_hex="The Hex code for your progress bar (e.g. #FFFFFF)",
        background_url="A direct image URL for your custom background",
        font_choice="Choose a custom font for your text",
        glow_toggle="Turn your booster glow outline on or off"
    )
    @app_commands.choices(font_choice=[
        app_commands.Choice(name="Comic Relief (Default)", value="comic"),
        app_commands.Choice(name="Bangers", value="bangers"),
        app_commands.Choice(name="Bytesized", value="bytesized"),
        app_commands.Choice(name="Caveat", value="caveat"),
        app_commands.Choice(name="Chewy", value="chewy"),
        app_commands.Choice(name="Crafty Girls", value="crafty"),
        app_commands.Choice(name="Creepster", value="creepster"),
        app_commands.Choice(name="Dancing Script", value="dancing_script"),
        app_commands.Choice(name="Germania One", value="germania"),
        app_commands.Choice(name="Griffy", value="griffy"),
        app_commands.Choice(name="Henny Penny", value="henny_penny"),
        app_commands.Choice(name="Lavishly Yours", value="lavishly_yours"),
        app_commands.Choice(name="Libertinus Math", value="libertinus_math"),
        app_commands.Choice(name="Lobster Two", value="lobster_two"),
        app_commands.Choice(name="Medieval Sharp", value="medieval"),
        app_commands.Choice(name="Mountains of Christmas", value="christmas"),
        app_commands.Choice(name="Nosifer", value="nosifer"),
        app_commands.Choice(name="Open Sans", value="open_sans"),
        app_commands.Choice(name="Pixelify Sans", value="pixelify_sans"),
        app_commands.Choice(name="Roboto", value="roboto"),
        app_commands.Choice(name="Rye", value="rye"),
        app_commands.Choice(name="Schoolbell", value="schoolbell"),
        app_commands.Choice(name="Shadows Into Night", value="shadows_night"),
        app_commands.Choice(name="Smokum", value="smokum"),
        app_commands.Choice(name="Ubuntu", value="ubuntu"),
    ])
    @app_commands.choices(glow_toggle=[
        app_commands.Choice(name="On", value="on"),
        app_commands.Choice(name="Off", value="off"),
    ])
    async def customize(self, ctx, color_hex: Optional[str] = None, background_url: Optional[str] = None, font_choice: app_commands.Choice[str] = None, glow_toggle: app_commands.Choice[str] = None):
        if not color_hex and not background_url and not font_choice and not glow_toggle: 
            return await ctx.send("Provide a hex color, image URL, pick a font, or toggle your glow!", ephemeral=True)
            
        async with aiosqlite.connect(self.db_path) as db:
            if color_hex:
                if not color_hex.startswith("#") or len(color_hex) != 7: return await ctx.send("Invalid hex color!", ephemeral=True)
                await db.execute("UPDATE users SET bar_color = ? WHERE user_id = ?", (color_hex, ctx.author.id))
            if background_url: 
                await db.execute("UPDATE users SET bg_url = ? WHERE user_id = ?", (background_url, ctx.author.id))
            if font_choice:
                # This grabs the 'value' (e.g., 'font2') to store in your database
                await db.execute("UPDATE users SET font_choice = ? WHERE user_id = ?", (font_choice.value, ctx.author.id))
            if glow_toggle:
                await db.execute("UPDATE users SET booster_glow = ? WHERE user_id = ?", (glow_toggle.value, ctx.author.id))
            await db.commit()
        await ctx.send("✅ Rank card updated!", ephemeral=True)

    @app_commands.command(name="setxp", description="Manually set a user's XP (Admin only)")
    @commands.has_permissions(administrator=True)
    async def setxp(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        temp_level = 0
        while amount >= self.get_xp_for_level(temp_level + 1):
            temp_level += 1
            
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO users (user_id, xp, level) 
                VALUES (?, ?, ?) 
                ON CONFLICT(user_id) 
                DO UPDATE SET xp = excluded.xp, level = excluded.level
            """, (member.id, amount, temp_level))
            await db.commit()

        await self._update_member_roles(member, temp_level)
        await interaction.response.send_message(f"✅ Set {member.name}'s XP to {amount} (Level {temp_level}).", ephemeral=True)

    @app_commands.command(name="setlevel", description="Manually set a user's level (Admin only)")
    @commands.has_permissions(administrator=True)
    async def setlevel(self, interaction: discord.Interaction, member: discord.Member, level: int):
        new_xp = self.get_xp_for_level(level)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO users (user_id, xp, level) 
                VALUES (?, ?, ?) 
                ON CONFLICT(user_id) 
                DO UPDATE SET xp = excluded.xp, level = excluded.level
            """, (member.id, new_xp, level))
            await db.commit()

        await self._update_member_roles(member, level)
        await interaction.response.send_message(f"✅ Set {member.mention} to **Level {level}** ({new_xp} XP).", ephemeral=True)

    @app_commands.command(name="addxp", description="Add XP to a user's current total (Admin only)")
    @commands.has_permissions(administrator=True)
    async def addxp(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        # Run your existing helper function which handles the math, DB, and roles!
        await self.add_xp(member, amount)
        
        # Fetch their updated stats to show in the confirmation message
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT xp, level FROM users WHERE user_id = ?", (member.id,)) as cursor:
                result = await cursor.fetchone()
                
        if result:
            new_xp, new_level = result
            # Removed ephemeral=True so it posts publicly in the channel
            await interaction.response.send_message(f"✅ Added {amount} XP to {member.mention}! They now have **{new_xp} XP** (Level {new_level}).")
        else:
            # Removed ephemeral=True here as well
            await interaction.response.send_message(f"✅ Added {amount} XP to {member.mention}!")

    @app_commands.command(name="sync_levels", description="Syncs everyone's levels based on roles without resetting progress. (Admin only)")
    @commands.has_permissions(administrator=True)
    async def sync_levels(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        synced_count = 0
        
        async with aiosqlite.connect(self.db_path) as db:
            for member in interaction.guild.members:
                if member.bot: continue
                
                starting_level = 0
                for level, role_id in sorted(self.level_roles.items(), reverse=True):
                    if role_id != 0 and member.get_role(role_id):
                        starting_level = level
                        break 
                
                async with db.execute("SELECT level FROM users WHERE user_id = ?", (member.id,)) as cursor:
                    result = await cursor.fetchone()
                current_db_level = result[0] if result else -1

                if starting_level > current_db_level:
                    xp = self.get_xp_for_level(starting_level)
                    
                    await db.execute("""
                        INSERT INTO users (user_id, xp, level, bar_color, bg_url) 
                        VALUES (?, ?, ?, '#8a2be2', 'default') 
                        ON CONFLICT(user_id) 
                        DO UPDATE SET xp = excluded.xp, level = excluded.level
                    """, (member.id, xp, starting_level))
                    synced_count += 1
                
            await db.commit()
        await interaction.followup.send(f"✅ Sync complete! Calibrated {synced_count} members.", ephemeral=True)

    @app_commands.command(name="reset", description="Wipe a user's XP and Level (Admin only)")
    @commands.has_permissions(administrator=True)
    async def reset(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(content=f"⚠️ Reset all data for **{member.mention}**?", view=ResetConfirm(self, member), ephemeral=True)

async def setup(bot):
    await bot.add_cog(Leveling(bot))