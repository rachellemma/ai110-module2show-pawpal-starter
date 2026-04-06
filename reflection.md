# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.

The UML design should contain info about pet tasks,
information about the pet owner, and then it should
generate a daily task schedule that incorporates both information and ideally explains why it chose that setup. 

- What classes did you include, and what responsibilities did you assign to each?

The four classes are PetTask, Pet, Owner, and DailySchedule. PetTask contains the title, duration, priority, preferred_time. Pet contains name, species, age, special_needs. Owner contains name, available_hours, max_tasks_per_day. Owner has a Pet.  DailySchedule takes Owner + list of PetTasks to build_schedule(). 

classDiagram
    class Pet {
        +String name
        +String species
        +int age
        +List~String~ special_needs
        +describe() String
    }

    class Owner {
        +String name
        +String available_start
        +String available_end
        +int max_tasks_per_day
        +Pet pet
        +get_available_window() int
    }

    class PetTask {
        +String title
        +int duration_minutes
        +String priority
        +String preferred_time
        +is_high_priority() bool
    }

    class DailyScheduler {
        +Owner owner
        +List~PetTask~ tasks
        +build_schedule() List
        +explain_plan() String
        +filter_by_priority(level: String) List
    }

    Owner "1" --> "1" Pet : has
    DailyScheduler "1" --> "1" Owner : uses
    DailyScheduler "1" --> "many" PetTask : schedules


**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

Some missing relationships were that Pet and PetTask have no connection but in real life a task belongs to a pet. Right now, any task could apply to any species. A simple fix would be to add a species field to PetTask. DailyScheduler never uses Pet.special_needs, it acceses owner.pet.name for display but ignores special needs entirely. 

Some logic bottlenecks is that preferred_time is stored on PetTask but build_schedule() never uses it. TIME_SLOTS on line 45 is defines but never used anywhere in class. 

Task (renamed from PetTask) — added frequency and completed status, plus mark_complete() and reset() methods. This makes it a proper stateful object.

Pet — now owns its tasks via tasks: list[Task]. get_pending_tasks() filters out completed ones. This is the key relationship change — tasks belong to a pet, not floating freely.

Owner — now has multiple pets (self.pets: list[Pet]). The critical method is get_all_tasks() which walks every pet and returns (pet, task) pairs. This is how the Scheduler "talks" to the Owner:
---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

**Greedy sequential placement instead of true overlap detection**

`build_schedule()` assigns each task a start time by advancing a single `current_minutes` clock forward after every task. This guarantees the *generated* schedule never has overlaps — but it also means the scheduler silently skips tasks that don't fit rather than warning the owner or trying a different ordering.

The tradeoff: `detect_conflicts()` uses a proper interval-overlap check (`a_start < b_end and b_start < a_end`) that would catch two tasks sharing the same window, but it only matters when a schedule is built externally or injected for testing. On a schedule the greedy builder produces, conflicts are structurally impossible.

**Why this is reasonable here:** A single pet owner following one linear day doesn't need an optimal packing algorithm. Greedy placement is easy to reason about, produces a schedule in O(n log n) time (dominated by the sort), and never crashes. The cost is that a lower-priority task at the end of a packed day may be silently dropped. A future improvement would be to collect dropped tasks and surface them as warnings alongside the schedule.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
