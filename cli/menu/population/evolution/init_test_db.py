"""
Test Database Initializer
----------------------
Inizializzazione del database per i test del sistema di evoluzione.
"""

from typing import Dict, List
import yaml
from datetime import datetime, timedelta
import numpy as np
from contextlib import contextmanager

from data.database.models.models import (
    get_session, reset_database,
    Exchange, Symbol, MarketData
)
from cli.logger.log_manager import get_logger

# Setup logger
logger = get_logger('test_db_initializer')

class TestDatabaseInitializer:
    """Inizializza il database per i test."""
    
    def __init__(self):
        """Inizializza il database initializer."""
        self.session = get_session()
        self.test_config = self._load_test_config()
        
    @contextmanager
    def transaction(self):
        """Context manager per gestire le transazioni."""
        try:
            yield
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise e
            
    def _load_test_config(self) -> Dict:
        """
        Carica la configurazione dei test.
        
        Returns:
            Dict: Configurazione test
        """
        try:
            with open('config/test.yaml', 'r') as f:
                config = yaml.safe_load(f)
            return config['evolution_test']
        except Exception as e:
            logger.error(f"Errore caricamento configurazione test: {str(e)}")
            raise
            
    def initialize(self) -> str:
        """
        Inizializza il database per i test.
        
        Returns:
            str: Messaggio di conferma o errore
        """
        try:
            with self.transaction():
                logger.info("Inizializzazione database test")
                
                # Resetta database
                reset_database()
                
                # Crea exchange
                exchange = Exchange(
                    name='binance',
                    is_active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                self.session.add(exchange)
                self.session.flush()
                
                # Crea symbol
                symbol = Symbol(
                    exchange_id=exchange.id,
                    name='BTCUSDT',
                    base_asset='BTC',
                    quote_asset='USDT',
                    is_active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                self.session.add(symbol)
                self.session.flush()
                
                # Genera e inserisci dati di test in batch
                self._generate_test_data(exchange.id, symbol.id)
                
                logger.info("Database test inizializzato con successo")
                return "Database test inizializzato con successo"
                
        except Exception as e:
            logger.error(f"Errore inizializzazione database test: {str(e)}")
            return f"Errore inizializzazione database test: {str(e)}"
            
    def _generate_test_data(self, exchange_id: int, symbol_id: int) -> None:
        """
        Genera dati di mercato sintetici per il test.
        
        Args:
            exchange_id: ID exchange
            symbol_id: ID symbol
        """
        logger.info("Generazione dati di mercato sintetici")
        
        # Parametri generazione
        days = self.test_config['test_days']
        timeframe = self.test_config['test_timeframe']
        
        # Calcola numero candele
        candles_per_day = self._get_candles_per_day(timeframe)
        total_candles = days * candles_per_day
        
        # Genera prezzi random walk
        price = 50000.0  # Prezzo iniziale BTC
        volatility = 0.02  # Volatilità giornaliera
        prices = []
        
        for _ in range(total_candles):
            # Random walk con drift
            change = np.random.normal(0, volatility) * price
            price += change
            prices.append(price)
            
        # Genera candele
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        interval = self._get_timeframe_interval(timeframe)
        
        # Prepara batch di candele
        batch_size = 1000
        candles_batch = []
        
        for i in range(total_candles):
            timestamp = start_time + i * interval
            price = prices[i]
            
            # Genera OHLCV
            high = price * (1 + abs(np.random.normal(0, 0.005)))
            low = price * (1 - abs(np.random.normal(0, 0.005)))
            volume = abs(np.random.normal(100, 30))
            
            candle = MarketData(
                exchange_id=exchange_id,
                symbol_id=symbol_id,
                timeframe=timeframe,
                timestamp=timestamp,
                open=prices[i-1] if i > 0 else price,
                high=high,
                low=low,
                close=price,
                volume=volume,
                is_valid=True
            )
            
            candles_batch.append(candle)
            
            # Inserisci batch quando raggiunge la dimensione massima
            if len(candles_batch) >= batch_size:
                self._insert_candles_batch(candles_batch)
                candles_batch = []
                
        # Inserisci eventuali candele rimanenti
        if candles_batch:
            self._insert_candles_batch(candles_batch)
            
        logger.info(f"Generati {total_candles} candele di test")
        
    def _insert_candles_batch(self, candles: List[MarketData]) -> None:
        """
        Inserisce un batch di candele nel database.
        
        Args:
            candles: Lista di candele da inserire
        """
        try:
            self.session.bulk_save_objects(candles)
            self.session.flush()
        except Exception as e:
            logger.error(f"Errore inserimento batch candele: {str(e)}")
            raise
        
    def _get_candles_per_day(self, timeframe: str) -> int:
        """
        Calcola il numero di candele per giorno.
        
        Args:
            timeframe: Timeframe delle candele
            
        Returns:
            int: Numero candele per giorno
        """
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
        
    def _get_timeframe_interval(self, timeframe: str) -> timedelta:
        """
        Converte il timeframe in timedelta.
        
        Args:
            timeframe: Timeframe da convertire
            
        Returns:
            timedelta: Intervallo corrispondente
        """
        timeframe_map = {
            '1m': timedelta(minutes=1),
            '5m': timedelta(minutes=5),
            '15m': timedelta(minutes=15),
            '1h': timedelta(hours=1),
            '4h': timedelta(hours=4),
            '1d': timedelta(days=1)
        }
        return timeframe_map[timeframe]
