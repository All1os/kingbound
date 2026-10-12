--[[ A fake Tabletop Simulator, just enough to run the Kingbound Global script outside the game.

It copies the TTS behaviours the script depends on: a deck is a container of card entries,
takeObject() spawns a card, a deck with one card left turns into a loose card, putObject() stacks
cards into a deck (A.putObject(B) puts B on top), Wait.time() runs later on a simulated clock and a
destroyed object raises an error when used. Moves are instant. It is not TTS: it catches script
errors and bookkeeping mistakes, not physics or looks.

Usage (from check_tts_script.py): lua fake_tts.lua <input.lua>
The input file defines OBJECTS (the save's objects), SCRIPT (the Global Lua), STEPS (messages for
onExternalMessage with the seconds to wait after each) and EXPECT (hands and items per colour at
the end).
]]

-- ------------------------------------------------------------------ JSON (TTS provides one)
JSON = {}
function JSON.decode(s)
  local i = 1
  local function ws() while true do local c = s:sub(i, i) if c == " " or c == "\n" or c == "\r" or c == "\t" then i = i + 1 else break end end end
  local value
  local function str()
    i = i + 1
    local out = {}
    while true do
      local c = s:sub(i, i)
      if c == '"' then i = i + 1 break end
      if c == "\\" then
        local n = s:sub(i + 1, i + 1)
        if n == "u" then
          local code = tonumber(s:sub(i + 2, i + 5), 16)
          out[#out + 1] = utf8.char(code)
          i = i + 6
        else
          out[#out + 1] = ({n = "\n", t = "\t", r = "\r", b = "\b", f = "\f"})[n] or n
          i = i + 2
        end
      else
        out[#out + 1] = c
        i = i + 1
      end
    end
    return table.concat(out)
  end
  function value()
    ws()
    local c = s:sub(i, i)
    if c == "{" then
      local t = {}
      i = i + 1 ws()
      if s:sub(i, i) == "}" then i = i + 1 return t end
      while true do
        ws() local k = str() ws() i = i + 1
        t[k] = value() ws()
        local d = s:sub(i, i) i = i + 1
        if d == "}" then return t end
      end
    elseif c == "[" then
      local t = {}
      i = i + 1 ws()
      if s:sub(i, i) == "]" then i = i + 1 return t end
      while true do
        t[#t + 1] = value() ws()
        local d = s:sub(i, i) i = i + 1
        if d == "]" then return t end
      end
    elseif c == '"' then return str()
    elseif s:sub(i, i + 3) == "true" then i = i + 4 return true
    elseif s:sub(i, i + 4) == "false" then i = i + 5 return false
    elseif s:sub(i, i + 3) == "null" then i = i + 4 return nil
    else
      local num = s:match("^-?%d+%.?%d*[eE]?[-+]?%d*", i)
      i = i + #num
      return tonumber(num) + 0.0   -- TTS (MoonSharp) numbers are doubles
    end
  end
  return value()
end
function JSON.encode(t) return "{}" end

-- ------------------------------------------------------------------ clock and timers
CLOCK, TIMERS = 0, {}
Wait = {}
function Wait.time(fn, delay) TIMERS[#TIMERS + 1] = {at = CLOCK + (delay or 0), fn = fn} end
function Wait.frames(fn, n) Wait.time(fn, (n or 1) / 60) end
ERRORS, REPLIES = {}, {}
local function runTimers(untilT)
  while true do
    local best, bi = nil, nil
    for k, t in ipairs(TIMERS) do if t.at <= untilT and (not best or t.at < best.at) then best, bi = t, k end end
    if not best then break end
    table.remove(TIMERS, bi)
    CLOCK = math.max(CLOCK, best.at)
    local ok, err = pcall(best.fn)
    if not ok then ERRORS[#ERRORS + 1] = "timer: " .. tostring(err) end
  end
  CLOCK = untilT
end

-- ------------------------------------------------------------------ objects
LIVE, NEXT = {}, 1
local function vec(p)
  if p == nil then return {x = 0, y = 0, z = 0} end
  return {x = p.x or p[1] or 0, y = p.y or p[2] or 0, z = p.z or p[3] or 0}
end
local function destroy(o) o.alive = false for k, x in ipairs(LIVE) do if x == o then table.remove(LIVE, k) break end end end

function newObject(o)
  o.guid = string.format("f%05d", NEXT) NEXT = NEXT + 1
  o.alive = true
  o.tags = o.tags or {}
  o.pos, o.rot = vec(o.pos), vec(o.rot)
  local self = o
  local function live() if not self.alive then error("object " .. self.guid .. " is destroyed") end end
  self.getGUID = function() live() return self.guid end
  self.getName = function() live() return self.name or "" end
  self.getGMNotes = function() live() return self.gm or "" end
  self.getDescription = function() return "" end
  self.getPosition = function() live() return {x = self.pos.x, y = self.pos.y, z = self.pos.z} end
  self.setPosition = function(p) live() self.pos = vec(p) end
  self.setPositionSmooth = function(p) live() self.pos = vec(p) end
  self.getRotation = function() return self.rot end
  self.setRotation = function(r) live() self.rot = vec(r) end
  self.setRotationSmooth = function(r) live() self.rot = vec(r) end
  self.isSmoothMoving = function() live() return false end
  self.highlightOn = function() live() end
  self.setLock = function() live() end
  self.destruct = function() live() destroy(self) end
  self.setRotationValue = function(v) live() self.value = v end
  self.call = function(fn, params) live() self.calls = (self.calls or 0) + 1 self.last = params return nil end
  self.getData = function()
    live()
    if self.type == "Card" then return {CardID = self.entry.CardID} end
    if self.type == "Deck" then local ids = {} for k, e in ipairs(self.contents) do ids[k] = e.CardID end return {DeckIDs = ids} end
    return {}
  end
  if self.type == "Deck" then
    self.getObjects = function()
      live()
      local out = {}
      for k, e in ipairs(self.contents) do out[k] = {guid = e.guid, gm_notes = e.gm, name = e.name, index = k - 1} end
      return out
    end
    self.takeObject = function(p)
      live()
      p = p or {}
      local idx
      if p.guid then for k, e in ipairs(self.contents) do if e.guid == p.guid then idx = k break end end
      else idx = (p.index or 0) + 1 end
      if not idx or not self.contents[idx] then error("takeObject: no such card in the deck") end
      local e = table.remove(self.contents, idx)
      local card = newCard(e, p.position or self.pos, p.rotation or self.rot)
      if #self.contents == 1 then
        newCard(table.remove(self.contents, 1), self.pos, self.rot)   -- TTS: the last card becomes a loose card
        destroy(self)
      elseif #self.contents == 0 then destroy(self) end
      if p.callback_function then Wait.time(function() p.callback_function(card) end, 0.1) end
      return card
    end
    self.shuffle = function()
      live()
      for k = #self.contents, 2, -1 do local j = math.random(k) self.contents[k], self.contents[j] = self.contents[j], self.contents[k] end
    end
    self.deal = function(n, color)
      live()
      for _ = 1, n do
        if not self.alive or #self.contents == 0 then break end
        self.takeObject({position = HAND_ZONE[color]})
      end
    end
  end
  if self.type == "Deck" or self.type == "Card" then
    self.putObject = function(other)
      live()
      if not other.alive then error("putObject: object is destroyed") end
      local add = other.type == "Deck" and other.contents or {other.entry}
      if self.type == "Deck" then
        for k = #add, 1, -1 do table.insert(self.contents, 1, add[k]) end
        destroy(other)
        return self
      end
      local contents = {}
      for _, e in ipairs(add) do contents[#contents + 1] = e end
      contents[#contents + 1] = self.entry
      local d = newObject({type = "Deck", name = "Deck", pos = self.pos, rot = self.rot, contents = contents})
      destroy(other) destroy(self)
      return d
    end
  end
  LIVE[#LIVE + 1] = self
  return self
end

function newCard(e, pos, rot)
  return newObject({type = "Card", name = e.name, gm = e.gm, entry = e, pos = pos, rot = rot})
end

function getObjects() local out = {} for k, o in ipairs(LIVE) do out[k] = o end return out end
function getObjectsWithTag(tag)
  local out = {}
  for _, o in ipairs(LIVE) do for _, t in ipairs(o.tags) do if t == tag then out[#out + 1] = o break end end end
  return out
end
function spawnObjectData(p)
  local d = p.data
  return newObject({type = d.Name == "Custom_Tile" and "Tile" or d.Name, name = d.Nickname, gm = d.GMNotes,
                    tags = d.Tags or {}, pos = p.position, rot = p.rotation})
end
function broadcastToAll() end
function broadcastToColor() end
function printToAll() end
function sendExternalMessage(t)
  REPLIES[#REPLIES + 1] = t
  if t.kind == "error" then ERRORS[#ERRORS + 1] = "reply: " .. tostring(t.text) end
end
UI = {setValue = function() end, setAttribute = function() end}
HAND_ZONE = {}
Player = setmetatable({getPlayers = function() return {} end}, {__index = function(_, color)
  return {getHandTransform = function() return {position = HAND_ZONE[color]} end, lookAt = function() end}
end})

-- ------------------------------------------------------------------ run
dofile(arg[1])
for _, o in ipairs(OBJECTS) do
  if o.Name == "HandTrigger" then HAND_ZONE[o.FogColor] = {x = o.posX, y = 2, z = o.posZ} end
end
local cardN = 0
for _, o in ipairs(OBJECTS) do
  local pos, rot = {x = o.posX, y = o.posY, z = o.posZ}, {x = 0, y = o.rotY, z = o.rotZ}
  if o.Name == "Deck" then
    local contents = {}
    for k, c in ipairs(o.cards) do cardN = cardN + 1 contents[k] = {guid = string.format("c%04d", cardN), gm = c.gm, name = c.name, CardID = c.id} end
    newObject({type = "Deck", name = o.Nickname, pos = pos, rot = rot, contents = contents})
  elseif o.Name == "Card" then
    cardN = cardN + 1
    newCard({guid = string.format("c%04d", cardN), gm = o.cards[1].gm, name = o.cards[1].name, CardID = o.cards[1].id}, pos, rot)
  elseif o.Name ~= "HandTrigger" then
    newObject({type = o.Name == "Custom_Tile" and "Tile" or o.Name, name = o.Nickname, gm = o.GMNotes, tags = o.Tags or {}, pos = pos, rot = rot})
  end
end
local chunk, err = load(SCRIPT, "Global")
if not chunk then print("COMPILE ERROR " .. err) os.exit(1) end
chunk()

local function countCards()
  local n = 0
  for _, o in ipairs(LIVE) do
    if o.type == "Card" then n = n + 1 elseif o.type == "Deck" then n = n + #o.contents end
  end
  return n
end

for k, st in ipairs(STEPS) do
  local ok, e = pcall(onExternalMessage, st.msg)
  if not ok then ERRORS[#ERRORS + 1] = "step " .. k .. " (" .. tostring(st.msg.op) .. "): " .. tostring(e) end
  runTimers(CLOCK + st.wait)
  if #ERRORS > 0 and not CONTINUE then
    print("FIRST ERROR at step " .. k .. " op=" .. tostring(st.msg.op) .. ": " .. ERRORS[1])
    os.exit(1)
  end
end
runTimers(CLOCK + 10)

-- ------------------------------------------------------------------ checks
local problems = {}
local function bad(s) problems[#problems + 1] = s end
if countCards() ~= 132 then bad("cards on the table: " .. countCards() .. " (want 132)") end
for color, want in pairs(EXPECT.hand) do
  local got = {}
  for _, rec in ipairs(B.hand[color]) do
    if not (rec.obj and rec.obj.alive) then bad(color .. " hand: " .. rec.id .. " has no live card")
    elseif rec.obj.gm ~= rec.id then bad(color .. " hand: record " .. rec.id .. " points at " .. tostring(rec.obj.gm))
    elseif math.abs(((rec.obj.rot.y - SEAT[color].rot) % 360)) > 1 or math.abs(rec.obj.rot.z) > 1 then
      bad(color .. " hand: " .. rec.id .. " is not face up towards its player") end
    got[#got + 1] = rec.id
  end
  table.sort(got) table.sort(want)
  if table.concat(got, ",") ~= table.concat(want, ",") then bad(color .. " hand " .. table.concat(got, ",") .. " but engine has " .. table.concat(want, ",")) end
end
for color, want in pairs(EXPECT.items) do
  local got = {}
  for _, rec in ipairs(B.items[color]) do
    if not (rec.obj and rec.obj.alive) then bad(color .. " item " .. rec.id .. " has no live card") end
    got[#got + 1] = rec.id
  end
  table.sort(got) table.sort(want)
  if table.concat(got, ",") ~= table.concat(want, ",") then bad(color .. " items " .. table.concat(got, ",") .. " but engine has " .. table.concat(want, ",")) end
end
for color, n in pairs(EXPECT.used or {}) do
  local used = 0
  for _, o in pairs(B.abil[color]) do if o.alive and math.abs(o.rot.z) > 90 then used = used + 1 end end
  if used ~= n then bad(color .. " has " .. used .. " used Abilities on the table, engine has " .. n) end
end
-- the human buttons on the finished table
for _, f in ipairs({"clearFight", "resetGame", "buildBoard", "setupGame", "drawAction", "wilds1", "wilds2", "wilds3", "merchant", "trial", "clearFight", "resetGame"}) do
  local ok, e = pcall(_G[f], {color = "Red", steam_name = "test"})
  if not ok then bad("button " .. f .. ": " .. tostring(e)) end
  runTimers(CLOCK + 3)
  if countCards() ~= 132 then bad("after " .. f .. ": " .. countCards() .. " cards") end
end
for _, e in ipairs(ERRORS) do bad(e) end
print("steps " .. #STEPS .. ", simulated " .. string.format("%.0f", CLOCK) .. " s, cards " .. countCards())
if #problems == 0 then print("OK") else for _, s in ipairs(problems) do print("PROBLEM " .. s) end os.exit(1) end
