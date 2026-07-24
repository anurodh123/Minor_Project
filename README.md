# PAGEFRAME — Desktop App

A real desktop application: its own window, mouse-clickable buttons, menus,
and file dialogs. Built with **Tkinter**, Python's standard-library GUI
toolkit — no browser, no HTML/CSS/JS, no terminal keyboard tricks.

Same visual language as the earlier builds (amber = occupied/hit,
rust = fault/evicted, teal = active/current), now drawn with Tkinter
Canvas shapes instead of DOM elements or terminal boxes.

## Run it

```bash
python gui.py
```

**Linux only:** Tkinter is a separate OS package, not a pip package:
```bash
sudo apt-get install python3-tk
```
On macOS and Windows, Tkinter ships with the standard python.org installer,
so nothing extra to install — just run `python gui.py`.

## Files

```
pageframe_desktop/
├── engine.py    # pure Python simulation core — algorithms, validation, no UI code
└── gui.py       # Tkinter window: widgets, canvas drawing, event handlers
```

## What's in the window

- **Simulate tab** — reference string entry, frame count, algorithm dropdown,
  random generator (with optional seed), Import/Export buttons (native file
  dialogs), a canvas-drawn reference tape and memory frames with live
  hit/fault coloring, Play/Pause/Step/Restart buttons, a speed slider, a
  stats panel, and a hit-ratio trend sparkline.
- **Compare tab** — one button runs all six algorithms on the current input;
  results land in a sortable table plus a canvas bar chart, with the best
  performer starred and highlighted in amber.
- **Learn tab** — scrollable panel of core OS paging concepts and full
  per-algorithm descriptions with time/space complexity.

Keyboard shortcuts also work as a bonus on top of the mouse controls:
`space` play/pause, `←`/`→` step, `r` restart.

## Algorithms

FIFO, LRU, OPT (Belady's optimal), Clock (second chance), LFU, MFU. Add a
new one by writing a `_pick_xxx(frames, refs, i, ctx)` function in
`engine.py` and adding one entry to `ALGORITHMS` — the GUI (dropdown,
description panel, compare table/chart, learn tab) picks it up automatically
via `ALGO_ORDER`.

## Scope notes

Implemented: all 6 algorithms, step-by-step and auto-play simulation with
adjustable speed, random generation with optional seeding, JSON/CSV
import-export via native OS file dialogs, live stats with a trend chart,
synchronized comparison across all algorithms with a results table and bar
chart, and a scrollable learn tab.

Not implemented (would need infrastructure beyond a desktop script): user
accounts, cloud sync, and real-time multi-user collaboration.
