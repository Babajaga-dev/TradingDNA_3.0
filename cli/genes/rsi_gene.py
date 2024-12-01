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
    
    def __init__(self, name: str = 'rsi', params: Optional[Dict[str, Any]] = None):
        """
        Inizializza il gene RSI.
        
        Args:
            name: Nome del gene (default: 'rsi')
            params: Parametri specifici del gene (opzionale)
        """
        super().__init__(name, params)
        
    def calculate_rsi(self, data: np.ndarray) -> np.ndarray:
        """
        Calcola l'indicatore RSI.
        
        Args:
            data: Array numpy con i prezzi di chiusura
            
        Returns:
            Array numpy con i valori RSI
        """
        try:
            # Assicurati che data sia un array 1D di float
            prices = np.asarray(data, dtype=float).flatten()
            
            if len(prices) < 2:
                return np.full_like(prices, np.nan)
                
            # Calcola le differenze
            delta = np.diff(prices)
            # Aggiungi uno zero all'inizio per mantenere la dimensione originale
            delta = np.insert(delta, 0, 0.0)
            
            # Separa guadagni e perdite
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)
            
            # Calcola le medie mobili di guadagni e perdite
            period = int(self.params['period'])
            if len(prices) < period:
                return np.full_like(prices, np.nan)
                
            # Inizializza array per le medie
            avg_gain = np.zeros_like(prices)
            avg_loss = np.zeros_like(prices)
            
            # Calcola la prima media
            avg_gain[period-1] = np.mean(gain[0:period])
            avg_loss[period-1] = np.mean(loss[0:period])
            
            # Calcola le medie successive usando formula EMA
            for i in range(period, len(prices)):
                avg_gain[i] = (avg_gain[i-1] * (period-1) + gain[i]) / period
                avg_loss[i] = (avg_loss[i-1] * (period-1) + loss[i]) / period
            
            # Calcola RSI
            rs = np.divide(avg_gain, np.where(avg_loss != 0, avg_loss, 1e-8))
            rsi = 100.0 - (100.0 / (1.0 + rs))
            
            # Imposta a NaN i valori prima del periodo
            rsi[:period-1] = np.nan
            
            return rsi
            
        except Exception as e:
            self.logger.error(f"Errore nel calcolo RSI: {str(e)}")
            return np.full_like(data, np.nan)
        
    def calculate_signal(self, data: Dict[str, np.ndarray]) -> float:
        """
        Calcola il segnale del gene sui dati forniti.
        
        Args:
            data: Dizionario con array numpy OHLCV
            
        Returns:
            Segnale normalizzato tra -1 e 1
        """
        try:
            # Estrai i prezzi di chiusura dal dizionario OHLCV
            if not isinstance(data, dict) or 'close' not in data:
                raise ValueError("Input deve essere un dizionario con chiave 'close'")
                
            prices = data['close']
            if not isinstance(prices, np.ndarray):
                raise ValueError("I prezzi devono essere un array numpy")
            
            period = int(self.params['period'])
            if len(prices) < period + 1:
                return 0.0
                
            rsi = self.calculate_rsi(prices)
            if rsi is None or np.all(np.isnan(rsi)):
                return 0.0
                
            # Prendi l'ultimo valore RSI valido
            valid_rsi = rsi[~np.isnan(rsi)]
            if len(valid_rsi) == 0:
                return 0.0
                
            last_rsi = valid_rsi[-1]
            overbought = float(self.params['overbought'])
            oversold = float(self.params['oversold'])
                
            # Normalizza il segnale tra -1 e 1 basandosi sui livelli di ipercomprato/ipervenduto
            if last_rsi > overbought:
                signal = -1.0 * (last_rsi - overbought) / (100.0 - overbought)
            elif last_rsi < oversold:
                signal = (oversold - last_rsi) / oversold
            else:
                # Zona neutrale
                mid_point = (overbought + oversold) / 2.0
                signal = (mid_point - last_rsi) / (overbought - oversold) * 2.0
                
            self.logger.debug(f"RSI={last_rsi:.1f}, Signal={signal:.2f}")
            return float(np.clip(signal, -1.0, 1.0))
            
        except Exception as e:
            self.logger.error(f"Errore nel calcolo del segnale RSI: {str(e)}")
            return 0.0
        
    def evaluate(self, data: Dict[str, np.ndarray]) -> float:
        """
        Valuta le performance del gene sui dati forniti.
        
        Args:
            data: Dizionario con array numpy OHLCV
            
        Returns:
            Punteggio di fitness del gene
        """
        try:
            # Estrai i prezzi di chiusura dal dizionario OHLCV
            if not isinstance(data, dict) or 'close' not in data:
                raise ValueError("Input deve essere un dizionario con chiave 'close'")
                
            prices = data['close']
            if not isinstance(prices, np.ndarray):
                raise ValueError("I prezzi devono essere un array numpy")
            
            period = int(self.params['period'])
            if len(prices) < period + 1:
                return 0.0
                
            # Calcola RSI
            rsi = self.calculate_rsi(prices)
            if rsi is None or np.all(np.isnan(rsi)):
                return 0.0
                
            # Crea array dei segnali
            signals = np.zeros_like(prices)
            
            # Genera segnali usando maschere booleane
            valid_mask = ~np.isnan(rsi)
            overbought = float(self.params['overbought'])
            oversold = float(self.params['oversold'])
            
            overbought_mask = valid_mask & (rsi > overbought)
            oversold_mask = valid_mask & (rsi < oversold)
            
            signals[overbought_mask] = -1.0  # Segnali di vendita
            signals[oversold_mask] = 1.0     # Segnali di acquisto
            
            # Calcola i rendimenti
            price_changes = np.diff(prices)
            returns = np.zeros_like(price_changes)
            non_zero_mask = prices[:-1] != 0
            returns[non_zero_mask] = price_changes[non_zero_mask] / prices[:-1][non_zero_mask]
            
            # Allinea i segnali con i rendimenti
            signals = signals[:-1]  # Rimuovi l'ultimo elemento per allineare con returns
            
            # Metriche di valutazione
            non_zero_signals = np.count_nonzero(signals)
            if non_zero_signals > 0:
                win_rate = np.count_nonzero(signals * returns > 0) / non_zero_signals
            else:
                win_rate = 0.0
                
            if non_zero_signals > 0:
                avg_return = np.mean(returns[signals != 0])
            else:
                avg_return = 0.0
            
            # Penalizza troppi segnali
            signal_frequency = non_zero_signals / len(signals)
            frequency_penalty = float(np.exp(-signal_frequency * 10))  # Penalizza alta frequenza
            
            fitness = (win_rate * 0.4 + avg_return * 0.4 + frequency_penalty * 0.2)
            
            self.logger.debug(f"RSI Fitness: win_rate={win_rate:.2f}, avg_return={avg_return:.2f}, penalty={frequency_penalty:.2f}")
            return float(fitness)
            
        except Exception as e:
            self.logger.error(f"Errore nella valutazione RSI: {str(e)}")
            return 0.0
