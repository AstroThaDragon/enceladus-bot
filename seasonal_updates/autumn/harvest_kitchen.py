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
        title = "🍂 Autumn Harvest Kitchen" if collection == "autumn" else "🦃 Thanksgiving Kitchen"
        embed = self._kitchen_embed()
        embed.title = title
        await ctx.send(embed=embed, view=KitchenView(self, ctx.author.id, collection=collection))

    def _kitchen_embed(self):
        return discord.Embed(title="🍁 Harvest Kitchen",description="Choose a recipe to prepare. Ingredients are consumed only when you confirm cooking. Butter, salt, sugar, and eggs are pantry staples and never need to be collected.\n\nSuccessful cooking has a **10% seasonal egg chance**. Treat crafting does not roll for eggs.",color=discord.Color.orange())

    async def recipe_embed(self, user_id, recipe_id):
        recipe=AUTUMN_RECIPES.get(recipe_id) or THANKSGIVING_RECIPES.get(recipe_id) or AUTUMN_PET_TREATS.get(recipe_id) or THANKSGIVING_PET_TREATS.get(recipe_id)
        if not recipe: return None
        if recipe_id in AUTUMN_PET_TREAT_RECIPES:
            recipe = dict(recipe); recipe["ingredients"] = AUTUMN_PET_TREAT_RECIPES[recipe_id]
        lines=[]
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            for iid,detail in recipe.get("ingredients",{}).items():
                qty=detail["quantity"]; label=ITEM_REGISTRY.get(iid,{}).get("name",iid.replace('_',' ').title())
                if detail.get("collection")=="pantry": lines.append(f"• {label} ×{qty} *(pantry staple)*"); continue
                async with db.execute("SELECT quantity FROM inventory WHERE user_id=? AND item_id=?",(user_id,iid)) as cur: row=await cur.fetchone()
                have=row[0] if row else 0; lines.append(f"• {label}: **{have}/{qty}**")
        return discord.Embed(title=f"{recipe.get('emoji','🍽️')} {recipe['name']}",description="\n".join(lines)+"\n\nConfirm to consume ingredients and cook.",color=discord.Color.orange())

    async def cook(self, interaction, recipe_id):
        if not self._active(): return await interaction.response.send_message("The Harvest Kitchen is closed.",ephemeral=True)
        recipe=AUTUMN_RECIPES.get(recipe_id) or THANKSGIVING_RECIPES.get(recipe_id) or AUTUMN_PET_TREATS.get(recipe_id) or THANKSGIVING_PET_TREATS.get(recipe_id)
        if not recipe: return await interaction.response.send_message("That recipe isn't available.",ephemeral=True)
        if recipe_id in AUTUMN_PET_TREAT_RECIPES:
            recipe = dict(recipe); recipe["ingredients"] = AUTUMN_PET_TREAT_RECIPES[recipe_id]
        ingredients=recipe.get("ingredients",{})
        async with aiosqlite.connect(ECONOMY_DB_NAME) as db:
            await db.execute("BEGIN IMMEDIATE")
            # Never consume ingredients if the finished item is already at its inventory cap.
            output_cap=ITEM_REGISTRY.get(recipe_id,{}).get("max_quantity",99)
            async with db.execute("SELECT quantity FROM inventory WHERE user_id=? AND item_id=?",(interaction.user.id,recipe_id)) as cur: output_row=await cur.fetchone()
            if output_row and output_row[0] >= output_cap:
                return await interaction.response.send_message(f"Your inventory is already at the cap for **{recipe['name']}**. Make room before cooking another.",ephemeral=True)
            missing=[]
            for iid,detail in ingredients.items():
                if detail.get("collection")=="pantry": continue
                async with db.execute("SELECT quantity FROM inventory WHERE user_id=? AND item_id=?",(interaction.user.id,iid)) as cur: row=await cur.fetchone()
                if not row or row[0]<detail["quantity"]: missing.append(iid)
            if missing:
                return await interaction.response.send_message("You're missing: "+", ".join(ITEM_REGISTRY.get(x,{}).get("name",x) for x in missing),ephemeral=True)
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
        await interaction.response.send_message(msg,ephemeral=True)

class KitchenView(discord.ui.View):
    def __init__(self, cog, owner_id, collection="thanksgiving"):
        super().__init__(timeout=180)
        self.cog = cog
        self.owner_id = owner_id
        self.collection = collection
        if collection == "autumn":
            recipes = {**AUTUMN_RECIPES, **AUTUMN_PET_TREATS}
        else:
            recipes = {**THANKSGIVING_RECIPES, **AUTUMN_PET_TREATS, **THANKSGIVING_PET_TREATS}
        options = [
            discord.SelectOption(label=v["name"][:100], value=k, emoji=v.get("emoji"))
            for k, v in recipes.items()
        ][:25]
        self.add_item(RecipeSelect(cog, owner_id, options))

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("This kitchen menu belongs to another player.", ephemeral=True)
            return False
        if not self.cog._active():
            await interaction.response.send_message("🍂 The Autumn event has ended; the Harvest Kitchen is closed.", ephemeral=True)
            return False
        return True

class RecipeSelect(discord.ui.Select):
    def __init__(self,cog,owner_id,options):
        super().__init__(placeholder="Choose a recipe…",min_values=1,max_values=1,options=options); self.cog=cog; self.owner_id=owner_id
    async def callback(self,interaction):
        recipe_id=self.values[0]; embed=await self.cog.recipe_embed(self.owner_id,recipe_id)
        await interaction.response.send_message(embed=embed,view=CookConfirmView(self.cog,self.owner_id,recipe_id),ephemeral=True)

class CookConfirmView(discord.ui.View):
    def __init__(self,cog,owner_id,recipe_id):
        super().__init__(timeout=120); self.cog=cog; self.owner_id=owner_id; self.recipe_id=recipe_id
    @discord.ui.button(label="Cook",style=discord.ButtonStyle.success,emoji="🍳")
    async def cook_button(self,interaction,button):
        if interaction.user.id!=self.owner_id: return await interaction.response.send_message("This recipe isn't yours.",ephemeral=True)
        await self.cog.cook(interaction,self.recipe_id)
    @discord.ui.button(label="Cancel",style=discord.ButtonStyle.secondary)
    async def cancel_button(self,interaction,button): await interaction.response.edit_message(content="Cooking cancelled. No ingredients were used.",embed=None,view=None)

async def setup(bot): await bot.add_cog(HarvestKitchen(bot))
