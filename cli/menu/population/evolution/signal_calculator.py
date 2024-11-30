"""
Signal Calculator
--------------
Calcolo dei segnali di trading dai geni.
"""

from typing import Dict, List, Optional, Union, Tuple
import time
import random
import json
import numpy as np
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, selectinload

from data.database.models.population_models import Chromosome, ChromosomeGene
from data.database.models.models import MarketData
from cli.menu.population.population_base import PopulationBaseManager
from cli.logger.log_manager import get_logger

# Import dei geni
from cli.genes.rsi_gene import RSIGene
from cli.genes.macd_gene import MACDGene
from cli.genes.moving_average_gene import MovingAverageGene
from cli.genes.bollinger_gene import BollingerGene
from cli.genes.stochastic_gene import StochasticGene
from cli.genes.atr_gene import ATRGene

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
                #print(f"[DEBUG] Tentativo {attempt+1}/{MAX_RETRIES} di esecuzione {func.__name__}")
                return func(*args, **kwargs)
            except OperationalError as e:
                if "database is locked" in str(e):
                    last_error = e
                    if attempt < MAX_RETRIES - 1:
                        #print(f"[DEBUG] Database LOCKED in {func.__name__}! Retry {attempt+1}/{MAX_RETRIES} dopo {delay:.1f}s")
                        logger.warning(f"Database locked, retry {attempt+1}/{MAX_RETRIES} dopo {delay:.1f}s")
                        time.sleep(delay)
                        delay = min(delay * 2 + random.random(), MAX_RETRY_DELAY)
                        continue
                raise
        #print(f"[DEBUG] MAX RETRY RAGGIUNTI per {func.__name__}! Ultimo errore: {str(last_error)}")
        logger.error(f"Max retries ({MAX_RETRIES}) raggiunti per database lock")
        raise last_error
    return wrapper

class SignalCalculator(PopulationBaseManager):
    """Calcola i segnali di trading dai geni."""
    
    def __init__(self):
        """Inizializza il calculator."""
        super().__init__()
        # Mappa dei tipi di gene alle loro classi
        self.gene_classes = {
            'rsi': RSIGene,
            'macd': MACDGene,
            'moving_average': MovingAverageGene,
            'bollinger': BollingerGene,
            'stochastic': StochasticGene,
            'atr': ATRGene
        }
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

    def _prepare_market_data(self, market_data: List[Union[MarketData, Dict]]) -> Tuple[Dict[str, np.ndarray], List]:
        """
        Converte i dati di mercato in array numpy OHLCV.
        
        Args:
            market_data: Lista di dati di mercato
            
        Returns:
            Tuple[Dict[str, np.ndarray], List]: Dizionario con array OHLCV e lista timestamp
        """
        try:
            print("[DEBUG] Preparazione dati di mercato OHLCV...")
            
            # Inizializza liste per ogni tipo di dato
            opens = []
            highs = []
            lows = []
            closes = []
            volumes = []
            timestamps = []
            
            for data in market_data:
                if isinstance(data, dict):
                    opens.append(float(data['open']))
                    highs.append(float(data['high']))
                    lows.append(float(data['low']))
                    closes.append(float(data['close']))
                    volumes.append(float(data['volume']))
                    timestamps.append(data['timestamp'])
                else:
                    opens.append(float(data.open))
                    highs.append(float(data.high))
                    lows.append(float(data.low))
                    closes.append(float(data.close))
                    volumes.append(float(data.volume))
                    timestamps.append(data.timestamp)
                    
            # Converti in numpy arrays
            ohlcv_data = {
                'open': np.array(opens, dtype=float),
                'high': np.array(highs, dtype=float),
                'low': np.array(lows, dtype=float),
                'close': np.array(closes, dtype=float),
                'volume': np.array(volumes, dtype=float)
            }
            
            #print(f"[DEBUG] Convertiti {len(closes)} candele in array OHLCV")
            
            return ohlcv_data, timestamps
            
        except Exception as e:
            #print(f"[DEBUG] ERRORE preparazione dati: {str(e)}")
            return {}, []

    def _create_gene_instance(self, gene: ChromosomeGene) -> Optional[object]:
        """
        Crea un'istanza del gene dai parametri salvati.
        
        Args:
            gene: Gene del cromosoma
            
        Returns:
            Optional[object]: Istanza del gene o None se errore
        """
        try:
            # Ottieni la classe del gene
            gene_class = self.gene_classes.get(gene.gene_type)
            if not gene_class:
                #print(f"[DEBUG] Tipo gene non riconosciuto: {gene.gene_type}")
                return None
                
            # Carica i parametri dal JSON
            try:
                params = json.loads(gene.parameters) if gene.parameters else {}
            except json.JSONDecodeError:
                #print(f"[DEBUG] Errore decodifica parametri per gene {gene.gene_type}")
                return None
                
            # Verifica parametri minimi necessari
            if not self._validate_gene_params(gene.gene_type, params):
                #print(f"[DEBUG] Parametri mancanti per gene {gene.gene_type}")
                return None
                
            # Crea e restituisci l'istanza
            return gene_class(params)
            
        except Exception as e:
            #print(f"[DEBUG] ERRORE creazione istanza gene: {str(e)}")
            return None
            
    def _validate_gene_params(self, gene_type: str, params: Dict) -> bool:
        """
        Verifica che i parametri necessari siano presenti.
        
        Args:
            gene_type: Tipo di gene
            params: Parametri del gene
            
        Returns:
            bool: True se i parametri sono validi
        """
        required_params = {
            'rsi': ['period', 'overbought', 'oversold'],
            'macd': ['fast_period', 'slow_period', 'signal_period'],
            'moving_average': ['period', 'type', 'distance'],  # Corretto per MovingAverageGene
            'bollinger': ['period', 'std_dev'],
            'stochastic': ['k_period', 'd_period', 'smooth_k', 'overbought', 'oversold'],
            'atr': ['period', 'multiplier']
        }
        
        # Verifica parametri richiesti
        for param in required_params.get(gene_type, []):
            if param not in params:
                #print(f"[DEBUG] Parametro mancante '{param}' per gene {gene_type}")
                return False
                
        return True
        
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
            #print(f"[DEBUG] Inizio calcolo segnali per cromosoma {chromosome.chromosome_id}")
            
            # Ricarica il cromosoma con le sue relazioni
            if session is not None:
                print("[DEBUG] Ricaricamento cromosoma con relazioni...")
                chromosome = self._get_chromosome(chromosome.chromosome_id, session)
                if not chromosome:
                    raise ValueError(f"Cromosoma {chromosome.chromosome_id} non trovato")
            
            # Prepara i dati di mercato
            ohlcv_data, timestamps = self._prepare_market_data(market_data)
            if not ohlcv_data:
                print("[DEBUG] Nessun dato di mercato valido")
                return {}
            
            # Filtra solo i geni attivi
            active_genes = [g for g in chromosome.genes if g and g.is_active]
            total_genes = len(active_genes)
            
            #print(f"[DEBUG] Numero di geni attivi da elaborare: {total_genes}")
            #print(f"[DEBUG] Numero di candele disponibili: {len(ohlcv_data['close'])}")
            
            # Processa i geni in batch
            for i in range(0, total_genes, GENE_BATCH_SIZE):
                batch = active_genes[i:i + GENE_BATCH_SIZE]
                print(f"\n[DEBUG] Processing batch di geni {i+1}-{min(i+GENE_BATCH_SIZE, total_genes)}")
                
                # Calcola segnali per il batch corrente
                batch_signals = self._calculate_batch_signals(batch, ohlcv_data, timestamps)
                
                # Combina i segnali pesati del batch
                #print(f"[DEBUG] Combinazione segnali pesati per il batch...")
                for gene_signals in batch_signals:
                    for timestamp, signal in gene_signals.items():
                        if timestamp not in signals:
                            signals[timestamp] = 0.0
                        signals[timestamp] += signal
                
                # Flush periodico
                if session is not None:
                    print("[DEBUG] Flush sessione dopo batch")
                    session.flush()
                        
            #print(f"[DEBUG] Calcolo segnali completato: {len(signals)} segnali totali")
            return signals
            
        except Exception as e:
            #print(f"[DEBUG] ERRORE calcolo segnali: {str(e)}")
            logger.error(f"Errore calcolo segnali: {str(e)}")
            return {}
        
    def _calculate_batch_signals(
        self,
        genes: List[ChromosomeGene],
        ohlcv_data: Dict[str, np.ndarray],
        timestamps: List
    ) -> List[Dict]:
        """Calcola i segnali per un batch di geni."""
        batch_signals = []
        
        try:
            #print(f"[DEBUG] Calcolo segnali per batch di {len(genes)} geni")
            
            # Genera segnali per ogni gene nel batch
            for gene in genes:
                #print(f"[DEBUG] Calcolo segnali per gene {gene.gene_type}")
                
                # Crea istanza del gene
                gene_instance = self._create_gene_instance(gene)
                if not gene_instance:
                    #print(f"[DEBUG] Impossibile creare istanza per gene {gene.gene_type}")
                    continue
                
                # Calcola il segnale usando l'istanza del gene
                gene_signals = {}
                try:
                    signal = gene_instance.calculate_signal(ohlcv_data['close'])
                    
                    # Applica il peso del gene al segnale
                    weighted_signal = signal * gene.weight
                    
                    # Usa l'ultimo timestamp disponibile
                    if timestamps:
                        gene_signals[timestamps[-1]] = weighted_signal
                        
                    #print(f"[DEBUG] Generato segnale pesato {weighted_signal:.4f} per gene {gene.gene_type}")
                    
                except Exception as e:
                    #print(f"[DEBUG] Errore calcolo segnale per gene {gene.gene_type}: {str(e)}")
                    continue
                
                batch_signals.append(gene_signals)
            
            return batch_signals
            
        except Exception as e:
            #print(f"[DEBUG] ERRORE calcolo segnali batch: {str(e)}")
            logger.error(f"Errore calcolo segnali batch: {str(e)}")
            return []
