"""Discord UI views used by the pet system."""

from typing import cast

import discord

from .config import PET_PASSIVE_MAX_LEVEL
from .core import get_pet_definition, get_passive_value, passive_level_for_pet, xp_needed_for_next_level
from .incubator import (INCUBATOR_UPGRADE_CAPS, UPGRADE_COSTS, UPGRADE_DESCRIPTIONS, UPGRADE_LABELS, SPEED_REDUCTIONS, DETECTION_BONUSES, LUCK_OCCURRENCE_BONUSES)



class IncubatorMainView(discord.ui.View):
    """Persistent controls for the main /incubator embed."""
    def __init__(self, cog, user_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id

    async def _owner(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This incubator interface isn't for you.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Upgrade Tubes", emoji="🔧", style=discord.ButtonStyle.primary, row=0)
    async def upgrade(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._owner(interaction):
            return
        view = IncubatorTubeSelectView(self.cog, self.user_id)
        await interaction.response.edit_message(
            embed=await self.cog._incubator_upgrade_tubes_embed(self.user_id),
            view=view,
        )


class IncubatorTubeSelectView(discord.ui.View):
    def __init__(self, cog, user_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id

        for tube_id in range(1, 4):
            if tube_id <= getattr(cog, "_incubator_slots_cache", {}).get(user_id, 3):
                button = discord.ui.Button(
                    label=f"Tube {tube_id}", emoji=("🧪", "🔬", "🧬")[tube_id - 1],
                    style=discord.ButtonStyle.primary, row=0,
                )
                button.callback = self._make_tube_callback(tube_id)
                self.add_item(button)

        back = discord.ui.Button(label="Back", emoji="↩️", style=discord.ButtonStyle.secondary, row=1)
        back.callback = self._back
        self.add_item(back)

    async def _owner(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This incubator interface isn't for you.", ephemeral=True)
            return False
        return True

    def _make_tube_callback(self, tube_id):
        async def callback(interaction):
            if not await self._owner(interaction):
                return
            view = IncubatorCategoryView(self.cog, self.user_id, tube_id)
            await interaction.response.edit_message(
                embed=await self.cog._incubator_tube_upgrade_embed(self.user_id, tube_id),
                view=view,
            )
        return callback

    async def _back(self, interaction):
        if not await self._owner(interaction):
            return
        await interaction.response.edit_message(
            embed=await self.cog._incubator_main_embed(self.user_id),
            view=IncubatorMainView(self.cog, self.user_id),
        )


class IncubatorCategoryView(discord.ui.View):
    def __init__(self, cog, user_id, tube_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        self.tube_id = tube_id
        categories = ("speed", "detection", "luck", "analysis")
        for index, category in enumerate(categories):
            emoji, label = UPGRADE_LABELS[category]
            button = discord.ui.Button(label=label, emoji=emoji, style=discord.ButtonStyle.primary, row=index // 2)
            button.callback = self._make_category_callback(category)
            self.add_item(button)
        back = discord.ui.Button(label="Back", emoji="↩️", style=discord.ButtonStyle.secondary, row=2)
        back.callback = self._back
        self.add_item(back)

    async def _owner(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This incubator interface isn't for you.", ephemeral=True)
            return False
        return True

    def _make_category_callback(self, category):
        async def callback(interaction):
            if not await self._owner(interaction):
                return
            view = IncubatorUpgradeDetailView(self.cog, self.user_id, self.tube_id, category)
            await interaction.response.edit_message(
                embed=await self.cog._incubator_upgrade_detail_embed(self.user_id, self.tube_id, category),
                view=view,
            )
        return callback

    async def _back(self, interaction):
        if not await self._owner(interaction):
            return
        await interaction.response.edit_message(
            embed=await self.cog._incubator_upgrade_tubes_embed(self.user_id),
            view=IncubatorTubeSelectView(self.cog, self.user_id),
        )


class IncubatorUpgradeDetailView(discord.ui.View):
    def __init__(self, cog, user_id, tube_id, category):
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        self.tube_id = tube_id
        self.category = category
        cap = INCUBATOR_UPGRADE_CAPS[tube_id][category]
        # Upgrade button is disabled at max level; the detail screen remains useful.
        button = discord.ui.Button(label="Upgrade", emoji="⬆️", style=discord.ButtonStyle.success, row=0, disabled=False)
        button.callback = self._upgrade
        self.add_item(button)
        back = discord.ui.Button(label="Back", emoji="↩️", style=discord.ButtonStyle.secondary, row=0)
        back.callback = self._back
        self.add_item(back)
        cancel = discord.ui.Button(label="Cancel", emoji="❌", style=discord.ButtonStyle.secondary, row=0)
        cancel.callback = self._cancel
        self.add_item(cancel)

    async def _owner(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This incubator interface isn't for you.", ephemeral=True)
            return False
        return True

    async def _upgrade(self, interaction):
        if not await self._owner(interaction):
            return
        result = await self.cog._upgrade_incubator(self.user_id, self.tube_id, self.category, channel=interaction.channel)
        if not result.get("ok"):
            return await interaction.response.edit_message(
                embed=await self.cog._incubator_upgrade_detail_embed(self.user_id, self.tube_id, self.category, error=result.get("message")),
                view=IncubatorUpgradeDetailView(self.cog, self.user_id, self.tube_id, self.category),
            )
        await interaction.response.edit_message(
            embed=await self.cog._incubator_upgrade_detail_embed(
                self.user_id, self.tube_id, self.category, success=result
            ),
            view=IncubatorUpgradeDetailView(self.cog, self.user_id, self.tube_id, self.category),
        )

    async def _back(self, interaction):
        if not await self._owner(interaction):
            return
        await interaction.response.edit_message(
            embed=await self.cog._incubator_tube_upgrade_embed(self.user_id, self.tube_id),
            view=IncubatorCategoryView(self.cog, self.user_id, self.tube_id),
        )

    async def _cancel(self, interaction):
        if not await self._owner(interaction):
            return
        await interaction.response.edit_message(
            embed=await self.cog._incubator_main_embed(self.user_id),
            view=IncubatorMainView(self.cog, self.user_id),
        )


class FeedTreatSelect(discord.ui.Select):
    def __init__(self, cog, user_id, pet_id, owned, parent_message, ctx):
        options = []
        for item_id, label, emoji in (
            ("pet_snack", "Pet Treat", "🍖"),
            ("halloween_pet_candy", "Halloween Pet Candy", "🎃"),
        ):
            quantity = owned.get(item_id, 0)
            if quantity <= 0:
                continue
            options.append(discord.SelectOption(
                label=f"{label} ×{quantity}",
                value=item_id,
                emoji=emoji,
                description="Feed this treat to the selected pet.",
            ))
        super().__init__(placeholder="Choose a treat...", min_values=1, max_values=1, options=options)
        self.cog = cog
        self.user_id = user_id
        self.pet_id = pet_id
        self.parent_message = parent_message
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This treat menu isn't for you.", ephemeral=True)
        result, error = await self.cog._feed_specific_pet(
            self.user_id,
            self.pet_id,
            self.values[0],
        )
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        if result is None:
            return await interaction.response.send_message(
                "❌ Feeding failed because no result was returned.",
                ephemeral=True,
            )
        pet = result["pet"]
        level_line = ""
        if result["leveled_up"]:
            level_line = (
                f"\n🎉 **Level Up!** Your pet reached **Level {result['new_level']}**!"
                f"\n✨ Passive is now **Level {result['passive_level']}/{PET_PASSIVE_MAX_LEVEL}**."
            )
        await interaction.response.send_message(
            f"{pet['emoji']} **{pet['nickname'] or pet['name']}** enjoyed the "
            f"**{result['treat']['name']}**!\n✨ **+{result['xp_amount']} Pet XP**{level_line}",
            ephemeral=True,
        )
        await self.cog._refresh_pet_view(self.parent_message, self.user_id, self.pet_id, ctx=self.ctx)


class FeedTreatView(discord.ui.View):
    def __init__(self, cog, user_id, pet_id, owned, parent_message, ctx):
        super().__init__(timeout=60)
        self.parent_message = parent_message
        self.add_item(FeedTreatSelect(cog, user_id, pet_id, owned, parent_message, ctx))


class ReleaseConfirmationView(discord.ui.View):
    def __init__(self, cog, user_id, pet, parent_message, ctx):
        super().__init__(timeout=30)
        self.cog = cog
        self.user_id = user_id
        self.pet_id = pet["pet_id"]
        self.pet = pet
        self.parent_message = parent_message
        self.ctx = ctx

    @discord.ui.button(label="Yes, Release Pet", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This confirmation isn't for you.", ephemeral=True)
        released = await self.cog._release_pet(self.user_id, self.pet_id)
        if not released:
            self.stop()
            return await interaction.response.edit_message(content="❌ That pet could not be released because it no longer exists.", view=None)
        if released.get("protected"):
            self.stop()
            return await interaction.response.edit_message(
                content="🔒 **This pet is favorited and protected!** Unfavorite it first if you really want to release it.",
                view=None,
            )
        self.stop()
        essence_line = "\n✨ **Astral Essence recovered!**" if released.get("essence_awarded") else ""
        await interaction.response.edit_message(
            content=(
                f"🔴 Released **{released['emoji']} {released['nickname'] or released['name']}** "
                f"(Level {released['level']}).{essence_line}\n\n"
                "This pet has been permanently removed from your collection."
            ),
            view=None,
        )
        await self.cog._refresh_pet_view(self.parent_message, self.user_id, self.pet_id, allow_missing=True, ctx=self.ctx)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This confirmation isn't for you.", ephemeral=True)
        self.stop()
        await interaction.response.edit_message(content="Release cancelled. 👍", view=None)


class RenamePetModal(discord.ui.Modal):
    def __init__(self, cog, user_id, pet_id, parent_message, ctx):
        super().__init__(title="Rename Pet", timeout=120)
        self.cog = cog
        self.user_id = user_id
        self.pet_id = pet_id
        self.parent_message = parent_message
        self.ctx = ctx

        self.name_input = discord.ui.TextInput(
            label="Pet Name",
            placeholder="Enter a new name (30 characters max)",
            max_length=30,
            required=False,
        )
        self.add_item(self.name_input)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "❌ This rename menu isn't for you.", ephemeral=True
            )

        new_name = str(self.name_input.value).strip()
        if len(new_name) > 30:
            return await interaction.response.send_message(
                "❌ Pet names can be at most **30 characters** long.",
                ephemeral=True,
            )

        renamed = await self.cog._rename_pet(self.user_id, self.pet_id, new_name)
        if not renamed:
            return await interaction.response.send_message(
                "❌ That pet no longer exists in your collection.",
                ephemeral=True,
            )

        display_name = renamed["nickname"] or renamed["name"]
        if renamed["nickname"]:
            message = (
                f"✏️ Pet renamed to **{display_name}**!\n"
                f"-# Original: {renamed['name']}"
            )
        else:
            message = f"✏️ **{renamed['name']}** is back to its original name."

        await interaction.response.send_message(message, ephemeral=True)
        await self.cog._refresh_pet_view(
            self.parent_message,
            self.user_id,
            self.pet_id,
            ctx=self.ctx,
        )


class PetCollectionView(discord.ui.View):
    """Landing-page category selector for the grouped /pets collection."""

    def __init__(self, cog, user_id, ctx):
        super().__init__(timeout=600)
        self.cog = cog
        self.user_id = user_id
        self.ctx = ctx

    async def _ensure_owner(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This pet collection isn't for you.",
                ephemeral=True,
            )
            return False
        return True

    async def _open_category(self, interaction, category):
        if not await self._ensure_owner(interaction):
            return
        pets = await self.cog._get_owned_pets(self.user_id)
        entries = self.cog._group_owned_pets(pets, category)
        if not entries:
            await interaction.response.edit_message(
                embed=self.cog._pet_category_embed(self.ctx, pets, category, 0, 1),
                view=self,
            )
            return

        # The inventory category behaves like the old pet screen: one pet at
        # a time, with the ◀️/▶️ buttons acting as the category's scroll.
        # Each entry is a representative for an exact pet/variant/level group.
        grouped_pets = [entry["pet"] for entry in entries]
        index = 0
        self.stop()
        view = PetManagementView(
            self.cog,
            self.user_id,
            self.ctx,
            grouped_pets,
            index,
            inventory_category=category,
            bundle_counts=[entry["count"] for entry in entries],
        )
        await interaction.response.edit_message(
            embed=self.cog._pet_embed(
                self.ctx, grouped_pets[index], index, len(grouped_pets),
                bundle_count=entries[index]["count"],
            ),
            view=view,
        )

    @discord.ui.button(label="🥚 Normal Eggs", style=discord.ButtonStyle.primary, row=0)
    async def normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._open_category(interaction, "normal")

    @discord.ui.button(label="💾 Glitched Eggs", style=discord.ButtonStyle.primary, row=0)
    async def glitched(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._open_category(interaction, "glitched")

    @discord.ui.button(label="🎃 Halloween Eggs", style=discord.ButtonStyle.primary, row=1)
    async def halloween(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._open_category(interaction, "halloween")

    @discord.ui.button(label="👻 Haunted Pets", style=discord.ButtonStyle.primary, row=1)
    async def haunted(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._open_category(interaction, "haunted")


class PetGroupSelect(discord.ui.Select):
    """Select one grouped pet entry and open an individual copy for management."""

    def __init__(self, cog, user_id, ctx, category, entries, page):
        options = []
        for entry in entries:
            pet = entry["pet"]
            marker = "⭐ " if any(member["is_active"] for member in entry["members"]) else ""
            count_text = f" ×{entry['count']}" if entry["count"] > 1 else ""
            label = f"{marker}{pet['name']} — Lv. {pet['level']}{count_text}"
            options.append(discord.SelectOption(
                label=label[:100],
                value=str(pet["pet_id"]),
                emoji=pet["emoji"],
                description=(
                    "Active companion" if any(member["is_active"] for member in entry["members"])
                    else f"{entry['count']} matching copies"
                ),
            ))
        super().__init__(
            placeholder="Choose a pet group to manage...",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.cog = cog
        self.user_id = user_id
        self.ctx = ctx
        self.category = category
        self.page = page

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "❌ This pet collection isn't for you.",
                ephemeral=True,
            )

        pets = await self.cog._get_owned_pets(self.user_id)
        pet_id = int(self.values[0])
        index = next((i for i, pet in enumerate(pets) if pet["pet_id"] == pet_id), None)
        if index is None:
            return await interaction.response.send_message(
                "❌ That pet is no longer in your collection.",
                ephemeral=True,
            )

        self.view.stop()
        view = PetManagementView(self.cog, self.user_id, self.ctx, pets, index)
        await interaction.response.edit_message(
            embed=self.cog._pet_embed(self.ctx, pets[index], index, len(pets)),
            view=view,
        )


class PetCategoryView(discord.ui.View):
    """Paginated grouped pet list for one /pets category."""

    def __init__(self, cog, user_id, ctx, category, pets=None, page=0):
        super().__init__(timeout=600)
        self.cog = cog
        self.user_id = user_id
        self.ctx = ctx
        self.category = category
        self.page = page
        if pets is not None:
            self._rebuild(pets)

    def _page_data(self, pets):
        entries = self.cog._group_owned_pets(pets, self.category)
        page_count = max(1, (len(entries) + 19) // 20)
        self.page = min(self.page, page_count - 1)
        start = self.page * 20
        return entries, page_count, entries[start:start + 20]

    def _rebuild(self, pets=None):
        if pets is None:
            # The view is constructed before the async refresh; controls are
            # rebuilt by _refresh once the live collection has been loaded.
            return
        for item in list(self.children):
            self.remove_item(item)
        entries, page_count, visible = self._page_data(pets)
        if visible:
            self.add_item(PetGroupSelect(
                self.cog,
                self.user_id,
                self.ctx,
                self.category,
                visible,
                self.page,
            ))

        previous = discord.ui.Button(
            label="◀️",
            style=discord.ButtonStyle.primary,
            disabled=self.page <= 0,
            row=1,
        )
        next_button = discord.ui.Button(
            label="▶️",
            style=discord.ButtonStyle.primary,
            disabled=self.page >= page_count - 1,
            row=1,
        )
        back = discord.ui.Button(
            label="◀️ Back to Collection",
            style=discord.ButtonStyle.secondary,
            row=1,
        )

        async def previous_callback(interaction):
            if not await self._ensure_owner(interaction):
                return
            self.page -= 1
            await self._refresh(interaction)

        async def next_callback(interaction):
            if not await self._ensure_owner(interaction):
                return
            self.page += 1
            await self._refresh(interaction)

        async def back_callback(interaction):
            if not await self._ensure_owner(interaction):
                return
            pets_now = await self.cog._get_owned_pets(self.user_id)
            self.stop()
            view = PetCollectionView(self.cog, self.user_id, self.ctx)
            await interaction.response.edit_message(
                embed=self.cog._pet_collection_embed(self.ctx, pets_now),
                view=view,
            )

        previous.callback = previous_callback
        next_button.callback = next_callback
        back.callback = back_callback
        self.add_item(previous)
        self.add_item(next_button)
        self.add_item(back)

    async def _ensure_owner(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This pet collection isn't for you.",
                ephemeral=True,
            )
            return False
        return True

    async def _refresh(self, interaction):
        pets = await self.cog._get_owned_pets(self.user_id)
        entries = self.cog._group_owned_pets(pets, self.category)
        page_count = max(1, (len(entries) + 19) // 20)
        self.page = min(self.page, page_count - 1)
        self._rebuild(pets)
        await interaction.response.edit_message(
            embed=self.cog._pet_category_embed(
                self.ctx,
                pets,
                self.category,
                self.page,
                page_count,
            ),
            view=self,
        )



class PetStatsView(discord.ui.View):
    def __init__(self, cog, user_id, ctx, pets, index=0):
        super().__init__(timeout=600)
        self.cog = cog
        self.user_id = user_id
        self.ctx = ctx
        self.pets = pets
        self.index = index

    async def _ensure_owner(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This pet menu isn't for you.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="◀️ Back to Pets", style=discord.ButtonStyle.primary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return

        pets = await self.cog._get_owned_pets(self.user_id)
        if not pets:
            self.stop()
            embed = discord.Embed(
                title=f"🐾 {self.ctx.author.display_name}'s Pet Collection",
                description="Your collection is empty!",
                color=discord.Color.from_rgb(120, 140, 160),
            )
            return await interaction.response.edit_message(embed=embed, view=None)

        index = next(
            (i for i, pet in enumerate(pets) if pet["pet_id"] == self.pets[self.index]["pet_id"]),
            min(self.index, len(pets) - 1),
        )
        self.stop()
        view = PetManagementView(self.cog, self.user_id, self.ctx, pets, index)
        await interaction.response.edit_message(
            embed=self.cog._pet_embed(self.ctx, pets[index], index, len(pets)),
            view=view,
        )


class PetManagementView(discord.ui.View):
    def __init__(self, cog, user_id, ctx, pets, index=0, inventory_category=None, bundle_counts=None):
        super().__init__(timeout=600)
        self.cog = cog
        self.user_id = user_id
        self.ctx = ctx
        self.pets = pets
        self.index = index
        self.inventory_category = inventory_category
        self.bundle_counts = bundle_counts or [1] * len(pets)
        self._sync_buttons()

    def _current_bundle_count(self):
        if 0 <= self.index < len(self.bundle_counts):
            return self.bundle_counts[self.index]
        return 1

    async def _reload_inventory_groups(self):
        pets = await self.cog._get_owned_pets(self.user_id)
        if not self.inventory_category:
            self.pets = pets
            self.bundle_counts = [1] * len(pets)
            self.index = min(self.index, len(pets) - 1)
            return

        entries = self.cog._group_owned_pets(pets, self.inventory_category)
        old_pet_id = self.pets[self.index]["pet_id"] if self.pets and self.index < len(self.pets) else None
        self.pets = [entry["pet"] for entry in entries]
        self.bundle_counts = [entry["count"] for entry in entries]
        if not self.pets:
            self.index = 0
            return
        self.index = next(
            (i for i, pet in enumerate(self.pets) if pet["pet_id"] == old_pet_id),
            min(self.index, len(self.pets) - 1),
        )

    def _sync_buttons(self):
        previous = cast(discord.ui.Button, self.previous)
        next_button = cast(discord.ui.Button, self.next)
        equip = cast(discord.ui.Button, self.equip)
        favorite = cast(discord.ui.Button, self.favorite)

        previous.disabled = len(self.pets) <= 1
        next_button.disabled = len(self.pets) <= 1
        pet = self.pets[self.index]
        equip.label = "⭐ Unequip Pet" if pet["is_active"] else "⭐ Equip Pet"
        equip.style = discord.ButtonStyle.primary
        favorite.label = "🔓 Unfavorite" if pet["is_favorite"] else "🔒 Favorite"
        favorite.style = discord.ButtonStyle.primary

    async def _ensure_owner(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This pet menu isn't for you.", ephemeral=True)
            return False
        return True

    async def _refresh(self, interaction=None, message=None):
        await self._reload_inventory_groups()
        if not self.pets:
            self.stop()
            embed = discord.Embed(
                title=f"🐾 {self.ctx.author.display_name}'s Pet Collection",
                description="Your collection is empty!",
                color=discord.Color.from_rgb(120, 140, 160),
            )
            target = message or (interaction.message if interaction else None)
            if target:
                await target.edit(embed=embed, view=None)
            return
        self.index = min(self.index, len(self.pets) - 1)
        self._sync_buttons()
        target = message or (interaction.message if interaction else None)
        if target:
            await target.edit(
                embed=self.cog._pet_embed(
                    self.ctx, self.pets[self.index], self.index, len(self.pets),
                    bundle_count=self._current_bundle_count(),
                ),
                view=self,
            )

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary, row=2)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        self.index = (self.index - 1) % len(self.pets)
        self._sync_buttons()
        await interaction.response.edit_message(
            embed=self.cog._pet_embed(self.ctx, self.pets[self.index], self.index, len(self.pets), bundle_count=self._current_bundle_count()),
            view=self,
        )

    @discord.ui.button(label="📊 Pet Stats", style=discord.ButtonStyle.primary, row=0)
    async def stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        pet = self.pets[self.index]
        await interaction.response.edit_message(
            embed=self.cog._pet_stats_embed(self.ctx, pet),
            view=PetStatsView(
                self.cog,
                self.user_id,
                self.ctx,
                self.pets,
                self.index,
            ),
        )

    @discord.ui.button(label="⭐ Equip Pet", style=discord.ButtonStyle.primary, row=0)
    async def equip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        pet = self.pets[self.index]
        if pet["is_active"]:
            changed = await self.cog._unequip_pet(self.user_id, pet["pet_id"])
            if not changed:
                return await interaction.response.send_message("❌ That pet is no longer equipped.", ephemeral=True)
            await self._reload_inventory_groups()
            if not self.pets:
                return await interaction.response.edit_message(content="❌ That pet is no longer available in this category.", view=None)
            self._sync_buttons()
            await interaction.response.edit_message(
                embed=self.cog._pet_embed(
                    self.ctx, self.pets[self.index], self.index, len(self.pets),
                    bundle_count=self._current_bundle_count(),
                ),
                view=self,
            )
        else:
            definition, error = await self.cog._equip_pet(self.user_id, pet["pet_id"])
            if error:
                return await interaction.response.send_message(error, ephemeral=True)
            await self._reload_inventory_groups()
            if not self.pets:
                return await interaction.response.edit_message(content="❌ That category is now empty.", view=None)
            self._sync_buttons()
            await interaction.response.edit_message(
            embed=self.cog._pet_embed(self.ctx, self.pets[self.index], self.index, len(self.pets), bundle_count=self._current_bundle_count()),
            view=self,
        )

    @discord.ui.button(label="🔒 Favorite", style=discord.ButtonStyle.primary, row=1)
    async def favorite(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        pet = self.pets[self.index]
        favorited, error = await self.cog._set_pet_favorite(self.user_id, pet["pet_id"], not pet["is_favorite"])
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        await self._reload_inventory_groups()
        if not self.pets:
            return await interaction.response.edit_message(content="❌ That category is now empty.", view=None)
        self._sync_buttons()
        await interaction.response.edit_message(
            embed=self.cog._pet_embed(
                self.ctx, self.pets[self.index], self.index, len(self.pets),
                bundle_count=self._current_bundle_count(),
            ),
            view=self,
        )

    @discord.ui.button(label="✏️ Rename Pet", style=discord.ButtonStyle.primary, row=1)
    async def rename(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        pet = self.pets[self.index]
        modal = RenamePetModal(
            self.cog,
            self.user_id,
            pet["pet_id"],
            interaction.message,
            self.ctx,
        )
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🔴 Release Pet", style=discord.ButtonStyle.danger, row=1)
    async def release(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        pet = self.pets[self.index]
        if pet["is_favorite"]:
            return await interaction.response.send_message(
                "🔒 **This pet is favorited and protected!** Unfavorite it first if you want to release it.",
                ephemeral=True,
            )
        await interaction.response.send_message(
            (
                f"⚠️ **Are you sure?**\n\n"
                f"You are about to permanently release **{pet['emoji']} {pet['nickname'] or pet['name']}**.\n"
                f"Level **{pet['level']}** • **{pet['xp']} XP**\n\n"
                f"This cannot be undone."
            ),
            view=ReleaseConfirmationView(self.cog, self.user_id, pet, interaction.message, self.ctx),
            ephemeral=True,
        )

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary, row=2)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        self.index = (self.index + 1) % len(self.pets)
        self._sync_buttons()
        await interaction.response.edit_message(
            embed=self.cog._pet_embed(self.ctx, self.pets[self.index], self.index, len(self.pets), bundle_count=self._current_bundle_count()),
            view=self,
        )

    @discord.ui.button(label="📦 Pet Inventory", style=discord.ButtonStyle.secondary, row=3)
    async def collection(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._ensure_owner(interaction):
            return
        pets = await self.cog._get_owned_pets(self.user_id)
        self.stop()
        view = PetCollectionView(self.cog, self.user_id, self.ctx)
        await interaction.response.edit_message(
            embed=self.cog._pet_collection_embed(self.ctx, pets),
            view=view,
        )


class FusionVariantView(discord.ui.View):
    def __init__(self, cog, user_id, target_pet_id, base_pet_type, variant_id, ctx):
        super().__init__(timeout=120)
        self.cog = cog
        self.user_id = user_id
        self.target_pet_id = target_pet_id
        self.base_pet_type = base_pet_type
        self.variant_id = variant_id
        self.ctx = ctx

    async def _owner(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This fusion result isn't for you.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🧬 Infuse into Current Pet", style=discord.ButtonStyle.primary)
    async def infuse(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._owner(interaction):
            return
        result = await self.cog._infuse_variant(
            self.user_id, self.target_pet_id, self.base_pet_type, self.variant_id
        )
        self.stop()
        if result is None:
            return await interaction.response.edit_message(
                content="❌ That pet could no longer be found, so the variant was not infused.",
                view=None,
            )
        definition = get_pet_definition(self.base_pet_type, self.variant_id)
        if not definition:
            return await interaction.response.edit_message(
                content="❌ The variant definition could no longer be found.",
                view=None,
            )
        await interaction.response.edit_message(
            content=(
                f"🧬 **Variant Infused!**\n\n"
                f"{definition['emoji']} **{definition['name']}** is now your existing pet's form.\n"
                f"✨ Level, XP, Fusion, and passive progression were all preserved."
            ),
            view=None,
        )

    @discord.ui.button(label="📦 Keep as Separate Pet", style=discord.ButtonStyle.secondary)
    async def separate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._owner(interaction):
            return
        result = await self.cog._create_variant_pet(
            self.user_id, self.base_pet_type, self.variant_id
        )
        self.stop()
        if result is None:
            return await interaction.response.edit_message(
                content="❌ The variant could not be created as a separate pet.",
                view=None,
            )
        definition = get_pet_definition(self.base_pet_type, self.variant_id)
        if not definition:
            return await interaction.response.edit_message(
                content="❌ The variant definition could no longer be found.",
                view=None,
            )
        await interaction.response.edit_message(
            content=(
                f"📦 **Variant Kept Separately!**\n\n"
                f"{definition['emoji']} **{definition['name']}** was added to your pet collection at Level 1."
            ),
            view=None,
        )


class PostFusionConfirmView(discord.ui.View):
    def __init__(self, cog, ctx, target_pet_id):
        super().__init__(timeout=60)
        self.cog = cog
        self.ctx = ctx
        self.target_pet_id = target_pet_id

    @discord.ui.button(label="Yes, Continue", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ This fusion confirmation isn't for you.", ephemeral=True)
        self.stop()
        await interaction.response.defer()
        await self.cog._execute_pet_fusion(self.ctx, self.target_pet_id)
        try:
            await interaction.edit_original_response(view=None)
        except discord.HTTPException:
            pass

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ This fusion confirmation isn't for you.", ephemeral=True)
        self.stop()
        await interaction.response.edit_message(
            content="🧬 Fusion cancelled. Your pet and materials were not changed.",
            view=None,
        )

