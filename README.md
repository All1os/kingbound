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

Each seat has a player board with HP, max HP, gold and the three stats, and spots for the character card, three Abilities (face down when used), three equipment items, one-use items and the hidden objective. Levels are the coloured markers on the track.

| Button | What it does |
|---|---|
| BUILD BOARD | Shuffles the middle and the outer ring (GDD §3). The Castle, Camps and Wilds I stay. |
| SETUP | Deals a character, its 3 Abilities, a hidden objective and a full hand to each seat; sets HP, 3 gold and level 1; puts the pawns on the Camps; picks the first player. |
| DRAW ACTION | One Action card into your hand. An empty deck is refilled from its discard pile. |
| WILDS I / II / III | Reveals the top card of that deck in the fight area. |
| MERCHANT | Reveals 3 Loot cards. |
| KING'S TRIAL | Moves the Champion card into the fight area. |
| CLEAR FIGHT | Sends everything in the fight area to its discard pile, removes the damage tokens and puts unbought Loot under the Loot deck. |
| RESET | Puts every card back in its deck. |

## Bots for the gameplay video

Four bots (Ann, Ben, Cleo, Dan) play a whole game in TTS by themselves. Pawns walk, the die rolls, cards are drawn and played face up, damage tokens go on the enemy, and the HP, gold and level counters change. A caption at the bottom of the screen says what each step is ("Ann (Mage) fights a Bandit: 7 damage, wins, +1 level") and a panel on the right shows everyone's level, HP and gold. The bots make help deals, sabotage each other, dig deep, complete hidden objectives and face the King's Trial.

Before you start: TTS open, KINGBOUND-prototype loaded. Then, in a terminal in this folder:

```
python3 bots/play.py                 # full game, from setup to the King's Trial
python3 bots/play.py --mode demo     # short game: starts mid-game at levels 6-8, ends with the Trial
python3 bots/play.py --speed 1.5     # faster; 0.7 is slower
python3 bots/play.py --seed 12       # another game; the same seed always replays the same game
python3 bots/play.py stop            # stops a running game (Ctrl+C in its window does the same)
```

| Game | Speed 1.0 | Speed 1.5 | Speed 2.0 |
|---|---|---|---|
| Full game (seed 1): 13 rounds, three Trial attempts, Ann (Mage) wins | 18:24 | 12:16 | 9:12 |
| Short demo (seed 94): 3 rounds, Ben (Mage) wins the Trial | 4:36 | 3:04 | 2:18 |

These lengths come from the bots' own timing; TTS adds a couple of seconds at the start.

More options: `--dry-run` prints the game with timestamps without TTS, `--find 10` lists seeds whose games show every mechanic, `--camera` also moves your camera between the board and the fight. The bots' decisions come from the balance simulator that set the GDD's numbers. `python3 bots/stats.py 500` plays 500 games without TTS and prints what happened in them.

## Checks

- `tts/build.py` stops if the card or tile counts don't match the GDD (132 cards, 49 tiles).
- `python3 tests/check_tts_script.py` plays the default bot game against a fake TTS and then presses every button: no script error, all 132 cards still on the table, every bot's hand and items match the engine. It needs Lua (`brew install lua`).
