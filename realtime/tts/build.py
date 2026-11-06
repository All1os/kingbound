"""Builds the Tabletop Simulator save for the real-time game, now called NULLWAKE (was Kingbound).

Rules: the team's "Game rules and gameplay video script" of 2026-11-03 (vault: kingbound/realtime/
kaynak-NULLWAKE-rules-2026-11-03.pdf), and from v2.2 the GDD of 2026-11-04 (vault: kaynak-NULLWAKE-GDD-2026-11-04.pdf):
the same rules word for word plus seven more event cards for round 2 ("According to last presentation"), and from
v2.3 the GDD of 2026-11-05 (vault: kaynak-NULLWAKE-GDD-2026-11-05.pdf, its last part "Changes after a series of
playtests before the Game Jam": no Rockfall, no Poison Gas, no treasure combinations, Lost Path swaps the Safe Zone
and the Integration Chamber, Time Freeze becomes an initiative roll). Names and look: Nastya's narrative document NULLWAKE (vault:
kaynak-NULLWAKE-narrative.docx). Yavuz, 2026-11-03: "gdd ve narrative ne diyosa o".
Where the rules document contradicts itself, Yavuz decided: moving one room and opening a room cost 2
Movement and treasure 2 Magic, "like the old game" (v2.0); the dice keep three symbols (no "special"
face). Where it leaves a detail open, the simplest value, marked "(open)". Where the narrative document
disagrees with the rules (its THE NULL event is marked "DEMO?? Concept"; it says treasures alone give no
points), the rules document wins: it is the newer one and names Nastya's document only for the story.
The rules for players are in ../../README.md.
Images are drawn with Pillow and copied into TTS's Mods/ folder (macOS doesn't let TTS read
~/Desktop); their names carry a content hash so TTS never shows a stale cached image.
Run: python3 build.py
"""
import hashlib, json, math, os, random, shutil, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

VERSION = "2.4"   # v1.0 (Yavuz, 2026-10-26: "oyun tamamlandı"), v1.1: each mat on its own side of the table,
                  # v1.2: a seat (hand zone) at every mat for online games, and ROLL DICE,
                  # v2.0: the GDD of 2026-11-02 (two rounds, events, treasure sets, special objects; no Loot, no traps)
                  # v2.1: NULLWAKE, the rules of 2026-11-03 and the narrative document (names, sci-fi look)
                  # v2.2: the GDD of 2026-11-04, eight event cards (Rockfall and seven new ones)
                  # v2.3: the GDD of 2026-11-05, six event cards, treasure without combinations
                  # v2.4: 2 to 4 players, the Integration Chamber in the top 5 rooms (balance test, 2026-11-06)
ROOT = Path(__file__).parent
OUT = ROOT / "output"
ASSETS = Path.home() / "Library/Tabletop Simulator/Mods/kingbound-realtime"
SAVES = Path.home() / "Library/Tabletop Simulator/Saves/prototipler"
SAVE_NAME = "NULLWAKE"
DICE_TEMPLATE = Path.home() / "Library/Application Support/Steam/steamapps/common/Tabletop Simulator/Modding/Dice Templates/D6.png"
for p in (OUT, ASSETS, SAVES):
    p.mkdir(parents=True, exist_ok=True)

FONT = "/System/Library/Fonts/Supplemental/"
def f(name, size): return ImageFont.truetype(FONT + name, size)
# Narrative §5 "industrial sci-fi": DIN, the lettering of signs and machines, for names; Arial for text.
BLACK, BOLD, REG, COND = "DIN Alternate Bold.ttf", "Arial Bold.ttf", "Arial.ttf", "DIN Condensed Bold.ttf"

# Narrative §5: "graphite, steel grey, cold blue, and off-white", cold lighting and "localized emergency
# light sources". PAPER is the off-white of a panel, INK graphite, GOLD (the old name, kept so every
# drawing reads the same) the cold blue light, EMERG the emergency amber of round 2.
PAPER, INK, CREAM, GOLD = (222, 227, 230), (24, 28, 34), (236, 240, 242), (92, 176, 222)
GRAPHITE, STEEL, EMERG = (40, 45, 52), (120, 130, 140), (226, 140, 36)
# The three symbols (rules §2.1). Each has its own colour so they read from far away on video.
SYM_COL = {"move": (36, 140, 104), "attack": (190, 52, 44), "magic": (66, 104, 200)}
SYM_NAME = {"move": "MOVEMENT", "attack": "ATTACK", "magic": "MAGIC"}
WALL, FLOOR, PLATE = (30, 34, 40), (108, 117, 126), (90, 98, 108)
SAFE_COL, OBJ_COL, EVENT_COL = (28, 70, 104), (40, 150, 160), (150, 70, 20)
# 2-4 players (Yavuz, 2026-11-06: "oyun 2 ila 4 kişilik"): four seats, one on each side of the table; Purple,
# v1.1's fifth seat beside Red, is gone. The mats show only the seat colour: the team members' names came off when the
# save went on the Steam Workshop (Yavuz, 2026-10-25: "kartlardan isimleri kaldır").
COLORS = ["Red", "Yellow", "Green", "Blue"]
RGB = {"Red": (0.856, 0.1, 0.094), "Yellow": (0.905, 0.898, 0.172), "Green": (0.192, 0.701, 0.168),
       "Blue": (0.118, 0.53, 1.0), "Purple": (0.627, 0.125, 0.941)}
PIX = {"Red": (200, 60, 52), "Yellow": (214, 190, 40), "Green": (64, 160, 60), "Blue": (52, 120, 210), "Purple": (140, 64, 196)}

# ------------------------------------------------------------------ game content
# Dice: 4 (rules §2.3's example), three symbols, two faces of each.
DIE_FACES = {1: "move", 2: "move", 3: "attack", 4: "attack", 5: "magic", 6: "magic"}
# Monsters (rules §5, names narrative §2): HP 1 / 2 / 3, reward 1 / 2 / 3 points. Each Attack deals 1
# damage and damage stays from one cycle to the next (video script, scene 6: a 3 HP monster takes 2, then
# 1 in the next cycle). Counts from v2.0.
MONSTERS = {"weak": ("Scraper", 1, 1, 4), "medium": ("Carrier", 2, 2, 3), "strong": ("Anomaly", 3, 3, 2)}  # name, HP, points, count
# Treasures (rules §6, names narrative §3): the rules' gold, silver and bronze, renamed in the narrative's
# order (open): Modules, Archives, Specimens. Taken with 2 Magic like v2.0. Three of each, as v2.0.
TREASURES = {"module": ("Module", 3), "archive": ("Archive", 3), "specimen": ("Specimen", 3)}   # name, count
# v2.3: no combinations (GDD 11-05; Yavuz, 2026-11-06: "trasure combınations artık yok"). Each treasure counts
# alone. The rules give a gold 3 points (§6.1 "1 gold 3") and say leftover treasure has its own value but not
# which (open): silver 2 and bronze 1, the same 3 / 2 / 1 steps as the monsters.
SINGLE = {"module": 3, "archive": 2, "specimen": 1}
# Special objects (rules §7, narrative §4): one tile, the Integration Chamber, with four slots. Objects are
# found while exploring (narrative) in the treasure tokens, taken with 2 Magic like v2.0, and placed only in
# round 2 (rules §7). The special task (rules §9, Amira: "this special tile = special task"): placing an
# object completes it for the player who places it (open). No points for it: the rules give none.
OBJECTS = ["I", "II", "III", "IV"]
# Room cards (narrative §4: safe zone, empty, monster, treasure, special objects): v2.0's counts.
ROOM_COUNT = {"empty": 6, "monster": 7, "treasure": 9, "special": 1}
ROOM_NAME = {"safe": "Safe Zone", "empty": "Unregistered Sector", "monster": "Infested Sector",
             "treasure": "Recovery Storage", "special": "Integration Chamber"}
# Rounds (rules §8, §9): 5 minutes each. Escaping (rules §9, §11): at 0:00 a player keeps their points if
# they are in the Safe Zone and have completed the special task; everyone else loses all their points (open:
# the rules say "the points earned in the first round" and "uncredited points").
GAME_SECS, ROUND2_AT = 600, 300
# Events: GDD 11-04 adds seven cards to Rockfall (Yavuz, 2026-11-04: "ekle"). Players turn up the card and set out its tokens by hand
# (Yavuz, 2026-11-04: "eventleri biz yerleştirelim kendi koymasın"); the script only reads the tokens on the table.
# Where the GDD leaves a detail open, the simplest value, marked (open) in global.lua beside the effect.
# "Time Freeze" is the GDD's only Time Event card and "Extra Risk" its only EXIT Challenge card: the headings
# are groups, the cards are what goes in the deck.
# GDD 11-05 ("Changes after a series of playtests"): Rockfall and Poison Gas are gone (rocks made dead ends; gas
# "removing ... from the game"), so E1 and E6 are no more; the other cards keep their IDs. Lost Path: "the map works
# provided that we swap the Safe Zone and the tile of special objects". Time Freeze: redesigned as the initiative
# mini-game; (open) it lasts one cycle, the GDD doesn't say how long. Its "1 identical symbol" can only come up for
# a player rolling 3 dice (last one done): 4 dice with three symbols always show a pair.
EVENTS = [("E2", "Lost Path", "The Safe Zone and the Integration Chamber swap places.",
           "Swap the two tiles now. Escape to the Safe Zone where it lies now; objects go on the chamber."),
          ("E3", "Time Freeze", "Time stops: this cycle you play one at a time.",
           "Everyone rolls at once. Most identical symbols goes first (4, then 3, 2, 1); the others wait. "
           "Same number: the lowest score goes first."),
          ("E4", "Extra Risk", "You may draw one or two more event cards.",
           "Draw them now. Every card drawn happens."),
          ("E5", "Extra Special Tile", "A second Integration Chamber joins the station.",
           "It has four slots too. An object placed on either chamber completes your special task."),
          ("E7", "Aliens", "Aliens take the place of every monster.",
           "1 HP more than the monster they replace, same points. You can't go through their room without beating them."),
          ("E8", "Black Holes", "Black holes open in every room with treasure.",
           "Each time you go through one, you lose 1 point. You can still enter and take the treasure.")]
# Tokens for the new events, each kind with one spare (taking a deck's last card stops the script).
HOLE_COUNT = ROOM_COUNT["treasure"] + 1
ALIEN_COL = (96, 168, 72)  # (open) the GDD gives aliens no colour: a sickly green, apart from the monsters' red
HOLE_COL = (60, 40, 96)

# ------------------------------------------------------------------ drawing helpers
def wrap(d, text, font, width):
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= width: cur = t
        else: out.append(cur); cur = w
    out.append(cur)
    return out


def para(d, text, top, x0, x1, name=REG, size=30, fill=INK, gap=8):
    font = f(name, size)
    y = top
    for ln in wrap(d, text, font, x1 - x0):
        d.text(((x0 + x1) / 2, y), ln, font=font, fill=fill, anchor="ma")
        y += size + gap
    return y


def fit(d, text, name, size, width):
    """The biggest font, up to size, that fits text in width."""
    while size > 12 and d.textlength(text, font=f(name, size)) > width:
        size -= 2
    return f(name, size)


def star(d, cx, cy, r, fill, outline=None):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill, outline=outline)


def sword(d, cx, cy, r, fill, angle=0.0):
    """A sword pointing up (angle in radians turns it)."""
    def rot(x, y):
        c, s = math.cos(angle), math.sin(angle)
        return (cx + x * c - y * s, cy + x * s + y * c)
    w = r * 0.16
    blade = [rot(-w, r * 0.35), rot(-w, -r * 0.75), rot(0, -r), rot(w, -r * 0.75), rot(w, r * 0.35)]
    d.polygon(blade, fill=fill)
    guard = [rot(-r * 0.45, r * 0.35), rot(r * 0.45, r * 0.35), rot(r * 0.45, r * 0.5), rot(-r * 0.45, r * 0.5)]
    d.polygon(guard, fill=fill)
    grip = [rot(-w * 0.7, r * 0.5), rot(w * 0.7, r * 0.5), rot(w * 0.7, r * 0.95), rot(-w * 0.7, r * 0.95)]
    d.polygon(grip, fill=fill)


def boot(d, cx, cy, r, fill):
    """Movement: an arrow made of two chevrons (a footstep forward)."""
    for k in (-0.35, 0.25):
        y = cy + k * r
        d.polygon([(cx - r * 0.75, y + r * 0.35), (cx, y - r * 0.35), (cx + r * 0.75, y + r * 0.35),
                   (cx + r * 0.75, y + r * 0.6), (cx, y - r * 0.1), (cx - r * 0.75, y + r * 0.6)], fill=fill)


def crossed(d, cx, cy, r, fill):
    sword(d, cx, cy, r, fill, math.radians(40))
    sword(d, cx, cy, r, fill, math.radians(-40))


def icon(d, kind, cx, cy, r, fill=CREAM):
    {"move": boot, "attack": crossed, "magic": lambda d_, x, y, rr, c: star(d_, x, y, rr, c)}[kind](d, cx, cy, r, fill)


def sym_row(d, kind, n, cx, cy, r):
    """n round symbol badges in a row, centred on cx."""
    gap = r * 2.3
    x0 = cx - gap * (n - 1) / 2
    for i in range(n):
        x = x0 + i * gap
        d.ellipse((x - r, cy - r, x + r, cy + r), fill=SYM_COL[kind], outline=INK, width=3)
        icon(d, kind, x, cy, r * 0.62)


def safe_mark(d, cx, cy, r, fill, outline=INK):
    """The Safe Zone's sign: a hexagon with a cross, like a station's shelter sign (replaces v2.0's crown)."""
    pts = [(cx + r * math.cos(math.radians(30 + 60 * i)), cy + r * math.sin(math.radians(30 + 60 * i))) for i in range(6)]
    d.polygon(pts, fill=fill, outline=outline, width=max(2, int(r * 0.08)))
    w, l = r * 0.2, r * 0.58
    d.rectangle((cx - w, cy - l, cx + w, cy + l), fill=outline)
    d.rectangle((cx - l, cy - w, cx + l, cy + w), fill=outline)


def chest(d, cx, cy, r):
    """A storage case (Recovery Storage, narrative §4): steel with a cold blue light strip."""
    d.rounded_rectangle((cx - r, cy - r * 0.64, cx + r, cy + r * 0.64), int(r * 0.12), fill=STEEL, outline=INK, width=5)
    d.rectangle((cx - r, cy - r * 0.27, cx + r, cy - r * 0.13), fill=INK)
    d.rectangle((cx - r * 0.5, cy + r * 0.1, cx + r * 0.5, cy + r * 0.22), fill=GOLD)


def claw(d, cx, cy, r, fill):
    """The Infested Sector's mark: three claw scratches."""
    for k in (-0.45, 0.0, 0.45):
        x = cx + k * r
        d.polygon([(x - r * 0.12 - r * 0.25, cy - r * 0.8), (x + r * 0.05 - r * 0.25, cy - r * 0.8),
                   (x + r * 0.16 + r * 0.25, cy + r * 0.8), (x + r * 0.02 + r * 0.25, cy + r * 0.8)], fill=fill)


def hazard(d, box, w=26):
    """Emergency stripes (amber and graphite) inside box."""
    x0, y0, x1, y1 = box
    k = x0 - (y1 - y0)
    while k < x1:
        d.polygon([(k, y1), (k + w, y1), (k + w + (y1 - y0), y0), (k + (y1 - y0), y0)], fill=EMERG)
        k += 2 * w


def save(im, fn):
    im.save(OUT / fn)
    return fn


# ------------------------------------------------------------------ artwork
# The team's drawings (Yavuz, 2026-11-06: "table top da kullanabilecegim görsellere ihtiyacım"), made with
# ChatGPT from the art brief (vault: kingbound/realtime/NULLWAKE-concept-art-for-ChatGPT.md) and saved in art/
# under the brief's number: 01.png ... 34.png. A drawing only replaces the picture: walls, passages, names,
# HP, points and rules are still drawn here, so they stay right whatever the drawing shows. A piece without
# a drawing keeps its drawn look. NULLWAKE_ART points to another folder (to try drawings out).
ART_DIR = Path(os.environ.get("NULLWAKE_ART", ROOT / "art"))
ART_NO = {"room-safe": 1, "room-empty": 2, "room-monster": 3, "room-treasure": 4, "room-special": 5, "room-back": 6,
          "mon-weak": 7, "mon-medium": 8, "mon-strong": 9, "mon-back": 10,
          "alienweak": 11, "alienmedium": 12, "alienstrong": 13, "alien-back": 14,
          "tre-module": 15, "tre-archive": 16, "tre-specimen": 17, "tre-back": 18,
          "obj-i": 19, "obj-ii": 20, "obj-iii": 21, "obj-iv": 22, "obj-back": 23,
          "E2": 24, "E3": 25, "E4": 26, "E5": 27, "E7": 28, "E8": 29, "event-back": 30,
          "hole": 31, "haz-back": 32, "dice": 33, "mat": 34}
ART_USED = []


def art(key, size):
    """The drawing for key, cropped to fill size (w, h) from its middle, or None."""
    n = ART_NO.get(key)
    if n is None:
        return None
    for name in (f"{n:02d}", f"{n}"):
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            path = ART_DIR / (name + ext)
            if path.exists():
                ART_USED.append(key)
                return ImageOps.fit(Image.open(path).convert("RGB"), size, Image.LANCZOS)
    return None


def band(im, box, alpha=190):
    """A dark see-through band, so text reads on any drawing."""
    over = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(over).rounded_rectangle(box, 14, fill=(14, 17, 22, alpha))
    im.paste(Image.alpha_composite(im.convert("RGBA"), over).convert("RGB"))


def round_art(im, pic, inset=14):
    """A drawing inside a token's circle."""
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).ellipse((inset, inset, im.size[0] - inset, im.size[1] - inset), fill=255)
    im.paste(pic.resize(im.size, Image.LANCZOS), (0, 0), mask)


# ------------------------------------------------------------------ dice (TTS D6 template)
# The template (TTS's Modding/Dice Templates/D6.png, 2048 px) has the six faces in the lower two rows:
# 2 4 5 over 1 3 6. We paint each face's square with its symbol and keep the rest of the template.
FACE_BOX = {2: (0, 700, 683, 1345), 4: (683, 700, 1366, 1345), 5: (1366, 700, 2048, 1345),
            1: (0, 1365, 683, 2048), 3: (683, 1365, 1366, 2048), 6: (1366, 1365, 2048, 2048)}


def dice_img():
    im = Image.open(DICE_TEMPLATE).convert("RGB")
    d = ImageDraw.Draw(im)
    for face, (x0, y0, x1, y1) in FACE_BOX.items():
        kind = DIE_FACES[face]
        d.rectangle((x0, y0, x1, y1), fill=SYM_COL[kind])
        d.rectangle((x0 + 30, y0 + 30, x1 - 30, y1 - 30), outline=CREAM, width=14)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        pic = DICE_ART.get(kind)
        if pic:
            im.paste(pic.resize((x1 - x0 - 88, y1 - y0 - 88), Image.LANCZOS), (x0 + 44, y0 + 44))
        else:
            icon(d, kind, cx, cy, 210)
    return save(im, "dice.png")


# Drawing 33 has the three symbols side by side (Movement, Attack, Magic): each third, its middle square.
DICE_ART = {}
_dice = art("dice", (1536, 1024))
if _dice:
    for i, kind in enumerate(("move", "attack", "magic")):
        DICE_ART[kind] = ImageOps.fit(_dice.crop((i * 512, 0, i * 512 + 512, 1024)), (512, 512), Image.LANCZOS)


# ------------------------------------------------------------------ room tiles (§2.1, §12, §13)
TILE_PX = 512
DOOR = {"N": (196, 0, 316, 64), "S": (196, 448, 316, 512), "W": (0, 196, 64, 316), "E": (448, 196, 512, 316)}


OBJ_SLOT_PX = [(150, 182), (362, 182), (150, 384), (362, 384)]   # the four slots, a token's size (1.4 of a 3.6 room)


def room_art(kind, doors, pic):
    """A room with a drawing: the drawing is the floor, then the walls and passages over it (they decide the
    route, so they are always drawn here), and the name on a band at the bottom."""
    im = pic.copy()
    d = ImageDraw.Draw(im)
    for box in ((0, 0, TILE_PX, 40), (0, TILE_PX - 40, TILE_PX, TILE_PX), (0, 0, 40, TILE_PX), (TILE_PX - 40, 0, TILE_PX, TILE_PX)):
        d.rectangle(box, fill=WALL)
    d.rectangle((40, 40, TILE_PX - 41, TILE_PX - 41), outline=INK, width=3)
    for s_ in doors:
        x0, y0, x1, y1 = DOOR[s_]
        im.paste(pic.crop(DOOR[s_]), (x0, y0))
        if s_ in "NS":
            d.line((x0, y0, x0, y1), fill=GOLD, width=5); d.line((x1, y0, x1, y1), fill=GOLD, width=5)
        else:
            d.line((x0, y0, x1, y0), fill=GOLD, width=5); d.line((x0, y1, x1, y1), fill=GOLD, width=5)
    if kind == "special":
        # The four slots stay where the script puts the objects, whatever the drawing shows.
        for cx, cy in OBJ_SLOT_PX:
            d.ellipse((cx - 86, cy - 86, cx + 86, cy + 86), outline=OBJ_COL, width=5)
    name = ROOM_NAME[kind].upper()
    band(im, (70, 404, 442, 452))
    d = ImageDraw.Draw(im)
    d.text((256, 428), name, font=fit(d, name, BLACK, 30, 350), fill=CREAM, anchor="mm")
    return save(im, f"room-{kind}-{''.join(sorted(doors))}.png")


def room_img(kind, doors):
    pic = art(f"room-{kind}", (TILE_PX, TILE_PX))
    if pic:
        return room_art(kind, doors, pic)
    # A station sector: graphite walls, steel floor plates with rivets (narrative §5: "matte metal").
    im = Image.new("RGB", (TILE_PX, TILE_PX), WALL)
    d = ImageDraw.Draw(im)
    d.rectangle((40, 40, 472, 472), fill=FLOOR)
    for x in range(40, 472, 108):
        for y in range(40, 472, 108):
            d.rectangle((x + 3, y + 3, x + 105, y + 105), outline=PLATE, width=3)
            for rx, ry in ((x + 12, y + 12), (x + 96, y + 12), (x + 12, y + 96), (x + 96, y + 96)):
                d.ellipse((rx - 3, ry - 3, rx + 3, ry + 3), fill=PLATE)
    for s_ in doors:   # passages: open floor through the wall to the tile's edge, a light strip at the door
        d.rectangle(DOOR[s_], fill=FLOOR)
        x0, y0, x1, y1 = DOOR[s_]
        if s_ in "NS":
            d.line((x0, y0, x0, y1), fill=GOLD, width=5); d.line((x1, y0, x1, y1), fill=GOLD, width=5)
        else:
            d.line((x0, y0, x1, y0), fill=GOLD, width=5); d.line((x0, y1, x1, y1), fill=GOLD, width=5)
    name = ROOM_NAME[kind].upper()
    if kind == "safe":
        # Narrative §4: the gathering point; rules §9: where you escape to.
        d.rounded_rectangle((92, 112, 420, 400), 18, fill=SAFE_COL, outline=GOLD, width=6)
        safe_mark(d, 256, 192, 60, GOLD, SAFE_COL)
        d.text((256, 296), name, font=fit(d, name, BLACK, 56, 300), fill=CREAM, anchor="mm")
        d.text((256, 352), "start · escape here", font=f(REG, 27), fill=GOLD, anchor="mm")
    elif kind == "monster":
        d.ellipse((136, 128, 376, 368), fill=SYM_COL["attack"], outline=INK, width=6)
        claw(d, 256, 248, 84, CREAM)
        d.text((256, 420), name, font=fit(d, name, BLACK, 42, 420), fill=INK, anchor="mm")
    elif kind == "treasure":
        d.ellipse((136, 128, 376, 368), fill=GOLD, outline=INK, width=6)
        chest(d, 256, 252, 70)
        d.text((256, 420), name, font=fit(d, name, BLACK, 42, 420), fill=INK, anchor="mm")
    elif kind == "special":
        # Rules §7: one tile with four slots, one special object in each.
        d.text((256, 64), name, font=fit(d, name, BLACK, 34, 420), fill=INK, anchor="mm")
        for o, (cx, cy) in zip(OBJECTS, OBJ_SLOT_PX):
            d.ellipse((cx - 86, cy - 86, cx + 86, cy + 86), fill=(196, 222, 226), outline=OBJ_COL, width=8)
            d.text((cx, cy), o, font=f(BLACK, 58), fill=OBJ_COL, anchor="mm")
        d.text((256, 488), "place objects in round 2", font=f(BOLD, 20), fill=CREAM, anchor="mm")
    else:
        d.text((256, 240), "UNREGISTERED", font=f(BLACK, 46), fill=(62, 68, 76), anchor="mm")
        d.text((256, 286), "SECTOR", font=f(BLACK, 46), fill=(62, 68, 76), anchor="mm")
    fn = f"room-{kind}-{''.join(sorted(doors))}.png"
    return save(im, fn)


def room_back():
    pic = art("room-back", (TILE_PX, TILE_PX))
    if pic:
        im = pic
        band(im, (60, 190, 452, 322))
        d = ImageDraw.Draw(im)
        d.text((256, 226), "NULLWAKE", font=f(BLACK, 66), fill=GOLD, anchor="mm")
        d.text((256, 290), "unexplored sector", font=f(REG, 30), fill=CREAM, anchor="mm")
        return save(im, "room-back.png")
    im = Image.new("RGB", (TILE_PX, TILE_PX), GRAPHITE)
    d = ImageDraw.Draw(im)
    d.rectangle((14, 14, 498, 498), outline=GOLD, width=6)
    d.rectangle((30, 30, 482, 482), outline=STEEL, width=2)
    d.text((256, 226), "NULLWAKE", font=f(BLACK, 66), fill=GOLD, anchor="mm")
    d.text((256, 290), "unexplored sector", font=f(REG, 30), fill=CREAM, anchor="mm")
    return save(im, "room-back.png")


# ------------------------------------------------------------------ monster and treasure tokens
TOK = 360


def token_front(fn, ring, title, need_kind, need_n, lines, title_col=None):
    """A round token: name, the symbols it needs, and one or two lines under them."""
    im = Image.new("RGB", (TOK, TOK), ring)
    pic = art(fn[:-4], (TOK, TOK))
    if pic:
        # The drawing fills the circle; the name on a band at the top, the cost and the value at the bottom.
        round_art(im, pic)
        band(im, (60, 46, TOK - 60, 104))
        band(im, (54, 236, TOK - 54, 318))
        d = ImageDraw.Draw(im)
        d.ellipse((14, 14, TOK - 14, TOK - 14), outline=INK, width=5)
        d.text((TOK / 2, 75), title, font=fit(d, title, BLACK, 40, 220), fill=CREAM, anchor="mm")
        sym_row(d, need_kind, need_n, TOK / 2, 260, 20 if need_n <= 3 else 17)
        line = " · ".join(lines)
        d.text((TOK / 2, 298), line, font=fit(d, line, BOLD, 28, 230), fill=CREAM, anchor="mm")
        return save(im, fn)
    d = ImageDraw.Draw(im)
    d.ellipse((14, 14, TOK - 14, TOK - 14), fill=PAPER, outline=INK, width=5)
    d.text((TOK / 2, 76), title, font=fit(d, title, BLACK, 44, 220), fill=title_col or ring, anchor="mm")   # the circle is narrow at the top
    sym_row(d, need_kind, need_n, TOK / 2, 156, 30 if need_n <= 3 else 26)
    for i, t in enumerate(lines):
        d.text((TOK / 2, 236 + i * 44), t, font=fit(d, t, BOLD, 38, 250 - i * 40), fill=INK, anchor="mm")
    return save(im, fn)


def token_back(fn, ring, text):
    im = Image.new("RGB", (TOK, TOK), ring)
    pic = art(fn[:-4], (TOK, TOK))
    if pic:
        round_art(im, pic)
        band(im, (40, TOK / 2 - 34, TOK - 40, TOK / 2 + 34))
        d = ImageDraw.Draw(im)
        d.ellipse((14, 14, TOK - 14, TOK - 14), outline=CREAM, width=6)
        d.text((TOK / 2, TOK / 2), text, font=fit(d, text, BLACK, 50, 260), fill=CREAM, anchor="mm")
        return save(im, fn)
    d = ImageDraw.Draw(im)
    d.ellipse((14, 14, TOK - 14, TOK - 14), outline=CREAM, width=6)
    d.text((TOK / 2, TOK / 2), text, font=fit(d, text, BLACK, 50, 280), fill=CREAM, anchor="mm")
    return save(im, fn)


# ------------------------------------------------------------------ event cards (rules §10)
CW, CH = 400, 560
EVENT_COLS = 2   # a sheet has at least two cells: the second one stays empty


def black_hole(d, cx, cy, r):
    for k, col in ((1.0, (120, 96, 170)), (0.72, HOLE_COL), (0.45, (20, 14, 34))):
        d.ellipse((cx - k * r, cy - k * r, cx + k * r, cy + k * r), fill=col, outline=INK, width=2)


def alien_head(d, cx, cy, r):
    d.ellipse((cx - r * 0.7, cy - r * 0.9, cx + r * 0.7, cy + r * 0.8), fill=ALIEN_COL, outline=INK, width=4)
    for sx in (-1, 1):
        d.ellipse((cx + sx * r * 0.32 - r * 0.2, cy - r * 0.2, cx + sx * r * 0.32 + r * 0.2, cy + r * 0.12), fill=INK)


def event_icon(d, eid, cx, cy, r):
    if eid == "E2":
        # The Safe Zone and the chamber with a two-way arrow between them: they swap places (v2.3).
        safe_mark(d, cx - r * 1.05, cy, r * 0.55, GOLD, SAFE_COL)
        s = r * 0.5
        d.rectangle((cx + r * 1.05 - s, cy - s, cx + r * 1.05 + s, cy + s), fill=FLOOR, outline=INK, width=3)
        for sx in (-1, 1):
            for sy in (-1, 1):
                x, y = cx + r * 1.05 + sx * s * 0.45, cy + sy * s * 0.45
                d.ellipse((x - s * 0.3, y - s * 0.3, x + s * 0.3, y + s * 0.3), fill=(196, 222, 226), outline=OBJ_COL, width=2)
        a, h = r * 0.4, 14
        d.rectangle((cx - a, cy - 5, cx + a, cy + 5), fill=EVENT_COL)
        d.polygon([(cx - a - h, cy), (cx - a + 4, cy - h), (cx - a + 4, cy + h)], fill=EVENT_COL)
        d.polygon([(cx + a + h, cy), (cx + a - 4, cy - h), (cx + a - 4, cy + h)], fill=EVENT_COL)
    elif eid == "E3":
        # A stopped clock over the turn order (v2.3: an initiative roll instead of 15 seconds).
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=CREAM, outline=GOLD, width=8)
        d.line((cx, cy, cx, cy - r * 0.7), fill=INK, width=8); d.line((cx, cy, cx + r * 0.5, cy), fill=INK, width=8)
        d.text((cx, cy + r * 0.45), "1 2 3", font=f(BLACK, 22), fill=INK, anchor="mm")
    elif eid == "E4":
        d.text((cx, cy), "+1 +2", font=f(BLACK, 70), fill=EVENT_COL, anchor="mm")
    elif eid == "E5":
        d.rectangle((cx - r, cy - r, cx + r, cy + r), fill=FLOOR, outline=INK, width=4)
        for sx in (-1, 1):
            for sy in (-1, 1):
                x, y = cx + sx * r * 0.45, cy + sy * r * 0.45
                d.ellipse((x - r * 0.3, y - r * 0.3, x + r * 0.3, y + r * 0.3), fill=(196, 222, 226), outline=OBJ_COL, width=4)
    elif eid == "E7": alien_head(d, cx, cy, r)
    elif eid == "E8": black_hole(d, cx, cy, r)


def event_face(eid, name, what, rule, size=27):
    # The text shrinks until the rule fits on the card (Rockfall's last line was cut off since v2.1, seen 2026-11-04).
    pic = art(eid, (CW, CH))
    if pic:
        return event_art(pic, name, what, rule, size)
    im = Image.new("RGB", (CW, CH), PAPER)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, CW - 1, CH - 1), outline=EVENT_COL, width=12)
    d.rectangle((0, 0, CW, 70), fill=GRAPHITE)
    hazard(d, (0, 62, CW, 74), 18)
    d.text((CW / 2, 32), "EVENT | ROUND 2", font=f(BLACK, 30), fill=EMERG, anchor="mm")
    y = para(d, name.upper(), 104, 30, CW - 30, name=BLACK, size=46, gap=6)
    event_icon(d, eid, CW / 2, y + 70, 64)
    y = para(d, what, y + 150, 34, CW - 34, size=size, gap=6)
    d.line((50, y + 14, CW - 50, y + 14), fill=EVENT_COL, width=3)
    end = para(d, rule, y + 34, 34, CW - 34, name=BOLD, size=size - 2, fill=EVENT_COL, gap=6)
    if end > CH - 20 and size > 18:
        return event_face(eid, name, what, rule, size - 1)
    return im


def event_art(pic, name, what, rule, size=26):
    """An event card with a drawing: the drawing fills the card, the rules on a dark panel at the bottom."""
    im = pic.copy()
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, CW, 70), fill=GRAPHITE)
    hazard(d, (0, 62, CW, 74), 18)
    d.text((CW / 2, 32), "EVENT | ROUND 2", font=f(BLACK, 30), fill=EMERG, anchor="mm")
    band(im, (20, 88, CW - 20, 150))
    d = ImageDraw.Draw(im)
    d.text((CW / 2, 119), name.upper(), font=fit(d, name.upper(), BLACK, 42, CW - 60), fill=CREAM, anchor="mm")
    top = 300
    band(im, (16, top, CW - 16, CH - 16), 215)
    d = ImageDraw.Draw(im)
    y = para(d, what, top + 14, 34, CW - 34, size=size, fill=CREAM, gap=5)
    d.line((50, y + 10, CW - 50, y + 10), fill=EMERG, width=3)
    end = para(d, rule, y + 24, 34, CW - 34, name=BOLD, size=size - 2, fill=EMERG, gap=5)
    d.rectangle((0, 0, CW - 1, CH - 1), outline=EVENT_COL, width=12)
    if end > CH - 26 and size > 16:
        return event_art(pic, name, what, rule, size - 1)
    return im


def event_sheet():
    ims = [event_face(*e) for e in EVENTS]
    rows = math.ceil(len(ims) / EVENT_COLS)
    sheet = Image.new("RGB", (CW * EVENT_COLS, CH * rows), PAPER)
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % EVENT_COLS) * CW, (i // EVENT_COLS) * CH))
    save(sheet, "event-sheet.png")
    back = art("event-back", (CW, CH)) or Image.new("RGB", (CW, CH), GRAPHITE)
    d = ImageDraw.Draw(back)
    hazard(d, (0, 0, CW, 40)); hazard(d, (0, CH - 40, CW, CH))
    d.rectangle((16, 56, CW - 16, CH - 56), outline=EMERG, width=6)
    d.text((CW / 2, CH / 2 - 20), "EVENT", font=f(BLACK, 80), fill=EMERG, anchor="mm")
    d.text((CW / 2, CH / 2 + 50), "NULLWAKE", font=f(BLACK, 32), fill=CREAM, anchor="mm")
    save(back, "event-back.png")
    return rows


# ------------------------------------------------------------------ player mats
# Three boxes: dice, TREASURE (the treasure and objects you took) and MONSTERS (the ones you beat), and the
# points at the right (v2.3: what each treasure and monster is worth; the combinations are gone). v2.0's CARRIED box is gone: the rules of 11-03 have no
# securing treasure in the Safe Room, only escaping at the end. Above, what each action needs. The mat is
# wider than v2.0's (1400 px, 12.7 table units) to fit the points table. Pixel spots for the tutorial.
MAT_W, MAT_H = 1400, 680
BOX_Y = (180, 660)
MAT_BOX = {"dice": (30, 300, "DICE", ""), "carry": (315, 660, "TREASURE", "and special objects"),
           "points": (675, 1020, "MONSTERS", "beaten: their points")}
TABLE_X = (1035, 1370)
MAT_ACTIONS = [("MOVE / OPEN", "move", 2), ("SCRAPER", "attack", 1), ("CARRIER", "attack", 2), ("ANOMALY", "attack", 3),
               ("TAKE", "magic", 2), ("ESCAPE", None, 0)]
DIE_PX = [(100, 375), (230, 375), (100, 555), (230, 555)]
CARRY_PX = [(x, y) for y in (365, 478, 591) for x in (375, 487, 600)]
POINTS_PX = [(x, y) for y in (365, 478, 591) for x in (735, 847, 960)]


def mat_img(color):
    pic = art("mat", (MAT_W, MAT_H))
    # The drawing darkened behind the boxes, so the dice and tokens on them stay easy to see.
    im = Image.blend(pic, Image.new("RGB", (MAT_W, MAT_H), GRAPHITE), 0.45) if pic else Image.new("RGB", (MAT_W, MAT_H), GRAPHITE)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, MAT_W - 1, MAT_H - 1), outline=PIX[color], width=16)
    d.rectangle((0, 0, MAT_W, 78), fill=PIX[color])
    light = color in ("Yellow",)
    d.text((MAT_W / 2, 40), color.upper(), font=f(BLACK, 50), fill=INK if light else CREAM, anchor="mm")
    slot = (MAT_W - 60) / len(MAT_ACTIONS)
    for i, (name, kind, n) in enumerate(MAT_ACTIONS):
        cx = 30 + slot * (i + 0.5)
        d.text((cx, 104), name, font=fit(d, name, BLACK, 26, slot - 10), fill=CREAM, anchor="mm")
        if kind:
            sym_row(d, kind, n, cx, 143, 14)
        else:
            safe_mark(d, cx - 92, 143, 15, GOLD, SAFE_COL)
            d.text((cx - 70, 143), "Safe Zone + object placed", font=fit(d, "Safe Zone + object placed", REG, 18, slot - 50),
                   fill=CREAM, anchor="lm")
        if i:
            d.line((30 + slot * i, 90, 30 + slot * i, 164), fill=(80, 88, 98), width=2)
    for key, (x0, x1, head, sub) in MAT_BOX.items():
        fill = {"dice": (52, 58, 66), "carry": (46, 60, 72), "points": (66, 50, 52)}[key]
        d.rounded_rectangle((x0, BOX_Y[0], x1, BOX_Y[1]), 16, fill=fill, outline=STEEL, width=3)
        d.text(((x0 + x1) / 2, BOX_Y[0] + 28), head, font=f(BLACK, 30), fill=(170, 182, 192), anchor="mm")
        if sub:
            d.text(((x0 + x1) / 2, BOX_Y[0] + 60), sub, font=fit(d, sub, REG, 20, x1 - x0 - 16), fill=(150, 160, 170), anchor="mm")
    # The points: each treasure alone (v2.3, no combinations), then each monster (rules §5.4).
    x0, x1 = TABLE_X
    d.rounded_rectangle((x0, BOX_Y[0], x1, BOX_Y[1]), 16, fill=PAPER, outline=STEEL, width=3)
    d.text(((x0 + x1) / 2, BOX_Y[0] + 28), "POINTS", font=f(BLACK, 28), fill=INK, anchor="mm")
    rows = [(TREASURES[k][0], v) for k, v in SINGLE.items()] + [(name, pts) for name, _hp, pts, _n in MONSTERS.values()]
    y = BOX_Y[0] + 70
    for i, (t, v) in enumerate(rows):
        if i == len(SINGLE):
            d.line((x0 + 16, y + 4, x1 - 16, y + 4), fill=STEEL, width=2)
            y += 22
        d.text((x0 + 22, y + 22), t, font=fit(d, t, REG, 28, x1 - x0 - 80), fill=INK, anchor="lm")
        d.text((x1 - 24, y + 22), str(v), font=f(BOLD, 30), fill=INK, anchor="rm")
        y += 56
    d.text(((x0 + x1) / 2, BOX_Y[1] - 26), "escape to keep them", font=f(REG, 20), fill=(90, 98, 108), anchor="mm")
    return save(im, f"mat-{color.lower()}.png")


def title_img():
    """The name plate: only the name (Yavuz, 2026-10-26, for Kingbound), now NULLWAKE in cold blue on graphite."""
    w, h = 1400, 360
    deep, mid = (14, 17, 22), (44, 52, 62)
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):                       # graphite, lighter in the middle, dark at the edges
        k = 1 - abs(y - h * 0.45) / (h * 0.55)
        row = tuple(int(deep[i] + (mid[i] - deep[i]) * max(0.0, k)) for i in range(3))
        for x in range(w):
            px[x, y] = row
    d = ImageDraw.Draw(im)
    d.rectangle((14, 14, w - 15, h - 15), outline=STEEL, width=6)
    d.rectangle((30, 30, w - 31, h - 31), outline=GOLD, width=2)
    hazard(d, (30, h - 58, 210, h - 31), 16)
    hazard(d, (w - 210, h - 58, w - 31, h - 31), 16)
    # Letters spaced out, with a cold glow under them.
    font, track = f(COND, 210), 26
    widths = [d.textlength(ch, font=font) for ch in "NULLWAKE"]
    x0, base = (w - (sum(widths) + track * 7)) / 2, 262
    glow_ = Image.new("L", (w, h), 0)
    sd = ImageDraw.Draw(glow_)
    x = x0
    for ch, cw in zip("NULLWAKE", widths):
        sd.text((x, base), ch, font=font, fill=170, anchor="ls")
        x += cw + track
    im.paste(GOLD, (0, 0), glow_.filter(ImageFilter.GaussianBlur(14)))
    x = x0
    for ch, cw in zip("NULLWAKE", widths):
        d.text((x, base), ch, font=font, fill=CREAM, anchor="ls", stroke_width=2, stroke_fill=GOLD)
        x += cw + track
    return save(im, "title.png")


# ------------------------------------------------------------------ draw everything
for old in OUT.glob("*.png"):
    old.unlink()
dice_img()
ROOM_BACK = room_back()
EVENT_ROWS = event_sheet()
for c in COLORS:
    mat_img(c)
title_img()
TOKEN_IMG = {}
for k, (name, hp, pts, n) in MONSTERS.items():
    TOKEN_IMG[("monster", k)] = token_front(f"mon-{k}.png", SYM_COL["attack"], name.upper(), "attack", hp,
                                            [f"{hp} HP", f"{pts} POINT{'S' if pts > 1 else ''}"])
for k, (name, n) in TREASURES.items():
    TOKEN_IMG[("treasure", k)] = token_front(f"tre-{k}.png", GOLD, name.upper(), "magic", 2, [f"{SINGLE[k]} POINT{'S' if SINGLE[k] != 1 else ''}"],
                                            title_col=(24, 92, 138))   # the cold blue ring is too light for letters
for o in OBJECTS:
    TOKEN_IMG[("object", o)] = token_front(f"obj-{o.lower()}.png", OBJ_COL, f"OBJECT {o}", "magic", 2,
                                           ["PLACE IT", "IN ROUND 2"])
# Symbol icons beside the part's name on screen (what the step costs), same look as the dice faces.
for k, fn in (("move", "icon-move.png"), ("attack", "icon-attack.png"), ("magic", "icon-magic.png")):
    im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((4, 4, 124, 124), fill=SYM_COL[k], outline=CREAM, width=6)
    icon(d, k, 64, 64, 40)
    save(im, fn)
MON_BACK = token_back("mon-back.png", SYM_COL["attack"], "MONSTER")
OBJ_BACK = token_back("obj-back.png", OBJ_COL, "OBJECT")
# Aliens (event E7): a token for each monster kind, 1 HP more, the same points.
ALIENS = {f"alien{k}": (f"Alien {name}", hp + 1, pts, n + 1) for k, (name, hp, pts, n) in MONSTERS.items()}
for k, (name, hp, pts, n) in ALIENS.items():
    TOKEN_IMG[("alien", k)] = token_front(f"{k}.png", ALIEN_COL, name.upper(), "attack", hp,
                                          [f"{hp} HP", f"{pts} POINT{'S' if pts > 1 else ''}"], title_col=(40, 96, 30))
ALIEN_BACK = token_back("alien-back.png", ALIEN_COL, "ALIEN")


def small_token(fn, ring, draw, text):
    """The black hole (event E8): a corner of a room, so small and simple."""
    im = Image.new("RGB", (TOK, TOK), ring)
    pic = art(fn[:-4], (TOK, TOK))
    if pic:
        round_art(im, pic)
        band(im, (60, 246, TOK - 60, 310))
        d = ImageDraw.Draw(im)
        d.ellipse((14, 14, TOK - 14, TOK - 14), outline=INK, width=5)
        d.text((TOK / 2, 278), text, font=fit(d, text, BLACK, 46, 220), fill=CREAM, anchor="mm")
        return save(im, fn)
    d = ImageDraw.Draw(im)
    d.ellipse((14, 14, TOK - 14, TOK - 14), fill=PAPER, outline=INK, width=5)
    draw(d, TOK / 2, 150, 92)
    d.text((TOK / 2, 278), text, font=fit(d, text, BLACK, 52, 230), fill=INK, anchor="mm")
    return save(im, fn)


# v2.3: only black holes are left (gas went with Poison Gas, the Safe Zone token with the old Lost Path).
HOLE = small_token("hole.png", HOLE_COL, black_hole, "HOLE -1")
HAZ_BACK = token_back("haz-back.png", EMERG, "EVENT")
TRE_BACK = token_back("tre-back.png", GOLD, "TREASURE")

# ------------------------------------------------------------------ the dungeon plan
# The tutorial (../tutorial.py) reveals rooms in a fixed order so the video shows each step; the room
# stack is built in that order, and the rooms after it are random. A passage is drawn on a side when
# the room there is connected in the plan, or when that cell stays empty (room for later).
# START GAME shuffles the stack for a real game; RESET TABLE puts the tutorial's order back.
import sys
sys.path.insert(0, str(ROOT.parent))
import plan as P  # noqa: E402  the tutorial's dungeon: which room goes where, in which order

rng = random.Random(7)
cells = {(0, 0): "safe"}
for cell, kind, _tok in P.ROOMS:
    cells[cell] = kind
links = set()
for a, b in P.LINKS:
    links.add((a, b)); links.add((b, a))
SIDES = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0)}


def doors_of(cell):
    out = []
    for s, (dx, dz) in SIDES.items():
        nb = (cell[0] + dx, cell[1] + dz)
        if (cell, nb) in links or (nb not in cells and rng.random() < 0.55):
            out.append(s)
    return out or ["N"]


ROOM_IMG = {(0, 0): room_img("safe", ["N", "S", "E", "W"])}
for cell, kind, _ in P.ROOMS:
    ROOM_IMG[cell] = room_img(kind, doors_of(cell))
# The rest of the stack (§3 step 3): random rooms with random passages, up to ROOM_COUNT. The special
# objects room has at least two passages, as v1.1's trap rooms had, so it sits on a route.
left = dict(ROOM_COUNT)
for _, kind, _ in P.ROOMS:
    left[kind] -= 1
assert all(v >= 0 for v in left.values()), left
SPARE = []
for kind, n in left.items():
    for _ in range(n):
        ds = [s for s in "NSEW" if rng.random() < 0.6]
        if len(ds) < 2:
            ds = ["N", "S"] if kind == "special" or not ds else ds
        SPARE.append((room_img(kind, ds), kind))
rng.shuffle(SPARE)

# Rooms and tokens are cards in decks, so players draw from a deck instead of a tall pile of
# loose tiles (Yavuz, 2026-10-25: "deste oluşturabilirsin"). The room deck, top card first: the
# tutorial's rooms in the order it reveals them, then the spares. START GAME shuffles every deck.
# The special objects room is "special" in its GM Notes: the script finds it there (objects placed).
ROOM_CARDS = ([{"fn": ROOM_IMG[c], "kind": k, "notes": "special" if k == "special" else f"{c[0]},{c[1]}"} for c, k, _ in P.ROOMS]
              + [{"fn": fn, "kind": kind, "notes": "special" if kind == "special" else f"spare{i}"}
                 for i, (fn, kind) in enumerate(SPARE)])
assert len(ROOM_CARDS) == sum(ROOM_COUNT.values())


def card_sheet(fns, out, cols):
    """Images side by side on one card sheet. TTS cuts it into cards, and square cells give square cards."""
    cell = Image.open(OUT / fns[0]).size[0]
    rows = math.ceil(len(fns) / cols)
    sheet = Image.new("RGB", (cell * cols, cell * rows), (0, 0, 0))
    for i, fn in enumerate(fns):
        sheet.paste(Image.open(OUT / fn).convert("RGB"), ((i % cols) * cell, (i // cols) * cell))
    save(sheet, out)
    return cols, rows


ROOM_SHEET = card_sheet([r["fn"] for r in ROOM_CARDS], "room-sheet.png", 7)
MON_SHEET = card_sheet([TOKEN_IMG[("monster", k)] for k in MONSTERS], "mon-sheet.png", 3)
TRE_SHEET = card_sheet([TOKEN_IMG[("treasure", k)] for k in TREASURES], "tre-sheet.png", 3)
OBJ_SHEET = card_sheet([TOKEN_IMG[("object", o)] for o in OBJECTS], "obj-sheet.png", 2)
ALIEN_SHEET = card_sheet([TOKEN_IMG[("alien", k)] for k in ALIENS], "alien-sheet.png", 3)
HAZ_SHEET = card_sheet([HOLE, HOLE], "hazard-sheet.png", 2)   # one face; a sheet has at least two cells
# Event E5's second Integration Chamber: passages on every side, so it fits beside any room (GDD: "It must be
# connected to an existing room").
EXTRA_ROOM = room_img("special", ["N", "S", "E", "W"])
EXTRA_SHEET = card_sheet([EXTRA_ROOM, EXTRA_ROOM], "extra-sheet.png", 2)

# ------------------------------------------------------------------ images into Mods/
for old in ASSETS.glob("*.png"):
    old.unlink()
HASHED = {}
for png in sorted(OUT.glob("*.png")):
    data = png.read_bytes()
    name = f"{png.stem}.{hashlib.sha1(data).hexdigest()[:10]}.png"
    (ASSETS / name).write_bytes(data)
    HASHED[png.name] = name


# Steam Cloud URLs, so the save also opens on other computers (the Steam Workshop item, 2026-10-25).
# cloud_urls.json maps an output file name to its URL and the sha1 of the file that was uploaded. A file
# that has changed since falls back to its local path, which only this Mac can open, until it is
# uploaded again: load the save, Modding > Cloud Manager > Upload All, save, python3 cloud_urls.py SAVE.
CLOUD = json.loads((ROOT / "cloud_urls.json").read_text()) if (ROOT / "cloud_urls.json").exists() else {}
LOCAL = set()


def url(fn):
    c = CLOUD.get(fn)
    if c and c["sha1"] == hashlib.sha1((OUT / fn).read_bytes()).hexdigest():
        return c["url"]
    LOCAL.add(fn)
    return str(ASSETS / HASHED[fn])


# ------------------------------------------------------------------ save JSON
guid_n = 0


def guid():
    global guid_n
    guid_n += 1
    return f"{0xd00000 + guid_n:06x}"


def tr(x, z, rot_y=180.0, face_down=False, s=1.0, y=1.5, sz=None):
    return {"posX": x, "posY": y, "posZ": z, "rotX": 0.0, "rotY": rot_y, "rotZ": 180.0 if face_down else 0.0,
            "scaleX": s, "scaleY": 1.0, "scaleZ": s if sz is None else sz}


def base(name, transform, nick="", desc="", **kw):
    o = {"GUID": guid(), "Name": name, "Transform": transform, "Nickname": nick, "Description": desc,
         "GMNotes": "", "Locked": True, "Grid": False, "Snap": False, "Tooltip": False, "Hands": False,
         "LuaScript": "", "LuaScriptState": "", "XmlUI": ""}
    o.update(kw)
    return o


def tile(fn, transform, nick, back=None, circle=False, thick=0.12, desc="", **kw):
    # Live-measured on v0.1: Stretch off draws the tile square (2 x scale); Stretch on keeps the image's
    # shape (2 x scale deep, wider by width / height).
    im = Image.open(OUT / fn)
    stretch = im.size[0] != im.size[1]
    return base("Custom_Tile", transform, nick, desc,
                CustomImage={"ImageURL": url(fn), "ImageSecondaryURL": url(back) if back else "", "ImageScalar": 1.0,
                             "WidthScale": 0.0, "CustomTile": {"Type": 2 if circle else 0, "Thickness": thick,
                                                               "Stackable": False, "Stretch": stretch}}, **kw)


# Table layout (table units). The players sit around the table, each mat on its own side, facing the
# player who sits there (Yavuz, 2026-10-26: "her oyuncunun kartı tek kişiye dönük, 4 kişi oynamak üzere
# yeniden düzenle"; before, all five mats lay along the south edge for the video). TTS seats Red on
# the south side of Table_RPG, Yellow west, Green north and Blue east (measured on The Limit); Purple,
# for a fifth player, lies next to Red. rot is the mat's Y rotation: 180 reads from the south, 0 from
# the north, 270 from the west, 90 from the east. The felt ends near x = ±28.3 and z = ±18.3.
GRID = 3.7            # room spacing; rooms are 3.6 wide
DUNGEON = (0.0, 0.0)  # the Safe Zone, in the middle of the table
ROOM_S = 1.8
MAT_DEPTH = round(10.0 * 680 / 1100, 4)                    # v2.0's depth; v2.1 is only wider
MAT_SIZE = (round(MAT_DEPTH * MAT_W / MAT_H, 4), MAT_DEPTH)  # width, depth in table units: 12.7 x 6.2
MAT_S = MAT_SIZE[1] / 2                                    # Stretch on: depth = 2 x scale
EDGE_Z, EDGE_X = round(18.2 - MAT_SIZE[1] / 2, 3), round(28.2 - MAT_SIZE[1] / 2, 3)   # mats against the felt's edge
MATS = {"Red": (0.0, -EDGE_Z, 180), "Green": (0.0, EDGE_Z, 0),
        "Yellow": (-EDGE_X, 0.0, 270), "Blue": (EDGE_X, 0.0, 90)}


def mat_world(color, px, py):
    """A point of a mat's image (pixels) on the table. The image's right and down turn with the mat."""
    cx, cz, rot = MATS[color]
    u, v = (px / MAT_W - 0.5) * MAT_SIZE[0], (py / MAT_H - 0.5) * MAT_SIZE[1]
    t = math.radians(rot)
    return round(cx - u * math.cos(t) + v * math.sin(t), 3), round(cz + u * math.sin(t) + v * math.cos(t), 3)


# A hand zone at every mat, just off the table's edge behind it and turned to the middle. A hand zone is
# what makes a colour a seat in TTS (it also sets where that player sits): v1.1 had none, so online nobody
# could pick a mat's colour (Yavuz, 2026-10-26: "colorlar teamlar yok ... yapamıyoruz online olarak").
# Table_RPG's own hands lie at z = ±21 and x = ±31, 11.8 x 9.2 x 4.9 (The Limit, SHOWDOWN).
def hand_of(color):
    x, z, rot = MATS[color]
    if rot in (0, 180):   # a mat on the south or north edge
        return x, math.copysign(21.0, z), (rot + 180) % 360
    return math.copysign(31.0, x), z, (rot + 180) % 360


# The shared decks wait in the corners, clear of the mats and of the dungeon growing from the middle.
STACK = (-13.5, 15.2)  # face-down room deck
MON_PILE, TRE_PILE = (11.5, 15.6), (14.6, 15.6)
EVENT_POS = (18.6, 15.2)    # the event deck, where v1.1's Loot Deck was
EVENT_SHOW = (22.6, 15.2)   # the event card turned up for round 2; Extra Risk's cards go below it
EXTRA_POS = (18.6, 11.4)    # event E5's chamber waits face down under the event deck
ALIEN_POS, HAZ_POS = (-21.4, 15.6), (-24.6, 15.6)
OBJ_POS = (8.4, 15.6)       # the special objects, beside the monster and treasure tokens
TITLE_POS = (-20.5, -15.4)
PAWN_HOME = {c: mat_world(c, 70, -110) for c in COLORS}   # just inside the mat's top edge, towards the middle
# Cards (measured live, 2026-10-25): a card cut from a square cell is 3.06 across at scale 1 and 0.027
# thick; it lies at y 0.974 on the felt and at 1.001 on another card. Cards of different shapes (a
# square room, a round token) never join into one deck, so a token can lie on a room card.
CARD_W = 3.06
ROOM_CARD_S = round(3.6 / CARD_W, 4)     # a room: 3.6 across, on the 3.7 grid
TOKEN_CARD_S = round(1.4 / CARD_W, 4)    # a token in a room's middle leaves space for five characters
MAT_TOKEN_S = round(1.0 / CARD_W, 4)     # a token on a mat box (the tutorial)


def cell_pos(c): return (round(DUNGEON[0] + c[0] * GRID, 3), round(DUNGEON[1] + c[1] * GRID, 3))


# Pieces players move are unlocked; the director locks them while it films (OPS.reset with stage).
objs = []
objs.append(tile("title.png", tr(*TITLE_POS, s=1.2, y=1.02), "NULLWAKE", thick=0.05, Tags=["title"]))
# Unlocked since v2.3: Lost Path has the players swap it with the Integration Chamber by hand, and the
# script reads where it lies (RESET TABLE puts it back).
objs.append(tile(ROOM_IMG[(0, 0)], tr(*cell_pos((0, 0)), s=ROOM_S, y=0.98), "Safe Zone", back=ROOM_BACK,
                 desc="Everyone starts here. Be back here at 0:00 with an object placed to keep your points.",
                 Tooltip=True, Tags=["room", "saferoom"], GMNotes="0,0", Locked=False))

# Cards and decks. A deck lies face down; each card carries its identity in GM Notes, so the tutorial
# takes the card its plan needs and RESET TABLE sends every card back to its own deck. A face-down card
# hides its name and text (HideWhenFaceDown), so hovering over a deck gives nothing away.
ROOM_KEY, MON_KEY, TRE_KEY, EVENT_KEY, ALIEN_KEY, HAZ_KEY, EXTRA_KEY, OBJ_KEY = 2, 3, 4, 1, 6, 7, 8, 9
SHAPE = {"rounded": 0, "square": 1, "circle": 4}     # TTS custom deck card shapes


def cdeck(face, back, cols_rows, shape):
    return {"FaceURL": url(face), "BackURL": url(back), "NumWidth": cols_rows[0], "NumHeight": cols_rows[1],
            "BackIsHidden": True, "UniqueBack": False, "Type": SHAPE[shape]}


def card(nick, desc, key, cd, index, notes, s, hide=True):
    return base("Card", tr(0, 0, face_down=True, s=s), nick, desc, GMNotes=notes, Locked=False, Tooltip=True,
                CardID=key * 100 + index, CustomDeck={str(key): cd}, SidewaysCard=False, HideWhenFaceDown=hide)


def deck(nick, pos, key, cd, cards, tag, s):
    return base("Deck", tr(*pos, face_down=True, s=s, y=1.3), nick, Locked=False, DeckIDs=[c["CardID"] for c in cards],
                CustomDeck={str(key): cd}, ContainedObjects=cards, SidewaysCard=False, HideWhenFaceDown=True, Tags=[tag])


# Room deck (§2, §8). Square corners, so rooms meet edge to edge.
ROOM_DECK = cdeck("room-sheet.png", ROOM_BACK, ROOM_SHEET, "square")
ROOM_TEXT = {"empty": "Nothing to fight or take.", "monster": "Turn a monster token face up on it.",
             "treasure": "Turn a treasure token face up on it.",
             "special": "Four slots. In round 2, drop a special object here: that completes your special task."}
ROOM_NICK = {k: ROOM_NAME[k] for k in ROOM_COUNT}
room_cards = [card(ROOM_NICK[r["kind"]], ROOM_TEXT[r["kind"]], ROOM_KEY, ROOM_DECK, i, r["notes"], ROOM_CARD_S)
              for i, r in enumerate(ROOM_CARDS)]
objs.append(deck("Rooms", STACK, ROOM_KEY, ROOM_DECK, room_cards, "roomdeck", ROOM_CARD_S))

# Monster and treasure tokens (§3 step 4): round cards in two decks. The special objects are in the
# treasure deck: they turn up in treasure rooms and are taken the same way.
TOKEN_IDS = []
MON_DECK = cdeck("mon-sheet.png", MON_BACK, MON_SHEET, "circle")
cards = []
for j, (k, (name, hp, pts, n)) in enumerate(MONSTERS.items()):
    for i in range(n):
        TOKEN_IDS.append(f"m-{k}-{i + 1}")
        cards.append(card(name, f"{hp} HP: each Attack deals 1 damage, and damage stays. {pts} point{'s' if pts > 1 else ''}. "
                          "Right-click: Hit.", MON_KEY, MON_DECK, j, TOKEN_IDS[-1], TOKEN_CARD_S))
random.Random(11).shuffle(cards)
objs.append(deck("Monster tokens", MON_PILE, MON_KEY, MON_DECK, cards, "mondeck", TOKEN_CARD_S))
objs[-1]["Tags"].append("token")       # the tutorial makes both token decks glow
TRE_DECK = cdeck("tre-sheet.png", TRE_BACK, TRE_SHEET, "circle")
def treasure_desc(k): return f"Needs 2 Magic. {SINGLE[k]} point{'s' if SINGLE[k] != 1 else ''}."
OBJECT_DESC = "Needs 2 Magic. In round 2, drop it on the Integration Chamber: that completes your special task."
cards = []
for j, (k, (name, n)) in enumerate(TREASURES.items()):
    for i in range(n):
        TOKEN_IDS.append(f"t-{k}-{i + 1}")
        cards.append(card(name, treasure_desc(k), TRE_KEY, TRE_DECK, j, TOKEN_IDS[-1], TOKEN_CARD_S))
random.Random(11).shuffle(cards)
objs.append(deck("Treasure tokens", TRE_PILE, TRE_KEY, TRE_DECK, cards, "tredeck", TOKEN_CARD_S))
objs[-1]["Tags"].append("token")
# The special objects in a deck of their own, apart from the treasure (Yavuz, 2026-11-04: "bu token de ayrı dursun
# diğerlerinden"). Players take them by hand, like the event tokens.
OBJ_DECK = cdeck("obj-sheet.png", OBJ_BACK, OBJ_SHEET, "circle")
obj_cards = []
for j, o in enumerate(OBJECTS):
    TOKEN_IDS.append(f"o-{j + 1}")
    obj_cards.append(card(f"Object {o}", OBJECT_DESC, OBJ_KEY, OBJ_DECK, j, TOKEN_IDS[-1], TOKEN_CARD_S, hide=False))
objs.append(deck("Special objects", OBJ_POS, OBJ_KEY, OBJ_DECK, obj_cards, "objdeck", TOKEN_CARD_S))

# Event tokens (GDD 11-04): aliens (E7) and black holes (E8).
ALIEN_DECK = cdeck("alien-sheet.png", ALIEN_BACK, ALIEN_SHEET, "circle")
def mon_desc(hp, pts, alien=False):
    return (f"{hp} HP: each Attack deals 1 damage, and damage stays. {pts} point{'s' if pts > 1 else ''}. Right-click: Hit."
            + (" You can't go through its room without beating it." if alien else ""))
alien_cards = []
for j, (k, (name, hp, pts, n)) in enumerate(ALIENS.items()):
    alien_cards += [card(name, mon_desc(hp, pts, True), ALIEN_KEY, ALIEN_DECK,
                         j, f"m-{k}-{i + 1}", TOKEN_CARD_S) for i in range(n)]
objs.append(deck("Alien tokens", ALIEN_POS, ALIEN_KEY, ALIEN_DECK, alien_cards, "aliendeck", TOKEN_CARD_S))
HAZ_DECK = cdeck("hazard-sheet.png", HAZ_BACK, HAZ_SHEET, "circle")
haz_cards = [card("Black hole", "Going through this room costs 1 point.", HAZ_KEY, HAZ_DECK, 0, f"hole-{i + 1}", MAT_TOKEN_S, hide=False)
             for i in range(HOLE_COUNT)]
objs.append(deck("Black hole tokens", HAZ_POS, HAZ_KEY, HAZ_DECK, haz_cards, "hazarddeck", MAT_TOKEN_S))
EXTRA_DECK = cdeck("extra-sheet.png", ROOM_BACK, EXTRA_SHEET, "square")
extra = card("Integration Chamber", "Extra Special Tile: four more slots. In round 2, drop a special object here: that "
             "completes your special task.", EXTRA_KEY, EXTRA_DECK, 0, "special2", ROOM_CARD_S)
extra["Transform"] = tr(*EXTRA_POS, face_down=True, s=ROOM_CARD_S, y=1.3)
extra["Tags"] = ["extradeck"]
objs.append(extra)

# The event card (rules §10), face down; round 2 turns it up. One card is a card, not a deck (TTS makes a deck
# of at least two), so it carries the deck's tag itself.
EVENT_DECK = cdeck("event-sheet.png", "event-back.png", (EVENT_COLS, EVENT_ROWS), "rounded")
event_cards = [card(name, f"{what} {rule}", EVENT_KEY, EVENT_DECK, i, eid, 0.75) for i, (eid, name, what, rule) in enumerate(EVENTS)]
if len(event_cards) > 1:
    objs.append(deck("Event cards", EVENT_POS, EVENT_KEY, EVENT_DECK, event_cards, "eventdeck", 0.75))
else:
    ev = event_cards[0]
    ev["Transform"] = tr(*EVENT_POS, face_down=True, s=0.75, y=1.3)
    ev["Tags"] = ["eventdeck"]
    objs.append(ev)

# Player mats, pawns (character tokens, §2.2) and 4 dice each (§2.3).
DICE_IMG = url("dice.png")
for c in COLORS:
    mx, mz, rot = MATS[c]
    objs.append(tile(f"mat-{c.lower()}.png", tr(mx, mz, rot_y=rot, s=MAT_S, y=1.02), f"{c} mat", thick=0.06,
                     Tags=["mat"], GMNotes=c))
    hx, hz, hrot = hand_of(c)
    objs.append(base("HandTrigger", {"posX": hx, "posY": 4.8, "posZ": hz, "rotX": 0.0, "rotY": hrot, "rotZ": 0.0,
                                     "scaleX": 11.8, "scaleY": 9.2, "scaleZ": 4.9}, FogColor=c))
    objs.append(base("PlayerPawn", tr(*PAWN_HOME[c], 0.0, s=1.1, y=1.6), f"{c} character", Locked=False,
                     ColorDiffuse={"r": RGB[c][0], "g": RGB[c][1], "b": RGB[c][2]}, Tags=["pawn"], GMNotes=c))
    for i in range(4):
        objs.append(base("Custom_Dice", tr(*mat_world(c, *DIE_PX[i]), rot, s=1.5, y=1.46), f"{c} die {i + 1}",
                         Locked=False, ColorDiffuse={"r": 1.0, "g": 1.0, "b": 1.0},
                         CustomImage={"ImageURL": DICE_IMG, "ImageSecondaryURL": "", "ImageScalar": 1.0,
                                      "WidthScale": 0.0, "CustomDice": {"Type": 1}},
                         Tags=["die"], GMNotes=f"{c}:{i + 1}"))

# A save must not carry a wrong type in a field TTS knows (v0.1: a text in "Locked" made TTS refuse
# the whole save).
for o in objs:
    for key in ("Locked", "Tooltip", "Grid", "Snap", "Hands"):
        assert isinstance(o[key], bool), (o["Nickname"], key)

# ------------------------------------------------------------------ Lua and UI
LAYOUT = {"icons": {"M": url("icon-move.png"), "A": url("icon-attack.png"), "G": url("icon-magic.png")},
          "grid": GRID, "dungeon": DUNGEON,
          "decks": {"room": "roomdeck", "monster": "mondeck", "treasure": "tredeck", "event": "eventdeck",
                    "alien": "aliendeck", "hazard": "hazarddeck", "extra": "extradeck", "object": "objdeck"},
          "deck_pos": {"room": STACK, "monster": MON_PILE, "treasure": TRE_PILE, "event": EVENT_POS,
                       "alien": ALIEN_POS, "hazard": HAZ_POS, "extra": EXTRA_POS, "object": OBJ_POS},
          "deck_s": {"room": ROOM_CARD_S, "monster": TOKEN_CARD_S, "treasure": TOKEN_CARD_S, "event": 0.75,
                     "alien": TOKEN_CARD_S, "hazard": MAT_TOKEN_S, "extra": ROOM_CARD_S, "object": TOKEN_CARD_S},
          "mat_tok_s": MAT_TOKEN_S,
          "colors": COLORS, "mats": MATS, "mat_size": MAT_SIZE, "mat_px": (MAT_W, MAT_H),
          "die_px": DIE_PX, "carry_px": CARRY_PX, "points_px": POINTS_PX,
          "pawn_home": PAWN_HOME, "faces": DIE_FACES, "game_secs": GAME_SECS, "round2_at": ROUND2_AT,
          "event_show": EVENT_SHOW,
          "objects": len(OBJECTS), "object_desc": OBJECT_DESC, "obj_slot_px": OBJ_SLOT_PX, "room_w": 3.6,
          "title_pos": TITLE_POS,
          "monsters": {k: {"name": v[0], "hp": v[1], "points": v[2]} for k, v in {**MONSTERS, **ALIENS}.items()},
          "mon_desc": {k: mon_desc(v[1], v[2], k in ALIENS) for k, v in {**MONSTERS, **ALIENS}.items()},
          "alien_s": TOKEN_CARD_S}
LUA = (ROOT / "global.lua").read_text().replace("__VERSION__", VERSION).replace("__LAYOUT__", json.dumps(LAYOUT))

XML = (
    # The 10-minute timer, top right, below TTS's toolbar and the player list: a 16:9 crop of the screen
    # without the toolbar (the gameplay video, 2026-11-03) keeps it whole.
    '<Panel id="kbTimer" active="false" rectAlignment="UpperRight" offsetXY="-24 -150" width="300" height="104" color="#000000C8">\n'
    '  <Text id="kbTimerLabel" rectAlignment="UpperCenter" offsetXY="0 -4" height="26" fontSize="19" color="#5CB0DE" alignment="MiddleCenter">TIME LEFT</Text>\n'
    '  <Text id="kbTimerText" rectAlignment="LowerCenter" offsetXY="0 2" height="76" fontSize="62" color="#ECF0F2" alignment="MiddleCenter">10:00</Text>\n'
    '</Panel>\n'
    # The name of the current part, bottom centre (no sentences: the team explains it while presenting).
    # Up to 4 symbol icons follow the name: what the step costs (2 Movement, 3 Attack ...).
    # Small (Yavuz, 2026-10-19: "make the texts at the bottom smaller").
    '<Panel id="kbCaption" active="false" rectAlignment="LowerCenter" offsetXY="0 22" width="400" height="56" color="#000000DC">\n'
    '  <HorizontalLayout childAlignment="MiddleCenter" childForceExpandWidth="false" childForceExpandHeight="false" spacing="8" padding="16 16 6 6">\n'
    '    <Text id="kbCaptionHead" preferredWidth="300" preferredHeight="44" fontSize="29" fontStyle="Bold" color="#5CB0DE" alignment="MiddleCenter" horizontalOverflow="Overflow" verticalOverflow="Overflow"></Text>\n'
    + "\n".join(f'    <Image id="kbIcon{i}" active="false" preferredWidth="38" preferredHeight="38"></Image>' for i in range(1, 5))
    + '\n  </HorizontalLayout>\n</Panel>\n'
    # Scores at the end, top centre over the dungeon (the camera is on the mats then).
    f'<Panel id="kbScore" active="false" rectAlignment="UpperCenter" offsetXY="0 -160" width="820" height="{48 + 58 * len(COLORS)}" color="#000000E6">\n'
    '  <VerticalLayout padding="24 24 14 14" spacing="6">\n'
    + "\n".join(f'    <Text id="kbScore{i}" fontSize="30" fontStyle="Bold" color="#ECF0F2" alignment="MiddleLeft"></Text>' for i in range(1, len(COLORS) + 1))
    + '\n  </VerticalLayout>\n</Panel>\n'
    # A big centre banner for "go", "time's up" and the winner.
    # Two lines at round 2: the round and the event, so smaller than v1.1's 72.
    '<Panel id="kbBanner" active="false" rectAlignment="MiddleCenter" offsetXY="0 120" width="1200" height="170" color="#000000D2">\n'
    '  <Text id="kbBannerText" fontSize="56" color="#5CB0DE" alignment="MiddleCenter"></Text>\n'
    '</Panel>\n'
    # The buttons under TTS's own toolbar at the top left (Yavuz, 2026-10-13: few buttons, and not over the toolbar).
    '<Button id="kbStart" rectAlignment="UpperLeft" offsetXY="8 -410" width="150" height="34" fontSize="15" color="#1C4668" textColor="#ECF0F2" onClick="startGame">START GAME</Button>\n'
    '<Button id="kbReset" rectAlignment="UpperLeft" offsetXY="8 -450" width="150" height="34" fontSize="15" color="#2D3238" textColor="#ECF0F2" onClick="resetGame">RESET TABLE</Button>\n'
    # ROLL DICE rolls the clicking player's own 4 dice (Yavuz, 2026-10-26: "4 zarın birden rollanması lazım").
    # Pressed all game long, so it is bigger, gold, and kept apart from the two buttons that clear the table.
    # ROUND 2 and END GAME jump the timer (Yavuz, 2026-11-04), under ROLL DICE and smaller, so nobody presses them by mistake.
    # ROLL 3 DICE: the last player done in a cycle rolls 3 (Yavuz, 2026-11-04), right under ROLL DICE.
    '<Button id="kbRoll3" rectAlignment="UpperLeft" offsetXY="8 -574" width="150" height="30" fontSize="15" fontStyle="Bold" color="#3A6F8E" textColor="#ECF0F2" onClick="rollThree">ROLL 3 DICE</Button>\n'
    '<Button id="kbSkip" rectAlignment="UpperLeft" offsetXY="8 -630" width="150" height="30" fontSize="14" color="#2D3238" textColor="#E28C24" onClick="skipToRound2">ROUND 2</Button>\n'
    '<Button id="kbEnd" rectAlignment="UpperLeft" offsetXY="8 -666" width="150" height="30" fontSize="14" color="#2D3238" textColor="#E28C24" onClick="endGameNow">END GAME</Button>\n'
    '<Button id="kbRoll" rectAlignment="UpperLeft" offsetXY="8 -520" width="150" height="48" fontSize="19" fontStyle="Bold" color="#5CB0DE" textColor="#181C22" onClick="rollDice">ROLL DICE</Button>\n'
)

now = time.localtime()
save_json = {
    "SaveName": SAVE_NAME, "EpochTime": int(time.time()), "Date": time.strftime("%m/%d/%Y %I:%M:%S %p", now),
    "VersionNumber": "v14.2.2", "GameMode": "NULLWAKE", "Tags": [], "Gravity": 0.5,
    "PlayArea": 0.5, "Table": "Table_RPG", "Sky": "Sky_Regal",
    "Note": "",
    "Hands": {"Enable": True, "DisableUnused": False, "Hiding": 0},
    "LuaScript": LUA, "LuaScriptState": "", "XmlUI": XML, "SnapPoints": [], "ObjectStates": objs,
}
(OUT / f"{SAVE_NAME}.json").write_text(json.dumps(save_json, indent=1, ensure_ascii=False))
shutil.copy(OUT / f"{SAVE_NAME}.json", SAVES / f"{SAVE_NAME}.json")
print(f"{len(objs)} objects: decks of {len(room_cards)} rooms, {len(TOKEN_IDS)} tokens, "
      f"{len(event_cards)} event cards, {len(alien_cards)} alien and {len(haz_cards)} event tokens")
print(f"drawings from {ART_DIR}: {len(set(ART_USED))} of {len(ART_NO)}")
print(f"images: {len(HASHED)}, {len(LOCAL)} of them local only (not on Steam Cloud){': ' + ', '.join(sorted(LOCAL)) if 0 < len(LOCAL) < 8 else ''}")
print(f"save → {SAVES / (SAVE_NAME + '.json')}")
