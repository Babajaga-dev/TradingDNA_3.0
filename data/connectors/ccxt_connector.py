"""
CCXT Exchange Connector
--------------------
Implementazione del connettore usando CCXT.
Supporta multiple exchanges tramite interfaccia unificata.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

import ccxt.async_support as ccxt
from ccxt.base.errors import (
    NetworkError as CCXTNetworkError,
    RateLimitExceeded,
    AuthenticationError as CCXTAuthError
)

from .base_connector import (
    BaseConnector,
    ExchangeError,
    RateLimitError,
    AuthenticationError,
    NetworkError
)

class CCXTConnector(BaseConnector):
    """Connettore per exchange usando CCXT."""
    
    def __init__(
        self,
        exchange_id: str,
        config: Dict[str, Any]
    ):
        """
        Inizializza il connettore CCXT.
        
        Args:
            exchange_id: ID dell'exchange
            config: Configurazione connettore
        """
        super().__init__(exchange_id, config)
        
        # Crea istanza CCXT
        exchange_class = getattr(ccxt, exchange_id)
        
        self.exchange = exchange_class({
            'apiKey': config.get('api_key'),
            'secret': config.get('api_secret'),
            'password': config.get('password'),
            'enableRateLimit': True,
            'timeout': config.get('timeout', 30000),
            'verbose': config.get('verbose', False)
        })
        
        # Configura rate limits
        if hasattr(self.exchange, 'rateLimit'):
            self.rate_limiter = self.exchange.rateLimit
            
        # Cache mercati
        self._markets: Optional[Dict[str, Any]] = None
        
    async def fetch_markets(self) -> List[Dict[str, Any]]:
        """
        Recupera informazioni sui mercati disponibili.
        
        Returns:
            Lista dei mercati
            
        Raises:
            ExchangeError: Se il recupero fallisce
        """
        try:
            if not self._markets:
                self._markets = await self.exchange.load_markets()
                
            return list(self._markets.values())
            
        except CCXTNetworkError as e:
            raise NetworkError(str(e))
        except RateLimitExceeded as e:
            raise RateLimitError(str(e))
        except CCXTAuthError as e:
            raise AuthenticationError(str(e))
        except Exception as e:
            raise ExchangeError(str(e))
            
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
            
        Raises:
            ExchangeError: Se il recupero fallisce
        """
        try:
            # Verifica supporto OHLCV
            if not self.exchange.has['fetchOHLCV']:
                raise ExchangeError(
                    f"{self.exchange_id} non supporta OHLCV"
                )
                
            # Verifica timeframe
            if timeframe not in self.exchange.timeframes:
                raise ExchangeError(
                    f"Timeframe {timeframe} non supportato"
                )
                
            # Recupera OHLCV
            ohlcv = await self.exchange.fetch_ohlcv(
                symbol,
                timeframe,
                since,
                limit
            )
            
            return ohlcv
            
        except CCXTNetworkError as e:
            raise NetworkError(str(e))
        except RateLimitExceeded as e:
            raise RateLimitError(str(e))
        except CCXTAuthError as e:
            raise AuthenticationError(str(e))
        except Exception as e:
            raise ExchangeError(str(e))
            
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
            
        Raises:
            ExchangeError: Se il recupero fallisce
        """
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return ticker
            
        except CCXTNetworkError as e:
            raise NetworkError(str(e))
        except RateLimitExceeded as e:
            raise RateLimitError(str(e))
        except CCXTAuthError as e:
            raise AuthenticationError(str(e))
        except Exception as e:
            raise ExchangeError(str(e))
            
    async def _do_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Esegue richiesta HTTP tramite CCXT.
        
        Args:
            method: Metodo HTTP
            endpoint: Endpoint API
            params: Parametri richiesta
            
        Returns:
            Risposta della richiesta
            
        Raises:
            ExchangeError: Se la richiesta fallisce
        """
        try:
            # Costruisci metodo CCXT
            ccxt_method = f"{method.lower()}_{endpoint}"
            if not hasattr(self.exchange, ccxt_method):
                raise ExchangeError(
                    f"Metodo {ccxt_method} non supportato"
                )
                
            # Esegui richiesta
            method_func = getattr(self.exchange, ccxt_method)
            response = await method_func(params or {})
            
            return response
            
        except CCXTNetworkError as e:
            raise NetworkError(str(e))
        except RateLimitExceeded as e:
            raise RateLimitError(str(e))
        except CCXTAuthError as e:
            raise AuthenticationError(str(e))
        except Exception as e:
            raise ExchangeError(str(e))
            
    async def get_timeframes(self) -> List[str]:
        """
        Recupera timeframes supportati.
        
        Returns:
            Lista dei timeframes
        """
        if not self._timeframes_cache:
            if not hasattr(self.exchange, 'timeframes'):
                self._timeframes_cache = ['1m', '5m', '15m', '1h', '4h', '1d']
            else:
                self._timeframes_cache = list(self.exchange.timeframes.keys())
                
        return self._timeframes_cache
        
    async def close(self) -> None:
        """Chiude il connettore e libera le risorse."""
        if self.exchange:
            await self.exchange.close()

class CCXTConnectorFactory:
    """Factory per creare connettori CCXT."""
    
    @staticmethod
    async def create_connector(
        exchange_id: str,
        config: Dict[str, Any]
    ) -> CCXTConnector:
        """
        Crea un nuovo connettore CCXT.
        
        Args:
            exchange_id: ID dell'exchange
            config: Configurazione connettore
            
        Returns:
            Istanza di CCXTConnector
            
        Raises:
            ExchangeError: Se la creazione fallisce
        """
        try:
            # Verifica exchange supportato
            if exchange_id not in ccxt.exchanges:
                raise ExchangeError(
                    f"Exchange {exchange_id} non supportato"
                )
                
            # Crea connettore
            connector = CCXTConnector(exchange_id, config)
            
            # Verifica connessione
            await connector.fetch_markets()
            
            return connector
            
        except Exception as e:
            raise ExchangeError(
                f"Errore creazione connettore: {str(e)}"
            )
            
    @staticmethod
    def get_supported_exchanges() -> List[str]:
        """
        Recupera lista exchange supportati.
        
        Returns:
            Lista degli exchange
        """
        return ccxt.exchanges