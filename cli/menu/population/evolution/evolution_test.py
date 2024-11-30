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
import time
import random

from sqlalchemy import text, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from data.database.models.population_models import (
    Population, Chromosome, ChromosomeGene, EvolutionHistory
)
from data.database.models.models import verify_database_state
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
        self.test_config = self._load_test_config()
        self.logger = get_logger('evolution_test')
        print("[DEBUG] EvolutionTester inizializzato")
        
    def _load_test_config(self) -> Dict:
        """Carica la configurazione dei test."""
        try:
            with open('config/test.yaml', 'r') as f:
                config = yaml.safe_load(f)
            return config['evolution_test']
        except Exception as e:
            self.logger.error(f"Errore caricamento configurazione test: {str(e)}")
            raise

    def _get_population(self, population_id: int, session: Session) -> Optional[Population]:
        """Carica una popolazione con tutte le sue relazioni."""
        try:
            # Prima otteniamo il lock sulla popolazione
            lock_result = session.execute(text("""
                SELECT *
                FROM populations 
                WHERE population_id = :population_id
                FOR UPDATE
            """), {"population_id": population_id})
            
            population_data = lock_result.fetchone()
            if not population_data:
                return None
                
            # Crea l'oggetto Population con i nuovi campi JSON
            population = Population(
                population_id=population_data.population_id,
                name=population_data.name,
                max_size=population_data.max_size,
                current_generation=population_data.current_generation,
                status=population_data.status,
                diversity_score=population_data.diversity_score,
                performance_score=population_data.performance_score,
                mutation_rate=population_data.mutation_rate,
                selection_pressure=population_data.selection_pressure,
                generation_interval=population_data.generation_interval,
                diversity_threshold=population_data.diversity_threshold,
                timeframe=population_data.timeframe,
                symbol_id=population_data.symbol_id,
                evolution_config=population_data.evolution_config or {},
                performance_thresholds=population_data.performance_thresholds or {},
                optimization_settings=population_data.optimization_settings or {}
            )
            
            # Carica i cromosomi
            chromosomes_result = session.execute(text("""
                SELECT *
                FROM chromosomes 
                WHERE population_id = :population_id
            """), {"population_id": population_id})
            
            population.chromosomes = []
            chromosome_ids = []
            
            for c in chromosomes_result:
                # Crea oggetto Chromosome con i nuovi campi JSON
                chromosome = Chromosome(
                    chromosome_id=c.chromosome_id,
                    population_id=c.population_id,
                    fingerprint=c.fingerprint,
                    generation=c.generation,
                    age=c.age,
                    created_at=c.created_at,
                    parent1_id=c.parent1_id,
                    parent2_id=c.parent2_id,
                    status=c.status,
                    performance_metrics=c.performance_metrics or {},
                    weight_distribution=c.weight_distribution or {},
                    test_results=c.test_results or {},
                    fitness_history=c.fitness_history or [],
                    mutation_stats=c.mutation_stats or {},
                    last_test_date=c.last_test_date
                )
                population.chromosomes.append(chromosome)
                chromosome_ids.append(c.chromosome_id)
            
            if chromosome_ids:
                # Carica i geni per tutti i cromosomi
                genes_result = session.execute(text("""
                    SELECT *
                    FROM chromosome_genes 
                    WHERE chromosome_id = ANY(:chromosome_ids)
                """), {"chromosome_ids": chromosome_ids})
                
                # Organizza i geni per chromosome_id
                genes_by_chromosome = {}
                for g in genes_result:
                    # Crea oggetto ChromosomeGene con i nuovi campi JSON
                    gene = ChromosomeGene(
                        chromosome_gene_id=g.chromosome_gene_id,
                        chromosome_id=g.chromosome_id,
                        gene_type=g.gene_type,
                        parameters=g.parameters or {},
                        weight=g.weight,
                        is_active=g.is_active,
                        performance_contribution=g.performance_contribution,
                        last_mutation_date=g.last_mutation_date,
                        mutation_history=g.mutation_history or [],
                        validation_rules=g.validation_rules or {},
                        optimization_history=g.optimization_history or [],
                        performance_metrics=g.performance_metrics or {}
                    )
                    
                    if g.chromosome_id not in genes_by_chromosome:
                        genes_by_chromosome[g.chromosome_id] = []
                    genes_by_chromosome[g.chromosome_id].append(gene)
                
                # Assegna i geni ai rispettivi cromosomi
                for chromosome in population.chromosomes:
                    chromosome.genes = genes_by_chromosome.get(chromosome.chromosome_id, [])
            
            return population
            
        except Exception as e:
            logger.error(f"Errore caricamento popolazione: {str(e)}")
            return None

    def run_test(self, population_id: int, generations: int = 5, session: Optional[Session] = None) -> str:
        """Esegue un test completo del sistema di evoluzione."""
        try:
            # Verifica stato database prima del test
            if not verify_database_state():
                raise Exception("Stato database non valido prima del test")
                
            if session is None:
                with self.session_scope() as session:
                    return self._run_test_internal(population_id, generations, session)
            else:
                return self._run_test_internal(population_id, generations, session)
                
        except Exception as e:
            logger.error(f"Errore test evoluzione: {str(e)}")
            raise

    def _run_test_internal(self, population_id: int, generations: int, session: Session) -> str:
        """Implementazione interna del test di evoluzione."""
        try:
            # Carica popolazione con lock
            population = self._get_population(population_id, session)
            if not population:
                return "Popolazione non trovata"
            
            # Carica dati di mercato
            print("[DEBUG] Caricamento dati di mercato...")
            market_data = self.fitness.market_data.get_market_data(population, session)
            if not market_data:
                print("[DEBUG] Creazione dati di test...")
                market_data = self.fitness.market_data.create_test_market_data(
                    self.test_config['backtest']['days']
                )
            print("[DEBUG] Dati di mercato caricati")
            
            # Calcola fitness iniziale
            initial_stats = self._calculate_population_stats(population_id, session)
            evolution_stats = []
            
            # Evolvi per N generazioni
            for i in range(generations):
                print(f"\n[DEBUG] === GENERAZIONE {i+1}/{generations} ===")
                
                # Esegui evoluzione in una transazione
                try:
                    # Selezione e riproduzione
                    parent_pairs = self.selection.select_parents(population, population.max_size // 2, session)
                    offspring = self.reproduction.reproduce_batch(parent_pairs, session)
                    
                    # Mutazione e fitness
                    mutated = self.mutation.mutate_population(population, offspring, session)
                    valid_mutated = []
                    for chromosome in mutated:
                        if chromosome and chromosome.population_id:
                            self.fitness._calculate_chromosome_fitness_no_merge(chromosome, market_data, session)
                            valid_mutated.append(chromosome)
                    
                    # Selezione sopravvissuti
                    survivors = self.selection.select_survivors(population, valid_mutated, session)
                    
                    # Aggiorna popolazione
                    self._update_population_stats(population_id, survivors, session)
                    
                    # Calcola statistiche generazione
                    gen_stats = self._calculate_generation_stats(survivors, session)
                    evolution_stats.append(gen_stats)
                    
                    # Verifica stato dopo ogni generazione
                    if not verify_database_state():
                        raise Exception(f"Stato database non valido dopo generazione {i+1}")
                    
                    session.commit()
                    
                except Exception as e:
                    session.rollback()
                    raise
            
            # Calcola statistiche finali
            final_stats = self._calculate_population_stats(population_id, session)
            
            # Genera e salva report
            report = self._generate_test_report(population, initial_stats, evolution_stats, final_stats)
            self._save_report(population, report)
            
            return report
            
        except Exception as e:
            logger.error(f"Errore in run_test_internal: {str(e)}")
            raise
            
    def _calculate_population_stats(self, population_id: int, session: Session) -> Dict:
        """Calcola statistiche della popolazione usando funzioni di aggregazione PostgreSQL."""
        try:
            result = session.execute(text("""
                SELECT 
                    avg((performance_metrics->>'fitness')::float) as avg_fitness,
                    max((performance_metrics->>'fitness')::float) as best_fitness,
                    avg((performance_metrics->>'win_rate')::float) as win_rate,
                    max((performance_metrics->>'max_drawdown')::float) as max_drawdown,
                    sum((performance_metrics->>'trades')::int) as total_trades
                FROM chromosomes
                WHERE population_id = :population_id
                AND status = 'active'
                AND performance_metrics IS NOT NULL
            """), {"population_id": population_id})
            
            stats = result.fetchone()
            return {
                'avg_fitness': stats.avg_fitness or 0.0,
                'best_fitness': stats.best_fitness or 0.0,
                'win_rate': stats.win_rate or 0.0,
                'max_drawdown': stats.max_drawdown or 0.0,
                'trades': stats.total_trades or 0
            }
            
        except Exception as e:
            logger.error(f"Errore calcolo statistiche popolazione: {str(e)}")
            return {
                'avg_fitness': 0.0,
                'best_fitness': 0.0,
                'win_rate': 0.0,
                'max_drawdown': 0.0,
                'trades': 0
            }
            
    def _calculate_generation_stats(self, survivors: List[Chromosome], session: Session) -> Dict:
        """Calcola statistiche della generazione usando funzioni di aggregazione PostgreSQL."""
        try:
            chromosome_ids = [s.chromosome_id for s in survivors if s and s.chromosome_id]
            if not chromosome_ids:
                return {
                    'fitness': {'min': 0.0, 'max': 0.0, 'avg': 0.0},
                    'genes': {},
                    'weights': {'min': 0.0, 'max': 0.0, 'avg': 0.0}
                }
            
            # Query per statistiche fitness e pesi
            result = session.execute(text("""
                SELECT 
                    min((c.performance_metrics->>'fitness')::float) as min_fitness,
                    max((c.performance_metrics->>'fitness')::float) as max_fitness,
                    avg((c.performance_metrics->>'fitness')::float) as avg_fitness,
                    min(g.weight) as min_weight,
                    max(g.weight) as max_weight,
                    avg(g.weight) as avg_weight
                FROM chromosomes c
                LEFT JOIN chromosome_genes g ON c.chromosome_id = g.chromosome_id
                WHERE c.chromosome_id = ANY(:chromosome_ids)
                AND c.performance_metrics IS NOT NULL
            """), {"chromosome_ids": chromosome_ids})
            
            stats = result.fetchone()
            
            # Query per conteggio geni
            gene_result = session.execute(text("""
                SELECT 
                    g.gene_type,
                    count(*) as gene_count,
                    avg((g.performance_metrics->>'contribution')::float) as avg_contribution
                FROM chromosome_genes g
                WHERE g.chromosome_id = ANY(:chromosome_ids)
                AND g.is_active = true
                GROUP BY g.gene_type
            """), {"chromosome_ids": chromosome_ids})
            
            gene_stats = {}
            for row in gene_result:
                gene_stats[row.gene_type] = {
                    'count': row.gene_count,
                    'contribution': row.avg_contribution or 0.0
                }
            
            return {
                'fitness': {
                    'min': stats.min_fitness or 0.0,
                    'max': stats.max_fitness or 0.0,
                    'avg': stats.avg_fitness or 0.0
                },
                'genes': gene_stats,
                'weights': {
                    'min': stats.min_weight or 0.0,
                    'max': stats.max_weight or 0.0,
                    'avg': stats.avg_weight or 0.0
                }
            }
            
        except Exception as e:
            logger.error(f"Errore calcolo statistiche generazione: {str(e)}")
            return {
                'fitness': {'min': 0.0, 'max': 0.0, 'avg': 0.0},
                'genes': {},
                'weights': {'min': 0.0, 'max': 0.0, 'avg': 0.0}
            }
            
    def _update_population_stats(self, population_id: int, survivors: List[Chromosome], session: Session) -> None:
        """Aggiorna le statistiche della popolazione usando UPDATE con RETURNING."""
        try:
            # Calcola il miglior fitness dai sopravvissuti
            best_fitness = max(
                (s.performance_metrics.get('fitness', 0.0) if isinstance(s.performance_metrics, dict)
                 else json.loads(s.performance_metrics).get('fitness', 0.0) if s.performance_metrics
                 else 0.0)
                for s in survivors
            )
            
            # Aggiorna la popolazione
            result = session.execute(text("""
                UPDATE populations 
                SET 
                    current_generation = current_generation + 1,
                    performance_score = :best_fitness,
                    updated_at = CURRENT_TIMESTAMP
                WHERE population_id = :population_id
                RETURNING current_generation, performance_score
            """), {
                "population_id": population_id,
                "best_fitness": best_fitness
            })
            
            updated = result.fetchone()
            logger.debug(f"Popolazione aggiornata: gen={updated.current_generation}, score={updated.performance_score}")
            
        except Exception as e:
            logger.error(f"Errore aggiornamento popolazione: {str(e)}")
            raise
            
    def _generate_test_report(
        self,
        population: Population,
        initial_stats: Dict,
        evolution_stats: List[Dict],
        final_stats: Dict
    ) -> str:
        """Genera un report dettagliato del test."""
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
                *[f"  * {gene}: count={data['count']}, contribution={data['contribution']:.2f}%" 
                  for gene, data in stats['genes'].items()],
                f"- Pesi: min={stats['weights']['min']:.2f}, "
                f"max={stats['weights']['max']:.2f}, "
                f"avg={stats['weights']['avg']:.2f}"
            ])
            
        lines.extend([
            "\nStatistiche Finali:",
            f"- Fitness Medio: {final_stats['avg_fitness']:.2f}",
            f"- Miglior Fitness: {final_stats['best_fitness']:.2f}",
            f"- Win Rate: {final_stats['win_rate']:.1%}",
            f"- Max Drawdown: {final_stats['max_drawdown']:.1%}",
            f"- Trades Totali: {final_stats['trades']}"
        ])
        
        if initial_stats['avg_fitness'] > 0:
            improvement = ((final_stats['avg_fitness'] - initial_stats['avg_fitness']) 
                         / initial_stats['avg_fitness'] * 100)
            lines.append(f"- Miglioramento: {improvement:.1f}%")
        
        return "\n".join(lines)
        
    def _save_report(self, population: Population, report: str) -> None:
        """Salva il report su file."""
        try:
            report_dir = Path('test_reports')
            report_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evolution_test_{population.name}_{timestamp}.txt"
            
            with open(report_dir / filename, 'w') as f:
                f.write(report)
                
            logger.info(f"Report salvato in {filename}")
            
        except Exception as e:
            logger.error(f"Errore salvataggio report: {str(e)}")
