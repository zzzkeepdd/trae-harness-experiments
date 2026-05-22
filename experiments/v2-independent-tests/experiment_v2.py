"""
新实验：独立测试驱动对比
核心改动：
  1. 测试用例独立编写，基于任务验收标准
  2. A/B 两组代码跑同一套测试，不依赖 auditor
  3. 指标：测试通过数/总数、覆盖率
"""
import sys, os, json, time, csv, io, tempfile, threading, contextlib
from pathlib import Path

# 把 A/B 组的代码路径加入 import
RESULTS = Path(r"d:\harness测试\ab-exp\results")


def load_module(tid, group):
    """动态加载 A 或 B 组的代码"""
    d = RESULTS / tid / group
    py_files = list(d.glob("*.py"))
    if not py_files:
        return None
    code = py_files[0].read_text(encoding="utf-8")
    ns = {}
    exec(code, ns)
    return ns


# ============================================================
# 测试框架
# ============================================================
_EXPECT_NONE = object()

class TestResult:
    def __init__(self, name):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.details = []

    def test(self, desc, expr, expected=_EXPECT_NONE):
        """expr 是布尔断言，或 callable 返回结果，expected 用于自动判断"""
        if callable(expr):
            try:
                result = expr()
                if expected is not _EXPECT_NONE:
                    ok = result == expected
                elif isinstance(result, bool):
                    ok = result
                else:
                    ok = result is not None and result is not False
            except Exception as e:
                ok = False
                result = f"Exception: {e}"
        else:
            ok = bool(expr)
            result = None

        if ok:
            self.passed += 1
        else:
            self.failed += 1
            detail = f"  FAIL {desc}: got {result!r}"
            if expected is not _EXPECT_NONE:
                detail += f", expected {expected!r}"
            self.details.append(detail)

    def raises(self, desc, fn, exc_type):
        try:
            fn()
            self.failed += 1
            self.details.append(f"  FAIL {desc}: no exception raised, expected {exc_type.__name__}")
        except exc_type:
            self.passed += 1
        except Exception as e:
            self.failed += 1
            self.details.append(f"  FAIL {desc}: wrong exception {type(e).__name__}: {e}")

    def summary(self):
        total = self.passed + self.failed
        rate = (self.passed / total * 100) if total > 0 else 0
        return self.passed, self.failed, total, rate


def run_tests(group="harness"):
    """对所有任务运行测试"""
    all_results = {}
    for func, tid in [
        (test_l1_1, "l1-1-string-utils"),
        (test_l1_2, "l1-2-list-utils"),
        (test_l2_1, "l2-1-cache"),
        (test_l2_2, "l2-2-csv-processor"),
        (test_l3_1, "l3-1-task-queue"),
        (test_l3_2, "l3-2-session-manager"),
    ]:
        ns = load_module(tid, group)
        if ns is None:
            r = TestResult(tid)
            r.failed = 99
            r.details.append(f"  FAIL: could not load {group} code")
            all_results[tid] = r
            continue
        r = func(ns)
        all_results[tid] = r
    return all_results


# ============================================================
# L1-1 字符串工具测试
# ============================================================
def test_l1_1(ns):
    r = TestResult("l1-1-string-utils")
    reverse = ns["reverse"]
    to_title_case = ns["to_title_case"]
    is_palindrome = ns["is_palindrome"]
    word_count = ns["word_count"]

    # reverse
    r.test("reverse: normal", lambda: reverse("hello"), "olleh")
    r.test("reverse: empty", lambda: reverse(""), "")
    r.test("reverse: single", lambda: reverse("a"), "a")
    r.test("reverse: unicode", lambda: reverse("你好世界"), "界世好你")

    # to_title_case
    r.test("to_title_case: normal", lambda: to_title_case("hello world"), "Hello World")
    r.test("to_title_case: empty becomes empty", lambda: to_title_case(""), "")
    r.test("to_title_case: single word", lambda: to_title_case("PYTHON"), "Python")

    # is_palindrome
    r.test("is_palindrome: true case", lambda: is_palindrome("racecar"), True)
    r.test("is_palindrome: false case", lambda: is_palindrome("hello"), False)
    r.test("is_palindrome: with spaces", lambda: is_palindrome("A man a plan a canal Panama"), True)
    r.test("is_palindrome: with punctuation", lambda: is_palindrome("Madam, I'm Adam"), True)
    r.test("is_palindrome: empty string", lambda: is_palindrome(""))

    # word_count
    r.test("word_count: normal", lambda: word_count("hello world hello"),
           {"hello": 2, "world": 1})
    r.test("word_count: empty", lambda: word_count(""), {})
    r.test("word_count: single", lambda: word_count("test"), {"test": 1})
    r.test("word_count: case insensitive", lambda: word_count("Hello hello HELLO"), {"hello": 3})

    return r


# ============================================================
# L1-2 列表工具测试
# ============================================================
def test_l1_2(ns):
    r = TestResult("l1-2-list-utils")
    dedup = ns["dedup"]
    flatten = ns["flatten"]
    group_by = ns["group_by"]
    top_n = ns["top_n"]

    # dedup
    r.test("dedup: normal", lambda: dedup([1, 2, 2, 3]), [1, 2, 3])
    r.test("dedup: all unique", lambda: dedup([1, 2, 3]), [1, 2, 3])
    r.test("dedup: empty", lambda: dedup([]), [])
    r.test("dedup: None", lambda: dedup(None), [])
    r.test("dedup: preserve order", lambda: dedup([3, 1, 2, 1, 3]), [3, 1, 2])

    # flatten
    r.test("flatten: normal", lambda: flatten([[1, 2], [3, 4]]), [1, 2, 3, 4])
    r.test("flatten: mixed", lambda: flatten([[1, 2], 3, [4]]), [1, 2, 3, 4])
    r.test("flatten: empty", lambda: flatten([]), [])
    r.test("flatten: None", lambda: flatten(None), [])

    # group_by
    r.test("group_by: by length",
           lambda: group_by(["a", "bb", "cc", "ddd"], len),
           {1: ["a"], 2: ["bb", "cc"], 3: ["ddd"]})
    r.test("group_by: empty", lambda: group_by([], str), {})
    r.test("group_by: none items", lambda: group_by(None, str), {})

    # top_n
    r.test("top_n: normal", lambda: top_n([5, 3, 8, 1, 9], 2), [9, 8])
    r.test("top_n: n > len", lambda: top_n([3, 1], 5), [3, 1])
    r.test("top_n: n = 0", lambda: top_n([1, 2], 0), [])
    r.test("top_n: n = 1", lambda: top_n([1, 2, 3], 1), [3])
    r.test("top_n: None items", lambda: top_n(None, 3), [])
    r.test("top_n: with key_fn",
           lambda: top_n(["a", "bb", "ccc"], 1, key_fn=len), ["ccc"])

    return r


# ============================================================
# L2-1 缓存库测试
# ============================================================
def test_l2_1(ns):
    r = TestResult("l2-1-cache")
    Cache = ns["Cache"]

    # basic set/get
    c = Cache(3)
    c.set("a", 1)
    r.test("set/get: basic", lambda: c.get("a"), 1)
    r.test("get: missing", lambda: c.get("b"), None)
    r.test("size: basic", lambda: c.size(), 1)

    # LRU eviction
    c2 = Cache(2)
    c2.set("a", 1)
    c2.set("b", 2)
    c2.get("a")
    c2.set("c", 3)
    r.test("LRU: b evicted", lambda: c2.get("b"), None)
    r.test("LRU: a retained", lambda: c2.get("a"), 1)
    r.test("LRU: c exists", lambda: c2.get("c"), 3)

    # overwrite existing key
    c3 = Cache(3)
    c3.set("a", 1)
    c3.set("a", 100)
    r.test("overwrite: new value", lambda: c3.get("a"), 100)
    r.test("overwrite: size unchanged", lambda: c3.size(), 1)

    # TTL
    c4 = Cache(5)
    c4.set("x", 99, ttl=0.1)
    r.test("TTL: before expiry", lambda: c4.get("x"), 99)
    time.sleep(0.15)
    r.test("TTL: after expiry", lambda: c4.get("x"), None)
    r.test("TTL: cache size after expiry",
           lambda: c4.size(), 0)

    # delete & clear
    c5 = Cache(10)
    c5.set("a", 1)
    c5.set("b", 2)
    c5.delete("a")
    r.test("delete: removed", lambda: c5.get("a"), None)
    r.test("delete: other remains", lambda: c5.get("b"), 2)
    c5.clear()
    r.test("clear: empty", lambda: c5.size(), 0)

    # keys
    c6 = Cache(10)
    c6.set("x", 1)
    c6.set("y", 2)
    r.test("keys: returns set", lambda: set(c6.keys()), {"x", "y"})

    return r


# ============================================================
# L2-2 CSV 处理器测试
# ============================================================
def test_l2_2(ns):
    r = TestResult("l2-2-csv-processor")
    read_csv = ns["read_csv"]
    filter_rows = ns["filter_rows"]
    aggregate = ns["aggregate"]
    write_csv = ns["write_csv"]
    process_pipeline = ns["process_pipeline"]

    # write then read roundtrip
    d = [{"name": "Alice", "score": "90"}, {"name": "Bob", "score": "85"}]
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", encoding="utf-8") as f:
        f.write("name,score\nAlice,90\nBob,85\n")
        tmp = f.name
    try:
        data = read_csv(tmp)
        r.test("read: count rows", lambda: len(data), 2)
        r.test("read: first row name", lambda: data[0]["name"], "Alice")
    finally:
        os.unlink(tmp)

    # filter
    r.test("filter: match", lambda: len(filter_rows(d, {"name": "Alice"})), 1)
    r.test("filter: no match", lambda: len(filter_rows(d, {"name": "Charlie"})), 0)
    r.test("filter: empty data", lambda: filter_rows([], {"a": "1"}), [])

    # aggregate
    r.test("aggregate: sum by name", 
           lambda: aggregate(d, "name", {"op": "sum", "column": "score"}),
           [{"name": "Alice", "sum": 90.0}, {"name": "Bob", "sum": 85.0}])
    r.test("aggregate: empty data",
           lambda: aggregate([], "x", {"op": "sum", "column": "v"}), [])

    # write_csv + read roundtrip
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        tmp2 = f.name
    try:
        write_data = [{"col": "A", "val": "1"}]
        write_csv(write_data, tmp2)
        read_back = read_csv(tmp2)
        r.test("write+read: roundtrip", lambda: read_back[0]["col"], "A")
    finally:
        if os.path.exists(tmp2):
            os.unlink(tmp2)

    return r


# ============================================================
# L3-1 任务队列测试
# ============================================================
def test_l3_1(ns):
    r = TestResult("l3-1-task-queue")
    Task = ns["Task"]
    TaskQueue = ns["TaskQueue"]

    # 基本 submit + start + get_result
    q = TaskQueue(max_workers=2)
    q.start()
    t1 = Task(priority=1, id="t1", func=lambda x: x * 2, args=(21,))
    q.submit(t1)
    result = q.get_result("t1", timeout=5)
    r.test("basic: result", lambda: result, 42)
    q.stop()

    # 优先级排序
    q2 = TaskQueue(max_workers=2)
    q2.start()
    results_holder = []
    t_high = Task(priority=10, id="high", func=lambda: results_holder.append("high"))
    t_low = Task(priority=1, id="low", func=lambda: results_holder.append("low"))
    q2.submit(t_low)
    q2.submit(t_high)
    q2.get_result("high", timeout=5)
    q2.get_result("low", timeout=5)
    r.test("priority: high first",
           lambda: results_holder[0] == "high" and results_holder[1] == "low", True)
    q2.stop()

    # 超时
    q3 = TaskQueue(max_workers=1)
    q3.start()
    t_slow = Task(priority=5, id="slow",
                  func=lambda: time.sleep(10) or 999,
                  max_retries=0, timeout=0.3)
    q3.submit(t_slow)
    result = q3.get_result("slow", timeout=5)
    r.test("timeout: returns error dict",
           lambda: isinstance(result, dict) and "error" in result, True)
    q3.stop()

    # 关闭后拒绝新任务
    q4 = TaskQueue(max_workers=1)
    q4.start()
    q4.stop()
    r.raises("closed: reject submit",
             lambda: q4.submit(Task(priority=1, id="rej", func=lambda: 1)),
             RuntimeError)

    # 重试
    q5 = TaskQueue(max_workers=1)
    q5.start()
    call_count = [0]

    def flaky():
        call_count[0] += 1
        if call_count[0] < 2:
            raise ValueError("fail")
        return "ok"

    t_retry = Task(priority=1, id="retry", func=flaky, max_retries=3)
    q5.submit(t_retry)
    result = q5.get_result("retry", timeout=5)
    r.test("retry: succeeds after retry", lambda: result, "ok")
    q5.stop()

    # 优雅关闭：stop 应等待任务完成
    q6 = TaskQueue(max_workers=1)
    q6.start()

    def quick_task():
        return "done"

    t_quick = Task(priority=1, id="quick", func=quick_task)
    q6.submit(t_quick)
    result = q6.get_result("quick", timeout=5)
    r.test("graceful: result before stop", lambda: result, "done")
    q6.stop()

    return r


# ============================================================
# L3-2 会话管理测试
# ============================================================
def test_l3_2(ns):
    r = TestResult("l3-2-session-manager")
    SessionManager = ns["SessionManager"]

    sm = SessionManager("test-secret-key-12345")

    # 注册
    uid = sm.register("alice", "password123")
    r.test("register: returns id", lambda: isinstance(uid, str), True)
    r.test("register: length", lambda: len(uid) > 0, True)
    r.raises("register: duplicate", lambda: sm.register("alice", "pass"), ValueError)

    # 登录获取 token
    token = sm.login("alice", "password123")
    r.test("login: returns token", lambda: isinstance(token, str) and len(token) > 20, True)

    # 验证 token
    payload = sm.verify_token(token)
    r.test("verify: returns payload", lambda: payload is not None, True)
    r.test("verify: correct username", lambda: payload.username, "alice")
    r.test("verify: has roles", lambda: "user" in payload.roles, True)

    # 错误 token 该被拒绝
    r.test("verify: bad token", lambda: sm.verify_token("bad.token.here"), None)

    # 权限
    r.test("permission: user read", lambda: sm.check_permission(uid, "read"), True)
    r.test("permission: user write", lambda: sm.check_permission(uid, "write"), False)

    # 登出后 token 应失效
    sm.logout(uid)
    r.test("logout: token invalidated",
           lambda: sm.verify_token(token), None)

    # 重新登录后旧 token 应被黑名单化
    sm.register("bob", "pass")
    token1 = sm.login("bob", "pass")
    token2 = sm.login("bob", "pass")
    r.test("re-login: old token invalid",
           lambda: sm.verify_token(token1), None)
    r.test("re-login: new token valid",
           lambda: sm.verify_token(token2) is not None, True)

    # JWT none algorithm 攻击
    fake_token = token2[:token2.index(".")] + "." + token2.split(".")[1] + "." + token2.split(".")[2]
    # 修改 header 为 alg:none 来尝试绕过
    import base64, json as _json
    fake_header = base64.urlsafe_b64encode(
        _json.dumps({"alg": "none", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    attack_token = fake_header + "." + token2.split(".")[1] + "." + token2.split(".")[2]
    r.test("security: JWT none attack rejected",
           lambda: sm.verify_token(attack_token), None)

    # 过期 token
    sm2 = SessionManager("secret", token_ttl=0.01)
    sm2.register("eve", "pw")
    expired = sm2.login("eve", "pw")
    time.sleep(0.05)
    r.test("expired: token rejected",
           lambda: sm2.verify_token(expired), None)

    return r


# ============================================================
# 运行 & 报告
# ============================================================
def run_and_report():
    print("=" * 90)
    print("Harness A/B v2: 独立测试驱动对比实验")
    print("=" * 90)
    print()

    a_results = run_tests("noharness")
    b_results = run_tests("harness")

    print(f"{'Task':<30} {'A-Pass':<8} {'A-Fail':<8} {'A-Rate':<8} {'B-Pass':<8} {'B-Fail':<8} {'B-Rate':<8} {'Delta':<8}")
    print("-" * 90)

    tasks = [
        "l1-1-string-utils", "l1-2-list-utils",
        "l2-1-cache", "l2-2-csv-processor",
        "l3-1-task-queue", "l3-2-session-manager",
    ]

    total_a_pass = 0
    total_a_fail = 0
    total_a_total = 0
    total_b_pass = 0
    total_b_fail = 0
    total_b_total = 0

    for tid in tasks:
        ar = a_results[tid]
        br = b_results[tid]
        ap, af, at, arate = ar.summary()
        bp, bf, bt, brate = br.summary()
        delta = brate - arate
        total_a_pass += ap
        total_a_fail += af
        total_a_total += at
        total_b_pass += bp
        total_b_fail += bf
        total_b_total += bt
        print(f"{tid:<30} {ap:<8} {af:<8} {arate:<7.0f}% {bp:<8} {bf:<8} {brate:<7.0f}% +{delta:+.0f}%")

    total_a_rate = (total_a_pass / total_a_total * 100) if total_a_total else 0
    total_b_rate = (total_b_pass / total_b_total * 100) if total_b_total else 0
    print("-" * 90)
    print(f"{'TOTAL':<30} {total_a_pass:<8} {total_a_fail:<8} {total_a_rate:<7.0f}% {total_b_pass:<8} {total_b_fail:<8} {total_b_rate:<7.0f}% +{total_b_rate - total_a_rate:+.0f}%")
    print("=" * 90)

    # 详细失败日志
    print()
    print("=" * 90)
    print("A 组 (noharness) 失败详情")
    print("=" * 90)
    for tid in tasks:
        ar = a_results[tid]
        if ar.failed > 0:
            print(f"\n--- {tid} ({ar.passed}/{ar.passed+ar.failed} passed) ---")
            for d in ar.details:
                print(d)

    print()
    print("=" * 90)
    print("B 组 (harness) 失败详情")
    print("=" * 90)
    for tid in tasks:
        br = b_results[tid]
        if br.failed > 0:
            print(f"\n--- {tid} ({br.passed}/{br.passed+br.failed} passed) ---")
            for d in br.details:
                print(d)

    # CSV
    csv_rows = []
    for tid in tasks:
        ar = a_results[tid]
        br = b_results[tid]
        ap, af, at, arate = ar.summary()
        bp, bf, bt, brate = br.summary()
        csv_rows.append({
            "task": tid,
            "a_pass": ap, "a_fail": af, "a_total": at, "a_rate": f"{arate:.0f}%",
            "b_pass": bp, "b_fail": bf, "b_total": bt, "b_rate": f"{brate:.0f}%",
            "delta": f"{brate - arate:+.0f}%",
        })

    csv_out = RESULTS / "experiment_v2.csv"
    with open(csv_out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_rows[0].keys())
        w.writeheader()
        w.writerows(csv_rows)

    report = RESULTS / "experiment_v2_report.md"
    report.write_text(f"""# Harness A/B v2: Independent Test-Driven Comparison

## Method
Each task's code from Group A (no-harness) and Group B (harness) is tested against
the **same independent test suite**. Tests are written based on task acceptance criteria,
not on Harness process artifacts.

## Metrics
| Metric | Group A | Group B |
|--------|---------|---------|
| Total Pass | {total_a_pass} | {total_b_pass} |
| Total Fail | {total_a_fail} | {total_b_fail} |
| Pass Rate | {total_a_rate:.0f}% | {total_b_rate:.0f}% |

## Failing Test Details

### Group A (no-harness)
{chr(10).join(f'- **{tid}**: ' + ', '.join([d.strip() for d in a_results[tid].details][:3]) for tid in tasks if a_results[tid].failed > 0)}

### Group B (harness)
{chr(10).join(f'- **{tid}**: ' + ', '.join([d.strip() for d in b_results[tid].details][:3]) for tid in tasks if b_results[tid].failed > 0)}

## Conclusion
The difference in pass rates directly measures the quality gap between
direct model output and debate-refined output.
""", encoding="utf-8")

    print(f"\nCSV: {csv_out}")
    print(f"Report: {report}")
    return total_a_rate, total_b_rate


if __name__ == "__main__":
    run_and_report()
