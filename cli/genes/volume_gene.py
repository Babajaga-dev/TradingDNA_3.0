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
        mask = (volume_ma_padded != 0) & ~np.isnan(volume_ma_padded)
        volume_ratio[mask] = volumes[mask] / volume_ma_padded[mask]
        
        return volume_ma_padded, volume_ratio
        
    def calculate_trend(self, data: np.ndarray, window: int = 10) -> float:
        """
        Calcola il trend dei dati usando variazioni percentuali.
        
        Args:
            data: Array numpy con i dati
            window: Finestra temporale per il calcolo
            
        Returns:
            Trend normalizzato tra -1 e 1
        """
        if len(data) < window:
            return 0
            
        recent_data = data[-window:]
        if recent_data[0] == 0:
            return 0
            
        # Calcola variazione percentuale totale
        total_change = (recent_data[-1] - recent_data[0]) / recent_data[0]
        
        # Calcola variazioni giornaliere
        daily_changes = np.diff(recent_data) / recent_data[:-1]
        
        # Combina trend totale con consistenza delle variazioni giornaliere
        consistency = np.mean(np.sign(daily_changes) == np.sign(total_change))
        trend_strength = total_change * (1 + consistency)
        
        return np.clip(trend_strength, -1, 1)
        
    def calculate_signal(self, data: np.ndarray) -> float:
        """
        Calcola il segnale del gene sui dati forniti.
        
        Args:
            data: Array numpy con i dati OHLC
            
        Returns:
            Segnale normalizzato tra -1 e 1
        """
        period = int(float(self.params['period']))
        if len(data) < period:
            return 0
            
        volumes = data[:, 1]  # Volume (colonna 1)
        prices = data[:, 0]   # Price (colonna 0)
        
        # Verifica dati validi
        if np.all(volumes == 0) or np.all(prices == 0) or np.any(np.isnan(volumes)) or np.any(np.isnan(prices)):
            return 0
            
        # Calcola metriche volume
        volume_ma, volume_ratio = self.calculate_volume_metrics(volumes)
        
        if len(volume_ratio) < period or np.isnan(volume_ratio[-1]):
            return 0
            
        # Calcola trend del volume e prezzo
        volume_trend = self.calculate_trend(volumes)
        price_trend = self.calculate_trend(prices)
        
        # Calcola variazione prezzo recente
        if len(prices) >= 2 and prices[-2] != 0:
            price_change = (prices[-1] - prices[-2]) / prices[-2]
        else:
            price_change = 0
            
        # Threshold per il volume ratio
        threshold = float(self.params['threshold'])
        min_price_change = float(self.params['min_price_change'])
        
        # Calcola segnale base dal trend del volume
        base_signal = volume_trend
        
        # Rafforza il segnale basato sul volume ratio
        if volume_ratio[-1] > threshold * 2:  # Volume molto alto
            base_signal = max(base_signal, 0.7)
        elif volume_ratio[-1] > threshold:  # Volume alto
            base_signal = max(base_signal, 0.5)
        elif volume_ratio[-1] < 1/(threshold * 2):  # Volume molto basso
            base_signal = min(base_signal, -0.7)
        elif volume_ratio[-1] < 1/threshold:  # Volume basso
            base_signal = min(base_signal, -0.5)
            
        # Analisi della divergenza prezzo-volume
        if abs(price_trend) > 0.1:  # Trend significativo del prezzo
            if np.sign(price_trend) != np.sign(base_signal):
                # Divergenza: inverti il segnale
                base_signal = -abs(base_signal) * 1.2
            else:
                # Conferma: rafforza il segnale
                base_signal *= 1.5
                # Se entrambi i trend sono forti, rafforza ulteriormente
                if abs(price_trend) > 0.15 and abs(volume_trend) > 0.15:
                    base_signal *= 1.3
                
        # Gestione breakout
        if volume_ratio[-1] > threshold * 2 and abs(price_change) > min_price_change * 2:
            # Breakout confermato da volume e prezzo
            breakout_signal = np.sign(price_change) * 0.8
            if np.sign(volume_trend) == np.sign(price_change):
                breakout_signal = np.sign(price_change) * 0.9  # Rafforza ulteriormente
            base_signal = breakout_signal
            
        # Assicura che il segnale sia abbastanza forte per i trend chiari
        if abs(volume_trend) > 0.3:
            base_signal = np.sign(base_signal) * max(abs(base_signal), 0.6)
            
        # Amplifica il segnale finale
        final_signal = base_signal * 1.5
            
        return np.clip(final_signal, -1, 1)
        
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
            
        volumes = data[:, 1]  # Volume (colonna 1)
        prices = data[:, 0]   # Price (colonna 0)
        
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
