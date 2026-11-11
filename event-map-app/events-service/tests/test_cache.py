"""Модульные тесты TTL-кэша (ПР6). Время подменяется управляемыми часами."""

from cache import BYPASS, HIT, MISS, TTLCache, event_key, list_key


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make_cache(ttl=60, stale=300, max_entries=100):
    clock = FakeClock()
    return TTLCache(ttl, stale, max_entries=max_entries, clock=clock), clock


def test_miss_then_hit_within_ttl():
    cache, _ = make_cache()
    assert cache.get("k") == (MISS, None)
    cache.set("k", {"v": 1})
    assert cache.get("k") == (HIT, {"v": 1})


def test_entry_expires_after_ttl():
    cache, clock = make_cache(ttl=10)
    cache.set("k", "value")
    clock.now += 9.9
    assert cache.get("k")[0] == HIT
    clock.now += 0.2
    assert cache.get("k") == (MISS, None)


def test_stale_value_available_after_ttl_but_not_after_stale_window():
    cache, clock = make_cache(ttl=10, stale=30)
    cache.set("k", "value")
    clock.now += 20
    assert cache.get("k")[0] == MISS
    assert cache.get_stale("k") == "value"
    clock.now += 25
    assert cache.get_stale("k") is None


def test_invalidate_by_key_and_prefix():
    cache, _ = make_cache()
    cache.set("events:list:a", 1)
    cache.set("events:list:b", 2)
    cache.set("events:item:1", 3)
    cache.set("events:item:2", 4)
    cache.invalidate("events:item:1", prefix="events:list:")
    assert cache.get("events:list:a")[0] == MISS
    assert cache.get("events:list:b")[0] == MISS
    assert cache.get("events:item:1")[0] == MISS
    assert cache.get("events:item:2") == (HIT, 4)


def test_ttl_zero_disables_cache():
    cache, _ = make_cache(ttl=0)
    cache.set("k", 1)
    assert cache.get("k") == (BYPASS, None)
    assert len(cache) == 0


def test_max_entries_evicts_oldest():
    cache, clock = make_cache(max_entries=10)
    for i in range(10):
        clock.now += 1
        cache.set(f"k{i}", i)
    cache.set("new", 99)
    assert len(cache) <= 10
    assert cache.get("new") == (HIT, 99)
    assert cache.get("k0")[0] == MISS


def test_keys_are_normalized():
    assert list_key(1, 20, None, None, None) == list_key(1, 20, "", "", "")
    assert list_key(1, 20, "concert", None, None) != list_key(2, 20, "concert", None, None)
    assert event_key("abc") == "events:item:abc"
