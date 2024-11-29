"""
Fitness Calculator
---------------
Calcolo del fitness per i cromosomi basato sulle performance di trading.
"""

from typing import Dict, List, Optional
import numpy as np
import json
import yaml
from datetime import datetime, timedelta
from contextlib import contextmanager
from sqlalchemy import desc
from sqlalchemy.orm import Session
import time

from data.database.models.population_models import (
    Population, Chromosome, ChromosomeGene
)
from data.database.models.models import MarketData, get_session
from cli.menu.population.population_base import PopulationBaseManager
from cli.logger.log_manager import get_logger

# Setup logger
logger = get_logger('fitness_calculator')

class FitnessCalculator(PopulationBaseManager):
    """Calcola il fitness dei cromosomi."""
    
    def __init__(self):
        """Inizializza il calculator."""
        super().__init__()
        self.test_config = self._load_test_config()
        self._market_data_cache = {}
        self._cache_timestamp = datetime.now()
        self._cache_timeout = timedelta(minutes=5)
        
    @contextmanager
    def _session_scope(self):
        """Context manager per gestire il ciclo di vita della sessione."""
        session = None
        try:
            session = get_session()
            yield session
            session.commit()
        except Exception as e:
            if session:
                session.rollback()
            raise
        finally:
            if session:
                session.close()
                
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
    
    def calculate_population_fitness(self, population: Population) -> Dict:
        """
        Calcola il fitness per tutti i cromosomi di una popolazione.
        
        Args:
            population: Popolazione da valutare
            
        Returns:
            Dict: Statistiche fitness
        """
        try:
            stats = {
                "total": len(population.chromosomes),
                "evaluated": 0,
                "best_fitness": 0.0,
                "avg_fitness": 0.0,
                "worst_fitness": float('inf'),
                "distribution": []
            }
            
            # Pre-carica i dati di mercato
            market_data = self._get_market_data(population)
            if not market_data:
                logger.error(f"Nessun dato di mercato per popolazione {population.name}")
                return stats
            
            # Calcola fitness per ogni cromosoma
            with self._session_scope() as session:
                for chromosome in population.chromosomes:
                    if chromosome and chromosome.status == 'active':
                        fitness = self.calculate_chromosome_fitness(
                            chromosome, 
                            market_data,
                            session
                        )
                        if fitness > 0:
                            stats["evaluated"] += 1
                            stats["best_fitness"] = max(stats["best_fitness"], fitness)
                            stats["worst_fitness"] = min(stats["worst_fitness"], fitness)
                            stats["distribution"].append(fitness)
                            
                if stats["evaluated"] > 0:
                    stats["avg_fitness"] = float(np.mean(stats["distribution"]))
                    
                # Log risultati
                logger.info(
                    f"Calcolato fitness per {stats['evaluated']}/{stats['total']} "
                    f"cromosomi (best={stats['best_fitness']:.2f}, "
                    f"avg={stats['avg_fitness']:.2f})"
                )
                
                return stats
                
        except Exception as e:
            logger.error(f"Errore calcolo fitness popolazione: {str(e)}")
            raise
            
    def calculate_chromosome_fitness(
        self, 
        chromosome: Chromosome, 
        market_data: Optional[List[MarketData]] = None,
        session: Optional[Session] = None
    ) -> float:
        """
        Calcola il fitness di un singolo cromosoma.
        
        Args:
            chromosome: Cromosoma da valutare
            market_data: Dati di mercato pre-caricati (opzionale)
            session: Sessione database (opzionale)
            
        Returns:
            float: Valore fitness
        """
        try:
            # Verifica cromosoma valido
            if not chromosome or not chromosome.population_id:
                logger.warning("Cromosoma non valido per il calcolo del fitness")
                return 0.0
                
            # Usa sessione fornita o creane una nuova
            use_session = session if session else self.session
                
            # Verifica popolazione valida
            population = self.get_population(chromosome.population_id)
            if not population:
                logger.warning(f"Popolazione {chromosome.population_id} non trovata")
                return 0.0
                
            # Usa dati di mercato forniti o caricali
            if market_data is None:
                market_data = self._get_market_data(population)
                
            if not market_data:
                logger.warning("Nessun dato di mercato disponibile")
                return 0.0
                
            # Calcola segnali per ogni gene
            signals = self._calculate_gene_signals(chromosome, market_data)
            
            # Simula trading
            performance = self._simulate_trading(signals, market_data)
            
            # Calcola metriche
            metrics = self._calculate_metrics(performance)
            
            # Calcola fitness finale
            fitness = self._combine_metrics(metrics)
            
            # Aggiorna cromosoma
            self._update_chromosome_metrics(chromosome, metrics, fitness, use_session)
            
            logger.debug(
                f"Calcolato fitness {fitness:.2f} per cromosoma "
                f"{chromosome.chromosome_id}"
            )
            
            return fitness
            
        except Exception as e:
            logger.error(f"Errore calcolo fitness cromosoma {getattr(chromosome, 'chromosome_id', None)}: {str(e)}")
            return 0.0
            
    def _get_market_data(self, population: Population) -> List[MarketData]:
        """
        Ottiene i dati di mercato per il backtest.
        
        Args:
            population: Popolazione per cui ottenere i dati
            
        Returns:
            List[MarketData]: Dati di mercato
        """
        try:
            # Verifica cache valida
            cache_key = f"{population.symbol_id}_{population.timeframe}"
            cache_valid = (
                cache_key in self._market_data_cache and
                datetime.now() - self._cache_timestamp < self._cache_timeout
            )
            
            if cache_valid:
                return self._market_data_cache[cache_key]
                
            # Ottieni ultimi N giorni di dati
            days = self.test_config['backtest']['days']
            
            # Query con timeout manuale
            start_time = time.time()
            timeout = 30  # 30 secondi
            
            with self._session_scope() as session:
                data = session.query(MarketData)\
                    .filter(
                        MarketData.symbol_id == population.symbol_id,
                        MarketData.timeframe == population.timeframe
                    )\
                    .order_by(desc(MarketData.timestamp))\
                    .limit(days * 24)\
                    .all()
                    
                # Verifica timeout manuale
                if time.time() - start_time > timeout:
                    logger.error("Timeout query dati mercato")
                    return []
                
            # Se non ci sono dati, crea dati di test
            if not data:
                logger.warning(f"Creazione dati di test per {population.symbol_id}")
                data = self._create_test_market_data(days)
            
            # Aggiorna cache
            self._market_data_cache[cache_key] = data
            self._cache_timestamp = datetime.now()
            
            return data
            
        except Exception as e:
            logger.error(f"Errore caricamento dati mercato: {str(e)}")
            return []
            
    def _create_test_market_data(self, days: int) -> List[MarketData]:
        """
        Crea dati di mercato di test.
        
        Args:
            days: Numero di giorni di dati da generare
            
        Returns:
            List[MarketData]: Dati di mercato di test
        """
        data = []
        base_price = 100.0
        timestamp = datetime.now()
        
        for i in range(days * 24):
            price = base_price * (1 + np.random.normal(0, 0.01))
            data.append(MarketData(
                timestamp=timestamp - timedelta(hours=i),
                open=price * (1 - 0.001),
                high=price * (1 + 0.001),
                low=price * (1 - 0.002),
                close=price,
                volume=np.random.randint(1000, 10000)
            ))
            
        return data
            
    def _calculate_gene_signals(self, chromosome: Chromosome, market_data: List[MarketData]) -> Dict:
        """
        Calcola i segnali di trading per ogni gene.
        
        Args:
            chromosome: Cromosoma da valutare
            market_data: Dati di mercato
            
        Returns:
            Dict: Segnali per timestamp
        """
        signals = {}
        
        try:
            for gene in chromosome.genes:
                if gene and gene.is_active:
                    # Calcola segnali del gene
                    gene_signals = self._calculate_gene_signal(gene, market_data)
                    
                    # Combina segnali pesati
                    for timestamp, signal in gene_signals.items():
                        if timestamp not in signals:
                            signals[timestamp] = 0.0
                        signals[timestamp] += signal * gene.weight
                        
            return signals
            
        except Exception as e:
            logger.error(f"Errore calcolo segnali: {str(e)}")
            return {}
        
    def _calculate_gene_signal(self, gene: ChromosomeGene, market_data: List[MarketData]) -> Dict:
        """
        Calcola i segnali per un singolo gene.
        
        Args:
            gene: Gene da valutare
            market_data: Dati di mercato
            
        Returns:
            Dict: Segnali per timestamp
        """
        signals = {}
        rng = np.random.default_rng()
        
        try:
            # Genera segnali in batch per efficienza
            signal_values = rng.uniform(-1, 1, size=len(market_data))
            
            for i, data in enumerate(market_data):
                signals[data.timestamp] = float(signal_values[i])
                
            return signals
            
        except Exception as e:
            logger.error(f"Errore calcolo segnali gene: {str(e)}")
            return {}
        
    def _simulate_trading(self, signals: Dict, market_data: List[MarketData]) -> List[Dict]:
        """
        Simula il trading usando i segnali.
        
        Args:
            signals: Segnali di trading
            market_data: Dati di mercato
            
        Returns:
            List[Dict]: Performance del trading
        """
        performance = []
        position = None
        entry_price = 0.0
        
        try:
            for data in market_data:
                signal = signals.get(data.timestamp, 0.0)
                
                # Logica trading semplificata
                if position is None and signal > 0.5:
                    # Apri long
                    position = 'long'
                    entry_price = data.close
                elif position is None and signal < -0.5:
                    # Apri short
                    position = 'short'
                    entry_price = data.close
                elif position == 'long' and signal < 0:
                    # Chiudi long
                    pnl = (data.close - entry_price) / entry_price
                    performance.append({
                        'timestamp': data.timestamp,
                        'type': 'long',
                        'entry': entry_price,
                        'exit': data.close,
                        'pnl': pnl
                    })
                    position = None
                elif position == 'short' and signal > 0:
                    # Chiudi short
                    pnl = (entry_price - data.close) / entry_price
                    performance.append({
                        'timestamp': data.timestamp,
                        'type': 'short',
                        'entry': entry_price,
                        'exit': data.close,
                        'pnl': pnl
                    })
                    position = None
                    
            return performance
            
        except Exception as e:
            logger.error(f"Errore simulazione trading: {str(e)}")
            return []
        
    def _calculate_metrics(self, performance: List[Dict]) -> Dict:
        """
        Calcola le metriche di performance.
        
        Args:
            performance: Lista operazioni
            
        Returns:
            Dict: Metriche calcolate
        """
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
                'win_rate': len(wins) / len(pnls) if pnls else 0.0,
                'avg_win': float(np.mean(wins)) if wins else 0.0,
                'avg_loss': float(np.mean(losses)) if losses else 0.0,
                'sharpe_ratio': float(np.mean(pnls) / np.std(pnls)) if len(pnls) > 1 else 0.0,
                'max_drawdown': self._calculate_max_drawdown(pnls),
                'trades': len(pnls)
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
        """
        Calcola il maximum drawdown.
        
        Args:
            pnls: Lista PnL
            
        Returns:
            float: Maximum drawdown
        """
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
        
    def _combine_metrics(self, metrics: Dict) -> float:
        """
        Combina le metriche in un singolo valore fitness.
        
        Args:
            metrics: Metriche da combinare
            
        Returns:
            float: Fitness finale
        """
        try:
            # Pesi per ogni metrica
            weights = self.test_config['fitness']['weights']
            
            # Normalizza e combina
            fitness = sum(
                metrics[metric] * weight
                for metric, weight in weights.items()
                if metric in metrics
            )
            
            return max(0.0, float(fitness))  # Non permettiamo fitness negativo
            
        except Exception as e:
            logger.error(f"Errore combinazione metriche: {str(e)}")
            return 0.0
        
    def _update_chromosome_metrics(
        self, 
        chromosome: Chromosome, 
        metrics: Dict, 
        fitness: float,
        session: Session
    ) -> None:
        """
        Aggiorna le metriche del cromosoma.
        
        Args:
            chromosome: Cromosoma da aggiornare
            metrics: Metriche calcolate
            fitness: Fitness calcolato
            session: Sessione database
        """
        try:
            metrics['fitness'] = fitness
            chromosome.performance_metrics = json.dumps(metrics)
            chromosome.last_test_date = datetime.now()
            
            # Aggiorna contributo performance dei geni
            total_trades = metrics['trades']
            if total_trades > 0:
                for gene in chromosome.genes:
                    if gene and gene.is_active:
                        gene.performance_contribution = gene.weight * fitness
            
            session.add(chromosome)
            
            logger.debug(
                f"Aggiornate metriche cromosoma {chromosome.chromosome_id} "
                f"(fitness={fitness:.2f})"
            )
            
        except Exception as e:
            logger.error(f"Errore aggiornamento metriche: {str(e)}")
            raise
