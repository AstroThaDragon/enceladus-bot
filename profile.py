import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import os
import json
from easy_pil import Canvas, Editor, Font, load_image_async

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db_path(self):
        """Fetches the active database path from the Leveling cog or defaults to levels.db."""
        leveling_cog = self.bot.get_cog("Leveling")
        if leveling_cog and hasattr(leveling_cog, "db_path"):
            return leveling_cog.db_path
        return "levels.db"

    async def ensure_schema(self, db):
        """Ensures all required columns exist in the users table without resetting data."""
        async with db.execute("PRAGMA table_info(users)") as cursor:
            existing_columns = {row[1] async for row in cursor}

        required_columns = {
            "stardust": "INTEGER DEFAULT 0",
            "bio": "TEXT DEFAULT NULL",
            "profile_card": "TEXT DEFAULT 'default_nebula'",
            "equipped_title": "TEXT DEFAULT ''",
            "daily_streak": "INTEGER DEFAULT 0",
            "mining_upgrade": "INTEGER DEFAULT 0",
            "scavenging_upgrade": "INTEGER DEFAULT 0",
            "unlocked_backgrounds": "TEXT DEFAULT '[\"default\"]'"
        }

        for column, column_type in required_columns.items():
            if column not in existing_columns:
                await db.execute(
                    f"ALTER TABLE users ADD COLUMN {column} {column_type}"
                )

    async def get_user_profile(self, user_id):
        """Fetches leveling data from levels.db and Station data from economy.db."""
        from database import DB_NAME, ECONOMY_DB_NAME

        # Read XP and level from the leveling/Fortune database.
        async with aiosqlite.connect(DB_NAME) as db:
            async with db.execute(
                """
                SELECT level, xp
                FROM users
                WHERE user_id = ?
                """,
                (user_id,)
            ) as cursor:
                leveling_data = await cursor.fetchone()

        # Read Station/economy data and pet data from economy.db.
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            await db.commit()

            async with db.execute(
                """
                SELECT stardust, bio, profile_card, equipped_title, daily_streak, mining_upgrade, scavenging_upgrade, unlocked_backgrounds
                FROM users
                WHERE user_id = ?
                """,
                (user_id,)
            ) as cursor:
                economy_data = await cursor.fetchone()

            async with db.execute(
                """
                SELECT pet_stage
                FROM pets
                WHERE user_id = ?
                ORDER BY pet_id DESC
                LIMIT 1
                """,
                (user_id,)
            ) as cursor:
                pet_data = await cursor.fetchone()

        # Fallback values if the user has not been initialized yet.
        if not leveling_data and not economy_data:
            return {
                "level": 0,
                "xp": 0,
                "stardust": 0,
                "bio": "Exploring the outer rims of Enceladus Station. 🚀",
                "bg": "default_nebula",
                "pet": "egg",
                "title": "",
                "daily_streak": 0,
                "mining_upgrade": 0,
                "scavenging_upgrade": 0,
            }

        stored_level = leveling_data[0] if leveling_data else 0
        xp = leveling_data[1] if leveling_data else 0

        stardust = economy_data[0] if economy_data else 0
        bio = economy_data[1] if economy_data else None
        profile_card = economy_data[2] if economy_data else None
        equipped_title = economy_data[3] if economy_data else ""
        daily_streak = economy_data[4] if economy_data else 0
        mining_upgrade = economy_data[5] if economy_data else 0
        scavenging_upgrade = economy_data[6] if economy_data else 0
        unlocked_backgrounds_raw = economy_data[7] if economy_data else '["default"]'

        try:
            unlocked_backgrounds = json.loads(unlocked_backgrounds_raw or '["default"]')
            if not isinstance(unlocked_backgrounds, list):
                unlocked_backgrounds = ["default"]
        except (TypeError, ValueError):
            unlocked_backgrounds = ["default"]

        if "default" not in unlocked_backgrounds:
            unlocked_backgrounds.insert(0, "default")

        # Calculate true level dynamically from accumulated XP.
        leveling_cog = self.bot.get_cog("Leveling")
        calculated_level = stored_level or 0

        if leveling_cog and hasattr(leveling_cog, "get_xp_for_level"):
            temp_level = 0

            while (xp or 0) >= leveling_cog.get_xp_for_level(temp_level + 1):
                temp_level += 1

            calculated_level = temp_level

        final_level = max(stored_level or 0, calculated_level)

        return {
            "level": final_level,
            "xp": xp or 0,
            "stardust": stardust or 0,
            "bio": bio or "Exploring the outer rims of Enceladus Station. 🚀",
            "title": equipped_title or "",
            "bg": profile_card or "default_nebula",
            "pet": pet_data[0] if pet_data else "egg",
            "daily_streak": max(0, daily_streak or 0),
            "mining_upgrade": max(0, min(5, mining_upgrade or 0)),
            "scavenging_upgrade": max(0, min(5, scavenging_upgrade or 0)),
            "unlocked_backgrounds": unlocked_backgrounds
        }

    @commands.hybrid_command(name="profile", description="View your cosmic station profile.")
    @app_commands.describe(member="The user whose profile you want to view")
    async def profile(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        await ctx.defer()

        # 1. Fetch user data
        data = await self.get_user_profile(target.id)

        # 2. Render Station Viewport (600x300 Environment Window)
        viewport_w, viewport_h = 600, 300
        canvas = Canvas((viewport_w, viewport_h), color="#0B0F19")
        viewport = Editor(canvas)

        bg_name = data['bg']
        if bg_name == "default":
            bg_name = "default_nebula"

        # Load Background Environment
        try:
            bg_image = Editor(f"assets/presets/backgrounds/{bg_name}.png").resize((viewport_w, viewport_h))
            viewport.paste(bg_image, (0, 0))
        except FileNotFoundError:
            viewport.rectangle((0, 0), width=viewport_w, height=viewport_h, fill="#1E2333")

        # Load & Paste Active Companion/Pet Sprite into the environment
        try:
            pet_image = Editor(f"assets/pets/{data['pet']}.png").resize((120, 120))
            viewport.paste(pet_image, (440, 150))
        except FileNotFoundError:
            pass

        # Save canvas to file attachment
        file = discord.File(fp=viewport.image_bytes, filename="viewport.png")

        # 3. Assemble Embed
        embed = discord.Embed(
            title=f"🛸 Personnel Record — {target.display_name}",
            description=(
                f"🏷️ **{data['title']}**\n"
                f"📜 *{data['bio']}*"
                if data["title"]
                else f"📜 *{data['bio']}*"
            ),
            color=target.color or discord.Color.blue()
        )
        
        # User's avatar in the top-right thumbnail spot
        embed.set_thumbnail(url=target.display_avatar.url)
        
        # Native Discord Stat Fields
        embed.add_field(name="⭐ Rank & XP", value=f"Level `{data['level']}` • `{data['xp']:,} XP`", inline=True)
        embed.add_field(name="✨ Stardust", value=f"`{data['stardust']:,}`", inline=True)
        embed.add_field(name="🔥 Daily Streak", value=f"`{data['daily_streak']} days`", inline=True)
        embed.add_field(
            name="🛠️ Exploration Upgrades",
            value=(
                f"⛏️ Mining Laser — **Tier {data['mining_upgrade']}/5**\n"
                f"🤖 Scavenging Drone — **Tier {data['scavenging_upgrade']}/5**"
            ),
            inline=False
        )
        embed.add_field(name="🐉 Companion", value=f"`{data['pet'].capitalize()}`", inline=True)
        
        # Environment Window Image
        embed.set_image(url="attachment://viewport.png")

        await ctx.send(file=file, embed=embed)

    @commands.hybrid_command(
        name="bio",
        description="Set your Enceladus Station profile biography."
    )
    @app_commands.describe(
        text="The biography you want displayed on your profile."
    )
    async def bio(self, ctx: commands.Context, text: str):
        await ctx.defer(ephemeral=True)

        text = text.strip()

        # Keep profile bios short enough to fit nicely on the profile card.
        if len(text) > 180:
            return await ctx.send(
                f"❌ **Your bio is too long!** "
                f"Please keep it to **180 characters or fewer** "
                f"({len(text)}/180)."
            )

        if not text:
            return await ctx.send(
                "❌ **Your bio can't be empty.** "
                "Use `/bio reset` if you want to restore the default bio."
            )

        from database import ECONOMY_DB_NAME

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await db.execute(
                """
                INSERT INTO users (user_id, bio)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    bio = excluded.bio
                """,
                (ctx.author.id, text)
            )
            await db.commit()

        await ctx.send(
            f"**Bio updated!**"
            f"Use `/profile` to check it out!\n"
            f"> {text}",
            ephemeral=True
        )

    @commands.hybrid_command(
        name="moderatebio",
        description="Force a user's profile bio to be marked as Moderated."
    )
    @app_commands.describe(
        member="The user whose bio should be moderated.",
        reason="Optional reason for the moderation action."
    )
    async def moderatebio(
        self, ctx: commands.Context,
        member: discord.Member,
        reason: str = "No reason provided"
    ):
        if not ctx.guild:
            return await ctx.send(
                "❌ This command can only be used in a server."
            )

        is_owner = await self.bot.is_owner(ctx.author)

        mod_role_id = int(os.getenv("MOD_ROLE_ID", "0"))
        admin_role_id = int(os.getenv("ADMIN_ROLE_ID", "0"))

        has_staff_role = any(
            role.id in {mod_role_id, admin_role_id}
            for role in ctx.author.roles
        )

        if not (is_owner or has_staff_role):
            return

        from database import ECONOMY_DB_NAME

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await db.execute(
                """
                INSERT INTO users (user_id, bio)
                VALUES (?, 'Moderated')
                ON CONFLICT(user_id) DO UPDATE SET
                    bio = 'Moderated'
                """,
                (member.id,)
            )
            await db.commit()

        await ctx.send(
            f"🛡️ **Bio Moderated**\n"
            f"User: {member.mention}\n"
            f"Reason: {reason}"
        )

    async def background_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ):
        """Show backgrounds permanently unlocked by the user."""
        user_id = interaction.user.id
        current = current.lower().strip()

        backgrounds = {
            "default": "Default Nebula",
            "neon_grid": "Cyberpunk Neon Grid",
            "deep_void": "Deep Void Galaxy",
            "solaris_ring": "Solaris Ring System",
        }

        from database import ECONOMY_DB_NAME

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)

            async with db.execute(
                "SELECT unlocked_backgrounds FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()

        unlocked_backgrounds = {"default"}

        if row:
            try:
                stored = json.loads(row[0] or '["default"]')
                if isinstance(stored, list):
                    unlocked_backgrounds.update(
                        item_id for item_id in stored if item_id in backgrounds
                    )
            except (TypeError, ValueError):
                pass

        choices = []

        for item_id in unlocked_backgrounds:
            display_name = backgrounds[item_id]

            if current and current not in display_name.lower():
                continue

            emoji = {
                "default": "🌌",
                "neon_grid": "🌆",
                "deep_void": "🌌",
                "solaris_ring": "💫",
            }.get(item_id, "🖼️")

            choices.append(
                app_commands.Choice(
                    name=f"{emoji} {display_name}",
                    value=item_id
                )
            )

        choices.sort(key=lambda choice: choice.name.lower())
        return choices[:25]

    @commands.hybrid_command(
        name="background",
        description="Equip an unlocked background for your profile card."
    )
    @app_commands.describe(background="Choose an unlocked background for your profile card.")
    @app_commands.autocomplete(background=background_autocomplete)
    async def background(self, ctx: commands.Context, background: str):
        await ctx.defer()
        user_id = ctx.author.id
        background = background.lower().strip()

        valid_backgrounds = {
            "default": "Default Nebula",
            "neon_grid": "Cyberpunk Neon Grid City",
            "deep_void": "Deep Void",
            "solaris_ring": "Solaris Ring"
        }

        if background not in valid_backgrounds:
            return await ctx.send(
                "❌ That background isn't unlocked. Please choose one from the dropdown."
            )

        from database import ECONOMY_DB_NAME

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)

            async with db.execute(
                "SELECT unlocked_backgrounds FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()

            unlocked_backgrounds = {"default"}

            if row:
                try:
                    stored = json.loads(row[0] or '["default"]')
                    if isinstance(stored, list):
                        unlocked_backgrounds.update(stored)
                except (TypeError, ValueError):
                    pass

            if background not in unlocked_backgrounds:
                return await ctx.send(
                    "🔒 **Background Locked!** Redeem its voucher with `/voucher` first."
                )

            await db.execute(
                "UPDATE users SET profile_card = ? WHERE user_id = ?",
                (background, user_id)
            )
            await db.commit()

        await ctx.send(
            f"{ctx.author.mention} 🌟 **Profile Updated!** Successfully equipped "
            f"**{valid_backgrounds[background]}** as your active profile background. "
            f"Run `/profile` to check it out!"
        )

    @commands.hybrid_command(
        name="voucher",
        description="Redeem one of your owned vouchers."
    )
    async def voucher(self, ctx: commands.Context):
        await ctx.defer()

        user_id = ctx.author.id
        from database import ECONOMY_DB_NAME

        voucher_rewards = {
            "neon_grid": {
                "name": "Cyberpunk Neon Grid",
                "emoji": "🌆",
                "unlock_type": "background",
            },
            "deep_void": {
                "name": "Deep Void Galaxy",
                "emoji": "🌌",
                "unlock_type": "background",
            },
            "solaris_ring": {
                "name": "Solaris Ring System",
                "emoji": "💫",
                "unlock_type": "background",
            },
        }

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)

            async with db.execute(
                """
                SELECT item_id, quantity
                FROM inventory
                WHERE user_id = ?
                  AND quantity > 0
                  AND item_type IN ('voucher', 'background_voucher')
                ORDER BY item_id
                """,
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()

        owned_vouchers = [
            (item_id, quantity)
            for item_id, quantity in rows
            if item_id in voucher_rewards
        ]

        if not owned_vouchers:
            return await ctx.send(
                "🎟️ **You don't have any redeemable vouchers!** "
                "Check the shop for available vouchers."
            )

        cog = self

        class VoucherSelect(discord.ui.Select):
            def __init__(self):
                options = [
                    discord.SelectOption(
                        label=reward["name"],
                        description=f"You own {quantity}x of this voucher.",
                        emoji=reward["emoji"],
                        value=item_id
                    )
                    for item_id, quantity in owned_vouchers[:25]
                    for reward in [voucher_rewards[item_id]]
                ]
                super().__init__(
                    placeholder="Choose a voucher to redeem...",
                    min_values=1,
                    max_values=1,
                    options=options
                )

            async def callback(self, interaction: discord.Interaction):
                if interaction.user.id != user_id:
                    return await interaction.response.send_message(
                        "❌ This menu belongs to someone else.",
                        ephemeral=True
                    )

                item_id = self.values[0]
                reward = voucher_rewards[item_id]

                async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
                    await cog.ensure_schema(db)

                    async with db.execute(
                        """
                        SELECT quantity
                        FROM inventory
                        WHERE user_id = ? AND item_id = ? AND quantity > 0
                        """,
                        (user_id, item_id)
                    ) as cursor:
                        voucher_row = await cursor.fetchone()

                    if not voucher_row:
                        return await interaction.response.send_message(
                            "❌ You no longer have that voucher.",
                            ephemeral=True
                        )

                    async with db.execute(
                        "SELECT unlocked_backgrounds FROM users WHERE user_id = ?",
                        (user_id,)
                    ) as cursor:
                        user_row = await cursor.fetchone()

                    try:
                        unlocked = json.loads(
                            user_row[0] if user_row and user_row[0] else '["default"]'
                        )
                        if not isinstance(unlocked, list):
                            unlocked = ["default"]
                    except (TypeError, ValueError):
                        unlocked = ["default"]

                    if item_id in unlocked:
                        return await interaction.response.send_message(
                            f"🔒 **{reward['name']}** is already permanently unlocked. "
                            "You cannot redeem or buy another copy.",
                            ephemeral=True
                        )

                    unlocked.append(item_id)

                    await db.execute(
                        "UPDATE users SET unlocked_backgrounds = ? WHERE user_id = ?",
                        (json.dumps(unlocked), user_id)
                    )

                    if voucher_row[0] > 1:
                        await db.execute(
                            """
                            UPDATE inventory
                            SET quantity = quantity - 1
                            WHERE user_id = ? AND item_id = ?
                            """,
                            (user_id, item_id)
                        )
                    else:
                        await db.execute(
                            """
                            DELETE FROM inventory
                            WHERE user_id = ? AND item_id = ?
                            """,
                            (user_id, item_id)
                        )

                    await db.commit()

                await interaction.response.edit_message(
                    content=(
                        f"{interaction.user.mention} 🎟️ **Voucher Redeemed!**\n"
                        f"{reward['emoji']} **{reward['name']}** is now permanently unlocked!\n"
                        "You can select it anytime with `/background`."
                    ),
                    embed=None,
                    view=None
                )

        class VoucherView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=300)
                self.add_item(VoucherSelect())

            async def interaction_check(self, interaction: discord.Interaction):
                if interaction.user.id != user_id:
                    await interaction.response.send_message(
                        "❌ This menu belongs to someone else.",
                        ephemeral=True
                    )
                    return False
                return True

        embed = discord.Embed(
            title=f"🎟️ {ctx.author.display_name}'s Vouchers",
            description=(
                "Redeem a voucher to permanently unlock its reward.\n"
                "Choose one below:"
            ),
            color=discord.Color.gold()
        )

        for item_id, quantity in owned_vouchers[:25]:
            reward = voucher_rewards[item_id]
            embed.add_field(
                name=f"{reward['emoji']} {reward['name']}",
                value=f"Owned: **{quantity}x**",
                inline=False
            )

        embed.set_footer(text="Redeemed backgrounds remain permanently unlocked.")

        await ctx.send(embed=embed, view=VoucherView())

async def setup(bot):
    await bot.add_cog(Profile(bot))