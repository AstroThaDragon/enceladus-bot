import re
import aiosqlite
from typing import Any, Optional, cast

import discord
from discord import app_commands

from inventory import ITEM_REGISTRY
from pets import get_active_pet_effects

from ..data import *

class ShopInteractionContext:
    """Small adapter that lets the existing buy/sell methods reply to an interaction."""

    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.author = interaction.user

    async def defer(self):
        if not self.interaction.response.is_done():
            await self.interaction.response.defer()

    async def send(self, *args, **kwargs):
        return await self.interaction.followup.send(*args, wait=True, **kwargs)

class ShopCategorySelect(discord.ui.Select):
    def __init__(self, shop_view):
        self.shop_view = shop_view
        if shop_view.mode == "buy":
            categories = SHOP_BUY_CATEGORY_CHOICES
        else:
            categories = SHOP_SELL_CATEGORY_CHOICES

        options = []
        for name, value in categories:
            emoji, label, description = SHOP_CATEGORY_INFO.get(
                value, (None, name, "Shop category")
            )
            options.append(
                discord.SelectOption(
                    label=label,
                    emoji=emoji,
                    value=value,
                    description=description[:100],
                )
            )

        super().__init__(
            placeholder="📂 Choose a category...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        if not await self.shop_view.check_owner(interaction):
            return
        self.shop_view.category = self.values[0]
        self.shop_view.page = 0
        self.shop_view.search_query = ""
        self.shop_view.selected_item = None
        self.shop_view.quantity = 1
        await self.shop_view.show_item_picker(interaction)

class ShopItemButton(discord.ui.Button):
    """Select one of the items currently showcased on the embed."""

    def __init__(self, shop_view, entry, row=0):
        self.shop_view = shop_view
        self.item_id = entry["id"]
        label = shop_view._strip_emoji_name(entry.get("name", self.item_id))
        # Keep the button readable on mobile while the full item name remains
        # visible in the embed above it.
        super().__init__(
            label=label[:80],
            style=discord.ButtonStyle.secondary,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction):
        if not await self.shop_view.check_owner(interaction):
            return

        self.shop_view.selected_item = self.item_id
        self.shop_view.quantity = 1
        self.shop_view.quantity_input = "1"

        if self.shop_view.mode == "sell" and self.item_id in BULK_SELL_OPTIONS:
            return await self.shop_view.show_bulk_sale(interaction)

        if self.shop_view.mode == "buy" and self.item_id == "lottery_ticket":
            return await interaction.response.send_modal(ShopLotteryModal(self.shop_view))

        await self.shop_view.show_quantity(interaction)

class ShopSearchModal(discord.ui.Modal, title="🔎 Search Shop Items"):
    search = discord.ui.TextInput(
        label="Search",
        placeholder="Type an item name or keyword...",
        required=False,
        max_length=100,
    )

    def __init__(self, shop_view):
        super().__init__()
        self.shop_view = shop_view

    async def on_submit(self, interaction: discord.Interaction):
        if not await self.shop_view.check_owner(interaction):
            return
        self.shop_view.search_query = str(self.search.value or "").strip().lower()
        self.shop_view.page = 0
        if self.shop_view.category is None:
            self.shop_view.category = "__search__"
        await self.shop_view.show_item_picker(interaction)

class ShopLotteryModal(discord.ui.Modal, title="🎟️ Lottery Ticket"):
    number1 = discord.ui.TextInput(label="Number 1", placeholder="1–99", required=True, max_length=2)
    number2 = discord.ui.TextInput(label="Number 2", placeholder="1–99", required=True, max_length=2)
    number3 = discord.ui.TextInput(label="Number 3", placeholder="1–99", required=True, max_length=2)
    number4 = discord.ui.TextInput(label="Number 4", placeholder="1–99", required=True, max_length=2)
    number5 = discord.ui.TextInput(label="Number 5", placeholder="1–99", required=True, max_length=2)

    def __init__(self, shop_view):
        super().__init__()
        self.shop_view = shop_view

    async def on_submit(self, interaction: discord.Interaction):
        if not await self.shop_view.check_owner(interaction):
            return

        lottery = self.shop_view.cog.bot.get_cog("Lottery")
        if lottery is None:
            return await interaction.response.send_message(
                "❌ The lottery system is currently unavailable.",
                ephemeral=True,
            )

        try:
            raw_numbers = (
                int(str(self.number1.value).strip()),
                int(str(self.number2.value).strip()),
                int(str(self.number3.value).strip()),
                int(str(self.number4.value).strip()),
                int(str(self.number5.value).strip()),
            )
        except ValueError:
            return await interaction.response.send_message(
                "❌ All five lottery numbers must be whole numbers from **1 to 99**.",
                ephemeral=True,
            )

        numbers = lottery.normalize_numbers(raw_numbers)
        if numbers is None:
            return await interaction.response.send_message(
                "❌ Your ticket must contain **5 different whole numbers from 1 to 99**.",
                ephemeral=True,
            )

        success, message = await lottery.purchase_ticket(interaction.user.id, numbers)
        await interaction.response.send_message(message, ephemeral=True)

class ShopQuantityModal(discord.ui.Modal, title="🔢 Custom Quantity"):
    quantity = discord.ui.TextInput(
        label="Quantity",
        placeholder="Enter a number...",
        required=True,
        min_length=1,
        max_length=4,
    )

    def __init__(self, shop_view):
        super().__init__()
        self.shop_view = shop_view

    async def on_submit(self, interaction: discord.Interaction):
        if not await self.shop_view.check_owner(interaction):
            return

        raw = str(self.quantity.value).strip()
        try:
            value = int(raw)
        except ValueError:
            return await interaction.response.send_message(
                "❌ Quantity must be a whole number.",
                ephemeral=True,
            )

        if value < 1 or value > 99:
            return await interaction.response.send_message(
                "❌ Quantity must be between **1 and 99**.",
                ephemeral=True,
            )

        if self.shop_view.mode == "sell":
            owned = self.shop_view.get_selected_owned_quantity()
            if owned is not None and value > owned:
                return await interaction.response.send_message(
                    f"❌ You only own **{owned:,}** of that item.",
                    ephemeral=True,
                )

        self.shop_view.quantity = value
        self.shop_view.quantity_input = str(value)
        await self.shop_view.show_quantity(interaction)

class ShopQuantityButton(discord.ui.Button):
    def __init__(self, shop_view, label, value, emoji=None, style=discord.ButtonStyle.secondary):
        super().__init__(label=label, emoji=emoji, style=style, row=0)
        self.shop_view = shop_view
        self.value = value

    async def callback(self, interaction: discord.Interaction):
        if not await self.shop_view.check_owner(interaction):
            return

        if self.value == "custom":
            return await interaction.response.send_modal(ShopQuantityModal(self.shop_view))

        if self.value == "max":
            owned = self.shop_view.get_selected_owned_quantity()
            if not owned:
                return await interaction.response.send_message(
                    "❌ You don't own any of that item.", ephemeral=True
                )
            self.shop_view.quantity = owned
            self.shop_view.quantity_input = "max"
        else:
            value = int(self.value)
            if self.shop_view.mode == "sell":
                owned = self.shop_view.get_selected_owned_quantity()
                if owned is not None and value > owned:
                    return await interaction.response.send_message(
                        f"❌ You only own **{owned:,}** of that item.", ephemeral=True
                    )
            self.shop_view.quantity = value
            self.shop_view.quantity_input = str(value)

        await self.shop_view.show_quantity(interaction)

class ShopTransactionView(discord.ui.View):
    """Reusable Category → Item → Quantity → Confirm shop flow."""

    # Five items fit cleanly across one Discord button row. The embed above
    # them contains the full item details, while the buttons simply select the
    # item being acted on.
    PAGE_SIZE = 5

    def __init__(self, cog, user_id, mode):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        self.mode = mode
        self.category: Optional[str] = None
        self.page = 0
        self.search_query = ""
        self.selected_item: Optional[str] = None
        self.quantity = 1
        self.quantity_input = "1"
        self.item_entries = []
        self.finished = False
        self.processing = False
        self.message = None
        self._build_category_view()

    async def check_owner(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "⚠️ This shop menu belongs to the person who opened it.",
                ephemeral=True,
            )
            return False
        if self.finished:
            await interaction.response.send_message(
                "⚠️ This shop has been closed.", ephemeral=True
            )
            return False
        if self.processing:
            await interaction.response.send_message(
                "⏳ Your transaction is still processing.", ephemeral=True
            )
            return False
        return True

    def _add_cancel_button(self, *, row=2):
        cancel = discord.ui.Button(
            label="Cancel",
            emoji="✖️",
            style=discord.ButtonStyle.danger,
            row=row,
        )

        async def cancel_callback(interaction: discord.Interaction):
            if not await self.check_owner(interaction):
                return
            self.finished = True
            self.stop()
            await interaction.response.edit_message(
                content="🛒 **Shop closed.**",
                embed=None,
                view=None,
            )

        cancel.callback = cast(Any, cancel_callback)
        self.add_item(cancel)

    def make_return_view(self):
        """Create a fresh view after a separate bulk-sale confirmation view."""
        view = ShopTransactionView(self.cog, self.user_id, self.mode)
        view.category = self.category
        view.page = self.page
        view.search_query = self.search_query
        view.message = self.message
        return view

    def _build_category_view(self):
        self.clear_items()
        self.add_item(ShopCategorySelect(self))

        search = discord.ui.Button(
            label="Search",
            emoji="🔎",
            style=discord.ButtonStyle.primary,
            row=1,
        )

        async def search_callback(interaction: discord.Interaction):
            if not await self.check_owner(interaction):
                return
            await interaction.response.send_modal(ShopSearchModal(self))

        search.callback = cast(Any, search_callback)
        self.add_item(search)
        self._add_cancel_button(row=2)

    def _category_title(self):
        emoji, label, _ = SHOP_CATEGORY_INFO.get(
            self.category or "", ("📂", "Shop", "")
        )
        return f"{emoji} {label}"

    def _get_buy_items(self):
        if self.category == "__rotating__":
            return list(self.cog.daily_rotation())
        if self.category == "__search__":
            item_ids = []
            for category, category_items in SHOP_BUY_CATEGORY_ITEMS.items():
                if category == "daily":
                    continue
                item_ids.extend(category_items)
            return list(dict.fromkeys(item_ids))
        if self.category is None:
            return []
        return list(SHOP_BUY_CATEGORY_ITEMS.get(self.category, []))

    async def _get_sell_items(self):
        if self.category == "__search__":
            entries = []
            for category in SHOP_SELL_CATEGORY_CHOICES:
                entries.extend(await self.cog.get_shop_sell_items(self.user_id, category[1]))
            seen = set()
            unique = []
            for entry in entries:
                if entry["id"] in seen:
                    continue
                seen.add(entry["id"])
                unique.append(entry)
            return unique
        if self.category is None:
            return []
        return await self.cog.get_shop_sell_items(self.user_id, self.category)

    def _filter_entries(self, entries):
        query = self.search_query
        if not query:
            return entries
        return [
            entry for entry in entries
            if query in str(entry["search"]).lower()
        ]

    async def _get_entries(self):
        if self.mode == "buy":
            entries = []
            for item_id in self._get_buy_items():
                if item_id == "lottery_ticket":
                    lottery = self.cog.bot.get_cog("Lottery")
                    ticket_cost = int(getattr(lottery, "TICKET_COST", 100)) if lottery else 100
                    info = {
                        "name": "Lottery Ticket",
                        "cost": ticket_cost,
                        "type": "lottery",
                        "desc": (
                            "Choose 5 different numbers from 1–99. "
                            "Use the ticket button to enter your numbers. "
                            "Maximum 25 active tickets per cycle."
                        ),
                    }
                else:
                    info = self.cog.SHOP_ITEMS.get(item_id) or self.cog.ROTATING_ITEMS.get(item_id)
                if not info:
                    continue
                entries.append({
                    "id": item_id,
                    "name": info.get("name", item_id),
                    "description": info.get("desc", ""),
                    "search": f"{item_id} {info.get('name', '')}",
                    "info": info,
                    "owned": None,
                })
        else:
            entries = await self._get_sell_items()
        return self._filter_entries(entries)

    def _entry_for_item(self, item_id):
        for entry in self.item_entries:
            if entry["id"] == item_id:
                return entry
        return None

    def get_selected_owned_quantity(self):
        entry = self._entry_for_item(self.selected_item)
        return entry.get("owned") if entry else None

    async def _get_buy_owned_quantity(self):
        """Read the current stack count for the selected shop item."""
        if not self.selected_item:
            return None
        selected_info = self._get_selected_info() or {}
        if selected_info.get("type") == "station_upgrade":
            return None

        legacy_columns = {
            "time_crystal": "time_crystals",
            "nanite_patch": "nanite_patchs",
            "medkit": "medkits",
        }
        async with aiosqlite.connect(self.cog.get_db_path()) as db:
            await self.cog.ensure_schema(db)
            if self.selected_item in legacy_columns:
                column = legacy_columns[self.selected_item]
                async with db.execute("PRAGMA table_info(users)") as cursor:
                    columns = {row[1] for row in await cursor.fetchall()}
                if column not in columns:
                    return 0
                async with db.execute(
                    f"SELECT COALESCE({column}, 0) FROM users WHERE user_id = ?",
                    (self.user_id,),
                ) as cursor:
                    row = await cursor.fetchone()
                return int(row[0] or 0) if row else 0

            await db.execute(
                """CREATE TABLE IF NOT EXISTS inventory (
                    user_id INTEGER NOT NULL,
                    item_id TEXT NOT NULL,
                    item_type TEXT NOT NULL DEFAULT 'crafting_material',
                    quantity INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (user_id, item_id)
                )"""
            )
            async with db.execute(
                "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                (self.user_id, self.selected_item),
            ) as cursor:
                row = await cursor.fetchone()
            return int(row[0] or 0) if row else 0

    @staticmethod
    def _strip_emoji_name(name):
        # Discord custom emoji markup is not reliably rendered in button labels.
        # Keep normal Unicode emoji, but strip <:name:id> / <a:name:id> markup.
        cleaned = re.sub(r"<a?:[A-Za-z0-9_~]+:\d+>\s*", "", str(name or ""))
        return cleaned.strip() or "Item"

    def _build_category_embed(self):
        title = "🛒 Buy Items" if self.mode == "buy" else "🛒 Sell Items"

        if self.mode == "buy":
            categories = SHOP_BUY_CATEGORY_CHOICES
            footer = "Choose a category to browse the station shop."
        else:
            categories = SHOP_SELL_CATEGORY_CHOICES
            footer = "Choose a category to browse your sellable inventory."

        category_lines = []
        for name, value in categories:
            emoji, label, description = SHOP_CATEGORY_INFO.get(
                value, ("📂", name, "Shop category")
            )
            category_lines.append(f"{emoji} **{label}** — {description}")

        description = (
            "Choose a category to continue.\n\n"
            "**Available Categories**\n"
            + "\n".join(category_lines)
        )

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.from_rgb(0, 229, 255),
        )
        embed.set_footer(text=footer)
        return embed

    async def show_category(self, interaction):
        self.category = None
        self.page = 0
        self.search_query = ""
        self.selected_item = None
        self.quantity = 1
        self.quantity_input = "1"
        self._build_category_view()

        # A category return can happen after other async shop work. Defer the
        # component interaction immediately so Discord does not time out while
        # the response is being edited.
        if not interaction.response.is_done():
            await interaction.response.defer()

        await interaction.edit_original_response(
            embed=self._build_category_embed(),
            view=self,
        )

    async def show_item_picker(self, interaction, *, edit_original=False):
        self.clear_items()
        entries = await self._get_entries()
        self.item_entries = entries

        total_pages = max(1, (len(entries) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.page = min(max(self.page, 0), total_pages - 1)
        start = self.page * self.PAGE_SIZE
        page_entries = entries[start:start + self.PAGE_SIZE]

        title = "🛒 Buy Items" if self.mode == "buy" else "🛒 Sell Items"
        page_text = f"Page {self.page + 1}/{total_pages}"
        if self.search_query:
            page_text += f" • Search: `{self.search_query}`"

        description = (
            f"Choose an item to {'buy' if self.mode == 'buy' else 'sell'}.\n\n"
            f"**{page_text}**\n"
            f"{len(entries):,} item{'s' if len(entries) != 1 else ''} available."
        )

        embed = discord.Embed(
            title=f"{title} — {self._category_title()}",
            description=description,
            color=discord.Color.from_rgb(0, 229, 255),
        )

        if page_entries:
            for entry in page_entries:
                info = entry.get("info") or {}
                item_name = str(entry.get("name", entry.get("id", "Item")))

                if self.mode == "buy":
                    price = int(info.get("cost", 0) or 0)
                    if entry["id"] in self.cog.SHOP_ITEMS and entry["id"] in self.cog.daily_rotation():
                        daily_price = int(price * 0.85)
                        detail = (
                            f"💰 ~~{price:,}~~ → **{daily_price:,} Stardust**\n"
                            "🏷️ **15% Daily Discount**"
                        )
                    else:
                        detail = f"💰 **{price:,} Stardust**"
                    if info.get("desc"):
                        detail += f"\n📖 {info['desc']}"
                    limit_text = self.cog.shop_limit_text(entry["id"])
                    limit = limit_text.removeprefix(" • Limit: ") if limit_text else "None"
                    detail += f"\n📦 **Purchase limit:** {limit}"
                else:
                    owned = int(entry.get("owned", 0) or 0)
                    stored_type = entry.get("stored_type") or info.get("type")
                    if str(stored_type).lower() == "space_junk" or info.get("type") == "Space Junk":
                        payout, candy = self.cog.get_junk_sell_reward(entry["id"])
                        price_line = f"💰 **{int(payout):,} Stardust each**"
                        if candy:
                            price_line += f" + 🍬 **{int(candy)} Candy**"
                    else:
                        payout = int(info.get("sell_price", 0) or 0)
                        price_line = f"💰 **{payout:,} Stardust each**"
                    detail = f"📦 You own: **{owned:,}**\n{price_line}"

                embed.add_field(
                    name=item_name,
                    value=detail,
                    inline=False,
                )

            # The buttons correspond exactly to the items displayed above.
            # Full names/details stay in the embed so long names never need to
            # be crammed into a select-menu popup.
            for entry in page_entries:
                self.add_item(ShopItemButton(self, entry, row=0))
        else:
            embed.description = (embed.description or "") + "\n\n❌ No items match that search."

        previous = discord.ui.Button(
            label="Previous",
            emoji="◀️",
            style=discord.ButtonStyle.secondary,
            disabled=self.page <= 0,
            row=1,
        )
        next_button = discord.ui.Button(
            label="Next",
            emoji="▶️",
            style=discord.ButtonStyle.secondary,
            disabled=self.page >= total_pages - 1,
            row=1,
        )
        search = discord.ui.Button(
            label="Search",
            emoji="🔎",
            style=discord.ButtonStyle.primary,
            row=2,
        )
        categories = discord.ui.Button(
            label="Categories",
            emoji="↩️",
            style=discord.ButtonStyle.secondary,
            row=2,
        )

        async def previous_callback(i: discord.Interaction):
            if not await self.check_owner(i):
                return
            self.page -= 1
            await self.show_item_picker(i)

        async def next_callback(i: discord.Interaction):
            if not await self.check_owner(i):
                return
            self.page += 1
            await self.show_item_picker(i)

        async def search_callback(i: discord.Interaction):
            if not await self.check_owner(i):
                return
            await i.response.send_modal(ShopSearchModal(self))

        async def categories_callback(i: discord.Interaction):
            if not await self.check_owner(i):
                return
            await self.show_category(i)

        previous.callback = cast(Any, previous_callback)
        next_button.callback = cast(Any, next_callback)
        search.callback = cast(Any, search_callback)
        categories.callback = cast(Any, categories_callback)
        self.add_item(previous)
        self.add_item(next_button)
        self.add_item(search)
        if self.category != "__rotating__":
            self.add_item(categories)
        self._add_cancel_button(row=2)

        embed.set_footer(
            text="Items are shown above • Use the item buttons to select one, or Search to filter."
        )

        if edit_original:
            self.message = await interaction.edit_original_response(
                content=None, embed=embed, view=self
            )
        else:
            await interaction.response.edit_message(content=None, embed=embed, view=self)

    def _get_selected_info(self):
        if self.selected_item is None:
            return None
        entry = self._entry_for_item(self.selected_item)
        if entry:
            return entry["info"]
        return self.cog.SHOP_ITEMS.get(self.selected_item) or self.cog.ROTATING_ITEMS.get(self.selected_item) or ITEM_REGISTRY.get(self.selected_item)

    def _buy_unit_price(self):
        info = self._get_selected_info() or {}
        price = int(info.get("cost", 0) or 0)
        if self.selected_item in self.cog.SHOP_ITEMS and self.selected_item in self.cog.daily_rotation():
            price = int(price * 0.85)
        return price

    def _sell_unit_price(self):
        info = self._get_selected_info() or {}
        entry = self._entry_for_item(self.selected_item)
        stored_type = entry.get("stored_type") if entry else info.get("type")
        if str(stored_type).lower() == "space_junk" or info.get("type") == "Space Junk":
            payout, _ = self.cog.get_junk_sell_reward(self.selected_item)
            return int(payout)
        return int(info.get("sell_price", 0) or 0)

    async def show_quantity(self, interaction):
        self.clear_items()
        info = self._get_selected_info() or {}
        entry = self._entry_for_item(self.selected_item) or {}
        name = info.get("name", self.selected_item)

        if self.mode == "buy":
            unit_price = self._buy_unit_price()
            total = unit_price * self.quantity
            owned = await self._get_buy_owned_quantity()
            lines = [
                f"📦 You currently have: **{owned:,}x**" if owned is not None else "",
                f"💰 Price: **{unit_price:,} Stardust each**",
                f"🧮 Quantity: **{self.quantity:,}**",
                f"💸 Total: **{total:,} Stardust**",
            ]
            lines = [line for line in lines if line]
            if self.selected_item in self.cog.SHOP_ITEMS and self.selected_item in self.cog.daily_rotation():
                lines.insert(1, "🏷️ **15% Daily Discount**")

            # The Void Merchant's free-purchase effect is rolled when the
            # transaction is confirmed, so this screen cannot know whether
            # this specific purchase will proc. Make that possibility explicit
            # whenever the active pet has the effect available.
            try:
                db_path = self.cog.get_db_path()
                async with aiosqlite.connect(db_path) as db:
                    pet_effects = await get_active_pet_effects(db, self.user_id)
                if float(pet_effects.get("shop_free_purchase", 0.0)) > 0:
                    lines.append(
                        "🕳️ **Void Merchant:** This purchase has a chance to be **FREE**."
                    )
            except Exception:
                # The confirmation UI should never fail because the optional
                # Void Merchant preview could not be loaded.
                pass
        else:
            unit_price = self._sell_unit_price()
            owned = entry.get("owned", 0)
            total = unit_price * self.quantity
            lines = [
                f"📦 You own: **{owned:,}**",
                f"💰 Sell price: **{unit_price:,} Stardust each**",
                f"🧮 Quantity: **{self.quantity:,}**",
                f"💸 Total: **{total:,} Stardust**",
            ]

        embed = discord.Embed(
            title=f"{name}",
            description="\n".join(lines) + "\n\nChoose a quantity, then confirm the transaction.",
            color=discord.Color.from_rgb(0, 229, 255),
        )
        embed.set_footer(text="Custom lets you enter a quantity up to 99.")

        if self.mode == "buy":
            # Keep the quick-purchase buttons aligned with the shop's common
            # purchase limits. Custom still allows any quantity permitted by
            # the existing purchase-limit validation.
            presets: list[tuple[str, str, Optional[str]]] = [
                ("1", "1", "1️⃣"),
                ("5", "5", "5️⃣"),
            ]
        else:
            # Selling keeps the existing 1 / Max shortcuts.
            presets = [
                ("1", "1", "1️⃣"),
                ("Max", "max", "📦"),
            ]
        for label, value, emoji in presets:
            self.add_item(ShopQuantityButton(self, label, value, emoji=emoji))
        self.add_item(ShopQuantityButton(self, "Custom", "custom", emoji="🔢"))

        back = discord.ui.Button(label="Back", emoji="◀️", style=discord.ButtonStyle.secondary, row=1)
        confirm = discord.ui.Button(label="Confirm", emoji="✅", style=discord.ButtonStyle.success, row=1)

        async def back_callback(i: discord.Interaction):
            if not await self.check_owner(i):
                return
            await self.show_item_picker(i)

        async def confirm_callback(i: discord.Interaction):
            if not await self.check_owner(i):
                return
            await self.confirm_transaction(i)

        back.callback = cast(Any, back_callback)
        confirm.callback = cast(Any, confirm_callback)
        self.add_item(back)
        self.add_item(confirm)
        self._add_cancel_button(row=2)
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_bulk_sale(self, interaction):
        rows, total_stardust, total_candy, item_count, lines = await self.cog._bulk_sale_preview(
            self.user_id, self.selected_item
        )
        if not rows:
            return await interaction.response.send_message(
                "❌ You don't currently have any items covered by this Sell All option.",
                ephemeral=True,
            )

        preview = "\n".join(lines[:12])
        if len(lines) > 12:
            preview += f"\n…and {len(lines) - 12} more."
        candy_preview = f"\n🍬 **Halloween Candy:** +{total_candy}" if total_candy else ""
        embed = discord.Embed(
            title="⚠️ Confirm Bulk Sale",
            description=(
                f"You are about to sell **{item_count} items** for approximately "
                f"✨ **{total_stardust:,} Stardust**.{candy_preview}\n\n"
                f"**Items included:**\n{preview}\n\n"
                "📚 **Collection Note:** Collectibles are permanently recorded in your collection once discovered. "
                "Selling the physical items does **not** remove them from your collection.\n\n"
                "This cannot be undone. Choose **Yes, Sell All** or **Cancel**."
            ),
            color=discord.Color.orange(),
        )
        self.stop()
        view = SellAllConfirmView(
            self.cog, self.user_id, self.selected_item, return_view=self
        )
        view.message = self.message
        await interaction.response.edit_message(embed=embed, content=None, view=view)

    async def confirm_transaction(self, interaction):
        if self.finished:
            return await interaction.response.send_message(
                "⚠️ This transaction has already been submitted.", ephemeral=True
            )
        if not self.selected_item:
            return await interaction.response.send_message("❌ No item selected.", ephemeral=True)

        self.processing = True
        await interaction.response.defer()

        # The existing transaction methods contain the full purchase/sale
        # accounting logic. The adapter lets them respond to this interaction
        # without duplicating that logic in the UI.
        ctx = ShopInteractionContext(interaction)
        try:
            if self.mode == "buy":
                await self.cog.buy(ctx, self.selected_item, self.quantity)
            else:
                await self.cog.sell(ctx, self.selected_item, self.quantity_input)
        finally:
            self.processing = False
            self.selected_item = None
            self.quantity = 1
            self.quantity_input = "1"
            await self.show_item_picker(interaction, edit_original=True)

    async def on_timeout(self):
        self.finished = True
        for child in self.children:
            if isinstance(child, (discord.ui.Button, discord.ui.Select)):
                child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except (discord.NotFound, discord.HTTPException):
                pass

class RotatingShopBuyButton(discord.ui.Button):
    """Buy button for one of today's rotating offers."""

    def __init__(self, cog, user_id, item_id, item, row=1):
        self.cog = cog
        self.user_id = user_id
        self.item_id = item_id
        self.item = item

        # Button labels cannot safely contain Discord custom-emoji markup.
        # Reuse the shop's normal name cleaner so custom emojis are removed
        # while ordinary Unicode emoji remain valid.
        label = ShopTransactionView._strip_emoji_name(
            item.get("name", item_id)
        )
        label = f"Buy {label}"

        super().__init__(
            label=label[:80],
            style=discord.ButtonStyle.success,
            row=row,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "⚠️ This rotating shop belongs to the person who opened it.",
                ephemeral=True,
            )

        # Reuse the normal transaction flow so rotating purchases get the same
        # quantity selection, purchase-limit checks, balance checks, and
        # confirmation behavior as /shop buy.
        view = ShopTransactionView(self.cog, self.user_id, "buy")
        view.category = "__rotating__"
        view.selected_item = self.item_id
        view.quantity = 1
        view.quantity_input = "1"
        view.item_entries = [{
            "id": self.item_id,
            "name": self.item.get("name", self.item_id),
            "description": self.item.get("desc", ""),
            "search": f"{self.item_id} {self.item.get('name', '')}",
            "info": self.item,
            "owned": None,
        }]
        view.message = interaction.message
        await view.show_quantity(interaction)

class ShopView(discord.ui.View):
    """Interactive daily rotating offers view."""

    def __init__(self, cog, user_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id

        self._add_daily_buttons()

    def _add_daily_buttons(self):
        for item_id in self.cog.daily_rotation():
            item = self.cog.SHOP_ITEMS.get(item_id) or self.cog.ROTATING_ITEMS.get(item_id)
            if not item:
                continue
            self.add_item(
                RotatingShopBuyButton(
                    self.cog,
                    self.user_id,
                    item_id,
                    item,
                    row=1,
                )
            )

    def build_embed(self):
        cog = self.cog
        embed = discord.Embed(
            title="🛒 Enceladus Station Trading Post",
            color=discord.Color.from_rgb(0, 229, 255)
        )
        embed.description = (
            "🔄 **Daily Rotating Offers**\n"
            f"Today's station market — **{cog.rotation_date()}**\n\n"
            "These offers rotate at midnight Eastern time."
        )
        for item_id in cog.daily_rotation():
            item = cog.SHOP_ITEMS.get(item_id) or cog.ROTATING_ITEMS.get(item_id)
            if not item:
                continue
            is_permanent = item_id in cog.SHOP_ITEMS
            daily_cost = int(item["cost"] * 0.85) if is_permanent else item["cost"]
            price_text = (
                f"💰 ~~{item['cost']:,}~~ → **{daily_cost:,} Stardust** 🔥\n🏷️ **15% Daily Discount**"
                if is_permanent else f"💰 Price: **{daily_cost:,} Stardust**"
            )
            limit_text = cog.shop_limit_text(item_id)
            embed.add_field(
                name=item["name"],
                value=f"{price_text}\n📖 {item['desc']}\n📦 **Purchase Limit:** {limit_text.removeprefix(' • Limit: ') if limit_text else 'None'}",
                inline=False,
            )
        return embed

class SellAllConfirmView(discord.ui.View):
    """Confirmation controls for bulk inventory sales."""

    def __init__(self, cog, owner_id, sale_kind, *, return_view=None):
        super().__init__(timeout=60)
        self.cog = cog
        self.owner_id = owner_id
        self.sale_kind = sale_kind
        self.return_view = return_view
        self.finished = False
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "⚠️ This sale confirmation belongs to someone else.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self):
        if self.finished:
            return
        for child in self.children:
            if isinstance(child, (discord.ui.Button, discord.ui.Select)):
                child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except (discord.NotFound, discord.HTTPException):
                pass

    @discord.ui.button(label="Yes, Sell All", emoji="✅", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.finished:
            return
        self.finished = True
        self.stop()
        for child in self.children:
            if isinstance(child, (discord.ui.Button, discord.ui.Select)):
                child.disabled = True
        await self.cog._confirm_bulk_sale(
            interaction, self.sale_kind, self, return_view=self.return_view
        )

    @discord.ui.button(label="Cancel", emoji="❌", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.finished:
            return
        self.finished = True
        self.stop()
        if self.return_view:
            view = self.return_view.make_return_view()
            await view.show_item_picker(interaction)
            return
        for child in self.children:
            if isinstance(child, (discord.ui.Button, discord.ui.Select)):
                child.disabled = True
        await interaction.response.edit_message(
            content="❌ **Sale cancelled.** Nothing was sold.",
            embed=None,
            view=self,
        )
