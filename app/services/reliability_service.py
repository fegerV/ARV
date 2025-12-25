"""
Reliability and Monitoring Service with Circuit Breaker, Retry Logic, and Health Checks.
"""
import asyncio
import time
import random
from typing import Any, Callable, Optional, Dict, List, Union
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import structlog
import json
from datetime import datetime, timedelta
import traceback

from prometheus_client import Counter, Histogram, Gauge

logger = structlog.get_logger()

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, calls fail fast
    HALF_OPEN = "half_open"  # Testing if service has recovered

class RetryStrategy(Enum):
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    NO_RETRY = "no_retry"

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5          # Failures before opening
    timeout: int = 60                  # Seconds to wait before trying again
    success_threshold: int = 3          # Successes to close circuit
    monitoring_period: int = 300       # Seconds to monitor for health
    expected_exceptions: List[type] = field(default_factory=lambda: [Exception])

@dataclass
class RetryConfig:
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True

@dataclass
class HealthCheck:
    name: str
    check_func: Callable[[], Any]
    timeout: float = 5.0
    critical: bool = True

# Prometheus metrics
CIRCUIT_BREAKER_STATE = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half_open)',
    ['service']
)

CIRCUIT_BREAKER_FAILURES = Counter(
    'circuit_breaker_failures_total',
    'Total circuit breaker failures',
    ['service']
)

RETRY_ATTEMPTS = Counter(
    'retry_attempts_total',
    'Total retry attempts',
    ['service', 'attempt']
)

HEALTH_CHECK_STATUS = Gauge(
    'health_check_status',
    'Health check status (1=healthy, 0=unhealthy)',
    ['check_name', 'service']
)

OPERATION_DURATION = Histogram(
    'operation_duration_seconds',
    'Operation duration',
    ['service', 'operation', 'status']
)

class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance."""
    
    def __init__(self, service_name: str, config: CircuitBreakerConfig):
        self.service_name = service_name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        self.lock = asyncio.Lock()
        
        # Metrics
        self.total_requests = 0
        self.total_failures = 0
        self.total_successes = 0
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        
        async with self.lock:
            # Check if circuit is open
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    CIRCUIT_BREAKER_STATE.labels(service=self.service_name).set(2)
                    logger.info("circuit_breaker_half_open", service=self.service_name)
                else:
                    raise CircuitBreakerOpenError(f"Circuit breaker open for {self.service_name}")
            
            self.total_requests += 1
        
        start_time = time.time()
        
        try:
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Record success
            await self._record_success()
            
            # Record metrics
            OPERATION_DURATION.labels(
                service=self.service_name,
                operation='circuit_breaker_call',
                status='success'
            ).observe(time.time() - start_time)
            
            return result
            
        except Exception as e:
            # Record failure
            await self._record_failure(e)
            
            # Record metrics
            OPERATION_DURATION.labels(
                service=self.service_name,
                operation='circuit_breaker_call',
                status='failure'
            ).observe(time.time() - start_time)
            
            # Re-raise if it's an expected exception
            if any(isinstance(e, exc_type) for exc_type in self.config.expected_exceptions):
                raise
            else:
                raise
    
    async def _record_success(self) -> None:
        """Record successful operation."""
        async with self.lock:
            self.success_count += 1
            self.total_successes += 1
            self.last_success_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    CIRCUIT_BREAKER_STATE.labels(service=self.service_name).set(0)
                    logger.info("circuit_breaker_closed", service=self.service_name)
    
    async def _record_failure(self, exception: Exception) -> None:
        """Record failed operation."""
        async with self.lock:
            self.failure_count += 1
            self.total_failures += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    self.state = CircuitState.OPEN
                    CIRCUIT_BREAKER_STATE.labels(service=self.service_name).set(1)
                    CIRCUIT_BREAKER_FAILURES.labels(service=self.service_name).inc()
                    logger.warning(
                        "circuit_breaker_opened",
                        service=self.service_name,
                        failures=self.failure_count,
                        threshold=self.config.failure_threshold
                    )
            elif self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                CIRCUIT_BREAKER_STATE.labels(service=self.service_name).set(1)
                CIRCUIT_BREAKER_FAILURES.labels(service=self.service_name).inc()
                logger.warning("circuit_breaker_reopened", service=self.service_name)
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset."""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.config.timeout
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            'service': self.service_name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'total_requests': self.total_requests,
            'total_failures': self.total_failures,
            'total_successes': self.total_successes,
            'failure_rate': self.total_failures / self.total_requests if self.total_requests > 0 else 0,
            'last_failure_time': self.last_failure_time,
            'last_success_time': self.last_success_time
        }

class RetryHandler:
    """Retry handler with multiple backoff strategies."""
    
    def __init__(self, service_name: str, config: RetryConfig):
        self.service_name = service_name
        self.config = config
    
    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Log successful attempt (if not first attempt)
                if attempt > 1:
                    logger.info(
                        "retry_success",
                        service=self.service_name,
                        attempt=attempt,
                        max_attempts=self.config.max_attempts
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Record retry attempt
                RETRY_ATTEMPTS.labels(
                    service=self.service_name,
                    attempt=str(attempt)
                ).inc()
                
                # Don't retry on last attempt
                if attempt == self.config.max_attempts:
                    logger.error(
                        "retry_exhausted",
                        service=self.service_name,
                        attempt=attempt,
                        max_attempts=self.config.max_attempts,
                        error=str(e)
                    )
                    raise
                
                # Calculate delay
                delay = self._calculate_delay(attempt)
                
                logger.warning(
                    "retry_attempt",
                    service=self.service_name,
                    attempt=attempt,
                    max_attempts=self.config.max_attempts,
                    delay=delay,
                    error=str(e)
                )
                
                await asyncio.sleep(delay)
        
        # This should never be reached
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        
        if self.config.strategy == RetryStrategy.NO_RETRY:
            return 0
        
        elif self.config.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.config.base_delay
        
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.base_delay * attempt
        
        elif self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.base_delay * (self.config.backoff_multiplier ** (attempt - 1))
        
        else:
            delay = self.config.base_delay
        
        # Apply max delay limit
        delay = min(delay, self.config.max_delay)
        
        # Add jitter if enabled
        if self.config.jitter:
            jitter = random.uniform(0, delay * 0.1)  # 10% jitter
            delay += jitter
        
        return delay

class HealthChecker:
    """Health checker for monitoring service health."""
    
    def __init__(self):
        self.health_checks: Dict[str, HealthCheck] = {}
        self.last_results: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()
        
        # Background monitoring task
        asyncio.create_task(self._monitoring_loop())
    
    def register_check(self, health_check: HealthCheck) -> None:
        """Register a health check."""
        self.health_checks[health_check.name] = health_check
        logger.info("health_check_registered", name=health_check.name, critical=health_check.critical)
    
    async def check_health(self, check_name: Optional[str] = None) -> Dict[str, Any]:
        """Execute health check(s)."""
        
        if check_name:
            checks_to_run = {check_name: self.health_checks.get(check_name)}
        else:
            checks_to_run = self.health_checks
        
        results = {}
        
        for name, health_check in checks_to_run.items():
            if not health_check:
                results[name] = {
                    'status': HealthStatus.UNKNOWN.value,
                    'error': 'Health check not found',
                    'timestamp': datetime.utcnow().isoformat()
                }
                continue
            
            start_time = time.time()
            
            try:
                # Execute health check with timeout
                if asyncio.iscoroutinefunction(health_check.check_func):
                    result = await asyncio.wait_for(
                        health_check.check_func(),
                        timeout=health_check.timeout
                    )
                else:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(health_check.check_func),
                        timeout=health_check.timeout
                    )
                
                duration = time.time() - start_time
                
                # Determine health status
                if isinstance(result, dict):
                    status = result.get('status', HealthStatus.HEALTHY.value)
                    message = result.get('message', 'OK')
                    details = result.get('details', {})
                elif result is True or result is None:
                    status = HealthStatus.HEALTHY.value
                    message = 'OK'
                    details = {}
                else:
                    status = HealthStatus.DEGRADED.value
                    message = str(result)
                    details = {'result': str(result)}
                
                results[name] = {
                    'status': status,
                    'message': message,
                    'details': details,
                    'duration': duration,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                # Update metrics
                is_healthy = status in [HealthStatus.HEALTHY.value, HealthStatus.DEGRADED.value]
                HEALTH_CHECK_STATUS.labels(
                    check_name=name,
                    service='vertex_ar'
                ).set(1 if is_healthy else 0)
                
            except asyncio.TimeoutError:
                results[name] = {
                    'status': HealthStatus.UNHEALTHY.value,
                    'error': f'Health check timed out after {health_check.timeout}s',
                    'duration': health_check.timeout,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                HEALTH_CHECK_STATUS.labels(
                    check_name=name,
                    service='vertex_ar'
                ).set(0)
                
            except Exception as e:
                results[name] = {
                    'status': HealthStatus.UNHEALTHY.value,
                    'error': str(e),
                    'traceback': traceback.format_exc(),
                    'duration': time.time() - start_time,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                HEALTH_CHECK_STATUS.labels(
                    check_name=name,
                    service='vertex_ar'
                ).set(0)
        
        # Store results
        async with self.lock:
            if check_name:
                self.last_results.update(results)
            else:
                self.last_results = results
        
        return results
    
    async def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        
        if not self.last_results:
            return {
                'status': HealthStatus.UNKNOWN.value,
                'message': 'No health checks performed',
                'checks': {}
            }
        
        critical_failures = 0
        total_checks = 0
        degraded_checks = 0
        
        for name, result in self.last_results.items():
            health_check = self.health_checks.get(name)
            if not health_check:
                continue
            
            total_checks += 1
            
            if result['status'] == HealthStatus.UNHEALTHY.value:
                if health_check.critical:
                    critical_failures += 1
            elif result['status'] == HealthStatus.DEGRADED.value:
                degraded_checks += 1
        
        # Determine overall status
        if critical_failures > 0:
            overall_status = HealthStatus.UNHEALTHY
            message = f"{critical_failures} critical health check(s) failed"
        elif degraded_checks > 0:
            overall_status = HealthStatus.DEGRADED
            message = f"{degraded_checks} health check(s) degraded"
        else:
            overall_status = HealthStatus.HEALTHY
            message = "All health checks passing"
        
        return {
            'status': overall_status.value,
            'message': message,
            'checks': self.last_results,
            'summary': {
                'total_checks': total_checks,
                'critical_failures': critical_failures,
                'degraded_checks': degraded_checks
            },
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def _monitoring_loop(self):
        """Background monitoring loop."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self.check_health()
            except Exception as e:
                logger.error("health_monitoring_loop_error", error=str(e))

class ReliabilityService:
    """Main reliability service combining circuit breaker, retry, and health checks."""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_handlers: Dict[str, RetryHandler] = {}
        self.health_checker = HealthChecker()
        
        # Register default health checks
        self._register_default_health_checks()
    
    def get_circuit_breaker(
        self,
        service_name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get or create circuit breaker for service."""
        
        if service_name not in self.circuit_breakers:
            config = config or CircuitBreakerConfig()
            self.circuit_breakers[service_name] = CircuitBreaker(service_name, config)
        
        return self.circuit_breakers[service_name]
    
    def get_retry_handler(
        self,
        service_name: str,
        config: Optional[RetryConfig] = None
    ) -> RetryHandler:
        """Get or create retry handler for service."""
        
        if service_name not in self.retry_handlers:
            config = config or RetryConfig()
            self.retry_handlers[service_name] = RetryHandler(service_name, config)
        
        return self.retry_handlers[service_name]
    
    def reliable_call(
        self,
        service_name: str,
        func: Callable,
        *args,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        retry_config: Optional[RetryConfig] = None,
        **kwargs
    ) -> Any:
        """Execute function with circuit breaker and retry protection."""
        
        # Get circuit breaker and retry handler
        cb = self.get_circuit_breaker(service_name, circuit_breaker_config)
        retry_handler = self.get_retry_handler(service_name, retry_config)
        
        # Execute with retry and circuit breaker
        async def protected_call():
            return await cb.call(func, *args, **kwargs)
        
        return retry_handler.execute_with_retry(protected_call)
    
    def _register_default_health_checks(self):
        """Register default health checks."""
        
        # Database health check
        async def check_database():
            try:
                from app.core.database import get_db
                async for db in get_db():
                    await db.execute("SELECT 1")
                    return True
            except Exception as e:
                return {'status': 'unhealthy', 'error': str(e)}
        
        self.health_checker.register_check(
            HealthCheck("database", check_database, critical=True)
        )
        
        # Redis health check
        async def check_redis():
            try:
                from app.core.redis import redis_client
                await redis_client.ping()
                return True
            except Exception as e:
                return {'status': 'unhealthy', 'error': str(e)}
        
        self.health_checker.register_check(
            HealthCheck("redis", check_redis, critical=True)
        )
        
        # Storage health check
        async def check_storage():
            try:
                from pathlib import Path
                storage_path = Path(settings.STORAGE_BASE_PATH)
                if storage_path.exists():
                    # Test write
                    test_file = storage_path / ".health_check"
                    test_file.write_text("test")
                    test_file.unlink()
                    return True
                else:
                    return {'status': 'unhealthy', 'error': 'Storage path not accessible'}
            except Exception as e:
                return {'status': 'unhealthy', 'error': str(e)}
        
        self.health_checker.register_check(
            HealthCheck("storage", check_storage, critical=False)
        )
    
    async def get_reliability_stats(self) -> Dict[str, Any]:
        """Get comprehensive reliability statistics."""
        
        stats = {
            'circuit_breakers': {},
            'health_status': await self.health_checker.get_overall_health(),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Circuit breaker stats
        for name, cb in self.circuit_breakers.items():
            stats['circuit_breakers'][name] = cb.get_stats()
        
        return stats

# Custom exception for circuit breaker
class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass

# Decorators for easy usage
def circuit_breaker(
    service_name: str,
    config: Optional[CircuitBreakerConfig] = None
):
    """Decorator to add circuit breaker protection to functions."""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cb = reliability_service.get_circuit_breaker(service_name, config)
            return await cb.call(func, *args, **kwargs)
        return wrapper
    return decorator

def retry(
    service_name: str,
    config: Optional[RetryConfig] = None
):
    """Decorator to add retry logic to functions."""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retry_handler = reliability_service.get_retry_handler(service_name, config)
            return await retry_handler.execute_with_retry(func, *args, **kwargs)
        return wrapper
    return decorator

def reliable(
    service_name: str,
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    retry_config: Optional[RetryConfig] = None
):
    """Decorator to add both circuit breaker and retry protection."""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await reliability_service.reliable_call(
                service_name=service_name,
                func=func,
                *args,
                circuit_breaker_config=circuit_breaker_config,
                retry_config=retry_config,
                **kwargs
            )
        return wrapper
    return decorator

# Global instance
reliability_service = ReliabilityService()