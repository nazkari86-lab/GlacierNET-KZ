"""Background task manager — priority queue, lifecycle, progress tracking."""

from __future__ import annotations

import asyncio
import enum
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional

logger = logging.getLogger("glacierkz.tasks")


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(int, enum.Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class TaskInfo:
    task_id: str
    name: str
    status: TaskStatus
    priority: TaskPriority
    progress: float = 0.0
    message: str = ""
    stage: str = ""
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    client_id: Optional[str] = None
    user_id: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    timeout: float = 600.0
    retry_count: int = 0
    max_retries: int = 0

    @property
    def elapsed(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.completed_at or time.time()
        return end - self.started_at

    @property
    def is_terminal(self) -> bool:
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status.value,
            "priority": self.priority.value,
            "progress": self.progress,
            "message": self.message,
            "stage": self.stage,
            "result": self.result if self.status == TaskStatus.COMPLETED else None,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "elapsed": self.elapsed,
            "client_id": self.client_id,
            "tags": self.tags,
            "retry_count": self.retry_count,
        }


@dataclass
class _TaskEntry:
    info: TaskInfo
    coroutine: Callable[..., Coroutine]
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    _future: Optional[asyncio.Task] = field(default=None, repr=False)


class TaskManager:
    """Async background task manager with concurrency control and progress."""

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self._tasks: dict[str, _TaskEntry] = {}
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running = False
        self._worker_tasks: list[asyncio.Task] = []
        self._progress_callbacks: dict[str, list[Callable]] = defaultdict(list)

    async def start(self, num_workers: int = 3) -> None:
        self._running = True
        for i in range(num_workers):
            task = asyncio.create_task(self._worker(f"worker-{i}"))
            self._worker_tasks.append(task)
        logger.info(f"Task manager started with {num_workers} workers")

    async def stop(self) -> None:
        self._running = False
        for task in self._worker_tasks:
            task.cancel()
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()
        logger.info("Task manager stopped")

    async def submit(
        self,
        name: str,
        coroutine_fn: Callable[..., Coroutine],
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        client_id: str | None = None,
        user_id: str | None = None,
        tags: list[str] | None = None,
        timeout: float = 600.0,
        max_retries: int = 0,
        **kwargs,
    ) -> str:
        task_id = str(uuid.uuid4())[:12]
        info = TaskInfo(
            task_id=task_id,
            name=name,
            status=TaskStatus.PENDING,
            priority=priority,
            client_id=client_id,
            user_id=user_id,
            tags=tags or [],
            timeout=timeout,
            max_retries=max_retries,
        )
        entry = _TaskEntry(
            info=info,
            coroutine=coroutine_fn,
            args=args,
            kwargs=kwargs,
        )
        self._tasks[task_id] = entry
        await self._queue.put((-priority.value, time.time(), task_id))
        logger.info(f"Task submitted: {task_id} ({name})")
        return task_id

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        entry = self._tasks.get(task_id)
        return entry.info if entry else None

    def list_tasks(
        self,
        status: TaskStatus | None = None,
        tags: list[str] | None = None,
        limit: int = 50,
    ) -> list[TaskInfo]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [e for e in tasks if e.info.status == status]
        if tags:
            tasks = [e for e in tasks if set(tags) & set(e.info.tags)]
        tasks.sort(key=lambda e: e.info.created_at, reverse=True)
        return [e.info for e in tasks[:limit]]

    async def cancel_task(self, task_id: str) -> bool:
        entry = self._tasks.get(task_id)
        if not entry or entry.info.is_terminal:
            return False
        if entry._future and not entry._future.done():
            entry._future.cancel()
        entry.info.status = TaskStatus.CANCELLED
        entry.info.completed_at = time.time()
        logger.info(f"Task cancelled: {task_id}")
        return True

    async def cancel_all(self) -> int:
        count = 0
        for entry in self._tasks.values():
            if not entry.info.is_terminal:
                if entry._future and not entry._future.done():
                    entry._future.cancel()
                entry.info.status = TaskStatus.CANCELLED
                entry.info.completed_at = time.time()
                count += 1
        return count

    def on_progress(self, task_id: str, callback: Callable) -> None:
        self._progress_callbacks[task_id].append(callback)

    async def update_progress(self, task_id: str, progress: float, message: str = "", stage: str = "") -> None:
        entry = self._tasks.get(task_id)
        if entry:
            entry.info.progress = min(100.0, max(0.0, progress))
            entry.info.message = message
            entry.info.stage = stage
            for cb in self._progress_callbacks.get(task_id, []):
                try:
                    await cb(entry.info) if asyncio.iscoroutinefunction(cb) else cb(entry.info)
                except Exception:
                    pass

    async def _worker(self, name: str) -> None:
        while self._running:
            try:
                _, _, task_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            entry = self._tasks.get(task_id)
            if not entry or entry.info.is_terminal:
                continue
            async with self._semaphore:
                entry.info.status = TaskStatus.RUNNING
                entry.info.started_at = time.time()
                try:
                    result = await asyncio.wait_for(
                        entry.coroutine(*entry.args, **entry.kwargs),
                        timeout=entry.info.timeout,
                    )
                    entry.info.status = TaskStatus.COMPLETED
                    entry.info.result = result
                    entry.info.progress = 100.0
                    logger.info(f"Task completed: {task_id}")
                except asyncio.CancelledError:
                    entry.info.status = TaskStatus.CANCELLED
                    entry.info.completed_at = time.time()
                except asyncio.TimeoutError:
                    entry.info.status = TaskStatus.FAILED
                    entry.info.error = f"Timeout after {entry.info.timeout}s"
                    entry.info.completed_at = time.time()
                    logger.error(f"Task timeout: {task_id}")
                except Exception as exc:
                    if entry.info.retry_count < entry.info.max_retries:
                        entry.info.retry_count += 1
                        entry.info.status = TaskStatus.PENDING
                        entry.info.started_at = None
                        await self._queue.put((-entry.info.priority.value, time.time(), task_id))
                        logger.warning(f"Task retry {entry.info.retry_count}/{entry.info.max_retries}: {task_id}")
                    else:
                        entry.info.status = TaskStatus.FAILED
                        entry.info.error = f"{type(exc).__name__}: {exc}"
                        entry.info.completed_at = time.time()
                        logger.error(f"Task failed: {task_id}: {exc}")
                finally:
                    entry.info.completed_at = entry.info.completed_at or time.time()

    def get_stats(self) -> dict:
        counts = defaultdict(int)
        for entry in self._tasks.values():
            counts[entry.info.status.value] += 1
        return {
            "total": len(self._tasks),
            "by_status": dict(counts),
            "queue_size": self._queue.qsize(),
            "max_concurrent": self.max_concurrent,
        }


_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    global _manager
    if _manager is None:
        _manager = TaskManager()
    return _manager
