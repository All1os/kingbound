"""Writes cloud_urls.json after TTS has put the images on the Steam Cloud.

  python3 cloud_urls.py SAVED.json
  python3 cloud_urls.py --github COMMIT

The second form needs no TTS: every image the build still points to on this Mac gets its address in
this public repository at COMMIT instead (the commit must already be pushed with those images), so
the save opens anywhere until the images go to the Steam Cloud.

Before it: build, load the save in TTS, Modding > Cloud Manager > Upload All, then save the game
(SAVED.json is that save, in TTS's Saves folder). The saved game is compared with output/KINGBOUND-realtime.json
piece by piece: wherever the build had a local image and the saved game has an http URL, that image is
now on the Steam Cloud. The table's script also uses three icons that no piece shows; Upload All
doesn't see them, so they are taken from this public repository, pinned to the commit given in --icons.
build.py then writes these URLs instead of local paths (for files whose sha1 still matches).
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "output"
ASSETS = Path.home() / "Library/Tabletop Simulator/Mods/kingbound-realtime"
REPO_RAW = "https://raw.githubusercontent.com/All1os/kingbound/{commit}/realtime/tts/output/{fn}"


def strings(o, path=()):
    """Every string in a save object, with the path to it."""
    if isinstance(o, dict):
        for k, v in o.items():
            yield from strings(v, path + (k,))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from strings(v, path + (i,))
    elif isinstance(o, str):
        yield path, o


def key(o):
    # GUIDs can change when TTS spawns a piece, so pieces are matched by what build.py names them.
    return (o["Name"], o.get("Nickname", ""), o.get("GMNotes", ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("saved", nargs="?", help="the game TTS saved after Upload All")
    ap.add_argument("--icons", metavar="COMMIT", help="commit of this repository that holds output/icon-*.png")
    ap.add_argument("--github", metavar="COMMIT", help="give every image still on this Mac its address in the repository")
    a = ap.parse_args()
    built = json.loads((OUT / "KINGBOUND-realtime.json").read_text())
    saved = json.loads(Path(a.saved).expanduser().read_text()) if a.saved else {"ObjectStates": []}
    by_key = {key(o): o for o in saved["ObjectStates"]}
    cloud_of = {}
    if a.github:
        for _, v in strings(built):
            if v.startswith(str(ASSETS)):
                fn = re.sub(r"\.[0-9a-f]{10}\.png$", ".png", Path(v).name)
                cloud_of[v] = REPO_RAW.format(commit=a.github, fn=fn)
    for o in built["ObjectStates"]:
        s = by_key.get(key(o))
        if not s:
            continue
        theirs = dict(strings(s))
        for p, v in strings(o):
            if v.startswith(str(ASSETS)) and theirs.get(p, "").startswith("http"):
                cloud_of[v] = theirs[p]
    # Start from what is already on the cloud: an image whose file hasn't changed keeps its URL (the build
    # wrote that URL, so the comparison above only finds the images that were local; 2026-10-25 a rerun
    # without this kept only the new ones).
    old = json.loads((ROOT / "cloud_urls.json").read_text()) if (ROOT / "cloud_urls.json").exists() else {}
    out = {fn: c for fn, c in old.items()
           if (OUT / fn).exists() and hashlib.sha1((OUT / fn).read_bytes()).hexdigest() == c["sha1"]}
    for local, cloud in sorted(cloud_of.items()):
        fn = re.sub(r"\.[0-9a-f]{10}\.png$", ".png", Path(local).name)
        out[fn] = {"url": cloud, "sha1": hashlib.sha1((OUT / fn).read_bytes()).hexdigest()}
    if a.icons:
        for fn in ("icon-move.png", "icon-attack.png", "icon-magic.png"):
            out[fn] = {"url": REPO_RAW.format(commit=a.icons, fn=fn), "sha1": hashlib.sha1((OUT / fn).read_bytes()).hexdigest()}
    (ROOT / "cloud_urls.json").write_text(json.dumps(out, indent=1) + "\n")
    missing = sorted(p.name for p in OUT.glob("*.png") if p.name not in out)
    print(f"{len(out)} images on the cloud; not found in the save: {', '.join(missing) or 'none'}")


if __name__ == "__main__":
    main()
