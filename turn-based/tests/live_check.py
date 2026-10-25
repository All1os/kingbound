"""Checks the Kingbound save in a running Tabletop Simulator.

With TTS open and KINGBOUND-prototype loaded: python3 tests/live_check.py
It asks the table script what is on the table (all 132 cards, 49 tiles, 4 pawns, 4 level markers,
4 player boards, the die), plays the short bot demo at double speed, counts again and resets the
table. Any script error TTS reports is printed. It moves the pieces, so don't run it while recording.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bots"))
from play import DEFAULT_SEED, TTS, Director, game_for  # noqa: E402

WANT = "cards=132 tiles=49 pawns=4 markers=4 boards=4 die=1"


def table(tts):
    tts.replies.clear()
    tts.send({"op": "check"})
    end = time.time() + 5
    while time.time() < end:
        for r in list(tts.replies):
            if r.get("kind") == "check":
                return r.get("text")
        time.sleep(0.1)
    return None


def main():
    tts = TTS()
    try:
        version = tts.hello()
    except OSError:
        print("Tabletop Simulator is not running.")
        return 1
    if not version:
        print("TTS is running but the KINGBOUND-prototype save is not loaded.")
        return 1
    print(f"save version {version}")
    before = table(tts)
    print(f"on the table: {before}  {'OK' if before == WANT else 'want ' + WANT}")
    g = game_for(DEFAULT_SEED["demo"], "demo")
    print(f"playing the demo game (seed {DEFAULT_SEED['demo']}) at speed 2...")
    Director(tts, 2.0, camera=False).run(g.events)
    time.sleep(3)
    after = table(tts)
    print(f"after the game: {after}  {'OK' if after and after.startswith('cards=132') else 'cards missing'}")
    tts.send({"op": "reset"})
    print(f"TTS script errors: {len(tts.errors)}")
    for e in tts.errors:
        print("  ", e)
    ok = before == WANT and after and after.startswith("cards=132") and not tts.errors
    print("LIVE CHECK " + ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
