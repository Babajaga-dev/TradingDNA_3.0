"""
Metrics Calculator
---------------
Calcolo delle metriche di performance del trading.
"""

from typing import Dict, List, Optional
import json
from datetime import datetime
import time
import random
import numpy as np
from sqlalchemy.exc import OperationalError, InvalidRequestError
from sqlalchemy.orm import Session

from data.database.models.population_models import Chromosome, ChromosomeGene
from cli.menu.population.population_base import PopulationBaseManager
from cli.logger.log_manager import get_logger

# Setup logger
logger = get_logger('metrics_calculator')

# Configurazione retry
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 0.1
MAX_RETRY_DELAY = 2.0

# Dimensione batch per l'aggiornamento dei geni
GENE_BATCH_SIZE = 5

def retry_on_db_lock(func):
    """Decorator per gestire i database lock con retry e backoff esponenziale."""
    def wrapper(*args, **kwargs):
        last_error = None
        delay = INITIAL_RETRY_DELAY
        
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except OperationalError as e:
                if "database is locked" in str(e):
                    last_error = e
                    if attempt < MAX_RETRIES - 1:
                        logger.warning(f"Database locked, retry {attempt+1}/{MAX_RETRIES} dopo {delay:.1f}s")
                        time.sleep(delay)
                        delay = min(delay * 2 + random.random(), MAX_RETRY_DELAY)
                        continue
                raise
        logger.error(f"Max retries ({MAX_RETRIES}) raggiunti per database lock")
        raise last_error
    return wrapper

class MetricsCalculator(PopulationBaseManager):
    """Calcola le metriche di performance del trading."""
    
    def __init__(self, test_config: Dict):
        """Inizializza il calculator."""
        super().__init__()
        self.test_config = test_config
        
    def calculate_metrics(self, performance: List[Dict]) -> Dict:
        """Calcola le metriche di performance."""
        try:
            if not performance:
                return {
                    'total_return': 0.0,
                    'win_rate': 0.0,
                    'avg_win': 0.0,
                    'avg_loss': 0.0,
                    'sharpe_ratio': 0.0,
                    'max_drawdown': 0.0,
                    'trades': 0
                }
            
            pnls = [trade['pnl'] for trade in performance]
            wins = [pnl for pnl in pnls if pnl > 0]
            losses = [pnl for pnl in pnls if pnl <= 0]
            
            metrics = {
                'total_return': float(np.sum(pnls)),
                'win_rate': float(len(wins) / len(pnls) if pnls else 0.0),
                'avg_win': float(np.mean(wins)) if wins else 0.0,
                'avg_loss': float(np.mean(losses)) if losses else 0.0,
                'sharpe_ratio': float(np.mean(pnls) / np.std(pnls)) if len(pnls) > 1 else 0.0,
                'max_drawdown': float(self._calculate_max_drawdown(pnls)),
                'trades': int(len(pnls))
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Errore calcolo metriche: {str(e)}")
            return {
                'total_return': 0.0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'trades': 0
            }
        
    def _calculate_max_drawdown(self, pnls: List[float]) -> float:
        """Calcola il maximum drawdown."""
        try:
            if not pnls:
                return 0.0
                
            cumulative = np.cumsum(pnls)
            max_dd = 0.0
            peak = cumulative[0]
            
            for value in cumulative[1:]:
                if value > peak:
                    peak = value
                dd = (peak - value) / peak if peak != 0 else 0
                max_dd = max(max_dd, dd)
                
            return float(max_dd)
            
        except Exception as e:
            logger.error(f"Errore calcolo drawdown: {str(e)}")
            return 0.0
        
    def combine_metrics(self, metrics: Dict) -> float:
        """Combina le metriche in un singolo valore fitness."""
        try:
            # Pesi per ogni metrica
            weights = self.test_config['fitness']['weights']
            
            # Normalizza e combina
            fitness = sum(
                metrics[metric] * weight
                for metric, weight in weights.items()
                if metric in metrics
            )
            
            fitness = max(0.0, float(fitness))  # Non permettiamo fitness negativo
            return fitness
            
        except Exception as e:
            logger.error(f"Errore combinazione metriche: {str(e)}")
            return 0.0
        
    @retry_on_db_lock
    def update_chromosome_metrics(
        self, 
        chromosome: Chromosome, 
        metrics: Dict, 
        fitness: float,
        session: Optional[Session] = None
    ) -> None:
        """Aggiorna le metriche del cromosoma."""
        try:
            if session is None:
                logger.error("Sessione database non fornita")
                return
                
            # Aggiorna metriche del cromosoma
            metrics_copy = metrics.copy()  # Crea una copia per non modificare l'originale
            metrics_copy['fitness'] = float(fitness)  # Assicura che fitness sia float
            
            # Serializza le metriche in JSON
            try:
                metrics_json = json.dumps(metrics_copy)
                chromosome.performance_metrics = metrics_json
                chromosome.last_test_date = datetime.now()
            except Exception as e:
                logger.error(f"Errore serializzazione metriche: {str(e)}")
                return
            
            # Aggiorna contributo performance dei geni in batch
            total_trades = metrics.get('trades', 0)
            if total_trades > 0 and chromosome.genes:
                try:
                    session.refresh(chromosome)
                except InvalidRequestError:
                    logger.error("Impossibile ricaricare il cromosoma")
                    return
                    
                active_genes = [g for g in chromosome.genes if g and g.is_active]
                total_genes = len(active_genes)
                
                # Processa i geni in batch
                for i in range(0, total_genes, GENE_BATCH_SIZE):
                    batch = active_genes[i:i + GENE_BATCH_SIZE]
                    
                    # Aggiorna il contributo per ogni gene nel batch
                    for gene in batch:
                        try:
                            # Verifica che il gene sia ancora valido
                            if gene in session:
                                gene.performance_contribution = float(gene.weight * fitness)
                        except Exception as e:
                            logger.error(f"Errore aggiornamento gene {gene.chromosome_gene_id}: {str(e)}")
                            continue
                    
                    # Flush dopo ogni batch
                    try:
                        session.flush()
                    except Exception as e:
                        logger.error(f"Errore flush batch: {str(e)}")
                        continue
            
            session.add(chromosome)
            try:
                session.flush()
            except Exception as e:
                logger.error(f"Errore salvataggio finale: {str(e)}")
            
        except Exception as e:
            logger.error(f"Errore aggiornamento metriche: {str(e)}")
            raise
