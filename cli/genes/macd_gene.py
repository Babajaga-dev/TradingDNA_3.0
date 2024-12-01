"""
MACD Gene
---------
Implementazione del gene MACD (Moving Average Convergence Divergence).
"""

import numpy as np
from typing import Dict, Any, Optional
from .base import Gene

class MACDGene(Gene):
    """Gene che implementa l'indicatore MACD."""
    
    def __init__(self, name: str = 'macd', params: Optional[Dict[str, Any]] = None):
        """
        Inizializza il gene MACD.
        
        Args:
            name: Nome del gene (default: 'macd')
            params: Parametri specifici del gene (opzionale)
        """
        super().__init__(name, params)
        
    def calculate_macd(self, data: np.ndarray) -> tuple:
        """
        Calcola l'indicatore MACD.
        
        Args:
            data: Array numpy con i prezzi di chiusura
            
        Returns:
            Tuple con (macd_line, signal_line, histogram)
        """
        try:
            fast_period = int(float(self.params['fast_period']))
            slow_period = int(float(self.params['slow_period']))
            signal_period = int(float(self.params['signal_period']))
            
            self.logger.debug(f"Calcolo MACD con parametri: fast={fast_period}, slow={slow_period}, signal={signal_period}")
            
            # Verifica che ci siano abbastanza dati
            min_periods = max(fast_period, slow_period) + signal_period
            if len(data) < min_periods:
                self.logger.warning(f"Serie temporale troppo corta per il calcolo del MACD (richiesti {min_periods} punti, disponibili {len(data)})")
                return np.full_like(data, np.nan), np.full_like(data, np.nan), np.full_like(data, np.nan)
                
            # Calcola EMA veloce e lenta
            alpha_fast = 2 / (fast_period + 1)
            alpha_slow = 2 / (slow_period + 1)
            
            ema_fast = np.zeros_like(data)
            ema_slow = np.zeros_like(data)
            
            # Inizializza le prime medie come SMA
            ema_fast[:fast_period] = np.nan
            ema_slow[:slow_period] = np.nan
            
            ema_fast[fast_period-1] = np.mean(data[:fast_period])
            ema_slow[slow_period-1] = np.mean(data[:slow_period])
            
            # Calcola EMA veloce
            for i in range(fast_period, len(data)):
                ema_fast[i] = data[i] * alpha_fast + ema_fast[i-1] * (1 - alpha_fast)
                
            # Calcola EMA lenta
            for i in range(slow_period, len(data)):
                ema_slow[i] = data[i] * alpha_slow + ema_slow[i-1] * (1 - alpha_slow)
                
            # Calcola MACD line
            macd_line = ema_fast - ema_slow
            
            # Calcola Signal line (EMA del MACD)
            signal_line = np.full_like(data, np.nan)
            alpha_signal = 2 / (signal_period + 1)
            
            # Trova il primo indice valido del MACD
            valid_indices = np.where(~np.isnan(macd_line))[0]
            if len(valid_indices) >= signal_period:
                start_idx = valid_indices[0]
                end_idx = start_idx + signal_period
                
                # Verifica che ci siano abbastanza dati validi
                if end_idx <= len(macd_line):
                    # Inizializza signal line
                    signal_line[end_idx-1] = np.mean(macd_line[start_idx:end_idx])
                    
                    # Calcola il resto della signal line
                    for i in range(end_idx, len(data)):
                        signal_line[i] = macd_line[i] * alpha_signal + signal_line[i-1] * (1 - alpha_signal)
            
            # Calcola l'istogramma
            histogram = macd_line - signal_line
            
            self.logger.debug("Calcolo MACD completato")
            return macd_line, signal_line, histogram
            
        except Exception as e:
            self.logger.error(f"Errore nel calcolo MACD: {str(e)}")
            return np.full_like(data, np.nan), np.full_like(data, np.nan), np.full_like(data, np.nan)
        
    def calculate_signal(self, data: np.ndarray) -> float:
        """
        Calcola il segnale del gene sui dati forniti.
        
        Args:
            data: Array numpy con i prezzi di chiusura
            
        Returns:
            Segnale normalizzato tra -1 e 1
        """
        try:
            if len(data) == 0 or np.all(data == 0) or np.all(np.isnan(data)):
                return 0.0
                
            min_periods = max(int(float(self.params['fast_period'])),
                            int(float(self.params['slow_period'])),
                            int(float(self.params['signal_period'])))
                            
            if len(data) < min_periods:
                return 0.0
                
            macd_line, signal_line, histogram = self.calculate_macd(data)
            
            # Verifica che ci siano dati validi alla fine della serie
            if np.isnan(histogram[-1]) or np.isnan(macd_line[-1]) or np.isnan(signal_line[-1]):
                return 0.0
            
            # Calcola il trend dei prezzi
            window = min(20, len(data))
            price_change = (data[-1] - data[-window]) / data[-window]
            
            # Calcola il trend del MACD
            macd_change = macd_line[-1] - macd_line[-window]
            
            # Se il MACD e i prezzi si muovono nella stessa direzione, il trend è confermato
            if np.sign(price_change) == np.sign(macd_change):
                trend_strength = price_change
            else:
                # Se c'è divergenza, inverti il segnale
                trend_strength = -price_change * 0.5  # Ridotto per essere più conservativi
            
            # Normalizza il segnale
            signal = np.tanh(trend_strength * 5)  # Fattore 5 per rendere il segnale più deciso
            
            return float(np.clip(signal, -1, 1))
            
        except Exception as e:
            self.logger.error(f"Errore nel calcolo del segnale MACD: {str(e)}")
            return 0.0
        
    def evaluate(self, data: np.ndarray) -> float:
        """
        Valuta le performance del gene sui dati forniti.
        
        Args:
            data: Array numpy con i prezzi di chiusura
            
        Returns:
            Punteggio di fitness del gene
        """
        try:
            if len(data) == 0:
                self.logger.warning("Array di dati vuoto")
                return 0.0
                
            min_periods = max(int(float(self.params['fast_period'])),
                            int(float(self.params['slow_period'])),
                            int(float(self.params['signal_period'])))
                            
            if len(data) < min_periods:
                self.logger.warning(f"Serie temporale troppo corta: {len(data)} < {min_periods}")
                return 0.0
                
            macd_line, signal_line, histogram = self.calculate_macd(data)
            
            # Rimuovi i NaN dall'inizio della serie
            valid_idx = np.where(~np.isnan(histogram))[0]
            if len(valid_idx) == 0:
                return 0.0
                
            start_idx = valid_idx[0]
            
            # Usa solo i dati validi per i segnali
            valid_histogram = histogram[start_idx:]
            valid_data = data[start_idx:]
            
            if len(valid_histogram) < 2:
                return 0.0
                
            signals = np.zeros_like(valid_histogram)
            
            # Genera segnali quando l'istogramma attraversa lo zero
            crossovers = np.diff(np.signbit(valid_histogram))
            signals[1:][crossovers] = 1
            signals[1:][~crossovers] = -1
            
            # Calcola i rendimenti
            returns = np.diff(valid_data) / valid_data[:-1]
            signal_returns = signals[:-1] * returns
            
            # Calcola metriche solo su segnali validi
            valid_signals = signals != 0
            if np.sum(valid_signals) == 0:
                return 0.0
                
            win_rate = np.sum(signal_returns > 0) / np.sum(valid_signals[:-1])
            avg_return = np.mean(signal_returns[valid_signals[:-1]])
            
            # Penalizza troppi segnali
            signal_frequency = np.sum(valid_signals) / len(signals)
            frequency_penalty = np.exp(-signal_frequency * 10)
            
            # Calcola trend following score
            trend_changes = np.sum(np.diff(signals) != 0)
            trend_score = np.exp(-trend_changes / len(signals) * 5)
            
            fitness = (win_rate * 0.3 + avg_return * 0.3 + frequency_penalty * 0.2 + trend_score * 0.2)
            self.logger.debug(f"Valutazione MACD completata. Fitness: {fitness}")
            return float(fitness)
            
        except Exception as e:
            self.logger.error(f"Errore nella valutazione MACD: {str(e)}")
            return 0.0
