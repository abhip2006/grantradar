"""
Simple caching utilities for analytics.

Provides an in-memory cache with TTL support for caching expensive analytics
calculations. For production, this can be replaced with Redis.

Features:
- In-memory cache with automatic TTL-based expiration
- Async-compatible decorator for caching function results
- Cache key generation from function arguments
- Manual cache invalidation support
"""
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Optional, TypeVar
import hashlib
import json
import logging

logger = logging.getLogger(__name__)

# Type variable for generic async functions
F = TypeVar("F", bound=Callable[..., Any])

# In-memory cache storage: key -> (value, expiration_time)
_cache: dict[str, tuple[Any, datetime]] = {}


def cache_key(*args, **kwargs) -> str:
    """
    Generate a cache key from function arguments.

    Args:
        *args: Positional arguments to include in the key
        **kwargs: Keyword arguments to include in the key

    Returns:
        MD5 hash of the serialized arguments
    """
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.md5(key_data.encode()).hexdigest()


def get_cached(key: str, ttl_minutes: int = 5) -> Optional[Any]:
    """
    Get a value from cache if it exists and hasn't expired.

    Args:
        key: Cache key to look up
        ttl_minutes: Time-to-live in minutes (used to check expiration)

    Returns:
        Cached value if found and not expired, None otherwise
    """
    if key in _cache:
        value, timestamp = _cache[key]
        if datetime.utcnow() - timestamp < timedelta(minutes=ttl_minutes):
            logger.debug(f"Cache hit for key: {key[:16]}...")
            return value
        # Expired, remove from cache
        del _cache[key]
        logger.debug(f"Cache expired for key: {key[:16]}...")
    return None


def set_cached(key: str, value: Any) -> None:
    """
    Set a value in the cache with the current timestamp.

    Args:
        key: Cache key
        value: Value to cache
    """
    _cache[key] = (value, datetime.utcnow())
    logger.debug(f"Cache set for key: {key[:16]}...")


def delete_cached(key: str) -> bool:
    """
    Delete a specific key from the cache.

    Args:
        key: Cache key to delete

    Returns:
        True if key was deleted, False if key didn't exist
    """
    if key in _cache:
        del _cache[key]
        logger.debug(f"Cache deleted for key: {key[:16]}...")
        return True
    return False


def clear_cache() -> int:
    """
    Clear all entries from the cache.

    Returns:
        Number of entries cleared
    """
    count = len(_cache)
    _cache.clear()
    logger.info(f"Cache cleared: {count} entries removed")
    return count


def invalidate_by_prefix(prefix: str) -> int:
    """
    Invalidate all cache entries that start with a given prefix.

    Args:
        prefix: Key prefix to match

    Returns:
        Number of entries invalidated
    """
    keys_to_delete = [k for k in _cache.keys() if k.startswith(prefix)]
    for key in keys_to_delete:
        del _cache[key]
    if keys_to_delete:
        logger.debug(f"Invalidated {len(keys_to_delete)} cache entries with prefix: {prefix}")
    return len(keys_to_delete)


def get_cache_stats() -> dict[str, Any]:
    """
    Get statistics about the current cache state.

    Returns:
        Dictionary with cache statistics
    """
    now = datetime.utcnow()
    expired_count = 0
    valid_count = 0
    oldest_entry = None
    newest_entry = None

    for key, (value, timestamp) in _cache.items():
        age = now - timestamp
        if age > timedelta(minutes=60):  # Consider >1 hour as "stale"
            expired_count += 1
        else:
            valid_count += 1

        if oldest_entry is None or timestamp < oldest_entry:
            oldest_entry = timestamp
        if newest_entry is None or timestamp > newest_entry:
            newest_entry = timestamp

    return {
        "total_entries": len(_cache),
        "valid_entries": valid_count,
        "stale_entries": expired_count,
        "oldest_entry": oldest_entry.isoformat() if oldest_entry else None,
        "newest_entry": newest_entry.isoformat() if newest_entry else None,
    }


def cached(ttl_minutes: int = 5):
    """
    Decorator for caching async function results.

    The cache key is generated from the function name and all arguments.
    Results are cached for the specified TTL.

    Args:
        ttl_minutes: Time-to-live for cached results in minutes

    Returns:
        Decorator function

    Usage:
        @cached(ttl_minutes=5)
        async def expensive_calculation(user_id: str) -> dict:
            # ... expensive operation ...
            return result
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key = f"{func.__module__}.{func.__name__}:{cache_key(*args, **kwargs)}"

            # Check cache
            result = get_cached(key, ttl_minutes)
            if result is not None:
                return result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            set_cached(key, result)
            return result
        return wrapper  # type: ignore
    return decorator


def cached_sync(ttl_minutes: int = 5):
    """
    Decorator for caching synchronous function results.

    Args:
        ttl_minutes: Time-to-live for cached results in minutes

    Returns:
        Decorator function
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key = f"{func.__module__}.{func.__name__}:{cache_key(*args, **kwargs)}"

            # Check cache
            result = get_cached(key, ttl_minutes)
            if result is not None:
                return result

            # Execute function and cache result
            result = func(*args, **kwargs)
            set_cached(key, result)
            return result
        return wrapper  # type: ignore
    return decorator


def make_user_cache_key(user_id: str, operation: str) -> str:
    """
    Create a standardized cache key for user-specific operations.

    Args:
        user_id: User ID
        operation: Operation name (e.g., "time_per_stage", "bottlenecks")

    Returns:
        Formatted cache key
    """
    return f"user:{user_id}:{operation}"


def invalidate_user_cache(user_id: str) -> int:
    """
    Invalidate all cache entries for a specific user.

    Args:
        user_id: User ID whose cache should be invalidated

    Returns:
        Number of entries invalidated
    """
    prefix = f"user:{user_id}:"
    keys_to_delete = [k for k in _cache.keys() if prefix in k]
    for key in keys_to_delete:
        del _cache[key]
    if keys_to_delete:
        logger.info(f"Invalidated {len(keys_to_delete)} cache entries for user: {user_id}")
    return len(keys_to_delete)


__all__ = [
    # Core functions
    "cache_key",
    "get_cached",
    "set_cached",
    "delete_cached",
    "clear_cache",
    "invalidate_by_prefix",
    "get_cache_stats",
    # Decorators
    "cached",
    "cached_sync",
    # User-specific helpers
    "make_user_cache_key",
    "invalidate_user_cache",
]
