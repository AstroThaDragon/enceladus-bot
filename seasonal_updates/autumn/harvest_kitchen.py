"""Autumn Harvest + Thanksgiving Gathering and Harvest Kitchen runtime cog."""
from __future__ import annotations
import random, time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import aiosqlite, discord
from discord import app_commands
from discord.ext import commands
from database import ECONOMY_DB_NAME
from inventory import ITEM_REGISTRY, add_inventory_item
from .autumn import is_autumn_active, AUTUMN_INGREDIENTS, AUTUMN_RECIPES, AUTUMN_PET_TREATS, AUTUMN_PET_TREAT_RECIPES, AUTUMN_EGGS, AUTUMN_PET_POOLS
from .thanksgiving import (THANKSGIVING_INGREDIENTS, THANKSGIVING_RECIPES, THANKSGIVING_PET_TREATS,
    THANKSGIVING_EGGS, THANKSGIVING_PETS, PANTRY_STAPLES)
from pets.core import get_active_pet_effects

ET = ZoneInfo("America/New_York")
ACTIVITIES = {"autumn_harvest": ("Autumn Harvest", "🍂", "autumn"), "thanksgiving_gathering": ("Thanksgiving Gathering", "🦃", "thanksgiving")}
COMMON_UNCOMMON_WEIGHTS = {"common": 0.88, "uncommon": 0.12}

class HarvestKitchen(commands.Cog):
    def __init__(self, bot): self.bot = bot
    async def cog_load(self):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await db.execute("""CREATE TABLE IF NOT EXISTS seasonal_activity_usage (
                user_id INTEGER NOT NULL, activity_id TEXT NOT NULL, window_start REAL NOT NULL,
                uses INTEGER NOT NULL DEFAULT 0, last_used REAL NOT NULL DEFAULT 0,
                PRIMARY KEY(user_id, activity_id))""")
            async with db.execute("PRAGMA table_info(seasonal_activity_usage)") as cur:
                columns = {row[1] for row in await cur.fetchall()}
            if "last_used" not in columns:
                await db.execute(
                    "ALTER TABLE seasonal_activity_usage ADD COLUMN last_used REAL NOT NULL DEFAULT 0"
                )
            await db.execute("""CREATE TABLE IF NOT EXISTS seasonal_pet_unlocks (
                user_id INTEGER NOT NULL, pet_type TEXT NOT NULL, unlocked_at REAL NOT NULL,
                PRIMARY KEY(user_id, pet_type))""")
            await db.commit()

    def _active(self): return is_autumn_active(datetime.now(ET))

    async def _use_slot(self, db, user_id, activity_id):
        now = time.time()
        interval = 12 * 3600
        cooldown = 15 * 60
        cap = 20
        async with db.execute(
            "SELECT window_start, uses, last_used FROM seasonal_activity_usage WHERE user_id=? AND activity_id=?",
            (user_id, activity_id),
        ) as cur:
            row = await cur.fetchone()
        if not row or now-row[0] >= interval:
            start = now
            uses = 0
            last_used = row[2] if row else 0
            await db.execute(
                "INSERT INTO seasonal_activity_usage(user_id,activity_id,window_start,uses,last_used) VALUES(?,?,?,0,?) "
                "ON CONFLICT(user_id,activity_id) DO UPDATE SET window_start=excluded.window_start, uses=0",
                (user_id, activity_id, start, last_used),
            )
        else:
            start, uses, last_used = row
        attempts_left = max(0, cap - uses)
        if uses >= cap:
            return False, max(0, int(interval - (now - start))), 0, "limit"
        cooldown_remaining = max(0, int(cooldown - (now - (last_used or 0)))) if last_used else 0
        if cooldown_remaining:
            return False, cooldown_remaining, attempts_left, "cooldown"
        await db.execute(
            "UPDATE seasonal_activity_usage SET uses=uses+1, last_used=? WHERE user_id=? AND activity_id=?",
            (now, user_id, activity_id),
        )
        return True, 0, attempts_left - 1, None

    def _pool(self, collection):
        if collection=="autumn": return AUTUMN_INGREDIENTS
        return THANKSGIVING_INGREDIENTS

    async def gather(self, interaction: discord.Interaction, activity_id: str):
        if not self._active():
            embed = discord.Embed(title="🍂 Seasonal Gathering", description="Autumn is dormant. The seasonal gathering grounds reopen November 1!", color=discord.Color.orange())
            return await interaction.response.send_message(embed=embed)
        if activity_id not in ACTIVITIES:
            embed = discord.Embed(title="Seasonal Gathering", description="Unknown seasonal activity.", color=discord.Color.orange())
            return await interaction.response.send_message(embed=embed)
        name,emoji,collection=ACTIVITIES[activity_id]
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await db.execute("BEGIN IMMEDIATE")
            ok, remaining, attempts_left, reason = await self._use_slot(
                db, interaction.user.id, activity_id
            )
            if not ok:
                await db.commit()
                if reason == "cooldown":
                    minutes, seconds = divmod(remaining, 60)
                    description = f"Your gathering grounds are still recovering. Try again in **{minutes}m {seconds}s**."
                    footer = f"Attempts left: {attempts_left}/20 • 15-minute cooldown per activity."
                else:
                    description = f"You're out of attempts for this 12-hour cycle. Your next cycle begins in **{remaining//3600}h {(remaining%3600)//60}m**."
                    footer = "Attempts left: 0/20 • Each activity resets on its own 12-hour cycle."
                embed = discord.Embed(title=f"{emoji} {name}", description=description, color=discord.Color.orange())
                embed.set_footer(text=footer)
                return await interaction.response.send_message(content=interaction.user.mention, embed=embed)
            effects=await get_active_pet_effects(db,interaction.user.id)
            pool=self._pool(collection)
            if collection=="thanksgiving":
                count=random.randint(2,3)
                common=[k for k,v in pool.items() if v.get("rarity")=="common"]
                uncommon=[k for k,v in pool.items() if v.get("rarity")=="uncommon"]
                selected=[]
                uncommon_chance=min(0.40, COMMON_UNCOMMON_WEIGHTS["uncommon"] + effects.get("sticky_fingers", 0.0))
                for _ in range(count):
                    candidates=uncommon if random.random()<uncommon_chance else common
                    candidates=[x for x in candidates if x not in selected] or [x for x in pool if x not in selected]
                    if candidates: selected.append(random.choice(candidates))
            else:
                count=random.randint(2,3); selected=random.sample(list(pool),min(count,len(pool)))
            if collection == "autumn":
                ingredient_bonus = effects.get("autumn_ingredient_discovery_bonus", 0.0)
                if ingredient_bonus and random.random() < ingredient_bonus:
                    selected.append(random.choice(list(pool)))
                acorn_bonus = effects.get("acorn_discovery_bonus", 0.0)
                if acorn_bonus and random.random() < acorn_bonus and "acorns" in pool:
                    selected.append("acorns")
            rewards=[]
            for item_id in selected:
                amount=random.randint(1,3)
                info=pool[item_id]
                # Each passive is scoped to its described activity and reward type.
                extra_chance = 0.0
                if collection == "thanksgiving":
                    extra_chance += effects.get("happy_gobbling", 0.0)
                    # Berry Picking excludes ingredients used only by drinks.
                    drink_only = {iid for iid, data in THANKSGIVING_INGREDIENTS.items()
                                  if data.get("used_in") and all(THANKSGIVING_RECIPES.get(rid, {}).get("category") == "drink" for rid in data["used_in"])}
                    if item_id not in drink_only:
                        extra_chance += effects.get("berry_picking", 0.0)
                elif collection == "autumn":
                    drink_ingredients = {"apple_cider", "chai_tea_leaves", "cup_and_saucer_set", "single_straw", "coffee_beans", "maple_syrup", "cinnamon_sticks", "whipped_cream"}
                    if item_id in drink_ingredients:
                        extra_chance += effects.get("baristas_blessing", 0.0)
                if random.random() < min(0.75, extra_chance): amount += 1
                added,_,_=await add_inventory_item(db,interaction.user.id,item_id,ITEM_REGISTRY.get(item_id,{}).get("type","Event Items"),amount)
                rewards.append(f"{info.get('emoji','🍂')} **{info.get('name',item_id)}** ×{added}")
            treat_pool=THANKSGIVING_PET_TREATS if collection=="thanksgiving" else AUTUMN_PET_TREATS
            if treat_pool and random.random()<0.02:
                treat_id=random.choice(list(treat_pool)); info=treat_pool[treat_id]
                added,_,_=await add_inventory_item(db,interaction.user.id,treat_id,"Pet Treat",1)
                if added: rewards.append(f"{info.get('emoji','🐾')} **{info.get('name',treat_id)}** ×1 (rare treat find!)")
            egg_chance=0.05
            egg_id=None
            if random.random()<egg_chance:
                if collection=="thanksgiving": egg_id=random.choice(["harvest_egg","feast_egg"])
                else: egg_id=random.choice(list(AUTUMN_PET_POOLS))
                added,_,_=await add_inventory_item(db,interaction.user.id,egg_id,"Pet Egg",1)
                if added: rewards.append(f"🥚 **{ITEM_REGISTRY.get(egg_id,{}).get('name',egg_id.replace('_',' ').title())}** ×1")
            await db.commit()
        achievements_cog = self.bot.get_cog("Achievements")
        if achievements_cog:
            await achievements_cog.record_autumn_action(
                interaction.user.id,
                f"{collection}_gathering",
                channel=interaction.channel,
            )
        outing = (
            "You wandered beneath the golden leaves and gathered a few autumn goodies."
            if collection == "autumn"
            else "You explored the harvest grounds and came back with a bounty for the feast."
        )
        embed=discord.Embed(title=f"{emoji} {name}",description=outing+"\n\n**You gathered:**\n"+"\n".join(rewards),color=discord.Color.orange())
        embed.set_footer(text=f"Attempts left: {attempts_left}/20 • 15-minute cooldown • Egg chance: 5% • Pet treat chance: 2%")
        await interaction.response.send_message(content=interaction.user.mention, embed=embed)

    async def open_kitchen(self, ctx, collection="autumn"):
        """Open this cog's recipe UI from the shared /seasonal crafting command."""
        if not self._active():
            await ctx.send("🍂 The Autumn Harvest Kitchen is dormant outside the Autumn event.")
            return
        if collection not in {"autumn", "thanksgiving"}:
            await ctx.send("That seasonal kitchen is not available.")
            return
        await ctx.send(
            embed=self._kitchen_embed(collection),
            view=KitchenView(self, ctx.author.id, collection),
        )

    def _recipes(self, collection):
        if collection == "autumn":
            return {**AUTUMN_RECIPES, **AUTUMN_PET_TREATS}
        return {**THANKSGIVING_RECIPES, **AUTUMN_PET_TREATS, **THANKSGIVING_PET_TREATS}

    def _kitchen_embed(self, collection):
        recipes = self._recipes(collection)
        title = "Seasonal Crafting Guide 🍂" if collection == "autumn" else "Seasonal Crafting Guide 🦃"
        return discord.Embed(
            title=title,
            description=(
                "*Prepare seasonal foods, drinks, and treats from gathered ingredients!*\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"**Known Recipes**\n{len(recipes)} recipes available.\n\n"
                "Food and drink crafting has a **10% seasonal egg chance**. Pet treat crafting does not roll for eggs.\n\n"
                "Choose an option below."
            ),
            color=discord.Color.orange(),
        )

    async def _owned(self, user_id):
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            async with db.execute(
                "SELECT item_id, quantity FROM inventory WHERE user_id=?", (user_id,)
            ) as cur:
                return {item_id: quantity for item_id, quantity in await cur.fetchall()}

    async def recipe_book_embeds(self, user_id, collection):
        owned = await self._owned(user_id)
        recipes = list(self._recipes(collection).items())
        pages = []
        for start in range(0, len(recipes), 3):
            sections = []
            for recipe_id, recipe in recipes[start:start + 3]:
                ingredients = recipe.get("ingredients", {})
                if recipe_id in AUTUMN_PET_TREAT_RECIPES:
                    ingredients = AUTUMN_PET_TREAT_RECIPES[recipe_id]
                lines = [f"{recipe.get('emoji', '🍽️')} **{recipe['name']}**"]
                for item_id, detail in ingredients.items():
                    quantity = detail["quantity"]
                    item_info = ITEM_REGISTRY.get(item_id, {})
                    name = item_info.get("name", item_id.replace("_", " ").title())
                    emoji = item_info.get("emoji", "🥣")
                    if detail.get("collection") == "pantry":
                        lines.append(f"✅ {emoji} {name} ×{quantity} *(pantry staple)*")
                        continue
                    have = owned.get(item_id, 0)
                    mark = "✅" if have >= quantity else "❌"
                    lines.append(f"{mark} {emoji} {name} ×{quantity} **(you have {have})**")
                lines.append(
                    f"📦 Currently owned: **{owned.get(recipe_id, 0)}x {recipe['name']}**"
                )
                sections.append("\n".join(lines))

            embed = discord.Embed(
                title="Seasonal Crafting Recipe Book 📖",
                description="\n\n──────────────\n\n".join(sections),
                color=discord.Color.orange(),
            )
            embed.set_footer(text=f"{start // 3 + 1}/{(len(recipes) + 2) // 3} • Pantry staples are always available")
            pages.append(embed)
        return pages

    async def materials_embed(self, user_id, collection):
        owned = await self._owned(user_id)
        ingredients = self._pool(collection)
        lines = []
        for item_id, info in ingredients.items():
            quantity = owned.get(item_id, 0)
            if quantity:
                lines.append(f"{info.get('emoji', '🥣')} **{info.get('name', item_id)}** ×{quantity}")
        title = "🍂 Autumn Materials" if collection == "autumn" else "🦃 Thanksgiving Materials"
        return discord.Embed(
            title=title,
            description="\n".join(lines) if lines else "You haven't gathered any seasonal ingredients yet.",
            color=discord.Color.orange(),
        )

    async def recipe_embed(self, user_id, recipe_id):
        recipe=AUTUMN_RECIPES.get(recipe_id) or THANKSGIVING_RECIPES.get(recipe_id) or AUTUMN_PET_TREATS.get(recipe_id) or THANKSGIVING_PET_TREATS.get(recipe_id)
        if not recipe: return None
        if recipe_id in AUTUMN_PET_TREAT_RECIPES:
            recipe = dict(recipe); recipe["ingredients"] = AUTUMN_PET_TREAT_RECIPES[recipe_id]
        lines=[]
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            for iid,detail in recipe.get("ingredients",{}).items():
                qty=detail["quantity"]
                item_info = ITEM_REGISTRY.get(iid, {})
                label=item_info.get("name",iid.replace('_',' ').title())
                emoji = item_info.get("emoji", "🥣")
                if detail.get("collection")=="pantry":
                    lines.append(f"✅ {emoji} {label} ×{qty} *(pantry staple)*")
                    continue
                async with db.execute("SELECT quantity FROM inventory WHERE user_id=? AND item_id=?",(user_id,iid)) as cur: row=await cur.fetchone()
                have=row[0] if row else 0
                mark = "✅" if have >= qty else "❌"
                lines.append(f"{mark} {emoji} {label} ×{qty} **(you have {have})**")
            async with db.execute(
                "SELECT quantity FROM inventory WHERE user_id=? AND item_id=?",
                (user_id, recipe_id),
            ) as cur:
                output_row = await cur.fetchone()
        output_owned = output_row[0] if output_row else 0
        lines.extend((
            "",
            f"📦 Currently owned: **{output_owned}x {recipe['name']}**",
            "",
            "Confirm to consume ingredients and cook.",
        ))
        return discord.Embed(title=f"{recipe.get('emoji','🍽️')} {recipe['name']}",description="\n".join(lines),color=discord.Color.orange())

    async def cook(self, interaction, recipe_id):
        if not self._active():
            return await interaction.response.edit_message(content="The Harvest Kitchen is closed.", embed=None, view=None)
        recipe=AUTUMN_RECIPES.get(recipe_id) or THANKSGIVING_RECIPES.get(recipe_id) or AUTUMN_PET_TREATS.get(recipe_id) or THANKSGIVING_PET_TREATS.get(recipe_id)
        if not recipe:
            return await interaction.response.edit_message(content="That recipe isn't available.", embed=None, view=None)
        if recipe_id in AUTUMN_PET_TREAT_RECIPES:
            recipe = dict(recipe); recipe["ingredients"] = AUTUMN_PET_TREAT_RECIPES[recipe_id]
        ingredients=recipe.get("ingredients",{})
        await interaction.response.defer()
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await db.execute("BEGIN IMMEDIATE")
            # Never consume ingredients if the finished item is already at its inventory cap.
            output_cap=ITEM_REGISTRY.get(recipe_id,{}).get("max_quantity",99)
            async with db.execute("SELECT quantity FROM inventory WHERE user_id=? AND item_id=?",(interaction.user.id,recipe_id)) as cur: output_row=await cur.fetchone()
            if output_row and output_row[0] >= output_cap:
                await db.rollback()
                return await interaction.edit_original_response(content=f"Your inventory is already at the cap for **{recipe['name']}**. Make room before cooking another.", embed=None, view=None)
            missing=[]
            for iid,detail in ingredients.items():
                if detail.get("collection")=="pantry": continue
                async with db.execute("SELECT quantity FROM inventory WHERE user_id=? AND item_id=?",(interaction.user.id,iid)) as cur: row=await cur.fetchone()
                if not row or row[0]<detail["quantity"]: missing.append(iid)
            if missing:
                await db.rollback()
                return await interaction.edit_original_response(content="You're missing: "+", ".join(ITEM_REGISTRY.get(x,{}).get("name",x) for x in missing), embed=None, view=None)
            for iid,detail in ingredients.items():
                if detail.get("collection")=="pantry": continue
                await db.execute("UPDATE inventory SET quantity=quantity-? WHERE user_id=? AND item_id=?",(detail["quantity"],interaction.user.id,iid))
            out_type=ITEM_REGISTRY.get(recipe_id,{}).get("type", "Pet Treat" if recipe_id in AUTUMN_PET_TREATS or recipe_id in THANKSGIVING_PET_TREATS else "Event Items")
            added,_,_=await add_inventory_item(db,interaction.user.id,recipe_id,out_type,1)
            first_food_discovery = False
            if added and (recipe_id in AUTUMN_RECIPES or recipe_id in THANKSGIVING_RECIPES):
                from collectibles import record_collectible
                collection_name = "Autumn Kitchen" if recipe_id in AUTUMN_RECIPES else "Thanksgiving Kitchen"
                first_food_discovery = await record_collectible(
                    db,
                    self.bot,
                    interaction.user.id,
                    recipe_id,
                    category=collection_name,
                    channel=interaction.channel,
                )
            effects=await get_active_pet_effects(db,interaction.user.id)
            extra=0
            bonus_ingredient = None
            if recipe.get("category")=="food" and recipe.get("sweet", False) and random.random()<effects.get("sweet_tooth",0): extra+=1
            if recipe.get("dessert", False) and random.random()<effects.get("sweet_rewards",0):
                eligible=[iid for iid,detail in ingredients.items() if detail.get("collection")!="pantry"]
                if eligible: bonus_ingredient=random.choice(eligible)
                if bonus_ingredient:
                    await add_inventory_item(db,interaction.user.id,bonus_ingredient,ITEM_REGISTRY.get(bonus_ingredient,{}).get("type","Event Items"),1)
            if recipe_id=="thanksgiving_tower_pizza":
                async with db.execute("SELECT pet_type FROM pets WHERE user_id=? AND pet_type IN ('peppino','peddito')",(interaction.user.id,)) as cur: owned={r[0] for r in await cur.fetchall()}
                if "peppino" not in owned:
                    await db.execute("INSERT INTO pets(user_id,pet_stage,pet_type,level,xp,is_active) VALUES(?, 'peppino','peppino',1,0,0)",(interaction.user.id,))
                    await db.execute("INSERT OR IGNORE INTO seasonal_pet_unlocks(user_id,pet_type,unlocked_at) VALUES(?,?,?)",(interaction.user.id,"peppino",time.time()))
                    special="Peppino joined your collection!"
                elif "peddito" not in owned and random.random()<0.10:
                    await db.execute("INSERT INTO pets(user_id,pet_stage,pet_type,level,xp,is_active) VALUES(?, 'peddito','peddito',1,0,0)",(interaction.user.id,))
                    await db.execute("INSERT OR IGNORE INTO seasonal_pet_unlocks(user_id,pet_type,unlocked_at) VALUES(?,?,?)",(interaction.user.id,"peddito",time.time()))
                    special="Peddito emerged from the pizza!"
                else: special=""
            else: special=""
            if extra: await add_inventory_item(db,interaction.user.id,recipe_id,out_type,extra)
            egg=None
            if recipe_id not in AUTUMN_PET_TREATS and recipe_id not in THANKSGIVING_PET_TREATS and random.random()<0.10:
                egg=random.choice(["harvest_egg","feast_egg"]) if recipe_id in THANKSGIVING_RECIPES else random.choice(list(AUTUMN_PET_POOLS))
                await add_inventory_item(db,interaction.user.id,egg,"Pet Egg",1)
            await db.commit()
        if recipe_id in AUTUMN_RECIPES or recipe_id in THANKSGIVING_RECIPES:
            collection = "autumn" if recipe_id in AUTUMN_RECIPES else "thanksgiving"
            achievements_cog = self.bot.get_cog("Achievements")
            if achievements_cog:
                await achievements_cog.record_autumn_action(
                    interaction.user.id,
                    f"{collection}_cooking",
                    channel=interaction.channel,
                )
        msg=f"You successfully prepared **{recipe['name']}**!"
        if first_food_discovery: msg+="\n📖 Added to your permanent Collectibles collection!"
        if extra: msg+=f"\n🍽️ Sweet Tooth produced **{extra}** extra serving(s)!"
        if bonus_ingredient: msg+=f"\n🦊 Sweet Rewards found an extra **{ITEM_REGISTRY.get(bonus_ingredient,{}).get('name',bonus_ingredient)}**!"
        if egg: msg+=f"\n🥚 You discovered a **{ITEM_REGISTRY.get(egg,{}).get('name',egg)}**!"
        if special: msg+=f"\n\n✨ {special}"
        await interaction.edit_original_response(content=msg, embed=None, view=None)

class KitchenView(discord.ui.View):
    def __init__(self, cog, owner_id, collection="autumn"):
        super().__init__(timeout=180)
        self.cog = cog
        self.owner_id = owner_id
        self.collection = collection

    async def interaction_check(self, interaction):
        return await _check_kitchen_interaction(interaction, self.owner_id, self.cog)

    @discord.ui.button(label="Recipes", style=discord.ButtonStyle.primary)
    async def recipes_button(self, interaction, button):
        pages = await self.cog.recipe_book_embeds(self.owner_id, self.collection)
        view = KitchenRecipeBookView(self.cog, self.owner_id, self.collection, pages)
        await interaction.response.edit_message(embed=pages[0], view=view)

    @discord.ui.button(label="Craft", style=discord.ButtonStyle.success)
    async def cook_button(self, interaction, button):
        view = KitchenSelectView(self.cog, self.owner_id, self.collection, self)
        embed = discord.Embed(
            title="Choose a seasonal recipe",
            description="Pick something delicious to prepare. You can review the ingredients before cooking.",
            color=discord.Color.orange(),
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Materials", style=discord.ButtonStyle.secondary)
    async def materials_button(self, interaction, button):
        embed = await self.cog.materials_embed(self.owner_id, self.collection)
        await interaction.response.edit_message(
            embed=embed,
            view=KitchenMaterialsView(self.cog, self.owner_id, self.collection),
        )


async def _check_kitchen_interaction(interaction, owner_id, cog):
    if interaction.user.id != owner_id:
        await interaction.response.send_message(
            "This seasonal kitchen belongs to another player.", ephemeral=True
        )
        return False
    if not cog._active():
        await interaction.response.send_message(
            "🍂 The Autumn event has ended; seasonal crafting is closed.", ephemeral=True
        )
        return False
    return True


class KitchenMaterialsView(discord.ui.View):
    def __init__(self, cog, owner_id, collection):
        super().__init__(timeout=300)
        self.cog = cog
        self.owner_id = owner_id
        self.collection = collection

    async def interaction_check(self, interaction):
        return await _check_kitchen_interaction(interaction, self.owner_id, self.cog)

    @discord.ui.button(label="◀ Back", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction, button):
        await interaction.response.edit_message(
            embed=self.cog._kitchen_embed(self.collection),
            view=KitchenView(self.cog, self.owner_id, self.collection),
        )


class KitchenRecipeBookView(discord.ui.View):
    def __init__(self, cog, owner_id, collection, pages, page=0):
        super().__init__(timeout=300)
        self.cog = cog
        self.owner_id = owner_id
        self.collection = collection
        self.pages = pages
        self.page = page
        self._update_buttons()

    def _update_buttons(self):
        self.previous_button.disabled = self.page <= 0
        self.next_button.disabled = self.page >= len(self.pages) - 1

    async def interaction_check(self, interaction):
        return await _check_kitchen_interaction(interaction, self.owner_id, self.cog)

    async def _show(self, interaction):
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.page], view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction, button):
        self.page -= 1
        await self._show(interaction)

    @discord.ui.button(label="Craft", style=discord.ButtonStyle.success)
    async def cook_button(self, interaction, button):
        view = KitchenSelectView(self.cog, self.owner_id, self.collection, self)
        embed = discord.Embed(
            title="Choose a seasonal recipe",
            description="Pick something delicious to prepare. You can review the ingredients before cooking.",
            color=discord.Color.orange(),
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction, button):
        self.page += 1
        await self._show(interaction)

    @discord.ui.button(label="◀ Back", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction, button):
        await interaction.response.edit_message(
            embed=self.cog._kitchen_embed(self.collection),
            view=KitchenView(self.cog, self.owner_id, self.collection),
        )


class KitchenSelectView(discord.ui.View):
    def __init__(self, cog, owner_id, collection, back_view):
        super().__init__(timeout=300)
        self.cog = cog
        self.owner_id = owner_id
        self.collection = collection
        self.back_view = back_view
        options = [
            discord.SelectOption(label=recipe["name"][:100], value=recipe_id, emoji=recipe.get("emoji"))
            for recipe_id, recipe in cog._recipes(collection).items()
        ][:25]
        self.add_item(RecipeSelect(cog, owner_id, options, collection, back_view))

    async def interaction_check(self, interaction):
        return await _check_kitchen_interaction(interaction, self.owner_id, self.cog)

    @discord.ui.button(label="◀ Back", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction, button):
        back_embed = (
            self.back_view.pages[self.back_view.page]
            if isinstance(self.back_view, KitchenRecipeBookView)
            else self.cog._kitchen_embed(self.collection)
        )
        await interaction.response.edit_message(
            embed=back_embed, view=self.back_view
        )


class RecipeSelect(discord.ui.Select):
    def __init__(self, cog, owner_id, options, collection, back_view):
        super().__init__(placeholder="Choose a recipe…", min_values=1, max_values=1, options=options)
        self.cog = cog
        self.owner_id = owner_id
        self.collection = collection
        self.back_view = back_view

    async def callback(self, interaction):
        recipe_id = self.values[0]
        embed = await self.cog.recipe_embed(self.owner_id, recipe_id)
        select_view = KitchenSelectView(
            self.cog, self.owner_id, self.collection, self.back_view
        )
        await interaction.response.edit_message(
            embed=embed,
            view=CookConfirmView(
                self.cog, self.owner_id, recipe_id, self.collection, select_view
            ),
        )


class CookConfirmView(discord.ui.View):
    def __init__(self, cog, owner_id, recipe_id, collection, return_view):
        super().__init__(timeout=120)
        self.cog = cog
        self.owner_id = owner_id
        self.recipe_id = recipe_id
        self.collection = collection
        self.return_view = return_view

    async def interaction_check(self, interaction):
        return await _check_kitchen_interaction(interaction, self.owner_id, self.cog)

    @discord.ui.button(label="Cook",style=discord.ButtonStyle.success,emoji="🍳")
    async def cook_button(self,interaction,button):
        await self.cog.cook(interaction,self.recipe_id)

    @discord.ui.button(label="Back",style=discord.ButtonStyle.secondary)
    async def cancel_button(self,interaction,button):
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="Choose a seasonal recipe",
                description="Pick something delicious to prepare. You can review the ingredients before cooking.",
                color=discord.Color.orange(),
            ),
            view=self.return_view,
        )

async def setup(bot): await bot.add_cog(HarvestKitchen(bot))
