"""
Base Exchange Connector
--------------------
Classe base per i connettori degli exchange.
Implementa funzionalità comuni come rate limiting e retry.
"""

import time
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

class RateLimiter:
    """Gestisce il rate limiting delle richieste."""
    
    def __init__(
        self,
        max_requests: int,
        time_window: float,
        buffer_size: int = 10
    ):
        """
        Inizializza il rate limiter.
        
        Args:
            max_requests: Massimo numero di richieste
            time_window: Finestra temporale in secondi
            buffer_size: Dimensione buffer sicurezza
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.buffer_size = buffer_size
        self.requests: List[float] = []
        self._lock = asyncio.Lock()
        
    async def acquire(self):
        """Acquisisce un permesso per la richiesta."""
        async with self._lock:
            now = time.time()
            
            # Rimuovi richieste vecchie
            self.requests = [
                ts for ts in self.requests
                if now - ts <= self.time_window
            ]
            
            # Verifica limiti
            if len(self.requests) >= self.max_requests - self.buffer_size:
                # Calcola tempo di attesa
                oldest = self.requests[0]
                wait_time = self.time_window - (now - oldest)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    
            # Registra richiesta
            self.requests.append(now)
            
    async def __aenter__(self):
        """Context manager entry."""
        await self.acquire()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass

class RetryStrategy:
    """Strategia di retry per le richieste."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential: bool = True
    ):
        """
        Inizializza la strategia.
        
        Args:
            max_retries: Massimo numero di tentativi
            base_delay: Ritardo base in secondi
            max_delay: Ritardo massimo in secondi
            exponential: Usa backoff esponenziale
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential = exponential
        
    def get_delay(self, attempt: int) -> float:
        """
        Calcola il ritardo per un tentativo.
        
        Args:
            attempt: Numero del tentativo
            
        Returns:
            Ritardo in secondi
        """
        if self.exponential:
            delay = self.base_delay * (2 ** (attempt - 1))
        else:
            delay = self.base_delay * attempt
            
        return min(delay, self.max_delay)

class ExchangeError(Exception):
    """Errore base per operazioni exchange."""
    pass

class RateLimitError(ExchangeError):
    """Errore per superamento rate limit."""
    pass

class AuthenticationError(ExchangeError):
    """Errore di autenticazione."""
    pass

class NetworkError(ExchangeError):
    """Errore di rete."""
    pass

class BaseConnector(ABC):
    """Classe base per connettori exchange."""
    
    def __init__(
        self,
        exchange_id: str,
        config: Dict[str, Any]
    ):
        """
        Inizializza il connettore.
        
        Args:
            exchange_id: ID dell'exchange
            config: Configurazione connettore
        """
        self.exchange_id = exchange_id
        self.config = config
        self.logger = logging.getLogger(f"connector.{exchange_id}")
        
        # Rate limiting
        self.rate_limiter = RateLimiter(
            max_requests=config.get('max_requests', 1200),
            time_window=config.get('time_window', 60)
        )
        
        # Retry strategy
        self.retry_strategy = RetryStrategy(
            max_retries=config.get('max_retries', 3),
            base_delay=config.get('base_delay', 1.0),
            max_delay=config.get('max_delay', 60.0),
            exponential=config.get('exponential_backoff', True)
        )
        
        # Cache
        self._symbols_cache: Dict[str, Dict[str, Any]] = {}
        self._timeframes_cache: Dict[str, List[str]] = {}
        
    @abstractmethod
    async def fetch_markets(self) -> List[Dict[str, Any]]:
        """
        Recupera informazioni sui mercati disponibili.
        
        Returns:
            Lista dei mercati
        """
        pass
        
    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[List[float]]:
        """
        Recupera dati OHLCV.
        
        Args:
            symbol: Simbolo trading
            timeframe: Timeframe
            since: Timestamp iniziale
            limit: Limite candle
            
        Returns:
            Lista di candle OHLCV
        """
        pass
        
    @abstractmethod
    async def fetch_ticker(
        self,
        symbol: str
    ) -> Dict[str, Any]:
        """
        Recupera ticker corrente.
        
        Args:
            symbol: Simbolo trading
            
        Returns:
            Dati ticker
        """
        pass
        
    async def execute_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        retry_on_errors: Optional[List[Exception]] = None
    ) -> Any:
        """
        Esegue una richiesta HTTP con retry.
        
        Args:
            method: Metodo HTTP
            endpoint: Endpoint API
            params: Parametri richiesta
            retry_on_errors: Errori su cui fare retry
            
        Returns:
            Risposta della richiesta
            
        Raises:
            ExchangeError: Se la richiesta fallisce
        """
        attempt = 1
        last_error = None
        
        while attempt <= self.retry_strategy.max_retries:
            try:
                async with self.rate_limiter:
                    response = await self._do_request(
                        method, endpoint, params
                    )
                    return response
                    
            except Exception as e:
                last_error = e
                
                # Verifica se fare retry
                should_retry = False
                if retry_on_errors:
                    should_retry = any(
                        isinstance(e, err_type)
                        for err_type in retry_on_errors
                    )
                else:
                    should_retry = isinstance(
                        e, (NetworkError, RateLimitError)
                    )
                    
                if not should_retry:
                    break
                    
                # Calcola delay
                delay = self.retry_strategy.get_delay(attempt)
                self.logger.warning(
                    f"Tentativo {attempt} fallito per {endpoint}. "
                    f"Retry tra {delay}s. Errore: {str(e)}"
                )
                
                await asyncio.sleep(delay)
                attempt += 1
                
        # Rilancia ultimo errore
        raise last_error or ExchangeError(
            f"Tutti i tentativi falliti per {endpoint}"
        )
        
    @abstractmethod
    async def _do_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Esegue la richiesta HTTP effettiva.
        
        Args:
            method: Metodo HTTP
            endpoint: Endpoint API
            params: Parametri richiesta
            
        Returns:
            Risposta della richiesta
        """
        pass
        
    async def get_symbols(self) -> List[str]:
        """
        Recupera lista simboli supportati.
        
        Returns:
            Lista dei simboli
        """
        if not self._symbols_cache:
            markets = await self.fetch_markets()
            self._symbols_cache = {
                m['symbol']: m for m in markets
            }
            
        return list(self._symbols_cache.keys())
        
    async def get_timeframes(self) -> List[str]:
        """
        Recupera timeframes supportati.
        
        Returns:
            Lista dei timeframes
        """
        if not self._timeframes_cache:
            # Implementazione specifica per exchange
            pass
            
        return list(self._timeframes_cache.keys())
        
    def parse_timeframe(self, timeframe: str) -> int:
        """
        Converte timeframe in millisecondi.
        
        Args:
            timeframe: Timeframe (es. 1m, 1h, 1d)
            
        Returns:
            Millisecondi
        """
        units = {
            'm': 60 * 1000,
            'h': 60 * 60 * 1000,
            'd': 24 * 60 * 60 * 1000,
            'w': 7 * 24 * 60 * 60 * 1000
        }
        
        amount = int(timeframe[:-1])
        unit = timeframe[-1]
        
        if unit not in units:
            raise ValueError(f"Timeframe non valido: {timeframe}")
            
        return amount * units[unit]
        
    def handle_error(self, error: Exception) -> None:
        """
        Gestisce un errore.
        
        Args:
            error: Errore da gestire
        """
        self.logger.error(
            f"Errore in {self.exchange_id}: {str(error)}",
            exc_info=True
        )
        
    async def close(self) -> None:
        """Chiude il connettore e libera le risorse."""
        pass