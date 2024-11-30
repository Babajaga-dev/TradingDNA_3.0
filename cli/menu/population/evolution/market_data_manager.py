"""
Market Data Manager
----------------
Gestione dei dati di mercato per il calcolo del fitness.
"""

from typing import Dict, List, Optional, Union
import time
import random
from datetime import datetime, timedelta
import numpy as np
from sqlalchemy import desc
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from data.database.models.population_models import Population
from data.database.models.models import MarketData
from cli.menu.population.population_base import PopulationBaseManager
from cli.logger.log_manager import get_logger

# Setup logger
logger = get_logger('market_data_manager')

# Configurazione retry
MAX_RETRIES = 3
RETRY_DELAY = 1.0
MAX_BACKOFF = 5.0
QUERY_TIMEOUT = 10  # Ridotto a 10 secondi

def retry_on_db_lock(func):
    """Decorator per gestire i database lock con retry e backoff esponenziale."""
    def wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                #print(f"[DEBUG] Tentativo {attempt+1}/{MAX_RETRIES} di esecuzione {func.__name__}")
                return func(*args, **kwargs)
            except OperationalError as e:
                if "database is locked" in str(e):
                    last_error = e
                    delay = min(RETRY_DELAY * (2 ** attempt) + random.random(), MAX_BACKOFF)
                    #print(f"[DEBUG] Database LOCKED in {func.__name__}! Retry {attempt+1}/{MAX_RETRIES} dopo {delay:.1f}s")
                    logger.warning(f"Database locked, retry {attempt+1}/{MAX_RETRIES} dopo {delay:.1f}s")
                    time.sleep(delay)
                    continue
                raise
        #print(f"[DEBUG] MAX RETRY RAGGIUNTI per {func.__name__}! Ultimo errore: {str(last_error)}")
        logger.error(f"Max retries ({MAX_RETRIES}) raggiunti per database lock")
        raise last_error
    return wrapper

class MarketDataManager(PopulationBaseManager):
    """Gestisce il caricamento e la cache dei dati di mercato."""
    
    def __init__(self, test_config: Dict):
        """Inizializza il manager."""
        super().__init__()
        self.test_config = test_config
        self._market_data_cache = {}
        self._cache_timestamp = datetime.now()
        self._cache_timeout = timedelta(minutes=5)
        print("[DEBUG] MarketDataManager inizializzato")
        
    @retry_on_db_lock
    def get_market_data(self, population: Population, session: Optional[Session] = None) -> List[MarketData]:
        """Ottiene i dati di mercato per il backtest."""
        try:
            print("[DEBUG] Inizio caricamento dati di mercato")
            # Verifica cache valida
            cache_key = f"{population.symbol_id}_{population.timeframe}"
            cache_valid = (
                cache_key in self._market_data_cache and
                datetime.now() - self._cache_timestamp < self._cache_timeout
            )
            
            if cache_valid:
                print("[DEBUG] Uso dati dalla cache")
                return self._market_data_cache[cache_key]
                
            # Ottieni ultimi N giorni di dati
            days = self.test_config['backtest']['days']
            #print(f"[DEBUG] Caricamento {days} giorni di dati")
            
            if session is None:
                print("[DEBUG] Creazione nuova sessione per market data")
                with self.session_scope() as session:
                    return self._get_market_data_internal(population, days, session)
            else:
                print("[DEBUG] Uso sessione esistente per market data")
                return self._get_market_data_internal(population, days, session)
            
        except Exception as e:
            #print(f"[DEBUG] ERRORE caricamento dati mercato: {str(e)}")
            logger.error(f"Errore caricamento dati mercato: {str(e)}")
            return []

    def _get_market_data_internal(self, population: Population, days: int, session: Session) -> List[MarketData]:
        """Implementazione interna per ottenere i dati di mercato."""
        #print(f"[DEBUG] Query dati mercato: symbol={population.symbol_id}, timeframe={population.timeframe}")
        start_time = time.time()
        
        # Calcola il numero corretto di candele in base al timeframe
        candles_per_day = self._get_candles_per_day(population.timeframe)
        total_candles = days * candles_per_day
        #print(f"[DEBUG] Richieste {total_candles} candele ({candles_per_day} candele/giorno)")
        
        data = session.query(MarketData)\
            .filter(
                MarketData.symbol_id == population.symbol_id,
                MarketData.timeframe == population.timeframe
            )\
            .order_by(desc(MarketData.timestamp))\
            .limit(total_candles)\
            .all()
            
        query_time = time.time() - start_time
        #print(f"[DEBUG] Query completata in {query_time:.2f}s")
            
        # Verifica timeout manuale
        if query_time > QUERY_TIMEOUT:
            #print(f"[DEBUG] TIMEOUT query dati mercato ({query_time:.2f}s > {QUERY_TIMEOUT}s)")
            logger.error("Timeout query dati mercato")
            return []
        
        # Aggiorna cache solo se ci sono dati
        if data:
            #print(f"[DEBUG] Aggiornamento cache con {len(data)} record")
            cache_key = f"{population.symbol_id}_{population.timeframe}"
            self._market_data_cache[cache_key] = data
            self._cache_timestamp = datetime.now()
        else:
            print("[DEBUG] Nessun dato trovato dalla query")
        
        return data
            
    def create_test_market_data(self, days: int) -> List[Dict]:
        """Crea dati di mercato di test."""
        #print(f"[DEBUG] Creazione {days} giorni di dati di test")
        data = []
        base_price = 100.0
        timestamp = datetime.now()
        
        for i in range(days * 24):
            price = base_price * (1 + np.random.normal(0, 0.01))
            data.append({
                'timestamp': timestamp - timedelta(hours=i),
                'open': price * (1 - 0.001),
                'high': price * (1 + 0.001),
                'low': price * (1 - 0.002),
                'close': price,
                'volume': np.random.randint(1000, 10000)
            })
            
        #print(f"[DEBUG] Creati {len(data)} record di test")
        return data

    def _get_candles_per_day(self, timeframe: str) -> int:
        """Calcola il numero di candele per giorno in base al timeframe."""
        timeframe_minutes = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '1h': 60,
            '4h': 240,
            '1d': 1440
        }
        minutes_per_day = 24 * 60
        return minutes_per_day // timeframe_minutes[timeframe]
