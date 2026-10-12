"""Kingbound card, tile and character data: the single source for build.py and the bots.

Every number and every card text is copied word for word from Kingbound-GDD.md (§2, §3, §10).
If the GDD changes, change it here, run build.py again and the counts below are checked again.
The GDD gives no IDs to characters, abilities and the Champion; the ones used here (C1-C5,
KN1..RA3, CH) are only for the prototype.
"""

# ------------------------------------------------------------------ §10.1 Action deck (45)
# (ID, name, type, cost, copies, text, effect for the bots)
ACTION = [
    ("ST1", "Strike", "STR", 1, 5, "Deal 2 + STR damage.", dict(dmg=2)),
    ("ST2", "Heavy Blow", "STR", 2, 3, "Deal 5 + STR damage.", dict(dmg=5)),
    ("ST3", "Brace", "STR", 1, 3, "Gain 3 + STR Block.", dict(block=3)),
    ("ST4", "Shield Bash", "STR", 1, 2, "Deal 1 + STR damage. Gain 2 Block.", dict(dmg=1, fblock=2)),
    ("ST5", "War Cry", "STR", 0, 2, "This round, each other STR card you play deals 2 more damage.", dict(warcry=2)),
    ("AG1", "Slash", "AGI", 1, 5, "Deal 2 + AGI damage.", dict(dmg=2)),
    ("AG2", "Ambush", "AGI", 2, 3, "Deal 4 + AGI damage. In round 1, deal 3 more.", dict(dmg=4, r1=3)),
    ("AG3", "Dodge", "AGI", 1, 3, "Gain 3 + AGI Block.", dict(block=3)),
    ("AG4", "Quick Stab", "AGI", 0, 2, "Deal 1 + AGI damage.", dict(dmg=1)),
    ("AG5", "Vanish", "AGI", 0, 2, "Flee now, no roll. Not while Snared.", dict(vanish=True)),
    ("WI1", "Spark", "WIS", 1, 5, "Deal 2 + WIS damage.", dict(dmg=2)),
    ("WI2", "Firebolt", "WIS", 2, 3, "Deal 5 + WIS damage.", dict(dmg=5)),
    ("WI3", "Ward", "WIS", 1, 3, "Gain 3 + WIS Block.", dict(block=3)),
    ("WI4", "Mend", "WIS", 1, 2, "Heal 2 + WIS HP.", dict(heal=2)),
    ("WI5", "Focus", "WIS", 0, 2, "Gain 2 energy this round.", dict(energy=2)),
]

# ------------------------------------------------------------------ §10.2 Enemies (28)
# (ID, name, copies, HP, ATK, gold, loot, trait text, trait key for the bots)
ENEMIES = {
    1: [("E11", "Giant Rat", 2, 4, 2, 1, False, "", None),
        ("E12", "Wolf", 2, 5, 3, 1, False, "", None),
        ("E13", "Goblin", 2, 6, 2, 2, False, "If you flee, lose 1 gold.", "flee_gold1"),
        ("E14", "Bandit", 2, 7, 3, 2, False, "", None),
        ("E15", "Wild Boar", 2, 8, 3, 1, False, "Charge: deals 2 more damage in round 1.", "charge")],
    2: [("E21", "Harpy", 2, 11, 5, 2, False, "", None),
        ("E22", "Dire Wolf", 2, 12, 5, 2, True, "", None),
        ("E23", "Orc Raider", 2, 13, 4, 3, False, "", None),
        ("E24", "Highwayman", 2, 14, 4, 3, False, "If you flee, lose 2 gold.", "flee_gold2"),
        ("E25", "Troll", 2, 15, 4, 3, False, "At the end of each round, remove 2 damage from it.", "regen")],
    3: [("E31", "Wraith", 2, 17, 6, 3, True, "Each STR and AGI card deals 1 less damage to it.", "ethereal"),
        ("E32", "Wyvern", 2, 18, 7, 4, True, "", None),
        ("E33", "Ogre", 2, 20, 6, 4, False, "", None),
        ("E34", "Dark Knight", 2, 22, 6, 5, True, "Armor: the first damage card you play each round deals 2 less.", "armor")],
}
LEVELS_FOR_TIER = {1: 1, 2: 2, 3: 3}  # §6.5

# The King's Champion (§8, §10.2): 1 card, next to the Castle.
CHAMPION = dict(id="CH", name="King's Champion", hp=20, atk=5, cap=10,
                text="Takes at most 10 damage per round.")

# ------------------------------------------------------------------ §10.3 Wilds events (10)
# (ID, tier, name, text)
EVENTS = [
    ("V11", 1, "Lost Purse", "Gain 2 gold."),
    ("V12", 1, "Old Veteran", "You may pay 2 gold to raise any stat by 1 (max 5)."),
    ("V13", 1, "Pit Trap", "Roll the die. On 1-3, lose 2 HP. This can't take you below 1 HP."),
    ("V14", 1, "Wandering Trader", "Visit the Merchant here (§5.3)."),
    ("V21", 2, "Hidden Cache", "Draw 1 Loot card for free."),
    ("V22", 2, "Ambush!", "Draw the next Wilds II card. If it is an enemy, it attacks you once before round 1 "
                          "(your Guard roll and item Block count), then fight it as normal. If it is an event, "
                          "resolve that instead."),
    ("V23", 2, "Healing Spring", "Heal to full HP."),
    ("V24", 2, "Mercenary Captain", "You may pay 4 gold to gain 1 level (not above 9)."),
    ("V31", 3, "Dragon Hoard", "Gain 4 gold. Then draw the next Wilds III card and resolve it."),
    ("V32", 3, "Ancient Shrine", "Choose one: raise any stat by 1 (max 5), or heal to full and ready all your Abilities."),
]

# ------------------------------------------------------------------ §10.4 Loot (20)
# (ID, name, price, copies, text, equipment?)
LOOT = [
    ("L01", "Iron Sword", 4, 1, "Your STR cards deal 1 more damage.", True),
    ("L02", "Hunting Bow", 4, 1, "Your AGI cards deal 1 more damage.", True),
    ("L03", "Oak Wand", 4, 1, "Your WIS cards deal 1 more damage.", True),
    ("L04", "Chain Mail", 4, 1, "Gain 1 Block every fight round.", True),
    ("L05", "Tower Shield", 6, 1, "Gain 2 Block every fight round.", True),
    ("L06", "Amulet of Vigor", 3, 1, "Max HP +3.", True),
    ("L07", "Backpack", 4, 1, "Hand size +1.", True),
    ("L08", "Lucky Charm", 3, 1, "+1 to your Guard and Flee rolls.", True),
    ("L09", "Swift Boots", 2, 1, "+1 to your movement roll.", True),
    ("L10", "Training Manual", 4, 2, "Raise any stat by 1 (max 5).", False),
    ("L11", "Healing Potion", 2, 3, "Heal 5 HP. Any time, even in another player's turn, but not once you are at 0 HP.", False),
    ("L12", "Bomb", 2, 2, "In any fight: deal 5 damage to the enemy.", False),
    ("L13", "Smoke Bomb", 1, 1, "In your fight: flee, no roll. Not while Snared.", False),
    ("L14", "Cursed Totem", 2, 2, "In another player's fight: the enemy deals 3 more damage this round.", False),
    ("L15", "Elixir", 3, 1, "Draw Action cards up to your hand size.", False),
]
EQUIPMENT_LIMIT = 3  # §7

# ------------------------------------------------------------------ §10.5 Characters (5) and Abilities (15)
# (ID, name, STR, AGI, WIS, HP, energy, hand, how it plays)
CHARACTERS = [
    ("C1", "Knight", 3, 0, 1, 13, 3, 5, "Steady hitter; a good helper to hire"),
    ("C2", "Rogue", 1, 3, 0, 8, 4, 5, "Fast, uses up cards quickly, steals gold"),
    ("C3", "Mage", 0, 1, 3, 10, 3, 5, "Big damage, fragile"),
    ("C4", "Cleric", 2, 0, 3, 12, 3, 5, "Two good stats, can draw extra cards"),
    ("C5", "Ranger", 1, 2, 1, 13, 3, 6, "Spread-out stats, bigger hand, moves far"),
]
# (ID, character, name, kind, when, text): kind is boost / sabotage / signature (§6.7, §10.5).
ABILITIES = [
    ("KN1", "Knight", "Cleave", "boost", "Any fight.", "Deal 3 damage to the enemy."),
    ("KN2", "Knight", "Provoke", "sabotage", "Another player's fight only.", "The enemy deals 3 more damage this round."),
    ("KN3", "Knight", "Shield Wall", "signature", "Any fight.", "The fighter gains 5 Block this round."),
    ("RO1", "Rogue", "Backstab", "boost", "Any fight.", "Deal 4 damage to the enemy."),
    ("RO2", "Rogue", "Trip", "sabotage", "Another player's fight only.", "The fighter's Block this round becomes 0 (cards and items)."),
    ("RO3", "Rogue", "Pickpocket", "signature", "Your turn.", "Take 2 gold from a player on your tile or a tile next to you."),
    ("MA1", "Mage", "Fireball", "boost", "Any fight.", "Deal 5 damage to the enemy."),
    ("MA2", "Mage", "Hex", "sabotage", "Another player's fight only.", "Remove 4 damage from the enemy."),
    ("MA3", "Mage", "Arcane Surge", "signature", "Your fight.", "Gain 2 energy this round."),
    ("CL1", "Cleric", "Holy Light", "boost", "Any fight.", "Deal 4 damage to the enemy; the fighter heals 2 HP."),
    ("CL2", "Cleric", "Penance", "sabotage", "Another player's fight only.", "The fighter loses 2 HP."),
    ("CL3", "Cleric", "Prayer", "signature", "Your turn or your fight.", "Draw 2 Action cards."),
    ("RA1", "Ranger", "Volley", "boost", "Any fight.", "Deal 3 damage to the enemy; the fighter gains 2 Block."),
    ("RA2", "Ranger", "Snare", "sabotage", "Another player's fight only.", "The fighter can't flee for the rest of this fight."),
    ("RA3", "Ranger", "Pathfinder", "signature", "After your movement roll.", "Add 3 to it."),
]

# ------------------------------------------------------------------ §10.6 Hidden objectives (8)
OBJECTIVES = [
    ("O1", "Giant Slayer", "Defeat a Tier III enemy."),
    ("O2", "Monster Hunter", "Defeat 3 Tier II enemies."),
    ("O3", "Drillmaster", "Have any stat at 5."),
    ("O4", "Well Equipped", "Hold 3 equipment items at the same time."),
    ("O5", "Hoarder", "Hold 10 gold at the same time."),
    ("O6", "Sellsword", "Get paid for helping in 2 fights."),
    ("O7", "Spoiler", "Twice, use a sabotage Ability or item in a fight that the fighter then loses (flees or is knocked out)."),
    ("O8", "Close Call", "Win a fight in which your HP dropped to 3 or less."),
]
OBJECTIVE_REWARD = "Show the card and gain 2 levels (not above 9)."

# ------------------------------------------------------------------ §2, §3 tiles (49)
# Ring of a square on the 7x7 grid: 0 = Castle, 1 = inner, 2 = middle, 3 = outer.
def ring_of(r, c):
    return max(abs(r - 3), abs(c - 3))


CASTLE = (3, 3)
CAMPS = [(2, 3), (3, 4), (4, 3), (3, 2)]          # north, east, south, west of the Castle (§3 step 1)
INNER_CORNERS = [(2, 2), (2, 4), (4, 4), (4, 2)]  # Wilds I (§3 step 2)
# Tiles shuffled within their own ring (§3 steps 3-4). Tile kinds: Wilds1..3, Merchant, Barracks, Healer.
MIDDLE_TILES = ["Merchant"] * 2 + ["Barracks"] * 2 + ["Healer"] * 2 + ["Wilds2"] * 10
OUTER_TILES = ["Merchant", "Barracks", "Healer"] + ["Wilds3"] * 21
TILE_COUNTS = {"Castle": 1, "Camp": 4, "Merchant": 3, "Barracks": 3, "Healer": 3,
               "Wilds1": 4, "Wilds2": 10, "Wilds3": 21}


def ring_squares(ring):
    return [(r, c) for r in range(7) for c in range(7) if ring_of(r, c) == ring]


def make_board(rng):
    """§3: Castle and Camps fixed, Wilds I on the inner corners, middle and outer rings shuffled."""
    board = {CASTLE: "Castle"}
    for p in CAMPS:
        board[p] = "Camp"
    for p in INNER_CORNERS:
        board[p] = "Wilds1"
    for ring, tiles in ((2, MIDDLE_TILES), (3, OUTER_TILES)):
        tiles = list(tiles)
        rng.shuffle(tiles)
        for p, t in zip(ring_squares(ring), tiles):
            board[p] = t
    return board


# ------------------------------------------------------------------ count checks (§2: 132 cards, 49 tiles)
N_ACTION = sum(c[4] for c in ACTION)
N_WILDS = {t: sum(e[2] for e in ENEMIES[t]) + sum(1 for e in EVENTS if e[1] == t) for t in (1, 2, 3)}
N_LOOT = sum(c[3] for c in LOOT)
COUNTS = {"Action": N_ACTION, "Wilds I": N_WILDS[1], "Wilds II": N_WILDS[2], "Wilds III": N_WILDS[3],
          "Champion": 1, "Loot": N_LOOT, "Objective": len(OBJECTIVES), "Character": len(CHARACTERS),
          "Ability": len(ABILITIES)}
assert COUNTS == {"Action": 45, "Wilds I": 14, "Wilds II": 14, "Wilds III": 10, "Champion": 1,
                  "Loot": 20, "Objective": 8, "Character": 5, "Ability": 15}, COUNTS
assert sum(COUNTS.values()) == 132
assert all(sum(c[4] for c in ACTION if c[2] == t) == 15 for t in ("STR", "AGI", "WIS"))  # §2: 15 per type
assert sum(e[2] for e in ENEMIES[1] + ENEMIES[2] + ENEMIES[3]) == 28
assert len(EVENTS) == 10
assert sum(1 for c in LOOT if c[5]) == 9
assert all(sum(1 for a in ABILITIES if a[1] == ch[1]) == 3 for ch in CHARACTERS)
assert sum(TILE_COUNTS.values()) == 49
assert len(ring_squares(1)) == 8 and len(ring_squares(2)) == len(MIDDLE_TILES) == 16
assert len(ring_squares(3)) == len(OUTER_TILES) == 24

# ------------------------------------------------------------------ lookups for the bots
ACTION_BY_NAME = {c[1]: c for c in ACTION}
LOOT_BY_NAME = {c[1]: c for c in LOOT}
EQUIPMENT = {c[1] for c in LOOT if c[5]}
PRICE = {c[1]: c[2] for c in LOOT}
CHAR_BY_NAME = {c[1]: c for c in CHARACTERS}
ABILITIES_OF = {ch[1]: [a for a in ABILITIES if a[1] == ch[1]] for ch in CHARACTERS}
OBJECTIVE_BY_ID = {o[0]: o for o in OBJECTIVES}
