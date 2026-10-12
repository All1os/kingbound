--[[ Kingbound prototype: Global script (build.py fills in the __PLACEHOLDERS__).

Two users drive this table:
  * people, with the buttons at the top left. None of them is required: everything can also be
    done by hand (GDD §13).
  * the bot director (bots/play.py), through onExternalMessage. It decides everything in Python
    and only sends "show this" commands; nothing here makes a game decision.

Card kinds by CustomDeck key (the CardID is key * 100 + its place on the sheet):
  1 Action, 2 Wilds I, 3 Wilds II, 4 Wilds III, 5 Champion, 6 Loot, 7 Objective, 8 Character, 9 Ability.
Every card's GM Notes hold its GDD ID (ST1, E23, L11 ...); the bots find cards by that ID.
]]
KB_VERSION = "__VERSION__"
L = JSON.decode([==[__LAYOUT__]==])
TOKENS = JSON.decode([==[__TOKENS__]==])

COLORS = {Red = {0.86, 0.1, 0.09}, Yellow = {0.9, 0.9, 0.17}, Green = {0.19, 0.7, 0.17}, Blue = {0.12, 0.53, 1}}
GOLDEN = {1, 0.82, 0.3}
SEAT = {}
for i, s in ipairs(L.seats) do s.i = i SEAT[s.color] = s end
DISCARD_OF = {[1] = "action_d", [2] = "w1_d", [3] = "w2_d", [4] = "w3_d", [6] = "loot_d"}

-- ------------------------------------------------------------------ small helpers
local function V(p, y) return {x = p[1], y = y or 1.6, z = p[2]} end
local function rot(y, up) return {x = 0, y = y, z = up and 0 or 180} end
function cellPos(r, c) return {(c - 3) * L.grid, L.board_z + (3 - r) * L.grid} end

local function near(pos, p, r)
  local dx, dz = pos.x - p[1], pos.z - p[2]
  return dx * dx + dz * dz < r * r
end

local function alive(o)
  if o == nil then return false end
  local ok, res = pcall(function() return o.getGUID() end)
  return ok and res ~= nil
end

local function moving(o)
  local ok, m = pcall(function() return o.isSmoothMoving() end)
  return ok and m
end

function keyOf(o)
  local ok, d = pcall(function() return o.getData() end)
  if not ok or not d then return nil end
  local id = d.CardID or (d.DeckIDs and d.DeckIDs[1])
  return id and math.floor(id / 100) or nil
end

-- Every card or deck lying near p (not in a hand, not flying).
function pilesAt(p, r)
  local out = {}
  for _, o in ipairs(getObjects()) do
    if (o.type == "Deck" or o.type == "Card") and not o.held_by_color and not moving(o)
        and near(o.getPosition(), p, r or 1.2) then
      table.insert(out, o)
    end
  end
  return out
end

function pileAt(p) return pilesAt(p)[1] end

local function cardId(o) local ok, g = pcall(function() return o.getGMNotes() end) return ok and g or nil end

-- Takes the card with GDD ID `id` (any card if id is nil) from whatever lies at p and moves it to
-- target. Works on a deck and on the single card a deck turns into when one card is left.
function takeById(p, id, target, rotation)
  for _, o in ipairs(pilesAt(p)) do
    if o.type == "Card" then
      if id == nil or cardId(o) == id or (cardId(o) == "" and L.names[id] == o.getName()) then
        o.setPositionSmooth(target, false, true)
        o.setRotationSmooth(rotation, false, true)
        return o
      end
    else
      -- Container entries carry the card's GM Notes; the name is a fallback in case they don't.
      local want = id and L.names[id]
      for _, e in ipairs(o.getObjects()) do
        if id == nil or e.gm_notes == id or ((e.gm_notes == nil or e.gm_notes == "") and want and (e.name == want or e.nickname == want)) then
          return o.takeObject({guid = e.guid, position = target, rotation = rotation, smooth = true})
        end
      end
    end
  end
  return nil
end

-- Moves a card onto the pile at p and merges it with what is there (a card or a deck).
function toPile(o, p, faceUp, rotY)
  if not alive(o) then return end
  o.setRotationSmooth(rot(rotY or 180, faceUp), false, true)
  o.setPositionSmooth(V(p, 2.4), false, true)
  Wait.time(function()
    if not alive(o) then return end
    pcall(function()
      for _, q in ipairs(pilesAt(p)) do
        if q ~= o then q.putObject(o) return end
      end
    end)
  end, 0.9)
end

-- Same, but under the deck (Merchant: "put the others on the bottom of the Loot deck", §5.3).
-- A.putObject(B) puts B on top of A, so the card goes in first and the deck on top of it.
function toBottom(o, p)
  if not alive(o) then return end
  o.setRotationSmooth(rot(180, false), false, true)
  o.setPositionSmooth(V(p, 2.6), false, true)
  Wait.time(function()
    if not alive(o) then return end
    local deck = nil
    for _, q in ipairs(pilesAt(p)) do if q ~= o then deck = q break end end
    if not deck then return end
    -- Lift the deck, put the card in its place, then the deck on top of the card. Never below
    -- the table top: a pile pushed into the table can fall through it.
    local ok = pcall(function()
      local dp = deck.getPosition()
      deck.setPosition({x = dp.x, y = dp.y + 1.5, z = dp.z})
      o.setPosition({x = dp.x, y = dp.y, z = dp.z})
      o.setRotation(rot(180, false))
      o.putObject(deck)
    end)
    if not ok then pcall(function() deck.putObject(o) end) end
  end, 0.9)
end

-- Gathers every card or deck of the given kinds into one pile at p (instant, used by RESET).
function gather(keys, p, faceUp)
  local base = nil
  for _, o in ipairs(pilesAt(p)) do if keys[keyOf(o)] then base = o break end end
  for _, o in ipairs(getObjects()) do
    if (o.type == "Card" or o.type == "Deck") and o ~= base and keys[keyOf(o)] then
      if not base then
        base = o
        base.setPosition(V(p, 1.6))
        base.setRotation(rot(180, faceUp))
      else
        base = base.putObject(o) or base
      end
    end
  end
  if base then base.setRotation(rot(180, faceUp)) end
  return base
end

-- When a deck runs out its discard pile becomes the new deck (§5.3).
function refill(drawP, discP)
  local base = nil
  for _, o in ipairs(pilesAt(discP, 1.6)) do
    if not base then
      base = o
      base.setPosition(V(drawP, 1.8))
      base.setRotation(rot(180, false))
    else
      base = base.putObject(o) or base
    end
  end
  if base then Wait.time(function() if alive(base) and base.type == "Deck" then base.shuffle() end end, 0.4) end
  return base
end

function shuffleAt(p)
  local d = pileAt(p)
  if d and d.type == "Deck" then d.shuffle() end
end

local function tagged(tag, color)
  for _, o in ipairs(getObjectsWithTag(tag)) do
    if color == nil or o.getGMNotes() == color then return o end
  end
end

function pawnOf(color) return tagged("pawn", color) end
function markerOf(color) return tagged("marker", color) end
function boardOf(color) return tagged("pboard", color) end

function trackPos(level, color)
  local s = SEAT[color]
  return {L.track.x + (level - 5.5) * L.track.dx + s.moff[1], L.track.z + s.moff[2]}
end

function campOf(color)
  local s = SEAT[color]
  return cellPos(s.camp[1], s.camp[2])
end

local function onCell(color, r, c)
  local s, p = SEAT[color], cellPos(r, c)
  return {x = p[1] + s.off[1], y = 1.7, z = p[2] + s.off[2]}
end

function setLevel(color, level)
  local m = markerOf(color)
  if m then
    local p = trackPos(math.max(1, math.min(10, level)), color)
    m.setPositionSmooth(V(p, 1.5), false, true)
  end
end

function clearTokens()
  for _, o in ipairs(getObjectsWithTag("dmg")) do o.destruct() end
end

-- Damage tokens (§6.2 step 2): 5s first, then 1s, in a 3 x 3 grid on the enemy card.
TOKEN_SPOTS = {{-0.62, 0.95}, {0, 0.95}, {0.62, 0.95}, {-0.62, 0}, {0, 0}, {0.62, 0},
               {-0.62, -0.95}, {0, -0.95}, {0.62, -0.95}}
function setDamage(total)
  clearTokens()
  local p = L.piles.enemy
  local k = 0
  local function put(data)
    k = k + 1
    local spot = TOKEN_SPOTS[((k - 1) % #TOKEN_SPOTS) + 1]
    local lift = math.floor((k - 1) / #TOKEN_SPOTS) * 0.3
    spawnObjectData({data = data, position = {p[1] + spot[1], 1.9 + lift, p[2] + spot[2]}, rotation = {0, 180, 0}})
  end
  total = math.max(0, math.floor(total or 0))
  for _ = 1, math.floor(total / 5) do put(TOKENS.d5) end
  for _ = 1, total % 5 do put(TOKENS.d1) end
end

-- Moves a board tile. Tiles stay locked (locked objects pass through each other); the final
-- setPosition makes sure the tile ends exactly on its square even if a smooth move is skipped.
local function placeTile(o, r, c, delay)
  local p = cellPos(r, c)
  Wait.time(function()
    o.setPositionSmooth({x = p[1], y = 1.2, z = p[2]}, false, false)
    o.setRotationSmooth(rot(180, true), false, false)
    Wait.time(function() o.setPosition({x = p[1], y = 1.05, z = p[2]}) o.setRotation(rot(180, true)) end, 1.4)
  end, delay)
end

local function shuffled(list)
  for i = #list, 2, -1 do
    local j = math.random(i)
    list[i], list[j] = list[j], list[i]
  end
  return list
end

local function ringOf(r, c) return math.max(math.abs(r - 3), math.abs(c - 3)) end

local function ringCells(ring)
  local out = {}
  for r = 0, 6 do for c = 0, 6 do if ringOf(r, c) == ring then table.insert(out, {r, c}) end end end
  return out
end

-- Tile GM Notes are "ring:kind", for example "2:Merchant" or "3:Wilds3".
local function tilesByKey()
  local pool = {}
  for _, o in ipairs(getObjectsWithTag("tile")) do
    local key = o.getGMNotes()
    pool[key] = pool[key] or {}
    table.insert(pool[key], o)
  end
  return pool
end

-- ------------------------------------------------------------------ overlays (for the bot video)
function caption(head, text)
  UI.setAttribute("kbCaption", "active", "true")
  UI.setValue("kbCaptionHead", head or "")
  UI.setValue("kbCaptionText", text or "")
end

function status(lines)
  UI.setAttribute("kbStatus", "active", "true")
  for i = 1, 4 do
    local ln = lines and lines[i]
    UI.setValue("kbStatus" .. i, ln and ln.text or "")
    if ln and ln.hex then UI.setAttribute("kbStatus" .. i, "color", ln.hex) end
  end
end

function hideOverlays()
  UI.setAttribute("kbCaption", "active", "false")
  UI.setAttribute("kbStatus", "active", "false")
end

-- ------------------------------------------------------------------ buttons for people
function buildBoard(player)
  -- §3: the Castle, the Camps and the Wilds I corners never move; the middle and the outer ring
  -- are each shuffled within themselves.
  local pool = tilesByKey()
  for _, ring in ipairs({2, 3}) do
    local tiles = {}
    for key, list in pairs(pool) do
      if string.sub(key, 1, 1) == tostring(ring) then
        for _, o in ipairs(list) do table.insert(tiles, o) end
      end
    end
    local cells = shuffled(ringCells(ring))
    for i, o in ipairs(tiles) do
      if cells[i] then placeTile(o, cells[i][1], cells[i][2], (ring - 2) * 0.8 + i * 0.03) end
    end
  end
  broadcastToAll("Board built: the middle and outer rings are shuffled (GDD §3).", GOLDEN)
end

function setupGame(player)
  -- §4 steps 2-7: characters face up, their Abilities ready, a hidden objective and a full hand
  -- each, level 1, full HP, 3 gold, pawns on their Camps, a random first player.
  resetBook()
  for _, p in ipairs({L.piles.chars, L.piles.objs, L.piles.action}) do shuffleAt(p) end
  Wait.time(function()
    for i, s in ipairs(L.seats) do
      Wait.time(function()
        local deck = pileAt(L.piles.chars)
        if not deck then return end
        local function placed(card)
          local ch = L.chars[card.getName()]
          if not ch then return end
          for k, name in ipairs(ch.abilities) do
            local o = takeById(L.piles.abils, L.ability_ids[name], V(s.abil[k], 1.8), rot(s.rot, true))
            B.abil[s.color][name] = o
          end
          local ob = pileAt(L.piles.objs)
          if ob then ob.deal(1, s.color) end
          local act = pileAt(L.piles.action)
          if act then act.deal(ch.hand, s.color) end
          local b = boardOf(s.color)
          if b then
            b.call("set", {hp = ch.hp, max = ch.hp, gold = 3, STR = ch.STR, AGI = ch.AGI, WIS = ch.WIS,
                           title = s.color .. " · " .. card.getName()})
          end
          setLevel(s.color, 1)
          local pawn = pawnOf(s.color)
          if pawn then pawn.setPositionSmooth(onCell(s.color, s.camp[1], s.camp[2]), false, true) end
        end
        if deck.type == "Deck" then
          deck.takeObject({position = V(s.char, 1.8), rotation = rot(s.rot, true), smooth = true,
                           callback_function = placed})
        else
          deck.setPositionSmooth(V(s.char, 1.8), false, true)
          deck.setRotationSmooth(rot(s.rot, true), false, true)
          placed(deck)
        end
      end, (i - 1) * 0.7)
    end
    Wait.time(function()
      local first = L.seats[math.random(#L.seats)]
      local pawn = pawnOf(first.color)
      if pawn then pawn.highlightOn(COLORS[first.color], 6) end
      broadcastToAll("Setup done. " .. first.color .. " goes first; play goes clockwise (GDD §4).", GOLDEN)
    end, #L.seats * 0.7 + 1.5)
  end, 0.5)
end

local function drawFrom(drawP, discP, label)
  local d = pileAt(drawP)
  if not d then
    d = refill(drawP, discP)
    if not d then broadcastToAll(label .. ": the deck and its discard pile are empty.", {1, 0.5, 0.4}) end
  end
  return d
end

-- deal() only works on a deck; the last card of a deck is a plain card, moved into the hand zone.
local function dealOne(o, color)
  if not o then return end
  if o.type == "Deck" then o.deal(1, color) return end
  local ok, hand = pcall(function() return Player[color].getHandTransform() end)
  if ok and hand then o.setPositionSmooth(hand.position, false, true) end
end

function drawAction(player)
  if not SEAT[player.color] then
    broadcastToColor("Sit at one of the four colored seats first.", player.color, {1, 0.5, 0.5})
    return
  end
  local d = pileAt(L.piles.action)
  if not d then
    refill(L.piles.action, L.piles.action_d)
    Wait.time(function() dealOne(pileAt(L.piles.action), player.color) end, 0.8)
    return
  end
  dealOne(d, player.color)
end

local function reveal(deckKey, discKey, label)
  local d = drawFrom(L.piles[deckKey], L.piles[discKey], label)
  if not d then return end
  Wait.time(function() takeById(L.piles[deckKey], nil, V(L.piles.enemy, 2.0), rot(180, true)) end, 0.5)
end

function wilds1(player) reveal("w1", "w1_d", "Wilds I") end
function wilds2(player) reveal("w2", "w2_d", "Wilds II") end
function wilds3(player) reveal("w3", "w3_d", "Wilds III") end

function merchant(player)
  -- §5.3: draw 3 Loot cards; buy one, the others go to the bottom of the Loot deck.
  for i = 1, 3 do
    Wait.time(function()
      if not pileAt(L.piles.loot) then refill(L.piles.loot, L.piles.loot_d) end
      takeById(L.piles.loot, nil, V(L.offer[i], 1.8), rot(180, true))
    end, (i - 1) * 0.3)
  end
end

local function championCard()
  for _, o in ipairs(getObjects()) do
    if o.type == "Card" and keyOf(o) == 5 then return o end
  end
end

function trial(player)
  local c = championCard()
  if not c then return end
  c.setPositionSmooth(V(L.piles.enemy, 1.8), false, true)
  c.setRotationSmooth(rot(180, true), false, true)
  broadcastToAll("The King's Trial: Champion HP 20, ATK 5, at most 10 damage per round. Nobody can help (GDD §8).", GOLDEN)
end

-- Everything in the fight area goes to its own discard pile; damage tokens are removed.
function clearFight(player)
  local spots = {L.piles.enemy}
  for _, list in ipairs({L.played, L.helper, L.extra}) do for _, p in ipairs(list) do table.insert(spots, p) end end
  local k = 0
  for _, p in ipairs(spots) do
    for _, o in ipairs(pilesAt(p, 1.3)) do
      k = k + 1
      local key = keyOf(o)
      Wait.time(function()
        if key == 5 then
          o.setPositionSmooth(V(L.piles.champ, 1.6), false, true)
          o.setRotationSmooth(rot(180, true), false, true)
        else
          toPile(o, L.piles[DISCARD_OF[key] or "action_d"], true)
        end
      end, k * 0.12)
    end
  end
  for i, p in ipairs(L.offer) do
    for _, o in ipairs(pilesAt(p, 1.3)) do Wait.time(function() toBottom(o, L.piles.loot) end, 0.4 + i * 0.3) end
  end
  clearTokens()
  B.played, B.helper, B.extra, B.enemy, B.offer = {}, {}, {}, nil, {}
end

function resetGame(player)
  clearTokens()
  gather({[1] = true}, L.piles.action, false)
  gather({[2] = true}, L.piles.w1, false)
  gather({[3] = true}, L.piles.w2, false)
  gather({[4] = true}, L.piles.w3, false)
  gather({[5] = true}, L.piles.champ, true)
  gather({[6] = true}, L.piles.loot, false)
  gather({[7] = true}, L.piles.objs, false)
  gather({[8] = true}, L.piles.chars, false)
  gather({[9] = true}, L.piles.abils, true)
  Wait.time(function()
    for _, p in ipairs({L.piles.action, L.piles.w1, L.piles.w2, L.piles.w3, L.piles.loot, L.piles.objs, L.piles.chars}) do
      shuffleAt(p)
    end
  end, 0.5)
  for _, s in ipairs(L.seats) do
    local b = boardOf(s.color)
    if b then b.call("set", {hp = 0, max = 0, gold = 0, STR = 0, AGI = 0, WIS = 0, title = s.color}) end
    setLevel(s.color, 1)
    local pawn = pawnOf(s.color)
    if pawn then pawn.setPositionSmooth(onCell(s.color, s.camp[1], s.camp[2]), false, true) end
  end
  resetBook()
  if player then broadcastToAll("Table reset. Press SETUP to deal a new game.", GOLDEN) end
end

-- ------------------------------------------------------------------ the bot director's commands
-- B remembers which card object is where, so the director can say "play ST2 from Red's hand"
-- without knowing any GUID. Each record is {id = "ST2", obj = <card>}.
B = {}
function resetBook()
  B = {hand = {}, abil = {}, items = {}, obj = {}, played = {}, helper = {}, extra = {}, offer = {}, enemy = nil}
  for _, s in ipairs(L.seats) do B.hand[s.color] = {} B.abil[s.color] = {} B.items[s.color] = {} end
end
resetBook()

local function reply(kind, text)
  pcall(function() sendExternalMessage({kind = kind, text = text}) end)
end

local function slot(list, k, u)
  if k <= #list then return list[k] end
  local last, e = list[#list], k - #list
  u = u or {1, 0}
  return {last[1] + u[1] * 0.45 * e, last[2] + u[2] * 0.45 * e}
end

local function handSpot(color, k) local s = SEAT[color] return slot(s.hand, k, s.u) end

local function repack(color)
  for k, rec in ipairs(B.hand[color]) do
    if alive(rec.obj) then rec.obj.setPositionSmooth(V(handSpot(color, k), 1.6), false, true) end
  end
end

local function fromHand(color, id)
  for k, rec in ipairs(B.hand[color]) do
    if rec.id == id then return table.remove(B.hand[color], k) end
  end
end

local function itemSpot(color, kind, k)
  local s = SEAT[color]
  return slot(kind == "equip" and s.equip or s.use, k, s.u)
end

local function repackItems(color)
  local n = {equip = 0, use = 0}
  for _, rec in ipairs(B.items[color]) do
    n[rec.slot] = n[rec.slot] + 1
    if alive(rec.obj) then rec.obj.setPositionSmooth(V(itemSpot(color, rec.slot, n[rec.slot]), 1.6), false, true) end
  end
end

local function addItem(color, rec, kind)
  rec.slot = kind
  table.insert(B.items[color], rec)
  local n = 0
  for _, r in ipairs(B.items[color]) do if r.slot == kind then n = n + 1 end end
  return itemSpot(color, kind, n)
end

local function fromItems(color, id)
  for k, rec in ipairs(B.items[color]) do
    if rec.id == id then return table.remove(B.items[color], k) end
  end
end

OPS = {}

function OPS.hello(d)
  reply("hello", KB_VERSION)
end

function OPS.reset(d)
  resetGame(nil)
  hideOverlays()
end

function OPS.board(d)
  local pool = tilesByKey()
  for i, cell in ipairs(d.cells) do
    local list = pool[cell.key]
    local o = list and table.remove(list)
    if o then placeTile(o, cell.r, cell.c, (i - 1) * (d.t or 0.05))
    else reply("error", "board: no tile left for " .. tostring(cell.key)) end
  end
end

-- One command deals a whole table: characters, Abilities (ready or used), hidden objectives,
-- items, hands, boards, level markers and pawns. Used for the real start and for the demo.
function OPS.setup(d)
  local t = d.t or 0.12
  local k = 0
  local function later(f) k = k + 1 Wait.time(f, k * t) end
  for _, p in ipairs(d.players) do
    local s = SEAT[p.color]
    later(function()
      local o = takeById(L.piles.chars, p.char_id, V(s.char, 1.8), rot(s.rot, true))
      if not o then reply("error", "setup: character " .. p.char_id .. " not found") end
    end)
    for i, ab in ipairs(p.abilities) do
      later(function()
        local o = takeById(L.piles.abils, ab.id, V(s.abil[i], 1.8), rot(s.rot, not ab.used))
        B.abil[p.color][ab.name] = o
      end)
    end
    later(function()
      B.obj[p.color] = takeById(L.piles.objs, p.objective, V(s.obj, 1.8), rot(s.rot, p.objective_open == true))
    end)
    for _, it in ipairs(p.items or {}) do
      local rec = {id = it.id}
      local spot = addItem(p.color, rec, it.slot)
      later(function() rec.obj = takeById(L.piles.loot, it.id, V(spot, 1.8), rot(s.rot, true)) end)
    end
    for _, id in ipairs(p.hand) do
      local rec = {id = id}
      table.insert(B.hand[p.color], rec)
      local spot = handSpot(p.color, #B.hand[p.color])
      later(function() rec.obj = takeById(L.piles.action, id, V(spot, 1.8), rot(s.rot, true)) end)
    end
    local b = boardOf(p.color)
    if b then b.call("set", {hp = p.hp, max = p.max, gold = p.gold, STR = p.STR, AGI = p.AGI, WIS = p.WIS, title = p.title}) end
    setLevel(p.color, p.level)
    local pawn = pawnOf(p.color)
    if pawn then pawn.setPositionSmooth(onCell(p.color, p.pos[1], p.pos[2]), false, true) end
  end
end

function OPS.caption(d) caption(d.head, d.text) end
function OPS.status(d) status(d.lines) end
function OPS.stop(d) hideOverlays() end

function OPS.highlight(d)
  local pawn = pawnOf(d.color)
  if pawn then pawn.highlightOn(COLORS[d.color], d.t or 2) end
  local b = boardOf(d.color)
  if b then b.highlightOn(COLORS[d.color], d.t or 2) end
end

function OPS.roll(d)
  local die = tagged("die")
  if not die then return end
  local p, t = L.die, d.t or 1
  die.setPositionSmooth({x = p[1], y = 3.4, z = p[2]}, false, true)
  die.setRotationSmooth({x = math.random(0, 359), y = math.random(0, 359), z = math.random(0, 359)}, false, true)
  Wait.time(function() die.setRotationValue(d.value) end, 0.35 * t)
  if d.color then die.highlightOn(COLORS[d.color] or GOLDEN, 1.5 * t) end
end

function OPS.move(d)
  local pawn = pawnOf(d.color)
  if not pawn then return end
  for i, rc in ipairs(d.path) do
    Wait.time(function() pawn.setPositionSmooth(onCell(d.color, rc[1], rc[2]), false, true) end, (i - 1) * (d.t or 0.35))
  end
end

function OPS.draw(d)
  local src = L.piles[d.from or "action"]
  local s = SEAT[d.color]
  for i, id in ipairs(d.cards) do
    local rec = {id = id}
    table.insert(B.hand[d.color], rec)
    local spot = handSpot(d.color, #B.hand[d.color])
    Wait.time(function()
      rec.obj = takeById(src, id, V(spot, 1.9), rot(s.rot, true))
      if not rec.obj then reply("error", "draw: " .. id .. " is not in the deck") end
    end, (i - 1) * (d.t or 0.15))
  end
end

function OPS.discard(d)
  for i, id in ipairs(d.cards) do
    local rec = fromHand(d.color, id)
    if rec then Wait.time(function() toPile(rec.obj, L.piles.action_d, true) end, (i - 1) * (d.t or 0.12))
    else reply("error", "discard: " .. id .. " is not in " .. d.color .. "'s hand") end
  end
  Wait.time(function() repack(d.color) end, #d.cards * (d.t or 0.12) + 0.3)
end

function OPS.play(d)
  local row, spots = B.played, L.played
  if d.helper then row, spots = B.helper, L.helper end
  for i, id in ipairs(d.cards) do
    local rec = fromHand(d.color, id)
    if rec then
      table.insert(row, rec)
      local spot = slot(spots, #row)
      Wait.time(function()
        if alive(rec.obj) then
          rec.obj.setPositionSmooth(V(spot, 1.9), false, true)
          rec.obj.setRotationSmooth(rot(180, true), false, true)
        end
      end, (i - 1) * (d.t or 0.2))
    else
      reply("error", "play: " .. id .. " is not in " .. d.color .. "'s hand")
    end
  end
  Wait.time(function() repack(d.color) end, #d.cards * (d.t or 0.2) + 0.3)
end

function OPS.reshuffle(d)
  refill(L.piles[d.deck], L.piles[d.deck .. "_d"])
end

function OPS.reveal(d)
  if d.deck == "champ" then
    B.enemy = championCard()
    if B.enemy then
      B.enemy.setPositionSmooth(V(L.piles.enemy, 1.9), false, true)
      B.enemy.setRotationSmooth(rot(180, true), false, true)
    end
  else
    B.enemy = takeById(L.piles[d.deck], d.id, V(L.piles.enemy, 2.0), rot(180, true))
    if not B.enemy then reply("error", "reveal: " .. tostring(d.id) .. " is not in " .. d.deck) end
  end
  if alive(B.enemy) then B.enemy.highlightOn(GOLDEN, 2) end
end

function OPS.damage(d) setDamage(d.total) end

function OPS.ability(d)
  local o = B.abil[d.color] and B.abil[d.color][d.name]
  if not alive(o) then reply("error", "ability: " .. tostring(d.name) .. " not found for " .. d.color) return end
  o.setRotationSmooth(rot(SEAT[d.color].rot, not d.used), false, true)
  if d.used then o.highlightOn(COLORS[d.color], 2) end
end

function OPS.ready(d)
  for _, o in pairs(B.abil[d.color] or {}) do
    if alive(o) then o.setRotationSmooth(rot(SEAT[d.color].rot, true), false, true) end
  end
end

function OPS.offer(d)
  B.offer = {}
  for i, id in ipairs(d.cards) do
    local rec = {id = id}
    table.insert(B.offer, rec)
    Wait.time(function()
      rec.obj = takeById(L.piles.loot, id, V(L.offer[i], 1.9), rot(180, true))
      if not rec.obj then reply("error", "offer: " .. id .. " is not in the Loot deck") end
    end, (i - 1) * 0.25)
  end
end

function OPS.buy(d)
  for k, rec in ipairs(B.offer) do
    if rec.id == d.id then
      table.remove(B.offer, k)
      local spot = addItem(d.color, rec, d.slot)
      if alive(rec.obj) then
        rec.obj.setPositionSmooth(V(spot, 1.9), false, true)
        rec.obj.setRotationSmooth(rot(SEAT[d.color].rot, true), false, true)
      end
      return
    end
  end
  reply("error", "buy: " .. tostring(d.id) .. " is not on offer")
end

function OPS.unoffer(d)
  for i, rec in ipairs(B.offer) do
    Wait.time(function() toBottom(rec.obj, L.piles.loot) end, (i - 1) * 0.25)
  end
  B.offer = {}
end

function OPS.loot(d)
  local s = SEAT[d.color]
  local rec = {id = d.id}
  local spot = addItem(d.color, rec, d.slot)
  rec.obj = takeById(L.piles.loot, d.id, V(spot, 1.9), rot(s.rot, true))
  if not rec.obj then reply("error", "loot: " .. d.id .. " is not in the Loot deck") end
end

-- An item leaves a player: into the fight area (used in a fight, cleared with it) or straight
-- to the Loot discard pile (used outside a fight, or dropped for a better one).
function OPS.item(d)
  local rec = fromItems(d.color, d.id)
  if not rec then reply("error", "item: " .. tostring(d.id) .. " not held by " .. d.color) return end
  if d.to == "fight" then
    table.insert(B.extra, rec)
    if alive(rec.obj) then
      rec.obj.setPositionSmooth(V(slot(L.extra, #B.extra), 1.9), false, true)
      rec.obj.setRotationSmooth(rot(180, true), false, true)
    end
  elseif d.to then
    local rec2 = rec
    local spot = addItem(d.to, rec2, d.slot or "use")
    if alive(rec2.obj) then
      rec2.obj.setPositionSmooth(V(spot, 1.9), false, true)
      rec2.obj.setRotationSmooth(rot(SEAT[d.to].rot, true), false, true)
    end
  else
    toPile(rec.obj, L.piles.loot_d, true)
  end
  Wait.time(function() repackItems(d.color) end, 0.6)
end

function OPS.objective(d)
  local o = B.obj[d.color]
  if not alive(o) then reply("error", "objective: no card for " .. d.color) return end
  o.setRotationSmooth(rot(SEAT[d.color].rot, true), false, true)
  o.highlightOn(COLORS[d.color], 4)
end

function OPS.player(d)
  local b = boardOf(d.color)
  if b then b.call("set", {hp = d.hp, max = d.max, gold = d.gold, STR = d.STR, AGI = d.AGI, WIS = d.WIS, title = d.title}) end
  if d.level then setLevel(d.color, d.level) end
end

function OPS.clear(d)
  local k = 0
  local function away(o)
    if not alive(o) then return end
    k = k + 1
    local key = keyOf(o)
    Wait.time(function()
      if key == 5 then
        o.setPositionSmooth(V(L.piles.champ, 1.6), false, true)
        o.setRotationSmooth(rot(180, true), false, true)
      else
        toPile(o, L.piles[DISCARD_OF[key] or "action_d"], true)
      end
    end, k * 0.1)
  end
  for _, rec in ipairs(B.played) do away(rec.obj) end
  for _, rec in ipairs(B.helper) do away(rec.obj) end
  for _, rec in ipairs(B.extra) do away(rec.obj) end
  away(B.enemy)
  B.played, B.helper, B.extra, B.enemy = {}, {}, {}, nil
  clearTokens()
  -- Anything still in the fight area (for example cards TTS stacked into a deck) follows them.
  Wait.time(function() sweepFight() end, k * 0.1 + 1.2)
end

function sweepFight()
  local spots = {L.piles.enemy}
  for _, list in ipairs({L.played, L.helper, L.extra}) do for _, p in ipairs(list) do table.insert(spots, p) end end
  for _, p in ipairs(spots) do
    for _, o in ipairs(pilesAt(p, 1.3)) do
      local key = keyOf(o)
      if key == 5 then
        o.setPositionSmooth(V(L.piles.champ, 1.6), false, true)
        o.setRotationSmooth(rot(180, true), false, true)
      else
        toPile(o, L.piles[DISCARD_OF[key] or "action_d"], true)
      end
    end
  end
end

function OPS.win(d)
  setLevel(d.color, 10)
  local pawn = pawnOf(d.color)
  if pawn then pawn.highlightOn(COLORS[d.color], 60) end
  local b = boardOf(d.color)
  if b then b.highlightOn(COLORS[d.color], 60) end
  local champ = championCard()
  if champ then champ.highlightOn(GOLDEN, 60) end
end

function OPS.camera(d)
  for _, pl in ipairs(Player.getPlayers()) do
    if pl.host then
      pcall(function()
        pl.lookAt({position = {x = d.x, y = 0, z = d.z}, pitch = d.pitch or 55, yaw = d.yaw or 0, distance = d.dist or 30})
      end)
    end
  end
end

function onExternalMessage(d)
  if type(d) ~= "table" then return end
  local f = OPS[d.op]
  if not f then reply("error", "unknown command " .. tostring(d.op)) return end
  local ok, err = pcall(f, d)
  if not ok then reply("error", tostring(d.op) .. ": " .. tostring(err)) end
end
