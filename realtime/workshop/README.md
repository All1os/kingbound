# Steam Workshop item

The real-time Kingbound is on the Steam Workshop as a Tabletop Simulator mod.

| File | What it is |
|---|---|
| `thumbnail.png` | The Workshop thumbnail (1024 x 1024), made by `thumbnail.py` from the save's own images and Beep |
| `beep.png` | Beep (Kenshi) from Yavuz's own model, cut out of its render |
| `description.txt` | The Workshop description (Steam's BBCode) |

The images in the save are on the Steam Cloud (`../tts/cloud_urls.json`), so the mod opens on any computer.

## Updating the item

1. `python3 ../tts/build.py`. It prints how many images are only local. If any are, load the save in TTS, Modding > Cloud Manager > Upload All, save the game, and run `python3 ../tts/cloud_urls.py THAT_SAVE.json --icons COMMIT`, then build again.
2. Put the build on the table: `python3 ../tts/hotload.py` (or load the save), then RESET TABLE.
3. In TTS: Modding > Workshop Upload > Update Workshop, with the item's Workshop ID.
