import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands

from database import ECONOMY_DB_NAME
from seasonal_updates.halloween.halloween import get_collectibles as get_halloween_collectibles
from inventory import HALLOWEEN_SPECIAL_USE_ITEMS, ITEM_REGISTRY

# ---------------------------------------------------------------------------
# Halloween Location-Based Collectibles
# ---------------------------------------------------------------------------
# These are permanent discoveries crafted exclusively at the Haunted
# Workshop. The physical inventory item may be sold, but discovery remains
# permanently recorded in the collectibles table.
# ---------------------------------------------------------------------------

LOCATION_BASED_COLLECTIBLES = {
    "bloodied_patient_file": {
        "name": "Bloodied Patient File", "emoji": "🩸",
        "description": "The patient's name has been scrubbed away. The medical notes haven't. Whatever happened here was still being documented long after treatment should have stopped.",
        "location": "Abandoned Asylum",
        "ingredients": {"bloodstained_gauze": 2, "cracked_syringe": 1}, "sell_price": 1100,
    },
    "last_treatment": {
        "name": "The Last Treatment", "emoji": "🧠",
        "description": "A sealed syringe recovered from a room that no longer exists on the asylum's floor plan.",
        "location": "Abandoned Asylum",
        "ingredients": {"bloodstained_gauze": 1, "cracked_syringe": 2}, "sell_price": 1300,
    },
    "gravekeepers_bloom": {
        "name": "Gravekeeper's Bloom", "emoji": "🌹",
        "description": "A flower that should have crumbled decades ago. It remains strangely soft, and faintly warm, when held.",
        "location": "Forgotten Graveyard",
        "ingredients": {"wilted_bloom": 3}, "sell_price": 950,
    },
    "broken_guest": {
        "name": "The Broken Guest", "emoji": "🧸",
        "description": "Three pieces of the same doll, each recovered from a different room. They fit together perfectly. Nobody remembers what the doll looked like before it was broken.",
        "location": "Haunted House",
        "ingredients": {"broken_doll_piece": 3}, "sell_price": 1000,
    },
    "empty_vial": {
        "name": "The Empty Vial", "emoji": "✝️",
        "description": "The vial still bears the markings of a consecrated blessing. Whatever was inside was emptied long before you found it.",
        "location": "Abandoned Church",
        "ingredients": {"cracked_holy_water_vial": 3}, "sell_price": 1000,
    },
    "witchs_heartwood": {
        "name": "Witch's Heartwood", "emoji": "🌲",
        "description": "A piece of ancient wood grown around something that should not have been buried beneath the Witch's Woods. The roots still twitch when exposed to moonlight.",
        "location": "Witch's Woods",
        "ingredients": {"witchroot": 2, "mooncap_mushroom": 1, "glowmoss": 2}, "sell_price": 1400,
    },
    "mascots_spare_parts": {
        "name": "The Mascot's Spare Parts", "emoji": "🍕",
        "description": "A handful of replacement parts from the pizzeria's long-dead mascot. The manufacturer's logo has been scratched away.",
        "location": "Dilapidated Pizzeria",
        "ingredients": {"nuts_bolts": 2, "glue": 2}, "sell_price": 1100,
    },
    "employee_prize_token": {
        "name": "Employee Prize Token", "emoji": "🎟️",
        "description": "A cheap prize token from the arcade machines. It shouldn't be worth anything. Somehow, it feels important.",
        "location": "Dilapidated Pizzeria",
        "ingredients": {"nuts_bolts": 1, "glue": 3}, "sell_price": 1250,
    },
    "unfinished_toy": {
        "name": "The Unfinished Toy", "emoji": "🧸",
        "description": "The toy was never finished. Someone painted its face anyway.",
        "location": "Abandoned Toy Workshop",
        "ingredients": {"stuffing": 2, "bent_toy_parts": 1, "faded_paint": 1}, "sell_price": 1250,
    },
    "painted_smile": {
        "name": "The Painted Smile", "emoji": "🎨",
        "description": "The paint is faded almost completely away. The smile underneath it isn't.",
        "location": "Abandoned Toy Workshop",
        "ingredients": {"bent_toy_parts": 2, "faded_paint": 2, "stuffing": 1}, "sell_price": 1450,
    },
    "dead_air_transmitter": {
        "name": "Dead-Air Transmitter", "emoji": "📻",
        "description": "The transmitter doesn't broadcast anything. It only receives.",
        "location": "Broadcast Station",
        "ingredients": {"burnt_capacitor": 2, "nuts_bolts": 2}, "sell_price": 1350,
    },
    "stationmasters_log": {
        "name": "Stationmaster's Log", "emoji": "📼",
        "description": "A scorched piece of broadcasting equipment with a handwritten frequency scratched into its casing.",
        "location": "Broadcast Station",
        "ingredients": {"burnt_capacitor": 1, "nuts_bolts": 3}, "sell_price": 1500,
    },
    "room_that_wasnt_there": {
        "name": "Room That Wasn't There", "emoji": "🏨",
        "description": "A piece of carpet from a hotel room that doesn't appear on any floor plan. The pattern changes when you stop looking at it.",
        "location": "Endless Hotel",
        "ingredients": {"hotel_carpet_thread": 2, "dusty_cleaning_rag": 1}, "sell_price": 1300,
    },
    "housekeepings_last_rag": {
        "name": "Housekeeping's Last Rag", "emoji": "🧽",
        "description": "The tag reads \"Room Service.\" The hotel's housekeeping department closed thirty years ago.",
        "location": "Endless Hotel",
        "ingredients": {"hotel_carpet_thread": 1, "dusty_cleaning_rag": 2}, "sell_price": 1450,
    },
    "town_that_remained": {
        "name": "The Town That Remained", "emoji": "🏚️",
        "description": "A fragment of a building from Fogbound Town. Nobody can agree on which building it came from.",
        "location": "Fogbound Town",
        "ingredients": {"rusty_pipe": 1, "cracked_brick": 2}, "sell_price": 1150,
    },
    "fogbound_street_marker": {
        "name": "Fogbound Street Marker", "emoji": "🪧",
        "description": "The lettering has almost completely eroded away. What remains is enough to tell you that the street no longer exists.",
        "location": "Fogbound Town",
        "ingredients": {"rusty_pipe": 2, "cracked_brick": 1}, "sell_price": 1300,
    },
    "unstable_sample": {
        "name": "Unstable Sample", "emoji": "🧪",
        "description": "The label is unreadable. The sample continues reacting to light despite being sealed.",
        "location": "Derelict Research Facility",
        "ingredients": {"chemical_sample": 2, "broken_lab_glass": 1}, "sell_price": 1600,
    },
    "researchers_final_kit": {
        "name": "Researcher's Final Kit", "emoji": "🧤",
        "description": "A battered collection of laboratory equipment recovered from a desk that was abandoned mid-experiment.",
        "location": "Derelict Research Facility",
        "ingredients": {"contaminated_gloves": 1, "broken_lab_glass": 1, "nuts_bolts": 2}, "sell_price": 1700,
    },
    "unmarked_door": {
        "name": "The Unmarked Door", "emoji": "🗝️",
        "description": "A key with no number, no label, and no obvious lock to belong to. The carpet fibers stuck to it are still warm.",
        "location": "Yellow Halls",
        "ingredients": {"unmarked_key": 1, "damp_carpet_fiber": 1, "yellow_hall_light_cover": 1}, "sell_price": 1200,
    },
    "room_zero": {
        "name": "Room 0", "emoji": "🏨",
        "description": "The sign points toward a motel that doesn't appear on any map. The key is labeled \"0.\" There is no room 0.",
        "location": "Dead-End Highway",
        "ingredients": {"rusted_road_sign": 1, "contaminated_fuel_can": 1, "motel_key": 1}, "sell_price": 1400,
    },
    "last_departure": {
        "name": "The Last Departure", "emoji": "🎟️",
        "description": "A transit ticket swollen with water. The printed departure time is tomorrow, yesterday, and a date that doesn't exist.",
        "location": "Drowned Station",
        "ingredients": {"waterlogged_transit_ticket": 1, "contaminated_water_sample": 1, "submerged_key": 1}, "sell_price": 1500,
    },
    "black_notebook": {
        "name": "The Black Notebook", "emoji": "📓",
        "description": "The pages describe things that happened at the campground. The final entry describes the person who will eventually read it.",
        "location": "Silent Campground",
        "ingredients": {"distorted_photograph": 1, "strange_notebook_page": 1, "blackened_tree_bark": 1, "unidentified_black_tendril": 1},
        "sell_price": 1800,
    },
    "photograph_that_changed": {
        "name": "The Photograph That Changed", "emoji": "📷",
        "description": "The people in the photograph are impossible to identify. Every time you look at it, there seems to be one more person standing among them.",
        "location": "Silent Campground",
        "ingredients": {"distorted_photograph": 2, "blackened_tree_bark": 1, "unidentified_black_tendril": 1},
        "sell_price": 2000,
    },
}

LOCATION_BASED_COLLECTIBLE_TITLE = "Haunted Item Collector"
LOCATION_BASED_COLLECTIBLE_COMPLETION_REWARD = 50000

LOCATION_BASED_COLLECTIBLE_ENTRIES = [
    (item_id, data["name"], data["emoji"], data["description"])
    for item_id, data in LOCATION_BASED_COLLECTIBLES.items()
]

# Register these as ordinary inventory items. Selling one does not erase
# permanent discovery progress.
for _item_id, _data in LOCATION_BASED_COLLECTIBLES.items():
    ITEM_REGISTRY.setdefault(
        _item_id,
        {
            "name": _data["name"],
            "emoji": _data["emoji"],
            "max_quantity": 10,
            "type": "Location-Based Collectible",
            "desc": _data["description"],
            "sell_price": _data["sell_price"],
        },
    )


def get_all_halloween_collectibles():
    return get_halloween_collectibles() + LOCATION_BASED_COLLECTIBLE_ENTRIES


async def ensure_collectible_tables(db):
    await db.execute("""
        CREATE TABLE IF NOT EXISTS collectibles (
            user_id INTEGER NOT NULL,
            collectible_id TEXT NOT NULL,
            category TEXT NOT NULL,
            discovered_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, collectible_id)
        )
    """)


async def record_collectible(db, bot, user_id, collectible_id, category="Halloween"):
    """Permanently record a seasonal collectible inside an existing transaction."""
    await ensure_collectible_tables(db)
    cursor = await db.execute(
        "INSERT OR IGNORE INTO collectibles (user_id, collectible_id, category) VALUES (?, ?, ?)",
        (user_id, collectible_id, category),
    )
    added = cursor.rowcount > 0

    if added:
        achievements_cog = bot.get_cog("Achievements") if bot else None
        if achievements_cog:
            await achievements_cog.check_user_achievements(user_id, db=db)
    return added


class Collectibles(commands.Cog):
    """Permanent seasonal collection tracker."""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="collectibles",
        description="View your permanent seasonal collectible collection.",
    )
    @app_commands.describe(
        info="View a collectible you have permanently discovered.",
    )
    async def collectibles(
        self,
        ctx: commands.Context,
        info: str | None = None,
    ):
        """View the permanent collection or inspect a discovered collectible."""

        # /collectibles info:<collectible>
        if info is not None:
            user_id = ctx.author.id

            collectible = info

            async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
                await ensure_collectible_tables(db)
                async with db.execute(
                    """
                    SELECT collectible_id
                    FROM collectibles
                    WHERE user_id = ?
                    """,
                    (user_id,),
                ) as cursor:
                    discovered = {row[0] for row in await cursor.fetchall()}

            entries = get_all_halloween_collectibles()
            collectible_map = {
                item_id: (name, emoji, desc)
                for item_id, name, emoji, desc in entries
            }

            if collectible not in discovered:
                return await ctx.send(
                    "❌ **You haven't discovered that collectible yet.**\n"
                    "Only collectibles you've found can be viewed here.",
                    ephemeral=True,
                )

            data = collectible_map.get(collectible)
            if not data:
                return await ctx.send(
                    "❌ **That collectible is no longer available in the current collection.**",
                    ephemeral=True,
                )

            name, emoji, description = data

            # Some seasonal collectible text is stored with literal ``\\n``
            # sequences. Normalize those into real Discord line breaks so
            # they never appear as ``\n`` in the displayed embed.
            description = description.replace("\\n", "\n")

            embed = discord.Embed(
                title=f"{emoji} {name}",
                description=description,
                color=discord.Color.dark_purple(),
            )
            embed.set_author(
                name=f"{ctx.author.display_name}'s Collectible",
                icon_url=ctx.author.display_avatar.url,
            )

            # Halloween special collectibles can have a permanent one-time
            # use state. Viewing this information is completely read-only.
            use_config = HALLOWEEN_SPECIAL_USE_ITEMS.get(collectible)
            if isinstance(use_config, dict) and use_config.get("enabled"):
                # /use creates this table when a usable collectible is first
                # used. Create it here too so info works before first use.
                async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
                    await db.execute("""
                        CREATE TABLE IF NOT EXISTS used_collectibles (
                            user_id INTEGER NOT NULL,
                            collectible_id TEXT NOT NULL,
                            used_at TEXT DEFAULT CURRENT_TIMESTAMP,
                            PRIMARY KEY (user_id, collectible_id)
                        )
                    """)
                    async with db.execute(
                        """
                        SELECT 1
                        FROM used_collectibles
                        WHERE user_id = ? AND collectible_id = ?
                        """,
                        (user_id, collectible),
                    ) as cursor:
                        already_used = await cursor.fetchone() is not None

                use_message = use_config.get("use_message", "???")
                if isinstance(use_message, str):
                    use_message = use_message.replace("\\n", "\n")

                embed.add_field(
                    name="🖐️ When Used",
                    value=use_message if already_used else "???",
                    inline=False,
                )

                # Do not reveal the repeat-use message until the collectible
                # has actually been used.
                if already_used:
                    embed.add_field(
                        name="🔁 Already Used",
                        value=(
                            use_config.get(
                                "already_used_message",
                                "🚫 This item has already been used.",
                            ).replace("\\n", "\n")
                        ),
                        inline=False,
                    )

            embed.set_footer(text="This discovery is permanent.")

            return await ctx.send(embed=embed)

        # /collectibles
        await ctx.defer()
        user_id = ctx.author.id

        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await ensure_collectible_tables(db)
            async with db.execute(
                "SELECT collectible_id FROM collectibles WHERE user_id = ?",
                (user_id,),
            ) as cursor:
                owned = {row[0] for row in await cursor.fetchall()}

        categories = {
            "🎃 Halloween - Lair of Frights Items": get_halloween_collectibles(),
            "🔧 Halloween - Location-Based Collectibles": LOCATION_BASED_COLLECTIBLE_ENTRIES,
        }

        pages = []
        page_size = 15

        for category, entries in categories.items():
            if not entries:
                continue

            found = sum(1 for item_id, *_ in entries if item_id in owned)
            total = len(entries)
            total_pages = (total + page_size - 1) // page_size

            for start in range(0, total, page_size):
                chunk_entries = entries[start:start + page_size]
                page_number = start // page_size + 1
                lines = []

                for item_id, name, emoji, _desc in chunk_entries:
                    if item_id in owned:
                        lines.append(f"{emoji} **{name}**")
                    else:
                        lines.append("❓ **???**")

                embed = discord.Embed(
                    title=f"📚 {ctx.author.display_name}'s Collectibles",
                    description=(
                        f"**{category}** • Part **{page_number}/{total_pages}**\n"
                        f"Collected: **{found}/{total}** ({found / total * 100:.0f}%)\n\n"
                        + "\n\n".join(lines)
                        + "\n\nUndiscovered collectibles remain hidden until you find them."
                    ),
                    color=discord.Color.dark_purple(),
                )
                pages.append(embed)

        if not pages:
            return await ctx.send("📚 **There are no seasonal collectibles available yet!**")

        class CollectiblesView(discord.ui.View):
            def __init__(self, owner_id, embeds):
                super().__init__(timeout=300)
                self.owner_id = owner_id
                self.embeds = embeds
                self.current_page = 0

            def current_embed(self):
                embed = self.embeds[self.current_page]
                embed.set_footer(
                    text=f"Page {self.current_page + 1}/{len(self.embeds)} • Seasonal discoveries are permanent."
                )
                return embed

            async def interaction_check(self, interaction: discord.Interaction):
                if interaction.user.id != self.owner_id:
                    await interaction.response.send_message(
                        "❌ This collectibles menu belongs to someone else.", ephemeral=True
                    )
                    return False
                return True

            @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
            async def previous(self, interaction, button):
                self.current_page = (self.current_page - 1) % len(self.embeds)
                await interaction.response.edit_message(embed=self.current_embed(), view=self)

            @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
            async def next(self, interaction, button):
                self.current_page = (self.current_page + 1) % len(self.embeds)
                await interaction.response.edit_message(embed=self.current_embed(), view=self)

        view = CollectiblesView(user_id, pages)
        await ctx.send(embed=view.current_embed(), view=view)

    @collectibles.autocomplete("info")
    async def collectibles_info_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ):
        """Offer only collectibles this member has permanently discovered."""
        user_id = interaction.user.id

        try:
            async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
                await ensure_collectible_tables(db)
                async with db.execute(
                    """
                    SELECT collectible_id
                    FROM collectibles
                    WHERE user_id = ?
                    """,
                    (user_id,),
                ) as cursor:
                    discovered = {row[0] for row in await cursor.fetchall()}
        except Exception:
            return []

        current = (current or "").lower().strip()
        choices = []

        for item_id, name, emoji, _description in get_all_halloween_collectibles():
            if item_id not in discovered:
                continue

            search_text = f"{name} {item_id}".lower()
            if current and current not in search_text:
                continue

            choices.append(
                app_commands.Choice(
                    name=f"{emoji} {name}"[:100],
                    value=item_id,
                )
            )

            if len(choices) >= 25:
                break

        return choices


async def setup(bot):
    await bot.add_cog(Collectibles(bot))
