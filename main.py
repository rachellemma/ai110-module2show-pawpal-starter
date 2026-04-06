import datetime
from pawpal_system import Task, Pet, Owner, DailyScheduler

# --- Create Pets ---
mochi = Pet(name="Mochi", species="dog", age=3)
luna = Pet(name="Luna", species="cat", age=5, special_needs=["diabetic"])

# --- Add Tasks OUT OF ORDER (low -> medium -> high, mixed time slots) ---
mochi.add_task(Task("Play fetch",      duration_minutes=20, priority="low",    preferred_time="afternoon"))
mochi.add_task(Task("Evening stroll",  duration_minutes=25, priority="medium", preferred_time="evening"))
mochi.add_task(Task("Morning walk",    duration_minutes=30, priority="high",   preferred_time="morning"))
mochi.add_task(Task("Feed breakfast",  duration_minutes=10, priority="high",   preferred_time="morning"))

luna.add_task(Task("Brush fur",        duration_minutes=15, priority="medium", preferred_time="evening"))
luna.add_task(Task("Clean litter box", duration_minutes=10, priority="medium", preferred_time="any",     frequency="as-needed"))
luna.add_task(Task("Insulin shot",     duration_minutes=5,  priority="high",   preferred_time="morning", frequency="daily"))

# --- Create Owner and Scheduler ---
owner = Owner(name="Jordan", available_start="07:00", available_end="20:00", max_tasks_per_day=8)
owner.add_pet(mochi)
owner.add_pet(luna)
scheduler = DailyScheduler(owner)

# ── 1. Full schedule ─────────────────────────────────────────────────────────
print("=" * 55)
print("           TODAY'S SCHEDULE (sorted by time)")
print("=" * 55)
print(scheduler.explain_plan())

# ── 2. CONFLICT DETECTION ────────────────────────────────────────────────────
# The scheduler sequences tasks linearly (no built-in overlaps), so we build a
# manual schedule that forces two tasks to start at the same time to prove that
# detect_conflicts() catches the overlap and returns a warning string.
print("\n" + "=" * 55)
print("  CONFLICT DETECTION — forced overlap test")
print("=" * 55)

conflicting_schedule = [
    {
        "pet": "Mochi",
        "task": "Morning walk",
        "start": "07:00",
        "duration_minutes": 30,
        "priority": "high",
        "frequency": "daily",
        "reason": "",
    },
    {
        # Starts at 07:00, overlaps with Morning walk (07:00-07:30)
        "pet": "Luna",
        "task": "Insulin shot",
        "start": "07:00",
        "duration_minutes": 5,
        "priority": "high",
        "frequency": "daily",
        "reason": "",
    },
    {
        # Starts at 07:15, still inside Morning walk window -> another overlap
        "pet": "Luna",
        "task": "Morning meds check",
        "start": "07:15",
        "duration_minutes": 20,
        "priority": "high",
        "frequency": "daily",
        "reason": "",
    },
    {
        # Starts at 07:35, after Morning walk ends -> no conflict
        "pet": "Mochi",
        "task": "Feed breakfast",
        "start": "07:35",
        "duration_minutes": 10,
        "priority": "high",
        "frequency": "daily",
        "reason": "",
    },
]

conflicts = scheduler.detect_conflicts(conflicting_schedule)
if conflicts:
    for warning in conflicts:
        print(f"  {warning}")
else:
    print("  No conflicts found.")

print(f"\n  Real schedule (sequential) has conflicts: {bool(scheduler.detect_conflicts())}")

# ── 3. Recurrence: complete a daily task, verify next instance created ───────
print("\n" + "=" * 55)
print("  Completing 'Insulin shot' (daily) -> next due tomorrow")
print("=" * 55)
scheduler.mark_completed("Insulin shot")
today = datetime.date.today()
for pet in owner.pets:
    for task in pet.tasks:
        if task.description == "Insulin shot" and not task.completed:
            gap = (task.due_date - today).days
            print(f"  [{pet.name}] 'Insulin shot' next due: {task.due_date}  (+{gap} day)")

# ── 4. filter_by_status after completion ────────────────────────────────────
print("\n" + "=" * 55)
print("  filter_by_status(completed=True)")
print("=" * 55)
for pet, task in scheduler.filter_by_status(completed=True):
    print(f"  [{pet.name:6}] {task.description}")

print("\n" + "=" * 55)
print("  filter_by_status(completed=False) — pending + new recurrence")
print("=" * 55)
for pet, task in scheduler.filter_by_status(completed=False):
    print(f"  [{pet.name:6}] {task.description:<25} due: {task.due_date}")

print("=" * 55)
