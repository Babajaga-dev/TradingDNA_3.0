"""
Test Population Creator
--------------------
Creazione di popolazioni per il testing del sistema di evoluzione.
"""

import json
import hashlib
from typing import Dict, Optional
import yaml
from datetime import datetime
from contextlib import contextmanager

from data.database.models.population_models import (
    Population, Chromosome, ChromosomeGene
)
from data.database.models.models import Symbol
from cli.menu.population.population_base import PopulationBaseManager
from cli.logger.log_manager import get_logger

# Setup logger
logger = get_logger('test_population_creator')

class TestPopulationCreator(PopulationBaseManager):
    """Crea popolazioni per il testing."""
    
    def __init__(self):
        """Inizializza il creator."""
        super().__init__()
        self.test_config = self._load_test_config()
        
    @contextmanager
    def transaction(self):
        """Context manager per gestire le transazioni."""
        try:
            yield
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise e
        
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
            logger.error(f"Errore caricamento configurazione test: {str(e)}")
            raise
            
    def create_test_population(self, name: Optional[str] = None) -> Population:
        """
        Crea una popolazione per il testing.
        
        Args:
            name: Nome popolazione (opzionale)
            
        Returns:
            Population: Popolazione creata
        """
        try:
            with self.transaction():
                # Usa nome default se non specificato
                if not name:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    name = f"test_population_{timestamp}"
                    
                logger.info(f"Creazione popolazione test '{name}'")
                
                # Crea popolazione con parametri da config
                population = Population(
                    name=name,
                    max_size=self.test_config['population_size']['default'],
                    current_generation=0,
                    status='active',
                    diversity_score=1.0,
                    performance_score=0.0,
                    mutation_rate=self.test_config['mutation_rate'],
                    selection_pressure=self.test_config['selection_pressure'],
                    generation_interval=self.test_config['generation_interval'],
                    diversity_threshold=self.test_config['diversity_threshold'],
                    timeframe=self.test_config['test_timeframe']
                )
                
                # Ottieni symbol_id per il test
                symbol = self.session.query(Symbol)\
                    .filter_by(name='BTCUSDT')\
                    .first()
                if not symbol:
                    raise ValueError("Symbol BTCUSDT non trovato")
                population.symbol_id = symbol.id
                
                # Salva popolazione e fai flush per ottenere l'ID
                self.session.add(population)
                self.session.flush()
                
                # Inizializza popolazione con i cromosomi
                self._initialize_population(population)
                
                logger.info(f"Popolazione test '{name}' creata con successo")
                return population
                
        except Exception as e:
            logger.error(f"Errore creazione popolazione test: {str(e)}")
            raise
            
    def _initialize_population(self, population: Population) -> None:
        """
        Inizializza una popolazione con cromosomi di test.
        
        Args:
            population: Popolazione da inizializzare
        """
        try:
            # Crea cromosomi iniziali
            for _ in range(population.max_size):
                chromosome = self._create_test_chromosome(population)
                self.session.add(chromosome)
                
            logger.info(f"Popolazione {population.name} inizializzata con {population.max_size} cromosomi")
            
        except Exception as e:
            logger.error(f"Errore inizializzazione popolazione: {str(e)}")
            raise
            
    def _create_test_chromosome(self, population: Population) -> Chromosome:
        """
        Crea un cromosoma di test.
        
        Args:
            population: Popolazione di appartenenza
            
        Returns:
            Chromosome: Cromosoma creato
        """
        # Ottieni lista geni dalla configurazione
        available_genes = [gene_type for gene_type in self.config['gene'].keys() if gene_type != 'base']
        
        # Crea cromosoma base
        timestamp = datetime.now().isoformat()
        random_seed = str(hash(timestamp))
        fingerprint = hashlib.sha256(f"{timestamp}{random_seed}".encode()).hexdigest()
        
        # Assicurati che population_id sia impostato
        if not population.population_id:
            raise ValueError("Population ID non disponibile")
            
        chromosome = Chromosome(
            population_id=population.population_id,  # Usa l'ID della popolazione
            generation=0,
            fingerprint=fingerprint,
            status='active',
            performance_metrics=json.dumps({'fitness': 0.0}),  # Inizializza metriche
            weight_distribution=json.dumps({})  # Inizializza distribuzione pesi
        )
        
        # Aggiungi geni con parametri di test
        for gene_type in available_genes:
            gene = ChromosomeGene(
                gene_type=gene_type,
                parameters=json.dumps(self.config['gene'][gene_type]['default']),
                weight=0.5,  # Peso uniforme per il test
                is_active=True,
                mutation_history=json.dumps({}),  # Inizializza storia mutazioni
                validation_rules=json.dumps(self.config['gene'][gene_type].get('constraints', {}))
            )
            chromosome.genes.append(gene)
            
        return chromosome
