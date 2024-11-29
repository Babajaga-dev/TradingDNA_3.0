"""
MACD Gene
---------
Implementazione del gene MACD (Moving Average Convergence Divergence).
"""

import numpy as np
import logging
from typing import Dict, Any, Optional
from .base import Gene

# Configura il logger per questo modulo
logger = logging.getLogger(__name__)

class MACDGene(Gene):
    """Gene che implementa l'indicatore MACD."""
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Inizializza il gene MACD.
        
        Args:
            params: Parametri specifici del gene (opzionale)
        """
        logger.debug("Inizializzazione MACDGene")
        super().__init__('macd', params)
        
    def calculate_macd(self, data: np.ndarray) -> tuple:
        """
        Calcola l'indicatore MACD.
        
        Args:
            data: Array numpy con i prezzi di chiusura
            
        Returns:
            Tuple con (macd_line, signal_line, histogram)
        """
        fast_period = int(float(self.params['fast_period']))
        slow_period = int(float(self.params['slow_period']))
        signal_period = int(float(self.params['signal_period']))
        
        logger.debug(f"Calcolo MACD con parametri: fast={fast_period}, slow={slow_period}, signal={signal_period}")
        
        if len(data) < max(fast_period, slow_period, signal_period):
            logger.warning("Serie temporale troppo corta per il calcolo del MACD")
            return np.full_like(data, np.nan), np.full_like(data, np.nan), np.full_like(data, np.nan)
            
        # Calcola EMA veloce e lenta
        alpha_fast = 2 / (fast_period + 1)
        alpha_slow = 2 / (slow_period + 1)
        
        ema_fast = np.full_like(data, np.nan)
        ema_slow = np.full_like(data, np.nan)
        
        # Inizializza le prime medie come SMA
        ema_fast[fast_period-1] = np.mean(data[:fast_period])
        ema_slow[slow_period-1] = np.mean(data[:slow_period])
        
        # Calcola EMA veloce
        for i in range(fast_period, len(data)):
            ema_fast[i] = data[i] * alpha_fast + ema_fast[i-1] * (1 - alpha_fast)
            
        # Calcola EMA lenta
        for i in range(slow_period, len(data)):
            ema_slow[i] = data[i] * alpha_slow + ema_slow[i-1] * (1 - alpha_slow)
            
        # Calcola MACD line
        macd_line = ema_fast - ema_slow
        
        # Calcola Signal line (EMA del MACD)
        signal_line = np.full_like(data, np.nan)
        alpha_signal = 2 / (signal_period + 1)
        
        # Inizializza signal line
        valid_macd = macd_line[~np.isnan(macd_line)]
        if len(valid_macd) >= signal_period:
            start_idx = np.where(~np.isnan(macd_line))[0][0]
            signal_line[start_idx+signal_period-1] = np.mean(macd_line[start_idx:start_idx+signal_period])
            
            # Calcola il resto della signal line
            for i in range(start_idx+signal_period, len(data)):
                signal_line[i] = macd_line[i] * alpha_signal + signal_line[i-1] * (1 - alpha_signal)
                
        # Calcola l'istogramma
        histogram = macd_line - signal_line
        
        logger.debug("Calcolo MACD completato")
        return macd_line, signal_line, histogram
        
    def calculate_signal(self, data: np.ndarray) -> float:
        """
        Calcola il segnale del gene sui dati forniti.
        
        Args:
            data: Array numpy con i prezzi di chiusura
            
        Returns:
            Segnale normalizzato tra -1 e 1
        """
        logger.debug("Calcolo segnale MACD")
        if len(data) < max(int(float(self.params['fast_period'])), 
                          int(float(self.params['slow_period'])), 
                          int(float(self.params['signal_period']))):
            logger.warning("Serie temporale troppo corta per il calcolo del segnale MACD")
            return 0
            
        macd_line, signal_line, histogram = self.calculate_macd(data)
        
        if np.isnan(histogram[-1]):
            logger.warning("Impossibile calcolare il segnale MACD: valori NaN")
            return 0
            
        # Normalizza il segnale basandosi sulla divergenza configurata
        signal = histogram[-1] / float(self.params['divergence'])
        
        logger.debug(f"Segnale MACD calcolato: {signal}")
        return np.clip(signal, -1, 1)
        
    def evaluate(self, data: np.ndarray) -> float:
        """
        Valuta le performance del gene sui dati forniti.
        
        Args:
            data: Array numpy con i prezzi di chiusura
            
        Returns:
            Punteggio di fitness del gene
        """
        logger.debug("Inizio valutazione MACD")
        if len(data) < max(int(float(self.params['fast_period'])), 
                          int(float(self.params['slow_period'])), 
                          int(float(self.params['signal_period']))):
            logger.warning("Serie temporale troppo corta per la valutazione MACD")
            return 0
            
        macd_line, signal_line, histogram = self.calculate_macd(data)
        signals = np.zeros_like(data)
        
        # Genera segnali quando l'istogramma attraversa lo zero
        histogram_crossover = np.diff(np.signbit(histogram))
        signals[1:][histogram_crossover] = 1  # Segnali di acquisto
        signals[1:][~histogram_crossover] = -1  # Segnali di vendita
        
        # Calcola i rendimenti
        returns = np.diff(data) / data[:-1]
        signal_returns = signals[:-1] * returns
        
        # Metriche di valutazione
        win_rate = np.sum(signal_returns > 0) / np.sum(signals != 0) if np.sum(signals != 0) > 0 else 0
        avg_return = np.mean(signal_returns[signals[:-1] != 0]) if np.sum(signals[:-1] != 0) > 0 else 0
        
        # Penalizza troppi segnali
        signal_frequency = np.sum(signals != 0) / len(signals)
        frequency_penalty = np.exp(-signal_frequency * 10)  # Penalizza alta frequenza
        
        # Calcola trend following score
        trend_changes = np.sum(np.diff(signals) != 0)
        trend_score = np.exp(-trend_changes / len(signals) * 5)  # Premia meno cambi di trend
        
        fitness = (win_rate * 0.3 + avg_return * 0.3 + frequency_penalty * 0.2 + trend_score * 0.2)
        logger.debug(f"Valutazione MACD completata. Fitness: {fitness}")
        return float(fitness)
