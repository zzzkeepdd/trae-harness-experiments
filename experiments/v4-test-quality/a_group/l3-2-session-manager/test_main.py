import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from main import SessionManager

def test_register_login():
    sm = SessionManager("secret")
    uid = sm.register("alice", "pw")
    assert isinstance(uid, str) and len(uid) > 0
    token = sm.login("alice", "pw")
    payload = sm.verify_token(token)
    assert payload is not None
    assert payload.username == "alice"

def test_permissions():
    sm = SessionManager("secret")
    uid = sm.register("alice", "pw")
    assert sm.check_permission(uid, "read") == True
    assert sm.check_permission(uid, "write") == False
