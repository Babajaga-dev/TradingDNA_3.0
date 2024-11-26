"""
TradingDNA Data System - Query Optimizations
-----------------------------------------
Sistema di ottimizzazione delle query e caching.
"""

from typing import Optional, Any, Set

from .query_optimizer import (
    QueryOptimizer,
    QueryStats,
    IndexManager
)

from .cache_manager import (
    CacheManager,
    CacheEntry,
    CacheStats,
    QueryCache,
    ResultTransformer
)

__all__ = [
    # Query Optimizer
    'QueryOptimizer',
    'QueryStats',
    'IndexManager',
    
    # Cache Manager
    'CacheManager',
    'CacheEntry',
    'CacheStats',
    'QueryCache',
    'ResultTransformer',
    
    # Factory functions
    'create_optimizer',
    'create_cache',
    'create_query_cache'
]

def create_optimizer(engine: Any) -> QueryOptimizer:
    """
    Crea una nuova istanza di QueryOptimizer.
    
    Args:
        engine: SQLAlchemy engine
        
    Returns:
        Istanza configurata di QueryOptimizer
    """
    return QueryOptimizer(engine)

def create_cache(
    max_size_mb: int = 100,
    max_entries: int = 1000,
    default_ttl: Optional[int] = 3600
) -> CacheManager:
    """
    Crea una nuova istanza di CacheManager.
    
    Args:
        max_size_mb: Dimensione massima cache in MB
        max_entries: Numero massimo di entry
        default_ttl: TTL predefinito in secondi
        
    Returns:
        Istanza configurata di CacheManager
    """
    return CacheManager(
        max_size_mb=max_size_mb,
        max_entries=max_entries,
        default_ttl=default_ttl
    )

def create_query_cache(
    engine: Any,
    max_size_mb: int = 100,
    max_entries: int = 1000,
    default_ttl: Optional[int] = 3600
) -> QueryCache:
    """
    Crea una nuova istanza di QueryCache.
    
    Args:
        engine: SQLAlchemy engine
        max_size_mb: Dimensione massima cache in MB
        max_entries: Numero massimo di entry
        default_ttl: TTL predefinito in secondi
        
    Returns:
        Istanza configurata di QueryCache
    """
    cache_manager = create_cache(
        max_size_mb=max_size_mb,
        max_entries=max_entries,
        default_ttl=default_ttl
    )
    return QueryCache(engine, cache_manager)