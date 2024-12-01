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
from cli.config.config_loader import get_config_loader

# Import dei geni
from cli.genes.rsi_gene import RSIGene
from cli.genes.macd_gene import MACDGene
from cli.genes.moving_average_gene import MovingAverageGene
from cli.genes.bollinger_gene import BollingerGene
from cli.genes.stochastic_gene import StochasticGene
from cli.genes.atr_gene import ATRGene

class SignalCalculator(PopulationBaseManager):
    """Calcola i segnali di trading dai geni."""
    
    def __init__(self):
        """Inizializza il calculator."""
        super().__init__()
        
        # Setup logger
        self.logger = get_logger('signal_calculator')
        
        # Carica configurazione
        self.config = get_config_loader()
        signals_config = self.config.get_value('gene.signals', {})
        
        # Parametri batch e retry
        self.GENE_BATCH_SIZE = signals_config.get('batch_size', 5)
        retry_config = signals_config.get('retry', {})
        self.MAX_RETRIES = retry_config.get('max_attempts', 5)
        self.INITIAL_RETRY_DELAY = retry_config.get('initial_delay', 0.1)
        self.MAX_RETRY_DELAY = retry_config.get('max_delay', 2.0)
        
        self.gene_classes = {
            'rsi': RSIGene,
            'macd': MACDGene,
            'moving_average': MovingAverageGene,
            'bollinger': BollingerGene,
            'stochastic': StochasticGene,
            'atr': ATRGene
        }
        
    def retry_on_db_lock(func):
        """Decorator per gestire i database lock con retry e backoff esponenziale."""
        def wrapper(self, *args, **kwargs):
            last_error = None
            delay = self.INITIAL_RETRY_DELAY
            
            for attempt in range(self.MAX_RETRIES):
                try:
                    return func(self, *args, **kwargs)
                except OperationalError as e:
                    if "database is locked" in str(e):
                        last_error = e
                        if attempt < self.MAX_RETRIES - 1:
                            self.logger.warning(f"Database locked, retry {attempt+1}/{self.MAX_RETRIES} dopo {delay:.1f}s")
                            time.sleep(delay)
                            delay = min(delay * 2 + random.random(), self.MAX_RETRY_DELAY)
                            continue
                    raise
            self.logger.error(f"Max retries ({self.MAX_RETRIES}) raggiunti per database lock")
            raise last_error
        return wrapper
        
    def _get_chromosome(self, chromosome_id: int, session: Session) -> Optional[Chromosome]:
        """Carica un cromosoma con tutte le sue relazioni."""
        return (
            session.query(Chromosome)
            .options(selectinload(Chromosome.genes))
            .filter(Chromosome.chromosome_id == chromosome_id)
            .first()
        )

    def _prepare_market_data(self, market_data: List[Union[MarketData, Dict]]) -> Tuple[Dict[str, np.ndarray], List]:
        """Converte i dati di mercato in array numpy OHLCV."""
        try:
            if not market_data:
                self.logger.error("Dati di mercato vuoti")
                return {}, []
                
            opens, highs, lows, closes, volumes, timestamps = [], [], [], [], [], []
            
            for data in market_data:
                try:
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
                except (ValueError, TypeError, AttributeError) as e:
                    self.logger.error(f"Errore conversione dati: {str(e)}")
                    continue
                    
            if not closes:  # Se non abbiamo dati validi
                self.logger.error("Nessun dato valido trovato")
                return {}, []
                    
            ohlcv_data = {
                'open': np.array(opens, dtype=float),
                'high': np.array(highs, dtype=float),
                'low': np.array(lows, dtype=float),
                'close': np.array(closes, dtype=float),
                'volume': np.array(volumes, dtype=float)
            }
            
            return ohlcv_data, timestamps
            
        except Exception as e:
            self.logger.error(f"Errore preparazione dati: {str(e)}")
            return {}, []

    def _create_gene_instance(self, gene: ChromosomeGene) -> Optional[object]:
        """Crea un'istanza del gene dai parametri salvati."""
        try:
            if gene.gene_type == 'base':
                self.logger.error("Gene 'base' non può essere istanziato")
                return None
                
            gene_class = self.gene_classes.get(gene.gene_type)
            if not gene_class:
                self.logger.error(f"Tipo gene non valido: {gene.gene_type}")
                return None
                
            try:
                params = json.loads(gene.parameters) if isinstance(gene.parameters, str) else gene.parameters
                if not isinstance(params, dict):
                    self.logger.error(f"Parametri non validi per {gene.gene_type}: {params}")
                    return None
            except (json.JSONDecodeError, TypeError):
                self.logger.error(f"Parametri gene non validi: {gene.parameters}")
                return None
                
            if not self._validate_gene_params(gene.gene_type, params):
                self.logger.error(f"Parametri mancanti per {gene.gene_type}: {params}")
                return None
                
            return gene_class(gene.gene_type, params)
            
        except Exception as e:
            self.logger.error(f"Errore creazione gene: {str(e)}")
            return None
            
    def _validate_gene_params(self, gene_type: str, params: Dict) -> bool:
        """Verifica che i parametri necessari siano presenti."""
        required_params = {
            'rsi': ['period', 'overbought', 'oversold'],
            'macd': ['fast_period', 'slow_period', 'signal_period'],
            'moving_average': ['period', 'type', 'distance'],
            'bollinger': ['period', 'std_dev'],
            'stochastic': ['k_period', 'd_period', 'smooth_k', 'overbought', 'oversold'],
            'atr': ['period', 'multiplier']
        }
        
        if gene_type not in required_params:
            return False
            
        for param in required_params[gene_type]:
            if param not in params:
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
            if session is not None:
                chromosome = self._get_chromosome(chromosome.chromosome_id, session)
                if not chromosome:
                    raise ValueError(f"Cromosoma {chromosome.chromosome_id} non trovato")
            
            ohlcv_data, timestamps = self._prepare_market_data(market_data)
            if not ohlcv_data or not timestamps:
                self.logger.error("Dati di mercato non validi")
                return {}
            
            active_genes = [g for g in chromosome.genes if g and g.is_active and g.gene_type != 'base']
            if not active_genes:
                self.logger.error("Nessun gene attivo trovato")
                return {}

            # Inizializza segnali per tutti i timestamp
            for ts in timestamps:
                signals[ts] = 0.0

            # Calcola peso totale per normalizzazione
            total_weight = sum(g.weight for g in active_genes)
            if total_weight == 0:
                self.logger.error("Peso totale dei geni è 0")
                return {}

            # Processa i geni in batch
            for i in range(0, len(active_genes), self.GENE_BATCH_SIZE):
                batch = active_genes[i:i + self.GENE_BATCH_SIZE]
                batch_signals = self._calculate_batch_signals(batch, ohlcv_data, timestamps, total_weight)
                
                # Combina i segnali normalizzati
                for ts_signals in batch_signals:
                    for timestamp, signal in ts_signals.items():
                        if timestamp in signals:
                            signals[timestamp] += signal

                if session is not None:
                    session.flush()

            # Normalizza i segnali finali usando tanh invece di clip
            for ts in signals:
                signals[ts] = np.tanh(signals[ts])
                
            # Log dei segnali generati per debug
            non_zero_signals = {ts: sig for ts, sig in signals.items() if abs(sig) > 0.1}
            if non_zero_signals:
                self.logger.debug(f"Segnali generati (>0.1): {len(non_zero_signals)}")
                self.logger.debug(f"Range segnali: min={min(signals.values()):.2f}, max={max(signals.values()):.2f}")

            return signals
            
        except Exception as e:
            self.logger.error(f"Errore calcolo segnali: {str(e)}")
            return {}
        
    def _calculate_batch_signals(
        self,
        genes: List[ChromosomeGene],
        ohlcv_data: Dict[str, np.ndarray],
        timestamps: List,
        total_weight: float
    ) -> List[Dict]:
        """Calcola i segnali per un batch di geni."""
        batch_signals = []
        
        try:
            for gene in genes:
                gene_instance = self._create_gene_instance(gene)
                if not gene_instance:
                    continue
                
                gene_signals = {}
                try:
                    # Calcola segnale passando tutti i dati OHLCV
                    raw_signals = gene_instance.calculate_signal(ohlcv_data)
                    if not isinstance(raw_signals, (np.ndarray, float)):
                        self.logger.error(f"Segnale non valido da {gene.gene_type}: {type(raw_signals)}")
                        continue
                        
                    # Converti in array se è un float
                    if isinstance(raw_signals, float):
                        raw_signals = np.full(len(timestamps), raw_signals)
                        
                    # Verifica lunghezza segnali
                    if len(raw_signals) != len(timestamps):
                        self.logger.error(f"Lunghezza segnali non valida per {gene.gene_type}: attesi {len(timestamps)}, ricevuti {len(raw_signals)}")
                        continue
                        
                    # Normalizza e applica peso
                    normalized_weight = gene.weight / total_weight
                    weighted_signals = raw_signals * normalized_weight
                    
                    # Salva segnale per ogni timestamp
                    for i, ts in enumerate(timestamps):
                        gene_signals[ts] = float(weighted_signals[i])
                    
                except Exception as e:
                    self.logger.error(f"Errore calcolo segnale gene {gene.gene_type}: {str(e)}")
                    continue
                
                batch_signals.append(gene_signals)
            
            return batch_signals
            
        except Exception as e:
            self.logger.error(f"Errore calcolo segnali batch: {str(e)}")
            return []
