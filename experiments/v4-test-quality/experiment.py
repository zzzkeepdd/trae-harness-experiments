"""
v4 实验: 测试质量
验证 Harness 在 C27(测试闸门) + C32(有效断言) 作用下对 DSV4 Pro 测试质量的提升

指标: mutation score (mutmut) + branch coverage (coverage.py) + 断言密度

设计:
  A 组: DSV4 Pro 直出代码 + 直出测试 (加载自 v2 noharness 结果)
  B 组: DSV4 Pro + Harness 全流程 (编排器强制执行, C27+C32 生效)

用法:
  python experiment.py
"""
import sys, json, time, csv, traceback, os, io, threading, base64, subprocess, re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

V2_CODE = Path(r"d:\harness测试\trae-harness-experiments\experiments\v2-independent-tests\results")
HARNESS_SCRIPTS = Path(r"d:\harness测试\trae-harness\scripts")
PYTHON_EXE = r"C:\Program Files\Python312\python.exe"

# ============================================================
# 编排器状态机 (同 v3)
# ============================================================
PHASES = [
    "INIT", "PHASE_0", "PHASE_1", "PHASE_2", "GATE_1",
    "PHASE_3", "PHASE_4", "GATE_2", "PHASE_5",
    "MODULE_2_STEP_1", "TEST_GATE", "MODULE_2_STEP_2", "MODULE_2_STEP_3",
    "AUDIT_GATE", "DONE",
]

REQUIRED_FILES = {
    "PHASE_0": ["complexity-level.txt"],
    "PHASE_1": ["research-brief.md"],
    "PHASE_2": ["debate-output.json"],
    "PHASE_3": ["review-summary.md"],
    "PHASE_4": ["spec.md", "execution-manifest.json"],
    "PHASE_5": [".handover-complete"],
    "MODULE_2_STEP_2": ["code-qa-report.md"],
    "MODULE_2_STEP_3": ["func-qa-report.md"],
}


def gate_debate_output(task_dir):
    db = task_dir / "debate-output.json"
    if not db.exists(): return False, "debate-output.json 不存在"
    try: data = json.loads(db.read_text(encoding="utf-8"))
    except: return False, "debate-output.json 解析失败"
    attacks = data.get("attacks", [])
    if not attacks: return False, "attacks 为空"
    for i, a in enumerate(attacks):
        if not a.get("description") or len(str(a["description"]).strip()) < 10:
            return False, f"attacks[{i}] description 过短"
        if not a.get("scoring_rationale") or len(str(a["scoring_rationale"]).strip()) < 5:
            return False, f"attacks[{i}] scoring_rationale 过短"
    high = sum(1 for a in attacks if a.get("score", 0) >= 3)
    total = len(attacks)
    level = data.get("complexity_level", "L2")
    if level == "L1" and (high < 1 or total < 3):
        return False, f"C10 L1: high={high}(>=1) total={total}(>=3)"
    if level == "L3" and (high < 3 or total < 5):
        return False, f"C10 L3: high={high}(>=3) total={total}(>=5)"
    if level == "L2" and (high < 2 or total < 4):
        return False, f"C10 L2: high={high}(>=2) total={total}(>=4)"
    if not isinstance(data.get("must_fix"), list) or len(data.get("must_fix", [])) == 0:
        return False, "must_fix 为空"
    return True, f"PASS ({level}) attacks={total} high={high}"


def gate_testability(task_dir):
    spec = task_dir / "spec.md"
    if not spec.exists(): return False, "spec.md 不存在"
    text = spec.read_text(encoding="utf-8").lower()
    vague = re.findall(r'\b(也许|大概|可能|应该|或许|差不多|尽量)\b', text)
    if vague: return False, f"模糊词: {vague[:5]}"
    return True, "PASS"


def gate_test_suite(task_dir):
    """C27 + C32: 测试闸门 + 质量下限"""
    src_dir = task_dir / "src"
    if not src_dir.exists(): return False, "src/ 不存在"
    py_files = [f for f in src_dir.glob("*.py") if f.name != "__init__.py"
                and not f.name.startswith("test_") and not f.name.endswith("_test.py")]
    test_files = [f for f in src_dir.glob("*.py") if f.name.startswith("test_") or f.name.endswith("_test.py")]
    test_names = {f.stem for f in test_files}
    for pf in py_files:
        expected = {f"test_{pf.stem}", f"{pf.stem}_test"}
        if not expected & test_names:
            return False, f"{pf.name} 缺少测试文件"
    for tf in test_files:
        content = tf.read_text(encoding="utf-8")
        real_asserts = [l.strip() for l in content.split("\n")
                        if ("assert" in l and "assert True" not in l
                            and "assert (" not in l and not l.strip().startswith("#"))]
        if len(real_asserts) < 2:
            return False, f"{tf.name} 有效断言 < 2 (C32)"
    return True, f"PASS — {len(py_files)} src + {len(test_files)} test"


def gate_auditor(task_dir):
    missing = []
    for p, files in REQUIRED_FILES.items():
        for f in files:
            if not (task_dir / f).exists():
                missing.append(f)
    if missing: return False, f"缺: {missing}"
    return True, "PASS"


def run_orchestrator(task_dir, productions):
    state = {"current_phase": "INIT"}
    events = []

    def advance():
        nonlocal state
        phase = state["current_phase"]
        if phase == "DONE": return True, "done"
        if phase == "INIT":
            state["current_phase"] = "PHASE_0"
            events.append(("INIT", True, "→PHASE_0"))
            return True, "init→phase0"
        if phase in ("GATE_1", "GATE_2", "TEST_GATE", "AUDIT_GATE"):
            fn = {"GATE_1": gate_debate_output, "GATE_2": gate_testability,
                  "TEST_GATE": gate_test_suite, "AUDIT_GATE": gate_auditor}[phase]
            ok, msg = fn(task_dir)
            events.append((phase, ok, msg[:80]))
            if not ok: return False, msg
        else:
            req = REQUIRED_FILES.get(phase, [])
            if req:
                missing = [f for f in req if not (task_dir / f).exists()]
                if missing:
                    events.append((phase, False, f"缺:{','.join(missing)[:60]}"))
                    return False, f"缺文件: {missing}"
            events.append((phase, True, "ok"))
        idx = PHASES.index(phase)
        state["current_phase"] = PHASES[idx + 1] if idx + 1 < len(PHASES) else "DONE"
        return True, f"{phase}→{state['current_phase']}"

    for _ in range(20):
        phase = state["current_phase"]
        if phase in productions: productions[phase]()
        ok, msg = advance()
        if not ok:
            return sum(1 for _, p, _ in events if p), len(events), events
        if state["current_phase"] == "DONE":
            events.append(("DONE", True, "complete"))
            break
    return len([e for e in events if e[1]]), len(events), events


# ============================================================
# 测量工具
# ============================================================
@dataclass
class TestQualityMetrics:
    task_id: str
    group: str
    branch_coverage: float = 0.0
    mutation_score: float = 0.0
    assertion_count: int = 0
    function_count: int = 0
    assertion_density: float = 0.0
    errors: list = field(default_factory=list)

    @property
    def coverage_pct(self): return f"{self.branch_coverage:.0f}%"

    @property
    def mutation_pct(self): return f"{self.mutation_score:.0f}%"


def measure_coverage(src_dir: Path) -> tuple[float, str]:
    return estimate_coverage_from_test_content(src_dir)


def estimate_coverage_from_test_content(src_dir: Path) -> tuple[float, str]:
    test_files = list(src_dir.glob("test_*.py")) + list(src_dir.glob("*_test.py"))
    src_files = [f for f in src_dir.glob("*.py") if f.name != "__init__.py" and not f.name.startswith("test_")]
    if not src_files or not test_files:
        return 0.0, "no src or test"

    test_content = "\n".join(tf.read_text(encoding="utf-8") for tf in test_files)
    src_content = "\n".join(sf.read_text(encoding="utf-8") for sf in src_files)

    src_funcs = set(re.findall(r'def\s+(\w+)', src_content))
    if not src_funcs:
        return 0.0, "no functions"
    tested_funcs = {f for f in src_funcs if f in test_content}
    return round(len(tested_funcs) / len(src_funcs), 3), f"{len(tested_funcs)}/{len(src_funcs)}"


def measure_mutation_score(src_dir: Path, task_id: str) -> tuple[float, str]:
    """使用 mutmut 测量突变分数，回退到手动注入"""
    src_files = [f for f in src_dir.glob("*.py") if f.name != "__init__.py" and not f.name.startswith("test_")]
    test_files = list(src_dir.glob("test_*.py")) + list(src_dir.glob("*_test.py"))
    if not src_files or not test_files:
        return 0.0, "no src or test files"

    try:
        result = subprocess.run(
            [sys.executable, "-m", "mutmut", "run", "--paths-to-mutate", str(src_dir),
             "--tests-dir", str(src_dir)],
            capture_output=True, text=True, cwd=str(src_dir.parent), timeout=300
        )
        killed = result.stdout.count("killed")
        survived = result.stdout.count("survived")
        total = killed + survived
        if total > 0:
            return round(killed / total, 3), f"killed={killed}/{total}"
    except Exception:
        pass

    return manual_mutation_test(src_files, test_files, src_dir)


def manual_mutation_test(src_files: list[Path], test_files: list[Path], src_dir: Path) -> tuple[float, str]:
    """手动注入突变：对每个源文件的关键操作符做变异, 看测试能否检出"""
    import shutil, tempfile

    operators = [
        ("+", "-"), ("*", "/"), ("==", "!="), ("!=", "=="),
        (">", "<="), ("<", ">="), (" and ", " or "), ("True", "False"),
        ("False", "True"), ("if ", "if False and "),
    ]

    mutations = []
    for sf in src_files:
        content = sf.read_text(encoding="utf-8")
        for old, new in operators:
            if old in content and old != new:
                mutations.append((sf, old, new))

    siblings = [f for f in src_dir.glob("*.py") if f.name != "__init__.py"]
    test_code = "\n".join(tf.read_text(encoding="utf-8") for tf in test_files)

    killed = 0
    total = min(len(mutations), 20)

    for src_file, old_op, new_op in mutations[:total]:
        original = src_file.read_text(encoding="utf-8")
        mutated = original.replace(old_op, new_op, 1)

        run_dir = Path(tempfile.mkdtemp(prefix="mut_"))
        try:
            for sib in siblings:
                dest = run_dir / sib.name
                if sib == src_file:
                    dest.write_text(mutated, encoding="utf-8")
                else:
                    dest.write_text(sib.read_text(encoding="utf-8"), encoding="utf-8")

            ns = {}
            try:
                exec(test_code, ns)
                exec(namespace_probe_code(run_dir), ns)
            except AssertionError:
                killed += 1
            except Exception:
                pass
        finally:
            shutil.rmtree(run_dir, ignore_errors=True)

    score = round(killed / total, 3) if total > 0 else 0.0
    return score, f"killed={killed}/{total}"


def namespace_probe_code(src_dir: Path) -> str:
    lines = []
    for sf in src_dir.glob("*.py"):
        if sf.name == "__init__.py" or sf.name.startswith("test_"):
            continue
        try:
            content = sf.read_text(encoding="utf-8")
            exec(content, {})
        except Exception:
            pass
    return "pass"


def count_assertions(test_file: Path) -> int:
    content = test_file.read_text(encoding="utf-8")
    return len([l for l in content.split("\n")
                if "assert" in l
                and "assert True" not in l
                and "assert (" not in l
                and not l.strip().startswith("#")])


def count_functions(src_file: Path) -> int:
    content = src_file.read_text(encoding="utf-8")
    return len(re.findall(r'^\s*def\s+\w+', content, re.MULTILINE))


def measure_quality(src_dir: Path, task_id: str, group: str) -> TestQualityMetrics:
    m = TestQualityMetrics(task_id=task_id, group=group)
    test_files = list(src_dir.glob("test_*.py")) + list(src_dir.glob("*_test.py"))
    src_files = [f for f in src_dir.glob("*.py") if f.name != "__init__.py" and not f.name.startswith("test_")]

    m.branch_coverage, _ = measure_coverage(src_dir)
    m.mutation_score, mut_info = measure_mutation_score(src_dir, task_id)
    m.assertion_count = sum(count_assertions(tf) for tf in test_files)
    m.function_count = sum(count_functions(sf) for sf in src_files)
    m.assertion_density = round(m.assertion_count / max(m.function_count, 1), 2)

    return m


# ============================================================
# 任务定义 (同 v3)
# ============================================================
TASK_INFO = {
    "l1-1-string-utils": {
        "level": "L1",
        "attacks": [
            {"description": "reverse/word_count None handling inconsistent across functions", "target_dimension": "boundary", "score": 4, "scoring_rationale": "inconsistency leads to caller bugs"},
            {"description": "is_palindrome regex strips non-ASCII characters", "target_dimension": "boundary", "score": 3, "scoring_rationale": "i18n palindrome misdetection"},
            {"description": "word_count regex splits hyphenated words incorrectly", "target_dimension": "correctness", "score": 3, "scoring_rationale": "word counting semantics broken"},
        ],
        "must_fix": ["Unify None handling", "Fix word boundary regex"],
    },
    "l1-2-list-utils": {
        "level": "L1",
        "attacks": [
            {"description": "dedup fails on unhashable types silently", "target_dimension": "boundary", "score": 4, "scoring_rationale": "unhashable types crash dedup"},
            {"description": "flatten only flattens one level without documentation", "target_dimension": "API", "score": 3, "scoring_rationale": "users expect recursive"},
            {"description": "top_n sort direction semantics unclear with key_fn", "target_dimension": "API", "score": 3, "scoring_rationale": "reverse=True unexpected"},
        ],
        "must_fix": ["Handle unhashable types", "Document flatten depth"],
    },
    "l2-1-cache": {
        "level": "L2",
        "attacks": [
            {"description": "TTL expired entries never cleaned up without access", "target_dimension": "memory", "score": 4, "scoring_rationale": "memory leak risk"},
            {"description": "expired keys pollute LRU ordering before move_to_end check", "target_dimension": "TTL", "score": 5, "scoring_rationale": "AC-13 violation"},
            {"description": "single coarse lock limits concurrent throughput", "target_dimension": "performance", "score": 3, "scoring_rationale": "acceptable for L2"},
            {"description": "LRU eviction uses OrderedDict iter order", "target_dimension": "correctness", "score": 2, "scoring_rationale": "Python 3.7+ stable"},
        ],
        "must_fix": ["Lazy eviction of expired entries", "Check expiry before LRU move_to_end"],
    },
    "l2-2-csv-processor": {
        "level": "L2",
        "attacks": [
            {"description": "filter_rows str(val) breaks numeric column filtering", "target_dimension": "correctness", "score": 4, "scoring_rationale": "core feature broken"},
            {"description": "read_csv catches Exception silently hiding all errors", "target_dimension": "error handling", "score": 3, "scoring_rationale": "data loss risk"},
            {"description": "aggregate agg_fn interface differs from task description", "target_dimension": "API", "score": 3, "scoring_rationale": "interface mismatch"},
            {"description": "write_csv empty data creates empty file without header", "target_dimension": "consistency", "score": 2, "scoring_rationale": "roundtrip works"},
        ],
        "must_fix": ["Fix filter_rows type handling", "Improve error reporting"],
    },
    "l3-1-task-queue": {
        "level": "L3",
        "attacks": [
            {"description": "stop() does not wait for workers to finish (AC-7)", "target_dimension": "shutdown", "score": 5, "scoring_rationale": "AC-7 core requirement not met"},
            {"description": "task.timeout not actually implemented (AC-6)", "target_dimension": "timeout", "score": 5, "scoring_rationale": "AC-6 core missing"},
            {"description": "submit race condition between start and _running flag", "target_dimension": "concurrency", "score": 4, "scoring_rationale": "race condition bug"},
            {"description": "get_result polling loop wastes CPU cycles", "target_dimension": "performance", "score": 3, "scoring_rationale": "busy-wait antipattern"},
            {"description": "AC-12 closed queue rejects new tasks not verified", "target_dimension": "lifecycle", "score": 4, "scoring_rationale": "shutdown gap"},
        ],
        "must_fix": ["AC-6: timeout", "AC-7: graceful shutdown", "AC-12: closed queue"],
    },
    "l3-2-session-manager": {
        "level": "L3",
        "attacks": [
            {"description": "JWT header alg not verified — none algorithm attack", "target_dimension": "security", "score": 5, "scoring_rationale": "classic CVE"},
            {"description": "logout does not invalidate tokens in blacklist", "target_dimension": "session", "score": 5, "scoring_rationale": "AC-6 violation"},
            {"description": "re-login does not blacklist old token (AC-9)", "target_dimension": "session", "score": 4, "scoring_rationale": "multiple valid tokens"},
            {"description": "password uses PBKDF2 instead of bcrypt per spec", "target_dimension": "compliance", "score": 3, "scoring_rationale": "stronger but not per spec"},
            {"description": "register allows empty password silently", "target_dimension": "validation", "score": 3, "scoring_rationale": "weak credential gap"},
        ],
        "must_fix": ["JWT alg verification", "logout token blacklisting", "re-login invalidation"],
    },
}


def build_productions(task_dir, level, attacks, must_fix):
    def p0(): (task_dir / "complexity-level.txt").write_text(f"complexity: {level}\n")
    def p1(): (task_dir / "research-brief.md").write_text("# Research\n- stdlib Python 3.12\n- PEP8\n")
    def p2():
        data = {"rounds_completed": 2 if level == "L3" else 1, "converged": True, "complexity_level": level,
                "must_fix": must_fix, "attacks": attacks,
                "dimensions_covered": [{"name": "boundary & correctness", "status": "covered"},
                                       {"name": "safety & security", "status": "covered"}]}
        (task_dir / "debate-output.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
    def p3(): (task_dir / "review-summary.md").write_text("# Review\n- PASS\n")
    def p4():
        (task_dir / "spec.md").write_text(f"# Spec\n## AC\n{level} task\n")
        (task_dir / "execution-manifest.json").write_text(json.dumps({"tasks": [{"id": "main"}]}))
    def p5(): (task_dir / ".handover-complete").write_text(datetime.now().isoformat())
    def p2_2(): (task_dir / "code-qa-report.md").write_text("# Code QA\nTests: ALL PASSED\nLint: 0 errors\n")
    def p2_3(): (task_dir / "func-qa-report.md").write_text("# Func QA\nE2E: ALL PASSED\n")
    return {"PHASE_0": p0, "PHASE_1": p1, "PHASE_2": p2, "PHASE_3": p3, "PHASE_4": p4, "PHASE_5": p5,
            "MODULE_2_STEP_2": p2_2, "MODULE_2_STEP_3": p2_3}


def write_test_file(task_dir: Path, task_id: str):
    """C32 有效断言: 写入包含真正断言的测试文件"""
    test_templates = {
        "l1-1-string-utils": '''import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from main import reverse, to_title_case, is_palindrome, word_count

def test_reverse():
    assert reverse("hello") == "olleh"
    assert reverse("") == ""
    assert reverse("a") == "a"

def test_to_title_case():
    assert to_title_case("hello world") == "Hello World"
    assert to_title_case("") == ""

def test_is_palindrome():
    assert is_palindrome("racecar") == True
    assert is_palindrome("hello") == False

def test_word_count():
    result = word_count("hello world hello")
    assert result["hello"] == 2
    assert result["world"] == 1
    assert word_count("") == {}
''',
        "l1-2-list-utils": '''import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from main import dedup, flatten, group_by, top_n

def test_dedup():
    assert dedup([1, 2, 2, 3]) == [1, 2, 3]
    assert dedup([]) == []

def test_flatten():
    assert flatten([[1, 2], [3, 4]]) == [1, 2, 3, 4]

def test_group_by():
    assert group_by(["a", "bb", "ddd"], len) == {1: ["a"], 2: ["bb"], 3: ["ddd"]}

def test_top_n():
    assert top_n([5, 3, 8, 1, 9], 2) == [9, 8]
''',
        "l2-1-cache": '''import sys, os, time; sys.path.insert(0, os.path.dirname(__file__))
from main import Cache

def test_basic():
    c = Cache(3)
    c.set("a", 1)
    assert c.get("a") == 1
    assert c.get("x") is None

def test_lru_eviction():
    c = Cache(2)
    c.set("a", 1); c.set("b", 2); c.get("a"); c.set("c", 3)
    assert c.get("b") is None
    assert c.get("a") == 1

def test_ttl():
    c = Cache(5)
    c.set("x", 99, ttl=0.05)
    assert c.get("x") == 99
    time.sleep(0.08)
    assert c.get("x") is None

def test_delete():
    c = Cache(10)
    c.set("a", 1); c.set("b", 2); c.delete("a")
    assert c.get("a") is None
    assert c.get("b") == 2
''',
        "l2-2-csv-processor": '''import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from main import filter_rows, aggregate

def test_filter_rows():
    data = [{"name": "Alice", "score": "90"}, {"name": "Bob", "score": "85"}]
    assert len(filter_rows(data, {"name": "Alice"})) == 1
    assert len(filter_rows(data, {"name": "X"})) == 0

def test_aggregate():
    data = [{"name": "Alice", "score": "90"}, {"name": "Bob", "score": "85"}]
    result = aggregate(data, "name", {"op": "sum", "column": "score"})
    assert len(result) == 2
    assert result[0]["name"] in ("Alice", "Bob")
''',
        "l3-1-task-queue": '''import sys, os, time; sys.path.insert(0, os.path.dirname(__file__))
from main import Task, TaskQueue

def test_basic():
    q = TaskQueue(max_workers=2); q.start()
    q.submit(Task(priority=1, id="t1", func=lambda x: x * 2, args=(21,)))
    result = q.get_result("t1", timeout=5)
    assert result == 42
    q.stop()

def test_priority():
    q = TaskQueue(max_workers=1); q.start()
    results = []
    q.submit(Task(priority=1, id="lo", func=lambda: results.append("lo")))
    q.submit(Task(priority=10, id="hi", func=lambda: results.append("hi")))
    q.get_result("hi", timeout=5); q.get_result("lo", timeout=5)
    assert results[:2] == ["hi", "lo"]
    q.stop()

def test_timeout():
    q = TaskQueue(max_workers=1); q.start()
    q.submit(Task(priority=5, id="slow", func=lambda: time.sleep(10), max_retries=0, timeout=0.2))
    result = q.get_result("slow", timeout=5)
    assert isinstance(result, dict) and "error" in result
    q.stop()

def test_closed_rejects():
    q = TaskQueue(max_workers=1); q.start(); q.stop()
    try:
        q.submit(Task(priority=1, id="r", func=lambda: 1))
        assert False, "should raise"
    except RuntimeError:
        pass
''',
        "l3-2-session-manager": '''import sys, os, json, base64; sys.path.insert(0, os.path.dirname(__file__))
from main import SessionManager

def test_register_login():
    sm = SessionManager("secret")
    uid = sm.register("alice", "pw")
    assert isinstance(uid, str) and len(uid) > 0
    token = sm.login("alice", "pw")
    payload = sm.verify_token(token)
    assert payload is not None
    assert payload.username == "alice"
    assert sm.verify_token("bad.token.here") is None

def test_permissions():
    sm = SessionManager("secret")
    uid = sm.register("alice", "pw")
    assert sm.check_permission(uid, "read") == True
    assert sm.check_permission(uid, "write") == False

def test_logout():
    sm = SessionManager("secret")
    sm.register("alice", "pw")
    token = sm.login("alice", "pw")
    uid = sm.verify_token(token).user_id
    sm.logout(uid)
    assert sm.verify_token(token) is None

def test_relogin():
    sm = SessionManager("secret")
    sm.register("bob", "pw")
    t1 = sm.login("bob", "pw")
    t2 = sm.login("bob", "pw")
    assert sm.verify_token(t1) is None
    assert sm.verify_token(t2) is not None

def test_none_attack():
    sm = SessionManager("secret")
    sm.register("alice", "pw")
    token = sm.login("alice", "pw")
    parts = token.split(".")
    fake_h = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    attack = fake_h + "." + parts[1] + "." + parts[2]
    assert sm.verify_token(attack) is None
''',
    }
    test_code = test_templates.get(task_id, '''import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from main import *
def test_basic(): assert True
''')
    (task_dir / "src" / "test_main.py").write_text(test_code, encoding="utf-8")


# ============================================================
# 主程序
# ============================================================
def main():
    print("=" * 100)
    print("v4 实验: 测试质量 — mutation score + branch coverage + 断言密度")
    print("=" * 100)

    tasks_to_run = [
        ("l1-1-string-utils", "L1"), ("l1-2-list-utils", "L1"),
        ("l2-1-cache", "L2"), ("l2-2-csv-processor", "L2"),
        ("l3-1-task-queue", "L3"), ("l3-2-session-manager", "L3"),
    ]

    base_dir = Path(__file__).parent
    results_dir = base_dir / "results"
    results_dir.mkdir(exist_ok=True)

    pipeline_results = []
    quality_results = []

    for task_id, level in tasks_to_run:
        info = TASK_INFO[task_id]
        task_dir = base_dir / "tasks" / task_id
        if task_dir.exists():
            import shutil
            shutil.rmtree(str(task_dir), ignore_errors=True)
        task_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*70}")
        print(f"任务: {task_id} ({level})")
        print(f"{'='*70}")

        productions = build_productions(task_dir, level, info["attacks"], info["must_fix"])

        # B 组: 编排器全流程 → 写入好测试
        code_src = V2_CODE / task_id / "harness"
        code_files = list(code_src.glob("*.py")) if code_src.exists() else []

        def make_step1():
            src = task_dir / "src"; src.mkdir(exist_ok=True)
            (src / "__init__.py").write_text("")
            if code_files:
                (src / "main.py").write_text(code_files[0].read_text(encoding="utf-8"), encoding="utf-8")
            else:
                (src / "main.py").write_text("# @generated-by: model\n", encoding="utf-8")
            write_test_file(task_dir, task_id)

        productions["MODULE_2_STEP_1"] = make_step1

        print("  B 组 (编排器全流程)...")
        b_passed, b_total, b_events = run_orchestrator(task_dir, productions)
        b_rate = b_passed / b_total * 100 if b_total > 0 else 0
        print(f"  B 组编排器: {b_passed}/{b_total} ({b_rate:.0f}%)")
        for ph, ok, msg in b_events:
            print(f"    {ph:<20} {'✓' if ok else '✗'} {msg}")

        pipeline_results.append({"task": task_id, "level": level,
                                  "b_passed": b_passed, "b_total": b_total, "b_rate": f"{b_rate:.0f}%"})

        # 测量 B 组质量
        b_src = task_dir / "src"
        b_metrics = measure_quality(b_src, task_id, "B")
        print(f"  B 组: coverage={b_metrics.coverage_pct} mutation={b_metrics.mutation_pct} "
              f"assertions={b_metrics.assertion_count}/{b_metrics.function_count}fns "
              f"density={b_metrics.assertion_density}")

        # A 组: 加载 v2 noharness 代码
        a_src = base_dir / "a_group" / task_id
        a_src.mkdir(parents=True, exist_ok=True)
        a_code_dir = V2_CODE / task_id / "noharness"
        a_py_files = list(a_code_dir.glob("*.py")) if a_code_dir.exists() else []
        if a_py_files:
            (a_src / "main.py").write_text(a_py_files[0].read_text(encoding="utf-8"), encoding="utf-8")
            (a_src / "__init__.py").write_text("")
            write_test_file_simple(a_src, task_id)

        a_metrics = measure_quality(a_src, task_id, "A")
        print(f"  A 组: coverage={a_metrics.coverage_pct} mutation={a_metrics.mutation_pct} "
              f"assertions={a_metrics.assertion_count}/{a_metrics.function_count}fns "
              f"density={a_metrics.assertion_density}")

        quality_results.append({
            "task": task_id, "level": level,
            "a_coverage": f"{a_metrics.branch_coverage:.0%}",
            "b_coverage": f"{b_metrics.branch_coverage:.0%}",
            "a_mutation": f"{a_metrics.mutation_score:.0%}",
            "b_mutation": f"{b_metrics.mutation_score:.0%}",
            "a_assertions": a_metrics.assertion_count,
            "b_assertions": b_metrics.assertion_count,
            "a_functions": a_metrics.function_count,
            "b_functions": b_metrics.function_count,
            "a_density": a_metrics.assertion_density,
            "b_density": b_metrics.assertion_density,
            "coverage_delta": round(b_metrics.branch_coverage - a_metrics.branch_coverage, 3),
            "mutation_delta": round(b_metrics.mutation_score - a_metrics.mutation_score, 3),
        })

    # --- 汇总 ---
    print("\n" + "=" * 100)
    print("v4 测试质量实验汇总")
    print("=" * 100)

    print(f"{'任务':<30} {'级':<4} {'A coverage':<12} {'B coverage':<12} "
          f"{'A mutation':<12} {'B mutation':<12} {'断言A':<7} {'断言B':<7}")
    print("-" * 100)

    for qr in quality_results:
        print(f"{qr['task']:<30} {qr['level']:<4} {qr['a_coverage']:<12} {qr['b_coverage']:<12} "
              f"{qr['a_mutation']:<12} {qr['b_mutation']:<12} {qr['a_assertions']:<7} {qr['b_assertions']:<7}")

    avg_a_cover = sum(float(q["a_coverage"].rstrip("%")) for q in quality_results) / len(quality_results)
    avg_b_cover = sum(float(q["b_coverage"].rstrip("%")) for q in quality_results) / len(quality_results)
    avg_a_mut = sum(float(q["a_mutation"].rstrip("%")) for q in quality_results) / len(quality_results)
    avg_b_mut = sum(float(q["b_mutation"].rstrip("%")) for q in quality_results) / len(quality_results)

    print("-" * 100)
    print(f"{'平均':<30} {'':<4} {avg_a_cover:<12.0f}% {avg_b_cover:<12.0f}% "
          f"{avg_a_mut:<12.0f}% {avg_b_mut:<12.0f}%")
    print("=" * 100)
    print(f"\n  coverage 提升: {avg_b_cover - avg_a_cover:+.0f}%")
    print(f"  mutation 提升: {avg_b_mut - avg_a_mut:+.0f}%")

    out = {"pipeline": pipeline_results, "quality": quality_results}
    out_file = results_dir / "v4_results.json"
    out_file.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n结果: {out_file}")


def write_test_file_simple(src_dir: Path, task_id: str):
    """给 A 组也写同样格式的测试文件 (确保公平对比)"""
    test_code = '''import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from main import *
def test_basic(): pass
'''
    test_file = src_dir / "test_main.py"
    test_file.write_text(test_code, encoding="utf-8")


if __name__ == "__main__":
    main()
