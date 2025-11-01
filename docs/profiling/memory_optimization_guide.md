# Memory Optimization Guide

**Feature**: 2.5 - Memory Optimization & Analysis
**Date**: October 31, 2025
**Status**: Production Guide
**Audience**: Developers, DevOps Engineers

---

## Overview

This guide provides practical guidance for monitoring, optimizing, and troubleshooting memory usage in the TruthGraph system. The current implementation operates at **477.6 MB peak** (11.7% of the 4GB target), providing significant headroom for future enhancements.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Monitoring in Production](#monitoring-in-production)
3. [Optimization Strategies](#optimization-strategies)
4. [Troubleshooting](#troubleshooting)
5. [Best Practices](#best-practices)
6. [Advanced Techniques](#advanced-techniques)

---

## Quick Start

### Basic Memory Monitoring

```python
from truthgraph.monitoring import MemoryMonitor

# Create and start monitoring
monitor = MemoryMonitor()
monitor.start()

# ... perform operations ...

# Get current state
snapshot = monitor.get_current_snapshot()
print(f"Memory: {snapshot.rss_mb:.1f} MB")

# Stop and get statistics
stats = monitor.stop()
print(f"Peak: {stats.max_rss_mb:.1f} MB")
print(f"Mean: {stats.mean_rss_mb:.1f} MB")
```

### Memory Alerting

```python
from truthgraph.monitoring import MemoryMonitor, AlertManager, AlertLevel

monitor = MemoryMonitor()
alert_manager = AlertManager()

# Configure thresholds
alert_manager.set_threshold(AlertLevel.WARNING, rss_mb=2048)   # 2GB
alert_manager.set_threshold(AlertLevel.CRITICAL, rss_mb=3500)  # 3.5GB

# Monitor with alerts
monitor.start()
# ... operations ...
snapshot = monitor.get_current_snapshot()
alerts = alert_manager.check_thresholds(snapshot)

if alerts:
    for alert in alerts:
        print(f"ALERT: {alert.message}")
```

### Memory Profiling

```bash
# Run full analysis suite
python scripts/profiling/analyze_memory_usage.py --full

# Run specific tests
python scripts/profiling/analyze_memory_usage.py --baseline-only
python scripts/profiling/analyze_memory_usage.py --load-test --concurrent 100
python scripts/profiling/analyze_memory_usage.py --leak-test --duration 30
```

---

## Monitoring in Production

### Continuous Monitoring Setup

```python
import logging
from truthgraph.monitoring import (
    MemoryMonitor,
    AlertManager,
    MemoryProfileStore,
    AlertLevel
)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize monitoring components
monitor = MemoryMonitor(enable_tracemalloc=True)
alert_manager = AlertManager()
profile_store = MemoryProfileStore()

# Configure production thresholds
alert_manager.set_threshold(AlertLevel.WARNING, rss_mb=2048)    # 2GB warning
alert_manager.set_threshold(AlertLevel.CRITICAL, rss_mb=3500)   # 3.5GB critical
alert_manager.set_threshold(AlertLevel.WARNING, growth_mb_per_hour=50)

# Add custom alert handler
def send_to_monitoring_system(alert):
    """Send alert to your monitoring system."""
    # Example: Send to Slack, PagerDuty, etc.
    print(f"ALERT: {alert.level.value} - {alert.message}")

alert_manager.add_handler(send_to_monitoring_system)

# Start monitoring
monitor.start()
```

### Periodic Profiling

```python
import time
from datetime import datetime

def periodic_memory_check(interval_seconds=300):
    """Check memory every 5 minutes."""
    while True:
        snapshot = monitor.capture_snapshot()
        alerts = alert_manager.check_thresholds(snapshot)

        # Log current state
        print(f"[{datetime.now()}] Memory: {snapshot.rss_mb:.1f} MB")

        # Save profile every hour
        if snapshot.timestamp.endswith(":00:00"):
            stats = monitor.calculate_statistics()
            profile_store.save_profile(
                name="production_hourly",
                monitor=monitor,
                stats=stats,
                metadata={"environment": "production"}
            )

        time.sleep(interval_seconds)
```

### Historical Analysis

```python
from truthgraph.monitoring import MemoryProfileStore

store = MemoryProfileStore()

# Analyze trends over past week
trend = store.analyze_trend("production_hourly", days=7)

if trend:
    print(f"Profiles analyzed: {trend.num_profiles}")
    print(f"Mean memory trend: {trend.mean_rss_trend:.2f} MB/day")
    print(f"Regression detected: {trend.regression_detected}")

# Compare two profiles
comparison = store.compare_profiles(
    "production_hourly_2025-10-30",
    "production_hourly_2025-10-31"
)
print(f"Memory change: {comparison['comparison']['mean_rss_pct_change']:.1f}%")
```

---

## Optimization Strategies

### Current System Performance

**Baseline**: 477.6 MB peak (11.7% of 4GB target)

| Component | Memory | Percentage |
|-----------|--------|------------|
| Python Runtime | 366 MB | 77% |
| Embedding Model | 72 MB | 15% |
| Batch Processing | 34 MB | 7% |
| Overhead | 5 MB | 1% |

### Optimization Priority Matrix

| Strategy | Effort | Impact | Priority | Recommended |
|----------|--------|--------|----------|-------------|
| **Embedding Cache** | Medium | Medium | Medium | Future |
| **Batch Size Tuning** | Low | Low | Low | Already optimal |
| **Model Quantization** | High | Medium | Low | Not needed |
| **Streaming Processing** | High | Low | Low | Not needed |
| **Connection Pooling** | Low | Low | Low | Future (DB) |

### Strategy 1: Embedding Cache (Future Enhancement)

**When to use**: If you frequently embed the same texts

```python
from functools import lru_cache
from truthgraph.services.ml.embedding_service import EmbeddingService

class CachedEmbeddingService:
    """Embedding service with LRU cache."""

    def __init__(self, cache_size=1000):
        self.service = EmbeddingService.get_instance()
        self.cache_size = cache_size

    @lru_cache(maxsize=1000)
    def embed_text_cached(self, text: str):
        """Cache embeddings for frequently-used texts."""
        return tuple(self.service.embed_text(text))

    def embed_batch(self, texts):
        """Batch embedding with cache checking."""
        return self.service.embed_batch(texts)
```

**Expected Impact**:
- Memory: +50 MB (for 1000 cached embeddings)
- Speed: +20-50% for cache hits
- Trade-off: Increased memory for faster repeated embeddings

### Strategy 2: Batch Size Optimization

**Current**: batch_size=32 (optimal based on Feature 2.1)

```python
# For memory-constrained environments
embedding_service = EmbeddingService.get_instance()
embedding_service.DEFAULT_BATCH_SIZE = 16  # Reduce memory by ~50%

# For maximum throughput
embedding_service.DEFAULT_BATCH_SIZE = 64  # +13% throughput
```

**Memory Impact by Batch Size** (from Feature 2.1):
- batch_size=8: 467 MB peak (minimal memory)
- batch_size=32: 500 MB peak (balanced)
- batch_size=64: 527 MB peak (high throughput)
- batch_size=256: 658 MB peak (maximum throughput)

### Strategy 3: Model Selection

**Current Model**: `sentence-transformers/all-MiniLM-L6-v2` (72 MB)

**Alternative Models**:

| Model | Size | Dimension | Trade-off |
|-------|------|-----------|-----------|
| all-MiniLM-L6-v2 | 72 MB | 384 | Current (optimal) ✅ |
| all-MiniLM-L12-v2 | 120 MB | 384 | Better quality, +67% memory |
| paraphrase-MiniLM-L3-v2 | 50 MB | 384 | Smaller, -30% memory |

**Recommendation**: Keep current model (optimal quality/size trade-off)

### Strategy 4: Memory-Aware Processing

```python
from truthgraph.monitoring import MemoryMonitor

def process_with_memory_awareness(texts, max_memory_mb=2048):
    """Adjust batch size based on available memory."""
    monitor = MemoryMonitor()
    current = monitor.capture_snapshot()

    # Calculate safe batch size
    available_mb = max_memory_mb - current.rss_mb
    safe_batch_size = min(64, int(available_mb / 10))  # 10 MB per batch estimate

    embedding_service = EmbeddingService.get_instance()

    # Process with adaptive batch size
    results = []
    for i in range(0, len(texts), safe_batch_size):
        batch = texts[i:i + safe_batch_size]
        embeddings = embedding_service.embed_batch(batch)
        results.extend(embeddings)

        # Check memory periodically
        if i % 100 == 0:
            snapshot = monitor.capture_snapshot()
            print(f"Processed {i}, Memory: {snapshot.rss_mb:.1f} MB")

    return results
```

---

## Troubleshooting

### Issue 1: High Memory Usage

**Symptoms**: Memory usage approaching 2GB+

**Diagnosis**:
```python
from truthgraph.monitoring import MemoryMonitor

monitor = MemoryMonitor(enable_tracemalloc=True)
monitor.start()

# ... reproduce issue ...

# Get top memory allocations
top_allocations = monitor.get_top_allocations(limit=10)
for alloc in top_allocations:
    print(f"{alloc['file']}: {alloc['size_mb']:.2f} MB")
```

**Common Causes**:
1. Large batch sizes - Reduce batch_size to 16 or 32
2. Accumulated results - Process and discard results incrementally
3. Multiple model instances - Ensure singleton pattern is working

**Solutions**:
```python
# Solution 1: Reduce batch size
embedding_service.DEFAULT_BATCH_SIZE = 16

# Solution 2: Clear results after processing
results = process_batch(texts)
save_to_database(results)
results = None  # Clear reference
import gc; gc.collect()

# Solution 3: Verify singleton
service1 = EmbeddingService.get_instance()
service2 = EmbeddingService.get_instance()
assert service1 is service2  # Should be same instance
```

### Issue 2: Memory Leaks

**Symptoms**: Memory grows continuously over time

**Diagnosis**:
```python
from truthgraph.monitoring import MemoryMonitor, AlertManager

monitor = MemoryMonitor()
alerts = AlertManager()

monitor.start()

# Run workload for extended period
# ... operations ...

# Check for leaks
leak_result = monitor.detect_memory_leak(threshold_mb_per_hour=10.0)

if leak_result['leak_detected']:
    print(f"LEAK DETECTED: {leak_result['growth_rate_mb_per_hour']:.2f} MB/hour")

    # Get statistics
    stats = monitor.calculate_statistics()
    print(f"Total growth: {stats.max_rss_mb - stats.min_rss_mb:.2f} MB")
```

**Common Causes**:
1. Unclosed resources (files, connections)
2. Circular references preventing GC
3. Growing caches without eviction

**Solutions**:
```python
# Solution 1: Use context managers
with open('file.txt') as f:
    data = f.read()

# Solution 2: Explicit cleanup
import gc
results = process_data()
# ... use results ...
del results
gc.collect()

# Solution 3: Bounded caches
from functools import lru_cache

@lru_cache(maxsize=100)  # Limit cache size
def cached_function(arg):
    return expensive_operation(arg)
```

### Issue 3: Out of Memory Errors

**Symptoms**: Process killed or crashes with OOM

**Diagnosis**:
```python
# Check system memory
from truthgraph.monitoring import MemoryMonitor

monitor = MemoryMonitor()
snapshot = monitor.capture_snapshot()

print(f"Available: {snapshot.available_system_mb:.1f} MB")
print(f"Process: {snapshot.rss_mb:.1f} MB")
print(f"Percent: {snapshot.percent:.1f}%")
```

**Prevention**:
```python
from truthgraph.monitoring import MemoryMonitor, AlertManager, AlertLevel

# Set up emergency alerts
monitor = MemoryMonitor()
alerts = AlertManager()

# More conservative thresholds
alerts.set_threshold(AlertLevel.WARNING, rss_mb=1024)   # 1GB warning
alerts.set_threshold(AlertLevel.CRITICAL, rss_mb=2048)  # 2GB critical

def emergency_handler(alert):
    """Emergency shutdown if critical."""
    if alert.level == AlertLevel.CRITICAL:
        print("CRITICAL MEMORY - Initiating graceful shutdown")
        # Trigger graceful shutdown logic

alerts.add_handler(emergency_handler)
```

---

## Best Practices

### 1. Always Monitor in Production

```python
# Good: Continuous monitoring
monitor = MemoryMonitor()
monitor.start()

# Bad: No monitoring
# (Don't do this in production)
```

### 2. Set Appropriate Thresholds

```python
# Good: Conservative thresholds
alerts.set_threshold(AlertLevel.WARNING, rss_mb=2048)   # 50% of 4GB
alerts.set_threshold(AlertLevel.CRITICAL, rss_mb=3072)  # 75% of 4GB

# Bad: Too aggressive
alerts.set_threshold(AlertLevel.CRITICAL, rss_mb=4000)  # Too close to limit
```

### 3. Clean Up Resources

```python
# Good: Explicit cleanup
results = process_batch(texts)
save_results(results)
del results
gc.collect()

# Bad: Accumulating results
all_results = []
for batch in batches:
    results = process_batch(batch)
    all_results.extend(results)  # Memory grows
```

### 4. Use Batch Processing

```python
# Good: Batch processing
for i in range(0, len(texts), batch_size):
    batch = texts[i:i + batch_size]
    embeddings = service.embed_batch(batch)
    process(embeddings)

# Bad: One at a time
for text in texts:
    embedding = service.embed_text(text)  # Inefficient
    process(embedding)
```

### 5. Profile Before Optimizing

```python
# Good: Profile first
from truthgraph.monitoring import MemoryMonitor

monitor = MemoryMonitor()
monitor.start()
# ... run workload ...
stats = monitor.stop()
print(f"Peak: {stats.max_rss_mb:.1f} MB")

# Then optimize based on data

# Bad: Premature optimization
# (Don't optimize without measuring)
```

---

## Advanced Techniques

### Component-Level Attribution

```python
from truthgraph.monitoring import MemoryMonitor

monitor = MemoryMonitor()

# Mark before loading component
monitor.mark_component("before_embedding_model")

# Load component
embedding_service = EmbeddingService.get_instance()
_ = embedding_service.embed_text("test")

# Mark after loading
monitor.mark_component("after_embedding_model")

# Get memory delta
component_memory = monitor.get_component_memory("before_embedding_model")
print(f"Embedding model: {component_memory['delta_mb']:.1f} MB")
```

### Custom Alert Handlers

```python
from truthgraph.monitoring import AlertManager, AlertLevel

alerts = AlertManager()

def slack_alert(alert):
    """Send alert to Slack."""
    if alert.level == AlertLevel.CRITICAL:
        send_to_slack(f"CRITICAL: {alert.message}")

def metrics_alert(alert):
    """Send metrics to monitoring system."""
    send_metric("memory_alert", {
        "level": alert.level.value,
        "type": alert.alert_type,
        "value": alert.snapshot.rss_mb if alert.snapshot else 0
    })

alerts.add_handler(slack_alert)
alerts.add_handler(metrics_alert)
```

### Memory Trend Analysis

```python
from truthgraph.monitoring import MemoryProfileStore

store = MemoryProfileStore()

# Analyze regression over 30 days
trend = store.analyze_trend("production", days=30, regression_threshold_mb=100)

if trend and trend.regression_detected:
    print(f"REGRESSION DETECTED")
    print(f"Growth rate: {trend.mean_rss_trend:.2f} MB/day")
    print(f"Over {trend.time_range_days:.0f} days")

    # Get detailed profiles
    for profile in trend.profiles[-5:]:  # Last 5 profiles
        print(f"{profile.timestamp}: {profile.stats.mean_rss_mb:.1f} MB")
```

---

## Configuration Reference

### MemoryMonitor Configuration

```python
# Enable detailed Python tracking (adds ~5% overhead)
monitor = MemoryMonitor(enable_tracemalloc=True)

# Disable for lower overhead
monitor = MemoryMonitor(enable_tracemalloc=False)
```

### AlertManager Thresholds

```python
alerts = AlertManager()

# Memory thresholds
alerts.set_threshold(AlertLevel.INFO, rss_mb=1024)      # 1GB
alerts.set_threshold(AlertLevel.WARNING, rss_mb=2048)   # 2GB
alerts.set_threshold(AlertLevel.CRITICAL, rss_mb=3500)  # 3.5GB

# Percentage thresholds
alerts.set_threshold(AlertLevel.WARNING, percent=50.0)
alerts.set_threshold(AlertLevel.CRITICAL, percent=75.0)

# Growth rate thresholds (leak detection)
alerts.set_threshold(AlertLevel.WARNING, growth_mb_per_hour=50)
alerts.set_threshold(AlertLevel.CRITICAL, growth_mb_per_hour=100)
```

### MemoryProfileStore Configuration

```python
from pathlib import Path

# Custom storage directory
store = MemoryProfileStore(
    storage_dir=Path("/var/log/truthgraph/memory_profiles")
)

# Cleanup old profiles
num_deleted = store.cleanup_old_profiles(days=30)
```

---

## Conclusion

The TruthGraph memory monitoring and optimization infrastructure provides comprehensive tools for managing memory in production. With peak usage of only 477.6 MB (11.7% of target), the system has significant headroom and requires minimal active optimization.

**Key Takeaways**:

1. **Monitor continuously** in production
2. **Set conservative thresholds** (2GB warning, 3.5GB critical)
3. **Profile before optimizing** - don't guess
4. **Use batch processing** for efficiency
5. **Clean up resources** explicitly when needed

**For Support**: See `docs/profiling/memory_analysis.md` for detailed analysis and `truthgraph/monitoring/` for API documentation.

---

**Document Version**: 1.0.0
**Last Updated**: October 31, 2025
**Feature**: 2.5 - Memory Optimization & Analysis
