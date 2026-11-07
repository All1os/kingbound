# Changelog

## v2.5 (2026-11-07)

The team's component list, "New prototype number of every component":

- 19 rooms in the deck instead of 23, plus the Safe Zone: 4 empty, 7 monster, 7 treasure and the Integration Chamber.
- 7 monster tokens: 3 Scrapers, 2 Carriers, 2 Anomalies.
- 7 alien tokens, in the same split as the monsters, and 7 black hole tokens.
- Extra Special Tile is now called +1 Special Object Tile, and four more special objects come with the second chamber.

## v2.4 (2026-11-06)

After a balance test with a simulation of the game:

- 2 to 4 players. The fifth seat, Purple, is gone; Red sits in the middle of the south side.
- The Integration Chamber is always in the top 5 cards of the room deck. Shuffled anywhere in the deck, it often stayed unopened in round 1, and then nobody could complete the special task. On a real table: take the chamber out, shuffle the deck, shuffle the chamber with the top 4 cards and put the 5 cards back on top.

## v2.3 (2026-11-06)

The team's GDD of 2026-11-05, "Changes after a series of playtests before the Game Jam":

- Rockfall is gone: its rocks could block the way completely. The rock tokens are gone too.
- Poison Gas is gone, and so are the gas tokens.
- No more treasure combinations. Each treasure counts on its own: a Module is 3 points, an Archive 2, a Specimen 1. The right side of the mat lists what each treasure and monster is worth.
- Lost Path: the Safe Zone and the Integration Chamber swap places. Players swap the two tiles by hand, and the table finds the Safe Zone wherever its tile lies. The Safe Zone token is gone.
- Time Freeze: instead of 15 seconds without moving, a roll for the order. Everyone rolls at once; the most identical symbols goes first, and the others wait. Same number: the lowest score goes first. It lasts one cycle.
- Six event cards are left: Lost Path, Time Freeze, Extra Risk, Extra Special Tile, Aliens and Black Holes.

## v2.2 (2026-11-04)

The team's GDD of 2026-11-04: seven more event cards for round 2. The players turn up a card from the deck of eight and set out its tokens by hand; the table reads the tokens (gas, black holes, the Safe Zone token):

- Rockfall, as before.
- Lost Path: the Safe Zone moves 5 rooms away. A Safe Zone token marks the new one.
- Time Freeze: nobody can move for 15 seconds.
- Extra Risk: draw one or two more event cards.
- Extra Special Tile: a second Integration Chamber. An object on either chamber completes your special task.
- Poison Gas: gas in an empty room and the rooms beside it. Entering one costs 1 point.
- Aliens: every monster becomes an alien with 1 HP more.
- Black Holes: in every room with treasure. Going through one costs 1 point.
- The points lost to gas and black holes are shown at 0:00.
- The event card text now always fits on the card.
- The special objects have a deck of their own, apart from the treasure tokens.
- Last one done: the player who finishes last in a cycle rolls 3 dice next cycle (ROLL 3 DICE button).
- ROUND 2 and END GAME buttons jump the timer.

## v2.1 (2026-11-03)

Kingbound is now NULLWAKE, set in ORPHEON, an abandoned research station. The team's new rules and the narrative document:

- A new look: graphite, steel and cold blue instead of parchment and gold. The rooms are station sectors: Safe Zone, Unregistered Sector, Infested Sector, Recovery Storage and the Integration Chamber.
- Monsters have HP: Scraper 1, Carrier 2, Anomaly 3, worth 1, 2 and 3 points. Each Attack deals 1 damage and the damage stays. Right-click a monster and choose Hit.
- Treasure: Modules, Archives and Specimens, scored with the table on your mat (a Module alone is 3, a combination like 2 Modules + 1 Archive is 5).
- The mats are wider. CARRIED is gone: a TREASURE box, a MONSTERS box and the treasure points table.
- The Integration Chamber has four slots, and there are four special objects. Objects are placed in round 2 only; placing one completes your special task. Objects no longer give points.
- Round 2 has one event, Rockfall: rocks fill every Unregistered Sector (the empty rooms) with nobody in it. No new rooms can be opened in round 2.
- At 0:00 the game shows who escaped: in the Safe Zone with the special task completed. Everyone else loses all their points. A tie is a draw.
- Play in cycles: everyone rolls, rerolls once, acts, and waits for the others.
- The save is now called NULLWAKE.

## v2.0 (2026-11-02)

The team's new design document:

- Two rounds of 5 minutes: collect points, then escape. Round 2 starts with an event card.
- Four event cards: Dungeon Collapse, Flood and Magical Chaos close 3 rooms with destruction tokens; The Awakening of the Monster brings a strong monster that chases the nearest player.
- Treasure gives no points on its own: one common, one rare and one special make a set worth 5 points.
- A special objects room with three places. The three objects are in the treasure tokens; placing one gives 2 points.
- The Loot Deck and its Prank cards are gone, and so are the trap rooms.
- Every mat is a seat: in an online game each player picks Red, Yellow, Green, Blue or Purple and sits at their own mat.
- ROLL DICE at the top left rolls all 4 of your dice at once.

## v1.1 (2026-10-26)

- Every player's mat lies on their own side of the table and faces them: Red in the south, Yellow in the west, Green in the north, Blue in the east, Purple next to Red. The dungeon grows from the middle of the table.
- Each mat shows what each action needs, so the shared action chart is gone.
- Each player's dice start on their mat.
- The name plate on the table only says KINGBOUND, in a new design.

## v1.0 (2026-10-26)

The finished game: a real-time dungeon race for 3 to 5 players in Tabletop Simulator, 10 minutes long.

- Everyone plays at once with 4 dice each. The dice show Movement, Attack and Magic.
- A deck of 28 rooms that you open one by one around the Safe Room: empty rooms, monster rooms, treasure rooms and six traps (Spike Pit, Pressure Plate, Collapsing Passage).
- Monster tokens in three strengths and treasure tokens worth 1 to 3 points. A special treasure also gives a Loot card.
- Treasure counts only once it is carried back to the Safe Room.
- A Loot Deck of 18 cards: weapons, equipment, one-use items and four Prank cards to play against the other players.
- A mat for each player with boxes for dice, Loot, carried treasure and points.
- START GAME shuffles the decks, deals the dice and starts the 10-minute timer. RESET TABLE puts everything back.
- On the Steam Workshop.

## v0.1 (2026-10-13)

An earlier, turn-based design for 4 players. They move around a 7×7 board, fight monsters with Action cards, collect Loot and level up, and the first to win the King's Trial at the Castle wins the game. It is in the `turn-based` folder; its rules are in `turn-based/Kingbound-GDD.pdf`.
