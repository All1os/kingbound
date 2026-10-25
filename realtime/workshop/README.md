# Steam Workshop item

The real-time Kingbound is on the Steam Workshop as a Tabletop Simulator mod: **KINGBOUND prototype**, Workshop ID 3827233466,
https://steamcommunity.com/sharedfiles/filedetails/?id=3827233466 (uploaded 2026-10-25, save version 0.3-realtime). A new item
starts hidden; its visibility is changed on that page.

| File | What it is |
|---|---|
| `thumbnail.png` | The Workshop thumbnail: the same Beep drawing (izzychan.wordpress.com) as Yavuz's THE LIMIT and SHOWDOWN items, numbered 3 as SHOWDOWN's is numbered 2 |
| `preview.png` | A picture of the game for the Workshop page, made by `thumbnail.py` from the save's own images and `beep.png` |
| `beep.png` | Beep (Kenshi) from Yavuz's own model, cut out of its render |
| `description.txt` | The Workshop description (Steam's BBCode) |

The images in the save are on the Steam Cloud (`../tts/cloud_urls.json`), so the mod opens on any computer.

## Updating the item

On this Mac, Tabletop Simulator reads the system's SOCKS proxy (ciadpi, 127.0.0.1:1080) as an HTTP proxy and can't download
any image from the web ("Curl error 52: Empty reply from server" in its Player.log; every piece turns white). Switch the proxy
off while working on the item and back on afterwards: `networksetup -setsocksfirewallproxystate "iPhone USB USB" off` / `on`.


1. `python3 ../tts/build.py`. It prints how many images are only local. If any are, load the save in TTS, Modding > Cloud Manager > Upload All, save the game, and run `python3 ../tts/cloud_urls.py THAT_SAVE.json --icons COMMIT`, then build again.
2. Put the build on the table: `python3 ../tts/hotload.py` (or load the save), then RESET TABLE.
3. In TTS: Modding > Workshop Upload > Update Workshop, with the item's Workshop ID.
