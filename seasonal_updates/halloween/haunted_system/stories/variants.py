"""Alternate authored encounters for replay variety within existing locations."""

from ..story_helpers import choice


STORY_VARIANTS = {
    "abandoned_toy_workshop": {
        "scenes": {
            "dolls": [{
                "text": "The shelf is empty except for a child's drawing pinned to the wall. It shows the workshop, the portal, and a stick figure standing behind you. The paper is still damp.",
                "choices": [
                    choice("🖍️ Turn the drawing over", "drawing_back", "medium", "On the back, someone has written **WE PUT THE EYES IN LAST**. A small plastic eye rolls out from beneath the paper.", -5, next_scene="prototype_room", effects={"variant_toy_drawing": True}),
                    choice("🧸 Check the empty shelf", "empty_shelf", "high", "The shelf creaks under a weight you cannot see. A tiny voice asks whether you are ready to be boxed.", -7, next_scene="prototype_room", effects={"variant_toy_shelf": True}),
                ],
            }],
        },
        "reactions": {
            "prototype_room": [{"all": ["variant_toy_drawing"], "text": "The toy on the workbench has a fresh plastic eye. It turns toward the drawing in your pocket."}],
        },
    },
    "asylum": {
        "scenes": {
            "records": [{
                "text": "The records room is empty except for a filing cabinet drawer left open. Every folder inside is labeled with a different version of your name. One is warm to the touch.",
                "choices": [
                    choice("📁 Open the warm folder", "warm_folder", "high", "The folder contains a discharge form signed by you. The date is tomorrow. The signature is still being written.", -7, next_scene="ward", effects={"variant_asylum_folder": True}),
                    choice("🔒 Close the drawer", "close_drawer", "low", "The drawer shuts. From inside it, a call button begins to ring.", -3, next_scene="ward", effects={"variant_asylum_drawer": True}),
                ],
            }],
        },
        "reactions": {
            "ward": [{"all": ["variant_asylum_folder"], "text": "A nurse's station clipboard now lists your discharge as **in progress**."}],
        },
    },
    "broadcast_station": {
        "scenes": {
            "studio": [{
                "text": "The studio is empty, but a microphone is live. On the glass, someone has written a question backward: **WHO IS IN THE CONTROL ROOM?**",
                "choices": [
                    choice("🎙️ Answer the question", "answer_studio", "high", "Your voice comes through the speakers from a few seconds in the future. It says, **Don't turn around.**", -6, next_scene="archive", effects={"variant_broadcast_answer": True}),
                    choice("🔌 Pull the microphone cable", "pull_mic", "medium", "The cable comes free. The red recording light stays on, now reflected in every dark window.", -4, next_scene="archive", effects={"variant_broadcast_cable": True}),
                ],
            }],
        },
        "reactions": {
            "archive": [{"all": ["variant_broadcast_answer"], "text": "One reel in the archive is labeled with your voice and today's date. It is already playing."}],
        },
    },
    "church": {
        "scenes": {
            "confessional": [{
                "text": "The confessional is empty. A handwritten list of names is tucked into the screen. The final line has not been filled in, but the ink is uncapped.",
                "choices": [
                    choice("🖋️ Read the names aloud", "names_aloud", "high", "Each name is answered by a whisper from a different pew. The final whisper comes from inside your own mouth.", -6, next_scene="bell_tower", effects={"variant_church_names": True}),
                    choice("🧎 Leave the list untouched", "leave_list", "low", "The paper folds itself in half. A new name appears on the outside of the fold.", -3, next_scene="bell_tower", effects={"variant_church_list": True}),
                ],
            }],
        },
        "reactions": {
            "bell_tower": [{"all": ["variant_church_names"], "text": "The bell rope sways once. No bell rings, but every pew answers with a soft creak."}],
        },
    },
    "dead_end_highway": {
        "scenes": {
            "car": [{
                "text": "The abandoned car's headlights switch on. In their beam, the empty highway is crowded with footprints all walking toward the vehicle.",
                "choices": [
                    choice("🔑 Check the ignition", "check_ignition", "medium", "The keys are already turned. The radio announces the mile marker you have not reached yet.", -5, next_scene="motel", effects={"variant_highway_keys": True}),
                    choice("🪟 Look in the back seat", "back_seat", "high", "The back seat is empty until your reflection appears in the rear window, sitting very still.", -7, next_scene="motel", effects={"variant_highway_backseat": True}),
                ],
            }],
        },
        "reactions": {
            "motel": [{"all": ["variant_highway_keys"], "text": "The motel vacancy sign clicks from **NO** to **WELCOME BACK**."}],
        },
    },
    "derelict_research_facility": {
        "scenes": {
            "experiment": [{
                "text": "A glass observation window looks into a clean, empty room. The wall inside is covered in handprints, all pressed from the other side of the glass.",
                "choices": [
                    choice("🖐️ Place your hand against the glass", "hand_glass", "high", "A handprint appears beneath yours from the far side. Its fingers keep moving after you pull away.", -7, next_scene="containment", effects={"variant_research_hand": True}),
                    choice("📸 Photograph the room", "photo_room", "medium", "The photograph shows a figure standing in the room. The live window remains empty.", -4, next_scene="containment", effects={"variant_research_photo": True}),
                ],
            }],
        },
        "reactions": {
            "containment": [{"all": ["variant_research_hand"], "text": "A new handprint marks the containment door at shoulder height. It is wet on the inside."}],
        },
    },
    "dilapidated_pizzeria": {
        "scenes": {
            "birthday": [{
                "text": "The birthday room is empty. A party tape turns in the player, slowed until the cheerful song sounds like a message being dragged through water.",
                "choices": [
                    choice("⏹️ Stop the tape", "stop_tape", "medium", "The tape stops, but the song continues from the party room next door. Someone there applauds once.", -4, next_scene="stage_room", effects={"variant_pizzeria_tape": True}),
                    choice("🎂 Count the candles", "count_candles", "high", "There is one candle for every year you have been alive. The last one is already burned down to the table.", -7, next_scene="stage_room", effects={"variant_pizzeria_candles": True}),
                ],
            }],
        },
        "reactions": {
            "stage_room": [{"all": ["variant_pizzeria_tape"], "text": "The stage speaker crackles with the final note of the party song. It ends with a child's voice saying **Encore**."}],
        },
    },
    "drowned_station": {
        "scenes": {
            "train": [{
                "text": "The underwater train doors open onto a dry carriage. Rows of wet coats hang from the seats. Each one drips upward toward the ceiling.",
                "choices": [
                    choice("🚇 Step into the carriage", "enter_carriage", "high", "The doors close without a sound. Through the glass, the platform recedes while the train remains perfectly still.", -7, next_scene="announcement", effects={"variant_station_carriage": True}),
                    choice("🧥 Check a coat pocket", "coat_pocket", "medium", "You find a ticket stamped **ONE WAY**. The destination has been rubbed away, but the return time is listed as **never**.", -4, next_scene="announcement", effects={"variant_station_ticket": True}),
                ],
            }],
        },
        "reactions": {
            "announcement": [{"all": ["variant_station_carriage"], "text": "The station announcement welcomes you aboard by name. The train is still visible through the flooded tunnel."}],
        },
    },
    "endless_hotel": {
        "scenes": {
            "hallway": [{
                "text": "The carpeted hallway slopes gently upward. Every room door is open by exactly the same narrow gap. From each room comes the sound of someone unpacking.",
                "choices": [
                    choice("🧳 Look inside a room", "look_room", "high", "The room is your own, down to the luggage you have not packed yet. Something inside the wardrobe knocks politely.", -6, next_scene="guestbook", effects={"variant_hotel_room": True}),
                    choice("🛎️ Call for the front desk", "call_desk", "medium", "A bell rings somewhere far below. The hallway stretches longer, as if making room for the sound.", -4, next_scene="guestbook", effects={"variant_hotel_bell": True}),
                ],
            }],
        },
        "reactions": {
            "guestbook": [{"all": ["variant_hotel_room"], "text": "The guestbook has a new entry: **Room occupied. Guest already inside.**"}],
        },
    },
    "fogbound_town": {
        "scenes": {
            "figure": [{
                "text": "The figure beneath the streetlight is gone. A wet umbrella leans against the post. It is dripping upward, and its handle is still warm.",
                "choices": [
                    choice("☂️ Open the umbrella", "open_umbrella", "medium", "The fog parts in a perfect circle overhead. Above it is not a sky, but the ceiling of a room you recognize.", -5, next_scene="diner", effects={"variant_town_umbrella": True}),
                    choice("🔦 Search beneath the streetlight", "search_light", "high", "A second shadow stands beside yours. It points down the street, then slowly points at you.", -7, next_scene="diner", effects={"variant_town_shadow": True}),
                ],
            }],
        },
        "reactions": {
            "diner": [{"all": ["variant_town_umbrella"], "text": "The diner windows reflect rain falling inside the room, though the town outside is dry."}],
        },
    },
    "graveyard": {
        "scenes": {
            "path": [{
                "text": "A groundskeeper's shed stands between the graves. Its window glows warmly. Inside, a figure in a raincoat is carefully labeling empty jars with the names on the headstones.",
                "choices": [
                    choice("🫙 Read a jar label", "jar_label", "high", "One jar bears your name. Something taps against the glass from the inside, though the jar is empty.", -7, next_scene="chapel", effects={"variant_graveyard_jar": True}),
                    choice("🚪 Knock on the shed door", "shed_door", "medium", "The figure turns toward the door. A second later, the knock comes from beneath your feet.", -5, next_scene="chapel", effects={"variant_graveyard_knock": True}),
                ],
            }],
        },
        "reactions": {
            "chapel": [{"all": ["variant_graveyard_jar"], "text": "A row of empty jars sits beneath the chapel pews. One has your name written on the lid."}],
        },
    },
    "haunted_house": {
        "scenes": {
            "portrait": [{
                "text": "The family portrait is gone. In its place hangs a small mirror. It reflects the hall as it looked a moment ago, with one extra person standing behind you.",
                "choices": [
                    choice("🪞 Cover the mirror", "cover_mirror", "low", "The cloth settles over the glass. Something beneath it breathes in, then out.", -3, next_scene="upstairs", effects={"variant_house_cover": True}),
                    choice("👁️ Hold the reflection's gaze", "hold_gaze", "high", "The reflected figure smiles first. In the hallway, a door opens upstairs.", -7, next_scene="upstairs", effects={"variant_house_gaze": True}),
                ],
            }],
        },
        "reactions": {
            "upstairs": [{"all": ["variant_house_cover"], "text": "A pale rectangle on the wall marks where the portrait used to hang. The outline looks like a door."}],
        },
    },
    "silent_campground": {
        "scenes": {
            "photograph": [{
                "text": "The photograph shows an empty campsite in daylight. A second look reveals every tent occupied. A third reveals the picture was taken from inside your tent.",
                "choices": [
                    choice("📷 Check the date", "photo_date", "medium", "The date is tomorrow. A thumb partly covers the lens, and the nail polish is yours.", -5, next_scene="notebook", effects={"variant_camp_date": True}),
                    choice("🌲 Compare the tree line", "tree_line", "high", "The trees in the photograph lean inward. The real trees answer by shifting closer without making a sound.", -7, next_scene="notebook", effects={"variant_camp_trees": True}),
                ],
            }],
        },
        "reactions": {
            "notebook": [{"all": ["variant_camp_date"], "text": "A fresh page has appeared in the ranger's notebook. It describes you finding the photograph, in handwriting that matches yours."}],
        },
    },
    "witch_woods": {
        "scenes": {
            "circle": [{
                "text": "The clearing is empty except for a ring of mushrooms. Every cap is turned toward the center. A second ring is growing around your boots.",
                "choices": [
                    choice("🍄 Step outside the ring", "step_ring", "medium", "The mushrooms bend aside to let you pass. Their pale undersides are covered in tiny, closed eyes.", -5, next_scene="tracks", effects={"variant_woods_ring": True}),
                    choice("🕯️ Wait for the candles", "wait_candles", "high", "One candle appears in the empty circle. Then another. The final candle is already burning behind you.", -7, next_scene="tracks", effects={"variant_woods_candle": True}),
                ],
            }],
        },
        "reactions": {
            "tracks": [{"all": ["variant_woods_ring"], "text": "Tiny pale mushrooms grow in your footprints. They stop where the trail reaches the portal."}],
        },
    },
}
