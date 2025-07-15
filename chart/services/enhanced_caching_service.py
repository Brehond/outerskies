"""
Enhanced Caching Service with Connection Pooling and Performance Monitoring

This module provides advanced caching capabilities with:
- Connection pooling for Redis
- Async support for heavy operations
- Performance monitoring and metrics
- Multi-level caching strategy
- Cache analytics and health monitoring
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional, List, Union
from functools import wraps
from datetime import datetime, timedelta
import redis
from redis.connection import ConnectionPool
from django.conf import settings
from django.core.cache import cache as django_cache
import threading
from collections import defaultdict, deque
import hashlib

logger = logging.getLogger(__name__)


class CacheMetrics:
    """Track cache performance metrics"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.errors = 0
        self.total_operations = 0
        self.operation_times = deque(maxlen=1000)  # Keep last 1000 operations
        self.error_counts = defaultdict(int)
        self.lock = threading.Lock()
    
    def record_hit(self, operation_time: float = 0):
        with self.lock:
            self.hits += 1
            self.total_operations += 1
            if operation_time > 0:
                self.operation_times.append(operation_time)
    
    def record_miss(self, operation_time: float = 0):
        with self.lock:
            self.misses += 1
            self.total_operations += 1
            if operation_time > 0:
                self.operation_times.append(operation_time)
    
    def record_error(self, error_type: str, operation_time: float = 0):
        with self.lock:
            self.errors += 1
            self.total_operations += 1
            self.error_counts[error_type] += 1
            if operation_time > 0:
                self.operation_times.append(operation_time)
    
    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            hit_rate = (self.hits / self.total_operations * 100) if self.total_operations > 0 else 0
            avg_time = sum(self.operation_times) / len(self.operation_times) if self.operation_times else 0
            
            return {
                'hits': self.hits,
                'misses': self.misses,
                'errors': self.errors,
                'total_operations': self.total_operations,
                'hit_rate_percent': round(hit_rate, 2),
                'average_operation_time_ms': round(avg_time * 1000, 2),
                'error_counts': dict(self.error_counts),
                'last_updated': datetime.now().isoformat()
            }


class EnhancedCachingService:
    """
    Enhanced caching service with connection pooling, async support, and monitoring
    """
    
    def __init__(self):
        self.metrics = CacheMetrics()
        self.redis_pool = None
        self.redis_client = None
        self._initialize_redis()
        self.cache_prefixes = {
            'chart': 'chart:',
            'ephemeris': 'ephemeris:',
            'ai': 'ai:',
            'user': 'user:',
            'system': 'system:'
        }
        self.default_timeouts = {
            'chart': 3600,      # 1 hour
            'ephemeris': 7200,  # 2 hours
            'ai': 1800,         # 30 minutes
            'user': 86400,      # 24 hours
            'system': 300       # 5 minutes
        }
    
    def _initialize_redis(self):
        """Initialize Redis connection pool"""
        try:
            redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
            self.redis_pool = ConnectionPool.from_url(
                redis_url,
                max_connections=20,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            self.redis_client = redis.Redis(connection_pool=self.redis_pool)
            
            # Test connection
            self.redis_client.ping()
            logger.info("Enhanced Redis connection pool initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection pool: {e}")
            self.redis_client = None
    
    def _get_cache_key(self, prefix: str, key: Union[str, Dict]) -> str:
        """Generate consistent cache key"""
        if isinstance(key, dict):
            # Filter out non-serializable items and sort
            serializable_items = []
            for k, v in key.items():
                try:
                    # Test if item is JSON serializable
                    json.dumps(v)
                    serializable_items.append((k, v))
                except (TypeError, ValueError):
                    # Replace non-serializable items with string representation
                    serializable_items.append((k, str(v)))
            
            sorted_items = sorted(serializable_items)
            key_str = json.dumps(sorted_items, sort_keys=True)
        else:
            try:
                json.dumps(key)
                key_str = str(key)
            except (TypeError, ValueError):
                key_str = str(key)
        
        # Create hash for long keys
        if len(key_str) > 100:
            key_hash = hashlib.md5(key_str.encode()).hexdigest()
            return f"{self.cache_prefixes.get(prefix, 'cache:')}{key_hash}"
        
        return f"{self.cache_prefixes.get(prefix, 'cache:')}{key_str}"
    
    def _measure_operation(self, func):
        """Decorator to measure operation performance"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                operation_time = time.time() - start_time
                self.metrics.record_hit(operation_time)
                return result
            except Exception as e:
                operation_time = time.time() - start_time
                self.metrics.record_error(type(e).__name__, operation_time)
                raise
        return wrapper
    
    def get(self, prefix: str, key: Union[str, Dict], default: Any = None) -> Any:
        """
        Get value from cache with performance monitoring
        
        Args:
            prefix: Cache prefix (chart, ephemeris, ai, user, system)
            key: Cache key or dict for complex keys
            default: Default value if not found
            
        Returns:
            Cached value or default
        """
        if not self.redis_client:
            return default
        
        cache_key = self._get_cache_key(prefix, key)
        start_time = time.time()
        
        try:
            value = self.redis_client.get(cache_key)
            operation_time = time.time() - start_time
            
            if value is not None:
                self.metrics.record_hit(operation_time)
                return json.loads(value)
            else:
                self.metrics.record_miss(operation_time)
                return default
                
        except Exception as e:
            operation_time = time.time() - start_time
            self.metrics.record_error(type(e).__name__, operation_time)
            logger.error(f"Cache get error: {e}")
            return default
    
    def set(self, prefix: str, key: Union[str, Dict], value: Any, 
            timeout: Optional[int] = None) -> bool:
        """
        Set value in cache with performance monitoring
        
        Args:
            prefix: Cache prefix
            key: Cache key or dict
            value: Value to cache
            timeout: Cache timeout in seconds
            
        Returns:
            Success status
        """
        if not self.redis_client:
            return False
        
        cache_key = self._get_cache_key(prefix, key)
        timeout = timeout or self.default_timeouts.get(prefix, 3600)
        start_time = time.time()
        
        try:
            serialized_value = json.dumps(value, default=str)
            result = self.redis_client.setex(cache_key, timeout, serialized_value)
            operation_time = time.time() - start_time
            self.metrics.record_hit(operation_time)
            return bool(result)
            
        except Exception as e:
            operation_time = time.time() - start_time
            self.metrics.record_error(type(e).__name__, operation_time)
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, prefix: str, key: Union[str, Dict]) -> bool:
        """Delete value from cache"""
        if not self.redis_client:
            return False
        
        cache_key = self._get_cache_key(prefix, key)
        start_time = time.time()
        
        try:
            result = self.redis_client.delete(cache_key)
            operation_time = time.time() - start_time
            self.metrics.record_hit(operation_time)
            return bool(result)
            
        except Exception as e:
            operation_time = time.time() - start_time
            self.metrics.record_error(type(e).__name__, operation_time)
            logger.error(f"Cache delete error: {e}")
            return False
    
    def clear_prefix(self, prefix: str) -> int:
        """Clear all keys with a specific prefix"""
        if not self.redis_client:
            return 0
        
        pattern = f"{self.cache_prefixes.get(prefix, 'cache:')}*"
        start_time = time.time()
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                operation_time = time.time() - start_time
                self.metrics.record_hit(operation_time)
                logger.info(f"Cleared {deleted} cache entries for prefix: {prefix}")
                return deleted
            return 0
            
        except Exception as e:
            operation_time = time.time() - start_time
            self.metrics.record_error(type(e).__name__, operation_time)
            logger.error(f"Cache clear error: {e}")
            return 0
    
    async def get_async(self, prefix: str, key: Union[str, Dict], default: Any = None) -> Any:
        """Async version of get method"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get, prefix, key, default)
    
    async def set_async(self, prefix: str, key: Union[str, Dict], value: Any, 
                       timeout: Optional[int] = None) -> bool:
        """Async version of set method"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.set, prefix, key, value, timeout)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get cache health status"""
        try:
            if not self.redis_client:
                return {
                    'status': 'unavailable',
                    'redis_connected': False,
                    'error': 'Redis client not initialized'
                }
            
            # Test connection
            self.redis_client.ping()
            
            # Get Redis info
            info = self.redis_client.info()
            
            # Get cache stats
            stats = self.metrics.get_stats()
            
            return {
                'status': 'healthy',
                'redis_connected': True,
                'redis_info': {
                    'used_memory': info.get('used_memory_human', 'Unknown'),
                    'connected_clients': info.get('connected_clients', 0),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0),
                    'uptime': info.get('uptime_in_seconds', 0)
                },
                'cache_stats': stats,
                'pool_info': {
                    'connection_pool_size': self.redis_pool._created_connections,
                    'available_connections': self.redis_pool._available_connections
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'redis_connected': False,
                'error': str(e)
            }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get detailed performance summary"""
        stats = self.metrics.get_stats()
        
        # Calculate additional metrics
        total_time = sum(self.metrics.operation_times) if self.metrics.operation_times else 0
        max_time = max(self.metrics.operation_times) if self.metrics.operation_times else 0
        min_time = min(self.metrics.operation_times) if self.metrics.operation_times else 0
        
        return {
            'cache_performance': {
                'hit_rate_percent': stats['hit_rate_percent'],
                'average_operation_time_ms': stats['average_operation_time_ms'],
                'total_operations': stats['total_operations'],
                'total_time_seconds': round(total_time, 3),
                'max_operation_time_ms': round(max_time * 1000, 2),
                'min_operation_time_ms': round(min_time * 1000, 2)
            },
            'error_analysis': {
                'total_errors': stats['errors'],
                'error_rate_percent': round(stats['errors'] / stats['total_operations'] * 100, 2) if stats['total_operations'] > 0 else 0,
                'error_types': stats['error_counts']
            },
            'recommendations': self._generate_recommendations(stats)
        }
    
    def _generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []
        
        if stats['hit_rate_percent'] < 70:
            recommendations.append("Consider increasing cache timeouts or optimizing cache keys")
        
        if stats['average_operation_time_ms'] > 10:
            recommendations.append("Cache operations are slow - check Redis performance")
        
        if stats['errors'] > 0:
            recommendations.append("Cache errors detected - review Redis configuration")
        
        if not recommendations:
            recommendations.append("Cache performance is optimal")
        
        return recommendations


# Global instance
enhanced_cache = EnhancedCachingService()


def cache_result(prefix: str, timeout: Optional[int] = None):
    """
    Decorator for caching function results
    
    Args:
        prefix: Cache prefix
        timeout: Cache timeout in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = {
                'func': func.__name__,
                'args': args,
                'kwargs': kwargs
            }
            
            # Try to get from cache
            cached_result = enhanced_cache.get(prefix, cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            enhanced_cache.set(prefix, cache_key, result, timeout)
            return result
        
        return wrapper
    return decorator


def async_cache_result(prefix: str, timeout: Optional[int] = None):
    """
    Decorator for caching async function results
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = {
                'func': func.__name__,
                'args': args,
                'kwargs': kwargs
            }
            
            # Try to get from cache
            cached_result = await enhanced_cache.get_async(prefix, cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await enhanced_cache.set_async(prefix, cache_key, result, timeout)
            return result
        
        return wrapper
    return decorator 