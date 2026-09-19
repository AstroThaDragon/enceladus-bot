"""Halloween seasonal content for Enceladus.

Edit the placeholder entries below to add the Halloween-themed Space Junk.
The event is active from October 5 through November 5, Eastern Time.
"""

from datetime import datetime
import pytz
from emojis import EMOJIS

EVENT_NAME = "Halloween"
EVENT_START_MONTH = 10
EVENT_START_DAY = 5
EVENT_END_MONTH = 11
EVENT_END_DAY = 5

# Chance that a scavenging run also finds one Halloween Space Junk item.
# This is an independent bonus roll, so normal scavenging loot is unaffected.
BONUS_ROLL_CHANCE = 0.15

# Independent seasonal bonus rolls during the active event.
CANDY_CHANCE = 0.30
PLASTIC_CHANCE = 0.20
TRICK_OR_TREAT_BAG_CHANCE = 0.10
# Independent pet egg roll. This only runs while Halloween is active.
HALLOWEEN_PET_EGG_CHANCE = 0.025
HALLOWEEN_PET_CANDY_CHANCE = 0.12
PLASTIC_MIN = 4
PLASTIC_MAX = 10

# ---------------------------------------------------------------------------
# HALLOWEEN SPACE JUNK
# ---------------------------------------------------------------------------
# Format:
# (item_id, name, emoji, description, stardust_sell_value, candy_sell_reward)
#
# Everything for each junk item lives together here, so you only need to edit
# one entry when creating or balancing a Halloween collectible.
HALLOWEEN_SPACE_JUNK = [
    ("one_wish_willow", "One Wish Willow", EMOJIS["one_wish_willow"], "Amaze your friends! You only get one wish. Spark the middle and break in half.", 25, 1),
    ("fabric_web", "Fabric Web", "🕸️", "Definitely not from a spider, that's for sure.", 10, 5),
    ("paper_ghost", "Paper Ghost", "👻", "*Spooky noises*.", 10, 5),
    ("skeleton_prop", "Skeleton Prop", "🦴", "**RATTLED**", 15, 5),
    ("fake_clown", "Fake Clown", "🤡", "*Honk honk*", 20, 5),
    ("plastic_bat", "Plastic Bat", "🦇", "It's gonna suck your d- I mean blood.", 15, 7),
    ("pumpkin", "Pumpkin", "🎃", "A great way to hide from an Enderman!", 25, 3),
    ("plastic_pumpkin", "Plastic Pumpkin", "🎃", "Throw it at your siblings head for fun!", 10, 4),
    ("fake_candle", "Fake Candle", "🕯️", "The batteries die within hours! How lovely!", 10, 8),
    ("plastic_spider", "Plastic Spider", "🕷️", "Imagine we're arguing and I throw a spider at you.", 10, 5),
    ("witch_cauldron", "Witch's Cauldron", EMOJIS["witch_cauldron"], "Good soup!", 25, 4),
    ("prop_knife", "Prop Knife", "🔪", "Won't cut you... probably.", 10, 10),
    ("crystal_ball", "Crystal Ball", "🔮", "I am the fortune teller. I am the teller of your fortune.", 30, 5),
    ("jack_o_lantern", "Jack O' Knife", "🎃", "A Jack O' Lantern with a knife in it. The Boogeyman's Jack O' Lantern.", 30, 7),
    ("pickle", "A Pickle", "🥒", "I've come for your pickle... 🦑", 15, 2),
    ("hockey_mask", "Broken Hockey Mask", EMOJIS["hockey_mask"], "It feels wet... almost like it was underwater.", 40, 6),
    ("red_balloon", "Red Balloon", "🎈", "It's still floating. **You'll float, too.**", 30, 8),
    ("vampire_doll", "Bald Vampire Doll", "🧛‍♂️", "Careful, it might bite! Blood is life.", 25, 4),
    ("broken_phone", "Broken Phone", "📞", "It still rings. **The call is coming from within the ship...**", 50, 10),
    ("old_tv", "Old Staticy TV", "📺", "You can faintly hear a little girl whispering 'they're heeereee...'", 60, 12),
    ("vhs_tape", "Old VHS Tape", "📼", "You will die in seven days...", 25, 5),
    ("key_tag", "Red Key Tag", "🏷️", "A red key tag, with the numbers '237' on it.", 20, 7),
    ("broken_chainsaw", "Broken Chainsaw", EMOJIS["broken_chainsaw"], "A heavy broken saw. Faintly etched along the guide bar are the words, 'The Saw is Family.'", 65, 15),
    ("scissor_hand_glove", "Scissor Hand Glove", "✂️", "A glove with sharp scissor blades for fingers.", 40, 8),
    ("puzzle_box", "Unknown Puzzle Box", EMOJIS["puzzle_box"], "We have such sights to show you.", 80, 15),
    ("proton_pack", "Proton Pack?", EMOJIS["proton_pack"], "Who you gonna call??", 100, 15),
    ("broken_camcorder", "Broken Camcorder", EMOJIS["broken_camcorder"], "It is a biological necessity. You see, I am a doctor.", 85, 12),
    ("necronomicon", "Suspiciously Evil Book", "📕", "A suspicious book. It looks like it has a face on it. Probably shouldn't recite what's inside...", 50, 16),
    ("large_bolts", "Large Bolts", "🔩", "Very large bolts. Looked like they'd go into a neck...?", 75, 20),
    ("toilet_paper", "Suspicious Toilet Paper", "🧻", "An ancient roll of paper. Darkened and dirty. Looks like it wrapped around someone.", 35, 10),
    ("porcelain_doll", "Broken Porcelain Doll", EMOJIS["porcelain_doll"], "A broken porcelain doll, who's energy is darker than anything we've seen...", 120, 25),
    ("red_headed_doll", "Red-headed Doll", EMOJIS["red_headed_doll"], "We're friends till the end... remember?", 100, 15),
    ("spooky_razor", "Spooky-looking Razor", "🪒", "The closest shave you'll ever know.", 75, 12),
    ("ouija_board", "A Ouija Board", EMOJIS["ouija_board"], "What an excellent day for an exorcism.", 100, 25),
    ("hand", "Sentient Hand", "🫳", "*The hand uses sign-language to say, 'You're a handful.'", 135, 20),
    ("bloodied_knife", "Bloodied Knife", "🔪", "A knife full of blood. You can faintly hear someone say 'go to sleep...'", 75, 10),
    ("bloody_ring", "Blood-soaked Gold Ring", EMOJIS["gold_ring"], "Do you want to play with me?", 90, 15),
    ("lost_page", "A Lost Page", "📄", "*Static noises*", 45, 5),
    ("tribal_mask", "Red Tribal Mask", EMOJIS["tribal_mask"], "Can't break the rules. ***RUN.***", 85, 10),
    ("hacked_phone", "Hacked Phone", "📱", "It doesn't want to hurt you. It just wants to make sure you never feel lonely again.", 100, 20),
    ("hair_trimmer", "Crazed Hair Trimmer", EMOJIS["hair_trimmer"], "Hello, new friend. My name is Fred. The words you hear are in my head.", 35, 8),
    ("mysterious_slab", "Mysterious Slab", EMOJIS["mysterious_slab"], "Return his slab, or suffer his curse.", 90, 10),
    ("marker", "Unknown Alien Artifact",  "**Make us whole.**", 100, 15),
    ("cupcake", "Cupcake with Eyes", "🧁", "Was a loving companion in the game. But was a violation in the movie. :(", 40, 12),
    ("old_wallpaper", "Old Wallpaper", EMOJIS["old_wallpaper"], "This shouldn't exist.", 65, 15),
    ("toy_remote", "Red Toy Remote", EMOJIS["toy_remote"], "Thank you for using our 'Limited-Time Imaginary Friend' remote! We hope you enjoy the next 2 days with your very own real, not-so-imaginary, friend!", 35, 10),
    ("dead_turtle", "Really Dead Turtle", EMOJIS["dead_turtle"], "It's been dead for *much* too long.", 75, 10),
    ("tails_doll", "A Doll of Tails", EMOJIS["doll_gem"], "Can you feel the sunshine?", 85, 10),
    ("coffee_mug", "Coffee Mug with Sticky Note", "☕", "A 'normal' coffee mug with a sticky note that reads 'Not a Mimic!'", 35, 8),
    ("pill_bottle", "Painkillers", EMOJIS["pill_bottle"], "It's the best decision I'll ever make.", 35, 15),
    ("bear_skull", "Bear Plush with Exposed Skull", "🐻", "*You say something to it. It repeats it right back...*", 65, 10),
]

def get_sell_reward(item_id):
    """Return (Stardust, Halloween Candy) for a Halloween Space Junk item."""
    for junk_id, _name, _emoji, _desc, stardust, candy in HALLOWEEN_SPACE_JUNK:
        if junk_id == item_id:
            return stardust, candy
    return None


# ---------------------------------------------------------------------------
# HALLOWEEN DAMAGE / KNOCKOUT FLAVOR
# ---------------------------------------------------------------------------
# These only change the flavor text. Damage amounts and hazard weights remain
# controlled by exploration.py.
# Damage messages start with "you" and their format is
# Message, minimum damage, maximum damage.
# Knockout Reports are messages on their own.
HALLOWEEN_DAMAGE_MESSAGES = [
    ("were ambushed by a swarm of space bats", 8, 14),
    ("opened a door marked 'definitely not haunted.' It was", 5, 10),
    ("were startled by something crawling across your helmet", 3, 8),
    ("accidentally disturbed a very angry space ghost", 10, 18),
    ("were pelted by flying Halloween decorations", 4, 9),
    ("ran into a paper ghost", 2, 5),
    ("saw a spider and ran into a wall", 8, 10),
    ("heard knocking from inside your helmet", 6, 12),
    ("followed a strange whisper into a maintenance tunnel", 7, 15),
    ("opened a locker and found something breathing inside", 9, 17),
    ("stepped on a suspiciously squishy alien object", 4, 9),
    ("were chased down a hallway by a pumpkin with legs", 5, 11),
    ("were attacked by a swarm of extremely rude bats", 6, 13),
    ("mistook a station mannequin for a ghost", 3, 7),
    ("saw something move in the corner of your visor", 7, 14),
    ("heard your name whispered from an empty corridor", 8, 16),
    ("were grabbed by a suspiciously cold hand", 10, 18),
    ("opened the wrong airlock. Thankfully, it was the spooky one", 5, 10),
    ("tripped over a skeleton that absolutely wasn't there a second ago", 4, 8),
    ("were ambushed by a haunted maintenance drone", 7, 15),
    ("disturbed a nest of tiny space spiders", 6, 12),
    ("were attacked by a pumpkin that rolled uphill", 5, 9),
    ("accidentally made eye contact with something in the darkness", 9, 17),
    ("heard a child's laughter over the station intercom", 8, 16),
    ("followed a floating candy wrapper into a very dark room", 4, 10),
    ("were chased by a ghost wearing a tiny cowboy hat", 5, 11),
    ("tried to pet a strange creature. It did not appreciate this", 6, 13),
    ("opened a crate labeled 'DO NOT OPEN.' Naturally, you opened it", 7, 14),
    ("were startled by your own reflection", 2, 6),
    ("found a handprint appear on the inside of your visor", 10, 18),
    ("were attacked by an angry inflatable Halloween decoration", 3, 8),
    ("heard a noise behind you and turned around way too slowly", 7, 13),
    ("were haunted by the ghost of a particularly judgmental janitor", 5, 10),
    ("walked directly into a cobweb the size of a satellite dish", 4, 9),
    ("were bitten by something that immediately apologized", 6, 11),
    ("accidentally interrupted a skeleton's lunch break", 5, 12),
    ("were chased by a possessed Roomba", 4, 9),
    ("were attacked by a Halloween decoration that was supposed to be motion-activated", 5, 10),
    ("heard a voice say 'behind you' over the radio", 9, 17),
    ("were jumpscared by a cardboard cutout", 2, 5),
    ("found a pumpkin staring at you. It blinked", 8, 15),

    # 👽 Alien
    ("heard something skittering inside the ventilation system", 6, 12),
    ("checked your motion tracker. It checked you back", 8, 16),
    ("opened a maintenance panel and immediately regretted it", 7, 15),
    ("discovered that something had been nesting inside the station", 9, 17),
    ("heard a wet clicking sound directly behind you", 10, 18),

    # 🔧 Dead Space
    ("found a strange alien artifact and immediately touched it", 8, 16),
    ("were attacked by something that really did not want to stay dead", 10, 18),
    ("heard the station whisper your name through the vents", 8, 17),
    ("accidentally wandered into what was definitely not a Unitology meeting", 5, 11),
    ("tried to go through a broken door without stasis. You got hit rather hard", 9, 16),

    # 🎃 Trick 'r Treat
    ("heard a tiny sack-covered figure giggling somewhere nearby", 7, 14),
    ("apparently failed the station's unofficial trick-or-treating etiquette", 6, 13),
    ("found a pumpkin that seemed very interested in whether you blew out its candle", 8, 15),
    ("were followed by a suspiciously small Halloween enthusiast", 5, 10),

    # 🦖 Godzilla
    ("heard a roar that was definitely too large to come from the station", 8, 16),
    ("were caught in the shockwave of something stomping outside", 10, 18),
    ("looked out the window and immediately wished you hadn't", 7, 15),
    ("accidentally wandered into a giant monster's personal space", 9, 17),

    # 🐻 FNAF
    ("checked a security camera and saw something standing where nobody was", 7, 14),
    ("switched camera feeds just in time to see something move", 8, 16),
    ("heard footsteps approaching from the dark hallway", 6, 13),
    ("were attacked by a mascot that really should have been powered off", 8, 15),

    # 💣 Minecraft
    ("heard a suspicious little hiss behind you", 10, 18),
    ("turned around and discovered that the green thing was already too close", 12, 20),
    ("accidentally looked at something you probably shouldn't have", 6, 14),
    ("heard a familiar blocky explosion from somewhere down the corridor", 8, 15),

    # 🏒 Friday the 13th
    ("noticed a hockey mask hanging at the end of the hallway", 6, 12),
    ("saw a very tall figure standing completely motionless in the distance", 8, 16),
    ("turned around and discovered that the hallway had somehow gotten longer", 7, 14),
    ("heard a machete scrape against the station floor", 9, 17),

    # 🧪 SCP
    ("were forced to file an incident report with Site-██", 5, 11),
    ("looked away from a suspicious statue for exactly one second", 10, 18),
    ("opened a containment chamber marked 'DO NOT OPEN'", 8, 16),
    ("were informed that your current situation is now classified", 6, 12),
    ("heard the intercom announce a containment breach", 9, 17),
    ("grabbed your phone, took a picture, and saw a skull-faced wolf behind you in it for a split second", 10, 15),

    # 📺 The Ring
    ("found a strange videotape labeled 'DO NOT WATCH'", 6, 12),
    ("watched a monitor flicker before displaying a very wet hallway", 7, 15),
    ("received a mysterious video file with no sender attached", 8, 16),
    ("heard static coming from a television that wasn't plugged in", 6, 13),

    # 🌫️ Silent Hill
    ("the station lights went out and the fog rolled in", 7, 15),
    ("heard a distant siren despite being nowhere near a siren", 8, 16),
    ("followed a radio signal that became increasingly less reassuring", 6, 13),
    ("found a hallway that definitely wasn't on the station's blueprint", 9, 17),

    # 🎃 Halloween / Michael Myers
    ("noticed someone standing at the end of the hallway", 7, 14),
    ("looked away for a moment and the figure was suddenly closer", 9, 17),
    ("heard slow footsteps approaching from somewhere behind you", 8, 16),
    ("turned around and found absolutely nobody there. Yet.", 6, 13),

    # 🧊 The Thing
    ("noticed that one of your crewmates was behaving... strangely", 8, 16),
    ("watched something imitate a crewmate a little too convincingly", 10, 18),
    ("discovered that the thing in the freezer was not supposed to be alive", 9, 17),
    ("were attacked by something that had far too many limbs", 10, 19),

    # 👁️ DOORS / Pressure vibes
    ("the lights flickered three times and you immediately regretted everything", 6, 13),
    ("heard something charging down the corridor at an unreasonable speed", 9, 17),
    ("saw the hallway lights go out one by one behind you", 8, 16),
    ("heard a door slam somewhere very, very far away", 5, 11),

    # 👻 Enceladus-specific chaos
    ("asked the station AI if the hallway was haunted. It said 'yes.'", 5, 10),
    ("followed a trail of candy directly into a maintenance shaft", 4, 9),
    ("mistook the station's emergency lighting for spooky ambience", 2, 6),
    ("were attacked by a pumpkin someone had inexplicably weaponized", 7, 13),
    ("heard something growling and discovered it was just the vending machine", 3, 6),
    ("were jumpscared by a maintenance bot wearing a bedsheet", 2, 5),
    ("tried to scare a ghost. The ghost scared you harder", 6, 12),
    ("were distracted by free candy and walked directly into a wall", 4, 8),
    
]

HALLOWEEN_KNOCKOUT_LINES = [
    "The station medic has officially classified the incident as 'extremely spooky.'",
    "A nearby ghost gave you a concerned thumbs-up before disappearing.",
    "Your helmet camera saved the footage under 'definitely_not_haunted.mp4'.",
    "The station AI has filed your incident under: 'Halloween was a bad time to explore.'",
    "A tiny skeleton waved at you as you hit the floor. Rude.",
    "The last thing you remember was hearing 'boo.' Very professional.",
    "Your final transmission was just a very loud 'NOPE.'",
    "The medical team assures you that the ghost was probably not real. Probably.",
    "A pumpkin rolled past your unconscious body. Nobody knows why.",
    "You have been temporarily defeated by the concept of Halloween.",
    "The station security footage has been classified as 'too embarrassing to review.'",
    "Someone placed a tiny 'GET WELL SOON' sign beside you. It has a skull on it.",
    "Your emergency contact has been notified. They laughed.",
    "The station AI would like to remind you that screaming does not improve survival odds.",
    "You were defeated by something the maintenance crew insists is 'not their problem.'",
    "A skeleton nearby checked your pulse, shrugged, and walked away.",
    "You woke up just long enough to hear someone whisper 'skill issue.'",
    "The medical scanner detected blunt-force trauma and an unusually high level of cowardice.",
    "Your helmet has been found. Your dignity has not.",
    "The station has logged your defeat as: 'Extremely avoidable.'",
    "A ghost has filed a noise complaint against you.",
    "Your last known location has been marked with a tiny pumpkin.",
    "The emergency medical drone arrived, looked at you, and played spooky music.",
    "You have been knocked unconscious. The good news is that the spider is also gone.",
    "The station medic asked what happened. You pointed at the darkness. They understood.",

    # Reference-ish knockouts
    "The motion tracker stopped beeping. You did not.",
    "Your plasma cutter is still on the floor. You're not.",
    "The security cameras have officially decided they didn't see anything.",
    "The station AI has classified you as 'temporarily deceased-ish.'",
    "The containment team has been notified. They sound extremely tired.",
    "The VHS player ejected the tape and refused to elaborate.",
    "The radio went silent. Somehow, that was worse.",
    "Your crewmate insists there was never anything behind you.",
    "The giant monster outside appears to have continued walking.",
    "You have been removed from the Halloween party for excessive screaming.",
]


def is_active(now=None) -> bool:
    """Return whether Halloween is currently active in Eastern Time."""
    eastern = pytz.timezone("US/Eastern")
    if now is None:
        now = datetime.now(eastern)
    else:
        now = now.astimezone(eastern)

    current = (now.month, now.day)
    start = (EVENT_START_MONTH, EVENT_START_DAY)
    end = (EVENT_END_MONTH, EVENT_END_DAY)

    return start <= current <= end


def get_space_junk():
    """Return Halloween Space Junk definitions for the active event."""
    return HALLOWEEN_SPACE_JUNK if is_active() else []


# Seasonal crafting/healing items. These are not Space Junk collectibles.
HALLOWEEN_ITEMS = {
    "halloween_candy": {
        "name": "Halloween Candy",
        "emoji": "🍬",
        "max_quantity": 99,
        "type": "Consumable",
        "desc": "Seasonal candy recovered during Halloween. Restores +5 HP when eaten with /heal.",
    },
    "halloween_plastic": {
        "name": "Halloween Themed Plastic",
        "emoji": "🧴",
        "max_quantity": 99,
        "type": "Crafting Material",
        "desc": "Flexible plastic salvaged from abandoned Halloween decorations and containers. Used to craft Trick-or-Treat Bags.",
    },
    "trick_or_treat_bag": {
        "name": "Trick-or-Treat Bag",
        "emoji": "🎃",
        "max_quantity": 25,
        "type": "Consumable",
        "desc": "A handmade Halloween treat bag. Open it with /heal to chow down on candy and restore +25 HP.",
    },
    "halloween_pet_candy": {
        "name": "Halloween Pet Candy",
        "emoji": "🍬",
        "max_quantity": 99,
        "type": "Pet Treat",
        "desc": "A special Halloween treat for pets. Gives a large chunk of Pet XP.",
    },
    "halloween_egg": {
        "name": "Halloween Pet Egg",
        "emoji": "🥚",
        "max_quantity": 10,
        "type": "Pet Egg",
        "desc": "A mysterious seasonal egg containing a Halloween pet. Incubate for 12 hours.",
    },
}

COLLECTIBLE_CATEGORY = "Halloween"

def get_collectibles():
    return [(item_id, name, emoji, desc) for item_id, name, emoji, desc, _stardust, _candy in HALLOWEEN_SPACE_JUNK]
