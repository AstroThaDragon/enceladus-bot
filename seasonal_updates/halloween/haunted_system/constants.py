"""Static Haunted Exploration configuration.

This module contains data only. It intentionally has no database or Discord
imports so the story engine and reward system can depend on it safely.
"""

HAUNTED_DAILY_ATTEMPTS = 35
SANITY_MAX = 100
SANITY_REGEN_SECONDS = 6 * 60 * 60

HAUNTED_LOCATIONS = {'asylum': {'name': 'Abandoned Asylum',
            'emoji': '🏥',
            'description': 'A long-abandoned asylum drifting in the dark. The lights should not still be on.'},
 'graveyard': {'name': 'Forgotten Graveyard',
               'emoji': '🪦',
               'description': 'An impossible graveyard beneath a sky that does not belong to any known world.'},
 'haunted_house': {'name': 'Haunted House',
                   'emoji': '🏚️',
                   'description': "A house that somehow exists inside the station's abandoned sector."},
 'church': {'name': 'Abandoned Church',
            'emoji': '⛪',
            'description': 'A silent church with a door that appears to have been locked from the inside.'},
 'witch_woods': {'name': "Witch's Woods",
                 'emoji': '🌲',
                 'description': 'Twisted woods where the trees seem to move whenever you stop watching them.'},
 'dilapidated_pizzeria': {'name': 'Dilapidated Pizzeria',
                          'emoji': '🍕',
                          'description': 'A faded family restaurant with a silent stage, dead arcade cabinets, and a '
                                         'security office that still has power.'},
 'abandoned_toy_workshop': {'name': 'Abandoned Toy Workshop',
                            'emoji': '🧸',
                            'description': 'A brightly painted factory where the conveyor belts stopped long ago, but '
                                           'something keeps moving between the aisles.'},
 'broadcast_station': {'name': 'Abandoned Broadcast Station',
                       'emoji': '📡',
                       'description': 'Every monitor shows the same empty hallway, even though the cameras point in '
                                      'different directions.'},
 'endless_hotel': {'name': 'The Endless Hotel',
                   'emoji': '🏨',
                   'description': 'A hotel whose corridors repeat forever. Room numbers change whenever you look '
                                  'away.'},
 'fogbound_town': {'name': 'Fogbound Town',
                   'emoji': '🌫️',
                   'description': 'A deserted town swallowed by fog so thick that the streetlights barely reach the '
                                  'ground.'},
 'derelict_research_facility': {'name': 'Derelict Research Facility',
                                'emoji': '🧪',
                                'description': 'A sealed research complex where the emergency lights still work and '
                                               'the experiments clearly did not end cleanly.'},
 'yellow_halls': {'name': 'The Yellow Halls',
                  'emoji': '🟨',
                  'description': 'Yellow wallpaper, damp carpet, humming fluorescent lights, and corridors that refuse '
                                 'to stay the same length.'},
 'dead_end_highway': {'name': 'The Dead-End Highway',
                      'emoji': '🛣️',
                      'description': 'An endless road under a dead night sky. The signs promise exits that the highway '
                                     'never seems to reach.'},
 'drowned_station': {'name': 'The Drowned Station',
                     'emoji': '🌊',
                     'description': 'A forgotten underground station slowly filling with dark water. Something keeps '
                                    'moving beneath the surface.'},
 'silent_campground': {'name': 'The Silent Campground',
                       'emoji': '🌲',
                       'description': 'A dead-silent campground where radios fill with static, tall figures watch from '
                                      'the trees, and recordings remember things you never did.'}}

HAUNTED_INGREDIENT_POOLS = {'asylum': ['ectoplasm', 'medical_residue', 'bloodstained_gauze', 'cracked_syringe', 'spectral_thread'],
 'graveyard': ['grave_dust', 'bone_fragment', 'wilted_bloom', 'funeral_thread', 'grave_marker_shard'],
 'haunted_house': ['black_wax', 'cursed_fabric', 'broken_doll_piece', 'attic_mothwing', 'dusty_looking_glass'],
 'church': ['consecrated_salt', 'ritual_chalk', 'bell_fragment', 'incense_resin', 'cracked_holy_water_vial'],
 'witch_woods': ['witchroot', 'mooncap_mushroom', 'nightshade_berry', 'spider_lily', 'glowmoss'],
 'dilapidated_pizzeria': ['circuit_board',
                          'nuts_bolts',
                          'wiring',
                          'scrap_metal',
                          'glue',
                          'mechanical_parts',
                          'mascot_fabric',
                          'blackened_grease'],
 'abandoned_toy_workshop': ['nuts_bolts',
                            'wiring',
                            'glue',
                            'scrap_metal',
                            'stuffing',
                            'bent_toy_parts',
                            'faded_paint',
                            'plastic_eye'],
 'broadcast_station': ['circuit_board',
                       'wiring',
                       'nuts_bolts',
                       'radio_components',
                       'damaged_vhs_tape',
                       'burnt_capacitor',
                       'recorded_static'],
 'endless_hotel': ['scrap_metal',
                   'wiring',
                   'glue',
                   'bent_key',
                   'hotel_carpet_thread',
                   'old_guest_receipt',
                   'flickering_bulb',
                   'dusty_cleaning_rag'],
 'fogbound_town': ['grave_dust',
                   'scrap_metal',
                   'rusty_pipe',
                   'cracked_brick',
                   'condensed_fog',
                   'bent_key',
                   'flickering_bulb'],
 'derelict_research_facility': ['circuit_board',
                                'wiring',
                                'nuts_bolts',
                                'damaged_battery',
                                'chemical_sample',
                                'broken_lab_glass',
                                'contaminated_gloves',
                                'unknown_biological_residue'],
 'yellow_halls': ['yellow_wallpaper_scrap',
                  'damp_carpet_fiber',
                  'frayed_electrical_wire',
                  'unmarked_key',
                  'strange_fluorescent_tube',
                  'yellow_hall_light_cover'],
 'dead_end_highway': ['rusted_road_sign',
                      'damaged_payphone_part',
                      'old_road_map',
                      'contaminated_fuel_can',
                      'rusty_car_part',
                      'motel_key'],
 'drowned_station': ['waterlogged_transit_ticket',
                     'corroded_train_part',
                     'flooded_flashlight',
                     'damaged_conductor',
                     'contaminated_water_sample',
                     'submerged_key'],
 'silent_campground': ['static_damaged_radio',
                       'distorted_photograph',
                       'strange_notebook_page',
                       'corrupted_video_tape',
                       'damaged_antenna',
                       'blackened_tree_bark',
                       'unidentified_black_tendril']}

HAUNTED_INGREDIENT_OVERFLOW_VALUES = {'yellow_wallpaper_scrap': 100,
 'damp_carpet_fiber': 165,
 'frayed_electrical_wire': 45,
 'unmarked_key': 80,
 'strange_fluorescent_tube': 125,
 'yellow_hall_light_cover': 145,
 'rusted_road_sign': 100,
 'damaged_payphone_part': 75,
 'old_road_map': 45,
 'contaminated_fuel_can': 85,
 'rusty_car_part': 120,
 'motel_key': 50,
 'waterlogged_transit_ticket': 10,
 'corroded_train_part': 10,
 'flooded_flashlight': 95,
 'damaged_conductor': 75,
 'contaminated_water_sample': 55,
 'submerged_key': 25,
 'static_damaged_radio': 35,
 'distorted_photograph': 25,
 'strange_notebook_page': 20,
 'corrupted_video_tape': 20,
 'damaged_antenna': 45,
 'blackened_tree_bark': 40,
 'unidentified_black_tendril': 200}

HAUNTED_REWARD_RANGES = {'common': {'stardust': (150, 275), 'candy': (3, 6), 'ingredients': (1, 2)},
 'uncommon': {'stardust': (250, 425), 'candy': (5, 10), 'ingredients': (2, 3)},
 'rare': {'stardust': (400, 700), 'candy': (8, 14), 'ingredients': (2, 4)},
 'legendary': {'stardust': (700, 1200), 'candy': (14, 22), 'ingredients': (3, 5)},
 'void': {'stardust': (1200, 2000), 'candy': (25, 40), 'ingredients': (4, 7)}}

HAUNTED_COLLECTIBLE_CHANCES = {'common': 0.15, 'uncommon': 0.20, 'rare': 0.25, 'legendary': 0.35, 'void': 0.55}

HAUNTED_RARITY_WEIGHTS = {'common': 50, 'uncommon': 30, 'rare': 14, 'legendary': 5.6, 'void': 0.4}

HAUNTED_RARITY_LABELS = {'common': 'Common', 'uncommon': 'Uncommon', 'rare': 'Rare', 'legendary': 'Legendary', 'void': 'Void'}

HAUNTED_RARITY_EMOJIS = {'common': '⚪', 'uncommon': '🟢', 'rare': '🔵', 'legendary': '🟣', 'void': '⚫'}

HAUNTED_IMPOSSIBLE_DISCOVERIES = {'bedroom_copy',
 'black_water_cottage',
 'camera',
 'channel_zero',
 'confessional',
 'containment_chamber',
 'drowned_platform',
 'familiar_room',
 'family_portrait',
 'future_tv',
 'impossible_camera',
 'last_train',
 'malo_incident',
 'moving_photograph',
 'observation_window',
 'passenger',
 'prototype',
 'redacted_file',
 'security_tape',
 'wrong_hallway',
 'your_own_grave'}


# The story engine uses a fixed authored scene count. These values are deliberately
# separate from the legacy random stage-count logic so existing databases can be
# migrated without changing Sanity or attempt data.
HAUNTED_STORY_VERSION = 3
# A location pet is an occasional opportunity, not a guaranteed part of every run.
HAUNTED_LOCATION_PET_OPPORTUNITY_CHANCE = 0.35
DEFAULT_STORY_SCENES = 7

