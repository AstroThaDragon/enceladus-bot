from ..story_helpers import choice, discovery_choice, pet_choice, scene, story

STORY = story(
    "derelict_research_facility",
    "Derelict Research Facility",
    {
        "normal": "The portal opens inside a sealed research corridor. Emergency lights still work. A terminal on the wall displays a single installed application: **MalO ver1.0.0**.",
        "low": "The facility feels less abandoned than paused. Somewhere behind the walls, a computer fan spins up and stops whenever you look toward it.",
        "insane": "The facility is spotless. Every terminal is already logged into your account. A photograph of you is open on every screen.",
    },
    {
        "arrival": scene("arrival", "The terminal asks whether you want to resume a previous session. You have never been here before.", [
            choice("💻 Open the terminal", "terminal", "medium", "The screen shows a directory of experiments, most marked TERMINATED. One folder is dated today.", -4, next_scene="experiment", effects={"opened_terminal": True}),
            choice("🚪 Check the security door", "security", "low", "The door is unlocked. That feels worse than if it had been sealed.", -2, next_scene="experiment", effects={"checked_security": True}),
            choice("📱 Check your phone", "phone", "medium", "Your phone has one new application installed. You do not remember downloading it.", -6, next_scene="experiment", effects={"checked_phone": True}),
        ]),
        "experiment": scene("experiment", "A research log lies open on a desk. The final page is marked **EXPERIMENT 17**.", [
            discovery_choice("📄 Read the final entry", "experiment_17", "high", "experiment_17", "The final entry reads: **It has learned the door.** The last page is dated today.", -11, "containment"),
            choice("🔒 Check the nearest door", "door", "medium", "The handle is warm. Something on the other side taps twice.", -6, next_scene="containment", effects={"checked_door": True}),
            choice("🏃 Leave the lab", "leave_lab", "low", "The door clicks behind you as soon as you step away.", -2, next_scene="containment", effects={"left_lab": True}),
        ]),
        "containment": scene("containment", "An empty containment chamber stands behind thick glass. Fingerprints cover the inside walls.", [
            discovery_choice("🔬 Examine the chamber", "containment", "extreme", "containment_chamber", "The chamber is empty, but the fingerprints are fresh. A second set appears while you watch.", -15, "archives"),
            choice("🖐️ Examine the fingerprints", "prints", "high", "Some prints are fresh enough to smear under your glove.", -8, next_scene="archives", effects={"examined_prints": True}),
            choice("🚪 Keep moving", "keep_moving", "low", "The chamber lights turn off as you pass.", -3, next_scene="archives", effects={"ignored_chamber": True}),
        ]),
        "archives": scene("archives", "The archive contains redacted files, old incident reports, and a single terminal that has somehow remained connected to the outside world.", [
            pet_choice("📱 Open the MalO terminal — 🐾 Pet Discovery", "malo", "high", "The application shows a sequence of photographs. The newest image was taken just now. MalO is already standing somewhere behind you.", -8, "malo_incident", effects={"met_malo": True, "malo_seen": True}),
            discovery_choice("📄 Read the redacted file", "redacted", "high", "redacted_file", "Every page is redacted except: **DO NOT LET IT KNOW YOU CAN SEE IT.** A second sentence appears: **Too late.**", -12, "malo_incident"),
            choice("🗃️ Close the archives", "close_archives", "low", "You leave the files untouched. The terminal remains connected.", -2, next_scene="malo_incident", effects={"closed_archives": True}),
        ]),
        "malo_incident": scene("malo_incident", "The terminal displays MalO ver1.0.0. A photograph appears. Then another. The figure is closer each time.", [
            discovery_choice("📱 Open the newest photograph", "malo_photo", "extreme", "malo_incident", "The newest image was taken from somewhere you cannot see. The figure is closer than it should be.", -16, "exit"),
            choice("📸 Check the older photographs", "old_photos", "high", "The images become progressively more personal. The final one shows the room you are standing in.", -9, next_scene="exit", effects={"saw_malo_sequence": True}),
            choice("🔌 Shut down the terminal", "shutdown", "medium", "The monitor dies. Your phone camera opens by itself.", -6, next_scene="exit", effects={"shut_malo_terminal": True}),
        ], reactions=[{"all": ["malo_seen"], "text": "You are certain MalO was not beside you a moment ago. You are less certain now."}]),
        "exit": scene("exit", "The emergency exit leads to the portal. Behind you, the facility begins shutting down sector by sector.", [
            choice("🚪 Leave", "leave", "low", "You reach the portal. The facility disappears into darkness.", 0, next_scene="ending"),
            choice("📱 Check your phone one last time", "phone", "high", "A new photograph is waiting. You are standing in the station already.", -9, next_scene="ending", effects={"checked_phone_again": True}),
            choice("👁️ Look back", "look_back", "high", "The corridor is empty. A single emergency light turns toward you as though it has a head.", -7, next_scene="ending", effects={"looked_back": True}),
        ]),
        "ending": scene("ending", "The portal closes. Your phone is quiet again. For now.", [
            choice("🌀 Return", "return", "low", "You return to the station. The screen on your phone stays black.", 0, end=True, ending_title="Containment Failed"),
            choice("📱 Keep the phone", "keep_phone", "medium", "You decide not to delete the application. You are not sure whether that was your choice.", -4, end=True, ending_title="Still Installed"),
            choice("🔌 Shut everything down", "shut_down", "high", "You power off every device you can reach before leaving the portal room.", -7, end=True, ending_title="No Signal"),
        ], reactions=[{"all": ["met_malo"], "text": "MalO remains a quiet presence on your device. You do not remember giving her permission to stay."}]),
    },
)
