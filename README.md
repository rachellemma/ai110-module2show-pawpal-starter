# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Smarter Scheduling

The scheduler has been extended with four algorithmic improvements beyond the original priority sort:

### Sort by time (`sort_by_time`)
Tasks are ordered by a two-key lambda: **priority first** (high → medium → low), then **time slot** (morning → afternoon → evening → any). This replaces the original single-key sort and ensures that two high-priority tasks are always sequenced by their preferred window rather than insertion order.

### Filter by pet and status (`filter_by_pet`, `filter_by_status`)
`filter_by_pet(name)` returns only pending tasks for one specific pet, useful for a per-pet view in the UI. `filter_by_status(completed)` walks every task on every pet regardless of pending status, making it easy to show a "done today" list alongside the remaining to-do items.

### Recurring task auto-scheduling (`mark_completed`)
When a `daily` or `weekly` task is marked complete, a new copy is automatically queued for the next occurrence using Python's `timedelta`:
- `daily` → due tomorrow (`today + timedelta(days=1)`)
- `weekly` → due in seven days (`today + timedelta(days=7)`)
- `as-needed` → no follow-up created

The new task is built with `dataclasses.replace()` so all original fields carry over unchanged.

### Conflict detection (`detect_conflicts`)
Accepts any list of schedule-item dicts and returns plain-text warning strings for overlapping time blocks. Uses `itertools.combinations` to check every unique pair with the standard interval-overlap condition (`A.start < B.end and B.start < A.end`). Returns an empty list (no crash) when the schedule is clean.

---

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
