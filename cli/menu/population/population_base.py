"""
Population Base Manager
---------------------
Classe base per la gestione delle popolazioni di trading.
"""

from typing import Dict, Optional, List, TypeVar, Type
from pathlib import Path
import yaml
import time
import random
from contextlib import contextmanager

from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from data.database.session_manager import DBSessionManager
from data.database.models.population_models import Population
from cli.menu.menu_utils import get_user_input
from cli.logger.log_manager import get_logger

# Setup logger
logger = get_logger('population_base')

# Type variable per oggetti del modello
T = TypeVar('T')

# Configurazione retry
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 0.1
MAX_RETRY_DELAY = 2.0

class PopulationBaseManager:
    """Classe base per la gestione delle popolazioni."""
    
    def __init__(self):
        """Inizializza il population manager."""
        
        self.db = DBSessionManager()
        self.config = self._load_configs()
        
        
    @contextmanager
    def session_scope(self):
        """
        Context manager per la gestione delle sessioni.
        Usa il DBSessionManager centralizzato.
        """
        
        with self.db.session() as session:
            yield session
            
            
    def get_population(self, population_id: int, session: Optional[Session] = None) -> Optional[Population]:
        """
        Ottiene una popolazione dal database.
        
        Args:
            population_id: ID della popolazione
            session: Sessione database opzionale
            
        Returns:
            Optional[Population]: Popolazione trovata o None
        """
        try:

            if session is not None:
                
                population = session.get(Population, population_id)
                if not population:

                    return None

                return population
            else:
                
                with self.session_scope() as session:
                    population = session.get(Population, population_id)
                    if not population:

                        return None

                    return session.merge(population)
        except Exception as e:

            logger.error(f"Errore recupero popolazione {population_id}: {str(e)}")
            return None
            
    def safe_merge(self, obj: T, session: Optional[Session] = None) -> T:
        """
        Merge sicuro di un oggetto nella sessione corrente.
        
        Args:
            obj: Oggetto da mergere
            session: Sessione database opzionale
            
        Returns:
            T: Oggetto mergeto
        """
        if obj is None:
            
            return None
            
        

        
        # Se non viene fornita una sessione, usa quella corrente o creane una nuova
        if session is None:
            
            session = self.db._session_maker()
        
        retries = 0
        last_error = None
        delay = INITIAL_RETRY_DELAY
        
        while retries < MAX_RETRIES:
            try:

                
                # Verifica se l'oggetto è già nella sessione
                if obj in session:
                    
                    return obj
                
                # Esegui il merge con timeout
                start_time = time.time()
                merged = session.merge(obj)
                session.flush()  # Forza il flush per verificare eventuali errori
                merge_time = time.time() - start_time

                return merged
                
            except OperationalError as e:
                if "database is locked" in str(e):
                    last_error = e
                    retries += 1
                    if retries < MAX_RETRIES:

                        time.sleep(delay)
                        delay = min(delay * 2 + random.random(), MAX_RETRY_DELAY)
                        continue
                raise
                
            except Exception as e:

                logger.error(f"Errore durante merge: {str(e)}")
                raise
        

        logger.error(f"Max retry raggiunti durante merge: {str(last_error)}")
        raise last_error
            
    def _load_configs(self) -> Dict:
        """
        Carica le configurazioni dai file YAML.
        
        Returns:
            Dict: Configurazioni unificate
        """
        try:
            
            config_dir = Path('config')
            
            with open(config_dir / 'population.yaml', 'r') as f:
                population_config = yaml.safe_load(f)
                
            with open(config_dir / 'portfolio.yaml', 'r') as f:
                portfolio_config = yaml.safe_load(f)
                
            with open(config_dir / 'logging.yaml', 'r') as f:
                logging_config = yaml.safe_load(f)
                
            with open(config_dir / 'gene.yaml', 'r') as f:
                gene_config = yaml.safe_load(f)
                
            # Unifica configurazioni
            config = {
                'population': population_config,
                'portfolio': portfolio_config['portfolio'],
                'system': logging_config['system'],
                'gene': gene_config['gene']
            }
            
            
            return config
            
        except Exception as e:

            logger.error(f"Errore caricamento configurazioni: {str(e)}")
            raise
          
    def list_populations(self) -> List[Dict]:
        """
        Lista tutte le popolazioni esistenti.
        
        Returns:
            List[Dict]: Lista di popolazioni con informazioni base
        """
        try:
            
            with self.session_scope() as session:
                populations = session.query(Population).all()
                
                result = []
                for pop in populations:
                    result.append({
                        'ID': pop.population_id,
                        'Nome': pop.name,
                        'Generazione': pop.current_generation,
                        'Dimensione': pop.max_size,
                        'Status': pop.status,
                        'Performance': f"{pop.performance_score:.2f}",
                        'Diversità': f"{pop.diversity_score:.2f}",
                        'Timeframe': pop.timeframe,
                        'Creazione': pop.created_at.strftime(self.config['population']['display']['date_format'])
                    })
                    

                return result
                
        except Exception as e:

            logger.error(f"Errore lista popolazioni: {str(e)}")
            return []
            
    def _validate_population_params(self, params: Dict) -> bool:
        """
        Valida i parametri di una popolazione.
        
        Args:
            params: Parametri da validare
            
        Returns:
            bool: True se validi, False altrimenti
        """
        try:
            config = self.config['population']
            
            # Valida dimensione
            if not (config['population_size']['min'] <= params['max_size'] <= config['population_size']['max']):
                return False
                
            # Valida mutation rate
            if not (config['evolution']['mutation_rate']['min'] <= params['mutation_rate'] <= config['evolution']['mutation_rate']['max']):
                return False
                
            # Valida selection pressure
            if not (config['evolution']['selection_pressure']['min'] <= params['selection_pressure'] <= config['evolution']['selection_pressure']['max']):
                return False
                
            # Valida generation interval
            if not (config['evolution']['generation_interval']['min'] <= params['generation_interval'] <= config['evolution']['generation_interval']['max']):
                return False
                
            # Valida diversity threshold
            if not (config['evolution']['diversity_threshold']['min'] <= params['diversity_threshold'] <= config['evolution']['diversity_threshold']['max']):
                return False
                
            return True
            
        except Exception as e:

            logger.error(f"Errore validazione parametri: {str(e)}")
            return False
            
    def _get_display_format(self, key: str) -> str:
        """
        Ottiene il formato di visualizzazione.
        
        Args:
            key: Chiave del formato
            
        Returns:
            str: Formato di visualizzazione
        """
        return self.config['population']['display'].get(key, '')
        
    def _get_table_columns(self) -> list:
        """
        Ottiene le colonne per la visualizzazione tabellare.
        
        Returns:
            list: Lista colonne
        """
        return self.config['population']['display']['table_columns']
