from ..story_helpers import choice, discovery_choice, pet_choice, scene, story

STORY = story(
    "asylum",
    "Abandoned Asylum",
    {
        "normal": "The portal deposits you in a hospital corridor that should have been dark for decades. A fluorescent tube buzzes overhead. Somewhere deeper inside, a call button rings once.",
        "low": "The portal deposits you in a hospital corridor. The lights buzz. You know you have been here before, although you cannot remember when.",
        "insane": "The corridor looks almost welcoming. The walls are clean. The lights are warm. Every room number has your name on it.",
    },
    {
        "arrival": scene(
            "arrival",
            "The reception desk is covered in dust except for one fresh clipboard. Its top page reads: **PATIENT INTAKE — TODAY**. The pen beside it is still warm.",
            [
                choice("📋 Read the clipboard", "read_clipboard", "medium", "The last line asks you to sign as both patient and examiner. You leave your name unsigned, but keep the page.", -4, next_scene="records", effects={"read_intake": True}),
                choice("🔦 Check the nurse station", "nurse_station", "low", "A dead monitor flickers once. For a second, it displays a map of the building.", -1, next_scene="records", effects={"saw_map": True}),
                choice("🚪 Follow the ringing", "follow_call", "high", "The call button stops before you reach it. A second one rings from upstairs.", -6, next_scene="records", effects={"followed_call": True}),
            
                choice('🪪 Check the visitor badge', 'visitor_badge', 'medium', "A visitor badge lies beneath the desk. It bears today's date and your photograph. The photograph was taken from somewhere inside the asylum.", -7, next_scene='records', effects={"story_visitor_badge": True}),
            ],
            low_sanity="The clipboard lists your current Sanity as a diagnosis. The number changes when you blink.",
            insane="The clipboard is already signed. The signature is yours, but the handwriting is not.",
        ),
        "records": scene(
            "records",
            "You find the records room. Filing cabinets stand open as though someone was searching them recently. A single folder is labeled with a number you recognize.",
            [
                discovery_choice("🔎 Open the Room 13 file", "room_13", "high", "patient_in_room_13", "The call button rings again from Room 13. The empty room feels suddenly occupied.", -10, "ward"),
                choice("📁 Search the recent admissions", "recent_admissions", "medium", "Several charts are blank except for today's date. One contains a note: **DO NOT LET THE PATIENT LEAVE**.", -5, next_scene="ward", effects={"found_warning": True}),
                choice("🚪 Leave the records room", "leave_records", "low", "You close the cabinets. Something inside one of them knocks once after the latch clicks.", -2, next_scene="ward", effects={"avoided_records": True}),
            
                choice('📎 Read the note behind the folder', 'hidden_note', 'high', 'Behind the folder is a note written in several different hands: **If the patient asks whether this is real, do not answer.**\n\nThe ink is still wet.', -9, next_scene='ward', effects={"story_hidden_note": True}),
            ],
            reactions=[{"all": ["read_intake"], "text": "The folder you picked up has your intake page clipped to it."}],
        ),
        "ward": scene(
            "ward",
            "Room 13 is at the end of the corridor. The observation glass is fogged from the inside. A patient chart lies on the floor outside.",
            [
                discovery_choice("🪟 Look through the observation glass", "observation", "high", "observation_window", "A figure inside the padded room points behind you. When you turn, the corridor is empty.", -12, "corridor"),
                choice("📄 Read the chart", "read_chart", "medium", "The chart describes a patient who responds to voices coming from inside the walls.", -5, next_scene="corridor", effects={"found_wall_note": True}),
                choice("🚶 Walk past Room 13", "pass_room", "low", "The call button follows you down the hall, ringing one room closer each time.", -2, next_scene="corridor", effects={"heard_following_call": True}),
            
                choice('🔒 Test the observation lock', 'observation_lock', 'medium', 'The observation room unlocks when you touch the handle, but the corridor light outside turns red. From inside the room comes the sound of someone slowly sitting down.', -7, next_scene='corridor', effects={"story_observation_lock": True}),
            ],
        ),
        "corridor": scene(
            "corridor",
            "The corridor opens into a long treatment wing. At the far end, a small hospital bed sits beneath a working light. Something scratches softly beneath it.",
            [
                pet_choice("🔎 Look underneath — 🐾 Pet Discovery", "look_under_bed", "medium", "A tiny patient peers out from beneath the bed. They look frightened, then slowly reach for your hand.", -3, "patient_list", effects={"met_patient": True}),
                choice("🛏️ Check the bed", "check_bed", "low", "The mattress is cold, but the indentation beside the pillow is fresh.", -1, next_scene="patient_list", effects={"checked_bed": True}),
                choice("🚪 Keep moving", "keep_moving", "medium", "The scratching stops. A small set of footsteps begins following you.", -5, next_scene="patient_list", effects={"ignored_patient": True}),
            
                choice('🩺 Examine the abandoned chart stand', 'chart_stand', 'high', 'A chart on the stand lists a treatment scheduled for you at 3:17 AM. Beneath it, someone has written: **We already tried keeping him asleep.**', -10, next_scene='patient_list', effects={"story_chart_stand": True}),
            ],
        ),
        "patient_list": scene(
            "patient_list",
            "A records cart blocks the exit. On top sits an old admission ledger opened to a page that should not exist.",
            [
                discovery_choice("📄 Read the open page", "read_patient_list", "high", "patient_list", "The page contains your name, an admission date of tomorrow, and no discharge date.", -13, "treatment_room"),
                choice("🧾 Compare it to the clipboard", "compare_files", "medium", "The two documents describe the same person from two different dates.", -5, next_scene="treatment_room", effects={"compared_records": True}),
                choice("🛒 Push the cart aside", "move_cart", "low", "The cart rolls away by itself and stops beside Room 13.", -2, next_scene="treatment_room", effects={"moved_cart": True}),
            
                choice('🖊️ Read the discharge column', 'discharge_column', 'medium', 'Every patient has a discharge date. Every date is crossed out except one: tomorrow. The name beside it is yours.', -8, next_scene='treatment_room', effects={"story_discharge_column": True}),
            ],
            reactions=[{"all": ["met_patient"], "text": "The little patient silently points at the ledger before you open it."}],
        ),
        "treatment_room": scene(
            "treatment_room",
            "The treatment room contains a single chair facing a wall of one-way glass. The chair is positioned for someone to watch the corridor, not the patient.",
            [
                choice("🪑 Sit in the chair", "sit_chair", "high", "For a few seconds, the asylum becomes completely quiet. Then the intercom says, **'Thank you for returning.'**", -9, next_scene="exit", effects={"sat_chair": True}),
                choice("🎙️ Use the intercom", "intercom", "medium", "You ask who is still here. A small voice answers, **'Everyone you left behind.'**", -6, next_scene="exit", effects={"used_intercom": True}),
                choice("🚪 Go straight for the exit", "exit_fast", "low", "The exit sign stays green. For once, nothing follows you.", 1, next_scene="exit", effects={"left_quickly": True}),
            
                choice('🪞 Look through the one-way glass', 'one_way_glass', 'high', 'The glass reflects the room behind you. In the reflection, the chair is occupied by someone wearing your clothes.', -11, next_scene='exit', effects={"story_one_way_glass": True}),
            ],
            reactions=[{"all": ["found_warning"], "text": "The intercom crackles: **'You were warned.'**"}],
        ),
        "exit": scene(
            "exit",
            "The front doors are waiting. Behind the glass, the asylum is dark again. Something small stands at the end of the corridor, watching you leave.",
            [
                choice("🚪 Step through the doors", "leave", "low", "The doors open. Cold station air replaces the smell of disinfectant. Whatever happened inside stays inside—at least for now.", 0, end=True, ending_title="You Left the Asylum"),
                choice("👋 Wave to the patient", "wave", "medium", "The little figure raises a hand. The doors close between you, and the corridor lights finally go out.", -2, end=True, ending_title="Someone Was Still There"),
                choice("👁️ Look back one last time", "look_back", "high", "The observation glass is filled with faces. None of them were visible before you turned around.", -8, end=True, ending_title="The Ward Remembers"),
            
                choice('🩸 Check the floor after leaving', 'floor_after', 'extreme', 'There are wet footprints outside the asylum. They begin at the door, continue through the station corridor, and stop directly behind you.', -9, end=True, ending_title='Floor After'),
            ],
            reactions=[
                {"all": ["met_patient"], "text": "The small patient remains beside the bed, watching until the portal takes you home."},
                {"all": ["found_wall_note"], "text": "You remember the note about voices in the walls. You decide not to repeat what you heard."},
            ],
        ),
    },
)

STORY["opening_variants"] = [
    'The first thing you hear is a call button. One press. Then another, farther down the corridor. Nothing is connected to the wall beside you.',
    "A clipboard lies just beyond the threshold. The top page bears today's date and a blank line labeled **PATIENT NAME**. The ink is still wet.",
    'The corridor beyond the portal is empty, but a wheelchair rolls slowly across the far intersection and disappears before you can reach it.',
]
