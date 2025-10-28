"""Middleware for FastAPI application.

This module provides middleware components including:
- Rate limiting for ML endpoints
- Request ID tracking
- Error handling
"""

import logging
import time
import uuid
from collections import defaultdict
from typing import Callable, Dict

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for expensive ML operations.

    Implements token bucket algorithm for rate limiting.
    Different limits for different endpoint categories.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        ml_requests_per_minute: int = 10,
    ):
        """Initialize rate limiter.

        Args:
            app: FastAPI application
            requests_per_minute: Global rate limit per IP
            ml_requests_per_minute: ML endpoint rate limit per IP
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.ml_requests_per_minute = ml_requests_per_minute

        # Store request counts: {ip: [(timestamp, endpoint_type), ...]}
        self.request_history: Dict[str, list] = defaultdict(list)

        # ML endpoints that need stricter limits
        self.ml_endpoints = {
            "/api/v1/verify",
            "/api/v1/embed",
            "/api/v1/nli",
            "/api/v1/nli/batch",
            "/api/v1/search",
        }

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request.

        Args:
            request: FastAPI request

        Returns:
            Client IP address
        """
        # Check for X-Forwarded-For header (proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # Fall back to direct connection IP
        if request.client:
            return request.client.host

        return "unknown"

    def _is_ml_endpoint(self, path: str) -> bool:
        """Check if endpoint is an ML endpoint.

        Args:
            path: Request path

        Returns:
            True if ML endpoint, False otherwise
        """
        return any(path.startswith(ml_path) for ml_path in self.ml_endpoints)

    def _check_rate_limit(self, ip: str, is_ml: bool) -> tuple[bool, int]:
        """Check if request is within rate limit.

        Args:
            ip: Client IP address
            is_ml: Whether this is an ML endpoint

        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        current_time = time.time()
        window = 60  # 1 minute window

        # Clean old requests outside the window
        self.request_history[ip] = [
            (ts, endpoint_type)
            for ts, endpoint_type in self.request_history[ip]
            if current_time - ts < window
        ]

        # Count requests in current window
        if is_ml:
            ml_count = sum(
                1 for ts, endpoint_type in self.request_history[ip] if endpoint_type == "ml"
            )
            limit = self.ml_requests_per_minute

            if ml_count >= limit:
                # Calculate retry after
                oldest_ml = min(
                    ts for ts, endpoint_type in self.request_history[ip] if endpoint_type == "ml"
                )
                retry_after = int(window - (current_time - oldest_ml)) + 1
                return False, retry_after

        else:
            total_count = len(self.request_history[ip])
            limit = self.requests_per_minute

            if total_count >= limit:
                oldest = min(ts for ts, _ in self.request_history[ip])
                retry_after = int(window - (current_time - oldest)) + 1
                return False, retry_after

        # Add current request
        endpoint_type = "ml" if is_ml else "general"
        self.request_history[ip].append((current_time, endpoint_type))

        return True, 0

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting.

        Args:
            request: Incoming request
            call_next: Next middleware/endpoint

        Returns:
            Response from endpoint or rate limit error
        """
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/", "/docs", "/openapi.json"]:
            return await call_next(request)

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Check if ML endpoint
        is_ml = self._is_ml_endpoint(request.url.path)

        # Check rate limit
        allowed, retry_after = self._check_rate_limit(client_ip, is_ml)

        if not allowed:
            logger.warning(
                f"Rate limit exceeded for {client_ip} on {request.url.path} "
                f"(retry after {retry_after}s)"
            )

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "RateLimitExceeded",
                    "message": f"Rate limit exceeded. Try again in {retry_after} seconds.",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(
                        self.ml_requests_per_minute if is_ml else self.requests_per_minute
                    ),
                    "X-RateLimit-Remaining": "0",
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = (self.ml_requests_per_minute if is_ml else self.requests_per_minute) - len(
            [
                1
                for ts, endpoint_type in self.request_history[client_ip]
                if (is_ml and endpoint_type == "ml") or (not is_ml)
            ]
        )

        response.headers["X-RateLimit-Limit"] = str(
            self.ml_requests_per_minute if is_ml else self.requests_per_minute
        )
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))

        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID tracking."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add request ID to request and response.

        Args:
            request: Incoming request
            call_next: Next middleware/endpoint

        Returns:
            Response with request ID header
        """
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Store in request state
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add to response headers
        response.headers["X-Request-ID"] = request_id

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle uncaught exceptions.

        Args:
            request: Incoming request
            call_next: Next middleware/endpoint

        Returns:
            Response or error response
        """
        try:
            return await call_next(request)
        except HTTPException:
            # Let FastAPI handle HTTPExceptions
            raise
        except Exception as e:
            logger.error(f"Unhandled exception for {request.url.path}: {e}", exc_info=True)

            request_id = getattr(request.state, "request_id", "unknown")

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "InternalServerError",
                    "message": "An unexpected error occurred",
                    "request_id": request_id,
                },
            )
