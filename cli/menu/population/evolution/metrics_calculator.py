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
from sqlalchemy.exc import OperationalError
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

class MetricsCalculator(PopulationBaseManager):
    """Calcola le metriche di performance del trading."""
    
    def __init__(self, test_config: Dict):
        """Inizializza il calculator."""
        super().__init__()
        self.test_config = test_config
        print("[DEBUG] MetricsCalculator inizializzato")
        
    def calculate_metrics(self, performance: List[Dict]) -> Dict:
        """Calcola le metriche di performance."""
        try:
            print("\n[DEBUG] === INIZIO CALCOLO METRICHE ===")
            print(f"[DEBUG] Numero operazioni da valutare: {len(performance)}")
            
            if not performance:
                print("[DEBUG] Nessuna operazione da valutare, ritorno metriche default")
                return {
                    'total_return': 0.0,
                    'win_rate': 0.0,
                    'avg_win': 0.0,
                    'avg_loss': 0.0,
                    'sharpe_ratio': 0.0,
                    'max_drawdown': 0.0,
                    'trades': 0
                }
            
            print("[DEBUG] Estrazione PnL dalle operazioni...")
            pnls = [trade['pnl'] for trade in performance]
            wins = [pnl for pnl in pnls if pnl > 0]
            losses = [pnl for pnl in pnls if pnl <= 0]
            
            print(f"[DEBUG] Statistiche operazioni:")
            print(f"[DEBUG] - Totale: {len(pnls)}")
            print(f"[DEBUG] - Vincenti: {len(wins)}")
            print(f"[DEBUG] - Perdenti: {len(losses)}")
            
            print("[DEBUG] Calcolo metriche...")
            metrics = {
                'total_return': float(np.sum(pnls)),
                'win_rate': len(wins) / len(pnls) if pnls else 0.0,
                'avg_win': float(np.mean(wins)) if wins else 0.0,
                'avg_loss': float(np.mean(losses)) if losses else 0.0,
                'sharpe_ratio': float(np.mean(pnls) / np.std(pnls)) if len(pnls) > 1 else 0.0,
                'max_drawdown': self._calculate_max_drawdown(pnls),
                'trades': len(pnls)
            }
            
            print("\n[DEBUG] Metriche calcolate:")
            print(f"[DEBUG] - Return totale: {metrics['total_return']:.2%}")
            print(f"[DEBUG] - Win rate: {metrics['win_rate']:.2%}")
            print(f"[DEBUG] - Media vincite: {metrics['avg_win']:.2%}")
            print(f"[DEBUG] - Media perdite: {metrics['avg_loss']:.2%}")
            print(f"[DEBUG] - Sharpe ratio: {metrics['sharpe_ratio']:.2f}")
            print(f"[DEBUG] - Max drawdown: {metrics['max_drawdown']:.2%}")
            print(f"[DEBUG] - Numero trade: {metrics['trades']}")
            
            print("[DEBUG] === FINE CALCOLO METRICHE ===\n")
            return metrics
            
        except Exception as e:
            print(f"[DEBUG] ERRORE calcolo metriche: {str(e)}")
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
            print("[DEBUG] Inizio calcolo maximum drawdown")
            if not pnls:
                print("[DEBUG] Nessun PnL disponibile, drawdown = 0")
                return 0.0
                
            print("[DEBUG] Calcolo equity curve...")
            cumulative = np.cumsum(pnls)
            max_dd = 0.0
            peak = cumulative[0]
            
            print("[DEBUG] Calcolo drawdown...")
            for value in cumulative[1:]:
                if value > peak:
                    peak = value
                dd = (peak - value) / peak if peak != 0 else 0
                max_dd = max(max_dd, dd)
                
            print(f"[DEBUG] Maximum drawdown calcolato: {max_dd:.2%}")
            return float(max_dd)
            
        except Exception as e:
            print(f"[DEBUG] ERRORE calcolo drawdown: {str(e)}")
            logger.error(f"Errore calcolo drawdown: {str(e)}")
            return 0.0
        
    def combine_metrics(self, metrics: Dict) -> float:
        """Combina le metriche in un singolo valore fitness."""
        try:
            print("[DEBUG] Inizio combinazione metriche in fitness")
            # Pesi per ogni metrica
            weights = self.test_config['fitness']['weights']
            print(f"[DEBUG] Pesi metriche: {weights}")
            
            # Normalizza e combina
            print("[DEBUG] Combinazione metriche pesate...")
            fitness = sum(
                metrics[metric] * weight
                for metric, weight in weights.items()
                if metric in metrics
            )
            
            fitness = max(0.0, float(fitness))  # Non permettiamo fitness negativo
            print(f"[DEBUG] Fitness finale calcolato: {fitness:.4f}")
            return fitness
            
        except Exception as e:
            print(f"[DEBUG] ERRORE combinazione metriche: {str(e)}")
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
            print(f"\n[DEBUG] === INIZIO AGGIORNAMENTO METRICHE CROMOSOMA {chromosome.chromosome_id} ===")
            
            # Aggiorna metriche del cromosoma senza merge
            print("[DEBUG] Aggiornamento metriche nel cromosoma...")
            metrics['fitness'] = fitness
            chromosome.performance_metrics = json.dumps(metrics)
            chromosome.last_test_date = datetime.now()
            
            # Aggiorna contributo performance dei geni in batch
            total_trades = metrics['trades']
            if total_trades > 0 and chromosome.genes:
                # Ricarica i geni dalla sessione per assicurarsi che siano ancora validi
                if session is not None:
                    print("[DEBUG] Ricaricamento geni dalla sessione...")
                    try:
                        session.refresh(chromosome)
                    except Exception as e:
                        print(f"[DEBUG] Errore refresh cromosoma: {str(e)}")
                        return
                
                active_genes = [g for g in chromosome.genes if g and g.is_active]
                total_genes = len(active_genes)
                
                print(f"[DEBUG] Aggiornamento contributo performance per {total_genes} geni attivi")
                
                # Processa i geni in batch
                for i in range(0, total_genes, GENE_BATCH_SIZE):
                    batch = active_genes[i:i + GENE_BATCH_SIZE]
                    print(f"[DEBUG] Processing batch di geni {i+1}-{min(i+GENE_BATCH_SIZE, total_genes)}")
                    
                    # Aggiorna il contributo per ogni gene nel batch
                    for gene in batch:
                        try:
                            if session is not None:
                                # Verifica che il gene sia ancora nella sessione
                                try:
                                    session.refresh(gene)
                                except Exception as e:
                                    print(f"[DEBUG] Skip gene {gene.chromosome_gene_id}: {str(e)}")
                                    continue
                            gene.performance_contribution = gene.weight * fitness
                        except Exception as e:
                            print(f"[DEBUG] Skip gene {gene.chromosome_gene_id}: {str(e)}")
                            continue
                    
                    # Flush dopo ogni batch
                    if session is not None:
                        try:
                            print("[DEBUG] Flush sessione dopo batch")
                            session.flush()
                        except Exception as e:
                            print(f"[DEBUG] Errore flush batch: {str(e)}")
                            continue
            
            if session is not None:
                print("[DEBUG] Salvataggio modifiche finali...")
                session.add(chromosome)
                try:
                    session.flush()
                    print("[DEBUG] Modifiche salvate")
                except Exception as e:
                    print(f"[DEBUG] Errore salvataggio finale: {str(e)}")
            
            print(f"[DEBUG] === FINE AGGIORNAMENTO METRICHE CROMOSOMA ===\n")
            
        except Exception as e:
            print(f"[DEBUG] ERRORE aggiornamento metriche: {str(e)}")
            logger.error(f"Errore aggiornamento metriche: {str(e)}")
            raise
