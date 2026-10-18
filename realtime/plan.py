"""The dungeon the tutorial builds (shared by tts/build.py and tutorial.py).

Cells are (x, z) in rooms from the start room; +z is north (up on screen). ROOMS is the order the
rooms come off the stack, with the token put on each one (monster or treasure, None for an empty
room). LINKS are the passages: build.py draws a door on both rooms of a link, so every revealed room
connects to the room it was revealed from (§6: "connecting the passages").

The final score is planned so the video can show the tiebreaker of §11: Anastasya (Yellow) and Amira
(Green) both end on 8 points, and Anastasya wins with more monsters defeated (2 against 1).
"""
ROOMS = [
    # practice part of the tutorial (top of the stack first)
    ((0, -1), "empty", None),               # Bora reveals
    ((0, -2), "monster", "m-weak-1"),       # Bora: weak monster, needs a reroll
    ((-1, -2), "treasure", "t-common-2"),   # Bora: treasure
    ((-1, 0), "monster", "m-medium-1"),     # Anastasya: medium monster (the document's example roll)
    ((1, 0), "monster", "m-strong-1"),      # Esma: strong monster, gives up
    ((0, 1), "treasure", "t-special-1"),    # Amira: special treasure, Loot card
    ((0, 2), "monster", "m-weak-2"),        # Amira: weak monster beaten with the Iron Sword
    # only in the real game after the reset
    ((2, 0), "treasure", "t-common-1"),
    ((-2, 0), "treasure", "t-rare-1"),
    ((2, 1), "monster", "m-weak-3"),
    ((-1, 2), "treasure", "t-rare-3"),
    ((-2, 1), "monster", "m-medium-2"),
    ((-2, -2), "monster", "m-medium-3"),
    ((1, 2), "treasure", "t-rare-2"),
    ((-2, -1), "treasure", "t-common-3"),
]

LINKS = [
    ((0, 0), (0, -1)), ((0, 0), (-1, 0)), ((0, 0), (0, 1)), ((0, 0), (1, 0)),
    ((1, 0), (2, 0)), ((0, -1), (0, -2)), ((0, 1), (0, 2)),
    ((-1, 0), (-2, 0)), ((0, -2), (-1, -2)), ((2, 0), (2, 1)), ((0, 2), (-1, 2)),
    ((-2, 0), (-2, 1)), ((-1, -2), (-2, -2)), ((0, 2), (1, 2)), ((-2, 0), (-2, -1)),
]
