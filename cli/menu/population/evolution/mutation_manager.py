"""
Mutation Manager
-------------
Gestione delle mutazioni genetiche.
"""

from typing import List, Dict, Union
import random
import json
from datetime import datetime
import time

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from data.database.models.population_models import (
    Population, Chromosome, ChromosomeGene, EvolutionHistory
)
from cli.menu.population.population_base import PopulationBaseManager
from cli.logger.log_manager import get_logger

# Setup logger
logger = get_logger('mutation_manager')

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

def ensure_json_dict(value: Union[str, Dict, None]) -> Dict:
    """Converte una stringa JSON o un dizionario in un dizionario."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}

def ensure_json_string(value: Union[str, Dict, None]) -> str:
    """Converte un dizionario o una stringa JSON in una stringa JSON."""
    if value is None:
        return '{}'
    if isinstance(value, str):
        try:
            # Verifica che sia un JSON valido
            json.loads(value)
            return value
        except json.JSONDecodeError:
            return '{}'
    try:
        return json.dumps(value)
    except TypeError:
        return '{}'

class MutationManager(PopulationBaseManager):
    """Gestisce le mutazioni dei cromosomi."""
    
    @retry_on_db_lock
    def mutate_population(self, population: Population, chromosomes: List[Chromosome], session: Session) -> List[Chromosome]:
        """
        Applica mutazioni a una lista di cromosomi.
        
        Args:
            population: Popolazione di appartenenza
            chromosomes: Lista di cromosomi da mutare
            session: Sessione database attiva
            
        Returns:
            List[Chromosome]: Cromosomi mutati
        """
        try:
            # Ricarica popolazione nella sessione corrente
            population = session.merge(population)
            
            mutation_stats = {
                "total": len(chromosomes),
                "mutated": 0,
                "gene_mutations": 0,
                "weight_mutations": 0,
                "parameter_mutations": 0
            }
            
            # Processa cromosomi in batch
            batch_size = 50
            for i in range(0, len(chromosomes), batch_size):
                batch = chromosomes[i:i + batch_size]
                
                for chromosome in batch:
                    # Merge del cromosoma nella sessione corrente
                    chromosome = session.merge(chromosome)
                    
                    if random.random() < population.mutation_rate:
                        self._mutate_chromosome(chromosome, session)
                        mutation_stats["mutated"] += 1
                        
                        # Aggiorna statistiche
                        mutation_stats["gene_mutations"] += len(chromosome.genes)
                        mutation_stats["weight_mutations"] += sum(
                            1 for g in chromosome.genes if g.last_mutation_date
                        )
                        mutation_stats["parameter_mutations"] += sum(
                            1 for g in chromosome.genes 
                            if ensure_json_dict(g.mutation_history)
                        )
                
                # Commit intermedio dopo ogni batch
                session.commit()
            
            # Log mutazioni
            logger.info(
                f"Mutati {mutation_stats['mutated']}/{mutation_stats['total']} "
                f"cromosomi con rate {population.mutation_rate}"
            )
            
            # Aggiorna statistiche popolazione
            self._update_mutation_stats(population, mutation_stats, session)
            
            return chromosomes
            
        except Exception as e:
            logger.error(f"Errore mutazione popolazione: {str(e)}")
            raise
            
    def _mutate_chromosome(self, chromosome: Chromosome, session: Session) -> None:
        """
        Applica mutazioni a un singolo cromosoma.
        
        Args:
            chromosome: Cromosoma da mutare
            session: Sessione database attiva
        """
        # Decidi tipo di mutazione
        mutation_type = random.choice([
            'add_gene',
            'remove_gene',
            'modify_weights',
            'modify_parameters'
        ])
        
        if mutation_type == 'add_gene':
            self._add_random_gene(chromosome, session)
        elif mutation_type == 'remove_gene':
            self._remove_random_gene(chromosome, session)
        elif mutation_type == 'modify_weights':
            self._mutate_weights(chromosome)
        else:
            self._mutate_parameters(chromosome)
            
        # Aggiorna timestamp mutazione
        for gene in chromosome.genes:
            gene.last_mutation_date = datetime.now()
            
    def _add_random_gene(self, chromosome: Chromosome, session: Session) -> None:
        """
        Aggiunge un nuovo gene casuale al cromosoma.
        
        Args:
            chromosome: Cromosoma da modificare
            session: Sessione database attiva
        """
        # Lista geni disponibili
        available_genes = set(self.config['gene'].keys()) - \
                         set(g.gene_type for g in chromosome.genes)
        
        if available_genes:
            gene_type = random.choice(list(available_genes))
            
            # Crea nuovo gene con peso tra 0.1 e 5.0
            new_gene = ChromosomeGene(
                chromosome_id=chromosome.chromosome_id,
                gene_type=gene_type,
                parameters=self._generate_random_parameters(gene_type),
                weight=random.uniform(0.1, 5.0),  # Genera peso nel range valido
                is_active=True,
                mutation_history=json.dumps({"added": datetime.now().isoformat()})
            )
            
            session.add(new_gene)
            session.flush()
            
    def _remove_random_gene(self, chromosome: Chromosome, session: Session) -> None:
        """
        Rimuove un gene casuale dal cromosoma.
        
        Args:
            chromosome: Cromosoma da modificare
            session: Sessione database attiva
        """
        if chromosome.genes:
            gene = random.choice(chromosome.genes)
            session.delete(gene)
            session.flush()
            
    def _mutate_weights(self, chromosome: Chromosome) -> None:
        """
        Muta i pesi dei geni.
        
        Args:
            chromosome: Cromosoma da modificare
        """
        for gene in chromosome.genes:
            if random.random() < 0.3:  # 30% chance per gene
                # Applica piccola variazione mantenendo il peso tra 0.1 e 5.0
                delta = random.uniform(-0.5, 0.5)
                new_weight = gene.weight + delta
                gene.weight = max(0.1, min(5.0, new_weight))
                
                # Aggiorna storia mutazioni
                history = ensure_json_dict(gene.mutation_history)
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
                params = ensure_json_dict(gene.parameters)
                rules = ensure_json_dict(gene.validation_rules)
                
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
                history = ensure_json_dict(gene.mutation_history)
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
        
    @retry_on_db_lock
    def _update_mutation_stats(self, population: Population, stats: Dict, session: Session) -> None:
        """
        Aggiorna statistiche mutazione nella storia evolutiva.
        
        Args:
            population: Popolazione
            stats: Statistiche mutazioni
            session: Sessione database attiva
        """
        history = session.query(EvolutionHistory)\
            .filter_by(
                population_id=population.population_id,
                generation=population.current_generation
            ).first()
            
        if history:
            history.mutation_stats = json.dumps(stats)
            session.flush()
