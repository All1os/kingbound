"""Builds the Tabletop Simulator save for the Kingbound prototype (rules: ../Kingbound-GDD.md).

One script, the same method as The Limit: text-only card faces drawn with Pillow (no art yet,
GDD §13), card backs, the 49 board tiles, the level track, player boards, tokens and the save JSON
with its Lua. Card data comes from cards.py, which is checked against the GDD's counts.
Images are copied into TTS's Mods/ folder because macOS doesn't let TTS read ~/Desktop (found on
SHOWDOWN, 2026-10-05). Their names there carry a content hash, so TTS never shows a stale cached
image after a rebuild.
Run: python3 build.py
"""
import hashlib, json, math, random, shutil, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

import cards as C
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bots"))
from engine import Game                     # noqa: E402  the bots' rules engine
from play import DEFAULT_SEED, Director, duration  # noqa: E402  turns a bot game into TTS commands

VERSION = "0.1"
ROOT = Path(__file__).parent
OUT = ROOT / "output"
ASSETS = Path.home() / "Library/Tabletop Simulator/Mods/kingbound"
SAVES = Path.home() / "Library/Tabletop Simulator/Saves/prototipler"  # Yavuz keeps the prototype saves here
SAVE_NAME = "KINGBOUND-prototype"
BOARD_SEED = 2026  # the board the save opens with; BUILD BOARD (or the bots) lay out a new one
OUT.mkdir(exist_ok=True)
ASSETS.mkdir(parents=True, exist_ok=True)
SAVES.mkdir(parents=True, exist_ok=True)

FONT = "/System/Library/Fonts/Supplemental/"
def f(name, size): return ImageFont.truetype(FONT + name, size)
BLACK, BOLD, REG, ITAL = "Arial Black.ttf", "Arial Bold.ttf", "Arial.ttf", "Arial Italic.ttf"

PAPER, INK, CREAM = (245, 240, 228), (25, 22, 20), (245, 236, 215)
GOLD = (212, 175, 75)
TYPE_COL = {"STR": (178, 40, 34), "AGI": (36, 125, 62), "WIS": (40, 84, 172)}    # GDD §15.2: STR red, AGI green, WIS blue
TIER_COL = {1: (150, 186, 112), 2: (84, 124, 70), 3: (40, 66, 42)}               # light / medium / dark by tier and ring
TIER_INK = {1: INK, 2: CREAM, 3: CREAM}
CHAMP_COL, LOOT_COL, OBJ_COL, CHAR_COL = (92, 44, 122), (150, 104, 40), (30, 30, 30), (38, 54, 86)
KIND_COL = {"boost": (178, 92, 22), "sabotage": (122, 30, 62), "signature": (36, 98, 120)}
TOWN_COL = {"Merchant": (205, 165, 60), "Barracks": (150, 60, 45), "Healer": (236, 236, 240),
            "Camp": (214, 118, 48), "Castle": (92, 44, 122)}
ROMAN = {1: "I", 2: "II", 3: "III"}


# ------------------------------------------------------------------ drawing helpers
def wrap(d, text, font, width):
    out = []
    for para in text.split("\n"):
        cur = ""
        for w in para.split():
            t = (cur + " " + w).strip()
            if d.textlength(t, font=font) <= width: cur = t
            else: out.append(cur); cur = w
        out.append(cur)
    return out


def fit(d, text, name, size, width, low=16):
    while size > low and d.textlength(text, font=f(name, size)) > width: size -= 2
    return f(name, size)


def para(d, text, top, bottom, x0, x1, name=REG, size=32, fill=INK, low=16, align="center"):
    """Wraps text into the box (top..bottom, x0..x1), shrinking the font until it fits."""
    while True:
        font = f(name, size)
        lines = wrap(d, text, font, x1 - x0)
        if top + len(lines) * (size + 7) <= bottom or size <= low: break
        size -= 2
    y = top
    for ln in lines:
        if align == "center": d.text(((x0 + x1) / 2, y), ln, font=font, fill=fill, anchor="ma")
        else: d.text((x0, y), ln, font=font, fill=fill)
        y += size + 7
    return y


# ------------------------------------------------------------------ card faces (400 x 560)
# 10 columns x 6 rows = 4000 x 3360 (sheet 1) and 10 x 3 = 4000 x 1680 (sheet 2): under the 4096 px limit.
W, H = 400, 560


def frame(col, header, header_ink=CREAM):
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W - 1, H - 1), outline=col, width=12)
    d.rectangle((0, 0, W, 66), fill=col)
    d.text((W / 2, 34), header, font=fit(d, header, BLACK, 27, W - 40), fill=header_ink, anchor="mm")
    return im, d


def corner_id(d, cid, col):
    d.text((24, H - 42), cid, font=f(BOLD, 22), fill=col)


def badge(d, xy, text, fill, ink=CREAM, r=36, sub=None):
    x, y = xy
    d.ellipse((x - r, y - r, x + r, y + r), fill=fill, outline=INK, width=3)
    d.text((x, y - (6 if sub else 0)), text, font=f(BLACK, 40), fill=ink, anchor="mm")
    if sub:
        d.text((x, y + 22), sub, font=f(BOLD, 13), fill=ink, anchor="mm")


def stat_box(d, box, title, value, fill, ink=CREAM):
    d.rounded_rectangle(box, 14, fill=fill)
    x0, y0, x1, y1 = box
    d.text(((x0 + x1) / 2, y0 + 20), title, font=f(BOLD, 22), fill=ink, anchor="mm")
    d.text(((x0 + x1) / 2, (y0 + y1) / 2 + 14), str(value), font=f(BLACK, 56), fill=ink, anchor="mm")


def face_action(cid, name, typ, cost, text):
    col = TYPE_COL[typ]
    im, d = frame(col, f"ACTION · {typ}")
    badge(d, (58, 118), str(cost), (35, 32, 30), sub="ENERGY")
    d.text((W / 2 + 30, 120), name, font=fit(d, name, BLACK, 40, W - 140), fill=INK, anchor="mm")
    d.line((40, 172, W - 40, 172), fill=col, width=3)
    para(d, text, 205, H - 70, 36, W - 36, size=40)
    d.text((W - 26, H - 42), typ, font=f(BLACK, 24), fill=col, anchor="ra")
    corner_id(d, cid, col)
    return im


def face_enemy(cid, tier, name, hp, atk, gold, loot, trait):
    col, ink = TIER_COL[tier], TIER_INK[tier]
    im, d = frame(col, f"ENEMY · TIER {ROMAN[tier]}", ink)
    d.text((W / 2, 112), name, font=fit(d, name, BLACK, 42, W - 50), fill=INK, anchor="mm")
    stat_box(d, (40, 150, 190, 262), "HP", hp, (168, 40, 34))
    stat_box(d, (210, 150, 360, 262), "ATK", atk, (40, 36, 34))
    reward = f"{gold} GOLD" + ("  ·  LOOT" if loot else "")
    d.text((W / 2, 296), reward, font=f(BLACK, 30), fill=(150, 104, 40), anchor="mm")
    if trait:
        para(d, trait, 330, H - 84, 34, W - 34, size=28)
    lv = C.LEVELS_FOR_TIER[tier]
    d.text((W / 2, H - 70), f"WIN: +{lv} LEVEL{'S' if lv > 1 else ''}", font=f(BOLD, 24), fill=col if tier > 1 else INK, anchor="mm")
    corner_id(d, cid, INK)
    return im


def face_event(cid, tier, name, text):
    col, ink = TIER_COL[tier], TIER_INK[tier]
    im, d = frame(col, f"EVENT · WILDS {ROMAN[tier]}", ink)
    d.text((W / 2, 116), name, font=fit(d, name, BLACK, 42, W - 50), fill=INK, anchor="mm")
    d.line((40, 164, W - 40, 164), fill=col, width=3)
    para(d, text, 192, H - 60, 34, W - 34, size=34)
    corner_id(d, cid, INK)
    return im


def face_champion():
    ch = C.CHAMPION
    im, d = frame(CHAMP_COL, "THE KING'S TRIAL", GOLD)
    d.text((W / 2, 112), ch["name"], font=fit(d, ch["name"], BLACK, 40, W - 50), fill=INK, anchor="mm")
    stat_box(d, (40, 150, 190, 262), "HP", ch["hp"], (168, 40, 34))
    stat_box(d, (210, 150, 360, 262), "ATK", ch["atk"], (40, 36, 34))
    y = para(d, ch["text"], 286, 360, 34, W - 34, name=BOLD, size=28)
    para(d, "Nobody can help you in the Trial. Everyone else may interfere as usual, and they will.",
         y + 10, 450, 34, W - 34, size=24)
    para(d, "Win: you reach level 10, the king chooses you and the game ends.", 458, H - 50, 34, W - 34,
         name=BOLD, size=22, fill=CHAMP_COL)
    corner_id(d, ch["id"], CHAMP_COL)
    return im


def face_loot(cid, name, price, text, equip):
    im, d = frame(LOOT_COL, "LOOT · EQUIPMENT" if equip else "LOOT · ONE USE")
    badge(d, (58, 118), str(price), (212, 175, 75), ink=INK, sub="GOLD")
    d.text((W / 2 + 30, 120), name, font=fit(d, name, BLACK, 38, W - 140), fill=INK, anchor="mm")
    d.line((40, 172, W - 40, 172), fill=LOOT_COL, width=3)
    para(d, text, 205, H - 100, 36, W - 36, size=36)
    foot = "You may hold 3 equipment items." if equip else "One use: discard after use."
    d.text((W / 2, H - 80), foot, font=f(ITAL, 21), fill=LOOT_COL, anchor="mm")
    corner_id(d, cid, LOOT_COL)
    return im


def face_objective(cid, name, cond):
    im, d = frame(OBJ_COL, "HIDDEN OBJECTIVE", GOLD)
    d.text((W / 2, 122), name, font=fit(d, name, BLACK, 42, W - 50), fill=INK, anchor="mm")
    d.line((40, 172, W - 40, 172), fill=OBJ_COL, width=3)
    para(d, cond, 205, 380, 36, W - 36, size=38)
    d.rounded_rectangle((30, 395, W - 30, H - 60), 14, fill=(40, 36, 30))
    para(d, C.OBJECTIVE_REWARD, 412, H - 66, 46, W - 46, name=BOLD, size=26, fill=GOLD)
    corner_id(d, cid, OBJ_COL)
    return im


def face_character(cid, name, s, a, w, hp, energy, hand, how):
    im, d = frame(CHAR_COL, "CHARACTER", GOLD)
    d.text((W / 2, 114), name, font=f(BLACK, 46), fill=INK, anchor="mm")
    for i, (t, v) in enumerate((("STR", s), ("AGI", a), ("WIS", w))):
        x0 = 34 + i * 114
        stat_box(d, (x0, 150, x0 + 104, 248), t, v, TYPE_COL[t])
    d.text((W / 2, 280), f"HP {hp}  ·  ENERGY {energy}  ·  HAND {hand}", font=fit(d, "HP 13  ·  ENERGY 3  ·  HAND 5", BOLD, 26, W - 50), fill=INK, anchor="mm")
    para(d, how, 308, 370, 34, W - 34, name=ITAL, size=26, fill=(70, 66, 60))
    y = 386
    for ab in C.ABILITIES_OF[name]:
        d.text((40, y), f"{ab[3].capitalize()}:", font=f(BOLD, 24), fill=KIND_COL[ab[3]])
        d.text((178, y), ab[2], font=f(BOLD, 24), fill=INK)
        y += 34
    corner_id(d, cid, CHAR_COL)
    return im


def face_ability(aid, char, name, kind, when, text):
    col = KIND_COL[kind]
    im, d = frame(col, f"ABILITY · {kind.upper()}")
    d.text((W / 2, 98), char.upper(), font=f(BOLD, 24), fill=col, anchor="mm")
    d.text((W / 2, 150), name, font=fit(d, name, BLACK, 44, W - 50), fill=INK, anchor="mm")
    d.text((W / 2, 200), when, font=fit(d, when, ITAL, 26, W - 60), fill=(80, 74, 66), anchor="mm")
    d.line((40, 228, W - 40, 228), fill=col, width=3)
    para(d, text, 258, H - 96, 36, W - 36, size=38)
    d.text((W / 2, H - 78), "Used: face down until you REST.", font=f(ITAL, 21), fill=col, anchor="mm")
    corner_id(d, aid, col)
    return im


# Sheet 1: Action, Loot, Character, Ability, Objective (58). Sheet 2: Wilds I-III and the Champion (25).
SHEET1, SHEET2 = [], []   # (ID, kind key, image)
for cid, name, typ, cost, n, text, _ in C.ACTION:
    SHEET1.append((cid, 1, face_action(cid, name, typ, cost, text)))
for cid, name, price, n, text, equip in C.LOOT:
    SHEET1.append((cid, 6, face_loot(cid, name, price, text, equip)))
for ch in C.CHARACTERS:
    SHEET1.append((ch[0], 8, face_character(*ch)))
for ab in C.ABILITIES:
    SHEET1.append((ab[0], 9, face_ability(*ab)))
for cid, name, cond in C.OBJECTIVES:
    SHEET1.append((cid, 7, face_objective(cid, name, cond)))
for tier in (1, 2, 3):
    for cid, name, n, hp, atk, gold, loot, trait, _ in C.ENEMIES[tier]:
        SHEET2.append((cid, 1 + tier, face_enemy(cid, tier, name, hp, atk, gold, loot, trait)))
    for cid, t, name, text in C.EVENTS:
        if t == tier:
            SHEET2.append((cid, 1 + tier, face_event(cid, tier, name, text)))
SHEET2.append(("CH", 5, face_champion()))

INDEX = {}   # card ID -> (sheet number, index on the sheet)


def save_sheet(items, fn, cols, rows, sheet_no):
    assert len(items) <= cols * rows
    im = Image.new("RGB", (W * cols, H * rows), PAPER)
    for i, (cid, _, face) in enumerate(items):
        INDEX[cid] = (sheet_no, i)
        im.paste(face, ((i % cols) * W, (i // cols) * H))
    assert im.size[0] <= 4096 and im.size[1] <= 4096, im.size
    im.save(OUT / fn)


SHEETS = {1: ("cards-1.png", 10, 6), 2: ("cards-2.png", 10, 3)}
# One small copy of each card face for the bot game's on-screen hand (XML images can't cut a sheet).
UI_CARD = (256, 358)
for _cid, _key, _face in SHEET1 + SHEET2:
    _face.resize(UI_CARD, Image.LANCZOS).save(OUT / f"ui-{_cid}.png")
save_sheet(SHEET1, "cards-1.png", 10, 6, 1)
save_sheet(SHEET2, "cards-2.png", 10, 3, 2)


def back(fn, title, col, sub="", ink=GOLD):
    im = Image.new("RGB", (W, H), col)
    d = ImageDraw.Draw(im)
    d.rectangle((18, 18, W - 18, H - 18), outline=GOLD, width=6)
    d.text((W / 2, H / 2 - 24), title, font=fit(d, title, BLACK, 60, W - 70), fill=ink, anchor="mm")
    if sub:
        para(d, sub, H / 2 + 22, H - 90, 50, W - 50, name=BOLD, size=26, fill=CREAM)
    d.text((W / 2, H - 52), "KINGBOUND", font=f(BLACK, 22), fill=GOLD, anchor="mm")
    im.save(OUT / fn)


back("back-action.png", "ACTION", (96, 24, 22))
back("back-wilds1.png", "WILDS I", TIER_COL[1], "+1 level per kill", ink=INK)
back("back-wilds2.png", "WILDS II", TIER_COL[2], "+2 levels per kill")
back("back-wilds3.png", "WILDS III", TIER_COL[3], "+3 levels per kill")
back("back-champion.png", "CHAMPION", CHAMP_COL, "The King's Trial")
back("back-loot.png", "LOOT", LOOT_COL)
back("back-objective.png", "OBJECTIVE", OBJ_COL, "Hidden: look only at your own")
back("back-character.png", "CHARACTER", CHAR_COL)
back("back-ability.png", "USED", (60, 58, 56), "Turn face up when you REST", ink=CREAM)

# ------------------------------------------------------------------ tiles (400 x 400)
TILE_PX = 400


def tile_img(fn, ring, kind):
    """Coloured by ring (GDD §13): Wilds tiles are the ring colour; town tiles get a panel in their
    own colour on a ring-coloured border, so each ring can still be read at a glance."""
    shade = TIER_COL[ring] if ring in (1, 2, 3) else CHAMP_COL
    im = Image.new("RGB", (TILE_PX, TILE_PX), shade)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, TILE_PX - 1, TILE_PX - 1), outline=(20, 20, 18), width=6)
    if kind.startswith("Wilds"):
        t = int(kind[-1])
        ink = TIER_INK[t]
        d.text((200, 160), f"WILDS {ROMAN[t]}", font=fit(d, f"WILDS {ROMAN[t]}", BLACK, 76, 360), fill=ink, anchor="mm")
        lv = C.LEVELS_FOR_TIER[t]
        d.text((200, 262), f"+{lv} LEVEL{'S' if lv > 1 else ''}", font=f(BOLD, 40), fill=ink, anchor="mm")
    else:
        col = TOWN_COL[kind]
        ink = INK if kind in ("Merchant", "Healer", "Camp") else GOLD if kind == "Castle" else CREAM
        d.rounded_rectangle((34, 34, TILE_PX - 34, TILE_PX - 34), 26, fill=col, outline=(20, 20, 18), width=4)
        d.text((200, 168), kind.upper(), font=fit(d, kind.upper(), BLACK, 70, 300), fill=ink, anchor="mm")
        hint = {"Merchant": "3 LOOT, BUY 1", "Barracks": "STAT +1", "Healer": "1 GOLD = 3 HP",
                "Camp": "REST: FULL HP", "Castle": "LEVEL 9: TRIAL"}[kind]
        d.text((200, 252), hint, font=fit(d, hint, BOLD, 36, 290), fill=ink, anchor="mm")
    im.save(OUT / fn)


TILE_FILES = {}   # (ring, kind) -> file name
for ring, kind in [(0, "Castle"), (1, "Camp"), (1, "Wilds1"), (2, "Wilds2"), (3, "Wilds3"),
                   (2, "Merchant"), (3, "Merchant"), (2, "Barracks"), (3, "Barracks"), (2, "Healer"), (3, "Healer")]:
    fn = f"tile-{kind.lower()}-{ring}.png"
    tile_img(fn, ring, kind)
    TILE_FILES[(ring, kind)] = fn


# ------------------------------------------------------------------ table geometry (TTS units)
# Table_RPG (measured on SHOWDOWN): hands at z = ±21 and x = ±31. A Custom_Tile is 2 x scale units
# along its long side. Cards at scale 1.0 are about 2.2 x 3.1.
GRID = 2.5               # board square spacing
BOARD_Z = 0.5            # the board sits a little north so the level track fits under it
TILE_S = 1.2             # 2.4-unit tiles, 0.1 apart
CS = 1.0


def cell(r, c): return (round((c - 3) * GRID, 3), round(BOARD_Z + (3 - r) * GRID, 3))


TRACK = dict(x=0.0, z=-9.85, dx=1.82)     # level track: 10 spaces of 1.82 under the board

# Seats clockwise seen from above (bottom -> left -> top -> right), the colours of the team's sketch.
# rot = the seat's viewing angle (0 = sitting at the bottom looking up the table).
SEATS = [("Red", 0.0, -21.0, 0.0), ("Yellow", -31.0, 0.0, 90.0), ("Green", 0.0, 21.0, 180.0), ("Blue", 31.0, 0.0, 270.0)]
CAMP_OF = {"Red": (4, 3), "Yellow": (3, 2), "Green": (2, 3), "Blue": (3, 4)}   # each player's own Camp (§4 step 7)
PAWN_OFF = {"Red": (-0.55, -0.55), "Yellow": (-0.55, 0.55), "Green": (0.55, 0.55), "Blue": (0.55, -0.55)}
MARK_OFF = {"Red": (-0.42, -0.45), "Yellow": (-0.42, 0.45), "Green": (0.42, 0.45), "Blue": (0.42, -0.45)}
RGB = {"Red": (0.856, 0.1, 0.094), "Yellow": (0.905, 0.898, 0.172), "Green": (0.192, 0.701, 0.168), "Blue": (0.118, 0.53, 1.0)}


def local(seat, u, v):
    """Seat coordinates: u = the player's right, v = towards the middle of the table."""
    _, hx, hz, rot = seat
    a = math.radians(rot)
    fx, fz = math.sin(a), math.cos(a)
    rx, rz = fz, -fx
    return round(hx + u * rx + v * fx, 2), round(hz + u * rz + v * fz, 2)


def right_of(seat):
    a = math.radians(seat[3])
    return [round(math.cos(a), 3), round(-math.sin(a), 3)]


# Player area (u, v). Row 1: the bots lay their hand open here; the player board on the right.
# Row 2: character, Abilities, equipment, one-use items, hidden objective.
HAND_U, HAND_V = [-11.6 + 2.3 * k for k in range(9)], 4.4
BOARD_UV = (11.05, 4.6)   # 6.3 x 3.6 player board: on the felt, clear of the 9th hand slot and of row 2
ROW2_V = 8.0
CHAR_U, ABIL_U, EQUIP_U, USE_U, OBJ_U = -11.6, [-9.3, -7.0, -4.7], [-2.0, 0.3, 2.6], [5.0, 7.3, 9.6], 12.0

# Middle. Left strip: decks, Merchant offer, player aid, damage tokens, die.
# Right strip: Wilds decks, Champion, the fight area (enemy, used items, played cards, helper).
LX = [-19.9, -17.3, -14.7, -12.1]
RX = [11.0, 13.4, 15.8, 18.2]
PILES = {
    "action": (LX[0], 9.0), "action_d": (LX[1], 9.0), "loot": (LX[2], 9.0), "loot_d": (LX[3], 9.0),
    "chars": (LX[0], 5.4), "abils": (LX[1], 5.4), "objs": (LX[2], 5.4),
    "w1": (RX[0], 9.0), "w2": (RX[1], 9.0), "w3": (RX[2], 9.0), "champ": (RX[3], 9.0),
    "w1_d": (RX[0], 5.4), "w2_d": (RX[1], 5.4), "w3_d": (RX[2], 5.4),
    "enemy": (RX[0], 1.8),
}
OFFER = [(LX[0], 1.8), (LX[1], 1.8), (LX[2], 1.8)]
EXTRA = [(RX[1], 1.8), (RX[2], 1.8), (RX[3], 1.8)]
PLAYED = [(x, -1.8) for x in RX] + [(x, -5.4) for x in RX]
HELPER = [(x, -9.0) for x in RX]
AID_POS = (-16.0, -4.6)
BAGS = {"d1": (LX[0], -9.0), "d5": (LX[1], -9.0)}
DIE_POS = (18.4, 5.4)   # beside the Wilds discard piles: inside the bot camera's fight and board views


# ------------------------------------------------------------------ other images
def frame_img():
    px = 910
    im = Image.new("RGB", (px, px), (54, 38, 26))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, px - 1, px - 1), outline=GOLD, width=10)
    d.rectangle((14, 14, px - 15, px - 15), outline=(30, 20, 14), width=4)
    im.save(OUT / "board-frame.png")


def track_img():
    w, h = 1820, 200
    im = Image.new("RGB", (w, h), (54, 38, 26))
    d = ImageDraw.Draw(im)
    for i in range(10):
        lv = i + 1
        x0 = i * 182
        fill = CHAMP_COL if lv >= 9 else (236, 226, 200)
        ink = GOLD if lv >= 9 else INK
        d.rectangle((x0 + 4, 6, x0 + 178, h - 6), fill=fill, outline=GOLD if lv >= 9 else (90, 70, 50), width=4)
        d.text((x0 + 91, 78), str(lv), font=f(BLACK, 84), fill=ink, anchor="mm")
        sub = {9: "TRIAL", 10: "CHOSEN"}.get(lv, "LEVEL")
        d.text((x0 + 91, 158), sub, font=f(BOLD, 26), fill=ink, anchor="mm")
    im.save(OUT / "level-track.png")


def circle_img(fn, fill, text="", ink=CREAM, ring=CREAM, size=200):
    im = Image.new("RGB", (size, size), fill)
    d = ImageDraw.Draw(im)
    d.ellipse((8, 8, size - 8, size - 8), outline=ring, width=10)
    if text:
        d.text((size / 2, size / 2), text, font=f(BLACK, 96), fill=ink, anchor="mm")
    im.save(OUT / fn)


def aid_img():
    w, h = 1250, 625
    im = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w - 1, h - 1), outline=(96, 24, 22), width=14)
    lines = [
        ("YOUR TURN: REST or TRAVEL", True),
        ("REST: discard any, draw up to hand size, Abilities ready; on a Camp heal to full.", False),
        ("TRAVEL: roll, move 1 up to the roll (no diagonals), resolve the tile you stop on.", False),
        ("FIGHT ROUND", True),
        ("1 Fight or flee.  2 Play cards and your Abilities; Dig Deep: 2 HP = 1 card.", False),
        ("3 Your helper plays.  4 The others interfere, clockwise, once.", False),
        ("5 Damage ≥ HP: you win.  6 The enemy hits: ATK − Block − Guard roll.", False),
        ("7 HP 0: knocked out: −1 level, nearest Camp, full HP, turn ends.", False),
        ("Guard roll 1-2: 0 · 3-4: −1 · 5-6: −2.    Flee: 4-6 escape, 1-3 it hits you.", False),
        ("Win: Tier I +1, II +2, III +3 levels, the gold, LOOT if printed. Max level 9.", False),
        ("Level 9: stop on the Castle for the King's Trial. Win it: level 10, you are chosen.", False),
    ]
    y = 30
    for text, head in lines:
        if head:
            d.text((40, y), text, font=f(BLACK, 40), fill=(96, 24, 22))
            y += 56
        else:
            d.text((40, y), text, font=fit(d, text, BOLD, 31, w - 80), fill=INK)
            y += 44
    im.save(OUT / "player-aid.png")


# Player board: a 6.3 x 3.6 tile (1120 x 640 image, Stretch on, even scale 1.8), kept inside the felt
# (the table's rim hid the lower edge of a 4.0-deep board, 2026-10-13). The layout is drawn for a
# 5.6 x 3.2 board in table units from its centre (x to the right, z down the image) and grows with K.
# Measured on the live table: a font size of 700 draws text about 1 local unit high, and 1000 button
# units are about 1.6 local units wide.
PB_S = 1.8
K = PB_S / 1.6
PB_W, PB_H = 1120, 640


def lp(x, z): return [round(x * K / PB_S, 4), round(z * K / PB_S, 4)]


def bu(w): return int(round(w * K / PB_S * 625))    # table units -> button units
def fs(h): return int(round(h * K / PB_S * 700))    # text height in table units -> font size


BTN = [bu(0.5), bu(0.5), fs(0.36)]
UI_POS = {
    "zfix": 1,
    "title": lp(0, -1.28), "title_font": fs(0.38),
    "hp": lp(-1.4, -0.4), "gold": lp(1.4, -0.4), "num_font": fs(0.52),
    "hp_btn": [lp(-2.47, -0.4), lp(-0.33, -0.4)], "gold_btn": [lp(0.33, -0.4), lp(2.47, -0.4)],
    "btn": BTN,
    "max_btn": [lp(-2.3, 0.5), lp(-0.5, 0.5)], "hp_full": lp(-1.4, 0.5), "small": [bu(0.8), bu(0.4), fs(0.22)],
    "stat": [lp(-1.85, 1.2), lp(0.0, 1.2), lp(1.85, 1.2)], "stat_font": fs(0.28),
    "stat_btn": [[lp(-2.55, 1.2), lp(-1.15, 1.2)], [lp(-0.7, 1.2), lp(0.7, 1.2)], [lp(1.15, 1.2), lp(2.55, 1.2)]],
    "stat_size": [bu(0.42), bu(0.42), fs(0.3)],
}


def wpx(x, z): return ((x / 5.6 + 0.5) * PB_W, (z / 3.2 + 0.5) * PB_H)   # 5.6 x 3.2 design units


def board_img(color):
    im = Image.new("RGB", (PB_W, PB_H), (34, 30, 28))
    d = ImageDraw.Draw(im)
    col = tuple(int(c * 255) for c in RGB[color])
    d.rectangle((0, 0, PB_W - 1, PB_H - 1), outline=col, width=18)
    for (x0, z0, x1, z1, title) in [(-2.72, -1.05, -0.08, 0.85, "HP"), (0.08, -1.05, 2.72, 0.85, "GOLD"),
                                    (-2.72, 0.92, 2.72, 1.5, "")]:
        a, b2 = wpx(x0, z0), wpx(x1, z1)
        d.rounded_rectangle((a[0], a[1], b2[0], b2[1]), 16, outline=(120, 104, 80), width=4)
        if title:
            d.text((a[0] + 18, a[1] + 8), title, font=f(BLACK, 30), fill=(190, 170, 130))
    im.save(OUT / f"board-{color.lower()}.png")


frame_img(); track_img(); aid_img()
for color, *_ in SEATS:
    circle_img(f"marker-{color.lower()}.png", tuple(int(c * 255) for c in RGB[color]), ring=(20, 20, 20))
    board_img(color)
circle_img("damage-1.png", (176, 28, 24), "1")
circle_img("damage-5.png", (96, 12, 12), "5", ring=GOLD)


# ------------------------------------------------------------------ images into TTS's Mods folder
for old in ASSETS.glob("*.png"):
    old.unlink()   # only this game's folder; every image is written again below
HASHED = {}
for png in sorted(OUT.glob("*.png")):
    if png.name.startswith("layout-"):
        continue   # preview.py's picture, not a game image
    data = png.read_bytes()
    h = hashlib.sha1(data).hexdigest()[:10]
    name = f"{png.stem}.{h}.png"
    (ASSETS / name).write_bytes(data)
    HASHED[png.name] = name

# Steam Cloud URLs for a save other people can open (cloud_urls.json, same format as The Limit's). Until the
# images are uploaded with TTS's Cloud Manager, the save points at the local copies, which only this Mac sees.
_CLOUD = json.loads((ROOT / "cloud_urls.json").read_text()) if (ROOT / "cloud_urls.json").exists() else {}
LOCAL = []


def url(fn):
    b = _CLOUD.get(fn)
    if b and hashlib.sha1((OUT / fn).read_bytes()).hexdigest() == b["sha1"]:
        return b["url"]
    LOCAL.append(fn)
    return str(ASSETS / HASHED[fn])


# ------------------------------------------------------------------ save JSON
guid_n = 0


def guid():
    global guid_n
    guid_n += 1
    return f"{0xc00000 + guid_n:06x}"


def tr(x, z, rot_y=180.0, face_down=False, s=1.0, y=1.5, sy=1.0, sz=None):
    return {"posX": x, "posY": y, "posZ": z, "rotX": 0.0, "rotY": rot_y,
            "rotZ": 180.0 if face_down else 0.0, "scaleX": s, "scaleY": sy, "scaleZ": s if sz is None else sz}


def base(name, transform, nick="", desc="", **kw):
    o = {"GUID": guid(), "Name": name, "Transform": transform, "Nickname": nick,
         "Description": desc, "GMNotes": "", "Locked": False, "Grid": False, "Snap": True,
         "Tooltip": True, "Hands": False, "LuaScript": "", "LuaScriptState": "", "XmlUI": ""}
    o.update(kw)
    return o


BACKS = {1: "back-action.png", 2: "back-wilds1.png", 3: "back-wilds2.png", 4: "back-wilds3.png",
         5: "back-champion.png", 6: "back-loot.png", 7: "back-objective.png", 8: "back-character.png",
         9: "back-ability.png"}
SHEET_OF = {1: 1, 6: 1, 7: 1, 8: 1, 9: 1, 2: 2, 3: 2, 4: 2, 5: 2}
CDECK = {k: {"FaceURL": url(SHEETS[SHEET_OF[k]][0]), "BackURL": url(BACKS[k]),
             "NumWidth": SHEETS[SHEET_OF[k]][1], "NumHeight": SHEETS[SHEET_OF[k]][2],
             "BackIsHidden": True, "UniqueBack": False, "Type": 0} for k in BACKS}

# Hover text: the card text, so people can read it without zooming in.
NAME, DESC = {}, {}
for cid, name, typ, cost, n, text, _ in C.ACTION:
    NAME[cid], DESC[cid] = name, f"{typ}, cost {cost}. {text}"
for t, lst in C.ENEMIES.items():
    for cid, name, n, hp, atk, gold, loot, trait, _ in lst:
        NAME[cid] = name
        DESC[cid] = f"Tier {ROMAN[t]}: HP {hp}, ATK {atk}, {gold} gold{', LOOT' if loot else ''}. {trait}".strip()
for cid, t, name, text in C.EVENTS:
    NAME[cid], DESC[cid] = name, f"Event, Wilds {ROMAN[t]}. {text}"
NAME["CH"], DESC["CH"] = C.CHAMPION["name"], f"HP {C.CHAMPION['hp']}, ATK {C.CHAMPION['atk']}. {C.CHAMPION['text']}"
for cid, name, price, n, text, equip in C.LOOT:
    NAME[cid], DESC[cid] = name, f"{'Equipment' if equip else 'One use'}, {price} gold. {text}"
for ch in C.CHARACTERS:
    NAME[ch[0]] = ch[1]
    DESC[ch[0]] = f"STR {ch[2]}, AGI {ch[3]}, WIS {ch[4]}, HP {ch[5]}, energy {ch[6]}, hand {ch[7]}. {ch[8]}."
for ab in C.ABILITIES:
    NAME[ab[0]], DESC[ab[0]] = ab[2], f"{ab[1]} {ab[3]}. {ab[4]} {ab[5]}"
for cid, name, cond in C.OBJECTIVES:
    NAME[cid], DESC[cid] = name, f"{cond} {C.OBJECTIVE_REWARD}"
KEY_OF = {cid: key for cid, key, _ in SHEET1 + SHEET2}


def card(cid, transform=None):
    key = KEY_OF[cid]
    return base("Card", transform or tr(0, 0, 180.0, True, CS), NAME[cid], DESC[cid], GMNotes=cid,
                CardID=key * 100 + INDEX[cid][1], CustomDeck={str(key): CDECK[key]},
                SidewaysCard=False, HideWhenFaceDown=True)


def deck(ids, pos, nick, face_up=False):
    cards = [card(cid) for cid in ids]
    key = KEY_OF[ids[0]]
    return base("Deck", tr(*pos, 180.0, not face_up, CS, y=1.3), nick,
                DeckIDs=[c["CardID"] for c in cards], CustomDeck={str(key): CDECK[key]},
                ContainedObjects=cards, SidewaysCard=False, HideWhenFaceDown=True)


def tile(fn, transform, nick, desc="", locked=True, circle=False, thick=0.1, **kw):
    # Measured live (2026-10-13): with Stretch off TTS draws every tile square, 2 x scale units each
    # way; with Stretch on the tile takes the image's shape, 2 x scale deep and 2 x scale x
    # (width / height of the image) wide. Square images use Stretch off, the others Stretch on with an
    # even scale = depth / 2.
    im = Image.open(OUT / fn)
    stretch = im.size[0] != im.size[1]
    return base("Custom_Tile", transform, nick, desc, Locked=locked,
                CustomImage={"ImageURL": url(fn), "ImageSecondaryURL": "", "ImageScalar": 1.0, "WidthScale": 0.0,
                             "CustomTile": {"Type": 2 if circle else 0, "Thickness": thick,
                                            "Stackable": False, "Stretch": stretch}}, **kw)


objs, snaps = [], []


def snap(p, rot=None, tags=None):
    s = {"Position": {"x": p[0], "y": 1.0, "z": p[1]}}
    if rot is not None:
        s["Rotation"] = {"x": 0.0, "y": rot, "z": 0.0}
    if tags:
        s["Tags"] = tags
    snaps.append(s)


# Board: the frame, then the 49 tiles in a random legal layout (§3) so the save is ready to play.
objs.append(tile("board-frame.png", tr(0.0, BOARD_Z, 180.0, s=9.1, y=1.0), "Board", thick=0.05))
BOARD = C.make_board(random.Random(BOARD_SEED))
for (r, c), kind in sorted(BOARD.items()):
    ring = C.ring_of(r, c)
    nick = {"Wilds1": "Wilds I", "Wilds2": "Wilds II", "Wilds3": "Wilds III"}.get(kind, kind)
    x, z = cell(r, c)
    objs.append(tile(TILE_FILES[(ring, kind)], tr(x, z, 180.0, s=TILE_S, y=1.05), nick,
                     thick=0.12, Tags=["tile", f"ring{ring}"], GMNotes=f"{ring}:{kind}"))
    snap((x, z), 180.0, ["tile"])
assert len([o for o in objs if "tile" in o.get("Tags", [])]) == 49
objs.append(tile("level-track.png", tr(TRACK["x"], TRACK["z"], 180.0, s=1.0, y=1.0), "Level track", thick=0.05))
for lv in range(1, 11):
    snap((round(TRACK["x"] + (lv - 5.5) * TRACK["dx"], 2), TRACK["z"]), None, ["marker"])

def to_lua(v):
    """Python data as a Lua table literal (lists become 1-based arrays)."""
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k} = {to_lua(x)}" for k, x in v.items()) + "}"
    if isinstance(v, (list, tuple)):
        return "{" + ", ".join(to_lua(x) for x in v) + "}"
    return json.dumps(v)


PB_LUA = (ROOT / "player_board.lua").read_text().replace("__POS__", to_lua(UI_POS))
lua_seats = []
for seat in SEATS:
    color, hx, hz, rot = seat
    cr = rot + 180.0
    objs.append(base("HandTrigger", {"posX": hx, "posY": 4.8, "posZ": hz, "rotX": 0.0, "rotY": rot,
                                     "rotZ": 0.0, "scaleX": 11.8, "scaleY": 9.2, "scaleZ": 4.9},
                     FogColor=color, Locked=True))
    bx, bz = local(seat, *BOARD_UV)
    objs.append(tile(f"board-{color.lower()}.png", tr(bx, bz, cr, s=PB_S, y=1.05), f"{color} board",
                     "HP, max HP, gold and stats. Click the buttons.", thick=0.1,
                     LuaScript=PB_LUA, LuaScriptState=json.dumps({"title": color}), Tags=["pboard"], GMNotes=color))
    camp = CAMP_OF[color]
    cx, cz = cell(*camp)
    objs.append(base("PlayerPawn", tr(cx + PAWN_OFF[color][0], cz + PAWN_OFF[color][1], 0.0, s=0.7, y=1.6),
                     f"{color} pawn", ColorDiffuse={"r": RGB[color][0], "g": RGB[color][1], "b": RGB[color][2]},
                     Tags=["pawn"], GMNotes=color))
    mx = TRACK["x"] + (1 - 5.5) * TRACK["dx"] + MARK_OFF[color][0]
    objs.append(tile(f"marker-{color.lower()}.png", tr(mx, TRACK["z"] + MARK_OFF[color][1], 180.0, s=0.3, y=1.3),
                     f"{color} level", locked=False, circle=True, thick=0.15, Tags=["marker"], GMNotes=color))
    hand = [local(seat, u, HAND_V) for u in HAND_U]
    abil = [local(seat, u, ROW2_V) for u in ABIL_U]
    equip = [local(seat, u, ROW2_V) for u in EQUIP_U]
    use = [local(seat, u, ROW2_V) for u in USE_U]
    ch, ob = local(seat, CHAR_U, ROW2_V), local(seat, OBJ_U, ROW2_V)
    for p in abil + equip + use + [ch, ob]:
        snap(p, cr)
    # Bot camera views of this seat. Every view looks from the south (yaw 0): TTS turns the camera
    # slowly, and turning to face each seat made the video drag (Yavuz, 2026-10-13); the hand strip
    # shows the cards upright anyway. They aim between the hand row and the row behind it.
    views = {"hand": list(local(seat, -2.5, 6.0)), "gear": list(local(seat, 9.0, 6.0)), "yaw": 0}
    lua_seats.append({"color": color, "rot": cr, "hand": hand, "char": ch, "abil": abil, "equip": equip,
                      "use": use, "obj": ob, "camp": list(camp), "off": list(PAWN_OFF[color]),
                      "moff": list(MARK_OFF[color]), "u": right_of(seat), "views": views})

# Decks (§2). The Champion card waits face up next to the board (§10.2).
action_ids = [c[0] for c in C.ACTION for _ in range(c[4])]
wilds_ids = {t: [e[0] for e in C.ENEMIES[t] for _ in range(e[2])] + [v[0] for v in C.EVENTS if v[1] == t] for t in (1, 2, 3)}
loot_ids = [c[0] for c in C.LOOT for _ in range(c[3])]
objs += [deck(action_ids, PILES["action"], "Action deck"),
         deck(wilds_ids[1], PILES["w1"], "Wilds I deck"), deck(wilds_ids[2], PILES["w2"], "Wilds II deck"),
         deck(wilds_ids[3], PILES["w3"], "Wilds III deck"), deck(loot_ids, PILES["loot"], "Loot deck"),
         deck([o[0] for o in C.OBJECTIVES], PILES["objs"], "Hidden objectives"),
         deck([c[0] for c in C.CHARACTERS], PILES["chars"], "Characters"),
         deck([a[0] for a in C.ABILITIES], PILES["abils"], "Abilities", face_up=True),
         card("CH", tr(*PILES["champ"], 180.0, False, CS, y=1.3))]
counted = {}
for o in objs:
    if o["Name"] == "Deck":
        counted[o["Nickname"]] = len(o["ContainedObjects"])
    elif o["Name"] == "Card":
        counted[o["Nickname"]] = 1
assert sum(counted.values()) == 132, counted   # §2: 132 cards in total
for p in list(PILES.values()) + OFFER + EXTRA + PLAYED + HELPER:
    snap(p, 180.0)

objs.append(tile("player-aid.png", tr(*AID_POS, 180.0, s=2.5, y=1.02), "Player aid", "Turn and fight summary", thick=0.05))
TOKEN_DATA = {}
for k, (x, z) in BAGS.items():
    tok = tile(f"damage-{k[1]}.png", tr(0, 0, 180.0, s=0.33, y=1.5), f"Damage {k[1]}", locked=False, circle=True,
               thick=0.15, Tags=["dmg"])
    TOKEN_DATA[k] = tok
    objs.append(base("Infinite_Bag", tr(x, z, 180.0, s=0.8, y=1.3), f"Damage {k[1]}", Locked=True,
                     ContainedObjects=[tok], ColorDiffuse={"r": 0.45, "g": 0.1, "b": 0.08}))
objs.append(base("Die_6", tr(*DIE_POS, 0.0, s=1.0, y=1.6), "Die", Tags=["die"]))

# ------------------------------------------------------------------ Lua and UI
LAYOUT = {
    "grid": GRID, "board_z": BOARD_Z, "track": TRACK, "seats": lua_seats,
    "piles": {k: list(v) for k, v in PILES.items()}, "offer": OFFER, "extra": EXTRA,
    "played": PLAYED, "helper": HELPER, "die": list(DIE_POS),
    "chars": {ch[1]: {"hp": ch[5], "STR": ch[2], "AGI": ch[3], "WIS": ch[4], "hand": ch[7],
                      "abilities": [a[2] for a in C.ABILITIES_OF[ch[1]]]} for ch in C.CHARACTERS},
    "ability_ids": {a[2]: a[0] for a in C.ABILITIES},
    "names": NAME,
}
# BOT GAME: the bots play the default full game and the short game here, and every command
# bots/play.py would send to TTS is stored in the save with the seconds to wait after it (speed 1).


class _Recorder:
    def __init__(self):
        self.sent = []

    def send(self, data):
        self.sent.append(data)


def scripted(seed, mode):
    g = Game(seed, mode)
    g.play()
    rec = _Recorder()
    director = Director(rec, 1.0, camera=True)
    steps = [{"msg": {"op": "reset"}, "wait": 2.0}]
    for e in g.events:
        before = len(rec.sent)
        director.show(e)
        new = rec.sent[before:]
        for k, m in enumerate(new):
            steps.append({"msg": m, "wait": round(duration(e), 3) if k == len(new) - 1 else 0})
        if not new:
            steps.append({"wait": round(duration(e), 3)})
    text = json.dumps(steps, ensure_ascii=False, separators=(",", ":"))
    assert "]=====]" not in text
    return text, sum(s["wait"] for s in steps), g


SCRIPT_FULL, TIME_FULL, GAME_FULL = scripted(DEFAULT_SEED["full"], "full")
SCRIPT_SHORT, TIME_SHORT, GAME_SHORT = scripted(DEFAULT_SEED["demo"], "demo")
LUA = ((ROOT / "global.lua").read_text()
       .replace("__VERSION__", VERSION)
       .replace("__LAYOUT__", json.dumps(LAYOUT))
       .replace("__TOKENS__", json.dumps(TOKEN_DATA))
       .replace("__SCRIPT_FULL__", SCRIPT_FULL).replace("__TIME_FULL__", f"{TIME_FULL:.1f}")
       .replace("__SCRIPT_SHORT__", SCRIPT_SHORT).replace("__TIME_SHORT__", f"{TIME_SHORT:.1f}"))


def mmss(sec): return f"{int(sec // 60)}:{int(sec % 60):02d}"


# Three buttons under TTS's own toolbar (top left), so they never cover its menus. BOT GAME opens a
# small menu beside it: the full game, the short game and the speed.
BTN = '    <Button {idattr}onClick="{f}" fontSize="15" color="{c}" textColor="#F5ECD7">{t}</Button>'
MENU = [("", "startGame", "#7A6012", "START GAME"), ('id="kbBotBtn" ', "toggleBotMenu", "#5C2C7A", "BOT GAME"),
        ("", "resetGame", "#3C2819", "RESET")]
BOTMENU = [('id="kbBotFull" ', "botFull", "#3E5A34", f"Full game · {mmss(TIME_FULL)}"),
           ('id="kbBotShort" ', "botShort", "#3E5A34", f"Short game · {mmss(TIME_SHORT)}"),
           ('id="kbBotSpeed" ', "botSpeed", "#3C2819", "Speed 1x"),
           ('id="kbBotCam" ', "botCamera", "#3C2819", "Camera: follows")]
HAND_SLOTS = 10
XML = ('<VerticalLayout id="kbMenu" height="{h}" width="150" rectAlignment="UpperLeft" offsetXY="8 -410" spacing="6">\n'.format(h=len(MENU) * 38)
       + "\n".join(BTN.format(idattr=i, f=f_, c=c_, t=t_) for i, f_, c_, t_ in MENU)
       + "\n</VerticalLayout>\n"
       + '<VerticalLayout id="kbBotMenu" active="false" height="{h}" width="200" rectAlignment="UpperLeft" offsetXY="164 -448" spacing="6">\n'.format(h=len(BOTMENU) * 38)
       + "\n".join(BTN.format(idattr=i, f=f_, c=c_, t=t_) for i, f_, c_, t_ in BOTMENU)
       + "\n</VerticalLayout>\n"
       # Bot overlays, hidden until a bot game runs: the hand of the player who acts, a caption at the
       # bottom and a status list on the right.
       + '<Panel id="kbHand" active="false" rectAlignment="LowerCenter" offsetXY="0 152" width="1400" height="190" color="#00000000">\n'
       + '  <Text id="kbHandLabel" rectAlignment="UpperCenter" offsetXY="0 0" height="30" fontSize="21" color="#F5ECD7" alignment="MiddleCenter" outline="#000000" outlineSize="1 1"></Text>\n'
       + '  <HorizontalLayout rectAlignment="LowerCenter" height="157" spacing="6" childAlignment="MiddleCenter" childForceExpandWidth="false" childForceExpandHeight="false">\n'
       + "\n".join(f'    <Image id="kbHand{i}" active="false" width="112" height="157" preferredWidth="112" preferredHeight="157" preserveAspect="true"></Image>' for i in range(1, HAND_SLOTS + 1))
       + '\n  </HorizontalLayout>\n</Panel>\n'
       + '<Panel id="kbCaption" active="false" rectAlignment="LowerCenter" offsetXY="0 30" width="1250" height="118" color="#000000C8">\n'
       + '  <Text id="kbCaptionHead" rectAlignment="UpperCenter" offsetXY="0 -6" height="32" fontSize="25" color="#D4AF4B" alignment="MiddleCenter"></Text>\n'
       + '  <Text id="kbCaptionText" rectAlignment="LowerCenter" offsetXY="0 10" height="72" width="1210" fontSize="30" color="#F5ECD7" alignment="MiddleCenter" horizontalOverflow="Wrap" verticalOverflow="Overflow"></Text>\n'
       + '</Panel>\n'
       + '<Panel id="kbStatus" active="false" rectAlignment="MiddleRight" offsetXY="-12 40" width="430" height="200" color="#000000B4">\n'
       + '  <VerticalLayout padding="12 12 10 10" spacing="4">\n'
       + "\n".join(f'    <Text id="kbStatus{i}" fontSize="19" color="#F5ECD7" alignment="MiddleLeft"></Text>' for i in range(1, 5))
       + '\n  </VerticalLayout>\n</Panel>')

now = time.localtime()
save = {
    "SaveName": SAVE_NAME, "EpochTime": int(time.time()),
    "Date": time.strftime("%m/%d/%Y %I:%M:%S %p", now), "VersionNumber": "v14.2.2",
    "GameMode": "Kingbound prototype", "Tags": [], "Gravity": 0.5, "PlayArea": 0.5,
    "Table": "Table_RPG", "Sky": "Sky_Regal",
    "Note": f"Kingbound v{VERSION} prototype (rules: Kingbound-GDD.md). START GAME deals a new game, BOT GAME lets "
            "four bots play by themselves, RESET puts everything back. Player boards: click the buttons.",
    "Hands": {"Enable": True, "DisableUnused": False, "Hiding": 0},
    "LuaScript": LUA, "LuaScriptState": "", "XmlUI": XML, "SnapPoints": snaps, "ObjectStates": objs,
    "CustomUIAssets": [{"Type": 0, "Name": cid, "URL": url(f"ui-{cid}.png")} for cid, _, _ in SHEET1 + SHEET2],
}
(OUT / f"{SAVE_NAME}.json").write_text(json.dumps(save, indent=1, ensure_ascii=False))
shutil.copy(OUT / f"{SAVE_NAME}.json", SAVES / f"{SAVE_NAME}.json")
print(f"{len(objs)} objects, {len(snaps)} snap points, cards {counted}")
print(f"images: {len(HASHED)} in {ASSETS} ({len(set(LOCAL))} local, not on Steam Cloud)")
print(f"bot games: full {mmss(TIME_FULL)} ({GAME_FULL.winner.label} wins), short {mmss(TIME_SHORT)} "
      f"({GAME_SHORT.winner.label} wins), script {len(LUA) // 1024} KB")
print(f"save → {SAVES / (SAVE_NAME + '.json')}")
