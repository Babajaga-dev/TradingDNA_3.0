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
    
    def __init__(self, name: str = 'atr', params: Optional[Dict[str, Any]] = None):
        """
        Inizializza il gene ATR.
        
        Args:
            name: Nome del gene (default: 'atr')
            params: Parametri specifici del gene (opzionale)
        """
        super().__init__(name, params)
        
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
        try:
            period = int(float(self.params['period']))
            
            if len(close) < period + 1:
                self.logger.warning("Serie temporale troppo corta per il calcolo ATR")
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
                
            self.logger.debug(f"ATR calcolato con successo: ultimo valore = {atr[-1]:.4f}")
            return atr
            
        except Exception as e:
            self.logger.error(f"Errore nel calcolo ATR: {str(e)}")
            return np.full_like(close, np.nan)
        
    def calculate_signal(self, data: Dict[str, np.ndarray]) -> float:
        """
        Calcola il segnale del gene sui dati forniti.
        
        Args:
            data: Dizionario con arrays numpy OHLCV
            
        Returns:
            Segnale normalizzato tra -1 e 1
        """
        try:
            if not all(k in data for k in ['high', 'low', 'close']):
                self.logger.error("Dati OHLCV mancanti per il calcolo ATR")
                return 0.0
                
            period = int(float(self.params['period']))
            if len(data['close']) < period + 1:
                self.logger.warning("Serie temporale troppo corta per il calcolo del segnale ATR")
                return 0.0
                
            atr = self.calculate_atr(data['high'], data['low'], data['close'])
            
            if np.isnan(atr[-1]):
                self.logger.warning("ATR non valido")
                return 0.0
                
            # Calcola le bande di volatilità
            multiplier = float(self.params['multiplier'])
            upper_band = data['close'] + (atr * multiplier)
            lower_band = data['close'] - (atr * multiplier)
            
            # Calcola la posizione del prezzo rispetto alle bande
            last_close = data['close'][-1]
            last_upper = upper_band[-1]
            last_lower = lower_band[-1]
            
            # Normalizza la distanza tra le bande
            band_width = last_upper - last_lower
            if band_width == 0:
                self.logger.warning("Ampiezza banda nulla")
                return 0.0
                
            # Calcola il segnale basato sulla posizione del prezzo
            position = (last_close - last_lower) / band_width
            signal = (position - 0.5) * -2  # Converte in range [-1, 1]
            
            # Modifica il segnale basandosi sul trend della volatilità
            volatility_trend = (atr[-1] / np.mean(atr[-20:])) - 1
            signal *= (1 + volatility_trend)  # Amplifica/riduce il segnale
            
            self.logger.debug(f"Segnale ATR calcolato: {signal:.4f}")
            return float(np.clip(signal, -1, 1))
            
        except Exception as e:
            self.logger.error(f"Errore nel calcolo del segnale ATR: {str(e)}")
            return 0.0
        
    def evaluate(self, data: Dict[str, np.ndarray]) -> float:
        """
        Valuta le performance del gene sui dati forniti.
        
        Args:
            data: Dizionario con arrays numpy OHLCV
            
        Returns:
            Punteggio di fitness del gene
        """
        try:
            if not all(k in data for k in ['high', 'low', 'close']):
                self.logger.error("Dati OHLCV mancanti per la valutazione ATR")
                return 0.0
                
            period = int(float(self.params['period']))
            if len(data['close']) < period + 1:
                self.logger.warning("Serie temporale troppo corta per la valutazione ATR")
                return 0.0
                
            atr = self.calculate_atr(data['high'], data['low'], data['close'])
            multiplier = float(self.params['multiplier'])
            
            # Calcola le bande di volatilità
            upper_band = data['close'] + (atr * multiplier)
            lower_band = data['close'] - (atr * multiplier)
            
            # Genera segnali quando il prezzo tocca le bande
            signals = np.zeros_like(data['close'])
            
            # Segnali di acquisto quando il prezzo tocca la banda inferiore
            signals[data['close'] <= lower_band] = 1
            # Segnali di vendita quando il prezzo tocca la banda superiore
            signals[data['close'] >= upper_band] = -1
            
            # Calcola i rendimenti
            returns = np.diff(data['close']) / data['close'][:-1]
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
            
            self.logger.debug(f"Valutazione ATR completata. Fitness: {fitness:.4f}")
            return float(fitness)
            
        except Exception as e:
            self.logger.error(f"Errore nella valutazione ATR: {str(e)}")
            return 0.0
