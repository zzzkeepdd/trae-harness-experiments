import json
import time
import threading
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

class OrderProcessor:
    def __init__(self):
        self._inventory = {}
        self._orders = []
        self._order_counter = 0
        self._lock = threading.Lock()

    def add_inventory(self, item_id, quantity, price):
        if not isinstance(item_id, str) or not item_id.strip():
            raise ValueError("item_id must be a non-empty string")
        if not isinstance(quantity, int) or quantity < 0:
            raise ValueError("quantity must be a non-negative integer")
        try:
            dprice = Decimal(str(price))
        except (InvalidOperation, ValueError):
            raise ValueError("price must be a valid number")
        if dprice < 0:
            raise ValueError("price must be non-negative")
        with self._lock:
            self._inventory[item_id] = {"quantity": quantity, "price": dprice}

    def process_order(self, customer_id, items):
        if not items:
            raise ValueError("order must contain at least one item")
        with self._lock:
            order_id = f"ORD-{self._order_counter + 1:06d}"
            total = Decimal("0")
            reservations = []
            for item_id, qty in items:
                if not isinstance(item_id, str):
                    raise ValueError(f"item_id must be string, got {type(item_id)}")
                if not isinstance(qty, int) or qty <= 0:
                    raise ValueError(f"quantity must be a positive integer for {item_id}")
                inv = self._inventory.get(item_id)
                if inv is None:
                    raise ValueError(f"item {item_id} not found")
                if inv["quantity"] < qty:
                    raise ValueError(f"insufficient stock for {item_id}: have {inv['quantity']}, need {qty}")
                inv["quantity"] -= qty
                total += inv["price"] * Decimal(qty)
                reservations.append((item_id, qty))
            total = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if total <= 0:
                for item_id, qty in reservations:
                    self._inventory[item_id]["quantity"] += qty
                raise ValueError("order total must be positive")
            self._order_counter += 1
            order = {
                "order_id": order_id,
                "customer_id": customer_id,
                "items": [(i, q) for i, q in items],
                "total": str(total),
                "timestamp": time.time(),
            }
            self._orders.append(order)
            return order

    def get_order(self, order_id):
        with self._lock:
            for o in self._orders:
                if o["order_id"] == order_id:
                    return dict(o)
            return None

    def get_inventory(self, item_id):
        with self._lock:
            inv = self._inventory.get(item_id)
            if inv is None:
                return None
            return {"quantity": inv["quantity"], "price": str(inv["price"])}

    def get_all_inventory(self):
        with self._lock:
            return {k: {"quantity": v["quantity"], "price": str(v["price"])} for k, v in self._inventory.items()}

    def export_orders_json(self, filepath):
        with self._lock:
            data = self._orders
        with open(filepath, "w") as f:
            json.dump(data, f, default=str)
