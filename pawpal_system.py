from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Pet:
    name: str
    species: str
    age: int
    special_needs: list[str] = field(default_factory=list)

    def describe(self) -> str:
        needs = ", ".join(self.special_needs) if self.special_needs else "none"
        return f"{self.name} is a {self.age}-year-old {self.species} (special needs: {needs})"


@dataclass
class PetTask:
    title: str
    duration_minutes: int
    priority: Literal["low", "medium", "high"]
    preferred_time: Literal["morning", "afternoon", "evening", "any"] = "any"

    def is_high_priority(self) -> bool:
        return self.priority == "high"


class Owner:
    def __init__(self, name: str, pet: Pet, available_start: str = "07:00",
                 available_end: str = "20:00", max_tasks_per_day: int = 5):
        self.name = name
        self.pet = pet
        self.available_start = available_start
        self.available_end = available_end
        self.max_tasks_per_day = max_tasks_per_day

    def get_available_window(self) -> int:
        """Returns total available minutes in the day."""
        start_h, start_m = map(int, self.available_start.split(":"))
        end_h, end_m = map(int, self.available_end.split(":"))
        return (end_h * 60 + end_m) - (start_h * 60 + start_m)


class DailyScheduler:
    PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
    TIME_SLOTS = {"morning": "07:00", "afternoon": "12:00", "evening": "17:00", "any": None}

    def __init__(self, owner: Owner, tasks: list[PetTask]):
        self.owner = owner
        self.tasks = tasks

    def build_schedule(self) -> list[dict]:
        """Sort tasks by priority, respect the owner's task cap and time window."""
        sorted_tasks = sorted(self.tasks, key=lambda t: self.PRIORITY_ORDER[t.priority])
        capped = sorted_tasks[: self.owner.max_tasks_per_day]

        schedule = []
        current_minutes = self._to_minutes(self.owner.available_start)
        window_end = self._to_minutes(self.owner.available_end)

        for task in capped:
            if current_minutes + task.duration_minutes > window_end:
                break
            start_str = self._to_time_str(current_minutes)
            schedule.append({
                "task": task.title,
                "start": start_str,
                "duration_minutes": task.duration_minutes,
                "priority": task.priority,
                "reason": self._explain(task, start_str),
            })
            current_minutes += task.duration_minutes

        return schedule

    def explain_plan(self) -> str:
        schedule = self.build_schedule()
        if not schedule:
            return "No tasks could be scheduled."
        lines = [f"Daily plan for {self.owner.pet.name}:"]
        for item in schedule:
            lines.append(f"  {item['start']} — {item['task']} ({item['duration_minutes']} min): {item['reason']}")
        return "\n".join(lines)

    def filter_by_priority(self, level: Literal["low", "medium", "high"]) -> list[PetTask]:
        return [t for t in self.tasks if t.priority == level]

    def _explain(self, task: PetTask, start_time: str) -> str:
        reason = f"Scheduled at {start_time} because it is {task.priority} priority"
        if task.preferred_time != "any":
            reason += f" and preferred in the {task.preferred_time}"
        return reason + "."

    @staticmethod
    def _to_minutes(time_str: str) -> int:
        h, m = map(int, time_str.split(":"))
        return h * 60 + m

    @staticmethod
    def _to_time_str(minutes: int) -> str:
        return f"{minutes // 60:02d}:{minutes % 60:02d}"
