"""
Test MACD Gene
-------------
Test funzionali per il gene MACD.
"""

import unittest
import numpy as np
from cli.genes.macd_gene import MACDGene

class TestMACDGene(unittest.TestCase):
    """Test case per il gene MACD."""
    
    def setUp(self):
        """Setup del test case."""
        self.gene = MACDGene(params={
            'fast_period': 12,    # Periodo EMA veloce standard
            'slow_period': 26,    # Periodo EMA lenta standard
            'signal_period': 9    # Periodo signal line standard
        })
        
    def test_uptrend(self):
        """Testa il comportamento con trend rialzista."""
        # Crea una serie di prezzi in trend rialzista
        # Ogni giorno sale del 1% con piccole fluttuazioni
        n_days = 100  # Periodo più lungo per MACD
        base_price = 100
        daily_return = 0.01
        noise = 0.002
        
        prices = np.zeros(n_days)
        prices[0] = base_price
        for i in range(1, n_days):
            prices[i] = prices[i-1] * (1 + daily_return + np.random.normal(0, noise))
            
        signal = self.gene.calculate_signal(prices)
        
        # In uptrend, MACD dovrebbe essere positivo
        self.assertGreater(signal, 0.3)
        self.assertLessEqual(signal, 1.0)
        
    def test_downtrend(self):
        """Testa il comportamento con trend ribassista."""
        # Crea una serie di prezzi in trend ribassista
        n_days = 100
        base_price = 100
        daily_return = -0.01
        noise = 0.002
        
        prices = np.zeros(n_days)
        prices[0] = base_price
        for i in range(1, n_days):
            prices[i] = prices[i-1] * (1 + daily_return + np.random.normal(0, noise))
            
        signal = self.gene.calculate_signal(prices)
        
        # In downtrend, MACD dovrebbe essere negativo
        self.assertLess(signal, -0.3)
        self.assertGreaterEqual(signal, -1.0)
        
    def test_sideways(self):
        """Testa il comportamento con mercato laterale."""
        # Crea una serie di prezzi in movimento laterale
        n_days = 100
        base_price = 100
        noise = 0.005
        
        prices = base_price * (1 + np.random.normal(0, noise, n_days))
        signal = self.gene.calculate_signal(prices)
        
        # In mercato laterale, MACD dovrebbe essere vicino a zero
        self.assertGreater(signal, -0.3)
        self.assertLess(signal, 0.3)
        
    def test_trend_acceleration(self):
        """Testa il comportamento con accelerazione del trend."""
        # Crea una serie di prezzi con trend accelerante
        n_days = 100
        base_price = 100
        prices = np.zeros(n_days)
        prices[0] = base_price
        
        # Accelerazione graduale del trend
        for i in range(1, n_days):
            daily_return = 0.001 * (i / 10)  # Rendimento crescente
            prices[i] = prices[i-1] * (1 + daily_return)
            
        signal = self.gene.calculate_signal(prices)
        
        # Con trend in accelerazione, MACD dovrebbe essere fortemente positivo
        self.assertGreater(signal, 0.5)
        
    def test_trend_deceleration(self):
        """Testa il comportamento con decelerazione del trend."""
        # Crea una serie di prezzi con trend decelerante
        n_days = 100
        base_price = 100
        prices = np.zeros(n_days)
        prices[0] = base_price
        
        # Decelerazione graduale del trend
        for i in range(1, n_days):
            daily_return = 0.01 * (1 - i/n_days)  # Rendimento decrescente
            prices[i] = prices[i-1] * (1 + daily_return)
            
        signal = self.gene.calculate_signal(prices)
        
        # Con trend in decelerazione, MACD dovrebbe essere debolmente positivo o negativo
        self.assertLess(signal, 0.3)
        
    def test_trend_reversal(self):
        """Testa il comportamento con inversione del trend."""
        # Crea una serie di prezzi con inversione del trend
        n_days = 100
        base_price = 100
        prices = np.zeros(n_days)
        prices[0] = base_price
        
        # Prima metà in uptrend
        for i in range(1, n_days//2):
            prices[i] = prices[i-1] * (1 + 0.01)
            
        # Seconda metà in downtrend
        for i in range(n_days//2, n_days):
            prices[i] = prices[i-1] * (1 - 0.01)
            
        signal = self.gene.calculate_signal(prices)
        
        # Durante inversione, MACD dovrebbe dare segnale forte
        self.assertNotEqual(signal, 0.0)
        self.assertTrue(abs(signal) > 0.5)
        
    def test_short_data(self):
        """Testa il comportamento con serie temporale corta."""
        # Serie più corta del periodo più lungo necessario
        prices = np.array([100, 101, 102])
        signal = self.gene.calculate_signal(prices)
        
        # Con dati insufficienti dovrebbe restituire 0
        self.assertEqual(signal, 0.0)
        
    def test_signal_bounds(self):
        """Testa che il segnale sia sempre tra -1 e 1."""
        # Test con vari scenari di mercato
        scenarios = [
            np.linspace(100, 200, 100),  # Trend rialzista lineare
            np.linspace(200, 100, 100),  # Trend ribassista lineare
            100 * np.ones(100),          # Prezzo costante
            100 * (1 + np.random.normal(0, 0.02, 100))  # Random walk
        ]
        
        for prices in scenarios:
            signal = self.gene.calculate_signal(prices)
            self.assertGreaterEqual(signal, -1.0)
            self.assertLessEqual(signal, 1.0)
            
    def test_null_data(self):
        """Testa il comportamento con dati nulli."""
        prices = np.zeros(100)
        signal = self.gene.calculate_signal(prices)
        
        # Con prezzi tutti zero dovrebbe restituire 0
        self.assertEqual(signal, 0.0)
        
    def test_nan_data(self):
        """Testa il comportamento con dati NaN."""
        prices = np.array([np.nan] * 100)
        signal = self.gene.calculate_signal(prices)
        
        # Con prezzi NaN dovrebbe restituire 0
        self.assertEqual(signal, 0.0)
        
    def test_divergence(self):
        """Testa il rilevamento delle divergenze."""
        # Crea una serie di prezzi con divergenza ribassista
        # Prezzi fanno nuovi massimi ma MACD fa massimi decrescenti
        n_days = 100
        base_price = 100
        prices = np.zeros(n_days)
        prices[0] = base_price
        
        # Trend rialzista con momentum decrescente
        for i in range(1, n_days):
            momentum = 1 - (i / n_days)  # Momentum decrescente
            daily_return = 0.01 * momentum
            prices[i] = prices[i-1] * (1 + daily_return)
            
        signal = self.gene.calculate_signal(prices)
        
        # Con divergenza ribassista, MACD dovrebbe dare segnale negativo
        self.assertLess(signal, 0)
        
if __name__ == '__main__':
    unittest.main()
