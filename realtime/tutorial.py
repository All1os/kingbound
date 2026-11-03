"""Plays the NULLWAKE tutorial in a running Tabletop Simulator, for the team's gameplay video.

  python3 tutorial.py               play it (the save NULLWAKE must be loaded)
  python3 tutorial.py --dry-run     print the captions with their times, no TTS
  python3 tutorial.py --record out.mov   also record the screen (macOS screencapture) while it plays
  python3 tutorial.py --cues cues.md     write what to say, second by second

It follows the video script of the team's rules (2026-11-03, part 2): its 13 scenes in order, except that
opening a room (scene 4) comes before moving (scene 3), because at the start no room is open to move into.
On screen there is only the name of each part and the symbols it costs (Yavuz, 2026-10-19: the team talks
over the video); what to say is the document's voiceover, in the cue sheet, corrected where it doesn't match
the game: a room costs 2 Movement to open and 2 to enter, and there is no "special" symbol (Yavuz,
2026-11-03: "eski oyundaki gibi"). The dice faces are set by this script so each rule is shown once.
"""
import argparse
import json
import random
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

HEX = {"Red": "#E8574E", "Yellow": "#F2E64A", "Green": "#55D04B", "Blue": "#4FA3FF"}
NAME = {"Red": "Bora", "Yellow": "Anastasya", "Green": "Amira", "Blue": "Esma"}
# Die faces (tts/build.py DIE_FACES): 1-2 Movement, 3-4 Attack, 5-6 Magic.
FACE = {"M": [1, 2], "A": [3, 4], "G": [5, 6]}
LIMIT = 4 * 60 + 30
REC_LEAD = 1.0      # seconds of recording before the first step


class TTS:
    """Same transport as bots/play.py: one JSON string per command to localhost:39999."""

    def __init__(self):
        self.replies, self.errors = [], []
        try:
            self.srv = socket.socket()
            self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.srv.bind(("127.0.0.1", 39998))
            self.srv.listen(5)
            threading.Thread(target=self._listen, daemon=True).start()
        except OSError:
            self.srv = None

    def _listen(self):
        dec = json.JSONDecoder()
        while True:
            try:
                c, _ = self.srv.accept()
            except OSError:
                return
            buf = b""
            while chunk := c.recv(65536):
                buf += chunk
            c.close()
            text, i = buf.decode("utf-8", "replace").strip(), 0
            while i < len(text):
                try:
                    msg, i = dec.raw_decode(text, i)
                except json.JSONDecodeError:
                    break
                while i < len(text) and text[i].isspace():
                    i += 1
                if msg.get("messageID") == 4:
                    data = msg.get("customMessage") or {}
                    self.replies.append(data)
                    if data.get("kind") == "error":
                        self.errors.append(data.get("text"))
                        print("   TTS:", data.get("text"))
                elif msg.get("messageID") == 3:
                    self.errors.append(msg.get("error"))
                    print("   TTS Lua error:", msg.get("error"))

    def send(self, data):
        payload = json.dumps({"messageID": 2, "customMessage": {"json": json.dumps(data, ensure_ascii=False)}}).encode()
        s = socket.create_connection(("127.0.0.1", 39999), timeout=3)
        s.sendall(payload)
        s.close()

    def hello(self, wait=4.0):
        self.send({"op": "hello"})
        end = time.time() + wait
        while time.time() < end:
            for r in self.replies:
                if r.get("kind") == "hello":
                    return r.get("text")
            time.sleep(0.1)
        return None


# ------------------------------------------------------------------ the script
# How it teaches (Yavuz, 2026-10-19: "explain it like to a child"; from the course book, Adams & Dormans:
# rules in small chunks, first where mistakes cost nothing, p. 31; one action and its visible result each,
# p. 238-239): one player at a time and slowly for each new rule (scenes 2-8), then everyone at once, fast,
# with moves the viewer already knows (scenes 9 and 11).
STEPS = []          # (seconds to wait after, [commands])
rng = random.Random(5)


def step(wait, *cmds):
    STEPS.append((wait, list(cmds)))


def cap(head, say, icons=""):
    """Only head (and the icons) is shown; say is the presenters' line in the cue sheet."""
    return {"op": "caption", "head": head, "icons": icons, "say": say}


def cam(view, **kw): return {"op": "camera", "view": view, **kw}


def faces(syms):
    return [rng.choice(FACE[s]) for s in syms]


def roll(color, syms, dice=(1, 2, 3, 4)):
    return {"op": "roll", "color": color, "dice": list(dice), "values": faces(syms)}


def keep(color, *dice, secs=3, delay=0):
    return {"op": "keep", "color": color, "dice": list(dice), "secs": secs, "delay": delay}


def reveal(color, cell, token=None, delay=0, rid=None):
    d = {"op": "reveal", "color": color, "cell": list(cell), "token": token, "delay": delay}
    if rid:
        d["id"] = rid
    return d


def move(color, *cells, delay=0):
    return {"op": "move", "color": color, "path": [list(c) for c in cells], "delay": delay}


def take(color, tid, delay=0): return {"op": "take", "color": color, "id": tid, "delay": delay}


def hit(color, tid, n, delay=0): return {"op": "hit", "color": color, "id": tid, "n": n, "delay": delay}


def place(color, tid, slot, delay=0): return {"op": "place", "color": color, "id": tid, "slot": slot, "delay": delay}


def filler(syms):
    """Fills a roll up to 4 dice with symbols that don't add to what is needed."""
    others = [s for s in "MAG" if s not in syms] or ["M"]
    return syms + "".join(rng.choice(others) for _ in range(4 - len(syms)))


def act(color, kind, *args):
    """A move the viewer already knows, in one beat: the roll lands, the dice that count glow, it happens.
    kind: "reveal" (cell, token or None, room id), "move" (cells...), "take" (token id), "hit" (monster id,
    Attacks), "place" (object id, slot: no dice), "blocked" (2 Movement, but the way is shut), "wait" (no luck)."""
    if kind == "place":
        return [place(color, args[0], args[1])]
    if kind == "wait":      # a roll with nothing useful in it
        return [roll(color, rng.choice(["AAGG", "AGAG", "GGAA"]))]
    if kind == "take":
        syms, n = filler("GG"), 2
    elif kind == "hit":
        syms, n = filler("A" * args[1]), args[1]
    else:
        syms, n = filler("MM"), 2
    cmds = [roll(color, syms), keep(color, *range(1, n + 1), delay=0.7)]
    if kind == "reveal":
        cmds.append(reveal(color, args[0], args[1] if len(args) > 1 else None, delay=0.8,
                           rid=args[2] if len(args) > 2 else None))
    elif kind == "move":
        cmds.append(move(color, *args, delay=0.8))
    elif kind == "take":
        cmds.append(take(color, args[0], delay=0.8))
    elif kind == "hit":
        cmds.append(hit(color, args[0], args[1], delay=0.8))
    elif kind == "blocked":
        cmds.append({"op": "spot", "color": color, "secs": 3, "delay": 0.8})
    return cmds


# --- scene 1: game start
step(2.0, {"op": "reset", "stage": True}, {"op": "button", "show": False}, {"op": "nocaption"}, {"op": "timer", "hide": True})
step(6.0, cam("title"), cap("NULLWAKE", "NULLWAKE is a competitive exploration game. Players explore the station's rooms, fight "
                                        "monsters, collect treasures, and escape before time runs out."))
step(4.5, cam("mats"), {"op": "deal"}, {"op": "glowtag", "tag": "mat", "secs": 4},
     cap("SETUP", "Everyone sits at their own mat and takes 4 dice."))
step(4.5, cam("dungeon"), {"op": "pawns"}, cap("SAFE ZONE", "Every character starts in the Safe Zone."))
step(4.5, cam("supply"), {"op": "shuffle"}, {"op": "glowtag", "tag": "token", "secs": 4},
     cap("SETUP", "The rooms are shuffled face down. Monster and treasure tokens wait next to them."))
step(6.0, cam("play"), {"op": "timer", "left": 600}, {"op": "label", "text": "ROUND 1 · COLLECT POINTS"},
     cap("TWO ROUNDS", "The game has two rounds of five minutes: scoring points, then escaping. "
                       "All players act simultaneously."))

# --- scene 2: first dice roll
step(4.0, cam("mats"), roll("Red", "MMAG"), roll("Yellow", "GAMM"), roll("Green", "AGMG"), roll("Blue", "MAAG"),
     cap("ROLL", "At the beginning of each game cycle, all players roll their dice simultaneously."))
step(3.5, cam("mat", color="Red", distance=11), keep("Red", 1, 2), cap("MOVEMENT", "Green is Movement: it moves you through the station.", "M"))
step(3.0, keep("Red", 3), cap("ATTACK", "Red is Attack: it is used against monsters.", "A"))
step(3.0, keep("Red", 4), cap("MAGIC", "Blue is Magic: it takes treasures and special objects.", "G"))
step(4.0, keep("Red", 1, 2, secs=5), cap("REROLL", "Keep the results you need and reroll the others, once. "
                                                     "Everyone rerolls at the same time."))
step(3.0, roll("Red", "MM", dice=(3, 4)))
step(3.0, keep("Red", 1, 2, 3, 4), cap("LOCKED", "After the reroll the results are locked until the next cycle. "
                                                 "Each die is used once."))

# --- scene 4 (before 3): opening a new room
step(4.5, cam("cell", cell=(0, -1), color="Red", distance=22), keep("Red", 1, 2), reveal("Red", (0, -1), delay=0.4),
     cap("NEW ROOM", "Two Movement open a new room: take a room card and connect its passage to an open passage.", "MM"))
step(4.0, cap("PASSAGES", "Passages must connect to passages. You cannot connect a passage to a wall or block a passage."))

# --- scene 3: movement
step(4.0, keep("Red", 3, 4), move("Red", (0, -1), delay=0.4),
     cap("MOVE", "Two more Movement: Bora moves into the room. You can only move through open passages.", "MM"))

# --- scene 5: monster encounter
step(3.0, roll("Red", "MMAG"), cap("NEXT CYCLE", "When everyone has finished, the next cycle begins."))
step(4.5, keep("Red", 1, 2), reveal("Red", (0, -2), "m-strong-1", delay=0.4),
     cap("MONSTER", "Some rooms contain monsters.", "MM"))
step(4.5, cam("cell", cell=(0, -2), distance=10), cap("3 HP", "Each monster has health. This Anomaly has 3 HP.", "AAA"))
step(3.0, cam("cell", cell=(0, -2), color="Red", distance=22), roll("Red", "MMAA"), cap("NEXT CYCLE", "Next cycle."))
step(4.0, keep("Red", 1, 2), move("Red", (0, -2), delay=0.4),
     cap("SAME ROOM", "To attack a monster, the player must be in the same room.", "MM"))

# --- scene 6: monster battle (3 HP: 2 damage, then 1 in the next cycle)
step(4.0, keep("Red", 3, 4), hit("Red", "m-strong-1", 2, delay=0.4),
     cap("2 DAMAGE", "Each Attack deals one damage. Two Attack: two damage.", "AA"))
step(3.5, cam("cell", cell=(0, -2), distance=10), cap("1 HP LEFT", "The monster has one health left, and the damage stays."))
step(3.0, cam("cell", cell=(0, -2), color="Red", distance=22), roll("Red", "AGMM"), cap("NEXT CYCLE", "In the next cycle..."))
step(4.5, keep("Red", 1), hit("Red", "m-strong-1", 1, delay=0.4),
     cap("DEFEATED", "...one more Attack, and the monster is defeated. It goes to his mat.", "A"))
step(4.5, cam("mat", color="Red", distance=11), cap("3 POINTS", "An Anomaly gives 3 points. You don't have to fight every "
                                                                  "monster: you can look for another route."))

# --- scene 7: treasure collection (Anastasya, the known moves faster)
step(3.0, cam("cell", cell=(-1, 0), color="Yellow", distance=22), *act("Yellow", "reveal", (-1, 0), "t-module-1"),
     cap("TREASURE", "Three types of treasure can be found in the station.", "MM"))
step(2.5, *act("Yellow", "move", (-1, 0)))
step(3.5, *act("Yellow", "take", "t-module-1"), cap("MODULE", "Two Magic take a treasure: a Module...", "GG"))
step(2.5, cam("cell", cell=(-2, 0), color="Yellow", distance=22), *act("Yellow", "reveal", (-2, 0), "t-archive-1"))
step(2.5, *act("Yellow", "move", (-2, 0)))
step(3.0, *act("Yellow", "take", "t-archive-1"), cap("ARCHIVE", "...an Archive...", "GG"))
step(2.5, *act("Yellow", "reveal", (-2, -1), "t-specimen-1"))
step(2.5, *act("Yellow", "move", (-2, -1)))
step(3.0, *act("Yellow", "take", "t-specimen-1"), cap("SPECIMEN", "...and a Specimen.", "GG"))
step(7.0, cam("mat", color="Yellow", distance=12),
     cap("COMBINATIONS", "Treasures give points alone or in combinations. Two Modules and one Archive give five points. "
                         "Three Archives give four. A Module, an Archive and a Specimen give four."))
step(3.5, cap("ONE EACH", "A single treasure counts in one combination only."))

# --- scene 8: the special tile
step(3.0, cam("cell", cell=(0, 1), color="Green", distance=22), *act("Green", "reveal", (0, 1), None, "special"),
     cap("SPECIAL TILE", "Amira opens a special room: the Integration Chamber.", "MM"))
step(5.0, cam("cell", cell=(0, 1), distance=9),
     cap("4 SLOTS", "It has four slots for special objects. They are linked to the special task of round two."))
step(4.0, cap("OBJECTS", "The objects hide among the treasure tokens. Take one with two Magic now; you place it in round two."))

# --- scene 9: end of the first round (everyone at once, fast)
R1 = {
    "Red": [("reveal", (-1, -2), "o-4"), ("move", (-1, -2)), ("take", "o-4"), ("reveal", (-1, -1), "t-archive-2"),
            ("move", (-1, -1)), ("take", "t-archive-2"),
            # Bora ends round 1 in the Unregistered Sector (0,-1): no rock goes there, as a player stands in it.
            ("move", (-1, -2)), ("move", (0, -2)), ("move", (0, -1))],
    "Yellow": [("reveal", (-2, -2)), ("move", (-2, 0)), ("reveal", (-2, 1), "m-medium-1"), ("move", (-2, 1)), ("hit", "m-medium-1", 2),
               ("move", (-2, 0)), ("move", (-1, 0)), ("reveal", (-1, 1), "o-3"), ("move", (-1, 1)), ("take", "o-3")],
    "Green": [("move", (0, 1)), ("reveal", (1, 1), "o-2"), ("move", (1, 1)), ("take", "o-2"), ("reveal", (1, 2)), ("move", (0, 1)),
              ("reveal", (0, 2), "m-weak-2"), ("move", (0, 2)), ("hit", "m-weak-2", 1)],
    "Blue": [("reveal", (1, 0)), ("move", (1, 0)), ("reveal", (2, 0), "t-module-2"), ("move", (2, 0)), ("take", "t-module-2"),
             ("reveal", (2, -1), "m-weak-1"), ("move", (2, -1)), ("hit", "m-weak-1", 1), ("reveal", (1, -1), "m-weak-3"),
             ("move", (2, 0)), ("reveal", (2, 1), "o-1"), ("move", (2, 1)), ("take", "o-1")],
}
BEAT = 1.9
beats = max(len(v) for v in R1.values())
for k in range(beats):
    cmds = [c for color, seq in R1.items() if k < len(seq) for c in act(color, *seq[k])]
    if k == 0:
        step(4.0, cam("play"), {"op": "timer", "left": 590, "run": True}, *cmds,
             cap("SAME TIME", "Players explore different parts of the station at the same time."))
    elif k == 1:
        step(BEAT, *cmds, {"op": "timer", "rate": 12, "run": True},   # 12 beats of 1.9 s: about 9:46 down to 5:00
             cap("FAST FORWARD", "Everyone chooses their own route and how to spend their dice."))
    else:
        step(BEAT, *cmds)
step(4.5, {"op": "timer", "left": 300}, {"op": "banner", "text": "ROUND 1 OVER"},
     cap("ROUND 1 OVER", "The first round is complete. Now the hardest part begins: escaping from the station."))

# --- scene 10: the event card
ROCKS = [(1, 0), (-2, -2), (1, 2)]      # every Unregistered Sector but (0,-1), where Bora stands
step(2.5, {"op": "banner"}, cam("event"), {"op": "round2", "cells": [list(c) for c in ROCKS]},
     cap("EVENT", "At the beginning of the second round, an event card is revealed. This time, a rockfall."))
step(3.0, {"op": "banner"})      # the round 2 banner lies over the card: off, so the card reads
step(5.0, cam("dungeon"), {"op": "banner"},
     cap("ROCKS", "Rocks fill every empty room, the Unregistered Sectors. Rooms with players, monsters, "
                 "treasures and special objects stay free."))
step(4.0, cap("BLOCKED", "Blocked rooms can no longer be used for movement, and no new rooms can be opened."))

# --- scene 11: escape
R2 = {
    "Green": [("move", (0, 1)), ("place", "o-2", 2), ("move", (0, 0))],
    "Red": [("move", (0, 0)), ("move", (0, 1)), ("place", "o-4", 4), ("move", (0, 0))],
    "Yellow": [("move", (-1, 0)), ("move", (0, 0)), ("move", (0, 1)), ("place", "o-3", 3), ("move", (0, 0))],
    # Esma: two unlucky cycles, then the rocks at (1,0) send her the long way round (shown on its own beat).
    "Blue": [("move", (2, 0)), ("wait",), ("wait",), ("blocked",), ("move", (2, -1)), ("move", (1, -1)), ("move", (0, -1)),
             ("move", (0, 0)), ("move", (0, 1)), ("place", "o-1", 1)],
}
beats = max(len(v) for v in R2.values())
for k in range(beats):
    cmds = [c for color, seq in R2.items() if k < len(seq) for c in act(color, *seq[k])]
    if k == 0:
        step(4.5, *cmds, {"op": "timer", "left": 300, "rate": 1, "run": True},
             cap("ESCAPE", "Now everyone must complete the special task and return to the Safe Zone."))
    elif k == 1:
        step(4.5, *cmds, {"op": "timer", "rate": 11, "run": True},   # ~25 s of beats left: 5:00 runs out at the end
             cap("PLACE IT", "Amira places her object in the Integration Chamber: her special task is completed."))
    elif k == 2:
        step(4.0, *cmds, cap("ESCAPED", "And she is back in the Safe Zone."))
    elif k == 3:
        step(4.0, *cmds, cam("cell", cell=(2, 0), color="Blue", distance=22),
             cap("DETOUR", "Esma's way home is blocked by rocks: she has to take the long way round."))
    elif k == 4:
        step(BEAT, *cmds, cam("dungeon"), {"op": "nocaption"})
    else:
        step(BEAT, *cmds)

# --- scene 12: end of the game
step(4.0, {"op": "timer", "left": 0}, {"op": "banner", "text": "TIME'S UP!"}, cap("TIME'S UP", "Time is up! Everyone stops."))
ESC = [("Yellow", True, 6, "4 + 2"), ("Red", True, 4, "3 + 1"), ("Green", True, 1, "1"), ("Blue", False, 4, "")]
step(6.5, {"op": "banner"},
     {"op": "score", "lines": [{"text": f"{NAME[c]}: " + ("escaped" if ok else "trapped, loses the points"),
                                "hex": HEX[c] if ok else "#E28C24"} for c, ok, _, _ in ESC]},
     cap("ESCAPED?", "Players who completed the special task and are in the Safe Zone keep their points. "
                     "Esma placed her object but didn't make it back: she loses hers."))
step(6.5, {"op": "score", "lines": [{"text": f"{NAME[c]}: " + (f"{p} point{'s' if p != 1 else ''} ({why})" if ok else "0 points"),
                                     "hex": HEX[c] if ok else "#E28C24"} for c, ok, p, why in ESC]},
     cap("SCORE", "Count the saved points: monsters, plus treasure alone or in combinations."))
# The score list goes away here: the winner banner sits in the middle of the screen, over its last line.
step(4.5, cam("mat", color="Yellow", distance=12), {"op": "score"}, {"op": "banner", "text": "ANASTASYA WINS!"},
     cap("WINNER", "The player with the most saved points wins. A tie is a draw."))

# --- scene 13: finale
step(5.0, {"op": "banner"}, {"op": "score"}, cam("table"),
     cap("NULLWAKE", "Explore, collect, and get out before the station collapses."))


def total(): return sum(w for w, _ in STEPS)


def cue_sheet():
    """Time, the part's name on screen and what happens: for the people presenting over the video."""
    out = ["# NULLWAKE gameplay video: what to say", "",
           f"The video is {mmss(total())} long. On screen there is only the name of each part (and the dice symbols it "
           "costs). Each line below starts at its time; one short sentence fits before the next one.", "",
           "| Time | On screen | Say |", "|---|---|---|"]
    # --record starts the screen recording 1 s before the first step, so the video's clock is 1 s ahead.
    clock, last = REC_LEAD, None
    for w, cmds in STEPS:
        for c in cmds:
            if c["op"] == "caption":
                icons = c.get("icons", "")
                sym = {"M": "Movement", "A": "Attack", "G": "Magic"}
                cost = (" (" + ", ".join(f"{icons.count(k)} {sym[k]}" for k in "MAG" if k in icons) + ")") if icons else ""
                head = (c["head"] + cost) if c["head"] != last else ""
                out.append(f"| {mmss(clock)} | {head} | {c['say']} |")
                last = c["head"]
        clock += w
    return "\n".join(out) + "\n"


def mmss(s): return f"{int(s // 60)}:{int(s % 60):02d}"


def main():
    ap = argparse.ArgumentParser(description="NULLWAKE tutorial in Tabletop Simulator.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--record", metavar="FILE", help="record the screen to this .mov while playing")
    ap.add_argument("--cues", metavar="FILE", help="write the presenters' cue sheet (time, part, what happens) as Markdown")
    a = ap.parse_args()
    length = total()
    assert length <= LIMIT, f"tutorial is {mmss(length)}, over 4:30"
    if a.cues:
        Path(a.cues).expanduser().write_text(cue_sheet())
        print("cue sheet →", a.cues)
    if a.dry_run:
        clock = 0.0
        for w, cmds in STEPS:
            for c in cmds:
                if c["op"] == "caption":
                    print(f"[{mmss(clock)}] {c['head']}: {c['say']}")
            clock += w
        print(f"[{mmss(clock)}] end ({len(STEPS)} steps)")
        return
    if a.cues:
        return
    tts = TTS()
    try:
        version = tts.hello()
    except OSError:
        sys.exit("Tabletop Simulator is not running. Open it and load NULLWAKE (Games → Save & Load → prototipler).")
    if not version:
        sys.exit("TTS is running but the NULLWAKE save is not loaded.")
    # The mouse goes to the left edge, off the table, so nothing on the table lights up under it.
    subprocess.run(["swift", "-e", "import CoreGraphics; CGWarpMouseCursorPosition(CGPoint(x: 4, y: 760))"],
                   capture_output=True)
    rec = None
    if a.record:
        # The table goes back to its starting places before the camera rolls, so the video opens clean.
        tts.send({"op": "reset", "stage": True})
        tts.send({"op": "camera", "view": "title"})
        time.sleep(4.0)
        # -v video, -V seconds, -x no sounds, -k show clicks off; a few seconds of margin at the end.
        rec = subprocess.Popen(["screencapture", "-v", "-x", "-V" + str(int(length + 4)), str(Path(a.record).expanduser())])
        time.sleep(REC_LEAD)
    print(f"Save {version}. Tutorial: {len(STEPS)} steps, {mmss(length)}.")
    # Every step starts at its planned time from the start, so sending commands never adds up to a
    # drift (the first test ran 7 s long) and the cue sheet's times match the video.
    start = time.time()
    due = start
    for w, cmds in STEPS:
        for c in cmds:
            tts.send(c)
        due += w
        time.sleep(max(0.0, due - time.time()))
    tts.send({"op": "button", "show": True})
    print(f"Done in {mmss(time.time() - start)}" + (f", {len(tts.errors)} TTS errors" if tts.errors else ""))
    if rec:
        rec.wait()
        print("Recording saved:", a.record)


if __name__ == "__main__":
    main()
