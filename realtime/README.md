# Kingbound, real-time version

Prototype of the team's final design (design document of 2026-10-18): a real-time dungeon race for 3-5 players with Escape: The Curse of the Temple as its reference. Everyone plays at once for 10 minutes, rolling symbol dice to reveal rooms, move, beat monsters and take treasures. Most points wins. The turn-based Kingbound (v0.1) in the folders above is untouched.

| File | What it is |
|---|---|
| `tts/build.py` | Draws every element with Pillow and writes the Tabletop Simulator save `KINGBOUND-realtime` (into TTS's `Saves/prototipler`) |
| `tts/global.lua` | The table's script: moves pieces, rolls dice to given faces, draws the part names, the timer and the scores |
| `tts/hotload.py` | Puts a freshly built save on the table of a running TTS without the Save & Load menu |
| `plan.py` | The dungeon the tutorial builds: which room goes where, in which order, with which token |
| `tutorial.py` | Plays the 3:52 tutorial video in TTS for the presentation; `--record FILE.mov` records the screen, `--cues FILE.md` writes what to say, `--dry-run` prints the timeline |
| `tutorial-cues.md` | What to say over the video, second by second |
| `photos.py` | Photos of every element for the slides: `python3 photos.py OUTDIR` (or only some shots: `... OUTDIR 01 05`) |

Run: `python3 tts/build.py`, load `KINGBOUND-realtime` in TTS (Games → Save & Load → prototipler) or run `python3 tts/hotload.py` with any game open, then `python3 tutorial.py`.

## Choices where the design document is open

| Topic | Prototype choice |
|---|---|
| Dice | 4 per player (a strong monster needs 4 Attack). Faces: 2 Movement, 2 Attack, 2 Magic. §2.3 also names "special-effect" symbols but never says what they do, so the dice have none |
| Room tiles | 26 in the stack: 6 empty, 11 monster, 9 treasure, plus the start room. Each tile has passages; a revealed room is placed so its passages connect |
| Monsters | 6 weak (2 Attack, 1 point), 4 medium (3 Attack, 2 points), 3 strong (4 Attack, 4 points). A strong one is worth more than two weak ones, so fighting it or taking easy rewards (§10) is a real choice |
| Treasures | All need 2 Magic. 6 common (1 point), 3 rare (3 points), 3 special (1 point and a Loot card) |
| Loot Deck | 10 cards, two of each: Iron Sword (counts as 1 Attack), Swift Boots (1 Movement), Rune Amulet (1 Magic), Lucky Charm (once: turn a die to any symbol), Fire Bomb (once: beat a weak monster without rolling) |
| Acting | Moving goes to a connected room. A monster or treasure is taken in its own room |
| Tie | Most monsters defeated wins (the document's own suggestion, §11) |
| Timer | On screen, top right, during the real game |

The tutorial sets every die face itself, so each rule shows once, including the document's example roll (§5: 2 Attack, 1 Movement, 1 Magic against a medium monster).
