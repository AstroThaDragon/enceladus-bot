from ..story_helpers import choice, discovery_choice, pet_choice, scene, story

STORY = story(
    "abandoned_toy_workshop",
    "Abandoned Toy Workshop",
    {
        "normal": "The portal opens beside a dead conveyor belt. Brightly painted walls surround rows of silent machines. Somewhere in the factory, a toy laughs once.",
        "low": "The workshop looks cheerful in a way that feels deeply wrong. The toys seem to notice whenever you look at them.",
        "insane": "Every toy is smiling. Every toy has your eyes.",
    },
    {
        "factory_floor": scene("factory_floor", "A factory speaker crackles: **ASSEMBLY COMPLETE. ONE GUEST REMAINS.** The conveyor begins moving again.", [
            choice("📢 Ask who the guest is", "ask_speaker", "medium", "The speaker answers, **'You are still being assembled.'**", -6, next_scene="dolls", effects={"answered_speaker": True}),
            choice("🔌 Shut off the conveyor", "stop_line", "low", "The belt stops. The toys on it keep moving their eyes.", -3, next_scene="dolls", effects={"stopped_line": True}),
            choice("🚶 Walk between the machines", "walk_machines", "medium", "Tiny footsteps keep pace with you from inside the machinery.", -5, next_scene="dolls", effects={"heard_footsteps": True}),
        ]),
        "dolls": scene("dolls", "A row of dolls sits on a shelf. They whisper the same sentence over and over: **Which one are you?**", [
            discovery_choice("🧸 Count the dolls", "dolls", "high", "assembly_line", "Every toy on the conveyor resembles you. The newest one is still warm.", -11, "prototype_room"),
            choice("👁️ Ask them a question", "ask_dolls", "medium", "The dolls stop whispering. One answers, **'We are waiting for the last part.'**", -5, next_scene="prototype_room", effects={"spoke_to_dolls": True}),
            choice("🚪 Leave them alone", "leave_dolls", "low", "You walk away. The whispering follows you through the factory.", -2, next_scene="prototype_room", effects={"ignored_dolls": True}),
        ]),
        "prototype_room": scene("prototype_room", "A workbench holds a single toy labeled **DO NOT ACTIVATE**. Its eyes open when you read the label.", [
            discovery_choice("🔘 Press the button", "prototype", "extreme", "prototype", "The toy says your name in your own voice. Its serial number matches a date that should mean nothing to it.", -15, "warehouse"),
            choice("🧸 Inspect it without touching", "inspect_toy", "medium", "Its serial number is your birth date. You decide you have seen enough.", -7, next_scene="warehouse", effects={"inspected_prototype": True}),
            choice("🚪 Leave the workbench", "leave_workbench", "low", "Tiny footsteps begin following you as you walk away.", -3, next_scene="warehouse", effects={"left_prototype": True}),
        ]),
        "warehouse": scene("warehouse", "The warehouse is packed with boxes. One moves slightly. Then another. Something small waves from between the stacks.", [
            pet_choice("🧸 Follow the long arm — 🐾 Pet Discovery", "longarms", "medium", "A large blue toy creature steps from between the machines and enthusiastically waves with one absurdly long arm.", -3, "music_box", effects={"met_longarms": True}),
            choice("📦 Open the moving box", "open_box", "high", "The box contains dozens of identical toys, all facing the lid.", -8, next_scene="music_box", effects={"opened_box": True}),
            choice("🚶 Walk around it", "walk_around", "low", "The movement stops as you pass. You hear cardboard creak behind you.", -2, next_scene="music_box", effects={"ignored_box": True}),
        ]),
        "music_box": scene("music_box", "A music box plays a melody of someone humming. The humming sounds exactly like your voice.", [
            discovery_choice("🎵 Wind the music box", "music_box", "medium", "music_box", "The melody begins again. For a moment, the humming sounds like it is coming from inside your chest.", -8, "loading_dock"),
            choice("🔇 Close the lid", "close_box", "low", "The music stops. A tiny mechanical voice says **thank you** from inside.", -2, next_scene="loading_dock", effects={"closed_music_box": True}),
            choice("👂 Listen closely", "listen_box", "high", "The melody contains a rhythm matching your footsteps.", -7, next_scene="loading_dock", effects={"listened_music": True}),
        ]),
        "loading_dock": scene("loading_dock", "The loading dock is open to darkness outside. The factory speaker announces **GUEST DEPARTURE IN PROGRESS**.", [
            choice("🚪 Leave", "leave", "low", "The factory lights turn off behind you one row at a time.", 0, next_scene="ending"),
            choice("📢 Ask who is leaving", "ask_departure", "medium", "The speaker answers, **'Not you.'** Then it shuts off.", -6, next_scene="ending", effects={"asked_departure": True}),
            choice("👀 Look back at the factory", "look_back", "high", "Every toy is standing in the loading dock now.", -9, next_scene="ending", effects={"saw_toys": True}),
        ]),
        "ending": scene("ending", "The portal is waiting in the dark beyond the loading dock. The workshop remains brightly lit behind you.", [
            choice("🌀 Return", "return", "low", "You leave the workshop. The last thing you hear is a tiny laugh.", 0, end=True, ending_title="Playtime Is Over"),
            choice("👋 Wave back", "wave", "low", "A dozen tiny hands wave from the windows.", 1, end=True, ending_title="Goodbye, Workshop"),
            choice("🏃 Run", "run", "high", "The factory speaker follows you with one final announcement: **ASSEMBLY COMPLETE.**", -8, end=True, ending_title="Assembly Complete"),
        ], reactions=[{"all": ["met_longarms"], "text": "Longarms cheerfully follows you to the portal, as though this were the most normal field trip imaginable."}]),
    },
)
