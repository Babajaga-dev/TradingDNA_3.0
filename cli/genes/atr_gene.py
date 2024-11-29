"""
Average True Range (ATR) Gene
----------------------------
Implementazione del gene ATR per l'analisi della volatilità.
"""

import numpy as np
from typing import Dict, Any, Optional
from .base import Gene

class ATRGene(Gene):
    """Gene che implementa l'indicatore Average True Range."""
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Inizializza il gene ATR.
        
        Args:
            params: Parametri specifici del gene (opzionale)
        """
        super().__init__('atr', params)
        
    def calculate_atr(self, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
        """
        Calcola l'Average True Range.
        
        Args:
            high: Array numpy con i prezzi massimi
            low: Array numpy con i prezzi minimi
            close: Array numpy con i prezzi di chiusura
            
        Returns:
            Array numpy con i valori ATR
        """
        period = int(float(self.params['period']))
        
        if len(close) < period + 1:
            return np.full_like(close, np.nan)
            
        # Calcola True Range
        prev_close = np.roll(close, 1)
        prev_close[0] = close[0]
        
        tr1 = high - low  # High-Low
        tr2 = np.abs(high - prev_close)  # |High-PrevClose|
        tr3 = np.abs(low - prev_close)   # |Low-PrevClose|
        
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        
        # Calcola ATR usando EMA
        atr = np.zeros_like(close)
        atr[period-1] = np.mean(tr[:period])  # Primo valore è SMA
        
        # Calcola EMA del True Range
        alpha = 2 / (period + 1)
        for i in range(period, len(close)):
            atr[i] = tr[i] * alpha + atr[i-1] * (1 - alpha)
            
        return atr
        
    def calculate_signal(self, data: np.ndarray) -> float:
        """
        Calcola il segnale del gene sui dati forniti.
        
        Args:
            data: Array numpy con i dati OHLC
            
        Returns:
            Segnale normalizzato tra -1 e 1
        """
        if len(data) < int(float(self.params['period'])) + 1:
            return 0
            
        high = data[:, 1]   # High prices
        low = data[:, 2]    # Low prices
        close = data[:, 3]  # Close prices
        
        atr = self.calculate_atr(high, low, close)
        
        if np.isnan(atr[-1]):
            return 0
            
        # Calcola le bande di volatilità
        multiplier = float(self.params['multiplier'])
        upper_band = close + (atr * multiplier)
        lower_band = close - (atr * multiplier)
        
        # Calcola la posizione del prezzo rispetto alle bande
        last_close = close[-1]
        last_upper = upper_band[-1]
        last_lower = lower_band[-1]
        
        # Normalizza la distanza tra le bande
        band_width = last_upper - last_lower
        if band_width == 0:
            return 0
            
        # Calcola il segnale basato sulla posizione del prezzo
        # rispetto alle bande di volatilità
        position = (last_close - last_lower) / band_width
        signal = (position - 0.5) * -2  # Converte in range [-1, 1]
        
        # Modifica il segnale basandosi sul trend della volatilità
        volatility_trend = (atr[-1] / np.mean(atr[-20:])) - 1
        signal *= (1 + volatility_trend)  # Amplifica/riduce il segnale
        
        return np.clip(signal, -1, 1)
        
    def evaluate(self, data: np.ndarray) -> float:
        """
        Valuta le performance del gene sui dati forniti.
        
        Args:
            data: Array numpy con i dati OHLC
            
        Returns:
            Punteggio di fitness del gene
        """
        if len(data) < int(float(self.params['period'])) + 1:
            return 0
            
        high = data[:, 1]   # High prices
        low = data[:, 2]    # Low prices
        close = data[:, 3]  # Close prices
        
        atr = self.calculate_atr(high, low, close)
        multiplier = float(self.params['multiplier'])
        
        # Calcola le bande di volatilità
        upper_band = close + (atr * multiplier)
        lower_band = close - (atr * multiplier)
        
        # Genera segnali quando il prezzo tocca le bande
        signals = np.zeros_like(close)
        
        # Segnali di acquisto quando il prezzo tocca la banda inferiore
        signals[close <= lower_band] = 1
        # Segnali di vendita quando il prezzo tocca la banda superiore
        signals[close >= upper_band] = -1
        
        # Calcola i rendimenti
        returns = np.diff(close) / close[:-1]
        signal_returns = signals[:-1] * returns
        
        # Metriche di valutazione
        win_rate = np.sum(signal_returns > 0) / np.sum(signals != 0) if np.sum(signals != 0) > 0 else 0
        avg_return = np.mean(signal_returns[signals[:-1] != 0]) if np.sum(signals[:-1] != 0) > 0 else 0
        
        # Penalizza troppi segnali
        signal_frequency = np.sum(signals != 0) / len(signals)
        frequency_penalty = np.exp(-signal_frequency * 10)
        
        # Premia segnali durante alta volatilità
        volatility_score = np.mean(atr[signals != 0]) / np.mean(atr) if np.sum(signals != 0) > 0 else 0
        
        fitness = (win_rate * 0.3 + avg_return * 0.3 + frequency_penalty * 0.2 + volatility_score * 0.2)
        return float(fitness)
