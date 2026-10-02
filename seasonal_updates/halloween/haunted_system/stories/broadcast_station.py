from ..story_helpers import choice, discovery_choice, pet_choice, scene, story

STORY = story(
    "broadcast_station",
    "Abandoned Broadcast Station",
    {
        "normal": "The portal opens in a control room filled with dead monitors. Every screen shows the same empty hallway. A red RECORDING light is already on.",
        "low": "The monitors show the hallway you are standing in, but none show you. The station seems to be waiting for a signal.",
        "insane": "Every monitor shows you standing in the station. You are not in any of them.",
    },
    {
        "control": scene("control", "A console printer spits out a strip of paper: **PLEASE STOP LISTENING TO YOURSELF.** The timestamp is five minutes in the future.", [
            choice("📺 Watch the future feed", "future_feed", "medium", "The feed catches up to you one movement at a time.", -6, next_scene="studio", effects={"watched_future": True}),
            choice("🎙️ Enter the studio", "studio", "medium", "The RECORDING light follows you down the hall.", -4, next_scene="studio", effects={"entered_studio": True}),
            choice("🔌 Shut down the console", "shutdown", "low", "The console dies. One monitor remains powered.", -2, next_scene="studio", effects={"shut_console": True}),
        ]),
        "studio": scene("studio", "A locked studio door has a sign: **RECORDING IN PROGRESS**. No one answers when you knock.", [
            discovery_choice("🚪 Enter the studio", "camera", "high", "impossible_camera", "A camera feed shows an empty hallway. Then the image changes to show you from somewhere you cannot see.", -12, "archive"),
            choice("🎧 Listen through the door", "listen", "medium", "The room contains your breathing, even though you are standing outside it.", -6, next_scene="archive", effects={"heard_recording": True}),
            choice("🚶 Leave the studio", "leave", "low", "The RECORDING light turns off when you stop looking at it.", -2, next_scene="archive", effects={"avoided_studio": True}),
        ]),
        "archive": scene("archive", "The archive room contains reels, tapes, and a shelf labeled **CHANNEL 0**. One monitor is already tuned there.", [
            discovery_choice("📡 Tune to Channel 0", "channel_zero", "high", "channel_zero", "Channel 0 shows a hallway that does not exist in the station. Something is walking toward the camera.", -11, "signal"),
            choice("📼 Check the archive logs", "logs", "medium", "Every log ends with the same phrase: **'Do not broadcast the reply.'**", -5, next_scene="signal", effects={"read_logs": True}),
            choice("🔌 Pull the monitor plug", "pull_plug", "low", "The monitor turns off. The unplugged screen keeps showing static for three seconds.", -3, next_scene="signal", effects={"unplugged_monitor": True}),
        ]),
        "signal": scene("signal", "The station suddenly becomes quiet. Even the electrical hum stops. A tiny figure appears on every monitor at once.", [
            pet_choice("📻 Follow the static figure — 🐾 Pet Discovery", "dead_air", "medium", "The static clears just long enough to reveal a tiny broadcast entity beside you. It crackles softly, as if saying hello.", -3, "emergency", effects={"met_dead_air": True}),
            choice("🎙️ Speak into the microphone", "microphone", "high", "Your own voice answers through every speaker in the building.", -8, next_scene="emergency", effects={"spoke_on_air": True}),
            choice("🔇 Stay silent", "silent", "low", "The static fades. For the first time, the station sounds empty.", 1, next_scene="emergency", effects={"stayed_silent": True}),
        ]),
        "emergency": scene("emergency", "An emergency tone begins. The announcement that follows is only your breathing.", [
            discovery_choice("🎙️ Listen to the full announcement", "emergency_broadcast", "high", "emergency_broadcast", "The station announces an emergency that has not happened yet. Your name is listed among the missing.", -13, "transmitter"),
            choice("📺 Turn up the volume", "volume", "medium", "The breathing becomes a whisper. It tells you to leave before the broadcast ends.", -6, next_scene="transmitter", effects={"heard_warning": True}),
            choice("🚪 Leave the booth", "leave_booth", "low", "You walk away. The announcement follows you through the hallway.", -2, next_scene="transmitter", effects={"left_booth": True}),
        ]),
        "transmitter": scene("transmitter", "The main transmitter is still running. Its display shows a single destination: **HOME**.", [
            choice("🔌 Shut it down", "shutdown", "medium", "The transmitter dies. The station becomes silent.", -3, next_scene="ending", effects={"stopped_transmitter": True}),
            choice("🎙️ Send one final message", "final_message", "high", "You say goodbye. The station replies with the sound of you saying goodbye from somewhere else.", -8, next_scene="ending", effects={"sent_message": True}),
            choice("🚪 Leave it running", "leave_running", "low", "You decide some signals are safer unanswered.", 1, next_scene="ending", effects={"left_signal": True}),
        ]),
        "ending": scene("ending", "The portal glows in the control room. Every monitor now shows it from a different angle.", [
            choice("🌀 Return", "return", "low", "You step through. The last monitor turns off behind you.", 0, end=True, ending_title="Off the Air"),
            choice("📺 Watch one last screen", "screen", "high", "The screen shows you returning to the station before you actually do.", -7, end=True, ending_title="Still Broadcasting"),
            choice("🔌 Cut the master power", "master_power", "medium", "The station goes dark all at once. The portal remains visible in the darkness.", -4, end=True, ending_title="Dead Air"),
        ], reactions=[{"all": ["met_dead_air"], "text": "Dead-Air crackles beside you until the portal closes, then the static stops."}]),
    },
    signal_scene="signal",
)
