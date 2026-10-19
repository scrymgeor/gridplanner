from datetime import datetime, timedelta
import random

# Syllabus Check: Data Structures (In-memory Action Stack for Undo operations)
class ActionStack:
    def __init__(self):
        self._stack = []

    def push(self, action_type, data):
        self._stack.append((action_type, data))

    def pop(self):
        if not self.is_empty():
            return self._stack.pop()
        return None

    def is_empty(self):
        return len(self._stack) == 0


# =====================================================================
# OOP Domain Models (Inheritance, Polymorphism & Encapsulation)
# =====================================================================

class Task:
    """Base Domain Model for any task."""
    def __init__(self, task_id, title, category, deadline_str, estimated_hours, priority, color_tag=None):
        self.id = task_id
        self.title = title
        self.category = category.strip().title()
        self.deadline = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M")
        self.remaining_hours = float(estimated_hours)
        self.priority = int(priority)
        
        # Retro color tag selection
        palette = ["#64c4b8", "#f28e46", "#f6c85f", "#f7a3b5", "#93b5e6", "#7dc48f"]
        self.color_tag = color_tag if color_tag else random.choice(palette)

    def get_urgency_score(self, current_time):
        """Standard Urgency Heuristic: Priority / Hours remaining until deadline."""
        hours_left = (self.deadline - current_time).total_seconds() / 3600.0
        if hours_left <= 0:
            return 99999.0  # Immediate emergency / overdue
        return (self.priority * 100.0) / hours_left


class AcademicTask(Task):
    """Subclass: Academic assignments with marks weightage."""
    def __init__(self, task_id, title, category, deadline_str, estimated_hours, priority, meta_val, color_tag=None):
        super().__init__(task_id, title, category, deadline_str, estimated_hours, priority, color_tag)
        try:
            self.weightage = float(meta_val)
        except (ValueError, TypeError):
            self.weightage = 10.0

    def get_urgency_score(self, current_time):
        base = super().get_urgency_score(current_time)
        return base * (1.0 + (self.weightage / 100.0))


class WorkProjectTask(Task):
    """Subclass: Work or milestone projects."""
    def __init__(self, task_id, title, category, deadline_str, estimated_hours, priority, client_or_repo, color_tag=None):
        super().__init__(task_id, title, category, deadline_str, estimated_hours, priority, color_tag)
        self.client_or_repo = client_or_repo

    def get_urgency_score(self, current_time):
        base = super().get_urgency_score(current_time)
        return base * 1.25


class FitnessHabitTask(Task):
    """Subclass: Workout or routine tasks with active streaks."""
    def __init__(self, task_id, title, category, deadline_str, estimated_hours, priority, streak_days, color_tag=None):
        super().__init__(task_id, title, category, deadline_str, estimated_hours, priority, color_tag)
        try:
            self.streak_days = int(streak_days)
        except (ValueError, TypeError):
            self.streak_days = 1

    def get_urgency_score(self, current_time):
        base = super().get_urgency_score(current_time)
        return base + (self.streak_days * 5.0)


class GeneralTask(Task):
    """Subclass: General chores, errands, or life tasks."""
    def __init__(self, task_id, title, category, deadline_str, estimated_hours, priority, notes, color_tag=None):
        super().__init__(task_id, title, category, deadline_str, estimated_hours, priority, color_tag)
        self.notes = notes


class TimeSlot:
    """Represents a discrete free study window."""
    def __init__(self, slot_date, start_hour, duration_hours):
        self.date = slot_date
        self.start_datetime = datetime.combine(slot_date, datetime.min.time()) + timedelta(hours=start_hour)
        self.available_hours = float(duration_hours)


class AutoScheduler:
    """Greedy Scheduling Engine to chunk and fit tasks into available slots."""
    def __init__(self, tasks, time_slots):
        self.tasks = tasks
        self.time_slots = time_slots

    def generate(self):
        current_time = datetime.now()
        schedule_blocks = []

        pending_tasks = [t for t in self.tasks if t.remaining_hours > 0]
        # Lambda sorting based on calculated urgency scores
        pending_tasks.sort(key=lambda t: t.get_urgency_score(current_time), reverse=True)

        for slot in self.time_slots:
            if not pending_tasks:
                break

            while slot.available_hours > 0 and pending_tasks:
                current_task = pending_tasks[0]
                session_duration = min(slot.available_hours, current_task.remaining_hours, 1.5)

                start_str = slot.start_datetime.strftime("%H:%M")
                slot.start_datetime += timedelta(hours=session_duration)
                end_str = slot.start_datetime.strftime("%H:%M")

                schedule_blocks.append({
                    "task_id": current_task.id,
                    "task_title": current_task.title,
                    "subject": current_task.category,
                    "color_tag": current_task.color_tag,
                    "session_date": slot.date.strftime("%Y-%m-%d"),
                    "start_time": start_str,
                    "end_time": end_str
                })

                slot.available_hours -= session_duration
                current_task.remaining_hours -= session_duration

                if current_task.remaining_hours <= 0:
                    pending_tasks.pop(0)

        return schedule_blocks
