"""
Cache Manager
-----------
Sistema di caching per query e risultati.
Implementa strategie di caching e invalidazione.
"""

import time
import logging
import pickle
from typing import Dict, Any, Optional, List, Tuple, Set
from datetime import datetime, timedelta
from threading import Lock
from sqlalchemy.orm import Query
from sqlalchemy.engine import Engine

class CacheEntry:
    """Entry nella cache."""
    
    def __init__(
        self,
        key: str,
        value: Any,
        expire_at: Optional[datetime] = None,
        tags: Optional[Set[str]] = None
    ):
        self.key = key
        self.value = value
        self.expire_at = expire_at
        self.tags = tags or set()
        self.created_at = datetime.utcnow()
        self.last_accessed = datetime.utcnow()
        self.access_count = 0
        
    def is_expired(self) -> bool:
        """Verifica se l'entry è scaduta."""
        if self.expire_at is None:
            return False
        return datetime.utcnow() > self.expire_at
        
    def touch(self):
        """Aggiorna timestamp ultimo accesso."""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1
        
    def size_in_bytes(self) -> int:
        """Calcola dimensione approssimativa in memoria."""
        return len(pickle.dumps(self.value))

class CacheStats:
    """Statistiche della cache."""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.size_bytes = 0
        self.entries = 0
        
    def hit(self):
        """Incrementa contatore hit."""
        self.hits += 1
        
    def miss(self):
        """Incrementa contatore miss."""
        self.misses += 1
        
    def evict(self):
        """Incrementa contatore evizioni."""
        self.evictions += 1
        
    @property
    def hit_ratio(self) -> float:
        """Calcola hit ratio."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

class CacheManager:
    """Gestore della cache per query e risultati."""
    
    def __init__(
        self,
        max_size_mb: int = 100,
        max_entries: int = 1000,
        default_ttl: Optional[int] = 3600
    ):
        """
        Inizializza il cache manager.
        
        Args:
            max_size_mb: Dimensione massima cache in MB
            max_entries: Numero massimo di entry
            default_ttl: TTL predefinito in secondi
        """
        self.max_size = max_size_mb * 1024 * 1024
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = CacheStats()
        self._lock = Lock()
        self.logger = logging.getLogger(__name__)
        
    def get(
        self,
        key: str,
        default: Any = None
    ) -> Optional[Any]:
        """
        Recupera un valore dalla cache.
        
        Args:
            key: Chiave da recuperare
            default: Valore predefinito
            
        Returns:
            Valore dalla cache o default
        """
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats.miss()
                return default
                
            if entry.is_expired():
                self._remove_entry(key)
                self._stats.miss()
                return default
                
            entry.touch()
            self._stats.hit()
            return entry.value
            
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None
    ) -> bool:
        """
        Inserisce un valore in cache.
        
        Args:
            key: Chiave del valore
            value: Valore da inserire
            ttl: Time-to-live in secondi
            tags: Tag per raggruppamento
            
        Returns:
            True se inserito con successo
        """
        with self._lock:
            # Calcola expire time
            expire_at = None
            if ttl is not None or self.default_ttl is not None:
                expire_at = datetime.utcnow() + timedelta(
                    seconds=(ttl or self.default_ttl)
                )
                
            # Crea entry
            entry = CacheEntry(key, value, expire_at, tags)
            
            # Verifica dimensione
            if not self._ensure_capacity(entry.size_in_bytes()):
                return False
                
            # Inserisci entry
            self._cache[key] = entry
            self._stats.size_bytes += entry.size_in_bytes()
            self._stats.entries += 1
            
            return True
            
    def delete(self, key: str) -> bool:
        """
        Elimina una chiave dalla cache.
        
        Args:
            key: Chiave da eliminare
            
        Returns:
            True se eliminata
        """
        with self._lock:
            return self._remove_entry(key)
            
    def clear(self):
        """Svuota la cache."""
        with self._lock:
            self._cache.clear()
            self._stats = CacheStats()
            
    def invalidate_by_tags(self, tags: Set[str]):
        """
        Invalida entry per tag.
        
        Args:
            tags: Tag da invalidare
        """
        with self._lock:
            keys_to_remove = [
                key for key, entry in self._cache.items()
                if entry.tags & tags
            ]
            
            for key in keys_to_remove:
                self._remove_entry(key)
                
    def get_stats(self) -> Dict[str, Any]:
        """
        Ottiene statistiche della cache.
        
        Returns:
            Dizionario con statistiche
        """
        with self._lock:
            return {
                'hits': self._stats.hits,
                'misses': self._stats.misses,
                'evictions': self._stats.evictions,
                'hit_ratio': self._stats.hit_ratio,
                'size_bytes': self._stats.size_bytes,
                'entries': self._stats.entries,
                'memory_usage': self._stats.size_bytes / self.max_size
            }
            
    def _ensure_capacity(self, required_bytes: int) -> bool:
        """
        Assicura spazio disponibile in cache.
        
        Args:
            required_bytes: Bytes richiesti
            
        Returns:
            True se spazio disponibile
        """
        # Verifica limiti
        if required_bytes > self.max_size:
            return False
            
        if len(self._cache) >= self.max_entries:
            self._evict_entries()
            
        while (
            self._stats.size_bytes + required_bytes > self.max_size
        ):
            if not self._evict_entries():
                return False
                
        return True
        
    def _evict_entries(self, count: int = 1) -> bool:
        """
        Elimina entry dalla cache.
        
        Args:
            count: Numero di entry da eliminare
            
        Returns:
            True se eliminazione riuscita
        """
        if not self._cache:
            return False
            
        # Elimina entry scadute
        expired = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        for key in expired:
            self._remove_entry(key)
            count -= 1
            
        if count <= 0:
            return True
            
        # Elimina per LRU
        entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].last_accessed
        )
        
        for key, _ in entries[:count]:
            self._remove_entry(key)
            
        return True
        
    def _remove_entry(self, key: str) -> bool:
        """
        Rimuove una entry dalla cache.
        
        Args:
            key: Chiave da rimuovere
            
        Returns:
            True se rimossa
        """
        entry = self._cache.pop(key, None)
        if entry:
            self._stats.size_bytes -= entry.size_in_bytes()
            self._stats.entries -= 1
            self._stats.evict()
            return True
        return False

class QueryCache:
    """Cache specializzata per query SQL."""
    
    def __init__(
        self,
        engine: Engine,
        cache_manager: Optional[CacheManager] = None
    ):
        """
        Inizializza query cache.
        
        Args:
            engine: SQLAlchemy engine
            cache_manager: Cache manager da usare
        """
        self.engine = engine
        self.cache = cache_manager or CacheManager()
        self.logger = logging.getLogger(__name__)
        
    def execute_cached(
        self,
        query: Query,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None
    ) -> List[Any]:
        """
        Esegue query con caching.
        
        Args:
            query: Query da eseguire
            ttl: Time-to-live cache
            tags: Tag per la cache
            
        Returns:
            Risultati query
        """
        # Genera chiave cache
        key = self._generate_cache_key(query)
        
        # Prova cache
        cached = self.cache.get(key)
        if cached is not None:
            return cached
            
        # Esegui query
        results = query.all()
        
        # Salva in cache
        self.cache.set(key, results, ttl, tags)
        
        return results
        
    def invalidate_query(self, query: Query):
        """
        Invalida cache per una query.
        
        Args:
            query: Query da invalidare
        """
        key = self._generate_cache_key(query)
        self.cache.delete(key)
        
    def _generate_cache_key(self, query: Query) -> str:
        """
        Genera chiave cache per query.
        
        Args:
            query: Query
            
        Returns:
            Chiave cache
        """
        sql = str(query.statement.compile(
            compile_kwargs={"literal_binds": True}
        ))
        return f"query:{hash(sql)}"

class ResultTransformer:
    """Trasformatore di risultati per caching."""
    
    @staticmethod
    def to_cacheable(results: List[Any]) -> List[Dict[str, Any]]:
        """
        Converte risultati in formato cacheable.
        
        Args:
            results: Risultati da convertire
            
        Returns:
            Risultati convertiti
        """
        return [
            {
                col: getattr(row, col)
                for col in row.__table__.columns.keys()
            }
            for row in results
        ]
        
    @staticmethod
    def from_cache(
        cached: List[Dict[str, Any]],
        model_class: Any
    ) -> List[Any]:
        """
        Converte risultati da cache in oggetti modello.
        
        Args:
            cached: Risultati cached
            model_class: Classe modello
            
        Returns:
            Oggetti modello
        """
        return [
            model_class(**row_data)
            for row_data in cached
        ]