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
    initialize_database, reset_database, MarketData,
    Exchange, Symbol
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
            print(f"[DEBUG] ERRORE caricamento config: {str(e)}")
            logger.error(f"Errore caricamento configurazione test: {str(e)}")
            raise
        
    def initialize(self) -> str:
        """Inizializza il database per i test."""
        try:
            print("[DEBUG] Inizio inizializzazione database test")
            with self.db.session() as session:
                # Prima resetta il database
                print("[DEBUG] Reset database...")
                reset_database()
                
                # Poi ricrea le tabelle
                print("[DEBUG] Creazione tabelle...")
                initialize_database()
                
                # Applica gli aggiornamenti delle tabelle
                print("[DEBUG] Applicazione aggiornamenti tabelle...")
                with open('data/database/migrations/update_population_tables.sql', 'r') as f:
                    update_sql = f.read()
                session.execute(text(update_sql))
                
                # Verifica che il database sia vuoto e pronto
                result = session.execute(text("""
                    SELECT tablename 
                    FROM pg_catalog.pg_tables 
                    WHERE schemaname = 'public'
                """))
                tables = result.fetchall()
                
                if not tables:
                    return "Errore: Nessuna tabella creata"
                
                # Crea exchange e symbol di test
                print("[DEBUG] Creazione exchange e symbol di test...")
                exchange_result = session.execute(text("""
                    INSERT INTO exchanges (name, is_active, created_at, updated_at)
                    VALUES ('binance', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING id;
                """))
                exchange_id = exchange_result.scalar_one()
                
                symbol_result = session.execute(text("""
                    INSERT INTO symbols (name, base_asset, quote_asset, exchange_id, is_active, created_at, updated_at)
                    VALUES ('BTCUSDT', 'BTC', 'USDT', :exchange_id, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING id;
                """), {"exchange_id": exchange_id})
                symbol_id = symbol_result.scalar_one()
                
                # Genera dati di mercato di test
                print("[DEBUG] Generazione dati di mercato di test...")
                self._generate_test_data(exchange_id, symbol_id, session)
                
                # Commit finale
                print("[DEBUG] Commit finale...")
                session.commit()
                
                print("[DEBUG] Database test inizializzato con successo")
                logger.info(f"Database inizializzato con {len(tables)} tabelle e dati di test")
                return "Database test inizializzato con successo"
                
        except Exception as e:
            error_msg = f"Errore inizializzazione database: {str(e)}"
            print(f"[DEBUG] {error_msg}")
            logger.error(error_msg)
            return error_msg
    
    def _generate_test_data(self, exchange_id: int, symbol_id: int, session) -> None:
        """Genera dati di mercato sintetici per il test."""
        try:
            print("[DEBUG] Inizio generazione dati di mercato sintetici")
            
            # Parametri generazione
            days = self.test_config['test_days']
            timeframe = self.test_config['test_timeframe']
            
            print(f"[DEBUG] Generazione {days} giorni di dati con timeframe {timeframe}")
            
            # Calcola numero candele
            candles_per_day = 24  # Per timeframe 1h
            total_candles = days * candles_per_day
            print(f"[DEBUG] Generazione {total_candles} candele ({candles_per_day} candele/giorno)")
            
            # Genera le candele in batch di 100
            start_time = datetime.now() - timedelta(days=days)
            price = 50000.0  # Prezzo iniziale BTC
            
            for i in range(0, total_candles, 100):
                batch_size = min(100, total_candles - i)
                values = []
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
                    values.append(
                        f"({exchange_id}, {symbol_id}, '{timeframe}', "
                        f"'{timestamp}', {price}, {high}, {low}, {price}, {volume}, true)"
                    )
                
                # Inserisci il batch
                sql = text(f"""
                    INSERT INTO market_data (
                        exchange_id, symbol_id, timeframe, timestamp,
                        open, high, low, close, volume, is_valid
                    )
                    VALUES {','.join(values)};
                """)
                
                session.execute(sql)
                print(f"[DEBUG] Inserite {batch_size} candele")
            
            print(f"[DEBUG] Generati {total_candles} candele di test")
            logger.info(f"Generati {total_candles} candele di test")
            
        except Exception as e:
            print(f"[DEBUG] ERRORE generazione dati test: {str(e)}")
            logger.error(f"Errore generazione dati test: {str(e)}")
            raise
