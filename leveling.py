import os
import discord
from discord.ext import commands, tasks
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
    def __init__(self, cog, member, admin_id):
        super().__init__(timeout=30)
        self.cog = cog
        self.member = member
        self.admin_id = admin_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.admin_id:
            await interaction.response.send_message(
                "❌ This reset confirmation belongs to another administrator.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Confirm XP Reset", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with aiosqlite.connect(self.cog.db_path) as db:
            await db.execute("""
                UPDATE users
                SET xp = 0,
                    level = 0
                WHERE user_id = ?
            """, (self.member.id,))
            await db.commit()

        await self.cog._update_member_roles(self.member, 0)

        await interaction.response.edit_message(
            content=f"♻️ **{self.member.name}**'s XP and Level have been reset to 0.",
            view=None
        )
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="❌ Reset cancelled.",
            view=None
        )
        self.stop()

class FullResetConfirm(discord.ui.View):
    def __init__(self, cog, member, admin_id):
        super().__init__(timeout=30)
        self.cog = cog
        self.member = member
        self.admin_id = admin_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.admin_id:
            await interaction.response.send_message(
                "❌ This reset confirmation belongs to another administrator.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="☢️ Confirm Full Wipe", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        from database import ECONOMY_DB_NAME

        async with aiosqlite.connect(self.cog.db_path) as db:
            await db.execute("ATTACH DATABASE ? AS economy", (ECONOMY_DB_NAME,))

            await db.execute(
                "DELETE FROM economy.inventory WHERE user_id = ?",
                (self.member.id,)
            )

            await db.execute(
                "DELETE FROM economy.pets WHERE user_id = ?",
                (self.member.id,)
            )

            await db.execute(
                "DELETE FROM economy.users WHERE user_id = ?",
                (self.member.id,)
            )

            await db.execute(
                "DELETE FROM main.users WHERE user_id = ?",
                (self.member.id,)
            )

            await db.commit()
            await db.execute("DETACH DATABASE economy")

        await interaction.response.edit_message(
            content=(
                f"☢️ **{self.member.name}**'s Enceladus account has been "
                f"completely wiped.\n"
                f"XP, Level, economy, profile data, inventory, and pets were deleted."
            ),
            view=None
        )
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="❌ Full wipe cancelled.",
            view=None
        )
        self.stop()

class LeaderboardView(discord.ui.View):
    def __init__(self, cog, author, entries, per_page=10):
        super().__init__(timeout=120)
        self.cog = cog
        self.author = author
        self.entries = entries
        self.per_page = per_page
        self.current_page = 0
        self.max_pages = max(1, (len(entries) - 1) // per_page + 1)
        self.update_buttons()

    def update_buttons(self):
        self.first_page.disabled = (self.current_page == 0) # type: ignore
        self.back_3.disabled = (self.current_page == 0) # type: ignore
        self.prev_page.disabled = (self.current_page == 0) # type: ignore
        self.next_page.disabled = (self.current_page >= self.max_pages - 1) # type: ignore
        self.forward_3.disabled = (self.current_page >= self.max_pages - 1) # type: ignore
        self.last_page.disabled = (self.current_page >= self.max_pages - 1) # type: ignore

    def build_embed(self):
        start_idx = self.current_page * self.per_page
        end_idx = start_idx + self.per_page
        page_entries = self.entries[start_idx:end_idx]

        embed = discord.Embed(
            title="🏆 Server XP Leaderboard",
            color=discord.Color.from_rgb(114, 0, 225),
            timestamp=discord.utils.utcnow()
        )

        description_lines = []
        for i, entry in enumerate(page_entries, start=start_idx + 1):
            user_id, xp, level = entry
            
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            else:
                medal = f"`#{i}`"

            description_lines.append(f"{medal} <@{user_id}> • Level **{level}** ({xp:,} XP)")

        embed.description = "\n".join(description_lines) if description_lines else "No active members found."
        embed.set_footer(text=f"Page {self.current_page + 1} / {self.max_pages} • Total Active Members: {len(self.entries)}")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.author.id:
            return True
        await interaction.response.send_message("This leaderboard isn't for you! Use `/leaderboard` to view your own.", ephemeral=True)
        return False

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.primary, row=0)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(emoji="⏪", style=discord.ButtonStyle.primary, row=0)
    async def back_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(0, self.current_page - 3)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.primary, row=0)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.primary, row=0)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(emoji="⏩", style=discord.ButtonStyle.primary, row=0)
    async def forward_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(self.max_pages - 1, self.current_page + 3)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.primary, row=1)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = self.max_pages - 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

async def load_custom_image(url):
    async with aiohttp.ClientSession() as session:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.read()
                return io.BytesIO(data)
            else:
                print(f"Image Load Failed: Status {response.status}")
                return None

class FontPreviewSelect(discord.ui.Select):
    def __init__(self, cog):
        self.cog = cog
        options = [
            discord.SelectOption(label="Comic Relief (Default)", value="comic"),
            discord.SelectOption(label="Bangers", value="bangers"),
            discord.SelectOption(label="Bytesized", value="bytesized"),
            discord.SelectOption(label="Caveat", value="caveat"),
            discord.SelectOption(label="Chewy", value="chewy"),
            discord.SelectOption(label="Crafty Girls", value="crafty"),
            discord.SelectOption(label="Creepster", value="creepster"),
            discord.SelectOption(label="Dancing Script", value="dancing_script"),
            discord.SelectOption(label="Germania One", value="germania"),
            discord.SelectOption(label="Griffy", value="griffy"),
            discord.SelectOption(label="Henny Penny", value="henny_penny"),
            discord.SelectOption(label="Lavishly Yours", value="lavishly_yours"),
            discord.SelectOption(label="Libertinus Math", value="libertinus_math"),
            discord.SelectOption(label="Lobster Two", value="lobster_two"),
            discord.SelectOption(label="Medieval Sharp", value="medieval"),
            discord.SelectOption(label="Mountains of Christmas", value="christmas"),
            discord.SelectOption(label="Nosifer", value="nosifer"),
            discord.SelectOption(label="Open Sans", value="open_sans"),
            discord.SelectOption(label="Pixelify Sans", value="pixelify_sans"),
            discord.SelectOption(label="Roboto", value="roboto"),
            discord.SelectOption(label="Rye", value="rye"),
            discord.SelectOption(label="Schoolbell", value="schoolbell"),
            discord.SelectOption(label="Shadows Into Light", value="shadows_light"),
            discord.SelectOption(label="Smokum", value="smokum"),
            discord.SelectOption(label="Ubuntu", value="ubuntu"),
        ]
        super().__init__(placeholder="Choose a font to preview...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        chosen_font = self.values[0]
        member = interaction.user
        
        async with aiosqlite.connect(self.cog.db_path) as db:
            async with db.execute(
                "SELECT xp, level, bar_color, bg_url, fortune_streak, booster_glow FROM users WHERE user_id = ?", 
                (member.id,)
            ) as cursor:
                result = await cursor.fetchone()

        if result:
            xp, level, bar_color, bg_url, fortune_streak, booster_glow = result
        else:
            xp, level, bar_color, bg_url, fortune_streak, booster_glow = 0, 0, "#8a2be2", "default", 0, "on"

        streak_number = fortune_streak or 0
        xp_start = self.cog.get_xp_for_level(level)
        xp_end = self.cog.get_xp_for_level(level + 1)
        xp_within_level = xp - xp_start
        needed_for_level = xp_end - xp_start
        percentage = (xp_within_level / needed_for_level) if needed_for_level > 0 else 0
        percentage = max(0, min(percentage, 1))

        current_role_name = "No Rank"
        for lvl, rid in sorted(self.cog.level_roles.items(), reverse=True):
            if rid == 0: continue
            role = member.get_role(rid)
            if role:
                current_role_name = role.name
                break

        dragon_rank = "0"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://draconova-production.up.railway.app/leaderboard", timeout=2) as response:
                    if response.status == 200:
                        data = await response.json()
                        for i, entry in enumerate(data):
                            if str(entry.get('user_id')) == str(member.id):
                                dragon_rank = str(i + 1)
                                break
        except Exception:
            pass

        try:
            if bg_url and bg_url != 'default':
                bg_data = await load_custom_image(bg_url)
                background = Editor(bg_data).resize((900, 270)) if bg_data else Editor(Canvas((900, 270), color="#23272a"))
            elif os.path.exists("images/rank_template.png"):
                background = Editor("images/rank_template.png")
            else:
                background = Editor(Canvas((900, 270), color="#23272a"))
        except Exception:
            background = Editor(Canvas((900, 270), color="#23272a"))

        try:
            avatar_image = await load_image_async(member.display_avatar.replace(format="png", size=256).url)
            avatar = Editor(avatar_image).resize((150, 150)).circle_image()
            background.paste(avatar, (50, 60))
        except Exception:
            pass

        STARBORN_ROLE_ID = 1496031062218772510 
        OWNER_ROLE_ID = 891356074689560626    
        ADMIN_ROLE_ID = 593718477831929858    
        MOD_ROLE_ID = 1036583011405266974      
        badge_size = (45, 45)

        try:
            if member.get_role(STARBORN_ROLE_ID) and os.path.exists("icons/starborn_icon.png"):
                background.paste(Editor("icons/starborn_icon.png").resize(badge_size), (30, 40)) 
            if member.get_role(OWNER_ROLE_ID) and os.path.exists("icons/owner_icon.png"):
                background.paste(Editor("icons/owner_icon.png").resize(badge_size), (30, 170)) 
            elif member.get_role(ADMIN_ROLE_ID) and os.path.exists("icons/admin_icon.png"):
                background.paste(Editor("icons/admin_icon.png").resize(badge_size), (30, 170))
            elif member.get_role(MOD_ROLE_ID) and os.path.exists("icons/mod_icon.png"):
                background.paste(Editor("icons/mod_icon.png").resize(badge_size), (30, 170))
            if member.get_role(self.cog.WATCHLIST_ROLE_ID) and os.path.exists("icons/watchlist_icon.png"):
                background.paste(Editor("icons/watchlist_icon.png").resize(badge_size), (102, 10))
        except Exception: 
            pass

        active_font_path = "fonts/ComicRelief-Regular.ttf"
        font_map = {
            "bangers": "fonts/Bangers-Regular.ttf",
            "bytesized": "fonts/Bytesized-Regular.ttf",
            "caveat": "fonts/Caveat-Regular.ttf",
            "chewy": "fonts/Chewy-Regular.ttf",
            "crafty": "fonts/CraftyGirls-Regular.ttf",
            "creepster": "fonts/Creepster-Regular.ttf",
            "dancing_script": "fonts/DancingScript-Regular.ttf",
            "germania": "fonts/GermaniaOne-Regular.ttf",
            "griffy": "fonts/Griffy-Regular.ttf",
            "henny_penny": "fonts/HennyPenny-Regular.ttf",
            "lavishly_yours": "fonts/LavishlyYours-Regular.ttf",
            "libertinus_math": "fonts/LibertinusMath-Regular.ttf",
            "lobster_two": "fonts/LobsterTwo-Regular.ttf",
            "medieval": "fonts/MedievalSharp-Regular.ttf",
            "christmas": "fonts/MountainsofChristmas-Regular.ttf",
            "nosifer": "fonts/Nosifer-Regular.ttf",
            "open_sans": "fonts/OpenSans-Regular.ttf",
            "pixelify_sans": "fonts/PixelifySans-Regular.ttf",
            "roboto": "fonts/Roboto-Regular.ttf",
            "rye": "fonts/Rye-Regular.ttf",
            "schoolbell": "fonts/Schoolbell-Regular.ttf",
            "shadows_light": "fonts/ShadowsIntoLight-Regular.ttf",
            "smokum": "fonts/Smokum-Regular.ttf",
            "ubuntu": "fonts/Ubuntu-Regular.ttf"
        }
        if chosen_font in font_map and os.path.exists(font_map[chosen_font]):
            active_font_path = font_map[chosen_font]
            
        font_large = Font(active_font_path, size=45)
        font_medium = Font(active_font_path, size=32)
        font_small = Font(active_font_path, size=22)
        font_tiny = Font(active_font_path, size=20)
        
        st_col, st_width = (0, 0, 0), 2
        current_icon_x = 230 
        icon_y = 45
        icon_size = (45, 45)
        
        SWORD_ROLE_ID = 1505077643567956069
        DRAGON_ROLE_ID = 1505083974509269074

        try:
            def get_icon(path, earned):
                img = Image.open(path).convert("RGBA")
                if not earned:
                    r, g, b, a = img.split()
                    a = a.point(lambda p: p * 0.3)
                    img.putalpha(a)
                return Editor(img).resize(icon_size)

            if os.path.exists("icons/sword_icon.png"):
                background.paste(get_icon("icons/sword_icon.png", bool(member.get_role(SWORD_ROLE_ID))), (current_icon_x, icon_y))
                current_icon_x += 60
                    
            if os.path.exists("icons/dragon_icon.png"):
                background.paste(get_icon("icons/dragon_icon.png", bool(member.get_role(DRAGON_ROLE_ID))), (current_icon_x, icon_y))
                current_icon_x += 60
                    
            cookie_x = current_icon_x
            if os.path.exists("icons/cookie_icon.png"):
                background.paste(Editor("icons/cookie_icon.png").resize(icon_size), (cookie_x, icon_y))
                text_x = cookie_x + 40 
                if streak_number >= 3 and os.path.exists("icons/fire_icon.png"):
                    background.paste(Editor("icons/fire_icon.png").resize((45, 45)), (text_x, icon_y - 18))
                background.text((text_x + 22, icon_y - 0), f"{streak_number}", font=font_tiny, color="white", align="center", stroke_width=st_width, stroke_fill=st_col)

            if os.path.exists("icons/booster_icon.png"):
                has_booster = bool(member.get_role(self.cog.BOOSTER_ROLE_ID))
                img = Image.open("icons/booster_icon.png").convert("RGBA")
                if not has_booster:
                    r, g, b, a = img.split()
                    a = a.point(lambda p: p * 0.3)
                    img.putalpha(a)
                background.paste(Editor(img).resize((35, 35)), (230, 232))
        except Exception: 
            pass

        background.text((550, 50), "Rank", font=font_small, color="white", stroke_width=st_width, stroke_fill=st_col)
        background.text((610, 42), f"#{dragon_rank}", font=font_large, color="white", stroke_width=st_width, stroke_fill=st_col)
        background.text((750, 50), "Level", font=font_small, color="#a97dd1", stroke_width=st_width, stroke_fill=st_col)
        background.text((820, 42), f"{level}", font=font_large, color="#a97dd1", stroke_width=st_width, stroke_fill=st_col)
        background.text((230, 130), f"{member.name}", font=font_medium, color="white", stroke_width=st_width, stroke_fill=st_col)
        background.text((230, 95), f"{current_role_name}", font=font_small, color="#d3d3d3", stroke_width=st_width, stroke_fill=st_col)

        is_glowing = member.get_role(self.cog.BOOSTER_ROLE_ID) and (booster_glow == 'on')
        if is_glowing:
            background.rectangle((223, 178), width=614, height=49, fill=(160, 32, 240, 140), radius=15)
            background.rectangle((225, 180), width=610, height=45, fill=(0, 242, 254, 180), radius=13)
            background.rectangle((227, 182), width=606, height=41, fill=(255, 0, 128, 220), radius=11)
        else:
            background.rectangle((228, 183), width=604, height=39, fill="black", radius=12)

        background.rectangle((230, 185), width=600, height=35, fill="#3d3d3d", radius=10)
        if percentage > 0:
            bar_width = int(600 * percentage)
            if bar_width > 0:
                background.rectangle((230, 185), width=max(bar_width, 20), height=35, fill=bar_color, radius=10)
        
        background.text((830, 155), f"Next level: {xp_within_level} / {needed_for_level} XP", font=font_small, color="white", align="right", stroke_width=st_width, stroke_fill=st_col)
        background.text((830, 238), f"Total: {xp} XP", font=font_small, color="#d3d3d3", align="right", stroke_width=st_width, stroke_fill=st_col)

        file = discord.File(fp=background.image_bytes, filename="preview.png")
        await interaction.edit_original_response(content=f"🎨 Previewing font: **{self.values[0]}**", attachments=[file])

class FontView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.add_item(FontPreviewSelect(cog))

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        if os.path.exists('/app/data'):
            self.db_path = '/app/data/levels.db'
            print(f"LevelingCog: Using PRODUCTION database at {self.db_path}")
        else:
            self.db_path = 'levels.db'
            print(f"LevelingCog: Using LOCAL database at {self.db_path}")

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
                await db.execute(
                    "ALTER TABLE users ADD COLUMN left_at INTEGER DEFAULT NULL"
                )
            except:
                pass

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

        self.cleanup_departed_users.start()

    def cog_unload(self):
        self.cleanup_departed_users.cancel()

    def get_xp_for_level(self, level):
        if level <= 0: return 0
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
        if member.bot:
            return False, 0

        user_id = member.id

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT xp, level FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                result = await cursor.fetchone()

            if result is None:
                xp, level = amount, 0

                new_level = level
                while xp >= self.get_xp_for_level(new_level + 1):
                    new_level += 1

                await db.execute(
                    "INSERT INTO users (user_id, xp, level) VALUES (?, ?, ?)",
                    (user_id, xp, new_level)
                )

                if new_level > 0:
                    await self._update_member_roles(member, new_level)

                await db.commit()
                return new_level > 0, new_level

            xp, level = result
            new_xp = xp + amount

            temp_level = level

            while new_xp >= self.get_xp_for_level(temp_level + 1):
                temp_level += 1

            leveled_up = temp_level > level

            if leveled_up:
                await self._update_member_roles(member, temp_level)
                await db.execute(
                    "UPDATE users SET xp = ?, level = ? WHERE user_id = ?",
                    (new_xp, temp_level, user_id)
                )
            else:
                await db.execute(
                    "UPDATE users SET xp = ? WHERE user_id = ?",
                    (new_xp, user_id)
                )

            await db.commit()

            return leveled_up, temp_level

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET left_at = NULL WHERE user_id = ?",
                (member.id,)
            )
            await db.commit()

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT level FROM users WHERE user_id = ?",
                (member.id,)
            ) as cursor:
                row = await cursor.fetchone()

            level = row[0] if row else 0

        await self._update_member_roles(member, level)


    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.bot:
            return

        left_at = int(time.time())

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET left_at = ? WHERE user_id = ?",
                (left_at, member.id)
            )
            await db.commit()

    @tasks.loop(hours=24)
    async def cleanup_departed_users(self):
        if not self.bot.is_ready():
            return

        cutoff = int(time.time()) - (14 * 24 * 60 * 60)

        from database import ECONOMY_DB_NAME

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("ATTACH DATABASE ? AS economy", (ECONOMY_DB_NAME,))

            async with db.execute(
                "SELECT user_id FROM main.users WHERE left_at IS NOT NULL AND left_at <= ?",
                (cutoff,)
            ) as cursor:
                expired_users = await cursor.fetchall()

            for (user_id,) in expired_users:
                await db.execute(
                    "DELETE FROM economy.inventory WHERE user_id = ?",
                    (user_id,)
                )

                await db.execute(
                    "DELETE FROM economy.pets WHERE user_id = ?",
                    (user_id,)
                )

                await db.execute(
                    "DELETE FROM economy.users WHERE user_id = ?",
                    (user_id,)
                )

                await db.execute(
                    "DELETE FROM main.users WHERE user_id = ?",
                    (user_id,)
                )

            await db.commit()
            await db.execute("DETACH DATABASE economy")

        if expired_users:
            print(f"[Leveling] Cleaned up {len(expired_users)} departed user(s).")

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
            streak_number = fortune_streak or 0
            
            xp_start = self.get_xp_for_level(level)
            xp_end = self.get_xp_for_level(level + 1)
            
            xp_within_level = xp - xp_start
            needed_for_level = xp_end - xp_start
            
            if needed_for_level > 0:
                percentage = xp_within_level / needed_for_level
            else:
                percentage = 0

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
                if member.get_role(STARBORN_ROLE_ID) and os.path.exists("icons/starborn_icon.png"):
                    starborn_icon = Editor("icons/starborn_icon.png").resize(badge_size)
                    background.paste(starborn_icon, (30, 40)) 

                if member.get_role(OWNER_ROLE_ID) and os.path.exists("icons/owner_icon.png"):
                    owner_icon = Editor("icons/owner_icon.png").resize(badge_size)
                    background.paste(owner_icon, (30, 170)) 
                elif member.get_role(ADMIN_ROLE_ID) and os.path.exists("icons/admin_icon.png"):
                    admin_icon = Editor("icons/admin_icon.png").resize(badge_size)
                    background.paste(admin_icon, (30, 170))
                elif member.get_role(MOD_ROLE_ID) and os.path.exists("icons/mod_icon.png"):
                    mod_icon = Editor("icons/mod_icon.png").resize(badge_size)
                    background.paste(mod_icon, (30, 170))

                if member.get_role(self.WATCHLIST_ROLE_ID) and os.path.exists("icons/watchlist_icon.png"):
                    watchlist_icon = Editor("icons/watchlist_icon.png").resize(badge_size)
                    background.paste(watchlist_icon, (102, 10))

            except Exception as e:
                print(f"Error drawing avatar badges: {e}")
            
            active_font_path = "fonts/ComicRelief-Regular.ttf"
            
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
                active_font_path = "fonts/MountainsofChristmas-Regular.ttf"
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
            elif font_choice == "shadows_light":
                active_font_path = "fonts/ShadowsIntoLight-Regular.ttf"
            elif font_choice == "smokum":
                active_font_path = "fonts/Smokum-Regular.ttf"
            elif font_choice == "ubuntu":
                active_font_path = "fonts/Ubuntu-Regular.ttf"
                
            font_large = Font(active_font_path, size=45)
            font_medium = Font(active_font_path, size=32)
            font_small = Font(active_font_path, size=22)
            font_tiny = Font(active_font_path, size=20)
            
            st_col, st_width = (0, 0, 0), 2

            current_icon_x = 230 
            icon_y = 45
            icon_spacing = 60 
            icon_size = (45, 45) 
            
            SWORD_ROLE_ID = 1505077643567956069
            DRAGON_ROLE_ID = 1505083974509269074

            try:
                def get_icon(path, earned):
                    img = Image.open(path).convert("RGBA")
                    if not earned:
                        r, g, b, a = img.split()
                        a = a.point(lambda p: p * 0.3)
                        img.putalpha(a)
                    return Editor(img).resize(icon_size)

                if os.path.exists("icons/sword_icon.png"):
                    has_sword = bool(member.get_role(SWORD_ROLE_ID))
                    sword_icon = get_icon("icons/sword_icon.png", has_sword)
                    background.paste(sword_icon, (current_icon_x, icon_y))
                    current_icon_x += icon_spacing
                        
                if os.path.exists("icons/dragon_icon.png"):
                    has_dragon = bool(member.get_role(DRAGON_ROLE_ID))
                    dragon_icon = get_icon("icons/dragon_icon.png", has_dragon)
                    background.paste(dragon_icon, (current_icon_x, icon_y))
                    current_icon_x += icon_spacing
                        
                cookie_x = current_icon_x

                if os.path.exists("icons/cookie_icon.png"):
                    cookie_icon = Editor("icons/cookie_icon.png").resize(icon_size)
                    background.paste(cookie_icon, (cookie_x, icon_y))
                    
                    text_x = cookie_x + 40 
                    
                    if streak_number >= 3 and os.path.exists("icons/fire_icon.png"):
                        fire_icon = Editor("icons/fire_icon.png").resize((45, 45))
                        background.paste(fire_icon, (text_x, icon_y - 18))

                    background.text((text_x + 22, icon_y - 0), f"{streak_number}", font=font_tiny, color="white", align="center", stroke_width=st_width, stroke_fill=st_col)

                if os.path.exists("icons/booster_icon.png"):
                    has_booster = bool(member.get_role(self.BOOSTER_ROLE_ID))
                    
                    img = Image.open("icons/booster_icon.png").convert("RGBA")
                    if not has_booster:
                        r, g, b, a = img.split()
                        a = a.point(lambda p: p * 0.3)
                        img.putalpha(a)
                    booster_icon = Editor(img).resize((35, 35))
                    background.paste(booster_icon, (230, 232))
                        
            except Exception as e:
                print(f"Error drawing rank card icons: {e}")

            background.text((550, 50), "Rank", font=font_small, color="white", stroke_width=st_width, stroke_fill=st_col)
            background.text((610, 42), f"#{dragon_rank}", font=font_large, color="white", stroke_width=st_width, stroke_fill=st_col)
            background.text((750, 50), "Level", font=font_small, color="#a97dd1", stroke_width=st_width, stroke_fill=st_col)
            background.text((820, 42), f"{level}", font=font_large, color="#a97dd1", stroke_width=st_width, stroke_fill=st_col)
            background.text((230, 130), f"{member.name}", font=font_medium, color="white", stroke_width=st_width, stroke_fill=st_col)
            background.text((230, 95), f"{current_role_name}", font=font_small, color="#d3d3d3", stroke_width=st_width, stroke_fill=st_col)

            is_glowing = member.get_role(self.BOOSTER_ROLE_ID) and (booster_glow == 'on')

            if is_glowing:
                background.rectangle((223, 178), width=614, height=49, fill=(160, 32, 240, 140), radius=15)
                background.rectangle((225, 180), width=610, height=45, fill=(0, 242, 254, 180), radius=13)
                background.rectangle((227, 182), width=606, height=41, fill=(255, 0, 128, 220), radius=11)
            else:
                background.rectangle((228, 183), width=604, height=39, fill="black", radius=12)

            background.rectangle((230, 185), width=600, height=35, fill="#3d3d3d", radius=10)

            if percentage > 0:
                bar_width = int(600 * percentage)
                if bar_width > 0:
                    background.rectangle((230, 185), width=max(bar_width, 20), height=35, fill=bar_color, radius=10)
            
            background.text((830, 155), f"Next level: {xp_within_level} / {needed_for_level} XP", font=font_small, color="white", align="right", stroke_width=st_width, stroke_fill=st_col)
            background.text((830, 238), f"Total: {xp} XP", font=font_small, color="#d3d3d3", align="right", stroke_width=st_width, stroke_fill=st_col)

            await ctx.send(file=discord.File(fp=background.image_bytes, filename="rank.png"))
        except Exception as e:
            print(f"Error: {e}")
            await ctx.send("There was an error generating the rank card.")

    @commands.hybrid_command(name="leaderboard", aliases=["levelscores"], description="View the server XP leaderboard!")
    async def leaderboard(self, ctx):
        await ctx.defer()

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT user_id, xp, level FROM users ORDER BY xp DESC"
            ) as cursor:
                entries = await cursor.fetchall()

        # Filter out users who are no longer in the server
        filtered_entries = [
            entry for entry in entries 
            if ctx.guild.get_member(entry[0]) is not None
        ]

        if not filtered_entries:
            return await ctx.send("No members found on the leaderboard yet!")

        view = LeaderboardView(self, ctx.author, filtered_entries)
        embed = view.build_embed()
        await ctx.send(embed=embed, view=view)

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
        app_commands.Choice(name="Shadows Into Light", value="shadows_light"),
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
        await self.add_xp(member, amount)
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT xp, level FROM users WHERE user_id = ?", (member.id,)) as cursor:
                result = await cursor.fetchone()
                
        if result:
            new_xp, new_level = result
            await interaction.response.send_message(f"✅ Added {amount} XP to {member.mention}! They now have **{new_xp} XP** (Level {new_level}).")
        else:
            await interaction.response.send_message(f"✅ Added {amount} XP to {member.mention}!")

    @app_commands.command(name="sync_levels", description="Syncs everyone's levels based on roles without resetting progress. (Admin only!)")
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

    @app_commands.command(name="purge_left_members", description="Removes users from the DB who are no longer in the server (Admin only)")
    @commands.has_permissions(administrator=True)
    async def purge_left_members(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        from database import ECONOMY_DB_NAME

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("ATTACH DATABASE ? AS economy", (ECONOMY_DB_NAME,))

            async with db.execute("SELECT user_id FROM main.users") as cursor:
                rows = await cursor.fetchall()

            deleted_count = 0

            for row in rows:
                user_id = row[0]

                # Check if the member is still in the guild
                if interaction.guild.get_member(user_id) is None:
                    await db.execute(
                        "DELETE FROM economy.inventory WHERE user_id = ?",
                        (user_id,)
                    )

                    await db.execute(
                        "DELETE FROM economy.pets WHERE user_id = ?",
                        (user_id,)
                    )

                    await db.execute(
                        "DELETE FROM economy.users WHERE user_id = ?",
                        (user_id,)
                    )

                    await db.execute(
                        "DELETE FROM main.users WHERE user_id = ?",
                        (user_id,)
                    )

                    deleted_count += 1

            await db.commit()
            await db.execute("DETACH DATABASE economy")
            
        await interaction.followup.send(f"✅ Cleaned up {deleted_count} former members from the database!", ephemeral=True)

    @commands.hybrid_command(name="reset", description="Reset a user's Enceladus data.")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(
        reset_type="Choose what data to reset.",
        member="The member whose data you want to reset."
    )
    @app_commands.choices(reset_type=[
        app_commands.Choice(name="all", value="all"),
        app_commands.Choice(name="xp", value="xp")
    ])
    async def reset(
        self,
        ctx: commands.Context,
        reset_type: app_commands.Choice[str],
        member: discord.Member
    ):
        if reset_type.value == "xp":
            await ctx.send(
                content=(
                    f"⚠️ Reset **XP and Level only** for {member.mention}?\n"
                    f"💰 Stardust, inventory, pets, profile data, and other progress "
                    f"will remain untouched."
                ),
                view=ResetConfirm(self, member, ctx.author.id),
                ephemeral=True
            )

        elif reset_type.value == "all":
            await ctx.send(
                content=(
                    f"☢️ **DANGER — COMPLETE ACCOUNT WIPE**\n\n"
                    f"This will permanently delete **ALL Enceladus data** for "
                    f"{member.mention}, including XP, Level, Stardust, profile data, "
                    f"inventory, and pets. This is a **dangerous** operation and "
                    f"**irreversible!**\n\n"
                    f"Are you ***absolutely*** sure?"
                ),
                view=FullResetConfirm(self, member, ctx.author.id),
                ephemeral=True
            )

    @app_commands.command(name="font_preview_setup", description="Sends the interactive font preview dropdown (Admin only)")
    @commands.has_permissions(administrator=True)
    async def font_preview_setup(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Rank Card Font Previewer! 🌠",
            description="Use the dropdown menu below to test out any of our custom fonts available! It will generate a private preview card just for you so you can see how your name and levels look before choosing.",
            color=discord.Color.purple()
        )
        await interaction.channel.send(embed=embed, view=FontView(self))
        await interaction.response.send_message("✅ Font preview menu deployed!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Leveling(bot))