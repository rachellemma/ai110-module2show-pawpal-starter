from pawpal_system import Task, Pet


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
