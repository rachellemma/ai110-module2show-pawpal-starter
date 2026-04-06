import datetime
from dataclasses import dataclass, field, replace
from itertools import combinations
from typing import Literal


@dataclass
class Task:
    description: str
    duration_minutes: int
    priority: Literal["low", "medium", "high"]
    preferred_time: Literal["morning", "afternoon", "evening", "any"] = "any"
    frequency: Literal["daily", "weekly", "as-needed"] = "daily"
    completed: bool = False
    due_date: datetime.date = field(default_factory=datetime.date.today)

    def is_high_priority(self) -> bool:
        """Return True if this task is marked high priority."""
        return self.priority == "high"

    def mark_complete(self):
        """Mark this task as done."""
        self.completed = True

    def reset(self):
        """Reset this task to incomplete for a new day."""
        self.completed = False


@dataclass
class Pet:
    name: str
    species: str
    age: int
    special_needs: list[str] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task):
        """Add a task to this pet's task list."""
        self.tasks.append(task)

    def get_pending_tasks(self) -> list[Task]:
        """Return only tasks that have not been completed yet."""
        return [t for t in self.tasks if not t.completed]

    def describe(self) -> str:
        """Return a human-readable summary of this pet's basic info and special needs."""
        needs = ", ".join(self.special_needs) if self.special_needs else "none"
        return f"{self.name} is a {self.age}-year-old {self.species} (special needs: {needs})"


class Owner:
    def __init__(self, name: str, available_start: str = "07:00",
                 available_end: str = "20:00", max_tasks_per_day: int = 8):
        self.name = name
        self.available_start = available_start
        self.available_end = available_end
        self.max_tasks_per_day = max_tasks_per_day
        self.pets: list[Pet] = []

    def add_pet(self, pet: Pet):
        """Add a pet to this owner's list of pets."""
        self.pets.append(pet)

    def get_all_tasks(self) -> list[tuple[Pet, Task]]:
        """Returns all pending tasks across all pets as (pet, task) pairs."""
        result = []
        for pet in self.pets:
            for task in pet.get_pending_tasks():
                result.append((pet, task))
        return result

    def get_available_window(self) -> int:
        """Returns total available minutes in the day."""
        start_h, start_m = map(int, self.available_start.split(":"))
        end_h, end_m = map(int, self.available_end.split(":"))
        return (end_h * 60 + end_m) - (start_h * 60 + start_m)


class DailyScheduler:
    PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
    TIME_SLOT_MINUTES = {"morning": 420, "afternoon": 720, "evening": 1020, "any": None}
    TIME_SLOT_ORDER = {"morning": 0, "afternoon": 1, "evening": 2, "any": 3}

    def __init__(self, owner: Owner):
        self.owner = owner

    def build_schedule(self) -> list[dict]:
        """Retrieve all tasks from owner's pets, sort by priority, fit into time window."""
        all_tasks = self.owner.get_all_tasks()

        sorted_tasks = self.sort_by_time(all_tasks)
        capped = sorted_tasks[: self.owner.max_tasks_per_day]

        schedule = []
        current_minutes = self._to_minutes(self.owner.available_start)
        window_end = self._to_minutes(self.owner.available_end)

        for pet, task in capped:
            # Honor preferred_time: if task has a preference and we haven't reached it yet, jump ahead
            preferred_start = self.TIME_SLOT_MINUTES.get(task.preferred_time)
            if preferred_start and current_minutes < preferred_start:
                current_minutes = preferred_start

            if current_minutes + task.duration_minutes > window_end:
                break

            start_str = self._to_time_str(current_minutes)
            schedule.append({
                "pet": pet.name,
                "task": task.description,
                "start": start_str,
                "duration_minutes": task.duration_minutes,
                "priority": task.priority,
                "frequency": task.frequency,
                "reason": self._explain(pet, task, start_str),
            })
            current_minutes += task.duration_minutes

        return schedule

    def sort_by_time(self, tasks: list[tuple["Pet", Task]]) -> list[tuple["Pet", Task]]:
        """Sort (pet, task) pairs by priority then by preferred time slot.

        Produces a stable ordering suitable for greedy scheduling:
          Priority:  high -> medium -> low
          Time slot: morning -> afternoon -> evening -> any

        Uses Python's built-in sorted() with a two-element tuple key so both
        dimensions are compared in a single pass — no secondary sort needed.

        Args:
            tasks: List of (Pet, Task) pairs to sort, typically from
                   Owner.get_all_tasks().

        Returns:
            A new list in ascending priority/time order; the original is unchanged.
        """
        return sorted(
            tasks,
            key=lambda pt: (
                self.PRIORITY_ORDER[pt[1].priority],
                self.TIME_SLOT_ORDER[pt[1].preferred_time],
            )
        )

    def filter_by_pet(self, pet_name: str) -> list[tuple["Pet", Task]]:
        """Return all pending (pet, task) pairs for a single named pet.

        Only incomplete tasks are included (delegates to get_pending_tasks
        via Owner.get_all_tasks). Case-sensitive match on pet name.

        Args:
            pet_name: Exact name of the pet to filter for (e.g. "Mochi").

        Returns:
            List of (Pet, Task) pairs, or an empty list if no match is found.
        """
        return [
            (pet, task)
            for pet, task in self.owner.get_all_tasks()
            if pet.name == pet_name
        ]

    def filter_by_status(self, completed: bool) -> list[tuple["Pet", Task]]:
        """Return all (pet, task) pairs matching the given completion status.

        Unlike filter_by_pet, this walks every task on every pet — including
        completed ones — so it can surface both done and still-pending work.

        Args:
            completed: Pass True to retrieve finished tasks, False for pending.

        Returns:
            List of (Pet, Task) pairs across all pets matching the status.
        """
        return [
            (pet, task)
            for pet in self.owner.pets
            for task in pet.tasks
            if task.completed == completed
        ]

    # How many days ahead each frequency schedules its next occurrence
    _RECURRENCE_DAYS = {"daily": 1, "weekly": 7}

    def mark_completed(self, task_description: str):
        """Mark a task done and automatically queue its next occurrence.

        Searches all pets for the first incomplete task matching the given
        description. Once found:
          - Marks it complete.
          - For "daily" tasks:  creates a copy due tomorrow
            (today + timedelta(days=1)).
          - For "weekly" tasks: creates a copy due in seven days
            (today + timedelta(days=7)).
          - For "as-needed" tasks: no follow-up is created.

        The new task is a dataclass replace() of the original, so all fields
        (duration, priority, preferred_time, frequency) carry over unchanged.

        Args:
            task_description: Exact description string of the task to complete.
        """
        for pet in self.owner.pets:
            for task in pet.tasks:
                if task.description == task_description and not task.completed:
                    task.mark_complete()
                    days_ahead = self._RECURRENCE_DAYS.get(task.frequency)
                    if days_ahead is not None:
                        next_due = datetime.date.today() + datetime.timedelta(days=days_ahead)
                        pet.add_task(replace(task, completed=False, due_date=next_due))

    def reset_all(self):
        """Reset all tasks to incomplete (start of new day)."""
        for pet in self.owner.pets:
            for task in pet.tasks:
                task.reset()

    def explain_plan(self) -> str:
        """Return a formatted string of the full daily schedule with reasons for each task."""
        schedule = self.build_schedule()
        if not schedule:
            return "No tasks could be scheduled."
        lines = [f"Daily plan for {self.owner.name}'s pets:"]
        for item in schedule:
            lines.append(
                f"  {item['start']} [{item['pet']}] {item['task']} "
                f"({item['duration_minutes']} min, {item['frequency']}): {item['reason']}"
            )
        return "\n".join(lines)

    def detect_conflicts(self, schedule: list[dict] | None = None) -> list[str]:
        """Return plain-text warnings for any overlapping time blocks in the schedule.

        Uses itertools.combinations to compare every unique pair of scheduled
        items — equivalent to the classic O(n^2) interval-overlap check but
        without manual index arithmetic. The overlap condition is:

            A.start < B.end  AND  B.start < A.end

        This catches same-start, partial, and full containment overlaps for
        tasks belonging to the same pet or different pets.

        Note: A schedule produced by build_schedule() will never trigger this
        because that method places tasks sequentially. This method is most
        useful for validating externally constructed or injected schedules.

        Args:
            schedule: List of schedule-item dicts (as returned by build_schedule).
                      Defaults to calling build_schedule() if None.

        Returns:
            List of human-readable WARNING strings, one per overlapping pair.
            Returns an empty list when no conflicts are found.
        """
        if schedule is None:
            schedule = self.build_schedule()

        warnings: list[str] = []
        for a, b in combinations(schedule, 2):
            a_start = self._to_minutes(a["start"])
            b_start = self._to_minutes(b["start"])
            if a_start < b_start + b["duration_minutes"] and b_start < a_start + a["duration_minutes"]:
                warnings.append(
                    f"WARNING: [{a['pet']}] '{a['task']}' ({a['start']}, {a['duration_minutes']} min) "
                    f"overlaps with [{b['pet']}] '{b['task']}' ({b['start']}, {b['duration_minutes']} min)"
                )
        return warnings

    def filter_by_priority(self, level: Literal["low", "medium", "high"]) -> list[dict]:
        """Return only scheduled items matching the given priority level."""
        return [item for item in self.build_schedule() if item["priority"] == level]

    def _explain(self, pet: Pet, task: Task, start_time: str) -> str:
        """Build a plain-English reason string for why a task was scheduled at a given time."""
        reason = f"Scheduled at {start_time} for {pet.name} — {task.priority} priority"
        if task.preferred_time != "any":
            reason += f", preferred in the {task.preferred_time}"
        if pet.special_needs:
            reason += f" (note: {pet.name} has special needs: {', '.join(pet.special_needs)})"
        return reason + "."

    @staticmethod
    def _to_minutes(time_str: str) -> int:
        """Convert a 'HH:MM' string to total minutes since midnight."""
        h, m = map(int, time_str.split(":"))
        return h * 60 + m

    @staticmethod
    def _to_time_str(minutes: int) -> str:
        """Convert total minutes since midnight back to a 'HH:MM' string."""
        return f"{minutes // 60:02d}:{minutes % 60:02d}"
