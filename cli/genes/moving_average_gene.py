"""
Moving Average Gene
------------------
Implementazione del gene Moving Average (SMA/EMA).
"""

import numpy as np
from typing import Dict, Any, Optional
from .base import Gene

class MovingAverageGene(Gene):
    """Gene che implementa l'indicatore Moving Average."""
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Inizializza il gene Moving Average.
        
        Args:
            params: Parametri specifici del gene (opzionale)
        """
        super().__init__('moving_average', params)
        
    def calculate_ma(self, data: np.ndarray) -> np.ndarray:
        """
        Calcola l'indicatore Moving Average (SMA o EMA).
        
        Args:
            data: Array numpy con i prezzi di chiusura
            
        Returns:
            Array numpy con i valori della media mobile
        """
        # Converti period in int, ma lascia type come stringa
        period = int(float(self.params['period']))
        ma_type = str(self.params['type'])  # Assicura che sia una stringa
        
        if len(data) < period:
            return np.full_like(data, np.nan)
            
        if ma_type == "SMA":
            # Simple Moving Average
            weights = np.ones(period)
            weights /= weights.sum()
            ma = np.convolve(data, weights, mode='valid')
            # Padding per mantenere la dimensione originale
            result = np.full_like(data, np.nan)
            result[period-1:] = ma
            return result
            
        elif ma_type == "EMA":
            # Exponential Moving Average
            alpha = 2 / (period + 1)
            result = np.full_like(data, np.nan)
            result[period-1] = np.mean(data[:period])  # Prima media come SMA
            
            # Calcola EMA
            for i in range(period, len(data)):
                result[i] = data[i] * alpha + result[i-1] * (1 - alpha)
                
            return result
            
    def calculate_signal(self, data: np.ndarray) -> float:
        """
        Calcola il segnale del gene sui dati forniti.
        
        Args:
            data: Array numpy con i prezzi di chiusura
            
        Returns:
            Segnale normalizzato tra -1 e 1
        """
        period = int(float(self.params['period']))
        if len(data) < period + 1:
            return 0
            
        ma = self.calculate_ma(data)
        last_price = data[-1]
        last_ma = ma[-1]
        
        if np.isnan(last_ma):
            return 0
            
        # Calcola la distanza percentuale tra prezzo e media mobile
        distance_percent = (last_price - last_ma) / last_ma
        
        # Normalizza il segnale basandosi sulla distanza configurata
        signal = distance_percent / float(self.params['distance'])
        
        return np.clip(signal, -1, 1)
        
    def evaluate(self, data: np.ndarray) -> float:
        """
        Valuta le performance del gene sui dati forniti.
        
        Args:
            data: Array numpy con i prezzi di chiusura
            
        Returns:
            Punteggio di fitness del gene
        """
        period = int(float(self.params['period']))
        if len(data) < period + 1:
            return 0
            
        ma = self.calculate_ma(data)
        signals = np.zeros_like(data)
        
        # Genera segnali quando il prezzo attraversa la media mobile
        price_above_ma = data > ma
        # Segnali di acquisto quando il prezzo sale sopra la MA
        signals[1:][np.diff(price_above_ma.astype(int)) == 1] = 1
        # Segnali di vendita quando il prezzo scende sotto la MA
        signals[1:][np.diff(price_above_ma.astype(int)) == -1] = -1
        
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
        return float(fitness)