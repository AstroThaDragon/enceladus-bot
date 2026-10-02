from ..story_helpers import choice, discovery_choice, pet_choice, scene, story

STORY = story(
    "church",
    "Abandoned Church",
    {
        "normal": "The portal opens in the nave of a church. The pews are covered in dust, but the candles at the altar are burning. The front door is locked from the inside.",
        "low": "The church is silent except for your breathing. You have the uneasy feeling that the building is listening for an answer.",
        "insane": "The church is full. Every pew is occupied by people with their heads bowed. Every face turns toward you at once.",
    },
    {
        "nave": scene("nave", "A prayer book rests open on the first pew. The page has been folded around a handwritten note: **WAIT FOR THE SECOND BELL**.", [
            choice("📖 Read the prayer", "read_prayer", "medium", "The prayer ends with a sentence that was not printed in the book: **'Do not answer if it calls you.'**", -4, next_scene="confessional", effects={"read_warning": True}),
            choice("🕯️ Light the candles", "light_candles", "low", "The flames straighten. The church feels briefly warmer.", 1, next_scene="confessional", effects={"lit_candles": True}),
            choice("🚪 Test the front door", "front_door", "medium", "The lock turns, but the door refuses to open.", -3, next_scene="confessional", effects={"tested_exit": True}),
        ]),
        "confessional": scene("confessional", "The confessional curtain moves gently even though the church has no wind. A voice from inside says, **'You already told me.'**", [
            discovery_choice("⛪ Enter the booth", "enter_booth", "high", "confessional", "The seat opposite you is warm. The voice knows a secret you have never spoken aloud.", -12, "bell_tower"),
            choice("🗣️ Ask what you told it", "ask_voice", "medium", "The voice answers with the name of someone you have never met.", -7, next_scene="bell_tower", effects={"heard_name": True}),
            choice("🚪 Walk away", "walk_away", "low", "The curtain opens behind you as you leave.", -2, next_scene="bell_tower", effects={"avoided_confessional": True}),
        ]),
        "bell_tower": scene("bell_tower", "The bell tower stairwell is narrow. A rope hangs from the ceiling. It has been cut cleanly in half.", [
            discovery_choice("🔔 Touch the bell rope", "bell", "high", "bell", "The church bell rings despite the cut rope. The sound comes from somewhere beside you as well as above you.", -11, "altar"),
            choice("👀 Look into the tower", "tower", "medium", "There is no bell above you. The ringing continues.", -6, next_scene="altar", effects={"saw_empty_tower": True}),
            choice("🏃 Return downstairs", "downstairs", "low", "The second bell rings while you are halfway down.", -3, next_scene="altar", effects={"heard_second_bell": True}),
        ]),
        "altar": scene("altar", "The altar is covered in old prayer cards. Every name has been crossed out except one.", [
            pet_choice("👻 Approach the figure at the altar — 🐾 Pet Discovery", "approach_figure", "medium", "A robed spirit stands at the altar. It never speaks. It simply watches you, then steps away from the candles.", -3, "prayer_book", effects={"met_forgotten": True}),
            choice("✝️ Kneel and wait", "kneel", "low", "For a moment, nothing happens. Then every candle bends toward the door.", 1, next_scene="prayer_book", effects={"knelt": True}),
            choice("🚶 Keep your distance", "distance", "medium", "The figure remains still. You can feel its attention follow you.", -4, next_scene="prayer_book", effects={"kept_distance": True}),
        ]),
        "prayer_book": scene("prayer_book", "An old prayer book lies beneath the altar. The cover is warm. The page beneath it has only one name left uncrossed.", [
            discovery_choice("📖 Read the remaining prayer", "prayer", "high", "prayer", "Every name has been crossed out except yours. Beneath it: **'Forgive them.'**", -14, "door"),
            choice("✝️ Close the book", "close_book", "medium", "A page turns itself behind your hand. You do not read it.", -5, next_scene="door", effects={"closed_prayer": True}),
            choice("🔥 Move it away from the altar", "move_book", "extreme", "The book becomes ice-cold. The candles go out one by one.", -10, next_scene="door", effects={"moved_prayer": True}),
        ]),
        "door": scene("door", "The front door is finally unlocked. Outside, there is no path—only the station corridor and the portal home.", [
            choice("🚪 Open the door", "open", "low", "The church releases you without protest.", 0, next_scene="ending"),
            choice("🔔 Wait for another bell", "wait", "high", "A bell rings once. The church door opens by itself.", -7, next_scene="ending", effects={"waited_for_bell": True}),
            choice("🕯️ Extinguish the altar candles", "extinguish", "medium", "The final flame dies. Somewhere inside the church, someone whispers, **'Thank you.'**", -4, next_scene="ending", effects={"extinguished": True}),
        ]),
        "ending": scene("ending", "The portal hums beyond the church door. Behind you, the building is dark again.", [
            choice("🌀 Return", "return", "low", "You step through. The last thing you hear is a soft bell, far away.", 0, end=True, ending_title="The Last Bell"),
            choice("🙏 Look back and bow", "bow", "low", "The empty church answers with a single creak from the pews.", 1, end=True, ending_title="A Quiet Benediction"),
            choice("🏃 Leave immediately", "run", "medium", "You do not wait to find out who said thank you.", -2, end=True, ending_title="No Second Bell"),
        ], reactions=[{"all": ["met_forgotten"], "text": "The Forgotten remains at the altar until the portal closes. It never speaks."}]),
    },
)
