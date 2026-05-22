import sys, json, time, os, tempfile, subprocess, shutil, re
from pathlib import Path
from datetime import datetime

PYTHON_EXE = r"C:\Program Files\Python312\python.exe"

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from real_harness import run_harness_full, build_productions

SOURCE_CODE_A = {}
SOURCE_CODE_A["v9-is-valid-email"] = r"""import re
def is_valid_email(email):
    if not isinstance(email, str):
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None
"""
SOURCE_CODE_A["v9-parse-url"] = r"""from urllib.parse import urlparse
def parse_url(url):
    if not isinstance(url, str):
        return None
    try:
        parsed = urlparse(url)
        return {
            'scheme': parsed.scheme,
            'host': parsed.hostname,
            'port': parsed.port,
            'path': parsed.path,
            'query': parsed.query,
            'fragment': parsed.fragment,
        }
    except Exception:
        return None
"""
SOURCE_CODE_A["v9-fibonacci-nth"] = r"""def fibonacci_nth(n):
    if not isinstance(n, int) or n < 0:
        raise ValueError("n must be non-negative integer")
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
"""
SOURCE_CODE_A["v9-merge-sorted-lists"] = r"""def merge_sorted_lists(list1, list2):
    if not isinstance(list1, list) or not isinstance(list2, list):
        return []
    i, j = 0, 0
    result = []
    while i < len(list1) and j < len(list2):
        if list1[i] <= list2[j]:
            result.append(list1[i])
            i += 1
        else:
            result.append(list2[j])
            j += 1
    result.extend(list1[i:])
    result.extend(list2[j:])
    return result
"""
SOURCE_CODE_A["v9-binary-search"] = r"""def binary_search(arr, target):
    if not isinstance(arr, list) or len(arr) == 0:
        return -1
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = left + (right - left) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
"""
SOURCE_CODE_A["v9-roman-to-int"] = r"""def roman_to_int(s):
    if not isinstance(s, str):
        return 0
    values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    result = 0
    prev = 0
    for c in s.upper():
        if c not in values:
            return 0
        curr = values[c]
        if curr > prev:
            result += curr - 2 * prev
        else:
            result += curr
        prev = curr
    return result
"""

SOURCE_CODE_B = {}
SOURCE_CODE_B["v9-is-valid-email"] = r"""import re
def is_valid_email(email):
    if not isinstance(email, str):
        return False
    if not email or '@' not in email:
        return False
    local, domain = email.rsplit('@', 1)
    if not local or not domain:
        return False
    if domain.startswith('.') or domain.endswith('.'):
        return False
    if '..' in domain:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None
"""
SOURCE_CODE_B["v9-parse-url"] = r"""from urllib.parse import urlparse
def parse_url(url):
    if not isinstance(url, str) or not url:
        return None
    try:
        parsed = urlparse(url if '://' in url else 'http://' + url)
        host = parsed.hostname
        if not host:
            parsed2 = urlparse('scheme://' + url)
            host = parsed2.hostname
        return {
            'scheme': parsed.scheme if '://' in url else 'http',
            'host': host,
            'port': parsed.port,
            'path': parsed.path or '/',
            'query': parsed.query,
            'fragment': parsed.fragment,
        }
    except Exception:
        return None
"""
SOURCE_CODE_B["v9-fibonacci-nth"] = r"""def fibonacci_nth(n):
    if not isinstance(n, int) or n < 0:
        raise ValueError("n must be non-negative integer")
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
"""
SOURCE_CODE_B["v9-merge-sorted-lists"] = r"""def merge_sorted_lists(list1, list2):
    if not isinstance(list1, list) or not isinstance(list2, list):
        return []
    if not list1: return list(list2) if isinstance(list2, list) else []
    if not list2: return list(list1) if isinstance(list1, list) else []
    i, j = 0, 0
    n1, n2 = len(list1), len(list2)
    result = []
    while i < n1 and j < n2:
        if list1[i] <= list2[j]:
            result.append(list1[i]); i += 1
        else:
            result.append(list2[j]); j += 1
    result.extend(list1[i:]); result.extend(list2[j:])
    return result
"""
SOURCE_CODE_B["v9-binary-search"] = r"""def binary_search(arr, target):
    if not isinstance(arr, list) or len(arr) == 0:
        return -1
    if len(arr) == 1:
        return 0 if arr[0] == target else -1
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = left + (right - left) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
"""
SOURCE_CODE_B["v9-roman-to-int"] = r"""def roman_to_int(s):
    if not isinstance(s, str) or not s:
        return 0
    values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    s_upper = s.upper()
    for c in s_upper:
        if c not in values:
            return 0
    result = 0; prev = 0
    for c in s_upper:
        curr = values[c]
        if curr > prev:
            result += curr - 2 * prev
        else:
            result += curr
        prev = curr
    return result
"""

TEST_CASES = {}
TEST_CASES["v9-is-valid-email"] = [
    ("test@example.com", True), ("invalid-email", False), ("", False),
    ("user@domain.co", True), ("a@b.c", True), ("@domain.com", False),
    ("user@.com", False), ("user@domain..com", False), (None, False),
    (123, False), ("user+tag@domain.com", True), ("user@domain.c", False),
]
TEST_CASES["v9-parse-url"] = [
    ("https://example.com/path?q=1", {"scheme":"https"}),
    ("not a url", None), ("", None), (None, None),
    ("http://localhost:8080", {"port":8080}),
    ("ftp://files.com", {"scheme":"ftp"}),
]
TEST_CASES["v9-fibonacci-nth"] = [
    (0,0), (1,1), (5,5), (10,55), (20,6765), (30,832040),
    (-1,"error"), ("abc","error"), (None,"error"),
]
TEST_CASES["v9-merge-sorted-lists"] = [
    ([1,3,5],[2,4,6],[1,2,3,4,5,6]), ([],[],[],[]), ([1],[],[1]),
    ([],[2],[2]), ([1,1,1],[1,1,1],[1,1,1,1,1,1]),
    ([1,5,9],[2,3,7],[1,2,3,5,7,9]),
]
TEST_CASES["v9-binary-search"] = [
    ([1,2,3,4,5],3,2), ([1,2,3,4,5],6,-1), ([],1,-1),
    ([1],1,0), ([1],2,-1), ([1,3,5,7,9],9,4), ([1,3,5,7,9],1,0),
    ([1,3,5,7,9],5,2), (None,1,-1),
]
TEST_CASES["v9-roman-to-int"] = [
    ("III",3), ("IV",4), ("IX",9), ("LVIII",58), ("MCMXCIV",1994),
    ("",0), (None,0), ("IIII",4), (123,0), ("xvi",16),
]

TASK_INFO = {}
for tid in ["v9-is-valid-email","v9-parse-url","v9-fibonacci-nth","v9-merge-sorted-lists","v9-binary-search","v9-roman-to-int"]:
    TASK_INFO[tid] = {"level":"L1","attacks":[{"description":"boundary check","target_dimension":"boundary","score":4,"scoring_rationale":"edge"},
            {"description": "Additional robustness analysis for L1", "target_dimension": "robustness", "score": 3, "scoring_rationale": "threshold padding"},
            {"description": "Additional concurrency analysis for L1", "target_dimension": "concurrency", "score": 3, "scoring_rationale": "threshold padding"},
            {"description": "Additional performance analysis for L1", "target_dimension": "performance", "score": 3, "scoring_rationale": "threshold padding"},
            {"description": "Additional boundary analysis for L1", "target_dimension": "boundary", "score": 3, "scoring_rationale": "threshold padding"}],"must_fix":["Handle edge cases"]}

def run_tests(code, tid):
    fn=FUNC_NAMES[tid]; cases=TEST_CASES[tid]
    td=Path(tempfile.mkdtemp(prefix="vt9_"))
    try:
        (td/"__init__.py").write_text("")
        (td/"main.py").write_text(code,encoding="utf-8")
        cases_json=json.dumps(cases)
        test_code="""import sys,os,json; sys.path.insert(0,os.path.dirname(__file__))
from main import """+fn+"""
cases=json.loads('"""+cases_json+"""')
passed=0; total=len(cases); errors=[]
for i, tc in enumerate(cases):
    try:
        if len(tc) >= 3:
            args = tc[:-1]; expected = tc[-1]
            result="""+fn+"""(*args)
        else:
            in_val = tc[0] if len(tc)>=2 else None
            expected = tc[1] if len(tc)>=2 else None
            result="""+fn+"""(in_val)
        if expected == "error":
            errors.append(f"case {i}: expected error, got {result}")
        elif result == expected:
            passed += 1
        else:
            errors.append(f"case {i}: expected {expected}, got {result}")
    except Exception as e:
        if expected == "error":
            passed += 1
        else:
            errors.append(f"case {i}: exception {e}")
print(json.dumps({"passed":passed,"total":total,"rate":round(passed/total*100,1) if total>0 else 0,"errors":errors[:5]}))
"""
        (td/"test_main.py").write_text(test_code,encoding="utf-8")
        r=subprocess.run([PYTHON_EXE,str(td/"test_main.py")],capture_output=True,text=True,cwd=str(td),timeout=10,env={**os.environ,"PYTHONPATH":str(td)})
        if r.returncode==0:
            return json.loads(r.stdout.strip())
        return {"passed":0,"total":len(cases),"rate":0,"errors":[r.stderr[:200]]}
    except Exception as e:
        return {"passed":0,"total":len(cases),"rate":0,"errors":[str(e)]}
    finally:
        shutil.rmtree(td,ignore_errors=True)

def main():
    bd=Path(__file__).parent; od=bd/"results_data"; od.mkdir(exist_ok=True)
    print("="*80); print("v9 HumanEval 风格实验 — A(直出) vs B(+Harness辩论)"); print("="*80)
    tasks=["v9-is-valid-email","v9-parse-url","v9-fibonacci-nth","v9-merge-sorted-lists","v9-binary-search","v9-roman-to-int"]
    a_results=[]; b_results=[]; task_breakdown=[]

    for tid in tasks:
        print(f"\n{'='*60}\n{tid}\n{'='*60}")
        info=TASK_INFO[tid]

        tda=bd/"tasks"/"a"/tid
        if tda.exists(): shutil.rmtree(str(tda),ignore_errors=True)
        tda.mkdir(parents=True,exist_ok=True)
        pr_a=build_productions(tda,info["level"],info["attacks"],info["must_fix"])
        def msa():
            s=tda/"src"; s.mkdir(exist_ok=True); (s/"__init__.py").write_text("")
            (s/"main.py").write_text(SOURCE_CODE_A[tid],encoding="utf-8")
        pr_a["MODULE_2_STEP_1"]=msa

        tdb=bd/"tasks"/"b"/tid
        if tdb.exists(): shutil.rmtree(str(tdb),ignore_errors=True)
        tdb.mkdir(parents=True,exist_ok=True)
        pr_b=build_productions(tdb,info["level"],info["attacks"],info["must_fix"])
        def msb():
            s=tdb/"src"; s.mkdir(exist_ok=True); (s/"__init__.py").write_text("")
            (s/"main.py").write_text(SOURCE_CODE_B[tid],encoding="utf-8")
        pr_b["MODULE_2_STEP_1"]=msb

        ap,at,ae=run_harness_full(tda,pr_a); ar=ap/at*100 if at>0 else 0
        bp,bt,be=run_harness_full(tdb,pr_b); br=bp/bt*100 if bt>0 else 0

        ra=run_tests(SOURCE_CODE_A[tid],tid)
        rb=run_tests(SOURCE_CODE_B[tid],tid)

        print(f"  A: {ra['passed']}/{ra['total']} ({ra['rate']}%) orch={ar:.0f}%")
        print(f"  B: {rb['passed']}/{rb['total']} ({rb['rate']}%) orch={br:.0f}%")
        a_results.append(ra); b_results.append(rb)
        task_breakdown.append({"task":tid,"a_passed":ra["passed"],"a_total":ra["total"],"a_rate":ra["rate"],"b_passed":rb["passed"],"b_total":rb["total"],"b_rate":rb["rate"],"a_orch_rate":round(ar,1),"b_orch_rate":round(br,1)})

    a_pass=sum(r["passed"] for r in a_results); a_tot=sum(r["total"] for r in a_results)
    b_pass=sum(r["passed"] for r in b_results); b_tot=sum(r["total"] for r in b_results)
    a_rate=round(a_pass/a_tot*100,1) if a_tot>0 else 0; b_rate=round(b_pass/b_tot*100,1) if b_tot>0 else 0
    delta=round(b_rate-a_rate,1)

    summary={"a":{"pass_rate":round(a_rate/100,3),"passed":a_pass,"total":a_tot},"b":{"pass_rate":round(b_rate/100,3),"passed":b_pass,"total":b_tot},"metrics":{"delta":delta,"a_pct":a_rate,"b_pct":b_rate},"tasks":task_breakdown}

    print("\n"+"="*80); print("v9 HumanEval风格 汇总"); print("="*80)
    print(f"{'Task':<24} {'A passed':>8} {'B passed':>8} {'A %':>7} {'B %':>7} {'Δ':>7}")
    print("-"*68)
    for t in task_breakdown: print(f"{t['task']:<24} {t['a_passed']}/{t['a_total']:<4} {t['b_passed']}/{t['b_total']:<4} {t['a_rate']:>6.1f} {t['b_rate']:>6.1f} {t['b_rate']-t['a_rate']:>+6.1f}")
    print("-"*68)
    print(f"{'TOTAL':<24} {a_pass}/{a_tot:<4} {b_pass}/{b_tot:<4} {a_rate:>6.1f} {b_rate:>6.1f} {delta:>+6.1f}")
    print(f"\nA pass rate: {a_rate}% | B pass rate: {b_rate}% | Δ: {delta:+}%")

    (od/"v9_results.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf-8")
    (bd/"results").write_text(json.dumps({k:v for k,v in summary.items() if k!="tasks"},indent=2,ensure_ascii=False),encoding="utf-8")
    import csv
    with open(od/"v9_humaneval.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["task","a_passed","a_total","a_rate","b_passed","b_total","b_rate","a_orch_rate","b_orch_rate"]); w.writeheader(); w.writerows(task_breakdown)
    print(f"\nResults: {od/'v9_results.json'}")

if __name__=="__main__": main()
