from ..story_helpers import choice, discovery_choice, pet_choice, scene, story

STORY = story(
    "endless_hotel",
    "The Endless Hotel",
    {
        "normal": "The portal opens in a hotel lobby. The front desk is empty. A brass sign reads **WELCOME BACK**. You do not remember staying here.",
        "low": "The lobby feels familiar. Every hallway looks like one you have already walked, even though you have only just arrived.",
        "insane": "The hotel lobby is crowded. Everyone is wearing your face.",
    },
    {
        "lobby": scene("lobby", "A bell sits on the front desk beside a guest register. The last entry is dated today.", [
            choice("🔔 Ring the bell", "ring", "medium", "A voice from the back office says, **'You are late.'**", -5, next_scene="hallway", effects={"rang_desk_bell": True}),
            choice("📖 Read the register", "register", "low", "Your name appears three pages before you arrived.", -4, next_scene="hallway", effects={"read_register": True}),
            choice("🚪 Enter the hallway", "hallway", "low", "The lobby door closes behind you. There is no sound of a lock.", -2, next_scene="hallway", effects={"skipped_desk": True}),
        ]),
        "hallway": scene("hallway", "Room numbers change every time you look away. One door briefly reads **314** before becoming 313.", [
            discovery_choice("🗝️ Follow the impossible room number", "room_314", "high", "room_314_future", "Room 314 appears where it should not. The door opens onto a hallway you have not reached yet.", -11, "guestbook"),
            choice("🧭 Mark the wall", "mark_wall", "medium", "You scratch a small mark into the wallpaper. When you turn around, the mark is several doors ahead.", -6, next_scene="guestbook", effects={"marked_hall": True}),
            choice("🚶 Keep walking", "walk", "low", "The carpet pattern repeats every seventeen steps.", -2, next_scene="guestbook", effects={"walked_hall": True}),
        ]),
        "guestbook": scene("guestbook", "A housekeeping cart waits beside an open room. On it sits a guestbook with fresh ink.", [
            discovery_choice("📖 Read the newest entry", "guestbook", "high", "guestbook", "The final guestbook entry reads: **If you're reading this, you're already one of us.** The ink is still wet.", -12, "elevator"),
            choice("✍️ Write your name", "write_name", "extreme", "The book writes your name before your pen touches the page.", -9, next_scene="elevator", effects={"signed_book": True}),
            choice("🚪 Close the book", "close_book", "low", "A new page turns itself behind your hand.", -3, next_scene="elevator", effects={"closed_book": True}),
        ]),
        "elevator": scene("elevator", "An elevator opens. A person with your face stands inside. They do not speak.", [
            pet_choice("🧍 Follow the quiet guest — 🐾 Pet Discovery", "hotel_guest", "medium", "The guest steps out of the elevator, walks beside you, and seems to know exactly which way leads out.", -3, "stairs", effects={"met_guest": True}),
            discovery_choice("🛗 Watch the person in the mirror", "elevator_face", "high", "elevator_face", "The elevator mirror shows you standing inside even though you are still outside. The person with your face smiles without moving their mouth.", -12, "stairs"),
            choice("🚪 Let the doors close", "let_close", "low", "The elevator departs empty. You hear it stop again one floor later.", -2, next_scene="stairs", effects={"avoided_elevator": True}),
        ]),
        "stairs": scene("stairs", "A stairwell should lead down to the lobby. Instead, it opens onto another identical hallway.", [
            choice("🪜 Take the stairs anyway", "stairs", "medium", "You count seven flights. The lobby is waiting at the bottom.", -5, next_scene="lobby_exit", effects={"took_stairs": True}),
            choice("🗺️ Follow your marks", "marks", "low", "Your mark leads directly to the exit, exactly where it should be.", 1, next_scene="lobby_exit", effects={"followed_marks": True}),
            choice("👁️ Stop and listen", "listen", "high", "You hear footsteps above, below, and beside you.", -8, next_scene="lobby_exit", effects={"heard_hotel": True}),
        ]),
        "lobby_exit": scene("lobby_exit", "The lobby is waiting again. The front desk is empty. The bell is still warm.", [
            choice("🚪 Open the portal door", "portal", "low", "You leave the hotel. Behind you, the lobby lights turn off one by one.", 0, next_scene="ending"),
            choice("🔔 Ring the bell", "bell", "medium", "A voice answers from somewhere upstairs: **'Thank you for staying.'**", -5, next_scene="ending", effects={"rang_exit_bell": True}),
            choice("📖 Check the register again", "register_again", "high", "Your name has been added to the current guest list.", -7, next_scene="ending", effects={"added_to_register": True}),
        ]),
        "ending": scene("ending", "The portal waits beyond the lobby. The hotel doors close behind you before you touch them.", [
            choice("🌀 Leave", "leave", "low", "You return to the station. Somewhere far away, an elevator bell rings.", 0, end=True, ending_title="Late Checkout"),
            choice("👋 Thank the hotel", "thank", "low", "A distant voice answers, **'Come back soon.'**", 1, end=True, ending_title="A Returning Guest"),
            choice("🏃 Run", "run", "high", "You run through the portal without looking back. The hotel still appears in the corner of your eye.", -7, end=True, ending_title="No Vacancy"),
        ], reactions=[{"all": ["met_guest"], "text": "The Hotel Guest stands at the lobby doors until you leave, as if making sure you find your way out."}]),
    },
    shortcut_scene="stairs",
)
