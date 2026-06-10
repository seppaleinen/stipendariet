import threading
from datetime import datetime
from enum import StrEnum


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TranslationTask:
    def __init__(self, task_id: str, task_name: str = "generic"):
        self.task_id = task_id
        self.task_name = task_name
        self.status = TaskStatus.PENDING
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.start_time: datetime | None = None
        self.progress = 0
        self.total = 0
        self.completed = 0
        self.failed = 0
        self.skipped = 0
        self.estimated_remaining_seconds: float | None = None
        self.result: dict | None = None
        self.error: str | None = None
        self._lock = threading.Lock()

    def update_status(self, status: TaskStatus):
        with self._lock:
            self.status = status
            self.updated_at = datetime.utcnow()
            if status == TaskStatus.RUNNING and self.start_time is None:
                self.start_time = datetime.utcnow()

    def update_progress(self, completed: int, failed: int, skipped: int, total: int):
        with self._lock:
            self.completed = completed
            self.failed = failed
            self.skipped = skipped
            self.total = total
            processed = completed + failed + skipped
            if total > 0:
                self.progress = processed / total * 100
            self.updated_at = datetime.utcnow()

            # Calculate estimated time remaining
            if self.start_time and processed > 0 and processed < total:
                elapsed = (datetime.utcnow() - self.start_time).total_seconds()
                avg_time_per_item = elapsed / processed
                remaining_items = total - processed
                self.estimated_remaining_seconds = avg_time_per_item * remaining_items
            else:
                self.estimated_remaining_seconds = None

    def set_result(self, result: dict):
        with self._lock:
            self.result = result
            self.status = TaskStatus.COMPLETED
            self.updated_at = datetime.utcnow()
            self.estimated_remaining_seconds = 0

    def set_error(self, error: str):
        with self._lock:
            self.error = error
            self.status = TaskStatus.FAILED
            self.updated_at = datetime.utcnow()
            self.estimated_remaining_seconds = None


# In-memory storage for tasks (in production, use Redis or database)
_active_tasks: dict[str, TranslationTask] = {}


def get_task(task_id: str) -> TranslationTask | None:
    """Get a task by ID"""
    return _active_tasks.get(task_id)


def create_task(task_id: str, task_name: str = "generic") -> TranslationTask:
    """Create a new task"""
    task = TranslationTask(task_id, task_name=task_name)
    _active_tasks[task_id] = task
    return task


def remove_task(task_id: str):
    """Remove a task by ID"""
    _active_tasks.pop(task_id, None)


def get_active_tasks_summary() -> dict[str, dict | None]:
    """
    Returns a summary of running tasks across different task_names.
    E.g. {'sync_foundations': {'task_id': '123...', 'status': 'running'}, 'bulk_translation': None}
    """
    summary = {}
    for t_id, task in _active_tasks.items():
        if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            summary[task.task_name] = {
                "task_id": task.task_id,
                "status": task.status
            }
    return summary
