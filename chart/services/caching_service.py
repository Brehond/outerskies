"""
Caching Service

This service handles all caching operations for chart calculations.
Focused responsibility: Caching only.
"""

import logging
import hashlib
import json
import pickle
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta
import redis
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class ChartCachingService:
    """
    Focused service for caching chart calculations
    """
    
    def __init__(self, cache_timeout: int = 3600):
        self.cache_timeout = cache_timeout
        self.redis_client = None
        self._init_redis()
    
    def _init_redis(self):
        """
        Initialize Redis connection
        """
        try:
            redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
            self.redis_client = redis.from_url(redis_url)
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Falling back to Django cache.")
            self.redis_client = None
    
    def _generate_cache_key(self, data: Dict[str, Any], prefix: str = "chart") -> str:
        """
        Generate a unique cache key from data

        Args:
            data: Data to hash
            prefix: Cache key prefix

        Returns:
            Unique cache key
        """
        # Create a deterministic string representation
        data_str = json.dumps(data, sort_keys=True)
        hash_obj = hashlib.md5(data_str.encode())
        return f"{prefix}:{hash_obj.hexdigest()}"
    
    def get_cached_calculation(self, calculation_type: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get cached calculation result

        Args:
            calculation_type: Type of calculation (planets, houses, aspects, etc.)
            params: Calculation parameters

        Returns:
            Cached result or None if not found
        """
        cache_key = self._generate_cache_key(params, f"chart:{calculation_type}")
        
        try:
            if self.redis_client:
                # Try Redis first
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    return pickle.loads(cached_data)
            
            # Fallback to Django cache
            cached_data = cache.get(cache_key)
            if cached_data:
                return cached_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached calculation: {e}")
            return None
    
    def cache_calculation(self, calculation_type: str, params: Dict[str, Any], 
                         result: Dict[str, Any], timeout: int = None) -> bool:
        """
        Cache calculation result

        Args:
            calculation_type: Type of calculation
            params: Calculation parameters
            result: Calculation result to cache
            timeout: Cache timeout in seconds (uses default if None)

        Returns:
            True if cached successfully, False otherwise
        """
        if timeout is None:
            timeout = self.cache_timeout
        
        cache_key = self._generate_cache_key(params, f"chart:{calculation_type}")
        
        try:
            if self.redis_client:
                # Try Redis first
                self.redis_client.setex(
                    cache_key,
                    timeout,
                    pickle.dumps(result)
                )
                logger.debug(f"Cached {calculation_type} calculation in Redis")
                return True
            
            # Fallback to Django cache
            cache.set(cache_key, result, timeout)
            logger.debug(f"Cached {calculation_type} calculation in Django cache")
            return True
            
        except Exception as e:
            logger.error(f"Error caching calculation: {e}")
            return False
    
    def invalidate_calculation(self, calculation_type: str, params: Dict[str, Any]) -> bool:
        """
        Invalidate cached calculation

        Args:
            calculation_type: Type of calculation
            params: Calculation parameters

        Returns:
            True if invalidated successfully, False otherwise
        """
        cache_key = self._generate_cache_key(params, f"chart:{calculation_type}")
        
        try:
            if self.redis_client:
                # Try Redis first
                self.redis_client.delete(cache_key)
            
            # Also clear Django cache
            cache.delete(cache_key)
            
            logger.debug(f"Invalidated {calculation_type} calculation cache")
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
            return False
    
    def clear_all_chart_cache(self) -> bool:
        """
        Clear all chart-related cache

        Returns:
            True if cleared successfully, False otherwise
        """
        try:
            if self.redis_client:
                # Clear Redis keys with chart prefix
                pattern = "chart:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            
            # Django cache doesn't support pattern deletion, so we can't clear it easily
            # This is a limitation of Django's cache framework
            
            logger.info("Cleared all chart cache")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing chart cache: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache statistics
        """
        stats = {
            "redis_available": self.redis_client is not None,
            "cache_timeout": self.cache_timeout
        }
        
        try:
            if self.redis_client:
                # Get Redis info
                info = self.redis_client.info()
                stats.update({
                    "redis_used_memory": info.get("used_memory_human", "Unknown"),
                    "redis_connected_clients": info.get("connected_clients", 0),
                    "redis_keyspace_hits": info.get("keyspace_hits", 0),
                    "redis_keyspace_misses": info.get("keyspace_misses", 0)
                })
                
                # Count chart keys
                chart_keys = self.redis_client.keys("chart:*")
                stats["chart_cache_entries"] = len(chart_keys)
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            stats["error"] = str(e)
        
        return stats
    
    def cache_planetary_positions(self, jd: float, positions: Dict[str, Any]) -> bool:
        """
        Cache planetary positions

        Args:
            jd: Julian Day
            positions: Planetary positions

        Returns:
            True if cached successfully
        """
        params = {"jd": jd, "type": "planetary_positions"}
        return self.cache_calculation("planets", params, positions)
    
    def get_cached_planetary_positions(self, jd: float) -> Optional[Dict[str, Any]]:
        """
        Get cached planetary positions

        Args:
            jd: Julian Day

        Returns:
            Cached positions or None
        """
        params = {"jd": jd, "type": "planetary_positions"}
        return self.get_cached_calculation("planets", params)
    
    def cache_house_positions(self, jd: float, latitude: float, longitude: float, 
                            house_system: str, house_data: Dict[str, Any]) -> bool:
        """
        Cache house positions

        Args:
            jd: Julian Day
            latitude: Latitude
            longitude: Longitude
            house_system: House system
            house_data: House data

        Returns:
            True if cached successfully
        """
        params = {
            "jd": jd,
            "latitude": latitude,
            "longitude": longitude,
            "house_system": house_system,
            "type": "house_positions"
        }
        return self.cache_calculation("houses", params, house_data)
    
    def get_cached_house_positions(self, jd: float, latitude: float, longitude: float, 
                                 house_system: str) -> Optional[Dict[str, Any]]:
        """
        Get cached house positions

        Args:
            jd: Julian Day
            latitude: Latitude
            longitude: Longitude
            house_system: House system

        Returns:
            Cached house data or None
        """
        params = {
            "jd": jd,
            "latitude": latitude,
            "longitude": longitude,
            "house_system": house_system,
            "type": "house_positions"
        }
        return self.get_cached_calculation("houses", params)
    
    def cache_aspects(self, positions: Dict[str, Any], aspects: Dict[str, Any]) -> bool:
        """
        Cache aspect calculations

        Args:
            positions: Planetary positions
            aspects: Aspect calculations

        Returns:
            True if cached successfully
        """
        # Create a hash of positions for the cache key
        positions_hash = hashlib.md5(json.dumps(positions, sort_keys=True).encode()).hexdigest()
        params = {"positions_hash": positions_hash, "type": "aspects"}
        return self.cache_calculation("aspects", params, aspects)
    
    def get_cached_aspects(self, positions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get cached aspect calculations

        Args:
            positions: Planetary positions

        Returns:
            Cached aspects or None
        """
        positions_hash = hashlib.md5(json.dumps(positions, sort_keys=True).encode()).hexdigest()
        params = {"positions_hash": positions_hash, "type": "aspects"}
        return self.get_cached_calculation("aspects", params)
    
    def cache_dignities(self, positions: Dict[str, Any], dignities: Dict[str, Any]) -> bool:
        """
        Cache dignity calculations

        Args:
            positions: Planetary positions
            dignities: Dignity calculations

        Returns:
            True if cached successfully
        """
        positions_hash = hashlib.md5(json.dumps(positions, sort_keys=True).encode()).hexdigest()
        params = {"positions_hash": positions_hash, "type": "dignities"}
        return self.cache_calculation("dignities", params, dignities)
    
    def get_cached_dignities(self, positions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get cached dignity calculations

        Args:
            positions: Planetary positions

        Returns:
            Cached dignities or None
        """
        positions_hash = hashlib.md5(json.dumps(positions, sort_keys=True).encode()).hexdigest()
        params = {"positions_hash": positions_hash, "type": "dignities"}
        return self.get_cached_calculation("dignities", params)
    
    def is_cache_healthy(self) -> bool:
        """
        Check if cache is healthy and accessible

        Returns:
            True if cache is healthy
        """
        try:
            if self.redis_client:
                self.redis_client.ping()
                return True
            else:
                # Test Django cache
                test_key = "cache_health_test"
                cache.set(test_key, "test", 10)
                result = cache.get(test_key)
                cache.delete(test_key)
                return result == "test"
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return False 