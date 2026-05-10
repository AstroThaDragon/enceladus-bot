import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiosqlite
from datetime import datetime, time, timezone, timedelta

# 1. Define the time OUTSIDE the class so the decorator can see it
# EST is UTC-5
est = timezone(timedelta(hours=-5))
est_midnight = time(hour=0, minute=0, tzinfo=est)

class BirthdayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_birthdays.start() # type: ignore

    def cog_unload(self):
        self.check_birthdays.cancel() # type: ignore

    @app_commands.command(name="set_birthday", description="Set your birthday (Month/Day)!")
    @app_commands.describe(month="Month (1-12)", day="Day (1-31)")
    async def set_birthday(self, interaction: discord.Interaction, month: int, day: int):
        if not (1 <= month <= 12) or not (1 <= day <= 31):
            return await interaction.response.send_message("Please provide a valid Month and Day!", ephemeral=True)
        
        async with aiosqlite.connect("/app/data/birthdays.db") as db:
            await db.execute("INSERT OR REPLACE INTO birthdays (user_id, month, day) VALUES (?, ?, ?)", 
                             (interaction.user.id, month, day))
            await db.commit()
        
        await interaction.response.send_message(f"Registered! I'll give you the role on **{month}/{day}**!", ephemeral=True)

    # 2. Use the variable we defined at the top
    @tasks.loop(time=est_midnight)
    async def check_birthdays(self):
        await self.bot.wait_until_ready()
        
        now = datetime.now(est) # Use EST for the comparison too!
        current_month = now.month
        current_day = now.day
        
        BIRTHDAY_ROLE_ID = 1503120250139578440 
        GUILD_ID = 593387999316934676 
        ANNOUNCEMENT_CHANNEL_ID = 1306602160527507456

        guild = self.bot.get_guild(GUILD_ID)
        if not guild: return
        
        role = guild.get_role(BIRTHDAY_ROLE_ID)
        if not role: return

        # Cleanup yesterday
        for member in role.members:
            try:
                await member.remove_roles(role)
            except:
                pass

        # Find today's stars
        birthday_members = []
        async with aiosqlite.connect("/app/data/birthdays.db") as db:
            async with db.execute("SELECT user_id FROM birthdays WHERE month = ? AND day = ?", 
                                  (current_month, current_day)) as cursor:
                async for (user_id,) in cursor:
                    member = guild.get_member(user_id)
                    if member:
                        await member.add_roles(role)
                        birthday_members.append(member.mention)

        if birthday_members:
            channel = guild.get_channel(ANNOUNCEMENT_CHANNEL_ID)
            if channel:
                shoutout_embed = discord.Embed(
                    title="🌌 Cosmic Birthday Celebration!",
                    description=(
                        f"Today we have some very special stars shining bright!\n\n"
                        f"**Happy Birthday to:**\n{', '.join(birthday_members)}\n\n"
                        f"Everyone give a warm happy birthday wish to our special birthday stars! 🎂✨"
                    ),
                    color=discord.Color.from_rgb(114, 0, 225)
                )
                shoutout_embed.set_thumbnail(url="https://media.discordapp.net/attachments/916221943101947914/1497326085099094209/IMG_20191102_191207_871.png")
                shoutout_embed.set_footer(text="May your day be filled with magical stardust and joy!")

                await channel.send(content=f"Hey <@&{BIRTHDAY_ROLE_ID}>, Happy Birthday!!", embed=shoutout_embed)

    @check_birthdays.before_loop
    async def before_check_birthdays(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(BirthdayCog(bot))