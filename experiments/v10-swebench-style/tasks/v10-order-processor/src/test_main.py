from main import OrderProcessor
from decimal import Decimal

errors = []
def check(desc, cond):
    if not cond:
        errors.append(f"FAIL {desc}")

op = OrderProcessor()
op.add_inventory("item1", 10, 9.99)
op.add_inventory("item2", 5, 19.50)

ord1 = op.process_order("cust1", [("item1", 2)])
check("basic order created", ord1 is not None)
check("order has id", ord1["order_id"].startswith("ORD-"))
check("order total correct", float(ord1["total"]) == 19.98)

ord2 = op.process_order("cust2", [("item1", 1), ("item2", 2)])
check("multi-item order total", float(ord2["total"]) == 48.99)

try:
    op.process_order("cust3", [("item1", 100)])
except ValueError:
    check("insufficient stock rejected", True)
else:
    check("insufficient stock rejected", False)

try:
    op.process_order("cust4", [("nonexistent", 1)])
except ValueError:
    check("unknown item rejected", True)
else:
    check("unknown item rejected", False)

inv = op.get_inventory("item1")
check("inventory after orders", inv is not None and inv["quantity"] == 7)

if errors:
    for e in errors:
        print(e)
    raise AssertionError(f"{len(errors)} tests failed")
print("ALL TESTS PASSED")
