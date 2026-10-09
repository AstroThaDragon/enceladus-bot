"""Authored Haunted location stories."""

from .asylum import STORY as ASYLUM_STORY
from .graveyard import STORY as GRAVEYARD_STORY
from .haunted_house import STORY as HAUNTED_HOUSE_STORY
from .church import STORY as CHURCH_STORY
from .witch_woods import STORY as WITCH_WOODS_STORY
from .dilapidated_pizzeria import STORY as PIZZERIA_STORY
from .abandoned_toy_workshop import STORY as TOY_WORKSHOP_STORY
from .broadcast_station import STORY as BROADCAST_STORY
from .endless_hotel import STORY as HOTEL_STORY
from .fogbound_town import STORY as FOGBOUND_STORY
from .derelict_research_facility import STORY as RESEARCH_STORY
from .yellow_halls import STORY as YELLOW_HALLS_STORY
from .dead_end_highway import STORY as HIGHWAY_STORY
from .drowned_station import STORY as DROWNED_STATION_STORY
from .silent_campground import STORY as CAMPGROUND_STORY

STORIES = {
    "asylum": ASYLUM_STORY,
    "graveyard": GRAVEYARD_STORY,
    "haunted_house": HAUNTED_HOUSE_STORY,
    "church": CHURCH_STORY,
    "witch_woods": WITCH_WOODS_STORY,
    "dilapidated_pizzeria": PIZZERIA_STORY,
    "abandoned_toy_workshop": TOY_WORKSHOP_STORY,
    "broadcast_station": BROADCAST_STORY,
    "endless_hotel": HOTEL_STORY,
    "fogbound_town": FOGBOUND_STORY,
    "derelict_research_facility": RESEARCH_STORY,
    "yellow_halls": YELLOW_HALLS_STORY,
    "dead_end_highway": HIGHWAY_STORY,
    "drowned_station": DROWNED_STATION_STORY,
    "silent_campground": CAMPGROUND_STORY,
}

from .variants import STORY_VARIANTS
from .alternate_routes import apply_alternate_routes

for _location_id, _variant_data in STORY_VARIANTS.items():
    STORIES[_location_id]["scene_variants"] = _variant_data.get("scenes", {})
    STORIES[_location_id]["scene_reactions"] = _variant_data.get("reactions", {})

apply_alternate_routes(STORIES)


def get_story(location_id):
    return STORIES.get(location_id)
