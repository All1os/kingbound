# Changelog

All notable changes to the Kingbound prototype. Each version is also a GitHub release.

## Unreleased

- Story and look from the narrative document (`narrative and settingKINGBOUND.docx`): the GDD opens with the Royal Selection and the Royal Chronicle and has a short section on the world; cards use the document's palette (aged parchment, ink black, antique gold, oxide red for STR, deep forest green for AGI, muted cobalt for WIS) and book-like lettering for titles.
- Characters and Abilities renamed after the narrative, effects unchanged: Knight → Bellkeeper (Iron Toll, Stand Fast, Echo Guard), Rogue → Foxglove (Quickstep, Pocket Sand, False Image), Mage → Ash Scribe (Mark of Knowing, Ink Snare, Recollection), Cleric → Briar Knight (Thorn Lunge, Briar Mark, Riposte), Ranger → Hollow Pilgrim (Wandering Step, Lantern Veil, Wayfinder). "Snared" on Vanish and Smoke Bomb reads "veiled". The team's word Ability stays (the document says cantrip).
- Briar Knight is a STR/AGI duelist in the narrative: STR 2, AGI 3, WIS 0, HP 9 (was the Cleric's STR 2, WIS 3, HP 12). With AGI 3 at HP 12 it won 36% of 1,000 bot games; at HP 9 the five characters win 21-29% (1,200 games), about as spread as before.
- Which Ability name goes with which effect was our call where the document gives only names: the boost deals damage, the sabotage hurts a rival's fight, the signature keeps its old job.
- Three buttons instead of ten, under TTS's own toolbar at the top left (the old column covered the toolbar's menus): START GAME, BOT GAME and RESET. START GAME now shuffles the board and deals in one click. Drawing cards, revealing enemies and clearing a fight are done by hand.
- BOT GAME plays a scripted bot game inside TTS, with no terminal: the full game or the short one, at 0.75x to 2x speed. `build.py` lets the bots play both games and stores every command in the save; the button replays them. Pressing it again (STOP BOTS) stops the game. `bots/play.py` still sends any seed from a terminal.
- Script errors during a bot game are also printed in TTS's chat.
- Bot games show the cards: the hand of the player who acts is shown as card pictures at the bottom of the screen.
- Who is who: the caption's first line is in the acting player's colour, the status list marks whose turn it is (▶), that player's pawn and board glow for the whole turn, and the names on the player boards are bigger.
- The camera follows every step of a bot game: the board for turns, rolls and moves, the fight area, the acting player's hand and Abilities, their items and board when HP or gold change, the level track when a level changes, the Merchant's cards, a deck being reshuffled. It always looks from the bottom of the table and never turns; Camera: follows / free in the BOT GAME menu switches it off. In a fight it stays on the fight area for the fighter's own cards and only leaves for another player stepping in.
- Whatever a bot touches glows in its colour for a few seconds and gives a short pop; the tiles a pawn walks over light up.
- The die sits beside the Wilds discard piles, inside the camera's board and fight views.
- `bots/play.py` moves the camera the same way by default (`--no-camera` leaves it alone).
- The camera always looks from the bottom of the table and never turns. When it shows a card at another seat (drawn, flipped, bought), the card turns to face the camera for a few seconds, then back to its player.
- The bots are called Bora, Anastasya, Amira and Esma, and each seat has a name plate in its colour at the left end of the hand row.
- The full bot game now takes 18:51 and the short one 4:48 at speed 1 (longer names, longer captions).

## v0.1 (2026-10-13)

### Tabletop Simulator prototype

- `tts/build.py` builds the save from `Kingbound-GDD.md`, the same way as The Limit: text-only card faces drawn with Pillow on two sheets (4000×3360 and 4000×1680 px), a different back for each deck, 49 tiles, the level track, player boards, tokens and the save with its Lua.
- 132 cards, counted against the GDD: 45 Action, Wilds I / II / III 14 / 14 / 10, 1 King's Champion, 20 Loot, 8 hidden objectives, 5 characters, 15 Abilities. Every name, number and text was checked against the GDD's tables cell by cell (0 differences).
- The board: 49 tiles on a 7×7 grid with the rings turned inside out (§3): the Castle in the middle, the 4 Camps next to it, Wilds I on the inner corners, the middle ring (10 Wilds II, 2 Merchant, 2 Barracks, 2 Healer) and the outer ring (21 Wilds III, 1 Merchant, 1 Barracks, 1 Healer) each shuffled within itself. Tiles are coloured by ring. The save opens with a board already built.
- Level track 1 to 10 under the board with a marker per player; a player board per seat with HP, max HP, gold and STR / AGI / WIS; damage tokens worth 1 and 5; four pawns; one die; a player aid.
- Buttons: BUILD BOARD, SETUP, DRAW ACTION, WILDS I / II / III, MERCHANT, KING'S TRIAL, CLEAR FIGHT, RESET. Everything can still be done by hand.
- `tts/preview.py` draws the table from above, so the layout can be checked without TTS.

### Bots for the gameplay video

- `bots/play.py`: four bots play Kingbound in a running TTS, from setup to the King's Trial, and the table moves with them: pawns walk, the die rolls, cards are drawn and played, damage tokens go on the enemy, HP / gold / level counters change. Every step gets a caption at the bottom of the screen and a status panel shows everyone's level, HP and gold.
- Speed is adjustable (`--speed`), a seed replays the same game (`--seed`), one command starts it and `play.py stop` (or Ctrl+C) stops it.
- Short demo mode (`--mode demo`): starts mid-game with everyone at level 6 to 8 and ends with the Trial. The default demo game takes 4:36 at speed 1.0; the default full game 18:24 (12:16 at speed 1.5).
- `bots/engine.py`: the rules and the bots' decisions, ported from the balance simulator that set the GDD's numbers, with its references moved to the team GDD. Extended so the video shows every mechanic: help deals for pay, sabotage Abilities and the Cursed Totem, Dig Deep, hidden objectives, Pickpocket and the King's Trial. In 500 bot games: median 14 table rounds; per game 5.4 help deals, 7.4 sabotages, 8.4 digs, 1.6 completed objectives and 2.0 Trial attempts.
- `bots/stats.py` plays many games without TTS and prints what happened in them.
- `tests/check_tts_script.py` runs the table script against a fake TTS with the commands of a whole bot game, then presses every button. It found one real bug before release (a Merchant visit would not have shown the item that was bought). 65 games pass.
- `tests/live_check.py` checks the save in a running TTS: the script answers, all 132 cards, 49 tiles, 4 pawns, 4 level markers and 4 player boards are on the table, the demo game runs without a script error, then the table is reset.

### Decisions the GDD left open

- Seats are Red, Yellow, Green and Blue (the colours of the team's table sketch), clockwise from the bottom. Each player starts on the Camp on their side of the Castle (§4 only asks for different Camps).
- Characters, Abilities and the Champion have no IDs in the GDD; the cards use C1-C5, KN1 to RA3 and CH.
- Cards carry the GDD text word for word. A few lines from other sections were added: "WIN: +N LEVELS" on enemies (§6.5), the Trial lines on the Champion (§8), the equipment limit or "One use: discard after use" on Loot (§7, §10.4), the reward on objectives (§10.6). The back of an Ability card reads USED, since a used Ability is turned face down (§10.5).
- One shared player aid board instead of four (§2 lists four), to keep the table readable.
- The bots lay their hands face up on the table instead of in hidden hand zones, so the video shows their cards.
- Bot rulings where the rules are silent: a Healing Potion in the bot's own fight is drunk in step 2, not as an answer to sabotage ("You can't answer until the next round", §6.2); the Champion's 10-damage cap counts the damage put on it in a round and Hex removes tokens after that; a helper plays only its own cards and its boost; bots never trade; the Rogue uses Pickpocket at the start of its turn or right after moving; Training Manual and Elixir are used as soon as they are taken; with 3 equipment items a new one only replaces the weakest if it is better; after Ambush! an event is resolved as a normal draw.
- Bots sabotage the Trial, a leader about to reach level 7 or more, or any fight when they hold the Spoiler objective, and keep their sabotage for the Trial once someone else is at level 9. Help costs 1, 2 or 3 gold by tier (1 less for a Sellsword) or the enemy's loot, and nobody helps a leader who is close to winning.

### Fixed after the first test in Tabletop Simulator

- The save would not load: the player boards and the player aid had their description written into the "Locked" field, which must be true or false. `build.py` now checks the type of every field before writing the save.
- The level track, the player aid and the player boards were drawn square. TTS draws a tile square when Stretch is off and in the image's shape when it is on (2 × scale deep, 2 × scale × width / height wide); non-square tiles now use Stretch with an even scale.
- Bot commands did not find their cards: TTS hands the nested lists of a message to Lua as C# objects. Each command now travels as one JSON string that the table script decodes.
- Player boards are bigger (6.3 × 3.6) and simpler: − and + beside HP and gold, FULL and MAX − / + under HP, − and + for each stat. They now sit fully on the felt.
- Checked in TTS: the save loads, every piece is on the table (132 cards, 49 tiles, 4 pawns, 4 level markers, 4 player boards, the die), and the short bot game ran at double speed with no script error and all 132 cards still on the table.

## Next

- Record the gameplay video with `bots/play.py`.
- To share the save, upload the images with TTS's Cloud Manager and fill in `tts/cloud_urls.json`.
