"""Rate limiting configuration and utilities for TruthGraph API.

This module provides:
- slowapi-based rate limiting with Redis backend support
- YAML-based configuration for endpoint-specific limits
- Rate limit monitoring and metrics
- Standard rate limit headers (RateLimit-*, Retry-After)
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


class RateLimitConfig:
    """Configuration manager for rate limits.

    Loads rate limits from YAML file and provides access to endpoint-specific limits.
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize rate limit configuration.

        Args:
            config_path: Path to YAML configuration file. If None, uses defaults.
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load rate limit configuration from YAML file.

        Returns:
            Configuration dictionary with rate limits
        """
        if self.config_path and Path(self.config_path).exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    logger.info(f"Loaded rate limit config from {self.config_path}")
                    return config.get('rate_limits', {})
            except Exception as e:
                logger.error(f"Failed to load rate limit config: {e}")
                return self._get_default_config()
        else:
            logger.info("Using default rate limit configuration")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default rate limit configuration.

        Returns:
            Default configuration dictionary
        """
        return {
            'default': '60/minute',
            'endpoints': {
                '/api/v1/verify': '5/minute',
                '/api/v1/embed': '10/minute',
                '/api/v1/search': '20/minute',
                '/api/v1/nli': '10/minute',
                '/api/v1/nli/batch': '5/minute',
                '/api/v1/verdict/{claim_id}': '20/minute',
                '/health': '100/minute',
            },
            'burst_multiplier': 1.5,  # Allow 50% burst above limit
        }

    def get_limit(self, endpoint: str) -> str:
        """Get rate limit for specific endpoint.

        Args:
            endpoint: Endpoint path (e.g., '/api/v1/verify')

        Returns:
            Rate limit string (e.g., '5/minute')
        """
        # Try exact match first
        if endpoint in self.config.get('endpoints', {}):
            return self.config['endpoints'][endpoint]

        # Try pattern matching for parameterized routes
        for pattern, limit in self.config.get('endpoints', {}).items():
            if self._match_pattern(endpoint, pattern):
                return limit

        # Fall back to default
        return self.config.get('default', '60/minute')

    def _match_pattern(self, endpoint: str, pattern: str) -> bool:
        """Match endpoint against pattern with path parameters.

        Args:
            endpoint: Actual endpoint path
            pattern: Pattern with optional {param} placeholders

        Returns:
            True if endpoint matches pattern
        """
        # Simple pattern matching for path parameters
        endpoint_parts = endpoint.split('/')
        pattern_parts = pattern.split('/')

        if len(endpoint_parts) != len(pattern_parts):
            return False

        for ep, pp in zip(endpoint_parts, pattern_parts):
            if pp.startswith('{') and pp.endswith('}'):
                # This is a parameter, accept any value
                continue
            if ep != pp:
                return False

        return True

    def get_burst_multiplier(self) -> float:
        """Get burst multiplier for rate limits.

        Returns:
            Burst multiplier (e.g., 1.5 for 50% burst)
        """
        return self.config.get('burst_multiplier', 1.5)


class RateLimitMonitor:
    """Monitor rate limit violations and usage patterns."""

    def __init__(self):
        """Initialize rate limit monitor."""
        self.violations: Dict[str, int] = {}
        self.requests: Dict[str, int] = {}
        self.start_time = time.time()

    def record_violation(self, identifier: str, endpoint: str):
        """Record a rate limit violation.

        Args:
            identifier: User identifier (IP or user ID)
            endpoint: Endpoint that was rate limited
        """
        key = f"{identifier}:{endpoint}"
        self.violations[key] = self.violations.get(key, 0) + 1

        logger.warning(
            f"Rate limit violation: {identifier} on {endpoint} "
            f"(total violations: {self.violations[key]})"
        )

    def record_request(self, identifier: str, endpoint: str):
        """Record a successful request.

        Args:
            identifier: User identifier (IP or user ID)
            endpoint: Endpoint that was accessed
        """
        key = f"{identifier}:{endpoint}"
        self.requests[key] = self.requests.get(key, 0) + 1

    def get_violation_count(self, identifier: str, endpoint: Optional[str] = None) -> int:
        """Get violation count for identifier.

        Args:
            identifier: User identifier
            endpoint: Optional endpoint filter

        Returns:
            Total violation count
        """
        if endpoint:
            key = f"{identifier}:{endpoint}"
            return self.violations.get(key, 0)
        else:
            return sum(
                count for key, count in self.violations.items()
                if key.startswith(f"{identifier}:")
            )

    def get_request_count(self, identifier: str, endpoint: Optional[str] = None) -> int:
        """Get request count for identifier.

        Args:
            identifier: User identifier
            endpoint: Optional endpoint filter

        Returns:
            Total request count
        """
        if endpoint:
            key = f"{identifier}:{endpoint}"
            return self.requests.get(key, 0)
        else:
            return sum(
                count for key, count in self.requests.items()
                if key.startswith(f"{identifier}:")
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get overall rate limit statistics.

        Returns:
            Statistics dictionary
        """
        uptime = time.time() - self.start_time
        total_violations = sum(self.violations.values())
        total_requests = sum(self.requests.values())

        return {
            'uptime_seconds': uptime,
            'total_requests': total_requests,
            'total_violations': total_violations,
            'violation_rate': total_violations / total_requests if total_requests > 0 else 0,
            'top_violators': self._get_top_violators(5),
        }

    def _get_top_violators(self, limit: int = 5) -> list:
        """Get top rate limit violators.

        Args:
            limit: Number of top violators to return

        Returns:
            List of (identifier:endpoint, count) tuples
        """
        sorted_violations = sorted(
            self.violations.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_violations[:limit]


# Global instances
_rate_limit_config: Optional[RateLimitConfig] = None
_rate_limit_monitor: Optional[RateLimitMonitor] = None


def get_rate_limit_config(config_path: Optional[str] = None) -> RateLimitConfig:
    """Get or create rate limit configuration instance.

    Args:
        config_path: Optional path to configuration file

    Returns:
        RateLimitConfig instance
    """
    global _rate_limit_config
    if _rate_limit_config is None:
        _rate_limit_config = RateLimitConfig(config_path)
    return _rate_limit_config


def get_rate_limit_monitor() -> RateLimitMonitor:
    """Get or create rate limit monitor instance.

    Returns:
        RateLimitMonitor instance
    """
    global _rate_limit_monitor
    if _rate_limit_monitor is None:
        _rate_limit_monitor = RateLimitMonitor()
    return _rate_limit_monitor


def get_identifier(request: Request) -> str:
    """Get identifier for rate limiting.

    Extracts user identifier from request. Uses authenticated user ID if available,
    falls back to IP address for unauthenticated requests.

    Args:
        request: FastAPI request

    Returns:
        User identifier string
    """
    # TODO: Check for authenticated user in request.state.user
    # For now, use IP address
    return get_remote_address(request)


# Create limiter instance
limiter = Limiter(
    key_func=get_identifier,
    default_limits=["60/minute"],  # Default limit
    storage_uri="memory://",  # Use in-memory storage (can be Redis in production)
    strategy="fixed-window",  # Fixed window strategy
    headers_enabled=True,  # Enable rate limit headers
)


def create_limiter(
    storage_uri: str = "memory://",
    default_limits: Optional[list] = None,
) -> Limiter:
    """Create a configured Limiter instance.

    Args:
        storage_uri: Storage backend URI (e.g., "memory://", "redis://localhost:6379")
        default_limits: Default rate limits

    Returns:
        Configured Limiter instance
    """
    if default_limits is None:
        config = get_rate_limit_config()
        default_limits = [config.config.get('default', '60/minute')]

    return Limiter(
        key_func=get_identifier,
        default_limits=default_limits,
        storage_uri=storage_uri,
        strategy="fixed-window",
        headers_enabled=True,
    )
