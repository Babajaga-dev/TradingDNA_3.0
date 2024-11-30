"""
Fitness Calculator
---------------
Calcolo del fitness per i cromosomi basato sulle performance di trading.
"""

from typing import Dict, List, Optional
import yaml
import time
import random
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import OperationalError

from data.database.models.population_models import Population, Chromosome
from cli.menu.population.population_base import PopulationBaseManager
from cli.logger.log_manager import get_logger
from .market_data_manager import MarketDataManager
from .signal_calculator import SignalCalculator
from .trading_simulator import TradingSimulator
from .metrics_calculator import MetricsCalculator

# Setup logger
logger = get_logger('fitness_calculator')

# Configurazione retry
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 0.1
MAX_RETRY_DELAY = 2.0

# Dimensione batch per il processing dei cromosomi
BATCH_SIZE = 5

def retry_on_db_lock(func):
    """Decorator per gestire i database lock con retry e backoff esponenziale."""
    def wrapper(*args, **kwargs):
        last_error = None
        delay = INITIAL_RETRY_DELAY
        
        for attempt in range(MAX_RETRIES):
            try:
                #print(f"[DEBUG] Tentativo {attempt+1}/{MAX_RETRIES} di esecuzione {func.__name__}")
                return func(*args, **kwargs)
            except OperationalError as e:
                if "database is locked" in str(e):
                    last_error = e
                    if attempt < MAX_RETRIES - 1:
                        #print(f"[DEBUG] Database LOCKED in {func.__name__}! Retry {attempt+1}/{MAX_RETRIES} dopo {delay:.1f}s")
                        logger.warning(f"Database locked, retry {attempt+1}/{MAX_RETRIES} dopo {delay:.1f}s")
                        time.sleep(delay)
                        delay = min(delay * 2 + random.random(), MAX_RETRY_DELAY)
                        continue
                raise
        #print(f"[DEBUG] MAX RETRY RAGGIUNTI per {func.__name__}! Ultimo errore: {str(last_error)}")
        logger.error(f"Max retries ({MAX_RETRIES}) raggiunti per database lock")
        raise last_error
    return wrapper

class FitnessCalculator(PopulationBaseManager):
    """Calcola il fitness dei cromosomi."""
    
    def __init__(self):
        """Inizializza il calculator."""
        super().__init__()
        print("[DEBUG] Inizializzazione FitnessCalculator")
        print("[DEBUG] Caricamento configurazione test...")
        self.test_config = self._load_test_config()
        print("[DEBUG] Configurazione test caricata")
        
        # Inizializza i componenti
        print("[DEBUG] Inizializzazione MarketDataManager...")
        self.market_data = MarketDataManager(self.test_config)
        print("[DEBUG] Inizializzazione SignalCalculator...")
        self.signal_calc = SignalCalculator()
        print("[DEBUG] Inizializzazione TradingSimulator...")
        self.trading_sim = TradingSimulator()
        print("[DEBUG] Inizializzazione MetricsCalculator...")
        self.metrics_calc = MetricsCalculator(self.test_config)
        print("[DEBUG] FitnessCalculator inizializzato con successo")
        
    def _load_test_config(self) -> Dict:
        """Carica la configurazione dei test."""
        try:
            print("[DEBUG] Apertura file config/test.yaml...")
            with open('config/test.yaml', 'r') as f:
                config = yaml.safe_load(f)
            print("[DEBUG] File config/test.yaml caricato")
            return config['evolution_test']
        except Exception as e:
            #print(f"[DEBUG] ERRORE caricamento config fitness: {str(e)}")
            logger.error(f"Errore caricamento configurazione test: {str(e)}")
            raise

    def _get_population(self, population_id: int, session: Session) -> Optional[Population]:
        """
        Carica una popolazione con tutte le sue relazioni.
        
        Args:
            population_id: ID della popolazione
            session: Sessione database attiva
            
        Returns:
            Population: Popolazione caricata con relazioni
        """
        return (
            session.query(Population)
            .options(
                selectinload(Population.chromosomes)
                .selectinload(Chromosome.genes)
            )
            .filter(Population.population_id == population_id)
            .first()
        )

    @retry_on_db_lock
    def reset_test_data(self, population: Population, session: Session) -> None:
        """
        Resetta i dati di test della popolazione usando query SQL dirette.
        
        Args:
            population: Popolazione da resettare
            session: Sessione database
        """
        try:
            print(f"\n[DEBUG] === INIZIO RESET DATI TEST POPOLAZIONE {population.name} ===")
            
            # Reset popolazione
            print("[DEBUG] Reset dati popolazione...")
            session.execute(
                text("""
                    UPDATE populations 
                    SET performance_score = 0.0,
                        diversity_score = 0.0
                    WHERE population_id = :pop_id
                """),
                {"pop_id": population.population_id}
            )
            
            # Reset cromosomi
            print("[DEBUG] Reset dati cromosomi...")
            session.execute(
                text("""
                    UPDATE chromosomes 
                    SET performance_metrics = NULL
                    WHERE population_id = :pop_id
                """),
                {"pop_id": population.population_id}
            )
            
            # Reset geni
            print("[DEBUG] Reset dati geni...")
            session.execute(
                text("""
                    UPDATE chromosome_genes 
                    SET performance_contribution = 0.0
                    WHERE chromosome_id IN (
                        SELECT chromosome_id 
                        FROM chromosomes 
                        WHERE population_id = :pop_id
                    )
                """),
                {"pop_id": population.population_id}
            )
            
            # Commit delle modifiche
            print("[DEBUG] Commit modifiche...")
            session.commit()
            
            print("[DEBUG] === FINE RESET DATI TEST POPOLAZIONE ===\n")
            
        except Exception as e:
            #print(f"[DEBUG] ERRORE reset dati test: {str(e)}")
            logger.error(f"Errore reset dati test: {str(e)}")
            session.rollback()
            raise
    
    @retry_on_db_lock
    def calculate_population_fitness(self, population: Population, session: Optional[Session] = None) -> Dict:
        """Calcola il fitness per tutti i cromosomi di una popolazione."""
        try:
            print(f"\n[DEBUG] === INIZIO CALCOLO FITNESS POPOLAZIONE {population.name} ===")
            
            # Usa la sessione fornita o crea una nuova transazione
            if session is not None:
                print("[DEBUG] Uso sessione esistente per il calcolo fitness")
                return self._calculate_population_fitness_internal(population, session)
            else:
                print("[DEBUG] Creazione nuova sessione per il calcolo fitness")
                with self.session_scope() as new_session:
                    return self._calculate_population_fitness_internal(population, new_session)
                    
        except Exception as e:
            #print(f"[DEBUG] ERRORE CRITICO calcolo fitness popolazione: {str(e)}")
            logger.error(f"Errore calcolo fitness popolazione: {str(e)}")
            raise
            
    def _calculate_population_fitness_internal(self, population: Population, session: Session) -> Dict:
        """Implementazione interna del calcolo fitness popolazione."""
        print("[DEBUG] Inizializzazione calcolo fitness...")
        
        # Reset dati test precedenti
        print("[DEBUG] Reset dati test precedenti...")
        self.reset_test_data(population, session)
        print("[DEBUG] Reset completato")
        
        # Ricarica la popolazione dopo il reset
        print("[DEBUG] Ricaricamento popolazione...")
        population = self._get_population(population.population_id, session)
        if not population:
            raise ValueError(f"Popolazione {population.population_id} non trovata")
        
        # Inizializza statistiche
        stats = {
            "total": len(population.chromosomes),
            "evaluated": 0,
            "best_fitness": 0.0,
            "avg_fitness": 0.0,
            "worst_fitness": float('inf'),
            "distribution": []
        }
        #print(f"[DEBUG] Statistiche inizializzate: {stats['total']} cromosomi totali")
        
        # Carica dati di mercato
        print("[DEBUG] Inizio caricamento dati di mercato...")
        start_time = time.time()
        market_data = self.market_data.get_market_data(population, session)
        if not market_data:
            print("[DEBUG] Creazione dati di test...")
            market_data = self.market_data.create_test_market_data(
                self.test_config['backtest']['days']
            )
        load_time = time.time() - start_time
        #print(f"[DEBUG] Dati di mercato pronti in {load_time:.2f}s")
        
        # Processa i cromosomi in batch
        chromosomes = [c for c in population.chromosomes if c and c.status == 'active']
        total_chromosomes = len(chromosomes)
        processed = 0
        
        #print(f"[DEBUG] Inizio processing {total_chromosomes} cromosomi attivi in batch di {BATCH_SIZE}")
        
        for i in range(0, total_chromosomes, BATCH_SIZE):
            batch = chromosomes[i:i + BATCH_SIZE]
            print(f"\n[DEBUG] Processing batch {(i//BATCH_SIZE)+1}, cromosomi {i+1}-{min(i+BATCH_SIZE, total_chromosomes)}")
            
            for chromosome in batch:
                try:
                    processed += 1
                    print(f"\n[DEBUG] --- Elaborazione cromosoma {processed}/{total_chromosomes} ---")
                    
                    # Calcola fitness senza merge del cromosoma
                    fitness = self._calculate_chromosome_fitness_no_merge(
                        chromosome,
                        market_data,
                        session
                    )
                    
                    if fitness > 0:
                        stats["evaluated"] += 1
                        stats["best_fitness"] = max(stats["best_fitness"], fitness)
                        stats["worst_fitness"] = min(stats["worst_fitness"], fitness)
                        stats["distribution"].append(fitness)
                        #print(f"[DEBUG] Fitness calcolato: {fitness}")
                        
                except Exception as e:
                    #print(f"[DEBUG] ERRORE calcolo fitness cromosoma: {str(e)}")
                    logger.error(f"Errore calcolo fitness cromosoma: {str(e)}")
                    continue
            
            # Flush dopo ogni batch
            print("[DEBUG] Flush sessione dopo batch")
            session.flush()
        
        # Calcola statistiche finali
        if stats["evaluated"] > 0:
            stats["avg_fitness"] = sum(stats["distribution"]) / len(stats["distribution"])
            
        print(f"\n[DEBUG] === FINE CALCOLO FITNESS POPOLAZIONE ===")
        #print(f"[DEBUG] Statistiche finali:")
        #print(f"[DEBUG] - Cromosomi valutati: {stats['evaluated']}/{stats['total']}")
        #print(f"[DEBUG] - Miglior fitness: {stats['best_fitness']:.2f}")
        #print(f"[DEBUG] - Fitness medio: {stats['avg_fitness']:.2f}")
        
        return stats
            
    def _calculate_chromosome_fitness_no_merge(
        self,
        chromosome: Chromosome,
        market_data: List,
        session: Session
    ) -> float:
        """Calcola il fitness di un cromosoma senza operazioni di merge."""
        try:
            #print(f"[DEBUG] Calcolo fitness per cromosoma {chromosome.chromosome_id}")
            
            # Calcola segnali
            print("[DEBUG] Calcolo segnali trading...")
            signals = self.signal_calc.calculate_signals(chromosome, market_data, session)
            
            # Simula trading
            print("[DEBUG] Simulazione trading...")
            performance = self.trading_sim.simulate_trading(signals, market_data)
            
            # Calcola metriche
            print("[DEBUG] Calcolo metriche...")
            metrics = self.metrics_calc.calculate_metrics(performance)
            
            # Calcola e aggiorna fitness
            print("[DEBUG] Calcolo fitness finale...")
            fitness = self.metrics_calc.combine_metrics(metrics)
            
            # Aggiorna metriche senza merge
            print("[DEBUG] Aggiornamento metriche...")
            self.metrics_calc.update_chromosome_metrics(chromosome, metrics, fitness, session)
            
            return fitness
                
        except Exception as e:
            #print(f"[DEBUG] ERRORE calcolo fitness cromosoma {getattr(chromosome, 'chromosome_id', None)}: {str(e)}")
            return 0.0
