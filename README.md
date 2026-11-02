# Kingbound

Kingbound is a real-time dungeon race for 3 to 5 players, played in Tabletop Simulator. There are no turns. For 10 minutes everyone rolls their dice at the same time, opens new rooms, fights monsters and grabs treasure. The game has two rounds: in the first you collect points, in the second an event threatens the dungeon and you have to escape to the Safe Room with what you carry. When the timer runs out, the player with the most points wins.

![A game of Kingbound in Tabletop Simulator: round 2, three rooms closed by the Dungeon Collapse](realtime/workshop/dungeon.jpg)

## Getting the game

Subscribe to [Kingbound on the Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3827233466). In Tabletop Simulator it is then under Games → Workshop.

You can also download `KINGBOUND-realtime.json` from the [latest release](https://github.com/All1os/kingbound/releases/latest) and put it in your Tabletop Simulator Saves folder (`Documents/My Games/Tabletop Simulator/Saves` on Windows, `~/Library/Tabletop Simulator/Saves` on a Mac). It shows up under Games → Save & Load.

## Starting a game

Sit at Red, Yellow, Green, Blue or Purple: pick the colour when you join, or later by clicking your name at the top right and choosing Change Color. Each player's mat lies on their own side of the table: Red in the south, Yellow in the west, Green in the north, Blue in the east, and Purple next to Red for a fifth player. The top of the mat shows what each action needs. Press START GAME at the top left of the screen. It shuffles the decks, gives everyone 4 dice, puts all the characters in the Safe Room and starts the 10-minute timer with round 1. RESET TABLE puts everything back where it was.

## How to play

Each die shows Movement (green), Attack (red) or Magic (blue). Roll whenever you want: ROLL DICE at the top left rolls all 4 of your dice at once. Keep the dice you need and reroll the rest as often as you like; to roll a single die, point at it and press R. When you have the symbols for an action, do it.

| Action | Dice |
|---|---|
| Move to a connected room | 2 Movement |
| Open a new room | 2 Movement |
| Beat a weak monster | 2 Attack |
| Beat a medium monster | 3 Attack |
| Beat a strong monster | 4 Attack |
| Take a treasure or an object | 2 Magic |
| Secure your treasure, standing in the Safe Room | none |
| Place an object, standing in the special objects room | none |

To open a room, take the top card of the room deck, flip it and lay it next to the room you are in so that the passages connect. If it is a monster room or a treasure room, put the top card of that token deck face up on it. You fight a monster or take a treasure in its own room.

A beaten monster goes straight to the POINTS box on your mat. A treasure goes to the CARRIED box first. It counts only after you bring it back to the Safe Room and move it to POINTS.

### Treasure sets

There are three types of treasure: common, rare and special. A treasure on its own gives no points. One of each type makes a set worth 5 points.

### Special objects

Three objects are mixed into the treasure tokens. Take one like a treasure, carry it to the special objects room and drop it on its own place there: it gives you 2 points. When all three places are filled, the goal is completed.

### Round 2: escape

At 5:00 round 2 starts and an event card turns up next to the event deck:

- Dungeon Collapse, Flood, Magical Chaos: 3 rooms get a destruction token. Nobody can go into a closed room.
- The Awakening of the Monster: a strong monster appears and chases the players. Every 30 seconds it moves one room towards the nearest character. You can't leave its room until you beat it (4 Attack, 4 points).

Get back to the Safe Room before the timer runs out: treasure still in your CARRIED box at 0:00 is lost.

When the timer reaches 0:00, everyone stops and counts their POINTS box: beaten monsters, treasure sets and placed objects. If two players have the same score, the one who beat more monsters wins.

## Versions

See the [changelog](CHANGELOG.md). Version 0.1 was an earlier, turn-based design of Kingbound. It is in the [turn-based](turn-based) folder, and its rules are in [Kingbound-GDD.pdf](turn-based/Kingbound-GDD.pdf).
