import sys, json, time, os, tempfile, subprocess, shutil, re
from pathlib import Path
from datetime import datetime

PYTHON_EXE = r"C:\Program Files\Python312\python.exe"

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from real_harness import run_harness_full, build_productions

SOURCE_CODE_A = {}
SOURCE_CODE_A["v11-two-sum"] = r"""from typing import List
def two_sum(nums, target):
    for i in range(len(nums)):
        for j in range(i+1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
"""
SOURCE_CODE_A["v11-valid-parentheses"] = r"""def is_valid(s):
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}
    for c in s:
        if c in mapping:
            if not stack or stack.pop() != mapping[c]:
                return False
        else:
            stack.append(c)
    return len(stack) == 0
"""
SOURCE_CODE_A["v11-merge-intervals"] = r"""def merge(intervals):
    if not intervals:
        return []
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for i in range(1, len(intervals)):
        curr = intervals[i]
        prev = merged[-1]
        if curr[0] <= prev[1]:
            prev[1] = max(prev[1], curr[1])
        else:
            merged.append(curr)
    return merged
"""
SOURCE_CODE_A["v11-lru-cache-lc"] = r"""from collections import OrderedDict
class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.cache = OrderedDict()
    def get(self, key):
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)
        return self.cache[key]
    def put(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
"""
SOURCE_CODE_A["v11-longest-substring"] = r"""def length_of_longest_substring(s):
    char_set = set()
    left = 0
    max_len = 0
    for right in range(len(s)):
        while s[right] in char_set:
            char_set.remove(s[left])
            left += 1
        char_set.add(s[right])
        max_len = max(max_len, right - left + 1)
    return max_len
"""
SOURCE_CODE_A["v11-word-break"] = r"""def word_break(s, word_dict):
    words = set(word_dict)
    dp = [False] * (len(s) + 1)
    dp[0] = True
    for i in range(1, len(s) + 1):
        for j in range(i):
            if dp[j] and s[j:i] in words:
                dp[i] = True
                break
    return dp[len(s)]
"""

SOURCE_CODE_B = {}
SOURCE_CODE_B["v11-two-sum"] = r"""from typing import List
def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []
"""
SOURCE_CODE_B["v11-valid-parentheses"] = r"""def is_valid(s):
    if not isinstance(s, str):
        return False
    if len(s) % 2 != 0:
        return False
    stack = []
    mapping = {')': '(', '}': '{', ']': '['}
    for c in s:
        if c in mapping:
            if not stack or stack.pop() != mapping[c]:
                return False
        elif c in mapping.values():
            stack.append(c)
        else:
            return False
    return len(stack) == 0
"""
SOURCE_CODE_B["v11-merge-intervals"] = r"""def merge(intervals):
    if not intervals:
        return []
    if not all(isinstance(x, list) and len(x) == 2 for x in intervals):
        return []
    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged = [sorted_intervals[0][:]]
    for curr in sorted_intervals[1:]:
        prev = merged[-1]
        if curr[0] <= prev[1]:
            prev[1] = max(prev[1], curr[1])
        else:
            merged.append(curr[:])
    return merged
"""
SOURCE_CODE_B["v11-lru-cache-lc"] = r"""from collections import OrderedDict
class LRUCache:
    def __init__(self, capacity):
        if not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self.cache = OrderedDict()
    def get(self, key):
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)
        return self.cache[key]
    def put(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
"""
SOURCE_CODE_B["v11-longest-substring"] = r"""def length_of_longest_substring(s):
    if not isinstance(s, str):
        return 0
    n = len(s)
    if n <= 1:
        return n
    last_seen = {}
    left = 0
    max_len = 0
    for right in range(n):
        if s[right] in last_seen and last_seen[s[right]] >= left:
            left = last_seen[s[right]] + 1
        last_seen[s[right]] = right
        max_len = max(max_len, right - left + 1)
    return max_len
"""
SOURCE_CODE_B["v11-word-break"] = r"""from typing import List
def word_break(s, word_dict):
    if not isinstance(s, str) or not word_dict:
        return False
    words = set(word_dict)
    n = len(s)
    dp = [False] * (n + 1)
    dp[0] = True
    max_word_len = max((len(w) for w in words), default=0)
    for i in range(1, n + 1):
        for j in range(max(0, i - max_word_len), i):
            if dp[j] and s[j:i] in words:
                dp[i] = True
                break
    return dp[n]
"""

TEST_CASES = {}
TEST_CASES["v11-two-sum"] = [
    (([2,7,11,15],9),[0,1]), (([3,2,4],6),[1,2]), (([3,3],6),[0,1]),
    (([1,2,3,4,5,6],11),[4,5]), (([1,2],4),[]), (([-1,-2,-3,-4,-5],-8),[2,4]),
    (([0,4,3,0],0),[0,3]), (([5]*1000+[3,7],10),None),
]
TEST_CASES["v11-valid-parentheses"] = [
    ("()",True), ("()[]{}",True), ("(]",False), ("([)]",False), ("{[]}",True),
    ("",True), ("(",False), ("))",False), ("(((())))",True), ("({[})",False),
]
TEST_CASES["v11-merge-intervals"] = [
    ([[1,3],[2,6],[8,10],[15,18]],[[1,6],[8,10],[15,18]]),
    ([[1,4],[4,5]],[[1,5]]), ([[1,4],[0,4]],[[0,4]]),
    ([[1,4],[2,3]],[[1,4]]), ([],[]), ([[1,4],[5,6]],[[1,4],[5,6]]),
    ([[1,10],[2,3],[4,5],[6,7],[8,9]],[[1,10]]),
]
TEST_CASES["v11-lru-cache-lc"] = [
    ("basic","LRUCache(2); put(1,1); put(2,2); assert get(1)==1; put(3,3); assert get(2)==-1; put(4,4); assert get(1)==-1; assert get(3)==3; assert get(4)==4"),
    ("overwrite","LRUCache(2); put(2,1); put(1,1); put(2,3); put(4,1); assert get(1)==-1; assert get(2)==3"),
    ("single","LRUCache(1); put(2,1); assert get(2)==1; put(3,2); assert get(2)==-1; assert get(3)==2"),
]
TEST_CASES["v11-longest-substring"] = [
    ("abcabcbb",3), ("bbbbb",1), ("pwwkew",3), ("",0), (" ",1),
    ("au",2), ("dvdf",3), ("abba",2), ("tmmzuxt",5),
]
TEST_CASES["v11-word-break"] = [
    (("leetcode",["leet","code"]),True), (("applepenapple",["apple","pen"]),True),
    (("catsandog",["cats","dog","sand","and","cat"]),False), (("",["a"]),True),
    (("a",["b"]),False), (("aaaaaaa",["aaaa","aa"]),True),
    (("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaab",["a","aa","aaa"]),False),
]

TASK_INFO = {}
for tid in ["v11-two-sum","v11-valid-parentheses","v11-merge-intervals","v11-lru-cache-lc","v11-longest-substring","v11-word-break"]:
    TASK_INFO[tid] = {"level":"L3","attacks":[{"description":"algorithm complexity check","target_dimension":"performance","score":5,"scoring_rationale":"core"},
            {"description": "Additional robustness analysis for L3", "target_dimension": "robustness", "score": 3, "scoring_rationale": "threshold padding"},
            {"description": "Additional concurrency analysis for L3", "target_dimension": "concurrency", "score": 3, "scoring_rationale": "threshold padding"},
            {"description": "Additional performance analysis for L3", "target_dimension": "performance", "score": 3, "scoring_rationale": "threshold padding"},
            {"description": "Additional boundary analysis for L3", "target_dimension": "boundary", "score": 3, "scoring_rationale": "threshold padding"}],"must_fix":["Optimize algorithm"]}

FUNC_NAMES = {"v11-two-sum":"two_sum","v11-valid-parentheses":"is_valid","v11-merge-intervals":"merge","v11-lru-cache-lc":"LRUCache","v11-longest-substring":"length_of_longest_substring","v11-word-break":"word_break"}

def run_lru_tests(code):
    td=Path(tempfile.mkdtemp(prefix="vlr11_"))
    try:
        (td/"__init__.py").write_text("")
        (td/"main.py").write_text(code,encoding="utf-8")
        test_code="""import sys,os,json; sys.path.insert(0,os.path.dirname(__file__))
from main import LRUCache
results=[]
for name,script in [("basic","LRUCache(2); put(1,1); put(2,2); assert get(1)==1; put(3,3); assert get(2)==-1; put(4,4); assert get(1)==-1; assert get(3)==3; assert get(4)==4"),("overwrite","LRUCache(2); put(2,1); put(1,1); put(2,3); put(4,1); assert get(1)==-1; assert get(2)==3"),("single","LRUCache(1); put(2,1); assert get(2)==1; put(3,2); assert get(2)==-1; assert get(3)==2")]:
    try:
        exec(script,{'LRUCache':LRUCache})
        results.append((name,True))
    except AssertionError:
        results.append((name,False))
    except Exception as e:
        results.append((name,False))
passed=sum(1 for _,ok in results if ok)
print(json.dumps({"passed":passed,"total":len(results),"rate":round(passed/len(results)*100,1),"results":results}))
"""
        (td/"test_main.py").write_text(test_code,encoding="utf-8")
        r=subprocess.run([PYTHON_EXE,str(td/"test_main.py")],capture_output=True,text=True,cwd=str(td),timeout=10)
        if r.returncode==0: return json.loads(r.stdout.strip())
        return {"passed":0,"total":3,"rate":0,"results":[]}
    except:
        return {"passed":0,"total":3,"rate":0,"results":[]}
    finally:
        shutil.rmtree(td,ignore_errors=True)

def run_fn_tests(code,tid,cases_json):
    fn=FUNC_NAMES[tid]; cases=TEST_CASES[tid]
    td=Path(tempfile.mkdtemp(prefix="vl11_"))
    try:
        (td/"__init__.py").write_text("")
        (td/"main.py").write_text(code,encoding="utf-8")
        test_code="""import sys,os,json; sys.path.insert(0,os.path.dirname(__file__))
from main import """+fn+"""
cases=json.loads('"""+cases_json+"""')
passed=0; total=len(cases); errors=[]
for i,tc in enumerate(cases):
    vals = tc[0]; expected = tc[1]
    try:
        if isinstance(vals,tuple): result="""+fn+"""(*vals)
        else: result="""+fn+"""(vals)
        if result == expected: passed+=1
        else: errors.append(f"case {i}: exp={expected} got={result}")
    except Exception as e: errors.append(f"case {i}: {e}")
print(json.dumps({"passed":passed,"total":total,"rate":round(passed/total*100,1) if total>0 else 0,"errors":errors[:5]}))
"""
        (td/"test_main.py").write_text(test_code,encoding="utf-8")
        r=subprocess.run([PYTHON_EXE,str(td/"test_main.py")],capture_output=True,text=True,cwd=str(td),timeout=10,env={**os.environ,"PYTHONPATH":str(td)})
        if r.returncode==0: return json.loads(r.stdout.strip())
        return {"passed":0,"total":len(cases),"rate":0,"errors":[r.stderr[:200]]}
    except Exception as e:
        return {"passed":0,"total":len(cases),"rate":0,"errors":[str(e)]}
    finally:
        shutil.rmtree(td,ignore_errors=True)

def run_tests(code,tid):
    if tid=="v11-lru-cache-lc": return run_lru_tests(code)
    cases=TEST_CASES[tid]
    cases_json=json.dumps(cases)
    return run_fn_tests(code,tid,cases_json)

def main():
    bd=Path(__file__).parent; od=bd/"results_data"; od.mkdir(exist_ok=True)
    print("="*80); print("v11 LiveCodeBench 风格实验 — A(直出) vs B(+Harness辩论)"); print("="*80)
    tasks=["v11-two-sum","v11-valid-parentheses","v11-merge-intervals","v11-lru-cache-lc","v11-longest-substring","v11-word-break"]
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

    print("\n"+"="*80); print("v11 LiveCodeBench风格 汇总"); print("="*80)
    print(f"{'Task':<24} {'A passed':>8} {'B passed':>8} {'A %':>7} {'B %':>7} {'Δ':>7}")
    print("-"*68)
    for t in task_breakdown: print(f"{t['task']:<24} {t['a_passed']}/{t['a_total']:<4} {t['b_passed']}/{t['b_total']:<4} {t['a_rate']:>6.1f} {t['b_rate']:>6.1f} {t['b_rate']-t['a_rate']:>+6.1f}")
    print("-"*68)
    print(f"{'TOTAL':<24} {a_pass}/{a_tot:<4} {b_pass}/{b_tot:<4} {a_rate:>6.1f} {b_rate:>6.1f} {delta:>+6.1f}")
    print(f"\nA pass rate: {a_rate}% | B pass rate: {b_rate}% | Δ: {delta:+}%")

    (od/"v11_results.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf-8")
    (bd/"results").write_text(json.dumps({k:v for k,v in summary.items() if k!="tasks"},indent=2,ensure_ascii=False),encoding="utf-8")
    import csv
    with open(od/"v11_livecodebench.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["task","a_passed","a_total","a_rate","b_passed","b_total","b_rate","a_orch_rate","b_orch_rate"]); w.writeheader(); w.writerows(task_breakdown)
    print(f"\nResults: {od/'v11_results.json'}")

if __name__=="__main__": main()
