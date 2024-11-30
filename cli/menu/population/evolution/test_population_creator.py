"""
Test Population Creator
--------------------
Creazione di popolazioni per il testing del sistema di evoluzione.
"""

import json
import hashlib
from typing import Dict, Optional, List
import yaml
from datetime import datetime

from sqlalchemy import text, select
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
        """Carica la configurazione dei test."""
        try:
            print("[DEBUG] Caricamento configurazione test")
            with open('config/test.yaml', 'r') as f:
                config = yaml.safe_load(f)
            print("[DEBUG] Configurazione test caricata con successo")
            return config['evolution_test']
        except Exception as e:
            logger.error(f"Errore caricamento configurazione test: {str(e)}")
            raise
            
    def create_test_population(self, name: Optional[str] = None, session: Optional[Session] = None) -> Population:
        """Crea una popolazione per il testing."""
        try:
            print("[DEBUG] Avvio creazione popolazione test")
            if session is None:
                with self.session_scope() as session:
                    return self._create_test_population_internal(name, session)
            else:
                return self._create_test_population_internal(name, session)
                
        except Exception as e:
            logger.error(f"Errore creazione popolazione test: {str(e)}")
            raise

    def _create_test_population_internal(self, name: Optional[str], session: Session) -> Population:
        """Implementazione interna della creazione della popolazione."""
        try:
            if not name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                name = f"test_population_{timestamp}"
                
            # Ottieni symbol usando una query nativa PostgreSQL
            symbol_result = session.execute(text("""
                SELECT id FROM symbols 
                WHERE name = :symbol_name 
                LIMIT 1
                FOR UPDATE
            """), {"symbol_name": "BTCUSDT"})
            
            symbol_data = symbol_result.fetchone()
            if not symbol_data:
                print("[DEBUG] ERRORE: Symbol BTCUSDT non trovato!")
                raise ValueError("Symbol BTCUSDT non trovato")
            
            symbol_id = symbol_data[0]
            
            # Crea popolazione usando INSERT ... RETURNING
            population_result = session.execute(text("""
                INSERT INTO populations (
                    name, max_size, current_generation, status, 
                    diversity_score, performance_score, mutation_rate,
                    selection_pressure, generation_interval, 
                    diversity_threshold, timeframe, symbol_id,
                    created_at, updated_at
                ) VALUES (
                    :name, :max_size, 0, 'active',
                    1.0, 0.0, :mutation_rate,
                    :selection_pressure, :generation_interval,
                    :diversity_threshold, :timeframe, :symbol_id,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                RETURNING population_id, name, max_size, symbol_id
            """), {
                "name": name,
                "max_size": self.test_config['population_size']['default'],
                "mutation_rate": self.test_config['mutation_rate'],
                "selection_pressure": self.test_config['selection_pressure'],
                "generation_interval": self.test_config['generation_interval'],
                "diversity_threshold": self.test_config['diversity_threshold'],
                "timeframe": self.test_config['test_timeframe'],
                "symbol_id": symbol_id
            })
            
            population_data = population_result.fetchone()
            if not population_data:
                raise ValueError("Errore creazione popolazione")
                
            population_id = population_data[0]
            
            # Crea cromosomi in batch
            self._create_chromosomes_batch(population_id, session)
            
            # Recupera la popolazione completa
            population = session.execute(
                select(Population).where(Population.population_id == population_id)
            ).scalar_one()
            
            return population
            
        except Exception as e:
            logger.error(f"Errore in create_test_population_internal: {str(e)}")
            session.rollback()
            raise
            
    def _create_chromosomes_batch(self, population_id: int, session: Session) -> None:
        """Crea cromosomi in batch usando PostgreSQL."""
        try:
            # Crea cromosomi
            chromosomes_values = []
            for i in range(self.test_config['population_size']['default']):
                timestamp = datetime.now().isoformat()
                fingerprint = hashlib.sha256(f"{timestamp}{i}".encode()).hexdigest()
                chromosomes_values.append(
                    f"({population_id}, '{fingerprint}', 0, 'active', "
                    f"'{json.dumps({'fitness': 0.0})}', '{json.dumps({})}')"
                )
            
            # Inserisci cromosomi in batch
            chromosomes_sql = text(f"""
                INSERT INTO chromosomes (
                    population_id, fingerprint, generation, status,
                    performance_metrics, weight_distribution
                )
                VALUES {','.join(chromosomes_values)}
                RETURNING chromosome_id;
            """)
            
            result = session.execute(chromosomes_sql)
            chromosome_ids = [row[0] for row in result]
            
            # Carica configurazione geni
            with open('config/gene.yaml', 'r') as f:
                gene_config = yaml.safe_load(f)['gene']
            
            # Prepara i dati dei geni
            genes_values = []
            base_risk_factor = gene_config['base']['risk_factor']
            
            for chromosome_id in chromosome_ids:
                for gene_type, config in gene_config.items():
                    if gene_type != 'base':
                        # Ottieni il risk_factor specifico del gene o usa quello base
                        risk_factor = config['default'].get('risk_factor', base_risk_factor)
                        # Rimuovi risk_factor dai parametri poiché è una colonna separata
                        params = config['default'].copy()
                        if 'risk_factor' in params:
                            del params['risk_factor']
                            
                        genes_values.append(
                            f"({chromosome_id}, '{gene_type}', "
                            f"'{json.dumps(params)}', 0.5, true, "
                            f"{risk_factor}, "  # Aggiunto risk_factor
                            f"'{json.dumps({})}', '{json.dumps(config['constraints'])}')"
                        )
            
            # Inserisci geni in batch
            if genes_values:
                genes_sql = text(f"""
                    INSERT INTO chromosome_genes (
                        chromosome_id, gene_type, parameters, weight,
                        is_active, risk_factor, mutation_history, validation_rules
                    )
                    VALUES {','.join(genes_values)};
                """)
                session.execute(genes_sql)
            
            session.flush()
            
        except Exception as e:
            logger.error(f"Errore creazione batch: {str(e)}")
            session.rollback()
            raise
