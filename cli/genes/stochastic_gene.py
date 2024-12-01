"""
Stochastic Oscillator Gene
-------------------------
Implementazione del gene Stochastic Oscillator.
"""

import numpy as np
from typing import Dict, Any, Optional, Tuple
from .base import Gene

class StochasticGene(Gene):
    """Gene che implementa l'indicatore Stochastic Oscillator."""
    
    def __init__(self, name: str = 'stochastic', params: Optional[Dict[str, Any]] = None):
        """
        Inizializza il gene Stochastic.
        
        Args:
            name: Nome del gene (default: 'stochastic')
            params: Parametri specifici del gene (opzionale)
        """
        super().__init__(name, params)
        
    def calculate_stochastic(self, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calcola l'indicatore Stochastic Oscillator (%K e %D).
        
        Args:
            high: Array numpy con i prezzi massimi
            low: Array numpy con i prezzi minimi
            close: Array numpy con i prezzi di chiusura
            
        Returns:
            Tuple con array numpy contenenti %K e %D
        """
        try:
            k_period = int(float(self.params['k_period']))
            d_period = int(float(self.params['d_period']))
            smooth_k = int(float(self.params['smooth_k']))
            
            self.logger.debug(f"Calcolo Stochastic con parametri: k={k_period}, d={d_period}, smooth={smooth_k}")
            
            if len(close) < k_period:
                self.logger.warning("Serie temporale troppo corta per il calcolo Stochastic")
                return np.full_like(close, np.nan), np.full_like(close, np.nan)
                
            # Calcola %K
            lowest_low = np.array([np.min(low[max(0, i-k_period+1):i+1]) 
                                 for i in range(len(low))])
            highest_high = np.array([np.max(high[max(0, i-k_period+1):i+1]) 
                                   for i in range(len(high))])
            
            k_line = np.zeros_like(close)
            mask = (highest_high - lowest_low) != 0
            k_line[mask] = 100 * ((close[mask] - lowest_low[mask]) / 
                                 (highest_high[mask] - lowest_low[mask]))
            
            # Applica smoothing a %K se richiesto
            if smooth_k > 1:
                smooth_k_line = np.zeros_like(k_line)
                for i in range(smooth_k-1, len(k_line)):
                    smooth_k_line[i] = np.mean(k_line[i-smooth_k+1:i+1])
                k_line = smooth_k_line
            
            # Calcola %D (media mobile di %K)
            d_line = np.zeros_like(close)
            for i in range(d_period-1, len(close)):
                d_line[i] = np.mean(k_line[i-d_period+1:i+1])
                
            self.logger.debug(f"Stochastic calcolato: K={k_line[-1]:.1f}, D={d_line[-1]:.1f}")
            return k_line, d_line
            
        except Exception as e:
            self.logger.error(f"Errore nel calcolo Stochastic: {str(e)}")
            return np.full_like(close, np.nan), np.full_like(close, np.nan)
        
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
                self.logger.error("Dati OHLCV mancanti per il calcolo Stochastic")
                return 0.0
                
            k_period = int(float(self.params['k_period']))
            if len(data['close']) < k_period:
                self.logger.warning("Serie temporale troppo corta per il calcolo del segnale Stochastic")
                return 0.0
                
            k_line, d_line = self.calculate_stochastic(data['high'], data['low'], data['close'])
            
            if np.isnan(k_line[-1]) or np.isnan(d_line[-1]):
                self.logger.warning("Impossibile calcolare il segnale Stochastic: valori NaN")
                return 0.0
                
            # Ottieni le soglie di ipercomprato/ipervenduto
            overbought = float(self.params['overbought'])
            oversold = float(self.params['oversold'])
            
            # Calcola il segnale basato sulla posizione di %K e %D
            k_last = k_line[-1]
            d_last = d_line[-1]
            
            # Segnale base dalla posizione rispetto alle soglie
            if k_last < oversold:
                base_signal = 1.0  # Segnale di acquisto
            elif k_last > overbought:
                base_signal = -1.0  # Segnale di vendita
            else:
                # Normalizza il segnale tra le soglie
                base_signal = (((k_last - oversold) / (overbought - oversold)) - 0.5) * -2
                
            # Modifica il segnale basandosi sull'incrocio di %K e %D
            cross_signal = np.sign(k_last - d_last)
            
            # Combina i segnali
            final_signal = (base_signal * 0.7 + cross_signal * 0.3)
            
            self.logger.debug(f"Segnale Stochastic calcolato: {final_signal:.2f}")
            return float(np.clip(final_signal, -1, 1))
            
        except Exception as e:
            self.logger.error(f"Errore nel calcolo del segnale Stochastic: {str(e)}")
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
                self.logger.error("Dati OHLCV mancanti per la valutazione Stochastic")
                return 0.0
                
            k_period = int(float(self.params['k_period']))
            if len(data['close']) < k_period:
                self.logger.warning("Serie temporale troppo corta per la valutazione Stochastic")
                return 0.0
                
            k_line, d_line = self.calculate_stochastic(data['high'], data['low'], data['close'])
            
            # Genera segnali quando %K incrocia %D
            signals = np.zeros_like(data['close'])
            k_above_d = k_line > d_line
            
            # Segnali di acquisto quando %K incrocia %D verso l'alto
            signals[1:][np.diff(k_above_d.astype(int)) == 1] = 1
            # Segnali di vendita quando %K incrocia %D verso il basso
            signals[1:][np.diff(k_above_d.astype(int)) == -1] = -1
            
            # Calcola i rendimenti
            returns = np.diff(data['close']) / data['close'][:-1]
            signal_returns = signals[:-1] * returns
            
            # Metriche di valutazione
            win_rate = np.sum(signal_returns > 0) / np.sum(signals != 0) if np.sum(signals != 0) > 0 else 0
            avg_return = np.mean(signal_returns[signals[:-1] != 0]) if np.sum(signals[:-1] != 0) > 0 else 0
            
            # Penalizza troppi segnali
            signal_frequency = np.sum(signals != 0) / len(signals)
            frequency_penalty = np.exp(-signal_frequency * 10)
            
            # Premia segnali nelle zone di ipercomprato/ipervenduto
            overbought = float(self.params['overbought'])
            oversold = float(self.params['oversold'])
            good_zones = ((k_line < oversold) & (signals == 1)) | ((k_line > overbought) & (signals == -1))
            zone_score = np.sum(good_zones) / np.sum(signals != 0) if np.sum(signals != 0) > 0 else 0
            
            fitness = (win_rate * 0.3 + avg_return * 0.3 + frequency_penalty * 0.2 + zone_score * 0.2)
            
            self.logger.debug(f"Valutazione Stochastic completata. Fitness: {fitness:.4f}")
            return float(fitness)
            
        except Exception as e:
            self.logger.error(f"Errore nella valutazione Stochastic: {str(e)}")
            return 0.0
