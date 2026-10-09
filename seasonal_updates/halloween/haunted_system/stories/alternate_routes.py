"""One complete alternate episode for every Haunted location.

Each episode reuses the location's authored scene slots so existing stage
shortcuts, pet encounters, and persisted run routing continue to work.
"""

import copy

from ..story_helpers import choice


# Each beat corresponds to one scene in the location's scene_order. These are
# separate through-lines, not randomized sentence substitutions: each has a
# new mystery, escalating clues, and a distinct resolution.
EPISODES = {
    "abandoned_toy_workshop": (
        "The Returned Toy",
        "A parcel sits outside the workshop door with your name on it. From inside the box comes the slow, careful sound of someone knocking to be let out.",
        [
            "The conveyor is carrying a single wrapped parcel against the direction of the belt. Its shipping label lists the factory as both sender and destination.",
            "A row of toys has been arranged like an audience. Every painted face is turned toward an empty chair beneath a paper sign that reads **THE GUEST**.",
            "The workbench holds a half-finished toy with a stitched mouth. Its instruction sheet says the final part must be supplied by whoever opens the box.",
            "A warehouse aisle ends at a stack of parcels, all addressed to you. One is open. Inside is a smaller box, and inside that, a faint knock.",
            "A music box plays the sound of tape being peeled from cardboard. The melody stops whenever you look directly at it.",
            "At the loading dock, the outbound parcels are moving on their own. The top box is addressed to your home and marked **RETURN TO SENDER**.",
            "The portal waits beside the sealed parcel. From within it comes one final knock, answered by a knock from the other side of the portal.",
        ],
    ),
    "asylum": (
        "The Night Roster",
        "A shift roster is pinned to the asylum entrance. Every name is crossed out except yours, written beneath **NIGHT STAFF** in fresh ink.",
        [
            "The reception desk holds a ringing telephone and a roster for tonight's staff. Your name is listed twice: once as orderly, once as patient.",
            "The records room contains a neat stack of incident reports describing the same empty corridor from different dates. Each report ends before the same sound.",
            "A treatment room has been prepared for a patient who has not arrived. The restraints are fastened around the chair from the inside.",
            "A hospital bed rolls slowly down the ward. Its blanket rises and falls, but the mattress is visibly empty.",
            "An attendance ledger records every staff member as present. The final signature is still forming, letter by letter, while you watch.",
            "The night supervisor's office is locked. A light moves behind its frosted glass, stopping whenever you approach the door.",
            "The front doors open onto the station. Behind you, the roster's final line changes from **ON DUTY** to **STILL HERE**.",
        ],
    ),
    "broadcast_station": (
        "The Last Listener",
        "A red ON AIR light glows above the station door. A voice from the speaker welcomes you by name, then asks you to stay on the line.",
        [
            "The control board is tuned to a frequency that should not exist. A handwritten note beside it says **DO NOT ACKNOWLEDGE THE CALLER**.",
            "The recording studio's microphone is live. In the glass, your reflection is speaking several seconds before you do.",
            "The archive shelves are filled with recordings of empty rooms. One reel contains the sound of a chair being pulled up beside the microphone.",
            "Every monitor shows the same caller, seated in a dark room. The figure raises a hand each time you consider leaving.",
            "The emergency broadcast repeats a calm instruction: **Remain where you are. Someone is coming to collect you.**",
            "At the transmitter, the destination display scrolls through station names, then settles on the name of the room you are standing in.",
            "The portal appears in the studio glass. The voice on the broadcast says goodbye from the room behind your reflection.",
        ],
    ),
    "church": (
        "The Unanswered Service",
        "The church bell rings once as the portal opens. Inside, every pew is occupied by a motionless congregation facing the wrong way.",
        [
            "A service program lies at the entrance. It lists a hymn, a sermon, and a closing prayer. Beside each item is the same time: **NOW**.",
            "The confessional is occupied. A voice inside asks you to name the person who has been standing behind you since you arrived.",
            "The bell tower rope sways gently. Dust on the floor shows footprints climbing the stairs, but none coming back down.",
            "The altar candles burn with dark flames. Their shadows point toward the church door, though the candles face the altar.",
            "A prayer book has been opened to a page of blank lines. One line fills itself whenever the bell rings.",
            "The front door is unlatched. Through its glass, the congregation is now standing in the aisle, still facing away from you.",
            "The portal waits outside. The bell rings again after you cross the threshold, followed by a quiet rustle of everyone sitting down.",
        ],
    ),
    "dead_end_highway": (
        "The Detour",
        "Orange roadwork lights blink beyond the portal. A sign warns **DETOUR — EXPECT DELAYS**. The road behind it is already closed.",
        [
            "A map at the roadside shows a detour route in thick red ink. It loops around the highway and ends at the exact spot where you began.",
            "An idling car has a roadwork vest folded on the passenger seat. The radio reports a crew member missing from the next mile marker.",
            "The motel office is lit. A clipboard lists the detour crew as checked in, though every room key hangs on its hook.",
            "A temporary sign points toward a bridge that is absent from the map. Beneath it, tire tracks descend into the dark shoulder.",
            "The mile marker has been moved. Its post is freshly dug, and a second marker lies face down in the dirt beside it.",
            "A payphone rings with a recorded traffic update. It warns of a closure behind you, then thanks you for your patience.",
            "The portal opens at the end of the detour. The roadwork lights blink out in order, one by one, from the far end toward you.",
        ],
    ),
    "derelict_research_facility": (
        "The Observation Protocol",
        "A placard by the portal says **OBSERVATION IN PROGRESS**. The viewing window is dark, but something on the other side has already taken a seat.",
        [
            "The intake terminal asks you to confirm that you are alone. The occupancy light turns red before you touch the keyboard.",
            "An experiment log describes a subject that appears only when nobody is observing. The last page is covered in notes written from both sides.",
            "The containment chamber is empty except for a chair facing the observation glass. The restraints are open and arranged neatly on the seat.",
            "An archive cabinet contains footage of this facility from tomorrow. In every recording, the camera slowly turns toward its operator.",
            "A terminal displays a new test result: **OBSERVER DETECTED INSIDE THE TEST ENVIRONMENT**. The progress bar is still moving.",
            "The exit corridor's cameras all show an empty hall. Their timestamps are current, but one feed shows you approaching from behind.",
            "The portal is visible through the observation glass. A silhouette on the far side raises a clipboard and checks your name off.",
        ],
    ),
    "dilapidated_pizzeria": (
        "The Birthday Recording",
        "A party-room door stands open beyond the portal. A paper crown rests on the floor, still warm, with **GUEST OF HONOR** written inside.",
        [
            "The dining room is set for a birthday party. The plates are dusty except for one place setting with a fresh slice of cake.",
            "A birthday tape starts by itself. The children singing grow quieter with each verse until only one voice remains.",
            "The stage curtains are closed. Behind them, the animatronics whisper the same birthday wish in a voice too small for their speakers.",
            "The security monitors show the party room from every angle. In one feed, the empty chair at the table is slowly turning toward the camera.",
            "A cassette labeled **AFTER THE PARTY** is already in the player. It contains applause, then the sound of someone being asked to stay.",
            "The exit sign points toward the dining room. A trail of cake crumbs leads the opposite way and stops at the portal.",
            "The portal closes behind you with a soft click. Somewhere in the pizzeria, a party horn gives one tired, lonely toot.",
        ],
    ),
    "drowned_station": (
        "The Missing Passenger",
        "The station platform is ankle-deep in still water. A departure board lists one passenger as **NOT YET ARRIVED**. The name is yours.",
        [
            "The platform clock counts backward. Under it, a lost-property notice asks whoever found the missing passenger to report to the last stop.",
            "A train waits with its doors open. Every seat is dry except one, where water drips upward from the cushion.",
            "The announcement system calls a passenger by name. The sound comes from beneath the platform instead of from the speakers.",
            "A service tunnel is flooded to the ceiling. On the far wall, a wet handprint appears above the waterline and slides along it.",
            "A trail of footprints crosses the platform and ends at a bench. The seat is wet, but the water around it is perfectly still.",
            "The last-stop sign lists no destination. Someone has scratched **YOU WERE HERE** into its metal frame.",
            "The portal opens beside the platform stairs. The departure board changes to **PASSENGER ACCOUNTED FOR** as you leave.",
        ],
    ),
    "endless_hotel": (
        "The Checkout That Never Was",
        "A brass key lies on the threshold. Its tag reads **CHECK OUT: YESTERDAY**. The hotel lobby clock has stopped just before midnight.",
        [
            "The front desk holds a guest register open to your name. The checkout column is blank, though the room key has been returned.",
            "The hallway carpet bears two sets of footprints: one leading to your room, the other leaving it before you arrived.",
            "The guestbook contains a review describing the hotel as quiet, clean, and impossible to leave. It is signed in your handwriting.",
            "The elevator indicator descends below the basement. A voice inside asks whether you have remembered to bring your luggage.",
            "The stairwell returns to the same landing. Someone has left a fresh room-service tray there, with a note: **WE MISSED YOU**.",
            "The lobby exit is chained from the outside. A bellhop's cart rolls up with one suitcase, damp from rain that never fell inside.",
            "The portal stands where the revolving door should be. Behind you, the desk clerk turns a page and marks the room vacant.",
        ],
    ),
    "fogbound_town": (
        "The Town That Knows Your Route",
        "A street map is posted beyond the portal. A dotted line marks your route through town, including the turns you have not taken yet.",
        [
            "The street is empty, but each traffic light turns green just before you reach it. A pedestrian signal counts down from a number above one hundred.",
            "A figure waits beneath a streetlamp holding a folded map. Its face is hidden, but the route drawn on the paper matches yours exactly.",
            "The diner serves a cup of coffee with your name written on the receipt. The waitress says you ordered it on your way back.",
            "A house television shows a live image of the street outside. In the broadcast, someone is standing at the window behind you.",
            "The television weather report predicts fog at the exact moment you leave. The forecast shows a map with your position marked in red.",
            "The town exit sign points toward home. Its arrow slowly rotates as you watch, settling on the road you just walked.",
            "The portal opens at the edge of town. A traffic light behind you turns green, and a distant engine begins to approach.",
        ],
    ),
    "graveyard": (
        "The Groundskeeper's Count",
        "A groundskeeper's ledger lies open beside the gate. It says the cemetery contains one more visitor than it did a moment ago.",
        [
            "The gate latch is wrapped in a strip of fresh black cloth. A small note says **PLEASE KEEP COUNT** in careful handwriting.",
            "The path passes a row of graves with matching dates. One headstone has a fresh mark where the name has been carefully removed.",
            "The chapel ledger records each grave in neat columns. The final column is titled **STILL WALKING** and has one entry.",
            "A mound of fresh earth settles with a sigh. Nearby, the caretaker's lantern casts a shadow shaped like someone holding a shovel.",
            "A new grave has appeared beside the path. Its stone is blank, but a small bouquet has been placed with the stems facing down.",
            "The gate is visible again. The groundskeeper's footprints lead out of the cemetery, then double back into the fog.",
            "You cross the threshold. In the ledger, the visitor count decreases by one, then immediately increases by one again.",
        ],
    ),
    "haunted_house": (
        "The House's Open House",
        "A real-estate flyer is pinned to the front door. It advertises the house as vacant, though one upstairs window is watching the portal.",
        [
            "The foyer contains a model of the house. A tiny light moves from room to room inside it, matching your route through the real building.",
            "A portrait has been replaced by a property listing. The listed owner is unknown; the listed occupant is **CURRENT GUEST**.",
            "The upstairs hall is staged for a viewing. Every door is open, and each room contains the same chair facing the doorway.",
            "The bedroom is furnished with a perfectly ordinary bed. Beneath it, a second set of floorboards creaks as if someone is getting up.",
            "A copy of the house's keys hangs on the wall. One key is still turning in a lock somewhere behind the wallpaper.",
            "The foyer door opens onto the living room instead of outside. A welcome mat has appeared with your name stitched into it.",
            "The portal waits beyond the front door. The flyer flutters in the draft and changes its status from **VACANT** to **UNDER CONTRACT**.",
        ],
    ),
    "silent_campground": (
        "The Ranger's Check-In",
        "A ranger station sign asks visitors to check in before entering. The logbook already contains your arrival time and a note: **DO NOT ANSWER THE SECOND CALL**.",
        [
            "The campsite is perfectly arranged for a group of hikers. Their boots are lined up by the fire, still wet, but no one is in the tents.",
            "A trail photograph shows the campground from high above. A small figure in the image is pointing toward the ranger station.",
            "The ranger's notebook lists a nightly headcount. Every name is crossed off except one, followed by the word **LISTENING**.",
            "The forest falls silent. From somewhere between the trees, a radio check asks each hiker to confirm they are safe.",
            "The trail camera records an empty path. Its latest image shows the ranger station from inside the room you are standing in.",
            "A path marker points back toward the campsite. The reverse side has been scratched with the words **YOU MISSED ONE**.",
            "The portal opens beyond the campground gate. The ranger radio gives one final check-in; a voice answers from inside your pack.",
        ],
    ),
    "witch_woods": (
        "The Lantern Procession",
        "A line of unlit lanterns hangs from the trees. As the portal opens, every lantern ignites at once and points deeper into the woods.",
        [
            "The trail is marked with little bundles of dried herbs. Each one is tied with a knot that tightens when you look away.",
            "A clearing contains a circle of lanterns and an empty place among them. The grass in that place is warm.",
            "Footprints cross the mud toward the woods, then continue across the trunks of the trees overhead.",
            "A cottage window glows. Inside, a kettle whistles while the room remains empty and the teacups slowly fill themselves.",
            "The black pool reflects a procession of lanterns moving through the trees. None of the lights are visible above the water.",
            "The heartwood is carved with a map of the forest. A fresh line is being drawn from the tree to the portal.",
            "The portal waits at the edge of the path. Behind you, the lantern procession turns around and begins following at a walking pace.",
        ],
    ),
    "yellow_halls": (
        "The Office's Closing Shift",
        "A laminated sign on the office door reads **PLEASE MAKE SURE ALL STAFF HAVE LEFT**. Somewhere inside, a desk phone begins to ring.",
        [
            "The entrance corridor is arranged like a workplace after closing. Chairs are tucked in, monitors are dark, and one desk lamp is still warm.",
            "A plain office door bears a nameplate with your initials. The room number is smudged, as if someone tried to remove it in a hurry.",
            "The cubicle loop contains a half-finished staff checklist. The last item reads **COUNT THE PEOPLE BEFORE LOCKING UP**.",
            "The break room coffee machine is still running. A paper cup beside it has your name on the side and a lipstick mark on the rim.",
            "A familiar office appears at the end of the hall. Every monitor shows the same empty corridor from a different desk.",
            "The exit sign points to the front lobby. Beneath it, a desk phone rings from inside a wall with no doorway.",
            "The portal opens beyond the office. The fluorescent lights switch off one by one, stopping at the room you just left.",
        ],
    ),
}


_ACTION_PAIRS = [
    ("🔎 Inspect the clue", "🚪 Leave it alone"),
    ("📞 Answer the sound", "🤫 Keep silent"),
    ("🧭 Follow the marker", "↩️ Take the other way"),
    ("🖐️ Touch the object", "🧤 Keep your distance"),
    ("📄 Read what it says", "🗑️ Turn it over"),
    ("👁️ Look behind you", "🏃 Keep moving"),
    ("🌀 Head for the portal", "⏳ Wait a moment"),
]

_LOCATION_ACTIONS = {
    "abandoned_toy_workshop": [("📦 Check the label", "🔔 Knock on the box"), ("🪑 Inspect the guest seat", "🧸 Address the toys"), ("🧵 Search the seams", "🚪 Step away"), ("📬 Open a parcel", "🛑 Stop the conveyor"), ("🎼 Follow the melody", "🔇 Silence the music box"), ("🚚 Read the dispatch sheet", "🧱 Block the loading belt"), ("📦 Open the parcel", "🌀 Take the portal")],
    "asylum": [("📞 Answer the desk phone", "📋 Check the roster"), ("🗃️ Compare the reports", "🔒 Close the cabinet"), ("🪑 Inspect the restraints", "🚪 Leave the treatment room"), ("🛏️ Follow the rolling bed", "🔦 Check the empty ward"), ("🖊️ Read the new signature", "📕 Shut the ledger"), ("🪟 Look through the glass", "🔑 Try the office key"), ("🚪 Leave the building", "👁️ Check the roster again")],
    "broadcast_station": [("🎛️ Tune the frequency", "📻 Turn down the speaker"), ("🎙️ Speak into the mic", "🔴 Switch off the light"), ("📼 Play the reel", "📦 Shelve the recording"), ("🖥️ Follow the caller", "🔌 Disconnect the monitors"), ("📢 Repeat the warning", "🔕 Mute the broadcast"), ("📡 Change the destination", "🛠️ Shut down the transmitter"), ("🎙️ Enter the studio", "🌀 Follow the reflection")],
    "church": [("📜 Read the service program", "🕯️ Light a candle"), ("🚪 Draw the curtain", "🙏 Ask the voice a question"), ("🔔 Climb the tower", "🪢 Hold the rope still"), ("🕯️ Extinguish a flame", "📖 Read the altar cards"), ("📖 Turn the blank page", "✍️ Write a name"), ("🔑 Test the front door", "🪟 Look through the glass"), ("🚪 Cross the threshold", "🔔 Wait for the bell")],
    "dead_end_highway": [("🗺️ Trace the detour", "🚧 Check the closure"), ("🚘 Inspect the car", "📻 Turn on the radio"), ("🛎️ Ring the motel bell", "🗝️ Take a room key"), ("🪧 Follow the sign", "🛞 Examine the tracks"), ("📏 Read the mile marker", "⛏️ Check the disturbed soil"), ("☎️ Lift the receiver", "📞 Let it ring"), ("🚗 Follow the headlights", "🌀 Take the portal")],
    "derelict_research_facility": [("⌨️ Confirm the occupancy", "🔴 Pull the alarm"), ("📑 Read the experiment log", "📹 Review the footage"), ("🪑 Inspect the empty chair", "🔒 Seal the chamber"), ("📼 Play tomorrow's recording", "🗄️ Close the archive"), ("🧪 Read the test result", "🛑 Stop the experiment"), ("📹 Check the rear camera", "🚪 Try the exit"), ("📋 Sign the clipboard", "🌀 Enter the portal")],
    "dilapidated_pizzeria": [("🎂 Check the place setting", "🥄 Taste the cake"), ("📼 Rewind the birthday tape", "🔌 Unplug the player"), ("🎭 Part the curtains", "🎤 Call to the stage"), ("📺 Change the camera view", "🔒 Lock the control room"), ("📻 Play the cassette", "⏏️ Eject it"), ("➡️ Follow the exit sign", "🍰 Follow the crumbs"), ("🎉 Leave the party", "📯 Listen for one more song")],
    "drowned_station": [("🕰️ Set the platform clock", "📋 Read the lost notice"), ("🚇 Enter the waiting train", "🪑 Check the wet seat"), ("📢 Answer the announcement", "🕳️ Listen below the platform"), ("🔦 Enter the flooded tunnel", "🖐️ Follow the handprint"), ("👣 Follow the footprints", "🪑 Touch the wet bench"), ("🚉 Read the last-stop sign", "🔩 Check the scratched words"), ("🪜 Climb the stairs", "🌀 Take the portal")],
    "endless_hotel": [("📖 Sign the register", "🔔 Ring for the clerk"), ("🚪 Enter the room", "👣 Follow the other footprints"), ("🖊️ Add a guestbook review", "📕 Close the book"), ("🛗 Enter the elevator", "🧳 Check for your luggage"), ("🥘 Inspect the tray", "🪜 Take the stairs"), ("🛒 Follow the bellhop's cart", "⛓️ Test the lobby exit"), ("🔑 Return the key", "🌀 Take the portal")],
    "fogbound_town": [("🚦 Follow the green light", "🚶 Wait for the signal"), ("🗺️ Take the figure's map", "👤 Ask who drew it"), ("☕ Drink the coffee", "🧾 Read the receipt"), ("📺 Watch the window", "🪟 Check behind you"), ("🌦️ Follow the forecast", "🗺️ Find your red marker"), ("🪧 Follow the exit sign", "🔄 Watch the arrow"), ("🚗 Listen for the engine", "🌀 Take the portal")],
    "graveyard": [("📖 Correct the ledger", "🧵 Untie the gate cloth"), ("🪦 Read the scratched stone", "🌼 Follow the flowers"), ("📒 Check the final column", "🕯️ Close the ledger"), ("🏮 Take the caretaker's lantern", "⛏️ Follow the shovel shadow"), ("💐 Turn the bouquet over", "🪦 Read the blank stone"), ("👣 Follow the groundskeeper", "🌫️ Wait for the path"), ("🚪 Leave the cemetery", "📖 Check the count")],
    "haunted_house": [("🏠 Study the miniature", "💡 Follow the moving light"), ("🖼️ Read the property listing", "🪞 Check the portrait frame"), ("🚪 Enter a staged room", "🪑 Move the chair"), ("🛏️ Lift the bedspread", "🪵 Tap the floorboards"), ("🔑 Take the turning key", "🧱 Follow the lock in the wall"), ("🧶 Step onto the welcome mat", "🚪 Try the foyer door"), ("📄 Update the flyer", "🌀 Take the portal")],
    "silent_campground": [("⛺ Check the empty tents", "🔥 Examine the fire ring"), ("📷 Zoom in on the figure", "🗺️ Turn the photograph over"), ("📓 Read the headcount", "📻 Check the ranger radio"), ("🌲 Call into the trees", "🤫 Keep listening"), ("📸 Review the latest image", "🔄 Turn the camera around"), ("🪧 Follow the trail marker", "✍️ Read its reverse"), ("📻 Answer the radio", "🌀 Take the portal")],
    "witch_woods": [("🏮 Follow the lit lanterns", "🌿 Inspect the herb bundles"), ("🕯️ Take the empty place", "🌾 Check the warm grass"), ("👣 Follow the overhead prints", "🌳 Look for their source"), ("🫖 Enter the cottage", "🪟 Watch the window"), ("🌑 Look into the pool", "🏮 Count the reflections"), ("🪵 Read the tree map", "✍️ Stop the moving line"), ("🏮 Turn toward the procession", "🌀 Take the portal")],
    "yellow_halls": [("🖥️ Check the warm monitor", "📞 Answer the ringing phone"), ("🚪 Read the nameplate", "🔑 Try the blank key"), ("📋 Finish the staff checklist", "🔢 Count the cubicles"), ("☕ Pour the coffee", "🪑 Check the empty seat"), ("🖥️ Compare the monitors", "💡 Turn off the screens"), ("☎️ Find the phone in the wall", "➡️ Follow the exit sign"), ("💡 Watch the lights go out", "🌀 Take the portal")],
}


def apply_alternate_routes(stories):
    for location_id, (title, opening, beats) in EPISODES.items():
        story = stories[location_id]
        scene_ids = story["scene_order"]
        if len(scene_ids) != len(beats):
            raise ValueError(f"Alternate episode for {location_id} has {len(beats)} beats; expected {len(scene_ids)}")

        scenes = {}
        for index, (scene_id, text) in enumerate(zip(scene_ids, beats)):
            next_scene = scene_ids[index + 1] if index + 1 < len(scene_ids) else None
            last = next_scene is None
            label_a, label_b = _LOCATION_ACTIONS.get(location_id, _ACTION_PAIRS)[index % 7]
            if last:
                first_text = f"You leave before the place can revise its account of what happened. {text}"
                second_text = f"You look back once. Something remains where the story says nobody was standing. {text}"
            else:
                first_text = "The clue shifts into place. For a moment, the way forward is clear—and something on the other side notices you noticed."
                second_text = "You move on without touching it. A moment later, the same sound comes from just behind your shoulder."

            choices = [
                choice(label_a, f"episode_{location_id}_{scene_id}_a", "medium", first_text, -3,
                       next_scene=next_scene, end=last, ending_title=title if last else None,
                       effects={f"episode_{location_id}_{scene_id}_a": True}),
                choice(label_b, f"episode_{location_id}_{scene_id}_b", "low", second_text, -1,
                       next_scene=next_scene, end=last, ending_title=title if last else None,
                       effects={f"episode_{location_id}_{scene_id}_b": True}),
            ]

            # Keep each location's pet and rare-discovery mechanics available
            # in the alternate episode as well.
            for old_choice in story["scenes"][scene_id].get("choices", []):
                if any(
                    isinstance(outcome, dict) and (outcome.get("pet_discovery") or outcome.get("discovery_id"))
                    for outcome in old_choice.get("outcomes", [])
                ):
                    choices.append(copy.deepcopy(old_choice))

            scenes[scene_id] = {"text": text, "choices": choices, "reactions": []}

        story["alternate_episode"] = {
            "title": title,
            "opening": opening,
            "scenes": scenes,
        }
