"""The dungeon the tutorial video builds (shared by tts/build.py and tutorial.py).

Cells are (x, z) in rooms from the Safe Zone; +z is north (up on screen). ROOMS is the order the rooms
come off the room deck in the video, with the token put on each one (monster, treasure or special object;
None for an empty room or the Integration Chamber). LINKS are the passages: build.py draws a door on both
rooms of a link, so every revealed room connects to the room it was revealed from.

The story (rules of 2026-11-03, part 2, the video script): Bora opens the first rooms and beats a 3 HP
Anomaly in two cycles; Anastasya finds a Module, an Archive and a Specimen (one of each type); Amira opens
the Integration Chamber. Everyone takes a special object. Bora ends round 1 in the empty room (0,-1). In round 2
rocks fill every Unregistered Sector (the empty rooms) except that one, since he stands in it: (1,0), (-2,-2), (1,2). Esma finds her way home blocked
at (1,0), takes the long way round through (2,-1), (1,-1), (0,-1) and is still in the Integration Chamber at
0:00. Scores: Anastasya 6, Bora 4, Amira 1 escape; Esma is trapped.
"""
ROOMS = [
    # scenes 3-8, one player at a time (top of the deck first)
    ((0, -1), "empty", None),               # Bora: the first new room, then he moves in
    ((0, -2), "monster", "m-strong-1"),     # Bora: an Anomaly, 3 HP (scenes 5-6)
    ((-1, 0), "treasure", "t-module-1"),    # Anastasya: Module (scene 7)
    ((-2, 0), "treasure", "t-archive-1"),   # Anastasya: Archive
    ((-2, -1), "treasure", "t-specimen-1"),  # Anastasya: Specimen
    ((0, 1), "special", None),              # Amira: the Integration Chamber (scene 8)
    # scene 9, everyone at once
    ((1, 0), "empty", None),                # Esma: an Unregistered Sector, rocked in round 2
    ((-1, -2), "treasure", "o-4"),          # Bora: object IV
    # v2.5: the deck has 7 treasure rooms now, so (1,1) and (2,1) are monster rooms: the 19 rooms of this plan are
    # the whole deck. Their object tokens stay for tutorial.py, which is already behind the rules (Rockfall).
    ((1, 1), "monster", "o-2"),             # Amira: object II
    ((-2, 1), "monster", "m-medium-1"),     # Anastasya: Carrier
    ((2, 0), "treasure", "t-module-2"),     # Esma: Module
    ((-1, -1), "treasure", "t-archive-2"),  # Bora: Archive
    ((0, 2), "monster", "m-weak-2"),        # Amira: Scraper
    ((2, 1), "monster", "o-1"),             # Esma: object I
    ((-1, 1), "treasure", "o-3"),           # Anastasya: object III
    ((2, -1), "monster", "m-weak-1"),       # Esma: Scraper, then her long way home goes through here...
    ((1, -1), "monster", "m-weak-3"),       # ...and past a Scraper nobody fights
    ((-2, -2), "empty", None),              # Anastasya: Unregistered Sector (rocked in round 2)
    ((1, 2), "empty", None),                # Amira: Unregistered Sector (rocked in round 2)
]

LINKS = [
    ((0, 0), (0, -1)), ((0, -1), (0, -2)), ((0, 0), (-1, 0)), ((-1, 0), (-2, 0)), ((-2, 0), (-2, -1)),
    ((0, 0), (0, 1)), ((0, 0), (1, 0)), ((0, -2), (-1, -2)), ((0, 1), (1, 1)), ((-2, 0), (-2, 1)),
    ((1, 0), (2, 0)), ((-1, -2), (-1, -1)), ((-1, -1), (-1, 0)), ((0, 1), (0, 2)), ((2, 0), (2, 1)),
    ((-1, 0), (-1, 1)), ((2, 0), (2, -1)), ((2, -1), (1, -1)), ((1, -1), (0, -1)), ((-2, -1), (-2, -2)),
    ((1, 1), (1, 2)),
]
