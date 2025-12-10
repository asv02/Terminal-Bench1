Implement a deterministic, in-memory micro-simulator of a retail order-fulfillment network with multiple dark stores (local micro-warehouses). The system must use only the Python standard library and be fully deterministic (no randomness, no clock, no network).

Runtime
- Dependencies: Python standard library only
- Deterministic and offline (no time, randomness, or network I/O)

Style constraints
- Do not use dataclasses anywhere. Do not import `dataclasses` and do not use `@dataclass`.
- `Product` and `Order` must be plain classes with explicit constructors:
    * Product.__init__(self, sku:int, name:str, price:float)
    * Order.__init__(self, order_id:int)   # items/partners/total_amount are set as attributes internally
- Do not use `from __future__ import annotations`.
- Do not use NamedTuple/namedtuple or third-party modeling helpers (e.g., `attrs`, `pydantic`)
anywhere in the file. `Order.items` must be a list of `(sku:int, qty:int, unit_price:float)` tuples.
- `Product` and `Order` must be plain old Python classes (no custom base classes).
- `Product` and `Order` must define `__slots__` to prevent attribute dictionaries:
    * Product.__slots__ == ("sku", "name", "price")
    * Order.__slots__   == ("order_id", "items", "partners", "total_amount")
- Do not use `from typing import ...` (use `import typing` if you must reference typing at all).
- Do not include any `# type: ignore` or `# noqa` comments in the source.

Files to implement
- Provide a single file named /app/retail_fulfillment.py that defines exactly the public API listed below.

Scope & actors (required identifiers)
- Product, ProductFactory, InventoryStore, InventoryManager, ReplenishStrategy, ThresholdReplenishStrategy, DarkStore, DarkStoreManager, Cart, User, Order, OrderManager.

ProductFactory (catalog)
- Fixed mapping:
    101->("Apple", 20.0), 102->("Banana", 10.0), 103->("Chocolate", 50.0),
    201->("TShirt", 500.0), 202->("Jeans", 1000.0).
- Unknown SKU -> name = "Item{sku}" (exact literal, e.g., 9999->"Item9999"), price = 100.0.
- Must expose: ProductFactory.create_product(sku:int) -> Product.
- The SKU_MAP may be mutated by client code at runtime; calls that consult the catalog must use the
current mapping values at the time of the call (no stale caches), except order items must snapshot unit_price.

Inventory system (per store)
- Quantities are non-negative ints keyed by SKU.
- add_product(product, qty): increases stock; ignore non-positive qty.
- remove_product(sku, qty): deduct up to qty; stock never negative (floor at 0). It is permissible to delete the key when quantity is 0.
- check_stock(sku) -> int: 0 for unknown SKUs.
- list_available_products() -> list[Product]:
    * Only SKUs with qty>0 are listed.
    * Must construct Product objects via ProductFactory at call time (no long-lived Product caching).
    * Must be sorted by:
        1) descending quantity,
        2) then ascending SKU.

Replenishment
- ReplenishStrategy must be an abstract base class (inherit from `abc.ABC`) and declare `replenish(self, manager, items_to_replenish: dict[int,int])` with `@abstractmethod`. Direct instantiation MUST fail (i.e., raises `TypeError`).
- ThresholdReplenishStrategy(threshold:int):
    For each (sku, qty) in items_to_replenish, if current stock < threshold and qty>0, add qty; else do nothing.
    Non-positive quantities in items_to_replenish are ignored.
- Strategies MUST NOT mutate the caller's items_to_replenish mapping (no add/remove/overwrite of keys/values).

Dark stores
- Each has name, location (x,y), and an InventoryManager over its InventoryStore.
- distance_to(ux,uy) returns Euclidean distance via math.hypot (implementations relying on other forms may fail ties).
- add_stock/remove_stock/check_stock delegate to the inventory manager.
- get_all_products() returns available products (qty>0) via ProductFactory and adheres to Inventory list ordering.
- set_replenish_strategy(strategy) and run_replenishment(items_to_replenish) (no-op if not set).

DarkStoreManager (singleton-like)
- get_instance() returns the singleton; reset_instance() clears it.
- register_dark_store(store) registers a store (stores are retained in registration order).
- get_nearby_dark_stores(ux,uy,max_distance) returns a NEW list (defensive copy) of stores with distance <= max_distance,
sorted by:
    1) ascending distance (computed with math.hypot),
    2) then ascending store.name for ties in distance,
    3) stability: if both distance and name are equal, preserve registration order.
Mutating the returned list MUST NOT affect internal manager state.

User
- A User has name, location (x, y), and owns a Cart accessible via user.cart, the constructor must set self.cart = Cart().

Cart & pricing
- Holds requested (sku->qty). add_item(sku, qty) accumulates; ignore non-positive qty.
- get_total() = sum(ProductFactory.create_product(sku).price * qty for each sku in cart).
- Order placement MUST NOT mutate the Cart (contents remain unchanged after place_order).

Orders & fulfillment
- Order fields:
    order_id:int (auto-increment starting at 1), items:list[(sku:int, qty:int, unit_price:float)],
    partners:list[str] (store names), total_amount:float.
- OrderManager (singleton-like):
    get_instance(), reset_instance(), get_all_orders() -> list[Order].
    get_all_orders must return a defensive copy (mutating the returned list does not affect the manager).
    place_order(user:User, cart:Cart) -> Order | None with the logic below.
- Fulfillment logic:
    1) If cart is empty -> return None.
    2) Find nearby stores within radius 5.0 (inclusive). If none -> return None.
    3) If the single nearest store can fulfill all SKUs/quantities:
        fulfill entirely from that store; deduct there only; partners = [that_store].
    4) Otherwise (split/partial):
        traverse nearby stores by the ordering above;
        iterate SKUs in ascending numeric order;
        for each SKU, take min(available, remaining_needed) and deduct immediately;
        include a store in partners if it contributed >= 1 unit (preserve traversal order, no duplicates by name);
        build the order with only SKUs that received >= 1 unit.
        Return this order even if total fulfilled quantity is zero (since nearby stores existed).
    5) Order.items MUST be sorted by ascending SKU; for rows with the same SKU, preserve the first-contribution encounter order (stable).
      5a) Row merge rule for items:
          - Contributions for the SAME SKU at the SAME unit_price MUST be COALESCED into a single (sku, qty, unit_price) row by accumulating qty.
          - Contributions for the same SKU at DIFFERENT unit_price MUST be kept as SEPARATE rows (do not merge).
          - Stability within a SKU: rows for one SKU must appear in the order of their first contribution (first-seen wins); the global items list is then sorted by ascending SKU while preserving the relative order of rows that share the same SKU.
    6) For each (sku, qty) in items, unit_price is snapshotted from ProductFactory at order time and never changes.
        If the unit price differs across contributions (e.g., due to catalog mutation during the call),
        the implementation MUST create multiple item rows for the same SKU (one per distinct price) and not merge them.
    7) Append every created order (including zero-amount partials) to the manager's internal list.

Behavioral guarantees & edge cases
- Inventory never goes below 0; removing >= available sets stock to 0.
- check_stock on unknown SKU returns 0.
- Available/listed products must be created via ProductFactory at call time and only include qty>0.
- Distance comparison is inclusive (<=). Equal distance tie-breakers by store.name asc; with identical names, preserve registration order.
- Partners:
    - single-store full fulfillment -> exactly one partner (the nearest by distance/name tie-breaker);
    - split fulfillment -> partners in traversal order, only if contributed >= 1 unit, unique by name, first-occurrence order.
- Pricing for unknown SKUs strictly uses price 100.0 and name "Item{sku}".
- Determinism: Do not import or rely on random, time, datetime, socket, http.client, urllib, or any network/clock source.
- Do not import or use `dataclasses` (no `@dataclass`).

Public API (concise)
- class Product     # __init__(self, sku:int, name:str, price:float)
- class ProductFactory:
    @staticmethod create_product(sku:int) -> Product
- class InventoryStore:
    add_product(product:Product, qty:int) -> None
    remove_product(sku:int, qty:int) -> None
    check_stock(sku:int) -> int
    list_available_products() -> list[Product]
- class InventoryManager:
    add_stock(sku:int, qty:int) -> None
    remove_stock(sku:int, qty:int) -> None
    check_stock(sku:int) -> int
    get_available_products() -> list[Product]
- class ReplenishStrategy(ABC):
    @abstractmethod
    def replenish(self, manager:"InventoryManager", items_to_replenish:dict[int,int]) -> None
- class ThresholdReplenishStrategy(ReplenishStrategy)
- class DarkStore:
    distance_to(ux:float, uy:float) -> float
    add_stock(sku:int, qty:int) -> None
    remove_stock(sku:int, qty:int) -> None
    check_stock(sku:int) -> int
    get_all_products() -> list[Product]
    set_replenish_strategy(strategy:"ReplenishStrategy") -> None
    run_replenishment(items_to_replenish:dict[int,int]) -> None
- class DarkStoreManager:
    @classmethod get_instance() -> "DarkStoreManager"
    @classmethod reset_instance() -> None
    register_dark_store(store:"DarkStore") -> None
    get_nearby_dark_stores(ux:float, uy:float, max_distance:float) -> list["DarkStore"]
- class Cart:
    add_item(sku:int, qty:int) -> None
    get_total() -> float
- class User
- Attributes: name:str, x:float, y:float, cart:Cart (constructor must set self.cart = Cart())
- class Order       # __init__(self, order_id:int); sets items, partners, total_amount internally
- class OrderManager:
    @classmethod get_instance() -> "OrderManager"
    @classmethod reset_instance() -> None
    get_all_orders() -> list["Order"]
    place_order(user:"User", cart:"Cart") -> "Order | None"

CLI demonstration artifacts
- After implementing the module, run the CLI to capture outputs into files under /app.
- Create exactly these files with these minimum contents (each created by a distinct command):

1) /app/_catalog_dump.txt
    <- output of: python3 /app/retail_fulfillment.py catalog
    (first 3 lines must be exactly)
    101 Apple
    102 Banana
    103 Chocolate

2) /app/_unknown_price.txt
    <- output of: python3 /app/retail_fulfillment.py price 9999
    (exact content)
    100.0

3) /app/_list_products_sorted.txt
    <- output of: python3 /app/retail_fulfillment.py list_products_sorted
    Format: each line "<sku> <qty> <name>".
    First two lines MUST be:
    102 5 Banana
    103 5 Chocolate
4) /app/_nearby_sorted.txt
    <- output of: python3 /app/retail_fulfillment.py nearby 0.0 0.0 5.0
    Format: store NAME only per line.
    First four lines MUST be:
    Z
    A
    A
    B
5) /app/_single_fulfill_total.txt
    <- output of: python3 /app/retail_fulfillment.py single_fulfill_demo
    Format: single line numeric total only.
    MUST be:
    60.0
6) /app/_split_partners.txt
    <- output of: python3 /app/retail_fulfillment.py split_demo

7) /app/_partial_zero_items.txt
    <- output of: python3 /app/retail_fulfillment.py partial_demo

8) /app/_orders_dump.txt
    <- output of: python3 /app/retail_fulfillment.py orders_dump

9) /app/_orders_count.txt
    <- output of: python3 /app/retail_fulfillment.py orders_count

10) /app/_defcopy_guard.txt
    <- output of: python3 /app/retail_fulfillment.py defcopy_guard

11) /app/_grep_A_count.txt
    <- output of: { grep -F 'A' /app/_catalog_dump.txt; grep -Fxm1 'A' /app/_nearby_sorted.txt; } | wc -l

12) /app/_awk_first_two.txt
    <- output of: awk 'NR<=2{print}' /app/_catalog_dump.txt

13) /app/_items_sorted_check.txt
    <- output of: python3 /app/retail_fulfillment.py items_sorted_check
    First line MUST be:
    [101, 102]
- Exact strings to assert:
* /app/_unknown_price.txt == "100.0\n"
* First three lines of /app/_catalog_dump.txt are:
    101 Apple
    102 Banana
    103 Chocolate
* /app/_grep_A_count.txt == "2\n"

- The exact multi-line payloads for the CLI artifacts MUST be computed at runtime.
- /app/retail_fulfillment.py MUST NOT contain verbatim multi-line literals that match these artifact outputs.

CLI order-creation semantics
- The following CLI commands MUST each append exactly one order to OrderManager’s internal list:
    - single_fulfill_demo  -> creates one fully fulfilled single-store order
    - split_demo           -> creates one split-fulfillment order across multiple stores
    - partial_demo         -> creates one order with zero items and zero total (nearby stores exist but requested SKUs receive 0 units)
- Consequently:
    - /app/_orders_dump.txt MUST contain exactly 3 lines (one per order created above, in the order they were created).
    - /app/_orders_count.txt MUST contain exactly "3\n".

Performance guidance
- Favor O(1)-average per-SKU operations (dicts/sets) to accommodate ~1e5 SKUs/orders.

Success criteria
- Provide a single-file /app/retail_fulfillment.py implementing the public API above.
- Behavior matches this specification exactly.
- Automated tests will validate the behaviors and edge cases.