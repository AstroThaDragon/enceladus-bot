import os
import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random
import time
from easy_pil import Editor, Canvas, Font, load_image_async
import json
from typing import Optional

class ResetConfirm(discord.ui.View):
    def __init__(self, cog, member):
        super().__init__(timeout=30)
        self.cog = cog
        self.member = member

    @discord.ui.button(label="Confirm Reset", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.cog.cursor.execute("DELETE FROM users WHERE user_id = ?", (self.member.id,))
        self.cog.conn.commit()
        await interaction.response.edit_message(content=f"♻️ **{self.member.name}** has been reset to Level 0.", view=None)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Reset cancelled.", view=None)
        self.stop()

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('/app/data/levels.db', timeout=10)
        self.cursor = self.conn.cursor()
        self.cursor.execute('PRAGMA journal_mode=WAL')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                            (user_id INTEGER PRIMARY KEY, 
                             xp INTEGER DEFAULT 0, 
                             level INTEGER DEFAULT 0,
                             bar_color TEXT DEFAULT '#8a2be2',
                             bg_url TEXT DEFAULT 'default')''')
        self.conn.commit()

        # --- CONFIGURATION ---
        self.ANNOUNCEMENT_CHANNEL_ID = 1306602160527507456 
        self.BOOSTER_ROLE_ID = 927505358736470047         
        self.WATCHLIST_ROLE_ID = 928584760748564570       
        
        self.NO_XP_CHANNELS = [1117403991266041906, 593398659530489858, 1306821711970435122, 1496628909570265199, 1473398974508437645, 1352415256584130590] 
        self.NO_XP_CATEGORIES = [593406939111751721, 593413698085978132]

        self.level_roles = {
            100: 1296961266627121223, 95: 1501609710573453324, 90: 1501609557804187781, 
            85: 1501609375318675657, 80: 1501609179566313522, 75: 1501608976507211920, 
            70: 1501608777613312020, 65: 1501608443356643328, 60: 1501608145582031000, 
            55: 1501607815893094552, 50: 1296959776667730143, 45: 1296959689367617660, 
            40: 1296959665455890483, 35: 1296959633436708897, 30: 1296959584820264980, 
            25: 1295861213695311935, 20: 1295861175388475463, 15: 1295861144996806726, 
            10: 1295861102483210260, 5: 1295861061995597844, 1: 1295860897532608615
        }

        self.cooldowns = {}

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
        for lvl, rid in sorted(self.level_roles.items(), reverse=True):
            if new_level >= lvl:
                new_role_id = rid
                break

        if new_role_id and new_role_id != 0:
            new_role = guild.get_role(new_role_id)
            if new_role and new_role not in member.roles:
                await member.add_roles(new_role)
                announcement_channel = self.bot.get_channel(self.ANNOUNCEMENT_CHANNEL_ID)
                if announcement_channel:
                    await announcement_channel.send(
                        f"🌌 **Congratulations, {member.mention}!** "
                        f"You've reached level {new_level} and earned the **{new_role.name}** role! 🚀"
                    )
            roles_to_remove = [
                guild.get_role(rid) for lvl, rid in self.level_roles.items() 
                if rid != new_role_id and rid != 0 and guild.get_role(rid) in member.roles
            ]
            if roles_to_remove:
                await member.remove_roles(*[r for r in roles_to_remove if r])

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        if message.channel.id in self.NO_XP_CHANNELS or message.channel.category_id in self.NO_XP_CATEGORIES: return
        if message.author.get_role(self.WATCHLIST_ROLE_ID): return

        user_id = message.author.id
        current_time = time.time()
        if user_id in self.cooldowns and current_time - self.cooldowns[user_id] < 60: return 
        self.cooldowns[user_id] = current_time

        self.cursor.execute("SELECT xp, level FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()

        if result is None:
            starting_level = 0
            for level, role_id in sorted(self.level_roles.items(), reverse=True):
                if role_id != 0 and message.author.get_role(role_id):
                    starting_level = level
                    break 
            xp, level = self.get_xp_for_level(starting_level), starting_level
            self.cursor.execute("INSERT INTO users (user_id, xp, level) VALUES (?, ?, ?)", (user_id, xp, level))
        else:
            xp, level = result

        base_xp = random.randint(15, 40)
        if message.author.get_role(self.BOOSTER_ROLE_ID):
            base_xp = int(base_xp * 1.15) 
        
        new_xp = xp + base_xp
        temp_level = level
        while new_xp >= self.get_xp_for_level(temp_level + 1):
            temp_level += 1
        new_level = temp_level

        if new_level > level:
            await self._update_member_roles(message.author, new_level)
            self.cursor.execute("UPDATE users SET xp = ?, level = ? WHERE user_id = ?", (new_xp, new_level, user_id))
        else:
            self.cursor.execute("UPDATE users SET xp = ? WHERE user_id = ?", (new_xp, user_id))
        self.conn.commit()

    @commands.hybrid_command(name="rank", description="Check your or another member's level!")
    async def rank(self, ctx, member: discord.Member = None):
        await ctx.defer() 
        member = member or ctx.author
        try:
            self.cursor.execute("SELECT xp, level, bar_color, bg_url FROM users WHERE user_id = ?", (member.id,))
            result = self.cursor.fetchone()
            if not result: return await ctx.send("This user hasn't earned any XP yet!")

            xp, level, bar_color, bg_url = result
            xp_start = self.get_xp_for_level(level)
            xp_end = self.get_xp_for_level(level + 1)
            xp_within_level = xp - xp_start
            needed_for_level = xp_end - xp_start
            percentage = (xp_within_level / needed_for_level) * 100 if needed_for_level > 0 else 0

            current_role_name = "No Rank"
            for lvl, rid in sorted(self.level_roles.items(), reverse=True):
                if rid == 0: continue
                role = member.get_role(rid)
                if role:
                    current_role_name = role.name
                    break

            dragon_rank = "0"
            try:
                import aiohttp
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
                if bg_url:
                    bg_image = await load_image_async(bg_url)
                    background = Editor(bg_image).resize((900, 270))
                elif os.path.exists("images/rank_template.png"):
                    background = Editor("images/rank_template.png")
                else:
                    background = Editor(Canvas((900, 270), color="#23272a"))
            except:
                background = Editor(Canvas((900, 270), color="#23272a"))

            avatar_image = await load_image_async(member.display_avatar.replace(format="png", size=256).url)
            avatar = Editor(avatar_image).resize((150, 150)).circle_image()
            background.paste(avatar, (50, 60))
            
            font_large = Font("fonts/ComicRelief-Bold.ttf", size=45)
            font_medium = Font("fonts/ComicRelief-Bold.ttf", size=32)
            font_small = Font("fonts/ComicRelief-Regular.ttf", size=22)
            st_col, st_width = (0, 0, 0), 2

            background.text((550, 50), "Rank", font=font_small, color="white", stroke_width=st_width, stroke_fill=st_col)
            background.text((610, 42), f"#{dragon_rank}", font=font_large, color="white", stroke_width=st_width, stroke_fill=st_col)
            background.text((750, 50), "Level", font=font_small, color="#a97dd1", stroke_width=st_width, stroke_fill=st_col)
            background.text((820, 42), f"{level}", font=font_large, color="#a97dd1", stroke_width=st_width, stroke_fill=st_col)
            background.text((230, 130), f"{member.name}", font=font_medium, color="white", stroke_width=st_width, stroke_fill=st_col)
            background.text((230, 95), f"{current_role_name}", font=font_small, color="#d3d3d3", stroke_width=st_width, stroke_fill=st_col)

            background.rectangle((230, 185), width=600, height=35, fill="#3d3d3d", radius=20)
            if percentage > 0: background.bar((230, 185), max_width=600, height=35, percentage=percentage, fill=bar_color, radius=20)
            background.text((830, 155), f"{xp} / {xp_end} XP", font=font_small, color="white", align="right", stroke_width=st_width, stroke_fill=st_col)

            await ctx.send(file=discord.File(fp=background.image_bytes, filename="rank.png"))
        except Exception as e:
            print(f"Error: {e}")
            await ctx.send("There was an error generating the rank card.")

    @commands.hybrid_command(name="customize", description="Change your rank card bar color or background!")
    async def customize(self, ctx, color_hex: Optional[str] = None, background_url: Optional[str] = None):
        if not color_hex and not background_url: return await ctx.send("Provide a hex color or image URL!", ephemeral=True)
        if color_hex:
            if not color_hex.startswith("#") or len(color_hex) != 7: return await ctx.send("Invalid hex color!", ephemeral=True)
            self.cursor.execute("UPDATE users SET bar_color = ? WHERE user_id = ?", (color_hex, ctx.author.id))
        if background_url: self.cursor.execute("UPDATE users SET bg_url = ? WHERE user_id = ?", (background_url, ctx.author.id))
        self.conn.commit()
        await ctx.send("✅ Rank card updated!", ephemeral=True)

    @app_commands.command(name="setxp", description="Manually set a user's XP (Admin only)")
    @commands.has_permissions(administrator=True)
    async def setxp(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        temp_level = 0
        while amount >= self.get_xp_for_level(temp_level + 1):
            temp_level += 1
        self.cursor.execute("INSERT OR REPLACE INTO users (user_id, xp, level) VALUES (?, ?, ?)", (member.id, amount, temp_level))
        self.conn.commit()
        await self._update_member_roles(member, temp_level)
        await interaction.response.send_message(f"✅ Set {member.name}'s XP to {amount} (Level {temp_level}).", ephemeral=True)

    @app_commands.command(name="setlevel", description="Manually set a user's level (Admin only)")
    @commands.has_permissions(administrator=True)
    async def setlevel(self, interaction: discord.Interaction, member: discord.Member, level: int):
        new_xp = self.get_xp_for_level(level)
        self.cursor.execute("INSERT OR REPLACE INTO users (user_id, xp, level) VALUES (?, ?, ?)", (member.id, new_xp, level))
        self.conn.commit()
        await self._update_member_roles(member, level)
        await interaction.response.send_message(f"✅ Set {member.mention} to **Level {level}** ({new_xp} XP).", ephemeral=True)

    @app_commands.command(name="sync_levels", description="Syncs everyone's levels based on roles without resetting progress. (Admin only)")
    @commands.has_permissions(administrator=True)
    async def sync_levels(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        synced_count = 0
        
        for member in interaction.guild.members:
            if member.bot: continue
            
            # Find the highest level role they have
            starting_level = 0
            for level, role_id in sorted(self.level_roles.items(), reverse=True):
                if role_id != 0 and member.get_role(role_id):
                    starting_level = level
                    break 
            
            # Check current DB level to avoid demoting (e.g., Level 14 stay Level 14)
            self.cursor.execute("SELECT level FROM users WHERE user_id = ?", (member.id,))
            result = self.cursor.fetchone()
            current_db_level = result[0] if result else -1

            # Only update if the role indicates they should be a higher level than the DB says
            if starting_level > current_db_level:
                xp = self.get_xp_for_level(starting_level)
                
                # ON CONFLICT ONLY updates xp/level. It ignores bar_color and bg_url!
                self.cursor.execute("""
                    INSERT INTO users (user_id, xp, level, bar_color, bg_url) 
                    VALUES (?, ?, ?, '#8a2be2', 'default') 
                    ON CONFLICT(user_id) 
                    DO UPDATE SET xp = excluded.xp, level = excluded.level
                """, (member.id, xp, starting_level))
                synced_count += 1
            
        self.conn.commit()
        await interaction.followup.send(f"✅ Sync complete! Calibrated {synced_count} members.", ephemeral=True)

    @app_commands.command(name="reset", description="Wipe a user's XP and Level (Admin only)")
    @commands.has_permissions(administrator=True)
    async def reset(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(content=f"⚠️ Reset all data for **{member.mention}**?", view=ResetConfirm(self, member), ephemeral=True)

async def setup(bot):
    await bot.add_cog(Leveling(bot))