--[[ Kingbound player board: HP, max HP, gold and the three stats of one seat (GDD §6.1, §7).
The level lives on the level track. People click the buttons; the Global script and the bots call
set({hp = .., max = .., gold = .., STR = .., AGI = .., WIS = .., title = ..}). Values never go below
0, HP never above max HP, a stat never above 5 (§5.3).
build.py writes the button positions; they match the boxes printed on the board image.
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
                     width = 0, height = 0, font_size = size, font_color = color or {0.96, 0.92, 0.84}})
end

local function button(name, text, pos, w, h, size, fn, color)
  _G[name] = function(obj, player_color, alt) fn() clamp() draw() end
  self.createButton({click_function = name, function_owner = self, label = text, position = {pos[1], 0.12, pos[2]},
                     width = w, height = h, font_size = size, color = color or {0.25, 0.2, 0.16},
                     font_color = {1, 1, 1}})
end

local function fmt(x) return string.format("%d", math.floor(x + 0.5)) end

function draw()
  self.clearButtons()
  local P = UI_POS
  label(v.title ~= "" and v.title or "PLAYER", P.title, 150)
  label(fmt(v.hp) .. "/" .. fmt(v.max), P.hp, 330, {1, 0.62, 0.55})
  label(fmt(v.gold), P.gold, 330, {1, 0.85, 0.35})
  local red, green = {0.55, 0.16, 0.12}, {0.16, 0.42, 0.22}
  for i, d in ipairs({-2, -1, 1, 2}) do
    button("hp" .. i, (d > 0 and "+" or "") .. d, P.hp_btn[i], 260, 190, 120, function() v.hp = v.hp + d end,
           d > 0 and green or red)
  end
  button("hpfull", "FULL", P.hp_full, 330, 150, 90, function() v.hp = v.max end)
  button("maxdown", "MAX -", P.max_btn[1], 330, 150, 80, function() v.max = v.max - 1 end)
  button("maxup", "MAX +", P.max_btn[2], 330, 150, 80, function() v.max = v.max + 1 v.hp = v.hp + 1 end)
  for i, d in ipairs({-3, -1, 1, 3}) do
    button("gold" .. i, (d > 0 and "+" or "") .. d, P.gold_btn[i], 260, 190, 120, function() v.gold = v.gold + d end,
           d > 0 and green or red)
  end
  for i, s in ipairs({"STR", "AGI", "WIS"}) do
    label(s .. " " .. fmt(v[s]), P.stat[i], 130)
    button("down" .. s, "-", P.stat_btn[i][1], 160, 160, 130, function() v[s] = v[s] - 1 end, red)
    button("up" .. s, "+", P.stat_btn[i][2], 160, 160, 130, function() v[s] = v[s] + 1 end, green)
  end
end
