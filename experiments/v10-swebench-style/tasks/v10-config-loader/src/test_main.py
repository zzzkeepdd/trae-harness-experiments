from main import ConfigLoader
import json, os, tempfile

errors = []
def check(desc, cond):
    if not cond:
        errors.append(f"FAIL {desc}")

cl = ConfigLoader()
cl._config["host"] = "localhost"
cl._config["port"] = "8080"
check("get returns value", cl.get("host") == "localhost")
check("get_int works", cl.get_int("port") == 8080)
check("get_bool default", cl.get_bool("nonexistent") == False)
cl._config["enabled"] = "true"
check("get_bool true string", cl.get_bool("enabled") == True)
check("get default for missing", cl.get("missing", "default") == "default")
check("get_int default for missing", cl.get_int("missing", 42) == 42)
cl._config["items"] = ["a", "b"]
check("get_list returns existing list", cl.get_list("items") == ["a", "b"])

tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
tmp.write(json.dumps({"timeout": 30, "debug": True}))
tmp.close()
cl.load_json(tmp.name)
check("load_json loads values", cl.get("timeout") == 30)
check("load_json loads bool", cl.get("debug") == True)
os.unlink(tmp.name)

cl._config["a"] = "${b}"
cl._config["b"] = "resolved"
cl.resolve_variables()
check("variable resolution", cl.get("a") == "resolved")

if errors:
    for e in errors:
        print(e)
    raise AssertionError(f"{len(errors)} tests failed")
print("ALL TESTS PASSED")
