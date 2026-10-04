from ..story_helpers import choice, discovery_choice, pet_choice, scene, story

STORY = story(
    "dilapidated_pizzeria",
    "Dilapidated Pizzeria",
    {
        "normal": "The portal opens behind the counter of a dead family pizzeria. The arcade machines are dark. The stage curtains are closed. Somewhere in the building, a birthday song begins.",
        "low": "The restaurant looks abandoned, but the tables are set for guests. You cannot shake the feeling that the room is waiting for you specifically.",
        "insane": "The pizzeria is full of cheering customers. Every empty chair is reserved for you.",
    },
    {
        "dining": scene("dining", "The dining room lights blink on one row at a time. A ticket dispenser prints **ADMIT ONE — RETURNING GUEST**.", [
            choice("🎟️ Take the ticket", "ticket", "medium", "The ticket is warm. The printed time is 3:17 AM, even though the clock says midnight.", -4, next_scene="birthday", effects={"took_ticket": True}),
            choice("🔌 Cut the power", "power", "medium", "The lights go out. The stage remains lit.", -5, next_scene="birthday", effects={"cut_power": True}),
            choice("🎭 Watch the stage", "stage", "low", "The curtains twitch once. Something on the other side whispers your name.", -3, next_scene="birthday", effects={"watched_stage": True}),
        
                choice('🎟️ Read the back of the ticket', 'ticket_back', 'medium', 'The back of the ticket contains a handwritten note: **When the broadcast ends, do not stay for the last song.** The ink smells faintly of dust and ozone.', -7, next_scene='birthday', effects={"story_ticket_back": True}),
            ]),
        "birthday": scene("birthday", "A party room is decorated for a birthday. Every candle is lit. The cake has your name written on it.", [
            discovery_choice("🎂 Step closer to the cake", "birthday_room", "high", "birthday_room", "The birthday room is prepared for you. When you look away, the candles have burned no shorter.", -11, "stage_room"),
            choice("🔪 Cut the cake", "cut_cake", "medium", "The cake is empty inside except for a warm birthday card addressed to you.", -5, next_scene="stage_room", effects={"found_card": True}),
            choice("🚪 Leave the party room", "leave_party", "low", "The candles remain lit after the door closes.", -2, next_scene="stage_room", effects={"left_party": True}),
        
                choice('🎁 Open the wrapped present', 'birthday_present', 'high', 'Inside the present is an old employee badge with the photograph scratched away. The badge is stamped **3:17 AM**.', -8, next_scene='stage_room', effects={"story_birthday_present": True}),
            ]),
        "stage_room": scene("stage_room", "The stage curtains are open now. An animatronic bear stands beneath a single spotlight. One eye flickers.", [
            discovery_choice("🤖 Approach the stage", "stage_head", "high", "stage_head", "The animatronic head turns toward you. A child's voice whispers from directly behind you.", -12, "security"),
            choice("💡 Turn on the house lights", "lights", "medium", "The bear freezes. Its shadow keeps moving for several seconds.", -6, next_scene="security", effects={"turned_lights": True}),
            choice("🚪 Stay away from the stage", "stay_back", "low", "The bear slowly turns toward the exit instead.", -2, next_scene="security", effects={"avoided_stage": True}),
        
                choice('🎤 Check the microphone stand', 'microphone_stand', 'medium', 'The microphone is unplugged, but when you lean toward it, a voice whispers through the dead speaker: **Please stop recording us.**', -8, next_scene='security', effects={"story_microphone_stand": True}),
            ]),
        "security": scene("security", "The security office still has power. A monitor shows the dining room from three different angles.", [
            pet_choice("🐻 Approach the flickering mascot — 🐾 Pet Discovery", "approach_bear", "medium", "The battered bear animatronic steps out of the darkness, gives you a slow wave, and waits for you to decide whether it may follow.", -3, "tape", effects={"met_bear": True}),
            choice("📺 Check the cameras", "cameras", "medium", "Every camera shows the same empty hallway, even though you are standing in one of the feeds.", -5, next_scene="tape", effects={"checked_cameras": True}),
            choice("🔌 Shut down the monitors", "monitors", "low", "The monitors go dark. One remains on, displaying a view from directly behind you.", -4, next_scene="tape", effects={"shut_monitors": True}),
        
                choice('📼 Search the bottom camera drawer', 'camera_drawer', 'high', 'You find a maintenance cassette labeled **BROADCAST STATION — RETURNED**. The tape has been rewound so many times the ribbon is almost transparent.', -10, next_scene='tape', effects={"story_camera_drawer": True}),
            ]),
        "tape": scene("tape", "A VHS cassette is labeled **3:17 AM**. The player is already waiting for you.", [
            discovery_choice("📼 Watch the tape", "watch_tape", "high", "security_tape", "The recording shows you walking through the restaurant at 3:17 AM and staring directly into the camera.", -13, "exit"),
            choice("⏩ Skip ahead", "skip_tape", "medium", "You see yourself standing behind the security desk. The timestamp is tomorrow.", -6, next_scene="exit", effects={"saw_future_tape": True}),
            choice("📺 Turn it off", "off_tape", "low", "The screen goes black. Your reflection remains on it.", -2, next_scene="exit", effects={"stopped_tape": True}),
        
                choice('📺 Watch only the final frame', 'final_frame', 'extreme', 'The final frame shows the pizzeria empty. In the dark reflection of the window, someone is standing in the broadcast station control room.', -11, next_scene='exit', effects={"story_final_frame": True}),
            ]),
        "exit": scene("exit", "The front doors unlock. The pizzeria's music starts playing softly as you approach them.", [
            choice("🚪 Leave", "leave", "low", "You step outside. The music stops the instant the portal closes.", 0, next_scene="ending"),
            choice("🎟️ Leave the ticket behind", "ticket", "low", "You place the ticket on the counter. The dispenser immediately prints another one.", 1, next_scene="ending", effects={"left_ticket": True}),
            choice("👀 Look at the stage", "look_stage", "high", "The bear is gone. The spotlight is still on.", -8, next_scene="ending", effects={"saw_empty_stage": True}),
        
                choice('🎵 Listen for the last song', 'last_song', 'high', 'The music changes to a melody you heard somewhere else. The final note is followed by three knocks from inside the locked restaurant.', -9, next_scene='ending', effects={"story_last_song": True}),
            ]),
        "ending": scene("ending", "The portal hums outside the restaurant. Behind you, one arcade cabinet powers on by itself.", [
            choice("🌀 Return", "return", "low", "You leave before the cabinet can finish booting.", 0, end=True, ending_title="After Closing"),
            choice("🎮 Press the arcade button", "arcade", "medium", "The screen displays your own face for one frame, then returns to the title screen.", -4, end=True, ending_title="One More Game"),
            choice("🏃 Run for the portal", "run", "high", "The birthday song follows you all the way back to the station.", -7, end=True, ending_title="The Guest of Honor Leaves"),
        
                choice('🍕 Look back through the window', 'window_after', 'extreme', 'The arcade cabinet is still lit. Its screen now displays a live view of you standing outside, even though the camera is facing the wrong direction.', -10, end=True, ending_title='Window After'),
            ], reactions=[{"all": ["met_bear"], "text": "Broken Bear gives one final mechanical wave before following you through the portal."}]),
    },
)

STORY["opening_variants"] = [
    'A birthday melody is playing beyond the portal, but there is no music coming from the speakers. The tune stops the instant you reach the threshold.',
    'One of the dark arcade cabinets lights up for a second. Its screen shows a single message: **PLAYER TWO READY.**',
    'A paper party hat lies just inside the doorway. It is clean despite the dust everywhere else, and its elastic strap is stretched as though it was recently worn.',
]
