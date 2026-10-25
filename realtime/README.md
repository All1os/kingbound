# Kingbound, real-time version

Prototype of the team's final design (design document of 2026-10-18, updated 2026-10-25): a real-time dungeon race for 3-5 players with Escape: The Curse of the Temple as its reference. Everyone plays at once for 10 minutes, rolling symbol dice to reveal rooms, move, beat monsters and take treasures. Treasure only counts once it is carried back to the Safe Room. Most points wins. The turn-based Kingbound (v0.1) in the folders above is untouched.

The update of 2026-10-25 answers the teacher's feedback with three changes, all in this prototype: the Safe Room (§12), Trap Tiles (§13) and Prank Cards (§14).

| File | What it is |
|---|---|
| `tts/build.py` | Draws every element with Pillow and writes the Tabletop Simulator save `KINGBOUND-realtime` (into TTS's `Saves/prototipler`) |
| `tts/global.lua` | The table's script: START GAME and RESET TABLE for players; for the tutorial it moves pieces, rolls dice to given faces, draws the part names, the timer and the scores |
| `tts/hotload.py` | Puts a freshly built save on the table of a running TTS without the Save & Load menu |
| `plan.py` | The dungeon the tutorial builds: which room goes where, in which order, with which token |
| `tutorial.py` | Plays the 3:52 tutorial video in TTS for the presentation; `--record FILE.mov` records the screen, `--cues FILE.md` writes what to say, `--dry-run` prints the timeline. It still teaches the rules from before the update (no Safe Room, traps or Prank Cards yet) |
| `tutorial-cues.md` | What to say over the video, second by second |
| `photos.py` | Photos of every element for the slides: `python3 photos.py OUTDIR` (or only some shots: `... OUTDIR 01 05`). It still stages rooms and tokens as loose tiles, from before they became decks |

Run: `python3 tts/build.py`, load `KINGBOUND-realtime` in TTS (Games → Save & Load → prototipler) or run `python3 tts/hotload.py` with any game open.

## Playing it in Tabletop Simulator

Sit at Red, Yellow, Green, Blue or Purple and press START GAME (top left, under TTS's toolbar). It shuffles the room deck, the two token decks and the Loot Deck, puts 4 dice on each seated player's mat and every character in the Safe Room, and starts the 10-minute timer. If nobody sits at a mat colour (one person trying it out), all five sets go out. From then on everything is done by hand: roll your dice, take the top card of the room deck and flip it (F), draw a token the same way, draw Loot. When the timer reaches 0:00 the screen says so; count the POINTS box of your mat. RESET TABLE puts every piece back.

## Choices where the design document is open

| Topic | Prototype choice |
|---|---|
| Dice | 4 per player (a strong monster needs 4 Attack). Faces: 2 Movement, 2 Attack, 2 Magic. §2.3 also names "special-effect" symbols but never says what they do, so the dice have none |
| Room tiles | A deck of 28 square cards: 6 empty, 7 monster, 9 treasure and 6 trap rooms. The Safe Room is a tile in the middle. Each room has passages; a revealed room is placed so its passages connect |
| Decks | Rooms, monster tokens, treasure tokens and rubble are decks of cards, not piles of loose tiles (Yavuz asked, 2026-10-25). Tokens and rubble are round cards. A round token and a square room never join into one deck, so a token can lie on its room |
| Safe Room (§12) | The start room in the middle, with the crown from the update's picture. The picture on p. 7 shows eight exits; the tile has four, like every room |
| Securing treasure (§12) | A collected treasure goes to the mat's CARRIED box. Standing in the Safe Room, a player moves everything CARRIED to POINTS, with no dice. Defeated monsters go straight to POINTS: §12 asks only for treasure to be secured. Only POINTS count at the end |
| Traps (§13) | Two of each trap. A trap goes off every time a character walks into its room; revealing the room doesn't set it off. Trap rooms always have at least two passages, so they sit on routes |
| Spike Pit | Lose 1 unsecured treasure (you choose which). It is out of the game |
| Pressure Plate | §13 says "losing a turn"; there are no turns, so: put your dice down and count to 10 out loud |
| Collapsing Passage | When its visitor walks out, the whole room caves in: a rubble token goes on it and nobody can walk in again. Blocking one passage, as §13 puts it, could shut a player inside a room with no way out |
| Prank Cards (§14) | Two of each of the document's four Pranks join the Loot Deck. Play any time, then discard. No Prank reaches a player standing in the Safe Room |
| Sticky Fingers | Steal 1 unsecured treasure from another player into your CARRIED box |
| Wrong Turn | Move another player's character into a room connected to theirs; a trap there goes off |
| Monster Magnet | The undefeated monster nearest to another player moves into their room; they can't leave until they beat it. A monster you only walk past doesn't stop you |
| Trap Surprise | Another player gets a Spike Pit or a Pressure Plate (you choose) where they stand. Collapsing Passage is left out: it acts when someone leaves a room |
| Monsters | 4 weak (2 Attack, 1 point), 3 medium (3 Attack, 2 points), 2 strong (4 Attack, 4 points). The feedback asked for less fighting: 7 monster rooms instead of 11. A strong one is worth more than two weak ones, so fighting it or taking easy rewards (§10) is a real choice |
| Treasures | All need 2 Magic. 3 common (1 point), 3 rare (3 points), 6 special (1 point and a Loot card). The feedback asked for more Loot: 6 special treasures instead of 3 |
| Loot Deck | 18 cards, two of each: Iron Sword (counts as 1 Attack), Swift Boots (1 Movement), Rune Amulet (1 Magic), Lucky Charm (once: turn a die to any symbol), Fire Bomb (once: beat a weak monster without rolling) and the four Pranks |
| Acting | Moving goes to a connected room. A monster or treasure is taken in its own room |
| Seats | Five, for 3-5 players (§1): Red, Yellow, Green, Blue and Purple. The mats show only the colour |
| Tie | Most monsters defeated wins (the document's own suggestion, §11) |
| Timer | On screen, top right. START GAME starts it; it follows the clock, so it never drifts |

The feedback's "make the map shrink over time" has no change of its own in the update; the Collapsing Passage rooms are the only rooms that disappear.

The tutorial sets every die face itself, so each rule shows once, including the document's example roll (§5: 2 Attack, 1 Movement, 1 Magic against a medium monster).
