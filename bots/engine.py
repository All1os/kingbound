"""Kingbound rules engine with four bot players (rules: ../Kingbound-GDD.md).

The bots' decisions come from the balance simulator that set the GDD's numbers (sim.py, October
2026), ported here and extended so that a recorded game shows every mechanic: help deals (§6.6),
sabotage and interference (§6.7), Dig Deep (§6.2), hidden objectives (§9), Pickpocket and the
King's Trial (§8).

Game(seed).play() runs a whole game in memory and fills game.events, a list of small dicts such
as {"op": "roll", "color": "Red", "value": 4, "say": "Ann rolls 4"}. bots/play.py shows them in
Tabletop Simulator; bots/stats.py plays many games without TTS. The same seed always gives the
same game: every random choice goes through one random.Random(seed), and no decision iterates a
set or depends on hash order.
"""
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tts"))
import cards as C  # noqa: E402

# ------------------------------------------------------------------ static data (from cards.py)


def _action(cid, name, typ, cost, eff):
    a = dict(id=cid, name=name, typ=typ, cost=cost, dmg=0, block=0, fblock=0, heal=0, energy=0,
             r1=0, vanish=False, warcry=0)
    a.update(eff)
    return a


ACT = {c[0]: _action(c[0], c[1], c[2], c[3], c[6]) for c in C.ACTION}
ENEMY = {}
for _t, _lst in C.ENEMIES.items():
    for _cid, _name, _n, _hp, _atk, _gold, _loot, _text, _trait in _lst:
        ENEMY[_cid] = dict(id=_cid, tier=_t, name=_name, hp=_hp, atk=_atk, gold=_gold, loot=_loot, trait=_trait)
EVENT = {v[0]: dict(id=v[0], tier=v[1], name=v[2]) for v in C.EVENTS}
LOOT = {c[0]: dict(id=c[0], name=c[1], price=c[2], equip=c[5]) for c in C.LOOT}
CHAR = {ch[1]: dict(id=ch[0], STR=ch[2], AGI=ch[3], WIS=ch[4], hp=ch[5], energy=ch[6], hand=ch[7])
        for ch in C.CHARACTERS}
ABIL = {ch[1]: [a[2] for a in C.ABILITIES_OF[ch[1]]] for ch in C.CHARACTERS}   # boost, sabotage, signature
ABIL_ID = {a[2]: a[0] for a in C.ABILITIES}
OBJ_NAME = {o[0]: o[1] for o in C.OBJECTIVES}
# Every boost deals damage (sim v1: a defensive-only boost left the Knight and Cleric fleeing far
# more often), so a bot treats its boost as free damage.
DMG_ABILITY = {"Cleave": 3, "Backstab": 4, "Fireball": 5, "Volley": 3, "Holy Light": 4}
WEAPON_FOR = {"STR": "L01", "AGI": "L02", "WIS": "L03"}
STAT_MAX = 5
DIG_COST = 2        # Dig Deep: lose 2 HP to draw 1 Action card (§6.2 step 2)
FLEE_TARGET = 4     # flee on 4-6 (§6.4)
HELP_ENERGY = 2     # a helper gets 2 energy each round (§6.6)
READY_MARGIN = 1.0  # a bot fights a tier when its hand's damage >= 1.0 x that tier's average enemy HP
CASTLE = C.CASTLE
TIER_DECK = {1: "w1", 2: "w2", 3: "w3"}
ROMAN = {1: "I", 2: "II", 3: "III"}

# Bots sit clockwise from the bottom of the table, in the colours of the team's table sketch.
SEATS = [("Ann", "Red"), ("Ben", "Yellow"), ("Cleo", "Green"), ("Dan", "Blue")]
CAMP_OF = {"Red": (4, 3), "Yellow": (3, 2), "Green": (2, 3), "Blue": (3, 4)}


def guard_value(roll):
    """Guard roll (§6.2): 1-2 no change, 3-4 one less, 5-6 two less. Lucky Charm adds 1 to the roll."""
    return 0 if roll <= 2 else (1 if roll <= 4 else 2)


def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def subsets(hand):
    n = len(hand)
    for mask in range(1 << n):
        yield [hand[i] for i in range(n) if mask >> i & 1]


def plural(n, word):
    if word == "gold":
        return f"{n} gold"
    return f"{n} {word}{'' if n == 1 else 's'}"


def a_(name):
    return ("an " if name[0] in "AEIOU" else "a ") + name


# ------------------------------------------------------------------ decks


class Deck:
    def __init__(self, key, cards, rng):
        self.key = key
        self.pile = list(cards)
        rng.shuffle(self.pile)
        self.discard = []
        self.rng = rng

    def draw(self):
        """Returns (card, reshuffled). An empty deck reshuffles its discard pile first (§5.3)."""
        reshuffled = False
        if not self.pile:
            if not self.discard:
                return None, False
            self.pile, self.discard = self.discard, []
            self.rng.shuffle(self.pile)
            reshuffled = True
        return self.pile.pop(), reshuffled

    def take(self, card):
        """Removes a given card (for the mid-game demo start)."""
        if card in self.pile:
            self.pile.remove(card)
            return True
        return False


# ------------------------------------------------------------------ players


class Bot:
    def __init__(self, name, color, seat, char):
        spec = CHAR[char]
        self.name, self.color, self.seat, self.char = name, color, seat, char
        self.stats = {s: spec[s] for s in ("STR", "AGI", "WIS")}
        self.base_hp = spec["hp"]
        self.hp = spec["hp"]
        self.energy = spec["energy"]
        self.base_hand = spec["hand"]
        self.hand = []
        self.gold = 3
        self.level = 1
        self.equipment = []
        self.consumables = []
        self.ready = list(ABIL[char])
        self.pos = CAMP_OF[color]
        self.objective = None
        self.obj_done = False
        self.t2_kills = 0
        self.paid_helps = 0
        self.spoils = 0

    @property
    def label(self):
        return f"{self.name} ({self.char})"

    @property
    def main(self):
        return max(("STR", "AGI", "WIS"), key=lambda s: self.stats[s])

    @property
    def maxhp(self):
        return self.base_hp + (3 if "L06" in self.equipment else 0)

    @property
    def handsize(self):
        return self.base_hand + (1 if "L07" in self.equipment else 0)

    def item_dmg(self, typ):
        return 1 if WEAPON_FOR[typ] in self.equipment else 0

    def item_block(self):
        return (1 if "L04" in self.equipment else 0) + (2 if "L05" in self.equipment else 0)

    def luck(self):
        return 1 if "L08" in self.equipment else 0

    def boost(self):
        return ABIL[self.char][0]

    def sabotage(self):
        return ABIL[self.char][1]

    def sig(self):
        return ABIL[self.char][2]


# ------------------------------------------------------------------ fight arithmetic (from the sim)


def eval_cards(p, cards, enemy, rnd):
    """Damage, block, heal and net energy of playing `cards` this round, plus each damage card's
    share (for the captions). Under Armor the bot leads with its weakest damage card."""
    warcry = sum(ACT[c]["warcry"] for c in cards)
    per = []
    blk = heal = cost = 0
    for c in cards:
        a = ACT[c]
        cost += a["cost"] - a["energy"]
        stat = p.stats[a["typ"]]
        if a["dmg"]:
            d = a["dmg"] + stat + p.item_dmg(a["typ"])
            if rnd == 1:
                d += a["r1"]
            if a["typ"] == "STR":
                d += warcry
            if enemy["trait"] == "ethereal" and a["typ"] in ("STR", "AGI"):
                d -= 1
            per.append([c, max(0, d)])
        if a["block"]:
            blk += a["block"] + stat
        blk += a["fblock"]
        if a["heal"]:
            heal += a["heal"] + stat
    dmg = sum(x[1] for x in per)
    if enemy["trait"] == "armor" and per:
        weakest = min(per, key=lambda x: x[1])
        cut = min(2, weakest[1])
        weakest[1] -= cut
        dmg -= cut
    return dmg, blk, heal, cost, per


def hand_potential(p, enemy, hand=None):
    return sum(eval_cards(p, [c], enemy, 2)[0] for c in (p.hand if hand is None else hand))


def plan_round(p, enemy, remaining, rnd, atk_now, free_dmg, extra_energy, cap=None, budget=None):
    """Cards for this round: the smallest set that kills, else the best value. From the sim."""
    best_kill = best_other = None
    budget = (p.energy if budget is None else budget) + extra_energy
    for s in subsets(p.hand):
        if any(ACT[c]["vanish"] for c in s):
            continue
        dmg, blk, heal, cost, per = eval_cards(p, s, enemy, rnd)
        if cost > budget:
            continue
        dmg += free_dmg
        if cap is not None:
            dmg = min(dmg, cap)
        if dmg >= remaining:
            key = (len(s), cost, dmg)
            if best_kill is None or key < best_kill[0]:
                best_kill = (key, s, dmg, blk, heal, per)
            continue
        blk_total = blk + p.item_block()
        incoming = max(0, atk_now - blk_total - 1)  # expected Guard roll about 1
        eff_heal = min(heal, p.maxhp - p.hp)
        hp_after = p.hp + eff_heal - incoming
        score = dmg + 0.6 * min(blk_total, atk_now) + 0.6 * eff_heal - 0.25 * len(s)
        if hp_after <= 0:
            score -= 100
        if best_other is None or score > best_other[0]:
            best_other = (score, s, dmg, blk, heal, per, hp_after)
    if best_kill:
        _, s, dmg, blk, heal, per = best_kill
        return dict(cards=s, dmg=dmg, blk=blk, heal=heal, per=per, kills=True, hp_after=p.hp,
                    cost=eval_cards(p, s, enemy, rnd)[3])
    _, s, dmg, blk, heal, per, hp_after = best_other
    return dict(cards=s, dmg=dmg, blk=blk, heal=heal, per=per, kills=False, hp_after=hp_after,
                cost=eval_cards(p, s, enemy, rnd)[3])


def card_value(p, c):
    """How much a bot wants to keep a card when it RESTs (damage dealt, or a rough equivalent)."""
    a = ACT[c]
    stat = p.stats[a["typ"]]
    if a["dmg"]:
        return a["dmg"] + stat + p.item_dmg(a["typ"])
    if a["block"]:
        return 0.7 * (a["block"] + stat)
    if a["heal"]:
        return 0.7 * (a["heal"] + stat)
    if a["energy"]:
        return 2.5
    if a["warcry"]:
        return 3 if p.stats["STR"] >= 2 else 0
    if a["vanish"]:
        return 3
    return 0


EQUIP_VALUE = {"L04": 3, "L05": 4, "L06": 3, "L07": 3, "L08": 2, "L09": 1}


def equip_value(p, item):
    if item in WEAPON_FOR.values():
        return 5 if WEAPON_FOR[p.main] == item else 1
    return EQUIP_VALUE.get(item, 1)


# ------------------------------------------------------------------ the game


class Game:
    def __init__(self, seed, mode="full", max_rounds=60):
        self.seed = seed
        self.mode = mode
        self.rng = random.Random(seed)
        self.max_rounds = max_rounds
        self.board = C.make_board(self.rng)
        self.tier_at = {pos: int(k[-1]) for pos, k in self.board.items() if k.startswith("Wilds")}
        self.action = Deck("action", [c[0] for c in C.ACTION for _ in range(c[4])], self.rng)
        self.wilds = {t: Deck(TIER_DECK[t], [e[0] for e in C.ENEMIES[t] for _ in range(e[2])]
                              + [v[0] for v in C.EVENTS if v[1] == t], self.rng) for t in (1, 2, 3)}
        self.loot = Deck("loot", [c[0] for c in C.LOOT for _ in range(c[3])], self.rng)
        chars = [ch[1] for ch in C.CHARACTERS]
        self.rng.shuffle(chars)                       # §4 step 2: one character each, the fifth back in the box
        self.players = [Bot(n, col, i, chars[i]) for i, (n, col) in enumerate(SEATS)]
        objectives = [o[0] for o in C.OBJECTIVES]
        self.rng.shuffle(objectives)                  # §4 step 3
        for p, o in zip(self.players, objectives):
            p.objective = o
        self.round = 0
        self.winner = None
        self.events = []
        self.head = ""
        self.stats = dict(help_deals=0, sabotage=0, digs=0, objectives=0, trials=0, kos=0, fights=0,
                          rests=0, pickpocket=0, flee=0, events=0, merchant=0, barracks=0, healer=0)

    # ---------------------------------------------------------------- event helpers
    def ev(self, op, say=None, **kw):
        e = dict(op=op, **kw)
        if say:
            e["say"] = say
            e["head"] = self.head
        self.events.append(e)

    def say(self, text):
        self.ev("say", text)

    def sync(self, p, say=None):
        self.ev("player", say, color=p.color, hp=p.hp, max=p.maxhp, gold=p.gold, level=p.level,
                STR=p.stats["STR"], AGI=p.stats["AGI"], WIS=p.stats["WIS"], title=f"{p.name} · {p.char}",
                name=p.name, char=p.char)

    def roll(self, p, why, spot="fight"):
        v = self.rng.randint(1, 6)
        self.ev("roll", f"{p.name} rolls {v} ({why})", value=v, color=p.color, spot=spot)
        return v

    def clockwise_from(self, p):
        i = self.players.index(p)
        return [self.players[(i + k) % 4] for k in range(1, 4)]

    def leader(self):
        top = max(q.level for q in self.players)
        tops = [q for q in self.players if q.level == top]
        return tops[0] if len(tops) == 1 else None

    # ---------------------------------------------------------------- cards in and out
    def draw_cards(self, p, n, why=None):
        drawn, batch = [], []
        for _ in range(n):
            c, reshuffled = self.action.draw()
            if c is None:
                break
            if reshuffled:
                if batch:
                    self.ev("draw", color=p.color, cards=batch)
                    batch = []
                self.ev("reshuffle", "The Action deck is empty: its discard pile is shuffled into a new deck.", deck="action")
            batch.append(c)
            drawn.append(c)
            p.hand.append(c)
        if batch:
            self.ev("draw", why, color=p.color, cards=batch)
        return drawn

    def refill(self, p):
        return self.draw_cards(p, max(0, p.handsize - len(p.hand)))

    def use_ability(self, p, name, say):
        p.ready.remove(name)
        self.ev("ability", say, color=p.color, name=name, used=True)

    def draw_wilds(self, tier):
        card, reshuffled = self.wilds[tier].draw()
        if reshuffled:
            self.ev("reshuffle", f"The Wilds {ROMAN[tier]} deck is empty: its discard pile becomes the new deck.",
                    deck=TIER_DECK[tier])
        return card

    def draw_loot(self):
        card, reshuffled = self.loot.draw()
        if reshuffled:
            self.ev("reshuffle", "The Loot deck is empty: its discard pile becomes the new deck.", deck="loot")
        return card

    def gain_levels(self, p, n, why):
        before = p.level
        p.level = min(9, p.level + n)
        if p.level > before:
            extra = " (level 9 is the most you can reach before the Trial)" if before + n > 9 else ""
            self.sync(p, f"{p.name} {why}: level {before} → {p.level}{extra}")
            self.check_objective(p)

    def take_loot(self, p, item, source):
        """An item arrives (bought, dropped or found). Equipment over the limit of 3 replaces the
        weakest piece (§7); one-use Training Manual and Elixir are used at once by the bots."""
        name = LOOT[item]["name"]
        if LOOT[item]["equip"]:
            if len(p.equipment) >= C.EQUIPMENT_LIMIT:
                worst = min(p.equipment, key=lambda x: equip_value(p, x))
                if equip_value(p, item) <= equip_value(p, worst):
                    self.ev("loot", f"{p.name} {source} {a_(name)} but already carries 3 equipment items: it goes to the discard pile.",
                            color=p.color, id=item, slot="equip")
                    self.ev("item", color=p.color, id=item)
                    self.loot.discard.append(item)
                    return
                p.equipment.remove(worst)
                self.loot.discard.append(worst)
                self.ev("item", f"{p.name} drops the {LOOT[worst]['name']} to make room (3 equipment items at most).",
                        color=p.color, id=worst)
            p.equipment.append(item)
            if item == "L06":
                p.hp += 3
            self.ev("loot", f"{p.name} {source} the {name}: {C.LOOT_BY_NAME[name][4]}", color=p.color, id=item, slot="equip")
            self.sync(p)
            self.check_objective(p)
            return
        self.ev("loot", f"{p.name} {source} {a_(name)}.", color=p.color, id=item, slot="use")
        if item == "L10":   # Training Manual: raise a stat now
            s = p.main if p.stats[p.main] < STAT_MAX else min(p.stats, key=lambda k: -p.stats[k] if p.stats[k] < STAT_MAX else 99)
            if p.stats[s] < STAT_MAX:
                p.stats[s] += 1
            self.loot.discard.append(item)
            self.ev("item", f"{p.name} reads the Training Manual: {s} {p.stats[s] - 1} → {p.stats[s]}.", color=p.color, id=item)
            self.sync(p)
            self.check_objective(p)
        elif item == "L15":   # Elixir: refill the hand now
            self.loot.discard.append(item)
            self.ev("item", f"{p.name} drinks the Elixir and draws up to a full hand.", color=p.color, id=item)
            self.refill(p)
        else:
            p.consumables.append(item)

    def use_item(self, p, item, say, in_fight):
        p.consumables.remove(item)
        self.loot.discard.append(item)
        self.ev("item", say, color=p.color, id=item, to="fight" if in_fight else None)

    # ---------------------------------------------------------------- objectives (§9)
    def check_objective(self, p):
        if p.obj_done:
            return
        o = p.objective
        done = ((o == "O2" and p.t2_kills >= 3) or
                (o == "O3" and max(p.stats.values()) >= 5) or
                (o == "O4" and len(p.equipment) >= 3) or
                (o == "O5" and p.gold >= 10) or
                (o == "O6" and p.paid_helps >= 2) or
                (o == "O7" and p.spoils >= 2))
        if done:
            self.complete_objective(p)

    def complete_objective(self, p):
        p.obj_done = True
        self.stats["objectives"] += 1
        self.ev("objective", f"{p.name} reveals a hidden objective: {OBJ_NAME[p.objective]}! "
                             f"\"{C.OBJECTIVE_BY_ID[p.objective][2]}\"", color=p.color)
        self.gain_levels(p, 2, "completes the objective, +2 levels")

    # ---------------------------------------------------------------- help deals (§6.6)
    def helper_plan(self, h, enemy, rnd, need):
        """The helper's best play with 2 energy and its own stats; its boost only if it finishes."""
        best = None
        for s in subsets(h.hand):
            if any(ACT[c]["vanish"] or ACT[c]["heal"] for c in s):
                continue
            dmg, blk, heal, cost, per = eval_cards(h, s, enemy, rnd)
            if cost > HELP_ENERGY or (dmg == 0 and blk == 0):
                continue
            kills = dmg >= need
            key = (kills, -len(s) if kills else dmg, blk)
            if best is None or key > best[0]:
                best = (key, s, dmg, blk, per)
        plan = dict(cards=[], dmg=0, blk=0, per=[], boost=None)
        if best:
            _, plan["cards"], plan["dmg"], plan["blk"], plan["per"] = best
        b = h.boost()
        if plan["dmg"] < need and b in h.ready and plan["dmg"] + DMG_ABILITY[b] >= need:
            plan["boost"] = b
        return plan

    def help_offer_value(self, h, enemy):
        plan = self.helper_plan(h, enemy, 1, 999)
        return plan["dmg"] + (DMG_ABILITY[h.boost()] if h.boost() in h.ready else 0)

    def help_deal(self, p, enemy):
        need = enemy["hp"] + (4 if enemy["trait"] == "regen" else 0)
        own = hand_potential(p, enemy) + self.free_damage(p)
        if own >= need + 4 or enemy["tier"] == 1:
            return None, None
        gain = C.LEVELS_FOR_TIER[enemy["tier"]]
        lead = self.leader()
        offers = []
        for h in self.clockwise_from(p):
            if h.level >= 9:
                continue   # busy getting to the Castle
            value = self.help_offer_value(h, enemy)
            if value < 3:
                continue
            sellsword = h.objective == "O6" and not h.obj_done
            if lead is p and p.level + gain >= 8 and not sellsword:
                continue   # helping the leader now would sell them the win (§6.6)
            price = max(1, enemy["tier"] - (1 if sellsword else 0))
            if enemy["loot"] and len(h.equipment) < 3 and not sellsword and h.gold < 5:
                offers.append((h, "loot", value))
            else:
                offers.append((h, price, value))
        if not offers:
            self.say(f"{p.name} asks the table for help against the {enemy['name']}. Nobody offers.")
            return None, None
        texts = [f"{h.name} offers {h.boost()} and cards for {'the loot' if pr == 'loot' else plural(pr, 'gold')}"
                 for h, pr, v in offers]
        self.say(f"{p.name} asks for help against the {enemy['name']}. " + "; ".join(texts) + ".")
        usable = [o for o in offers if o[1] == "loot" or p.gold + enemy["gold"] >= o[1]]
        useful = [o for o in usable if own + o[2] >= need]
        pick = None
        if useful:
            pick = min(useful, key=lambda o: (0 if o[1] == "loot" else o[1], -o[2]))
        elif usable and own + max(o[2] for o in usable) >= need - 4:
            pick = max(usable, key=lambda o: o[2])
        if not pick:
            self.say(f"{p.name} turns the offers down.")
            return None, None
        h, price, _ = pick
        self.stats["help_deals"] += 1
        self.say(f"Deal: {h.name} helps {p.name} for {'the loot' if price == 'loot' else plural(price, 'gold')}, paid only if they win.")
        return h, price

    # ---------------------------------------------------------------- fights (§6)
    def free_damage(self, p):
        dmg = DMG_ABILITY[p.boost()] if p.boost() in p.ready else 0
        return dmg + 5 * p.consumables.count("L12")

    def show_play(self, who, plan, rnd, helper=False):
        if not plan["cards"]:
            return
        parts = []
        for c in plan["cards"]:
            d = next((x[1] for x in plan["per"] if x[0] == c), None)
            parts.append(f"{ACT[c]['name']} {d}" if d is not None else ACT[c]["name"])
        self.ev("play", f"{who.name} plays " + ", ".join(parts), color=who.color, cards=list(plan["cards"]), helper=helper)

    def fight(self, p, enemy, trial=False, pre_hit=False):
        """One fight, round by round as in §6.2. Returns 'win', 'flee' or 'ko'."""
        E = enemy
        self.stats["fights"] += 1
        damage = 0
        rnd = 0
        snared = False
        hp_low = p.hp
        spoilers = []
        helper, price = (None, None) if trial else self.help_deal(p, E)
        cap = C.CHAMPION["cap"] if trial else None
        if pre_hit:
            v = self.roll(p, "Guard roll")
            inc = max(0, E["atk"] - p.item_block() - guard_value(v + p.luck()))
            p.hp = max(0, p.hp - inc)
            hp_low = min(hp_low, p.hp)
            self.sync(p, f"The {E['name']} attacks before round 1: {inc} damage, {p.name} has {p.hp} HP.")
            if p.hp <= 0:
                return self.end_fight(p, E, "ko", helper, price, spoilers, hp_low, trial, damage)
        while True:
            rnd += 1
            if rnd > 25:
                snared = False   # safety net for a stalemate the rules don't cover; never seen in test games
            remaining = E["hp"] - damage
            atk_now = E["atk"] + (2 if E["trait"] == "charge" and rnd == 1 else 0)
            self.ev("fightround", f"Round {rnd} against the {E['name']}: {damage} of {E['hp']} damage so far.", round=rnd)
            # Prayer (Cleric signature, your fight): draw 2 when the hand is short.
            if p.sig() == "Prayer" and "Prayer" in p.ready and (len(p.hand) <= 3 or hand_potential(p, E) < remaining):
                self.use_ability(p, "Prayer", f"{p.name} uses Prayer: draws 2 Action cards.")
                self.draw_cards(p, 2)
            free = self.free_damage(p)
            surge = 2 if (p.sig() == "Arcane Surge" and "Arcane Surge" in p.ready) else 0
            help_pot = 0
            if helper:
                help_pot = self.helper_plan(helper, E, rnd, 999)["dmg"]
            potential = hand_potential(p, E) + free + help_pot - (2 if E["trait"] == "regen" else 0)

            def plans():
                need = remaining - help_pot
                a = plan_round(p, E, need, rnd, atk_now, 0, 0, cap) if p.hand else None
                b = None
                if (a is None or not a["kills"]) and (free or surge):
                    if p.hand:
                        b = plan_round(p, E, need, rnd, atk_now, free, surge, cap)
                    else:
                        b = dict(cards=[], dmg=min(free, cap or free), blk=0, heal=0, per=[], kills=free >= need,
                                 hp_after=p.hp - max(0, atk_now - p.item_block() - 1))
                use_b = bool(b and (b["kills"] or trial))
                return a, b, use_b, (b if use_b else a)

            plan_a, plan_b, use_b, plan = plans()
            # Dig Deep (§6.2 step 2): 2 HP per card, never down to 0. The bot digs only when one
            # more card could plausibly finish the enemy this round (sim policy, at most 3 a round).
            digs = 0
            while ((plan is None or not plan["kills"]) and digs < 3
                   and p.hp - DIG_COST > max(0, atk_now - p.item_block() - 1)
                   and potential + 6 >= remaining):
                c, reshuffled = self.action.draw()
                if c is None:
                    break
                if reshuffled:
                    self.ev("reshuffle", "The Action deck is empty: its discard pile is shuffled into a new deck.", deck="action")
                p.hp -= DIG_COST
                p.hand.append(c)
                digs += 1
                self.stats["digs"] += 1
                hp_low = min(hp_low, p.hp)
                self.ev("draw", f"{p.name} digs deep: loses 2 HP and draws {ACT[c]['name']}.", color=p.color, cards=[c])
                self.sync(p)
                potential = hand_potential(p, E) + free + help_pot - (2 if E["trait"] == "regen" else 0)
                plan_a, plan_b, use_b, plan = plans()
            # Step 1: FIGHT or FLEE.
            want_flee = False
            if not snared:
                if potential < remaining:
                    want_flee = True
                elif plan is None:
                    want_flee = True
                elif not plan["kills"] and plan["hp_after"] <= 0:
                    defensive = (p.sig() == "Shield Wall" and "Shield Wall" in p.ready) or "L11" in p.consumables
                    want_flee = not defensive
            if want_flee:
                vanish = next((c for c in p.hand if ACT[c]["vanish"]), None)
                if vanish:
                    p.hand.remove(vanish)
                    self.action.discard.append(vanish)
                    self.ev("play", f"{p.name} plays Vanish and slips away, no roll needed.", color=p.color, cards=[vanish])
                    return self.end_fight(p, E, "flee", helper, price, spoilers, hp_low, trial, damage)
                if "L13" in p.consumables:
                    self.use_item(p, "L13", f"{p.name} throws a Smoke Bomb and escapes.", True)
                    return self.end_fight(p, E, "flee", helper, price, spoilers, hp_low, trial, damage)
                self.say(f"{p.name} tries to flee: 4-6 escapes.")
                v = self.roll(p, "flee")
                if v + p.luck() >= FLEE_TARGET:
                    return self.end_fight(p, E, "flee", helper, price, spoilers, hp_low, trial, damage)
                g = self.roll(p, "Guard roll")
                inc = max(0, atk_now - p.item_block() - guard_value(g + p.luck()))
                p.hp = max(0, p.hp - inc)
                hp_low = min(hp_low, p.hp)
                self.sync(p, f"The escape fails. The {E['name']} hits for {inc}: {p.name} has {p.hp} HP.")
                if p.hp <= 0:
                    return self.end_fight(p, E, "ko", helper, price, spoilers, hp_low, trial, damage)
                if E["trait"] == "regen" and damage:
                    damage = max(0, damage - 2)
                    self.ev("damage", f"The Troll heals 2 damage.", total=damage)
                continue
            if plan is None:
                plan = dict(cards=[], dmg=0, blk=0, heal=0, per=[], kills=False, hp_after=p.hp)
            # Step 2: the fighter plays cards and Abilities.
            for c in plan["cards"]:
                p.hand.remove(c)
                self.action.discard.append(c)
            card_dmg = sum(x[1] for x in plan["per"])   # already after the Wraith / Armor cuts
            self.show_play(p, plan, rnd)
            dealt = card_dmg
            blk = plan["blk"]
            heal = plan["heal"]
            if use_b:
                need = remaining - help_pot - card_dmg
                b = p.boost()
                if b in p.ready and (need > 0 or trial):
                    extra = ""
                    if b == "Holy Light":
                        heal += 2
                        extra = " and heals 2 HP"
                    if b == "Volley":
                        blk += 2
                        extra = " and gains 2 Block"
                    self.use_ability(p, b, f"{p.name} uses {b}: {DMG_ABILITY[b]} damage{extra}.")
                    dealt += DMG_ABILITY[b]
                    need -= DMG_ABILITY[b]
                while need > 0 and "L12" in p.consumables:
                    self.use_item(p, "L12", f"{p.name} throws a Bomb: 5 damage.", True)
                    dealt += 5
                    need -= 5
                if surge and plan.get("cost", 0) > p.energy:
                    self.use_ability(p, "Arcane Surge", f"{p.name} uses Arcane Surge: +2 energy this round.")
            if heal:
                before = p.hp
                p.hp = min(p.maxhp, p.hp + heal)
                if p.hp > before:
                    self.sync(p, f"{p.name} heals {p.hp - before} HP.")
            if cap is not None:
                dealt = min(dealt, cap)
            round_dealt = dealt
            damage += dealt
            self.ev("damage", total=damage)
            # Shield Wall or a potion before the hit lands, if the hit would knock the fighter out.
            if damage < E["hp"]:
                expect = max(0, atk_now - blk - p.item_block() - 1)
                if expect >= p.hp and p.sig() == "Shield Wall" and "Shield Wall" in p.ready:
                    self.use_ability(p, "Shield Wall", f"{p.name} raises Shield Wall: +5 Block this round.")
                    blk += 5
                    expect = max(0, expect - 5)
                if expect >= p.hp and "L11" in p.consumables:
                    self.use_item(p, "L11", f"{p.name} drinks a Healing Potion: +5 HP.", True)
                    p.hp = min(p.maxhp, p.hp + 5)
                    self.sync(p)
            # Step 3: the helper plays (2 energy, own cards and stats, boost).
            hblk = 0
            if helper:
                need = E["hp"] - damage
                hp_plan = self.helper_plan(helper, E, rnd, need) if need > 0 else dict(cards=[], dmg=0, blk=0, per=[], boost=None)
                for c in hp_plan["cards"]:
                    helper.hand.remove(c)
                    self.action.discard.append(c)
                self.show_play(helper, hp_plan, rnd, helper=True)
                hd = hp_plan["dmg"]
                if hp_plan["boost"]:
                    b = hp_plan["boost"]
                    self.use_ability(helper, b, f"{helper.name} adds {b}: {DMG_ABILITY[b]} damage.")
                    hd += DMG_ABILITY[b]
                    if b == "Volley":
                        hblk += 2
                if cap is not None:
                    hd = min(hd, cap - round_dealt)
                hblk += hp_plan["blk"]
                round_dealt += hd
                damage += hd
                if hd or hblk:
                    self.ev("damage", total=damage)
            # Step 4: interference, clockwise from the fighter, once around.
            block_total = blk + p.item_block() + hblk
            provoke = 0
            for o in self.clockwise_from(p):
                if o is helper:
                    continue
                act = self.interfere(o, p, E, trial, damage, block_total, rnd, potential, remaining)
                if not act:
                    continue
                kind, say = act
                if o not in spoilers:
                    spoilers.append(o)
                self.stats["sabotage"] += 1
                if kind == "Hex":
                    damage = max(0, damage - 4)
                    self.use_ability(o, "Hex", say)
                    self.ev("damage", total=damage)
                elif kind == "Provoke":
                    provoke += 3
                    self.use_ability(o, "Provoke", say)
                elif kind == "Trip":
                    block_total = 0
                    self.use_ability(o, "Trip", say)
                elif kind == "Penance":
                    self.use_ability(o, "Penance", say)
                    p.hp = max(0, p.hp - 2)
                    hp_low = min(hp_low, p.hp)
                    self.sync(p)
                elif kind == "Snare":
                    snared = True
                    self.use_ability(o, "Snare", say)
                elif kind == "Totem":
                    provoke += 3
                    self.use_item(o, "L14", say, True)
            # Step 5: check.
            if damage >= E["hp"]:
                self.say(f"{damage} damage: the {E['name']} falls before it can attack.")
                return self.end_fight(p, E, "win", helper, price, spoilers, hp_low, trial, damage)
            # Step 6: the enemy attacks.
            g = self.roll(p, "Guard roll")
            gv = guard_value(g + p.luck())
            atk_total = atk_now + provoke
            inc = max(0, atk_total - block_total - gv)
            p.hp = max(0, p.hp - inc)
            hp_low = min(hp_low, p.hp)
            parts = [f"ATK {atk_now}"] + ([f"+{provoke}"] if provoke else []) + \
                    ([f"− {block_total} Block"] if block_total else []) + ([f"− {gv} Guard"] if gv else [])
            self.sync(p, f"The {E['name']} attacks: {' '.join(parts)} = {inc} damage. {p.name} has {p.hp} HP.")
            # Step 7: end of round.
            if p.hp <= 0:
                return self.end_fight(p, E, "ko", helper, price, spoilers, hp_low, trial, damage)
            if E["trait"] == "regen" and damage:
                damage = max(0, damage - 2)
                self.ev("damage", "End of the round: the Troll removes 2 damage.", total=damage)

    def interfere(self, o, p, E, trial, damage, block_total, rnd, potential, remaining):
        """A rival's step 4. Bots sabotage the Trial, a leader about to break away, or (with the
        Spoiler objective) any fight they can make the fighter lose. They keep their sabotage for
        the Trial when someone else is already at level 9 (§6.7)."""
        sab = o.sabotage()
        would_kill = damage >= E["hp"]
        gain = 0 if trial else C.LEVELS_FOR_TIER.get(E["tier"], 0)
        lead = self.leader()
        threat = trial or (p.level + gain >= 7 and (lead is p or p.level >= max(q.level for q in self.players)))
        spoiler = o.objective == "O7" and not o.obj_done
        if not trial and not spoiler and any(q.level >= 9 for q in self.players if q is not p and q is not o):
            threat = False
        if not (threat or spoiler):
            return None
        has_totem = "L14" in o.consumables
        if sab in o.ready:
            if sab == "Hex" and would_kill and damage - 4 < E["hp"]:
                return "Hex", f"{o.name} casts Hex on {p.name}'s fight: 4 damage comes off the {E['name']}."
            if sab == "Hex" and trial and damage > 0:
                return "Hex", f"{o.name} casts Hex: 4 damage comes off the Champion."
            if not would_kill:
                if sab == "Provoke":
                    return "Provoke", f"{o.name} uses Provoke: the {E['name']} deals 3 more damage this round."
                if sab == "Penance":
                    return "Penance", f"{o.name} uses Penance: {p.name} loses 2 HP."
                if sab == "Trip" and block_total >= 2:
                    return "Trip", f"{o.name} uses Trip: {p.name}'s {block_total} Block drops to 0."
                if sab == "Snare" and (trial and rnd == 1 or potential < remaining + 4):
                    return "Snare", f"{o.name} uses Snare: {p.name} can't flee for the rest of this fight."
        if has_totem and not would_kill and (trial or threat or spoiler):
            return "Totem", f"{o.name} raises a Cursed Totem: the {E['name']} deals 3 more damage this round."
        return None

    def end_fight(self, p, E, result, helper, price, spoilers, hp_low, trial, damage=0):
        if result == "win":
            if trial:
                p.level = 10
                self.winner = p
                self.sync(p)
                self.ev("clear")
                self.ev("win", f"{p.label} wins the King's Trial and reaches level 10. The king chooses {p.name}!", color=p.color)
                return result
            gain = C.LEVELS_FOR_TIER[E["tier"]]
            p.gold += E["gold"]
            before = p.level
            p.level = min(9, p.level + gain)
            capped = " (9 is the cap before the Trial)" if before + gain > 9 else ""
            self.sync(p, f"{p.label} fights {a_(E['name'])}: {damage} damage, wins, +{plural(gain, 'level')} "
                         f"(level {p.level}){capped}, +{E['gold']} gold.")
            if E["loot"]:
                item = self.draw_loot()
                if item:
                    if helper and price == "loot":
                        self.take_loot(helper, item, f"gets {p.name}'s loot as payment:")
                    else:
                        self.take_loot(p, item, "takes the loot:")
            if helper:
                if price != "loot":
                    pay = min(price, p.gold)
                    p.gold -= pay
                    helper.gold += pay
                    self.sync(p)
                    self.sync(helper, f"{p.name} pays {helper.name} {plural(pay, 'gold')} for the help.")
                helper.paid_helps += 1
                self.check_objective(helper)
            if E["tier"] == 2:
                p.t2_kills += 1
            if not p.obj_done and ((p.objective == "O1" and E["tier"] == 3) or (p.objective == "O8" and hp_low <= 3)):
                self.complete_objective(p)
            self.check_objective(p)
        elif result == "flee":
            self.stats["flee"] += 1
            lost = {"flee_gold1": 1, "flee_gold2": 2}.get(E["trait"], 0)
            if lost and p.gold:
                p.gold = max(0, p.gold - lost)
                self.sync(p, f"{p.label} fights {a_(E['name'])}: {damage} damage, flees and drops {plural(lost, 'gold')}.")
            else:
                self.say(f"{p.label} fights {a_(E['name'])}: {damage} damage, flees. No reward.")
            if helper:
                self.say(f"{helper.name} gets nothing: the fight was not won.")
        else:
            self.stats["kos"] += 1
            if helper:
                self.say(f"{helper.name} gets nothing: the fight was lost.")
        for o in spoilers:
            if result in ("flee", "ko") and o is not p:
                o.spoils += 1
                self.check_objective(o)
        self.ev("clear")
        if not trial:
            self.wilds[E["tier"]].discard.append(E["id"])
        if result == "ko":
            self.knock_out(p)
        return result

    def knock_out(self, p):
        """§6.5: lose 1 level, go to the nearest Camp, HP back to full, hand and Abilities stay."""
        before = p.level
        p.level = max(1, p.level - 1)
        camps = sorted(C.CAMPS, key=lambda c: (dist(c, p.pos), c != CAMP_OF[p.color]))
        p.pos = camps[0]
        p.hp = p.maxhp
        self.ev("move", color=p.color, path=[list(p.pos)])
        self.sync(p, f"{p.name} is knocked out: level {before} → {p.level}, back to the nearest Camp with full HP.")

    # ---------------------------------------------------------------- the board (§5)
    def readiness(self, p, tier):
        avg_hp = statistics.mean(e[3] for e in C.ENEMIES[tier])
        avg_atk = statistics.mean(e[4] for e in C.ENEMIES[tier])
        dummy = dict(trait=None, hp=avg_hp, atk=avg_atk)
        pot = (hand_potential(p, dummy) if p.hand else 0) + self.free_damage(p)
        safe = p.hp >= 2 * max(1, avg_atk - p.item_block() - 1)
        return pot >= READY_MARGIN * avg_hp and safe

    def best_tier(self, p):
        for t in (3, 2, 1):
            if self.readiness(p, t):
                return t
        return None

    def trial_ready(self, p):
        e = dict(trait="cap10", hp=C.CHAMPION["hp"], atk=C.CHAMPION["atk"])
        pot = (hand_potential(p, e) if p.hand else 0) + self.free_damage(p)
        return pot >= C.CHAMPION["hp"] + 4 and p.hp >= 0.7 * p.maxhp

    def weak_hand(self, p):
        return any(card_value(p, c) < 3 for c in p.hand) or len(p.hand) < p.handsize

    def rest(self, p):
        self.stats["rests"] += 1
        keep_min = 4.5 if p.level >= 9 else 3
        out = [c for c in p.hand if card_value(p, c) < keep_min]
        for c in out:
            p.hand.remove(c)
            self.action.discard.append(c)
        self.say(f"{p.label} RESTs" + (f", discards {', '.join(ACT[c]['name'] for c in out)}" if out else "") + ", draws up to a full hand and readies all Abilities.")
        if out:
            self.ev("discard", color=p.color, cards=out)
        self.refill(p)
        if len(p.ready) < 3:
            p.ready = list(ABIL[p.char])
            self.ev("ready", color=p.color)
        if self.board[p.pos] == "Camp" and p.hp < p.maxhp:
            p.hp = p.maxhp
            self.sync(p, f"{p.name} rests on a Camp: HP back to {p.hp}.")

    def path_to(self, a, b):
        """An L-shaped route, rows first; any tile and any pawn can be passed (§5.2)."""
        path, (r, c) = [], a
        while r != b[0]:
            r += 1 if b[0] > r else -1
            path.append([r, c])
        while c != b[1]:
            c += 1 if b[1] > c else -1
            path.append([r, c])
        return path

    def choose_dest(self, p, reach, goal):
        b = self.board
        legal = [x for x in reach if b[x] != "Castle" or p.level >= 9]
        sites = [x for x in legal if b[x] in ("Merchant", "Barracks", "Healer", "Camp")]
        if goal == "castle":
            if CASTLE in legal:
                return CASTLE
            if sites:
                return min(sites, key=lambda x: dist(x, CASTLE))
            ready = [x for x in legal if b[x].startswith("Wilds") and self.readiness(p, self.tier_at[x])]
            pool = ready or [x for x in legal if b[x].startswith("Wilds")] or legal
            return min(pool, key=lambda x: (dist(x, CASTLE), self.tier_at.get(x, 0)))
        if p.hp <= 0.45 * p.maxhp:
            heal = [x for x in legal if b[x] == "Healer"] if p.gold >= 2 else []
            if heal:
                return heal[0]
            camps = [x for x in legal if b[x] == "Camp"]
            if camps:
                return camps[0]
            if sites:
                return self.rng.choice(sites)
        hoard = p.objective == "O5" and not p.obj_done and p.gold >= 6
        nxt = p.stats[p.main] + 1
        if p.gold >= nxt and p.stats[p.main] < STAT_MAX and not hoard:
            bar = [x for x in legal if b[x] == "Barracks"]
            if bar:
                return bar[0]
        if p.gold >= 5 and len(p.equipment) < 3 and not hoard:
            mer = [x for x in legal if b[x] == "Merchant"]
            if mer:
                return mer[0]
        for tier in (3, 2, 1):
            if self.readiness(p, tier):
                tiles = [x for x in legal if b[x].startswith("Wilds") and self.tier_at[x] == tier]
                if tiles:
                    return self.rng.choice(tiles)
        if sites:
            return self.rng.choice(sites)
        wild = [x for x in legal if b[x].startswith("Wilds")]
        return min(wild, key=lambda x: self.tier_at[x]) if wild else legal[0]

    def merchant(self, p, where="the Merchant"):
        self.stats["merchant"] += 1
        offer = [c for c in (self.draw_loot() for _ in range(3)) if c]
        if not offer:
            return
        self.ev("offer", f"{p.name} visits {where}: " + ", ".join(f"{LOOT[c]['name']} ({LOOT[c]['price']})" for c in offer) + ".",
                cards=list(offer))
        prio = [WEAPON_FOR[p.main], "L10", "L04", "L05", "L07", "L06", "L11", "L12", "L08", "L14", "L13", "L09", "L15"]
        if p.objective == "O4" and not p.obj_done:
            prio = [WEAPON_FOR[p.main], "L04", "L05", "L07", "L06", "L08", "L09", "L10", "L11", "L12", "L14", "L13", "L15"]
        bought = None
        hoard = p.objective == "O5" and not p.obj_done
        for want in prio:
            if want in offer and LOOT[want]["price"] <= p.gold and not (hoard and p.gold - LOOT[want]["price"] < 6):
                if LOOT[want]["equip"] and (len(p.equipment) >= 3 or want in p.equipment):
                    continue
                bought = want
                break
        if bought:
            p.gold -= LOOT[bought]["price"]
            offer.remove(bought)
            self.ev("buy", f"{p.name} buys the {LOOT[bought]['name']} for {LOOT[bought]['price']} gold.",
                    color=p.color, id=bought, slot="equip" if LOOT[bought]["equip"] else "use")
            self.sync(p)
            self.give_bought(p, bought)
        else:
            self.say(f"{p.name} buys nothing.")
        for c in offer:
            self.loot.pile.insert(0, c)   # the others go to the bottom of the Loot deck (§5.3)
        self.ev("unoffer")

    def give_bought(self, p, item):
        """A bought item is already on the table in front of the player: just apply it."""
        if LOOT[item]["equip"]:
            p.equipment.append(item)
            if item == "L06":
                p.hp += 3
                self.sync(p)
            self.check_objective(p)
            return
        if item == "L10":
            s = p.main
            if p.stats[s] < STAT_MAX:
                p.stats[s] += 1
            self.loot.discard.append(item)
            self.ev("item", f"{p.name} reads the Training Manual: {s} {p.stats[s] - 1} → {p.stats[s]}.", color=p.color, id=item)
            self.sync(p)
            self.check_objective(p)
        elif item == "L15":
            self.loot.discard.append(item)
            self.ev("item", f"{p.name} drinks the Elixir and draws up to a full hand.", color=p.color, id=item)
            self.refill(p)
        else:
            p.consumables.append(item)

    def barracks(self, p):
        self.stats["barracks"] += 1
        bought = []
        changed = True
        while changed:
            changed = False
            for s in sorted(p.stats, key=lambda k: -p.stats[k]):
                nxt = p.stats[s] + 1
                if nxt <= STAT_MAX and p.gold >= nxt and (s == p.main or p.stats[p.main] >= 4):
                    p.gold -= nxt
                    p.stats[s] = nxt
                    bought.append(f"{s} {nxt - 1} → {nxt} for {nxt} gold")
                    changed = True
                    break
        if bought:
            self.sync(p, f"{p.name} trains at the Barracks: " + "; ".join(bought) + ".")
            self.check_objective(p)
        else:
            self.say(f"{p.name} can't pay for training here.")

    def healer(self, p):
        self.stats["healer"] += 1
        paid = 0
        while p.hp < p.maxhp and p.gold >= 1:
            p.gold -= 1
            p.hp = min(p.maxhp, p.hp + 3)
            paid += 1
        if paid:
            self.sync(p, f"{p.name} pays the Healer {plural(paid, 'gold')}: HP {p.hp}/{p.maxhp}.")
        else:
            self.say(f"{p.name} stops at the Healer but needs no healing.")

    def pickpocket(self, p):
        """Rogue signature (§10.5): on your turn, take 2 gold from a player on your tile or next to it."""
        if p.sig() != "Pickpocket" or "Pickpocket" not in p.ready:
            return
        marks = [q for q in self.players if q is not p and dist(q.pos, p.pos) <= 1 and q.gold > 0]
        if not marks:
            return
        q = max(marks, key=lambda x: (x.level, x.gold))
        n = min(2, q.gold)
        self.use_ability(p, "Pickpocket", f"{p.name} uses Pickpocket on {q.name}: takes {plural(n, 'gold')}.")
        q.gold -= n
        p.gold += n
        self.stats["pickpocket"] += 1
        self.sync(q)
        self.sync(p)
        self.check_objective(p)

    def resolve_wilds(self, p, tier, depth=0):
        card = self.draw_wilds(tier)
        if card is None:
            return
        if card in ENEMY:
            E = dict(ENEMY[card])
            loot = " · LOOT" if E["loot"] else ""
            self.ev("reveal", f"{p.name} draws {a_(E['name'])} (Tier {ROMAN[tier]}: HP {E['hp']}, ATK {E['atk']}, {E['gold']} gold{loot}).",
                    deck=TIER_DECK[tier], id=card)
            self.fight(p, E)
            return
        ev = EVENT[card]
        self.stats["events"] += 1
        text = C.EVENTS[[v[0] for v in C.EVENTS].index(card)][3]
        self.ev("reveal", f"{p.name} finds an event: {ev['name']}. {text}", deck=TIER_DECK[tier], id=card)
        self.wilds[tier].discard.append(card)
        name = ev["name"]
        if name == "Lost Purse":
            p.gold += 2
            self.sync(p, f"{p.name} gains 2 gold.")
            self.check_objective(p)
        elif name == "Old Veteran":
            if p.gold >= 2 and p.stats[p.main] < STAT_MAX and not (p.objective == "O5" and not p.obj_done):
                p.gold -= 2
                p.stats[p.main] += 1
                self.sync(p, f"{p.name} pays 2 gold: {p.main} {p.stats[p.main] - 1} → {p.stats[p.main]}.")
                self.check_objective(p)
            else:
                self.say(f"{p.name} passes.")
        elif name == "Pit Trap":
            v = self.roll(p, "Pit Trap")
            if v <= 3:
                p.hp = max(1, p.hp - 2)
                self.sync(p, f"{p.name} falls in: −2 HP, {p.hp} left.")
            else:
                self.say(f"{p.name} steps around the trap.")
        elif name == "Wandering Trader":
            self.ev("clear")
            self.merchant(p, "the Wandering Trader")
            return
        elif name == "Hidden Cache":
            item = self.draw_loot()
            if item:
                self.ev("clear")
                self.take_loot(p, item, "finds")
                return
        elif name == "Ambush!":
            self.ev("clear")
            nxt = self.draw_wilds(2)
            if nxt in ENEMY:
                E = dict(ENEMY[nxt])
                self.ev("reveal", f"Ambush! {a_(E['name'])[0].upper() + a_(E['name'])[1:]} jumps out (HP {E['hp']}, ATK {E['atk']}) and attacks first.",
                        deck="w2", id=nxt)
                self.fight(p, E, pre_hit=True)
            elif nxt:
                self.wilds[2].pile.append(nxt)    # put back: resolve it as a normal draw
                self.resolve_wilds(p, 2, depth + 1)
            return
        elif name == "Healing Spring":
            p.hp = p.maxhp
            self.sync(p, f"{p.name} heals to full: {p.hp} HP.")
        elif name == "Mercenary Captain":
            if p.gold >= 4 and p.level < 9:
                p.gold -= 4
                self.sync(p)
                self.gain_levels(p, 1, "pays the Mercenary Captain 4 gold, +1 level")
            else:
                self.say(f"{p.name} can't pay the Captain.")
        elif name == "Dragon Hoard":
            p.gold += 4
            self.sync(p, f"{p.name} takes 4 gold from the hoard, and something stirs...")
            self.check_objective(p)
            self.ev("clear")
            if depth < 2:
                self.resolve_wilds(p, tier, depth + 1)
            return
        elif name == "Ancient Shrine":
            if p.hp < p.maxhp * 0.5 or (len(p.ready) < 2 and p.stats[p.main] >= STAT_MAX):
                p.hp = p.maxhp
                p.ready = list(ABIL[p.char])
                self.ev("ready", color=p.color)
                self.sync(p, f"{p.name} prays at the shrine: full HP and all Abilities ready.")
            elif p.stats[p.main] < STAT_MAX:
                p.stats[p.main] += 1
                self.sync(p, f"{p.name} prays at the shrine: {p.main} {p.stats[p.main] - 1} → {p.stats[p.main]}.")
                self.check_objective(p)
        self.ev("clear")

    def trial(self, p):
        self.stats["trials"] += 1
        champ = dict(id="CH", tier=4, name="King's Champion", hp=C.CHAMPION["hp"], atk=C.CHAMPION["atk"],
                     gold=0, loot=False, trait="cap10")
        self.ev("reveal", f"{p.label} faces the King's Trial! The Champion: HP 20, ATK 5, takes at most 10 damage a round. "
                          f"Nobody may help; everyone else may interfere.", deck="champ", id="CH")
        return self.fight(p, champ, trial=True)

    def take_turn(self, p):
        self.head = f"Round {self.round} · {p.label} · level {p.level}"
        self.ev("turn", f"{p.label}'s turn: level {p.level}, {p.hp}/{p.maxhp} HP, {p.gold} gold.", color=p.color)
        if p.sig() == "Prayer" and "Prayer" in p.ready and len(p.hand) <= 2:
            self.use_ability(p, "Prayer", f"{p.name} uses Prayer: draws 2 Action cards.")
            self.draw_cards(p, 2)
        while p.hp <= p.maxhp * 0.4 and "L11" in p.consumables:
            self.use_item(p, "L11", f"{p.name} drinks a Healing Potion.", False)
            p.hp = min(p.maxhp, p.hp + 5)
            self.sync(p, f"{p.name} drinks a Healing Potion: {p.hp} HP.")
        self.pickpocket(p)
        b = self.board
        low_hp = p.hp <= 0.45 * p.maxhp
        if p.level >= 9:
            if b[p.pos] == "Castle":
                if self.trial_ready(p):
                    self.say(f"{p.name} starts the turn on the Castle and faces the Trial again.")
                    self.trial(p)
                    return
                if self.weak_hand(p) or len(p.ready) < 3 or p.hp < 0.7 * p.maxhp:
                    self.rest(p)
                    return
                goal = "improve"
            elif self.trial_ready(p):
                goal = "castle"
            elif self.weak_hand(p) and not low_hp:
                self.rest(p)
                return
            else:
                goal = "improve"
        else:
            threat = any(o is not p and o.level >= 9 for o in self.players)
            if threat and p.sabotage() not in p.ready and len(p.hand) < p.handsize:
                self.rest(p)
                return
            if (self.best_tier(p) is None or len(p.hand) <= 2) and not (low_hp and p.gold >= 2):
                self.rest(p)
                return
            goal = "normal"
        boots = 1 if "L09" in p.equipment else 0
        v = self.roll(p, "movement" + (", +1 Swift Boots" if boots else ""), spot="board")
        roll = v + boots
        if p.sig() == "Pathfinder" and "Pathfinder" in p.ready:
            want = roll <= 3 or (goal == "castle" and roll < dist(p.pos, CASTLE) <= roll + 3)
            if want:
                self.use_ability(p, "Pathfinder", f"{p.name} uses Pathfinder: {roll} + 3 = {roll + 3}.")
                roll += 3
        reach = [pos for pos in b if 1 <= dist(pos, p.pos) <= roll]
        dest = self.choose_dest(p, reach, goal)
        path = self.path_to(p.pos, dest)
        p.pos = dest
        kind = b[dest]
        nice = {"Wilds1": "Wilds I", "Wilds2": "Wilds II", "Wilds3": "Wilds III"}.get(kind, kind)
        where = "the Castle" if kind == "Castle" else f"{a_(nice)} tile"
        self.ev("move", f"{p.name} moves {plural(len(path), 'step')} to {where}.", color=p.color, path=path)
        self.pickpocket(p)
        if kind.startswith("Wilds"):
            self.resolve_wilds(p, self.tier_at[dest])
        elif kind == "Merchant":
            self.merchant(p)
        elif kind == "Barracks":
            self.barracks(p)
        elif kind == "Healer":
            self.healer(p)
        elif kind == "Castle":
            self.trial(p)
        elif kind == "Camp":
            self.say(f"{p.name} stops at a Camp.")

    # ---------------------------------------------------------------- setup and the main loop
    def setup_events(self):
        cells = [dict(r=r, c=c, key=f"{C.ring_of(r, c)}:{k}") for (r, c), k in sorted(self.board.items(),
                 key=lambda x: (C.ring_of(*x[0]), x[0]))]
        self.ev("board", "The board: Castle in the middle, Camps next to it; the middle and outer rings are shuffled.", cells=cells)
        players = []
        for p in self.players:
            players.append(dict(
                color=p.color, char_id=CHAR[p.char]["id"], objective=p.objective, title=f"{p.name} · {p.char}",
                abilities=[dict(id=ABIL_ID[a], name=a, used=a not in p.ready) for a in ABIL[p.char]],
                items=[dict(id=i, slot="equip") for i in p.equipment] + [dict(id=i, slot="use") for i in p.consumables],
                hand=list(p.hand), hp=p.hp, max=p.maxhp, gold=p.gold, level=p.level, pos=list(p.pos),
                STR=p.stats["STR"], AGI=p.stats["AGI"], WIS=p.stats["WIS"]))
        if self.mode == "demo":
            intro = ", ".join(f"{p.name} ({p.char}) level {p.level}" for p in self.players)
            text = f"Mid-game: {intro}. Their stats, items, gold and hands are on the table."
        else:
            intro = ", ".join(f"{p.name} is the {p.char}" for p in self.players)
            text = f"Four recruits: {intro}. Each gets 3 Abilities, a hidden objective and a hand of Action cards."
        self.ev("setup", text, players=players)
        for p in self.players:
            self.sync(p)

    def start_full(self):
        for p in self.players:
            self.draw_hand_silent(p)

    def draw_hand_silent(self, p):
        while len(p.hand) < p.handsize:
            c, _ = self.action.draw()
            p.hand.append(c)

    def start_demo(self):
        """Mid-game start for the short video: everyone at level 6-8 with the stats, items and gold a
        player at that level usually has (numbers from full bot games), pawns spread over the board."""
        levels = [8, 7, 7, 6]
        self.rng.shuffle(levels)
        spots = [pos for pos, k in self.board.items() if C.ring_of(*pos) >= 2]
        self.rng.shuffle(spots)
        for p, lv in zip(self.players, levels):
            p.level = lv
            p.stats[p.main] = min(STAT_MAX, p.stats[p.main] + self.rng.choice([1, 2]))
            weapon = WEAPON_FOR[p.main]
            gear = [weapon] + self.rng.sample(["L04", "L06", "L07", "L08"], 1)
            for g in gear:
                if self.loot.take(g):
                    p.equipment.append(g)
            for g in self.rng.sample(["L11", "L12", "L14"], 1):
                if self.loot.take(g):
                    p.consumables.append(g)
            p.gold = self.rng.randint(2, 6)
            p.hp = max(1, round(p.maxhp * self.rng.choice([0.6, 0.8, 1.0])))
            p.pos = spots.pop()
            p.t2_kills = self.rng.choice([1, 2])
            p.paid_helps = self.rng.choice([0, 1])
            p.spoils = self.rng.choice([0, 1])
            self.draw_hand_silent(p)
            if self.rng.random() < 0.4:
                p.ready.remove(p.sig())
        # Objectives that would already be complete at this point are counted as done earlier.
        for p in self.players:
            o = p.objective
            if (o == "O3" and max(p.stats.values()) >= 5) or (o == "O4" and len(p.equipment) >= 3) or (o == "O5" and p.gold >= 10):
                p.gold = min(p.gold, 7)
                if o == "O3":
                    p.stats[p.main] = 4

    def play(self):
        if self.mode == "demo":
            self.start_demo()
        else:
            self.start_full()
        self.head = "Kingbound"
        self.setup_events()
        order = list(range(4))
        start = self.rng.randrange(4)
        order = order[start:] + order[:start]
        first = self.players[order[0]]
        if self.mode == "demo":
            self.say(f"The first to win the King's Trial at the Castle is chosen. {first.name} plays next.")
        else:
            self.say(f"{first.name} goes first; play goes clockwise. First to level 9 may face the King's Trial at the Castle.")
        for rnd in range(1, self.max_rounds + 1):
            self.round = rnd
            for i in order:
                self.take_turn(self.players[i])
                if self.winner:
                    return self.winner
        self.say("The game reached the round limit without a winner.")
        return None
