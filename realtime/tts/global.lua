--[[ Kingbound real-time prototype: Global script (build.py fills in the __PLACEHOLDERS__).

The tutorial director (../tutorial.py) decides everything in Python and sends "show this" commands
through TTS's External Editor API; this script only moves pieces, rolls dice to the faces it is told,
and draws the caption, the timer and the scores. Nothing here makes a game decision.

GM Notes: room tiles hold their dungeon cell ("x,z") or "spareN"; tokens their ID (m-weak-1,
t-rare-2 ...); dice "Color:n"; pawns and mats their colour; Loot cards their ID (L1-L5).
]]
KB_VERSION = "__VERSION__"
L = JSON.decode([==[__LAYOUT__]==])

COLORS = {Red = {0.86, 0.1, 0.09}, Yellow = {0.95, 0.85, 0.1}, Green = {0.19, 0.7, 0.17}, Blue = {0.12, 0.53, 1}}
GOLDEN = {1, 0.82, 0.3}
-- Where each pawn stands inside a room, so four can share one.
PAWN_OFF = {Red = {-0.85, -0.85}, Yellow = {-0.85, 0.85}, Green = {0.85, 0.85}, Blue = {0.85, -0.85}}
-- Mat geometry: the mat is 11.0 x 5.2; its image is 1100 x 520 px (build.py mat_img).
local function matPos(color, px, py)
  return {x = L.mat_x[color] + (px / 1100 - 0.5) * 11.0, y = 1.25, z = L.mat_z + (0.5 - py / 520) * 5.2}
end
DIE_PX = {{150, 230}, {320, 230}, {150, 400}, {320, 400}}
-- Heights measured live (2026-10-19): the felt is at y 0.96; a tile's position is its bottom face when
-- face up; a mat's top is at 1.08, a room's at 1.10; a die at scale 1.5 is 1.0 high (centre pivot).
DIE_Y, ROOM_Y, TOKEN_ON_ROOM, TOKEN_ON_MAT = 1.58, 0.98, 1.11, 1.09
TROPHY_PX = {{730, 225}, {865, 225}, {1000, 225}, {730, 395}, {865, 395}, {1000, 395}}
TROPHIES = {Red = 0, Yellow = 0, Green = 0, Blue = 0}
OPS = {}

-- ------------------------------------------------------------------ finding things
local function alive(o) return o ~= nil and not o.isDestroyed() end
local function notes(o) local ok, g = pcall(function() return o.getGMNotes() end) return ok and g or "" end
local function byNote(tag, note)
  for _, o in ipairs(getObjectsWithTag(tag)) do if notes(o) == note then return o end end
end
function cellPos(c) return {x = L.dungeon[1] + c[1] * L.grid, y = 1.1, z = L.dungeon[2] + c[2] * L.grid} end
function dieOf(color, i) return byNote("die", color .. ":" .. i) end
function pawnOf(color) return byNote("pawn", color) end

function glow(o, color, secs)
  if alive(o) then pcall(function() o.highlightOn(COLORS[color] or GOLDEN, secs or 3) end) end
end

-- ------------------------------------------------------------------ overlays
-- Only the name of the part is shown (the team explains the rest live while presenting), with the
-- symbols the step costs as icons after it: d.icons = "MM" (2 Movement), "AAA", "GG" ...
local function textWidth(t)
  local w = 0
  -- Bold 29 px capitals are about 21 px wide (42 px ones measured 31 px on screen, 2026-10-19); a
  -- little more, so the text never runs into the icons (it overflows its box instead of wrapping).
  for ch in t:gmatch(".") do w = w + ((ch == " " or ch == "·" or ch == ":") and 10 or 24) end
  return math.max(60, w)
end
function caption(head, icons)
  icons = icons or ""
  local tw = textWidth(head or "")
  UI.setAttribute("kbCaptionHead", "preferredWidth", tw)
  UI.setAttribute("kbCaption", "width", tw + 32 + #icons * 46)
  UI.setValue("kbCaptionHead", head or "")
  for i = 1, 4 do
    local k = icons:sub(i, i)
    if k ~= "" then
      UI.setAttribute("kbIcon" .. i, "image", "icon" .. k)
      UI.setAttribute("kbIcon" .. i, "active", "true")
    else
      UI.setAttribute("kbIcon" .. i, "active", "false")
    end
  end
  UI.setAttribute("kbCaption", "active", "true")
end
function OPS.caption(d) caption(d.head, d.icons) end
function OPS.nocaption(d) UI.setAttribute("kbCaption", "active", "false") end

function OPS.banner(d)
  if not d.text then UI.setAttribute("kbBanner", "active", "false") return end
  UI.setValue("kbBannerText", d.text)
  UI.setAttribute("kbBanner", "active", "true")
end

function OPS.score(d)
  if not d.lines then UI.setAttribute("kbScore", "active", "false") return end
  UI.setAttribute("kbScore", "active", "true")
  for i = 1, 4 do
    local ln = d.lines[i]
    UI.setValue("kbScore" .. i, ln and ln.text or "")
    if ln and ln.hex then UI.setAttribute("kbScore" .. i, "color", ln.hex) end
  end
end

-- The 10-minute timer (§10). It never pauses in the game; the director only speeds it up for the
-- "a few minutes later" part of the video (rate = game seconds per real second).
TIMER = {left = 600, rate = 1, token = 0}
local function showTime()
  local s = math.max(0, math.floor(TIMER.left + 0.5))
  UI.setValue("kbTimerText", string.format("%d:%02d", math.floor(s / 60), s % 60))
  UI.setAttribute("kbTimerText", "color", s <= 60 and "#FF6A5A" or "#F5ECD7")
end
local function tick(token)
  if token ~= TIMER.token then return end
  TIMER.left = TIMER.left - 1
  showTime()
  if TIMER.left <= 0 then return end
  Wait.time(function() tick(token) end, 1 / TIMER.rate)
end
function OPS.timer(d)
  UI.setAttribute("kbTimer", "active", d.hide and "false" or "true")
  TIMER.token = TIMER.token + 1
  if d.left then TIMER.left = d.left end
  TIMER.rate = d.rate or 1
  showTime()
  if d.run then
    local token = TIMER.token
    Wait.time(function() tick(token) end, 1 / TIMER.rate)
  end
end

-- ------------------------------------------------------------------ camera
-- Always from the south (yaw 0), so every mat and card reads upright.
function viewFor(d)
  local v = d.view
  if v == "table" then return {position = {x = 0, y = 0, z = 0}, pitch = 68, yaw = 0, distance = 54} end
  if v == "play" then return {position = {x = 0, y = 0, z = -4.0}, pitch = 62, yaw = 0, distance = 40} end
  if v == "dungeon" then return {position = {x = 0, y = 0, z = 1.5}, pitch = 70, yaw = 0, distance = 30} end
  if v == "mats" then return {position = {x = 0, y = 0, z = -9.0}, pitch = 60, yaw = 0, distance = 34} end
  if v == "chart" then return {position = {x = -16.5, y = 0, z = -0.2}, pitch = 66, yaw = 0, distance = 15} end
  if v == "supply" then return {position = {x = 4, y = 0, z = 7}, pitch = 64, yaw = 0, distance = 34} end
  if v == "title" then return {position = {x = 0, y = 0, z = 15.8}, pitch = 70, yaw = 0, distance = 20} end
  if v == "mat" then
    return {position = {x = L.mat_x[d.color], y = 0, z = L.mat_z - 0.8}, pitch = 62, yaw = 0, distance = d.distance or 15}
  end
  if v == "cell" then
    local p = cellPos(d.cell)
    -- With a colour: the room and that player's mat (where the dice are) in one shot. The view frames
    -- both (half-way put the far-left mat's dice off screen, seen 2026-10-19) and aims a little low,
    -- because the part's name covers the bottom of the screen.
    if d.color then
      local mx, mz = L.mat_x[d.color], L.mat_z
      local x0, x1 = math.min(mx - 5.5, p.x - 2.2), math.max(mx + 5.5, p.x + 2.2)
      local z0, z1 = mz - 2.6, p.z + 2.2
      local dist = math.max(d.distance or 0, (x1 - x0) / 1.2, (z1 - z0) * 1.1)
      return {position = {x = (x0 + x1) / 2, y = 0, z = (z0 + z1) / 2 - 1.8}, pitch = 62, yaw = 0, distance = dist}
    end
    return {position = {x = p.x, y = 0, z = p.z - 0.8}, pitch = 64, yaw = 0, distance = d.distance or 16}
  end
end
function OPS.camera(d)
  local v = viewFor(d)
  if not v then return end
  for _, pl in ipairs(Player.getPlayers()) do
    if pl.host then pcall(function() pl.lookAt(v) end) end
  end
end

-- ------------------------------------------------------------------ setup (§3)
function OPS.deal(d)
  -- Each player takes their 4 dice (§3 step 1): from the middle of the table onto their mat.
  local k = 0
  for color, _ in pairs(L.mat_x) do
    for i = 1, 4 do
      local die = dieOf(color, i)
      if die then
        k = k + 1
        local p = matPos(color, DIE_PX[i][1], DIE_PX[i][2])
        -- Face first, then the move: setRotationValue after setPositionSmooth cancels the move
        -- (seen live, 2026-10-19: the dice stayed in the supply).
        Wait.time(function()
          die.setRotationValue(i)
          die.setPositionSmooth({x = p.x, y = DIE_Y, z = p.z}, false, true)
          glow(die, color, 2)
        end, k * 0.06)
      end
    end
  end
end

function OPS.pawns(d)
  -- Characters go on the start room (§6), or back to their place beside the mat.
  for color, _ in pairs(L.mat_x) do
    local pawn = pawnOf(color)
    if pawn then
      local c, off = cellPos({0, 0}), PAWN_OFF[color]
      pawn.setPositionSmooth({x = c.x + off[1], y = 1.6, z = c.z + off[2]}, false, false)
      glow(pawn, color, 3)
    end
  end
end

function OPS.shuffle(d)
  -- The room stack is already in the tutorial's order; this only shows it being shuffled (§3 step 3).
  local rooms = {}
  for _, o in ipairs(getObjectsWithTag("room")) do
    if notes(o) ~= "0,0" and o.getRotation().z > 90 then table.insert(rooms, o) end
  end
  for k, o in ipairs(rooms) do
    local p = o.getPosition()
    local dx = (k % 2 == 0) and 1.6 or -1.6
    Wait.time(function() o.setPositionSmooth({x = p.x + dx, y = p.y, z = p.z}, false, true) end, 0.02 * k)
    Wait.time(function() o.setPositionSmooth(p, false, true) end, 0.6 + 0.02 * k)
  end
end

function OPS.button(d) UI.setAttribute("kbReset", "active", d.show and "true" or "false") end

function OPS.spot(d)
  -- One player's character and mat glow: "watch this player".
  glow(pawnOf(d.color), d.color, d.secs or 3)
  glow(byNote("mat", d.color), d.color, d.secs or 3)
end

function OPS.glowtag(d)
  for _, o in ipairs(getObjectsWithTag(d.tag)) do glow(o, d.color, d.secs or 3) end
end

-- ------------------------------------------------------------------ dice (§4, §5)
-- d.color, d.dice = which dice (1-4), d.values = the faces they land on (1-2 Movement, 3-4 Attack,
-- 5-6 Magic). The dice jump, tumble and land on the face; kept dice stay where they are.
local function rollOne(color, i, value, delay)
  local die = dieOf(color, i)
  if not die then return end
  local p = matPos(color, DIE_PX[i][1], DIE_PX[i][2])
  Wait.time(function()
    die.setPositionSmooth({x = p.x, y = DIE_Y + 2.2, z = p.z}, false, true)
    die.setRotationSmooth({x = math.random(0, 359), y = math.random(0, 359), z = math.random(0, 359)}, false, true)
  end, delay)
  Wait.time(function()
    die.setRotationSmooth({x = math.random(0, 359), y = math.random(0, 359), z = math.random(0, 359)}, false, true)
  end, delay + 0.25)
  Wait.time(function()
    die.setRotationValue(value)
    die.setPositionSmooth({x = p.x, y = DIE_Y, z = p.z}, false, true)
  end, delay + 0.55)
end
function OPS.roll(d)
  for k, i in ipairs(d.dice) do rollOne(d.color, i, d.values[k], (k - 1) * 0.04) end
end
function OPS.keep(d)
  -- The dice that already show what the player needs glow in their colour.
  for _, i in ipairs(d.dice) do glow(dieOf(d.color, i), d.color, d.secs or 3) end
end

-- ------------------------------------------------------------------ the dungeon (§6)
function OPS.reveal(d)
  -- The room tile of this cell comes off the stack, turns over and lands next to the room it was
  -- revealed from, passages lined up (build.py drew them that way).
  local o = byNote("room", d.cell[1] .. "," .. d.cell[2])
  if not o then return end
  local p = cellPos(d.cell)
  o.setPositionSmooth({x = p.x, y = 2.6, z = p.z}, false, true)
  o.setRotationSmooth({x = 0, y = 180, z = 0}, false, true)
  Wait.time(function() o.setPositionSmooth({x = p.x, y = ROOM_Y, z = p.z}, false, true) glow(o, d.color, 3) end, 0.7)
  if d.token then
    Wait.time(function() OPS.token({id = d.token, cell = d.cell, color = d.color}) end, 1.2)
  end
end

function OPS.token(d)
  local o = byNote("token", d.id)
  if not o then return end
  local p = cellPos(d.cell)
  o.setPositionSmooth({x = p.x, y = 2.4, z = p.z}, false, true)
  o.setRotationSmooth({x = 0, y = 180, z = 0}, false, true)
  Wait.time(function() o.setPositionSmooth({x = p.x, y = TOKEN_ON_ROOM, z = p.z}, false, true) glow(o, d.color, 3) end, 0.6)
end

function OPS.move(d)
  local pawn = pawnOf(d.color)
  if not pawn then return end
  local path = d.path or {d.cell}
  for k, c in ipairs(path) do
    Wait.time(function()
      local p, off = cellPos(c), PAWN_OFF[d.color]
      pawn.setPositionSmooth({x = p.x + off[1], y = 1.6, z = p.z + off[2]}, false, true)
      glow(pawn, d.color, 2)
    end, (k - 1) * (d.t or 0.45))
  end
end

function OPS.take(d)
  -- A defeated monster or a collected treasure goes onto the player's mat: trophies are points (§11).
  local o = byNote("token", d.id)
  if not o then return end
  TROPHIES[d.color] = TROPHIES[d.color] + 1
  local spot = TROPHY_PX[math.min(TROPHIES[d.color], #TROPHY_PX)]
  local p = matPos(d.color, spot[1], spot[2])
  o.setPositionSmooth({x = o.getPosition().x, y = 3.0, z = o.getPosition().z}, false, true)
  Wait.time(function()
    o.setPositionSmooth({x = p.x, y = TOKEN_ON_MAT, z = p.z}, false, true)
    o.setScale({x = 0.6, y = 1, z = 0.6})
    glow(o, d.color, 3)
  end, 0.4)
end

function OPS.loot(d)
  -- Draw the Loot card with this ID (§9: special treasure) onto the mat's Loot box, face up.
  local deck = getObjectsWithTag("lootdeck")[1]
  local p = matPos(d.color, 550, 300)
  if deck and not deck.isDestroyed() then
    for _, c in ipairs(deck.getObjects()) do
      if c.gm_notes == d.id then
        deck.takeObject({guid = c.guid, position = {x = p.x, y = 1.12, z = p.z}, rotation = {x = 0, y = 180, z = 0},
                         smooth = true, callback_function = function(card)
                           card.setLock(true)
                           card.addTag("loot")
                           glow(card, d.color, 4)
                         end})
        return
      end
    end
  end
end

function OPS.glowloot(d)
  for _, o in ipairs(getObjectsWithTag("loot")) do glow(o, d.color, d.secs or 3) end
end

-- ------------------------------------------------------------------ reset
-- Every object's starting place is remembered at load; RESET TABLE (or the director) puts it back.
HOME = {}
function onLoad()
  local assets = {}
  for k, u in pairs(L.icons) do table.insert(assets, {name = "icon" .. k, url = u}) end
  UI.setCustomAssets(assets)
  for _, o in ipairs(getObjects()) do
    HOME[o.getGUID()] = {pos = o.getPosition(), rot = o.getRotation(), scale = o.getScale()}
  end
  for _, id in ipairs({"kbCaption", "kbScore", "kbBanner"}) do UI.setAttribute(id, "active", "false") end
end

function OPS.reset(d)
  local deck = getObjectsWithTag("lootdeck")[1]
  for _, o in ipairs(getObjects()) do
    if o.type == "Card" and deck and o ~= deck then
      o.setLock(false)
      o.removeTag("loot")
      deck.putObject(o)
    else
      local h = HOME[o.getGUID()]
      if h then
        o.setPositionSmooth(h.pos, false, true)
        o.setRotationSmooth(h.rot, false, true)
        o.setScale(h.scale)
      end
    end
  end
  TROPHIES = {Red = 0, Yellow = 0, Green = 0, Blue = 0}
  TIMER.token = TIMER.token + 1
  TIMER.left = 600
  showTime()
  for _, id in ipairs({"kbCaption", "kbScore", "kbBanner", "kbTimer"}) do UI.setAttribute(id, "active", "false") end
end
function resetGame(player) OPS.reset({}) end

-- ------------------------------------------------------------------ the director's commands
local function reply(kind, text) sendExternalMessage({kind = kind, text = text}) end
function OPS.hello(d) reply("hello", KB_VERSION) end

function onExternalMessage(d)
  if type(d) ~= "table" then return end
  -- One JSON string per command: TTS hands nested lists of a custom message to Lua as C# objects
  -- (seen live on v0.1), so the director sends {json = "..."}.
  if d.json then d = JSON.decode(d.json) end
  local f = OPS[d.op]
  if not f then reply("error", "unknown command " .. tostring(d.op)) return end
  local function run()
    local ok, err = pcall(f, d)
    if not ok then reply("error", tostring(d.op) .. ": " .. tostring(err)) end
  end
  -- d.delay: wait before doing it, so one beat can be "the dice land, then the room is revealed".
  if type(d.delay) == "number" and d.delay > 0 then Wait.time(run, d.delay) else run() end
end
