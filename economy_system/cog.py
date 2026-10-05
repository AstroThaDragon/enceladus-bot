import asyncio
import aiosqlite
import datetime
import json
import random
import re
import time
from datetime import datetime, timedelta, time as dt_time
from typing import Any, Optional, cast

import discord
from discord import app_commands
from discord.ext import commands, tasks
import pytz

from emojis import EMOJIS
from seasonal_updates.halloween.halloween import is_active as halloween_is_active
from seasonal_updates.halloween.halloween import HALLOWEEN_SPACE_JUNK, get_sell_reward as get_halloween_sell_reward
from seasonal_updates.halloween.halloween import get_collectibles as get_halloween_collectibles
from inventory import ITEM_REGISTRY
from collectibles import LOCATION_BASED_COLLECTIBLES
from pets.core import get_pet_definition
from error_handler import log_task_error

from .data import *

from .database import EconomyDatabaseMixin
from .daily import EconomyDailyMixin
from .bank import EconomyBankMixin
from .giving import EconomyGivingMixin
from .shop.catalog import EconomyShopCatalogMixin
from .shop.autocomplete import EconomyShopAutocompleteMixin
from .shop.buying import EconomyShopBuyingMixin
from .shop.selling import EconomyShopSellingMixin
from .salvage.autocomplete import EconomySalvageAutocompleteMixin
from .salvage.system import EconomySalvageMixin
from .lookup import EconomyLookupMixin


class Economy(
    EconomyDatabaseMixin,
    EconomyDailyMixin,
    EconomyBankMixin,
    EconomyGivingMixin,
    EconomyShopCatalogMixin,
    EconomyShopAutocompleteMixin,
    EconomyShopBuyingMixin,
    EconomyShopSellingMixin,
    EconomySalvageAutocompleteMixin,
    EconomySalvageMixin,
    EconomyLookupMixin,
    commands.Cog,
):
    def __init__(self, bot):
        self.bot = bot
        self.DEFAULT_VAULT_CAPACITY = 250_000
        self.MAX_VAULT_CAPACITY = 1_000_000
        self._give_locks = {}
        self.SHOP_ITEMS = SHOP_ITEMS
        self.JUNK_PRICES = JUNK_PRICES
        self.ROTATING_ITEMS = ROTATING_ITEMS
        self.SHOP_LIMITS = SHOP_LIMITS


async def setup(bot):
    await bot.add_cog(Economy(bot))
