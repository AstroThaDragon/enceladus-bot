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
        
        await interaction.response.send_message(f"Registered! I'll give you the role and ping you on **{month}/{day}**!")

    @app_commands.command(name="upcoming_birthdays", description="View upcoming server birthdays!")
    async def upcoming_birthdays(self, interaction: discord.Interaction):

        guild = interaction.guild
        if not guild:
            return await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True
            )

        now = datetime.now(est)

        async with aiosqlite.connect("/app/data/birthdays.db") as db:
            async with db.execute(
                "SELECT user_id, month, day FROM birthdays"
            ) as cursor:
                rows = await cursor.fetchall()

        if not rows:
            return await interaction.response.send_message(
                "No birthdays have been registered yet!",
                ephemeral=True
            )

        upcoming = []

        for user_id, month, day in rows:
            member = guild.get_member(user_id)

            # Skip users no longer in the server
            if not member:
                continue

            try:
                birthday_this_year = datetime(
                    year=now.year,
                    month=month,
                    day=day,
                    tzinfo=est
                )
            except ValueError:
                # Invalid dates like Feb 30
                continue

            # If already passed this year, use next year
            if birthday_this_year < now:
                birthday_this_year = datetime(
                    year=now.year + 1,
                    month=month,
                    day=day,
                    tzinfo=est
                )

            days_until = (birthday_this_year - now).days

            upcoming.append((
                days_until,
                member.display_name,
                month,
                day
            ))

        if not upcoming:
            return await interaction.response.send_message(
                "No valid birthdays found!",
                ephemeral=True
            )

        # Sort by closest birthday
        upcoming.sort(key=lambda x: x[0])

        # Show top 10 upcoming birthdays
        birthday_lines = []

        for days_until, name, month, day in upcoming[:10]:

            if days_until == 0:
                countdown = "🎉 Today!"
            elif days_until == 1:
                countdown = "⏳ 1 day away"
            else:
                countdown = f"⏳ {days_until} days away"

            birthday_lines.append(
                f"**{name}** — `{month}/{day}` • {countdown}"
            )

        embed = discord.Embed(
            title="🎂 Upcoming Birthdays",
            description="\n".join(birthday_lines),
            color=discord.Color.from_rgb(114, 0, 225)
        )

        embed.set_footer(
            text="Cosmic birthday tracker ✨"
        )

        await interaction.response.send_message(embed=embed)

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