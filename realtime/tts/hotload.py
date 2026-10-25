"""Puts a freshly built save on the table of a running TTS, without the Save & Load menu.

First sends the Global script and UI through the External Editor API's "Save & Play" (messageID 1).
That reloads whatever save file TTS has open, so the objects come next: the table is cleared and every
object of output/KINGBOUND-realtime.json is spawned, then the script's onLoad runs again so it
remembers the new starting places and decks. (Spawning first and reloading last only worked while the
open file was the build itself: after a save made in TTS, the reload brought that save's objects back,
seen 2026-10-25.) Needs TTS open with any game loaded.
Run: python3 hotload.py
"""
import json
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
SAVE = ROOT / "output" / "KINGBOUND-realtime.json"
sys.path.insert(0, str(ROOT.parent))
from tutorial import TTS  # noqa: E402


def send_raw(msg):
    s = socket.create_connection(("127.0.0.1", 39999), timeout=3)
    s.sendall(json.dumps(msg).encode())
    s.close()


def main():
    save = json.loads(SAVE.read_text())
    parts = []
    for o in save["ObjectStates"]:
        text = json.dumps(o, ensure_ascii=False)
        assert "]==]" not in text
        parts.append("[==[" + text + "]==]")
    # Each object travels as its own JSON string: decoding and re-encoding in Lua would turn whole
    # numbers like CardID into floats.
    lua = ("for _, o in ipairs(getObjects()) do o.destruct() end\n"
           "Notes.setNotes('')\n"
           "local list = {" + ",\n".join(parts) + "}\n"
           "for _, j in ipairs(list) do spawnObjectJSON({json = j}) end\n"
           "print('spawned ' .. #list)")
    tts = TTS()
    send_raw({"messageID": 1, "scriptStates": [{"name": "Global", "guid": "-1",
                                                "script": save["LuaScript"], "ui": save["XmlUI"]}]})
    time.sleep(6.0)
    send_raw({"messageID": 3, "guid": "-1", "script": lua})
    time.sleep(4.0)
    send_raw({"messageID": 3, "guid": "-1", "script": "onLoad()"})
    time.sleep(1.0)
    version = tts.hello()
    print("table reloaded, save version:", version, "| errors:", tts.errors or "none")


if __name__ == "__main__":
    main()
