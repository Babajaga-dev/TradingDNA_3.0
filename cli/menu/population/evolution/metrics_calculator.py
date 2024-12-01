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
from sqlalchemy.exc import OperationalError, InvalidRequestError, StatementError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import ObjectDeletedError

from data.database.models.population_models import Chromosome, ChromosomeGene
from cli.menu.population.population_base import PopulationBaseManager
from cli.logger.log_manager import get_logger
from cli.config.config_loader import get_config_loader

class MetricsCalculator(PopulationBaseManager):
    """Calcola le metriche di performance del trading."""
    
    def __init__(self):
        """Inizializza il calculator."""
        super().__init__()
        self.logger = get_logger('metrics_calculator')
        self.config = get_config_loader()
        
        # Carica configurazione
        evolution_config = self.config.get_value('population.evolution', {})
        self.validation_config = evolution_config.get('validation', {})
        self.fitness_weights = evolution_config.get('fitness', {}).get('weights', {})
        
    def calculate_metrics(self, performance: List[Dict]) -> Dict:
        """Calcola le metriche di performance."""
        try:
            if not performance:
                self.logger.warning("Nessun trade da analizzare")
                return self._get_empty_metrics()
            
            # Estrai il sommario se presente
            summary = next((p for p in performance if 'summary' in p), None)
            if summary:
                performance = [p for p in performance if 'summary' not in p]
            
            if not performance:
                self.logger.warning("Nessun trade valido dopo filtro summary")
                return self._get_empty_metrics()
            
            # Calcola metriche base
            pnls = [trade['pnl'] for trade in performance]
            wins = [pnl for pnl in pnls if pnl > 0]
            losses = [pnl for pnl in pnls if pnl <= 0]
            
            total_trades = len(pnls)
            win_trades = len(wins)
            
            # Calcola win rate e medie
            win_rate = win_trades / total_trades if total_trades > 0 else 0.0
            avg_win = np.mean(wins) if wins else 0.0
            avg_loss = np.mean(losses) if losses else 0.0
            
            # Calcola Sharpe ratio migliorato
            returns = np.array(pnls)
            if len(returns) > 1:
                excess_returns = returns - self.config.get_value('portfolio.risk_management.commission', 0.001)
                sharpe_ratio = self._calculate_sharpe_ratio(excess_returns)
            else:
                sharpe_ratio = 0.0
            
            # Calcola drawdown
            max_dd = self._calculate_max_drawdown(pnls)
            
            # Calcola profit factor
            profit_factor = (sum(wins) / -sum(losses)) if losses and sum(losses) != 0 else 0.0
            
            # Prepara metriche
            metrics = {
                'total_return': float(np.sum(pnls)),
                'win_rate': float(win_rate),
                'avg_win': float(avg_win),
                'avg_loss': float(avg_loss),
                'sharpe_ratio': float(sharpe_ratio),
                'max_drawdown': float(max_dd),
                'profit_factor': float(profit_factor),
                'trades': total_trades,
                'trades_distribution': summary['summary']['trades_distribution'] if summary else {}
            }
            
            # Log delle metriche principali
            self.logger.debug(f"Metriche calcolate: trades={metrics['trades']}, "
                        f"win_rate={metrics['win_rate']*100:.1f}%, "
                        f"return={metrics['total_return']*100:.1f}%, "
                        f"sharpe={metrics['sharpe_ratio']:.2f}")
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Errore calcolo metriche: {str(e)}")
            return self._get_empty_metrics()
            
    def _get_empty_metrics(self) -> Dict:
        """Restituisce un dizionario di metriche vuote."""
        return {
            'total_return': 0.0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'profit_factor': 0.0,
            'trades': 0,
            'trades_distribution': {'long': 0, 'short': 0}
        }
        
    def _calculate_sharpe_ratio(self, returns: np.ndarray, risk_free_rate: float = 0.0) -> float:
        """Calcola lo Sharpe ratio con gestione degli errori."""
        try:
            if len(returns) < 2:
                return 0.0
                
            # Annualizziamo assumendo dati giornalieri
            periods_per_year = 252
            excess_returns = returns - (risk_free_rate / periods_per_year)
            
            # Calcola media e deviazione standard
            avg_return = np.mean(excess_returns)
            std_return = np.std(excess_returns, ddof=1)
            
            if std_return == 0:
                return 0.0
                
            # Annualizza lo Sharpe ratio
            sharpe = (avg_return / std_return) * np.sqrt(periods_per_year)
            
            return float(sharpe)
            
        except Exception as e:
            self.logger.error(f"Errore calcolo Sharpe ratio: {str(e)}")
            return 0.0
        
    def _calculate_max_drawdown(self, pnls: List[float]) -> float:
        """Calcola il maximum drawdown."""
        try:
            if not pnls:
                return 0.0
                
            # Calcola equity curve cumulativa
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
            self.logger.error(f"Errore calcolo drawdown: {str(e)}")
            return 0.0
        
    def combine_metrics(self, metrics: Dict) -> float:
        """Combina le metriche in un singolo valore fitness."""
        try:
            if not metrics or 'trades' not in metrics or metrics['trades'] == 0:
                self.logger.warning("Metriche non valide o nessun trade")
                return 0.0
            
            # Verifica requisiti minimi
            min_trades = self.validation_config.get('min_trades', 10)
            min_win_rate = self.validation_config.get('min_win_rate', 0.45)
            max_allowed_dd = self.validation_config.get('max_drawdown', 0.20)
            
            if (metrics['trades'] < min_trades or
                metrics['win_rate'] < min_win_rate or
                metrics['max_drawdown'] > max_allowed_dd):
                self.logger.debug(f"Requisiti minimi non soddisfatti: trades={metrics['trades']}, "
                           f"win_rate={metrics['win_rate']*100:.1f}%, dd={metrics['max_drawdown']*100:.1f}%")
                return 0.0
            
            # Normalizza e combina usando i pesi da population.yaml
            fitness = sum(
                metrics[metric] * weight
                for metric, weight in self.fitness_weights.items()
                if metric in metrics
            )
            
            # Aggiungi bonus per profit factor > 1
            if metrics['profit_factor'] > 1:
                fitness *= (1 + (metrics['profit_factor'] - 1) * 0.1)
            
            fitness = max(0.0, float(fitness))
            
            self.logger.debug(f"Fitness calcolato: {fitness:.4f}")
            return fitness
            
        except Exception as e:
            self.logger.error(f"Errore combinazione metriche: {str(e)}")
            return 0.0

    def _is_valid_gene(self, session: Session, gene: ChromosomeGene) -> bool:
        """Verifica se un gene è valido e presente nella sessione."""
        try:
            session.refresh(gene)
            return True
        except (ObjectDeletedError, InvalidRequestError, StatementError):
            return False
        
    def update_chromosome_metrics(
        self, 
        chromosome: Chromosome, 
        metrics: Dict, 
        fitness: float,
        session: Optional[Session] = None
    ) -> None:
        """Aggiorna le metriche del cromosoma."""
        if session is None:
            self.logger.error("Sessione database non fornita")
            return
            
        try:
            # Verifica e aggiorna il cromosoma
            try:
                session.refresh(chromosome)
            except (ObjectDeletedError, InvalidRequestError) as e:
                self.logger.error(f"Cromosoma non più valido: {str(e)}")
                return
                
            # Aggiorna metriche del cromosoma
            metrics_copy = metrics.copy()
            metrics_copy['fitness'] = float(fitness)
            
            try:
                metrics_json = json.dumps(metrics_copy)
                chromosome.performance_metrics = metrics_json
                chromosome.last_test_date = datetime.now()
            except Exception as e:
                self.logger.error(f"Errore serializzazione metriche: {str(e)}")
                return
            
            # Aggiorna contributo performance dei geni
            total_trades = metrics.get('trades', 0)
            if total_trades > 0 and chromosome.genes:
                # Filtra solo i geni attivi e validi
                active_genes = []
                for gene in chromosome.genes:
                    if gene and gene.is_active and self._is_valid_gene(session, gene):
                        active_genes.append(gene)
                
                # Processa i geni in batch
                batch_size = self.config.get_value('gene.signals.batch_size', 5)
                for i in range(0, len(active_genes), batch_size):
                    batch = active_genes[i:i + batch_size]
                    
                    for gene in batch:
                        try:
                            gene.performance_contribution = float(gene.weight * fitness)
                        except Exception as e:
                            self.logger.error(f"Errore aggiornamento gene {gene.chromosome_gene_id}: {str(e)}")
                            continue
                    
                    try:
                        session.flush()
                    except Exception as e:
                        self.logger.error(f"Errore flush batch: {str(e)}")
                        session.rollback()
                        continue
            
            session.add(chromosome)
            try:
                session.flush()
            except Exception as e:
                self.logger.error(f"Errore salvataggio finale: {str(e)}")
                session.rollback()
            
        except Exception as e:
            self.logger.error(f"Errore aggiornamento metriche: {str(e)}")
            session.rollback()
            raise
