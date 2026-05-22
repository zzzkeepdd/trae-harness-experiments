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
    assert sm.login("alice", "wrong") is None
    try:
        sm.register("", "pw")
        assert False
    except ValueError:
        pass
    try:
        sm.register("alice", "pw")
        assert False
    except ValueError:
        pass

def test_permissions():
    sm = SessionManager("secret")
    uid = sm.register("alice", "pw")
    assert sm.check_permission(uid, "read") == True
    assert sm.check_permission(uid, "write") == False
    assert sm.check_permission(uid, "delete") == False
    assert sm.check_permission("nonexistent", "read") == False

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
    fake_header = '{"alg": "none", "typ": "JWT"}'
    fake_h = base64.urlsafe_b64encode(fake_header.encode()).rstrip(b"=").decode()
    attack_token = fake_h + "." + parts[1] + "." + parts[2]
    assert sm.verify_token(attack_token) is None

def test_refresh_token():
    sm = SessionManager("secret")
    sm.register("alice", "pw")
    t1 = sm.login("alice", "pw")
    t2 = sm.refresh_token(t1)
    assert sm.verify_token(t1) is None
    assert sm.verify_token(t2) is not None

def test_online_users():
    sm = SessionManager("secret")
    sm.register("alice", "pw")
    sm.register("bob", "pw")
    sm.login("alice", "pw")
    sm.login("bob", "pw")
    users = sm.get_online_users()
    assert len(users) == 2
    sm.logout(users[0])
    assert len(sm.get_online_users()) == 1
