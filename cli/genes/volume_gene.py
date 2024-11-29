"""
Volume Gene
----------
Implementazione del gene Volume per l'analisi dei volumi.
"""

import numpy as np
from typing import Dict, Any, Optional
from .base import Gene

class VolumeGene(Gene):
    """Gene che implementa l'analisi dei volumi."""
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Inizializza il gene Volume.
        
        Args:
            params: Parametri specifici del gene (opzionale)
        """
        super().__init__('volume', params)
        
    def calculate_volume_metrics(self, volumes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Calcola le metriche di volume.
        
        Args:
            volumes: Array numpy con i volumi
            
        Returns:
            Tuple con array numpy contenenti media mobile e ratio
        """
        period = int(float(self.params['period']))
        
        if len(volumes) < period:
            return np.full_like(volumes, np.nan), np.full_like(volumes, np.nan)
            
        # Calcola media mobile dei volumi
        weights = np.ones(period)
        weights /= weights.sum()
        volume_ma = np.convolve(volumes, weights, mode='valid')
        
        # Padding per mantenere la dimensione originale
        volume_ma_padded = np.full_like(volumes, np.nan)
        volume_ma_padded[period-1:] = volume_ma
        
        # Calcola volume ratio (volume corrente / media mobile)
        volume_ratio = np.zeros_like(volumes)
        mask = volume_ma_padded != 0
        volume_ratio[mask] = volumes[mask] / volume_ma_padded[mask]
        
        return volume_ma_padded, volume_ratio
        
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
            
        volumes = data[:, 4]  # Volume
        prices = data[:, 3]   # Close price
        
        # Calcola metriche volume
        volume_ma, volume_ratio = self.calculate_volume_metrics(volumes)
        
        if np.isnan(volume_ratio[-1]):
            return 0
            
        # Calcola variazione prezzo
        price_change = (prices[-1] - prices[-2]) / prices[-2]
        
        # Threshold per il volume ratio
        threshold = float(self.params['threshold'])
        
        # Calcola segnale base dal volume ratio
        if volume_ratio[-1] > threshold:
            base_signal = 1.0  # Volume sopra la media
        elif volume_ratio[-1] < 1/threshold:
            base_signal = -1.0  # Volume sotto la media
        else:
            base_signal = 0.0  # Volume nella norma
            
        # Modifica il segnale basandosi sulla direzione del prezzo
        if abs(price_change) > float(self.params['min_price_change']):
            signal = base_signal * np.sign(price_change)
        else:
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
            
        volumes = data[:, 4]  # Volume
        prices = data[:, 3]   # Close price
        
        # Calcola metriche volume
        volume_ma, volume_ratio = self.calculate_volume_metrics(volumes)
        
        # Genera segnali quando il volume ratio supera le soglie
        threshold = float(self.params['threshold'])
        signals = np.zeros_like(prices)
        
        # Calcola variazioni prezzo
        price_changes = np.diff(prices) / prices[:-1]
        price_changes = np.append(0, price_changes)  # Padding per mantenere dimensione
        
        # Segnali quando volume e prezzo confermano la direzione
        high_volume = volume_ratio > threshold
        low_volume = volume_ratio < 1/threshold
        significant_price = abs(price_changes) > float(self.params['min_price_change'])
        
        # Segnali di acquisto con alto volume e prezzo in salita
        signals[(high_volume) & (price_changes > 0) & significant_price] = 1
        # Segnali di vendita con alto volume e prezzo in discesa
        signals[(high_volume) & (price_changes < 0) & significant_price] = -1
        
        # Calcola i rendimenti
        returns = np.diff(prices) / prices[:-1]
        signal_returns = signals[:-1] * returns
        
        # Metriche di valutazione
        win_rate = np.sum(signal_returns > 0) / np.sum(signals != 0) if np.sum(signals != 0) > 0 else 0
        avg_return = np.mean(signal_returns[signals[:-1] != 0]) if np.sum(signals[:-1] != 0) > 0 else 0
        
        # Penalizza troppi segnali
        signal_frequency = np.sum(signals != 0) / len(signals)
        frequency_penalty = np.exp(-signal_frequency * 10)
        
        # Premia segnali con alto volume
        volume_score = np.mean(volume_ratio[signals != 0]) if np.sum(signals != 0) > 0 else 0
        
        fitness = (win_rate * 0.3 + avg_return * 0.3 + frequency_penalty * 0.2 + volume_score * 0.2)
        return float(fitness)
