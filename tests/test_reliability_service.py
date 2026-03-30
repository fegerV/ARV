import asyncio
import importlib
import sys
from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_circuit_breaker_success_open_half_open_and_stats(monkeypatch):
    mod = _module()
    config = mod.CircuitBreakerConfig(failure_threshold=2, timeout=5, success_threshold=2)
    breaker = mod.CircuitBreaker("demo", config)

    assert await breaker.call(lambda: "ok") == "ok"
    assert breaker.get_stats()["total_successes"] == 1

    async def _fail():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        await breaker.call(_fail)
    with pytest.raises(ValueError):
        await breaker.call(_fail)

    assert breaker.state == mod.CircuitState.OPEN

    with pytest.raises(mod.CircuitBreakerOpenError):
        await breaker.call(lambda: "blocked")

    breaker.last_failure_time = 10
    breaker.success_count = 0
    monkeypatch.setattr(mod.time, "time", lambda: 20)

    assert await breaker.call(lambda: "recovered-1") == "recovered-1"
    assert breaker.state == mod.CircuitState.HALF_OPEN
    assert await breaker.call(lambda: "recovered-2") == "recovered-2"
    assert breaker.state == mod.CircuitState.CLOSED
    assert breaker.get_stats()["failure_rate"] > 0


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_failure_reopens():
    mod = _module()
    breaker = mod.CircuitBreaker("demo", mod.CircuitBreakerConfig(failure_threshold=1, success_threshold=1))
    breaker.state = mod.CircuitState.HALF_OPEN

    with pytest.raises(RuntimeError):
        await breaker.call(_async_fail(RuntimeError("fail")))

    assert breaker.state == mod.CircuitState.OPEN


@pytest.mark.asyncio
async def test_retry_handler_execute_and_delay_calculation(monkeypatch):
    mod = _module()
    sleep_calls = []
    monkeypatch.setattr(mod.asyncio, "sleep", _async_record(sleep_calls))
    monkeypatch.setattr(mod.random, "uniform", lambda a, b: 0.5)

    handler = mod.RetryHandler(
        "svc",
        mod.RetryConfig(max_attempts=3, base_delay=1.0, backoff_multiplier=2.0, jitter=True),
    )

    attempts = {"count": 0}

    async def _sometimes():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("retry me")
        return "done"

    assert await handler.execute_with_retry(_sometimes) == "done"
    assert len(sleep_calls) == 2

    fixed = mod.RetryHandler("svc", mod.RetryConfig(strategy=mod.RetryStrategy.FIXED_DELAY, base_delay=2, jitter=False))
    linear = mod.RetryHandler("svc", mod.RetryConfig(strategy=mod.RetryStrategy.LINEAR_BACKOFF, base_delay=2, jitter=False))
    none = mod.RetryHandler("svc", mod.RetryConfig(strategy=mod.RetryStrategy.NO_RETRY, base_delay=2, jitter=False))

    assert fixed._calculate_delay(3) == 2
    assert linear._calculate_delay(3) == 6
    assert none._calculate_delay(3) == 0

    failing = mod.RetryHandler("svc", mod.RetryConfig(max_attempts=2, jitter=False))
    with pytest.raises(RuntimeError):
        await failing.execute_with_retry(_async_fail(RuntimeError("nope")))


@pytest.mark.asyncio
async def test_health_checker_check_health_and_overall(monkeypatch):
    mod = _module()
    checker = _make_health_checker(mod)

    checker.register_check(mod.HealthCheck("async_ok", _async_return(True), critical=True))
    checker.register_check(mod.HealthCheck("sync_degraded", lambda: "slow", critical=False))
    checker.register_check(mod.HealthCheck("dict_ok", _async_return({"status": "healthy", "message": "great", "details": {"x": 1}})))
    checker.register_check(mod.HealthCheck("boom", _async_fail(RuntimeError("broken"))))

    async def _timeout(awaitable, *args, **kwargs):
        awaitable.close()
        raise asyncio.TimeoutError()

    monkeypatch.setattr(mod.asyncio, "wait_for", _timeout)
    timeout_only = await checker.check_health("async_ok")
    assert timeout_only["async_ok"]["status"] == mod.HealthStatus.UNHEALTHY.value

    monkeypatch.setattr(mod.asyncio, "wait_for", _passthrough_wait_for)
    results = await checker.check_health()

    assert results["async_ok"]["status"] == mod.HealthStatus.HEALTHY.value
    assert results["sync_degraded"]["status"] == mod.HealthStatus.DEGRADED.value
    assert results["dict_ok"]["details"] == {"x": 1}
    assert results["boom"]["status"] == mod.HealthStatus.UNHEALTHY.value

    missing = await checker.check_health("missing")
    assert missing["missing"]["status"] == mod.HealthStatus.UNKNOWN.value

    overall = await checker.get_overall_health()
    assert overall["status"] == mod.HealthStatus.UNHEALTHY.value


@pytest.mark.asyncio
async def test_monitoring_loop_sends_alerts_and_honors_cooldown(monkeypatch):
    mod = _module()
    checker = _make_health_checker(mod)
    checker.last_results = {
        "db": {"status": mod.HealthStatus.UNHEALTHY.value, "error": "down"},
        "cache": {"status": mod.HealthStatus.DEGRADED.value, "message": "slow", "details": {"latency": 3}},
    }
    checker.health_checks = {
        "db": mod.HealthCheck("db", lambda: True, critical=True),
        "cache": mod.HealthCheck("cache", lambda: True, critical=False),
    }

    async def _check_health():
        return checker.last_results

    async def _overall():
        return {"status": mod.HealthStatus.UNHEALTHY.value}

    checker.check_health = _check_health
    checker.get_overall_health = _overall

    sent = {"count": 0, "alerts": None}
    fake_alert_module = SimpleNamespace(
        Alert=lambda **kwargs: SimpleNamespace(**kwargs),
        send_critical_alerts=_capture_alerts(sent),
    )
    monkeypatch.setitem(sys.modules, "app.services.alert_service", fake_alert_module)
    monkeypatch.setitem(sys.modules, "psutil", SimpleNamespace(cpu_percent=lambda interval=0.1: 12.0, virtual_memory=lambda: SimpleNamespace(percent=34.0)))

    ticks = {"count": 0}

    async def _sleep(seconds):
        ticks["count"] += 1
        if ticks["count"] > 1:
            raise asyncio.CancelledError()

    now = {"value": 1000.0}

    def _time():
        now["value"] += 400
        return now["value"]

    monkeypatch.setattr(mod.asyncio, "sleep", _sleep)
    monkeypatch.setattr(mod.time, "time", _time)

    with pytest.raises(asyncio.CancelledError):
        await checker._monitoring_loop()

    assert sent["count"] == 1
    assert len(sent["alerts"]) == 2


@pytest.mark.asyncio
async def test_reliability_service_helpers_and_stats(monkeypatch):
    mod = _module()
    service = _make_service(mod)

    cb = service.get_circuit_breaker("svc")
    retry = service.get_retry_handler("svc")

    assert service.get_circuit_breaker("svc") is cb
    assert service.get_retry_handler("svc") is retry
    assert {"database", "redis", "storage"} <= set(service.health_checker.health_checks.keys())

    service.health_checker.get_overall_health = _async_return({"status": "healthy", "checks": {}})
    stats = await service.get_reliability_stats()
    assert stats["health_status"]["status"] == "healthy"
    assert "timestamp" in stats

    called = {}

    class _FakeCB:
        async def call(self, func, *args, **kwargs):
            called["args"] = args
            return await func(*args, **kwargs)

    class _FakeRetry:
        async def execute_with_retry(self, func, *args, **kwargs):
            called["retried"] = True
            return await func()

    service.get_circuit_breaker = lambda service_name, config=None: _FakeCB()
    service.get_retry_handler = lambda service_name, config=None: _FakeRetry()

    async def _sum(a, b):
        return a + b

    assert await service.reliable_call("svc", _sum, 2, 3) == 5
    assert called["args"] == (2, 3)
    assert called["retried"] is True


@pytest.mark.asyncio
async def test_decorators_delegate_to_global_reliability_service(monkeypatch):
    mod = _module()
    recorded = {}

    async def _reliable_call(service_name, func, *args, **kwargs):
        kwargs.pop("circuit_breaker_config", None)
        kwargs.pop("retry_config", None)
        recorded["reliable"] = (service_name, args, kwargs)
        return await func(*args, **kwargs)

    class _FakeCB:
        async def call(self, func, *args, **kwargs):
            recorded["cb"] = (args, kwargs)
            return await func(*args, **kwargs)

    class _FakeRetry:
        async def execute_with_retry(self, func, *args, **kwargs):
            recorded["retry"] = (args, kwargs)
            return await func(*args, **kwargs)

    monkeypatch.setattr(
        mod,
        "reliability_service",
        SimpleNamespace(
            reliable_call=_reliable_call,
            get_circuit_breaker=lambda service_name, config=None: _FakeCB(),
            get_retry_handler=lambda service_name, config=None: _FakeRetry(),
        ),
    )

    @mod.circuit_breaker("cb-service")
    async def _cb_func(x):
        return x + 1

    @mod.retry("retry-service")
    async def _retry_func(x):
        return x + 2

    @mod.reliable("reliable-service")
    async def _reliable_func(x):
        return x + 3

    assert await _cb_func(1) == 2
    assert await _retry_func(1) == 3
    assert await _reliable_func(1) == 4
    assert recorded["reliable"][0] == "reliable-service"


def _module():
    return importlib.import_module("app.services.reliability_service")


def _make_health_checker(mod):
    class _Loop:
        def create_task(self, coro):
            coro.close()
            return "task"

    original = mod.asyncio.get_running_loop
    mod.asyncio.get_running_loop = lambda: _Loop()
    try:
        return mod.HealthChecker()
    finally:
        mod.asyncio.get_running_loop = original


def _make_service(mod):
    class _Loop:
        def create_task(self, coro):
            coro.close()
            return "task"

    original = mod.asyncio.get_running_loop
    mod.asyncio.get_running_loop = lambda: _Loop()
    try:
        return mod.ReliabilityService()
    finally:
        mod.asyncio.get_running_loop = original


async def _passthrough_wait_for(awaitable, timeout=None):
    return await awaitable


def _capture_alerts(state):
    async def _inner(alerts, metrics):
        state["count"] += 1
        state["alerts"] = alerts
        state["metrics"] = metrics

    return _inner


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner


def _async_fail(exc):
    async def _inner(*args, **kwargs):
        raise exc

    return _inner


def _async_record(calls):
    async def _inner(delay):
        calls.append(delay)

    return _inner
