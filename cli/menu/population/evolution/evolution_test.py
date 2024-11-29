"""
Evolution Test
------------
Test del sistema di evoluzione delle popolazioni.
"""

from typing import Dict, List, Optional
import json
from datetime import datetime
from pathlib import Path
import yaml
from contextlib import contextmanager
import time
import random

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from data.database.models.population_models import (
    Population, Chromosome, ChromosomeGene, EvolutionHistory
)
from cli.menu.population.population_base import PopulationBaseManager
from cli.logger.log_manager import get_logger
from cli.progress.indicators import ProgressBar
from .evolution_manager import EvolutionManager
from .selection_manager import SelectionManager
from .reproduction_manager import ReproductionManager
from .mutation_manager import MutationManager
from .fitness_calculator import FitnessCalculator

# Setup logger
logger = get_logger('evolution_test')

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
                print(f"[DEBUG] Tentativo {attempt+1}/{MAX_RETRIES} di esecuzione {func.__name__}")
                return func(*args, **kwargs)
            except OperationalError as e:
                if "database is locked" in str(e):
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

class EvolutionTester(PopulationBaseManager):
    """Tester per il sistema di evoluzione."""
    
    def __init__(self):
        """Inizializza il tester."""
        super().__init__()
        self.evolution = EvolutionManager()
        self.selection = SelectionManager()
        self.reproduction = ReproductionManager()
        self.mutation = MutationManager()
        self.fitness = FitnessCalculator()
        
        # Carica configurazione test
        self.test_config = self._load_test_config()
        
        # Setup logger specifico per i test
        self.logger = get_logger('evolution_test')
        print("[DEBUG] EvolutionTester inizializzato")
        
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
            self.logger.error(f"Errore caricamento configurazione test: {str(e)}")
            raise

    @retry_on_db_lock
    def run_test(self, population_id: int, generations: int = 5, session: Optional[Session] = None) -> str:
        """
        Esegue un test completo del sistema di evoluzione.
        
        Args:
            population_id: ID della popolazione da testare
            generations: Numero di generazioni da evolvere
            session: Sessione database opzionale
            
        Returns:
            str: Report del test
        """
        try:
            print(f"[DEBUG] Avvio run_test per popolazione {population_id}, generazioni {generations}")
            # Se non viene fornita una sessione, ne crea una nuova
            if session is None:
                print("[DEBUG] Creazione nuova sessione database")
                with self.session_scope() as session:
                    return self._run_test_internal(population_id, generations, session)
            else:
                # Usa la sessione fornita
                print("[DEBUG] Utilizzo sessione database esistente")
                return self._run_test_internal(population_id, generations, session)
                
        except Exception as e:
            print(f"[DEBUG] ERRORE in run_test: {str(e)}")
            logger.error(f"Errore test evoluzione: {str(e)}")
            raise

    def _run_test_internal(self, population_id: int, generations: int, session: Session) -> str:
        """
        Implementazione interna del test di evoluzione.
        
        Args:
            population_id: ID della popolazione da testare
            generations: Numero di generazioni da evolvere
            session: Sessione database attiva
            
        Returns:
            str: Report del test
        """
        # Verifica popolazione
        print(f"[DEBUG] Verifica popolazione {population_id}")
        population = session.get(Population, population_id)
        if not population:
            return "Popolazione non trovata"
            
        logger.info(f"Inizio test evoluzione per popolazione {population.name}")
        
        # Test iniziale fitness
        print("[DEBUG] Calcolo fitness iniziale")
        initial_stats = self.fitness.calculate_population_fitness(population)
        
        # Evolvi per N generazioni
        evolution_stats = []
        for i in range(generations):
            print(f"\n[DEBUG] ===== INIZIO GENERAZIONE {i+1}/{generations} =====")
            logger.info(f"Evoluzione generazione {i+1}/{generations}")
            
            # Ricarica popolazione nella sessione corrente
            print(f"[DEBUG] Ricarico popolazione {population_id} nella sessione")
            population = session.get(Population, population_id)
            
            # Selezione genitori
            print("[DEBUG] Selezione genitori")
            parent_pairs = self.selection.select_parents(
                population,
                population.max_size // 2,
                session
            )
            print(f"[DEBUG] Selezionati {len(parent_pairs)} coppie di genitori")
            
            # Riproduzione
            print("[DEBUG] Avvio riproduzione")
            offspring = self.reproduction.reproduce_batch(parent_pairs, session)
            print(f"[DEBUG] Generati {len(offspring)} figli")
            
            # Mutazione
            print("[DEBUG] Avvio mutazione")
            mutated = self.mutation.mutate_population(population, offspring, session)
            print(f"[DEBUG] Mutati {len(mutated)} cromosomi")
            
            # Calcolo fitness solo per cromosomi validi
            print("[DEBUG] Calcolo fitness cromosomi mutati")
            valid_mutated = []
            for chromosome in mutated:
                if chromosome and chromosome.population_id:
                    self.fitness.calculate_chromosome_fitness(chromosome)
                    valid_mutated.append(chromosome)
            print(f"[DEBUG] {len(valid_mutated)} cromosomi validi dopo mutazione")
            
            # Selezione sopravvissuti
            print("[DEBUG] Selezione sopravvissuti")
            survivors = self.selection.select_survivors(population, valid_mutated, session)
            print(f"[DEBUG] Selezionati {len(survivors)} sopravvissuti")
            
            # Calcola statistiche
            gen_stats = self._calculate_generation_stats(survivors)
            evolution_stats.append(gen_stats)
            
            # Aggiorna popolazione
            print("[DEBUG] Aggiornamento popolazione")
            self._update_population(population, survivors, session)
            
            # Commit esplicito per ogni generazione
            print("[DEBUG] Commit della generazione")
            session.commit()
            print(f"[DEBUG] ===== FINE GENERAZIONE {i+1}/{generations} =====\n")
        
        # Test finale fitness
        print("[DEBUG] Calcolo fitness finale")
        population = session.get(Population, population_id)
        final_stats = self.fitness.calculate_population_fitness(population)
        
        # Genera report
        print("[DEBUG] Generazione report")
        report = self._generate_test_report(
            population,
            initial_stats,
            evolution_stats,
            final_stats
        )
        
        # Salva report
        print("[DEBUG] Salvataggio report")
        self._save_report(population, report)
        
        logger.info("Test evoluzione completato")
        print("[DEBUG] Test evoluzione completato con successo")
        return report
            
    def _calculate_generation_stats(self, chromosomes: List[Chromosome]) -> Dict:
        """
        Calcola statistiche per una generazione.
        
        Args:
            chromosomes: Lista cromosomi
            
        Returns:
            Dict: Statistiche generazione
        """
        try:
            if not chromosomes:
                return {
                    'fitness': {'min': 0.0, 'max': 0.0, 'avg': 0.0},
                    'genes': {},
                    'weights': {'min': 0.0, 'max': 0.0, 'avg': 0.0}
                }
                
            fitness_values = []
            gene_counts = {}
            weight_stats = {
                'min': float('inf'),
                'max': float('-inf'),
                'total': 0.0,
                'count': 0
            }
            
            for chromosome in chromosomes:
                if not chromosome or not chromosome.performance_metrics:
                    continue
                    
                # Fitness
                try:
                    fitness = float(json.loads(chromosome.performance_metrics)['fitness'])
                    fitness_values.append(fitness)
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
                    
                # Geni
                for gene in chromosome.genes:
                    if gene.gene_type not in gene_counts:
                        gene_counts[gene.gene_type] = 0
                    gene_counts[gene.gene_type] += 1
                    
                    # Pesi
                    weight_stats['min'] = min(weight_stats['min'], gene.weight)
                    weight_stats['max'] = max(weight_stats['max'], gene.weight)
                    weight_stats['total'] += gene.weight
                    weight_stats['count'] += 1
                    
            return {
                'fitness': {
                    'min': min(fitness_values) if fitness_values else 0.0,
                    'max': max(fitness_values) if fitness_values else 0.0,
                    'avg': sum(fitness_values) / len(fitness_values) if fitness_values else 0.0
                },
                'genes': gene_counts,
                'weights': {
                    'min': weight_stats['min'] if weight_stats['count'] > 0 else 0.0,
                    'max': weight_stats['max'] if weight_stats['count'] > 0 else 0.0,
                    'avg': weight_stats['total'] / weight_stats['count'] if weight_stats['count'] > 0 else 0.0
                }
            }
            
        except Exception as e:
            logger.error(f"Errore calcolo statistiche: {str(e)}")
            return {
                'fitness': {'min': 0.0, 'max': 0.0, 'avg': 0.0},
                'genes': {},
                'weights': {'min': 0.0, 'max': 0.0, 'avg': 0.0}
            }
        
    def _update_population(self, population: Population, survivors: List[Chromosome], session: Session) -> None:
        """
        Aggiorna la popolazione con i sopravvissuti.
        
        Args:
            population: Popolazione da aggiornare
            survivors: Cromosomi sopravvissuti
            session: Sessione database attiva
        """
        try:
            print(f"[DEBUG] Inizio aggiornamento popolazione {population.name}")
            # Aggiorna cromosomi
            for chromosome in population.chromosomes:
                if chromosome not in survivors:
                    chromosome.status = 'archived'
                    
            # Incrementa generazione
            population.current_generation += 1
            
            # Aggiorna metriche
            valid_survivors = [s for s in survivors if s and s.performance_metrics]
            if valid_survivors:
                best_chromosome = max(
                    valid_survivors,
                    key=lambda x: float(json.loads(x.performance_metrics)['fitness'])
                )
                population.performance_score = float(
                    json.loads(best_chromosome.performance_metrics)['fitness']
                )
            
            print(f"[DEBUG] Popolazione aggiornata: gen={population.current_generation}, score={population.performance_score}")
            logger.info(
                f"Popolazione {population.name} aggiornata a generazione "
                f"{population.current_generation}"
            )
            
        except Exception as e:
            print(f"[DEBUG] ERRORE aggiornamento popolazione: {str(e)}")
            logger.error(f"Errore aggiornamento popolazione: {str(e)}")
            raise
            
    def _validate_results(
        self,
        initial_stats: Dict,
        final_stats: Dict,
        evolution_stats: List[Dict]
    ) -> Dict:
        """
        Valida i risultati del test.
        
        Args:
            initial_stats: Statistiche iniziali
            final_stats: Statistiche finali
            evolution_stats: Statistiche evoluzione
            
        Returns:
            Dict: Risultati validazione
        """
        validation = {
            'passed': True,
            'failures': [],
            'warnings': []
        }
        
        # Verifica miglioramento minimo
        if initial_stats['avg_fitness'] > 0:
            improvement = (final_stats['avg_fitness'] - initial_stats['avg_fitness']) / initial_stats['avg_fitness']
            if improvement < self.test_config['validation']['min_improvement']:
                validation['passed'] = False
                validation['failures'].append(
                    f"Miglioramento insufficiente: {improvement:.1%} < "
                    f"{self.test_config['validation']['min_improvement']:.1%}"
                )
            
        # Verifica win rate
        if final_stats.get('win_rate', 0) < self.test_config['validation']['min_win_rate']:
            validation['warnings'].append(
                f"Win rate basso: {final_stats.get('win_rate', 0):.1%} < "
                f"{self.test_config['validation']['min_win_rate']:.1%}"
            )
            
        # Verifica drawdown
        if final_stats.get('max_drawdown', 0) > self.test_config['validation']['max_drawdown']:
            validation['warnings'].append(
                f"Drawdown alto: {final_stats.get('max_drawdown', 0):.1%} > "
                f"{self.test_config['validation']['max_drawdown']:.1%}"
            )
            
        # Verifica numero trade
        if final_stats.get('trades', 0) < self.test_config['validation']['min_trades']:
            validation['warnings'].append(
                f"Pochi trade: {final_stats.get('trades', 0)} < "
                f"{self.test_config['validation']['min_trades']}"
            )
            
        return validation
        
    def _generate_test_report(
        self,
        population: Population,
        initial_stats: Dict,
        evolution_stats: List[Dict],
        final_stats: Dict
    ) -> str:
        """
        Genera un report dettagliato del test.
        
        Args:
            population: Popolazione testata
            initial_stats: Statistiche iniziali
            evolution_stats: Statistiche evoluzione
            final_stats: Statistiche finali
            
        Returns:
            str: Report formattato
        """
        lines = [
            f"\n=== Report Test Evoluzione ===\n",
            f"Popolazione: {population.name}",
            f"Generazioni: {len(evolution_stats)}",
            f"Dimensione: {population.max_size}",
            
            "\nStatistiche Iniziali:",
            f"- Fitness Medio: {initial_stats['avg_fitness']:.2f}",
            f"- Miglior Fitness: {initial_stats['best_fitness']:.2f}",
            
            "\nProgresso Evoluzione:"
        ]
        
        for i, stats in enumerate(evolution_stats):
            lines.extend([
                f"\nGenerazione {i+1}:",
                f"- Fitness: min={stats['fitness']['min']:.2f}, "
                f"max={stats['fitness']['max']:.2f}, "
                f"avg={stats['fitness']['avg']:.2f}",
                "- Distribuzione Geni:",
                *[f"  * {gene}: {count}" 
                  for gene, count in stats['genes'].items()],
                f"- Pesi: min={stats['weights']['min']:.2f}, "
                f"max={stats['weights']['max']:.2f}, "
                f"avg={stats['weights']['avg']:.2f}"
            ])
            
        lines.extend([
            "\nStatistiche Finali:",
            f"- Fitness Medio: {final_stats['avg_fitness']:.2f}",
            f"- Miglior Fitness: {final_stats['best_fitness']:.2f}"
        ])
        
        if initial_stats['avg_fitness'] > 0:
            improvement = ((final_stats['avg_fitness'] - initial_stats['avg_fitness']) 
                         / initial_stats['avg_fitness'] * 100)
            lines.append(f"- Miglioramento: {improvement:.1f}%")
        
        return "\n".join(lines)
        
    @retry_on_db_lock
    def _save_report(self, population: Population, report: str) -> None:
        """
        Salva il report su file.
        
        Args:
            population: Popolazione testata
            report: Report da salvare
        """
        try:
            print(f"[DEBUG] Inizio salvataggio report per popolazione {population.name}")
            # Crea directory se non esiste
            report_dir = Path('test_reports')
            report_dir.mkdir(parents=True, exist_ok=True)
            
            # Genera nome file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evolution_test_{population.name}_{timestamp}.txt"
            
            # Salva report
            with open(report_dir / filename, 'w') as f:
                f.write(report)
                
            print(f"[DEBUG] Report salvato con successo in {filename}")
            logger.info(f"Report salvato in {filename}")
            
        except Exception as e:
            print(f"[DEBUG] ERRORE salvataggio report: {str(e)}")
            logger.error(f"Errore salvataggio report: {str(e)}")
