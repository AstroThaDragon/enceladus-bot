import discord
from discord.ext import commands
import sqlite3
import random
import time
from easy_pil import Editor, Canvas, Font, load_image_async

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 1. Added timeout=10 to prevent the "Silent Freeze"
        self.conn = sqlite3.connect('/data/levels.db', timeout=10)
        self.cursor = self.conn.cursor()
        
        # 2. Optimization: Helps with concurrent reads/writes on Railway volumes
        self.cursor.execute('PRAGMA journal_mode=WAL')
        
        # Updated table to support customization: bar_color and bg_url
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                            (user_id INTEGER PRIMARY KEY, 
                             xp INTEGER DEFAULT 0, 
                             level INTEGER DEFAULT 0,
                             bar_color TEXT DEFAULT '#8a2be2',
                             bg_url TEXT DEFAULT NULL)''')
        self.conn.commit()

        # --- CONFIGURATION ---
        self.ANNOUNCEMENT_CHANNEL_ID = 1306602160527507456 # #spam-chat
        self.BOOSTER_ROLE_ID = 927505358736470047         # Celestial Amplifier
        self.WATCHLIST_ROLE_ID = 928584760748564570       # On Watchlist
        
        # Add your extra channel/category IDs here
        self.NO_XP_CHANNELS = [1117403991266041906, 593398659530489858, 1306821711970435122, 1496628909570265199, 1473398974508437645, 1352415256584130590] 
        self.NO_XP_CATEGORIES = [593406939111751721, 593413698085978132]

        # Role IDs (Replace 0s with the actual IDs for each level)
        self.level_roles = {
            100: 1296961266627121223, 50: 1296959776667730143, 45: 1296959689367617660, 40: 1296959665455890483, 35: 1296959633436708897, 30: 1296959584820264980, 
            25: 1295861213695311935, 20: 1295861175388475463, 15: 1295861144996806726, 10: 1295861102483210260, 5: 1295861061995597844, 1: 1295860897532608615
        }

        # Cooldown dictionary: {user_id: last_xp_time}
        self.cooldowns = {}

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        # 1. CHECK RESTRICTIONS
        if message.channel.id in self.NO_XP_CHANNELS:
            return
        if message.channel.category_id in self.NO_XP_CATEGORIES:
            return
        if message.author.get_role(self.WATCHLIST_ROLE_ID):
            return

        # 2. CHECK COOLDOWN (60 Seconds)
        user_id = message.author.id
        current_time = time.time()
        if user_id in self.cooldowns:
            if current_time - self.cooldowns[user_id] < 60:
                return 
        
        self.cooldowns[user_id] = current_time

        # 3. GET/MIGRATE DATA
        self.cursor.execute("SELECT xp, level FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()

        if result is None:
            starting_level = 0
            for level, role_id in sorted(self.level_roles.items(), reverse=True):
                if role_id != 0 and message.author.get_role(role_id):
                    starting_level = level
                    break 
            xp = starting_level * 500
            level = starting_level
            self.cursor.execute("INSERT INTO users (user_id, xp, level) VALUES (?, ?, ?)", (user_id, xp, level))
        else:
            xp, level = result

        # 4. CALCULATE XP (15-40 + Booster)
        base_xp = random.randint(15, 40)
        if message.author.get_role(self.BOOSTER_ROLE_ID):
            base_xp = int(base_xp * 1.15) 
        
        new_xp = xp + base_xp
        new_level = new_xp // 500 

        # 5. LEVEL UP & ROLES
        if new_level > level:
            if new_level in self.level_roles:
                new_role_id = self.level_roles[new_level]
                new_role = message.guild.get_role(new_role_id)
                
                if new_role:
                    await message.author.add_roles(new_role)

                    announcement_channel = self.bot.get_channel(self.ANNOUNCEMENT_CHANNEL_ID)
                    if announcement_channel:
                        await announcement_channel.send(
                            f"🌌 **Congratulations, {message.author.mention}!** "
                            f"You've reached Level {new_level} and earned the {new_role.mention} role!"
                        )

                    roles_to_remove = []
                    for lvl, rid in self.level_roles.items():
                        if rid != 0 and rid != new_role_id:
                            existing_role = message.author.get_role(rid)
                            if existing_role:
                                roles_to_remove.append(existing_role)
                    
                    if roles_to_remove:
                        await message.author.remove_roles(*roles_to_remove)

            self.cursor.execute("UPDATE users SET xp = ?, level = ? WHERE user_id = ?", (new_xp, new_level, user_id))
        else:
            self.cursor.execute("UPDATE users SET xp = ? WHERE user_id = ?", (new_xp, user_id))

        self.conn.commit()

    @commands.hybrid_command(name="rank", description="Check your or another member's level!")
    async def rank(self, ctx, member: discord.Member = None):
        await ctx.defer() 
        member = member or ctx.author
        
        # Wrapped in a try/except to ensure errors show up in logs
        try:
            self.cursor.execute("SELECT xp, level, bar_color, bg_url FROM users WHERE user_id = ?", (member.id,))
            result = self.cursor.fetchone()
            
            if not result:
                return await ctx.send("This user hasn't earned any XP yet!")

            xp, level, bar_color, bg_url = result
            next_lvl_xp = (level + 1) * 500
            xp_within_level = xp - (level * 500)
            
            # 1. Create Background
            try:
                if bg_url:
                    bg_image = await load_image_async(bg_url)
                    background = Editor(bg_image).resize((900, 270))
                else:
                    background = Editor(Canvas((900, 270), color="#23272a"))
            except:
                background = Editor(Canvas((900, 270), color="#23272a"))

            # 2. Draw Avatar (Forced to PNG for stability)
            avatar_url = member.display_avatar.replace(format="png", size=256).url
            avatar_image = await load_image_async(avatar_url)
            avatar = Editor(avatar_image).resize((150, 150)).circle_image()
            background.paste(avatar, (50, 50))
            
            # 3. Text and Progress Bar
            font_large = Font("fonts/Poppins-Bold.ttf", size=40)
            font_small = Font("fonts/Poppins-Regular.ttf", size=30)

            background.text((230, 50), f"{member.name}", font=font_large, color="white")
            background.text((230, 120), f"Level: {level}   XP: {xp}/{next_lvl_xp}", font=font_small, color="white")
            
            # Percentage calculation based on your 500xp-per-level rule
            percentage = (xp_within_level / 500) * 100
            background.bar((230, 180), max_width=600, height=40, percentage=percentage, fill=bar_color, back_fill="#484b4e")

            file = discord.File(fp=background.image_bytes, filename="rank.png")
            await ctx.send(file=file)
        except Exception as e:
            # This will force the error into your Railway logs if it crashes
            print(f"Error generating rank card: {e}")
            await ctx.send("There was an error generating the rank card. Check logs.")

    @commands.hybrid_command(name="customize", description="Change your rank card bar color or background!")
    async def customize(self, ctx, color_hex: str = None, background_url: str = None):
        """Update your rank card. Example: /customize color_hex:#FF5733"""
        if not color_hex and not background_url:
            return await ctx.send("Please provide a hex color (e.g. #FFFFFF) or an image URL!", ephemeral=True)
        
        if color_hex:
            # Simple check to ensure it looks like a hex code
            if not color_hex.startswith("#") or len(color_hex) != 7:
                return await ctx.send("Invalid hex color! Use format like #FF5733", ephemeral=True)
            self.cursor.execute("UPDATE users SET bar_color = ? WHERE user_id = ?", (color_hex, ctx.author.id))
            
        if background_url:
            self.cursor.execute("UPDATE users SET bg_url = ? WHERE user_id = ?", (background_url, ctx.author.id))
            
        self.conn.commit()
        await ctx.send("✅ Rank card updated!", ephemeral=True)

    @discord.app_commands.command(name="setxp", description="Manually set a user's XP (Admin only)")
    @commands.has_permissions(administrator=True)
    async def setxp(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        new_level = amount // 500
        self.cursor.execute("INSERT OR REPLACE INTO users (user_id, xp, level) VALUES (?, ?, ?)", (member.id, amount, new_level))
        self.conn.commit()
        await interaction.response.send_message(f"✅ Set {member.name}'s XP to {amount} (Level {new_level}).", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Leveling(bot))