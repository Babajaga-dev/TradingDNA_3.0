"""
Rate Limiter
-----------
Sistema avanzato di rate limiting per le richieste API.
Supporta multiple strategie e monitoraggio.
"""

import time
import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

@dataclass
class RateLimitRule:
    """Regola di rate limiting."""
    max_requests: int
    time_window: float
    weight: int = 1
    scope: str = "global"

class RateLimitStrategy(Enum):
    """Strategie di rate limiting."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"

class RateLimitStats:
    """Statistiche di rate limiting."""
    
    def __init__(self):
        self.total_requests = 0
        self.throttled_requests = 0
        self.total_wait_time = 0.0
        self.max_wait_time = 0.0
        self.last_reset = datetime.utcnow()
        
    def update_wait_time(self, wait_time: float):
        """Aggiorna statistiche tempo di attesa."""
        self.total_wait_time += wait_time
        self.max_wait_time = max(self.max_wait_time, wait_time)
        
    def request_processed(self, throttled: bool = False):
        """Aggiorna statistiche richieste."""
        self.total_requests += 1
        if throttled:
            self.throttled_requests += 1
            
    def reset(self):
        """Resetta statistiche."""
        self.total_requests = 0
        self.throttled_requests = 0
        self.total_wait_time = 0.0
        self.max_wait_time = 0.0
        self.last_reset = datetime.utcnow()
        
    @property
    def throttle_ratio(self) -> float:
        """Calcola ratio di throttling."""
        if self.total_requests == 0:
            return 0.0
        return self.throttled_requests / self.total_requests
        
    @property
    def avg_wait_time(self) -> float:
        """Calcola tempo medio di attesa."""
        if self.throttled_requests == 0:
            return 0.0
        return self.total_wait_time / self.throttled_requests

class BaseRateLimiter(ABC):
    """Classe base per implementazioni rate limiter."""
    
    def __init__(self, rule: RateLimitRule):
        self.rule = rule
        self.stats = RateLimitStats()
        self._lock = asyncio.Lock()
        
    @abstractmethod
    async def acquire(self, weight: int = 1) -> float:
        """
        Acquisisce un permesso.
        
        Args:
            weight: Peso della richiesta
            
        Returns:
            Tempo di attesa
        """
        pass
        
    @abstractmethod
    def reset(self):
        """Resetta lo stato."""
        pass

class FixedWindowRateLimiter(BaseRateLimiter):
    """Rate limiter con finestra fissa."""
    
    def __init__(self, rule: RateLimitRule):
        super().__init__(rule)
        self._window_start = time.time()
        self._request_count = 0
        
    async def acquire(self, weight: int = 1) -> float:
        async with self._lock:
            now = time.time()
            window_elapsed = now - self._window_start
            
            # Nuova finestra
            if window_elapsed >= self.rule.time_window:
                self._window_start = now
                self._request_count = 0
                self.stats.reset()
                return 0.0
                
            # Verifica limite
            if (self._request_count + weight) > self.rule.max_requests:
                wait_time = self.rule.time_window - window_elapsed
                self.stats.update_wait_time(wait_time)
                self.stats.request_processed(throttled=True)
                return wait_time
                
            # Aggiorna contatore
            self._request_count += weight
            self.stats.request_processed()
            return 0.0
            
    def reset(self):
        """Resetta lo stato."""
        self._window_start = time.time()
        self._request_count = 0
        self.stats.reset()

class SlidingWindowRateLimiter(BaseRateLimiter):
    """Rate limiter con finestra scorrevole."""
    
    def __init__(self, rule: RateLimitRule):
        super().__init__(rule)
        self._requests: List[float] = []
        
    async def acquire(self, weight: int = 1) -> float:
        async with self._lock:
            now = time.time()
            
            # Rimuovi richieste vecchie
            window_start = now - self.rule.time_window
            self._requests = [
                ts for ts in self._requests
                if ts > window_start
            ]
            
            # Verifica limite
            if (len(self._requests) + weight) > self.rule.max_requests:
                # Calcola tempo di attesa
                if self._requests:
                    wait_time = self._requests[0] - window_start
                    self.stats.update_wait_time(wait_time)
                    self.stats.request_processed(throttled=True)
                    return wait_time
                    
            # Aggiungi richieste
            for _ in range(weight):
                self._requests.append(now)
                
            self.stats.request_processed()
            return 0.0
            
    def reset(self):
        """Resetta lo stato."""
        self._requests.clear()
        self.stats.reset()

class TokenBucketRateLimiter(BaseRateLimiter):
    """Rate limiter con token bucket."""
    
    def __init__(
        self,
        rule: RateLimitRule,
        burst_size: Optional[int] = None
    ):
        super().__init__(rule)
        self.burst_size = burst_size or rule.max_requests
        self._tokens = self.burst_size
        self._last_update = time.time()
        
    async def acquire(self, weight: int = 1) -> float:
        async with self._lock:
            now = time.time()
            
            # Aggiungi token
            elapsed = now - self._last_update
            new_tokens = elapsed * (
                self.rule.max_requests / self.rule.time_window
            )
            self._tokens = min(
                self._tokens + new_tokens,
                self.burst_size
            )
            self._last_update = now
            
            # Verifica token
            if self._tokens < weight:
                # Calcola tempo di attesa
                wait_time = (
                    (weight - self._tokens) *
                    self.rule.time_window /
                    self.rule.max_requests
                )
                self.stats.update_wait_time(wait_time)
                self.stats.request_processed(throttled=True)
                return wait_time
                
            # Usa token
            self._tokens -= weight
            self.stats.request_processed()
            return 0.0
            
    def reset(self):
        """Resetta lo stato."""
        self._tokens = self.burst_size
        self._last_update = time.time()
        self.stats.reset()

class LeakyBucketRateLimiter(BaseRateLimiter):
    """Rate limiter con leaky bucket."""
    
    def __init__(
        self,
        rule: RateLimitRule,
        bucket_size: Optional[int] = None
    ):
        super().__init__(rule)
        self.bucket_size = bucket_size or rule.max_requests
        self._water_level = 0
        self._last_leak = time.time()
        
    async def acquire(self, weight: int = 1) -> float:
        async with self._lock:
            now = time.time()
            
            # Calcola perdita
            elapsed = now - self._last_leak
            leak_amount = elapsed * (
                self.rule.max_requests / self.rule.time_window
            )
            self._water_level = max(0, self._water_level - leak_amount)
            self._last_leak = now
            
            # Verifica spazio
            if (self._water_level + weight) > self.bucket_size:
                # Calcola tempo di attesa
                wait_time = (
                    (self._water_level + weight - self.bucket_size) *
                    self.rule.time_window /
                    self.rule.max_requests
                )
                self.stats.update_wait_time(wait_time)
                self.stats.request_processed(throttled=True)
                return wait_time
                
            # Aggiungi acqua
            self._water_level += weight
            self.stats.request_processed()
            return 0.0
            
    def reset(self):
        """Resetta lo stato."""
        self._water_level = 0
        self._last_leak = time.time()
        self.stats.reset()

class RateLimiterFactory:
    """Factory per creare rate limiter."""
    
    @staticmethod
    def create_limiter(
        strategy: RateLimitStrategy,
        rule: RateLimitRule,
        **kwargs: Any
    ) -> BaseRateLimiter:
        """
        Crea un rate limiter.
        
        Args:
            strategy: Strategia da usare
            rule: Regola di limiting
            **kwargs: Parametri aggiuntivi
            
        Returns:
            Rate limiter configurato
        """
        limiters = {
            RateLimitStrategy.FIXED_WINDOW: FixedWindowRateLimiter,
            RateLimitStrategy.SLIDING_WINDOW: SlidingWindowRateLimiter,
            RateLimitStrategy.TOKEN_BUCKET: TokenBucketRateLimiter,
            RateLimitStrategy.LEAKY_BUCKET: LeakyBucketRateLimiter
        }
        
        limiter_class = limiters.get(strategy)
        if not limiter_class:
            raise ValueError(f"Strategia non valida: {strategy}")
            
        return limiter_class(rule, **kwargs)

class RateLimitManager:
    """Gestore centrale dei rate limiter."""
    
    def __init__(self):
        self.limiters: Dict[str, BaseRateLimiter] = {}
        self.logger = logging.getLogger(__name__)
        
    def add_limiter(
        self,
        name: str,
        strategy: RateLimitStrategy,
        rule: RateLimitRule,
        **kwargs: Any
    ) -> None:
        """
        Aggiunge un rate limiter.
        
        Args:
            name: Nome del limiter
            strategy: Strategia da usare
            rule: Regola di limiting
            **kwargs: Parametri aggiuntivi
        """
        self.limiters[name] = RateLimiterFactory.create_limiter(
            strategy, rule, **kwargs
        )
        
    async def acquire(
        self,
        name: str,
        weight: int = 1
    ) -> float:
        """
        Acquisisce un permesso.
        
        Args:
            name: Nome del limiter
            weight: Peso della richiesta
            
        Returns:
            Tempo di attesa
        """
        limiter = self.limiters.get(name)
        if not limiter:
            raise ValueError(f"Rate limiter non trovato: {name}")
            
        return await limiter.acquire(weight)
        
    def get_stats(self, name: str) -> RateLimitStats:
        """
        Ottiene statistiche limiter.
        
        Args:
            name: Nome del limiter
            
        Returns:
            Statistiche del limiter
        """
        limiter = self.limiters.get(name)
        if not limiter:
            raise ValueError(f"Rate limiter non trovato: {name}")
            
        return limiter.stats
        
    def reset(self, name: Optional[str] = None) -> None:
        """
        Resetta limiters.
        
        Args:
            name: Nome del limiter da resettare
        """
        if name:
            limiter = self.limiters.get(name)
            if limiter:
                limiter.reset()
        else:
            for limiter in self.limiters.values():
                limiter.reset()