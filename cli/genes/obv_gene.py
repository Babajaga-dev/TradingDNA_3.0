"""
On Balance Volume (OBV) Gene
--------------------------
Implementazione del gene OBV per l'analisi del flusso di volume.
"""

import numpy as np
from typing import Dict, Any, Optional
from .base import Gene

class OBVGene(Gene):
    """Gene che implementa l'indicatore On Balance Volume."""
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Inizializza il gene OBV.
        
        Args:
            params: Parametri specifici del gene (opzionale)
        """
        super().__init__('obv', params)
        
    def calculate_obv(self, close: np.ndarray, volume: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Calcola l'On Balance Volume e la sua media mobile.
        
        Args:
            close: Array numpy con i prezzi di chiusura
            volume: Array numpy con i volumi
            
        Returns:
            Tuple con array numpy contenenti OBV e media mobile OBV
        """
        period = int(float(self.params['period']))
        
        if len(close) < 2:
            return np.array([0]), np.array([0])
            
        # Calcola la direzione del prezzo
        price_direction = np.diff(close)
        price_direction = np.insert(price_direction, 0, 0)  # Padding per il primo elemento
        
        # Calcola OBV
        obv = np.zeros_like(volume)
        obv[0] = volume[0]  # Primo valore è il volume iniziale
        
        # Se il prezzo sale, aggiungi il volume
        # Se il prezzo scende, sottrai il volume
        # Se il prezzo è invariato, volume è 0
        for i in range(1, len(close)):
            if price_direction[i] > 0:
                obv[i] = obv[i-1] + volume[i]
            elif price_direction[i] < 0:
                obv[i] = obv[i-1] - volume[i]
            else:
                obv[i] = obv[i-1]
                
        # Calcola media mobile dell'OBV
        weights = np.ones(period)
        weights /= weights.sum()
        obv_ma = np.convolve(obv, weights, mode='valid')
        
        # Padding per mantenere la dimensione originale
        obv_ma_padded = np.full_like(obv, np.nan)
        obv_ma_padded[period-1:] = obv_ma
        
        return obv, obv_ma_padded
        
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
            
        close = data[:, 3]  # Close price
        volume = data[:, 4]  # Volume
        
        # Calcola OBV e media mobile
        obv, obv_ma = self.calculate_obv(close, volume)
        
        if np.isnan(obv_ma[-1]):
            return 0
            
        # Calcola divergenza tra OBV e prezzo
        obv_change = (obv[-1] - obv[-2]) / abs(obv[-2]) if obv[-2] != 0 else 0
        price_change = (close[-1] - close[-2]) / close[-2]
        
        # Threshold per la divergenza
        threshold = float(self.params['threshold'])
        
        # Calcola segnale base dalla divergenza OBV/prezzo
        if abs(obv_change) > threshold:
            # Divergenza significativa
            if np.sign(obv_change) != np.sign(price_change):
                # Divergenza negativa/positiva
                signal = -np.sign(price_change)
            else:
                # Conferma trend
                signal = np.sign(price_change) * 0.5
        else:
            # Nessuna divergenza significativa
            signal = 0
            
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
            
        close = data[:, 3]  # Close price
        volume = data[:, 4]  # Volume
        
        # Calcola OBV e media mobile
        obv, obv_ma = self.calculate_obv(close, volume)
        
        # Genera segnali basati sulla divergenza
        signals = np.zeros_like(close)
        
        # Calcola variazioni
        obv_changes = np.diff(obv) / np.abs(obv[:-1])
        obv_changes = np.append(0, obv_changes)  # Padding per primo elemento
        price_changes = np.diff(close) / close[:-1]
        price_changes = np.append(0, price_changes)  # Padding per primo elemento
        
        # Threshold per la divergenza
        threshold = float(self.params['threshold'])
        
        # Identifica divergenze significative
        significant_changes = abs(obv_changes) > threshold
        divergences = np.sign(obv_changes) != np.sign(price_changes)
        
        # Segnali di acquisto/vendita su divergenze significative
        signals[significant_changes & divergences] = -np.sign(price_changes[significant_changes & divergences])
        
        # Calcola i rendimenti
        returns = np.diff(close) / close[:-1]
        signal_returns = signals[:-1] * returns
        
        # Metriche di valutazione
        win_rate = np.sum(signal_returns > 0) / np.sum(signals != 0) if np.sum(signals != 0) > 0 else 0
        avg_return = np.mean(signal_returns[signals[:-1] != 0]) if np.sum(signals[:-1] != 0) > 0 else 0
        
        # Penalizza troppi segnali
        signal_frequency = np.sum(signals != 0) / len(signals)
        frequency_penalty = np.exp(-signal_frequency * 10)
        
        # Premia divergenze significative
        divergence_score = np.mean(abs(obv_changes)[signals != 0]) if np.sum(signals != 0) > 0 else 0
        
        fitness = (win_rate * 0.3 + avg_return * 0.3 + frequency_penalty * 0.2 + divergence_score * 0.2)
        return float(fitness)
