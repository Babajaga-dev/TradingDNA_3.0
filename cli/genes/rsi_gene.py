"""
RSI Gene
--------
Implementazione del gene RSI (Relative Strength Index).
"""

import numpy as np
from typing import Dict, Any, Optional
from .base import Gene

class RSIGene(Gene):
    """Gene che implementa l'indicatore RSI."""
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Inizializza il gene RSI.
        
        Args:
            params: Parametri specifici del gene (opzionale)
        """
        super().__init__('rsi', params)
        
    def calculate_rsi(self, data: np.ndarray) -> np.ndarray:
        """
        Calcola l'indicatore RSI.
        
        Args:
            data: Array numpy con i prezzi di chiusura
            
        Returns:
            Array numpy con i valori RSI
        """
        # Calcola le differenze
        delta = np.diff(data)
        
        # Separa guadagni e perdite
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        
        # Calcola le medie mobili di guadagni e perdite
        period = int(self.params['period'])
        avg_gain = np.zeros_like(data)
        avg_loss = np.zeros_like(data)
        
        # Prima media
        avg_gain[period] = np.mean(gain[:period])
        avg_loss[period] = np.mean(loss[:period])
        
        # Calcola le medie successive
        for i in range(period + 1, len(data)):
            avg_gain[i] = (avg_gain[i-1] * (period-1) + gain[i-1]) / period
            avg_loss[i] = (avg_loss[i-1] * (period-1) + loss[i-1]) / period
            
        # Calcola RSI
        rs = avg_gain[period:] / np.where(avg_loss[period:] != 0, avg_loss[period:], 1e-8)
        rsi = 100 - (100 / (1 + rs))
        
        # Padding per mantenere la dimensione originale
        result = np.full_like(data, np.nan)
        result[period:] = rsi
        
        return result
        
    def calculate_signal(self, data: np.ndarray) -> float:
        """
        Calcola il segnale del gene sui dati forniti.
        
        Args:
            data: Array numpy con i prezzi di chiusura
            
        Returns:
            Segnale normalizzato tra -1 e 1
        """
        period = int(self.params['period'])
        if len(data) < period + 1:
            return 0
            
        rsi = self.calculate_rsi(data)
        last_rsi = rsi[-1]
        
        if np.isnan(last_rsi):
            return 0
            
        # Normalizza il segnale tra -1 e 1 basandosi sui livelli di ipercomprato/ipervenduto
        if last_rsi > self.params['overbought']:
            signal = -1 * (last_rsi - self.params['overbought']) / (100 - self.params['overbought'])
        elif last_rsi < self.params['oversold']:
            signal = (self.params['oversold'] - last_rsi) / self.params['oversold']
        else:
            # Zona neutrale
            mid_point = (self.params['overbought'] + self.params['oversold']) / 2
            signal = (mid_point - last_rsi) / (self.params['overbought'] - self.params['oversold']) * 2
            
        return np.clip(signal, -1, 1)
        
    def evaluate(self, data: np.ndarray) -> float:
        """
        Valuta le performance del gene sui dati forniti.
        
        Args:
            data: Array numpy con i prezzi di chiusura
            
        Returns:
            Punteggio di fitness del gene
        """
        period = int(self.params['period'])
        if len(data) < period + 1:
            return 0
            
        rsi = self.calculate_rsi(data)
        signals = np.zeros_like(data)
        
        # Genera segnali
        signals[rsi > self.params['overbought']] = -1  # Segnali di vendita
        signals[rsi < self.params['oversold']] = 1     # Segnali di acquisto
        
        # Calcola i rendimenti
        returns = np.diff(data) / data[:-1]
        signal_returns = signals[:-1] * returns
        
        # Metriche di valutazione
        win_rate = np.sum(signal_returns > 0) / np.sum(signals != 0) if np.sum(signals != 0) > 0 else 0
        avg_return = np.mean(signal_returns[signals[:-1] != 0]) if np.sum(signals[:-1] != 0) > 0 else 0
        
        # Penalizza troppi segnali
        signal_frequency = np.sum(signals != 0) / len(signals)
        frequency_penalty = np.exp(-signal_frequency * 10)  # Penalizza alta frequenza
        
        fitness = (win_rate * 0.4 + avg_return * 0.4 + frequency_penalty * 0.2)
        return float(fitness)
