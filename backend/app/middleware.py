"""
Production middleware:
- Request ID injection + structured logging
- Rate limiting: Redis (if REDIS_URL set) or in-memory fallback
  - Auth endpoints: 10 req/min (brute-force protection)
  - All other endpoints: 30 req/min
- In-memory store: periodic cleanup to prevent unbounded growth
- Prometheus metrics (optional)
"""
import time
import uuid
import logging
import threading
from app.config import settings
from collections import defaultdict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

try:
    import structlog
    logger = structlog.get_logger("request")
    _use_structlog = True
except ImportError:
    logger = logging.getLogger("request")
    _use_structlog = False

try:
    from prometheus_client import Counter, Histogram, Gauge
    REQUEST_COUNT    = Counter("http_requests_total", "Total HTTP requests",
                               ["method", "endpoint", "status_code"])
    REQUEST_DURATION = Histogram("http_request_duration_seconds", "Request duration",
                                 ["method", "endpoint"])
    ACTIVE_REQUESTS  = Gauge("http_active_requests", "Active requests")
    _prometheus = True
except ImportError:
    _prometheus = False

# Redis rate limiter — optional
_redis_client = None
_REDIS_URL = settings.REDIS_URL
if _REDIS_URL:
    try:
        import redis as _redis_lib
        _redis_client = _redis_lib.from_url(_REDIS_URL, socket_connect_timeout=1)
        _redis_client.ping()
    except Exception:
        _redis_client = None

# In-memory fallback
_rate_store:      dict  = defaultdict(list)
_rate_store_lock: threading.Lock = threading.Lock()
_last_cleanup:    float = time.time()
_CLEANUP_INTERVAL = 300   # purge stale IPs every 5 minutes

# Rate limits
_AUTH_PATHS   = {"/api/v1/auth/login", "/api/v1/auth/register"}
_AUTH_LIMIT   = 10   # stricter limit for auth endpoints
_GLOBAL_LIMIT = 30
_RATE_WINDOW  = 60   # seconds

# Skip rate limiting for these paths
_SKIP_PATHS = {"/health", "/metrics", "/"}


class RequestTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        start = time.monotonic()

        if _prometheus:
            ACTIVE_REQUESTS.inc()

        response: Response = await call_next(request)

        duration    = time.monotonic() - start
        duration_ms = int(duration * 1000)

        if _prometheus:
            ACTIVE_REQUESTS.dec()
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
            ).inc()
            REQUEST_DURATION.labels(
                method=request.method,
                endpoint=request.url.path,
            ).observe(duration)

        if _use_structlog:
            logger.info("request_completed", method=request.method,
                        path=request.url.path, status=response.status_code,
                        ms=duration_ms, id=request_id)
        else:
            logger.info(f"{request.method} {request.url.path} → "
                        f"{response.status_code} [{duration_ms}ms] id={request_id}")

        response.headers["X-Request-ID"]    = request_id
        response.headers["X-Response-Time"] = f"{duration_ms}ms"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        ip    = request.client.host if request.client else "unknown"
        now   = int(time.time())
        limit = _AUTH_LIMIT if request.url.path in _AUTH_PATHS else _GLOBAL_LIMIT

        count = (self._redis_check(ip, now, limit)
                 if _redis_client
                 else self._memory_check(ip, now))

        if count > limit:
            return Response(
                content=f'{{"detail":"Rate limit exceeded. Max {limit} requests/minute."}}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "60"},
            )
        return await call_next(request)

    def _redis_check(self, ip: str, now: int, limit: int) -> int:
        key  = f"rate_limit:{ip}"
        pipe = _redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, now - _RATE_WINDOW)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, _RATE_WINDOW)
        _, count, _, _ = pipe.execute()
        return count

    def _memory_check(self, ip: str, now: int) -> int:
        global _last_cleanup
        with _rate_store_lock:
            # Periodic full cleanup — evict IPs not seen in the last window
            if now - _last_cleanup > _CLEANUP_INTERVAL:
                stale = [k for k, v in _rate_store.items()
                         if not any(now - t < _RATE_WINDOW for t in v)]
                for k in stale:
                    del _rate_store[k]
                _last_cleanup = now

            _rate_store[ip] = [t for t in _rate_store[ip] if now - t < _RATE_WINDOW]
            _rate_store[ip].append(now)
            return len(_rate_store[ip])
