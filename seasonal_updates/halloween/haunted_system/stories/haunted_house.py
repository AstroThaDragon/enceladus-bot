from ..story_helpers import choice, discovery_choice, pet_choice, scene, story

STORY = story(
    "haunted_house",
    "Haunted House",
    {
        "normal": "The portal opens inside a house that should not fit inside the station. Dust hangs in the foyer. Somewhere upstairs, something walks across a ceiling that has no floor above it.",
        "low": "The house feels less like a building and more like a memory you have forgotten. Every doorway looks slightly familiar.",
        "insane": "The house is your home. Everything is exactly where you left it. The front door is locked from the outside.",
    },
    {
        "foyer": scene("foyer", "The foyer contains three doors: a kitchen, a staircase, and a bedroom that you do not remember being there.", [
            choice("🍽️ Check the kitchen", "kitchen", "low", "The kitchen clock has stopped. Its hands point toward the bedroom door.", -1, next_scene="portrait", effects={"checked_kitchen": True}),
            choice("🪜 Take the stairs", "stairs", "medium", "A footstep answers yours from the ceiling.", -4, next_scene="portrait", effects={"heard_ceiling": True}),
            choice("🚪 Open the unfamiliar bedroom", "bedroom", "high", "The room is dark, but you recognize the smell of your own bedroom.", -7, next_scene="portrait", effects={"entered_unknown_room": True}),
        ]),
        "portrait": scene("portrait", "A crooked family portrait hangs in the hall. There are several people in it. You are not sure you recognize any of them.", [
            discovery_choice("🖼️ Study the portrait", "portrait", "high", "family_portrait", "An extra person stands in the family portrait. Every time you look away, they move closer to the edge of the frame.", -12, "upstairs"),
            choice("🪞 Check the hall mirror", "mirror", "medium", "The mirror shows the hallway from a slightly different angle. The house seems to have one more door in the reflection.", -5, next_scene="upstairs", effects={"saw_extra_door": True}),
            choice("🚪 Keep moving", "move", "low", "The portrait seems to follow you with its eyes.", -2, next_scene="upstairs", effects={"ignored_portrait": True}),
        ]),
        "upstairs": scene("upstairs", "There is no second floor on the house's exterior. Inside, the staircase leads to a hallway that stretches far beyond the roofline.", [
            discovery_choice("👣 Follow the footsteps", "footsteps", "high", "upstairs_footsteps", "Footsteps cross the ceiling above you even though the house has no second floor. One step lands beside you.", -11, "bedroom"),
            choice("🔦 Search for the source", "search", "medium", "You find a ceiling panel opening onto darkness. There is no room above it.", -6, next_scene="bedroom", effects={"found_ceiling_gap": True}),
            choice("🚪 Turn around", "turn_back", "low", "The stairs are still there. They lead somewhere you cannot see.", -3, next_scene="bedroom", effects={"retreated": True}),
        ]),
        "bedroom": scene("bedroom", "At the end of the hallway is a bedroom. The furniture is arranged exactly like yours, down to the smallest detail.", [
            pet_choice("🧸 Follow the tiny figure — 🐾 Pet Discovery", "follow_child", "medium", "A tiny ghost sits at the end of the hall holding out a hand. When you approach, it quietly decides you belong here too.", -3, "copy_room", effects={"met_resident": True}),
            choice("🛏️ Check the bed", "check_bed", "medium", "The blanket rises and falls. When you pull it back, there is nothing underneath.", -6, next_scene="copy_room", effects={"checked_bed": True}),
            choice("🚪 Close the bedroom door", "close_door", "low", "Something knocks from your side of the door after you close it.", -2, next_scene="copy_room", effects={"closed_door": True}),
        ]),
        "copy_room": scene("copy_room", "The bedroom contains a desk with a photograph on it. The photograph is facing down. The clock beside it runs one minute too fast.", [
            discovery_choice("📷 Turn over the photograph", "photo", "high", "bedroom_copy", "The photograph shows you sleeping in this room. When you blink, the person in the photograph is awake.", -15, "front_room"),
            choice("⏰ Watch the clock", "clock", "medium", "The clock catches up to real time. Somewhere downstairs, a clock begins running backward.", -5, next_scene="front_room", effects={"watched_clock": True}),
            choice("🚪 Leave the bedroom", "leave", "low", "You shut the door. The hallway outside is shorter than it was before.", -2, next_scene="front_room", effects={"left_copy": True}),
        ]),
        "front_room": scene("front_room", "The foyer is back exactly as you found it. The unfamiliar bedroom is gone. Only the front door remains.", [
            choice("🚪 Open the front door", "open", "low", "The door opens onto the station corridor. Behind you, the house settles into silence.", 0, next_scene="ending"),
            choice("🔑 Check the locks", "locks", "medium", "Every lock is already open. The deadbolt turns anyway when you touch it.", -5, next_scene="ending", effects={"checked_locks": True}),
            choice("👁️ Look through the peephole", "peephole", "high", "You see yourself standing on the other side of the door, waiting to be let in.", -9, next_scene="ending", effects={"saw_double": True}),
        ]),
        "ending": scene("ending", "You step toward the portal. The house remains behind you, quiet enough to pretend it never moved.", [
            choice("🌀 Leave", "leave", "low", "The portal closes. For a moment, your reflection smiles before you do.", 0, end=True, ending_title="House Left Behind"),
            choice("👋 Wave toward the hallway", "wave", "medium", "The tiny resident waves back from a room that no longer exists.", -2, end=True, ending_title="Someone Still Lives There"),
            choice("🚪 Shut the portal quickly", "shut", "high", "You close the portal before the house can decide which door to send next.", -7, end=True, ending_title="No Vacancy at Home"),
        ], reactions=[{"all": ["met_resident"], "text": "The little resident gives you one last annoyed look, as if you are the guest who keeps leaving without saying goodbye."}]),
    },
)
