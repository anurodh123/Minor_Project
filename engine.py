"""
engine.py — the page-replacement simulation core.

Pure Python, zero UI dependencies. This is the same logic that was
validated in the Flask backend, just detached from any web framework.
Both a terminal UI and (if ever wanted again) a web UI can sit on top
of this module unchanged.
"""
from __future__ import annotations

from typing import Callable, Optional
import random

MAX_REF_LENGTH = 500
MAX_FRAMES = 10
MAX_PAGE_VALUE = 999


# ======================================================================
# ALGORITHM REGISTRY
# Add a new algorithm by writing one _pick_xxx(frames, refs, i, ctx)
# function and adding one entry to ALGORITHMS. Nothing else changes.
# ======================================================================

def _pick_fifo(frames, refs, i, ctx):
    return min(range(len(frames)), key=lambda idx: frames[idx]["inserted_at"])


def _pick_lru(frames, refs, i, ctx):
    return min(range(len(frames)), key=lambda idx: frames[idx]["last_used"])


def _pick_opt(frames, refs, i, ctx):
    """Evict the page whose next use is farthest in the future (Belady's algorithm)."""
    victim, farthest = 0, -1
    for fi, f in enumerate(frames):
        page = f["page"]
        try:
            next_use = refs.index(page, i + 1)
        except ValueError:
            next_use = float("inf")
        if next_use > farthest:
            farthest, victim = next_use, fi
    return victim


def _pick_clock(frames, refs, i, ctx):
    """Second-chance: sweep a circular hand, clearing reference bits until a 0 is found."""
    n = len(frames)
    while frames[ctx["hand"]]["ref_bit"] == 1:
        frames[ctx["hand"]]["ref_bit"] = 0
        ctx["hand"] = (ctx["hand"] + 1) % n
    victim = ctx["hand"]
    ctx["hand"] = (ctx["hand"] + 1) % n
    return victim


def _pick_lfu(frames, refs, i, ctx):
    return min(range(len(frames)), key=lambda idx: (frames[idx]["freq"], frames[idx]["inserted_at"]))


def _pick_mfu(frames, refs, i, ctx):
    return max(range(len(frames)), key=lambda idx: (frames[idx]["freq"], -frames[idx]["inserted_at"]))


ALGORITHMS: dict[str, dict] = {
    "fifo": {
        "label": "FIFO",
        "name": "First-In, First-Out",
        "time": "O(1)",
        "space": "O(f)",
        "desc": (
            "FIFO replaces the page that entered memory first. The algorithm does not "
            "consider how often or how recently a page has been used. Instead, it simply "
            "removes the oldest page currently in memory.\n\n"
            "How it works:\n"
            "1. When a page is requested, check whether it is already in memory.\n"
            "2. If the page is present, it is a Page Hit and nothing is replaced.\n"
            "3. If the page is absent and there is an empty frame, place the page into that frame.\n"
            "4. If all frames are full, remove the page that has been in memory the longest.\n"
            "5. Insert the new page into the freed frame.\n\n"
            "FIFO is very simple and fast to implement using a queue, but it may remove "
            "important pages that are still being used because it only considers arrival time."
        ),
        "pick": _pick_fifo,
    },

    "lru": {
        "label": "LRU",
        "name": "Least Recently Used",
        "time": "O(1) amortized",
        "space": "O(f)",
        "desc": (
            "LRU replaces the page that has not been used for the longest period of time. "
            "It assumes that pages accessed recently are more likely to be used again soon "
            "(Temporal Locality).\n\n"
            "How it works:\n"
            "1. Check whether the requested page is already in memory.\n"
            "2. If it is present, record it as the most recently used page.\n"
            "3. If the page is absent and a free frame exists, load the page.\n"
            "4. If memory is full, identify the page whose last access occurred furthest in the past.\n"
            "5. Replace that page with the new page.\n\n"
            "LRU usually performs much better than FIFO because it keeps recently used pages "
            "in memory. However, it requires tracking when each page was last accessed."
        ),
        "pick": _pick_lru,
    },

    "opt": {
        "label": "OPT",
        "name": "Optimal (Belady's Algorithm)",
        "time": "O(f·n)",
        "space": "O(f)",
        "desc": (
            "The Optimal Page Replacement algorithm removes the page that will not be used "
            "again for the longest time in the future. Because it requires knowing future "
            "memory references, it cannot be used in real operating systems.\n\n"
            "How it works:\n"
            "1. Check whether the requested page already exists in memory.\n"
            "2. If it is a hit, continue to the next request.\n"
            "3. If there is an empty frame, place the page there.\n"
            "4. If memory is full, examine all pages currently in memory.\n"
            "5. Determine when each page will be used next in the future.\n"
            "6. Replace the page whose next use is farthest away or never occurs again.\n\n"
            "OPT produces the minimum possible number of page faults and is mainly used as "
            "a benchmark for comparing other algorithms."
        ),
        "pick": _pick_opt,
    },

    "clock": {
        "label": "CLOCK",
        "name": "Clock (Second Chance)",
        "time": "O(1) amortized",
        "space": "O(f)",
        "desc": (
            "Clock, also called the Second Chance algorithm, improves FIFO by giving recently "
            "used pages another chance before replacing them. Each page has a Reference Bit "
            "(0 or 1), and the frames are arranged in a circular structure.\n\n"
            "How it works:\n"
            "1. Every time a page is accessed, its Reference Bit is set to 1.\n"
            "2. When a replacement is needed, the clock hand moves through the frames.\n"
            "3. If a page's Reference Bit is 1, the bit is changed to 0 and the page is skipped.\n"
            "4. The hand continues moving until it finds a page whose Reference Bit is already 0.\n"
            "5. That page is replaced with the new page.\n\n"
            "Clock provides performance close to LRU while being much easier and more efficient "
            "to implement in operating systems."
        ),
        "pick": _pick_clock,
    },

    "lfu": {
        "label": "LFU",
        "name": "Least Frequently Used",
        "time": "O(f)",
        "space": "O(f)",
        "desc": (
            "LFU replaces the page that has been accessed the fewest number of times. "
            "It assumes that pages with very low usage are less likely to be needed again.\n\n"
            "How it works:\n"
            "1. Maintain a counter for every page in memory.\n"
            "2. Each time a page is accessed, increase its counter.\n"
            "3. If a page fault occurs and memory is full, compare the counters.\n"
            "4. Replace the page with the smallest access count.\n"
            "5. If multiple pages have the same count, replace the oldest one.\n\n"
            "LFU works well when frequently used pages continue to be important, but it may "
            "keep old pages that were heavily used in the past even if they are no longer needed."
        ),
        "pick": _pick_lfu,
    },

    "mfu": {
        "label": "MFU",
        "name": "Most Frequently Used",
        "time": "O(f)",
        "space": "O(f)",
        "desc": (
            "MFU replaces the page that has been accessed the most times. The idea is that "
            "a page with a very high access count may have completed its period of heavy use "
            "and is less likely to be needed immediately.\n\n"
            "How it works:\n"
            "1. Keep an access counter for every page in memory.\n"
            "2. Increase the counter whenever the page is referenced.\n"
            "3. When memory is full and a page fault occurs, compare all counters.\n"
            "4. Replace the page with the highest access count.\n"
            "5. If there is a tie, replace the oldest page among them.\n\n"
            "MFU is not commonly used in real operating systems because its assumption is "
            "often incorrect. However, it is valuable for learning and comparing page "
            "replacement strategies."
        ),
        "pick": _pick_mfu,
    },
}
ALGO_ORDER = ["fifo", "lru", "opt", "clock", "lfu", "mfu"]


# ======================================================================
# SIMULATION ENGINE
# ======================================================================

def simulate(algo_key: str, refs: list[int], frame_count: int) -> dict:
    if algo_key not in ALGORITHMS:
        raise ValidationError(f"Unknown algorithm '{algo_key}'. Choose one of {ALGO_ORDER}.")
    refs = validate_refs(refs)
    frame_count = validate_frames(frame_count)

    pick: Callable = ALGORITHMS[algo_key]["pick"]
    frames: list[Optional[dict]] = [None] * frame_count
    ctx = {"hand": 0}
    steps = []
    replacements = 0
    cum_hits = 0
    cum_faults = 0

    for i, page in enumerate(refs):
        idx_in_frames = next((idx for idx, f in enumerate(frames) if f and f["page"] == page), None)
        hit = idx_in_frames is not None
        victim_idx = -1
        evicted_page = None
        kind = "fill"

        if hit:
            frames[idx_in_frames]["last_used"] = i
            frames[idx_in_frames]["freq"] += 1
            if algo_key == "clock":
                frames[idx_in_frames]["ref_bit"] = 1
        else:
            empty_idx = next((idx for idx, f in enumerate(frames) if f is None), None)
            if empty_idx is not None:
                frames[empty_idx] = {
                    "page": page, "inserted_at": i, "last_used": i, "freq": 1,
                    "ref_bit": 1 if algo_key == "clock" else None,
                }
                victim_idx = empty_idx
            else:
                victim_idx = pick(frames, refs, i, ctx)
                evicted_page = frames[victim_idx]["page"]
                frames[victim_idx] = {
                    "page": page, "inserted_at": i, "last_used": i, "freq": 1,
                    "ref_bit": 1 if algo_key == "clock" else None,
                }
                kind = "evict"
                replacements += 1

        cum_hits += 1 if hit else 0
        cum_faults += 0 if hit else 1

        steps.append({
            "index": i,
            "page": page,
            "hit": hit,
            "fault": not hit,
            "frame_state": [
                {"page": f["page"], "ref_bit": f["ref_bit"]} if f else None for f in frames
            ],
            "victim_idx": victim_idx,
            "evicted_page": evicted_page,
            "kind": kind,
            "cum_hits": cum_hits,
            "cum_faults": cum_faults,
        })

    total = len(refs)
    return {
        "algorithm": algo_key,
        "steps": steps,
        "hits": cum_hits,
        "faults": cum_faults,
        "replacements": replacements,
        "hit_ratio": round(cum_hits / total, 4) if total else 0,
        "fault_ratio": round(cum_faults / total, 4) if total else 0,
    }


def compare_all(refs: list[int], frame_count: int) -> tuple[dict, str]:
    results = {k: simulate(k, refs, frame_count) for k in ALGO_ORDER}
    best = min(results, key=lambda k: results[k]["faults"])
    return results, best


# ======================================================================
# VALIDATION
# ======================================================================

class ValidationError(Exception):
    pass


def validate_refs(raw: list[int]) -> list[int]:
    if not isinstance(raw, list) or len(raw) == 0:
        raise ValidationError("Reference string must be a non-empty list of integers.")
    if len(raw) > MAX_REF_LENGTH:
        raise ValidationError(f"Reference string may contain at most {MAX_REF_LENGTH} entries.")
    refs = []
    for v in raw:
        if not isinstance(v, int) or isinstance(v, bool) or v < 0 or v > MAX_PAGE_VALUE:
            raise ValidationError(f"Invalid page number: {v!r}. Use integers 0-{MAX_PAGE_VALUE}.")
        refs.append(v)
    return refs


def parse_ref_string(text: str) -> list[int]:
    parts = [p.strip() for p in text.split(",") if p.strip() != ""]
    if not parts:
        raise ValidationError("Reference string cannot be empty.")
    nums = []
    for p in parts:
        if not p.lstrip("-").isdigit():
            raise ValidationError(f"'{p}' is not a valid integer.")
        nums.append(int(p))
    return validate_refs(nums)


def validate_frames(raw) -> int:
    try:
        raw = int(raw)
    except (TypeError, ValueError):
        raise ValidationError(f"Frame count must be an integer between 1 and {MAX_FRAMES}.")
    if raw < 1 or raw > MAX_FRAMES:
        raise ValidationError(f"Frame count must be between 1 and {MAX_FRAMES}.")
    return raw


def random_refs(length: int, max_page: int, seed: Optional[str] = None) -> list[int]:
    if not (1 <= length <= MAX_REF_LENGTH):
        raise ValidationError(f"Length must be between 1 and {MAX_REF_LENGTH}.")
    if not (0 <= max_page <= MAX_PAGE_VALUE):
        raise ValidationError(f"Max page must be between 0 and {MAX_PAGE_VALUE}.")
    rng = random.Random(seed) if seed else random.Random()
    return [rng.randint(0, max_page) for _ in range(length)]
