from ..story_helpers import choice, discovery_choice, pet_choice, scene, story

STORY = story(
    "yellow_halls",
    "The Yellow Halls",
    {
        "normal": "The portal opens into yellow wallpaper, damp carpet, and fluorescent lights that hum with no visible power source. The corridor stretches farther than it should.",
        "low": "The halls are already familiar. You cannot remember walking them, but you know which turns you should not take.",
        "insane": "The wallpaper is skin. The lights are eyes. The carpet is whispering your name.",
    },
    {
        "entrance": scene("entrance", "There are three corridors ahead. All three have the same stain on the carpet, but only one has a working light.", [
            choice("💡 Follow the working light", "light", "low", "The light stays exactly one room ahead of you.", -1, next_scene="door", effects={"followed_light": True}),
            choice("🟨 Follow the clean carpet", "clean", "medium", "The carpet becomes damp under your boots. The hum gets louder.", -5, next_scene="door", effects={"followed_clean": True}),
            choice("↩️ Stay where you are", "stay", "low", "The hallway behind you changes length.", -3, next_scene="door", effects={"stayed": True}),
        
                choice('🧵 Follow the red thread under the carpet', 'thread_carpet', 'medium', 'A red thread disappears beneath the carpet. You pull it free and find a tiny brass key tied to its end. The key is stamped **314**.', -7, next_scene='door', effects={"story_thread_carpet": True}),
            ]),
        "door": scene("door", "A door appears without a handle, hinges, or frame. Someone—or something—knocks from the other side.", [
            discovery_choice("🚪 Knock back", "unmarked", "high", "unmarked_door", "Your own voice answers from behind the impossible door: **Let me out.**", -10, "loop"),
            choice("👂 Listen", "listen", "medium", "Something knocks back three times. The rhythm matches your heartbeat.", -6, next_scene="loop", effects={"counted_knocks": True}),
            choice("🏃 Leave the door", "leave_door", "low", "The door is gone when you look back.", -2, next_scene="loop", effects={"ignored_door": True}),
        
                choice('🕳️ Look through the gap beneath the door', 'door_gap', 'high', 'There is no floor on the other side. Only darkness—and the sound of fluorescent lights humming very far away.', -9, next_scene='loop', effects={"story_door_gap": True}),
            ]),
        "loop": scene("loop", "You turn a corner and recognize the hallway. Your own footprints are already on the carpet.", [
            discovery_choice("👁️ Follow the other you", "wrong_hallway", "high", "wrong_hallway", "Your previous self is standing in the hallway. It turns its head when you approach.", -13, "break_room"),
            choice("🏃 Run past", "run_past", "high", "You pass yourself. Your own footsteps continue behind you.", -9, next_scene="break_room", effects={"passed_self": True}),
            choice("↩️ Turn around", "turn_back", "medium", "The hallway behind you is no longer there.", -6, next_scene="break_room", effects={"lost_hallway": True}),
        
                choice('🧭 Mark the wall with your name', 'name_mark', 'medium', 'The mark appears on the wall ahead of you before you make it. Beneath it is another message: **You have already tried this.**', -8, next_scene='break_room', effects={"story_name_mark": True}),
            ]),
        "break_room": scene("break_room", "A fluorescent-lit room contains a vending machine that hums without power. Something taps from inside it.", [
            pet_choice("🐾 Follow the tapping — 🐾 Pet Discovery", "patch", "medium", "A glitched little creature steps from behind the vending machine. It has too many eyes, but it seems delighted to see you.", -2, "familiar", effects={"met_patch": True}),
            choice("🥤 Open the vending machine", "vending", "medium", "The machine is empty except for a single item labeled **RETURN TO START**.", -5, next_scene="familiar", effects={"opened_vending": True}),
            choice("🚪 Leave the room", "leave_room", "low", "The fluorescent lights follow you into the hallway.", -2, next_scene="familiar", effects={"left_room": True}),
        
                choice("🥤 Check the vending machine's reflection", 'vending_reflection', 'high', 'The vending machine reflection shows the room empty. Something is standing where you are, but its face is turned toward the corner.', -10, next_scene='familiar', effects={"story_vending_reflection": True}),
            ]),
        "familiar": scene("familiar", "A bedroom waits at the end of the corridor. It looks almost exactly like yours. The clock runs backward.", [
            discovery_choice("🛏️ Lift the blanket", "familiar_room", "extreme", "familiar_room", "The bedroom contains your belongings. Something breathes beneath the blanket, but the bed is empty.", -15, "exit"),
            choice("⏰ Watch the clock", "clock", "high", "The hands reverse until they point directly at you.", -8, next_scene="exit", effects={"watched_clock": True}),
            choice("🚪 Leave", "leave_room", "low", "The room door opens into another copy of the same room.", -3, next_scene="exit", effects={"left_familiar": True}),
        
                choice('🛏️ Check the underside of the bed', 'bed_underside', 'extreme', 'There are fingernail marks carved into the wooden frame. Beneath them, someone has written: **Do not let the room remember you.**', -12, next_scene='exit', effects={"story_bed_underside": True}),
            ]),
        "exit": scene("exit", "The halls finally end at a familiar portal glow. The fluorescent hum is fading.", [
            choice("🌀 Follow the glow", "portal", "low", "The portal carries you home. The fluorescent hum stops behind you.", 0, next_scene="ending"),
            choice("💡 Break a light", "break_light", "medium", "The light shatters. For the first time, the hallway is genuinely dark.", -4, next_scene="ending", effects={"broke_light": True}),
            choice("👁️ Wait for the hum to stop", "wait", "high", "The hum stops. In the silence, you hear footsteps approaching from every direction.", -8, next_scene="ending", effects={"waited": True}),
        
                choice('💡 Turn off the last working light', 'last_light', 'high', 'The darkness lasts three seconds. When the light returns, the portal is closer—and there is a yellow handprint on the wall beside it.', -9, next_scene='ending', effects={"story_last_light": True}),
            ]),
        "ending": scene("ending", "The portal closes. The Yellow Halls are gone, but the smell of damp carpet remains on your boots.", [
            choice("🌀 Return", "return", "low", "You return before the halls can decide to rearrange themselves again.", 0, end=True, ending_title="Lost, Actually"),
            choice("👋 Wave goodbye", "wave", "low", "Something in the fluorescent buzz sounds almost like a laugh.", 1, end=True, ending_title="Wrong Reality"),
            choice("🏃 Run", "run", "medium", "You leave quickly. For one second, your station corridor has yellow wallpaper.", -5, end=True, ending_title="The Hallway Followed"),
        
                choice('🟨 Check your reflection after returning', 'yellow_reflection', 'extreme', 'Your reflection looks normal until you blink. For one frame, the background behind you is yellow wallpaper and fluorescent light.', -10, end=True, ending_title='Yellow Reflection'),
            ], reactions=[{"all": ["met_patch"], "text": "Patch pads beside you until the portal closes, completely unconcerned that none of its anatomy makes sense."}]),
    },
)

STORY["opening_variants"] = [
    'The fluorescent hum reaches you before you see the corridor. One light flickers on after another, tracing a path into the distance without revealing what lies at the end.',
    'A damp footprint appears on the carpet beyond the threshold. Then another. They lead deeper into the halls and stop abruptly beneath a light that is not working.',
    'The wallpaper beyond the portal is perfectly still. Then, just before you enter, a section of it dimples inward as though something behind it has taken a breath.',
]
