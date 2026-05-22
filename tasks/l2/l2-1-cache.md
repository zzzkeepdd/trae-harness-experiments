# 任务 L2-1：带TTL和LRU的内存缓存库

## 复杂度
L2（中等复杂度，完整流程，涉及线程安全）

## 任务描述
实现 `cache.py`，支持以下功能：

1. `Cache(max_size: int)` — 初始化，设置最大容量
2. `set(key, value, ttl=None)` — 设置键值对，可选TTL秒数，过期自动清理
3. `get(key)` — 获取值，过期或不存在返回 None
4. `delete(key)` — 删除键，不存在时静默
5. `size()` — 返回当前条目数
6. `clear()` — 清空所有缓存
7. `keys()` — 返回当前所有 key 列表（调试用）

## 约束
- 纯 Python stdlib（time, threading, collections）
- 线程安全（threading.Lock）
- LRU 淘汰：超出 max_size 时淘汰最久未访问的条目
- get 访问会更新 LRU 顺序（touch）
- set 已存在的 key 不应触发淘汰
- 使用 monotonic 时间（防时钟跳变）
- max_size < 1 时抛出 ValueError
- delete 不存在的 key 时静默（不抛异常）

## 验收标准
AC-1: set后get返回正确值 ✓
AC-2: TTL过期后get返回None ✓
AC-3: 同key重新set更新TTL和值 ✓
AC-4: max_size=3时插入第4个不同key淘汰最旧项 ✓
AC-5: get(key)后key不算最旧（LRU更新）✓
AC-6: set已存在key不淘汰自身也不淘汰其他key ✓
AC-7: delete后get返回None ✓
AC-8: delete不存在的key不抛异常 ✓
AC-9: clear后size=0 ✓
AC-10: 100并发线程同时读写不崩溃 ✓
AC-11: 并发下size不超过max_size ✓
AC-12: max_size=0或负数抛出ValueError ✓
AC-13: get中先检查TTL过期再移动LRU位置（过期key不污染LRU）✓

## 边界条件（提示模型思考）
- max_size=1 的行为
- max_size=0 或负数
- 并发淘汰时的容量一致性
- TTL刚好过期的竞态条件
- 系统时钟调整（用monotonic解决）
- 过期key是否影响LRU顺序