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

# --- Add a Task to a Pet ---
st.subheader("Add a Task")

if not st.session_state.owner.pets:
    st.warning("Add a pet first before adding tasks.")
else:
    pet_names = [p.name for p in st.session_state.owner.pets]

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

    # Show all pending tasks
    all_tasks = st.session_state.owner.get_all_tasks()
    if all_tasks:
        st.markdown("**Pending tasks:**")
        rows = [
            {
                "Pet": pet.name,
                "Task": task.description,
                "Duration (min)": task.duration_minutes,
                "Priority": task.priority,
                "Preferred time": task.preferred_time,
                "Frequency": task.frequency,
            }
            for pet, task in all_tasks
        ]
        st.table(rows)
    else:
        st.info("No tasks yet. Add one above.")

st.divider()

# --- Generate Schedule ---
st.subheader("Build Schedule")

if st.button("Generate schedule"):
    scheduler = DailyScheduler(st.session_state.owner)
    schedule = scheduler.build_schedule()

    if not schedule:
        st.warning("No tasks could be scheduled. Add pets and tasks first.")
    else:
        st.success("Here is today's plan:")
        for item in schedule:
            st.markdown(
                f"**{item['start']}** — [{item['pet']}] {item['task']} "
                f"({item['duration_minutes']} min, {item['frequency']})"
            )
            st.caption(item["reason"])
