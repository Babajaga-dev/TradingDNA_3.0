"""
Volatility Breakout Gene
----------------------
Implementazione del gene Volatility Breakout per l'identificazione di breakout significativi.
"""

import numpy as np
from typing import Dict, Any, Optional
from .base import Gene

class VolatilityBreakoutGene(Gene):
    """Gene che implementa la strategia Volatility Breakout."""
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Inizializza il gene Volatility Breakout.
        
        Args:
            params: Parametri specifici del gene (opzionale)
        """
        super().__init__('volatility_breakout', params)
        
    def calculate_volatility_bands(self, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Calcola le bande di volatilità.
        
        Args:
            high: Array numpy con i prezzi massimi
            low: Array numpy con i prezzi minimi
            close: Array numpy con i prezzi di chiusura
            
        Returns:
            Tuple con array numpy contenenti banda superiore e inferiore
        """
        period = int(float(self.params['period']))
        multiplier = float(self.params['multiplier'])
        
        if len(close) < period:
            return np.full_like(close, np.nan), np.full_like(close, np.nan)
            
        # Calcola il range medio
        ranges = high - low
        avg_range = np.zeros_like(close)
        for i in range(period-1, len(close)):
            avg_range[i] = np.mean(ranges[i-period+1:i+1])
            
        # Calcola le bande
        upper_band = close + (avg_range * multiplier)
        lower_band = close - (avg_range * multiplier)
        
        return upper_band, lower_band
        
    def calculate_signal(self, data: np.ndarray) -> float:
        """
        Calcola il segnale del gene sui dati forniti.
        
        Args:
            data: Array numpy con i dati OHLC
            
        Returns:
            Segnale normalizzato tra -1 e 1
        """
        if len(data) < int(float(self.params['period'])):
            return 0
            
        high = data[:, 1]   # High prices
        low = data[:, 2]    # Low prices
        close = data[:, 3]  # Close prices
        
        # Calcola bande di volatilità
        upper_band, lower_band = self.calculate_volatility_bands(high, low, close)
        
        if np.isnan(upper_band[-1]) or np.isnan(lower_band[-1]):
            return 0
            
        # Calcola la forza del breakout
        breakout_threshold = float(self.params['breakout_threshold'])
        consolidation_periods = int(float(self.params['consolidation_periods']))
        
        # Verifica consolidamento precedente
        recent_range = (high[-consolidation_periods:] - low[-consolidation_periods:]) / close[-consolidation_periods:]
        avg_range = np.mean(recent_range)
        
        # Se il mercato è in consolidamento (range ridotto)
        if avg_range < breakout_threshold:
            # Calcola distanza dalle bande
            upper_distance = (upper_band[-1] - close[-1]) / close[-1]
            lower_distance = (close[-1] - lower_band[-1]) / close[-1]
            
            # Genera segnale basato sulla prossimità alle bande
            if upper_distance < breakout_threshold:
                signal = 1.0  # Potenziale breakout rialzista
            elif lower_distance < breakout_threshold:
                signal = -1.0  # Potenziale breakout ribassista
            else:
                signal = 0.0  # No breakout
        else:
            # Mercato già in movimento, nessun segnale
            signal = 0.0
            
        return np.clip(signal, -1, 1)
        
    def evaluate(self, data: np.ndarray) -> float:
        """
        Valuta le performance del gene sui dati forniti.
        
        Args:
            data: Array numpy con i dati OHLC
            
        Returns:
            Punteggio di fitness del gene
        """
        if len(data) < int(float(self.params['period'])):
            return 0
            
        high = data[:, 1]   # High prices
        low = data[:, 2]    # Low prices
        close = data[:, 3]  # Close prices
        
        # Calcola bande di volatilità
        upper_band, lower_band = self.calculate_volatility_bands(high, low, close)
        
        # Genera segnali sui breakout
        signals = np.zeros_like(close)
        breakout_threshold = float(self.params['breakout_threshold'])
        consolidation_periods = int(float(self.params['consolidation_periods']))
        
        for i in range(consolidation_periods, len(close)):
            # Verifica consolidamento
            recent_range = (high[i-consolidation_periods:i] - low[i-consolidation_periods:i]) / close[i-consolidation_periods:i]
            avg_range = np.mean(recent_range)
            
            if avg_range < breakout_threshold:
                # Calcola distanze dalle bande
                upper_distance = (upper_band[i] - close[i]) / close[i]
                lower_distance = (close[i] - lower_band[i]) / close[i]
                
                # Segnali di breakout
                if upper_distance < breakout_threshold:
                    signals[i] = 1
                elif lower_distance < breakout_threshold:
                    signals[i] = -1
        
        # Calcola i rendimenti
        returns = np.diff(close) / close[:-1]
        signal_returns = signals[:-1] * returns
        
        # Metriche di valutazione
        win_rate = np.sum(signal_returns > 0) / np.sum(signals != 0) if np.sum(signals != 0) > 0 else 0
        avg_return = np.mean(signal_returns[signals[:-1] != 0]) if np.sum(signals[:-1] != 0) > 0 else 0
        
        # Penalizza troppi segnali
        signal_frequency = np.sum(signals != 0) / len(signals)
        frequency_penalty = np.exp(-signal_frequency * 10)
        
        # Premia breakout dopo consolidamento
        consolidation_score = np.mean(
            [1 - avg_range for avg_range in recent_range if avg_range < breakout_threshold]
        ) if len(recent_range) > 0 else 0
        
        fitness = (win_rate * 0.3 + avg_return * 0.3 + frequency_penalty * 0.2 + consolidation_score * 0.2)
        return float(fitness)
