import threading
import queue
import time
import os
from dataclasses import dataclass, field
from typing import Any, Optional, Callable

@dataclass(order=True)
class Task:
    priority: int
    id: str = field(compare=False)
    func: Callable = field(compare=False)
    args: tuple = field(default_factory=tuple, compare=False)
    kwargs: dict = field(default_factory=dict, compare=False)
    max_retries: int = field(default=3, compare=False)
    timeout: Optional[float] = field(default=None, compare=False)

class TaskQueue:
    def __init__(self, max_workers=4):
        if max_workers < 1:
            raise ValueError("max_workers must be >= 1")
        self._max_workers = max_workers
        self._queue = queue.PriorityQueue()
        self._results = {}
        self._results_lock = threading.Lock()
        self._workers = []
        self._running = False
        self._stop_event = threading.Event()
        self._stats = {"completed": 0, "failed": 0, "pending": 0}
        self._stats_lock = threading.Lock()
        self._closed = False
        self._close_lock = threading.Lock()

    def submit(self, task):
        with self._close_lock:
            if self._closed:
                raise RuntimeError("TaskQueue is closed, cannot submit new tasks")
        with self._stats_lock:
            self._stats["pending"] += 1
        self._queue.put((-task.priority, task))

    def start(self):
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        for i in range(self._max_workers):
            t = threading.Thread(target=self._worker, daemon=True)
            self._workers.append(t)
            t.start()

    def stop(self):
        self._running = False
        self._stop_event.set()
        with self._close_lock:
            self._closed = True
        for t in self._workers:
            t.join(timeout=5)

    def get_result(self, task_id, timeout=None):
        deadline = time.monotonic() + timeout if timeout is not None else None
        while True:
            with self._results_lock:
                if task_id in self._results:
                    return self._results.pop(task_id)
            if deadline is not None and time.monotonic() >= deadline:
                return None
            time.sleep(0.01)

    def _worker(self):
        while self._running or not self._queue.empty():
            try:
                _, task = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            retries = 0
            result = None
            while retries <= task.max_retries:
                try:
                    if task.timeout is not None:
                        result_container = []
                        exc_container = []
                        def target():
                            try:
                                result_container.append(task.func(*task.args, **task.kwargs))
                            except Exception as e:
                                exc_container.append(e)
                        t = threading.Thread(target=target, daemon=True)
                        t.start()
                        t.join(timeout=task.timeout)
                        if t.is_alive():
                            retries += 1
                            continue
                        if exc_container:
                            raise exc_container[0]
                        result = result_container[0] if result_container else None
                    else:
                        result = task.func(*task.args, **task.kwargs)
                    break
                except Exception:
                    retries += 1
            if retries > task.max_retries:
                result = {"error": "task failed after max retries"}
                with self._stats_lock:
                    self._stats["failed"] += 1
            else:
                with self._stats_lock:
                    self._stats["completed"] += 1
            with self._stats_lock:
                self._stats["pending"] -= 1
            with self._results_lock:
                self._results[task.id] = result
            self._queue.task_done()
