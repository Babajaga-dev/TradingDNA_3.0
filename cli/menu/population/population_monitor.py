"""
Population Monitor
---------------
Monitoraggio delle popolazioni di trading.
"""

from typing import Dict, List, Optional
from datetime import datetime
import json

from data.database.models.population_models import (
    Population, Chromosome, ChromosomeGene, EvolutionHistory
)
from cli.menu.population.population_base import PopulationBaseManager
from cli.menu.menu_utils import print_table
from cli.logger.log_manager import get_logger

# Setup logger
logger = get_logger('population_monitor')

class PopulationMonitor(PopulationBaseManager):
    """Gestisce il monitoraggio delle popolazioni."""
    
    def get_population_status(self, population_id: int) -> Dict:
        """
        Ottiene lo stato dettagliato di una popolazione.
        
        Args:
            population_id: ID della popolazione
            
        Returns:
            Dict: Stato della popolazione
        """
        try:
            population = self.get_population(population_id)
            if not population:
                return {"error": "Popolazione non trovata"}
                
            # Conta cromosomi per stato
            chromosome_stats = self._get_chromosome_stats(population)
            
            # Ottieni metriche evoluzione
            evolution_metrics = self._get_evolution_metrics(population)
            
            # Formatta stato
            status = {
                "info": {
                    "id": population.population_id,
                    "nome": population.name,
                    "generazione": population.current_generation,
                    "età": self._calculate_age(population.created_at),
                    "stato": population.status
                },
                "dimensione": {
                    "attuale": chromosome_stats["total"],
                    "massima": population.max_size,
                    "attivi": chromosome_stats["active"],
                    "in_test": chromosome_stats["testing"],
                    "archiviati": chromosome_stats["archived"]
                },
                "performance": {
                    "miglior_fitness": evolution_metrics["best_fitness"],
                    "media_fitness": evolution_metrics["avg_fitness"],
                    "trend": self._calculate_trend(evolution_metrics["fitness_history"])
                },
                "diversità": {
                    "indice": population.diversity_score,
                    "soglia": population.diversity_threshold,
                    "cluster": self._count_gene_clusters(population)
                },
                "evoluzione": {
                    "tasso_mutazione": population.mutation_rate,
                    "pressione_selezione": population.selection_pressure,
                    "intervallo": population.generation_interval
                }
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Errore recupero stato popolazione {population_id}: {str(e)}")
            return {"error": str(e)}
            
    def get_chromosome_details(self, chromosome_id: int) -> Dict:
        """
        Ottiene i dettagli di un cromosoma.
        
        Args:
            chromosome_id: ID del cromosoma
            
        Returns:
            Dict: Dettagli del cromosoma
        """
        try:
            chromosome = self.session.query(Chromosome).get(chromosome_id)
            if not chromosome:
                return {"error": "Cromosoma non trovato"}
                
            # Analizza geni
            gene_analysis = self._analyze_genes(chromosome)
            
            details = {
                "info": {
                    "id": chromosome.chromosome_id,
                    "popolazione": chromosome.population.name,
                    "generazione": chromosome.generation,
                    "età": chromosome.age,
                    "stato": chromosome.status
                },
                "performance": json.loads(chromosome.performance_metrics) if chromosome.performance_metrics else {},
                "geni": {
                    "distribuzione": json.loads(chromosome.weight_distribution) if chromosome.weight_distribution else {},
                    "analisi": gene_analysis
                },
                "test": {
                    "ultimo": chromosome.last_test_date.strftime(self.config['population']['display']['date_format']) if chromosome.last_test_date else None,
                    "risultati": json.loads(chromosome.test_results) if chromosome.test_results else {}
                }
            }
            
            return details
            
        except Exception as e:
            logger.error(f"Errore recupero dettagli cromosoma {chromosome_id}: {str(e)}")
            return {"error": str(e)}
            
    def _get_chromosome_stats(self, population: Population) -> Dict:
        """
        Calcola statistiche sui cromosomi di una popolazione.
        
        Args:
            population: Popolazione da analizzare
            
        Returns:
            Dict: Statistiche cromosomi
        """
        stats = {
            "total": 0,
            "active": 0,
            "testing": 0,
            "archived": 0
        }
        
        for chromosome in population.chromosomes:
            stats["total"] += 1
            stats[chromosome.status] += 1
            
        return stats
        
    def _get_evolution_metrics(self, population: Population) -> Dict:
        """
        Ottiene metriche evolutive di una popolazione.
        
        Args:
            population: Popolazione da analizzare
            
        Returns:
            Dict: Metriche evolutive
        """
        history = self.session.query(EvolutionHistory)\
            .filter_by(population_id=population.population_id)\
            .order_by(EvolutionHistory.generation.desc())\
            .limit(10)\
            .all()
            
        if not history:
            return {
                "best_fitness": 0.0,
                "avg_fitness": 0.0,
                "fitness_history": []
            }
            
        return {
            "best_fitness": history[0].best_fitness,
            "avg_fitness": history[0].avg_fitness,
            "fitness_history": [(h.generation, h.best_fitness) for h in reversed(history)]
        }
        
    def _calculate_trend(self, history: List[tuple]) -> str:
        """
        Calcola il trend dalle ultime generazioni.
        
        Args:
            history: Lista di tuple (generazione, fitness)
            
        Returns:
            str: Indicatore trend (↑, →, ↓)
        """
        if len(history) < 2:
            return "→"
            
        last_values = [f for _, f in history[-3:]]
        if all(a < b for a, b in zip(last_values, last_values[1:])):
            return "↑"
        elif all(a > b for a, b in zip(last_values, last_values[1:])):
            return "↓"
        return "→"
        
    def _count_gene_clusters(self, population: Population) -> int:
        """
        Conta i cluster genetici nella popolazione.
        
        Args:
            population: Popolazione da analizzare
            
        Returns:
            int: Numero di cluster
        """
        # Implementazione semplificata
        unique_distributions = set()
        for chromosome in population.chromosomes:
            if chromosome.weight_distribution:
                unique_distributions.add(str(sorted(json.loads(chromosome.weight_distribution).items())))
        return len(unique_distributions)
        
    def _analyze_genes(self, chromosome: Chromosome) -> Dict:
        """
        Analizza i geni di un cromosoma.
        
        Args:
            chromosome: Cromosoma da analizzare
            
        Returns:
            Dict: Analisi dei geni
        """
        analysis = {
            "count": len(chromosome.genes),
            "active": sum(1 for g in chromosome.genes if g.is_active),
            "types": {},
            "performance": {}
        }
        
        for gene in chromosome.genes:
            # Conta tipi di geni
            if gene.gene_type not in analysis["types"]:
                analysis["types"][gene.gene_type] = 0
            analysis["types"][gene.gene_type] += 1
            
            # Analizza performance
            if gene.performance_contribution > 0:
                analysis["performance"][gene.gene_type] = gene.performance_contribution
                
        return analysis
        
    def _calculate_age(self, created_at: datetime) -> str:
        """
        Calcola l'età in giorni.
        
        Args:
            created_at: Data creazione
            
        Returns:
            str: Età formattata
        """
        age = (datetime.now() - created_at).days
        return f"{age} giorni"
