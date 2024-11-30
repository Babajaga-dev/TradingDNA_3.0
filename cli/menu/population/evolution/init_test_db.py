"""
Test Database Initializer
----------------------
Inizializzazione del database per i test.
"""

from typing import Dict, List
import yaml
import time
import random
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
import psycopg2
from psycopg2 import errors
from data.database.session_manager import DBSessionManager
from data.database.models.models import (
    initialize_database, reset_database, verify_database_state,
    MarketData, Exchange, Symbol
)
from data.database.models.population_models import (
    Population, Chromosome, ChromosomeGene
)
from cli.logger.log_manager import get_logger

# Setup logger
logger = get_logger('test_db_init')

class TestDatabaseInitializer:
    """Inizializza il database per i test."""
    
    def __init__(self):
        """Inizializza il database initializer."""
        self.db = DBSessionManager()
        self.test_config = self._load_test_config()
        
    def _load_test_config(self) -> Dict:
        """Carica la configurazione dei test."""
        try:
            print("[DEBUG] Caricamento configurazione test")
            with open('config/test.yaml', 'r') as f:
                config = yaml.safe_load(f)
            print("[DEBUG] Configurazione test caricata")
            return config['evolution_test']
        except Exception as e:
            logger.error(f"Errore caricamento configurazione test: {str(e)}")
            raise
        
    def initialize(self) -> str:
        """Inizializza il database per i test."""
        try:
            print("[DEBUG] Inizio inizializzazione database test")
            
            # Prima resetta il database
            print("[DEBUG] Reset database...")
            reset_database()
            
            # Verifica lo stato dopo il reset
            print("[DEBUG] Verifica stato database...")
            if not verify_database_state():
                raise Exception("Verifica stato database fallita dopo il reset")
            
            with self.db.session() as session:
                # Crea exchange e symbol di test
                print("[DEBUG] Creazione exchange e symbol di test...")
                exchange = Exchange(
                    name='binance',
                    is_active=True,
                    api_config={'test': True},
                    rate_limits={'test': True},
                    supported_features=['spot']
                )
                session.add(exchange)
                session.flush()  # Per ottenere l'ID
                
                symbol = Symbol(
                    name='BTCUSDT',
                    base_asset='BTC',
                    quote_asset='USDT',
                    exchange_id=exchange.id,
                    is_active=True,
                    trading_config={'test': True},
                    filters={'test': True},
                    limits={'test': True}
                )
                session.add(symbol)
                session.flush()  # Per ottenere l'ID
                
                # Genera dati di mercato di test
                print("[DEBUG] Generazione dati di mercato di test...")
                self._generate_test_data(exchange.id, symbol.id, session)
                
                # Commit finale
                print("[DEBUG] Commit finale...")
                session.commit()
                
                # Verifica finale
                print("[DEBUG] Verifica finale...")
                if not verify_database_state():
                    raise Exception("Verifica finale del database fallita")
                
                print("[DEBUG] Database test inizializzato con successo")
                logger.info("Database test inizializzato con successo")
                return "Database test inizializzato con successo"
                
        except Exception as e:
            error_msg = f"Errore inizializzazione database: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def _generate_test_data(self, exchange_id: int, symbol_id: int, session) -> None:
        """Genera dati di mercato sintetici per il test."""
        try:
            print("[DEBUG] Inizio generazione dati di mercato sintetici")
            
            # Parametri generazione
            days = self.test_config['test_days']
            timeframe = self.test_config['test_timeframe']
            
            # Calcola numero candele
            candles_per_day = 24  # Per timeframe 1h
            total_candles = days * candles_per_day
            
            # Genera le candele in batch di 100
            start_time = datetime.now() - timedelta(days=days)
            price = 50000.0  # Prezzo iniziale BTC
            
            for i in range(0, total_candles, 100):
                batch_size = min(100, total_candles - i)
                market_data_batch = []
                current_time = start_time + timedelta(hours=i)
                
                for j in range(batch_size):
                    # Random walk con drift
                    change = np.random.normal(0, 0.02) * price
                    price = price + change
                    
                    # Genera OHLCV
                    high = price * (1 + abs(np.random.normal(0, 0.005)))
                    low = price * (1 - abs(np.random.normal(0, 0.005)))
                    volume = abs(np.random.normal(100, 30))
                    
                    timestamp = current_time + timedelta(hours=j)
                    
                    # Crea oggetto MarketData con i nuovi campi JSON
                    market_data = MarketData(
                        exchange_id=exchange_id,
                        symbol_id=symbol_id,
                        timeframe=timeframe,
                        timestamp=timestamp,
                        open=price,
                        high=high,
                        low=low,
                        close=price,
                        volume=volume,
                        is_valid=True,
                        technical_indicators={},
                        pattern_recognition={},
                        market_metrics={}
                    )
                    market_data_batch.append(market_data)
                
                # Inserisci il batch
                session.bulk_save_objects(market_data_batch)
                session.flush()
            
            logger.info(f"Generati {total_candles} candele di test")
            
        except Exception as e:
            logger.error(f"Errore generazione dati test: {str(e)}")
            raise
