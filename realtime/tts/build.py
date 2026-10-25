"""Builds the Tabletop Simulator save for the real-time Kingbound (rules: the team's
"KINGBOUND — Detailed Game Design Document" of 2026-10-18 and its update of 2026-10-25, which adds the
teacher's feedback and three changes: §12 Safe Room, §13 Trap Tiles, §14 Prank Cards; the rules for
players are in ../../README.md).

Everything the document lists (§2, §12-§14): room cards with the Safe Room in the middle and trap
rooms in the deck, character tokens, 4 symbol dice per player, the Loot Deck with its Prank Cards,
monster and treasure tokens, and a 10-minute timer (on screen, Global UI). The document leaves counts,
points and card texts open; our choices and their reasons are in the constants below.
Images are drawn with Pillow and copied into TTS's Mods/ folder (macOS doesn't let TTS read
~/Desktop); their names carry a content hash so TTS never shows a stale cached image.
Run: python3 build.py
"""
import hashlib, json, math, random, shutil, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

VERSION = "1.1"   # v1.0 (Yavuz, 2026-10-26: "oyun tamamlandı"), v1.1: each mat on its own side of the table
ROOT = Path(__file__).parent
OUT = ROOT / "output"
ASSETS = Path.home() / "Library/Tabletop Simulator/Mods/kingbound-realtime"
SAVES = Path.home() / "Library/Tabletop Simulator/Saves/prototipler"
SAVE_NAME = "KINGBOUND-realtime"
DICE_TEMPLATE = Path.home() / "Library/Application Support/Steam/steamapps/common/Tabletop Simulator/Modding/Dice Templates/D6.png"
for p in (OUT, ASSETS, SAVES):
    p.mkdir(parents=True, exist_ok=True)

FONT = "/System/Library/Fonts/Supplemental/"
def f(name, size): return ImageFont.truetype(FONT + name, size)
BLACK, BOLD, REG = "Georgia Bold.ttf", "Arial Bold.ttf", "Arial.ttf"

# Same palette as the turn-based Kingbound (narrative document): parchment, ink, antique gold.
PAPER, INK, CREAM, GOLD = (236, 223, 193), (30, 25, 21), (244, 232, 204), (181, 145, 66)
# The three symbols of §5. Each has its own colour so they read from far away on video.
SYM_COL = {"move": (44, 120, 70), "attack": (160, 46, 36), "magic": (60, 84, 160)}
SYM_NAME = {"move": "MOVEMENT", "attack": "ATTACK", "magic": "MAGIC"}
STONE, WALL, FLOOR = (92, 86, 78), (44, 40, 36), (150, 140, 122)
TRAP_COL, PRANK_COL, SAFE_COL = (204, 112, 26), (112, 48, 128), (92, 44, 122)
STEEL = (204, 204, 210)
# 3-5 players (§1): five seats. The mats show only the seat colour: the team members' names came off when the
# save went on the Steam Workshop (Yavuz, 2026-10-25: "kartlardan isimleri kaldır").
COLORS = ["Red", "Yellow", "Green", "Blue", "Purple"]
RGB = {"Red": (0.856, 0.1, 0.094), "Yellow": (0.905, 0.898, 0.172), "Green": (0.192, 0.701, 0.168),
       "Blue": (0.118, 0.53, 1.0), "Purple": (0.627, 0.125, 0.941)}
PIX = {"Red": (200, 60, 52), "Yellow": (214, 190, 40), "Green": (64, 160, 60), "Blue": (52, 120, 210), "Purple": (140, 64, 196)}

# ------------------------------------------------------------------ game content (our choices where the document is open)
# Dice (§5): a D6 with Movement, Attack and Magic; the document names no other face, so two of each.
DIE_FACES = {1: "move", 2: "move", 3: "attack", 4: "attack", 5: "magic", 6: "magic"}
# Monsters (§6): weak / medium / strong need 2 / 3 / 4 Attack (§5 table). Points are ours: a strong one
# is worth more than two weak ones, so "fight the strong one or take easy rewards" (§10) is a real choice.
# The update's feedback says "reduce fighting": 7 monster rooms instead of 11 and 9 tokens instead of 13.
MONSTERS = {"weak": (2, 1, 4), "medium": (3, 2, 3), "strong": (4, 4, 2)}      # attack, points, count
# Treasures (§9): 2 Magic. Common = few points, rare = more, special = a Loot Card (+1 point).
# The feedback says "not enough loot cards": 6 special treasures instead of 3, so more Loot comes out.
TREASURES = {"common": (1, 3), "rare": (3, 3), "special": (1, 6)}             # points, count
# Room tiles (§2.1, §13): the Safe Room in the middle, then empty, monster, treasure and trap rooms.
ROOM_COUNT = {"empty": 6, "monster": 7, "treasure": 9, "trap": 6}
# Trap tiles (§13): the document's three traps, two of each. A trap goes off every time a character
# walks into its room (revealing it doesn't: the room is only placed). The tile shows the short rule.
# Pressure Plate: §13 says "losing a turn", and the game has no turns, so the player stops for a
# 10-count. Collapsing Passage: blocking one passage could shut a player inside a room with no way
# out, so the whole room caves in once its visitor has left it; the routes through it are gone.
TRAPS = {"spike": ("SPIKE PIT", "Lose 1 unsecured treasure",
                   "Trap. When you walk in: lose 1 unsecured treasure (you choose which). It is out of the game."),
         "plate": ("PRESSURE PLATE", "Stop and count to 10",
                   "Trap. When you walk in: put your dice down and count to 10 out loud, then go on."),
         "collapse": ("COLLAPSING PASSAGE", "Caves in when you leave",
                      "Trap. When you walk out of this room, it caves in: put rubble on it. Nobody can walk in again.")}
TRAP_COUNT = 2
# Loot Deck (§2.4): weapons, equipment and consumables. "unless a room or item effect changes this
# requirement" (§9) is what they do here. Prank Cards (§14) join the deck: the document's four, two of
# each, so the deck grows from 10 to 18 cards (the feedback: "more loot cards").
LOOT = [("L1", "Iron Sword", "WEAPON", "Counts as 1 Attack symbol in every fight.", 2),
        ("L2", "Swift Boots", "EQUIPMENT", "Counts as 1 Movement symbol when you move or reveal a room.", 2),
        ("L3", "Rune Amulet", "EQUIPMENT", "Counts as 1 Magic symbol when you collect a treasure.", 2),
        ("L4", "Lucky Charm", "CONSUMABLE", "Use once: turn one of your dice to any symbol. Then discard.", 2),
        ("L5", "Fire Bomb", "CONSUMABLE", "Use once: defeat a weak monster without rolling. Then discard.", 2),
        ("P1", "Sticky Fingers", "PRANK", "Steal 1 unsecured treasure from another player. Put it in your CARRIED box.", 2),
        ("P2", "Wrong Turn", "PRANK", "Move another player's character into a room connected to theirs. A trap there goes off.", 2),
        ("P3", "Monster Magnet", "PRANK", "The monster nearest to another player moves into their room. They can't leave until they beat it.", 2),
        ("P4", "Trap Surprise", "PRANK", "Another player gets a Spike Pit or a Pressure Plate (you choose) where they stand.", 2)]
# §14 doesn't say when a Prank is played; real time, so any time. The Safe Room is safe (§12): no
# Prank reaches a player standing in it.
PRANK_RULE = "Play any time, then discard. Not on a player in the Safe Room."

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


def crown(d, cx, cy, r, fill, outline=INK):
    """The Safe Room's crown (the update's picture, p. 7)."""
    pts = [(cx - r, cy + r * 0.45), (cx - r, cy - r * 0.35), (cx - r * 0.5, cy + r * 0.05), (cx, cy - r * 0.7),
           (cx + r * 0.5, cy + r * 0.05), (cx + r, cy - r * 0.35), (cx + r, cy + r * 0.45)]
    d.polygon(pts, fill=fill, outline=outline, width=4)
    d.rectangle((cx - r, cy + r * 0.45, cx + r, cy + r * 0.7), fill=fill, outline=outline, width=4)
    for x, y in ((cx - r, cy - r * 0.35), (cx, cy - r * 0.7), (cx + r, cy - r * 0.35)):
        d.ellipse((x - r * 0.12, y - r * 0.12, x + r * 0.12, y + r * 0.12), fill=fill, outline=outline, width=3)


def chest(d, cx, cy, r):
    d.rounded_rectangle((cx - r, cy - r * 0.64, cx + r, cy + r * 0.64), int(r * 0.14), fill=(120, 70, 30), outline=INK, width=5)
    d.rectangle((cx - r, cy - r * 0.27, cx + r, cy - r * 0.13), fill=INK)
    d.rectangle((cx - r * 0.14, cy - r * 0.34, cx + r * 0.14, cy + r * 0.14), fill=GOLD)


def arrowhead(d, x, y, angle, size, fill):
    """A triangle pointing along angle (radians), its tip at (x, y)."""
    d.polygon([(x, y), (x - size * math.cos(angle - 0.5), y - size * math.sin(angle - 0.5)),
               (x - size * math.cos(angle + 0.5), y - size * math.sin(angle + 0.5))], fill=fill)


def spikes(d, cx, cy, r):
    """Spike Pit: steel spikes in a dark pit."""
    d.ellipse((cx - r, cy + r * 0.2, cx + r, cy + r * 0.8), fill=(40, 34, 30), outline=INK, width=3)
    for k in range(5):
        x = cx - r * 0.66 + k * r * 0.33
        d.polygon([(x - r * 0.15, cy + r * 0.52), (x, cy - r * 0.62), (x + r * 0.15, cy + r * 0.52)], fill=STEEL, outline=INK)


def plate(d, cx, cy, r):
    """Pressure Plate: a stone plate with an arrow pressing it."""
    d.rectangle((cx - r, cy - r * 0.05, cx + r, cy + r * 0.6), fill=(110, 104, 96), outline=INK, width=5)
    d.rectangle((cx - r * 0.72, cy + r * 0.08, cx + r * 0.72, cy + r * 0.45), fill=(156, 150, 140), outline=INK, width=3)
    d.line((cx, cy - r * 0.95, cx, cy - r * 0.35), fill=INK, width=int(r * 0.2))
    arrowhead(d, cx, cy - r * 0.12, math.pi / 2, r * 0.42, INK)


def rubble(d, cx, cy, r):
    """Collapsing Passage: fallen stones."""
    for dx, dy, s in ((-0.62, 0.32, 0.34), (0.05, 0.4, 0.4), (0.62, 0.3, 0.32), (-0.3, -0.22, 0.34), (0.34, -0.26, 0.3), (0.0, -0.72, 0.22)):
        x, y, rr = cx + dx * r, cy + dy * r, s * r
        d.polygon([(x - rr, y), (x - rr * 0.5, y - rr * 0.85), (x + rr * 0.6, y - rr * 0.8), (x + rr, y + rr * 0.1),
                   (x + rr * 0.45, y + rr * 0.8), (x - rr * 0.6, y + rr * 0.72)], fill=(132, 124, 114), outline=INK)


def trap_art(d, kind, cx, cy, r):
    {"spike": spikes, "plate": plate, "collapse": rubble}[kind](d, cx, cy, r)


def uturn(d, cx, cy, r, fill):
    """Wrong Turn: a U-turn arrow."""
    w = int(r * 0.24)
    d.arc((cx - r * 0.6, cy - r * 0.75, cx + r * 0.6, cy + r * 0.45), 180, 360, fill=fill, width=w)
    d.line((cx - r * 0.6 + w / 2, cy - r * 0.15, cx - r * 0.6 + w / 2, cy + r * 0.85), fill=fill, width=w)
    d.line((cx + r * 0.6 - w / 2, cy - r * 0.15, cx + r * 0.6 - w / 2, cy + r * 0.35), fill=fill, width=w)
    arrowhead(d, cx + r * 0.6 - w / 2, cy + r * 0.95, math.pi / 2, r * 0.62, fill)


def magnet(d, cx, cy, r):
    """Monster Magnet: a horseshoe magnet."""
    red, w = SYM_COL["attack"], r * 0.38
    d.pieslice((cx - r, cy - r, cx + r, cy + r), 180, 360, fill=red, outline=INK, width=3)
    d.pieslice((cx - r + w, cy - r + w, cx + r - w, cy + r - w), 180, 360, fill=PAPER, outline=INK, width=3)
    for x0 in (cx - r, cx + r - w):
        d.rectangle((x0, cy, x0 + w, cy + r * 0.62), fill=red, outline=INK, width=3)
        d.rectangle((x0, cy + r * 0.62, x0 + w, cy + r * 0.95), fill=STEEL, outline=INK, width=3)
    d.line((cx - r + w, cy, cx + r - w, cy), fill=PAPER, width=5)


def save(im, fn):
    im.save(OUT / fn)
    return fn


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
        icon(d, kind, cx, cy, 210)
    return save(im, "dice.png")


# ------------------------------------------------------------------ room tiles (§2.1, §12, §13)
TILE_PX = 512
DOOR = {"N": (196, 0, 316, 64), "S": (196, 448, 316, 512), "W": (0, 196, 64, 316), "E": (448, 196, 512, 316)}


def room_img(kind, doors, trap=None):
    im = Image.new("RGB", (TILE_PX, TILE_PX), WALL)
    d = ImageDraw.Draw(im)
    d.rectangle((40, 40, 472, 472), fill=FLOOR)
    for x in range(40, 472, 72):   # flagstones
        d.line((x, 40, x, 472), fill=(132, 122, 106), width=3)
    for y in range(40, 472, 72):
        d.line((40, y, 472, y), fill=(132, 122, 106), width=3)
    for s in doors:   # passages: open floor through the wall to the tile's edge
        d.rectangle(DOOR[s], fill=FLOOR)
    if kind == "safe":
        # §12: the starting room is the Safe Room, where treasure is secured.
        d.rounded_rectangle((92, 112, 420, 400), 18, fill=SAFE_COL, outline=GOLD, width=6)
        crown(d, 256, 190, 62, GOLD)
        d.text((256, 290), "SAFE ROOM", font=fit(d, "SAFE ROOM", BLACK, 54, 300), fill=CREAM, anchor="mm")
        d.text((256, 352), "secure your treasure", font=f(REG, 27), fill=GOLD, anchor="mm")
    elif kind == "monster":
        d.ellipse((136, 136, 376, 376), fill=SYM_COL["attack"], outline=INK, width=6)
        crossed(d, 256, 248, 92, CREAM)
        d.text((256, 420), "MONSTER", font=f(BOLD, 40), fill=INK, anchor="mm")
    elif kind == "treasure":
        d.ellipse((136, 136, 376, 376), fill=GOLD, outline=INK, width=6)
        chest(d, 256, 271, 70)
        d.text((256, 420), "TREASURE", font=f(BOLD, 40), fill=INK, anchor="mm")
    elif kind == "trap":
        name, short, _ = TRAPS[trap]
        d.text((256, 84), "TRAP", font=f(BOLD, 30), fill=(120, 60, 10), anchor="mm")
        d.ellipse((156, 110, 356, 310), fill=TRAP_COL, outline=INK, width=6)
        trap_art(d, trap, 256, 210, 72)
        d.text((256, 360), name, font=fit(d, name, BOLD, 40, 410), fill=INK, anchor="mm")
        d.text((256, 414), short, font=fit(d, short, BOLD, 30, 410), fill=(120, 60, 10), anchor="mm")
    else:
        d.text((256, 256), "EMPTY ROOM", font=f(BOLD, 38), fill=(96, 88, 76), anchor="mm")
    fn = f"room-{kind}{'-' + trap if trap else ''}-{''.join(sorted(doors))}.png"
    return save(im, fn)


def room_back():
    im = Image.new("RGB", (TILE_PX, TILE_PX), (52, 40, 34))
    d = ImageDraw.Draw(im)
    d.rectangle((14, 14, 498, 498), outline=GOLD, width=8)
    d.text((256, 226), "KINGBOUND", font=f(BLACK, 54), fill=GOLD, anchor="mm")
    d.text((256, 290), "unexplored room", font=f(REG, 30), fill=CREAM, anchor="mm")
    return save(im, "room-back.png")


# ------------------------------------------------------------------ monster, treasure and rubble tokens
TOK = 360


def token_front(fn, ring, title, need_kind, need_n, pts_text):
    im = Image.new("RGB", (TOK, TOK), ring)
    d = ImageDraw.Draw(im)
    d.ellipse((14, 14, TOK - 14, TOK - 14), fill=PAPER, outline=INK, width=5)
    d.text((TOK / 2, 76), title, font=f(BLACK, 40), fill=ring, anchor="mm")
    sym_row(d, need_kind, need_n, TOK / 2, 160, 30 if need_n <= 3 else 26)
    d.text((TOK / 2, 252), pts_text, font=f(BOLD, 40 if len(pts_text) < 10 else 30), fill=INK, anchor="mm")
    return save(im, fn)


def token_back(fn, ring, text):
    im = Image.new("RGB", (TOK, TOK), ring)
    d = ImageDraw.Draw(im)
    d.ellipse((14, 14, TOK - 14, TOK - 14), outline=CREAM, width=6)
    d.text((TOK / 2, TOK / 2), text, font=f(BLACK, 46), fill=CREAM, anchor="mm")
    return save(im, fn)


def rubble_img():
    """Goes on a Collapsing Passage room that has caved in (§13)."""
    im = Image.new("RGB", (TOK, TOK), (90, 84, 76))
    d = ImageDraw.Draw(im)
    d.ellipse((14, 14, TOK - 14, TOK - 14), fill=(168, 160, 148), outline=INK, width=5)
    rubble(d, TOK / 2, 150, 96)
    d.text((TOK / 2, 268), "CAVED IN", font=f(BLACK, 40), fill=INK, anchor="mm")
    return save(im, "rubble.png")


# ------------------------------------------------------------------ Loot cards (§2.4, §14)
CW, CH = 400, 560
LOOT_COLS = 5


def loot_face(cid, name, kind, text):
    im = Image.new("RGB", (CW, CH), PAPER)
    d = ImageDraw.Draw(im)
    col = {"WEAPON": SYM_COL["attack"], "EQUIPMENT": SYM_COL["move"], "CONSUMABLE": (120, 70, 30), "PRANK": PRANK_COL}[kind]
    d.rectangle((0, 0, CW - 1, CH - 1), outline=col, width=12)
    d.rectangle((0, 0, CW, 70), fill=col)
    d.text((CW / 2, 36), "LOOT · " + kind, font=f(BOLD, 26), fill=CREAM, anchor="mm")
    d.text((CW / 2, 116), name, font=fit(d, name, BLACK, 42, CW - 50), fill=INK, anchor="mm")
    k = {"L1": "attack", "L2": "move", "L3": "magic"}.get(cid)
    if kind == "PRANK":
        # Shorter art and text: a Prank also carries its rule at the bottom.
        cy = 214
        if cid == "P1":
            chest(d, CW / 2 - 30, cy + 8, 58)
            d.line((CW / 2 + 40, cy + 8, CW / 2 + 100, cy + 8), fill=PRANK_COL, width=14)
            arrowhead(d, CW / 2 + 128, cy + 8, 0, 44, PRANK_COL)
        elif cid == "P2":
            uturn(d, CW / 2, cy, 76, PRANK_COL)
        elif cid == "P3":
            magnet(d, CW / 2, cy + 12, 74)
        else:
            d.ellipse((CW / 2 - 72, cy - 66, CW / 2 + 72, cy + 78), fill=TRAP_COL, outline=INK, width=5)
            spikes(d, CW / 2, cy + 8, 52)
        para(d, text, 314, 30, CW - 30, size=27, gap=7)
        d.line((40, CH - 104, CW - 40, CH - 104), fill=col, width=3)
        para(d, PRANK_RULE, CH - 92, 34, CW - 34, name=BOLD, size=21, fill=col, gap=6)
    else:
        if k:
            sym_row(d, k, 1, CW / 2, 240, 70)
        elif cid == "L4":
            star(d, CW / 2, 240, 80, GOLD, INK)
        else:
            d.ellipse((CW / 2 - 66, 180, CW / 2 + 66, 312), fill=INK)
            d.line((CW / 2 + 40, 196, CW / 2 + 80, 160), fill=(220, 120, 30), width=10)
        para(d, text, 350, 34, CW - 34, size=30)
        d.text((24, CH - 40), cid, font=f(BOLD, 22), fill=col)
    return im


def loot_sheet():
    ims = [loot_face(c[0], c[1], c[2], c[3]) for c in LOOT]
    rows = math.ceil(len(ims) / LOOT_COLS)
    sheet = Image.new("RGB", (CW * LOOT_COLS, CH * rows), PAPER)
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % LOOT_COLS) * CW, (i // LOOT_COLS) * CH))
    save(sheet, "loot-sheet.png")
    back = Image.new("RGB", (CW, CH), (70, 52, 30))
    d = ImageDraw.Draw(back)
    d.rectangle((16, 16, CW - 16, CH - 16), outline=GOLD, width=8)
    d.text((CW / 2, CH / 2 - 20), "LOOT", font=f(BLACK, 70), fill=GOLD, anchor="mm")
    d.text((CW / 2, CH / 2 + 50), "KINGBOUND", font=f(BOLD, 28), fill=CREAM, anchor="mm")
    save(back, "loot-back.png")
    return rows


# ------------------------------------------------------------------ player mats
# Four boxes: dice, Loot, CARRIED (treasure not secured yet, §12) and POINTS (defeated monsters and
# secured treasure: only this box counts at the end). Above them, what each action needs (§5): the
# players sit on four sides of the table, so each reads the actions on their own mat instead of one
# chart. Pixel spots for the pieces the tutorial places.
MAT_W, MAT_H = 1100, 680
BOX_Y = (180, 660)
MAT_BOX = {"dice": (30, 320, "DICE", ""), "loot": (335, 545, "LOOT", ""),
           "carry": (560, 805, "CARRIED", "treasure, not secured"),
           "points": (820, 1070, "POINTS", "monsters, secured treasure")}
MAT_ACTIONS = [("MOVE / OPEN", "move", 2), ("WEAK", "attack", 2), ("MEDIUM", "attack", 3), ("STRONG", "attack", 4),
               ("TREASURE", "magic", 2), ("SECURE", None, 0)]
DIE_PX = [(105, 375), (245, 375), (105, 555), (245, 555)]
LOOT_PX = (440, 450)
CARRY_PX = [(622, 365), (743, 365), (622, 478), (743, 478), (622, 591), (743, 591)]
POINTS_PX = [(884, 365), (1006, 365), (884, 478), (1006, 478), (884, 591), (1006, 591)]


def mat_img(color):
    im = Image.new("RGB", (MAT_W, MAT_H), PAPER)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, MAT_W - 1, MAT_H - 1), outline=PIX[color], width=16)
    d.rectangle((0, 0, MAT_W, 78), fill=PIX[color])
    light = color in ("Yellow",)
    d.text((MAT_W / 2, 40), color.upper(), font=f(BLACK, 46), fill=INK if light else CREAM, anchor="mm")
    slot = (MAT_W - 60) / len(MAT_ACTIONS)
    for i, (name, kind, n) in enumerate(MAT_ACTIONS):
        cx = 30 + slot * (i + 0.5)
        d.text((cx, 106), name, font=f(BOLD, 21), fill=INK, anchor="mm")
        if kind:
            sym_row(d, kind, n, cx, 143, 14)
        else:
            crown(d, cx - 52, 141, 13, GOLD)
            d.text((cx - 32, 143), "in the Safe Room", font=f(REG, 17), fill=INK, anchor="lm")
        if i:
            d.line((30 + slot * i, 92, 30 + slot * i, 162), fill=(200, 184, 150), width=2)
    for key, (x0, x1, head, sub) in MAT_BOX.items():
        fill = {"carry": (242, 220, 196), "points": (226, 230, 196)}.get(key)
        d.rounded_rectangle((x0, BOX_Y[0], x1, BOX_Y[1]), 16, fill=fill, outline=(150, 130, 100), width=4)
        d.text(((x0 + x1) / 2, BOX_Y[0] + 28), head, font=f(BOLD, 28), fill=(120, 100, 70), anchor="mm")
        if sub:
            d.text(((x0 + x1) / 2, BOX_Y[0] + 60), sub, font=fit(d, sub, REG, 20, x1 - x0 - 16), fill=(120, 100, 70), anchor="mm")
    return save(im, f"mat-{color.lower()}.png")


def title_img():
    """The name plate: only KINGBOUND (Yavuz, 2026-10-26), in the Safe Room's royal purple and gold."""
    w, h = 1400, 360
    deep, royal, bronze = (26, 14, 34), (70, 34, 92), (110, 78, 30)
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):                       # purple, lighter in the middle, dark at the edges
        k = 1 - abs(y - h * 0.45) / (h * 0.55)
        row = tuple(int(deep[i] + (royal[i] - deep[i]) * max(0.0, k)) for i in range(3))
        for x in range(w):
            px[x, y] = row
    d = ImageDraw.Draw(im)
    # Two gold frames and a diamond in each corner.
    d.rectangle((14, 14, w - 15, h - 15), outline=GOLD, width=8)
    d.rectangle((34, 34, w - 35, h - 35), outline=bronze, width=3)
    for cx, cy in ((34, 34), (w - 35, 34), (34, h - 35), (w - 35, h - 35)):
        d.polygon([(cx, cy - 16), (cx + 16, cy), (cx, cy + 16), (cx - 16, cy)], fill=GOLD, outline=bronze)
    crown(d, w / 2, 66, 24, GOLD, bronze)
    # Letters spaced out, with a soft shadow under them.
    font, track = f(BLACK, 150), 18
    widths = [d.textlength(ch, font=font) for ch in "KINGBOUND"]
    x0, base = (w - (sum(widths) + track * 8)) / 2, 236
    shadow = Image.new("L", (w, h), 0)
    sd = ImageDraw.Draw(shadow)
    x = x0
    for ch, cw in zip("KINGBOUND", widths):
        sd.text((x + 6, base + 8), ch, font=font, fill=200, anchor="ls")
        x += cw + track
    im.paste((8, 4, 12), (0, 0), shadow.filter(ImageFilter.GaussianBlur(6)))
    x = x0
    for ch, cw in zip("KINGBOUND", widths):
        d.text((x, base), ch, font=font, fill=GOLD, anchor="ls", stroke_width=3, stroke_fill=bronze)
        x += cw + track
    # A line under the name with a diamond in the middle.
    for x1, x2 in ((x0, w / 2 - 22), (w / 2 + 22, x0 + sum(widths) + track * 8)):
        d.line((x1, 282, x2, 282), fill=GOLD, width=3)
    d.polygon([(w / 2, 270), (w / 2 + 12, 282), (w / 2, 294), (w / 2 - 12, 282)], fill=GOLD, outline=bronze)
    return save(im, "title.png")


# ------------------------------------------------------------------ draw everything
for old in OUT.glob("*.png"):
    old.unlink()
dice_img()
ROOM_BACK = room_back()
LOOT_ROWS = loot_sheet()
for c in COLORS:
    mat_img(c)
title_img()
RUBBLE = rubble_img()
TOKEN_IMG = {}
for k, (atk, pts, n) in MONSTERS.items():
    TOKEN_IMG[("monster", k)] = token_front(f"mon-{k}.png", SYM_COL["attack"], k.upper(), "attack", atk,
                                            f"{pts} POINT{'S' if pts > 1 else ''}")
for k, (pts, n) in TREASURES.items():
    TOKEN_IMG[("treasure", k)] = token_front(f"tre-{k}.png", GOLD, k.upper(), "magic", 2,
                                             "1 POINT + LOOT" if k == "special" else f"{pts} POINT{'S' if pts > 1 else ''}")
# Symbol icons beside the part's name on screen (what the step costs), same look as the dice faces.
for k, fn in (("move", "icon-move.png"), ("attack", "icon-attack.png"), ("magic", "icon-magic.png")):
    im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((4, 4, 124, 124), fill=SYM_COL[k], outline=CREAM, width=6)
    icon(d, k, 64, 64, 40)
    save(im, fn)
MON_BACK = token_back("mon-back.png", SYM_COL["attack"], "MONSTER")
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
# The rest of the stack (§3 step 3): random rooms with random passages, up to ROOM_COUNT. Trap rooms
# always have at least two passages, so they sit on routes (§13: "plan their routes carefully").
left = dict(ROOM_COUNT)
for _, kind, _ in P.ROOMS:
    left[kind] -= 1
assert all(v >= 0 for v in left.values()), left
assert left["trap"] == len(TRAPS) * TRAP_COUNT, "the tutorial's plan has no trap rooms yet"
SPARE = []
for kind, n in left.items():
    traps = [t for t in TRAPS for _ in range(TRAP_COUNT)] if kind == "trap" else [None] * n
    for trap in traps:
        ds = [s for s in "NSEW" if rng.random() < 0.6]
        if len(ds) < 2:
            ds = ["N", "S"] if trap or not ds else ds
        SPARE.append((room_img(kind, ds, trap), trap))
rng.shuffle(SPARE)

# Rooms, tokens and rubble are cards in decks, so players draw from a deck instead of a tall pile of
# loose tiles (Yavuz, 2026-10-25: "deste oluşturabilirsin"). The room deck, top card first: the
# tutorial's rooms in the order it reveals them, then the spares. START GAME shuffles every deck.
ROOM_CARDS = ([{"fn": ROOM_IMG[c], "kind": k, "trap": None, "notes": f"{c[0]},{c[1]}"} for c, k, _ in P.ROOMS]
              + [{"fn": fn, "kind": "trap" if trap else fn.split("-")[1], "trap": trap, "notes": f"spare{i}"}
                 for i, (fn, trap) in enumerate(SPARE)])
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
RUBBLE_SHEET = card_sheet([RUBBLE, RUBBLE], "rubble-sheet.png", 2)    # one face; a sheet has at least two cells

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
DUNGEON = (0.0, 0.0)  # the Safe Room, in the middle of the table
ROOM_S = 1.8
MAT_SIZE = (10.0, round(10.0 * MAT_H / MAT_W, 4))        # width, depth in table units
MAT_S = MAT_SIZE[1] / 2                                    # Stretch on: depth = 2 x scale
EDGE_Z, EDGE_X = round(18.2 - MAT_SIZE[1] / 2, 3), round(28.2 - MAT_SIZE[1] / 2, 3)   # mats against the felt's edge
MATS = {"Red": (7.5, -EDGE_Z, 180), "Purple": (-7.5, -EDGE_Z, 180), "Green": (0.0, EDGE_Z, 0),
        "Yellow": (-EDGE_X, 0.0, 270), "Blue": (EDGE_X, 0.0, 90)}


def mat_world(color, px, py):
    """A point of a mat's image (pixels) on the table. The image's right and down turn with the mat."""
    cx, cz, rot = MATS[color]
    u, v = (px / MAT_W - 0.5) * MAT_SIZE[0], (py / MAT_H - 0.5) * MAT_SIZE[1]
    t = math.radians(rot)
    return round(cx - u * math.cos(t) + v * math.sin(t), 3), round(cz + u * math.sin(t) + v * math.cos(t), 3)


# The shared decks wait in the corners, clear of the mats and of the dungeon growing from the middle.
STACK = (-13.5, 15.2)  # face-down room deck
RUBBLE_POS = (-18.0, 15.6)
MON_PILE, TRE_PILE = (11.5, 15.6), (14.6, 15.6)
LOOT_POS = (18.6, 15.2)
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
objs.append(tile("title.png", tr(*TITLE_POS, s=1.2, y=1.02), "Kingbound", thick=0.05, Tags=["title"]))
objs.append(tile(ROOM_IMG[(0, 0)], tr(*cell_pos((0, 0)), s=ROOM_S, y=0.98), "Safe Room", back=ROOM_BACK,
                 desc="Start here. Bring your CARRIED treasure back here to secure it: move it to POINTS, no dice.",
                 Tooltip=True, Tags=["room", "saferoom"], GMNotes="0,0"))

# Cards and decks. A deck lies face down; each card carries its identity in GM Notes, so the tutorial
# takes the card its plan needs and RESET TABLE sends every card back to its own deck. A face-down card
# hides its name and text (HideWhenFaceDown), so hovering over a deck gives nothing away.
ROOM_KEY, MON_KEY, TRE_KEY, RUBBLE_KEY, LOOT_KEY = 2, 3, 4, 5, 1
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


# Room deck (§2.1, §13). Square corners, so rooms meet edge to edge.
ROOM_DECK = cdeck("room-sheet.png", ROOM_BACK, ROOM_SHEET, "square")
ROOM_TEXT = {"empty": "Nothing to fight or take.", "monster": "Turn a monster token face up on it.",
             "treasure": "Turn a treasure token face up on it."}
room_cards = []
for i, r in enumerate(ROOM_CARDS):
    if r["trap"]:
        nick, desc = TRAPS[r["trap"]][0].title(), TRAPS[r["trap"]][2]
    else:
        nick, desc = f"{r['kind'].capitalize()} room", ROOM_TEXT[r["kind"]]
    room_cards.append(card(nick, desc, ROOM_KEY, ROOM_DECK, i, r["notes"], ROOM_CARD_S))
objs.append(deck("Rooms", STACK, ROOM_KEY, ROOM_DECK, room_cards, "roomdeck", ROOM_CARD_S))

# Monster and treasure tokens (§3 step 4): round cards in two decks.
TOKEN_IDS = []
for cat, table, key, back, sheet, pos, tag in (("monster", MONSTERS, MON_KEY, MON_BACK, MON_SHEET, MON_PILE, "mondeck"),
                                               ("treasure", TREASURES, TRE_KEY, TRE_BACK, TRE_SHEET, TRE_PILE, "tredeck")):
    cd = cdeck(f"{cat[:3]}-sheet.png", back, sheet, "circle")
    cards = []
    for j, (k, v) in enumerate(table.items()):
        n = v[2] if cat == "monster" else v[1]
        if cat == "monster":
            desc = f"Needs {v[0]} Attack. {v[1]} point{'s' if v[1] > 1 else ''}."
        else:
            gain = "1 point and a Loot card" if k == "special" else f"{v[0]} point{'s' if v[0] > 1 else ''}"
            desc = f"Needs 2 Magic. {gain}. Counts once secured in the Safe Room."
        for i in range(n):
            tid = f"{cat[0]}-{k}-{i + 1}"
            TOKEN_IDS.append(tid)
            cards.append(card(f"{k.capitalize()} {cat}", desc, key, cd, j, tid, TOKEN_CARD_S))
    random.Random(11).shuffle(cards)
    objs.append(deck(f"{cat.capitalize()} tokens", pos, key, cd, cards, tag, TOKEN_CARD_S))
    objs[-1]["Tags"].append("token")       # the tutorial makes both token decks glow

# Rubble (§13): one round card for each Collapsing Passage room.
RUBBLE_DECK = cdeck("rubble-sheet.png", RUBBLE, RUBBLE_SHEET, "circle")
rubble_cards = [card("Rubble", "Put it on a Collapsing Passage room after its visitor walks out: nobody can walk in again.",
                     RUBBLE_KEY, RUBBLE_DECK, 0, f"rubble-{i + 1}", TOKEN_CARD_S, hide=False) for i in range(TRAP_COUNT)]
objs.append(deck("Rubble", RUBBLE_POS, RUBBLE_KEY, RUBBLE_DECK, rubble_cards, "rubbledeck", TOKEN_CARD_S))

# Loot Deck (§2.4, §14), face down.
LOOT_DECK = cdeck("loot-sheet.png", "loot-back.png", (LOOT_COLS, LOOT_ROWS), "rounded")
loot_cards = []
for i, (cid, name, kind, text, n) in enumerate(LOOT):
    desc = f"{kind}. {text}" + (f" {PRANK_RULE}" if kind == "PRANK" else "")
    loot_cards += [card(name, desc, LOOT_KEY, LOOT_DECK, i, cid, 0.75) for _ in range(n)]
random.Random(3).shuffle(loot_cards)
objs.append(deck("Loot Deck", LOOT_POS, LOOT_KEY, LOOT_DECK, loot_cards, "lootdeck", 0.75))

# Player mats, pawns (character tokens, §2.2) and 4 dice each (§2.3).
DICE_IMG = url("dice.png")
for c in COLORS:
    mx, mz, rot = MATS[c]
    objs.append(tile(f"mat-{c.lower()}.png", tr(mx, mz, rot_y=rot, s=MAT_S, y=1.02), f"{c} mat", thick=0.06,
                     Tags=["mat"], GMNotes=c))
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
          "decks": {"room": "roomdeck", "monster": "mondeck", "treasure": "tredeck", "rubble": "rubbledeck", "loot": "lootdeck"},
          "deck_pos": {"room": STACK, "monster": MON_PILE, "treasure": TRE_PILE, "rubble": RUBBLE_POS, "loot": LOOT_POS},
          "deck_s": {"room": ROOM_CARD_S, "monster": TOKEN_CARD_S, "treasure": TOKEN_CARD_S, "rubble": TOKEN_CARD_S, "loot": 0.75},
          "mat_tok_s": MAT_TOKEN_S,
          "colors": COLORS, "mats": MATS, "mat_size": MAT_SIZE, "mat_px": (MAT_W, MAT_H),
          "die_px": DIE_PX, "loot_px": LOOT_PX, "carry_px": CARRY_PX, "points_px": POINTS_PX,
          "pawn_home": PAWN_HOME, "faces": DIE_FACES, "game_secs": 600,
          "points": {**{f"m-{k}": v[1] for k, v in MONSTERS.items()}, **{f"t-{k}": v[0] for k, v in TREASURES.items()}}}
LUA = (ROOT / "global.lua").read_text().replace("__VERSION__", VERSION).replace("__LAYOUT__", json.dumps(LAYOUT))

XML = (
    # The 10-minute timer (§2.5, §10), top right.
    '<Panel id="kbTimer" active="false" rectAlignment="UpperRight" offsetXY="-24 -78" width="300" height="104" color="#000000C8">\n'
    '  <Text id="kbTimerLabel" rectAlignment="UpperCenter" offsetXY="0 -4" height="26" fontSize="19" color="#D4AF4B" alignment="MiddleCenter">TIME LEFT</Text>\n'
    '  <Text id="kbTimerText" rectAlignment="LowerCenter" offsetXY="0 2" height="76" fontSize="62" color="#F5ECD7" alignment="MiddleCenter">10:00</Text>\n'
    '</Panel>\n'
    # The name of the current part, bottom centre (no sentences: the team explains it while presenting).
    # Up to 4 symbol icons follow the name: what the step costs (2 Movement, 3 Attack ...).
    # Small (Yavuz, 2026-10-19: "make the texts at the bottom smaller").
    '<Panel id="kbCaption" active="false" rectAlignment="LowerCenter" offsetXY="0 22" width="400" height="56" color="#000000DC">\n'
    '  <HorizontalLayout childAlignment="MiddleCenter" childForceExpandWidth="false" childForceExpandHeight="false" spacing="8" padding="16 16 6 6">\n'
    '    <Text id="kbCaptionHead" preferredWidth="300" preferredHeight="44" fontSize="29" fontStyle="Bold" color="#D4AF4B" alignment="MiddleCenter" horizontalOverflow="Overflow" verticalOverflow="Overflow"></Text>\n'
    + "\n".join(f'    <Image id="kbIcon{i}" active="false" preferredWidth="38" preferredHeight="38"></Image>' for i in range(1, 5))
    + '\n  </HorizontalLayout>\n</Panel>\n'
    # Scores at the end, top centre over the dungeon (the camera is on the mats then).
    f'<Panel id="kbScore" active="false" rectAlignment="UpperCenter" offsetXY="0 -96" width="660" height="{40 + 50 * len(COLORS)}" color="#000000E6">\n'
    '  <VerticalLayout padding="24 24 14 14" spacing="6">\n'
    + "\n".join(f'    <Text id="kbScore{i}" fontSize="34" fontStyle="Bold" color="#F5ECD7" alignment="MiddleLeft"></Text>' for i in range(1, len(COLORS) + 1))
    + '\n  </VerticalLayout>\n</Panel>\n'
    # A big centre banner for "go", "time's up" and the winner.
    '<Panel id="kbBanner" active="false" rectAlignment="MiddleCenter" offsetXY="0 120" width="1000" height="150" color="#000000D2">\n'
    '  <Text id="kbBannerText" fontSize="72" color="#D4AF4B" alignment="MiddleCenter"></Text>\n'
    '</Panel>\n'
    # Two buttons under TTS's own toolbar at the top left (Yavuz, 2026-10-13: few buttons, and not over the toolbar).
    '<Button id="kbStart" rectAlignment="UpperLeft" offsetXY="8 -410" width="150" height="34" fontSize="15" color="#5C2C7A" textColor="#F5ECD7" onClick="startGame">START GAME</Button>\n'
    '<Button id="kbReset" rectAlignment="UpperLeft" offsetXY="8 -450" width="150" height="34" fontSize="15" color="#3C2819" textColor="#F5ECD7" onClick="resetGame">RESET TABLE</Button>\n'
)

now = time.localtime()
save_json = {
    "SaveName": SAVE_NAME, "EpochTime": int(time.time()), "Date": time.strftime("%m/%d/%Y %I:%M:%S %p", now),
    "VersionNumber": "v14.2.2", "GameMode": "Kingbound", "Tags": [], "Gravity": 0.5,
    "PlayArea": 0.5, "Table": "Table_RPG", "Sky": "Sky_Regal",
    "Note": "",
    "Hands": {"Enable": False, "DisableUnused": False, "Hiding": 0},
    "LuaScript": LUA, "LuaScriptState": "", "XmlUI": XML, "SnapPoints": [], "ObjectStates": objs,
}
(OUT / f"{SAVE_NAME}.json").write_text(json.dumps(save_json, indent=1, ensure_ascii=False))
shutil.copy(OUT / f"{SAVE_NAME}.json", SAVES / f"{SAVE_NAME}.json")
print(f"{len(objs)} objects: decks of {len(room_cards)} rooms ({sum(1 for _, t in SPARE if t)} traps), "
      f"{len(TOKEN_IDS)} tokens, {len(rubble_cards)} rubble, {len(loot_cards)} Loot cards")
print(f"images: {len(HASHED)}, {len(LOCAL)} of them local only (not on Steam Cloud){': ' + ', '.join(sorted(LOCAL)) if 0 < len(LOCAL) < 8 else ''}")
print(f"save → {SAVES / (SAVE_NAME + '.json')}")
