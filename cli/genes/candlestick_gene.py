"""
Candlestick Gene
--------------
Implementazione del gene Candlestick per l'identificazione di pattern candlestick.
"""

import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from .base import Gene

class CandlestickGene(Gene):
    """Gene che implementa l'analisi dei pattern candlestick."""
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Inizializza il gene Candlestick.
        
        Args:
            params: Parametri specifici del gene (opzionale)
        """
        super().__init__('candlestick', params)
        
    def is_doji(self, open_price: float, high: float, low: float, close: float) -> bool:
        """
        Verifica se una candela è un doji.
        
        Args:
            open_price: Prezzo di apertura
            high: Prezzo massimo
            low: Prezzo minimo
            close: Prezzo di chiusura
            
        Returns:
            True se la candela è un doji
        """
        body_size = abs(close - open_price)
        total_range = high - low
        if total_range == 0:
            return False
            
        doji_threshold = float(self.params['doji_threshold'])
        return body_size / total_range < doji_threshold
        
    def is_hammer(self, open_price: float, high: float, low: float, close: float) -> Tuple[bool, bool]:
        """
        Verifica se una candela è un hammer o hanging man.
        
        Args:
            open_price: Prezzo di apertura
            high: Prezzo massimo
            low: Prezzo minimo
            close: Prezzo di chiusura
            
        Returns:
            Tuple con (is_hammer, is_hanging_man)
        """
        body_size = abs(close - open_price)
        total_range = high - low
        if total_range == 0:
            return False, False
            
        body_position = (min(open_price, close) - low) / total_range
        shadow_ratio = float(self.params['shadow_ratio'])
        
        # Hammer: piccolo corpo in alto, lunga shadow inferiore
        is_hammer = (body_size / total_range < shadow_ratio and body_position > 0.6)
        
        # Hanging Man: simile al hammer ma in trend rialzista
        is_hanging_man = is_hammer  # La differenza sta nel contesto del trend
        
        return is_hammer, is_hanging_man
        
    def is_engulfing(self, prev_open: float, prev_close: float, curr_open: float, curr_close: float) -> Tuple[bool, bool]:
        """
        Verifica se due candele formano un pattern engulfing.
        
        Args:
            prev_open: Apertura candela precedente
            prev_close: Chiusura candela precedente
            curr_open: Apertura candela corrente
            curr_close: Chiusura candela corrente
            
        Returns:
            Tuple con (bullish_engulfing, bearish_engulfing)
        """
        prev_body_size = abs(prev_close - prev_open)
        curr_body_size = abs(curr_close - curr_open)
        
        # Bullish engulfing
        bullish = (
            prev_close < prev_open and  # Candela precedente ribassista
            curr_close > curr_open and  # Candela corrente rialzista
            curr_open < prev_close and  # Apertura sotto chiusura precedente
            curr_close > prev_open      # Chiusura sopra apertura precedente
        )
        
        # Bearish engulfing
        bearish = (
            prev_close > prev_open and  # Candela precedente rialzista
            curr_close < curr_open and  # Candela corrente ribassista
            curr_open > prev_close and  # Apertura sopra chiusura precedente
            curr_close < prev_open      # Chiusura sotto apertura precedente
        )
        
        # Verifica dimensione minima
        size_threshold = float(self.params['engulfing_size'])
        if curr_body_size < prev_body_size * size_threshold:
            return False, False
            
        return bullish, bearish
        
    def is_star(self, data: np.ndarray, idx: int) -> Tuple[bool, bool]:
        """
        Verifica se tre candele formano un morning/evening star.
        
        Args:
            data: Array numpy con i dati OHLC
            idx: Indice della candela corrente
            
        Returns:
            Tuple con (morning_star, evening_star)
        """
        if idx < 2:
            return False, False
            
        # Estrai i dati delle tre candele
        first_open, _, _, first_close = data[idx-2, [0,1,2,3]]
        second_open, second_high, second_low, second_close = data[idx-1, [0,1,2,3]]
        third_open, _, _, third_close = data[idx, [0,1,2,3]]
        
        # Verifica se la candela centrale è un doji o piccola
        second_body = abs(second_close - second_open)
        second_range = second_high - second_low
        small_body = second_body / second_range < float(self.params['star_body_size'])
        
        # Morning Star
        morning_star = (
            first_close < first_open and     # Prima candela ribassista
            small_body and                   # Seconda candela piccola
            third_close > third_open and     # Terza candela rialzista
            second_close < first_close and   # Gap ribassista
            third_open > second_close        # Gap rialzista
        )
        
        # Evening Star
        evening_star = (
            first_close > first_open and     # Prima candela rialzista
            small_body and                   # Seconda candela piccola
            third_close < third_open and     # Terza candela ribassista
            second_close > first_close and   # Gap rialzista
            third_open < second_close        # Gap ribassista
        )
        
        return morning_star, evening_star
        
    def is_harami(self, prev_open: float, prev_close: float, curr_open: float, curr_close: float) -> Tuple[bool, bool]:
        """
        Verifica se due candele formano un pattern harami.
        
        Args:
            prev_open: Apertura candela precedente
            prev_close: Chiusura candela precedente
            curr_open: Apertura candela corrente
            curr_close: Chiusura candela corrente
            
        Returns:
            Tuple con (bullish_harami, bearish_harami)
        """
        prev_body_size = abs(prev_close - prev_open)
        curr_body_size = abs(curr_close - curr_open)
        
        # Verifica dimensione relativa
        size_ratio = curr_body_size / prev_body_size if prev_body_size > 0 else 0
        if size_ratio > float(self.params['harami_size']):
            return False, False
            
        # Bullish Harami
        bullish = (
            prev_close < prev_open and                      # Candela precedente ribassista
            curr_close > curr_open and                      # Candela corrente rialzista
            curr_open > min(prev_open, prev_close) and     # Corpo contenuto
            curr_close < max(prev_open, prev_close)        # nella candela precedente
        )
        
        # Bearish Harami
        bearish = (
            prev_close > prev_open and                      # Candela precedente rialzista
            curr_close < curr_open and                      # Candela corrente ribassista
            curr_open < max(prev_open, prev_close) and     # Corpo contenuto
            curr_close > min(prev_open, prev_close)        # nella candela precedente
        )
        
        return bullish, bearish
        
    def calculate_signal(self, data: np.ndarray) -> float:
        """
        Calcola il segnale del gene sui dati forniti.
        
        Args:
            data: Array numpy con i dati OHLC
            
        Returns:
            Segnale normalizzato tra -1 e 1
        """
        if len(data) < 3:  # Servono almeno 3 candele per alcuni pattern
            return 0
            
        # Estrai dati ultima candela
        open_price = data[-1, 0]
        high = data[-1, 1]
        low = data[-1, 2]
        close = data[-1, 3]
        
        # Estrai dati penultima candela
        prev_open = data[-2, 0]
        prev_close = data[-2, 3]
        
        signal = 0.0
        pattern_weight = float(self.params['pattern_weight'])
        
        # Verifica Doji
        if self.is_doji(open_price, high, low, close):
            # Doji è un segnale di indecisione/inversione
            signal += np.sign(close - open_price) * pattern_weight * 0.5
            
        # Verifica Hammer/Hanging Man
        hammer, hanging_man = self.is_hammer(open_price, high, low, close)
        if hammer:
            signal += pattern_weight  # Segnale rialzista
        if hanging_man:
            signal -= pattern_weight  # Segnale ribassista
            
        # Verifica Engulfing
        bullish_eng, bearish_eng = self.is_engulfing(prev_open, prev_close, open_price, close)
        if bullish_eng:
            signal += pattern_weight * 1.5  # Pattern forte
        if bearish_eng:
            signal -= pattern_weight * 1.5  # Pattern forte
            
        # Verifica Morning/Evening Star
        morning_star, evening_star = self.is_star(data, -1)
        if morning_star:
            signal += pattern_weight * 2.0  # Pattern molto forte
        if evening_star:
            signal -= pattern_weight * 2.0  # Pattern molto forte
            
        # Verifica Harami
        bullish_harami, bearish_harami = self.is_harami(prev_open, prev_close, open_price, close)
        if bullish_harami:
            signal += pattern_weight
        if bearish_harami:
            signal -= pattern_weight
            
        return np.clip(signal, -1, 1)
        
    def evaluate(self, data: np.ndarray) -> float:
        """
        Valuta le performance del gene sui dati forniti.
        
        Args:
            data: Array numpy con i dati OHLC
            
        Returns:
            Punteggio di fitness del gene
        """
        if len(data) < 3:
            return 0
            
        signals = []
        for i in range(3, len(data) + 1):
            signal = self.calculate_signal(data[:i])
            signals.append(signal)
            
        # Padding con zeri all'inizio
        signals = [0] * 2 + signals
        signals = np.array(signals)
        
        # Calcola i rendimenti
        returns = np.diff(data[:, 3]) / data[:-1, 3]  # Rendimenti su prezzi di chiusura
        signal_returns = signals[:-1] * returns
        
        # Metriche di valutazione
        non_zero_signals = signals[signals != 0]
        if len(non_zero_signals) == 0:
            return 0
            
        # Win rate
        win_rate = np.sum(signal_returns > 0) / np.sum(signals != 0)
        
        # Rendimento medio
        avg_return = np.mean(signal_returns[signals[:-1] != 0])
        
        # Penalizza troppi segnali
        signal_frequency = np.sum(signals != 0) / len(signals)
        frequency_penalty = np.exp(-signal_frequency * 10)
        
        # Premia pattern più forti
        pattern_strength = np.mean(np.abs(non_zero_signals))
        
        fitness = (win_rate * 0.3 + avg_return * 0.3 + frequency_penalty * 0.2 + pattern_strength * 0.2)
        return float(fitness)
