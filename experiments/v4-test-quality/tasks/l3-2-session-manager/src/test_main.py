import sys, os, json, base64; sys.path.insert(0, os.path.dirname(__file__))
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
