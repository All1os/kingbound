"""Plays many bot games without Tabletop Simulator and prints what happened in them.

A sanity check for the bots and the numbers, not a balance proof: the bots follow simple greedy
rules (engine.py). Run: python3 bots/stats.py [games] [--demo]
"""
import statistics
import sys
from collections import Counter

from engine import Game

args = [a for a in sys.argv[1:] if not a.startswith("--")]
n = int(args[0]) if args else 500
mode = "demo" if "--demo" in sys.argv else "full"
rounds, wins, present, total = [], Counter(), Counter(), Counter()
unfinished = 0
for seed in range(1, n + 1):
    g = Game(seed, mode)
    w = g.play()
    present.update(p.char for p in g.players)
    total.update(g.stats)
    if w is None:
        unfinished += 1
        continue
    rounds.append(g.round)
    wins[w.char] += 1
q = statistics.quantiles(rounds, n=10)
print(f"{n} {mode} games, {unfinished} without a winner")
print(f"table rounds: median {statistics.median(rounds):.0f}, 10% of games by round {q[0]:.0f}, 90% by round {q[-1]:.0f}")
print("win rate when in the game (fair share 25%): " +
      ", ".join(f"{c} {100 * wins[c] / present[c]:.0f}%" for c in sorted(present)))
print("per game: " + ", ".join(f"{k.replace('_', ' ')} {v / n:.1f}" for k, v in total.items()))
