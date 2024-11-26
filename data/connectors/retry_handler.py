"""
Retry Handler
-----------
Sistema di retry con backoff esponenziale.
Gestisce tentativi di riconnessione in modo robusto.
"""

import time
import random
import logging
import asyncio
from typing import (
    TypeVar, Callable, Awaitable, Optional,
    List, Dict, Any, Type, Union, Set
)
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from functools import wraps

T = TypeVar('T')

class RetryStrategy(Enum):
    """Strategie di retry."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIBONACCI = "fibonacci"
    RANDOM = "random"

@dataclass
class RetryConfig:
    """Configurazione retry."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: bool = True
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    exceptions: Set[Type[Exception]] = None

class RetryStats:
    """Statistiche dei retry."""
    
    def __init__(self):
        self.total_retries = 0
        self.successful_retries = 0
        self.failed_retries = 0
        self.total_delay = 0.0
        self.last_retry = None
        self.last_error = None
        
    def retry_attempted(self, success: bool, delay: float):
        """Aggiorna statistiche retry."""
        self.total_retries += 1
        if success:
            self.successful_retries += 1
        else:
            self.failed_retries += 1
        self.total_delay += delay
        self.last_retry = datetime.utcnow()
        
    @property
    def success_rate(self) -> float:
        """Calcola tasso di successo."""
        if self.total_retries == 0:
            return 0.0
        return self.successful_retries / self.total_retries
        
    @property
    def average_delay(self) -> float:
        """Calcola delay medio."""
        if self.total_retries == 0:
            return 0.0
        return self.total_delay / self.total_retries

class RetryError(Exception):
    """Errore dopo tutti i tentativi falliti."""
    
    def __init__(
        self,
        message: str,
        last_error: Optional[Exception] = None,
        attempts: int = 0
    ):
        super().__init__(message)
        self.last_error = last_error
        self.attempts = attempts

class RetryHandler:
    """Gestore dei retry."""
    
    def __init__(
        self,
        config: Optional[RetryConfig] = None
    ):
        """
        Inizializza il retry handler.
        
        Args:
            config: Configurazione retry
        """
        self.config = config or RetryConfig()
        self.stats = RetryStats()
        self.logger = logging.getLogger(__name__)
        
    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any
    ) -> T:
        """
        Esegue una funzione con retry.
        
        Args:
            func: Funzione da eseguire
            *args: Argomenti posizionali
            **kwargs: Argomenti nominali
            
        Returns:
            Risultato della funzione
            
        Raises:
            RetryError: Se tutti i tentativi falliscono
        """
        attempt = 1
        last_error = None
        
        while attempt <= self.config.max_attempts:
            try:
                result = await func(*args, **kwargs)
                
                # Aggiorna statistiche successo
                if attempt > 1:
                    self.stats.retry_attempted(True, 0)
                    
                return result
                
            except Exception as e:
                last_error = e
                
                # Verifica se fare retry
                if self.config.exceptions and not any(
                    isinstance(e, exc) for exc in self.config.exceptions
                ):
                    raise
                    
                # Calcola delay
                delay = self._calculate_delay(attempt)
                
                # Log errore
                self.logger.warning(
                    f"Tentativo {attempt} fallito. "
                    f"Retry tra {delay}s. Errore: {str(e)}"
                )
                
                # Aggiorna statistiche
                self.stats.retry_attempted(False, delay)
                self.stats.last_error = last_error
                
                # Attendi prima del retry
                await asyncio.sleep(delay)
                attempt += 1
                
        # Tutti i tentativi falliti
        raise RetryError(
            f"Tutti i {self.config.max_attempts} tentativi falliti",
            last_error,
            attempt - 1
        )
        
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calcola delay per un tentativo.
        
        Args:
            attempt: Numero del tentativo
            
        Returns:
            Delay in secondi
        """
        if self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (2 ** (attempt - 1))
        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = self.config.base_delay * attempt
        elif self.config.strategy == RetryStrategy.FIBONACCI:
            delay = self._fibonacci(attempt) * self.config.base_delay
        else:  # RANDOM
            delay = random.uniform(
                self.config.base_delay,
                self.config.base_delay * attempt
            )
            
        # Applica jitter
        if self.config.jitter:
            delay *= random.uniform(0.5, 1.5)
            
        return min(delay, self.config.max_delay)
        
    def _fibonacci(self, n: int) -> int:
        """Calcola n-esimo numero Fibonacci."""
        if n <= 0:
            return 0
        elif n == 1:
            return 1
        else:
            a, b = 0, 1
            for _ in range(2, n + 1):
                a, b = b, a + b
            return b

def retry(
    max_attempts: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    strategy: Optional[RetryStrategy] = None,
    exceptions: Optional[Set[Type[Exception]]] = None
) -> Callable:
    """
    Decoratore per retry.
    
    Args:
        max_attempts: Massimo numero tentativi
        base_delay: Delay base
        max_delay: Delay massimo
        strategy: Strategia retry
        exceptions: Eccezioni da gestire
        
    Returns:
        Funzione decorata
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Crea config
            config = RetryConfig(
                max_attempts=max_attempts or 3,
                base_delay=base_delay or 1.0,
                max_delay=max_delay or 60.0,
                strategy=strategy or RetryStrategy.EXPONENTIAL,
                exceptions=exceptions
            )
            
            # Esegui con retry
            handler = RetryHandler(config)
            return await handler.execute(func, *args, **kwargs)
            
        return wrapper
    return decorator

class CircuitBreaker:
    """Implementazione Circuit Breaker."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0
    ):
        """
        Inizializza il circuit breaker.
        
        Args:
            failure_threshold: Soglia fallimenti
            reset_timeout: Timeout reset in secondi
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure = None
        self.state = "closed"
        self._lock = asyncio.Lock()
        
    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any
    ) -> T:
        """
        Esegue funzione con circuit breaker.
        
        Args:
            func: Funzione da eseguire
            *args: Argomenti posizionali
            **kwargs: Argomenti nominali
            
        Returns:
            Risultato della funzione
            
        Raises:
            Exception: Se il circuito è aperto
        """
        async with self._lock:
            if self.state == "open":
                if self._should_reset():
                    self.state = "half-open"
                else:
                    raise Exception("Circuit breaker aperto")
                    
            try:
                result = await func(*args, **kwargs)
                
                if self.state == "half-open":
                    self.state = "closed"
                    self.failures = 0
                    
                return result
                
            except Exception as e:
                self.failures += 1
                self.last_failure = datetime.utcnow()
                
                if (
                    self.failures >= self.failure_threshold or
                    self.state == "half-open"
                ):
                    self.state = "open"
                    
                raise
                
    def _should_reset(self) -> bool:
        """Verifica se resettare il circuito."""
        if not self.last_failure:
            return False
            
        elapsed = (
            datetime.utcnow() - self.last_failure
        ).total_seconds()
        
        return elapsed >= self.reset_timeout

class RetryWithCircuitBreaker:
    """Combina Retry e Circuit Breaker."""
    
    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0
    ):
        """
        Inizializza il gestore.
        
        Args:
            retry_config: Configurazione retry
            failure_threshold: Soglia fallimenti
            reset_timeout: Timeout reset
        """
        self.retry_handler = RetryHandler(retry_config)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold,
            reset_timeout
        )
        
    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any
    ) -> T:
        """
        Esegue funzione con retry e circuit breaker.
        
        Args:
            func: Funzione da eseguire
            *args: Argomenti posizionali
            **kwargs: Argomenti nominali
            
        Returns:
            Risultato della funzione
        """
        return await self.circuit_breaker.execute(
            self.retry_handler.execute,
            func, *args, **kwargs
        )