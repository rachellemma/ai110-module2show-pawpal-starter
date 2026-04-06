import datetime
from pawpal_system import Task, Pet, Owner, DailyScheduler


# --- Existing tests ---

def test_mark_complete_changes_status():
    task = Task("Morning walk", duration_minutes=30, priority="high")
    assert task.completed == False
    task.mark_complete()
    assert task.completed == True


def test_add_task_increases_pet_task_count():
    pet = Pet(name="Mochi", species="dog", age=3)
    assert len(pet.tasks) == 0
    pet.add_task(Task("Feed breakfast", duration_minutes=10, priority="high"))
    assert len(pet.tasks) == 1


# --- Helpers ---

def make_scheduler(*pets):
    """Build a DailyScheduler with a standard owner window (07:00–20:00)."""
    owner = Owner("Test Owner")
    for pet in pets:
        owner.add_pet(pet)
    return DailyScheduler(owner)


# ── 1. SORTING CORRECTNESS ────────────────────────────────────────────────────

def test_sort_high_before_medium_before_low():
    """High-priority tasks must come before medium, which come before low."""
    pet = Pet("Rex", "dog", 2)
    low    = Task("Bath time",     duration_minutes=20, priority="low")
    medium = Task("Afternoon fetch", duration_minutes=15, priority="medium")
    high   = Task("Insulin shot",  duration_minutes=5,  priority="high")
    pet.add_task(low)
    pet.add_task(medium)
    pet.add_task(high)

    scheduler = make_scheduler(pet)
    sorted_tasks = scheduler.sort_by_time([(pet, low), (pet, medium), (pet, high)])
    priorities = [t.priority for _, t in sorted_tasks]
    assert priorities == ["high", "medium", "low"]


def test_sort_within_same_priority_orders_by_time_slot():
    """Within the same priority, morning tasks come before afternoon, then evening, then any."""
    pet = Pet("Luna", "cat", 4)
    t_any       = Task("Play",       duration_minutes=10, priority="medium", preferred_time="any")
    t_evening   = Task("Cuddle",     duration_minutes=10, priority="medium", preferred_time="evening")
    t_morning   = Task("Breakfast",  duration_minutes=10, priority="medium", preferred_time="morning")
    t_afternoon = Task("Brushing",   duration_minutes=10, priority="medium", preferred_time="afternoon")

    scheduler = make_scheduler(pet)
    pairs = [(pet, t_any), (pet, t_evening), (pet, t_morning), (pet, t_afternoon)]
    sorted_tasks = scheduler.sort_by_time(pairs)
    slots = [t.preferred_time for _, t in sorted_tasks]
    assert slots == ["morning", "afternoon", "evening", "any"]


def test_sort_high_priority_any_before_medium_morning():
    """A high-priority 'any' task outranks a medium-priority 'morning' task."""
    pet = Pet("Buddy", "dog", 1)
    high_any    = Task("Meds",       duration_minutes=5,  priority="high",   preferred_time="any")
    med_morning = Task("Walk",       duration_minutes=30, priority="medium", preferred_time="morning")

    scheduler = make_scheduler(pet)
    sorted_tasks = scheduler.sort_by_time([(pet, med_morning), (pet, high_any)])
    assert sorted_tasks[0][1].description == "Meds"


def test_sort_empty_list_returns_empty():
    """Sorting an empty list should return an empty list without error."""
    pet = Pet("Ghost", "cat", 3)
    scheduler = make_scheduler(pet)
    assert scheduler.sort_by_time([]) == []


def test_sort_does_not_mutate_original_list():
    """sort_by_time must return a new list and leave the input unchanged."""
    pet = Pet("Max", "dog", 5)
    low  = Task("Bath",  duration_minutes=20, priority="low")
    high = Task("Meds",  duration_minutes=5,  priority="high")
    original = [(pet, low), (pet, high)]
    original_copy = list(original)

    scheduler = make_scheduler(pet)
    scheduler.sort_by_time(original)
    assert original == original_copy


# ── 2. RECURRENCE LOGIC ───────────────────────────────────────────────────────

def test_daily_task_creates_next_day_copy():
    """Completing a daily task adds a new task due tomorrow."""
    pet = Pet("Luna", "cat", 4)
    task = Task("Insulin shot", duration_minutes=5, priority="high", frequency="daily")
    pet.add_task(task)

    scheduler = make_scheduler(pet)
    scheduler.mark_completed("Insulin shot")

    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    new_tasks = [t for t in pet.tasks if not t.completed]
    assert len(new_tasks) == 1
    assert new_tasks[0].due_date == tomorrow


def test_weekly_task_creates_copy_seven_days_out():
    """Completing a weekly task adds a new task due 7 days from today."""
    pet = Pet("Mochi", "dog", 3)
    task = Task("Vet visit", duration_minutes=60, priority="medium", frequency="weekly")
    pet.add_task(task)

    scheduler = make_scheduler(pet)
    scheduler.mark_completed("Vet visit")

    next_week = datetime.date.today() + datetime.timedelta(days=7)
    new_tasks = [t for t in pet.tasks if not t.completed]
    assert len(new_tasks) == 1
    assert new_tasks[0].due_date == next_week


def test_as_needed_task_does_not_create_followup():
    """Completing an as-needed task must NOT add any follow-up task."""
    pet = Pet("Mochi", "dog", 3)
    task = Task("Trim nails", duration_minutes=15, priority="low", frequency="as-needed")
    pet.add_task(task)

    scheduler = make_scheduler(pet)
    scheduler.mark_completed("Trim nails")

    assert len(pet.tasks) == 1                      # original only
    assert pet.tasks[0].completed is True           # marked done
    assert len(pet.get_pending_tasks()) == 0        # nothing new queued


def test_recurring_task_inherits_original_fields():
    """The new recurring task carries over all fields from the original."""
    pet = Pet("Luna", "cat", 4)
    task = Task("Insulin shot", duration_minutes=5, priority="high",
                preferred_time="morning", frequency="daily")
    pet.add_task(task)

    scheduler = make_scheduler(pet)
    scheduler.mark_completed("Insulin shot")

    new_task = pet.get_pending_tasks()[0]
    assert new_task.description    == "Insulin shot"
    assert new_task.duration_minutes == 5
    assert new_task.priority       == "high"
    assert new_task.preferred_time == "morning"
    assert new_task.frequency      == "daily"


def test_mark_completed_only_affects_first_matching_incomplete_task():
    """If the same description appears twice, only the first incomplete one is completed."""
    pet = Pet("Buddy", "dog", 2)
    t1 = Task("Feed", duration_minutes=10, priority="high", frequency="daily")
    t2 = Task("Feed", duration_minutes=10, priority="high", frequency="daily")
    pet.add_task(t1)
    pet.add_task(t2)

    scheduler = make_scheduler(pet)
    scheduler.mark_completed("Feed")

    completed = [t for t in pet.tasks if t.completed]
    assert len(completed) == 1


# ── 3. CONFLICT DETECTION ─────────────────────────────────────────────────────

def test_no_conflicts_in_clean_schedule():
    """A schedule built by build_schedule() must never self-report conflicts."""
    pet = Pet("Mochi", "dog", 3)
    pet.add_task(Task("Walk",      duration_minutes=30, priority="high",   preferred_time="morning"))
    pet.add_task(Task("Breakfast", duration_minutes=10, priority="high",   preferred_time="morning"))
    pet.add_task(Task("Fetch",     duration_minutes=20, priority="medium", preferred_time="afternoon"))

    scheduler = make_scheduler(pet)
    assert scheduler.detect_conflicts() == []


def test_detect_exact_same_start_time_conflict():
    """Two tasks with the same start time must be flagged as a conflict."""
    overlapping = [
        {"pet": "Mochi", "task": "Walk",      "start": "07:00", "duration_minutes": 30,
         "priority": "high", "frequency": "daily", "reason": ""},
        {"pet": "Mochi", "task": "Breakfast", "start": "07:00", "duration_minutes": 10,
         "priority": "high", "frequency": "daily", "reason": ""},
    ]
    pet = Pet("Mochi", "dog", 3)
    scheduler = make_scheduler(pet)
    conflicts = scheduler.detect_conflicts(overlapping)
    assert len(conflicts) == 1
    assert "WARNING" in conflicts[0]


def test_detect_partial_overlap_conflict():
    """A task starting mid-way through another must be flagged."""
    overlapping = [
        {"pet": "Luna",  "task": "Nap",    "start": "07:00", "duration_minutes": 60,
         "priority": "low", "frequency": "daily", "reason": ""},
        {"pet": "Mochi", "task": "Walk",   "start": "07:30", "duration_minutes": 30,
         "priority": "high", "frequency": "daily", "reason": ""},
    ]
    pet = Pet("Mochi", "dog", 3)
    scheduler = make_scheduler(pet)
    conflicts = scheduler.detect_conflicts(overlapping)
    assert len(conflicts) == 1


def test_no_conflict_back_to_back_tasks():
    """Tasks that end exactly when the next begins must NOT be flagged."""
    back_to_back = [
        {"pet": "Mochi", "task": "Walk",      "start": "07:00", "duration_minutes": 30,
         "priority": "high", "frequency": "daily", "reason": ""},
        {"pet": "Mochi", "task": "Breakfast", "start": "07:30", "duration_minutes": 10,
         "priority": "high", "frequency": "daily", "reason": ""},
    ]
    pet = Pet("Mochi", "dog", 3)
    scheduler = make_scheduler(pet)
    assert scheduler.detect_conflicts(back_to_back) == []


def test_multiple_conflicts_detected():
    """Three mutually-overlapping tasks should produce three conflict warnings."""
    three_way = [
        {"pet": "A", "task": "Task1", "start": "08:00", "duration_minutes": 60,
         "priority": "high", "frequency": "daily", "reason": ""},
        {"pet": "B", "task": "Task2", "start": "08:15", "duration_minutes": 60,
         "priority": "high", "frequency": "daily", "reason": ""},
        {"pet": "C", "task": "Task3", "start": "08:30", "duration_minutes": 60,
         "priority": "high", "frequency": "daily", "reason": ""},
    ]
    pet = Pet("A", "dog", 1)
    scheduler = make_scheduler(pet)
    conflicts = scheduler.detect_conflicts(three_way)
    assert len(conflicts) == 3


# ── 4. EDGE CASES ─────────────────────────────────────────────────────────────

def test_pet_with_no_tasks_produces_empty_schedule():
    """An owner with a pet that has zero tasks yields an empty schedule."""
    pet = Pet("Ghost", "cat", 2)
    scheduler = make_scheduler(pet)
    assert scheduler.build_schedule() == []


def test_two_tasks_at_exact_same_time_only_one_scheduled():
    """build_schedule places tasks sequentially — identical-preference tasks cannot overlap."""
    pet = Pet("Mochi", "dog", 3)
    pet.add_task(Task("Walk",  duration_minutes=30, priority="high", preferred_time="morning"))
    pet.add_task(Task("Meds",  duration_minutes=5,  priority="high", preferred_time="morning"))

    scheduler = make_scheduler(pet)
    schedule = scheduler.build_schedule()
    # Both fit, but they must start at different times
    starts = [item["start"] for item in schedule]
    assert len(starts) == len(set(starts)), "Two tasks were assigned the exact same start time"


def test_max_tasks_per_day_cap_is_respected():
    """Scheduler must not schedule more tasks than owner.max_tasks_per_day."""
    pet = Pet("Busy", "dog", 1)
    for i in range(10):
        pet.add_task(Task(f"Task {i}", duration_minutes=5, priority="low"))

    owner = Owner("Test", max_tasks_per_day=3)
    owner.add_pet(pet)
    scheduler = DailyScheduler(owner)
    assert len(scheduler.build_schedule()) <= 3


def test_task_exceeding_window_is_dropped():
    """A single task too long to fit in the available window should not be scheduled."""
    pet = Pet("Mochi", "dog", 3)
    # 07:00–20:00 = 780 min window; task is 900 min
    pet.add_task(Task("Very long task", duration_minutes=900, priority="high"))

    scheduler = make_scheduler(pet)
    assert scheduler.build_schedule() == []


def test_owner_with_no_pets_produces_empty_schedule():
    """An owner with no pets should yield an empty schedule without error."""
    owner = Owner("Empty Owner")
    scheduler = DailyScheduler(owner)
    assert scheduler.build_schedule() == []
