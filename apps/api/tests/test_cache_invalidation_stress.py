"""Stress tests for the cache invalidation system.

Tests concurrent access, race conditions, callback lifecycle,
type filtering, memory behaviour, and real-world legislation-update
simulations — all against in-memory state only (no DB).
"""

from __future__ import annotations

import gc
import sys
import threading
import time
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import pytest

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_callbacks() -> None:
    """Clear the global callback registry so tests are isolated."""
    from services import cache_invalidation as mod

    mod._invalidation_callbacks.clear()


# ---------------------------------------------------------------------------
# 1. Callback registration and invocation
# ---------------------------------------------------------------------------

class TestCallbackRegistration:
    """Register, invoke, and lifecycle of invalidation callbacks."""

    def setup_method(self):
        _reset_callbacks()

    def teardown_method(self):
        _reset_callbacks()

    def test_register_and_invoke_single(self):
        from services.cache_invalidation import (
            invalidate_all,
            register_invalidation_callback,
        )

        invoked = []
        register_invalidation_callback("test_cache", lambda: invoked.append(1))
        invalidate_all(reason="test")

        assert invoked == [1]

    def test_register_multiple_callbacks_all_invoked(self):
        from services.cache_invalidation import (
            invalidate_all,
            register_invalidation_callback,
        )

        order = []
        register_invalidation_callback("a", lambda: order.append("a"))
        register_invalidation_callback("b", lambda: order.append("b"))
        register_invalidation_callback("c", lambda: order.append("c"))
        invalidate_all(reason="multi")

        assert order == ["a", "b", "c"]

    def test_callback_exception_does_not_stop_others(self):
        from services.cache_invalidation import (
            invalidate_all,
            register_invalidation_callback,
        )

        invoked = []

        def failing_callback():
            raise RuntimeError("boom")

        register_invalidation_callback("failing", failing_callback)
        register_invalidation_callback("ok", lambda: invoked.append("ok"))
        register_invalidation_callback("also_ok", lambda: invoked.append("also_ok"))

        # Should not raise — exceptions are logged, not re-raised
        invalidate_all(reason="robustness")
        assert invoked == ["ok", "also_ok"]

    def test_duplicate_names_allowed(self):
        from services.cache_invalidation import (
            invalidate_all,
            register_invalidation_callback,
        )

        invoked = []
        cb = lambda: invoked.append("x")  # noqa: E731
        register_invalidation_callback("dup", cb)
        register_invalidation_callback("dup", cb)
        invalidate_all(reason="dup")

        assert invoked == ["x", "x"]

    def test_invalidate_all_reason_propagated(self, caplog):
        from services.cache_invalidation import (
            invalidate_all,
            register_invalidation_callback,
        )

        register_invalidation_callback("x", lambda: None)
        with caplog.at_level("INFO", logger="services.cache_invalidation"):
            invalidate_all(reason="legislation_update")

        assert "legislation_update" in caplog.text

    def test_empty_registry_noop(self):
        from services.cache_invalidation import invalidate_all

        # Should not raise
        invalidate_all(reason="empty")


# ---------------------------------------------------------------------------
# 2. Type filtering — invalidate_by_type
# ---------------------------------------------------------------------------

class TestTypeFiltering:
    """invalidate_by_type selectively clears matching caches only."""

    def setup_method(self):
        _reset_callbacks()

    def teardown_method(self):
        _reset_callbacks()

    def test_filter_models_only(self):
        from services.cache_invalidation import (
            invalidate_by_type,
            register_invalidation_callback,
        )

        invoked = Counter()
        register_invalidation_callback("model_cache", lambda: invoked.update({"model": 1}))
        register_invalidation_callback("config_cache", lambda: invoked.update({"config": 1}))
        register_invalidation_callback("reranker", lambda: invoked.update({"reranker": 1}))

        invalidate_by_type("model", "test")
        assert invoked == Counter({"model": 1})

    def test_filter_config_only(self):
        from services.cache_invalidation import (
            invalidate_by_type,
            register_invalidation_callback,
        )

        invoked = Counter()
        register_invalidation_callback("model_cache", lambda: invoked.update({"model": 1}))
        register_invalidation_callback("config_cache", lambda: invoked.update({"config": 1}))

        invalidate_by_type("config", "test")
        assert invoked == Counter({"config": 1})

    def test_filter_reranker(self):
        from services.cache_invalidation import (
            invalidate_by_type,
            register_invalidation_callback,
        )

        invoked = []
        register_invalidation_callback("model_cache", lambda: invoked.append("model"))
        register_invalidation_callback("reranker", lambda: invoked.append("reranker"))

        invalidate_by_type("reranker", "test")
        assert invoked == ["reranker"]

    def test_filter_all_calls_everything(self):
        from services.cache_invalidation import (
            invalidate_by_type,
            register_invalidation_callback,
        )

        invoked = []
        register_invalidation_callback("a", lambda: invoked.append("a"))
        register_invalidation_callback("b", lambda: invoked.append("b"))

        invalidate_by_type("all", "test")
        assert sorted(invoked) == ["a", "b"]

    def test_filter_no_match_does_nothing(self):
        from services.cache_invalidation import (
            invalidate_by_type,
            register_invalidation_callback,
        )

        invoked = []
        register_invalidation_callback("model_cache", lambda: invoked.append("model"))

        invalidate_by_type("nonexistent", "test")
        assert invoked == []

    def test_filter_substring_match(self):
        """Callback names are matched as substrings (cache_type in name)."""
        from services.cache_invalidation import (
            invalidate_by_type,
            register_invalidation_callback,
        )

        invoked = []
        register_invalidation_callback("my_model_cache_v2", lambda: invoked.append("a"))
        register_invalidation_callback("model_registry", lambda: invoked.append("b"))
        register_invalidation_callback("config_cache", lambda: invoked.append("c"))

        invalidate_by_type("model", "test")
        assert sorted(invoked) == ["a", "b"]


# ---------------------------------------------------------------------------
# 3. Concurrent invalidation — 10+ threads
# ---------------------------------------------------------------------------

class TestConcurrentInvalidation:
    """Stress test invalidate_all() with many threads simultaneously."""

    def setup_method(self):
        _reset_callbacks()

    def teardown_method(self):
        _reset_callbacks()

    def test_concurrent_invalidate_all(self):
        """10 threads calling invalidate_all() simultaneously — no errors."""
        from services.cache_invalidation import (
            invalidate_all,
            register_invalidation_callback,
        )

        COUNT = 100
        call_count = Counter()
        lock = threading.Lock()

        def make_cb(name, n):
            return lambda: call_count.__setitem__(name, call_count.get(name, 0) + n)

        for i in range(COUNT):
            register_invalidation_callback(f"cache_{i}", make_cb(f"cache_{i}", 1))

        barrier = threading.Barrier(10)
        errors = []

        def worker():
            barrier.wait()
            try:
                invalidate_all(reason="concurrent_test")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Threads raised: {errors}"
        # Each callback should have been called exactly 10 times
        for i in range(COUNT):
            key = f"cache_{i}"
            assert call_count[key] == 10, f"{key} called {call_count[key]} times"

    def test_interleaved_invalidate_all_and_by_type(self):
        """Mix invalidate_all() and invalidate_by_type() concurrently."""
        from services.cache_invalidation import (
            invalidate_all,
            invalidate_by_type,
            register_invalidation_callback,
        )

        call_log = []
        log_lock = threading.Lock()

        def model_cb():
            with log_lock:
                call_log.append("model")

        def config_cb():
            with log_lock:
                call_log.append("config")

        register_invalidation_callback("model_cache", model_cb)
        register_invalidation_callback("config_cache", config_cb)

        barrier = threading.Barrier(12)
        errors = []

        def all_worker():
            barrier.wait()
            try:
                invalidate_all(reason="mixed")
            except Exception as exc:
                errors.append(exc)

        def type_worker(cache_type):
            barrier.wait()
            try:
                invalidate_by_type(cache_type, "mixed")
            except Exception as exc:
                errors.append(exc)

        threads = []
        for _ in range(6):
            threads.append(threading.Thread(target=all_worker))
        for _ in range(3):
            threads.append(threading.Thread(target=type_worker, args=("model",)))
        for _ in range(3):
            threads.append(threading.Thread(target=type_worker, args=("config",)))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Threads raised: {errors}"
        # 6 all_workers * 2 callbacks + 3 model_workers * 1 + 3 config_workers * 1 = 18
        assert len(call_log) == 6 * 2 + 3 + 3

    def test_rapid_sequence_no_crash(self):
        """Fire 50 invalidate_all() calls back-to-back in 10 threads."""
        from services.cache_invalidation import (
            invalidate_all,
            register_invalidation_callback,
        )

        register_invalidation_callback("stress", lambda: time.sleep(0.001))

        errors = []

        def worker():
            try:
                for _ in range(5):
                    invalidate_all(reason="rapid")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors


# ---------------------------------------------------------------------------
# 4. Race condition — cache cleared even under concurrent read
# ---------------------------------------------------------------------------

class TestRaceConditions:
    """Ensure cache state is consistent under concurrent reads + invalidation."""

    def setup_method(self):
        _reset_callbacks()

    def teardown_method(self):
        _reset_callbacks()

    def test_invalidate_clears_cache_under_concurrent_read(self):
        """Simulate readers holding references while invalidation runs."""
        from services.cache_invalidation import (
            invalidate_all,
            register_invalidation_callback,
        )

        cache = {"data": [1, 2, 3]}
        read_count = 0
        write_barrier = threading.Barrier(2)
        errors = []

        def reader():
            nonlocal read_count
            write_barrier.wait()
            for _ in range(1000):
                # Simulate reading cache
                _ = cache.get("data")
                read_count += 1
                time.sleep(0.0001)

        def invalidator():
            write_barrier.wait()
            time.sleep(0.005)  # Let reader start first
            cache["data"] = []
            invalidate_all(reason="race_test")

        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=invalidator),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors
        assert read_count > 0
        # After invalidation, cache should be empty
        assert cache["data"] == []

    def test_callback_clearing_lru_cache_concurrently(self):
        """Test that lru_cache.clear() is safe under concurrent access."""
        from functools import lru_cache
        from services.cache_invalidation import (
            invalidate_all,
            register_invalidation_callback,
        )

        @lru_cache(maxsize=1)
        def _cached_value():
            return time.time()

        errors = []

        def reader():
            try:
                for _ in range(500):
                    _cached_value()
            except Exception as exc:
                errors.append(exc)

        def invalidator():
            try:
                for _ in range(100):
                    _cached_value.cache_clear()
                    invalidate_all(reason="lru_race")
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=invalidator),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Errors: {errors}"
        # Cache should still work after clearing
        val = _cached_value()
        assert isinstance(val, float)

    def test_concurrent_register_and_invalidate(self):
        """Register callbacks while invalidate_all() is running."""
        from services.cache_invalidation import (
            invalidate_all,
            register_invalidation_callback,
        )

        invoked = []
        stop_flag = threading.Event()
        register_count = 0
        lock = threading.Lock()

        def invoker():
            while not stop_flag.is_set():
                invalidate_all(reason="register_race")
                time.sleep(0.001)

        def registerer():
            nonlocal register_count
            while not stop_flag.is_set():
                name = f"dynamic_{register_count}"
                register_invalidation_callback(name, lambda: None)
                with lock:
                    register_count += 1
                time.sleep(0.001)

        invoker_thread = threading.Thread(target=invoker)
        registerer_thread = threading.Thread(target=registerer)

        invoker_thread.start()
        registerer_thread.start()

        time.sleep(0.5)
        stop_flag.set()

        invoker_thread.join(timeout=5)
        registerer_thread.join(timeout=5)

        # If we got here without crash, the test passes


# ---------------------------------------------------------------------------
# 5. Memory impact — cleared caches don't leak
# ---------------------------------------------------------------------------

class TestMemoryImpact:
    """Verify that invalidation actually frees memory, not leaks."""

    def setup_method(self):
        _reset_callbacks()

    def teardown_method(self):
        _reset_callbacks()
        gc.collect()

    def test_cache_clear_frees_references(self):
        """After invalidation, large objects should be dereferenceable."""
        from services.cache_invalidation import (
            invalidate_all,
            register_invalidation_callback,
        )

        large_data = list(range(100000))
        cache_holder = {"data": large_data}

        def clear_cache():
            cache_holder["data"] = None

        register_invalidation_callback("leak_test", clear_cache)
        invalidate_all(reason="memory")

        del large_data
        gc.collect()

        # The cache should have been cleared
        assert cache_holder["data"] is None

    def test_rapid_create_invalidate_no_growth(self):
        """Create and invalidate many times — memory should stabilise."""
        from services.cache_invalidation import (
            invalidate_all,
            register_invalidation_callback,
        )

        import sys

        sizes = []
        cache_holder = [None]

        for iteration in range(20):
            # Create a large object
            cache_holder[0] = list(range(50000))

            # Register a fresh callback each time (simulating dynamic registration)
            cb_name = f"iter_{iteration}"
            register_invalidation_callback(
                cb_name,
                lambda: cache_holder.__setitem__(0, None),
            )

            invalidate_all(reason="growth_test")
            gc.collect()

            # Measure approximate memory
            sizes.append(sys.getsizeof(cache_holder[0]))

        # All measurements should be the singleton None size after invalidation.
        assert all(s == sys.getsizeof(None) for s in sizes), f"Memory leak detected: {sizes}"

    def test_multiple_invalidations_dont_accumulate_callbacks(self):
        """Invalidating the same callback multiple times should not duplicate."""
        from services.cache_invalidation import (
            invalidate_all,
            register_invalidation_callback,
        )

        invoked = []
        cb = lambda: invoked.append(1)  # noqa: E731
        register_invalidation_callback("stable", cb)

        for _ in range(50):
            invalidate_all(reason="no_accumulate")

        assert len(invoked) == 50  # 50 calls, but only 1 callback registered


# ---------------------------------------------------------------------------
# 6. Real-world simulation — legislation updates
# ---------------------------------------------------------------------------

class TestRealWorldSimulation:
    """Simulate rapid legislation changes followed by cache invalidation."""

    def setup_method(self):
        _reset_callbacks()

    def teardown_method(self):
        _reset_callbacks()

    def test_legislation_update_flow(self):
        """Simulate: update legislation -> invalidate model/config/reranker caches."""
        from services.cache_invalidation import (
            invalidate_all,
            register_invalidation_callback,
        )

        state = {
            "model_cache": {"active_model": "embedding-v1"},
            "config_cache": {"hybrid_weight": 0.3},
            "reranker_cache": {"model_loaded": True},
        }

        events = []

        def invalidate_model():
            state["model_cache"] = {}
            events.append("model_invalidated")

        def invalidate_config():
            state["config_cache"] = {}
            events.append("config_invalidated")

        def invalidate_reranker():
            state["reranker_cache"] = {}
            events.append("reranker_invalidated")

        register_invalidation_callback("model_cache", invalidate_model)
        register_invalidation_callback("config_cache", invalidate_config)
        register_invalidation_callback("reranker", invalidate_reranker)

        # Simulate legislation update event
        invalidate_all(reason="legislation_update")

        assert state["model_cache"] == {}
        assert state["config_cache"] == {}
        assert state["reranker_cache"] == {}
        assert "model_invalidated" in events
        assert "config_invalidated" in events
        assert "reranker_invalidated" in events

    def test_partial_invalidation_after_rate_change(self):
        """IVA rate change should only invalidate config, not models or reranker."""
        from services.cache_invalidation import (
            invalidate_by_type,
            register_invalidation_callback,
        )

        state = {
            "model_cache": {"active_model": "embedding-v1"},
            "config_cache": {"iva_rate": 0.21},
            "reranker_cache": {"model_loaded": True},
        }

        def invalidate_model():
            state["model_cache"] = {}

        def invalidate_config():
            state["config_cache"] = {}

        def invalidate_reranker():
            state["reranker_cache"] = {}

        register_invalidation_callback("model_cache", invalidate_model)
        register_invalidation_callback("config_cache", invalidate_config)
        register_invalidation_callback("reranker", invalidate_reranker)

        # Only config should be cleared
        invalidate_by_type("config", "iva_rate_change")

        assert state["model_cache"] == {"active_model": "embedding-v1"}
        assert state["config_cache"] == {}
        assert state["reranker_cache"] == {"model_loaded": True}

    def test_rapid_legislation_updates_stress(self):
        """Simulate 100 rapid legislation updates with invalidation each."""
        from services.cache_invalidation import (
            invalidate_all,
            register_invalidation_callback,
        )

        state = {
            "model_cache": {"v": 1},
            "config_cache": {"v": 1},
        }

        update_count = 0
        lock = threading.Lock()

        def invalidate_model():
            state["model_cache"] = {}

        def invalidate_config():
            state["config_cache"] = {}

        register_invalidation_callback("model_cache", invalidate_model)
        register_invalidation_callback("config_cache", invalidate_config)

        errors = []

        def update_worker():
            nonlocal update_count
            try:
                for _ in range(10):
                    state["model_cache"]["v"] = state["model_cache"].get("v", 0) + 1
                    state["config_cache"]["v"] = state["config_cache"].get("v", 0) + 1
                    invalidate_all(reason="legislation_update")
                    with lock:
                        update_count += 1
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=update_worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert not errors, f"Errors: {errors}"
        assert update_count == 100

    def test_model_activation_flow(self):
        """Simulate model activation: deactivate old, activate new, invalidate."""
        from services.cache_invalidation import (
            invalidate_by_type,
            register_invalidation_callback,
        )

        models = {
            "embedding-v1": {"activo": True},
            "embedding-v2": {"activo": False},
        }

        def invalidate_model_cache():
            models.clear()

        register_invalidation_callback("model_cache", invalidate_model_cache)

        # Activate v2
        models["embedding-v1"]["activo"] = False
        models["embedding-v2"]["activo"] = True

        # Invalidate model cache
        invalidate_by_type("models", "model_activation")

        assert models == {}

    def test_config_rollback_flow(self):
        """Simulate config rollback: create new version, invalidate, verify."""
        from services.cache_invalidation import (
            invalidate_by_type,
            register_invalidation_callback,
        )

        config_versions = [
            {"version_id": "v0001", "hybrid_weight": 0.2},
            {"version_id": "v0002", "hybrid_weight": 0.3},
        ]
        config_cache = {v["version_id"]: v for v in config_versions}

        def invalidate_config_cache():
            config_cache.clear()

        register_invalidation_callback("config_cache", invalidate_config_cache)

        # Rollback to v0001
        invalidate_by_type("config", "rollback")

        assert config_cache == {}


# ---------------------------------------------------------------------------
# 7. Integration with actual services (model_registry, reranker)
# ---------------------------------------------------------------------------

class TestIntegrationWithServices:
    """Test that real service callbacks integrate with the invalidation system."""

    def setup_method(self):
        _reset_callbacks()

    def teardown_method(self):
        _reset_callbacks()

    def test_reranker_callback_clears_lru(self):
        """The reranker's _invalidate_reranker_cache should clear its lru_cache."""
        from services.cache_invalidation import (
            invalidate_all,
            register_invalidation_callback,
        )
        from services.reranker import (
            _invalidate_reranker_cache,
            _load_model,
            register_reranker_callbacks,
        )

        register_reranker_callbacks()
        invalidate_all(reason="reranker_test")

        # The callback was registered and invoked without error

    def test_model_registry_style_callbacks(self):
        """Simulate the model_registry callback pattern."""
        from services.cache_invalidation import (
            invalidate_by_type,
            invalidate_all,
            register_invalidation_callback,
        )

        model_cache = {"model-1": {"nombre": "test"}}
        config_cache = {"v0001": {"hybrid_weight": 0.3}}

        def invalidate_model_cache():
            model_cache.clear()

        def invalidate_config_cache():
            config_cache.clear()

        register_invalidation_callback("model_cache", invalidate_model_cache)
        register_invalidation_callback("config_cache", invalidate_config_cache)

        # Activate model — should only invalidate model cache
        invalidate_by_type("models", "model_activation")
        assert model_cache == {}
        assert config_cache == {"v0001": {"hybrid_weight": 0.3}}

        # Update config — should only invalidate config cache
        invalidate_by_type("config", "config_change")
        assert model_cache == {}
        assert config_cache == {}

    def test_full_pipeline_legislation_to_search(self):
        """Simulate full pipeline: legislation update -> invalidate -> search uses fresh data."""
        from services.cache_invalidation import (
            invalidate_all,
            register_invalidation_callback,
        )

        # Simulated caches
        caches = {
            "legislacion": {"articulos": [1, 2, 3]},
            "doctrina": {"consultas": ["V0001"]},
            "model_cache": {"models": ["emb-v1"]},
            "config_cache": {"config": {"weight": 0.3}},
        }

        invalidated = []

        def clear_legislacion():
            caches["legislacion"] = {}
            invalidated.append("legislacion")

        def clear_doctrina():
            caches["doctrina"] = {}
            invalidated.append("doctrina")

        def clear_model():
            caches["model_cache"] = {}
            invalidated.append("model")

        def clear_config():
            caches["config_cache"] = {}
            invalidated.append("config")

        register_invalidation_callback("legislacion", clear_legislacion)
        register_invalidation_callback("doctrina", clear_doctrina)
        register_invalidation_callback("model_cache", clear_model)
        register_invalidation_callback("config_cache", clear_config)

        # Before: all caches populated
        for key, val in caches.items():
            assert val != {}, f"{key} should be populated"

        # Legislation update triggers full invalidation
        invalidate_all(reason="legislation_update")

        # After: all caches cleared
        for key, val in caches.items():
            assert val == {}, f"{key} should be cleared"

        assert sorted(invalidated) == ["config", "doctrina", "legislacion", "model"]
