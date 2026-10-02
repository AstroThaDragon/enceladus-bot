from ..story_helpers import choice, discovery_choice, pet_choice, scene, story

STORY = story(
    "drowned_station",
    "The Drowned Station",
    {
        "normal": "The portal opens on a flooded underground platform. Water covers the tracks. A station announcement crackles through speakers that should be underwater.",
        "low": "The water is colder than it should be. Every ripple seems to move toward you rather than away from you.",
        "insane": "The station is dry. The ceiling is full of water. People walk upside down above you.",
    },
    {
        "platform": scene("platform", "A dead timetable still displays the next train. The arrival time reads **NOW**.", [
            choice("🚇 Watch the tracks", "tracks", "medium", "The water ripples as though a train is approaching beneath it.", -5, next_scene="train", effects={"watched_tracks": True}),
            choice("📋 Read the timetable", "timetable", "low", "Every departure is listed as **last train**.", -3, next_scene="train", effects={"read_timetable": True}),
            choice("🚪 Search for stairs", "stairs", "low", "You find a stairwell. The water rises while you look for the top.", -2, next_scene="train", effects={"found_stairs": True}),
        ]),
        "train": scene("train", "A train sits underwater without tracks. Its interior lights are still on.", [
            discovery_choice("🚇 Look through the windows", "last_train", "high", "last_train", "Every passenger slowly turns toward you. The train has no tracks, yet it is somehow waiting at the platform.", -13, "announcement"),
            choice("🚪 Approach the doors", "doors", "extreme", "The doors open before you touch them. Cold water pours outward instead of inward.", -10, next_scene="announcement", effects={"approached_train": True}),
            choice("🏃 Back away", "back", "low", "The train horn sounds beneath the water.", -3, next_scene="announcement", effects={"backed_from_train": True}),
        ]),
        "announcement": scene("announcement", "The station speakers crackle. A calm voice says: **PLEASE REMAIN ON THE PLATFORM. IT HAS ALREADY SEEN YOU.**", [
            discovery_choice("📢 Answer the announcement", "answer", "high", "station_announcement", "The speaker repeats your name. Another voice whispers from the water.", -10, "water"),
            choice("👂 Listen", "listen", "medium", "The announcement continues with directions to a platform number that does not exist.", -6, next_scene="water", effects={"listened_announcement": True}),
            choice("🏃 Leave the platform", "leave", "low", "The announcement follows you into the tunnel.", -2, next_scene="water", effects={"left_platform": True}),
        ]),
        "water": scene("water", "A current moves through the station even though there is no visible source. Wet footprints appear on the platform.", [
            pet_choice("🚂 Follow the train whistle — 🐾 Pet Discovery", "conductor", "medium", "A drowned conductor emerges from the dark water, checks an ancient watch, and gestures for you to follow.", -3, "footprints", effects={"met_conductor": True}),
            choice("🔦 Track the current", "current", "high", "The current stops beneath you. Something large moves below the surface.", -8, next_scene="footprints", effects={"tracked_current": True}),
            choice("🚶 Stay on the platform", "stay_platform", "low", "The water rises by another inch, but the platform remains stable.", -2, next_scene="footprints", effects={"stayed_platform": True}),
        ]),
        "footprints": scene("footprints", "Hundreds of wet footprints cover the platform. Every set leads out of the water. None lead back in.", [
            discovery_choice("👣 Follow the footprints", "drowned_platform", "high", "drowned_platform", "The footprints stop at your feet. Something beneath the water looks up.", -14, "last_stop"),
            choice("🌊 Look into the water", "water_look", "extreme", "Something beneath you looks up before you can look away.", -12, next_scene="last_stop", effects={"looked_water": True}),
            choice("🚪 Leave the platform", "leave_platform", "low", "Wet footprints appear behind you as you walk.", -3, next_scene="last_stop", effects={"left_footprints": True}),
        ]),
        "last_stop": scene("last_stop", "A final tunnel leads toward the portal. A train whistle sounds once behind you.", [
            choice("🚇 Follow the whistle", "whistle", "high", "You find the conductor's empty watch on a bench. The second hand is moving backward.", -7, next_scene="ending", effects={"followed_whistle": True}),
            choice("🌀 Follow the portal", "portal", "low", "You move toward the portal without looking back.", 0, next_scene="ending", effects={"followed_portal": True}),
            choice("🌊 Wait for the water to settle", "wait", "medium", "The water becomes perfectly still. A train arrives without making a sound.", -8, next_scene="ending", effects={"waited_water": True}),
        ]),
        "ending": scene("ending", "The portal closes behind you. For a moment, you can still hear a train beneath the station floor.", [
            choice("🌀 Return", "return", "low", "You leave the drowned station behind.", 0, end=True, ending_title="Mind the Water"),
            choice("👋 Wave toward the tracks", "wave", "low", "A distant train light blinks once beneath the floor.", 1, end=True, ending_title="Last Stop"),
            choice("🏃 Run", "run", "high", "The station announcement calls your name one final time.", -7, end=True, ending_title="Please Remain on the Platform"),
        ], reactions=[{"all": ["met_conductor"], "text": "The Drowned Conductor remains near the portal until you leave, still holding the same impossible timetable."}]),
    },
    shortcut_scene="last_stop",
)
