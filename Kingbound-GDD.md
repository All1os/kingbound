# Kingbound

Game Design Document v0.1: prototype rules. Based on Yusuf's original Kingbound draft.

## 1. Overview

| Players | Playtime | Genre |
|---|---|---|
| 4 | about 60 minutes | competitive role-playing adventure card game |

References: Munchkin (fighting and looting), Catan (random board), Slay the Spire (fighting with energy and cards).

The king needs one new soldier. Four recruits roam the realm, fight monsters, train and gear up. The first to reach level 10 is chosen. The last level only comes from beating the King's Champion at the Castle, and while you fight it, the other three try to stop you.

### Design goals

- Every turn is a risk choice: how deep into danger can I go with the cards in my hand?
- Your hand is your stamina. Cards you play are gone until you rest, and resting costs a turn.
- Nobody just waits: during your fight, the others can help you for a price or sabotage you.
- The game ends with a public climax, the King's Trial.

### Core loop

```
REST (refill hand, ready Abilities)   or   TRAVEL (roll, move)
  -> stop on a tile: fight / event / buy / train / heal
  -> win a fight: levels + gold (+ loot) -> stronger build -> go deeper
  -> at level 9: walk to the Castle and face the King's Trial
```

## 2. Components

| Component | Count | Notes |
|---|---|---|
| Board frame | 1 | Holds a 7×7 grid of tiles |
| Tiles | 49 | 1 Castle, 4 Camp, 3 Merchant, 3 Barracks, 3 Healer, 4 Wilds I, 10 Wilds II, 21 Wilds III |
| Character cards | 5 | Stats printed on them (§10.5) |
| Ability cards | 15 | 3 per character (§10.5) |
| Action deck | 45 | Shared by everyone: 15 STR, 15 AGI, 15 WIS (§10.1) |
| Wilds I deck | 14 | 10 enemies + 4 events |
| Wilds II deck | 14 | 10 enemies + 4 events |
| Wilds III deck | 10 | 8 enemies + 2 events |
| Champion card | 1 | The King's Trial (§8) |
| Loot deck | 20 | Items (§10.4) |
| Objective cards | 8 | Hidden objectives (§10.6) |
| Level track | 1 | 1 to 10, one marker per player |
| Pawns | 4 | |
| Die | 1 | Six-sided |
| Gold | about 60 coins | Or a counter per player |
| HP counters | 4 | Dial or counter per player |
| Damage tokens | about 30 | Placed on enemies |
| Player aid | 4 | Turn and fight summary |

132 cards in total.

## 3. The board

A 7×7 grid of square tiles in three rings around the Castle. The land around the Castle is safe; the strongest enemies live on the frontier at the edges. The further out you go, the more an enemy is worth. You start next to the Castle, head out to grow stronger, and walk back to the Castle for the Trial.

```
 3  3  3  3  3  3  3      K = Castle (centre)
 3  2  2  2  2  2  3      C = Camp (start tiles, next to the Castle)
 3  2  1  C  1  2  3      1 = inner ring:  Wilds I + Camps
 3  2  C  K  C  2  3      2 = middle ring: Wilds II + town tiles
 3  2  1  C  1  2  3      3 = outer ring:  Wilds III + 3 frontier towns
 3  2  2  2  2  2  3
 3  3  3  3  3  3  3
```

| Ring | Squares | Tiles | Danger |
|---|---|---|---|
| Centre | 1 | Castle | the King's Trial |
| Inner | 8 | 4 Camp, 4 Wilds I | Tier I: +1 level per kill |
| Middle | 16 | 10 Wilds II, 2 Merchant, 2 Barracks, 2 Healer | Tier II: +2 levels per kill |
| Outer | 24 | 21 Wilds III, 1 Merchant, 1 Barracks, 1 Healer | Tier III: +3 levels per kill |

**Building the board.** The board is random every game:

1. Place the Castle in the centre and the 4 Camps on the 4 tiles next to it (north, east, south, west).
2. Put the 4 Wilds I tiles on the 4 corner squares of the inner ring.
3. Shuffle the 16 middle-ring tiles face down, lay them around the middle ring and turn them face up.
4. Do the same with the 24 outer-ring tiles.

The town tiles land in different places every game, so the routes change.

## 4. Setup

1. Build the board (§3).
2. Shuffle the 5 Character cards and deal 1 face up to each player. Put the fifth back in the box. Take your 3 Ability cards face up (ready).
3. Shuffle the 8 Objective cards and deal 1 face down to each player. Look only at your own.
4. Shuffle the Action deck. Each player draws up to their hand size (5, Ranger 6).
5. Shuffle the three Wilds decks and the Loot deck, each on its own.
6. Each player starts at level 1, with HP at the maximum printed on their character, and takes 3 gold.
7. Each player puts their pawn on a different Camp. Pick the first player at random. Play goes clockwise.

## 5. Your turn

On your turn, choose **REST** or **TRAVEL**.

### 5.1 REST

1. Discard any number of Action cards from your hand, then draw up to your hand size.
2. Turn all your used Ability cards face up (ready again).
3. If you are on a Camp, heal to full HP.
4. Your turn ends.

### 5.2 TRAVEL

1. Roll the die. Move your pawn from 1 tile up to the number rolled, horizontally or vertically (no diagonals).
2. You may move through any tile and past any pawn. Only the tile where you stop counts.
3. You must stop on a different tile than the one you started on.
4. You may not stop on the Castle unless you are level 9 (§8).
5. Resolve the tile where you stopped (§5.3).

### 5.3 Tiles

| Tile | What happens |
|---|---|
| Wilds I / II / III | Draw the top card of that tier's Wilds deck. Enemy: fight it (§6). Event: do what it says (§10.3). You must draw; stopping here means you chose the danger. |
| Merchant | Draw 3 Loot cards. You may buy one of them at its price. Put the others on the bottom of the Loot deck. |
| Barracks | Raise a stat by 1. The cost in gold is the new value: 2→3 costs 3, 4→5 costs 5. Max 5. Buy as many raises as you can pay for. |
| Healer | Pay 1 gold for each 3 HP healed (never above your max). |
| Camp | Nothing happens when you arrive. If you REST here later, you heal to full. |
| Castle | Level 9 only: the King's Trial (§8). |

After a fight, put the enemy card on its deck's discard pile, whatever the result. When any deck runs out, shuffle its discard pile to make a new deck.

### 5.4 Trading

Any time outside a fight, two players may trade gold and Loot items in any mix, if both agree. Action cards and Abilities can't be traded. Promises are not binding, except the payment in a help deal (§6.6).

## 6. Fights

### 6.1 What you fight with

| Resource | How it works |
|---|---|
| Hand | Your Action cards. A card you play is gone until you REST, so the same hand has to last through several fights. Hand size (5, Ranger 6) is how many cards you draw up to when you REST; some effects let you hold more. |
| Energy | 3 each round (Rogue 4). Each card costs 0, 1 or 2 energy. Energy you don't spend is lost at the end of the round. |
| Stats | Each Action card has a type: STR, AGI or WIS. Add your stat of that type to the card's number. Strike says "Deal 2 + STR damage": with STR 3 it deals 5, with STR 0 it deals 2. |
| Abilities | Every character has 3. Using one turns it face down; you get it back when you REST. |
| HP | Enemies take it away. You can also spend it in your own fight to draw more cards (Dig Deep, §6.2 step 2). |

### 6.2 A fight round, step by step

Reveal the enemy. Before round 1 you may make a help deal (§6.6). Then repeat these steps:

| Step | What happens |
|---|---|
| 1. FIGHT or FLEE | Choose one. If you flee, see §6.4. |
| 2. You play | Play any Action cards you can pay for and use your own Abilities, in any order. Put damage tokens on the enemy and keep track of your Block. Dig Deep: you may also lose 2 HP to draw 1 Action card, as often as you like, but never down to 0 HP (only in your own fight). |
| 3. Your helper plays | Only if you made a deal (§6.6). |
| 4. Interference | Going clockwise from you, each other player may use any of their ready Abilities and items on your fight, to help or to sabotage, or pass. Go around the table once. You can't answer until the next round. |
| 5. Check | If the damage on the enemy is equal to or more than its HP, you win (§6.5) and it doesn't attack. |
| 6. The enemy attacks | You take damage equal to its ATK, minus your Block, minus your Guard roll (never below 0). |
| 7. End of round | If your HP is 0, you are knocked out (§6.5). Otherwise, Block and unused energy are lost, traits that say "at the end of each round" happen, and the next round starts at step 1. |

| Guard roll | Damage |
|---|---|
| 1-2 | no change |
| 3-4 | 1 less |
| 5-6 | 2 less |

With no cards left you can still choose FIGHT (and use Abilities) or FLEE.

### 6.3 Damage and Block

- Damage stays on the enemy between rounds unless a trait removes it.
- Block only lasts for the round you got it in.
- Items that say "every fight round" add their Block on their own.

### 6.4 FLEE

Roll the die.

| Roll | Result |
|---|---|
| 4-6 | You escape. The fight ends with no reward. Some enemies take gold when you flee; their card says so. |
| 1-3 | You fail. The enemy attacks you, and only your Guard roll and item Block reduce the damage. Then the next round starts and you choose again. |

The AGI card Vanish and the Smoke Bomb item let you escape without rolling. Snare (Ranger) stops every kind of fleeing.

### 6.5 Winning and being knocked out

**Win.** Gain the level reward for the enemy's tier: Tier I +1, Tier II +2, Tier III +3. Take the gold printed on the card. If the card says LOOT, draw the top Loot card for free. Your level can't go above 9 this way (§8).

**Knocked out (HP 0).**

- Lose 1 level (never below 1).
- Move your pawn to the nearest Camp. If two are equally near, you choose.
- Your HP goes back to full. Your hand and Abilities stay as they are.
- Your turn ends. Your helper gets nothing.

### 6.6 Help for pay

Before round 1, you may ask the table for help. Anyone may make an offer, for example "I'll help for 2 gold" or "I want the loot". You may accept one offer. Only one player can help in a fight.

- The helper fights with their own hand. In step 3 of each round they get 2 energy, and they may play their own Action cards (with their own stats) and use their boost Ability. Block that the helper plays protects you.
- The enemy attacks only you. The helper only risks their cards.
- You pay only if you win, right after the fight. Payment can be gold, the loot the enemy drops, or both.
- Levels always go to the fighter. They can't be paid or shared.
- The payment you agreed on must be made. Other promises don't have to be kept.
- Nobody can help in the King's Trial.

This is the Munchkin rule where the helper gets part of the treasure. Helping the leader means selling them the win, while helping the player in last place costs little.

### 6.7 Interference

Every character has one **boost** Ability that damages the enemy and can be used in any fight, and one **sabotage** Ability that can only be used in another player's fight. Some items work the same way: the Bomb helps and the Cursed Totem sabotages. Nobody needs permission. In step 4 anyone may act. A boost used in someone's fight without a deal is a gift.

Every kill brings a rival closer to level 10, but your sabotage only comes back when you REST. If you spend it on someone's Tier I fight, you may not have it when the leader faces the Trial.

### 6.8 Example fight

Mira plays the Knight: STR 3, AGI 0, WIS 1, HP 13, 3 energy. Mira is level 4, carries an Iron Sword (+1 damage on STR cards) and holds Strike, Heavy Blow, Brace, Spark and Dodge. Mira stops on a Wilds II tile and draws an Orc Raider (HP 13, ATK 4, 3 gold).

**Before round 1.** Ben (Rogue) offers Backstab for 2 gold. Mira expects 15 damage to be enough and says no.

**Round 1.**

- Mira plays Heavy Blow (2 energy) for 5 + 3 STR + 1 sword = 9, and Strike (1 energy) for 2 + 3 + 1 = 6. That makes 15 damage.
- Interference: Ben passes. Lea (Mage) uses Hex and removes 4 damage, so the damage is 11.
- Check: 11 is less than 13, so the Orc survives.
- The Orc attacks: ATK 4, no Block. Mira rolls a 4 on the Guard roll, so takes 1 less. Mira goes from 13 HP to 10.

**Round 2.**

- Mira has Brace, Spark and Dodge left. Spark (1 energy) deals 2 + 1 WIS = 3 (the sword only helps STR cards). The damage is now 14, so the Orc falls before it can attack.
- Mira gains 2 levels (4 → 6) and 3 gold.

Lea's Hex stays face down until Lea rests. Mira has two cards left and neither deals damage, so Mira will probably REST next turn.

## 7. Getting stronger

Gold comes from kills and events. You spend it in three places:

| Place | What gold buys |
|---|---|
| Barracks | Stats (§5.3). One stat point makes every card of that type stronger. |
| Merchant | Items (§10.4). You can hold at most 3 equipment items; to take a fourth, discard one. One-use items don't count toward the limit. |
| Healer | HP (§5.3). |

Two things are free: a REST refills your cards and Abilities, and a REST on a Camp also heals you.

## 8. Winning: the King's Trial

- You gain levels from kills (§6.5), from your objective (§9) and from two events. None of these can take you above level 9.
- At level 9 you may stop on the Castle. Stopping there starts the Trial at once: a fight against the **King's Champion** (HP 20, ATK 5).
- The Champion takes at most 10 damage per round; damage above 10 in one round is lost. So the Trial always lasts at least two rounds, and everyone gets a chance to act.
- Nobody can help you in the Trial. Everyone else may interfere as usual, and they will.
- If two players are at level 9, both may try. The first to win wins.

| Trial result | What happens |
|---|---|
| Win | You reach level 10, the king chooses you and the game ends. |
| Flee | You stay on the Castle. On a later turn that you start on the Castle, you may face the Trial again in place of REST or TRAVEL. You may also REST there first. |
| Knocked out | The normal rules apply (§6.5). You drop to level 8, go to the nearest Camp and must earn level 9 again. |

## 9. Hidden objectives

- Each player gets one objective at setup, face down. Look only at your own.
- Track your progress yourself; a die or a few coins next to the card is enough.
- When you complete it, show it and gain 2 levels (never above 9).
- One objective per player per game.

## 10. Card lists

### 10.1 Action deck: 45 cards, shared

Every type has the same skeleton (basic attack ×5, big attack ×3, defence ×3) plus two cards that give it a personality. Numbers are before items.

| ID | Card | Type | Cost | Copies | Text |
|---|---|---|---|---|---|
| ST1 | Strike | STR | 1 | 5 | Deal 2 + STR damage. |
| ST2 | Heavy Blow | STR | 2 | 3 | Deal 5 + STR damage. |
| ST3 | Brace | STR | 1 | 3 | Gain 3 + STR Block. |
| ST4 | Shield Bash | STR | 1 | 2 | Deal 1 + STR damage. Gain 2 Block. |
| ST5 | War Cry | STR | 0 | 2 | This round, each other STR card you play deals 2 more damage. |
| AG1 | Slash | AGI | 1 | 5 | Deal 2 + AGI damage. |
| AG2 | Ambush | AGI | 2 | 3 | Deal 4 + AGI damage. In round 1, deal 3 more. |
| AG3 | Dodge | AGI | 1 | 3 | Gain 3 + AGI Block. |
| AG4 | Quick Stab | AGI | 0 | 2 | Deal 1 + AGI damage. |
| AG5 | Vanish | AGI | 0 | 2 | Flee now, no roll. Not while Snared. |
| WI1 | Spark | WIS | 1 | 5 | Deal 2 + WIS damage. |
| WI2 | Firebolt | WIS | 2 | 3 | Deal 5 + WIS damage. |
| WI3 | Ward | WIS | 1 | 3 | Gain 3 + WIS Block. |
| WI4 | Mend | WIS | 1 | 2 | Heal 2 + WIS HP. |
| WI5 | Focus | WIS | 0 | 2 | Gain 2 energy this round. |

### 10.2 Enemies: 28 cards in the three Wilds decks

**Tier I (Wilds I): +1 level each.**

| ID | Enemy | Copies | HP | ATK | Gold | Loot | Trait |
|---|---|---|---|---|---|---|---|
| E11 | Giant Rat | 2 | 4 | 2 | 1 | | |
| E12 | Wolf | 2 | 5 | 3 | 1 | | |
| E13 | Goblin | 2 | 6 | 2 | 2 | | If you flee, lose 1 gold. |
| E14 | Bandit | 2 | 7 | 3 | 2 | | |
| E15 | Wild Boar | 2 | 8 | 3 | 1 | | Charge: deals 2 more damage in round 1. |

**Tier II (Wilds II): +2 levels each.**

| ID | Enemy | Copies | HP | ATK | Gold | Loot | Trait |
|---|---|---|---|---|---|---|---|
| E21 | Harpy | 2 | 11 | 5 | 2 | | |
| E22 | Dire Wolf | 2 | 12 | 5 | 2 | LOOT | |
| E23 | Orc Raider | 2 | 13 | 4 | 3 | | |
| E24 | Highwayman | 2 | 14 | 4 | 3 | | If you flee, lose 2 gold. |
| E25 | Troll | 2 | 15 | 4 | 3 | | At the end of each round, remove 2 damage from it. |

**Tier III (Wilds III): +3 levels each.**

| ID | Enemy | Copies | HP | ATK | Gold | Loot | Trait |
|---|---|---|---|---|---|---|---|
| E31 | Wraith | 2 | 17 | 6 | 3 | LOOT | Each STR and AGI card deals 1 less damage to it. |
| E32 | Wyvern | 2 | 18 | 7 | 4 | LOOT | |
| E33 | Ogre | 2 | 20 | 6 | 4 | | |
| E34 | Dark Knight | 2 | 22 | 6 | 5 | LOOT | Armor: the first damage card you play each round deals 2 less. |

**The King's Champion** (1 card, next to the Castle): HP 20, ATK 5. Takes at most 10 damage per round.

### 10.3 Wilds events: 10 cards

| ID | Deck | Event | Text |
|---|---|---|---|
| V11 | I | Lost Purse | Gain 2 gold. |
| V12 | I | Old Veteran | You may pay 2 gold to raise any stat by 1 (max 5). |
| V13 | I | Pit Trap | Roll the die. On 1-3, lose 2 HP. This can't take you below 1 HP. |
| V14 | I | Wandering Trader | Visit the Merchant here (§5.3). |
| V21 | II | Hidden Cache | Draw 1 Loot card for free. |
| V22 | II | Ambush! | Draw the next Wilds II card. If it is an enemy, it attacks you once before round 1 (your Guard roll and item Block count), then fight it as normal. If it is an event, resolve that instead. |
| V23 | II | Healing Spring | Heal to full HP. |
| V24 | II | Mercenary Captain | You may pay 4 gold to gain 1 level (not above 9). |
| V31 | III | Dragon Hoard | Gain 4 gold. Then draw the next Wilds III card and resolve it. |
| V32 | III | Ancient Shrine | Choose one: raise any stat by 1 (max 5), or heal to full and ready all your Abilities. |

### 10.4 Loot deck: 20 cards

**Equipment** (you may hold 3):

| ID | Item | Price | Copies | Text |
|---|---|---|---|---|
| L01 | Iron Sword | 4 | 1 | Your STR cards deal 1 more damage. |
| L02 | Hunting Bow | 4 | 1 | Your AGI cards deal 1 more damage. |
| L03 | Oak Wand | 4 | 1 | Your WIS cards deal 1 more damage. |
| L04 | Chain Mail | 4 | 1 | Gain 1 Block every fight round. |
| L05 | Tower Shield | 6 | 1 | Gain 2 Block every fight round. |
| L06 | Amulet of Vigor | 3 | 1 | Max HP +3. |
| L07 | Backpack | 4 | 1 | Hand size +1. |
| L08 | Lucky Charm | 3 | 1 | +1 to your Guard and Flee rolls. |
| L09 | Swift Boots | 2 | 1 | +1 to your movement roll. |

**One use** (discard after use; these don't count toward the 3):

| ID | Item | Price | Copies | Text |
|---|---|---|---|---|
| L10 | Training Manual | 4 | 2 | Raise any stat by 1 (max 5). |
| L11 | Healing Potion | 2 | 3 | Heal 5 HP. Any time, even in another player's turn, but not once you are at 0 HP. |
| L12 | Bomb | 2 | 2 | In any fight: deal 5 damage to the enemy. |
| L13 | Smoke Bomb | 1 | 1 | In your fight: flee, no roll. Not while Snared. |
| L14 | Cursed Totem | 2 | 2 | In another player's fight: the enemy deals 3 more damage this round. |
| L15 | Elixir | 3 | 1 | Draw Action cards up to your hand size. |

### 10.5 Characters and Abilities

| Character | STR | AGI | WIS | HP | Energy | Hand | How it plays |
|---|---|---|---|---|---|---|---|
| Knight | 3 | 0 | 1 | 13 | 3 | 5 | Steady hitter; a good helper to hire |
| Rogue | 1 | 3 | 0 | 8 | 4 | 5 | Fast, uses up cards quickly, steals gold |
| Mage | 0 | 1 | 3 | 10 | 3 | 5 | Big damage, fragile |
| Cleric | 2 | 0 | 3 | 12 | 3 | 5 | Two good stats, can draw extra cards |
| Ranger | 1 | 2 | 1 | 13 | 3 | 6 | Spread-out stats, bigger hand, moves far |

Each character has three Abilities: one **boost** (any fight), one **sabotage** (another player's fight only) and one **signature**. A used Ability is turned face down until you REST.

| Character | Boost | Sabotage | Signature |
|---|---|---|---|
| Knight | **Cleave:** deal 3 damage to the enemy. | **Provoke:** the enemy deals 3 more damage this round. | **Shield Wall** (any fight): the fighter gains 5 Block this round. |
| Rogue | **Backstab:** deal 4 damage to the enemy. | **Trip:** the fighter's Block this round becomes 0 (cards and items). | **Pickpocket** (your turn): take 2 gold from a player on your tile or a tile next to you. |
| Mage | **Fireball:** deal 5 damage to the enemy. | **Hex:** remove 4 damage from the enemy. | **Arcane Surge** (your fight): gain 2 energy this round. |
| Cleric | **Holy Light:** deal 4 damage to the enemy; the fighter heals 2 HP. | **Penance:** the fighter loses 2 HP. | **Prayer** (your turn or your fight): draw 2 Action cards. |
| Ranger | **Volley:** deal 3 damage to the enemy; the fighter gains 2 Block. | **Snare:** the fighter can't flee for the rest of this fight. | **Pathfinder** (after your movement roll): add 3 to it. |

### 10.6 Hidden objectives: 8 cards

Reward for each: show the card and gain 2 levels (not above 9).

| ID | Objective | Condition |
|---|---|---|
| O1 | Giant Slayer | Defeat a Tier III enemy. |
| O2 | Monster Hunter | Defeat 3 Tier II enemies. |
| O3 | Drillmaster | Have any stat at 5. |
| O4 | Well Equipped | Hold 3 equipment items at the same time. |
| O5 | Hoarder | Hold 10 gold at the same time. |
| O6 | Sellsword | Get paid for helping in 2 fights. |
| O7 | Spoiler | Twice, use a sabotage Ability or item in a fight that the fighter then loses (flees or is knocked out). |
| O8 | Close Call | Win a fight in which your HP dropped to 3 or less. |

## 11. Example: the first table round

- Ann (Mage) rolls 4 at the north Camp. There is a Merchant in the middle ring within reach, but Ann has 3 gold and would rather fight. Ann steps onto the Wilds I tile next to the Camp and draws a Bandit (HP 7, ATK 3). Spark deals 2 + 3 WIS = 5 and Quick Stab deals 1 + 1 AGI = 2. That is 7 damage, and the Bandit falls in round 1. Ann gains 1 level and 2 gold and has 3 cards left.
- Ben (Rogue) rolls 2 at the east Camp, moves one tile out into the middle ring and lands on a Wilds II tile: a Harpy (HP 11, ATK 5). Ambush deals 4 + 3 AGI + 3 for round 1 = 10, and Quick Stab deals 1 + 3 = 4. That is 14 damage for 2 of Ben's 4 energy, and the Harpy falls. Ben is level 3 after one turn.
- Cleo (Cleric) holds three AGI cards (AGI 0) and RESTs: Cleo discards them and draws 3 new cards.
- Dan (Knight) rolls 5 and stops on a Wilds I tile: Lost Purse, +2 gold. Dan now has 5 gold, enough to raise STR from 3 to 4 at a Barracks next turn.

## 12. Playtesting

First play a short fight test (2 players, 15 minutes): one player fights a stack of Tier I and Tier II enemies with fresh hands, and the other only interferes. Then play full games.

After each game, each player answers alone, on paper:

1. What was the most exciting moment?
2. What was the most important decision you made?
3. Did you make or refuse a help deal? Why?
4. When did you use your sabotage, and on whom?
5. Was there a moment the rules didn't cover? Write it down.
6. How long did you wait between your turns? Was watching fun?
7. If you could change one thing, what would it be?

For every game, note: total time, table rounds, the winner and their character, the number of help deals, Trial attempts and knockouts, and who reached level 5 first.

## 13. Making the prototype

- 132 cards, text only, about playing-card size (63×88 mm). Print on paper and put each one in a sleeve in front of an old playing card.
- 49 tiles, 5×5 cm, coloured by ring.
- One die, coins, paper HP counters.
- Hand-drawn is fine. No art needed yet.

The card lists in §10 are complete, so the same lists can be used for a Tabletop Simulator version.
