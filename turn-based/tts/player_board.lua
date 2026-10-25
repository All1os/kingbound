--[[ Kingbound player board: HP, max HP, gold and the three stats of one seat (GDD §6.1, §7).
The level lives on the level track. People click the buttons; the Global script and the bots call
set({hp = .., max = .., gold = .., STR = .., AGI = .., WIS = .., title = ..}). Values never go below
0, HP never above max HP, a stat never above 5 (§5.3).
build.py writes UI_POS: button positions, sizes and fonts that match the boxes on the board image.
The board is scaled unevenly (wider than deep), so every button gets a z scale (UI_POS.zfix) that
keeps its text in proportion.
]]
v = {hp = 0, max = 0, gold = 0, STR = 0, AGI = 0, WIS = 0, title = ""}
UI_POS = __POS__

local function clamp()
  v.max = math.max(0, v.max)
  v.hp = math.max(0, math.min(v.hp, v.max))
  v.gold = math.max(0, v.gold)
  for _, s in ipairs({"STR", "AGI", "WIS"}) do v[s] = math.max(0, math.min(5, v[s])) end
end

function onLoad(state)
  if state and state ~= "" then
    local ok, d = pcall(function() return JSON.decode(state) end)
    if ok and type(d) == "table" then for k, x in pairs(d) do v[k] = x end end
  end
  clamp()
  draw()
end

function onSave() return JSON.encode(v) end

function set(p)
  for k, x in pairs(p or {}) do
    if v[k] ~= nil then v[k] = (k == "title") and tostring(x) or (tonumber(x) or v[k]) end
  end
  clamp()
  draw()
end

function get() return v end

function noop() end

local function label(text, pos, size, color)
  self.createButton({click_function = "noop", function_owner = self, label = text, position = {pos[1], 0.12, pos[2]},
                     width = 0, height = 0, font_size = size, font_color = color or {0.96, 0.92, 0.84},
                     scale = {1, 1, UI_POS.zfix}})
end

local function button(name, text, pos, size, fn, color)
  _G[name] = function(obj, player_color, alt) fn() clamp() draw() end
  self.createButton({click_function = name, function_owner = self, label = text, position = {pos[1], 0.12, pos[2]},
                     width = size[1], height = size[2], font_size = size[3], color = color or {0.25, 0.2, 0.16},
                     font_color = {1, 1, 1}, scale = {1, 1, UI_POS.zfix}})
end

local function fmt(x) return string.format("%d", math.floor(x + 0.5)) end

function draw()
  self.clearButtons()
  local P = UI_POS
  local red, green = {0.55, 0.16, 0.12}, {0.16, 0.42, 0.22}
  label(v.title ~= "" and v.title or "PLAYER", P.title, P.title_font)
  label(fmt(v.hp) .. "/" .. fmt(v.max), P.hp, P.num_font, {1, 0.62, 0.55})
  label(fmt(v.gold), P.gold, P.num_font, {1, 0.85, 0.35})
  button("hpdown", "-", P.hp_btn[1], P.btn, function() v.hp = v.hp - 1 end, red)
  button("hpup", "+", P.hp_btn[2], P.btn, function() v.hp = v.hp + 1 end, green)
  button("hpfull", "FULL", P.hp_full, P.small, function() v.hp = v.max end)
  button("maxdown", "MAX -", P.max_btn[1], P.small, function() v.max = v.max - 1 end)
  button("maxup", "MAX +", P.max_btn[2], P.small, function() v.max = v.max + 1 v.hp = v.hp + 1 end)
  button("golddown", "-", P.gold_btn[1], P.btn, function() v.gold = v.gold - 1 end, red)
  button("goldup", "+", P.gold_btn[2], P.btn, function() v.gold = v.gold + 1 end, green)
  for i, s in ipairs({"STR", "AGI", "WIS"}) do
    label(s .. " " .. fmt(v[s]), P.stat[i], P.stat_font)
    button("down" .. s, "-", P.stat_btn[i][1], P.stat_size, function() v[s] = v[s] - 1 end, red)
    button("up" .. s, "+", P.stat_btn[i][2], P.stat_size, function() v[s] = v[s] + 1 end, green)
  end
end
