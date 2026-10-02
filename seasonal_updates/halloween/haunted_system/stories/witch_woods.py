from ..story_helpers import choice, discovery_choice, pet_choice, scene, story

STORY = story(
    "witch_woods",
    "Witch's Woods",
    {
        "normal": "The portal opens beneath a canopy of twisted trees. Lanterns hang between branches with no ropes holding them. The forest is too quiet.",
        "low": "The woods seem to breathe when you stop. Every tree looks slightly different when you look back at it.",
        "insane": "The forest is full of flowers. Every flower has an eye in the center, and every eye follows you.",
    },
    {
        "trail": scene("trail", "A trail of lanterns winds into the woods. None has a flame, yet every one glows softly.", [
            choice("🏮 Follow the lanterns", "follow_lanterns", "medium", "The lanterns lead you deeper, always staying just out of reach.", -5, next_scene="circle", effects={"followed_lanterns": True}),
            choice("🔦 Inspect one", "inspect_lantern", "low", "Inside the lantern is a tiny moth made of pale light. It flies away when you touch the glass.", 1, next_scene="circle", effects={"saw_moth": True}),
            choice("🌲 Leave the trail", "leave_trail", "low", "You stay among the trees. Somewhere ahead, something starts humming.", -2, next_scene="circle", effects={"avoided_lanterns": True}),
        ]),
        "circle": scene("circle", "You reach a clearing. Twelve candles surround it. One has your name scratched into the wax.", [
            discovery_choice("🕯️ Step into the circle", "candle_circle", "high", "candle_circle", "Twelve candles surround the clearing. One bears your name. When you enter, the woods go silent.", -12, "tracks"),
            choice("🔥 Extinguish the named candle", "extinguish", "medium", "The other eleven flames lean toward you as the named candle goes dark.", -6, next_scene="tracks", effects={"extinguished_candle": True}),
            choice("🚶 Leave the clearing", "leave_circle", "low", "You back away. One candle follows you with its flame.", -2, next_scene="tracks", effects={"left_circle": True}),
        ]),
        "tracks": scene("tracks", "Mud appears beneath your boots even though the ground was dry. Enormous footprints form behind you.", [
            discovery_choice("👣 Follow the footprints", "giant_tracks", "high", "giant_footprints", "The enormous footprints appear behind you whenever you stop, then suddenly appear ahead of you too.", -11, "cottage"),
            choice("🛑 Stop moving", "stop", "medium", "The forest becomes silent. Something exhales behind you.", -7, next_scene="cottage", effects={"stopped_for_tracks": True}),
            choice("🏃 Run", "run", "high", "The footprints keep pace without getting closer.", -9, next_scene="cottage", effects={"ran_from_tracks": True}),
        ]),
        "cottage": scene("cottage", "A crooked cottage appears between two trees. Beside it is a pool of black water. Something watches from the window.", [
            pet_choice("🐈 Follow the soft meow — 🐾 Pet Discovery", "follow_meow", "low", "A ghostly cat walks directly through a tree, then looks back at you as if you are the strange one.", -1, "black_water", effects={"met_cat": True}),
            choice("🏚️ Approach the cottage", "approach", "medium", "The door opens before you touch it. Inside is completely dark.", -6, next_scene="black_water", effects={"approached_cottage": True}),
            choice("🌲 Stay among the trees", "stay_trees", "low", "You refuse the cottage. The light inside turns on anyway.", -2, next_scene="black_water", effects={"avoided_cottage": True}),
        ]),
        "black_water": scene("black_water", "The black pool is perfectly still. Your reflection stands a little farther away than you do.", [
            discovery_choice("🌊 Look into the water", "black_water", "high", "black_water_cottage", "The reflection shows the cottage from outside—with you standing inside it. It blinks before you do.", -14, "heartwood"),
            choice("🪨 Throw a stone", "stone", "medium", "The stone hits the surface and sinks without making a ripple.", -5, next_scene="heartwood", effects={"disturbed_water": True}),
            choice("🚶 Walk away", "away", "low", "The cottage light turns on behind you.", -2, next_scene="heartwood", effects={"left_water": True}),
        ]),
        "heartwood": scene("heartwood", "A massive tree stands ahead, its trunk covered in old carvings. The path home is visible through its roots.", [
            choice("🪵 Read the carvings", "carvings", "medium", "The carvings describe travelers who entered the woods and returned with companions.", -4, next_scene="ending", effects={"read_carvings": True}),
            choice("🌿 Touch the roots", "roots", "low", "The roots are warm. The forest's constant tension eases for a heartbeat.", 2, next_scene="ending", effects={"touched_roots": True}),
            choice("🌀 Head for the portal", "portal", "low", "You keep moving until the familiar portal light appears.", 0, next_scene="ending", effects={"ignored_woods": True}),
        ]),
        "ending": scene("ending", "The portal waits between the trees. The woods do not try to stop you. That may be the most unsettling part.", [
            choice("🌀 Leave", "leave", "low", "You return to the station. Somewhere behind you, a cat meows once.", 0, end=True, ending_title="The Woods Let You Go"),
            choice("👁️ Look into the trees", "look", "high", "For a second, dozens of eyes reflect the portal light. Then the trees are ordinary again.", -8, end=True, ending_title="The Forest Was Watching"),
            choice("🌲 Leave a lantern behind", "lantern", "low", "You place a small light at the edge of the path. The woods accept it without a sound.", 1, end=True, ending_title="A Light in the Woods"),
        ], reactions=[{"all": ["met_cat"], "text": "The ghostly cat sits beside the portal and watches you leave, entirely unbothered by the impossible forest."}]),
    },
)
