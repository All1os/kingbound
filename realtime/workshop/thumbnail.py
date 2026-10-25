"""A picture of the game (1024 x 1024) for the Workshop page, put together from the save's own images.

Run after tts/build.py: python3 thumbnail.py  ->  preview.png next to this file.
beep.png is Beep (Kenshi) from Yavuz's own model, cut out of its render (beep-odev/beep-onizleme.png);
Yavuz asked for him on the thumbnail (2026-10-25). Without beep.png the dungeon is centred alone.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
OUT = HERE.parent / "tts" / "output"
FONT = "/System/Library/Fonts/Supplemental/"
GOLD, CREAM, BG = (181, 145, 66), (244, 232, 204), (40, 30, 26)
PAWNS = {"Red": (200, 60, 52), "Yellow": (214, 190, 40), "Green": (64, 160, 60), "Blue": (52, 120, 210), "Purple": (140, 64, 196)}
BEEP = HERE / "beep.png"


def first(pattern):
    return Image.open(sorted(OUT.glob(pattern))[0]).convert("RGB")


im = Image.new("RGB", (1024, 1024), BG)
d = ImageDraw.Draw(im)
d.rectangle((10, 10, 1013, 1013), outline=GOLD, width=10)
size = 150
while d.textlength("KINGBOUND", font=ImageFont.truetype(FONT + "Georgia Bold.ttf", size)) > 900:
    size -= 4
d.text((512, 122), "KINGBOUND", font=ImageFont.truetype(FONT + "Georgia Bold.ttf", size), fill=GOLD, anchor="mm")
d.text((512, 222), "real-time dungeon race  ·  3-5 players  ·  10 minutes",
       font=ImageFont.truetype(FONT + "Arial.ttf", 34), fill=CREAM, anchor="mm")
# A small dungeon around the Safe Room: the kinds of room the game has, a token on each monster and
# treasure room, and the five characters on their way.
grid = [["room-trap-spike-*", "room-treasure-*", "room-monster-*"],
        ["room-empty-*", "room-safe-*", "room-trap-collapse-*"],
        ["room-monster-*", "room-trap-plate-*", "room-treasure-*"]]
tokens = {(0, 1): "tre-rare.png", (0, 2): "mon-strong.png", (2, 0): "mon-weak.png", (2, 2): "tre-special.png"}
pawns = {(1, 1): ["Red", "Yellow"], (0, 1): ["Green"], (2, 2): ["Blue"], (1, 0): ["Purple"]}
beep = BEEP.exists()
T, G = (212, 6) if beep else (236, 8)
x0, y0 = (34, 290) if beep else ((1024 - 3 * T - 2 * G) // 2, 276)
k_tok, k_pawn = T / 236, T / 236
for r, row in enumerate(grid):
    for c, pat in enumerate(row):
        x, y = x0 + c * (T + G), y0 + r * (T + G)
        im.paste(first(pat).resize((T, T)), (x, y))
        if (r, c) in tokens:
            n = int(112 * k_tok)
            tok = Image.open(OUT / tokens[(r, c)]).convert("RGB").resize((n, n))
            mask = Image.new("L", (n, n), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, n - 1, n - 1), fill=255)
            im.paste(tok, (x + T // 2 - n // 2, y + T // 2 - n // 2), mask)
        for k, color in enumerate(pawns.get((r, c), [])):
            rr = int(20 * k_pawn)
            px, py = x + int(46 * k_pawn) + k * int(52 * k_pawn), y + int(48 * k_pawn)
            d.ellipse((px - rr, py - rr, px + rr, py + rr), fill=PAWNS[color], outline=(20, 16, 14), width=4)
if beep:
    # Beep stands on the right, at the dungeon's edge, with a shadow under his feet.
    b = Image.open(BEEP).convert("RGBA")
    hgt = 760
    b = b.resize((round(b.size[0] * hgt / b.size[1]), hgt), Image.LANCZOS)
    bx, by = 1024 - 36 - b.size[0], 1004 - hgt
    shadow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse((bx + 10, by + hgt - 26, bx + b.size[0] - 10, by + hgt + 6), fill=(0, 0, 0, 110))
    im = Image.alpha_composite(im.convert("RGBA"), shadow)
    im.alpha_composite(b, (bx, by))
    im = im.convert("RGB")
im.save(HERE / "preview.png")
print("preview.png", im.size, "with Beep" if beep else "")
