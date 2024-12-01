"""
Test Candlestick Gene
--------------------
Test funzionali per il gene Candlestick.
"""

import unittest
import numpy as np
from cli.genes.candlestick_gene import CandlestickGene

class TestCandlestickGene(unittest.TestCase):
    """Test case per il gene Candlestick."""
    
    def setUp(self):
        """Setup del test case."""
        self.gene = CandlestickGene(params={
            'lookback': 5  # Numero di candele da analizzare
        })
        
    def generate_ohlc_data(self, n_days, base_price=100):
        """
        Genera dati OHLC simulati.
        
        Args:
            n_days: Numero di giorni
            base_price: Prezzo base iniziale
            
        Returns:
            Tuple di array (opens, highs, lows, closes)
        """
        opens = np.zeros(n_days)
        highs = np.zeros(n_days)
        lows = np.zeros(n_days)
        closes = np.zeros(n_days)
        
        opens[0] = base_price
        closes[0] = base_price
        highs[0] = base_price * 1.01
        lows[0] = base_price * 0.99
        
        return opens, highs, lows, closes
        
    def test_hammer(self):
        """Testa il riconoscimento del pattern hammer."""
        n_days = 20
        base_price = 100
        
        opens, highs, lows, closes = self.generate_ohlc_data(n_days, base_price)
        
        # Crea trend ribassista
        for i in range(1, n_days-1):
            opens[i] = base_price * (1 - i*0.01)
            closes[i] = opens[i] * 0.99
            highs[i] = opens[i] * 1.01
            lows[i] = closes[i] * 0.98
            
        # Crea hammer nell'ultimo giorno
        opens[-1] = closes[-2]
        closes[-1] = opens[-1] * 1.02
        highs[-1] = closes[-1] * 1.01
        lows[-1] = opens[-1] * 0.95  # Lunga shadow inferiore
        
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con hammer dopo trend ribassista, dovrebbe dare segnale positivo
        self.assertGreater(signal, 0.5)
        
    def test_shooting_star(self):
        """Testa il riconoscimento del pattern shooting star."""
        n_days = 20
        base_price = 100
        
        opens, highs, lows, closes = self.generate_ohlc_data(n_days, base_price)
        
        # Crea trend rialzista
        for i in range(1, n_days-1):
            opens[i] = base_price * (1 + i*0.01)
            closes[i] = opens[i] * 1.01
            highs[i] = closes[i] * 1.01
            lows[i] = opens[i] * 0.99
            
        # Crea shooting star nell'ultimo giorno
        opens[-1] = closes[-2]
        closes[-1] = opens[-1] * 0.98
        highs[-1] = opens[-1] * 1.05  # Lunga shadow superiore
        lows[-1] = closes[-1] * 0.99
        
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con shooting star dopo trend rialzista, dovrebbe dare segnale negativo
        self.assertLess(signal, -0.5)
        
    def test_bullish_engulfing(self):
        """Testa il riconoscimento del pattern bullish engulfing."""
        n_days = 20
        base_price = 100
        
        opens, highs, lows, closes = self.generate_ohlc_data(n_days, base_price)
        
        # Crea trend ribassista
        for i in range(1, n_days-2):
            opens[i] = base_price * (1 - i*0.01)
            closes[i] = opens[i] * 0.99
            highs[i] = opens[i] * 1.01
            lows[i] = closes[i] * 0.99
            
        # Crea candela ribassista
        opens[-2] = closes[-3]
        closes[-2] = opens[-2] * 0.98
        highs[-2] = opens[-2] * 1.01
        lows[-2] = closes[-2] * 0.99
        
        # Crea candela rialzista che ingloba la precedente
        opens[-1] = closes[-2]
        closes[-1] = opens[-2] * 1.03
        highs[-1] = closes[-1] * 1.01
        lows[-1] = opens[-1] * 0.99
        
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con bullish engulfing, dovrebbe dare segnale positivo forte
        self.assertGreater(signal, 0.7)
        
    def test_bearish_engulfing(self):
        """Testa il riconoscimento del pattern bearish engulfing."""
        n_days = 20
        base_price = 100
        
        opens, highs, lows, closes = self.generate_ohlc_data(n_days, base_price)
        
        # Crea trend rialzista
        for i in range(1, n_days-2):
            opens[i] = base_price * (1 + i*0.01)
            closes[i] = opens[i] * 1.01
            highs[i] = closes[i] * 1.01
            lows[i] = opens[i] * 0.99
            
        # Crea candela rialzista
        opens[-2] = closes[-3]
        closes[-2] = opens[-2] * 1.02
        highs[-2] = closes[-2] * 1.01
        lows[-2] = opens[-2] * 0.99
        
        # Crea candela ribassista che ingloba la precedente
        opens[-1] = closes[-2]
        closes[-1] = opens[-2] * 0.97
        highs[-1] = opens[-1] * 1.01
        lows[-1] = closes[-1] * 0.99
        
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con bearish engulfing, dovrebbe dare segnale negativo forte
        self.assertLess(signal, -0.7)
        
    def test_doji(self):
        """Testa il riconoscimento del pattern doji."""
        n_days = 20
        base_price = 100
        
        opens, highs, lows, closes = self.generate_ohlc_data(n_days, base_price)
        
        # Crea trend precedente
        for i in range(1, n_days-1):
            opens[i] = base_price * (1 + i*0.01)
            closes[i] = opens[i] * 1.01
            highs[i] = closes[i] * 1.01
            lows[i] = opens[i] * 0.99
            
        # Crea doji nell'ultimo giorno
        opens[-1] = closes[-2]
        closes[-1] = opens[-1]  # Apertura = Chiusura
        highs[-1] = opens[-1] * 1.02
        lows[-1] = opens[-1] * 0.98
        
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con doji, dovrebbe dare segnale neutro/debole
        self.assertGreater(signal, -0.3)
        self.assertLess(signal, 0.3)
        
    def test_morning_star(self):
        """Testa il riconoscimento del pattern morning star."""
        n_days = 20
        base_price = 100
        
        opens, highs, lows, closes = self.generate_ohlc_data(n_days, base_price)
        
        # Crea trend ribassista
        for i in range(1, n_days-3):
            opens[i] = base_price * (1 - i*0.01)
            closes[i] = opens[i] * 0.99
            highs[i] = opens[i] * 1.01
            lows[i] = closes[i] * 0.99
            
        # Prima candela ribassista
        opens[-3] = closes[-4]
        closes[-3] = opens[-3] * 0.97
        highs[-3] = opens[-3] * 1.01
        lows[-3] = closes[-3] * 0.99
        
        # Seconda candela piccola (stella)
        opens[-2] = closes[-3] * 0.99
        closes[-2] = opens[-2] * 1.001
        highs[-2] = opens[-2] * 1.01
        lows[-2] = closes[-2] * 0.99
        
        # Terza candela rialzista
        opens[-1] = closes[-2]
        closes[-1] = opens[-1] * 1.03
        highs[-1] = closes[-1] * 1.01
        lows[-1] = opens[-1] * 0.99
        
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con morning star, dovrebbe dare segnale positivo forte
        self.assertGreater(signal, 0.7)
        
    def test_evening_star(self):
        """Testa il riconoscimento del pattern evening star."""
        n_days = 20
        base_price = 100
        
        opens, highs, lows, closes = self.generate_ohlc_data(n_days, base_price)
        
        # Crea trend rialzista
        for i in range(1, n_days-3):
            opens[i] = base_price * (1 + i*0.01)
            closes[i] = opens[i] * 1.01
            highs[i] = closes[i] * 1.01
            lows[i] = opens[i] * 0.99
            
        # Prima candela rialzista
        opens[-3] = closes[-4]
        closes[-3] = opens[-3] * 1.03
        highs[-3] = closes[-3] * 1.01
        lows[-3] = opens[-3] * 0.99
        
        # Seconda candela piccola (stella)
        opens[-2] = closes[-3] * 1.01
        closes[-2] = opens[-2] * 0.999
        highs[-2] = opens[-2] * 1.01
        lows[-2] = closes[-2] * 0.99
        
        # Terza candela ribassista
        opens[-1] = closes[-2]
        closes[-1] = opens[-1] * 0.97
        highs[-1] = opens[-1] * 1.01
        lows[-1] = closes[-1] * 0.99
        
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con evening star, dovrebbe dare segnale negativo forte
        self.assertLess(signal, -0.7)
        
    def test_short_data(self):
        """Testa il comportamento con serie temporale corta."""
        opens, highs, lows, closes = self.generate_ohlc_data(3, 100)
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con dati insufficienti dovrebbe restituire 0
        self.assertEqual(signal, 0.0)
        
    def test_signal_bounds(self):
        """Testa che il segnale sia sempre tra -1 e 1."""
        n_days = 20
        patterns = [
            (1.02, 1.03, 0.99, 1.02),  # Candela rialzista
            (1.02, 1.02, 0.98, 0.99),  # Candela ribassista
            (1.00, 1.02, 0.98, 1.00),  # Doji
            (1.00, 1.05, 0.95, 1.00)   # Alta volatilità
        ]
        
        for open_mult, high_mult, low_mult, close_mult in patterns:
            opens, highs, lows, closes = self.generate_ohlc_data(n_days, 100)
            
            for i in range(1, n_days):
                opens[i] = closes[i-1]
                closes[i] = opens[i] * close_mult
                highs[i] = opens[i] * high_mult
                lows[i] = opens[i] * low_mult
                
            data = np.array([opens, highs, lows, closes]).T
            signal = self.gene.calculate_signal(data)
            
            self.assertGreaterEqual(signal, -1.0)
            self.assertLessEqual(signal, 1.0)
            
    def test_null_data(self):
        """Testa il comportamento con dati nulli."""
        data = np.zeros((20, 4))  # [open, high, low, close] tutti zero
        signal = self.gene.calculate_signal(data)
        
        # Con dati nulli dovrebbe restituire 0
        self.assertEqual(signal, 0.0)
        
    def test_nan_data(self):
        """Testa il comportamento con dati NaN."""
        data = np.full((20, 4), np.nan)  # [open, high, low, close] tutti NaN
        signal = self.gene.calculate_signal(data)
        
        # Con dati NaN dovrebbe restituire 0
        self.assertEqual(signal, 0.0)
        
if __name__ == '__main__':
    unittest.main()
