"""Runs the save's Global script against a fake Tabletop Simulator (fake_tts.lua), feeding it the
exact commands bots/play.py would send for a whole bot game, then the people's buttons.

It checks that no command raises a Lua error, that all 132 cards are still on the table, and that
every bot's hand and items in TTS match the game engine at the end. It needs `lua` (brew install lua)
and an up-to-date save (python3 tts/build.py). TTS itself is not needed.

Run: python3 tests/check_tts_script.py [seeds...] [--demo]
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "bots"))
from play import Director, duration  # noqa: E402
from engine import Game  # noqa: E402

SAVE = json.loads((REPO / "tts/output/KINGBOUND-prototype.json").read_text())


def lua(v):
    if isinstance(v, dict):
        return "{" + ", ".join(f"[{json.dumps(str(k), ensure_ascii=False)}] = {lua(x)}" for k, x in v.items()) + "}"
    if isinstance(v, (list, tuple)):
        return "{" + ", ".join(lua(x) for x in v) + "}"
    if v is None:
        return "nil"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(float(v))
    return json.dumps(v, ensure_ascii=False)


def objects():
    out = []
    for o in SAVE["ObjectStates"]:
        t = o["Transform"]
        d = dict(Name=o["Name"], Nickname=o.get("Nickname", ""), GMNotes=o.get("GMNotes", ""), Tags=o.get("Tags", []),
                 posX=t["posX"], posY=t["posY"], posZ=t["posZ"], rotY=t["rotY"], rotZ=t["rotZ"])
        if o["Name"] == "HandTrigger":
            d["FogColor"] = o["FogColor"]
        if o["Name"] == "Deck":
            d["cards"] = [dict(gm=c["GMNotes"], name=c["Nickname"], id=c["CardID"]) for c in o["ContainedObjects"]]
        if o["Name"] == "Card":
            d["cards"] = [dict(gm=o["GMNotes"], name=o["Nickname"], id=o["CardID"])]
        out.append(d)
    return out


class Recorder:
    def __init__(self):
        self.sent = []

    def send(self, data):
        self.sent.append(json.loads(json.dumps(data)))


def run(seed, mode):
    g = Game(seed, mode)
    g.play()
    rec = Recorder()
    director = Director(rec, 1.0, camera=True)
    steps = [dict(msg={"json": json.dumps({"op": "reset"})}, wait=2.0)]
    for e in g.events:
        before = len(rec.sent)
        director.show(e)
        new = rec.sent[before:]
        for k, m in enumerate(new):
            steps.append(dict(msg={"json": json.dumps(m, ensure_ascii=False)}, wait=duration(e) if k == len(new) - 1 else 0.0))
        if not new:
            steps.append(dict(msg=None, wait=duration(e)))
    steps.append(dict(msg={"json": json.dumps({"op": "check"})}, wait=3.0))
    expect = dict(hand={p.color: p.hand for p in g.players},
                  items={p.color: p.equipment + p.consumables for p in g.players},
                  used={p.color: 3 - len(p.ready) for p in g.players})
    script = SAVE["LuaScript"]
    with tempfile.NamedTemporaryFile("w", suffix=".lua", delete=False) as f:
        f.write("OBJECTS = " + lua(objects()) + "\n")
        f.write("SCRIPT = [=========[" + script + "]=========]\n")
        f.write("STEPS = " + lua(steps) + "\n")
        f.write("EXPECT = " + lua(expect) + "\n")
        path = f.name
    r = subprocess.run(["lua", str(REPO / "tests/fake_tts.lua"), path], capture_output=True, text=True)
    Path(path).unlink()
    out = (r.stdout + r.stderr).strip()
    print(f"seed {seed} ({mode}, {len(g.events)} events): {out}")
    return r.returncode == 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mode = "demo" if "--demo" in sys.argv else "full"
    seeds = [int(a) for a in args] or ([94] if mode == "demo" else [1])
    ok = all([run(s, mode) for s in seeds])
    sys.exit(0 if ok else 1)
