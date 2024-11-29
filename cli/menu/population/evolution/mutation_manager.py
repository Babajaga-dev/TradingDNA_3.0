"""
Mutation Manager
-------------
Gestione delle mutazioni genetiche.
"""

from typing import List, Dict
import random
import json
from datetime import datetime

from data.database.models.population_models import (
    Population, Chromosome, ChromosomeGene, EvolutionHistory
)
from cli.menu.population.population_base import PopulationBaseManager
from cli.logger.log_manager import get_logger

# Setup logger
logger = get_logger('mutation_manager')

class MutationManager(PopulationBaseManager):
    """Gestisce le mutazioni dei cromosomi."""
    
    def mutate_population(self, population: Population, chromosomes: List[Chromosome]) -> List[Chromosome]:
        """
        Applica mutazioni a una lista di cromosomi.
        
        Args:
            population: Popolazione di appartenenza
            chromosomes: Lista di cromosomi da mutare
            
        Returns:
            List[Chromosome]: Cromosomi mutati
        """
        try:
            mutation_stats = {
                "total": len(chromosomes),
                "mutated": 0,
                "gene_mutations": 0,
                "weight_mutations": 0,
                "parameter_mutations": 0
            }
            
            for chromosome in chromosomes:
                if random.random() < population.mutation_rate:
                    self._mutate_chromosome(chromosome)
                    mutation_stats["mutated"] += 1
                    
                    # Aggiorna statistiche
                    mutation_stats["gene_mutations"] += len(chromosome.genes)
                    mutation_stats["weight_mutations"] += sum(
                        1 for g in chromosome.genes if g.last_mutation_date
                    )
                    mutation_stats["parameter_mutations"] += sum(
                        1 for g in chromosome.genes 
                        if g.mutation_history and json.loads(g.mutation_history)
                    )
            
            # Log mutazioni
            logger.info(
                f"Mutati {mutation_stats['mutated']}/{mutation_stats['total']} "
                f"cromosomi con rate {population.mutation_rate}"
            )
            
            # Aggiorna statistiche popolazione
            self._update_mutation_stats(population, mutation_stats)
            
            return chromosomes
            
        except Exception as e:
            logger.error(f"Errore mutazione popolazione: {str(e)}")
            raise
            
    def _mutate_chromosome(self, chromosome: Chromosome) -> None:
        """
        Applica mutazioni a un singolo cromosoma.
        
        Args:
            chromosome: Cromosoma da mutare
        """
        # Decidi tipo di mutazione
        mutation_type = random.choice([
            'add_gene',
            'remove_gene',
            'modify_weights',
            'modify_parameters'
        ])
        
        if mutation_type == 'add_gene':
            self._add_random_gene(chromosome)
        elif mutation_type == 'remove_gene':
            self._remove_random_gene(chromosome)
        elif mutation_type == 'modify_weights':
            self._mutate_weights(chromosome)
        else:
            self._mutate_parameters(chromosome)
            
        # Aggiorna timestamp mutazione
        for gene in chromosome.genes:
            gene.last_mutation_date = datetime.now()
            
    def _add_random_gene(self, chromosome: Chromosome) -> None:
        """
        Aggiunge un nuovo gene casuale al cromosoma.
        
        Args:
            chromosome: Cromosoma da modificare
        """
        # Lista geni disponibili
        available_genes = set(self.config['gene'].keys()) - \
                         set(g.gene_type for g in chromosome.genes)
        
        if available_genes:
            gene_type = random.choice(list(available_genes))
            
            # Crea nuovo gene
            new_gene = ChromosomeGene(
                gene_type=gene_type,
                parameters=self._generate_random_parameters(gene_type),
                weight=random.random(),
                is_active=True,
                mutation_history=json.dumps({"added": datetime.now().isoformat()})
            )
            
            chromosome.genes.append(new_gene)
            
    def _remove_random_gene(self, chromosome: Chromosome) -> None:
        """
        Rimuove un gene casuale dal cromosoma.
        
        Args:
            chromosome: Cromosoma da modificare
        """
        if chromosome.genes:
            gene = random.choice(chromosome.genes)
            chromosome.genes.remove(gene)
            
    def _mutate_weights(self, chromosome: Chromosome) -> None:
        """
        Muta i pesi dei geni.
        
        Args:
            chromosome: Cromosoma da modificare
        """
        for gene in chromosome.genes:
            if random.random() < 0.3:  # 30% chance per gene
                # Applica piccola variazione
                delta = random.uniform(-0.2, 0.2)
                gene.weight = max(0.0, min(1.0, gene.weight + delta))
                
                # Aggiorna storia mutazioni
                history = json.loads(gene.mutation_history or '{}')
                history[datetime.now().isoformat()] = {
                    'type': 'weight',
                    'delta': delta
                }
                gene.mutation_history = json.dumps(history)
                
    def _mutate_parameters(self, chromosome: Chromosome) -> None:
        """
        Muta i parametri dei geni.
        
        Args:
            chromosome: Cromosoma da modificare
        """
        for gene in chromosome.genes:
            if random.random() < 0.2:  # 20% chance per gene
                params = json.loads(gene.parameters)
                
                # Ottieni regole validazione
                rules = json.loads(gene.validation_rules or '{}')
                
                # Muta parametri rispettando regole
                for param, value in params.items():
                    if random.random() < 0.5:  # 50% chance per parametro
                        if isinstance(value, (int, float)):
                            # Applica variazione numerica
                            range_min = rules.get(param, {}).get('min', value * 0.5)
                            range_max = rules.get(param, {}).get('max', value * 1.5)
                            params[param] = random.uniform(range_min, range_max)
                        else:
                            # Parametro non numerico, usa valori permessi
                            allowed = rules.get(param, {}).get('values', [value])
                            params[param] = random.choice(allowed)
                            
                # Aggiorna parametri
                gene.parameters = json.dumps(params)
                
                # Aggiorna storia mutazioni
                history = json.loads(gene.mutation_history or '{}')
                history[datetime.now().isoformat()] = {
                    'type': 'parameters',
                    'params': params
                }
                gene.mutation_history = json.dumps(history)
                
    def _generate_random_parameters(self, gene_type: str) -> str:
        """
        Genera parametri casuali per un tipo di gene.
        
        Args:
            gene_type: Tipo di gene
            
        Returns:
            str: Parametri in formato JSON
        """
        # Ottieni configurazione gene
        gene_config = self.config['gene'].get(gene_type, {})
        default_params = gene_config.get('default', {})
        
        # Genera parametri casuali basati sui default
        params = {}
        for param, value in default_params.items():
            if isinstance(value, (int, float)):
                # Varia del ±50% dal default
                params[param] = random.uniform(value * 0.5, value * 1.5)
            else:
                params[param] = value
                
        return json.dumps(params)
        
    def _update_mutation_stats(self, population: Population, stats: Dict) -> None:
        """
        Aggiorna statistiche mutazione nella storia evolutiva.
        
        Args:
            population: Popolazione
            stats: Statistiche mutazioni
        """
        history = self.session.query(EvolutionHistory)\
            .filter_by(
                population_id=population.population_id,
                generation=population.current_generation
            ).first()
            
        if history:
            history.mutation_stats = json.dumps(stats)
            self.session.commit()
