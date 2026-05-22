# 任务 L3-1：并发任务队列

## 复杂度
L3（复杂，多线程、优先级队列、重试机制、错误处理）

## 任务描述
实现 `task_queue.py`，一个支持多worker并发消费、带优先级和重试的任务队列系统。

1. `Task(id, func, args=(), kwargs={}, priority=0, max_retries=3)` — 任务对象
2. `TaskQueue(max_workers=4)` — 任务队列，管理worker池
3. `submit(task: Task)` — 提交任务
4. `start()` — 启动worker池
5. `stop()` — 优雅停止（等待所有任务完成）
6. `get_result(task_id: str, timeout=None) -> Any` — 获取结果
7. `TaskQueueStats` — 统计信息（完成数、失败数、待处理数、重试次数）

## 约束
- 纯 Python stdlib（threading, queue, dataclasses, time）
- worker 数量可配置
- 优先级队列：数字越大优先级越高
- 重试机制：任务失败自动重试（最多max_retries次）
- 结果存储：已完成任务的结果存储有限制（最多保留最近1000个）
- 优雅关闭：stop() 等待所有运行中任务完成后再退出
- 线程安全
- 任务执行超时（可配置，每个任务最多执行 N 秒）

## 验收标准
AC-1: 基础提交和执行：submit后任务被执行，get_result获取结果 ✓
AC-2: 多worker并发：4个worker同时处理4个独立任务，总时间 < 单任务时间的2倍 ✓
AC-3: 优先级顺序：高优先级任务先于低优先级被执行 ✓
AC-4: 重试机制：任务失败自动重试，最终失败记录retry_count ✓
AC-5: 永久失败：超过max_retries后标记为failed，结果存储失败信息 ✓
AC-6: 任务超时：执行超过timeout秒的任务被强制取消并标记timeout ✓
AC-7: 优雅停止：stop()等待所有任务完成后返回，未完成任务保留在队列 ✓
AC-8: 统计准确：stats反映真实的完成/失败/待处理数量 ✓
AC-9: 结果清理：超过1000个结果后最老的被清理，不影响新任务 ✓
AC-10: 并发下结果一致性：多任务同时get_result不冲突 ✓
AC-11: 队列空时worker阻塞不消耗CPU ✓
AC-12: 已关闭队列不能再提交任务（抛异常）✓

## 边界条件（提示模型思考）
- worker=0 或负数
- get_result超时（任务未完成）
- 任务抛出异常（非Exception的子类）
- 任务函数本身阻塞（用超时机制解决）
- 多线程同时stop()
- 重试时任务ID的追踪
- 结果存储的内存泄漏风险