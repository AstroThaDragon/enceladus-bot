from ..story_helpers import choice, discovery_choice, pet_choice, scene, story

STORY = story(
    "silent_campground",
    "The Silent Campground",
    {
        "normal": "The portal opens beside an abandoned campground. No insects buzz. No wind moves the trees. A ranger radio emits a single burst of static.",
        "low": "The silence is complete enough to hear your own heartbeat. Something moves whenever you stop listening for it.",
        "insane": "The campground is full of tents. Every tent is occupied. Every occupant is sitting perfectly still, facing the tree line.",
    },
    {
        "campsite": scene("campsite", "The main campsite contains a dead fire ring, a ranger radio, and a trail camera pointed directly at the tents.", [
            choice("📻 Turn on the ranger radio", "radio", "medium", "A voice whispers, **Do not look into the trees.** The radio clicks off.", -6, next_scene="photograph", effects={"heard_radio": True}),
            choice("📹 Check the trail camera", "camera", "high", "The camera's red light turns on when you approach. The display shows you arriving ten minutes ago.", -8, next_scene="photograph", effects={"checked_camera": True}),
            choice("🏕️ Search the campsite", "search", "low", "You find an old notebook with several pages torn out.", -2, next_scene="photograph", effects={"found_notebook": True}),
        
                choice('🧵 Check beneath the fire ring', 'fire_ring', 'medium', 'A red thread is buried beneath the cold ash. It leads toward the trees and is tied around a broken tent peg.', -6, next_scene='photograph', effects={"story_fire_ring": True}),
            ]),
        "photograph": scene("photograph", "A photograph lies face-down beside the fire ring. The trees behind the campsite look strangely close.", [
            discovery_choice("📸 Look at the photograph", "photo", "high", "moving_photograph", "The photograph contains a tall figure between the trees. Each time you look again, it is closer.", -12, "notebook"),
            choice("🖼️ Turn it over", "turn_photo", "medium", "A message is written on the back: **DON'T LOOK UP.**", -5, next_scene="notebook", effects={"read_photo_message": True}),
            choice("🏃 Put it down", "leave_photo", "low", "The photograph is gone when you look back.", -2, next_scene="notebook", effects={"left_photo": True}),
        
                choice('📸 Compare the photograph to the campsite', 'photo_compare', 'high', 'The photograph shows the same campsite from a different year. A person stands behind the tent. You are standing where they stood.', -9, next_scene='notebook', effects={"story_photo_compare": True}),
            ]),
        "notebook": scene("notebook", "The ranger station contains a notebook filled with drawings of the campground. The same tall figure appears in every page.", [
            discovery_choice("📓 Read the final page", "ranger", "high", "ranger_notebook", "The final line reads: **Don't look toward the trees.** Branches move behind you.", -11, "watcher"),
            choice("🔥 Burn the notebook", "burn", "medium", "The pages burn without heat. Static pours from the smoke.", -7, next_scene="watcher", effects={"burned_notebook": True}),
            choice("🚶 Leave it alone", "leave", "low", "The notebook is back in your backpack moments later.", -3, next_scene="watcher", effects={"kept_notebook": True}),
        
                choice("🖊️ Read the ranger's crossed-out sentence", 'crossed_sentence', 'high', 'Under several layers of ink you can make out: **The cameras do not watch the woods. They watch what comes out.**', -10, next_scene='watcher', effects={"story_crossed_sentence": True}),
            ]),
        "watcher": scene("watcher", "The forest has gone completely silent. Between the trees, something tall shifts its weight.", [
            pet_choice("🌲 Keep walking beside the figure — 🐾 Pet Discovery", "watcher_pet", "high", "A tall silent figure begins walking beside you. It never blinks, but it never touches you either.", -4, "camera", effects={"met_watcher": True}),
            choice("🔦 Sweep the tree line", "sweep", "extreme", "Your flashlight finds nothing. Something taps the back of your headlamp.", -10, next_scene="camera", effects={"searched_trees": True}),
            choice("🤫 Stay on the trail", "trail", "medium", "You keep your eyes forward. Something follows through the brush.", -6, next_scene="camera", effects={"stayed_trail": True}),
        
                choice('🌲 Listen for the second set of footsteps', 'second_steps', 'extreme', 'You hear your own footsteps behind you, perfectly synchronized. Then another set begins, one step slower.', -12, next_scene='camera', effects={"story_second_steps": True}),
            ]),
        "camera": scene("camera", "A second camera sits on the ranger station porch. Its screen shows the campground from directly behind you.", [
            discovery_choice("📷 Check the final recording", "camera_discovery", "extreme", "camera", "The final image shows you from directly behind. The camera is sitting in front of you now.", -14, "exit"),
            choice("🔌 Unplug it", "unplug", "medium", "The camera keeps recording with no battery inside.", -7, next_scene="exit", effects={"unplugged_camera": True}),
            choice("🚶 Leave it recording", "leave_camera", "low", "The red light follows you through the trees.", -3, next_scene="exit", effects={"left_camera": True}),
        
                choice('📹 Review the timestamp', 'camera_time', 'high', 'The recording timestamp is 3:17 AM. The footage shows the campsite empty, then shows someone entering the frame from the direction of the highway.', -10, next_scene='exit', effects={"story_camera_time": True}),
            ]),
        "exit": scene("exit", "The portal waits beyond the campground gate. The trees are motionless now.", [
            choice("🌀 Return", "return", "low", "You step through. The campground is silent until the portal closes.", 0, next_scene="ending"),
            choice("👁️ Look toward the trees", "look", "high", "A tall figure stands between the trees. You are certain it was closer a moment ago.", -8, next_scene="ending", effects={"looked_trees": True}),
            choice("🏃 Run without looking back", "run", "medium", "You run for the portal. Something keeps pace beside you.", -6, next_scene="ending", effects={"ran_from_camp": True}),
        
                choice('🌲 Leave the trail camera facing the woods', 'leave_facing', 'medium', "The camera's red light remains visible after you step through the portal. It blinks three times, as if acknowledging you.", -7, next_scene='ending', effects={"story_leave_facing": True}),
            ]),
        "ending": scene("ending", "The portal closes. The station is loud compared with the campground, and you are grateful for every sound.", [
            choice("🌀 Finish the return", "finish", "low", "You return to the station and refuse to check the nearest window.", 0, end=True, ending_title="Don't Look Behind You"),
            choice("📸 Keep the photograph", "keep_photo", "medium", "The photograph is in your pocket. You decide not to look at it again.", -3, end=True, ending_title="The Watcher Walks With You"),
            choice("🌲 Listen for the forest", "listen", "high", "For one second, the station goes silent. Then something taps on the wall behind you.", -7, end=True, ending_title="Never Alone"),
        
                choice('📻 Listen for the ranger radio after returning', 'radio_after', 'extreme', 'The radio crackles once from somewhere behind you. A voice whispers: **Do not let it follow you home.**', -11, end=True, ending_title='Radio After'),
            ], reactions=[{"all": ["met_watcher"], "text": "The Watcher remains beside the portal until you leave. It never looks away."}]),
    },
)

STORY["opening_variants"] = [
    'The first thing you notice is the lack of insects. Then you realize the trees are not moving either. Somewhere beyond the portal, a ranger radio clicks on and says nothing.',
    'Fresh tire tracks lead toward the campground. They stop at the threshold of the trees. There are no tracks leading back out.',
    'A trail camera mounted near the entrance turns toward you before you step through. Its red indicator flashes once, then the display goes dark.',
]
