import threading, queue, time
from dataclasses import dataclass
@dataclass(order=True)
class Task:
    priority: int
    id: str = field(default="", compare=False)
    func: any = field(default=None, compare=False)
    args: any = field(default_factory=tuple, compare=False)
class TaskQueue:
    def __init__(self, max_workers=4):
        self._max_workers = max_workers
        self._queue = queue.PriorityQueue()
        self._results = {}
        self._workers = []; self._running = False; self._lock = threading.Lock()
    def submit(self, task):
        self._queue.put((-task.priority, task))
    def start(self):
        self._running = True
        for _ in range(self._max_workers):
            t = threading.Thread(target=self._worker, daemon=True); self._workers.append(t); t.start()
    def stop(self):
        self._running = False
        for t in self._workers: t.join(timeout=5)
    def get_result(self, task_id, timeout=None):
        deadline = time.monotonic() + timeout if timeout else None
        while deadline is None or time.monotonic() < deadline:
            with self._lock:
                if task_id in self._results: return self._results.pop(task_id)
            time.sleep(0.01)
        return None
    def _worker(self):
        while self._running or not self._queue.empty():
            try: _, task = self._queue.get(timeout=0.1)
            except queue.Empty: continue
            try: result = task.func(*task.args) if hasattr(task, 'args') else task.func()
            except Exception as e: result = {"error": str(e)}
            with self._lock: self._results[task.id] = result
            self._queue.task_done()
