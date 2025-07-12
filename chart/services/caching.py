"""
Caching Service for Outer Skies

This module provides comprehensive caching for expensive operations:
- Swiss Ephemeris calculations
- AI interpretations
- User session data
- Chart data
- Theme configurations
"""

import hashlib
import json
import logging
from typing import Any, Dict, Optional, Union
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
import pickle

logger = logging.getLogger(__name__)


class CacheService:
    """
    Centralized caching service for Outer Skies application
    """

    # Cache key prefixes
    CACHE_PREFIXES = {
        'ephemeris': 'ephemeris',
        'ai_interpretation': 'ai_interp',
        'chart_data': 'chart_data',
        'user_session': 'user_sess',
        'theme_config': 'theme',
        'api_response': 'api_resp',
        'planetary_positions': 'planets',
        'house_positions': 'houses',
        'aspects': 'aspects',
    }

    # Default cache timeouts (in seconds)
    DEFAULT_TIMEOUTS = {
        'ephemeris': 86400 * 30,  # 30 days (ephemeris data rarely changes)
        'ai_interpretation': 86400 * 7,  # 7 days
        'chart_data': 86400 * 90,  # 90 days
        'user_session': 3600,  # 1 hour
        'theme_config': 86400,  # 1 day
        'api_response': 3600,  # 1 hour
        'planetary_positions': 86400 * 30,  # 30 days
        'house_positions': 86400 * 30,  # 30 days
        'aspects': 86400 * 30,  # 30 days
    }

    def __init__(self):
        self.cache = cache
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
        }

    def _generate_cache_key(self, prefix: str, identifier: Union[str, int],
                            additional_data: Optional[Dict] = None) -> str:
        """
        Generate a consistent cache key
        """
        key_parts = [self.CACHE_PREFIXES.get(prefix, prefix), str(identifier)]

        if additional_data:
            # Create a hash of additional data for consistent keys
            data_hash = hashlib.md5(
                json.dumps(additional_data, sort_keys=True).encode()
            ).hexdigest()[:8]
            key_parts.append(data_hash)

        return ':'.join(key_parts)

    def _serialize_data(self, data: Any) -> bytes:
        """
        Serialize data for caching (handles complex objects)
        """
        try:
            return pickle.dumps(data)
        except Exception as e:
            logger.warning(f"Failed to serialize data for caching: {e}")
            return json.dumps(data, default=str).encode()

    def _deserialize_data(self, data: bytes) -> Any:
        """
        Deserialize cached data
        """
        try:
            return pickle.loads(data)
        except Exception:
            try:
                return json.loads(data.decode())
            except Exception as e:
                logger.warning(f"Failed to deserialize cached data: {e}")
                return None

    def get(self, prefix: str, identifier: Union[str, int],
            additional_data: Optional[Dict] = None) -> Optional[Any]:
        """
        Get data from cache
        """
        cache_key = self._generate_cache_key(prefix, identifier, additional_data)

        try:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                self._cache_stats['hits'] += 1
                logger.debug(f"Cache HIT for key: {cache_key}")
                return self._deserialize_data(cached_data)
            else:
                self._cache_stats['misses'] += 1
                logger.debug(f"Cache MISS for key: {cache_key}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
            return None

    def set(self, prefix: str, identifier: Union[str, int], data: Any,
            timeout: Optional[int] = None, additional_data: Optional[Dict] = None) -> bool:
        """
        Set data in cache
        """
        cache_key = self._generate_cache_key(prefix, identifier, additional_data)

        if timeout is None:
            timeout = self.DEFAULT_TIMEOUTS.get(prefix, 3600)

        try:
            serialized_data = self._serialize_data(data)
            success = self.cache.set(cache_key, serialized_data, timeout)
            if success:
                self._cache_stats['sets'] += 1
                logger.debug(f"Cache SET for key: {cache_key} (timeout: {timeout}s)")
            return success
        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            return False

    def delete(self, prefix: str, identifier: Union[str, int],
               additional_data: Optional[Dict] = None) -> bool:
        """
        Delete data from cache
        """
        cache_key = self._generate_cache_key(prefix, identifier, additional_data)

        try:
            success = self.cache.delete(cache_key)
            if success:
                self._cache_stats['deletes'] += 1
                logger.debug(f"Cache DELETE for key: {cache_key}")
            return success
        except Exception as e:
            logger.error(f"Error deleting from cache: {e}")
            return False

    def get_or_set(self, prefix: str, identifier: Union[str, int],
                   data_func, timeout: Optional[int] = None,
                   additional_data: Optional[Dict] = None) -> Any:
        """
        Get data from cache or set it if not exists
        """
        cached_data = self.get(prefix, identifier, additional_data)
        if cached_data is not None:
            return cached_data

        # Data not in cache, generate it
        try:
            new_data = data_func()
            self.set(prefix, identifier, new_data, timeout, additional_data)
            return new_data
        except Exception as e:
            logger.error(f"Error in get_or_set: {e}")
            return None

    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics
        """
        total_requests = self._cache_stats['hits'] + self._cache_stats['misses']
        hit_rate = (self._cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0

        return {
            **self._cache_stats,
            'total_requests': total_requests,
            'hit_rate_percent': round(hit_rate, 2)
        }

    def reset_stats(self):
        """
        Reset cache statistics
        """
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
        }


# Specialized cache services for different data types
class EphemerisCacheService(CacheService):
    """
    Specialized caching for Swiss Ephemeris calculations
    """

    def cache_ephemeris_calculation(self, birth_data: Dict, result: Dict) -> bool:
        """
        Cache ephemeris calculation results
        """
        # Create a unique identifier from birth data
        identifier = self._create_birth_data_hash(birth_data)
        return self.set('ephemeris', identifier, result, additional_data=birth_data)

    def get_ephemeris_calculation(self, birth_data: Dict) -> Optional[Dict]:
        """
        Get cached ephemeris calculation
        """
        identifier = self._create_birth_data_hash(birth_data)
        return self.get('ephemeris', identifier, additional_data=birth_data)

    def _create_birth_data_hash(self, birth_data: Dict) -> str:
        """
        Create a hash from birth data for consistent caching
        """
        # Normalize birth data for consistent hashing
        normalized_data = {
            'date': str(birth_data.get('date', '')),
            'time': str(birth_data.get('time', '')),
            'latitude': round(float(birth_data.get('latitude', 0)), 6),
            'longitude': round(float(birth_data.get('longitude', 0)), 6),
            'timezone': str(birth_data.get('timezone', 'UTC')),
        }

        data_string = json.dumps(normalized_data, sort_keys=True)
        return hashlib.md5(data_string.encode()).hexdigest()


class AIInterpretationCacheService(CacheService):
    """
    Specialized caching for AI interpretations
    """

    def cache_interpretation(self, chart_data: Dict, interpretation: str,
                             ai_model: str, temperature: float = 0.7) -> bool:
        """
        Cache AI interpretation results
        """
        identifier = self._create_chart_hash(chart_data)
        additional_data = {
            'ai_model': ai_model,
            'temperature': temperature,
            'timestamp': timezone.now().isoformat()
        }
        return self.set('ai_interpretation', identifier, interpretation,
                        additional_data=additional_data)

    def get_interpretation(self, chart_data: Dict, ai_model: str,
                           temperature: float = 0.7) -> Optional[str]:
        """
        Get cached AI interpretation
        """
        identifier = self._create_chart_hash(chart_data)
        additional_data = {
            'ai_model': ai_model,
            'temperature': temperature
        }
        return self.get('ai_interpretation', identifier, additional_data=additional_data)

    def _create_chart_hash(self, chart_data: Dict) -> str:
        """
        Create a hash from chart data for consistent caching
        """
        # Extract key chart elements for hashing
        key_elements = {
            'planetary_positions': chart_data.get('planetary_positions', {}),
            'house_positions': chart_data.get('house_positions', {}),
            'aspects': chart_data.get('aspects', {}),
        }

        data_string = json.dumps(key_elements, sort_keys=True)
        return hashlib.md5(data_string.encode()).hexdigest()


class UserSessionCacheService(CacheService):
    """
    Specialized caching for user session data
    """

    def cache_user_preferences(self, user_id: int, preferences: Dict) -> bool:
        """
        Cache user preferences
        """
        return self.set('user_session', user_id, preferences, timeout=3600)

    def get_user_preferences(self, user_id: int) -> Optional[Dict]:
        """
        Get cached user preferences
        """
        return self.get('user_session', user_id)

    def cache_user_charts_summary(self, user_id: int, charts_summary: Dict) -> bool:
        """
        Cache user's charts summary for dashboard
        """
        return self.set('user_session', f"{user_id}_charts", charts_summary, timeout=1800)

    def get_user_charts_summary(self, user_id: int) -> Optional[Dict]:
        """
        Get cached user charts summary
        """
        return self.get('user_session', f"{user_id}_charts")


# Global cache service instances
cache_service = CacheService()
ephemeris_cache = EphemerisCacheService()
ai_cache = AIInterpretationCacheService()
user_cache = UserSessionCacheService()
