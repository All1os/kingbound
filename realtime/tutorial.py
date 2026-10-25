"""Plays the Kingbound real-time tutorial in a running Tabletop Simulator, for the team's video.

  python3 tutorial.py               play it (the save KINGBOUND-realtime must be loaded)
  python3 tutorial.py --dry-run     print the captions with their times, no TTS
  python3 tutorial.py --record out.mov   also record the screen (macOS screencapture) while it plays

It teaches the game for the team's presentation (at most 5 minutes, the team talks over the video):
the goal, setup, one player practising without the timer, bigger challenges, then a real game with
everyone at once. On screen there is only the name of each part and the symbols it costs; what to say
is in the cue sheet (--cues). The dice faces are set by this script so each rule is shown once,
including the document's own example (§5: 2 Attack, 1 Movement, 1 Magic against a medium monster).
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
# How it teaches (Yavuz, 2026-10-19: "explain it like to a child"; the team talks over the video in a
# presentation of at most 5 minutes, for a teacher who must understand the game). From the course
# book, Adams & Dormans, Game Mechanics: rules in small chunks, first in a safe place where mistakes
# cost nothing (p. 31); every chunk is one action and its visible result (skill atoms, p. 238-239);
# the order of karate training: one move, the move repeated, moves combined, a free fight (p. 241-242).
# So: the goal first, setup, one player practising without the timer, bigger challenges with the
# known moves sped up, then the real game with everyone at once.
STEPS = []          # (seconds to wait after, [commands])
rng = random.Random(5)
NEED = {"weak": "AA", "medium": "AAA", "strong": "AAAA"}


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


def reveal(color, cell, token=None, delay=0):
    return {"op": "reveal", "color": color, "cell": list(cell), "token": token, "delay": delay}


def move(color, *cells, delay=0):
    return {"op": "move", "color": color, "path": [list(c) for c in cells], "delay": delay}


def take(color, tid, delay=0): return {"op": "take", "color": color, "id": tid, "delay": delay}


def need_of(tid):
    """What a token costs: monsters by strength, treasures 2 Magic (§5)."""
    return NEED[tid.split("-")[1]] if tid.startswith("m-") else "GG"


def filler(syms):
    """Fills a roll up to 4 dice with symbols that don't add to what is needed."""
    others = [s for s in "MAG" if s not in syms] or ["M"]
    return syms + "".join(rng.choice(others) for _ in range(4 - len(syms)))


def act(color, kind, *args):
    """A move the viewer already knows, in one beat: the roll lands, the dice that count glow, it happens.
    kind: "reveal" (cell, token), "move" (cells...), "take" (token id), "fail" (strong monster, 3 Attack)."""
    # The symbols that count come first, so dice 1..n are the ones that glow.
    if kind == "fail":
        syms, n = "AAAM", 3
    elif kind == "take":
        need = need_of(args[0])
        syms, n = filler(need), len(need)
    else:
        syms, n = filler("MM"), 2
    cmds = [roll(color, syms), keep(color, *range(1, n + 1), delay=0.7)]
    if kind == "reveal":
        cmds.append(reveal(color, args[0], args[1] if len(args) > 1 else None, delay=0.8))
    elif kind == "move":
        cmds.append(move(color, *args, delay=0.8))
    elif kind == "take":
        cmds.append(take(color, args[0], delay=0.8))
    return cmds


# --- 1. what the game is: the goal first, so every rule after it has a reason
step(2.0, {"op": "reset", "stage": True}, {"op": "button", "show": False}, {"op": "nocaption"}, {"op": "timer", "hide": True})
step(4.5, cam("title"), cap("KINGBOUND", "This is Kingbound: a dungeon race for 3 to 5 players."))
step(5.5, cam("mats"), {"op": "timer", "left": 600}, {"op": "glowtag", "tag": "mat", "secs": 5},
     cap("GOAL", "The goal: have the most points when the 10-minute timer runs out."))
step(4.5, cam("table"), {"op": "glowtag", "tag": "pawn", "secs": 4},
     cap("NO TURNS", "There are no turns. Everybody plays at the same time."))

# --- 2. setup (§3), one piece at a time
step(4.5, cam("mats"), {"op": "deal"}, {"op": "timer", "hide": True},
     cap("SETUP", "Everyone takes a character and 4 dice."))
step(4.0, cam("dungeon"), {"op": "pawns"}, cap("SETUP", "All characters start in the start room, in the middle."))
step(4.0, cam("supply"), {"op": "shuffle"},
     cap("SETUP", "The other rooms are shuffled face down. Nobody knows what is inside."))
step(4.5, {"op": "glowtag", "tag": "token", "secs": 4}, {"op": "glowtag", "tag": "lootdeck", "secs": 4},
     cap("SETUP", "Monster tokens, treasure tokens and the Loot Deck wait next to them."))

# --- 3. practice: one player, no timer, every rule once and slowly (kihon)
step(4.0, cam("cell", cell=(0, -1), color="Red", distance=22), {"op": "spot", "color": "Red", "secs": 4},
     cap("PRACTICE", "First we watch one player, Bora, without the timer."))
step(3.5, cam("mat", color="Red", distance=10), roll("Red", "MAGM"),
     cap("DICE", "Each die shows one of three symbols."))
step(3.0, keep("Red", 1, 4), cap("MOVEMENT", "Green is Movement.", "M"))
step(3.0, keep("Red", 2), cap("ATTACK", "Red is Attack.", "A"))
step(3.0, keep("Red", 3), cap("MAGIC", "Blue is Magic.", "G"))
step(3.0, cam("cell", cell=(0, -1), color="Red", distance=22), roll("Red", "MMAG"),
     cap("ROLL", "Bora rolls his 4 dice."))
step(4.5, keep("Red", 1, 2), reveal("Red", (0, -1)),
     cap("NEW ROOM", "Two Movement: he takes a new room and puts it next to his room, doors connected.", "MM"))
step(2.5, roll("Red", "MGMA"), cap("MOVE", "He rolls again: two Movement...", "MM"))
step(3.5, keep("Red", 1, 3), move("Red", (0, -1)), cap("MOVE", "...and he walks into the new room. It is empty.", "MM"))
step(3.0, *act("Red", "reveal", (0, -2), "m-weak-1"), cap("NEW ROOM", "Two Movement again: another room...", "MM"))
step(3.0, cap("WEAK MONSTER", "...with a monster in it. A weak monster needs 2 Attack.", "AA"))
step(2.5, *act("Red", "move", (0, -2)), cap("MOVE", "He walks in.", "MM"))
step(3.5, roll("Red", "AMGM"), cap("FIGHT", "He rolls for the fight: only one Attack.", "AA"))
step(4.0, keep("Red", 1, secs=6), cap("REROLL", "Not enough? Keep the good dice and roll the others again."))
step(3.0, roll("Red", "AGM", dice=(2, 3, 4)))
step(4.0, keep("Red", 1, 2), take("Red", "m-weak-1"),
     cap("DEFEATED", "Two Attack: the monster is defeated and goes on his mat."))
step(4.0, cam("mat", color="Red", distance=11),
     cap("POINTS", "Everything on your mat is points. A weak monster is 1 point."))
# the same moves again, faster (kihon-kata)
step(2.5, cam("cell", cell=(-1, -2), color="Red", distance=22), *act("Red", "reveal", (-1, -2), "t-common-2"),
     cap("NEW ROOM", "Again: two Movement, a new room...", "MM"))
step(2.5, cap("TREASURE", "...with a treasure."))
step(2.5, *act("Red", "move", (-1, -2)), cap("MOVE", "He walks in...", "MM"))
step(3.5, *act("Red", "take", "t-common-2"), cap("TREASURE", "...and two Magic collect the treasure: 1 more point.", "GG"))
step(6.0, cam("chart"), cap("ACTIONS", "That is the whole game: roll, collect symbols, do an action, take the "
                                       "reward, roll again. This card shows every action."))

# --- 4. bigger challenges: known moves fast, new things slow (kata)
step(2.5, cam("cell", cell=(-1, 0), color="Yellow", distance=22), *act("Yellow", "reveal", (-1, 0), "m-medium-1"),
     cap("NEW ROOM", "Bigger monsters need more Attack. Anastasya finds one.", "MM"))
step(2.5, *act("Yellow", "move", (-1, 0)), cap("MEDIUM MONSTER", "A medium monster needs 3 Attack.", "AAA"))
step(3.5, roll("Yellow", "AAMG"), cap("FIGHT", "Two Attack, one Movement, one Magic: not enough.", "AAA"))
step(3.0, keep("Yellow", 1, 2, secs=4), roll("Yellow", "AG", dice=(3, 4)),
     cap("REROLL", "She keeps the Attacks and rolls the other two."))
step(3.5, keep("Yellow", 1, 2, 3), take("Yellow", "m-medium-1"),
     cap("DEFEATED", "Three Attack: 2 points."))
step(2.5, cam("cell", cell=(1, 0), color="Blue", distance=22), *act("Blue", "reveal", (1, 0), "m-strong-1"),
     cap("STRONG MONSTER", "Esma finds a strong monster: 4 Attack, 4 points.", "AAAA"))
step(2.0, *act("Blue", "move", (1, 0)))
step(2.5, roll("Blue", "AMAG"), cap("FIGHT", "Two Attack...", "AAAA"))
step(2.5, keep("Blue", 1, 3), roll("Blue", "GA", dice=(2, 4)), cap("REROLL", "...three..."))
step(2.5, keep("Blue", 1, 3, 4), roll("Blue", "M", dice=(2,)), cap("REROLL", "...still three."))
step(4.0, {"op": "spot", "color": "Blue", "secs": 4},
     cap("TOO HARD", "In the real game the timer never stops, so she can leave it and try something easier."))
step(2.5, cam("cell", cell=(0, 1), color="Green", distance=24), *act("Green", "reveal", (0, 1), "t-special-1"),
     cap("SPECIAL TREASURE", "Amira finds a special treasure.", "GG"))
step(2.0, *act("Green", "move", (0, 1)))
step(3.5, *act("Green", "take", "t-special-1"), {"op": "loot", "color": "Green", "id": "L1", "delay": 0.9},
     cap("SPECIAL TREASURE", "Two Magic: 1 point and a card from the Loot Deck.", "GG"))
step(5.0, cam("mat", color="Green", distance=10), {"op": "glowloot", "color": "Green", "secs": 5},
     cap("LOOT", "Her Iron Sword counts as one Attack in every fight.", "A"))
step(2.5, cam("cell", cell=(0, 2), color="Green", distance=26), *act("Green", "reveal", (0, 2), "m-weak-2"),
     cap("USE LOOT", "A weak monster needs 2 Attack...", "AA"))
step(2.0, *act("Green", "move", (0, 2)))
step(3.0, roll("Green", "AGMG"), cap("USE LOOT", "...she rolls only one...", "AA"))
step(4.0, keep("Green", 1), {"op": "glowloot", "color": "Green", "secs": 4}, take("Green", "m-weak-2", delay=0.5),
     cap("USE LOOT", "...and the sword is the second. Defeated.", "AA"))

# --- 5. the real game: everyone at once, the timer running (kumite)
step(3.0, {"op": "reset", "stage": True}, cam("table"), cap("REAL GAME", "Now a real game, from the start."))
step(3.5, {"op": "deal"}, {"op": "pawns"}, {"op": "timer", "left": 600},
     cap("10 MINUTES", "Same setup, and the timer is set to 10 minutes."))
step(1.5, cam("play"), {"op": "nocaption"}, {"op": "banner", "text": "GO!"}, {"op": "timer", "left": 600, "run": True})
# Each player's own sequence; one beat = every player acts at once.
SEQ = {
    "Red": [("reveal", (0, -1)), ("move", (0, -1)), ("reveal", (0, -2), "m-weak-1"), ("move", (0, -2)),
            ("take", "m-weak-1"), ("reveal", (-1, -2), "t-common-2"), ("move", (-1, -2)), ("take", "t-common-2"),
            ("reveal", (-2, -2), "m-medium-3"), ("move", (-2, -2)), ("take", "m-medium-3")],
    "Yellow": [("reveal", (-1, 0), "m-medium-1"), ("move", (-1, 0)), ("take", "m-medium-1"),
               ("reveal", (-2, 0), "t-rare-1"), ("move", (-2, 0)), ("take", "t-rare-1"),
               ("reveal", (-2, 1), "m-medium-2"), ("move", (-2, 1)), ("take", "m-medium-2"), ("move", (-2, 0)),
               ("reveal", (-2, -1), "t-common-3"), ("move", (-2, -1)), ("take", "t-common-3")],
    "Green": [("reveal", (0, 1), "t-special-1"), ("move", (0, 1)), ("take", "t-special-1"),
              ("reveal", (0, 2), "m-weak-2"), ("move", (0, 2)), ("take", "m-weak-2"),
              ("reveal", (-1, 2), "t-rare-3"), ("move", (-1, 2)), ("take", "t-rare-3"), ("move", (0, 2)),
              ("reveal", (1, 2), "t-rare-2"), ("move", (1, 2)), ("take", "t-rare-2")],
    "Blue": [("reveal", (1, 0), "m-strong-1"), ("move", (1, 0)), ("fail",), ("fail",),
             ("reveal", (2, 0), "t-common-1"), ("move", (2, 0)), ("take", "t-common-1"),
             ("reveal", (2, 1), "m-weak-3"), ("move", (2, 1)), ("take", "m-weak-3"), ("move", (2, 0)), ("move", (1, 0))],
}
BEATS = max(len(v) for v in SEQ.values())
for k in range(BEATS):
    cmds = []
    for color, seq in SEQ.items():
        if k < len(seq):
            cmds += act(color, *seq[k])
            if seq[k] == ("take", "t-special-1"):
                cmds.append({"op": "loot", "color": "Green", "id": "L1", "delay": 0.9})
    if k == 0:
        step(4.0, {"op": "banner"}, *cmds, cap("SAME TIME", "Everyone rolls and acts at the same time."))
    elif k == 1:
        step(1.9, *cmds, {"op": "timer", "rate": 25, "run": True},
             cap("FAST FORWARD", "Fast forward: the dungeon grows, monsters fall, treasures are taken."))
    else:
        step(1.9, *cmds)
step(3.5, cam("cell", cell=(1, 0), color="Blue", distance=24), {"op": "timer", "left": 11, "run": True},
     cap("LAST SECONDS", "The last seconds: Esma is back at the strong monster."))
step(2.5, roll("Blue", "AAAA"))
step(3.5, keep("Blue", 1, 2, 3, 4, secs=5), take("Blue", "m-strong-1"),
     cap("DEFEATED", "Four Attack, just in time: 4 points."))
step(1.5, {"op": "timer", "left": 0})
step(4.0, cam("mats"), {"op": "banner", "text": "TIME'S UP!"},
     cap("END", "When the timer ends, everyone stops at the same moment."))
SCORES = [("Yellow", 8, 2), ("Green", 8, 1), ("Blue", 6, 2), ("Red", 4, 2)]
step(5.5, {"op": "banner"}, {"op": "score", "lines": [{"text": f"{NAME[c]}: {p} points", "hex": HEX[c]} for c, p, _ in SCORES]},
     cap("SCORE", "Count the points on your mat: monsters and treasures."))
step(6.0, {"op": "score", "lines": [{"text": f"{NAME[c]}: {p} points · {m} monster{'s' if m > 1 else ''}", "hex": HEX[c]}
                                    for c, p, m in SCORES]},
     cap("TIE", "Anastasya and Amira both have 8. The tie goes to the most monsters: Anastasya has 2."))
step(4.5, cam("mat", color="Yellow", distance=12), {"op": "banner", "text": "ANASTASYA WINS!"},
     cap("WINNER", "Anastasya wins."))
step(4.0, {"op": "banner"}, {"op": "score"}, cam("table"),
     cap("KINGBOUND", "Roll fast, choose fast: the timer waits for no one."))


def total(): return sum(w for w, _ in STEPS)


def cue_sheet():
    """Time, the part's name on screen and what happens: for the people presenting over the video."""
    out = ["# Kingbound tutorial: what to say", "",
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
    ap = argparse.ArgumentParser(description="Kingbound real-time tutorial in Tabletop Simulator.")
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
        sys.exit("Tabletop Simulator is not running. Open it and load KINGBOUND-realtime (Games → Save & Load → prototipler).")
    if not version:
        sys.exit("TTS is running but the KINGBOUND-realtime save is not loaded.")
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
