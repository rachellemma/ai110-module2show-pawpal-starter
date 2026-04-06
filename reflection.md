# PawPal+ Project Reflection

---

## 1. System Design

**a. Initial design**

My initial UML had four classes: `PetTask`, `Pet`, `Owner`, and `DailyScheduler`. The core idea was right — an owner has a pet, and a scheduler uses an owner plus a list of tasks to build a plan. But the design was too flat. Tasks were a free-floating list on the scheduler rather than belonging to individual pets, the `Owner` could only hold one pet, and `PetTask` had no sense of state (no `completed` flag, no `frequency`). The scheduler itself only had `build_schedule()` and `explain_plan()` — no filtering, no recurrence, no conflict detection.

**b. Design changes**

The biggest structural change was moving task ownership from the scheduler to `Pet`. In the initial design, `DailyScheduler` held `List~PetTask~ tasks` directly. During implementation it became clear that a task without an owner is ambiguous — you can't explain *why* a task is scheduled, generate a per-pet view, or handle recurrence correctly without knowing which animal the task belongs to. The fix was giving `Pet` a `tasks: list[Task]` field and a `get_pending_tasks()` method, and having the scheduler ask `Owner.get_all_tasks()` for `(Pet, Task)` pairs instead.

Three other changes followed from that:

- `Owner` became a one-to-many relationship with `Pet` (the original had a single `pet` attribute).
- `Task` (renamed from `PetTask`) gained `frequency`, `completed`, `due_date`, `mark_complete()`, and `reset()` — turning it from a passive data bag into a proper stateful object.
- `DailyScheduler` gained `sort_by_time()`, `filter_by_pet()`, `filter_by_status()`, `mark_completed()`, `detect_conflicts()`, and `reset_all()` — methods that only make sense once tasks are tied to pets and carry state.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers four constraints in order:

1. **Priority** (`high → medium → low`) — the most important constraint. A pet's medication always runs before a grooming session, regardless of time preference.
2. **Preferred time slot** (`morning → afternoon → evening → any`) — the secondary sort key within a priority tier. If two high-priority tasks exist, the one preferred in the morning schedules first.
3. **Owner time window** (`available_start` to `available_end`) — any task that would push past the window end is dropped rather than placed partially.
4. **Daily cap** (`max_tasks_per_day`) — the sorted list is sliced before placement so the plan stays realistic.

Priority was chosen as the top constraint because the consequences of missing a low-priority task (a play session) are trivially lower than missing a high-priority one (insulin). Time slot is second because it represents the pet's biological rhythm — a preference, not a hard rule.

**b. Tradeoffs**

The most significant tradeoff is **greedy sequential placement instead of backtracking search**.

`build_schedule()` advances a single `current_minutes` clock forward after every task. If a task prefers the afternoon and the clock is only at 08:00, the clock jumps to 12:00 — but it never goes backward. This means a long low-priority morning task can push a short high-priority afternoon task into a later-than-ideal slot, and tasks that don't fit at the end of the day are silently dropped rather than rescheduled.

A backtracking or bin-packing algorithm could produce a denser, more optimal schedule, but it would be harder to explain to a non-technical pet owner ("why did my dog's walk move?") and would add complexity that doesn't meaningfully improve real-world outcomes for a single owner managing one or two pets over a 13-hour window.

The greedy approach is transparent, predictable, and runs in O(n log n) time. Dropped tasks are a known limitation documented in the README rather than a hidden failure.

---

## 3. AI Collaboration

**a. How you used AI**

AI tools were used across all four phases of the project, but in different roles at each stage.

- **Design phase** — Copilot Chat (`#codebase`) was used to audit whether the initial UML actually matched the implemented code. The prompt "Based on my final implementation, what updates should I make to my initial UML diagram?" surfaced every divergence in one pass, much faster than manually diffing a diagram against 294 lines of code.
- **Test planning** — Chat was used to generate the initial edge-case list ("What are the most important edge cases to test for a pet scheduler with sorting and recurring tasks?"). This gave a structured starting point rather than an empty file, and several cases I hadn't considered (back-to-back tasks that touch but don't overlap, three-way mutual conflicts) came from that conversation.
- **Debugging** — The infinite loop in `mark_completed` was caught by the test suite, not AI. But once the traceback was in scope, AI helped confirm the root cause quickly: iterating over a list while appending to it during the same loop.
- **Documentation** — Copilot was used to draft the Features section of the README by asking it to describe each algorithm accurately based on the codebase. The output required editing for tone and precision, but the structure was correct on the first pass.

The most effective feature overall was **Copilot Chat with `#file:` or `#codebase` context**. Asking questions grounded in the actual source code produced answers that were specific and actionable rather than generic. Autocomplete was useful for boilerplate (dataclass fields, pytest assertion patterns) but required more review for logic-heavy methods.

**b. Judgment and verification**

During test generation, Copilot suggested a test for `detect_conflicts()` that injected a schedule with three tasks and asserted `len(conflicts) >= 1`. That assertion is too weak — it passes even if the method only catches one of the three overlapping pairs. The test was modified to assert `len(conflicts) == 3`, which is the correct number for three mutually-overlapping tasks (`combinations(3, 2) = 3` unique pairs).

The AI's version would have passed and given false confidence. Catching it required understanding the interval-overlap algorithm well enough to calculate the expected output by hand before writing the assertion. The lesson: AI-generated tests need the same code review as AI-generated application code — the assertion is where the specification lives, and a weak assertion is a bug in the test.

**c. Separate chat sessions for different phases**

Using separate chat sessions for design, implementation, testing, and documentation kept each conversation focused. When working on tests, the context window only held `pawpal_system.py` and the test file — there was no noise from earlier conversations about UI layout or UML syntax. This made Copilot's suggestions more relevant and made it easier to evaluate them: if a suggestion referenced something outside the current phase's scope, that was a signal it wasn't grounded in the right context.

It also created natural checkpoints. Finishing a phase and opening a new session forced a brief review of what was actually done before moving forward, which caught two inconsistencies between the reflection notes and the final code before they became permanent record.

**d. Being the lead architect**

The most important thing AI tools cannot do is decide what the system should *mean*. Copilot can generate a `mark_completed` method that technically works, but it cannot decide whether "completing" a task should silently queue a new one, require explicit opt-in, or notify the owner. Those are design decisions that carry consequences downstream — for the test suite, the UI, and the user's mental model of the app.

Working with AI effectively meant staying clear on which decisions were mine and which were suggestions to evaluate. Every time Copilot generated code, the question wasn't "does this run?" but "does this match the contract I intended?" The infinite loop bug is a good example: the code ran (for small inputs), but it violated the docstring's own "first incomplete task" contract. The AI didn't flag that inconsistency — reading the spec carefully did.

The practical habit that made this work: write the docstring or the test assertion first, then evaluate the implementation against it. AI is a fast generator of plausible implementations; the architect's job is to hold the specification.

---

## 4. Testing and Verification

**a. What you tested**

The 22-test suite covers four areas:

- **Sorting** — verifies the two-key sort produces the correct order across all priority and time-slot combinations, handles empty input, and does not mutate the original list.
- **Recurrence** — verifies that `daily`, `weekly`, and `as-needed` tasks behave correctly after completion, that all original fields carry over to the new task, and that only the first matching incomplete task is affected.
- **Conflict detection** — verifies true positives (same-start, partial overlap, three-way overlap), true negatives (back-to-back tasks, clean generated schedule), and correct warning count.
- **Edge cases** — verifies graceful handling of no tasks, time window overflow, and the daily cap.

These were prioritized because they cover the three behaviors most likely to produce silent wrong answers: an incorrect sort order produces a valid-looking but wrong schedule; a missed recurrence loses a task permanently; an undetected conflict produces a schedule the owner physically cannot execute.

**b. Confidence**

**★★★★☆ (4/5)**

All 22 tests pass. The scheduling contract is well-specified and the tests cover both happy paths and the key edge cases. The missing star reflects two gaps: the Streamlit UI has no automated tests (form input validation, session state behavior), and time arithmetic (`_to_minutes`, `_to_time_str`) is tested only indirectly through `detect_conflicts` and `build_schedule` rather than with dedicated unit tests.

If given more time, the next tests would be:
- Malformed time strings passed to `_to_minutes` (e.g. `"7:5"`, `"25:00"`)
- An owner whose `available_start` equals `available_end` (zero-length window)
- Two pets with tasks of identical descriptions to verify recurrence targets the right pet

---

## 5. Reflection

**a. What went well**

The decision to move task ownership to `Pet` early — even though it wasn't in the initial UML — paid off throughout the rest of the project. Every subsequent feature (recurrence, per-pet filtering, schedule reasoning) was simpler to implement because tasks had a clear owner. A design decision made in week one removed complexity in weeks two and three.

**b. What you would improve**

The scheduler silently drops tasks that don't fit in the time window. A pet owner has no way to know a task was skipped unless they count the output rows. The next iteration would collect dropped tasks and surface them as a "tasks that couldn't fit today" list in the UI — same visual style as the conflict warnings, but advisory rather than alarming.

**c. Key takeaway**

AI tools are most valuable when you already know what you're building. A vague prompt produces a plausible but directionless output. A prompt grounded in a specific contract ("this method should find the first incomplete task, mark it done, and queue a copy with the next due date") produces something you can actually evaluate. The quality of AI output is largely a function of the quality of the specification you bring to it — which means the architect's job isn't replaced, it's made more important.
