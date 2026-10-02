from ..story_helpers import choice, discovery_choice, pet_choice, scene, story

STORY = story(
    "graveyard",
    "Forgotten Graveyard",
    {
        "normal": "The portal opens onto wet grass beneath a sky with no stars. Rows of graves disappear into the fog. Somewhere nearby, a shovel hits stone.",
        "low": "The graveyard looks familiar in the way a nightmare can feel familiar. The graves seem to rearrange themselves whenever you stop counting.",
        "insane": "The graveyard is bright daylight. Every grave is open. Every empty coffin has your name carved inside.",
    },
    {
        "gate": scene("gate", "The cemetery gate stands open. A crooked sign says **VISITORS MUST BE ACCOUNTED FOR**. There is nobody to account for you.", [
            choice("🔢 Count the rows", "count_rows", "medium", "You count until the rows stop matching the number of paths.", -4, next_scene="path", effects={"counted_rows": True}),
            choice("🕯️ Light a nearby lantern", "light_lantern", "low", "The lantern burns with a steady flame that makes the fog retreat by a few feet.", 1, next_scene="path", effects={"lit_lantern": True}),
            choice("🚪 Leave the gate behind", "leave_gate", "medium", "The gate closes behind you without a sound.", -3, next_scene="path", effects={"closed_gate": True}),
        ]),
        "path": scene("path", "A muddy path forks around a cluster of fresh graves. One grave has flowers. Another has a shovel. A third has no headstone at all.", [
            discovery_choice("🪦 Examine the fresh grave", "own_grave", "high", "your_own_grave", "A fresh grave bears your name. The death date is empty, and the soil beside it is still damp.", -12, "chapel"),
            choice("🌼 Follow the flowers", "flowers", "low", "The flowers lead to an old memorial wall covered in names. One name has been scratched away.", -2, next_scene="chapel", effects={"followed_flowers": True}),
            choice("🪓 Take the shovel", "take_shovel", "medium", "The shovel is warm despite the cold. You leave it where you found it after hearing a knock underground.", -5, next_scene="chapel", effects={"heard_knock": True}),
        ]),
        "chapel": scene("chapel", "A ruined caretaker's chapel sits between the graves. Its door is open. Inside, a ledger records every burial—but one entry is still being written.", [
            discovery_choice("👂 Listen beside the sealed grave", "breathing_grave", "extreme", "grave_that_breathes", "Slow breathing comes from beneath a sealed grave. It stops when you hold your breath.", -16, "deep_graves"),
            choice("📖 Read the caretaker ledger", "read_ledger", "medium", "The final completed entry says: **'If the count changes, do not correct it.'**", -5, next_scene="deep_graves", effects={"read_ledger": True}),
            choice("🔔 Ring the chapel bell", "ring_bell", "high", "The bell rings once. Every grave outside answers with a soft knock.", -9, next_scene="deep_graves", effects={"rang_bell": True}),
        ]),
        "deep_graves": scene("deep_graves", "The fog thickens around the oldest section. Something rustles beneath freshly turned soil. A small hand rises, then disappears again.", [
            pet_choice("🖐️ Kneel beside the disturbed earth — 🐾 Pet Discovery", "find_ghoul", "medium", "A little graveyard ghoul crawls from the soil, looks at you, and gives an awkward wave.", -2, "extra_grave", effects={"met_ghoul": True}),
            choice("🪦 Mark the disturbed grave", "mark_grave", "low", "You place a stone beside it. The ground settles.", 1, next_scene="extra_grave", effects={"marked_grave": True}),
            choice("🏃 Back away", "back_away", "medium", "The rustling stops. You hear footsteps moving between the graves instead.", -4, next_scene="extra_grave", effects={"backed_away": True}),
        ]),
        "extra_grave": scene("extra_grave", "You return to the main path. You are certain there were three graves here before. Now there are four.", [
            discovery_choice("🔢 Count them again", "extra_grave", "medium", "extra_grave", "There is one more grave than there was a moment ago. Its headstone is blank.", -8, "last_path"),
            choice("🧭 Follow the lantern light", "follow_light", "low", "The lantern leads you toward the cemetery gate. The fog is finally thinning.", 1, next_scene="last_path", effects={"followed_lantern": True}),
            choice("🚶 Ignore the new grave", "ignore_grave", "medium", "You refuse to look at the extra grave. The path seems to lengthen in response.", -5, next_scene="last_path", effects={"ignored_grave": True}),
        ]),
        "last_path": scene("last_path", "The cemetery gate is visible again. The path behind you is now empty. No footprints. No shovel marks. Nothing.", [
            choice("🚪 Head for the gate", "gate", "low", "The gate opens before you touch it. The normal station corridor beyond feels impossibly bright.", 0, next_scene="ending", effects={"left_quietly": True}),
            choice("🕯️ Leave the lantern burning", "lantern", "low", "You leave the small light behind. The fog gathers around it instead of swallowing it.", 1, next_scene="ending", effects={"left_lantern": True}),
            choice("👀 Look back", "look_back", "high", "Every grave is occupied now. You do not remember seeing anyone arrive.", -9, next_scene="ending", effects={"saw_occupied_graves": True}),
        ]),
        "ending": scene("ending", "The portal waits beyond the gate. The graveyard is quiet again, but the quiet no longer feels empty.", [
            choice("🌀 Step through", "return", "low", "You return to the station with mud on your boots and a strong feeling that the cemetery counted you among the living.", 0, end=True, ending_title="Counted Among the Living"),
            choice("🪦 Touch your name if it remains", "touch_name", "high", "The stone is warm. For one second, the fog says your name back to you.", -7, end=True, ending_title="The Grave Remembers"),
            choice("🏃 Do not look back", "dont_look_back", "low", "You leave without giving the cemetery another chance to add something to the count.", 1, end=True, ending_title="Don't Add to the Count"),
        ], reactions=[{"all": ["met_ghoul"], "text": "The little ghoul follows you to the gate, then sits down and watches the portal close."}]),
    },
)
