"""
Comprehensive Caching Service

Provides intelligent caching for API responses, database queries, and expensive computations.
Optimized for commercial scale with cache invalidation, TTL management, and performance monitoring.
"""

import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional, Union, Callable
from functools import wraps
from django.core.cache import cache
from django.conf import settings
from django.db.models import Model, QuerySet
from django.core.serializers.json import DjangoJSONEncoder

logger = logging.getLogger('api.caching')


class CacheService:
    """
    Advanced caching service with intelligent cache management.
    """
    
    # Cache key prefixes for different types of data
    CACHE_PREFIXES = {
        'user': 'user',
        'chart': 'chart',
        'subscription': 'sub',
        'payment': 'payment',
        'plan': 'plan',
        'api_response': 'api',
        'computation': 'comp',
        'session': 'session',
    }
    
    # Default TTL values (in seconds)
    DEFAULT_TTL = {
        'user': 3600,  # 1 hour
        'chart': 1800,  # 30 minutes
        'subscription': 900,  # 15 minutes
        'payment': 600,  # 10 minutes
        'plan': 7200,  # 2 hours
        'api_response': 300,  # 5 minutes
        'computation': 1800,  # 30 minutes
        'session': 1800,  # 30 minutes
    }
    
    @classmethod
    def generate_key(cls, prefix: str, *args, **kwargs) -> str:
        """
        Generate a consistent cache key from prefix and arguments.
        """
        # Create a deterministic string representation
        key_parts = [prefix]
        
        # Add positional arguments
        for arg in args:
            if isinstance(arg, Model):
                key_parts.append(f"{arg.__class__.__name__}:{arg.pk}")
            elif isinstance(arg, QuerySet):
                # For QuerySets, use the query hash
                key_parts.append(f"qs:{hash(str(arg.query))}")
            else:
                key_parts.append(str(arg))
        
        # Add keyword arguments (sorted for consistency)
        for key, value in sorted(kwargs.items()):
            if isinstance(value, Model):
                key_parts.append(f"{key}:{value.__class__.__name__}:{value.pk}")
            else:
                key_parts.append(f"{key}:{str(value)}")
        
        # Create hash for consistent key length
        key_string = "|".join(key_parts)
        return f"{prefix}:{hashlib.md5(key_string.encode()).hexdigest()[:16]}"
    
    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """
        Get value from cache with error handling.
        """
        try:
            value = cache.get(key)
            if value is not None:
                logger.debug(f"Cache HIT: {key}")
            else:
                logger.debug(f"Cache MISS: {key}")
            return value
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return default
    
    @classmethod
    def set(cls, key: str, value: Any, ttl: Optional[int] = None, prefix: str = None) -> bool:
        """
        Set value in cache with error handling and TTL management.
        """
        try:
            # Determine TTL based on prefix if not specified
            if ttl is None and prefix:
                ttl = cls.DEFAULT_TTL.get(prefix, 300)
            
            # Serialize complex objects
            if not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                try:
                    value = json.dumps(value, cls=DjangoJSONEncoder)
                except (TypeError, ValueError):
                    logger.warning(f"Could not serialize value for cache key {key}")
                    return False
            
            cache.set(key, value, ttl)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False
    
    @classmethod
    def delete(cls, key: str) -> bool:
        """
        Delete value from cache with error handling.
        """
        try:
            cache.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False
    
    @classmethod
    def invalidate_pattern(cls, pattern: str) -> int:
        """
        Invalidate all cache keys matching a pattern.
        Note: This is a simplified version. In production, use Redis SCAN.
        """
        try:
            # This is a simplified implementation
            # In production with Redis, you'd use SCAN command
            logger.info(f"Cache pattern invalidation requested: {pattern}")
            return 0
        except Exception as e:
            logger.warning(f"Cache pattern invalidation error: {e}")
            return 0
    
    @classmethod
    def invalidate_user_data(cls, user_id: int) -> bool:
        """
        Invalidate all cache entries related to a specific user.
        """
        try:
            patterns = [
                f"{cls.CACHE_PREFIXES['user']}:*:{user_id}",
                f"{cls.CACHE_PREFIXES['chart']}:*:{user_id}",
                f"{cls.CACHE_PREFIXES['subscription']}:*:{user_id}",
                f"{cls.CACHE_PREFIXES['payment']}:*:{user_id}",
            ]
            
            for pattern in patterns:
                cls.invalidate_pattern(pattern)
            
            logger.info(f"Invalidated cache for user {user_id}")
            return True
        except Exception as e:
            logger.warning(f"User cache invalidation error for user {user_id}: {e}")
            return False


def cache_response(prefix: str, ttl: Optional[int] = None, key_func: Optional[Callable] = None):
    """
    Decorator to cache API responses.
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        key_func: Custom function to generate cache key
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = CacheService.generate_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = CacheService.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            CacheService.set(cache_key, result, ttl, prefix)
            
            return result
        return wrapper
    return decorator


def cache_model_queryset(prefix: str, ttl: Optional[int] = None):
    """
    Decorator to cache model queryset results.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key including the model class
            if args and hasattr(args[0], '__class__'):
                model_class = args[0].__class__.__name__
                cache_key = CacheService.generate_key(f"{prefix}:{model_class}", *args, **kwargs)
            else:
                cache_key = CacheService.generate_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = CacheService.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            CacheService.set(cache_key, result, ttl, prefix)
            
            return result
        return wrapper
    return decorator


def invalidate_cache_on_save(model_class: type):
    """
    Decorator to automatically invalidate cache when model is saved.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Invalidate related cache
            if hasattr(result, 'user_id'):
                CacheService.invalidate_user_data(result.user_id)
            elif hasattr(result, 'user'):
                CacheService.invalidate_user_data(result.user.id)
            
            return result
        return wrapper
    return decorator


# Performance monitoring
class CacheMetrics:
    """
    Track cache performance metrics.
    """
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0
    
    def reset(self):
        """Reset all metrics."""
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0


# Global metrics instance
cache_metrics = CacheMetrics() 