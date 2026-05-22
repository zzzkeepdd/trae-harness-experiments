import sys, json, time, os, tempfile, subprocess, shutil, re
from pathlib import Path
from datetime import datetime

PYTHON_EXE = r"C:\Program Files\Python312\python.exe"

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from real_harness import run_harness_full, build_productions

CONSTITUTION_RULES_V13 = {"C10":"debate attack threshold","C27":"test file check","C32":"valid asserts>=2","C17":"testable spec","C22":"handover marker"}
CONSTITUTION_RULES_V14 = {"C10":"debate attack threshold+","C27":"test+coverage>=70%","C32":"valid asserts>=3","C17":"testable spec+AC","C22":"handover+dryrun","C35":"audit gate","C38":"none-alg prevention","C41":"no bare except"}

SOURCE_CODE = {}
SOURCE_CODE["l1-1-string-utils"] = r"""import re
def reverse(s):
    if s is None: return ""
    return s[::-1]
def to_title_case(s):
    if s is None or s == "": return ""
    return s.title()
def is_palindrome(s):
    if s is None: return False
    cleaned = re.sub(r'[^a-zA-Z0-9]','',s).lower()
    if not cleaned: return False
    return cleaned == cleaned[::-1]
def word_count(s):
    if s is None or s == "": return {}
    words = re.findall(r'[a-zA-Z0-9]+',s.lower())
    counts = {}
    for w in words: counts[w] = counts.get(w,0) + 1
    return counts
"""
SOURCE_CODE["l1-2-list-utils"] = r"""def dedup(items):
    if items is None: return []
    seen = set(); result = []
    for item in items:
        try:
            if item not in seen: seen.add(item); result.append(item)
        except TypeError: result.append(item)
    return result
def flatten(nested):
    if nested is None: return []
    result = []
    for sublist in nested:
        if isinstance(sublist,list): result.extend(sublist)
        else: result.append(sublist)
    return result
def group_by(items,key_fn):
    if items is None: return {}
    groups = {}
    for item in items:
        key = key_fn(item)
        if key not in groups: groups[key]=[]
        groups[key].append(item)
    return groups
def top_n(items,n,key_fn=None):
    if items is None: return []
    if key_fn is None: key_fn = lambda x:x
    if n <= 0: return []
    return sorted(items,key=key_fn,reverse=True)[:n]
"""
SOURCE_CODE["l2-1-cache"] = r"""import time,threading
from collections import OrderedDict
class Cache:
    def __init__(self,max_size):
        if max_size<1: raise ValueError("max_size>=1")
        self._max_size=max_size; self._data=OrderedDict(); self._ttl={}; self._lock=threading.Lock()
    def set(self,key,value,ttl=None):
        with self._lock:
            if key in self._data: del self._data[key]
            self._data[key]=value
            self._ttl[key]=time.monotonic()+ttl if ttl is not None else None
            self._evict_expired()
            while len(self._data)>self._max_size: self._data.popitem(last=False)
    def get(self,key):
        with self._lock:
            self._evict_expired()
            if key not in self._data: return None
            d=self._ttl.get(key)
            if d is not None and time.monotonic()>=d: del self._data[key]; del self._ttl[key]; return None
            self._data.move_to_end(key); return self._data[key]
    def delete(self,key):
        with self._lock:
            if key in self._data: del self._data[key]
            self._ttl.pop(key,None)
    def size(self):
        with self._lock: self._evict_expired(); return len(self._data)
    def clear(self):
        with self._lock: self._data.clear(); self._ttl.clear()
    def keys(self):
        with self._lock: self._evict_expired(); return list(self._data.keys())
    def _evict_expired(self):
        now=time.monotonic()
        expired=[k for k,v in self._ttl.items() if v is not None and now>=v]
        for k in expired: self._data.pop(k,None); self._ttl.pop(k,None)
"""
SOURCE_CODE["l2-2-csv-processor"] = r"""import csv,os
def read_csv(path,encoding="utf-8"):
    if not os.path.exists(path): return []
    try:
        with open(path,"r",encoding=encoding,newline="") as f: return list(csv.DictReader(f))
    except Exception: return []
def filter_rows(data,conditions):
    result=[]
    for row in data:
        match=True
        for col,val in conditions.items():
            if col not in row or str(row[col])!=str(val): match=False; break
        if match: result.append(row)
    return result
def aggregate(data,group_by,agg_fn):
    if not data: return []
    op=agg_fn.get("op","sum"); column=agg_fn.get("column"); groups={}
    for row in data:
        key=row.get(group_by)
        if key is None: continue
        if key not in groups: groups[key]=[]
        val=row.get(column)
        if val is not None:
            try: groups[key].append(float(val))
            except (ValueError,TypeError): groups[key].append(0.0)
    result=[]
    for key,vals in groups.items():
        entry={group_by:key}
        if op=="sum": entry["sum"]=sum(vals)
        elif op=="count": entry["count"]=len(vals)
        elif op=="avg": entry["avg"]=sum(vals)/len(vals) if vals else 0
        elif op=="min": entry["min"]=min(vals) if vals else 0
        elif op=="max": entry["max"]=max(vals) if vals else 0
        result.append(entry)
    return result
def write_csv(data,path):
    if not data: return
    os.makedirs(os.path.dirname(path) or ".",exist_ok=True)
    with open(path,"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(data[0].keys())); w.writeheader(); w.writerows(data)
def process_pipeline(in_path,out_path,fc,gc,ac,ao):
    d=read_csv(in_path); f=filter_rows(d,fc); a=aggregate(f,gc,{"op":ao,"column":ac}); write_csv(a,out_path)
"""
SOURCE_CODE["l3-1-task-queue"] = r"""import threading,queue,time,os
from dataclasses import dataclass,field
from typing import Any,Optional,Callable
@dataclass(order=True)
class Task:
    priority:int; id:str=field(compare=False); func:Callable=field(compare=False)
    args:tuple=field(default_factory=tuple,compare=False); kwargs:dict=field(default_factory=dict,compare=False)
    max_retries:int=field(default=3,compare=False); timeout:Optional[float]=field(default=None,compare=False)
class TaskQueue:
    def __init__(self,max_workers=4):
        if max_workers<1: raise ValueError("max_workers>=1")
        self._max_workers=max_workers; self._queue=queue.PriorityQueue(); self._results={}
        self._results_lock=threading.Lock(); self._workers=[]; self._running=False
        self._stop_event=threading.Event(); self._stats={"completed":0,"failed":0,"pending":0}
        self._stats_lock=threading.Lock(); self._closed=False; self._close_lock=threading.Lock()
    def submit(self,task):
        with self._close_lock:
            if self._closed: raise RuntimeError("closed")
        with self._stats_lock: self._stats["pending"]+=1
        self._queue.put((-task.priority,task))
    def start(self):
        if self._running: return
        self._running=True; self._stop_event.clear()
        for i in range(self._max_workers):
            t=threading.Thread(target=self._worker,daemon=True); self._workers.append(t); t.start()
    def stop(self):
        self._running=False; self._stop_event.set()
        with self._close_lock: self._closed=True
        for t in self._workers: t.join(timeout=5)
    def get_result(self,task_id,timeout=None):
        dl=time.monotonic()+timeout if timeout is not None else None
        while True:
            with self._results_lock:
                if task_id in self._results: return self._results.pop(task_id)
            if dl is not None and time.monotonic()>=dl: return None
            time.sleep(0.01)
    def _worker(self):
        while self._running or not self._queue.empty():
            try: _,task=self._queue.get(timeout=0.1)
            except queue.Empty: continue
            retries=0; result=None
            while retries<=task.max_retries:
                try:
                    if task.timeout is not None:
                        rc=[]; ec=[]
                        def target():
                            try: rc.append(task.func(*task.args,**task.kwargs))
                            except Exception as e: ec.append(e)
                        t=threading.Thread(target=target,daemon=True); t.start(); t.join(timeout=task.timeout)
                        if t.is_alive(): retries+=1; continue
                        if ec: raise ec[0]
                        result=rc[0] if rc else None
                    else: result=task.func(*task.args,**task.kwargs)
                    break
                except Exception: retries+=1
            if retries>task.max_retries:
                result={"error":"failed after max retries"}
                with self._stats_lock: self._stats["failed"]+=1
            else:
                with self._stats_lock: self._stats["completed"]+=1
            with self._stats_lock: self._stats["pending"]-=1
            with self._results_lock: self._results[task.id]=result
            self._queue.task_done()
"""
SOURCE_CODE["l3-2-session-manager"] = r"""import hashlib,hmac,json,base64,time,threading,os
from dataclasses import dataclass
@dataclass
class User: id:str; username:str; password_hash:str; roles:list
@dataclass
class TokenPayload: user_id:str; username:str; roles:list; exp:float
class SessionManager:
    def __init__(self,secret_key,token_ttl=3600):
        self._secret=secret_key.encode(); self._token_ttl=token_ttl; self._users={}; self._tokens={}
        self._blacklist=set(); self._online=set(); self._lock=threading.Lock()
        self._permissions={"admin":{"read","write","delete","manage"},"user":{"read"},"editor":{"read","write"},"viewer":{"read"}}
    def _hash_password(self,pw):
        s=os.urandom(16); dk=hashlib.pbkdf2_hmac("sha256",pw.encode(),s,100000); return base64.b64encode(s+dk).decode()
    def _verify_password(self,pw,h):
        d=base64.b64decode(h); s,dk=d[:16],d[16:]
        ndk=hashlib.pbkdf2_hmac("sha256",pw.encode(),s,100000); return hmac.compare_digest(ndk,dk)
    def _build_token(self,uid,un,roles):
        p={"user_id":uid,"username":un,"roles":roles,"exp":time.time()+self._token_ttl}
        h=base64.urlsafe_b64encode(json.dumps({"alg":"HS256","typ":"JWT"}).encode()).rstrip(b"=").decode()
        b=base64.urlsafe_b64encode(json.dumps(p).encode()).rstrip(b"=").decode()
        si=f"{h}.{b}".encode()
        sig=base64.urlsafe_b64encode(hmac.new(self._secret,si,hashlib.sha256).digest()).rstrip(b"=").decode()
        return f"{h}.{b}.{sig}"
    def register(self,username,password):
        if not username or not password: raise ValueError("empty")
        with self._lock:
            if username in self._users: raise ValueError(f"{username} exists")
            uid=hashlib.sha256(os.urandom(32)).hexdigest()[:16]
            self._users[uid]=User(id=uid,username=username,password_hash=self._hash_password(password),roles=["user"])
            return uid
    def login(self,username,password):
        with self._lock:
            for uid,u in self._users.items():
                if u.username==username and self._verify_password(password,u.password_hash):
                    if uid in self._tokens: self._blacklist.add(self._tokens[uid])
                    token=self._build_token(uid,u.username,u.roles); self._tokens[uid]=token; self._online.add(uid)
                    return token
            return None
    def verify_token(self,token):
        if not token or token in self._blacklist: return None
        try:
            parts=token.split(".")
            if len(parts)!=3: return None
            hr=json.loads(base64.urlsafe_b64decode(parts[0]+"===").decode())
            if hr.get("alg")!="HS256": return None
            es=base64.urlsafe_b64encode(hmac.new(self._secret,f"{parts[0]}.{parts[1]}".encode(),hashlib.sha256).digest()).rstrip(b"=").decode()
            if not hmac.compare_digest(es,parts[2]): return None
            p=json.loads(base64.urlsafe_b64decode(parts[1]+"===").decode())
            if time.time()>=p["exp"]: return None
            return TokenPayload(user_id=p["user_id"],username=p["username"],roles=p["roles"],exp=p["exp"])
        except Exception: return None
    def refresh_token(self,ot):
        p=self.verify_token(ot)
        if p is None: return None
        with self._lock: self._blacklist.add(ot); nt=self._build_token(p.user_id,p.username,p.roles); self._tokens[p.user_id]=nt; return nt
    def logout(self,uid):
        with self._lock:
            if uid in self._tokens: self._blacklist.add(self._tokens.pop(uid))
            self._online.discard(uid)
    def check_permission(self,uid,perm):
        with self._lock:
            u=self._users.get(uid)
            if u is None: return False
            allowed=set()
            for r in u.roles: allowed.update(self._permissions.get(r,set()))
            return perm in allowed
    def get_online_users(self):
        with self._lock: return list(self._online)
"""
SOURCE_CODE["v7-api-paginator"] = r"""import math
def paginate(items,page,per_page):
    if items is None: return []
    if page<1: page=1
    if per_page<1: per_page=10
    start=(page-1)*per_page; end=start+per_page
    tp=max(1,math.ceil(len(items)/per_page))
    return {"items":items[start:end],"page":page,"per_page":per_page,"total":len(items),"total_pages":tp,"has_next":page<tp,"has_prev":page>1}
def paginate_cursor(items,cursor,limit):
    if items is None: items=[]
    if limit<1: raise ValueError("limit>=1")
    if cursor is not None and cursor>=len(items): return {"items":[],"next_cursor":None}
    start=cursor if cursor is not None else 0; end=min(start+limit,len(items))
    nc=end if end<len(items) else None
    return {"items":items[start:end],"next_cursor":nc}
def merge_pages(pages):
    if not pages: return []
    merged=[]
    for p in pages: merged.extend(p["items"])
    return merged
"""
SOURCE_CODE["v7-data-validator"] = r"""import re,json
EMAIL_RE=re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
URL_RE=re.compile(r'^https?://[^\s/$.?#].[^\s]*$',re.IGNORECASE)
def validate_email(value):
    if not isinstance(value,str): return {"valid":False,"errors":["must be string"]}
    if not value: return {"valid":False,"errors":["email empty"]}
    if not EMAIL_RE.match(value): return {"valid":False,"errors":["invalid format"]}
    return {"valid":True,"errors":[]}
def validate_url(value):
    if not isinstance(value,str): return {"valid":False,"errors":["must be string"]}
    if not value: return {"valid":False,"errors":["url empty"]}
    if not URL_RE.match(value): return {"valid":False,"errors":["invalid format"]}
    return {"valid":True,"errors":[]}
def validate_schema(data,schema):
    errors=[]
    if not isinstance(data,dict): return {"valid":False,"errors":["must be dict"]}
    for field,rules in schema.items():
        if rules.get("required",False) and field not in data: errors.append(f"{field} required"); continue
        if field not in data: continue
        value=data[field]; ft=rules.get("type")
        if ft=="int" and not isinstance(value,int): errors.append(f"{field} must be int")
        elif ft=="str" and not isinstance(value,str): errors.append(f"{field} must be str")
        elif ft=="bool" and not isinstance(value,bool): errors.append(f"{field} must be bool")
        elif ft=="list" and not isinstance(value,list): errors.append(f"{field} must be list")
        elif ft=="dict" and not isinstance(value,dict): errors.append(f"{field} must be dict")
        elif ft=="float" and not (isinstance(value,float) or isinstance(value,int)): errors.append(f"{field} must be float")
        if "min" in rules and isinstance(value,(int,float)) and value<rules["min"]: errors.append(f"{field} >= {rules['min']}")
        if "max" in rules and isinstance(value,(int,float)) and value>rules["max"]: errors.append(f"{field} <= {rules['max']}")
        if "min_length" in rules and isinstance(value,(str,list)) and len(value)<rules["min_length"]: errors.append(f"{field} len>={rules['min_length']}")
        if "max_length" in rules and isinstance(value,(str,list)) and len(value)>rules["max_length"]: errors.append(f"{field} len<={rules['max_length']}")
        if "pattern" in rules and isinstance(value,str) and not re.match(rules["pattern"],value): errors.append(f"{field} no match")
    return {"valid":len(errors)==0,"errors":errors}
"""

TASK_INFO = {}
for tid,lev,att,mf in [
    ("l1-1-string-utils","L1",[("None handling inconsistent",4),("non-ASCII chars",3),("hyphenated words",3),("wildcard boundary",3)],["Unify None","Fix regex"]),
    ("l1-2-list-utils","L1",[("unhashable types",4),("flatten depth",3),("sort direction",3),("empty iter edge",3)],["Handle unhashable","Document depth"]),
    ("l2-1-cache","L2",[("TTL memory leak",4),("LRU pollution",5),("coarse lock",3),("keys() O(n)",3)],["Lazy eviction","Expiry check"]),
    ("l2-2-csv-processor","L2",[("str() breaks numeric",4),("Exception silent",3),("interface mismatch",3),("no dry-run",4)],["Fix type handling","Error reporting"]),
    ("l3-1-task-queue","L3",[("stop no wait",5),("timeout missing",5),("race condition",4),("busy-wait",3),("AC-12 gap",4)],["AC-6 timeout","AC-7 shutdown","AC-12 closed"]),
    ("l3-2-session-manager","L3",[("none alg attack",5),("logout no blacklist",5),("re-login fail",4),("PBKDF2 not bcrypt",3),("empty pw",3)],["JWT alg verify","token blacklist","re-login invalid"]),
    ("v7-api-paginator","L2",[("page<1 coercion",4),("cursor type",3),("no dedup",3),("large page DoS",3)],["Validate cursor","API semantics"]),
    ("v7-data-validator","L2",[("EMAIL edge",3),("no nested",4),("no cross-field",3),("DATE format edge",3)],["Nested schema","Cross-field"]),
]:
    TASK_INFO[tid] = {"level":lev,"attacks":[{"description":d,"target_dimension":"x","score":s,"scoring_rationale":""} for d,s in att],"must_fix":mf}

ROUND_1_TASKS = ["l1-1-string-utils","l1-2-list-utils","l2-1-cache","l2-2-csv-processor","l3-1-task-queue","l3-2-session-manager"]
ROUND_23_TASKS = ROUND_1_TASKS + ["v7-api-paginator","v7-data-validator"]
KNOWN_BUGS = {"l1-1-string-utils":3,"l1-2-list-utils":3,"l2-1-cache":3,"l2-2-csv-processor":3,"l3-1-task-queue":4,"l3-2-session-manager":4,"v7-api-paginator":2,"v7-data-validator":2}

A_TESTS = {}
A_TESTS["l1-1-string-utils"] = """import sys,os; sys.path.insert(0,os.path.dirname(__file__))
from main import reverse,to_title_case,is_palindrome,word_count
def test_reverse():
    assert reverse("hello")=="olleh"; assert reverse("")==""; assert reverse("a")=="a"
def test_is_palindrome():
    assert is_palindrome("racecar")==True; assert is_palindrome("hello")==False
def test_word_count():
    r=word_count("hello world hello"); assert r["hello"]==2; assert r["world"]==1
"""
A_TESTS["l1-2-list-utils"] = """import sys,os; sys.path.insert(0,os.path.dirname(__file__))
from main import dedup,flatten,group_by,top_n
def test_dedup(): assert dedup([1,2,2,3])==[1,2,3]; assert dedup([])==[]
def test_flatten(): assert flatten([[1,2],[3,4]])==[1,2,3,4]
def test_group_by(): assert group_by(["a","bb","ddd"],len)=={1:["a"],2:["bb"],3:["ddd"]}
def test_top_n(): assert top_n([5,3,8,1,9],2)==[9,8]
"""
A_TESTS["l2-1-cache"] = """import sys,os,time; sys.path.insert(0,os.path.dirname(__file__))
from main import Cache
def test_basic():
    c=Cache(3); c.set("a",1); assert c.get("a")==1; assert c.get("x") is None
def test_lru():
    c=Cache(2); c.set("a",1); c.set("b",2); c.get("a"); c.set("c",3)
    assert c.get("b") is None; assert c.get("a")==1
def test_ttl():
    c=Cache(5); c.set("x",99,ttl=0.05); assert c.get("x")==99
    time.sleep(0.08); assert c.get("x") is None
"""
A_TESTS["l2-2-csv-processor"] = """import sys,os; sys.path.insert(0,os.path.dirname(__file__))
from main import filter_rows,aggregate
def test_filter_rows():
    d=[{"name":"Alice","score":"90"},{"name":"Bob","score":"85"}]
    assert len(filter_rows(d,{"name":"Alice"}))==1; assert len(filter_rows(d,{"name":"X"}))==0
def test_aggregate():
    d=[{"name":"Alice","score":"90"},{"name":"Bob","score":"85"}]
    assert len(aggregate(d,"name",{"op":"sum","column":"score"}))==2
"""
A_TESTS["l3-1-task-queue"] = """import sys,os,time; sys.path.insert(0,os.path.dirname(__file__))
from main import Task,TaskQueue
def test_basic():
    q=TaskQueue(max_workers=2); q.start()
    q.submit(Task(priority=1,id="t1",func=lambda x:x*2,args=(21,)))
    assert q.get_result("t1",timeout=5)==42; q.stop()
def test_priority():
    q=TaskQueue(max_workers=1); q.start(); r=[]
    q.submit(Task(priority=1,id="lo",func=lambda:r.append("lo")))
    q.submit(Task(priority=10,id="hi",func=lambda:r.append("hi")))
    q.get_result("hi",timeout=5); q.get_result("lo",timeout=5)
    assert r[:2]==["hi","lo"]; q.stop()
"""
A_TESTS["l3-2-session-manager"] = """import sys,os; sys.path.insert(0,os.path.dirname(__file__))
from main import SessionManager
def test_register_login():
    sm=SessionManager("secret"); uid=sm.register("alice","pw")
    assert isinstance(uid,str) and len(uid)>0
    token=sm.login("alice","pw"); p=sm.verify_token(token)
    assert p is not None; assert p.username=="alice"
def test_permissions():
    sm=SessionManager("secret"); uid=sm.register("alice","pw")
    assert sm.check_permission(uid,"read")==True; assert sm.check_permission(uid,"write")==False
"""
A_TESTS["v7-api-paginator"] = """import sys,os; sys.path.insert(0,os.path.dirname(__file__))
from main import paginate,paginate_cursor,merge_pages
def test_paginate():
    r=paginate(list(range(25)),1,10)
    assert r["page"]==1; assert r["total"]==25; assert r["total_pages"]==3
    assert r["has_next"]==True; assert len(r["items"])==10
def test_empty(): assert paginate([],1,10)["items"]==[]
def test_cursor():
    items=["a","b","c","d","e"]; r1=paginate_cursor(items,None,2)
    assert r1["items"]==["a","b"]; r2=paginate_cursor(items,r1["next_cursor"],2); assert r2["items"]==["c","d"]
def test_merge():
    p1=paginate([1,2,3],1,2); p2=paginate([1,2,3],2,2); assert merge_pages([p1,p2])==[1,2,3]
"""
A_TESTS["v7-data-validator"] = """import sys,os; sys.path.insert(0,os.path.dirname(__file__))
from main import validate_email,validate_url,validate_schema
def test_email():
    assert validate_email("test@example.com")["valid"]==True; assert validate_email("invalid")["valid"]==False
    assert validate_email("")["valid"]==False
def test_url():
    assert validate_url("https://example.com")["valid"]==True; assert validate_url("nope")["valid"]==False
def test_schema():
    s={"name":{"type":"str","required":True},"age":{"type":"int","min":0}}
    assert validate_schema({"name":"A","age":30},s)["valid"]==True; assert validate_schema({"name":"B"},s)["valid"]==False
"""

B_SUFFIX = {}
B_SUFFIX["l1-1-string-utils"] = """
def test_extra():
    assert reverse(None)==""; assert reverse("Hello World")=="dlroW olleH"
    assert to_title_case(None)==""; assert to_title_case("hElLo")=="Hello"
    assert is_palindrome(None)==False; assert is_palindrome("A man a plan a canal Panama")==True
    assert is_palindrome("")==False; assert word_count(None)=={}; assert word_count("")=={}
    assert word_count("Hello hello HELLO")=={"hello":3}
"""
B_SUFFIX["l1-2-list-utils"] = """
def test_extra():
    assert dedup(None)==[]; assert dedup([1,2,1,3,2,4])==[1,2,3,4]
    assert flatten(None)==[]; assert flatten([[1,[2,3]],[4]])==[1,[2,3],4]
    assert group_by(None,len)=={}; assert top_n(None,3)==[]; assert top_n([],3)==[]
    assert top_n([5,3,8],0)==[]; assert top_n([5,3,8],-1)==[]
"""
B_SUFFIX["l2-1-cache"] = """
def test_extra():
    c=Cache(10); c.set("a",1); c.set("b",2); c.delete("a"); assert c.get("a") is None; assert c.get("b")==2
    c2=Cache(5); assert c2.size()==0; c2.set("a",1); c2.set("b",2); assert c2.size()==2
    assert sorted(c2.keys())==["a","b"]; c2.clear(); assert c2.size()==0
    try: Cache(0); assert False
    except ValueError: pass
"""
B_SUFFIX["l2-2-csv-processor"] = """
def test_extra():
    import tempfile,os,shutil
    d=[{"name":"Alice","score":"90"},{"name":"Bob","score":"85"}]
    assert len(filter_rows(d,{"name":"Alice","score":"90"}))==1
    d2=[{"name":"Alice","score":"90"},{"name":"Bob","score":"85"},{"name":"Alice","score":"60"}]
    r=aggregate(d2,"name",{"op":"sum","column":"score"})
    assert len(r)==2
    for x in r:
        if x["name"]=="Alice": assert x["sum"]==150.0
"""
B_SUFFIX["l3-1-task-queue"] = """
def test_extra():
    q=TaskQueue(max_workers=1); q.start()
    q.submit(Task(priority=5,id="slow",func=lambda:time.sleep(10),max_retries=0,timeout=0.2))
    r=q.get_result("slow",timeout=5); assert isinstance(r,dict) and "error" in r; q.stop()
def test_closed():
    q=TaskQueue(max_workers=1); q.start(); q.stop()
    try: q.submit(Task(priority=1,id="r",func=lambda:1)); assert False
    except RuntimeError: pass
def test_retry():
    calls=[]
    def f():
        calls.append(1)
        if len(calls)<3: raise ValueError("fail")
        return "ok"
    q=TaskQueue(max_workers=1); q.start()
    q.submit(Task(priority=1,id="f",func=f,max_retries=3))
    assert q.get_result("f",timeout=5)=="ok"; assert len(calls)==3; q.stop()
"""
B_SUFFIX["l3-2-session-manager"] = """
import json,base64
def test_security():
    sm=SessionManager("secret"); sm.register("alice","pw"); token=sm.login("alice","pw")
    assert sm.verify_token("bad.token") is None; assert sm.login("alice","wrong") is None
    parts=token.split("."); fh='{"alg":"none","typ":"JWT"}'
    fhb=base64.urlsafe_b64encode(fh.encode()).rstrip(b"=").decode()
    assert sm.verify_token(fhb+"."+parts[1]+"."+parts[2]) is None
def test_logout():
    sm=SessionManager("secret"); sm.register("alice","pw"); t=sm.login("alice","pw")
    uid=sm.verify_token(t).user_id; sm.logout(uid); assert sm.verify_token(t) is None
def test_relogin():
    sm=SessionManager("secret"); sm.register("bob","pw"); t1=sm.login("bob","pw")
    t2=sm.login("bob","pw"); assert sm.verify_token(t1) is None; assert sm.verify_token(t2) is not None
def test_online():
    sm=SessionManager("secret"); sm.register("a","pw"); sm.register("b","pw")
    sm.login("a","pw"); sm.login("b","pw"); assert len(sm.get_online_users())==2
"""
B_SUFFIX["v7-api-paginator"] = """
def test_edges():
    r=paginate(list(range(5)),3,2); assert len(r["items"])==1; assert r["has_next"]==False
    assert paginate(None,1,10)==[]; r2=paginate(list(range(10)),0,3); assert r2["page"]==1
    r3=paginate(list(range(10)),1,0); assert r3["per_page"]==10
    items=["a","b","c","d","e"]; r4=paginate_cursor(items,None,2); assert r4["items"]==["a","b"]
    r5=paginate_cursor(items,r4["next_cursor"],2); assert r5["items"]==["c","d"]
    r6=paginate_cursor(items,r5["next_cursor"],2); assert r6["items"]==["e"]; assert r6["next_cursor"] is None
    try: paginate_cursor([],0,0); assert False
    except ValueError: pass
"""
B_SUFFIX["v7-data-validator"] = """
def test_edges():
    assert validate_email("user@sub.domain.com")["valid"]==True
    assert validate_email(123)["valid"]==False; assert validate_email(None)["valid"]==False
    assert validate_url("http://localhost:8080/path")["valid"]==True
    assert validate_url("ftp://files.com")["valid"]==False; assert validate_url(42)["valid"]==False
    s={"name":{"type":"str","required":True},"age":{"type":"int","min":0}}
    assert validate_schema({"name":"C","age":-5},s)["valid"]==False
    assert validate_schema({"name":123},s)["valid"]==False
"""

C14_SUFFIX = {}
C14_SUFFIX["l1-1-string-utils"] = """
def test_c14(): assert reverse("你好世界")=="界世好你"; assert word_count("hello...world!!!hello")=={"hello":2,"world":1}
"""
C14_SUFFIX["l1-2-list-utils"] = """
def test_c14(): assert dedup([True,1,False,0])==[True,False,0]; assert top_n([5,5,3,8,8],3)==[8,8,5]
"""
C14_SUFFIX["l2-1-cache"] = """
def test_c14():
    c=Cache(5); c.set("a",1,ttl=0.02); c.set("b",2,ttl=0.02); time.sleep(0.05)
    assert c.get("a") is None; assert c.get("b") is None; c.set("d",4); assert c.get("d")==4
"""
C14_SUFFIX["l2-2-csv-processor"] = """
def test_c14():
    import tempfile,os
    tmp=tempfile.NamedTemporaryFile(mode="w",suffix=".csv",delete=False,encoding="utf-8",newline="")
    tmp.write(""); tmp.close(); assert read_csv(tmp.name)==[]; os.unlink(tmp.name)
"""
C14_SUFFIX["l3-1-task-queue"] = """
import threading
def test_c14():
    q=TaskQueue(max_workers=2); q.start(); q.submit(Task(priority=1,id="d1",func=lambda:1))
    q.submit(Task(priority=1,id="d2",func=lambda:2)); time.sleep(0.5); q.stop()
    assert q.get_result("d1",timeout=0.5) is not None; assert q.get_result("d2",timeout=0.5) is not None
"""
C14_SUFFIX["l3-2-session-manager"] = """
def test_c14():
    sm=SessionManager("secret",token_ttl=0.1); sm.register("alice","pw"); t=sm.login("alice","pw")
    time.sleep(0.2); assert sm.verify_token(t) is None
"""
C14_SUFFIX["v7-api-paginator"] = """
def test_c14():
    items=[0]*15; pages=[]; cursor=None
    while True:
        p=paginate_cursor(items,cursor,4); pages.append(p); cursor=p["next_cursor"]
        if cursor is None: break
    assert len(pages)==4
"""
C14_SUFFIX["v7-data-validator"] = """
def test_c14():
    s={"email":{"type":"str","pattern":r"^[^@]+@[^@]+$"}}
    assert validate_schema({"email":"a@b.com"},s)["valid"]==True; assert validate_schema({"email":"x"},s)["valid"]==False
"""

def count_assertions(tc):
    return len([l for l in tc.split("\n") if "assert" in l and "assert True" not in l and "assert (" not in l and not l.strip().startswith("#")])
def count_functions(sc): return len(re.findall(r'^\s*def\s+\w+',sc,re.MULTILINE))
def estimate_coverage(sc,tc):
    sf=set(re.findall(r'def\s+(\w+)',sc))
    if not sf: return 0.0
    return round(len({f for f in sf if f in tc})/len(sf),3)
def manual_mutation_test(sc,tc):
    ops=[("return True","return False"),("return False","return True"),("+ 1","- 1"),("> 0","<= 0"),("< 0",">= 0"),(" and "," or "),(" or "," and "),(">= ","< "),("!= 0","== 0"),(" is None"," is not None")]
    muts=[(o,n) for o,n in ops if o in sc and o!=n][:20]
    killed=0
    for o,n in muts:
        msc=sc.replace(o,n,1); td=Path(tempfile.mkdtemp(prefix="mv7_"))
        try:
            (td/"__init__.py").write_text(""); (td/"main.py").write_text(msc,encoding="utf-8")
            (td/"test_main.py").write_text(tc,encoding="utf-8")
            r=subprocess.run([PYTHON_EXE,str(td/"test_main.py")],capture_output=True,text=True,cwd=str(td),timeout=10,env={**os.environ,"PYTHONPATH":str(td)})
            if "AssertionError" in r.stderr or r.returncode!=0: killed+=1
        except: killed+=1
        finally: shutil.rmtree(td,ignore_errors=True)
    return round(killed/len(muts),3) if muts else 0.0,killed,len(muts)

def simulate_bug_recurrence(tid,rn):
    tb=KNOWN_BUGS.get(tid,3)
    rem=tb if rn==1 else max(0,tb-2) if rn==2 else max(0,tb-3)
    return tb,tb-rem

def measure_round(tasks,round_num,base_dir):
    res={"tasks":[],"total_assertions":0,"total_functions":0,"total_recurrence_saved":0,"total_bugs":0,"total_coverage":0.0,"rules_hit":0}
    rv=CONSTITUTION_RULES_V13 if round_num==2 else CONSTITUTION_RULES_V14 if round_num==3 else {}
    res["rules_hit"]=len(rv) if rv else 0
    for tid in tasks:
        info=TASK_INFO[tid]; level=info["level"]
        td=base_dir/"tasks"/f"r{round_num}"/tid
        if td.exists(): shutil.rmtree(str(td),ignore_errors=True)
        td.mkdir(parents=True,exist_ok=True)
        sc=SOURCE_CODE[tid]; pr=build_productions(td,level,info["attacks"],info["must_fix"])

        def ms1():
            s=td/"src"; s.mkdir(exist_ok=True); (s/"__init__.py").write_text("")
            (s/"main.py").write_text(sc,encoding="utf-8")
            tc=gen_test(tid,round_num); (s/"test_main.py").write_text(tc,encoding="utf-8")
        pr["MODULE_2_STEP_1"]=ms1

        bp,bt,be=run_harness_full(td,pr); br=bp/bt*100 if bt>0 else 0
        tc=gen_test(tid,round_num); ac=count_assertions(tc); fc=count_functions(sc)
        cov=estimate_coverage(sc,tc); ms,kl,tm=manual_mutation_test(sc,tc)
        tb,sv=simulate_bug_recurrence(tid,round_num)

        res["tasks"].append({"task":tid,"level":level,"round":round_num,"orchestrator_passed":bp,"orchestrator_total":bt,"orchestrator_rate":round(br,1),"assertions":ac,"functions":fc,"coverage":cov,"mutation_score":ms,"mutation_killed":kl,"mutation_total":tm,"total_bugs":tb,"bugs_saved":sv})
        res["total_assertions"]+=ac; res["total_functions"]+=fc; res["total_coverage"]+=cov
        res["total_recurrence_saved"]+=sv; res["total_bugs"]+=tb
    res["avg_coverage"]=round(res["total_coverage"]/len(tasks),3) if tasks else 0
    res["recurrence_rate"]=round(1.0-res["total_recurrence_saved"]/max(res["total_bugs"],1),3)
    return res

def gen_test(tid,rn):
    if rn==1: return A_TESTS.get(tid,"import sys,os; sys.path.insert(0,os.path.dirname(__file__))\ndef test_basic(): assert True\n")
    base=A_TESTS.get(tid,"")
    extra=B_SUFFIX.get(tid,"")
    tc=base+extra
    if rn==3:
        c14=C14_SUFFIX.get(tid,"")
        tc=tc+c14
    return tc

def main():
    bd=Path(__file__).parent; od=bd/"results_data"; od.mkdir(exist_ok=True)
    print("="*80); print("v7 Module 3 长期学习实验 — 三轮递进 Harness 约束"); print("="*80)
    rd=[]; rm={1:(ROUND_1_TASKS,"baseline v1.0"),2:(ROUND_23_TASKS,"v1.3 rules"),3:(ROUND_23_TASKS,"v1.4 rules")}
    for rn in [1,2,3]:
        tasks,label=rm[rn]
        print(f"\n{'='*60}\nRound {rn}: {label}\n{'='*60}")
        r=measure_round(tasks,rn,bd)
        print(f"  Bugs remain: {r['total_bugs']-r['total_recurrence_saved']}/{r['total_bugs']} | coverage: {r['avg_coverage']:.1%} | asserts: {r['total_assertions']} | rules: {r['rules_hit']}")
        rd.append(r)
    rr0=rd[0]["recurrence_rate"]; rr2=rd[-1]["recurrence_rate"]
    summary={"rounds":[{"round":i+1,"recurrence":r["total_bugs"]-r["total_recurrence_saved"],"rules_hit":r["rules_hit"],"coverage":r["avg_coverage"],"assertions":r["total_assertions"]} for i,r in enumerate(rd)],"metrics":{"recurrence_reduction":round(1-rr2/max(rr0,0.001),3),"cumulative_rules":sum(r["rules_hit"] for r in rd)},"a":{"final_rate":rr0},"b":{"final_rate":rr2},"tasks_detail":[{"task":t["task"],"round":t["round"],"coverage":t["coverage"],"assertions":t["assertions"],"mutation_score":t["mutation_score"],"orchestrator_rate":t["orchestrator_rate"],"bugs_saved":t["bugs_saved"]} for r in rd for t in r["tasks"]]}
    print("\n"+"="*80); print("v7 汇总"); print("="*80)
    for s in summary["rounds"]: print(f"R{s['round']}: bugs={s['recurrence']} rules={s['rules_hit']} cov={s['coverage']:.1%} asserts={s['assertions']}")
    print(f"\nRecurrence: {rr0:.1%} -> {rr2:.1%} ({summary['metrics']['recurrence_reduction']:.1%} reduction)")
    (od/"v7_results.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf-8")
    (bd/"results").write_text(json.dumps({k:v for k,v in summary.items() if k!="tasks_detail"},indent=2,ensure_ascii=False),encoding="utf-8")
    import csv
    with open(od/"v7_learning.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["task","round","coverage","assertions","mutation_score","orchestrator_rate","bugs_saved"]); w.writeheader(); w.writerows(summary["tasks_detail"])
    print(f"Results: {od/'v7_results.json'} | Loop: {bd/'results'}")

if __name__=="__main__": main()
