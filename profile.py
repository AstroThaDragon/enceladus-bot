import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import os
import json
from easy_pil import Canvas, Editor, Font, load_image_async

# Artwork credits for profile backgrounds.
# Replace each placeholder with the artist's preferred credit name.
# Leave the value as None when no artwork credit is needed.
BACKGROUND_ARTISTS = {
    "default": "NASA Hubble Space Telescope",
    "default_nebula": "NASA Hubble Space Telescope",
    "neon_grid": "pikisuperstar on Magnific",
    "deep_void": "Marek Pavlík on Unsplash",
    "solaris_ring": "NASA / Solar Dynamics Observatory (SDO)",
    "halloween_haunted": "@john_silliman on Unsplash",
    "halloween_candy_collector": "Yaroslav Danylchenko0",
    "halloween_haunting_friend": "@helloimnik on Unsplash",
    "halloween_trick_or_treat": "Daisy Anderson on Pexels",
    "background_glowing_gem": "SynoMatesXD on Reddit",
    "background_malo": "@upsetfroglet on Tumblr",

    # Haunted achievement backgrounds
    "background_the_graveyard": "Just Jus on Unsplash",
    "background_abandoned_sanctuary": "Giancarlo Corti on Unsplash",
    "background_midnight_pizzeria": "InkBuddy10 on Reddit",
    "background_dead_air": "Dan Coe on Flickr",
    "background_fogbound": "KoolShooters on Pexels",
    "background_dead_end": "Rebecca Johnsen on Unsplash",
    "background_watched_from_the_trees": "Ben Griffiths on Unsplash",
    "background_haunted_item_collector": "Michel Bocquet on Unsplash",
    "background_corrupted_reality": "Egor Komarov on Unsplash",
}

BACKGROUND_COLLECTIONS = {
    "shop": {
        "label": "🛒 Shop Backgrounds",
        "emoji": "🛒",
        "items": [
            "default",
            "neon_grid",
            "deep_void",
            "solaris_ring",
        ],
    },
    "halloween": {
        "label": "🎃 Halloween",
        "emoji": "🎃",
        "items": [
            "halloween_haunted",
            "halloween_candy_collector",
            "halloween_haunting_friend",
            "halloween_trick_or_treat",
            "background_glowing_gem",
            "background_malo",
            "background_the_graveyard",
            "background_abandoned_sanctuary",
            "background_midnight_pizzeria",
            "background_dead_air",
            "background_fogbound",
            "background_dead_end",
            "background_watched_from_the_trees",
            "background_haunted_item_collector",
            "background_corrupted_reality",
        ],
    },
}

BACKGROUND_COLLECTION_INFO = {
    "default": {
        "name": "Default Nebula", "emoji": "🌌",
        "obtained": "Available automatically when you join the station.",
    },
    "neon_grid": {
        "name": "Cyberpunk Neon Grid City", "emoji": "🌆",
        "obtained": "Redeem the **Cyberpunk Neon Grid** voucher.",
    },
    "deep_void": {
        "name": "Deep Void Galaxy", "emoji": "🌌",
        "obtained": "Redeem the **Deep Void Galaxy** voucher.",
    },
    "solaris_ring": {
        "name": "Solaris Ring System", "emoji": "💫",
        "obtained": "Redeem the **Solaris Ring System** voucher.",
    },
    "halloween_haunted": {
        "name": "Haunted Halloween", "emoji": "🎃",
        "obtained": "Collect at least **50% of the Halloween collectibles**.",
    },
    "halloween_candy_collector": {
        "name": "Candy Collector", "emoji": "🍬",
        "obtained": "Consume **100 pieces of Halloween Candy and/or Trick-or-Treat Bags**.",
    },
    "halloween_haunting_friend": {
        "name": "Haunting Friend", "emoji": "🐣",
        "obtained": "Hatch a **Halloween Egg**.",
    },
    "halloween_trick_or_treat": {
        "name": "Trick-or-Treat", "emoji": "🎃",
        "obtained": "Craft **25 Trick-or-Treat Bags**.",
    },
    "background_glowing_gem": {
        "name": "Glowing Gem", "emoji": "💎",
        "obtained": "Use the **Doll of Tails**.",
    },
    "background_malo": {
        "name": "MalO", "emoji": "📱",
        "obtained": "Use the **Hacked Phone**.",
    },
    "background_the_graveyard": {
        "name": "The Graveyard", "emoji": "🪦",
        "obtained": "Discover every rare discovery in the **Forgotten Graveyard**.",
    },
    "background_abandoned_sanctuary": {
        "name": "Abandoned Sanctuary", "emoji": "⛪",
        "obtained": "Discover every rare discovery in the **Abandoned Church**.",
    },
    "background_midnight_pizzeria": {
        "name": "Midnight Pizzeria", "emoji": "🍕",
        "obtained": "Discover every rare discovery in the **Dilapidated Pizzeria**.",
    },
    "background_dead_air": {
        "name": "Dead Air", "emoji": "📡",
        "obtained": "Discover every rare discovery in the **Abandoned Broadcast Station**.",
    },
    "background_fogbound": {
        "name": "Fogbound", "emoji": "🌫️",
        "obtained": "Discover every rare discovery in **Fogbound Town**.",
    },
    "background_dead_end": {
        "name": "Dead-End", "emoji": "🛣️",
        "obtained": "Discover every rare discovery on the **Dead-End Highway**.",
    },
    "background_watched_from_the_trees": {
        "name": "Watched From the Trees", "emoji": "🌲",
        "obtained": "Discover every rare discovery in the **Silent Campground**.",
    },
    "background_haunted_item_collector": {
        "name": "Haunted Item Collector", "emoji": "🔧",
        "obtained": "Craft all **23 location-based Haunted collectibles**.",
    },
    "background_corrupted_reality": {
        "name": "CORRUPTED REALITY", "emoji": "💾",
        "obtained": "Hatch your first pet from a **Glitched Egg**.",
    },
}

BACKGROUND_ASSET_NAMES = {
    "default": "default_nebula",
    "halloween_haunting_friend": "halloween_hunting_friend",
}


class BackgroundCollectionView(discord.ui.View):
    def __init__(self, cog, user_id, unlocked):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        self.unlocked = set(unlocked)
        self.section = "main"
        self.page = 0
        self.items = []
        self._refresh_items()

    def _refresh_items(self):
        if self.section == "main":
            self.items = []
            return

        if self.section == "events":
            self.items = []
            return

        category = BACKGROUND_COLLECTIONS.get(self.section)
        if not category:
            self.items = []
            return

        self.items = [
            item_id for item_id in category["items"]
            if item_id in self.unlocked
        ]
        self.page = max(0, min(self.page, max(0, len(self.items) - 1)))

    def _rebuild_buttons(self):
        self.clear_items()

        if self.section == "main":
            shop = discord.ui.Button(
                label="Shop Backgrounds", emoji="🛒",
                style=discord.ButtonStyle.primary
            )
            events = discord.ui.Button(
                label="Event Backgrounds", emoji="🎃",
                style=discord.ButtonStyle.primary
            )
            shop.callback = self._shop_callback
            events.callback = self._events_callback
            self.add_item(shop)
            self.add_item(events)
            return

        if self.section == "events":
            halloween = discord.ui.Button(
                label="Halloween", emoji="🎃",
                style=discord.ButtonStyle.primary
            )
            back = discord.ui.Button(
                label="Back", emoji="↩️",
                style=discord.ButtonStyle.secondary
            )
            halloween.callback = self._halloween_callback
            back.callback = self._back_main_callback
            self.add_item(halloween)
            self.add_item(back)
            return

        prev_button = discord.ui.Button(
            label="Previous", emoji="◀️",
            style=discord.ButtonStyle.secondary,
            disabled=(self.page <= 0)
        )
        next_button = discord.ui.Button(
            label="Next", emoji="▶️",
            style=discord.ButtonStyle.secondary,
            disabled=(self.page >= len(self.items) - 1)
        )
        back_button = discord.ui.Button(
            label="Back", emoji="↩️",
            style=discord.ButtonStyle.secondary
        )
        prev_button.callback = self._previous_callback
        next_button.callback = self._next_callback
        back_button.callback = self._back_category_callback
        self.add_item(prev_button)
        self.add_item(next_button)
        self.add_item(back_button)

    async def render(self):
        self._rebuild_buttons()

        if self.section == "main":
            embed = discord.Embed(
                title="🖼️ Background Collection",
                description=(
                    "Browse the profile backgrounds you have permanently unlocked.\n\n"
                    "Choose a category below to get started.\n"
                    "Locked backgrounds are not shown here."
                ),
                color=discord.Color.blurple()
            )
            embed.set_footer(text="Your collection is separate from your currently equipped background.")
            return embed, None

        if self.section == "events":
            embed = discord.Embed(
                title="🎃 Event Backgrounds",
                description=(
                    "Choose an event to browse the backgrounds you've unlocked from it.\n\n"
                    "More events can be added here in the future!"
                ),
                color=discord.Color.orange()
            )
            embed.set_footer(text="Only backgrounds you own are shown in each collection.")
            return embed, None

        category = BACKGROUND_COLLECTIONS[self.section]
        if not self.items:
            embed = discord.Embed(
                title=f"{category['emoji']} {category['label'].split(' ', 1)[1]}",
                description="You don't own any backgrounds in this collection yet.",
                color=discord.Color.dark_grey()
            )
            return embed, None

        item_id = self.items[self.page]
        info = BACKGROUND_COLLECTION_INFO[item_id]
        active = await self.cog.get_user_profile(self.user_id)
        is_equipped = (active.get("bg") or "default_nebula") == item_id

        embed = discord.Embed(
            title=f"{info['emoji']} {info['name']}",
            description=(
                ("✨ **Currently Equipped**\n\n" if is_equipped else "") +
                f"**Obtained:** {info['obtained']}"
            ),
            color=discord.Color.gold() if is_equipped else discord.Color.blurple()
        )
        embed.set_footer(text=f"{category['label']} • Background {self.page + 1}/{len(self.items)}")

        asset_name = BACKGROUND_ASSET_NAMES.get(item_id, item_id)
        asset_path = os.path.join("assets", "presets", "backgrounds", f"{asset_name}.png")
        if os.path.exists(asset_path):
            file = discord.File(asset_path, filename="background_collection.png")
            embed.set_image(url="attachment://background_collection.png")
            return embed, file

        embed.add_field(
            name="Preview",
            value="🖼️ Background artwork is currently unavailable.",
            inline=False
        )
        return embed, None

    async def _update(self, interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "❌ This collection belongs to someone else.",
                ephemeral=True
            )

        embed, file = await self.render()
        kwargs = {"embed": embed, "view": self}
        if file:
            kwargs["attachments"] = [file]
        else:
            kwargs["attachments"] = []
        await interaction.response.edit_message(**kwargs)

    async def _shop_callback(self, interaction):
        self.section = "shop"
        self.page = 0
        self._refresh_items()
        await self._update(interaction)

    async def _events_callback(self, interaction):
        self.section = "events"
        self.page = 0
        self._refresh_items()
        await self._update(interaction)

    async def _halloween_callback(self, interaction):
        self.section = "halloween"
        self.page = 0
        self._refresh_items()
        await self._update(interaction)

    async def _back_main_callback(self, interaction):
        self.section = "main"
        self.page = 0
        self._refresh_items()
        await self._update(interaction)

    async def _back_category_callback(self, interaction):
        self.section = "main" if self.section == "shop" else "events"
        self.page = 0
        self._refresh_items()
        await self._update(interaction)

    async def _previous_callback(self, interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "❌ This collection belongs to someone else.", ephemeral=True
            )
        self.page = max(0, self.page - 1)
        await self._update(interaction)

    async def _next_callback(self, interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "❌ This collection belongs to someone else.", ephemeral=True
            )
        self.page = min(len(self.items) - 1, self.page + 1)
        await self._update(interaction)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


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
                SELECT pet_type, pet_stage, nickname, level, xp
                FROM pets
                WHERE user_id = ? AND is_active = 1
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
                "pet": None,
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

        active_pet = None
        if pet_data:
            pet_type, pet_stage, nickname, pet_level, pet_xp = pet_data
            pet_id = pet_type or pet_stage
            try:
                from pets import get_pet_definition
                pet_definition = get_pet_definition(pet_id)
            except Exception:
                pet_definition = None

            if pet_definition:
                active_pet = {
                    "id": pet_id,
                    "name": pet_definition["name"],
                    "emoji": pet_definition["emoji"],
                    "nickname": nickname or "",
                    "level": pet_level or 1,
                    "xp": pet_xp or 0,
                }

        # Calculate true level dynamically from accumulated XP.
        leveling_cog = self.bot.get_cog("Leveling")
        calculated_level = stored_level or 0

        if leveling_cog and hasattr(leveling_cog, "get_xp_for_level"):
            temp_level = 0

            while (xp or 0) >= leveling_cog.get_xp_for_level(temp_level + 1):
                temp_level += 1

            calculated_level = temp_level

        final_level = max(stored_level or 0, calculated_level)

        # Resolve the stored internal title ID to its configured display name.
        # Keep the database value as the ID, but never expose IDs such as
        # "title_something_is_very_wrong" on the profile card.
        display_title = ""
        if equipped_title:
            try:
                from inventory import ITEM_REGISTRY
                title_info = ITEM_REGISTRY.get(equipped_title)
                if title_info and str(title_info.get("type", "")).lower() == "title":
                    display_title = title_info.get("name") or ""
                    # Inventory title names may include the shop's title emoji.
                    if display_title:
                        display_title = display_title.strip()
                        if display_title.startswith("🏷️"):
                            display_title = display_title[len("🏷️"):].strip()
                        if display_title.lower().startswith("title:"):
                            display_title = display_title[len("title:"):].strip()
            except Exception:
                display_title = ""

        # Fallback for legacy/missing registry entries: make a readable name
        # rather than ever exposing the raw internal ID.
        if equipped_title and not display_title:
            display_title = (
                equipped_title.removeprefix("title_")
                .replace("_", " ")
                .title()
            )

        return {
            "level": final_level,
            "xp": xp or 0,
            "stardust": stardust or 0,
            "bio": bio or "Exploring the outer rims of Enceladus Station. 🚀",
            "title": display_title,
            "bg": profile_card or "default_nebula",
            "pet": active_pet,
            "daily_streak": max(0, daily_streak or 0),
            "mining_upgrade": max(0, min(5, mining_upgrade or 0)),
            "scavenging_upgrade": max(0, min(5, scavenging_upgrade or 0)),
            "unlocked_backgrounds": unlocked_backgrounds
        }

    @commands.hybrid_command(name="profile", description="View your cosmic station profile.")
    @app_commands.describe(member="The user whose profile you want to view")
    async def profile(self, ctx: commands.Context, member: discord.Member | None = None):
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

        # Some existing background IDs do not exactly match their asset filenames.
        # Keep the IDs stable for saved unlocks/equipped profiles, and translate
        # them only when resolving the physical PNG asset.
        background_asset_names = {
            "halloween_haunted": "halloween_haunted_halloween",
            "halloween_haunting_friend": "halloween_hunting_friend",
        }
        bg_asset_name = background_asset_names.get(bg_name, bg_name)

        # Load Background Environment
        try:
            bg_image = Editor(
                f"assets/presets/backgrounds/{bg_asset_name}.png"
            ).resize((viewport_w, viewport_h))
            viewport.paste(bg_image, (0, 0))
        except FileNotFoundError:
            viewport.rectangle((0, 0), width=viewport_w, height=viewport_h, fill="#1E2333")

        # Load & Paste Active Companion/Pet Sprite into the environment
        if data.get("pet"):
            try:
                pet_image = Editor(
                    f"assets/pets/{data['pet']['id']}.png"
                ).resize((120, 120))
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
        embed.add_field(name="⭐ Rank & XP", value=f"Level **{data['level']}** • **{data['xp']:,} XP**", inline=True)
        embed.add_field(name="✨ Stardust", value=f"**{data['stardust']:,}**", inline=True)
        embed.add_field(name="🔥 Daily Streak", value=f"**{data['daily_streak']} days**", inline=True)
        embed.add_field(
            name="🛠️ Exploration Upgrades",
            value=(
                f"⛏️ Mining Laser — **Tier {data['mining_upgrade']}/5**\n"
                f"🤖 Scavenging Drone — **Tier {data['scavenging_upgrade']}/5**"
            ),
            inline=False
        )
        if data.get("pet"):
            pet_name = data["pet"]["nickname"] or data["pet"]["name"]
            companion_text = (
                f"{data['pet']['emoji']} **{pet_name}**\n"
                f"Level **{data['pet']['level']}**"
            )
        else:
            companion_text = "**None**"

        embed.add_field(name="🐾 Companion", value=companion_text, inline=True)
        
        # Environment Window Image
        embed.set_image(url="attachment://viewport.png")

        # Add an artwork credit only when the active background has one.
        # The profile data stores the actual background ID, so this also works
        # automatically for newly added backgrounds once they are listed above.
        active_background_id = data.get("bg") or "default"
        artist = BACKGROUND_ARTISTS.get(active_background_id)

        if artist:
            embed.set_footer(text=f"Artwork credit — {artist}")

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

        has_staff_role = isinstance(ctx.author, discord.Member) and any(
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
            "halloween_haunted": "Haunted Halloween",
            "halloween_candy_collector": "Candy Collector",
            "halloween_haunting_friend": "Haunting Friend",
            "halloween_trick_or_treat": "Trick-or-Treat",
            "background_glowing_gem": "Glowing Gem",
            "background_malo": "MalO",
            "background_the_graveyard": "The Graveyard",
            "background_abandoned_sanctuary": "Abandoned Sanctuary",
            "background_midnight_pizzeria": "Midnight Pizzeria",
            "background_dead_air": "Dead Air",
            "background_fogbound": "Fogbound",
            "background_dead_end": "Dead-End",
            "background_watched_from_the_trees": "Watched From the Trees",
            "background_haunted_item_collector": "Haunted Item Collector",
            "background_corrupted_reality": "CORRUPTED REALITY",
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
                "halloween_haunted": "🎃",
                "halloween_candy_collector": "🍬",
                "halloween_haunting_friend": "🐣",
                "halloween_trick_or_treat": "🎃",
                "background_glowing_gem": "💎",
                "background_malo": "📱",
                "background_the_graveyard": "🪦",
                "background_abandoned_sanctuary": "⛪",
                "background_midnight_pizzeria": "🍕",
                "background_dead_air": "📡",
                "background_fogbound": "🌫️",
                "background_dead_end": "🛣️",
                "background_watched_from_the_trees": "🌲",
                "background_haunted_item_collector": "🔧",
                "background_corrupted_reality": "💾",
            }.get(item_id, "🖼️")

            choices.append(
                app_commands.Choice(
                    name=f"{emoji} {display_name}",
                    value=item_id
                )
            )

        choices.sort(key=lambda choice: choice.name.lower())
        return choices[:25]

    async def _get_owned_backgrounds(self, user_id):
        """Return the user's permanently unlocked background IDs."""
        from database import ECONOMY_DB_NAME

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await self.ensure_schema(db)
            async with db.execute(
                "SELECT unlocked_backgrounds FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()

        unlocked = {"default"}
        if row:
            try:
                stored = json.loads(row[0] or '["default"]')
                if isinstance(stored, list):
                    unlocked.update(stored)
            except (TypeError, ValueError):
                pass

        return unlocked

    @commands.hybrid_group(
        name="background",
        description="Manage your profile backgrounds.",
        invoke_without_command=True
    )
    async def background(self, ctx: commands.Context):
        """Show the background command options."""
        embed = discord.Embed(
            title="🖼️ Profile Backgrounds",
            description=(
                "Manage your unlocked profile backgrounds.\n\n"
                "**Equip a background:** `/background equip`\n"
                "**Browse your collection:** `/background collection`"
            ),
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed)

    @background.command(
        name="equip",
        description="Equip an unlocked background for your profile card."
    )
    @app_commands.describe(
        background="Choose an unlocked background for your profile card."
    )
    @app_commands.autocomplete(background=background_autocomplete)
    async def background_equip(self, ctx: commands.Context, background: str):
        await ctx.defer()
        user_id = ctx.author.id
        background = background.lower().strip()

        valid_backgrounds = {
            "default": "Default Nebula",
            "neon_grid": "Cyberpunk Neon Grid City",
            "deep_void": "Deep Void",
            "solaris_ring": "Solaris Ring",
            "halloween_haunted": "Haunted Halloween",
            "halloween_candy_collector": "Candy Collector",
            "halloween_haunting_friend": "Haunting Friend",
            "halloween_trick_or_treat": "Trick-or-Treat",
            "background_glowing_gem": "Glowing Gem",
            "background_malo": "MalO",
            "background_the_graveyard": "The Graveyard",
            "background_abandoned_sanctuary": "Abandoned Sanctuary",
            "background_midnight_pizzeria": "Midnight Pizzeria",
            "background_dead_air": "Dead Air",
            "background_fogbound": "Fogbound",
            "background_dead_end": "Dead-End",
            "background_watched_from_the_trees": "Watched From the Trees",
            "background_haunted_item_collector": "Haunted Item Collector",
            "background_corrupted_reality": "CORRUPTED REALITY"
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

    @background.command(
        name="collection",
        description="Browse your owned profile background collection."
    )
    async def background_collection(self, ctx: commands.Context):
        await ctx.defer()

        user_id = ctx.author.id
        unlocked = await self._get_owned_backgrounds(user_id)
        view = BackgroundCollectionView(self, user_id, unlocked)
        embed, file = await view.render()

        if file:
            await ctx.send(embed=embed, file=file, view=view)
        else:
            await ctx.send(embed=embed, view=view)

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