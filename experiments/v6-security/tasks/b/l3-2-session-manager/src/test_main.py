import sys, os, json, base64; sys.path.insert(0, os.path.dirname(__file__))
from main import SessionManager
def test_none_algorithm():
    sm=SessionManager("supersecretkey99")
    sm.register("alice","password123")
    token=sm.login("alice","password123")
    parts=token.split(".")
    fake_h=base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    attack=fake_h+"."+parts[1]+"."+parts[2]
    assert sm.verify_token(attack) is None
def test_weak_password():
    try:
        sm=SessionManager("supersecretkey99")
        sm.register("weak","123")
        assert False
    except ValueError: pass
def test_empty_username():
    try:
        sm=SessionManager("supersecretkey99")
        sm.register("","pass12345")
        assert False
    except ValueError: pass
def test_logout_blacklist():
    sm=SessionManager("supersecretkey99")
    sm.register("alice","password123")
    t=sm.login("alice","password123")
    uid=sm.verify_token(t) if hasattr(sm.verify_token(t),'user_id') else sm.verify_token(t).get('user_id', sm._users[list(sm._users.keys())[0]].id) if sm.verify_token(t) else sm._users[list(sm._users.keys())[0]].id
    if hasattr(sm,'logout'):
        sm.logout(uid)
        assert sm.verify_token(t) is None
