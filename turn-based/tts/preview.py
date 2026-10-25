"""Draws the save's table seen from above (north up), without opening Tabletop Simulator.

Used to check the layout after changing positions in build.py: every tile, card, deck, pawn and
token is drawn at its saved position, and the empty slots the scripts use (bot hands, the fight
area, the Merchant offer) are outlined. Output: output/layout-preview.png
Run: python3 preview.py
"""
import json, re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
OUT = ROOT / "output"
save = json.loads((OUT / "KINGBOUND-prototype.json").read_text())
PX = 30                       # pixels per table unit
X0, X1, Z0, Z1 = -36, 36, -25, 25
img = Image.new("RGB", ((X1 - X0) * PX, (Z1 - Z0) * PX), (70, 52, 40))
d = ImageDraw.Draw(img)
font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 14)
CARD = (2.2, 3.1)             # card size at scale 1.0
_cache = {}


def to_px(x, z): return ((x - X0) * PX, (Z1 - z) * PX)


def load(path):
    if path not in _cache:
        _cache[path] = Image.open(path).convert("RGB")
    return _cache[path]


def paste(im, x, z, w, h, rot_y):
    im = im.resize((max(1, int(w * PX)), max(1, int(h * PX))))
    im = im.rotate(-(rot_y - 180), expand=True)   # rotY 180 = readable from the south = upright here
    cx, cz = to_px(x, z)
    img.paste(im, (int(cx - im.size[0] / 2), int(cz - im.size[1] / 2)))


def card_image(o):
    key = str(o["CardID"] // 100)
    cd = o["CustomDeck"][key]
    face_down = abs(o["Transform"]["rotZ"]) > 90
    if face_down:
        return load(cd["BackURL"])
    sheet = load(cd["FaceURL"])
    i = o["CardID"] % 100
    w, h = sheet.size[0] // cd["NumWidth"], sheet.size[1] // cd["NumHeight"]
    c, r = i % cd["NumWidth"], i // cd["NumWidth"]
    return sheet.crop((c * w, r * h, (c + 1) * w, (r + 1) * h))


for o in save["ObjectStates"]:
    t = o["Transform"]
    x, z, ry, s = t["posX"], t["posZ"], t["rotY"], t["scaleX"]
    name = o["Name"]
    if name == "Custom_Tile":
        im = load(o["CustomImage"]["ImageURL"])
        stretch = o["CustomImage"]["CustomTile"]["Stretch"]
        h = 2 * t["scaleZ"]            # Stretch on: the image's shape, 2 x scale deep; off: square
        w = h * im.size[0] / im.size[1] if stretch else 2 * s
        paste(im, x, z, w, h, ry)
    elif name in ("Card", "Deck"):
        top = o if name == "Card" else o["ContainedObjects"][-1 if abs(t["rotZ"]) > 90 else 0]
        top = dict(top, Transform=t)
        paste(card_image(top), x, z, CARD[0] * s, CARD[1] * s, ry)
        if name == "Deck":
            cx, cz = to_px(x, z)
            d.text((cx, cz + CARD[1] * PX / 2 + 2), f"{o['Nickname']} ({len(o['ContainedObjects'])})", font=font, fill=(255, 255, 255), anchor="ma")
    elif name == "PlayerPawn":
        c = o["ColorDiffuse"]
        col = tuple(int(c[k] * 255) for k in "rgb")
        cx, cz = to_px(x, z)
        r = 0.37 * PX
        d.ellipse((cx - r, cz - r, cx + r, cz + r), fill=col, outline=(0, 0, 0), width=2)
    elif name == "Die_6":
        cx, cz = to_px(x, z)
        d.rectangle((cx - 15, cz - 15, cx + 15, cz + 15), fill=(250, 250, 250), outline=(0, 0, 0), width=2)
    elif name == "Infinite_Bag":
        cx, cz = to_px(x, z)
        d.ellipse((cx - 30, cz - 30, cx + 30, cz + 30), fill=(110, 30, 25), outline=(0, 0, 0), width=2)
        d.text((cx, cz), o["Nickname"], font=font, fill=(255, 255, 255), anchor="mm")
    elif name == "HandTrigger":
        hw, hd = t["scaleX"] / 2, t["scaleZ"] / 2
        horiz = abs(((ry % 180) - 90)) > 45
        if not horiz: hw, hd = hd, hw
        a, b = to_px(x - hw, z + hd), to_px(x + hw, z - hd)
        d.rectangle((a[0], a[1], b[0], b[1]), outline=o["FogColor"].lower(), width=3)

# Slots the scripts fill (from the layout written into the Global script).
L = json.loads(re.search(r"JSON\.decode\(\[==\[(.*?)\]==\]\)", save["LuaScript"], re.S).group(1))


def outline(p, rot_y, col=(255, 255, 255)):
    w, h = CARD
    if abs((rot_y % 180) - 90) < 45: w, h = h, w
    a, b = to_px(p[0] - w / 2, p[1] + h / 2), to_px(p[0] + w / 2, p[1] - h / 2)
    d.rectangle((a[0], a[1], b[0], b[1]), outline=col, width=2)


for s in L["seats"]:
    for p in s["hand"]:
        outline(p, s["rot"], (255, 230, 120))
    for p in s["equip"] + s["use"] + s["abil"] + [s["char"], s["obj"]]:
        outline(p, s["rot"])
for p in L["played"] + L["helper"] + L["extra"] + L["offer"] + [L["piles"]["enemy"]]:
    outline(p, 180, (120, 200, 255))
for k, p in L["piles"].items():
    cx, cz = to_px(*p)
    d.text((cx, cz - CARD[1] * PX / 2 - 16), k, font=font, fill=(200, 230, 255), anchor="ma")

img.save(OUT / "layout-preview.png")
print("→", OUT / "layout-preview.png", img.size)
