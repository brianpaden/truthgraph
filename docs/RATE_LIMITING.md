# Rate Limiting Documentation

## Overview

TruthGraph API implements comprehensive rate limiting to protect against abuse and ensure fair resource allocation. Rate limits are enforced using the `slowapi` library with support for:

- **Per-IP rate limiting** - Tracks requests by client IP address
- **Per-endpoint limits** - Different limits for different computational costs
- **Standard headers** - Returns RFC-compliant rate limit headers
- **Real-time monitoring** - Tracks violations and usage patterns
- **Flexible configuration** - YAML-based configuration system

## Rate Limit Headers

All rate-limited endpoints return standard headers in responses:

| Header | Description | Example |
|--------|-------------|---------|
| `X-RateLimit-Limit` | Maximum requests allowed in window | `10` |
| `X-RateLimit-Remaining` | Requests remaining in current window | `7` |
| `X-RateLimit-Reset` | Unix timestamp when limit resets | `1699564800` |
| `Retry-After` | Seconds to wait before retrying (on 429) | `45` |

## Endpoint Rate Limits

Different endpoints have different rate limits based on computational cost:

### ML Endpoints (Expensive Operations)

| Endpoint | Limit | Description |
|----------|-------|-------------|
| `POST /api/v1/verify` | **5/minute** | Full verification pipeline (most expensive) |
| `POST /api/v1/nli/batch` | **5/minute** | Batch NLI inference |
| `POST /api/v1/embed` | **10/minute** | Embedding generation |
| `POST /api/v1/nli` | **10/minute** | Single NLI inference |
| `POST /api/v1/search` | **20/minute** | Vector/hybrid search |

### Data Retrieval Endpoints

| Endpoint | Limit | Description |
|----------|-------|-------------|
| `GET /api/v1/verdict/{claim_id}` | **20/minute** | Retrieve verdict by claim ID |
| `GET /api/v1/claims` | **30/minute** | List claims with pagination |
| `GET /api/v1/claims/{claim_id}` | **30/minute** | Get specific claim |

### System Endpoints

| Endpoint | Limit | Description |
|----------|-------|-------------|
| `GET /health` | **100/minute** | Health check |
| `GET /` | **100/minute** | API root information |
| `GET /rate-limit-stats` | **100/minute** | Rate limit statistics |

### Default Limit

All other endpoints default to **60 requests/minute** unless specifically configured.

## HTTP 429 Response

When rate limit is exceeded, the API returns HTTP 429 (Too Many Requests):

```json
{
  "error": "Rate limit exceeded",
  "detail": "5 per 1 minute"
}
```

Response headers include `Retry-After` indicating seconds to wait before retrying.

## Configuration

Rate limits are configured in `truthgraph/api/rate_limits.yaml`:

```yaml
rate_limits:
  # Default limit for all endpoints
  default: "60/minute"

  # Endpoint-specific limits
  endpoints:
    /api/v1/verify: "5/minute"
    /api/v1/embed: "10/minute"
    /api/v1/search: "20/minute"
    # ... more endpoints

  # Burst multiplier (allows temporary bursts)
  burst_multiplier: 1.5
```

### Customizing Limits

To customize rate limits:

1. Edit `truthgraph/api/rate_limits.yaml`
2. Update the limit for specific endpoints
3. Restart the API server

**Supported time periods:**
- `second` - Per second limits
- `minute` - Per minute limits
- `hour` - Per hour limits
- `day` - Per day limits

**Example limits:**
- `"10/minute"` - 10 requests per minute
- `"100/hour"` - 100 requests per hour
- `"1000/day"` - 1000 requests per day

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RATE_LIMIT_CONFIG` | Path to rate limit configuration file | `truthgraph/api/rate_limits.yaml` |
| `RATE_LIMIT_STORAGE` | Storage backend for rate limits | `memory://` |

**Redis Backend (Production):**
```bash
export RATE_LIMIT_STORAGE="redis://localhost:6379"
```

## Monitoring

### Statistics Endpoint

Get real-time rate limiting statistics:

```bash
GET /rate-limit-stats
```

**Response:**
```json
{
  "rate_limit_statistics": {
    "uptime_seconds": 3600,
    "total_requests": 1523,
    "total_violations": 42,
    "violation_rate": 0.0276,
    "top_violators": [
      ["192.168.1.1:/api/v1/verify", 15],
      ["192.168.1.2:/api/v1/embed", 8]
    ]
  },
  "message": "Rate limit monitoring data"
}
```

### Metrics

The monitoring system tracks:
- **Total requests** - All successful requests
- **Total violations** - Rate limit violations (429 errors)
- **Violation rate** - Percentage of requests that were rate limited
- **Top violators** - IPs/endpoints with most violations
- **Per-endpoint stats** - Violations per endpoint

## Best Practices

### For API Consumers

1. **Check headers** - Always check `X-RateLimit-Remaining` to avoid hitting limits
2. **Respect Retry-After** - Wait the specified time before retrying after 429
3. **Implement backoff** - Use exponential backoff for retries
4. **Batch operations** - Use batch endpoints (`/nli/batch`) when possible
5. **Cache responses** - Cache verification results to reduce API calls

### Example: Respecting Rate Limits

```python
import time
import requests

def call_api_with_rate_limit(url, data):
    response = requests.post(url, json=data)

    # Check if rate limited
    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 60))
        print(f"Rate limited. Waiting {retry_after} seconds...")
        time.sleep(retry_after)
        return call_api_with_rate_limit(url, data)

    # Check remaining requests
    remaining = response.headers.get('X-RateLimit-Remaining')
    if remaining and int(remaining) < 2:
        print("Close to rate limit, pausing...")
        time.sleep(5)

    return response
```

### For API Operators

1. **Monitor violations** - Check `/rate-limit-stats` regularly
2. **Adjust limits** - Tune limits based on actual usage patterns
3. **Use Redis** - In production, use Redis backend for distributed systems
4. **Alert on abuse** - Set up alerts for high violation rates
5. **Whitelist IPs** - Consider whitelisting trusted IPs (future feature)

## Architecture

### Components

```
Rate Limiting System
├── slowapi (Core library)
├── rate_limit.py (Configuration & monitoring)
├── middleware.py (Monitoring middleware)
├── rate_limits.yaml (Configuration file)
└── main.py (Integration)
```

### How It Works

1. **Request arrives** → Middleware extracts client IP
2. **Check limit** → slowapi checks current request count
3. **Under limit?** → Process request, inject headers
4. **Over limit?** → Return 429 with Retry-After header
5. **Monitor** → Record request/violation in monitoring system

### Storage Backends

**In-Memory (Default):**
- Fast, no external dependencies
- Suitable for single-instance deployments
- Data lost on restart

**Redis (Production):**
- Persistent across restarts
- Supports distributed deployments
- Requires Redis server

## Future Enhancements

Planned improvements for rate limiting:

- **User-based limits** - Different limits for authenticated users
- **Tiered limits** - Free/Pro/Enterprise tiers with different limits
- **IP whitelisting** - Bypass limits for trusted IPs
- **Dynamic adjustment** - Auto-adjust limits based on system load
- **Quota system** - Monthly/daily quotas in addition to per-minute limits
- **Custom storage** - Support for Memcached and other backends

## Troubleshooting

### Common Issues

**Issue: Rate limit headers not appearing**
- Ensure endpoint has `@limiter.limit()` decorator
- Check that `response: Response` parameter is present
- Verify slowapi is properly initialized in `app.state.limiter`

**Issue: 429 errors for all requests**
- Check rate limit configuration file exists
- Verify storage backend is accessible (Redis if configured)
- Check system clock is synchronized

**Issue: Rate limits not resetting**
- Verify time window is correct (minute/hour/day)
- Check storage backend has enough memory
- Ensure no clock drift issues

### Debug Mode

Enable debug logging for rate limiting:

```python
import logging
logging.getLogger('slowapi').setLevel(logging.DEBUG)
```

## API Reference

### RateLimitConfig

Configuration manager for rate limits.

```python
from truthgraph.api.rate_limit import RateLimitConfig

config = RateLimitConfig('path/to/config.yaml')
limit = config.get_limit('/api/v1/verify')  # Returns "5/minute"
```

### RateLimitMonitor

Monitoring system for tracking violations.

```python
from truthgraph.api.rate_limit import get_rate_limit_monitor

monitor = get_rate_limit_monitor()
stats = monitor.get_stats()
violations = monitor.get_violation_count('192.168.1.1')
```

### Limiter

slowapi Limiter instance configured for TruthGraph.

```python
from truthgraph.api.rate_limit import limiter

@router.get("/custom")
@limiter.limit("30/minute")
async def custom_endpoint(request: Request, response: Response):
    return {"message": "Custom endpoint with rate limiting"}
```

## Testing

Run rate limiting tests:

```bash
# All rate limiting tests
pytest tests/test_rate_limiting.py -v

# Specific test class
pytest tests/test_rate_limiting.py::TestRateLimitConfig -v

# Test coverage
pytest tests/test_rate_limiting.py --cov=truthgraph.api.rate_limit
```

## Support

For issues or questions about rate limiting:
- Check this documentation
- Review `/rate-limit-stats` endpoint for current status
- Check application logs for rate limit errors
- Open an issue on GitHub with details

---

**Last Updated:** November 2025
**Version:** 2.0.0
**Feature:** 4.5 - Rate Limiting & Throttling
