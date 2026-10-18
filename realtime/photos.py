"""Photos of every Kingbound element for the presentation, taken in a running Tabletop Simulator.

  python3 photos.py OUTDIR

Each shot puts the table back to its starting places, lays the element(s) out on the empty felt in
front of the start room, points the camera at them and grabs the screen (macOS screencapture), cropped
to 16:9 without TTS's toolbars. The save KINGBOUND-realtime must be loaded and TTS in front.
"""
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tutorial import TTS  # noqa: E402
import plan as P  # noqa: E402

OUT = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.cwd() / "photos"
ONLY = set(sys.argv[2:])   # e.g. 01 05: retake just these shots
OUT.mkdir(parents=True, exist_ok=True)
SHOT = OUT / "_screen.png"
# 16:9 crop of the 3456 x 2234 Retina screen that leaves out TTS's toolbars (top, left) and corner icons.
CROP = (178, 245, 3278, 1989)

# Lua run in the Global script for staging (the Global's own helpers are local, so these are repeated).
LUA_HEAD = """
local function find(tag, note)
  for _, o in ipairs(getObjectsWithTag(tag)) do if o.getGMNotes() == note then return o end end
end
local function put(o, x, z, y, up)
  if not o then return end
  o.setPositionSmooth({x = x, y = y, z = z}, false, true)
  o.setRotationSmooth({x = 0, y = 180, z = up and 0 or 180}, false, true)
end
local function look(x, z, pitch, dist)
  for _, pl in ipairs(Player.getPlayers()) do
    if pl.host then pl.lookAt({position = {x = x, y = 0, z = z}, pitch = pitch, yaw = 0, distance = dist}) end
  end
end
"""


def lua(code):
    s = socket.create_connection(("127.0.0.1", 39999), timeout=3)
    s.sendall(json.dumps({"messageID": 3, "guid": "-1", "script": LUA_HEAD + code}).encode())
    s.close()


def wanted(name):
    return not ONLY or name[:2] in ONLY


def grab(name, crop=CROP):
    time.sleep(2.2)   # smooth moves and the camera settle
    subprocess.run(["screencapture", "-x", str(SHOT)], check=True)
    im = Image.open(SHOT).convert("RGB").crop(crop)
    im.save(OUT / f"{name}.png")
    SHOT.unlink()
    print("  ", name)


def main():
    tts = TTS()
    if not tts.hello():
        sys.exit("TTS is not running with the KINGBOUND-realtime save loaded.")
    subprocess.run(["osascript", "-e", 'tell application "Tabletop Simulator" to activate'])
    subprocess.run(["swift", "-e", "import CoreGraphics; CGWarpMouseCursorPosition(CGPoint(x: 4, y: 760))"],
                   capture_output=True)

    def fresh():
        tts.send({"op": "reset"})
        tts.send({"op": "button", "show": False})
        time.sleep(2.0)

    # Room tiles (§2.1): start, empty, monster, treasure, and the back of an unexplored room.
    if wanted("01"):
        fresh()
        lua("""
        put(find('room', '0,0'), -8, -3, 0.98, true)
        put(find('room', '0,-1'), -4, -3, 0.98, true)
        put(find('room', '0,-2'), 0, -3, 0.98, true)
        put(find('room', '-1,-2'), 4, -3, 0.98, true)
        put(find('room', 'spare0'), 8, -3, 1.10, false)
        look(0, -3.3, 78, 14.8)""")
        grab("01-room-tiles")

    # Dice (§2.3, §5): the three symbols on top.
    if wanted("02"):
        fresh()
        lua("""
        for i, v in ipairs({1, 3, 5}) do
          local d = find('die', 'Red:' .. i)
          d.setRotationValue(v)   -- before the move: setRotationValue cancels a smooth move started earlier
          d.setPositionSmooth({x = (i - 2) * 1.9, y = 1.46, z = -3}, false, true)
        end
        look(0, -2.9, 52, 4.6)""")
        grab("02-dice-symbols")

    # Monster tokens (§6): weak, medium, strong, and the back.
    if wanted("03"):
        fresh()
        lua("""
        put(find('token', 'm-weak-1'), -4.5, -3, 0.97, true)
        put(find('token', 'm-medium-1'), -1.5, -3, 0.97, true)
        put(find('token', 'm-strong-1'), 1.5, -3, 0.97, true)
        put(find('token', 'm-weak-2'), 4.5, -3, 1.13, false)
        look(0, -3.1, 78, 7.5)""")
        grab("03-monster-tokens")

    # Treasure tokens (§9): common, rare, special, and the back.
    if wanted("04"):
        fresh()
        lua("""
        put(find('token', 't-common-1'), -4.5, -3, 0.97, true)
        put(find('token', 't-rare-1'), -1.5, -3, 0.97, true)
        put(find('token', 't-special-1'), 1.5, -3, 0.97, true)
        put(find('token', 't-common-2'), 4.5, -3, 1.13, false)
        look(0, -3.1, 78, 7.5)""")
        grab("04-treasure-tokens")

    # Loot Deck (§2.4): the five cards and the deck.
    if wanted("05"):
        fresh()
        lua("""
        local deck = getObjectsWithTag('lootdeck')[1]
        local want = {L1 = -6.4, L2 = -4.0, L3 = -1.6, L4 = 0.8, L5 = 3.2}
        for _, c in ipairs(deck.getObjects()) do
          local x = want[c.gm_notes]
          if x then
            want[c.gm_notes] = nil
            deck.takeObject({guid = c.guid, position = {x = x, y = 1.2, z = -3}, rotation = {x = 0, y = 180, z = 0},
                             smooth = false, callback_function = function(o) o.setLock(true) end})
          end
        end
        deck.setPositionSmooth({x = 5.9, y = 1.2, z = -3}, false, true)
        look(-0.25, -3.2, 78, 11)""")
        grab("05-loot-cards")

    # Player mat (§2.2-2.3): 4 dice, a Loot card, trophies.
    if wanted("06"):
        fresh()
        tts.send({"op": "deal"})
        time.sleep(1.5)
        for tid in ("t-special-1", "m-weak-2", "t-rare-2"):
            tts.send({"op": "take", "color": "Green", "id": tid})
        tts.send({"op": "loot", "color": "Green", "id": "L1"})
        time.sleep(1.5)
        tts.send({"op": "camera", "view": "mat", "color": "Green", "distance": 10})
        grab("06-player-mat")

    # Action chart (§5).
    if wanted("07"):
        fresh()
        lua("look(-16.5, 0.3, 80, 11)")
        grab("07-action-chart")

    # Character tokens (§2.2) in the start room.
    if wanted("08"):
        fresh()
        tts.send({"op": "pawns"})
        lua("look(0, 2.6, 45, 6)")
        grab("08-characters")

    # Timer (§2.5): the on-screen 10-minute clock, top right.
    if wanted("09"):
        fresh()
        tts.send({"op": "timer", "left": 600})
        tts.send({"op": "camera", "view": "table"})
        grab("09-timer", crop=(2860, 205, 3420, 430))

    # The whole table after setup (§3).
    if wanted("10"):
        fresh()
        tts.send({"op": "deal"})
        tts.send({"op": "pawns"})
        tts.send({"op": "camera", "view": "table"})
        grab("10-table-setup")

    # A game in progress: the dungeon grown, tokens on rooms and on mats.
    if wanted("11") or wanted("12"):
        fresh()
        tts.send({"op": "deal"})
        for cell, kind, tok in P.ROOMS:
            tts.send({"op": "reveal", "color": "Red", "cell": list(cell), "token": tok})
        time.sleep(2.5)
        for color, tid in (("Yellow", "m-medium-1"), ("Yellow", "t-rare-1"), ("Green", "t-special-1"),
                           ("Green", "m-weak-2"), ("Blue", "t-common-1"), ("Red", "m-weak-1"), ("Red", "t-common-2")):
            tts.send({"op": "take", "color": color, "id": tid})
        tts.send({"op": "loot", "color": "Green", "id": "L1"})
        for color, cell in (("Red", (-2, -2)), ("Yellow", (-2, 1)), ("Green", (1, 2)), ("Blue", (1, 0))):
            tts.send({"op": "move", "color": color, "path": [list(cell)]})
        time.sleep(1.5)
        tts.send({"op": "camera", "view": "dungeon"})
        grab("11-dungeon-in-progress")
        tts.send({"op": "camera", "view": "play"})
        grab("12-table-in-progress")

    fresh()
    tts.send({"op": "camera", "view": "title"})
    print("errors:", tts.errors or "none")


if __name__ == "__main__":
    main()
