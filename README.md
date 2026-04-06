# PawPal+ — Pet Care Scheduling Assistant

PawPal+ is a Streamlit app that helps busy pet owners stay consistent with daily pet care. It takes your pets, their tasks, and your available hours and produces a conflict-free daily schedule — with explanations for every decision it makes.

---

## Features

### Priority-first scheduling
Every task is tagged `high`, `medium`, or `low`. The scheduler always places high-priority tasks (medications, feeding) before medium, and medium before low — so the most critical care never gets bumped by a lower-stakes activity.

### Sorting by time slot
Within the same priority level, tasks are further ordered by preferred time of day: **morning → afternoon → evening → any**. A two-key sort (`priority, preferred_time`) runs in O(n log n) and produces a stable, predictable sequence regardless of the order tasks were added.

### Time-window placement
Each owner sets a daily availability window (default 07:00–20:00). The scheduler walks the sorted task list sequentially, advancing a clock forward after each placement. If a task prefers the afternoon, the clock jumps to 12:00 before placing it — so tasks genuinely land in the windows you expect, not just any free slot.

### Daily recurrence
Mark a task complete and PawPal+ automatically queues the next occurrence:
- `daily` → new copy due tomorrow
- `weekly` → new copy due in 7 days
- `as-needed` → no follow-up created

All fields (duration, priority, preferred time, special-needs notes) carry over unchanged via `dataclasses.replace()`.

### Conflict detection
After a schedule is built, every pair of time blocks is checked with the standard interval-overlap condition (`A.start < B.end and B.start < A.end`). If any overlap is found, the UI surfaces a clear warning banner — above the schedule table, not buried below it — with a plain-English description of which two tasks clash and when.

### Per-pet and per-status filtering
- `filter_by_pet(name)` — isolates all pending tasks for one specific pet, useful for a quick per-pet view.
- `filter_by_status(completed)` — surfaces either the "done today" list or the remaining to-do list across all pets.
- `filter_by_priority(level)` — returns only scheduled items at a given priority level.

### Schedule reasoning
Every item in the generated plan includes a plain-English explanation: why it was placed at that time, what its priority is, and whether the pet has any special needs that influenced the decision.

### Daily cap
Each owner has a configurable `max_tasks_per_day` limit (default 8). The scheduler caps the sorted task list before placement, ensuring the plan stays realistic even when the task backlog is long.

---

## Project structure

```
pawpal_system.py   — Core data model and scheduling logic
app.py             — Streamlit UI
main.py            — Demo/test harness (run standalone)
tests/
  test_pawpal.py   — 22 unit tests
requirements.txt   — streamlit, pytest
```

---

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run the app

```bash
streamlit run app.py
```

### Run the tests

```bash
python -m pytest tests/test_pawpal.py -v
```

---

## Testing

| Area | Tests | What is verified |
|------|-------|-----------------|
| **Sorting correctness** | 5 | Priority order (high → medium → low); time-slot order within same priority; empty list handled; original list not mutated |
| **Recurrence logic** | 5 | Daily → tomorrow; weekly → 7 days; as-needed → no follow-up; all fields inherit; only first matching incomplete task is completed |
| **Conflict detection** | 5 | No false positives on clean schedule; same-start flagged; partial overlap flagged; back-to-back (touching) passes; three-way overlap produces three warnings |
| **Edge cases** | 4 | Pet with no tasks → empty schedule; two same-preference tasks get distinct starts; `max_tasks_per_day` cap respected; task too long for window is dropped |

**Total: 22 tests** — all passing.

**Confidence: ★★★★☆ (4/5)** — core scheduling logic is fully covered. One star withheld: the Streamlit UI layer has no automated tests and boundary validation (malformed time strings, empty form fields) is not yet enforced.

### Bug found during testing

Writing the recurrence tests surfaced an infinite loop in `mark_completed`: the method iterated over `pet.tasks` while appending to it, causing the newly-queued task to be immediately re-processed. Fixed by iterating over `list(pet.tasks)` (a snapshot) and returning after the first match.

---

## Design notes

**Greedy placement over optimal packing** — `build_schedule()` advances a single clock forward after each task, guaranteeing no overlaps in O(n log n) time. The tradeoff: lower-priority tasks at the end of a full day may be silently dropped. This is intentional — a predictable, explainable plan is more useful to a pet owner than a theoretically optimal one that's hard to reason about.

**Tasks belong to pets, not the scheduler** — each `Pet` owns its `tasks` list. The scheduler asks `Owner.get_all_tasks()` for `(Pet, Task)` pairs, which gives every scheduled item a clear owner. This makes filtering, recurrence, and reasoning strings straightforward without any global task registry.
