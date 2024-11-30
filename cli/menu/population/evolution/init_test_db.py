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

# Configurazione retry
MAX_RETRIES = 3
RETRY_DELAY = 1.0
MAX_BACKOFF = 5.0

def retry_on_db_lock(func):
    """Decorator per gestire i lock del database con retry e backoff esponenziale."""
    def wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                print(f"[DEBUG] Tentativo {attempt+1}/{MAX_RETRIES} di esecuzione {func.__name__}")
                return func(*args, **kwargs)
            except (psycopg2.OperationalError, OperationalError) as e:
                if any(err in str(e).lower() for err in ["deadlock", "lock", "timeout"]):
                    last_error = e
                    delay = min(RETRY_DELAY * (2 ** attempt) + random.random(), MAX_BACKOFF)
                    print(f"[DEBUG] Database LOCKED in {func.__name__}! Retry {attempt+1}/{MAX_RETRIES} dopo {delay:.1f}s")
                    logger.warning(f"Database locked, retry {attempt+1}/{MAX_RETRIES} dopo {delay:.1f}s")
                    time.sleep(delay)
                    continue
                raise
        print(f"[DEBUG] MAX RETRY RAGGIUNTI per {func.__name__}! Ultimo errore: {str(last_error)}")
        logger.error(f"Max retries ({MAX_RETRIES}) raggiunti per database lock")
        raise last_error
    return wrapper

class TestDatabaseInitializer:
    """Inizializza il database per i test."""
    
    def __init__(self):
        """Inizializza il database initializer."""
        self.db = DBSessionManager()
        self.test_config = self._load_test_config()
        
    def _load_test_config(self) -> Dict:
        """
        Carica la configurazione dei test.
        
        Returns:
            Dict: Configurazione test
        """
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
        
    @retry_on_db_lock
    def initialize(self) -> str:
        """
        Inizializza il database per i test.
        
        Returns:
            str: Messaggio di stato
        """
        try:
            print("[DEBUG] Inizio inizializzazione database test")
            with self.db.session() as session:
                # Prima resetta il database
                print("[DEBUG] Reset database...")
                reset_database()
                
                # Poi ricrea le tabelle
                print("[DEBUG] Creazione tabelle...")
                initialize_database()
                
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
                exchange = Exchange(
                    name='binance',
                    is_active=True
                )
                session.add(exchange)
                session.flush()
                
                symbol = Symbol(
                    name='BTCUSDT',
                    base_asset='BTC',
                    quote_asset='USDT',
                    exchange_id=exchange.id,
                    is_active=True
                )
                session.add(symbol)
                session.flush()
                
                # Genera dati di mercato di test
                print("[DEBUG] Generazione dati di mercato di test...")
                self._generate_test_data(exchange.id, symbol.id, session)
                
                # Crea popolazione di test
                print("[DEBUG] Creazione popolazione di test...")
                population = Population(
                    name='Test Population',
                    max_size=100,
                    symbol_id=symbol.id,
                    timeframe=self.test_config['test_timeframe'],
                    mutation_rate=0.01,
                    selection_pressure=5,
                    generation_interval=4,
                    diversity_threshold=0.7,
                    status='active'
                )
                session.add(population)
                session.flush()
                
                # Crea cromosomi di test
                print("[DEBUG] Creazione cromosomi di test...")
                self._create_test_chromosomes(population, session)
                
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
            
    def _create_test_chromosomes(self, population: Population, session) -> None:
        """
        Crea cromosomi di test per la popolazione.
        
        Args:
            population: Popolazione di test
            session: Sessione database attiva
        """
        try:
            print("[DEBUG] Creazione cromosomi di test...")
            
            # Carica configurazione geni
            with open('config/gene.yaml', 'r') as f:
                gene_config = yaml.safe_load(f)['gene']
            
            # Lista dei tipi di geni disponibili
            gene_types = ['rsi', 'macd', 'moving_average', 'bollinger', 'stochastic', 'atr']
            
            # Crea cromosomi
            for i in range(population.max_size):
                chromosome = Chromosome(
                    population_id=population.population_id,
                    fingerprint=f"test_chromosome_{i}",
                    generation=0,
                    status='active',
                    performance_metrics={'fitness': 0.0},
                    weight_distribution={}
                )
                session.add(chromosome)
                session.flush()
                
                # Aggiungi 2-5 geni casuali a ogni cromosoma
                num_genes = random.randint(2, 5)
                selected_genes = random.sample(gene_types, num_genes)
                
                for gene_type in selected_genes:
                    # Ottieni parametri di default dal config
                    default_params = gene_config[gene_type]['default']
                    constraints = gene_config[gene_type]['constraints']
                    
                    gene = ChromosomeGene(
                        chromosome_id=chromosome.chromosome_id,
                        gene_type=gene_type,
                        parameters=default_params,
                        weight=random.uniform(0.1, 5.0),
                        is_active=True,
                        validation_rules=constraints
                    )
                    session.add(gene)
                
                if i % 10 == 0:
                    print(f"[DEBUG] Creati {i+1}/{population.max_size} cromosomi")
                    session.flush()
            
            print("[DEBUG] Cromosomi di test creati con successo")
            
        except Exception as e:
            print(f"[DEBUG] ERRORE creazione cromosomi test: {str(e)}")
            logger.error(f"Errore creazione cromosomi test: {str(e)}")
            raise
    
    def _generate_test_data(self, exchange_id: int, symbol_id: int, session) -> None:
        """
        Genera dati di mercato sintetici per il test.
        
        Args:
            exchange_id: ID exchange
            symbol_id: ID symbol
            session: Sessione database attiva
        """
        try:
            print("[DEBUG] Inizio generazione dati di mercato sintetici")
            
            # Parametri generazione
            days = self.test_config['test_days']
            timeframe = self.test_config['test_timeframe']
            
            print(f"[DEBUG] Generazione {days} giorni di dati con timeframe {timeframe}")
            
            # Calcola numero candele
            candles_per_day = self._get_candles_per_day(timeframe)
            total_candles = days * candles_per_day
            print(f"[DEBUG] Generazione {total_candles} candele ({candles_per_day} candele/giorno)")
            
            # Genera prezzi random walk
            price = 50000.0  # Prezzo iniziale BTC
            volatility = 0.02  # Volatilità giornaliera
            
            # Genera candele
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            interval = self._get_timeframe_interval(timeframe)
            
            # Prepara batch di candele
            batch_size = 100  # Ridotto per evitare problemi di memoria
            candles_batch = []
            last_price = price
            
            for i in range(total_candles):
                timestamp = start_time + i * interval
                
                # Random walk con drift
                change = np.random.normal(0, volatility) * last_price
                price = last_price + change
                
                # Genera OHLCV
                high = price * (1 + abs(np.random.normal(0, 0.005)))
                low = price * (1 - abs(np.random.normal(0, 0.005)))
                volume = abs(np.random.normal(100, 30))
                
                candle = MarketData(
                    exchange_id=exchange_id,
                    symbol_id=symbol_id,
                    timeframe=timeframe,
                    timestamp=timestamp,
                    open=last_price,
                    high=high,
                    low=low,
                    close=price,
                    volume=volume,
                    is_valid=True
                )
                
                candles_batch.append(candle)
                last_price = price
                
                # Inserisci batch quando raggiunge la dimensione massima
                if len(candles_batch) >= batch_size:
                    print(f"[DEBUG] Inserimento batch di {len(candles_batch)} candele...")
                    self._insert_candles_batch(candles_batch, session)
                    candles_batch = []
                    session.flush()
                    
            # Inserisci eventuali candele rimanenti
            if candles_batch:
                print(f"[DEBUG] Inserimento batch finale di {len(candles_batch)} candele...")
                self._insert_candles_batch(candles_batch, session)
                session.flush()
                
            print(f"[DEBUG] Generati {total_candles} candele di test")
            logger.info(f"Generati {total_candles} candele di test")
            
        except Exception as e:
            print(f"[DEBUG] ERRORE generazione dati test: {str(e)}")
            logger.error(f"Errore generazione dati test: {str(e)}")
            raise
    
    @retry_on_db_lock
    def _insert_candles_batch(self, candles: List[MarketData], session) -> None:
        """
        Inserisce un batch di candele nel database.
        
        Args:
            candles: Lista di candele da inserire
            session: Sessione database attiva
        """
        try:
            # Usa il bulk insert ottimizzato di PostgreSQL
            session.bulk_save_objects(
                candles,
                update_changed_only=True,
                preserve_order=False
            )
            session.flush()
        except Exception as e:
            print(f"[DEBUG] ERRORE inserimento batch candele: {str(e)}")
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
