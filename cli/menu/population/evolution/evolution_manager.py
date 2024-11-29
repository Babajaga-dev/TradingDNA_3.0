"""
Evolution Manager
--------------
Gestione del ciclo evolutivo delle popolazioni.
"""

from typing import Dict, List, Optional
from datetime import datetime
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

from data.database.models.population_models import (
    Population, Chromosome, ChromosomeGene, EvolutionHistory
)
from cli.menu.population.population_base import PopulationBaseManager
from cli.logger.log_manager import get_logger
from .selection_manager import SelectionManager
from .reproduction_manager import ReproductionManager
from .mutation_manager import MutationManager
from .fitness_calculator import FitnessCalculator

# Setup logger
logger = get_logger('evolution_manager')

class EvolutionManager(PopulationBaseManager):
    """Gestisce l'evoluzione delle popolazioni."""
    
    def __init__(self):
        """Inizializza l'evolution manager."""
        super().__init__()
        self.active_populations: Dict[int, bool] = {}  # population_id: is_evolving
        self.selection_manager = SelectionManager()
        self.reproduction_manager = ReproductionManager()
        self.mutation_manager = MutationManager()
        self.fitness_calculator = FitnessCalculator()
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    def start_evolution(self, population_id: int) -> str:
        """
        Avvia l'evoluzione di una popolazione.
        
        Args:
            population_id: ID della popolazione
            
        Returns:
            str: Messaggio di conferma o errore
        """
        try:
            # Verifica popolazione
            population = self.get_population(population_id)
            if not population:
                return "Popolazione non trovata"
                
            if population.status != 'active':
                return f"Popolazione in stato {population.status}, deve essere 'active'"
                
            if population_id in self.active_populations:
                return "Evoluzione già in corso"
                
            # Avvia evoluzione in background
            self.active_populations[population_id] = True
            asyncio.create_task(self._evolution_loop(population))
            
            # Log avvio
            logger.info(f"Avviata evoluzione popolazione {population.name}")
            
            # Aggiorna stato
            population.status = 'evolving'
            self.session.commit()
            
            return f"Evoluzione avviata per popolazione {population.name}"
            
        except Exception as e:
            logger.error(f"Errore avvio evoluzione: {str(e)}")
            return f"Errore avvio evoluzione: {str(e)}"
            
    def stop_evolution(self, population_id: int) -> str:
        """
        Ferma l'evoluzione di una popolazione.
        
        Args:
            population_id: ID della popolazione
            
        Returns:
            str: Messaggio di conferma o errore
        """
        try:
            # Verifica popolazione
            population = self.get_population(population_id)
            if not population:
                return "Popolazione non trovata"
                
            if population_id not in self.active_populations:
                return "Evoluzione non in corso"
                
            # Ferma evoluzione
            self.active_populations.pop(population_id)
            
            # Log stop
            logger.info(f"Fermata evoluzione popolazione {population.name}")
            
            # Aggiorna stato
            population.status = 'active'
            self.session.commit()
            
            return f"Evoluzione fermata per popolazione {population.name}"
            
        except Exception as e:
            logger.error(f"Errore stop evoluzione: {str(e)}")
            return f"Errore stop evoluzione: {str(e)}"
            
    async def _evolution_loop(self, population: Population) -> None:
        """
        Loop principale di evoluzione.
        
        Args:
            population: Popolazione da evolvere
        """
        try:
            while self.active_populations.get(population.population_id):
                # Evolvi una generazione
                await self._evolve_generation(population)
                
                # Attendi intervallo
                await asyncio.sleep(population.generation_interval * 3600)  # ore in secondi
                
        except Exception as e:
            logger.error(f"Errore loop evoluzione: {str(e)}")
            self.stop_evolution(population.population_id)
            
    async def _evolve_generation(self, population: Population) -> None:
        """
        Evolve una generazione della popolazione.
        
        Args:
            population: Popolazione da evolvere
        """
        try:
            logger.info(f"Inizio evoluzione generazione {population.current_generation + 1}")
            
            # 1. Selezione genitori
            num_pairs = population.max_size // 2
            parent_pairs = self.selection_manager.select_parents(population, num_pairs)
            
            # 2. Riproduzione
            offspring = self.reproduction_manager.reproduce_batch(parent_pairs)
            
            # 3. Mutazione
            mutated_offspring = self.mutation_manager.mutate_population(
                population, offspring
            )
            
            # 4. Calcolo fitness
            for chromosome in mutated_offspring:
                self.fitness_calculator.calculate_chromosome_fitness(chromosome)
            
            # 5. Selezione sopravvissuti
            survivors = self.selection_manager.select_survivors(
                population, mutated_offspring
            )
            
            # 6. Aggiorna popolazione
            await self._update_population(population, survivors)
            
            logger.info(
                f"Completata evoluzione generazione "
                f"{population.current_generation} con {len(survivors)} cromosomi"
            )
            
        except Exception as e:
            logger.error(f"Errore evoluzione generazione: {str(e)}")
            raise
            
    async def _update_population(self, population: Population, survivors: List[Chromosome]) -> None:
        """
        Aggiorna la popolazione con i sopravvissuti.
        
        Args:
            population: Popolazione da aggiornare
            survivors: Cromosomi sopravvissuti
        """
        try:
            # Aggiorna cromosomi
            for chromosome in population.chromosomes:
                if chromosome not in survivors:
                    chromosome.status = 'archived'
                    
            # Incrementa generazione
            population.current_generation += 1
            
            # Aggiorna metriche
            best_chromosome = max(
                survivors,
                key=lambda x: float(json.loads(x.performance_metrics)['fitness'])
            )
            population.performance_score = float(
                json.loads(best_chromosome.performance_metrics)['fitness']
            )
            
            # Commit cambiamenti
            self.session.commit()
            
            logger.info(
                f"Popolazione {population.name} aggiornata a generazione "
                f"{population.current_generation}"
            )
            
        except Exception as e:
            logger.error(f"Errore aggiornamento popolazione: {str(e)}")
            self.session.rollback()
            raise
            
    def get_evolution_status(self, population_id: int) -> Dict:
        """
        Ottiene lo stato dell'evoluzione.
        
        Args:
            population_id: ID della popolazione
            
        Returns:
            Dict: Stato evoluzione
        """
        try:
            # Verifica popolazione
            population = self.get_population(population_id)
            if not population:
                return {"error": "Popolazione non trovata"}
                
            # Ottieni ultima history
            history = self.session.query(EvolutionHistory)\
                .filter_by(population_id=population_id)\
                .order_by(EvolutionHistory.generation.desc())\
                .first()
                
            status = {
                "is_evolving": population_id in self.active_populations,
                "generation": population.current_generation,
                "mutation_rate": population.mutation_rate,
                "selection_pressure": population.selection_pressure,
                "diversity": population.diversity_score
            }
            
            if history:
                status.update({
                    "best_fitness": history.best_fitness,
                    "avg_fitness": history.avg_fitness,
                    "stats": {
                        "generation": json.loads(history.generation_stats) if history.generation_stats else {},
                        "mutation": json.loads(history.mutation_stats) if history.mutation_stats else {},
                        "selection": json.loads(history.selection_stats) if history.selection_stats else {}
                    }
                })
                
            return status
            
        except Exception as e:
            logger.error(f"Errore recupero stato evoluzione: {str(e)}")
            return {"error": str(e)}
