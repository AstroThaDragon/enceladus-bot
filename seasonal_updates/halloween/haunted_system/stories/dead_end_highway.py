from ..story_helpers import choice, discovery_choice, pet_choice, scene, story

STORY = story(
    "dead_end_highway",
    "The Dead-End Highway",
    {
        "normal": "The portal opens beside an empty highway under a dead black sky. Road signs promise exits that never seem to get closer.",
        "low": "The road is empty, but you hear another engine somewhere behind you. Every time you look, the road is empty again.",
        "insane": "The highway is packed with parked cars. Every driver is sitting perfectly still, staring at you.",
    },
    {
        "road": scene("road", "A payphone stands beside the shoulder. It rings once, stops, then rings again.", [
            discovery_choice("☎️ Answer the payphone", "phone", "medium", "last_payphone", "The payphone rings with no line connected. The voice says, **'You are going the wrong way.'** Then it hangs up.", -7, "car"),
            choice("🗺️ Check the road map", "map", "low", "The map shows a road that does not exist on the highway.", -3, next_scene="car", effects={"checked_map": True}),
            choice("🚶 Ignore the phone", "ignore", "low", "The phone keeps ringing behind you.", -2, next_scene="car", effects={"ignored_phone": True}),
        
                choice('🪞 Check the payphone reflection', 'phone_reflection', 'high', "The payphone's metal casing reflects the road behind you. In the reflection, a second vehicle is parked where there is empty pavement.", -8, next_scene='car', effects={"story_phone_reflection": True}),
            ]),
        "car": scene("car", "An abandoned car sits with its passenger door locked. Something taps from inside.", [
            discovery_choice("🚗 Open the passenger door", "passenger", "extreme", "passenger", "The passenger seat is empty. Something exhales beside you as invisible footsteps begin following.", -15, "motel"),
            choice("👂 Listen through the window", "listen", "high", "The tapping matches your heartbeat.", -8, next_scene="motel", effects={"matched_tapping": True}),
            choice("🏃 Walk away", "walk_away", "low", "The footsteps follow you along the shoulder.", -3, next_scene="motel", effects={"left_car": True}),
        
                choice('🧤 Search the glove compartment', 'glovebox', 'medium', 'The glove compartment contains an old map with a route circled in red. The route ends at **Mile 0**, but the highway on the map has no beginning.', -7, next_scene='motel', effects={"story_glovebox": True}),
            ]),
        "motel": scene("motel", "A motel sign glows beside an exit ramp. The office is empty, but one room is lit.", [
            choice("🚪 Check the lit room", "room", "medium", "The room is unlocked. The bed has been made recently.", -5, next_scene="sign", effects={"checked_motel": True}),
            choice("🗺️ Compare the exit to the map", "compare", "low", "The exit number is different on the map than on the road sign.", -2, next_scene="sign", effects={"compared_exit": True}),
            choice("🏃 Keep driving", "drive", "medium", "The motel disappears in your mirror, then appears ahead of you again.", -6, next_scene="sign", effects={"drove_past": True}),
        
                choice('🛎️ Knock on the lit room', 'motel_knock', 'high', 'Three knocks come from inside before you touch the door. When you knock back, the sound comes from the room behind you instead.', -9, next_scene='sign', effects={"story_motel_knock": True}),
            ]),
        "sign": scene("sign", "A road sign reads **MILE 0**. There is another Mile 0 sign farther ahead.", [
            pet_choice("🚗 Follow the passenger-side silhouette — 🐾 Pet Discovery", "hitchhiker", "medium", "A silent hitchhiker appears beside the road, then is suddenly sitting in your passenger seat. They point toward the road ahead.", -3, "mile_zero", effects={"met_hitchhiker": True}),
            choice("🪧 Inspect the sign", "inspect_sign", "high", "The distance number changes while you watch.", -7, next_scene="mile_zero", effects={"inspected_sign": True}),
            choice("🛣️ Keep driving", "keep_driving", "low", "The road behind you disappears.", -3, next_scene="mile_zero", effects={"kept_driving": True}),
        
                choice('🩸 Look beneath the road sign', 'sign_beneath', 'medium', 'Someone has buried a row of old license plates beneath the sign. Every plate begins with the same three characters. One is still warm.', -8, next_scene='mile_zero', effects={"story_sign_beneath": True}),
            ]),
        "mile_zero": scene("mile_zero", "The highway bends around a hill and returns to the same sign. Mile 0 is now printed on both sides of the road.", [
            discovery_choice("🔄 Turn around", "mile_zero", "high", "mile_zero", "The sign reads Mile 0 in both directions. Your destination becomes farther away while you watch.", -12, "payphone"),
            choice("🛣️ Keep going forward", "forward", "medium", "The road stretches ahead until the horizon disappears.", -6, next_scene="payphone", effects={"went_forward": True}),
            choice("☎️ Look for another payphone", "find_phone", "low", "A payphone appears exactly where you were standing earlier.", -2, next_scene="payphone", effects={"found_second_phone": True}),
        
                choice('🛣️ Watch the road markings', 'road_markings', 'high', 'The lane markings slowly move beneath your feet. One white line passes through your shadow without disturbing it.', -10, next_scene='payphone', effects={"story_road_markings": True}),
            ]),
        "payphone": scene("payphone", "The payphone is ringing again. This time, the receiver is already off the hook.", [
            choice("☎️ Pick it up", "pickup", "high", "The voice says, **'I'm you.'** Then gives directions to the place you are standing.", -8, next_scene="ending", effects={"heard_self": True}),
            choice("📞 Hang it up", "hang", "medium", "The phone rings immediately again.", -4, next_scene="ending", effects={"hung_up": True}),
            choice("🏃 Leave it", "leave", "low", "The receiver swings gently after you walk away.", -2, next_scene="ending", effects={"left_phone": True}),
        
                choice('☎️ Ask the caller where they are', 'caller_location', 'extreme', 'The voice answers, **Behind you.** You turn. The road is empty. The receiver whispers, **No. Farther behind you.**', -11, next_scene='ending', effects={"story_caller_location": True}),
            ]),
        "ending": scene("ending", "The portal appears beside the shoulder. The highway continues behind it, apparently without an end.", [
            choice("🌀 Return", "return", "low", "You step through before the road can offer another exit.", 0, end=True, ending_title="Wrong Turn"),
            choice("👋 Thank the passenger", "thank", "low", "The passenger seat is empty, but the belt clicks as though someone buckled in.", -2, end=True, ending_title="Roadside Company"),
            choice("🏃 Run for the portal", "run", "high", "The road signs all change to read **DO NOT STOP**.", -7, end=True, ending_title="Dead End"),
        
                choice('🛣️ Watch the road after returning', 'road_after', 'high', 'For a moment, the station floor has highway markings across it. They fade before you can step onto them.', -7, end=True, ending_title='Road After'),
            ], reactions=[{"all": ["met_hitchhiker"], "text": "The passenger is gone when you return to the station. You are not sure whether they ever occupied the seat."}]),
    },
    signal_scene="payphone",
)

STORY["opening_variants"] = [
    'You hear tires on wet pavement before you see the road. The sound passes from one side of the portal to the other, but no vehicle ever appears.',
    'A road sign beyond the threshold is turned toward you. Its arrow points behind you, toward a place you did not come from.',
    'The portal opens onto darkness and distant headlights. They remain perfectly still until you take a step, then begin moving toward you.',
]
