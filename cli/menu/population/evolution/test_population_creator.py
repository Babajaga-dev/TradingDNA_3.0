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

from sqlalchemy.orm import Session
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
        print("[DEBUG] TestPopulationCreator inizializzato")
        
    def _load_test_config(self) -> Dict:
        """
        Carica la configurazione dei test.
        
        Returns:
            Dict: Configurazione test
        """
        try:
            print("[DEBUG] Caricamento configurazione test")
            with open('config/test.yaml', 'r') as f:
                config = yaml.safe_load(f)
            print("[DEBUG] Configurazione test caricata con successo")
            return config['evolution_test']
        except Exception as e:
            print(f"[DEBUG] ERRORE caricamento configurazione: {str(e)}")
            logger.error(f"Errore caricamento configurazione test: {str(e)}")
            raise
            
    def create_test_population(self, name: Optional[str] = None, session: Optional[Session] = None) -> Population:
        """
        Crea una popolazione per il testing.
        
        Args:
            name: Nome popolazione (opzionale)
            session: Sessione database esistente (opzionale)
            
        Returns:
            Population: Popolazione creata
        """
        try:
            print("[DEBUG] Avvio creazione popolazione test")
            # Se non viene fornita una sessione, ne crea una nuova
            if session is None:
                print("[DEBUG] Creazione nuova sessione database")
                with self.session_scope() as session:
                    return self._create_test_population_internal(name, session)
            else:
                # Usa la sessione fornita
                print("[DEBUG] Utilizzo sessione database esistente")
                return self._create_test_population_internal(name, session)
                
        except Exception as e:
            print(f"[DEBUG] ERRORE creazione popolazione: {str(e)}")
            logger.error(f"Errore creazione popolazione test: {str(e)}")
            raise

    def _create_test_population_internal(self, name: Optional[str], session: Session) -> Population:
        """
        Implementazione interna della creazione della popolazione.
        
        Args:
            name: Nome popolazione
            session: Sessione database attiva
            
        Returns:
            Population: Popolazione creata
        """
        # Usa nome default se non specificato
        if not name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"test_population_{timestamp}"
            
        print(f"[DEBUG] Creazione popolazione '{name}'")
        logger.info(f"Creazione popolazione test '{name}'")
        
        # Crea popolazione con parametri da config
        print("[DEBUG] Configurazione parametri popolazione")
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
        print("[DEBUG] Ricerca symbol BTCUSDT")
        symbol = session.query(Symbol)\
            .filter_by(name='BTCUSDT')\
            .first()
        if not symbol:
            print("[DEBUG] ERRORE: Symbol BTCUSDT non trovato!")
            raise ValueError("Symbol BTCUSDT non trovato")
        population.symbol_id = symbol.id
        print(f"[DEBUG] Symbol trovato con ID {symbol.id}")
        
        # Salva popolazione
        print("[DEBUG] Salvataggio popolazione nel database")
        session.add(population)
        session.flush()
        print(f"[DEBUG] Popolazione salvata con ID {population.population_id}")
        
        # Inizializza popolazione con i cromosomi
        print("[DEBUG] Avvio inizializzazione cromosomi")
        self._initialize_population(population, session)
        
        print(f"[DEBUG] Popolazione '{name}' creata con successo")
        logger.info(f"Popolazione test '{name}' creata con successo")
        return population
            
    def _initialize_population(self, population: Population, session: Session) -> None:
        """
        Inizializza una popolazione con cromosomi di test.
        
        Args:
            population: Popolazione da inizializzare
            session: Sessione database attiva
        """
        try:
            print(f"[DEBUG] Inizio inizializzazione popolazione {population.name}")
            # Crea cromosomi iniziali
            for i in range(population.max_size):
                print(f"[DEBUG] Creazione cromosoma {i+1}/{population.max_size}")
                chromosome = self._create_test_chromosome(population)
                session.add(chromosome)
                session.flush()
                print(f"[DEBUG] Cromosoma {i+1} creato con ID {chromosome.chromosome_id}")
                
                print(f"[DEBUG] Aggiunta geni al cromosoma {chromosome.chromosome_id}")
                self._add_genes_to_chromosome(chromosome, session)
                print(f"[DEBUG] Geni aggiunti al cromosoma {chromosome.chromosome_id}")
                
            print(f"[DEBUG] Popolazione {population.name} inizializzata con {population.max_size} cromosomi")
            logger.info(f"Popolazione {population.name} inizializzata con {population.max_size} cromosomi")
            
        except Exception as e:
            print(f"[DEBUG] ERRORE inizializzazione popolazione: {str(e)}")
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
        try:
            print("[DEBUG] Creazione nuovo cromosoma di test")
            # Crea cromosoma base
            timestamp = datetime.now().isoformat()
            random_seed = str(hash(timestamp))
            fingerprint = hashlib.sha256(f"{timestamp}{random_seed}".encode()).hexdigest()
            
            # Assicurati che population_id sia impostato
            if not population.population_id:
                print("[DEBUG] ERRORE: Population ID non disponibile!")
                raise ValueError("Population ID non disponibile")
                
            chromosome = Chromosome(
                population_id=population.population_id,
                generation=0,
                fingerprint=fingerprint,
                status='active',
                performance_metrics=json.dumps({'fitness': 0.0}),
                weight_distribution=json.dumps({})
            )
            
            print(f"[DEBUG] Cromosoma creato con fingerprint {fingerprint[:8]}...")
            return chromosome
            
        except Exception as e:
            print(f"[DEBUG] ERRORE creazione cromosoma: {str(e)}")
            logger.error(f"Errore creazione cromosoma test: {str(e)}")
            raise

    def _add_genes_to_chromosome(self, chromosome: Chromosome, session: Session) -> None:
        """
        Aggiunge i geni a un cromosoma.
        
        Args:
            chromosome: Cromosoma a cui aggiungere i geni
            session: Sessione database attiva
        """
        try:
            print(f"[DEBUG] Inizio aggiunta geni al cromosoma {chromosome.chromosome_id}")
            # Ottieni lista geni dalla configurazione
            available_genes = [gene_type for gene_type in self.config['gene'].keys() if gene_type != 'base']
            print(f"[DEBUG] Geni disponibili: {available_genes}")
            
            # Aggiungi geni con parametri di test
            for gene_type in available_genes:
                print(f"[DEBUG] Aggiunta gene {gene_type}")
                gene = ChromosomeGene(
                    chromosome_id=chromosome.chromosome_id,
                    gene_type=gene_type,
                    parameters=json.dumps(self.config['gene'][gene_type]['default']),
                    weight=0.5,  # Peso uniforme per il test
                    is_active=True,
                    mutation_history=json.dumps({}),
                    validation_rules=json.dumps(self.config['gene'][gene_type].get('constraints', {}))
                )
                session.add(gene)
                print(f"[DEBUG] Gene {gene_type} aggiunto con successo")
                
        except Exception as e:
            print(f"[DEBUG] ERRORE aggiunta geni: {str(e)}")
            logger.error(f"Errore aggiunta geni al cromosoma: {str(e)}")
            raise
