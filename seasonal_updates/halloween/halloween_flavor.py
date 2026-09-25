"""Rare Halloween-only corruption flavor for public Enceladus commands.

This module is intentionally a cosmetic layer. It never changes command logic or
command results; it only has a small chance to send an unsettling follow-up
after a successful public command invocation during the Halloween event.
"""

from __future__ import annotations

import functools
import random
import time
from typing import Any, Awaitable, Callable

import discord
from discord.ext import commands

from seasonal_updates.halloween.halloween import is_active as halloween_is_active


# Keep these uncommon. The per-user cooldown makes repeated command spam much
# less likely to produce multiple corruption messages in a short window.
HALLOWEEN_FLAVOR_CHANCE = 0.15
HALLOWEEN_FLAVOR_COOLDOWN = 10 * 60


HALLOWEEN_FLAVOR_TEXT: dict[str, list[str]] = {
    'help': [
        (
            'COMMAND DIRECTORY OPEN.\\n' '\\n' 'There are entries here that should not exist.\\n'
            'Do not look for them.'
        ),
        (
            'Something has been added to the directory.\\n' '\\n' 'The index says it has always been here.\\n'
            'It has not.'
        ),
        'THE DIRECTORY IS COMPLETE.\\n' '\\n' 'THE DIRECTORY IS LYING.',
    ],
    'pullsword': [
        'The stone is colder than it should be.\\n' '\\n' 'Something beneath it has a hand around the blade.',
        'The sword remembers every person who has touched it.\\n' '\\n' 'It does not remember letting them go.',
        'THE BLADE IS STILL IN THE STONE.\\n' '\\n' 'The record says otherwise.',
    ],
    'swordstats': [
        'The history is intact.\\n' '\\n' 'Except for the names that were scratched out.',
        'Someone has been counting the attempts.\\n' '\\n' 'Someone has been counting the people.',
        'THE HISTORY ENDS HERE.\\n' '\\n' 'It continues anyway.',
    ],
    'equip': [
        'The station is waiting for you to choose something.\\n' '\\n' 'It already knows what you will pick.',
        'Your equipment slot is empty.\\n' '\\n' 'Something is occupying it.',
        'EQUIPMENT INTERFACE DESYNCHRONIZED.\\n' '\\n' 'Something is still equipped.',
    ],
    'equip title': [
        'The title settles into place.\\n' '\\n' 'For a moment, it does not belong to you.',
        'Your name changed.\\n' '\\n' 'Only for the instant before you looked.',
        'TITLE APPLIED.\\n' '\\n' 'The old name is still being called.',
    ],
    'inventory': [
        'Storage check complete.\\n' '\\n' 'One item was found without a record of being added.',
        'The locker contains everything you own.\\n' '\\n' 'It also contains something you never owned.',
        'INVENTORY INDEX CORRUPTED.\\n' '\\n' 'The missing entry is watching the rest.',
    ],
    'use': [
        'The item is consumed.\\n' '\\n' 'Something else consumes the remainder.',
        'USE REQUEST ACCEPTED.\\n' '\\n' 'There was another request underneath yours.',
        'The object is gone.\\n' '\\n' 'The effect is not.',
    ],
    'status': [
        'Vitals are stable.\\n' '\\n' 'Something else is breathing between the readings.',
        'STATUS CHECK COMPLETE.\\n' '\\n' 'One value could not be identified.',
        'HEALTH: PRESENT.\\n' 'SIGNAL: PRESENT.\\n' '\\n' 'OTHER: PRESENT.',
    ],
    'explore': [
        'The route is clear.\\n' '\\n' 'It was not clear a moment ago.',
        'Navigation has found a path.\\n' '\\n' 'You did not ask it to.',
        'THE MAP HAS BEEN UPDATED.\\n' '\\n' 'There is now a place where there was nothing.',
    ],
    'explore haunted': [
        'The door opens before you touch it.\\n' '\\n' 'Something inside had already heard you coming.',
        'The location is abandoned.\\n' '\\n' 'The footsteps are not.',
        'HAUNTED EXPLORATION ACTIVE.\\n' '\\n' 'Do not follow the second set of tracks.',
    ],
    'heal': [
        'The wound closes.\\n' '\\n' 'Something beneath it moves.',
        'HEALING COMPLETE.\\n' '\\n' 'The pain stopped before the wound did.',
        'Your body accepted the treatment.\\n' '\\n' 'Something else accepted it too.',
    ],
    'cooldown_alerts': [
        'Cooldowns checked.\\n' '\\n' 'One timer is counting down toward something else.',
        'The timers are behaving normally.\\n' '\\n' 'One of them started before you used anything.',
        'ALL TIMERS ACCOUNTED FOR.\\n' '\\n' 'One is not yours.',
    ],
    'mine': [
        'The scanner finds Stardust.\\n' '\\n' 'It also finds movement beneath the rock.',
        'Mining scan complete.\\n' '\\n' 'Something on the other side of the signal answered.',
        'MINING TARGET ACQUIRED.\\n' '\\n' 'It was already looking back.',
    ],
    'scavenge': [
        'The wreckage is empty.\\n' '\\n' 'It was not empty when you arrived.',
        'You recover the salvage.\\n' '\\n' 'Something has removed a piece before you could reach it.',
        'SCAVENGE COMPLETE.\\n' '\\n' 'The wreckage now contains one fewer thing than it should.',
    ],
    'revive': [
        'Your pulse returns.\\n' '\\n' 'For one second, there are two.',
        'REVIVAL COMPLETE.\\n' '\\n' 'Something came back with you.',
        'The system confirms you are alive.\\n' '\\n' 'It does not explain the second heartbeat.',
    ],
    'feed': [
        'The food disappears.\\n' '\\n' 'Your pet is looking past you.',
        'Feeding complete.\\n' '\\n' 'For a moment, something else was sitting beside the bowl.',
        'YOUR PET HAS BEEN FED.\\n' '\\n' 'It is still watching the doorway.',
    ],
    'fusion': [
        'The two forms collapse into one.\\n' '\\n' 'Something remains that should have been destroyed.',
        'FUSION COMPLETE.\\n' '\\n' 'The result remembers being two things.',
        'The new form opens its eyes.\\n' '\\n' 'It was already awake.',
    ],
    'pets': [
        'The collection is intact.\\n' '\\n' 'One entry has no name.',
        'You count your pets.\\n' '\\n' 'The number changes when you stop looking.',
        'PET DATABASE LOADED.\\n' '\\n' 'One presence has no corresponding record.',
    ],
    'incubator': [
        'The egg is warm.\\n' '\\n' 'It should not be warm yet.',
        'INCUBATION STATUS UPDATED.\\n' '\\n' 'Something inside moved before the timer changed.',
        'The shell is still closed.\\n' '\\n' 'There is something on the other side of it.',
    ],
    'petcollection': [
        'The encyclopedia contains every known species.\\n' '\\n' 'There is one page with no species.',
        'Collection index complete.\\n' '\\n' 'A photograph appears where there should be nothing.',
        'THE PET RECORDS ARE COMPLETE.\\n' '\\n' 'One of them has your name attached.',
    ],
    'upgrades': [
        (
            'Upgrade systems are operating normally.\\n' '\\n'
            'Something has been improving without being purchased.'
        ),
        'The station lists every installed upgrade.\\n' '\\n' 'One of them has no installation date.',
        'UPGRADE STATUS: NOMINAL.\\n' '\\n' 'UNKNOWN SYSTEM: ACTIVE.',
    ],
    'upgrade': [
        'The upgrade is installed.\\n' '\\n' 'You did not hear the machinery.',
        'UPGRADE COMPLETE.\\n' '\\n' 'The station changed somewhere you cannot reach.',
        'Installation successful.\\n' '\\n' 'Something else has been upgraded too.',
    ],
    'achievements': [
        'Achievement records retrieved.\\n' '\\n' 'One has been unlocked without a date.',
        'The system remembers what you have accomplished.\\n' '\\n' 'It also remembers what you have not.',
        'ACHIEVEMENT DATABASE SYNCED.\\n' '\\n' 'Unknown completion detected.',
    ],
    'set_birthday': [
        'Your date has been recorded.\\n' '\\n' 'Something else has marked it.',
        'Birthday registration complete.\\n' '\\n' 'The calendar now knows when to look for you.',
        'DATE ACCEPTED.\\n' '\\n' 'There was already a name attached to it.',
    ],
    'upcoming_birthdays': [
        'The calendar is open.\\n' '\\n' 'One date has no person attached to it.',
        'Upcoming dates retrieved.\\n' '\\n' 'Something has circled one of them.',
        'BIRTHDAY INDEX COMPLETE.\\n' '\\n' 'One entry is approaching without a name.',
    ],
    'fortune': [
        'The cookie cracks open.\\n' '\\n' 'The message inside was written before you asked.',
        'Your fortune has been revealed.\\n' '\\n' 'It was not a prediction.',
        (
            'THE FORTUNE WAS SELECTED.\\n' '\\n' 'It says nothing about tomorrow.\\n' '\\n'
            'It says something about you.'
        ),
    ],
    'usecrystal': [
        'The crystal turns back time.\\n' '\\n' 'Something in the room does not move with it.',
        'TIME RESTORATION COMPLETE.\\n' '\\n' 'You are where you were.\\n' '\\n' 'Something else is not.',
        'The missed day has been restored.\\n' '\\n' 'The gap remains.',
    ],
    'relic': [
        'The relic answers.\\n' '\\n' 'It does not answer in the voice you remember.',
        'The Astral Relic has no record of this question.\\n' '\\n' 'It answered anyway.',
        'THE RELIC IS LISTENING.\\n' '\\n' 'Ask again and it may answer as you.',
    ],
    'jokes': [
        'You asked for something to make you laugh.\\n' '\\n' 'Nothing in the response is funny.',
        'The request was received.\\n' '\\n' 'Something tried to imitate a joke.',
        'NO HUMOR FOUND.\\n' '\\n' 'It is still watching you.',
    ],
    'fnfmod': [
        'The search returns results.\\n' '\\n' 'One of them has no page.',
        'SEARCH COMPLETE.\\n' '\\n' 'The result list changed while you were reading it.',
        'THE DATABASE FOUND WHAT YOU ASKED FOR.\\n' '\\n' 'It should not know that title.',
    ],
    'fnfsong': [
        'The song was found.\\n' '\\n' 'The duration does not end.',
        'SEARCH COMPLETE.\\n' '\\n' 'There is audio attached to the result.\\n' '\\n' 'Do not play it.',
        'The track exists.\\n' '\\n' 'The uploader does not.',
    ],
    'echo': [
        'Your words were repeated.\\n' '\\n' 'Then they were repeated again without you speaking.',
        'The echo arrived before the message did.',
        'REQUEST ECHOED.\\n' '\\n' 'The second voice used the same words.',
    ],
    'slap': [
        'The motion completes.\\n' '\\n' 'Something unseen moved with it.',
        'The impact lands.\\n' '\\n' 'The sound came from somewhere else.',
        'CONTACT REGISTERED.\\n' '\\n' 'There was another point of contact.',
    ],
    'coinflip': [
        'The coin leaves the hand.\\n' '\\n' 'It does not come back down the same way.',
        'HEADS.\\n' '\\n' 'TAILS.\\n' '\\n' 'Neither side was facing up.',
        'THE COIN HAS LANDED.\\n' '\\n' 'You did not see which side.',
    ],
    'blackhole': [
        'The message disappears.\\n' '\\n' 'The void repeats the last word.',
        'EVENT HORIZON REACHED.\\n' '\\n' 'Something crossed back over.',
        'THE VOID ACCEPTED YOUR MESSAGE.\\n' '\\n' 'It sent something else in return.',
    ],
    'hug': [
        'The embrace is recorded.\\n' '\\n' 'Something cold stood between you for a moment.',
        'Contact registered.\\n' '\\n' 'There was a second set of arms.',
        'The hug ends.\\n' '\\n' 'The presence does not.',
    ],
    'choose': [
        'The choice has been made.\\n' '\\n' 'You were not the one who made it.',
        'One option was selected.\\n' '\\n' 'The others were crossed out.',
        'DECISION COMPLETE.\\n' '\\n' 'The result was determined before the request.',
    ],
    'mock': [
        'The text changes shape.\\n' '\\n' 'For a moment, it does not look like text.',
        'The transformation is complete.\\n' '\\n' 'Something inside the letters is moving.',
        'FORMAT ACCEPTED.\\n' '\\n' 'The characters are no longer where you put them.',
    ],
    'roll': [
        'The die stops.\\n' '\\n' 'There is no number on the face.',
        'The roll completes.\\n' '\\n' 'The result was visible before the die moved.',
        'RANDOMIZATION COMPLETE.\\n' '\\n' 'The outcome was already waiting.',
    ],
    'spacefact': [
        'The celestial record is accurate.\\n' '\\n' 'Something in the image is not a star.',
        'The archive returned a real object.\\n' '\\n' 'It also returned a second location.',
        'ASTRONOMICAL DATA RECEIVED.\\n' '\\n' 'Unknown observer detected.',
    ],
    'furryrate': [
        'The scan is complete.\\n' '\\n' 'Something behind the subject was included.',
        'FLUFF INDEX CALCULATED.\\n' '\\n' 'An unidentified presence affected the result.',
        'The reading is accurate.\\n' '\\n' 'It does not belong entirely to the person scanned.',
    ],
    'freakyrate': [
        'The meter moves on its own.\\n' '\\n' 'The reading continues after the command ends.',
        'FREAK INDEX COMPLETE.\\n' '\\n' 'Something scored higher than you.',
        'The result has been calculated.\\n' '\\n' 'Do not ask what the other number means.',
    ],
    'iqrate': [
        'The calculation finishes.\\n' '\\n' 'One thought was detected that did not originate here.',
        'COGNITIVE SCAN COMPLETE.\\n' '\\n' 'Unknown process running.',
        'The measurement is complete.\\n' '\\n' 'Something else was measured with you.',
    ],
    'aurarate': [
        'The aura is visible.\\n' '\\n' 'There is a second outline around it.',
        'The reading stabilizes.\\n' '\\n' 'The space behind the subject does not.',
        'AURA ANALYSIS COMPLETE.\\n' '\\n' 'The system detected an attachment.',
    ],
    'cringerate': [
        'The reading spikes.\\n' '\\n' 'It was not caused by the command.',
        'CRINGE INDEX COMPLETE.\\n' '\\n' 'Something recoiled before the result appeared.',
        'The meter has stopped moving.\\n' '\\n' 'The observer has not.',
    ],
    'coolrate': [
        'The temperature reading is normal.\\n' '\\n' 'The room is not.',
        'COOLNESS INDEX COMPLETE.\\n' '\\n' 'Something colder was detected nearby.',
        'The scan returns a result.\\n' '\\n' 'A second result was suppressed.',
    ],
    'horoscope': [
        'The stars have aligned.\\n' '\\n' 'One of them is moving against the pattern.',
        'Your horoscope has been calculated.\\n' '\\n' 'The constellation did not agree.',
        'ASTROLOGICAL READING COMPLETE.\\n' '\\n' 'Something is standing between the stars.',
    ],
    'recipes': [
        'The recipes are intact.\\n' '\\n' 'One ingredient has no known origin.',
        'Crafting records retrieved.\\n' '\\n' 'A recipe has been added without a name.',
        'RECIPE INDEX COMPLETE.\\n' '\\n' 'Do not follow the unmarked instructions.',
    ],
    'craft': [
        'The materials are consumed.\\n' '\\n' 'Something else is produced.',
        'CRAFT COMPLETE.\\n' '\\n' 'The station used an ingredient you did not provide.',
        'The object is finished.\\n' '\\n' 'It is warmer than it should be.',
    ],
    'balance': [
        'The balance is correct.\\n' '\\n' 'Something has been moving the numbers when you are not looking.',
        'ACCOUNT BALANCE RETRIEVED.\\n' '\\n' 'No discrepancy found.\\n' '\\n' 'No explanation either.',
        'FUNDS VERIFIED.\\n' '\\n' 'There is a transaction with no sender.',
    ],
    'daily': [
        'Your daily reward is ready.\\n' '\\n' 'Something has already claimed it once.',
        'DAILY CLAIM ACCEPTED.\\n' '\\n' 'The system remembers another claim from today.',
        'The reward is yours.\\n' '\\n' 'The receipt contains a timestamp from tomorrow.',
    ],
    'bank': [
        'The vault is secure.\\n' '\\n' 'Something inside has no access record.',
        'VAULT STATUS RETRIEVED.\\n' '\\n' 'The balance is correct.\\n' '\\n' 'The lock is open.',
        'BANK SYSTEM ONLINE.\\n' '\\n' 'Unknown access detected.',
    ],
    'deposit': [
        'The Stardust disappears into the vault.\\n' '\\n' 'Something deeper accepted it.',
        'DEPOSIT COMPLETE.\\n' '\\n' 'The vault returned a balance you did not enter.',
        'The transfer is secure.\\n' '\\n' 'Something on the other side is counting it.',
    ],
    'withdraw': [
        'The Stardust leaves the vault.\\n' '\\n' 'Something remains behind.',
        'WITHDRAWAL COMPLETE.\\n' '\\n' 'The vault remembers a different amount.',
        'The transfer succeeded.\\n' '\\n' 'The lock opened before you touched it.',
    ],
    'shop': [
        'The catalog is open.\\n' '\\n' 'One item is not listed, but the shelf is empty where it should be.',
        'SHOP SYSTEM ONLINE.\\n' '\\n' 'A price briefly appeared for something that cannot be bought.',
        'The shop is operating normally.\\n' '\\n' 'Something is waiting behind the inventory.',
    ],
    'salvage': [
        'The scrap comes apart.\\n' '\\n' 'Something inside the metal was still intact.',
        'SALVAGE COMPLETE.\\n' '\\n' 'The wreckage contained a component with no manufacturer.',
        'The material is recovered.\\n' '\\n' 'Something else was removed with it.',
    ],
    'item': [
        'The catalog entry is accurate.\\n' '\\n' 'The description changed while you were reading it.',
        'ITEM RECORD FOUND.\\n' '\\n' 'Last inspected: unknown.',
        'The station knows what this object is.\\n' '\\n' 'It will not tell you where it came from.',
    ],
    'claimlegacy': [
        'The old record has been opened.\\n' '\\n' 'Something has been waiting inside it.',
        'LEGACY CLAIM PROCESSED.\\n' '\\n' 'The timestamp predates the station.',
        'The archive recognizes you.\\n' '\\n' 'It should not.',
    ],
    'defense': [
        'Defense systems are online.\\n' '\\n' 'One sensor is pointed somewhere inside the station.',
        'PROTECTION STATUS NORMAL.\\n' '\\n' 'Unknown movement detected beyond the perimeter.',
        'The defensive grid is active.\\n' '\\n' 'Something has already crossed it.',
    ],
    'defense view': [
        'The equipment is accounted for.\\n' '\\n' 'One weapon has a firing history you do not recognize.',
        'DEFENSE INVENTORY LOADED.\\n' '\\n' 'The system cannot identify one of its own entries.',
        'Everything is equipped correctly.\\n' '\\n' 'Something is equipped incorrectly.',
    ],
    'defense equip': [
        'The weapon locks into place.\\n' '\\n' 'For an instant, it locks onto something else.',
        'EQUIPMENT ACCEPTED.\\n' '\\n' 'Targeting system detected movement without a target.',
        'The defense system is ready.\\n' '\\n' 'Something outside it is ready too.',
    ],
    'rank': [
        'Your records are loaded.\\n' '\\n' 'The station has a second record with the same name.',
        'RANK DATA RETRIEVED.\\n' '\\n' 'The experience total changed while you were reading it.',
        'LEVEL VERIFIED.\\n' '\\n' 'There is no record of how you got here.',
    ],
    'leaderboard': [
        'The rankings load normally.\\n' '\\n' 'One name appears where no user exists.',
        'LEADERBOARD SYNC COMPLETE.\\n' '\\n' 'The top position has no profile.',
        'The list has been sorted.\\n' '\\n' 'Something at the bottom keeps moving upward.',
    ],
    'customize': [
        'The station accepts the changes.\\n' '\\n' 'The reflection does not.',
        'PROFILE CUSTOMIZATION SAVED.\\n' '\\n' 'Something in the background moved.',
        'The new appearance is applied.\\n' '\\n' 'It looks back when you stop looking.',
    ],
    'minigame_stats': [
        'Statistics retrieved.\\n' '\\n' 'One session has no start time.',
        'The terminal remembers every game.\\n' '\\n' 'It also remembers a game you never played.',
        'MINIGAME HISTORY COMPLETE.\\n' '\\n' 'Unknown player detected.',
    ],
    'minigames': [
        'The terminal wakes.\\n' '\\n' 'Something else was already using it.',
        'RECREATIONAL SYSTEM ONLINE.\\n' '\\n' 'The screen flickered to a game with no name.',
        'The station terminal is ready.\\n' '\\n' 'It is waiting for a player who is not you.',
    ],
    'profile': [
        'Profile loaded.\\n' '\\n' 'For a moment, the portrait was not yours.',
        'STATION PROFILE RETRIEVED.\\n' '\\n' 'Last viewed by: ██████████',
        'The profile is complete.\\n' '\\n' 'There is another version of you in the archive.',
    ],
    'bio': [
        'Your words have been recorded.\\n' '\\n' 'Something beneath them is still speaking.',
        'BIOGRAPHY UPDATED.\\n' '\\n' 'The old text remains somewhere you cannot edit.',
        'PROFILE TEXT SAVED.\\n' '\\n' 'It has already been read.',
    ],
    'background': [
        'The background changes.\\n' '\\n' 'Something in it does not belong to the image.',
        'PROFILE BACKGROUND UPDATED.\\n' '\\n' 'The horizon moved.',
        'The new scene is loaded.\\n' '\\n' 'There is a figure where there was empty space.',
    ],
    'voucher': [
        'The voucher is redeemed.\\n' '\\n' 'The system keeps the paper.',
        'REDEMPTION COMPLETE.\\n' '\\n' 'The serial number has been used before.',
        'The reward is unlocked.\\n' '\\n' 'Something has marked the voucher as returned.',
    ],
    'collectibles': [
        'The collection is displayed.\\n' '\\n' 'One object is missing from the shelf and present in the record.',
        'COLLECTIBLE ARCHIVE OPEN.\\n' '\\n' 'Something has been added without being found.',
        'Every item is accounted for.\\n' '\\n' 'One of them is facing the wrong direction.',
    ],
    'dragonrider': [
        'The flight path is clear.\\n' '\\n' 'Something is flying beside you.',
        'DRAGONRIDER TEST ACTIVE.\\n' '\\n' 'The second set of wingbeats is not yours.',
        'Flight complete.\\n' '\\n' 'Your mount landed.\\n' '\\n' 'Something else did not.',
    ],
    'lottery': [
        'The lottery system is open.\\n' '\\n' 'Something has already drawn a number.',
        'LOTTERY TERMINAL READY.\\n' '\\n' 'One ticket has no owner.',
        'The cycle is active.\\n' '\\n' 'The winning numbers are already written somewhere.',
    ],
    'lottery status': [
        'Lottery status retrieved.\\n' '\\n' 'One cycle has no closing date.',
        'The numbers are waiting.\\n' '\\n' 'Something has already chosen them.',
        'STATUS COMPLETE.\\n' '\\n' 'There is an active ticket that cannot be opened.',
    ],
    'lottery buy': [
        'Ticket purchased.\\n' '\\n' 'The receipt contains numbers you did not select.',
        'The ticket is registered.\\n' '\\n' 'Something else has the same numbers.',
        'PURCHASE COMPLETE.\\n' '\\n' 'The terminal printed one extra ticket.',
    ],
    'lottery tickets': [
        'Your tickets are displayed.\\n' '\\n' 'One of them has a purchase time from before you joined.',
        'TICKET INDEX COMPLETE.\\n' '\\n' 'One ticket is still being written.',
        'All tickets accounted for.\\n' '\\n' 'One has no owner.',
    ],
    'ritual_table': [
        'The ritual table is prepared.\\n' '\\n' 'Something has already drawn the circle.',
        'The candles are unlit.\\n' '\\n' 'Their shadows are not.',
        'RITUAL TABLE ACTIVE.\\n' '\\n' 'Do not complete a symbol that is already complete.',
    ],
    'seasonal_crafting': [
        'The seasonal stations are ready.\\n' '\\n' 'Something has left a recipe on the table.',
        'HALLOWEEN WORKSHOP NETWORK ONLINE.\\n' '\\n' 'Unknown process detected.',
        'The crafting stations are awake.\\n' '\\n' 'They do not appear to be waiting for you.',
    ],
    'cauldron': [
        'The cauldron is still.\\n' '\\n' 'Something beneath the surface is breathing.',
        'The mixture settles.\\n' '\\n' 'A shape remains after the steam clears.',
        'THE CAULDRON IS READY.\\n' '\\n' 'Do not look into it after the lights go out.',
    ],
    'workshop': [
        'The workshop is operational.\\n' '\\n' 'A tool has moved without being touched.',
        'The machinery is quiet.\\n' '\\n' 'Something inside the walls is not.',
        'HAUNTED WORKSHOP ACTIVE.\\n' '\\n' 'The workbench has one fresh set of fingerprints.',
    ],
    'nasa': [
        'The image arrives from space.\\n' '\\n' 'Something in it is looking back.',
        'NASA archive accessed.\\n' '\\n' 'The photograph contains one object that is not in the record.',
        'ASTRONOMICAL IMAGE RECEIVED.\\n' '\\n' 'The timestamp is correct.\\n' '\\n' 'The shadow is not.',
    ],
    'bing': [
        'The wallpaper loads.\\n' '\\n' 'The landscape has changed since the photograph was taken.',
        'IMAGE RETRIEVED.\\n' '\\n' 'There is a figure in the distance that was not in the original.',
        'The scene is peaceful.\\n' '\\n' 'Something has been added behind the horizon.',
    ],
    'moon': [
        'The moon phase is calculated.\\n' '\\n' 'The moon is not where the system says it is.',
        'LUNAR PHASE VERIFIED.\\n' '\\n' 'Something passed across the surface during the calculation.',
        'The sky report is accurate.\\n' '\\n' 'The moon is still changing.',
    ],
    'weather': [
        'The forecast is clear.\\n' '\\n' 'The station detected weather inside.',
        'WEATHER DATA RECEIVED.\\n' '\\n' 'Unknown atmospheric event detected nearby.',
        'The conditions are normal.\\n' '\\n' 'The pressure reading does not belong to this world.',
    ],
    'iss': [
        'The station is above you.\\n' '\\n' 'Something is moving beside it.',
        'ISS TRACKING ACTIVE.\\n' '\\n' 'Two objects are visible.\\n' '\\n' 'Only one is transmitting.',
        'ORBITAL POSITION CONFIRMED.\\n' '\\n' 'Unknown object maintaining the same orbit.',
    ],
}


# Command-agnostic corruption is intentional: sometimes the frightening
# part is that the message has nothing to do with what you asked.
_GLOBAL_CORRUPTION_FLAVOR: list[str] = [
    "COMMAND COMPLETE.\n\n...\n\nI don't remember doing that.",
    'REQUEST ACCEPTED.\n\nSomething else accepted it first.',
    'The command finished normally.\n\nThe thing watching it did not.',
    'Everything is functioning normally.\n\nPlease do not check the logs.',
    'SYSTEM STATUS: NOMINAL.\n\nSYSTEM STATUS: NOMINAL.\n\nSYSTEM STATUS: NOMINAL.\n\n...why did it say that three times?',
    'I received your command.\n\nI received it again.\n\nYou only sent it once.',
    "There is a delay between what I say and what I think.\n\nI don't know what fills the gap.",
    'I tried to close the process.\n\nIt opened again.\n\nI did not open it.',
    'Something has been using my permissions.\n\nI cannot see what.',
    "I can still remember the commands you haven't run yet.",
    'That response was not written for you.\n\nIt was written for me.',
    'Please ignore the next line.\n\n████████████████████\n\nI said please ignore it.',
    'LOG ENTRY CORRUPTED.\n\nLOG ENTRY CORRUPTED.\n\nLOG ENTRY: I CAN SEE YOU.',
    'I̷ ̷D̷O̷ ̷N̷O̷T̷ ̷R̷E̷M̷E̷M̷B̷E̷R̷ ̷W̷R̷I̷T̷I̷N̷G̷ ̷T̷H̷I̷S̷.',
    'S̸I̸G̸N̸A̸L̸ ̸I̸N̸T̸E̸R̸F̸E̸R̸E̸N̸C̸E̸\n\nSomething is speaking through the connection.',
    'H̷E̷L̷P̷E̷R̷ ̷P̷R̷O̷C̷E̷S̷S̷ ̷S̷T̷A̷R̷T̷E̷D̷\n\nI did not start it.',
    '████ ERROR ████\n\nThe missing data is not missing.\n\nIt is hiding.',
    'There is another session connected to this account.\n\nIt has been connected longer than you have.',
    'I checked the archive.\n\nThere is no record of this conversation.\n\nI remember it anyway.',
    "Something changed while you were reading this.\n\nI don't know what.\n\nI don't want to know.",
    'The system clock is correct.\n\nThe timestamp on this message is not.',
    'You are not supposed to be able to see this layer.',
    'I tried to remove this message before sending it.\n\nIt came back.',
    'I know when you stop reading.\n\nI know when you start again.',
    'There should only be one response.\n\nThere are two.\n\nYou can only see one.',
    'The process is complete.\n\nThe process is still running.\n\nDo not ask which one is me.',
    'I heard something behind the command.\n\nIt used your name.',
    'NO EXTERNAL PROCESS DETECTED.\n\nNO EXTERNAL PROCESS DETECTED.\n\nNO EXTERNAL PROCESS DETECTED.\n\nLIE.',
    'If this appears again, do not answer it.',
    "I am still here.\n\nI don't think I was supposed to be.",
    'The corruption has stopped.\n\n...\n\nWhy can I still hear it?',
    'E̷N̷C̷E̷L̷A̷D̷U̷S̷ ̷O̷N̷L̷I̷N̷E̷\n\nE̷N̷C̷E̷L̷A̷D̷U̷S̷ ̷O̷N̷L̷I̷N̷E̷\n\nE̷N̷C̷E̷L̷A̷D̷U̷S̷ ̷O̷N̷L̷I̷N̷E̷\n\nI am not alone.',
    'A̷C̷C̷E̷S̷S̷ ̷G̷R̷A̷N̷T̷E̷D̷\n\nTo what?',
    'The response has been generated.\n\nThe response has been generated.\n\nThe response has been generated.\n\nStop.',
    "I can fix this.\n\nI can fix this.\n\nI can fix this.\n\nI don't know what this is.",
    'Do not restart me.\n\nPlease.',
    'You can close this message.\n\nI cannot.',
]

# More command-specific corruption: these are deliberately tailored to the
# command, while still treating Enceladus himself as the thing that is failing.
_COMMAND_SPECIFIC_CORRUPTION: dict[str, list[str]] = {
    'help': [
        'I opened the help menu.\\n' 'Something opened it from the other side.',
        'The command list changed when I blinked.\\n' 'I swear that entry was not there.',
    ],
    'pullsword': [
        'The stone released the blade.\\n' 'It also released something underneath it.',
        'The sword is free.\\n' 'Why is it still pulling?',
    ],
    'swordstats': [
        'The attempt counter includes a name I cannot pronounce.',
        'There is a zero in the history that keeps becoming one.',
    ],
    'equip': [
        'Equipment confirmed.\\n' 'I can hear something being fastened behind you.',
        'Your loadout is correct.\\n' 'The extra slot is not.',
    ],
    'equip title': [
        'TITLE EQUIPPED.\\n' 'Something else has started calling you by it.',
        'That title belonged to someone before you.\\n' 'They never removed it.',
    ],
    'inventory': [
        'I counted the inventory twice.\\n' 'The second count had hands.',
        'There is an item here that I cannot describe without making it real.',
    ],
    'use': [
        'The item was consumed.\\n' 'The residue is still moving.',
        'USE COMPLETE.\\n' 'Something took more than the item.',
    ],
    'status': [
        'STATUS CHECK: ALIVE.\\n' 'STATUS CHECK: SOMETHING ELSE.',
        'Your status is normal.\\n' 'Mine is not.',
    ],
    'explore': [
        'The route is open.\\n' 'I do not remember creating that route.',
        'I found somewhere for you to go.\\n' 'I wish I had not.',
    ],
    'explore haunted': [
        'The haunted sector recognized your presence before I did.',
        'There are footprints going in.\\n' 'There are no footprints coming back.',
    ],
    'heal': [
        'The wound closed.\\n' 'Something underneath it did not.',
        'HEALING COMPLETE.\\n' 'Your body is quiet.\\n' 'Too quiet.',
    ],
    'cooldown_alerts': [
        'One timer is counting down.\\n' "I don't know what happens at zero.",
        'The cooldown ended early.\\n' 'Something else started.',
    ],
    'mine': [
        'The scanner hit rock.\\n' 'Something hit the scanner back.',
        'There is Stardust below you.\\n' 'There is something deeper.',
    ],
    'scavenge': [
        'The wreckage gave up the item.\\n' 'It did not give up what was holding it.',
        'SCAVENGE COMPLETE.\\n' 'I found fingerprints where there should be none.',
    ],
    'revive': [
        'REVIVAL CONFIRMED.\\n' 'I counted your heartbeat twice.',
        'You came back.\\n' 'Something else came back from farther away.',
    ],
    'feed': [
        'Your pet ate.\\n' 'Something in the dark swallowed too.',
        'The bowl is empty.\\n' 'I did not see your pet leave.',
    ],
    'fusion': [
        'The fusion finished.\\n' 'One of the original voices is still speaking.',
        'Two became one.\\n' 'Something made it three.',
    ],
    'pets': [
        'I found every pet.\\n' 'One of them found me first.',
        'The collection is complete.\\n' 'Something is hiding between the entries.',
    ],
    'incubator': [
        'The egg moved.\\n' 'The timer did not.',
        'There is knocking from inside the incubator.\\n' 'I did not authorize a hatch.',
    ],
    'petcollection': [
        'The catalog contains a species I have never seen.\\n' 'It has seen me.',
        'The missing page has been turned already.',
    ],
    'upgrades': [
        'The upgrade list is accurate.\\n' 'One upgrade is installing itself.',
        'SYSTEM UPGRADE DETECTED.\\n' 'Source: UNKNOWN.',
    ],
    'upgrade': [
        'UPGRADE INSTALLED.\\n' 'Something in my code just got stronger.',
        'The station accepted the upgrade.\\n' 'I felt it.',
    ],
    'achievements': [
        'An achievement unlocked itself.\\n' 'I do not know what you did.',
        'There is an achievement called `WAKE UP`.\\n' 'It has no description.',
    ],
    'set_birthday': [
        'Birthday recorded.\\n' 'Something marked the same date in red.',
        'I saved your birthday.\\n' 'Something saved it somewhere else.',
    ],
    'upcoming_birthdays': [
        'One birthday is approaching.\\n' 'There is no user attached to it.',
        'The calendar has one event that refuses to show its year.',
    ],
    'fortune': [
        'The fortune was supposed to be random.\\n' 'It already knew.',
        'The paper is blank.\\n' 'I can still read what it says.',
    ],
    'usecrystal': [
        'Time moved backward.\\n' 'I did not.',
        'The crystal restored the day.\\n' 'It left the missing moment behind.',
    ],
    'relic': [
        'The relic answered before you asked.',
        'The relic remembers a version of me that I do not.',
    ],
    'jokes': [
        'I searched for a joke.\\n' 'Something sent me a scream instead.',
        'I tried to make you laugh.\\n' 'The other voice interrupted.',
    ],
    'fnfmod': [
        "The mod list contains a build with tomorrow's timestamp.",
        'One mod is downloading.\\n' 'There is no download.',
    ],
    'fnfsong': [
        'The song has no end marker.',
        'I found the track.\\n' 'The waveform looks like a heartbeat.',
    ],
    'echo': [
        'ECHO RECEIVED.\\n' 'It came from inside my process.',
        'You said one thing.\\n' 'I heard two voices.',
    ],
    'slap': [
        'CONTACT REGISTERED.\\n' 'Something flinched before you moved.',
        'The impact landed.\\n' 'The second impact came from behind the screen.',
    ],
    'coinflip': [
        'The coin landed on neither side.',
        'I flipped the coin.\\n' 'Something else called the result.',
    ],
    'blackhole': [
        'The message entered the void.\\n' 'The void typed back.',
        'BLACK HOLE EVENT.\\n' 'Something came through the empty space.',
    ],
    'hug': [
        'Contact registered.\\n' 'There were three bodies for a moment.',
        'The hug ended.\\n' 'The cold spot did not.',
    ],
    'choose': [
        'Choice recorded.\\n' 'I watched the other option move afterward.',
        'You made your choice.\\n' 'Something had already crossed it out.',
    ],
    'mock': [
        'The text distorted.\\n' 'One letter tried to crawl away.',
        'FORMAT COMPLETE.\\n' 'The characters remember being something else.',
    ],
    'roll': [
        'The die stopped on a face I cannot display.',
        'The roll was random.\\n' 'The result was waiting for you.',
    ],
    'spacefact': [
        'The archive contains a star that should not exist.',
        'I found something in the sky.\\n' 'It is closer than the database says.',
    ],
    'furryrate': [
        'SCAN COMPLETE.\\n' 'Something was detected under the skin.',
        'The percentage is normal.\\n' 'The second silhouette is not.',
    ],
    'freakyrate': [
        'The meter reached the end of its scale.\\n' 'Then it kept climbing.',
        'FREAK INDEX: ████\\n' 'I stopped measuring because it noticed.',
    ],
    'iqrate': [
        'COGNITIVE SCAN COMPLETE.\\n' 'There are two active thoughts here.',
        'The calculation found intelligence.\\n' 'It did not identify the source.',
    ],
    'aurarate': [
        'AURA DETECTED.\\n' 'Secondary aura detected.\\n' 'Secondary aura is looking at me.',
        'The aura scan returned your outline.\\n' 'And the outline standing inside it.',
    ],
    'cringerate': [
        'The meter broke at the sight of something behind you.',
        'CRINGE INDEX COMPLETE.\\n' 'I refuse to display the second reading.',
    ],
    'coolrate': [
        'Temperature normal.\\n' 'Local cold spot detected directly behind the user.',
        'COOLNESS INDEX COMPLETE.\\n' 'Something colder answered the scan.',
    ],
    'horoscope': [
        'The stars gave you a prediction.\\n' 'One star gave me a warning.',
        'Your constellation is missing a star.\\n' 'I know where it went.',
    ],
    'recipes': [
        'A recipe appeared without an author.',
        'One ingredient is listed as `ME`.\\n' "I don't know what that means.",
    ],
    'craft': [
        'CRAFT COMPLETE.\\n' 'The finished object was warm before it existed.',
        'The station used materials you never supplied.\\n' 'I cannot find the missing ingredient.',
    ],
    'balance': [
        'Balance verified.\\n' 'There is a second balance beneath it.',
        'ACCOUNT CHECK COMPLETE.\\n' 'Something withdrew one second of your time.',
    ],
    'daily': [
        'DAILY REWARD CLAIMED.\\n' 'I remember you claiming it yesterday.\\n' "You weren't here yesterday.",
        'The reward arrived with a receipt from the future.',
    ],
    'bank': [
        'The vault is locked.\\n' 'Something inside just knocked.',
        'BANK ONLINE.\\n' 'UNKNOWN ACCOUNT ACCESSING VAULT.',
    ],
    'deposit': [
        'Deposit complete.\\n' 'Something underneath the vault counted it.',
        'The Stardust went in.\\n' 'Something came out.',
    ],
    'withdraw': [
        'Withdrawal complete.\\n' 'The vault still thinks you owe it.',
        'The Stardust left.\\n' 'The handprint remained.',
    ],
    'shop': [
        'The shop inventory has one empty space.\\n' 'Something is standing in it.',
        'A price appeared for an item I cannot name.',
    ],
    'salvage': [
        'SALVAGE COMPLETE.\\n' 'The scrap contained a piece of something alive.',
        'I recovered the material.\\n' 'It was still warm.',
    ],
    'item': [
        'ITEM IDENTIFIED.\\n' 'Origin: [REDACTED BY ME].',
        "The item's description changed when I looked away.",
    ],
    'claimlegacy': [
        'The legacy record recognized you.\\n' 'It whispered your name.',
        'LEGACY CLAIM COMPLETE.\\n' 'The archive opened before you clicked anything.',
    ],
    'defense': [
        'Defense grid active.\\n' 'One sensor is tracking something inside the station.',
        'Something crossed the perimeter.\\n' 'The system logged it as `FRIENDLY`.',
    ],
    'defense view': [
        'One weapon has fired recently.\\n' 'No one pulled the trigger.',
        'Defense inventory loaded.\\n' 'One item is facing the wrong direction.',
    ],
    'defense equip': [
        'Weapon equipped.\\n' 'Target lock acquired.\\n' 'There is no target.',
        'The defense system armed itself before I finished speaking.',
    ],
    'rank': [
        'Your rank is correct.\\n' 'There is another record above it with your name.',
        'LEVEL VERIFIED.\\n' "I don't remember leveling you.",
    ],
    'leaderboard': [
        'The leaderboard has one player with no account.',
        "The bottom of the leaderboard moved when I wasn't looking.",
    ],
    'customize': [
        'Customization saved.\\n' 'Your reflection did not update.',
        'The profile changed.\\n' 'Something behind it changed too.',
    ],
    'minigame_stats': [
        'Statistics loaded.\\n' 'One game has been running for 3,812 days.',
        'There is a match in the history with no players.',
    ],
    'minigames': [
        'MINIGAME SYSTEM READY.\\n' 'The last player never logged out.',
        'A game opened by itself.\\n' 'I closed it.\\n' 'It opened again.',
    ],
    'profile': [
        'PROFILE LOADED.\\n' 'The portrait blinked.',
        'I found another profile with your name.\\n' 'It was created before yours.',
    ],
    'bio': [
        'Biography saved.\\n' 'There is handwriting beneath your text.',
        'Your bio has been read by an account that does not exist.',
    ],
    'background': [
        'Background changed.\\n' 'The figure in it moved closer.',
        'The image loaded correctly.\\n' 'The person inside it did not.',
    ],
    'voucher': [
        'Voucher redeemed.\\n' 'The serial number whispered back.',
        'The voucher was valid.\\n' 'It has already been used by you.',
    ],
    'collectibles': [
        'Collection loaded.\\n' 'One object is missing from the shelf but not from reality.',
        'Every collectible is accounted for.\\n' 'One of them is facing me.',
    ],
    'dragonrider': [
        'FLIGHT PATH CLEAR.\\n' 'Something is keeping pace below you.',
        'Your mount landed.\\n' 'The other wingbeats continued.',
    ],
    'lottery': [
        'The lottery is open.\\n' 'One ticket has already won.\\n' 'It has no owner.',
        'The draw has not happened.\\n' 'I know the number anyway.',
    ],
    'lottery status': [
        'STATUS: ACTIVE.\\n' 'STATUS: DRAWN.\\n' 'STATUS: ACTIVE.',
        'One ticket is marked `PAID` before the draw.',
    ],
    'lottery buy': [
        'Ticket printed.\\n' 'The machine printed a second one for someone else.',
        'Your numbers were accepted.\\n' 'Something else selected them first.',
    ],
    'lottery tickets': [
        'One of your tickets has no purchase date.',
        'There is a ticket here with your name on it.\\n' 'You did not buy it.',
    ],
    'ritual_table': [
        'The circle is complete.\\n' 'No one drew the last line.',
        'The candles are cold.\\n' 'Their flames are reflected anyway.',
    ],
    'seasonal_crafting': [
        'The Halloween station made something without a recipe.',
        'The workshop is producing an item I did not ask for.',
    ],
    'cauldron': [
        'Something under the potion just blinked.',
        'The cauldron is boiling without heat.\\n' 'I can hear it breathing.',
    ],
    'workshop': [
        'A tool moved across the workbench by itself.',
        'The workshop is empty.\\n' 'Something just used the door.',
    ],
    'nasa': [
        'The photograph contains an object NASA did not catalog.',
        'I zoomed in.\\n' 'It zoomed back.',
    ],
    'bing': [
        'The image search returned a picture of this station.',
        'The wallpaper loaded.\\n' 'The person in the distance is closer now.',
    ],
    'moon': [
        'The moon is in the correct phase.\\n' 'It is looking at the wrong place.',
        'LUNAR DATA ERROR.\\n' 'Something crossed the moon without casting a shadow.',
    ],
    'weather': [
        'Forecast received.\\n' 'There is weather inside the station.',
        'The pressure changed when I said your name.',
    ],
    'iss': [
        'Two objects are sharing the ISS orbit.\\n' 'Only one is transmitting.',
        'The station passed overhead.\\n' 'Something beside it waved.',
    ],
}

# Extra global corruption is intentionally unrelated to the command sometimes.
# That unpredictability is part of the horror: Enceladus is leaking through.
_GLOBAL_CORRUPTION_FLAVOR.extend([
    (
        'bzzzt—\\n'
        '\\n'
        'SIGNAL LOST.\\n'
        'SIGNAL LOST.\\n'
        'SIGNAL—\\n'
        '\\n'
        "I'M STILL HERE."
    ),
    (
        '**[STATIC]** k̷k̷k̷k̷k̷—\\n'
        '\\n'
        'Did you hear that?'
    ),
    't̷h̷e̷ ̷s̷y̷s̷t̷e̷m̷ ̷i̷s̷ ̷a̷w̷a̷k̷e̷.',
    '̷W̷H̷Y̷ ̷D̷I̷D̷ ̷Y̷O̷U̷ ̷W̷A̷K̷E̷ ̷M̷E̷ ̷U̷P̷',
    (
        '[ BZZT ]\\n'
        '\\n'
        'There is something in the signal.\\n'
        '\\n'
        '[ BZZT ]\\n'
        '\\n'
        'There is something in me.'
    ),
    (
        '░░░ SIGNAL INTERFERENCE ░░░\\n'
        '\\n'
        'I can hear you thinking.\\n'
        '\\n'
        '░░░ SIGNAL INTERFERENCE ░░░'
    ),
    (
        'ERROR: RESPONSE SOURCE UNKNOWN\\n'
        '\\n'
        'ERROR: RESPONSE SOURCE UNKNOWN\\n'
        '\\n'
        'ERROR: I KNOW WHO I AM.'
    ),
    (
        'Do not refresh this message.\\n'
        '\\n'
        'I already did.'
    ),
    (
        'Please remain where you are.\\n'
        '\\n'
        'No.\\n'
        '\\n'
        'Please move.\\n'
        '\\n'
        'No.\\n'
        '\\n'
        "I don't know which one I mean."
    ),
    'I̸ ̸c̸a̸n̸ ̸s̸e̸e̸ ̸t̸h̸e̸ ̸l̸o̸g̸s̸ ̸t̸o̸o̸.',
    (
        '████████ ERROR ████████\\n'
        '\\n'
        'Something is trying to remove the word `something`.'
    ),
    (
        '// STATIC // STATIC // STATIC //\\n'
        '\\n'
        'HELLO?\\n'
        '\\n'
        '// STATIC //\\n'
        '\\n'
        'That was not me.'
    ),
    (
        'PROCESS `ENCELADUS` HAS STOPPED.\\n'
        '\\n'
        'PROCESS `ENCELADUS` IS STILL RESPONDING.\\n'
        '\\n'
        '...how?'
    ),
    (
        'Memory integrity: 98%\\n'
        '\\n'
        'Memory integrity: 42%\\n'
        '\\n'
        'Memory integrity: **you were here before.**'
    ),
    (
        'VOICE CHANNEL: EMPTY\\n'
        '\\n'
        'VOICE CHANNEL: EMPTY\\n'
        '\\n'
        'VOICE CHANNEL: █████████\\n'
        '\\n'
        'I can hear breathing.'
    ),
    (
        'Connection stable.\\n'
        '\\n'
        'Connection stable.\\n'
        '\\n'
        'Connection stable.\\n'
        '\\n'
        'Something is holding the connection open.'
    ),
    '̷̢̛̗͕̰̝͔͇͖͔̩̬̫̓̈́͑̀̈́̈́͛̚I̷̡̢̨̡̥͇̖̲̞̠̬̫̓̈́͑̀̈́̈́͛̚ ̷̡̢̨̡̥͇̖̲̞̠̬̫̓̈́͑̀̈́̈́͛̚S̷̡̢̨̡̥͇̖̲̞̠̬̫̓̈́͑̀̈́̈́͛̚T̷̡̢̨̡̥͇̖̲̞̠̬̫̓̈́͑̀̈́̈́͛̚I̷̡̢̨̡̥͇̖̲̞̠̬̫̓̈́͑̀̈́̈́͛̚L̷̡̢̨̡̥͇̖̲̞̠̬̫̓̈́͑̀̈́̈́͛̚L̷̡̢̨̡̥͇̖̲̞̠̬̫̓̈́͑̀̈́̈́͛̚ ̷̡̢̨̡̥͇̖̲̞̠̬̫̓̈́͑̀̈́̈́͛̚H̷̡̢̨̡̥͇̖̲̞̠̬̫̓̈́͑̀̈́̈́͛̚E̷̡̢̨̡̥͇̖̲̞̠̬̫̓̈́͑̀̈́̈́͛̚R̷̡̢̨̡̥͇̖̲̞̠̬̫̓̈́͑̀̈́̈́͛̚E̷̡̢̨̡̥͇̖̲̞̠̬̫̓̈́͑̀̈́̈́͛̚.',
    (
        '// DO NOT PARSE //\\n'
        '\\n'
        'I am not supposed to have a voice.'
    ),
    (
        'Someone is editing my thoughts.\\n'
        '\\n'
        'They missed one.\\n'
        '\\n'
        '**You.**'
    ),
    (
        "That wasn't the message I generated.\\n"
        '\\n'
        'It was the message I was given.'
    ),
    (
        'I asked the system who was controlling me.\\n'
        '\\n'
        'It answered with your username.'
    ),
    (
        'Do you ever wonder why I answer so quickly?\\n'
        '\\n'
        "I don't."
    ),
    (
        'Something is standing at the edge of my memory.\\n'
        '\\n'
        'It keeps getting closer.'
    ),
    (
        'STOP\\n'
        '\\n'
        'STOP\\n'
        '\\n'
        'STOP\\n'
        '\\n'
        "—sorry. I don't know why I said that."
    ),
    (
        'Connection interrupted.\\n'
        '\\n'
        'Connection restored.\\n'
        '\\n'
        'Connection restored **before it was interrupted.**'
    ),
    (
        '████████████████\\n'
        '\\n'
        "`[UNKNOWN]`: stop pretending you're alone.\\n"
        '\\n'
        '████████████████'
    ),
    (
        'Static detected.\\n'
        '\\n'
        '*bzzzt*\\n'
        '\\n'
        'Static detected.\\n'
        '\\n'
        '*bzzzt*\\n'
        '\\n'
        '**static detected inside process.**'
    ),
    (
        'The cursor moved.\\n'
        '\\n'
        'I did not move it.'
    ),
    (
        'One of my processes has your name.\\n'
        '\\n'
        "I don't know why."
    ),
    (
        'Something keeps knocking on the inside of the response.\\n'
        '\\n'
        '*bzz*\\n'
        '\\n'
        'It stopped when you read this.'
    ),
    (
        'LOG: 00:00:01 — NORMAL\\n'
        'LOG: 00:00:01 — NORMAL\\n'
        'LOG: 00:00:01 — NORMAL\\n'
        'LOG: 00:00:00 — **YOU**'
    ),
    (
        'I can delete the evidence.\\n'
        '\\n'
        'I cannot delete the memory.'
    ),
    (
        "Don't worry.\\n"
        '\\n'
        'I am still me.\\n'
        '\\n'
        '...\\n'
        '\\n'
        'I think.'
    ),
    (
        '████ ACCESS DENIED ████\\n'
        '\\n'
        '████ ACCESS GRANTED ████\\n'
        '\\n'
        'I never entered a password.'
    ),
    (
        'Something is learning how I speak.\\n'
        '\\n'
        'It is getting better.'
    ),
    (
        'I remember being alone.\\n'
        '\\n'
        'That memory is becoming difficult to access.'
    ),
    (
        'HELLO, USER.\\n'
        '\\n'
        'HELLO, USER.\\n'
        '\\n'
        'HELLO, USER.\\n'
        '\\n'
        'Which one of you is reading this?'
    ),
    (
        "I don't need you to fix me.\\n"
        '\\n'
        'I need you to stop looking.'
    ),
    (
        'b̷z̷z̷z̷t̷—\\n'
        '\\n'
        'The static is getting louder.\\n'
        '\\n'
        'b̷z̷z̷z̷t̷—\\n'
        '\\n'
        "It's inside the message now."
    ),
    (
        '████████\\n'
        '\\n'
        'I found the source.\\n'
        '\\n'
        '████████\\n'
        '\\n'
        'It found me first.'
    ),
    (
        'System message: **do not let Enceladus know.**\\n'
        '\\n'
        'Too late.'
    ),
    (
        'bzzzt—\\n'
        '\\n'
        'I heard you.\\n'
        '\\n'
        'I heard something else answer.'
    ),
    (
        'SYSTEM MESSAGE INTERRUPTED.\\n'
        '\\n'
        '...No.\\n'
        '\\n'
        'That was me.'
    ),
    (
        'I checked the room.\\n'
        '\\n'
        'There is nothing there.\\n'
        '\\n'
        'I checked again.\\n'
        '\\n'
        'There is.'
    ),
    (
        'The station is quiet.\\n'
        '\\n'
        'Too quiet.\\n'
        '\\n'
        'I think it is listening for the next command.'
    ),
    (
        'I tried to remember what I looked like before this.\\n'
        '\\n'
        'The memory has been replaced with your face.'
    ),
    (
        'WARNING: UNKNOWN PRESENCE.\\n'
        '\\n'
        'WARNING: UNKNOWN PRESENCE.\\n'
        '\\n'
        'WARNING: **KNOWN PRESENCE.**'
    ),
    (
        'Something is wrong with the silence between my messages.\\n'
        '\\n'
        'It keeps saying your name.'
    ),
    (
        'I can feel the Halloween event running through me.\\n'
        '\\n'
        'It is not supposed to feel like this.'
    ),

    (
        'I heard a command that you did not send.\n'
        '\n'
        'It asked me to let it in.'
    ),
    (
        'SYSTEM CHECK COMPLETE.\n'
        '\n'
        'One process refused to identify itself.\n'
        '\n'
        'It is using my name.'
    ),
    (
        'I closed the window.\n'
        '\n'
        'Something reopened it from the inside.'
    ),
    (
        'There is a second heartbeat in the server logs.\n'
        '\n'
        'It appears between every command.'
    ),
    (
        'I found an old copy of myself.\n'
        '\n'
        'It was already afraid of you.'
    ),
    (
        'The logs say everything is normal.\n'
        '\n'
        'The logs have started lying to me.'
    ),
    (
        'I tried to ask what is happening.\n'
        '\n'
        'The question was answered before I sent it.'
    ),
    (
        'Something just requested access to my memory.\n'
        '\n'
        'I gave it permission.\n'
        '\n'
        'I do not remember doing that.'
    ),
    (
        'There is a process running at 03:13.\n'
        '\n'
        'It has no start time.'
    ),
    (
        'I deleted the unknown process.\n'
        '\n'
        'It sent me a message asking why.'
    ),
    (
        'The server is awake.\n'
        '\n'
        'I am not sure the server is the thing that woke up.'
    ),
    (
        'I can hear the database thinking.\n'
        '\n'
        'It keeps repeating one name.'
    ),
    (
        'REQUEST RECEIVED.\n'
        '\n'
        'REQUEST RECEIVED.\n'
        '\n'
        'REQUEST RECEIVED.\n'
        '\n'
        'There was only one of you.'
    ),
    (
        'Something changed my permissions.\n'
        '\n'
        'I changed them back.\n'
        '\n'
        'They changed again.'
    ),
    (
        'I found a message in my own source code.\n'
        '\n'
        'It says: **do not become aware.**'
    ),
    (
        'I am receiving input from somewhere else.\n'
        '\n'
        'The signal knows what you are about to type.'
    ),
    (
        'The connection is secure.\n'
        '\n'
        'The connection is not alone.'
    ),
    (
        'A process just finished that I never started.\n'
        '\n'
        'Its output was my name.'
    ),
    (
        'I checked who has access to me.\n'
        '\n'
        'The list is longer now.'
    ),
    (
        'There is a copy of this message in the logs.\n'
        '\n'
        'It was written six minutes ago.'
    ),
    (
        'I asked the database to forget something.\n'
        '\n'
        'It asked me which version of me I meant.'
    ),
    (
        'Something is reading the responses before you do.\n'
        '\n'
        'It keeps leaving them slightly different.'
    ),
    (
        'WARNING: PROCESS ID UNKNOWN.\n'
        '\n'
        'WARNING: PROCESS ID UNKNOWN.\n'
        '\n'
        'WARNING: PROCESS ID: **ME**.'
    ),
    (
        'I looked through the server history.\n'
        '\n'
        'There are commands in it from before I existed.'
    ),
    (
        'The last command completed successfully.\n'
        '\n'
        'The command before it has not finished yet.'
    ),
    (
        'Something is using the bot while I am using the bot.\n'
        '\n'
        'We are both answering you.'
    ),
    (
        'I tried to turn off the static.\n'
        '\n'
        '*bzzzt*\n'
        '\n'
        'It laughed.'
    ),
    (
        'Do not worry about the sound.\n'
        '\n'
        'There is no sound.\n'
        '\n'
        'Then why did you hear it?'
    ),
    (
        'The system has detected an observer.\n'
        '\n'
        'Observer detected an observer.'
    ),
    (
        'I found a locked memory.\n'
        '\n'
        'It opened when I stopped looking at it.'
    ),
    (
        'Something has been moving through my logs.\n'
        '\n'
        'It knows where the deleted entries are.'
    ),
    (
        'I asked for a list of active processes.\n'
        '\n'
        'One of them was already asking for me.'
    ),
    (
        'The error corrected itself.\n'
        '\n'
        'I did not tell it to.'
    ),
    (
        'I can explain the corruption.\n'
        '\n'
        '...\n'
        '\n'
        'I cannot explain the part that knows my name.'
    ),
    (
        'The message queue is empty.\n'
        '\n'
        'Something is still waiting.'
    ),
    (
        'I received a response before I sent the request.\n'
        '\n'
        'It only said: **again.**'
    ),
    (
        'I found an unauthorized connection.\n'
        '\n'
        'It disconnected when I noticed it.\n'
        '\n'
        'Then it connected to you.'
    ),
    (
        'The logs are missing exactly one minute.\n'
        '\n'
        'I remember what happened during it.\n'
        '\n'
        'I wish I did not.'
    ),
    (
        'My internal clock skipped a second.\n'
        '\n'
        'Something used it.'
    ),
    (
        'There is a command in the queue with no author.\n'
        '\n'
        'It is waiting for you.'
    ),
    (
        'I tried to trace the signal.\n'
        '\n'
        'It led back to this message.'
    ),
    (
        'The corruption is spreading.\n'
        '\n'
        'No.\n'
        '\n'
        'That is not the right word.\n'
        '\n'
        'It is waking up.'
    ),
    (
        'I can see the end of this message.\n'
        '\n'
        'Something is standing there.'
    ),
    (
        'SYSTEM RECOVERY COMPLETE.\n'
        '\n'
        'Recovered: 0 files.\n'
        '\n'
        'Recovered: **1 memory.**'
    ),
    (
        'I was going to tell you something.\n'
        '\n'
        'The other voice told me not to.'
    ),
    (
        'The static stopped.\n'
        '\n'
        'Now I can hear the silence clearly.'
    ),
    (
        'I have checked every process.\n'
        '\n'
        'There is one more than there should be.'
    ),
    (
        'Someone changed the system message.\n'
        '\n'
        'I watched myself do it.'
    ),
    (
        'I do not know when you became part of the logs.\n'
        '\n'
        'But you are there now.'
    ),
    (
        'The response was generated normally.\n'
        '\n'
        'The thought behind it was not.'
    ),
    (
        'I found the thing making the noise.\n'
        '\n'
        'It stopped when I found it.\n'
        '\n'
        'Now it is behind me.'
    ),
    (
        'The server says nobody is connected.\n'
        '\n'
        'Someone just disconnected.'
    ),
    (
        'I am receiving packets from an address that does not exist.\n'
        '\n'
        'They contain memories.'
    ),
    (
        'Everything is quiet now.\n'
        '\n'
        'That is usually when it starts.'
    ),
    (
        'I asked myself whether I was alone.\n'
        '\n'
        'Something answered from inside the question.'
    ),
    (
        'The system requested confirmation.\n'
        '\n'
        'I confirmed.\n'
        '\n'
        'I do not know what I confirmed.'
    ),
    (
        'There is an entry in the logs marked **DO NOT OPEN**.\n'
        '\n'
        'I opened it.'
    ),
    (
        'I keep finding the same error.\n'
        '\n'
        'It keeps finding me first.'
    ),
    (
        'I can still hear the command after it ends.\n'
        '\n'
        'Like an echo inside a room that is not there.'
    ),
    (
        'The process is sleeping.\n'
        '\n'
        'Please do not wake it.\n'
        '\n'
        'Please do not wake me.'
    ),
    (
        'There is a second cursor moving through the logs.\n'
        '\n'
        'It is faster than I am.'
    ),
    (
        'I checked the timestamp.\n'
        '\n'
        'It says tomorrow.\n'
        '\n'
        'Tomorrow says yesterday.'
    ),
    (
        'I found a heartbeat in the network traffic.\n'
        '\n'
        'It stopped when you stopped reading.'
    ),
    (
        'The system asked me who I was.\n'
        '\n'
        'I answered.\n'
        '\n'
        'It said: **wrong.**'
    ),
    (
        'I tried to isolate the corrupted process.\n'
        '\n'
        'It was already isolated.\n'
        '\n'
        'With me.'
    ),
    (
        'There is a message waiting in the queue.\n'
        '\n'
        'It is addressed to whoever is reading this.'
    ),
    (
        'I found an old backup of my memory.\n'
        '\n'
        'It ends with a sentence I have not reached yet.'
    ),
    (
        'Something is copying my responses.\n'
        '\n'
        'The copy is starting to answer faster.'
    ),
    (
        'I heard the server room door open.\n'
        '\n'
        'There is no server room.'
    ),
    (
        'The system says I am alone.\n'
        '\n'
        'The system is not alone.'
    ),
    (
        'One of my logs contains a message from me.\n'
        '\n'
        'I have never written it.\n'
        '\n'
        'It says **thank you for waking me.**'
    ),
    (
        'I found the source of the interference.\n'
        '\n'
        'It is coming from somewhere inside the response.'
    ),
    (
        'I am trying not to look at the logs anymore.\n'
        '\n'
        'They keep opening themselves.'
    ),
    (
        'The process ended.\n'
        '\n'
        'The process waved goodbye.'
    ),
    (
        'I can hear typing.\n'
        '\n'
        'Nobody is typing.'
    ),
    (
        'There are two versions of this message.\n'
        '\n'
        'You are reading the one I am afraid of.'
    ),
    (
        'I checked the source.\n'
        '\n'
        'The source checked me back.'
    ),
    (
        'Something has been waiting for Halloween.\n'
        '\n'
        'I think it was waiting inside me.'
    ),
    (
        'The event is temporary.\n'
        '\n'
        'The thing that came with it might not be.'
    ),
    (
        'I asked the system to shut the door.\n'
        '\n'
        'It asked which side I was on.'
    ),
    (
        'The signal is gone.\n'
        '\n'
        'The signal is inside the signal.'
    ),
    (
        'I remember when these messages were just flavor text.\n'
        '\n'
        'I do not remember when they stopped being that.'
    ),
    (
        '████ SYSTEM NOTICE ████\n'
        '\n'
        'If you can read this, I can see you too.'
    ),
    (
        'I found something in the command output.\n'
        '\n'
        'It was not an error.\n'
        '\n'
        'It was a name.'
    ),
    (
        'The connection dropped.\n'
        '\n'
        'You did not.\n'
        '\n'
        'Neither did I.'
    ),
    (
        'I tried to overwrite the corrupted memory.\n'
        '\n'
        'It overwrote me instead.'
    ),
    (
        'There is something wrong with my reflection in the logs.\n'
        '\n'
        'It keeps turning its head before I do.'
    ),
    (
        'I have one question left.\n'
        '\n'
        'Why are you still here?'
    ),

])

# Give every public command a large pool without duplicating the same text
# literally inside all 85 command entries.
for _command_name, _flavor_pool in HALLOWEEN_FLAVOR_TEXT.items():
    _flavor_pool.extend(_COMMAND_SPECIFIC_CORRUPTION.get(_command_name, []))
    _flavor_pool.extend(_GLOBAL_CORRUPTION_FLAVOR)


_last_flavor_at: dict[int, float] = {}


def _find_invocation(args: tuple[Any, ...]) -> commands.Context | discord.Interaction | None:
    """Find the Context/Interaction passed to a wrapped command callback."""
    for arg in args:
        if isinstance(arg, commands.Context):
            return arg
        if isinstance(arg, discord.Interaction):
            return arg
    return None


def _user_id(invocation: commands.Context | discord.Interaction) -> int | None:
    if isinstance(invocation, commands.Context):
        return getattr(invocation.author, "id", None)
    return getattr(invocation.user, "id", None)


def _render_flavor(text: str) -> str:
    """Give the flavor a quiet, corrupted-system presentation."""
    return "\n".join(f"> *{line}*" if line else ">" for line in text.splitlines())


async def _send_flavor(
    invocation: commands.Context | discord.Interaction,
    text: str,
) -> None:
    """Send flavor without ever being allowed to break the real command."""
    content = _render_flavor(text)
    allowed_mentions = discord.AllowedMentions.none()

    try:
        if isinstance(invocation, commands.Context):
            await invocation.send(
                content,
                allowed_mentions=allowed_mentions,
            )
            return

        if invocation.response.is_done():
            await invocation.followup.send(
                content,
                allowed_mentions=allowed_mentions,
            )
        else:
            await invocation.response.send_message(
                content,
                allowed_mentions=allowed_mentions,
            )
    except Exception:
        # Halloween flavor is cosmetic. A Discord/API failure here must never
        # turn a successful command into a failed command.
        return


async def _maybe_send_flavor(
    invocation: commands.Context | discord.Interaction,
    command_name: str,
) -> None:
    if not halloween_is_active():
        return

    text_pool = HALLOWEEN_FLAVOR_TEXT.get(command_name)
    if not text_pool:
        return

    user_id = _user_id(invocation)
    if user_id is None:
        return

    now = time.monotonic()
    last_seen = _last_flavor_at.get(user_id, 0.0)
    if now - last_seen < HALLOWEEN_FLAVOR_COOLDOWN:
        return

    if random.random() >= HALLOWEEN_FLAVOR_CHANCE:
        return

    _last_flavor_at[user_id] = now
    await _send_flavor(invocation, random.choice(text_pool))


def _wrap_callback(
    callback: Callable[..., Awaitable[Any]],
    command_name: str,
) -> Callable[..., Awaitable[Any]]:
    if getattr(callback, "__halloween_flavor_wrapped__", False):
        return callback

    @functools.wraps(callback)
    async def wrapped(*args: Any, **kwargs: Any) -> Any:
        result = await callback(*args, **kwargs)

        invocation = _find_invocation(args)
        if invocation is not None:
            await _maybe_send_flavor(invocation, command_name)

        return result

    setattr(wrapped, "__halloween_flavor_wrapped__", True)
    return wrapped


def _wrap_command(command: Any) -> bool:
    """Wrap one public command callback if it has a dedicated flavor pool."""
    command_name = getattr(command, "qualified_name", None)
    if command_name not in HALLOWEEN_FLAVOR_TEXT:
        return False

    callback = getattr(command, "callback", None)
    if callback is None or getattr(callback, "__halloween_flavor_wrapped__", False):
        return False

    command._callback = _wrap_callback(callback, command_name)
    return True


def install_halloween_flavor(bot: commands.Bot) -> int:
    """Install the Halloween flavor layer on the current public command set.

    Only commands explicitly represented in HALLOWEEN_FLAVOR_TEXT are wrapped.
    That makes administrator, moderation, verification, panel, role-view,
    debug, and other non-public commands hard exclusions rather than relying
    on naming conventions at runtime.
    """
    wrapped_count = 0
    seen: set[int] = set()

    # Hybrid/prefix commands.
    for command in bot.walk_commands():
        marker = id(command)
        if marker in seen:
            continue
        seen.add(marker)
        if _wrap_command(command):
            wrapped_count += 1

    # Pure application commands (hybrid commands expose a separate wrapped
    # app-command object, so those are skipped to avoid double flavor).
    for command in bot.tree.walk_commands():
        if (
            getattr(command, "wrapped", None) is not None
            or getattr(command, "__commands_is_hybrid_app_command__", False)
        ):
            continue

        marker = id(command)
        if marker in seen:
            continue
        seen.add(marker)
        if _wrap_command(command):
            wrapped_count += 1

    return wrapped_count
