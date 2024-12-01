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
from cli.config.config_loader import get_config_loader
from .market_data_manager import MarketDataManager
from .signal_calculator import SignalCalculator
from .trading_simulator import TradingSimulator
from .metrics_calculator import MetricsCalculator
from .db_utils import retry_on_db_lock

class FitnessCalculator(PopulationBaseManager):
    """Calcola il fitness dei cromosomi."""
    
    def __init__(self):
        """Inizializza il calculator."""
        super().__init__()
        
        # Setup logger
        self.logger = get_logger('fitness_calculator')
        
        # Carica configurazione
        self.config = get_config_loader()
        self.test_config = self._load_test_config()
        
        # Parametri batch
        signals_config = self.config.get_value('gene.signals', {})
        self.BATCH_SIZE = signals_config.get('batch_size', 5)
        
        # Parametri retry
        retry_config = signals_config.get('retry', {})
        self.MAX_RETRIES = retry_config.get('max_attempts', 5)
        self.INITIAL_RETRY_DELAY = retry_config.get('initial_delay', 0.1)
        self.MAX_RETRY_DELAY = retry_config.get('max_delay', 2.0)
        
        # Inizializza i componenti
        self.market_data = MarketDataManager(self.test_config)
        self.signal_calc = SignalCalculator()
        self.trading_sim = TradingSimulator()
        self.metrics_calc = MetricsCalculator()
        
    def _load_test_config(self) -> Dict:
        """Carica la configurazione dei test."""
        try:
            with open('config/cromo.yaml', 'r') as f:
                config = yaml.safe_load(f)
            return config['evolution_test']
        except Exception as e:
            self.logger.error(f"Errore caricamento configurazione test: {str(e)}")
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
            self.logger.debug(f"Reset dati test popolazione {population.name}")
            
            # Reset popolazione
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
            session.execute(
                text("""
                    UPDATE chromosomes 
                    SET performance_metrics = NULL
                    WHERE population_id = :pop_id
                """),
                {"pop_id": population.population_id}
            )
            
            # Reset geni
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
            session.commit()
            
        except Exception as e:
            self.logger.error(f"Errore reset dati test: {str(e)}")
            session.rollback()
            raise
    
    @retry_on_db_lock
    def calculate_population_fitness(self, population: Population, session: Optional[Session] = None) -> Dict:
        """Calcola il fitness per tutti i cromosomi di una popolazione."""
        try:
            self.logger.debug(f"Inizio calcolo fitness popolazione {population.name}")
            
            # Usa la sessione fornita o crea una nuova transazione
            if session is not None:
                return self._calculate_population_fitness_internal(population, session)
            else:
                with self.session_scope() as new_session:
                    return self._calculate_population_fitness_internal(population, new_session)
                    
        except Exception as e:
            self.logger.error(f"Errore calcolo fitness popolazione: {str(e)}")
            raise
            
    def _calculate_population_fitness_internal(self, population: Population, session: Session) -> Dict:
        """Implementazione interna del calcolo fitness popolazione."""
        
        # Reset dati test precedenti
        self.reset_test_data(population, session)
        
        # Ricarica la popolazione dopo il reset
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
        
        # Carica dati di mercato
        start_time = time.time()
        market_data = self.market_data.get_market_data(population, session)
        if not market_data:
            market_data = self.market_data.create_test_market_data(
                self.test_config['test_days']  # Corretto il riferimento alla configurazione
            )
        load_time = time.time() - start_time
        self.logger.debug(f"Dati di mercato caricati in {load_time:.2f}s")
        
        # Processa i cromosomi in batch
        chromosomes = [c for c in population.chromosomes if c and c.status == 'active']
        total_chromosomes = len(chromosomes)
        processed = 0
        
        for i in range(0, total_chromosomes, self.BATCH_SIZE):
            batch = chromosomes[i:i + self.BATCH_SIZE]
            self.logger.debug(f"Processing batch {(i//self.BATCH_SIZE)+1}, cromosomi {i+1}-{min(i+self.BATCH_SIZE, total_chromosomes)}")
            
            for chromosome in batch:
                try:
                    processed += 1
                    self.logger.debug(f"Elaborazione cromosoma {processed}/{total_chromosomes}")
                    
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
                        
                except Exception as e:
                    self.logger.error(f"Errore calcolo fitness cromosoma: {str(e)}")
                    continue
            
            # Flush dopo ogni batch
            session.flush()
        
        # Calcola statistiche finali
        if stats["evaluated"] > 0:
            stats["avg_fitness"] = sum(stats["distribution"]) / len(stats["distribution"])
            
        self.logger.debug(f"Fine calcolo fitness popolazione: {stats['evaluated']}/{stats['total']} cromosomi valutati")
        return stats
            
    def _calculate_chromosome_fitness_no_merge(
        self,
        chromosome: Chromosome,
        market_data: List,
        session: Session
    ) -> float:
        """Calcola il fitness di un cromosoma senza operazioni di merge."""
        try:
            # Calcola segnali
            signals = self.signal_calc.calculate_signals(chromosome, market_data, session)
            
            # Simula trading
            performance = self.trading_sim.simulate_trading(signals, market_data)
            
            # Calcola metriche
            metrics = self.metrics_calc.calculate_metrics(performance)
            
            # Calcola e aggiorna fitness
            fitness = self.metrics_calc.combine_metrics(metrics)
            
            # Aggiorna metriche senza merge
            self.metrics_calc.update_chromosome_metrics(chromosome, metrics, fitness, session)
            
            return fitness
                
        except Exception as e:
            self.logger.error(f"Errore calcolo fitness cromosoma: {str(e)}")
            return 0.0
