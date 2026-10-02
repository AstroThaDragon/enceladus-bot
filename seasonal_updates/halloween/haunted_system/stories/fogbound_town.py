from ..story_helpers import choice, discovery_choice, pet_choice, scene, story

STORY = story(
    "fogbound_town",
    "Fogbound Town",
    {
        "normal": "The portal opens on an empty town street. Fog hides the ends of every road. A diner sign glows in the distance despite having no visible power.",
        "low": "The town feels occupied even though every window is dark. You hear doors close somewhere in the fog.",
        "insane": "The town is crowded. Nobody speaks. Everyone is looking toward the same house.",
    },
    {
        "street": scene("street", "Streetlights form a line through the fog. One flickers three times whenever you move.", [
            choice("💡 Follow the streetlights", "lights", "low", "The lights lead you toward the center of town.", 0, next_scene="figure", effects={"followed_lights": True}),
            choice("🌫️ Walk into the fog", "fog", "medium", "The town disappears behind you after three steps.", -5, next_scene="figure", effects={"entered_fog": True}),
            choice("🏠 Check a nearby house", "house", "medium", "The front door is open. Inside, a television is already playing.", -4, next_scene="figure", effects={"checked_house": True}),
        ]),
        "figure": scene("figure", "A figure stands beneath a streetlight. Every time the fog shifts, it is closer. It never seems to walk.", [
            discovery_choice("🌫️ Approach the figure", "figure", "high", "figure_in_fog", "The figure answers in your voice when you call to it. When you blink, it is standing behind you.", -12, "diner"),
            choice("👋 Call to it", "call", "medium", "It answers with your own voice, asking where you are going.", -7, next_scene="diner", effects={"spoke_to_figure": True}),
            choice("🏃 Walk away", "walk_away", "low", "The streetlight goes dark one block at a time behind you.", -2, next_scene="diner", effects={"avoided_figure": True}),
        ]),
        "diner": scene("diner", "A diner is freshly lit. Chairs pull themselves out from the tables as you approach. Food is still warm.", [
            discovery_choice("🍽️ Sit at the counter", "diner", "high", "diner_invitation", "The diner welcomes you as though you are expected. A receipt appears with your name already printed.", -10, "house_tv"),
            choice("☕ Inspect the food", "inspect_food", "medium", "The plate is empty except for a handwritten receipt bearing your name.", -5, next_scene="house_tv", effects={"found_receipt": True}),
            choice("🚪 Leave the diner", "leave_diner", "low", "The lights stay on behind you.", -1, next_scene="house_tv", effects={"left_diner": True}),
        ]),
        "house_tv": scene("house_tv", "The town's quietest house contains a television showing a few seconds of your current run ahead of time.", [
            pet_choice("🌫️ Follow the small shape beneath the streetlight — 🐾 Pet Discovery", "fogling", "low", "The fog gathers into a tiny creature with glowing eyes. It waddles over, dissolves around your feet, and reforms beside you.", -1, "television", effects={"met_fogling": True}),
            choice("📺 Keep watching", "watch_tv", "high", "Future-you stops and looks directly at the screen.", -8, next_scene="television", effects={"watched_future": True}),
            choice("🔌 Turn it off", "off_tv", "medium", "The screen goes black. Your reflection keeps moving for another second.", -5, next_scene="television", effects={"turned_off_tv": True}),
        ]),
        "television": scene("television", "The television turns itself back on. The screen shows the same street you entered from, but the fog is gone.", [
            discovery_choice("📺 Keep watching the screen", "future_tv", "high", "future_tv", "The screen shows your Haunted run several seconds ahead. Future-you stops and looks directly at you.", -13, "street_exit"),
            choice("📵 Unplug the television", "unplug", "medium", "The screen dies. The house becomes silent.", -4, next_scene="street_exit", effects={"unplugged_tv": True}),
            choice("🚪 Leave the house", "leave_house", "low", "You step back into the fog. The house door closes behind you.", -2, next_scene="street_exit", effects={"left_house": True}),
        ]),
        "street_exit": scene("street_exit", "The portal is visible at the end of the street. The fog is thinning around it.", [
            choice("🌀 Return", "return", "low", "You leave the town. The fog closes around the street behind you.", 0, next_scene="ending"),
            choice("🌫️ Wait for the fog to clear", "wait", "medium", "For one moment, the whole town becomes visible. Every window is occupied.", -7, next_scene="ending", effects={"saw_town": True}),
            choice("🏃 Run through the fog", "run", "high", "You run without looking back. Something small keeps pace beside you.", -5, next_scene="ending", effects={"ran_fog": True}),
        ]),
        "ending": scene("ending", "The portal closes behind you. The station corridor is refreshingly ordinary.", [
            choice("🌀 Finish the return", "finish", "low", "You are back. The town's last streetlight flickers once in your memory.", 0, end=True, ending_title="Fogbound"),
            choice("👋 Wave into the fog", "wave", "low", "A tiny shape waves back before the fog swallows the street.", 1, end=True, ending_title="A Little Light in the Fog"),
            choice("🏃 Do not wait", "leave", "medium", "You leave the portal behind before the town can show you another future.", -2, end=True, ending_title="Lost in the Fog"),
        ], reactions=[{"all": ["met_fogling"], "text": "Fogling dissolves into mist at the edge of the portal, then reforms on your side of it."}]),
    },
)
