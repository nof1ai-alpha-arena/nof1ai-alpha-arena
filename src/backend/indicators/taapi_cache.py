"""
TAAPI Cache - Simple in-memory cache for TAAPI indicator results
Reduces redundant API calls and respects rate limits
"""

import time
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class TAAPICache:
    """
    Simple in-memory cache for TAAPI indicator results.
    
    Cache keys: f"{asset}:{interval}"
    TTL: configurable (default 60 seconds)
    """
    
    def __init__(self, ttl: int = 60):
        """
        Initialize cache.
        
        Args:
            ttl: Time-to-live in seconds (default: 60)
        """
        self.ttl = ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        logger.info(f"TAAPI Cache initialized with TTL={ttl}s")
    
    def get(self, asset: str, interval: str) -> Optional[Dict[str, Any]]:
        """
        Get cached indicators for asset and interval.
        
        Args:
            asset: Asset symbol (e.g., "BTC", "ETH")
            interval: Time interval (e.g., "5m", "1h")
            
        Returns:
            Cached data dict or None if expired/missing
        """
        key = f"{asset}:{interval}"
        
        if key not in self._cache:
            logger.debug(f"Cache MISS: {key}")
            return None
        
        entry = self._cache[key]
        age = time.time() - entry['timestamp']
        
        if age > self.ttl:
            logger.debug(f"Cache EXPIRED: {key} (age: {age:.1f}s)")
            del self._cache[key]
            return None
        
        logger.debug(f"Cache HIT: {key} (age: {age:.1f}s)")
        return entry['data']
    
    def set(self, asset: str, interval: str, data: Dict[str, Any]) -> None:
        """
        Store indicators in cache.
        
        Args:
            asset: Asset symbol
            interval: Time interval
            data: Indicator data to cache
        """
        key = f"{asset}:{interval}"
        
        self._cache[key] = {
            'timestamp': time.time(),
            'data': data
        }
        
        logger.debug(f"Cache SET: {key}")
    
    def clear(self) -> None:
        """Clear all cached data"""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared ({count} entries removed)")
    
    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache stats
        """
        now = time.time()
        active = 0
        expired = 0
        
        for entry in self._cache.values():
            age = now - entry['timestamp']
            if age <= self.ttl:
                active += 1
            else:
                expired += 1
        
        return {
            'total_entries': len(self._cache),
            'active_entries': active,
            'expired_entries': expired,
            'ttl_seconds': self.ttl
        }


# Global cache instance
_cache_instance: Optional[TAAPICache] = None


def get_cache(ttl: int = 60) -> TAAPICache:
    """
    Get or create global TAAPI cache instance.
    
    Args:
        ttl: Time-to-live in seconds
        
    Returns:
        TAAPICache instance
    """
    global _cache_instance
    
    if _cache_instance is None:
        _cache_instance = TAAPICache(ttl=ttl)
    
    return _cache_instance
