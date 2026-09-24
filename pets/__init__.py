"""Pet package compatibility surface.

This package replaces the former monolithic ``pets.py`` module while keeping
its public imports available to the rest of Enceladus.
"""

from .config import (
    PET_PASSIVE_MAX_LEVEL, SPECIAL_PASSIVE_DEFINITIONS, PETS, HALLOWEEN_PETS,
    HAUNTED_PETS, ALL_PETS, EGG_POOLS,
    NORMAL_EXPLORATION_PET_XP_MIN, NORMAL_EXPLORATION_PET_XP_MAX,
    HAUNTED_EXPLORATION_PET_XP_MIN, HAUNTED_EXPLORATION_PET_XP_MAX,
    HAUNTED_HOME_PET_XP_BONUS, PET_TREAT_XP, HALLOWEEN_PET_CANDY_XP,
    NORMAL_EGG_CHANCE, HALLOWEEN_EGG_CHANCE, INCUBATION_SECONDS,
    INCUBATOR_NOTIFICATION_CHANNEL_ID,
)
from .core import (
    xp_needed_for_next_level, passive_level_for_pet, get_pet_definition,
    ensure_pet_variant_schema, get_haunted_pet_for_location,
    get_haunted_pet_discovery_message, grant_haunted_pet, get_passive_value,
    get_active_pet, get_active_pet_effects, roll_normal_exploration_pet_xp,
    roll_haunted_exploration_pet_xp, get_haunted_exploration_pet_xp, add_pet_xp,
)
from .views import (
    FeedTreatSelect, FeedTreatView, ReleaseConfirmationView, RenamePetModal,
    PetStatsView, PetManagementView, FusionVariantView, PostFusionConfirmView,
)
from .cog import Pets

async def setup(bot):
    await bot.add_cog(Pets(bot))

__all__ = [
    "PET_PASSIVE_MAX_LEVEL", "SPECIAL_PASSIVE_DEFINITIONS", "PETS",
    "HALLOWEEN_PETS", "HAUNTED_PETS", "ALL_PETS", "EGG_POOLS",
    "NORMAL_EXPLORATION_PET_XP_MIN", "NORMAL_EXPLORATION_PET_XP_MAX",
    "HAUNTED_EXPLORATION_PET_XP_MIN", "HAUNTED_EXPLORATION_PET_XP_MAX",
    "HAUNTED_HOME_PET_XP_BONUS", "PET_TREAT_XP", "HALLOWEEN_PET_CANDY_XP",
    "NORMAL_EGG_CHANCE", "HALLOWEEN_EGG_CHANCE", "INCUBATION_SECONDS",
    "INCUBATOR_NOTIFICATION_CHANNEL_ID", "xp_needed_for_next_level",
    "passive_level_for_pet", "get_pet_definition", "ensure_pet_variant_schema",
    "get_haunted_pet_for_location", "get_haunted_pet_discovery_message",
    "grant_haunted_pet", "get_passive_value", "get_active_pet",
    "get_active_pet_effects", "roll_normal_exploration_pet_xp",
    "roll_haunted_exploration_pet_xp", "get_haunted_exploration_pet_xp",
    "add_pet_xp", "FeedTreatSelect", "FeedTreatView",
    "ReleaseConfirmationView", "RenamePetModal", "PetStatsView",
    "PetManagementView", "FusionVariantView", "PostFusionConfirmView", "Pets",
    "setup",
]
