"""
Test Volatility Breakout Gene
---------------------------
Test funzionali per il gene Volatility Breakout.
"""

import unittest
import numpy as np
from cli.genes.volatility_breakout_gene import VolatilityBreakoutGene

class TestVolatilityBreakoutGene(unittest.TestCase):
    """Test case per il gene Volatility Breakout."""
    
    def setUp(self):
        """Setup del test case."""
        self.gene = VolatilityBreakoutGene(params={
            'period': 20,        # Periodo per il calcolo della volatilità
            'std_mult': 2.0      # Moltiplicatore per le deviazioni standard
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
        
    def test_upward_breakout(self):
        """Testa il riconoscimento di breakout rialzista."""
        n_days = 50
        base_price = 100
        
        opens, highs, lows, closes = self.generate_ohlc_data(n_days, base_price)
        
        # Crea periodo di consolidamento
        for i in range(1, n_days-5):
            volatility = 0.01
            opens[i] = base_price * (1 + np.random.normal(0, volatility/2))
            closes[i] = opens[i] * (1 + np.random.normal(0, volatility/2))
            highs[i] = max(opens[i], closes[i]) * (1 + volatility)
            lows[i] = min(opens[i], closes[i]) * (1 - volatility)
            
        # Crea breakout rialzista
        for i in range(n_days-5, n_days):
            opens[i] = closes[i-1]
            closes[i] = opens[i] * 1.02  # +2% al giorno
            highs[i] = closes[i] * 1.01
            lows[i] = opens[i] * 0.995
            
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con breakout rialzista, dovrebbe dare segnale positivo forte
        self.assertGreater(signal, 0.7)
        self.assertLessEqual(signal, 1.0)
        
    def test_downward_breakout(self):
        """Testa il riconoscimento di breakout ribassista."""
        n_days = 50
        base_price = 100
        
        opens, highs, lows, closes = self.generate_ohlc_data(n_days, base_price)
        
        # Crea periodo di consolidamento
        for i in range(1, n_days-5):
            volatility = 0.01
            opens[i] = base_price * (1 + np.random.normal(0, volatility/2))
            closes[i] = opens[i] * (1 + np.random.normal(0, volatility/2))
            highs[i] = max(opens[i], closes[i]) * (1 + volatility)
            lows[i] = min(opens[i], closes[i]) * (1 - volatility)
            
        # Crea breakout ribassista
        for i in range(n_days-5, n_days):
            opens[i] = closes[i-1]
            closes[i] = opens[i] * 0.98  # -2% al giorno
            highs[i] = opens[i] * 1.005
            lows[i] = closes[i] * 0.99
            
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con breakout ribassista, dovrebbe dare segnale negativo forte
        self.assertLess(signal, -0.7)
        self.assertGreaterEqual(signal, -1.0)
        
    def test_false_breakout(self):
        """Testa il comportamento con falso breakout."""
        n_days = 50
        base_price = 100
        
        opens, highs, lows, closes = self.generate_ohlc_data(n_days, base_price)
        
        # Crea periodo di consolidamento
        for i in range(1, n_days-3):
            volatility = 0.01
            opens[i] = base_price * (1 + np.random.normal(0, volatility/2))
            closes[i] = opens[i] * (1 + np.random.normal(0, volatility/2))
            highs[i] = max(opens[i], closes[i]) * (1 + volatility)
            lows[i] = min(opens[i], closes[i]) * (1 - volatility)
            
        # Crea falso breakout (movimento seguito da inversione)
        opens[-3] = closes[-4]
        closes[-3] = opens[-3] * 1.02
        highs[-3] = closes[-3] * 1.01
        lows[-3] = opens[-3] * 0.995
        
        opens[-2] = closes[-3]
        closes[-2] = opens[-2] * 0.99
        highs[-2] = opens[-2] * 1.005
        lows[-2] = closes[-2] * 0.99
        
        opens[-1] = closes[-2]
        closes[-1] = opens[-1] * 0.98
        highs[-1] = opens[-1] * 1.005
        lows[-1] = closes[-1] * 0.99
        
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con falso breakout, dovrebbe dare segnale nella direzione dell'inversione
        self.assertLess(signal, 0)
        
    def test_increasing_volatility(self):
        """Testa il comportamento con volatilità crescente."""
        n_days = 50
        base_price = 100
        
        opens, highs, lows, closes = self.generate_ohlc_data(n_days, base_price)
        
        # Crea serie con volatilità crescente
        for i in range(1, n_days):
            volatility = 0.01 * (1 + i/n_days)  # Volatilità crescente
            opens[i] = base_price * (1 + np.random.normal(0, volatility/2))
            closes[i] = opens[i] * (1 + np.random.normal(0, volatility/2))
            highs[i] = max(opens[i], closes[i]) * (1 + volatility)
            lows[i] = min(opens[i], closes[i]) * (1 - volatility)
            
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con volatilità crescente, dovrebbe dare segnale significativo
        self.assertTrue(abs(signal) > 0.5)
        
    def test_decreasing_volatility(self):
        """Testa il comportamento con volatilità decrescente."""
        n_days = 50
        base_price = 100
        
        opens, highs, lows, closes = self.generate_ohlc_data(n_days, base_price)
        
        # Crea serie con volatilità decrescente
        for i in range(1, n_days):
            volatility = 0.02 * (1 - i/n_days)  # Volatilità decrescente
            opens[i] = base_price * (1 + np.random.normal(0, volatility/2))
            closes[i] = opens[i] * (1 + np.random.normal(0, volatility/2))
            highs[i] = max(opens[i], closes[i]) * (1 + volatility)
            lows[i] = min(opens[i], closes[i]) * (1 - volatility)
            
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con volatilità decrescente, dovrebbe dare segnale debole
        self.assertGreater(signal, -0.3)
        self.assertLess(signal, 0.3)
        
    def test_consolidation(self):
        """Testa il comportamento durante consolidamento."""
        n_days = 50
        base_price = 100
        
        opens, highs, lows, closes = self.generate_ohlc_data(n_days, base_price)
        
        # Crea periodo di consolidamento
        volatility = 0.01
        for i in range(1, n_days):
            opens[i] = base_price * (1 + np.random.normal(0, volatility/2))
            closes[i] = opens[i] * (1 + np.random.normal(0, volatility/2))
            highs[i] = max(opens[i], closes[i]) * (1 + volatility)
            lows[i] = min(opens[i], closes[i]) * (1 - volatility)
            
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Durante consolidamento, dovrebbe dare segnale debole
        self.assertGreater(signal, -0.3)
        self.assertLess(signal, 0.3)
        
    def test_breakout_after_squeeze(self):
        """Testa il comportamento con breakout dopo squeeze."""
        n_days = 50
        base_price = 100
        
        opens, highs, lows, closes = self.generate_ohlc_data(n_days, base_price)
        
        # Crea periodo di squeeze (bassa volatilità)
        for i in range(1, n_days-5):
            volatility = 0.005
            opens[i] = base_price * (1 + np.random.normal(0, volatility/2))
            closes[i] = opens[i] * (1 + np.random.normal(0, volatility/2))
            highs[i] = max(opens[i], closes[i]) * (1 + volatility)
            lows[i] = min(opens[i], closes[i]) * (1 - volatility)
            
        # Crea breakout con alta volatilità
        for i in range(n_days-5, n_days):
            opens[i] = closes[i-1]
            closes[i] = opens[i] * 1.03
            highs[i] = closes[i] * 1.02
            lows[i] = opens[i] * 0.99
            
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con breakout dopo squeeze, dovrebbe dare segnale molto forte
        self.assertTrue(abs(signal) > 0.8)
        
    def test_short_data(self):
        """Testa il comportamento con serie temporale corta."""
        opens, highs, lows, closes = self.generate_ohlc_data(3, 100)
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con dati insufficienti dovrebbe restituire 0
        self.assertEqual(signal, 0.0)
        
    def test_signal_bounds(self):
        """Testa che il segnale sia sempre tra -1 e 1."""
        n_days = 50
        scenarios = [
            (0.02, 1.02),  # Alta volatilità, trend up
            (0.02, 0.98),  # Alta volatilità, trend down
            (0.005, 1.0),  # Bassa volatilità
            (0.03, 1.0)    # Volatilità molto alta
        ]
        
        for volatility, trend in scenarios:
            opens, highs, lows, closes = self.generate_ohlc_data(n_days, 100)
            
            for i in range(1, n_days):
                opens[i] = closes[i-1]
                closes[i] = opens[i] * trend
                highs[i] = max(opens[i], closes[i]) * (1 + volatility)
                lows[i] = min(opens[i], closes[i]) * (1 - volatility)
                
            data = np.array([opens, highs, lows, closes]).T
            signal = self.gene.calculate_signal(data)
            
            self.assertGreaterEqual(signal, -1.0)
            self.assertLessEqual(signal, 1.0)
            
    def test_null_data(self):
        """Testa il comportamento con dati nulli."""
        data = np.zeros((50, 4))  # [open, high, low, close] tutti zero
        signal = self.gene.calculate_signal(data)
        
        # Con dati nulli dovrebbe restituire 0
        self.assertEqual(signal, 0.0)
        
    def test_nan_data(self):
        """Testa il comportamento con dati NaN."""
        data = np.full((50, 4), np.nan)  # [open, high, low, close] tutti NaN
        signal = self.gene.calculate_signal(data)
        
        # Con dati NaN dovrebbe restituire 0
        self.assertEqual(signal, 0.0)
        
if __name__ == '__main__':
    unittest.main()
