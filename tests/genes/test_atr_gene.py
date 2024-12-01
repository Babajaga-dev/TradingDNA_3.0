"""
Test ATR Gene
------------
Test funzionali per il gene ATR (Average True Range).
"""

import unittest
import numpy as np
from cli.genes.atr_gene import ATRGene

class TestATRGene(unittest.TestCase):
    """Test case per il gene ATR."""
    
    def setUp(self):
        """Setup del test case."""
        self.gene = ATRGene(params={
            'period': 14  # Periodo standard per ATR
        })
        
    def generate_ohlc_data(self, n_days, base_price=100, volatility=0.02):
        """
        Genera dati OHLC simulati.
        
        Args:
            n_days: Numero di giorni
            base_price: Prezzo base iniziale
            volatility: Volatilità dei prezzi
            
        Returns:
            Tuple di array (open, high, low, close)
        """
        opens = np.zeros(n_days)
        highs = np.zeros(n_days)
        lows = np.zeros(n_days)
        closes = np.zeros(n_days)
        
        opens[0] = base_price
        closes[0] = base_price * (1 + np.random.normal(0, volatility))
        highs[0] = max(opens[0], closes[0]) * (1 + abs(np.random.normal(0, volatility/2)))
        lows[0] = min(opens[0], closes[0]) * (1 - abs(np.random.normal(0, volatility/2)))
        
        for i in range(1, n_days):
            opens[i] = closes[i-1]
            closes[i] = opens[i] * (1 + np.random.normal(0, volatility))
            highs[i] = max(opens[i], closes[i]) * (1 + abs(np.random.normal(0, volatility/2)))
            lows[i] = min(opens[i], closes[i]) * (1 - abs(np.random.normal(0, volatility/2)))
            
        return opens, highs, lows, closes
        
    def test_increasing_volatility(self):
        """Testa il comportamento con volatilità crescente."""
        n_days = 50
        base_price = 100
        
        # Genera dati con volatilità crescente
        opens, highs, lows, closes = [], [], [], []
        for i in range(n_days):
            volatility = 0.01 * (1 + i/n_days)  # Volatilità crescente
            o, h, l, c = self.generate_ohlc_data(1, base_price, volatility)
            opens.extend(o)
            highs.extend(h)
            lows.extend(l)
            closes.extend(c)
            base_price = c[0]
            
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con volatilità crescente, dovrebbe dare segnale positivo forte
        self.assertGreater(signal, 0.5)
        self.assertLessEqual(signal, 1.0)
        
    def test_decreasing_volatility(self):
        """Testa il comportamento con volatilità decrescente."""
        n_days = 50
        base_price = 100
        
        # Genera dati con volatilità decrescente
        opens, highs, lows, closes = [], [], [], []
        for i in range(n_days):
            volatility = 0.02 * (1 - i/n_days)  # Volatilità decrescente
            o, h, l, c = self.generate_ohlc_data(1, base_price, volatility)
            opens.extend(o)
            highs.extend(h)
            lows.extend(l)
            closes.extend(c)
            base_price = c[0]
            
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con volatilità decrescente, dovrebbe dare segnale negativo
        self.assertLess(signal, -0.3)
        self.assertGreaterEqual(signal, -1.0)
        
    def test_price_gaps(self):
        """Testa il comportamento con gap di prezzo."""
        n_days = 50
        base_price = 100
        
        # Genera dati con alcuni gap
        opens, highs, lows, closes = self.generate_ohlc_data(n_days, base_price, 0.01)
        
        # Inserisce alcuni gap
        gap_indices = [20, 30, 40]
        for idx in gap_indices:
            opens[idx] = closes[idx-1] * 1.05  # Gap up del 5%
            closes[idx] = opens[idx] * (1 + np.random.normal(0, 0.01))
            highs[idx] = max(opens[idx], closes[idx]) * 1.01
            lows[idx] = min(opens[idx], closes[idx]) * 0.99
            
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con presenza di gap, dovrebbe dare segnale significativo
        self.assertTrue(abs(signal) > 0.5)
        
    def test_calm_market(self):
        """Testa il comportamento in mercato calmo."""
        n_days = 50
        base_price = 100
        low_volatility = 0.005
        
        opens, highs, lows, closes = self.generate_ohlc_data(n_days, base_price, low_volatility)
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # In mercato calmo, il segnale dovrebbe essere debole
        self.assertGreater(signal, -0.3)
        self.assertLess(signal, 0.3)
        
    def test_volatile_market(self):
        """Testa il comportamento in mercato volatile."""
        n_days = 50
        base_price = 100
        high_volatility = 0.03
        
        opens, highs, lows, closes = self.generate_ohlc_data(n_days, base_price, high_volatility)
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # In mercato volatile, il segnale dovrebbe essere forte
        self.assertTrue(abs(signal) > 0.5)
        
    def test_trend_with_volatility(self):
        """Testa il comportamento con trend e volatilità."""
        n_days = 50
        base_price = 100
        
        # Genera dati con trend e volatilità variabile
        opens, highs, lows, closes = [], [], [], []
        for i in range(n_days):
            trend = 0.001 * i  # Trend crescente
            volatility = 0.01 * (1 + np.sin(i/10))  # Volatilità oscillante
            o, h, l, c = self.generate_ohlc_data(1, base_price, volatility)
            opens.extend(o)
            highs.extend(h)
            lows.extend(l)
            closes.extend(c)
            base_price = c[0] * (1 + trend)
            
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Verifica che il segnale sia entro i limiti
        self.assertGreaterEqual(signal, -1.0)
        self.assertLessEqual(signal, 1.0)
        
    def test_short_data(self):
        """Testa il comportamento con serie temporale corta."""
        # Serie più corta del periodo ATR
        opens, highs, lows, closes = self.generate_ohlc_data(3, 100, 0.01)
        data = np.array([opens, highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con dati insufficienti dovrebbe restituire 0
        self.assertEqual(signal, 0.0)
        
    def test_signal_bounds(self):
        """Testa che il segnale sia sempre tra -1 e 1."""
        # Test con vari scenari di volatilità
        volatilities = [0.005, 0.01, 0.02, 0.03]
        
        for vol in volatilities:
            opens, highs, lows, closes = self.generate_ohlc_data(50, 100, vol)
            data = np.array([opens, highs, lows, closes]).T
            signal = self.gene.calculate_signal(data)
            self.assertGreaterEqual(signal, -1.0)
            self.assertLessEqual(signal, 1.0)
            
    def test_null_data(self):
        """Testa il comportamento con dati nulli."""
        data = np.zeros((50, 4))  # [open, high, low, close] tutti zero
        signal = self.gene.calculate_signal(data)
        
        # Con prezzi tutti zero dovrebbe restituire 0
        self.assertEqual(signal, 0.0)
        
    def test_nan_data(self):
        """Testa il comportamento con dati NaN."""
        data = np.full((50, 4), np.nan)  # [open, high, low, close] tutti NaN
        signal = self.gene.calculate_signal(data)
        
        # Con prezzi NaN dovrebbe restituire 0
        self.assertEqual(signal, 0.0)
        
if __name__ == '__main__':
    unittest.main()
