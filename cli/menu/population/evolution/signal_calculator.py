"""
Signal Calculator
--------------
Calcolo dei segnali di trading dai geni.
"""

from typing import Dict, List, Optional, Union
import time
import random
import numpy as np
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, selectinload

from data.database.models.population_models import Chromosome, ChromosomeGene
from data.database.models.models import MarketData
from cli.menu.population.population_base import PopulationBaseManager
from cli.logger.log_manager import get_logger

# Setup logger
logger = get_logger('signal_calculator')

# Configurazione retry
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 0.1
MAX_RETRY_DELAY = 2.0

# Dimensione batch per il processing dei geni
GENE_BATCH_SIZE = 5

def retry_on_db_lock(func):
    """Decorator per gestire i database lock con retry e backoff esponenziale."""
    def wrapper(*args, **kwargs):
        last_error = None
        delay = INITIAL_RETRY_DELAY
        
        for attempt in range(MAX_RETRIES):
            try:
                print(f"[DEBUG] Tentativo {attempt+1}/{MAX_RETRIES} di esecuzione {func.__name__}")
                return func(*args, **kwargs)
            except OperationalError as e:
                if "database is locked" in str(e):
                    last_error = e
                    if attempt < MAX_RETRIES - 1:
                        print(f"[DEBUG] Database LOCKED in {func.__name__}! Retry {attempt+1}/{MAX_RETRIES} dopo {delay:.1f}s")
                        logger.warning(f"Database locked, retry {attempt+1}/{MAX_RETRIES} dopo {delay:.1f}s")
                        time.sleep(delay)
                        delay = min(delay * 2 + random.random(), MAX_RETRY_DELAY)
                        continue
                raise
        print(f"[DEBUG] MAX RETRY RAGGIUNTI per {func.__name__}! Ultimo errore: {str(last_error)}")
        logger.error(f"Max retries ({MAX_RETRIES}) raggiunti per database lock")
        raise last_error
    return wrapper

class SignalCalculator(PopulationBaseManager):
    """Calcola i segnali di trading dai geni."""
    
    def __init__(self):
        """Inizializza il calculator."""
        super().__init__()
        print("[DEBUG] SignalCalculator inizializzato")
        
    def _get_chromosome(self, chromosome_id: int, session: Session) -> Optional[Chromosome]:
        """
        Carica un cromosoma con tutte le sue relazioni.
        
        Args:
            chromosome_id: ID del cromosoma
            session: Sessione database attiva
            
        Returns:
            Chromosome: Cromosoma caricato con relazioni
        """
        return (
            session.query(Chromosome)
            .options(
                selectinload(Chromosome.genes)
            )
            .filter(Chromosome.chromosome_id == chromosome_id)
            .first()
        )
        
    @retry_on_db_lock
    def calculate_signals(
        self, 
        chromosome: Chromosome, 
        market_data: List[Union[MarketData, Dict]],
        session: Optional[Session] = None
    ) -> Dict:
        """Calcola i segnali di trading per ogni gene."""
        signals = {}
        
        try:
            print(f"[DEBUG] Inizio calcolo segnali per cromosoma {chromosome.chromosome_id}")
            
            # Ricarica il cromosoma con le sue relazioni
            if session is not None:
                print("[DEBUG] Ricaricamento cromosoma con relazioni...")
                chromosome = self._get_chromosome(chromosome.chromosome_id, session)
                if not chromosome:
                    raise ValueError(f"Cromosoma {chromosome.chromosome_id} non trovato")
            
            # Filtra solo i geni attivi
            active_genes = [g for g in chromosome.genes if g and g.is_active]
            total_genes = len(active_genes)
            
            print(f"[DEBUG] Numero di geni attivi da elaborare: {total_genes}")
            print(f"[DEBUG] Numero di candele disponibili: {len(market_data)}")
            
            # Inizializza il generatore di numeri casuali una sola volta
            print(f"[DEBUG] Inizializzazione generatore numeri casuali...")
            rng = np.random.default_rng()
            
            # Processa i geni in batch
            for i in range(0, total_genes, GENE_BATCH_SIZE):
                batch = active_genes[i:i + GENE_BATCH_SIZE]
                print(f"\n[DEBUG] Processing batch di geni {i+1}-{min(i+GENE_BATCH_SIZE, total_genes)}")
                
                # Calcola segnali per il batch corrente
                batch_signals = self._calculate_batch_signals(batch, market_data, rng)
                
                # Combina i segnali pesati del batch
                print(f"[DEBUG] Combinazione segnali pesati per il batch...")
                for gene_signals in batch_signals:
                    for timestamp, signal in gene_signals.items():
                        if timestamp not in signals:
                            signals[timestamp] = 0.0
                        signals[timestamp] += signal
                
                # Flush periodico
                if session is not None:
                    print("[DEBUG] Flush sessione dopo batch")
                    session.flush()
                        
            print(f"[DEBUG] Calcolo segnali completato: {len(signals)} segnali totali")
            return signals
            
        except Exception as e:
            print(f"[DEBUG] ERRORE calcolo segnali: {str(e)}")
            logger.error(f"Errore calcolo segnali: {str(e)}")
            return {}
        
    def _calculate_batch_signals(
        self,
        genes: List[ChromosomeGene],
        market_data: List[Union[MarketData, Dict]],
        rng: np.random.Generator
    ) -> List[Dict]:
        """Calcola i segnali per un batch di geni."""
        batch_signals = []
        
        try:
            print(f"[DEBUG] Calcolo segnali per batch di {len(genes)} geni")
            
            # Pre-calcola i timestamp una sola volta
            timestamps = [
                data['timestamp'] if isinstance(data, dict) else data.timestamp 
                for data in market_data
            ]
            
            # Genera segnali per ogni gene nel batch
            for gene in genes:
                print(f"[DEBUG] Calcolo segnali per gene {gene.gene_type}")
                
                # Genera segnali uno alla volta invece che in batch
                gene_signals = {}
                for timestamp in timestamps:
                    # Genera un singolo segnale per ogni timestamp
                    signal = float(rng.uniform(-1, 1))
                    gene_signals[timestamp] = signal * gene.weight
                
                batch_signals.append(gene_signals)
                print(f"[DEBUG] Generati {len(gene_signals)} segnali pesati per gene {gene.gene_type}")
            
            return batch_signals
            
        except Exception as e:
            print(f"[DEBUG] ERRORE calcolo segnali batch: {str(e)}")
            logger.error(f"Errore calcolo segnali batch: {str(e)}")
            return []
