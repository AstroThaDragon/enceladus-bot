from ..story_helpers import choice, discovery_choice, pet_choice, scene, story

STORY = story(
    "yellow_halls",
    "The Yellow Halls",
    {
        "normal": "The portal opens onto an empty office floor: yellow wallpaper, damp carpet, and fluorescent panels that buzz without a visible power source. Identical corridors branch between silent cubicles. The floor plan says this space should be much smaller.",
        "low": "The office is familiar in the way a bad dream is familiar. You know which corridors to avoid, though you cannot remember learning them.",
        "insane": "The wallpaper is skin. The lights are eyes. Every empty cubicle is occupied by someone just out of sight, and the carpet is whispering your name.",
    },
    {
        "entrance": scene("entrance", "An office corridor opens into three more. Each has the same water stain, the same crooked EXIT sign, and the same fluorescent buzz. Only one light is working—and its glow stops at the next corner.", [
            choice("💡 Follow the working light", "light", "low", "The light stays exactly one room ahead of you.", -1, next_scene="door", effects={"followed_light": True}),
            choice("🟨 Follow the clean carpet", "clean", "medium", "The carpet becomes damp under your boots. The hum gets louder.", -5, next_scene="door", effects={"followed_clean": True}),
            choice("↩️ Stay where you are", "stay", "low", "The hallway behind you changes length.", -3, next_scene="door", effects={"stayed": True}),
        
                choice('🧵 Follow the red thread under the carpet', 'thread_carpet', 'medium', 'A red thread disappears beneath the carpet. You pull it free and find a tiny brass key tied to its end. The key is stamped **314**.', -7, next_scene='door', effects={"story_thread_carpet": True}),
            ]),
        "door": scene("door", "A plain office door stands in the corridor without a frame, handle, or hinges. The carpet continues beneath it. Something on the other side knocks in the rhythm of a fluorescent light switching on.", [
            discovery_choice("🚪 Knock back", "unmarked", "high", "unmarked_door", "Your own voice answers from behind the impossible door: **Let me out.**", -10, "loop"),
            choice("👂 Listen", "listen", "medium", "Something knocks back three times. The rhythm matches your heartbeat.", -6, next_scene="loop", effects={"counted_knocks": True}),
            choice("🏃 Leave the door", "leave_door", "low", "The door is gone when you look back.", -2, next_scene="loop", effects={"ignored_door": True}),
        
                choice('🕳️ Look through the gap beneath the door', 'door_gap', 'high', 'There is no floor on the other side. Only darkness—and the sound of fluorescent lights humming very far away.', -9, next_scene='loop', effects={"story_door_gap": True}),
            ], reactions=[
                {"all": ["followed_light"], "text": "A thin line of light shines beneath the door. It is the same shade as the light you followed—and it is moving away."},
                {"all": ["followed_clean"], "text": "A damp carpet print appears beside yours. It is facing the wrong direction."},
                {"all": ["stayed"], "text": "The corridor has moved while you waited. The water stain is still there, but now it is above your head."},
                {"all": ["story_thread_carpet"], "text": "The little brass key is warm in your pocket. From behind the door, something tries a lock."},
            ]),
        "loop": scene("loop", "You turn past a row of identical cubicles and arrive back at the same water stain. Your footprints are already here. A second set walks beside them, keeping perfect pace.", [
            discovery_choice("👁️ Follow the other you", "wrong_hallway", "high", "wrong_hallway", "Your previous self is standing in the hallway. It turns its head when you approach.", -13, "break_room"),
            choice("🏃 Run past", "run_past", "high", "You pass yourself. Your own footsteps continue behind you.", -9, next_scene="break_room", effects={"passed_self": True}),
            choice("↩️ Turn around", "turn_back", "medium", "The hallway behind you is no longer there.", -6, next_scene="break_room", effects={"lost_hallway": True}),
        
                choice('🧭 Mark the wall with your name', 'name_mark', 'medium', 'The mark appears on the wall ahead of you before you make it. Beneath it is another message: **You have already tried this.**', -8, next_scene='break_room', effects={"story_name_mark": True}),
            ], reactions=[
                {"all": ["counted_knocks"], "text": "Three knocks sound from the cubicle wall. After a pause, a fourth answers from somewhere overhead."},
                {"all": ["lost_hallway"], "text": "A fresh arrow has appeared on the wall, pointing behind you. The handwriting looks like yours."},
                {"all": ["story_name_mark"], "text": "Your name is already written on the next cubicle partition. The ink is still wet."},
            ]),
        "break_room": scene("break_room", "A break room sits between two rows of silent cubicles. The vending machine hums with no power cable. A paper cup on the counter is still warm. Something taps from inside the machine.", [
            pet_choice("🐾 Follow the tapping — 🐾 Pet Discovery", "patch", "medium", "A glitched little creature steps from behind the vending machine. It has too many eyes, but it seems delighted to see you.", -2, "familiar", effects={"met_patch": True}),
            choice("🥤 Open the vending machine", "vending", "medium", "The machine is empty except for a single item labeled **RETURN TO START**.", -5, next_scene="familiar", effects={"opened_vending": True}),
            choice("🚪 Leave the room", "leave_room", "low", "The fluorescent lights follow you into the hallway.", -2, next_scene="familiar", effects={"left_room": True}),
        
                choice("🥤 Check the vending machine's reflection", 'vending_reflection', 'high', 'The vending machine reflection shows the room empty. Something is standing where you are, but its face is turned toward the corner.', -10, next_scene='familiar', effects={"story_vending_reflection": True}),
            ], reactions=[
                {"all": ["passed_self"], "text": "A chair rolls out from beneath a desk and stops beside you. The seat is still warm."},
                {"all": ["lost_hallway"], "text": "A desk phone rings once in the next room. When you reach it, the cord disappears into the wall."},
            ]),
        "familiar": scene("familiar", "A familiar office door opens onto a bedroom with your name on a brass room plate. The furniture is almost right. The clock runs backward, and somewhere beyond the wall a printer begins a job that never finishes.", [
            discovery_choice("🛏️ Lift the blanket", "familiar_room", "extreme", "familiar_room", "The bedroom contains your belongings. Something breathes beneath the blanket, but the bed is empty.", -15, "exit"),
            choice("⏰ Watch the clock", "clock", "high", "The hands reverse until they point directly at you.", -8, next_scene="exit", effects={"watched_clock": True}),
            choice("🚪 Leave", "leave_room", "low", "The room door opens into another copy of the same room.", -3, next_scene="exit", effects={"left_familiar": True}),
        
                choice('🛏️ Check the underside of the bed', 'bed_underside', 'extreme', 'There are fingernail marks carved into the wooden frame. Beneath them, someone has written: **Do not let the room remember you.**', -12, next_scene='exit', effects={"story_bed_underside": True}),
            ]),
        "exit": scene("exit", "The corridors finally open onto the familiar glow of the portal. Behind you, office lights switch off one by one, though the hallway keeps stretching farther away.", [
            choice("🌀 Follow the glow", "portal", "low", "The portal carries you home. The fluorescent hum stops behind you.", 0, next_scene="ending"),
            choice("💡 Break a light", "break_light", "medium", "The light shatters. For the first time, the hallway is genuinely dark.", -4, next_scene="ending", effects={"broke_light": True}),
            choice("👁️ Wait for the hum to stop", "wait", "high", "The hum stops. In the silence, you hear footsteps approaching from every direction.", -8, next_scene="ending", effects={"waited": True}),
        
                choice('💡 Turn off the last working light', 'last_light', 'high', 'The darkness lasts three seconds. When the light returns, the portal is closer—and there is a yellow handprint on the wall beside it.', -9, next_scene='ending', effects={"story_last_light": True}),
            ], reactions=[
                {"all": ["watched_clock"], "text": "The backward clock stops. From the other side of the wall comes the sound of a second hand starting to tick."},
                {"all": ["story_bed_underside"], "text": "The warning beneath the bed is now written on the office door, in fresh ink: **Do not let the hall remember you.**"},
            ]),
        "ending": scene("ending", "The portal closes. The Yellow Halls are gone, but the smell of damp carpet clings to your boots. For a moment, the station lights buzz in the same rhythm.", [
            choice("🌀 Return", "return", "low", "You return before the halls can decide to rearrange themselves again.", 0, end=True, ending_title="Lost, Actually"),
            choice("👋 Wave goodbye", "wave", "low", "Something in the fluorescent buzz sounds almost like a laugh.", 1, end=True, ending_title="Wrong Reality"),
            choice("🏃 Run", "run", "medium", "You leave quickly. For one second, your station corridor has yellow wallpaper.", -5, end=True, ending_title="The Hallway Followed"),
        
                choice('🟨 Check your reflection after returning', 'yellow_reflection', 'extreme', 'Your reflection looks normal until you blink. For one frame, the background behind you is yellow wallpaper and fluorescent light.', -10, end=True, ending_title='Yellow Reflection'),
            ], reactions=[
                {"all": ["met_patch"], "text": "Patch pads beside you until the portal closes, completely unconcerned that none of its anatomy makes sense."},
                {"all": ["broke_light"], "text": "The broken bulb continues to buzz from somewhere inside the dark corridor."},
                {"all": ["waited"], "text": "The approaching footsteps stop when the portal opens. Something on the other side starts walking again."},
            ]),
    },
)

STORY["opening_variants"] = [
    'The fluorescent hum reaches you before you see the office floor. One light flickers on after another, illuminating a row of empty cubicles that seems to continue past the horizon.',
    'A damp footprint appears on the carpet beyond the threshold. Then another. They lead toward an EXIT sign and stop beneath it. The sign points back at you.',
    'The wallpaper beyond the portal is perfectly still. Just before you enter, a section dimples inward as though something behind it has taken a breath.',
    'A printer starts somewhere beyond the portal. It feeds out a single page, though there is no paper tray in sight. The page bears a map of the halls, with your location marked ahead of you.',
    'The portal opens onto a break room. The coffee is fresh, the chairs are tucked in, and a wall clock shows a time that has not happened yet.',
    'Every light in the corridor turns on at once. At the far end, an office chair slowly rolls across the carpet and disappears around a corner.',
]
