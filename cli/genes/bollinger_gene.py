"""
Bollinger Bands Gene
-------------------
Implementazione del gene Bollinger Bands.
"""

import numpy as np
import logging
from typing import Dict, Any, Optional
from .base import Gene

# Configura il logger per questo modulo
logger = logging.getLogger(__name__)

class BollingerGene(Gene):
    """Gene che implementa l'indicatore Bollinger Bands."""
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Inizializza il gene Bollinger Bands.
        
        Args:
            params: Parametri specifici del gene (opzionale)
        """
        logger.debug("Inizializzazione BollingerGene")
        super().__init__('bollinger', params)
        
    def calculate_bands(self, data: np.ndarray) -> tuple:
        """
        Calcola le Bollinger Bands.
        
        Args:
            data: Array numpy con i prezzi di chiusura
            
        Returns:
            Tuple con (middle_band, upper_band, lower_band)
        """
        period = int(float(self.params['period']))
        std_dev = float(self.params['std_dev'])
        
        logger.debug(f"Calcolo Bollinger Bands con parametri: period={period}, std_dev={std_dev}")
        
        if len(data) < period:
            logger.warning("Serie temporale troppo corta per il calcolo delle Bollinger Bands")
            return np.full_like(data, np.nan), np.full_like(data, np.nan), np.full_like(data, np.nan)
            
        # Calcola la media mobile (middle band)
        weights = np.ones(period)
        weights /= weights.sum()
        middle_band = np.full_like(data, np.nan)
        sma = np.convolve(data, weights, mode='valid')
        middle_band[period-1:] = sma
        
        # Calcola le deviazioni standard
        std = np.full_like(data, np.nan)
        for i in range(period-1, len(data)):
            std[i] = np.std(data[i-period+1:i+1])
            
        # Calcola le bande superiori e inferiori
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        logger.debug("Calcolo Bollinger Bands completato")
        return middle_band, upper_band, lower_band
        
    def calculate_signal(self, data: np.ndarray) -> float:
        """
        Calcola il segnale del gene sui dati forniti.
        
        Args:
            data: Array numpy con i prezzi di chiusura
            
        Returns:
            Segnale normalizzato tra -1 e 1
        """
        logger.debug("Calcolo segnale Bollinger Bands")
        period = int(float(self.params['period']))
        if len(data) < period:
            logger.warning("Serie temporale troppo corta per il calcolo del segnale Bollinger")
            return 0
            
        middle_band, upper_band, lower_band = self.calculate_bands(data)
        
        if np.isnan(middle_band[-1]):
            logger.warning("Impossibile calcolare il segnale Bollinger: valori NaN")
            return 0
            
        last_price = data[-1]
        band_width = upper_band[-1] - lower_band[-1]
        
        if band_width == 0:
            logger.warning("Ampiezza delle bande nulla, impossibile calcolare il segnale")
            return 0
            
        # Calcola la posizione relativa del prezzo all'interno delle bande
        position = (last_price - middle_band[-1]) / (band_width / 2)
        
        # Normalizza il segnale basandosi sulla percentuale di tocco configurata
        touch_percentage = float(self.params['touch_percentage'])
        signal = position / touch_percentage
        
        logger.debug(f"Segnale Bollinger calcolato: {signal}")
        return np.clip(signal, -1, 1)
        
    def evaluate(self, data: np.ndarray) -> float:
        """
        Valuta le performance del gene sui dati forniti.
        
        Args:
            data: Array numpy con i prezzi di chiusura
            
        Returns:
            Punteggio di fitness del gene
        """
        logger.debug("Inizio valutazione Bollinger Bands")
        period = int(float(self.params['period']))
        if len(data) < period:
            logger.warning("Serie temporale troppo corta per la valutazione Bollinger")
            return 0
            
        middle_band, upper_band, lower_band = self.calculate_bands(data)
        signals = np.zeros_like(data)
        
        # Genera segnali quando il prezzo tocca le bande
        price_above_upper = data > upper_band
        price_below_lower = data < lower_band
        
        # Segnali di vendita quando il prezzo tocca la banda superiore
        signals[price_above_upper] = -1
        # Segnali di acquisto quando il prezzo tocca la banda inferiore
        signals[price_below_lower] = 1
        
        # Calcola i rendimenti
        returns = np.diff(data) / data[:-1]
        signal_returns = signals[:-1] * returns
        
        # Metriche di valutazione
        win_rate = np.sum(signal_returns > 0) / np.sum(signals != 0) if np.sum(signals != 0) > 0 else 0
        avg_return = np.mean(signal_returns[signals[:-1] != 0]) if np.sum(signals[:-1] != 0) > 0 else 0
        
        # Penalizza troppi segnali
        signal_frequency = np.sum(signals != 0) / len(signals)
        frequency_penalty = np.exp(-signal_frequency * 10)  # Penalizza alta frequenza
        
        # Calcola mean reversion score
        mean_reversion_signals = np.sum((data > upper_band) | (data < lower_band))
        mean_reversion_score = np.exp(-mean_reversion_signals / len(data) * 5)  # Premia il ritorno alla media
        
        fitness = (win_rate * 0.3 + avg_return * 0.3 + frequency_penalty * 0.2 + mean_reversion_score * 0.2)
        logger.debug(f"Valutazione Bollinger completata. Fitness: {fitness}")
        return float(fitness)
