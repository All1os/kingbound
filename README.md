# Kingbound

Prototype of Kingbound, a competitive adventure card game for 4 players. Recruits roam a 7×7 board, fight monsters with a hand of Action cards, train and gear up. The first to win the King's Trial at the Castle is chosen by the king.

Version history: [CHANGELOG.md](CHANGELOG.md). Each version is also a GitHub release.

| File | What it is |
|---|---|
| `Kingbound-GDD.md` (`.docx`, `.pdf`) | The rules and every card list, with the team's decisions |
| `Kingbound-choices.txt` | The 8 questions the team answered |
| `tts/` | Tabletop Simulator build. `cards.py` holds every card and tile from the GDD, `build.py` draws the cards and writes the save, `global.lua` and `player_board.lua` are the table's scripts, `preview.py` draws the table from above without TTS |
| `tts/output/` | The card sheets, tiles and other images, and the save `KINGBOUND-prototype.json` |
| `bots/` | Four bots that play the game in TTS (`play.py`), their rules engine (`engine.py`) and a statistics run (`stats.py`) |
| `tests/` | `check_tts_script.py` runs the table script against a fake TTS |

## Tabletop Simulator

`python3 tts/build.py` writes the save to `tts/output/` and copies it to `~/Library/Tabletop Simulator/Saves/prototipler/`. The images go to `~/Library/Tabletop Simulator/Mods/kingbound/`, because macOS doesn't let TTS read the Desktop.

1. In TTS: Games → Save & Load → prototipler → KINGBOUND-prototype.
2. The board is already built. Sit at Red, Yellow, Green or Blue and press SETUP.

The images are local files on this Mac, so for now the save only opens with its pictures here. To share it, upload the images with TTS's Cloud Manager, put their URLs in `tts/cloud_urls.json` (same format as The Limit's) and run `build.py` again.

### The table

The board sits in the middle with the level track (1 to 10) under it. Left of the board: the Action and Loot decks with their discard piles, the Characters, Abilities and hidden objectives, the Merchant's three offer spots, the player aid, the damage token bags (1 and 5) and the die. Right of the board: the three Wilds decks and their discard piles, the King's Champion, and the fight area (enemy card, used items, the fighter's cards, the helper's cards).

Each seat has a player board with HP (− +, FULL, MAX − +), gold (− +) and the three stats (− +), and spots for the character card, three Abilities (face down when used), three equipment items, one-use items and the hidden objective. Levels are the coloured markers on the track.

Three buttons sit under TTS's own toolbar at the top left:

| Button | What it does |
|---|---|
| START GAME | Puts everything back, shuffles the middle and outer rings of the board (GDD §3) and deals (§4): a character, its 3 Abilities, a hidden objective and a full hand to each seat, HP, 3 gold, level 1, pawns on the Camps, a random first player. |
| BOT GAME | Opens a small menu: the full bot game, the short bot game and the speed. While bots play, the button reads STOP BOTS. |
| RESET | Stops the bots and puts every card back in its deck. |

Drawing cards, revealing enemies and clearing a fight are done by hand.

## Bots for the gameplay video

Four bots (Ann, Ben, Cleo, Dan) play a whole game in TTS by themselves. Pawns walk, the die rolls, cards are drawn and played face up, damage tokens go on the enemy, and the HP, gold and level counters change. A caption at the bottom of the screen says what each step is ("Ann (Mage) fights a Bandit: 7 damage, wins, +1 level") and a panel on the right shows everyone's level, HP and gold. The bots make help deals, sabotage each other, dig deep, complete hidden objectives and face the King's Trial.

In TTS: BOT GAME, then Full game or Short game. Speed changes the pace (0.75x to 2x) and can be pressed during a game; BOT GAME (now STOP BOTS) stops it. Both games are stored in the save, so nothing else needs to run.

During a bot game the camera goes wherever the next step happens (Camera: free in the same menu leaves it to you), the acting player's hand is shown as cards at the bottom of the screen, the caption and the status list use each player's colour, and whatever a bot touches glows in its colour.

| Game | 0.75x | 1x | 1.5x | 2x |
|---|---|---|---|---|
| Full game (seed 1): 13 rounds, three Trial attempts, Ann (Mage) wins | 24:35 | 18:26 | 12:17 | 9:13 |
| Short game (seed 94): starts at levels 6-8, ends with the Trial, Ben (Mage) wins | 6:11 | 4:38 | 3:05 | 2:19 |

The same games, or any other seed, can also be sent from a terminal in this folder (TTS open, save loaded):

```
python3 bots/play.py                 # full game
python3 bots/play.py --mode demo     # short game
python3 bots/play.py --speed 1.5     # any speed
python3 bots/play.py --seed 12       # another game; the same seed always replays the same game
python3 bots/play.py stop            # stops a running game (Ctrl+C in its window does the same)
```

More options: `--dry-run` prints the game with timestamps without TTS, `--find 10` lists seeds whose games show every mechanic, `--no-camera` leaves your camera alone. The bots' decisions come from the balance simulator that set the GDD's numbers. `python3 bots/stats.py 500` plays 500 games without TTS and prints what happened in them.

## Checks

- `tts/build.py` stops if the card or tile counts don't match the GDD (132 cards, 49 tiles).
- `python3 tests/check_tts_script.py` plays both stored bot games against a fake TTS, once through the BOT GAME button and once as `bots/play.py` sends them, then presses every button: no script error, all 132 cards still on the table, every bot's hand and items match the engine. It needs Lua (`brew install lua`).
- `python3 tests/live_check.py` does the real thing in a running TTS with the save loaded: counts the pieces, plays the short demo at double speed, counts again and resets the table (about 2.5 minutes). Don't run it while recording.
