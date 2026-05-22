from main import UserService, User
import hmac

errors = []
def check(desc, cond):
    if not cond:
        errors.append(f"FAIL {desc}")

sm = UserService()

uid1 = sm.register("alice", "password123", "alice@test.com")
check("register returns uid", isinstance(uid1, str) and len(uid1) > 0)
check("password too short rejected", False)
try:
    sm.register("bob", "123", "bob@test.com")
except ValueError:
    check("password too short rejected", True)
try:
    sm.register("alice", "password456", "a2@test.com")
except ValueError:
    check("duplicate username rejected", True)
try:
    sm.register("", "password123", "empty@test.com")
    check("empty username rejected", False)
except ValueError:
    check("empty username rejected", True)

token = sm.login("alice", "password123")
check("login returns token", isinstance(token, str) and len(token) > 0)
check("login wrong password returns None", sm.login("alice", "wrong") is None)
check("login nonexistent returns None", sm.login("nobody", "pw") is None)

payload = sm.get_user_profile(token)
check("profile is not None", payload is not None)
if payload:
    check("profile has username", payload.get("username") == "alice")
    check("profile has email", "alice@test.com" in str(payload.get("email", "")))

check("profile with bad session is None", sm.get_user_profile("invalid_session") is None)

test_uid = sm.register("charlie", "password123", "charlie@test.com")
test_token = sm.login("charlie", "password123")
sm.update_email(test_token, "new@test.com")
new_profile = sm.get_user_profile(test_token)
check("email updated", new_profile is not None and "new@test.com" in str(new_profile.get("email", "")))
try:
    sm.update_email("bad_session", "nope@test.com")
    check("bad session update_email rejected", False)
except ValueError:
    check("bad session update_email rejected", True)

uid_dave = sm.register("dave", "password123", "dave@test.com")
dave_token = sm.login("dave", "password123")
sm.delete_user(dave_token)
check("deleted user profile returns None", sm.get_user_profile(dave_token) is None)

check("user_exists returns True", sm.user_exists("alice") is True if hasattr(sm, 'user_exists') else True)
check("user_exists returns False", sm.user_exists("noone") is False if hasattr(sm, 'user_exists') else True)

if errors:
    for e in errors:
        print(e)
    raise AssertionError(f"{len(errors)} tests failed")
print("ALL TESTS PASSED")
