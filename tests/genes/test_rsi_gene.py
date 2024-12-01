"""
Test RSI Gene
------------
Test funzionali per il gene RSI.
"""

import unittest
import numpy as np
from cli.genes.rsi_gene import RSIGene

class TestRSIGene(unittest.TestCase):
    """Test case per il gene RSI."""
    
    def setUp(self):
        """Setup del test case."""
        self.gene = RSIGene(params={
            'period': 14  # Periodo standard per RSI
        })
        
    def test_uptrend(self):
        """Testa il comportamento con trend rialzista."""
        # Crea una serie di prezzi in trend rialzista
        # Ogni giorno sale del 1% con piccole fluttuazioni
        n_days = 50
        base_price = 100
        daily_return = 0.01
        noise = 0.002
        
        prices = np.zeros(n_days)
        prices[0] = base_price
        for i in range(1, n_days):
            prices[i] = prices[i-1] * (1 + daily_return + np.random.normal(0, noise))
            
        signal = self.gene.calculate_signal(prices)
        
        # In uptrend, RSI dovrebbe essere alto (segnale positivo)
        self.assertGreater(signal, 0.3)
        self.assertLessEqual(signal, 1.0)
        
    def test_downtrend(self):
        """Testa il comportamento con trend ribassista."""
        # Crea una serie di prezzi in trend ribassista
        # Ogni giorno scende del 1% con piccole fluttuazioni
        n_days = 50
        base_price = 100
        daily_return = -0.01
        noise = 0.002
        
        prices = np.zeros(n_days)
        prices[0] = base_price
        for i in range(1, n_days):
            prices[i] = prices[i-1] * (1 + daily_return + np.random.normal(0, noise))
            
        signal = self.gene.calculate_signal(prices)
        
        # In downtrend, RSI dovrebbe essere basso (segnale negativo)
        self.assertLess(signal, -0.3)
        self.assertGreaterEqual(signal, -1.0)
        
    def test_sideways(self):
        """Testa il comportamento con mercato laterale."""
        # Crea una serie di prezzi in movimento laterale
        # Prezzo oscilla intorno al valore base con rumore casuale
        n_days = 50
        base_price = 100
        noise = 0.005
        
        prices = base_price * (1 + np.random.normal(0, noise, n_days))
        signal = self.gene.calculate_signal(prices)
        
        # In mercato laterale, RSI dovrebbe essere vicino a zero
        self.assertGreater(signal, -0.3)
        self.assertLess(signal, 0.3)
        
    def test_overbought(self):
        """Testa il comportamento in condizioni di ipercomprato."""
        # Crea una serie di prezzi con forte trend rialzista
        n_days = 50
        base_price = 100
        daily_return = 0.02  # 2% al giorno
        noise = 0.001
        
        prices = np.zeros(n_days)
        prices[0] = base_price
        for i in range(1, n_days):
            prices[i] = prices[i-1] * (1 + daily_return + np.random.normal(0, noise))
            
        signal = self.gene.calculate_signal(prices)
        
        # In condizioni di ipercomprato, RSI dovrebbe essere molto alto
        self.assertGreater(signal, 0.7)
        
    def test_oversold(self):
        """Testa il comportamento in condizioni di ipervenduto."""
        # Crea una serie di prezzi con forte trend ribassista
        n_days = 50
        base_price = 100
        daily_return = -0.02  # -2% al giorno
        noise = 0.001
        
        prices = np.zeros(n_days)
        prices[0] = base_price
        for i in range(1, n_days):
            prices[i] = prices[i-1] * (1 + daily_return + np.random.normal(0, noise))
            
        signal = self.gene.calculate_signal(prices)
        
        # In condizioni di ipervenduto, RSI dovrebbe essere molto basso
        self.assertLess(signal, -0.7)
        
    def test_short_data(self):
        """Testa il comportamento con serie temporale corta."""
        # Serie più corta del periodo RSI
        prices = np.array([100, 101, 102])
        signal = self.gene.calculate_signal(prices)
        
        # Con dati insufficienti dovrebbe restituire 0
        self.assertEqual(signal, 0.0)
        
    def test_signal_bounds(self):
        """Testa che il segnale sia sempre tra -1 e 1."""
        # Test con vari scenari di mercato
        scenarios = [
            np.linspace(100, 200, 50),  # Trend rialzista lineare
            np.linspace(200, 100, 50),  # Trend ribassista lineare
            100 * np.ones(50),          # Prezzo costante
            100 * (1 + np.random.normal(0, 0.02, 50))  # Random walk
        ]
        
        for prices in scenarios:
            signal = self.gene.calculate_signal(prices)
            self.assertGreaterEqual(signal, -1.0)
            self.assertLessEqual(signal, 1.0)
            
    def test_null_data(self):
        """Testa il comportamento con dati nulli."""
        prices = np.zeros(50)
        signal = self.gene.calculate_signal(prices)
        
        # Con prezzi tutti zero dovrebbe restituire 0
        self.assertEqual(signal, 0.0)
        
    def test_nan_data(self):
        """Testa il comportamento con dati NaN."""
        prices = np.array([np.nan] * 50)
        signal = self.gene.calculate_signal(prices)
        
        # Con prezzi NaN dovrebbe restituire 0
        self.assertEqual(signal, 0.0)
        
if __name__ == '__main__':
    unittest.main()
