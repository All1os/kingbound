"""Four bots play Kingbound in a running Tabletop Simulator, for the presentation video.

  python3 bots/play.py                  full game, from setup to the King's Trial
  python3 bots/play.py --mode demo      short game: starts mid-game (levels 6-8), ends with the Trial
  python3 bots/play.py --speed 1.5      faster; 0.7 is slower (default 1.0)
  python3 bots/play.py --seed 12        another game; the same seed always replays the same game
  python3 bots/play.py --dry-run        print the game and how long it takes, without TTS
  python3 bots/play.py --find 10        list seeds whose game shows every mechanic
  python3 bots/play.py --no-camera      don't move the camera (by default it follows every step)
  python3 bots/play.py stop             stop a running game (Ctrl+C in its window does the same)

Before starting: Tabletop Simulator open, the KINGBOUND-prototype save loaded (Games → Save & Load →
prototipler). The bots decide everything here in Python (engine.py) and send TTS only "show this"
commands through its External Editor API: we send on localhost:39999 and TTS answers on 39998.
"""
import argparse
import json
import os
import signal
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import Game  # noqa: E402

# Seeds picked with --find: each game has a help deal, sabotage, Dig Deep, an objective and a Trial,
# and runs to a good length at speed 1.0. Any other seed works too.
DEFAULT_SEED = {"full": 1, "demo": 94}
PID_FILE = Path(tempfile.gettempdir()) / "kingbound-bots.pid"
HEX = {"Red": "#E8574E", "Yellow": "#F2E64A", "Green": "#55D04B", "Blue": "#4FA3FF"}

# ------------------------------------------------------------------ pacing
# Seconds at speed 1.0. A step with a caption lasts at least as long as the caption takes to read.
BASE = {"turn": 0.9, "roll": 1.3, "reveal": 1.3, "damage": 0.5, "ability": 0.8, "ready": 0.6,
        "player": 0.3, "offer": 1.4, "buy": 0.9, "unoffer": 0.6, "loot": 1.0, "item": 0.8,
        "objective": 1.6, "clear": 0.9, "reshuffle": 1.3, "board": 6.0, "win": 8.0,
        "say": 0.0, "fightround": 0.0}


def read_time(text):
    return min(6.0, max(1.8, 0.9 + len(text) / 21.0))


def duration(e):
    op = e["op"]
    n = len(e.get("cards", [])) or len(e.get("path", []))
    if op == "move":
        base = 0.4 + 0.35 * n
    elif op == "draw":
        base = 0.4 + 0.3 * n
    elif op == "discard":
        base = 0.4 + 0.2 * n
    elif op == "play":
        base = 0.6 + 0.35 * n
    elif op == "setup":
        k = sum(5 + len(p["hand"]) + len(p["items"]) for p in e["players"])
        base = 2.5 + 0.12 * k
    else:
        base = BASE.get(op, 0.5)
    if e.get("say"):
        base = max(base, read_time(e["say"]))
    return base


def total_time(events, speed=1.0):
    return sum(duration(e) for e in events) / speed


def mmss(s):
    return f"{int(s // 60):02d}:{int(s % 60):02d}"


# ------------------------------------------------------------------ choosing a good game
def game_for(seed, mode):
    g = Game(seed, mode)
    g.play()
    return g


def shows_everything(g, mode):
    s = g.stats
    if not g.winner or s["help_deals"] < 1 or s["sabotage"] < 1 or s["digs"] < 1 or s["trials"] < 1:
        return False
    if s["objectives"] < 1:
        return False
    t = total_time(g.events)
    return (180 <= t <= 300) if mode == "demo" else (8 * 60 <= t <= 20 * 60)


def find(mode, start, count):
    found, seed = [], start
    while len(found) < count and seed < start + 5000:
        g = game_for(seed, mode)
        if shows_everything(g, mode):
            found.append((seed, g))
        seed += 1
    return found


# ------------------------------------------------------------------ talking to TTS
class TTS:
    def __init__(self):
        self.replies = []
        self.errors = []
        self.srv = None
        try:
            self.srv = socket.socket()
            self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.srv.bind(("127.0.0.1", 39998))
            self.srv.listen(5)
            threading.Thread(target=self._listen, daemon=True).start()
        except OSError:
            print("Note: port 39998 is busy (another script editor?). TTS errors won't be shown here.")
            self.srv = None

    def _listen(self):
        dec = json.JSONDecoder()
        while True:
            try:
                c, _ = self.srv.accept()
            except OSError:
                return
            buf = b""
            while True:
                chunk = c.recv(65536)
                if not chunk:
                    break
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
                self._handle(msg)

    def _handle(self, msg):
        mid = msg.get("messageID")
        if mid == 4:   # sendExternalMessage from our Global script
            data = msg.get("customMessage") or {}
            self.replies.append(data)
            if data.get("kind") == "error":
                self.errors.append(data.get("text"))
                print(f"   TTS: {data.get('text')}")
        elif mid == 3:  # Lua error
            self.errors.append(msg.get("error"))
            print(f"   TTS Lua error: {msg.get('error')}")

    def send(self, data):
        # One JSON string per command: TTS passes nested lists of a custom message to Lua as
        # C# objects, so global.lua decodes the string itself.
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


# ------------------------------------------------------------------ running a game
class Director:
    def __init__(self, tts, speed, camera):
        self.tts, self.speed, self.camera = tts, speed, camera
        self.mirror = {}
        self.order = []
        self.active = None
        self.view = None
        self.fighting = False

    def status(self):
        # The player whose turn it is gets an arrow, so the colours on the table and the names match up.
        lines = []
        for color in self.order:
            m = self.mirror[color]
            mark = "▶" if color == self.active else "●"
            lines.append({"text": f"{mark} {m['name']} · {m['char']} · level {m['level']} · HP {m['hp']}/{m['max']} · {m['gold']} gold",
                          "hex": HEX[color]})
        self.tts.send({"op": "status", "lines": lines})

    # The camera goes to wherever the next step happens: the board for turns, rolls and moves, the
    # fight area, the acting player's hand and Abilities, their items and board (HP, gold), the level
    # track when a level changes, the Merchant's cards, a deck being reshuffled. Yavuz asked for every
    # event to be on screen (2026-10-13). global.lua turns the view names into camera positions.
    def target(self, e):
        op, c = e["op"], e.get("color")
        # In a fight the camera stays on the fight area for the fighter's own cards, digs, Abilities
        # and HP; it only leaves for another player stepping in (sabotage, a boost, an item), so it
        # doesn't swing round the table every few seconds (Yavuz: "it turns around itself", 2026-10-13).
        if op == "player":
            before = self.mirror.get(c)
            if before and before.get("level") != e.get("level"):
                return ("track", None)      # a level change is always shown on the track
        if self.fighting and op in ("draw", "discard", "ability", "player", "item") and c == self.active:
            return ("fight", None)
        if op in ("board", "setup"):
            return ("table", None)
        if op in ("turn", "move"):
            return ("board", None)
        if op == "roll":
            return ("board", None) if e.get("spot") == "board" else ("fight", None)
        if op in ("reveal", "play", "damage", "fightround", "clear"):
            return ("fight", None)
        if op in ("draw", "discard", "ready", "ability"):
            return ("hand", c)
        if op in ("objective", "loot", "buy"):
            return ("gear", c)
        if op == "item":
            return ("fight", None) if e.get("to") == "fight" else ("gear", c)
        if op in ("offer", "unoffer"):
            return ("shop", None)
        if op == "reshuffle":
            return ("decks", None) if e.get("deck") in ("action", "loot") else ("wilds", None)
        if op == "player":
            before = self.mirror.get(c)
            if before and before.get("level") != e.get("level"):
                return ("track", None)
            if e.get("say"):
                return ("gear", c)
        return None

    def aim(self, e):
        if e["op"] == "reveal" and e.get("deck") in ("w1", "w2", "w3", "champ"):
            self.fighting = True
        if e["op"] == "turn":
            self.fighting = False
        if not self.camera:
            return
        t = self.target(e)
        if t and t != self.view:
            self.view = t
            self.tts.send({"op": "camera", "view": t[0], "color": t[1]})

    def show(self, e):
        t = 1.0 / self.speed
        op = e["op"]
        if op == "turn":
            self.active = e["color"]
        self.aim(e)
        if e.get("say"):
            self.tts.send({"op": "caption", "head": e.get("head", ""), "text": e["say"], "color": self.active})
        if op in ("say", "fightround"):
            return
        if op == "turn":
            self.tts.send({"op": "highlight", "color": e["color"], "t": 2.5 * t, "turn": True})
            if len(self.mirror) == 4:
                self.status()
            return
        msg = {k: v for k, v in e.items() if k not in ("say", "head")}
        msg["t"] = {"move": 0.35, "draw": 0.15, "play": 0.2, "discard": 0.12, "setup": 0.12,
                    "board": 0.05, "roll": 1.0}.get(op, 1.0) * t
        self.tts.send(msg)
        if op == "player":
            self.mirror[e["color"]] = e
            if e["color"] not in self.order:
                self.order.append(e["color"])
            if len(self.mirror) == 4:
                self.status()
        if op == "setup":
            self.order = [p["color"] for p in e["players"]]

    def run(self, events):
        self.tts.send({"op": "reset"})
        time.sleep(2.0)
        start = time.time()
        for i, e in enumerate(events):
            self.show(e)
            time.sleep(duration(e) / self.speed)
        return time.time() - start


def stop_running():
    try:
        pid = int(PID_FILE.read_text())
    except (OSError, ValueError):
        print("No running bot game found.")
        return
    try:
        os.kill(pid, signal.SIGINT)
        print(f"Stopped the bot game (process {pid}).")
    except ProcessLookupError:
        print("No running bot game found.")
        PID_FILE.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser(description="Four Kingbound bots play in Tabletop Simulator.")
    ap.add_argument("command", nargs="?", default="play", choices=["play", "stop"])
    ap.add_argument("--mode", choices=["full", "demo"], default="full")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--dry-run", action="store_true", help="print the game and its length, no TTS")
    ap.add_argument("--find", type=int, metavar="N", help="list N seeds that show every mechanic")
    ap.add_argument("--no-camera", action="store_true", help="leave the camera alone (it follows every step by default)")
    a = ap.parse_args()
    if a.command == "stop":
        stop_running()
        return
    if a.speed <= 0:
        ap.error("--speed must be above 0")
    if a.find:
        for seed, g in find(a.mode, a.seed or 1, a.find):
            print(f"seed {seed}: {g.winner.label} wins, {g.round} rounds, {mmss(total_time(g.events))} at speed 1, "
                  f"{g.stats['help_deals']} help deals, {g.stats['sabotage']} sabotage, {g.stats['digs']} digs, "
                  f"{g.stats['objectives']} objectives, {g.stats['trials']} Trial attempts")
        return
    seed = a.seed if a.seed is not None else DEFAULT_SEED[a.mode]
    g = game_for(seed, a.mode)
    length = total_time(g.events, a.speed)
    who = g.winner.label if g.winner else "nobody"
    print(f"Kingbound bots: {a.mode} game, seed {seed}, speed {a.speed}: {len(g.events)} steps, about {mmss(length)}. "
          f"{who} wins in round {g.round}.")
    if a.dry_run:
        clock = 0.0
        for e in g.events:
            if e.get("say"):
                print(f"[{mmss(clock)}] {e['say']}")
            clock += duration(e) / a.speed
        print(f"[{mmss(clock)}] end")
        return
    tts = TTS()
    try:
        version = tts.hello()
    except OSError:
        print("Tabletop Simulator is not running (nothing on localhost:39999). Open it and load the "
              "KINGBOUND-prototype save (Games → Save & Load → prototipler), then run this again.")
        sys.exit(1)
    if not version:
        print("Tabletop Simulator is running but the Kingbound save is not loaded. Load KINGBOUND-prototype "
              "(Games → Save & Load → prototipler), then run this again.")
        sys.exit(1)
    PID_FILE.write_text(str(os.getpid()))
    director = Director(tts, a.speed, not a.no_camera)

    def bye(*_):
        try:
            tts.send({"op": "stop"})
        except OSError:
            pass
        PID_FILE.unlink(missing_ok=True)
        print("\nStopped.")
        os._exit(0)

    signal.signal(signal.SIGINT, bye)
    signal.signal(signal.SIGTERM, bye)
    print(f"Save version {version}. Playing... (stop: Ctrl+C, or python3 bots/play.py stop)")
    took = director.run(g.events)
    PID_FILE.unlink(missing_ok=True)
    errors = f", {len(tts.errors)} TTS errors (see above)" if tts.errors else ""
    print(f"Done in {mmss(took)}{errors}. The last caption stays on screen; RESET clears the table.")


if __name__ == "__main__":
    main()
