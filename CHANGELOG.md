# Changelog

All notable changes to the Kingbound prototype. Each version is also a GitHub release.

## Unreleased

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

### Decisions the GDD left open

- Seats are Red, Yellow, Green and Blue (the colours of the team's table sketch), clockwise from the bottom. Each player starts on the Camp on their side of the Castle (§4 only asks for different Camps).
- Characters, Abilities and the Champion have no IDs in the GDD; the cards use C1-C5, KN1 to RA3 and CH.
- Cards carry the GDD text word for word. A few lines from other sections were added: "WIN: +N LEVELS" on enemies (§6.5), the Trial lines on the Champion (§8), the equipment limit or "One use: discard after use" on Loot (§7, §10.4), the reward on objectives (§10.6). The back of an Ability card reads USED, since a used Ability is turned face down (§10.5).
- One shared player aid board instead of four (§2 lists four), to keep the table readable.
- The bots lay their hands face up on the table instead of in hidden hand zones, so the video shows their cards.
- Bot rulings where the rules are silent: a Healing Potion in the bot's own fight is drunk in step 2, not as an answer to sabotage ("You can't answer until the next round", §6.2); the Champion's 10-damage cap counts the damage put on it in a round and Hex removes tokens after that; a helper plays only its own cards and its boost; bots never trade; the Rogue uses Pickpocket at the start of its turn or right after moving; Training Manual and Elixir are used as soon as they are taken; with 3 equipment items a new one only replaces the weakest if it is better; after Ambush! an event is resolved as a normal draw.
- Bots sabotage the Trial, a leader about to reach level 7 or more, or any fight when they hold the Spoiler objective, and keep their sabotage for the Trial once someone else is at level 9. Help costs 1, 2 or 3 gold by tier (1 less for a Sellsword) or the enemy's loot, and nobody helps a leader who is close to winning.

### Not checked yet

- The save has not been opened in Tabletop Simulator yet: TTS was closed while this was built. The fake TTS catches script errors, not looks. v0.1 follows the first check in TTS.
