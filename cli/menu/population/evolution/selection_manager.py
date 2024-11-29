"""
Selection Manager
--------------
Gestione della selezione naturale dei cromosomi.
"""

from typing import List, Dict, Tuple
import random
import numpy as np
from datetime import datetime
import json
import time

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from data.database.models.population_models import (
    Population, Chromosome, ChromosomeGene, EvolutionHistory
)
from cli.menu.population.population_base import PopulationBaseManager
from cli.logger.log_manager import get_logger

# Setup logger
logger = get_logger('selection_manager')

# Configurazione retry
MAX_RETRIES = 5
RETRY_DELAY = 2.0
MAX_BACKOFF = 10.0

def retry_on_db_lock(func):
    """Decorator per gestire i database lock con retry e backoff esponenziale."""
    def wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except OperationalError as e:
                if "database is locked" in str(e):
                    last_error = e
                    delay = min(RETRY_DELAY * (2 ** attempt) + random.random(), MAX_BACKOFF)
                    logger.warning(f"Database locked, retry {attempt+1}/{MAX_RETRIES} dopo {delay:.1f}s")
                    time.sleep(delay)
                    continue
                raise
        logger.error(f"Max retries ({MAX_RETRIES}) raggiunti per database lock")
        raise last_error
    return wrapper

class SelectionManager(PopulationBaseManager):
    """Gestisce la selezione naturale dei cromosomi."""
    
    @retry_on_db_lock
    def select_parents(self, population: Population, num_pairs: int, session: Session) -> List[Tuple[Chromosome, Chromosome]]:
        """
        Seleziona coppie di cromosomi per la riproduzione usando tournament selection.
        
        Args:
            population: Popolazione da cui selezionare
            num_pairs: Numero di coppie da selezionare
            session: Sessione database attiva
            
        Returns:
            List[Tuple[Chromosome, Chromosome]]: Lista di coppie di cromosomi
        """
        try:
            # Ricarica popolazione nella sessione corrente
            population = session.merge(population)
            
            # Ottieni cromosomi attivi
            active_chromosomes = []
            for chromosome in population.chromosomes:
                if chromosome.status == 'active':
                    active_chromosomes.append(chromosome)
                    
            if len(active_chromosomes) < 2:
                raise ValueError("Non ci sono abbastanza cromosomi attivi")
                
            # Calcola dimensione torneo
            tournament_size = max(2, int(len(active_chromosomes) * 0.1))
            
            # Seleziona coppie
            pairs = []
            for _ in range(num_pairs):
                parent1 = self._tournament_select(active_chromosomes, tournament_size)
                parent2 = self._tournament_select(
                    [c for c in active_chromosomes if c != parent1], 
                    tournament_size
                )
                pairs.append((parent1, parent2))
                
            # Log selezione
            logger.info(f"Selezionate {len(pairs)} coppie per riproduzione")
            
            return pairs
            
        except Exception as e:
            logger.error(f"Errore selezione genitori: {str(e)}")
            raise
            
    @retry_on_db_lock
    def select_survivors(self, population: Population, offspring: List[Chromosome], session: Session) -> List[Chromosome]:
        """
        Seleziona i cromosomi che sopravviveranno alla prossima generazione.
        
        Args:
            population: Popolazione corrente
            offspring: Nuovi cromosomi generati
            session: Sessione database attiva
            
        Returns:
            List[Chromosome]: Cromosomi selezionati
        """
        try:
            # Ricarica popolazione nella sessione corrente
            population = session.merge(population)
            
            # Unisci cromosomi esistenti e nuovi
            all_chromosomes = []
            
            # Aggiungi cromosomi esistenti
            for chromosome in population.chromosomes:
                if chromosome.status == 'active':
                    all_chromosomes.append(chromosome)
            
            # Aggiungi nuovi cromosomi
            for chromosome in offspring:
                if chromosome:
                    merged_chromosome = session.merge(chromosome)
                    all_chromosomes.append(merged_chromosome)
            
            # Ordina per fitness
            all_chromosomes.sort(
                key=lambda x: self._get_fitness(x),
                reverse=True
            )
            
            # Seleziona i migliori
            survivors = all_chromosomes[:population.max_size]
            
            # Aggiorna statistiche
            stats = {
                "total_evaluated": len(all_chromosomes),
                "survivors": len(survivors),
                "avg_fitness": np.mean([self._get_fitness(c) for c in survivors]),
                "best_fitness": self._get_fitness(survivors[0]) if survivors else 0.0,
                "worst_fitness": self._get_fitness(survivors[-1]) if survivors else 0.0
            }
            
            # Salva storia
            history = EvolutionHistory(
                population_id=population.population_id,
                generation=population.current_generation + 1,
                best_fitness=stats["best_fitness"],
                avg_fitness=stats["avg_fitness"],
                diversity_metric=self._calculate_diversity(survivors),
                mutation_rate=population.mutation_rate,
                selection_stats=json.dumps(stats)
            )
            
            session.add(history)
            
            # Log selezione
            logger.info(
                f"Selezionati {len(survivors)} sopravvissuti "
                f"(best={stats['best_fitness']:.2f}, avg={stats['avg_fitness']:.2f})"
            )
            
            return survivors
            
        except Exception as e:
            logger.error(f"Errore selezione sopravvissuti: {str(e)}")
            raise
            
    def _tournament_select(self, chromosomes: List[Chromosome], tournament_size: int) -> Chromosome:
        """
        Seleziona un cromosoma usando tournament selection.
        
        Args:
            chromosomes: Lista di cromosomi
            tournament_size: Dimensione del torneo
            
        Returns:
            Chromosome: Cromosoma selezionato
        """
        # Seleziona partecipanti
        tournament = random.sample(chromosomes, tournament_size)
        
        # Trova il migliore
        return max(tournament, key=self._get_fitness)
        
    def _get_fitness(self, chromosome: Chromosome) -> float:
        """
        Ottiene il fitness di un cromosoma.
        
        Args:
            chromosome: Cromosoma da valutare
            
        Returns:
            float: Valore fitness
        """
        if not chromosome or not chromosome.performance_metrics:
            return 0.0
            
        try:
            metrics = json.loads(chromosome.performance_metrics)
            return float(metrics.get('fitness', 0.0))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return 0.0
        
    def _calculate_diversity(self, chromosomes: List[Chromosome]) -> float:
        """
        Calcola la diversità genetica tra i cromosomi.
        
        Args:
            chromosomes: Lista di cromosomi
            
        Returns:
            float: Indice di diversità (0-1)
        """
        if not chromosomes:
            return 0.0
            
        # Calcola distanza media tra fingerprint
        distances = []
        for i, c1 in enumerate(chromosomes):
            if not c1 or not c1.fingerprint:
                continue
            for c2 in chromosomes[i+1:]:
                if not c2 or not c2.fingerprint:
                    continue
                distance = self._hamming_distance(c1.fingerprint, c2.fingerprint)
                distances.append(distance)
                
        return np.mean(distances) if distances else 0.0
        
    def _hamming_distance(self, s1: str, s2: str) -> float:
        """
        Calcola la distanza di Hamming normalizzata tra due stringhe.
        
        Args:
            s1: Prima stringa
            s2: Seconda stringa
            
        Returns:
            float: Distanza normalizzata (0-1)
        """
        if not s1 or not s2 or len(s1) != len(s2):
            return 1.0
            
        differences = sum(c1 != c2 for c1, c2 in zip(s1, s2))
        return differences / len(s1)
