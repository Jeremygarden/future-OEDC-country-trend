#!/usr/bin/env python3
"""
Simple TTL file cache for expensive database queries.
Uses JSON files with expiry timestamps.
"""
import os
import sys
import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Any, Optional, Callable
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

# Cache directory
CACHE_DIR = Path(__file__).parent.parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)

# Default TTL: 1 hour
DEFAULT_TTL_SECONDS = 3600


def _cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """Generate a cache key from function name and arguments."""
    key_data = f"{func_name}:{args}:{sorted(kwargs.items())}"
    return hashlib.md5(key_data.encode()).hexdigest()


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def get_cached(key: str) -> Optional[Any]:
    """Get a cached value if it exists and hasn't expired."""
    cache_file = _cache_path(key)
    
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file) as f:
            entry = json.load(f)
        
        if time.time() > entry.get("expires_at", 0):
            cache_file.unlink(missing_ok=True)
            return None
        
        return entry["data"]
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def set_cached(key: str, data: Any, ttl: int = DEFAULT_TTL_SECONDS) -> None:
    """Cache a value with a TTL."""
    entry = {
        "data": data,
        "expires_at": time.time() + ttl,
        "cached_at": time.time()
    }
    
    cache_file = _cache_path(key)
    try:
        with open(cache_file, "w") as f:
            json.dump(entry, f, default=str)
    except OSError as e:
        logger.warning(f"Cache write failed: {e}")


def invalidate_cache(pattern: str = None) -> int:
    """Invalidate cache entries. If pattern given, only matching keys."""
    count = 0
    for cache_file in CACHE_DIR.glob("*.json"):
        if pattern is None or pattern in cache_file.name:
            cache_file.unlink(missing_ok=True)
            count += 1
    return count


def cached(ttl: int = DEFAULT_TTL_SECONDS):
    """Decorator for caching function results."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            key = _cache_key(func.__name__, args, kwargs)
            
            cached_result = get_cached(key)
            if cached_result is not None:
                logger.debug(f"Cache hit: {func.__name__}")
                return cached_result
            
            result = func(*args, **kwargs)
            set_cached(key, result, ttl)
            logger.debug(f"Cache set: {func.__name__}")
            return result
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator


def warmup_cache() -> dict:
    """Pre-warm the cache with common queries."""
    from db.query import get_latest_comparison, get_indicator_trend
    
    logger.info("Warming up query cache...")
    stats = {"warmed": 0, "failed": 0}
    
    # Cache the latest comparison
    try:
        key = _cache_key("get_latest_comparison", (), {})
        data = get_latest_comparison()
        set_cached(key, data, ttl=3600)
        stats["warmed"] += 1
        logger.info("  ✓ Cached: latest comparison")
    except Exception as e:
        logger.error(f"  ✗ Failed to cache comparison: {e}")
        stats["failed"] += 1
    
    # Cache GDP trend
    try:
        key = _cache_key("get_indicator_trend", ("NY.GDP.MKTP.CD",), {})
        data = get_indicator_trend("NY.GDP.MKTP.CD")
        set_cached(key, data, ttl=3600)
        stats["warmed"] += 1
        logger.info("  ✓ Cached: GDP trend")
    except Exception as e:
        logger.error(f"  ✗ Failed to cache GDP trend: {e}")
        stats["failed"] += 1
    
    logger.info(f"Cache warmup complete: {stats}")
    return stats


if __name__ == "__main__":
    # Test cache
    key = "test_key"
    set_cached(key, {"test": "data"}, ttl=60)
    result = get_cached(key)
    assert result == {"test": "data"}, "Cache test failed"
    print("✓ Cache working correctly")
    
    count = invalidate_cache()
    print(f"✓ Invalidated {count} cache entries")
