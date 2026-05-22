import threading, queue, time, uuid
from dataclasses import dataclass, field
from typing import Callable, Optional

@dataclass(order=True)
class Task:
    priority: int
    id: str = field(compare=False)
    func: Callable = field(compare=False)
    args: tuple = field(compare=False, default_factory=tuple)
    kwargs: dict = field(compare=False, default_factory=dict)
    max_retries: int = field(compare=False, default=3)
    timeout: Optional[float] = field(compare=False, default=None)

@dataclass
class TaskQueueStats:
    completed: int = 0; failed: int = 0; pending: int = 0; retries: int = 0

class TaskQueue:
    def __init__(self, max_workers=4, max_results=1000):
        self._max_workers = max_workers
        self._max_results = max_results
        self._pq = queue.PriorityQueue()
        self._results = {}; self._results_lock = threading.Lock()
        self._stats = TaskQueueStats(); self._stats_lock = threading.Lock()
        self._workers = []
        self._running = False
        self._stop_event = threading.Event()

    def submit(self, task):
        if not self._running: raise RuntimeError("Queue not running")
        self._pq.put((-task.priority, task.id, task))
        with self._stats_lock: self._stats.pending += 1

    def start(self):
        self._running = True; self._stop_event.clear()
        for _ in range(self._max_workers):
            t = threading.Thread(target=self._worker_loop, daemon=True); t.start(); self._workers.append(t)

    def _worker_loop(self):
        while not self._stop_event.is_set():
            try: item = self._pq.get(timeout=0.5)
            except queue.Empty: continue
            _, _, task = item
            with self._stats_lock: self._stats.pending -= 1
            self._execute_task(task); self._pq.task_done()

    def _execute_task(self, task):
        retries = 0; last_error = None
        while retries <= task.max_retries:
            try:
                result = task.func(*task.args, **task.kwargs)
                self._store_result(task.id, result)
                with self._stats_lock: self._stats.completed += 1; self._stats.retries += retries
                return
            except Exception as e: last_error = e; retries += 1
        self._store_result(task.id, {"error": str(last_error), "retries": retries})
        with self._stats_lock: self._stats.failed += 1; self._stats.retries += retries

    def _store_result(self, task_id, result):
        with self._results_lock:
            self._results[task_id] = result
            while len(self._results) > self._max_results:
                oldest = next(iter(self._results)); del self._results[oldest]

    def get_result(self, task_id, timeout=None):
        deadline = time.monotonic() + timeout if timeout else None
        while True:
            with self._results_lock:
                if task_id in self._results: return self._results[task_id]
            if deadline and time.monotonic() >= deadline: return None
            time.sleep(0.1)

    @property
    def stats(self):
        with self._stats_lock: return TaskQueueStats(completed=self._stats.completed, failed=self._stats.failed, pending=self._stats.pending, retries=self._stats.retries)

    def stop(self): self._running = False; self._stop_event.set()
