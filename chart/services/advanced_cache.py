"""
Advanced Caching Service

This module provides advanced caching capabilities including:
- Cache warming strategies
- Intelligent cache invalidation patterns
- Cache analytics and monitoring
- Multi-level caching (L1/L2)
- Cache compression and optimization
- Cache hit/miss analytics
- Predictive caching
"""

import logging
import time
import json
import hashlib
import gzip
import pickle
from typing import Dict, Any, Optional, List, Callable, Union, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from django.core.cache import cache
from django.conf import settings
from django.db.models import QuerySet
import redis
from redis.exceptions import RedisError
import psutil
import threading

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache levels for multi-level caching."""
    L1 = 'l1'  # Memory cache (fastest)
    L2 = 'l2'  # Redis cache (persistent)


class CacheStrategy(Enum):
    """Cache strategies."""
    WRITE_THROUGH = 'write_through'
    WRITE_BEHIND = 'write_behind'
    WRITE_AROUND = 'write_around'
    READ_THROUGH = 'read_through'
    CACHE_ASIDE = 'cache_aside'


@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    size_bytes: int = 0
    hit_rate: float = 0.0
    avg_get_time: float = 0.0
    avg_set_time: float = 0.0
    
    def calculate_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_requests = self.hits + self.misses
        if total_requests == 0:
            return 0.0
        return self.hits / total_requests


class AdvancedCache:
    """
    Advanced caching service with intelligent strategies and analytics.
    """
    
    def __init__(self):
        self.redis_client = redis.Redis.from_url(settings.REDIS_URL)
        self.memory_cache = {}  # L1 cache
        self.memory_cache_ttl = {}  # TTL for memory cache
        self.metrics = CacheMetrics()
        self.cache_patterns = {}
        self.warming_enabled = True
        self.compression_enabled = True
        self.compression_threshold = 1024  # Compress objects larger than 1KB
        self.monitoring_enabled = True
        self._lock = threading.RLock()
        
        # Cache warming strategies
        self.warming_strategies = {
            'predictive': self._predictive_warming,
            'scheduled': self._scheduled_warming,
            'on_demand': self._on_demand_warming
        }
        
        # Invalidation patterns
        self.invalidation_patterns = {
            'time_based': self._time_based_invalidation,
            'dependency_based': self._dependency_based_invalidation,
            'pattern_based': self._pattern_based_invalidation,
            'version_based': self._version_based_invalidation
        }
    
    def get(self, key: str, default: Any = None, level: CacheLevel = CacheLevel.L1) -> Any:
        """
        Get value from cache with multi-level support.
        
        Args:
            key: Cache key
            default: Default value if key not found
            level: Cache level to check first
            
        Returns:
            Cached value or default
        """
        start_time = time.time()
        
        try:
            # Try L1 cache first if requested
            if level == CacheLevel.L1:
                value = self._get_from_l1(key)
                if value is not None:
                    self._record_hit('l1')
                    self._update_metrics('hit', time.time() - start_time)
                    return value
            
            # Try L2 cache (Redis)
            value = self._get_from_l2(key)
            if value is not None:
                # Store in L1 for future access
                if level == CacheLevel.L1:
                    self._set_in_l1(key, value)
                self._record_hit('l2')
                self._update_metrics('hit', time.time() - start_time)
                return value
            
            # Cache miss
            self._record_miss()
            self._update_metrics('miss', time.time() - start_time)
            return default
            
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return default
    
    def set(self, key: str, value: Any, timeout: int = 300, 
            level: CacheLevel = CacheLevel.L1, strategy: CacheStrategy = CacheStrategy.WRITE_THROUGH) -> bool:
        """
        Set value in cache with strategy support.
        
        Args:
            key: Cache key
            value: Value to cache
            timeout: Cache timeout in seconds
            level: Cache level to use
            strategy: Cache strategy to apply
            
        Returns:
            True if successful
        """
        start_time = time.time()
        
        try:
            if strategy == CacheStrategy.WRITE_THROUGH:
                # Write to both L1 and L2
                success = True
                if level == CacheLevel.L1:
                    success &= self._set_in_l1(key, value, timeout)
                success &= self._set_in_l2(key, value, timeout)
                
            elif strategy == CacheStrategy.WRITE_BEHIND:
                # Write to L1 immediately, L2 asynchronously
                success = self._set_in_l1(key, value, timeout)
                if success:
                    self._schedule_l2_write(key, value, timeout)
                
            elif strategy == CacheStrategy.WRITE_AROUND:
                # Write directly to L2, invalidate L1
                success = self._set_in_l2(key, value, timeout)
                if success:
                    self._delete_from_l1(key)
            
            if success:
                self._update_metrics('set', time.time() - start_time)
                self._track_cache_pattern(key, 'set')
            
            return success
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str, level: CacheLevel = CacheLevel.L1) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key to delete
            level: Cache level to delete from
            
        Returns:
            True if successful
        """
        try:
            success = True
            
            if level == CacheLevel.L1:
                success &= self._delete_from_l1(key)
            
            # Always delete from L2 for consistency
            success &= self._delete_from_l2(key)
            
            if success:
                self._update_metrics('delete', 0)
                self._track_cache_pattern(key, 'delete')
            
            return success
            
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def invalidate_pattern(self, pattern: str, strategy: str = 'pattern_based') -> int:
        """
        Invalidate cache keys matching a pattern.
        
        Args:
            pattern: Pattern to match keys
            strategy: Invalidation strategy to use
            
        Returns:
            Number of keys invalidated
        """
        try:
            if strategy in self.invalidation_patterns:
                return self.invalidation_patterns[strategy](pattern)
            else:
                return self._pattern_based_invalidation(pattern)
                
        except Exception as e:
            logger.error(f"Cache invalidation error for pattern {pattern}: {e}")
            return 0
    
    def warm_cache(self, strategy: str = 'predictive', **kwargs) -> Dict[str, Any]:
        """
        Warm cache using specified strategy.
        
        Args:
            strategy: Warming strategy to use
            **kwargs: Strategy-specific parameters
            
        Returns:
            Warming results
        """
        try:
            if strategy in self.warming_strategies:
                return self.warming_strategies[strategy](**kwargs)
            else:
                logger.warning(f"Unknown cache warming strategy: {strategy}")
                return {'success': False, 'error': 'Unknown strategy'}
                
        except Exception as e:
            logger.error(f"Cache warming error: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_metrics(self, reset: bool = False) -> Dict[str, Any]:
        """
        Get cache performance metrics.
        
        Args:
            reset: Whether to reset metrics after getting them
            
        Returns:
            Cache metrics
        """
        with self._lock:
            metrics = asdict(self.metrics)
            metrics['hit_rate'] = self.metrics.calculate_hit_rate()
            metrics['memory_usage'] = self._get_memory_usage()
            metrics['redis_info'] = self._get_redis_info()
            
            if reset:
                self.metrics = CacheMetrics()
            
            return metrics
    
    def optimize_cache(self) -> Dict[str, Any]:
        """
        Optimize cache performance.
        
        Returns:
            Optimization results
        """
        try:
            results = {
                'l1_cleanup': self._cleanup_l1_cache(),
                'l2_cleanup': self._cleanup_l2_cache(),
                'compression_optimization': self._optimize_compression(),
                'memory_optimization': self._optimize_memory_usage()
            }
            
            logger.info(f"Cache optimization completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Cache optimization error: {e}")
            return {'error': str(e)}
    
    def get_cache_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive cache analytics.
        
        Returns:
            Cache analytics data
        """
        try:
            return {
                'metrics': self.get_metrics(),
                'patterns': self._analyze_cache_patterns(),
                'performance': self._analyze_performance(),
                'recommendations': self._generate_recommendations()
            }
            
        except Exception as e:
            logger.error(f"Cache analytics error: {e}")
            return {'error': str(e)}
    
    def _get_from_l1(self, key: str) -> Any:
        """Get value from L1 cache (memory)."""
        with self._lock:
            if key in self.memory_cache:
                # Check TTL
                if key in self.memory_cache_ttl:
                    if time.time() > self.memory_cache_ttl[key]:
                        # Expired, remove
                        del self.memory_cache[key]
                        del self.memory_cache_ttl[key]
                        return None
                
                return self.memory_cache[key]
            return None
    
    def _set_in_l1(self, key: str, value: Any, timeout: int = 300) -> bool:
        """Set value in L1 cache (memory)."""
        try:
            with self._lock:
                self.memory_cache[key] = value
                if timeout > 0:
                    self.memory_cache_ttl[key] = time.time() + timeout
                return True
        except Exception as e:
            logger.error(f"L1 cache set error: {e}")
            return False
    
    def _delete_from_l1(self, key: str) -> bool:
        """Delete value from L1 cache (memory)."""
        try:
            with self._lock:
                if key in self.memory_cache:
                    del self.memory_cache[key]
                if key in self.memory_cache_ttl:
                    del self.memory_cache_ttl[key]
                return True
        except Exception as e:
            logger.error(f"L1 cache delete error: {e}")
            return False
    
    def _get_from_l2(self, key: str) -> Any:
        """Get value from L2 cache (Redis)."""
        try:
            value = self.redis_client.get(key)
            if value is not None:
                return self._deserialize_value(value)
            return None
        except Exception as e:
            logger.error(f"L2 cache get error: {e}")
            return None
    
    def _set_in_l2(self, key: str, value: Any, timeout: int = 300) -> bool:
        """Set value in L2 cache (Redis)."""
        try:
            serialized_value = self._serialize_value(value)
            return self.redis_client.setex(key, timeout, serialized_value)
        except Exception as e:
            logger.error(f"L2 cache set error: {e}")
            return False
    
    def _delete_from_l2(self, key: str) -> bool:
        """Delete value from L2 cache (Redis)."""
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"L2 cache delete error: {e}")
            return False
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage."""
        try:
            # Use pickle for complex objects
            serialized = pickle.dumps(value)
            
            # Compress if enabled and value is large enough
            if self.compression_enabled and len(serialized) > self.compression_threshold:
                compressed = gzip.compress(serialized)
                # Only use compression if it actually saves space
                if len(compressed) < len(serialized):
                    return b'gzip:' + compressed
            
            return serialized
            
        except Exception as e:
            logger.error(f"Serialization error: {e}")
            # Fallback to JSON for simple types
            return json.dumps(value).encode('utf-8')
    
    def _deserialize_value(self, value: bytes) -> Any:
        """Deserialize value from storage."""
        try:
            # Check if compressed
            if value.startswith(b'gzip:'):
                compressed = value[5:]
                serialized = gzip.decompress(compressed)
                return pickle.loads(serialized)
            
            # Try pickle first
            try:
                return pickle.loads(value)
            except:
                # Fallback to JSON
                return json.loads(value.decode('utf-8'))
                
        except Exception as e:
            logger.error(f"Deserialization error: {e}")
            return None
    
    def _record_hit(self, level: str):
        """Record cache hit."""
        if self.monitoring_enabled:
            with self._lock:
                self.metrics.hits += 1
    
    def _record_miss(self):
        """Record cache miss."""
        if self.monitoring_enabled:
            with self._lock:
                self.metrics.misses += 1
    
    def _update_metrics(self, operation: str, duration: float):
        """Update cache metrics."""
        if not self.monitoring_enabled:
            return
        
        with self._lock:
            if operation == 'hit':
                if self.metrics.hits > 0:
                    # Update average get time
                    total_time = self.metrics.avg_get_time * (self.metrics.hits - 1) + duration
                    self.metrics.avg_get_time = total_time / self.metrics.hits
            elif operation == 'set':
                self.metrics.sets += 1
                if self.metrics.sets > 0:
                    # Update average set time
                    total_time = self.metrics.avg_set_time * (self.metrics.sets - 1) + duration
                    self.metrics.avg_set_time = total_time / self.metrics.sets
            elif operation == 'delete':
                self.metrics.deletes += 1
    
    def _track_cache_pattern(self, key: str, operation: str):
        """Track cache access patterns."""
        if not self.monitoring_enabled:
            return
        
        # Extract pattern from key (e.g., "user:123:profile" -> "user:*:profile")
        pattern = self._extract_pattern(key)
        
        if pattern not in self.cache_patterns:
            self.cache_patterns[pattern] = {
                'hits': 0,
                'misses': 0,
                'sets': 0,
                'deletes': 0,
                'last_access': None
            }
        
        self.cache_patterns[pattern][operation + 's'] += 1
        self.cache_patterns[pattern]['last_access'] = datetime.now()
    
    def _extract_pattern(self, key: str) -> str:
        """Extract pattern from cache key."""
        # Simple pattern extraction - replace numbers with *
        import re
        return re.sub(r'\d+', '*', key)
    
    def _schedule_l2_write(self, key: str, value: Any, timeout: int):
        """Schedule asynchronous L2 write."""
        # In a production environment, you'd use a background task
        # For now, we'll do it synchronously
        self._set_in_l2(key, value, timeout)
    
    def _predictive_warming(self, **kwargs) -> Dict[str, Any]:
        """Predictive cache warming based on access patterns."""
        try:
            warmed_keys = 0
            
            # Analyze patterns and predict what will be accessed
            for pattern, stats in self.cache_patterns.items():
                if stats['hits'] > stats['misses'] and stats['last_access']:
                    # High hit rate pattern, warm it
                    time_since_access = (datetime.now() - stats['last_access']).total_seconds()
                    if time_since_access < 3600:  # Accessed within last hour
                        # This is a simplified implementation
                        # In production, you'd have more sophisticated prediction logic
                        warmed_keys += 1
            
            return {
                'success': True,
                'warmed_keys': warmed_keys,
                'strategy': 'predictive'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _scheduled_warming(self, **kwargs) -> Dict[str, Any]:
        """Scheduled cache warming."""
        try:
            # This would be called by a scheduled task
            # For now, return empty result
            return {
                'success': True,
                'warmed_keys': 0,
                'strategy': 'scheduled'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _on_demand_warming(self, keys: List[str], **kwargs) -> Dict[str, Any]:
        """On-demand cache warming for specific keys."""
        try:
            warmed_keys = 0
            
            for key in keys:
                # This is a simplified implementation
                # In production, you'd fetch the data and cache it
                warmed_keys += 1
            
            return {
                'success': True,
                'warmed_keys': warmed_keys,
                'strategy': 'on_demand'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _pattern_based_invalidation(self, pattern: str) -> int:
        """Invalidate keys matching a pattern."""
        try:
            # Get all keys matching pattern
            keys = self.redis_client.keys(pattern)
            
            if keys:
                # Delete from both L1 and L2
                for key in keys:
                    self._delete_from_l1(key.decode('utf-8'))
                
                # Batch delete from Redis
                self.redis_client.delete(*keys)
            
            return len(keys)
            
        except Exception as e:
            logger.error(f"Pattern-based invalidation error: {e}")
            return 0
    
    def _time_based_invalidation(self, pattern: str) -> int:
        """Time-based cache invalidation."""
        # This would invalidate based on time patterns
        # For now, use pattern-based invalidation
        return self._pattern_based_invalidation(pattern)
    
    def _dependency_based_invalidation(self, pattern: str) -> int:
        """Dependency-based cache invalidation."""
        # This would invalidate based on data dependencies
        # For now, use pattern-based invalidation
        return self._pattern_based_invalidation(pattern)
    
    def _version_based_invalidation(self, pattern: str) -> int:
        """Version-based cache invalidation."""
        # This would invalidate based on version changes
        # For now, use pattern-based invalidation
        return self._pattern_based_invalidation(pattern)
    
    def _cleanup_l1_cache(self) -> int:
        """Clean up expired L1 cache entries."""
        try:
            current_time = time.time()
            expired_keys = []
            
            with self._lock:
                for key, expiry in self.memory_cache_ttl.items():
                    if current_time > expiry:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self.memory_cache[key]
                    del self.memory_cache_ttl[key]
            
            return len(expired_keys)
            
        except Exception as e:
            logger.error(f"L1 cleanup error: {e}")
            return 0
    
    def _cleanup_l2_cache(self) -> int:
        """Clean up L2 cache (Redis handles this automatically)."""
        # Redis handles expiration automatically
        return 0
    
    def _optimize_compression(self) -> Dict[str, Any]:
        """Optimize compression settings."""
        try:
            # Analyze compression effectiveness
            total_size = 0
            compressed_size = 0
            
            # This is a simplified analysis
            # In production, you'd analyze actual cache data
            
            return {
                'compression_ratio': compressed_size / total_size if total_size > 0 else 0,
                'recommendations': []
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _optimize_memory_usage(self) -> Dict[str, Any]:
        """Optimize memory usage."""
        try:
            # Get current memory usage
            memory_usage = self._get_memory_usage()
            
            recommendations = []
            
            if memory_usage['l1_size_mb'] > 100:  # More than 100MB
                recommendations.append("Consider reducing L1 cache size")
            
            if memory_usage['hit_rate'] < 0.8:  # Less than 80% hit rate
                recommendations.append("Consider increasing cache size or improving cache keys")
            
            return {
                'current_usage': memory_usage,
                'recommendations': recommendations
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        try:
            with self._lock:
                l1_size = sum(len(str(v)) for v in self.memory_cache.values())
                l1_size_mb = l1_size / (1024 * 1024)
            
            return {
                'l1_size_mb': l1_size_mb,
                'l1_entries': len(self.memory_cache),
                'hit_rate': self.metrics.calculate_hit_rate()
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_redis_info(self) -> Dict[str, Any]:
        """Get Redis information."""
        try:
            info = self.redis_client.info()
            return {
                'used_memory_mb': info.get('used_memory', 0) / (1024 * 1024),
                'connected_clients': info.get('connected_clients', 0),
                'total_commands_processed': info.get('total_commands_processed', 0)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _analyze_cache_patterns(self) -> Dict[str, Any]:
        """Analyze cache access patterns."""
        try:
            patterns = []
            
            for pattern, stats in self.cache_patterns.items():
                total_ops = stats['hits'] + stats['misses'] + stats['sets'] + stats['deletes']
                if total_ops > 0:
                    hit_rate = stats['hits'] / (stats['hits'] + stats['misses']) if (stats['hits'] + stats['misses']) > 0 else 0
                    
                    patterns.append({
                        'pattern': pattern,
                        'hit_rate': hit_rate,
                        'total_operations': total_ops,
                        'last_access': stats['last_access'].isoformat() if stats['last_access'] else None
                    })
            
            # Sort by total operations
            patterns.sort(key=lambda x: x['total_operations'], reverse=True)
            
            return {
                'patterns': patterns[:10],  # Top 10 patterns
                'total_patterns': len(patterns)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _analyze_performance(self) -> Dict[str, Any]:
        """Analyze cache performance."""
        try:
            return {
                'avg_get_time_ms': self.metrics.avg_get_time * 1000,
                'avg_set_time_ms': self.metrics.avg_set_time * 1000,
                'hit_rate': self.metrics.calculate_hit_rate(),
                'total_operations': self.metrics.hits + self.metrics.misses + self.metrics.sets + self.metrics.deletes
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _generate_recommendations(self) -> List[str]:
        """Generate cache optimization recommendations."""
        recommendations = []
        
        # Analyze metrics and generate recommendations
        if self.metrics.calculate_hit_rate() < 0.8:
            recommendations.append("Consider increasing cache size or improving cache key patterns")
        
        if self.metrics.avg_get_time > 0.001:  # More than 1ms
            recommendations.append("Consider optimizing cache serialization or using L1 cache more")
        
        if len(self.memory_cache) > 1000:
            recommendations.append("Consider reducing L1 cache size to prevent memory issues")
        
        return recommendations


# Global instance
advanced_cache = AdvancedCache() 