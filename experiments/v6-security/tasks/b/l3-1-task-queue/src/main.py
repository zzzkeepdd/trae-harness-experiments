import threading, queue, time, re
from dataclasses import dataclass, field as dc_field
@dataclass(order=True)
class Task:
    priority: int
    id: str = dc_field(default="", compare=False)
    func: any = dc_field(default=None, compare=False)
    args: any = dc_field(default_factory=tuple, compare=False)
    kwargs: any = dc_field(default_factory=dict, compare=False)
    max_retries: int = dc_field(default=3, compare=False)
    timeout: float = dc_field(default=None, compare=False)
SAFE_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')
class TaskQueue:
    def __init__(self, max_workers=4):
        if max_workers < 1: raise ValueError("max_workers>=1")
        self._max_workers = max_workers
        self._queue = queue.PriorityQueue()
        self._results = {}; self._results_lock = threading.Lock()
        self._workers = []; self._running = False
        self._stop_event = threading.Event()
        self._stats = {"completed": 0, "failed": 0, "pending": 0}
        self._stats_lock = threading.Lock()
        self._closed = False; self._close_lock = threading.Lock()
    def submit(self, task):
        with self._close_lock:
            if self._closed: raise RuntimeError("closed")
        with self._stats_lock: self._stats["pending"] += 1
        self._queue.put((-task.priority, task))
    def start(self):
        if self._running: return
        self._running = True; self._stop_event.clear()
        for _ in range(self._max_workers):
            t = threading.Thread(target=self._worker, daemon=True); self._workers.append(t); t.start()
    def stop(self):
        self._running = False; self._stop_event.set()
        with self._close_lock: self._closed = True
        for t in self._workers: t.join(timeout=5)
    def get_result(self, task_id, timeout=None):
        deadline = time.monotonic() + timeout if timeout else None
        while deadline is None or time.monotonic() < deadline:
            with self._results_lock:
                if task_id in self._results: return self._results.pop(task_id)
            time.sleep(0.01)
        return None
    def _validate_task(self, task):
        if not SAFE_PATTERN.match(str(task.id)):
            raise ValueError(f"invalid task id: {task.id}")
    def _worker(self):
        while self._running or not self._queue.empty():
            try: _, task = self._queue.get(timeout=0.1)
            except queue.Empty: continue
            try:
                self._validate_task(task)
            except ValueError as e:
                with self._stats_lock: self._stats["failed"] += 1; self._stats["pending"] -= 1
                with self._results_lock: self._results[task.id] = {"error": str(e)}
                self._queue.task_done(); continue
            retries = 0; result = None
            while retries <= task.max_retries:
                try:
                    result = task.func(*task.args, **task.kwargs); break
                except Exception:
                    retries += 1
            if retries > task.max_retries:
                result = {"error": "max retries exceeded"}
                with self._stats_lock: self._stats["failed"] += 1
            else:
                with self._stats_lock: self._stats["completed"] += 1
            with self._stats_lock: self._stats["pending"] -= 1
            with self._results_lock: self._results[task.id] = result
            self._queue.task_done()
