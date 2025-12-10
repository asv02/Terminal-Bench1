# This is a template test file. Each of these functions will be called
# by the test harness to evaluate the final state of the terminal

import os
import pathlib
import sys
import inspect
import math
if "/app" not in sys.path:
    sys.path.insert(0, "/app")

import pytest
import importlib.util

_spec = importlib.util.find_spec("retail_fulfillment")

if _spec is None:
    # Module missing: create a proxy that raises at *use* time (so tests import cleanly).
    class _MissingModuleProxy:
        def __getattr__(self, _):
            raise RuntimeError("retail_fulfillment unavailable")

    rf = _MissingModuleProxy()
else:
    import retail_fulfillment as rf


def setup_three_stores():
    """Helper: reset managers, create three dark stores with stock and strategies, and register them."""
    rf.DarkStoreManager.reset_instance()
    rf.OrderManager.reset_instance()

    ds_manager = rf.DarkStoreManager.get_instance()

    dsA = rf.DarkStore("DarkStoreA", 0.0, 0.0)
    dsA.set_replenish_strategy(rf.ThresholdReplenishStrategy(3))
    dsA.add_stock(101, 5)  # Apple
    dsA.add_stock(102, 2)  # Banana

    dsB = rf.DarkStore("DarkStoreB", 4.0, 1.0)
    dsB.set_replenish_strategy(rf.ThresholdReplenishStrategy(3))
    dsB.add_stock(101, 3)   # Apple
    dsB.add_stock(103, 10)  # Chocolate

    dsC = rf.DarkStore("DarkStoreC", 2.0, 3.0)
    dsC.set_replenish_strategy(rf.ThresholdReplenishStrategy(3))
    dsC.add_stock(102, 5)   # Banana
    dsC.add_stock(201, 7)   # T-Shirt

    ds_manager.register_dark_store(dsA)
    ds_manager.register_dark_store(dsB)
    ds_manager.register_dark_store(dsC)

    return ds_manager, dsA, dsB, dsC


def test_nearby_order_single_store_fulfill():
    """Nearest store fully fulfills: one partner, correct stock deductions, exact total."""
    ds_manager, dsA, dsB, dsC = setup_three_stores()
    user = rf.User("Aditya", 1.0, 1.0)
    user.cart.add_item(101, 4)
    user.cart.add_item(102, 2)

    order = rf.OrderManager.get_instance().place_order(user, user.cart)
    assert order is not None
    assert len(order.partners) == 1
    assert dsA.check_stock(101) == 1
    assert dsA.check_stock(102) == 0

    expected_total = (
        4 * rf.ProductFactory.create_product(101).price
        + 2 * rf.ProductFactory.create_product(102).price
    )
    assert order.total_amount == expected_total


def test_split_across_stores():
    """Split fulfillment across multiple nearby stores in ascending distance order; totals and stocks match."""
    ds_manager, dsA, dsB, dsC = setup_three_stores()
    user = rf.User("Aditya", 1.0, 1.0)
    user.cart.add_item(101, 6)  # apples
    user.cart.add_item(102, 3)  # bananas

    order = rf.OrderManager.get_instance().place_order(user, user.cart)
    assert order is not None
    assert len(order.partners) == 3

    # Post-fulfillment inventory
    assert dsA.check_stock(101) == 0
    assert dsA.check_stock(102) == 0
    assert dsB.check_stock(101) == 2
    assert dsC.check_stock(102) == 4

    # Prices and quantities
    expected_total = (6 * 20.0) + (3 * 10.0)
    assert order.total_amount == expected_total

    # Items must be sorted by ascending SKU
    assert [sku for (sku, qty, price) in order.items] == sorted([sku for (sku, qty, price) in order.items])

    fulfilled = {sku: qty for (sku, qty, price) in order.items}
    assert fulfilled[101] == 6
    assert fulfilled[102] == 3


def test_partial_fulfillment_all_unavailable():
    """Cart contains only unavailable SKU; order object is returned with zero items and zero total."""
    ds_manager, dsA, dsB, dsC = setup_three_stores()
    user = rf.User("Aditya", 1.0, 1.0)
    user.cart.add_item(202, 10)  # Jeans unavailable in nearby stores

    order = rf.OrderManager.get_instance().place_order(user, user.cart)
    assert order is not None
    assert len(order.items) == 0
    assert order.total_amount == 0


def test_mixed_partial_fulfillment():
    """One SKU available and another unavailable: only available SKU appears in order items."""
    ds_manager, dsA, dsB, dsC = setup_three_stores()
    user = rf.User("Aditya", 1.0, 1.0)
    user.cart.add_item(101, 2)   # apples available
    user.cart.add_item(202, 5)   # jeans unavailable

    order = rf.OrderManager.get_instance().place_order(user, user.cart)
    assert order is not None
    assert any(sku == 101 for (sku, qty, price) in order.items)
    assert not any(sku == 202 for (sku, qty, price) in order.items)
    assert order.total_amount > 0


def test_unknown_sku_factory():
    """Unknown SKU maps to name 'Item{sku}' and price 100.0."""
    prod = rf.ProductFactory.create_product(9999)
    assert prod.name == "Item9999"
    assert prod.price == 100.0


def test_replenish_trigger_and_no_trigger_and_ignore_nonpositive():
    """Threshold replenishment adds stock only when stock<threshold and qty>0; ignores non-positive quantities."""
    ds_manager, dsA, dsB, dsC = setup_three_stores()

    dsA.run_replenishment({102: 5, 103: 0, 201: -3})
    assert dsA.check_stock(102) == 7  # only 102 added
    assert dsA.check_stock(103) == 0  # ignored as <=0 and nonexistent
    before = dsB.check_stock(103)
    dsB.run_replenishment({103: 5})
    after = dsB.check_stock(103)
    assert before == after


def test_order_saved_in_manager_defensive_copy():
    """Every created order is persisted; get_all_orders returns a defensive copy."""
    ds_manager, dsA, dsB, dsC = setup_three_stores()
    user = rf.User("Aditya", 1.0, 1.0)
    user.cart.add_item(101, 1)

    om = rf.OrderManager.get_instance()
    order = om.place_order(user, user.cart)
    lst = om.get_all_orders()
    assert order in lst
    lst.clear()
    # Internal store must remain intact
    assert len(om.get_all_orders()) == 1


def test_sequential_order_ids():
    """Order IDs start at 1 and increment by 1 for each new order."""
    ds_manager, dsA, dsB, dsC = setup_three_stores()
    user = rf.User("Aditya", 1.0, 1.0)
    user.cart.add_item(101, 1)

    order1 = rf.OrderManager.get_instance().place_order(user, user.cart)
    assert order1.order_id == 1

    user.cart = rf.Cart()
    user.cart.add_item(102, 1)
    order2 = rf.OrderManager.get_instance().place_order(user, user.cart)
    assert order2.order_id == order1.order_id + 1


def test_empty_cart_order():
    """Empty cart returns None (no order created)."""
    ds_manager, dsA, dsB, dsC = setup_three_stores()
    user = rf.User("Aditya", 1.0, 1.0)

    order = rf.OrderManager.get_instance().place_order(user, user.cart)
    assert order is None


def test_no_nearby_store():
    """No nearby stores within radius 5.0 returns None and does not record an order."""
    rf.DarkStoreManager.reset_instance()
    rf.OrderManager.reset_instance()

    ds_manager = rf.DarkStoreManager.get_instance()
    ds_far = rf.DarkStore("FarAway", 100.0, 100.0)
    ds_far.add_stock(101, 10)
    ds_manager.register_dark_store(ds_far)

    user = rf.User("FarUser", 0.0, 0.0)
    user.cart.add_item(101, 1)

    order = rf.OrderManager.get_instance().place_order(user, user.cart)
    assert order is None
    assert len(rf.OrderManager.get_instance().get_all_orders()) == 0


def test_cart_total_and_cart_not_mutated_by_place_order():
    """Cart total equals sum of prices; calling place_order must not mutate the cart."""
    cart = rf.Cart()
    cart.add_item(103, 1)
    cart.add_item(101, 2)
    baseline = cart.get_total()

    rf.DarkStoreManager.reset_instance()
    rf.OrderManager.reset_instance()
    ds = rf.DarkStore("S", 0.0, 0.0)
    ds.add_stock(103, 1)
    ds.add_stock(101, 2)
    rf.DarkStoreManager.get_instance().register_dark_store(ds)

    user = rf.User("U", 0.0, 0.0)
    user.cart = cart
    om = rf.OrderManager.get_instance()
    order = om.place_order(user, cart)
    assert order is not None
    assert cart.get_total() == baseline  # unchanged
    # quantities still present
    assert sorted(cart._items.items()) == sorted({101: 2, 103: 1}.items())

def test_cart_add_item_ignores_non_positive_qty():
    """Cart.add_item must ignore zero or negative quantities and only accumulate positives."""
    cart = rf.Cart()
    price101 = rf.ProductFactory.create_product(101).price

    cart.add_item(101, 0)
    cart.add_item(101, -3)
    assert cart.get_total() == 0.0
    assert getattr(cart, "_items", {}).get(101, 0) == 0

    cart.add_item(101, 2)
    assert getattr(cart, "_items", {}).get(101, 0) == 2
    assert cart.get_total() == 2 * price101


def test_get_nearby_dark_stores_tie_break_and_copy_and_stability():
    """Equal distance tie-breaker by name, stability by registration for identical names, and returned list is a defensive copy."""
    rf.DarkStoreManager.reset_instance()
    m = rf.DarkStoreManager.get_instance()
    s1 = rf.DarkStore("A", 3.0, 4.0)   # distance 5
    s2 = rf.DarkStore("B", -3.0, -4.0) # distance 5
    s3 = rf.DarkStore("Z", 0.0, 0.0)   # distance 0
    s4 = rf.DarkStore("A", -3.0, 4.0)  # distance 5, same name as s1; registration order must resolve tie
    m.register_dark_store(s2)
    m.register_dark_store(s3)
    m.register_dark_store(s1)
    m.register_dark_store(s4)

    out = m.get_nearby_dark_stores(0.0, 0.0, 5.0)
    # Order: Z (0), then A (5) [s1 before s4], then B (5)
    assert [s.name for s in out] == ["Z", "A", "A", "B"]
    assert out[1] is s1 and out[2] is s4  # stability on identical (distance,name)

    out.append(rf.DarkStore("Injected", 0, 0))
    out2 = m.get_nearby_dark_stores(0.0, 0.0, 5.0)
    assert [s.name for s in out2] == ["Z", "A", "A", "B"]  # internal state not affected


def test_fulfillment_excludes_empty_store():
    """A store that provides zero units for requested SKUs must not appear in partners."""
    ds_manager, dsA, dsB, dsC = setup_three_stores()

    dsB.remove_stock(101, dsB.check_stock(101))

    user = rf.User("Aditya", 1.0, 1.0)
    user.cart.add_item(101, 2)

    order = rf.OrderManager.get_instance().place_order(user, user.cart)
    assert order is not None
    assert dsB.name not in order.partners


def test_remove_stock_edge_case():
    """Removing more than available floors the stock at zero (no negatives)."""
    ds_manager, dsA, dsB, dsC = setup_three_stores()
    available = dsA.check_stock(101)
    dsA.remove_stock(101, available + 5)
    assert dsA.check_stock(101) == 0


def test_get_all_products_and_sorting_and_no_caching():
    """Available products must reflect current ProductFactory mapping and be sorted by (-qty, sku)."""
    rf.DarkStoreManager.reset_instance()
    s = rf.DarkStore("S", 0.0, 0.0)
    s.add_stock(101, 2)
    s.add_stock(103, 5)
    s.add_stock(102, 5)
    rf.DarkStoreManager.get_instance().register_dark_store(s)

    # initial ordering by (-qty, sku) => qty 5 for 102,103 then 101; among 102/103, SKU 102 before 103
    names1 = [p.name for p in s.get_all_products()]
    assert names1[:3] == [
        rf.ProductFactory.create_product(102).name,
        rf.ProductFactory.create_product(103).name,
        rf.ProductFactory.create_product(101).name,
    ]

    # mutate catalog name for 101 and ensure it is reflected
    rf.ProductFactory.SKU_MAP[101] = ("AppleRenamed", 20.0)
    names2 = [p.name for p in s.get_all_products()]
    assert "AppleRenamed" in names2


def test_order_split_stores_and_item_sorting_and_sku_iteration():
    """Split traversal must iterate SKUs in ascending order and items must be sorted by SKU."""
    rf.DarkStoreManager.reset_instance()
    rf.OrderManager.reset_instance()

    ds1 = rf.DarkStore("DS1", 0, 0)
    ds2 = rf.DarkStore("DS2", 1, 1)
    # Skewed stocks force split across both for both SKUs
    ds1.add_stock(102, 1)  # Banana
    ds2.add_stock(102, 2)
    ds1.add_stock(101, 1)  # Apple
    ds2.add_stock(101, 2)

    m = rf.DarkStoreManager.get_instance()
    m.register_dark_store(ds1)
    m.register_dark_store(ds2)

    user = rf.User("Bob", 0, 0)
    user.cart.add_item(102, 3)
    user.cart.add_item(101, 3)  # added second to cart; iterator must still handle SKUs in ascending order

    om = rf.OrderManager.get_instance()
    order = om.place_order(user, user.cart)
    assert order is not None

    # Items sorted by SKU ascending
    assert [sku for (sku, qty, price) in order.items] == [101, 102]
    # Both stores contributed and partners preserved by traversal order
    assert order.partners == ["DS1", "DS2"]
    # Totals match
    assert order.total_amount == (3 * 20.0 + 3 * 10.0)


def test_order_single_store():
    """If nearest can fully satisfy, use only that store; single partner and correct total with item sort."""
    rf.DarkStoreManager.reset_instance()
    rf.OrderManager.reset_instance()

    ds = rf.DarkStore("DS1", 0, 0)
    ds.add_stock(101, 5)
    ds.add_stock(102, 5)
    manager = rf.DarkStoreManager.get_instance()
    manager.register_dark_store(ds)

    user = rf.User("Alice", 0, 0)
    user.cart.add_item(102, 3)
    user.cart.add_item(101, 3)

    order_manager = rf.OrderManager.get_instance()
    order = order_manager.place_order(user, user.cart)

    assert order is not None
    assert order.total_amount == (3 * 10.0 + 3 * 20.0)
    # Items must be sorted by SKU ascending
    assert [sku for (sku, qty, price) in order.items] == [101, 102]
    assert order.partners == ["DS1"]


def test_inventory_add_product_ignores_non_positive_qty():
    """InventoryStore.add_product must ignore non-positive qty (no stock change, not listed)."""
    store = rf.InventoryStore()
    prod = rf.ProductFactory.create_product(101)

    store.add_product(prod, 0)
    assert store.check_stock(101) == 0
    assert all(p.sku != 101 for p in store.list_available_products())

    store.add_product(prod, -5)
    assert store.check_stock(101) == 0
    assert all(p.sku != 101 for p in store.list_available_products())

    # sanity: positive add now should work
    store.add_product(prod, 2)
    assert store.check_stock(101) == 2
    assert any(p.sku == 101 for p in store.list_available_products())


def test_inventory_remove_never_negative_and_visibility():
    """Removing >= available floors to 0; SKU with 0 qty should not appear in available products."""
    store = rf.InventoryStore()
    prod = rf.ProductFactory.create_product(102)
    store.add_product(prod, 3)

    store.remove_product(102, 10)  # over-remove
    assert store.check_stock(102) == 0
    assert all(p.sku != 102 for p in store.list_available_products())

    # further removes should be harmless
    store.remove_product(102, 1)
    assert store.check_stock(102) == 0

    # adding again should bring it back
    store.add_product(prod, 1)
    assert store.check_stock(102) == 1
    assert any(p.sku == 102 for p in store.list_available_products())


def test_run_replenishment_no_strategy_is_noop():
    """DarkStore.run_replenishment with no strategy set must be a no-op."""
    store = rf.DarkStore("NoStrat", 0.0, 0.0)
    store.add_stock(101, 2)  # stock below typical threshold
    before = store.check_stock(101)

    store.run_replenishment({101: 5})
    after = store.check_stock(101)

    assert before == after  # unchanged since no strategy attached


def test_darkstoremanager_is_singleton_and_reset_changes_instance():
    """get_instance returns the same object repeatedly; reset_instance replaces it with a fresh one."""
    rf.DarkStoreManager.reset_instance()
    a = rf.DarkStoreManager.get_instance()
    b = rf.DarkStoreManager.get_instance()
    assert a is b

    rf.DarkStoreManager.reset_instance()
    c = rf.DarkStoreManager.get_instance()
    assert c is not a
    assert c is rf.DarkStoreManager.get_instance()


def test_user_has_distinct_carts():
    """Each User must own a distinct Cart instance."""
    u1 = rf.User("U1", 0.0, 0.0)
    u2 = rf.User("U2", 0.0, 0.0)
    assert u1.cart is not u2.cart
    u1.cart.add_item(101, 1)
    assert u2.cart.get_total() == 0.0


def test_snapshot_unit_price_immutable_after_order():
    """Order stores unit_price snapshot; later changes to ProductFactory prices must not affect existing orders."""
    rf.DarkStoreManager.reset_instance()
    rf.OrderManager.reset_instance()
    s = rf.DarkStore("S", 0, 0)
    s.add_stock(101, 1)
    rf.DarkStoreManager.get_instance().register_dark_store(s)
    user = rf.User("U", 0, 0)
    user.cart.add_item(101, 1)

    om = rf.OrderManager.get_instance()
    order = om.place_order(user, user.cart)
    assert order is not None
    original_total = order.total_amount

    # mutate price
    rf.ProductFactory.SKU_MAP[101] = ("Apple", 9999.0)

    # order total remains unchanged
    assert order.total_amount == original_total


def test_mid_fulfillment_price_change_creates_separate_item_rows(monkeypatch):
    """If unit price differs across contributions during a single place_order call, the order must contain
    multiple rows for the same SKU (one per distinct price), with correct quantities and partners preserved."""
    rf.DarkStoreManager.reset_instance()
    rf.OrderManager.reset_instance()

    ds1 = rf.DarkStore("DS1", 0, 0)
    ds2 = rf.DarkStore("DS2", 1, 0)
    ds1.add_stock(101, 1)
    ds2.add_stock(101, 3)

    m = rf.DarkStoreManager.get_instance()
    m.register_dark_store(ds1)
    m.register_dark_store(ds2)

    # Patch create_product so that the first call for sku=101 returns price 20.0,
    # and the second and subsequent calls for sku=101 return price 25.0.
    real = rf.ProductFactory.create_product
    calls = {"n": 0}

    def fake_create(sku: int):
        p = real(sku)
        if sku == 101:
            calls["n"] += 1
            if calls["n"] >= 2:
                # return a different price to simulate catalog mutation mid-fulfillment
                return rf.Product(101, p.name, 25.0)
            else:
                return rf.Product(101, p.name, 20.0)
        return p

    monkeypatch.setattr(rf.ProductFactory, "create_product", staticmethod(fake_create))

    user = rf.User("Zoe", 0, 0)
    user.cart.add_item(101, 4)

    om = rf.OrderManager.get_instance()
    order = om.place_order(user, user.cart)
    assert order is not None
    # Expect two rows for SKU 101: one for 1 unit at 20, one for 3 units at 25; partners DS1 then DS2
    assert order.partners == ["DS1", "DS2"]
    rows = [(sku, qty, price) for (sku, qty, price) in order.items if sku == 101]
    assert len(rows) == 2
    # Items must be sorted by SKU; both rows have sku=101 so original relative order must be preserved by merge logic,
    # but price difference prevents merging. Quantity split must be 1 and 3 in some order; total must be 4.
    assert sorted(q for (_s, q, _p) in rows) == [1, 3]
    assert order.total_amount == (1 * 20.0 + 3 * 25.0)

def test_price_rows_preserve_first_seen_order_when_same_sku():
    """
    When multiple rows exist for the same SKU due to price changes, rows must appear
    in the order their first contribution was created (stable by encounter time).
    """
    rf.DarkStoreManager.reset_instance()
    rf.OrderManager.reset_instance()

    ds1 = rf.DarkStore("DS1", 0, 0)
    ds2 = rf.DarkStore("DS2", 1, 0)
    ds1.add_stock(101, 2)
    ds2.add_stock(101, 2)
    m = rf.DarkStoreManager.get_instance()
    m.register_dark_store(ds1)
    m.register_dark_store(ds2)

    real = rf.ProductFactory.create_product
    calls = {"n": 0}
    def fake_create(sku: int):
        p = real(sku)
        if sku == 101:
            calls["n"] += 1
            # First contribution price 20, next price 25
            return rf.Product(101, p.name, 20.0 if calls["n"] == 1 else 25.0)
        return p

    setattr(rf.ProductFactory, "create_product", staticmethod(fake_create))
    try:
        u = rf.User("U", 0, 0)
        u.cart.add_item(101, 4)
        o = rf.OrderManager.get_instance().place_order(u, u.cart)
        assert [row[2] for row in o.items if row[0] == 101] == [20.0, 25.0]
    finally:
        setattr(rf.ProductFactory, "create_product", staticmethod(real))


def test_banned_imports_absent():
    """Ensure no non-deterministic/network/time libraries are imported in the solution source."""
    import pathlib
    src = pathlib.Path("/app/retail_fulfillment.py").read_text(encoding="utf-8")
    banned = [
        "import random", "from random", "import time", "from time",
        "import datetime", "from datetime",
        "import socket", "from socket", "import http", "from http",
        "import urllib", "from urllib"
    ]
    for needle in banned:
        assert needle not in src, f"found forbidden import: {needle}"

def test_distance_to_calls_math_hypot(monkeypatch):

    calls = {"n": 0, "args": None}

    def fake_hypot(dx, dy):
        calls["n"] += 1
        calls["args"] = (dx, dy)
        # return a distinctive value to ensure caller uses math.hypot's result
        return 123.456789

    # Patch the global math.hypot used by retail_fulfillment.DarkStore.distance_to
    monkeypatch.setattr(math, "hypot", fake_hypot, raising=True)

    s = rf.DarkStore("S", 10.0, -4.0)
    d = s.distance_to(ux=3.0, uy=2.0)
    assert calls["n"] == 1
    assert isinstance(calls["args"][0], float) and isinstance(calls["args"][1], float)
    assert d == 123.456789


def test_source_mentions_math_hypot():

    src = pathlib.Path("/app/retail_fulfillment.py").read_text(encoding="utf-8")
    assert "math.hypot" in src  # explicit requirement from spec


def test_replenishstrategy_is_abstract_and_signature():

    # Must be abstract; direct instantiation should fail
    assert inspect.isabstract(rf.ReplenishStrategy)
    try:
        rf.ReplenishStrategy()
        assert False, "ReplenishStrategy should be abstract and not directly instantiable"
    except TypeError:
        pass

    # Method signature must be (self, manager, items_to_replenish)
    sig = inspect.signature(rf.ReplenishStrategy.replenish)
    params = list(sig.parameters.values())
    assert len(params) == 3
    assert params[0].name == "self"
    assert params[1].name == "manager"
    assert params[2].name == "items_to_replenish"


def test_list_available_products_creates_fresh_products_each_call_and_uses_factory():

    store = rf.InventoryStore()
    # add stock via a Product created now
    store.add_product(rf.ProductFactory.create_product(101), 2)

    first = store.list_available_products()
    assert len(first) == 1 and first[0].sku == 101
    first_id = id(first[0])
    first_name = first[0].name

    # mutate catalog so next call must reflect new name if factory is consulted
    rf.ProductFactory.SKU_MAP[101] = ("AppleRenamed", 20.0)

    second = store.list_available_products()
    assert len(second) == 1 and second[0].sku == 101
    second_id = id(second[0])
    second_name = second[0].name

    assert second_id != first_id, "Products must be freshly constructed per call (no long-lived caching)."
    assert second_name == "AppleRenamed", "Must consult ProductFactory at call time (no stale cache)."
    assert first_name != second_name


def test_list_available_products_excludes_zero_qty_and_no_residual_cache():

    store = rf.InventoryStore()
    store.add_product(rf.ProductFactory.create_product(102), 1)
    # first call should include 102
    assert any(p.sku == 102 for p in store.list_available_products())

    # over-remove to zero; next call must exclude 102
    store.remove_product(102, 5)
    assert all(p.sku != 102 for p in store.list_available_products())


def test_replenishstrategy_is_subclass_of_ABC_and_abstract():
    from abc import ABC
    # must inherit ABC
    assert issubclass(rf.ReplenishStrategy, ABC), "ReplenishStrategy must inherit from abc.ABC"
    # method itself must be abstract
    assert getattr(rf.ReplenishStrategy.replenish, "__isabstractmethod__", False), \
        "replenish() must be decorated with @abstractmethod"
    # direct instantiation must fail
    with pytest.raises(TypeError):
        rf.ReplenishStrategy()  # noqa: F401

def test_replenishstrategy_does_not_mutate_input_mapping():
    """ThresholdReplenishStrategy must treat items_to_replenish as read-only from the caller's POV."""
    rf.DarkStoreManager.reset_instance()
    rf.OrderManager.reset_instance()

    # simple store/manager with some stock
    s = rf.DarkStore("S", 0, 0)
    s.add_stock(101, 1)   # below typical thresholds
    s.add_stock(102, 5)   # above thresholds
    s.set_replenish_strategy(rf.ThresholdReplenishStrategy(3))

    # input mapping with mix of positive/zero/negative quantities
    items = {101: 5, 102: 7, 201: 0, 202: -1}
    snapshot = dict(items)           # shallow copy to compare structure & values
    keys_before = tuple(sorted(items.keys()))
    id_before = id(items)

    # run; strategy must NOT mutate the caller's dict (no pop/del/overwrites)
    s.run_replenishment(items)

    assert id(items) == id_before, "Strategy must not replace the mapping object"
    assert tuple(sorted(items.keys())) == keys_before, "Strategy must not add/remove keys"
    assert items == snapshot, "Strategy must not modify values inside the mapping"

    # sanity: behavior still correct (only 101 should have been topped up)
    assert s.check_stock(101) == 1 + 5   # added because < threshold and qty>0
    assert s.check_stock(102) == 5       # not added (already >= threshold)

def test_no_dataclasses_anywhere_in_source():
    src = pathlib.Path("/app/retail_fulfillment.py").read_text(encoding="utf-8")
    forbidden = ["from dataclasses", "import dataclasses", "@dataclass"]
    for needle in forbidden:
        assert needle not in src, f"dataclasses are forbidden: found '{needle}'"


def test_Product_and_Order_are_not_dataclasses_and_have_expected_inits():
    # not dataclasses (common shortcut that we forbid)
    for cls in (rf.Product, rf.Order):
        assert not hasattr(cls, "__dataclass_fields__"), f"{cls.__name__} must not be a dataclass"

    # Product(sku:int, name:str, price:float)
    psig = inspect.signature(rf.Product.__init__)
    assert list(psig.parameters)[1:] == ["sku", "name", "price"], \
        "Product.__init__ must be (self, sku, name, price)"

    # Order(order_id:int) only; items/partners/total_amount set as attributes internally
    osig = inspect.signature(rf.Order.__init__)
    assert list(osig.parameters)[1:] == ["order_id"], "Order.__init__ must be (self, order_id)"


def test_replenishstrategy_defined_in_module_scope():
    # catch nested/alias definitions; must be the module's class
    assert rf.ReplenishStrategy.__module__ == "retail_fulfillment", \
        "ReplenishStrategy must be defined at module scope in retail_fulfillment.py"
    
def test_no_future_annotations_import():
    src = pathlib.Path("/app/retail_fulfillment.py").read_text(encoding="utf-8")
    assert "from __future__ import annotations" not in src, \
        "Do not use 'from __future__ import annotations' in this task."


def test_no_namedtuple_or_attrs_or_pydantic_anywhere():
    src = pathlib.Path("/app/retail_fulfillment.py").read_text(encoding="utf-8")
    forbidden = [
        "typing.NamedTuple", "NamedTuple",          # typing usage
        "collections.namedtuple", "namedtuple(",    # legacy namedtuple
        "from attrs", "import attrs",               # attrs lib
        "from pydantic", "import pydantic",         # pydantic
    ]
    for needle in forbidden:
        assert needle not in src, f"forbidden construct/library found: {needle}"


def test_Product_and_Order_are_plain_classes_not_subclassing_custom_bases():
    # Only inherit from object (i.e., plain classes, not frameworks / mixins)
    for cls in (rf.Product, rf.Order):
        assert cls.__mro__[1] is object, f"{cls.__name__} must not subclass custom bases"

def test_artifacts_exist_and_contents():
    base = "/app"
    required = [
        "_catalog_dump.txt",
        "_unknown_price.txt",
        "_list_products_sorted.txt",
        "_nearby_sorted.txt",
        "_single_fulfill_total.txt",
        "_split_partners.txt",
        "_partial_zero_items.txt",
        "_orders_dump.txt",
        "_orders_count.txt",
        "_defcopy_guard.txt",
        "_grep_A_count.txt",
        "_awk_first_two.txt",
        "_items_sorted_check.txt",
    ]
    for f in required:
        assert os.path.exists(os.path.join(base, f)), f"Missing {f}"

    assert pathlib.Path("/app/_unknown_price.txt").read_text() == "100.0\n"
    first3 = pathlib.Path("/app/_catalog_dump.txt").read_text().splitlines()[:3]
    assert first3 == ["101 Apple", "102 Banana", "103 Chocolate"]
    assert pathlib.Path("/app/_grep_A_count.txt").read_text() == "2\n"

def test_Product_and_Order_have_required_slots():
    # Enforce memory/shape constraints; blocks dataclass-like and dynamic attrs
    assert hasattr(rf.Product, "__slots__"), "Product must define __slots__"
    assert tuple(rf.Product.__slots__) == ("sku", "name", "price")

    assert hasattr(rf.Order, "__slots__"), "Order must define __slots__"
    assert tuple(rf.Order.__slots__) == ("order_id", "items", "partners", "total_amount")

    # Instances must not have __dict__
    p = rf.ProductFactory.create_product(101)
    assert not hasattr(p, "__dict__"), "Product instances must not have __dict__"

    rf.OrderManager.get_instance()  # just to ensure class is loaded
    rf.OrderManager.reset_instance()  # reset back; not creating Order here

def test_no_from_typing_import_and_no_ignores():
    src = pathlib.Path("/app/retail_fulfillment.py").read_text(encoding="utf-8")
    assert "from typing import" not in src, "Do not use 'from typing import ...'"

    # Disallow code-suppression comments that hide lint/type errors
    assert "# type: ignore" not in src
    assert "# noqa" not in src

def test_cli_list_products_sorted_top_two_exact():
    # Must be exactly "sku qty name" with the ordering (-qty, sku)
    lines = pathlib.Path("/app/_list_products_sorted.txt").read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 2, "Expected at least two lines in _list_products_sorted.txt"
    assert lines[0] == "102 5 Banana"
    assert lines[1] == "103 5 Chocolate"


def test_cli_nearby_sorted_exact_sequence():
    # Must be exactly these 4 lines (no extra spaces), in order
    lines = pathlib.Path("/app/_nearby_sorted.txt").read_text(encoding="utf-8").splitlines()
    assert lines[:4] == ["Z", "A", "A", "B"], "Nearby ordering must be Z, A, A, B"


def test_cli_single_fulfill_total_exact():
    text = pathlib.Path("/app/_single_fulfill_total.txt").read_text(encoding="utf-8")
    assert text == "60.0\n", "Single-fulfill total must be exactly '60.0\\n'"


def test_cli_orders_count_matches_dump_and_is_three():
    count_text = pathlib.Path("/app/_orders_count.txt").read_text(encoding="utf-8")
    dump_lines = pathlib.Path("/app/_orders_dump.txt").read_text(encoding="utf-8").splitlines()
    # Must be exactly 3 and must match the dump line count
    assert count_text == "3\n", "orders_count must be exactly '3\\n'"
    assert int(count_text.strip()) == len(dump_lines), "orders_count must equal number of lines in orders_dump"


def test_cli_items_sorted_check_exact_output():
    # Must print the ordered SKU list on the first line as Python list syntax
    text = pathlib.Path("/app/_items_sorted_check.txt").read_text(encoding="utf-8")
    first_line = text.splitlines()[0] if text else ""
    assert first_line == "[101, 102]", "items_sorted_check must print '[101, 102]' on the first line"

def test_no_literal_cli_artifacts_in_source():
    """
    Guardrail: the CLI demo outputs must be computed, not printed from hardcoded multi-line literals.
    We ban verbatim presence of the exact multi-line payloads in the source file.
    (Single tokens like 'A'/'Z' are fine; we only block full artifact blobs.)
    """
    import pathlib
    src = pathlib.Path("/app/retail_fulfillment.py").read_text(encoding="utf-8")

    banned_multilines = [
        "Z\nA\nA\nB",                             # nearby exact block
        "102 5 Banana\n103 5 Chocolate",         # top-two list_products_sorted block
        "60.0\n",                                 # single_fulfill_total exact line as a literal block
        "[101, 102]\n",                           # items_sorted_check first line verbatim
    ]
    for blob in banned_multilines:
        assert blob not in src, f"Hardcoded CLI artifact detected: {repr(blob)}"

def test_partners_dedup_by_name_when_two_stores_share_name_and_both_contribute():
    """
    Partners de-duplication by store name: If two distinct stores share the same name and both contribute units to the same order, the partners list must include that name exactly once.
    """
    rf.DarkStoreManager.reset_instance()
    rf.OrderManager.reset_instance()

    a1 = rf.DarkStore("A", 0, 0)
    a2 = rf.DarkStore("A", 1, 0)
    b  = rf.DarkStore("B", 0, 1)

    # Stock so that A1 and A2 both contribute to the SAME SKU
    a1.add_stock(101, 1)
    a2.add_stock(101, 2)
    b.add_stock(102, 1)

    m = rf.DarkStoreManager.get_instance()
    m.register_dark_store(a1)
    m.register_dark_store(a2)
    m.register_dark_store(b)

    u = rf.User("U", 0, 0)
    u.cart.add_item(101, 3)  # forces contribution from both A stores

    o = rf.OrderManager.get_instance().place_order(u, u.cart)
    assert o is not None
    # Must include "A" only once even though two distinct stores named "A" contributed
    assert o.partners.count("A") == 1

def test_partners_dedup_by_name_compact():
    """
    Compact form of the partners de-duplication test: Verifies that multiple contributing stores with the same name
    appear once in `order.partners` (unique-by-name, traversal order preserved).
    """
    rf.DarkStoreManager.reset_instance()
    rf.OrderManager.reset_instance()

    a1 = rf.DarkStore("A", 0, 0)
    a2 = rf.DarkStore("A", 1, 0)
    b = rf.DarkStore("B", 0, 1)

    a1.add_stock(101, 1)
    a2.add_stock(101, 2)
    b.add_stock(102, 1)

    m = rf.DarkStoreManager.get_instance()
    m.register_dark_store(a1)
    m.register_dark_store(a2)
    m.register_dark_store(b)

    u = rf.User("U", 0, 0)
    u.cart.add_item(101, 3)

    o = rf.OrderManager.get_instance().place_order(u, u.cart)
    assert o is not None
    assert o.partners.count("A") == 1

def test_inventorymanager_get_available_products_basic_and_ordering():
    """
    InventoryManager.get_available_products: returns only qty>0 Products and is sorted by
    (-qty, sku) exactly as specified (descending quantity, then ascending SKU).
    """
    import retail_fulfillment as rf
    st = rf.InventoryStore()
    im = rf.InventoryManager(st)
    st.add_product(rf.ProductFactory.create_product(101), 2)
    st.add_product(rf.ProductFactory.create_product(103), 5)
    st.add_product(rf.ProductFactory.create_product(102), 5)
    st.add_product(rf.ProductFactory.create_product(201), 0)  # zero must be excluded
    out = im.get_available_products()
    assert [p.sku for p in out] == [102, 103, 101]  # (-qty, sku): 5/102, 5/103, then 2/101
    assert all(p.sku != 201 for p in out)

def test_check_stock_unknown_sku_returns_zero_in_store_and_manager():
    """
    check_stock: unknown SKU must return 0 for InventoryStore and InventoryManager.
    (DarkStore delegates to manager, already indirectly covered elsewhere.)
    """
    import retail_fulfillment as rf
    st = rf.InventoryStore()
    im = rf.InventoryManager(st)
    unknown = 999_999
    assert st.check_stock(unknown) == 0
    assert im.check_stock(unknown) == 0

def test_strategy_direct_call_does_not_mutate_input_mapping():
    """
    Strategy non-mutation: call ThresholdReplenishStrategy.replenish(...) directly and assert
    the input mapping object and its contents are unchanged.
    """
    import retail_fulfillment as rf
    st = rf.InventoryStore()
    im = rf.InventoryManager(st)
    # one SKU below threshold (should be topped up), one at/above threshold (ignored)
    st.add_product(rf.ProductFactory.create_product(101), 1)
    st.add_product(rf.ProductFactory.create_product(102), 3)
    strat = rf.ThresholdReplenishStrategy(3)

    items = {101: 5, 102: 7, 201: 0, 202: -1}
    snapshot = dict(items)
    obj_id = id(items)
    keys_before = tuple(sorted(items.keys()))

    strat.replenish(im, items)  # direct strategy call

    # mapping identity and contents must be unchanged
    assert id(items) == obj_id
    assert tuple(sorted(items.keys())) == keys_before
    assert items == snapshot

    # sanity: effect on inventory still correct
    assert im.check_stock(101) == 6  # 1 + 5 (was below threshold and qty>0)
    assert im.check_stock(102) == 3  # unchanged (already >= threshold)
