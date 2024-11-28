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
    
    # Mappa dei timeframe standard a quelli di Binance
    TIMEFRAME_MAP = {
        '1m': '1m',
        '5m': '5m',
        '15m': '15m',
        '1h': '1h',
        '4h': '4h',
        '1d': '1d'
    }
    
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
        
        # Configura l'exchange
        exchange_config = {
            'enableRateLimit': True,
            'timeout': config.get('timeout', 30000),
            'verbose': config.get('verbose', False)
        }
        
        if exchange_id == 'binance':
            exchange_config['options'] = {
                'defaultType': 'spot',
                'fetchMarkets': {
                    'type': 'spot'
                },
                'fetchOHLCV': {
                    'type': 'spot'
                }
            }
        
        # Aggiungi API key solo se sono configurate e non sono i valori di default
        api_key = config.get('api_key')
        api_secret = config.get('api_secret')
        if (api_key and api_secret and 
            api_key != 'your_api_key_here' and 
            api_secret != 'your_api_secret_here'):
            exchange_config['apiKey'] = api_key
            exchange_config['secret'] = api_secret
        
        self.exchange = exchange_class(exchange_config)
        
        # Configura rate limits
        if hasattr(self.exchange, 'rateLimit'):
            self.rate_limiter = self.exchange.rateLimit
            
        # Cache mercati e timeframe
        self._markets: Optional[Dict[str, Any]] = None
        self._timeframes_cache: Optional[List[str]] = None
        
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
                
            # Mappa il timeframe al formato corretto per l'exchange
            exchange_timeframe = self.TIMEFRAME_MAP.get(timeframe)
            if not exchange_timeframe:
                raise ExchangeError(
                    f"Timeframe {timeframe} non supportato"
                )
            
            # Recupera OHLCV con retry in caso di errore
            max_retries = 3
            retry_delay = 1  # secondi
            
            for attempt in range(max_retries):
                try:
                    # Usa la firma corretta del metodo fetch_ohlcv
                    ohlcv = await self.exchange.fetch_ohlcv(
                        symbol,
                        exchange_timeframe,
                        since,
                        limit
                    )
                    return ohlcv
                except (CCXTNetworkError, RateLimitExceeded) as e:
                    if attempt == max_retries - 1:  # Ultimo tentativo
                        raise
                    await asyncio.sleep(retry_delay * (attempt + 1))
            
            return []  # Non dovrebbe mai arrivare qui
            
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
        return list(self.TIMEFRAME_MAP.keys())
        
    def parse_timeframe(self, timeframe: str) -> int:
        """
        Converte un timeframe in millisecondi.
        
        Args:
            timeframe: Timeframe da convertire
            
        Returns:
            Millisecondi corrispondenti al timeframe
        """
        units = {
            'm': 60 * 1000,  # minuti in ms
            'h': 60 * 60 * 1000,  # ore in ms
            'd': 24 * 60 * 60 * 1000  # giorni in ms
        }
        
        unit = timeframe[-1]
        if unit not in units:
            raise ExchangeError(f"Unità timeframe non valida: {unit}")
            
        try:
            value = int(timeframe[:-1])
            return value * units[unit]
        except ValueError:
            raise ExchangeError(f"Formato timeframe non valido: {timeframe}")
        
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
