--[[ Kingbound real-time prototype: Global script (build.py fills in the __PLACEHOLDERS__).

Two jobs. For players: START GAME shuffles the decks (rooms, monster and treasure tokens, Loot), hands
out the dice, puts the characters in the Safe Room and starts the 10-minute timer; RESET TABLE puts
everything back; ROLL DICE rolls all four of the clicking player's dice. Everything else is done by
hand, as on a real table.
For the tutorial video: the director (../tutorial.py) decides everything in Python and sends "show
this" commands through TTS's External Editor API; this script only moves pieces, rolls dice to the
faces it is told, and draws the caption, the timer and the scores. Nothing here makes a game decision.

Rooms, tokens, rubble and Loot are cards in five decks. A card's GM Notes say what it is: a room its
dungeon cell ("x,z") or "spareN", a token its ID (m-weak-1, t-rare-2 ...), rubble "rubble-n", Loot its
ID (L1-L5, Prank cards P1-P4). Dice hold "Color:n"; pawns and mats their colour; the Safe Room tile "0,0".
]]
KB_VERSION = "__VERSION__"
L = JSON.decode([==[__LAYOUT__]==])

COLORS = {Red = {0.86, 0.1, 0.09}, Yellow = {0.95, 0.85, 0.1}, Green = {0.19, 0.7, 0.17}, Blue = {0.12, 0.53, 1},
          Purple = {0.63, 0.13, 0.94}}
GOLDEN = {1, 0.82, 0.3}
-- Where each character stands inside a room, so five can share one: a ring around the token in the
-- middle (a room is 3.6 across, a token 1.4).
PAWN_OFF = {Green = {0, 1.15}, Yellow = {-1.09, 0.36}, Red = {-0.68, -0.93}, Purple = {0.68, -0.93}, Blue = {1.09, 0.36}}
-- Mat geometry: a mat is L.mat_size table units; its image is L.mat_px pixels (build.py mat_img). Each
-- mat lies on its player's side of the table, turned to face them (L.mats: x, z, Y rotation), so a
-- point of the image turns with it (same sums as build.py mat_world).
local function matPos(color, px, py)
  local m = L.mats[color]
  local u, v = (px / L.mat_px[1] - 0.5) * L.mat_size[1], (py / L.mat_px[2] - 0.5) * L.mat_size[2]
  local t = math.rad(m[3])
  return {x = m[1] - u * math.cos(t) + v * math.sin(t), y = 1.25, z = m[2] + u * math.sin(t) + v * math.cos(t)}
end
local function matRot(color) return {x = 0, y = L.mats[color][3], z = 0} end
-- Heights measured live: the felt is at y 0.96, a mat's top at 1.08, a die at scale 1.5 is 1.0 high
-- (centre pivot) (2026-10-19); a card lies at 0.974 on the felt, at 1.001 on another card and is 0.027
-- thick (2026-10-25).
DIE_Y, CARD_Y, CARD_ON_CARD, CARD_ON_MAT = 1.58, 0.974, 1.001, 1.095
-- The loose pieces players move (unlocked in the save; the director locks them while it films).
MOVABLE = {"die", "pawn"}
STAGED = false
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

-- ------------------------------------------------------------------ cards and decks
-- Which deck a card belongs to, from its GM Notes.
local function kindOf(n)
  if n == nil or n == "" then return nil end
  if n:match("^%-?%d+,%-?%d+$") or n:match("^spare") then return "room" end
  if n:sub(1, 2) == "m-" then return "monster" end
  if n:sub(1, 2) == "t-" then return "treasure" end
  if n:sub(1, 7) == "rubble-" then return "rubble" end
  if n:match("^[LP]%d$") then return "loot" end
end

-- Each kind's deck, remembered by GUID. A deck that is down to its last card stops being a deck (TTS
-- turns it into a single card); that card, or the first card to come back, becomes the deck again.
DECK = {}
local function mainDeck(kind)
  local g = DECK[kind]
  local o = g and getObjectFromGUID(g)
  if alive(o) then return o end
end
local function isMain(o, kind)
  if kind then return DECK[kind] == o.getGUID() end
  for k, _ in pairs(L.decks) do if DECK[k] == o.getGUID() then return true end end
  return false
end
local function deckHome(kind)
  local p = L.deck_pos[kind]
  return {x = p[1], y = 1.4, z = p[2]}
end

-- A card on the table, or the card with these notes taken out of whichever deck holds it; then
-- after(card) runs with the card at pos.
local function takeCard(id, pos, after)
  for _, o in ipairs(getObjects()) do
    if o.type == "Card" and notes(o) == id then
      o.setPositionSmooth(pos, false, true)
      o.setRotationSmooth({x = 0, y = 180, z = 0}, false, true)
      if after then after(o) end
      return
    end
  end
  local main = mainDeck(kindOf(id))
  local decks = {main}
  for _, o in ipairs(getObjects()) do if o.type == "Deck" and not isMain(o, kindOf(id)) then table.insert(decks, o) end end
  for _, d in ipairs(decks) do
    for _, c in ipairs(d.getObjects()) do
      if c.gm_notes == id then
        d.takeObject({guid = c.guid, position = pos, rotation = {x = 0, y = 180, z = 0}, smooth = true,
                      callback_function = after})
        return
      end
    end
  end
end

-- A card (or a small deck players made) goes back into its kind's deck.
local function sendHome(kind, o)
  o.setLock(false)
  local main = mainDeck(kind)
  if main and not isMain(o, kind) then
    local d = main.putObject(o)
    if alive(d) then DECK[kind] = d.getGUID() end   -- two single cards become a new deck
  else
    o.setPosition(deckHome(kind))
    o.setRotation({x = 0, y = 180, z = 180})
    o.setScale({x = L.deck_s[kind], y = 1, z = L.deck_s[kind]})
    DECK[kind] = o.getGUID()
  end
end

-- Every card on the table goes home. A small deck of one kind goes home whole; a mixed one (a monster
-- and a treasure token stacked on a mat) is taken apart first. Joining two cards destroys both and
-- makes a new deck, so a piece met later in the loop may be gone: touching it stopped the whole RESET
-- ("Value cannot be null", seen live 2026-10-25). Each piece is checked, and one that fails is skipped.
local function gatherOne(o)
  if not alive(o) then return end
  if o.type == "Card" then
    local kind = kindOf(notes(o))
    if kind and not isMain(o, kind) then sendHome(kind, o) end
  elseif o.type == "Deck" and not isMain(o) then
    local kinds, first = {}, nil
    for _, c in ipairs(o.getObjects()) do
      local k = kindOf(c.gm_notes)
      if k then kinds[k] = true first = first or k end
    end
    local n = 0
    for _ in pairs(kinds) do n = n + 1 end
    if n == 1 then
      sendHome(first, o)
    elseif n > 1 then
      -- All but the last card: taking a deck's last card throws an error Lua can't catch (the deck is
      -- turning into that card, seen live 2026-10-25). The card left over goes home in the second pass.
      local cards = o.getObjects()
      for i = 1, #cards - 1 do
        local k = kindOf(cards[i].gm_notes)
        if k then
          o.takeObject({guid = cards[i].guid, position = deckHome(k), smooth = false,
                        callback_function = function(card) sendHome(k, card) end})
        end
      end
    end
  end
end
local function gatherCards()
  for _, o in ipairs(getObjects()) do pcall(gatherOne, o) end
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
  if v == "mats" then return {position = {x = 0, y = 0, z = 0}, pitch = 75, yaw = 0, distance = 60} end
  if v == "chart" then return {position = {x = -16.5, y = 0, z = -0.2}, pitch = 66, yaw = 0, distance = 16} end
  if v == "supply" then return {position = {x = 4, y = 0, z = 7}, pitch = 64, yaw = 0, distance = 34} end
  if v == "title" then return {position = {x = 0, y = 0, z = 15.8}, pitch = 70, yaw = 0, distance = 20} end
  if v == "mat" then
    local m = L.mats[d.color]
    return {position = {x = m[1], y = 0, z = m[2]}, pitch = 62, yaw = (m[3] + 180) % 360, distance = d.distance or 15}
  end
  if v == "cell" then
    local p = cellPos(d.cell)
    -- With a colour: the room and that player's mat (where the dice are) in one shot. The view frames
    -- both (half-way put the far-left mat's dice off screen, seen 2026-10-19) and aims a little low,
    -- because the part's name covers the bottom of the screen.
    if d.color then
      local mx, mz = L.mats[d.color][1], L.mats[d.color][2]
      local hw = math.max(L.mat_size[1], L.mat_size[2]) / 2 + 0.5
      local hd = hw
      local x0, x1 = math.min(mx - hw, p.x - 2.2), math.max(mx + hw, p.x + 2.2)
      local z0, z1 = math.min(mz - hd, p.z - 2.2), math.max(mz + hd, p.z + 2.2)
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
  -- §3 step 3: the room deck is shuffled (the tutorial still finds its rooms by their notes).
  local deck = mainDeck("room")
  if deck and deck.type == "Deck" then deck.shuffle() glow(deck, d.color, 2) end
end

function OPS.button(d)
  for _, id in ipairs({"kbStart", "kbReset", "kbRoll"}) do UI.setAttribute(id, "active", d.show and "true" or "false") end
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

-- ROLL DICE: all four of the clicking player's dice at once (Yavuz, 2026-10-26: "4 zarın birden
-- rollanması lazım"). The tutorial's jump with a random face: each die lands back on its own spot of
-- the mat, so the dice never wander off it in a 10-minute game, and it is locked until it has landed
-- so it can't tumble onto another face. To keep some dice, the others are still rolled by hand (R).
ROLLING = {}
function rollDice(player)
  local color = player.color
  if not L.mats[color] then
    broadcastToColor("Sit at Red, Yellow, Green, Blue or Purple to roll your dice.", color, GOLDEN)
    return
  end
  if ROLLING[color] then return end   -- a second click while the dice are in the air
  ROLLING[color] = true
  for i = 1, 4 do
    local die = dieOf(color, i)
    if die then
      die.setLock(true)
      rollOne(color, i, math.random(1, 6), (i - 1) * 0.04)
    end
  end
  Wait.time(function()
    for i = 1, 4 do
      local die = dieOf(color, i)
      if alive(die) then die.setLock(STAGED) end
    end
    ROLLING[color] = nil
  end, 1.2)
end

-- ------------------------------------------------------------------ the dungeon (§6, §12)
-- A card the director put somewhere stays there while it films.
local function settle(card, pos, scale, color, rot)
  card.setScale({x = scale, y = 1, z = scale})
  if STAGED then card.setLock(true) end
  card.setPositionSmooth(pos, false, true)
  if rot then card.setRotationSmooth(rot, false, true) end
  glow(card, color, 3)
end

function OPS.reveal(d)
  -- The room card of this cell comes off the room deck, turns over and lands next to the room it was
  -- revealed from, passages lined up (build.py drew them that way).
  local p = cellPos(d.cell)
  takeCard(d.cell[1] .. "," .. d.cell[2], {x = p.x, y = 2.6, z = p.z}, function(card)
    Wait.time(function() settle(card, {x = p.x, y = CARD_Y, z = p.z}, L.deck_s.room, d.color) end, 0.4)
  end)
  if d.token then
    Wait.time(function() OPS.token({id = d.token, cell = d.cell, color = d.color}) end, 1.4)
  end
end

function OPS.token(d)
  local p = cellPos(d.cell)
  takeCard(d.id, {x = p.x, y = 2.4, z = p.z}, function(card)
    Wait.time(function() settle(card, {x = p.x, y = CARD_ON_CARD, z = p.z}, L.deck_s.monster, d.color) end, 0.4)
  end)
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
local function toMat(id, color, spots, n, delay)
  local px = spots[math.min(n, #spots)]
  local p = matPos(color, px[1], px[2])
  Wait.time(function()
    takeCard(id, {x = p.x, y = 2.2, z = p.z}, function(card)
      Wait.time(function() settle(card, {x = p.x, y = CARD_ON_MAT, z = p.z}, L.mat_tok_s, color, matRot(color)) end, 0.4)
    end)
  end, delay)
end

function OPS.take(d)
  -- A defeated monster goes onto POINTS; a collected treasure onto CARRIED until it is secured.
  if d.id:sub(1, 2) == "t-" then
    table.insert(CARRY[d.color], d.id)
    toMat(d.id, d.color, L.carry_px, #CARRY[d.color], 0)
  else
    table.insert(POINTS[d.color], d.id)
    toMat(d.id, d.color, L.points_px, #POINTS[d.color], 0)
  end
end

function OPS.secure(d)
  -- §12: back in the Safe Room, everything CARRIED moves to POINTS, no dice.
  for k, id in ipairs(CARRY[d.color]) do
    table.insert(POINTS[d.color], id)
    toMat(id, d.color, L.points_px, #POINTS[d.color], (k - 1) * 0.25)
  end
  CARRY[d.color] = {}
end

function OPS.loot(d)
  -- Draw the Loot card with this ID (§9: special treasure) onto the mat's Loot box, face up.
  local p = matPos(d.color, L.loot_px[1], L.loot_px[2])
  takeCard(d.id, {x = p.x, y = 1.4, z = p.z}, function(card)
    card.addTag("loot")
    Wait.time(function() settle(card, {x = p.x, y = CARD_ON_MAT, z = p.z}, L.deck_s.loot, d.color, matRot(d.color)) end, 0.4)
  end)
end

function OPS.glowloot(d)
  for _, o in ipairs(getObjectsWithTag("loot")) do if o.type == "Card" then glow(o, d.color, d.secs or 3) end end
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
  for kind, tag in pairs(L.decks) do
    for _, o in ipairs(getObjectsWithTag(tag)) do if o.type == "Deck" then DECK[kind] = o.getGUID() end end
  end
  clearMats()
  for _, id in ipairs({"kbCaption", "kbScore", "kbBanner"}) do UI.setAttribute(id, "active", "false") end
  -- ROLL DICE's faces come from math.random: seeded from the clock, so two games never roll alike.
  local t = wall()
  if t then math.randomseed(t) end
end

local function isMovable(o)
  for _, t in ipairs(MOVABLE) do if o.hasTag(t) then return true end end
  return false
end

function OPS.reset(d)
  -- d.stage: the director films, so dice and characters stay locked and only its scripts move them.
  STAGED = d.stage == true
  gatherCards()
  Wait.time(gatherCards, 1.2)    -- the last card of a small deck that was taken apart
  for _, o in ipairs(getObjects()) do
    local h = HOME[o.getGUID()]
    if h and o.type ~= "Card" then
      -- A die or a pawn is locked on the way home, so it doesn't tumble, then gets its own state back.
      -- Nothing else is locked: a locked deck takes no cards back (seen live, 2026-10-25).
      if isMovable(o) then
        local lock = h.lock == true or STAGED
        o.setLock(true)
        Wait.time(function() if alive(o) then o.setLock(lock) end end, 1.2)
      end
      o.setPositionSmooth(h.pos, false, true)
      o.setRotationSmooth(h.rot, false, true)
      o.setScale(h.scale)
    end
  end
  -- Decks back home, face down, even ones that were made again from returning cards.
  Wait.time(function()
    for kind, _ in pairs(L.decks) do
      local deck = mainDeck(kind)
      if deck then
        deck.setPositionSmooth(deckHome(kind), false, true)
        deck.setRotationSmooth({x = 0, y = 180, z = 180}, false, true)
        deck.setScale({x = L.deck_s[kind], y = 1, z = L.deck_s[kind]})
      end
    end
  end, 1.6)
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
    if L.mats[pl.color] then table.insert(out, pl.color) end
  end
  if #out == 0 then return L.colors end
  return out
end

local starting = false
function startGame(player)
  if starting then return end
  starting = true
  OPS.reset({})
  Wait.time(function()
    -- §3: the rooms, the token piles and the Loot Deck are shuffled.
    for _, kind in ipairs({"room", "monster", "treasure", "loot"}) do
      local deck = mainDeck(kind)
      if deck and deck.type == "Deck" then deck.shuffle() end
    end
    local who = seatedColors()
    OPS.deal({colors = who})
    OPS.pawns({colors = who})
    OPS.timer({left = L.game_secs, run = true, play = true})
    OPS.banner({text = "GO!"})
    Wait.time(function()
      if TIMER.play and TIMER.left > 0 then OPS.banner({}) end
      starting = false
    end, 2.5)
  end, 2.4)
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
