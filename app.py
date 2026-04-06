import streamlit as st
from pawpal_system import Task, Pet, Owner, DailyScheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# --- Initialize session state once ---
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan")

if "scheduler" not in st.session_state:
    st.session_state.scheduler = DailyScheduler(st.session_state.owner)

# --- Page header ---
st.title("🐾 PawPal+")
st.caption("A pet care planning assistant that builds a daily schedule for your pets.")

st.divider()

# --- Add a Pet ---
st.subheader("Add a Pet")

col1, col2, col3 = st.columns(3)
with col1:
    pet_name = st.text_input("Pet name", value="Mochi")
with col2:
    species = st.selectbox("Species", ["dog", "cat", "rabbit", "other"])
with col3:
    age = st.number_input("Age", min_value=0, max_value=30, value=3)

special_needs = st.text_input("Special needs (comma-separated, or leave blank)", value="")

if st.button("Add pet"):
    needs_list = [s.strip() for s in special_needs.split(",") if s.strip()]
    new_pet = Pet(name=pet_name, species=species, age=age, special_needs=needs_list)
    st.session_state.owner.add_pet(new_pet)
    st.success(f"Added {pet_name} the {species}!")

# Show current pets
if st.session_state.owner.pets:
    st.markdown("**Current pets:**")
    for pet in st.session_state.owner.pets:
        st.write(f"- {pet.describe()}")
else:
    st.info("No pets yet. Add one above.")

st.divider()

# --- Add a Task ---
st.subheader("Add a Task")

if st.session_state.owner.pets:
    pet_names = [pet.name for pet in st.session_state.owner.pets]

    col1, col2 = st.columns(2)
    with col1:
        selected_pet = st.selectbox("Assign to pet", pet_names)
    with col2:
        task_description = st.text_input("Task description", value="Morning walk")

    col3, col4, col5 = st.columns(3)
    with col3:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    with col4:
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
    with col5:
        preferred_time = st.selectbox("Preferred time", ["morning", "afternoon", "evening", "any"])

    frequency = st.selectbox("Frequency", ["daily", "weekly", "as-needed"])

    if st.button("Add task"):
        new_task = Task(
            description=task_description,
            duration_minutes=int(duration),
            priority=priority,
            preferred_time=preferred_time,
            frequency=frequency,
        )
        for pet in st.session_state.owner.pets:
            if pet.name == selected_pet:
                pet.add_task(new_task)
                st.success(f"Added '{task_description}' to {selected_pet}!")
                break

    # Show all pending tasks, sorted by priority then time slot
    scheduler = st.session_state.scheduler
    all_tasks = scheduler.sort_by_time(st.session_state.owner.get_all_tasks())

    if all_tasks:
        PRIORITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        st.markdown("**Pending tasks** *(sorted by priority, then preferred time)*:")
        rows = [
            {
                "Pet": pet.name,
                "Task": task.description,
                "Priority": f"{PRIORITY_ICON[task.priority]} {task.priority}",
                "Preferred time": task.preferred_time,
                "Duration (min)": task.duration_minutes,
                "Frequency": task.frequency,
            }
            for pet, task in all_tasks
        ]
        st.table(rows)
    else:
        st.info("No tasks yet. Add one above.")
else:
    st.info("Add a pet first before adding tasks.")

st.divider()

# --- Generate Schedule ---
st.subheader("Build Schedule")

if st.button("Generate schedule"):
    scheduler = st.session_state.scheduler
    schedule = scheduler.build_schedule()

    if not schedule:
        st.warning("No tasks could be scheduled. Add pets and tasks first.")
    else:
        # --- Conflict check — show before the plan so the owner can act on it ---
        conflicts = scheduler.detect_conflicts(schedule)
        if conflicts:
            st.error(
                f"⚠️ **{len(conflicts)} scheduling conflict{'s' if len(conflicts) > 1 else ''} detected** — "
                "two or more tasks overlap in time. Review the warnings below, then adjust task "
                "durations or preferred time slots before relying on this plan."
            )
            with st.expander("Show conflict details", expanded=True):
                for warning in conflicts:
                    # Strip the leading "WARNING: " prefix for cleaner display
                    clean = warning.removeprefix("WARNING: ")
                    st.warning(f"🕐 {clean}")
        else:
            st.success(f"Today's plan is ready — {len(schedule)} task{'s' if len(schedule) > 1 else ''} scheduled, no conflicts.")

        # --- Schedule table ---
        PRIORITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        rows = [
            {
                "Start": item["start"],
                "Pet": item["pet"],
                "Task": item["task"],
                "Duration (min)": item["duration_minutes"],
                "Priority": f"{PRIORITY_ICON[item['priority']]} {item['priority']}",
                "Frequency": item["frequency"],
            }
            for item in schedule
        ]
        st.table(rows)

        # --- Per-task reasoning ---
        with st.expander("Why was each task scheduled this way?"):
            for item in schedule:
                st.markdown(f"**{item['start']} · {item['pet']} · {item['task']}**")
                st.caption(item["reason"])
