--[[ Kingbound real-time prototype: Global script (build.py fills in the __PLACEHOLDERS__).

Two jobs. For players: START GAME shuffles the room stack, the token piles and the Loot Deck, hands
out the dice, puts the characters in the Safe Room and starts the 10-minute timer; RESET TABLE puts
everything back. Everything else is done by hand, as on a real table.
For the tutorial video: the director (../tutorial.py) decides everything in Python and sends "show
this" commands through TTS's External Editor API; this script only moves pieces, rolls dice to the
faces it is told, and draws the caption, the timer and the scores. Nothing here makes a game decision.

GM Notes: room tiles hold their dungeon cell ("x,z") or "spareN"; tokens their ID (m-weak-1,
t-rare-2 ...); rubble "rubble-n"; dice "Color:n"; pawns and mats their colour; Loot cards their ID
(L1-L5, Prank cards P1-P4).
]]
KB_VERSION = "__VERSION__"
L = JSON.decode([==[__LAYOUT__]==])

COLORS = {Red = {0.86, 0.1, 0.09}, Yellow = {0.95, 0.85, 0.1}, Green = {0.19, 0.7, 0.17}, Blue = {0.12, 0.53, 1},
          Purple = {0.63, 0.13, 0.94}}
GOLDEN = {1, 0.82, 0.3}
-- Where each character stands inside a room, so five can share one: a ring around the token in the
-- middle (a room is 3.6 across, a token 1.4).
PAWN_OFF = {Green = {0, 1.15}, Yellow = {-1.09, 0.36}, Red = {-0.68, -0.93}, Purple = {0.68, -0.93}, Blue = {1.09, 0.36}}
-- Mat geometry: a mat is L.mat_size table units; its image is L.mat_px pixels (build.py mat_img).
local function matPos(color, px, py)
  return {x = L.mat_x[color] + (px / L.mat_px[1] - 0.5) * L.mat_size[1], y = 1.25,
          z = L.mat_z + (0.5 - py / L.mat_px[2]) * L.mat_size[2]}
end
-- Heights measured live (2026-10-19): the felt is at y 0.96; a tile's position is its bottom face when
-- face up; a mat's top is at 1.08, a room's at 1.10; a die at scale 1.5 is 1.0 high (centre pivot).
DIE_Y, ROOM_Y, TOKEN_ON_ROOM, TOKEN_ON_MAT = 1.58, 0.98, 1.11, 1.09
-- The pieces players move (unlocked in the save; the director locks them while it films).
MOVABLE = {"room", "token", "rubble", "die", "pawn"}
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
  for i = 1, #L.colors do
    local ln = d.lines[i]
    UI.setValue("kbScore" .. i, ln and ln.text or "")
    if ln and ln.hex then UI.setAttribute("kbScore" .. i, "color", ln.hex) end
  end
end

-- The 10-minute timer (§10). It never pauses in the game. In a real game (START GAME) it follows the
-- clock, so it can't drift; the director only speeds it up for the "a few minutes later" part of the
-- video (rate = game seconds per real second).
TIMER = {left = L.game_secs, rate = 1, token = 0, play = false, ends = nil}
local function wall()
  local ok, t = pcall(function() return os.time() end)
  if ok and type(t) == "number" then return t end
end
local function showTime()
  local s = math.max(0, math.floor(TIMER.left + 0.5))
  UI.setValue("kbTimerText", string.format("%d:%02d", math.floor(s / 60), s % 60))
  UI.setAttribute("kbTimerText", "color", s <= 60 and "#FF6A5A" or "#F5ECD7")
end
local function timeUp()
  OPS.banner({text = "TIME'S UP!"})
  broadcastToAll("Time's up! Only the POINTS box counts: defeated monsters and secured treasure.", GOLDEN)
end
local function tick(token)
  if token ~= TIMER.token then return end
  if TIMER.ends then TIMER.left = TIMER.ends - wall() else TIMER.left = TIMER.left - 1 end
  if TIMER.left <= 0 then
    TIMER.left = 0
    showTime()
    if TIMER.play then timeUp() end
    return
  end
  showTime()
  Wait.time(function() tick(token) end, TIMER.ends and 0.25 or 1 / TIMER.rate)
end
function OPS.timer(d)
  UI.setAttribute("kbTimer", "active", d.hide and "false" or "true")
  TIMER.token = TIMER.token + 1
  if d.left then TIMER.left = d.left end
  TIMER.rate = d.rate or 1
  TIMER.play = d.play or false
  TIMER.ends = nil
  if TIMER.play and wall() then TIMER.ends = wall() + TIMER.left end
  showTime()
  if d.run then
    local token = TIMER.token
    Wait.time(function() tick(token) end, TIMER.ends and 0.25 or 1 / TIMER.rate)
  end
end

-- ------------------------------------------------------------------ camera
-- Always from the south (yaw 0), so every mat and card reads upright.
function viewFor(d)
  local v = d.view
  if v == "table" then return {position = {x = 0, y = 0, z = 0}, pitch = 68, yaw = 0, distance = 54} end
  if v == "play" then return {position = {x = 0, y = 0, z = -4.0}, pitch = 62, yaw = 0, distance = 40} end
  if v == "dungeon" then return {position = {x = 0, y = 0, z = 1.5}, pitch = 70, yaw = 0, distance = 30} end
  if v == "mats" then return {position = {x = 0, y = 0, z = -9.0}, pitch = 60, yaw = 0, distance = 36} end
  if v == "chart" then return {position = {x = -16.5, y = 0, z = -0.2}, pitch = 66, yaw = 0, distance = 16} end
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
      local mx, mz, hw, hd = L.mat_x[d.color], L.mat_z, L.mat_size[1] / 2 + 0.5, L.mat_size[2] / 2 + 0.1
      local x0, x1 = math.min(mx - hw, p.x - 2.2), math.max(mx + hw, p.x + 2.2)
      local z0, z1 = mz - hd, p.z + 2.2
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
  for _, color in ipairs(d.colors or L.colors) do
    for i = 1, 4 do
      local die = dieOf(color, i)
      if die then
        k = k + 1
        local px = L.die_px[i]
        local p = matPos(color, px[1], px[2])
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
  -- Characters go into the Safe Room (§12: it is everyone's starting room).
  for _, color in ipairs(d.colors or L.colors) do
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

function OPS.button(d)
  for _, id in ipairs({"kbStart", "kbReset"}) do UI.setAttribute(id, "active", d.show and "true" or "false") end
end

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
  local px = L.die_px[i]
  local p = matPos(color, px[1], px[2])
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

-- ------------------------------------------------------------------ the dungeon (§6, §12)
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

-- What lies on each mat: CARRIED treasure (not secured yet, §12) and POINTS (defeated monsters and
-- secured treasure; only POINTS count at the end).
CARRY, POINTS = {}, {}
local function clearMats()
  CARRY, POINTS = {}, {}
  for _, c in ipairs(L.colors) do CARRY[c], POINTS[c] = {}, {} end
end
local function toMat(o, color, spots, n, delay)
  local px = spots[math.min(n, #spots)]
  local p = matPos(color, px[1], px[2])
  Wait.time(function()
    o.setPositionSmooth({x = p.x, y = TOKEN_ON_MAT, z = p.z}, false, true)
    o.setScale({x = 0.5, y = 1, z = 0.5})
    glow(o, color, 3)
  end, delay)
end

function OPS.take(d)
  -- A defeated monster goes onto POINTS; a collected treasure onto CARRIED until it is secured.
  local o = byNote("token", d.id)
  if not o then return end
  o.setPositionSmooth({x = o.getPosition().x, y = 3.0, z = o.getPosition().z}, false, true)
  if d.id:sub(1, 2) == "t-" then
    table.insert(CARRY[d.color], d.id)
    toMat(o, d.color, L.carry_px, #CARRY[d.color], 0.4)
  else
    table.insert(POINTS[d.color], d.id)
    toMat(o, d.color, L.points_px, #POINTS[d.color], 0.4)
  end
end

function OPS.secure(d)
  -- §12: back in the Safe Room, everything CARRIED moves to POINTS, no dice.
  for k, id in ipairs(CARRY[d.color]) do
    local o = byNote("token", id)
    if o then
      table.insert(POINTS[d.color], id)
      toMat(o, d.color, L.points_px, #POINTS[d.color], (k - 1) * 0.25)
    end
  end
  CARRY[d.color] = {}
end

function OPS.loot(d)
  -- Draw the Loot card with this ID (§9: special treasure) onto the mat's Loot box, face up.
  local deck = getObjectsWithTag("lootdeck")[1]
  local p = matPos(d.color, L.loot_px[1], L.loot_px[2])
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
    HOME[o.getGUID()] = {pos = o.getPosition(), rot = o.getRotation(), scale = o.getScale(), lock = o.getLock()}
  end
  clearMats()
  for _, id in ipairs({"kbCaption", "kbScore", "kbBanner"}) do UI.setAttribute(id, "active", "false") end
end

local function isMovable(o)
  for _, t in ipairs(MOVABLE) do if o.hasTag(t) then return true end end
  return false
end
-- Piles (the room stack, the token piles, rubble) are put in place locked, so no piece knocks another
-- over on the way, and let go half a second later: a stack of loose tiles stays a neat stack.
local function isPile(o)
  return (o.hasTag("room") and notes(o) ~= "0,0") or o.hasTag("token") or o.hasTag("rubble")
end
local function place(objs, slots, stay_locked)
  for k, o in ipairs(objs) do
    local s = slots[k]
    o.setLock(true)
    o.setPosition(s.pos)
    o.setRotation(s.rot)
    o.setScale(s.scale)
  end
  if not stay_locked then
    Wait.time(function() for _, o in ipairs(objs) do if alive(o) then o.setLock(false) end end end, 0.5)
  end
end

function OPS.reset(d)
  -- d.stage: the director films, so every piece stays locked and only its scripts move them.
  local deck = getObjectsWithTag("lootdeck")[1]
  local piles, slots = {}, {}
  for _, o in ipairs(getObjects()) do
    -- Loot cards back into the deck; two cards dropped on each other have become a small deck of
    -- their own (seen live, 2026-10-25), so those go back too.
    local loose = o.type == "Card" or (o.type == "Deck" and not o.hasTag("lootdeck"))
    if loose and deck and o ~= deck then
      o.setLock(false)
      o.removeTag("loot")
      deck.putObject(o)
    else
      local h = HOME[o.getGUID()]
      if h and isPile(o) then
        table.insert(piles, o)
        table.insert(slots, h)
      elseif h then
        -- A die or a pawn is locked on the way home, so it doesn't tumble, then gets its own state
        -- back. Nothing else is locked: a locked Loot Deck takes no cards back (seen live, 2026-10-25).
        if isMovable(o) then
          local lock = h.lock == true or d.stage == true
          o.setLock(true)
          Wait.time(function() if alive(o) then o.setLock(lock) end end, 1.2)
        end
        o.setPositionSmooth(h.pos, false, true)
        o.setRotationSmooth(h.rot, false, true)
        o.setScale(h.scale)
      end
    end
  end
  place(piles, slots, d.stage)
  clearMats()
  TIMER.token = TIMER.token + 1
  TIMER.left, TIMER.play, TIMER.ends = L.game_secs, false, nil
  showTime()
  for _, id in ipairs({"kbCaption", "kbScore", "kbBanner", "kbTimer"}) do UI.setAttribute(id, "active", "false") end
end
function resetGame(player) OPS.reset({}) end

-- ------------------------------------------------------------------ START GAME
-- The colours at a mat that someone sits at; nobody at a mat colour (one person trying it out) =
-- every colour.
local function seatedColors()
  local out = {}
  for _, pl in ipairs(Player.getPlayers()) do
    if L.mat_x[pl.color] then table.insert(out, pl.color) end
  end
  if #out == 0 then return L.colors end
  return out
end

local function shufflePile(objs)
  -- The pieces swap their starting places (§3 step 3: shuffle the room tiles).
  local slots = {}
  for _, o in ipairs(objs) do table.insert(slots, HOME[o.getGUID()]) end
  table.sort(slots, function(a, b) return a.pos.y < b.pos.y end)
  for i = #objs, 2, -1 do
    local j = math.random(i)
    objs[i], objs[j] = objs[j], objs[i]
  end
  place(objs, slots, false)
end

local starting = false
function startGame(player)
  if starting then return end
  starting = true
  OPS.reset({})
  Wait.time(function()
    local rooms = {}
    for _, o in ipairs(getObjectsWithTag("room")) do
      if notes(o) ~= "0,0" and HOME[o.getGUID()] then table.insert(rooms, o) end
    end
    shufflePile(rooms)
    shufflePile(getObjectsWithTag("monster"))
    shufflePile(getObjectsWithTag("treasure"))
    local deck = getObjectsWithTag("lootdeck")[1]
    if deck then deck.shuffle() end
    local who = seatedColors()
    OPS.deal({colors = who})
    OPS.pawns({colors = who})
    OPS.timer({left = L.game_secs, run = true, play = true})
    OPS.banner({text = "GO!"})
    Wait.time(function()
      if TIMER.play and TIMER.left > 0 then OPS.banner({}) end
      starting = false
    end, 2.5)
  end, 1.4)
end

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
