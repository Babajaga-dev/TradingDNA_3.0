"""
Test Moving Average Gene
-----------------------
Test funzionali per il gene Moving Average.
"""

import unittest
import numpy as np
from cli.genes.moving_average_gene import MovingAverageGene

class TestMovingAverageGene(unittest.TestCase):
    """Test case per il gene Moving Average."""
    
    def setUp(self):
        """Setup del test case."""
        self.gene = MovingAverageGene(params={
            'fast_period': 10,    # Periodo MA veloce
            'slow_period': 20     # Periodo MA lenta
        })
        
    def test_crossover_up(self):
        """Testa il comportamento durante crossover rialzista."""
        # Crea una serie di prezzi che genera un golden cross
        n_days = 50
        base_price = 100
        prices = np.zeros(n_days)
        prices[0] = base_price
        
        # Prima parte flat
        prices[:30] = base_price
        
        # Ultima parte con trend rialzista per generare crossover
        for i in range(30, n_days):
            prices[i] = prices[i-1] * 1.01
            
        signal = self.gene.calculate_signal(prices)
        
        # Durante golden cross, dovrebbe dare segnale positivo forte
        self.assertGreater(signal, 0.7)
        self.assertLessEqual(signal, 1.0)
        
    def test_crossover_down(self):
        """Testa il comportamento durante crossover ribassista."""
        # Crea una serie di prezzi che genera un death cross
        n_days = 50
        base_price = 100
        prices = np.zeros(n_days)
        prices[0] = base_price
        
        # Prima parte flat
        prices[:30] = base_price
        
        # Ultima parte con trend ribassista per generare crossover
        for i in range(30, n_days):
            prices[i] = prices[i-1] * 0.99
            
        signal = self.gene.calculate_signal(prices)
        
        # Durante death cross, dovrebbe dare segnale negativo forte
        self.assertLess(signal, -0.7)
        self.assertGreaterEqual(signal, -1.0)
        
    def test_strong_trend(self):
        """Testa il comportamento durante trend forte."""
        # Crea una serie di prezzi con trend forte
        n_days = 50
        base_price = 100
        daily_return = 0.02  # 2% al giorno
        noise = 0.001
        
        prices = np.zeros(n_days)
        prices[0] = base_price
        for i in range(1, n_days):
            prices[i] = prices[i-1] * (1 + daily_return + np.random.normal(0, noise))
            
        signal = self.gene.calculate_signal(prices)
        
        # Con trend forte, il segnale dovrebbe essere forte
        self.assertGreater(abs(signal), 0.7)
        
    def test_weak_trend(self):
        """Testa il comportamento durante trend debole."""
        # Crea una serie di prezzi con trend debole
        n_days = 50
        base_price = 100
        daily_return = 0.001  # 0.1% al giorno
        noise = 0.001
        
        prices = np.zeros(n_days)
        prices[0] = base_price
        for i in range(1, n_days):
            prices[i] = prices[i-1] * (1 + daily_return + np.random.normal(0, noise))
            
        signal = self.gene.calculate_signal(prices)
        
        # Con trend debole, il segnale dovrebbe essere debole
        self.assertLess(abs(signal), 0.3)
        
    def test_sideways(self):
        """Testa il comportamento durante mercato laterale."""
        # Crea una serie di prezzi in movimento laterale
        n_days = 50
        base_price = 100
        noise = 0.005
        
        prices = base_price * (1 + np.random.normal(0, noise, n_days))
        signal = self.gene.calculate_signal(prices)
        
        # In mercato laterale, il segnale dovrebbe essere vicino a zero
        self.assertGreater(signal, -0.3)
        self.assertLess(signal, 0.3)
        
    def test_support_resistance(self):
        """Testa il comportamento vicino a supporti/resistenze dinamici."""
        # Crea una serie di prezzi che testa la media mobile come supporto
        n_days = 50
        base_price = 100
        prices = np.zeros(n_days)
        prices[0] = base_price
        
        # Trend rialzista con pullback verso la media
        for i in range(1, n_days):
            if i < n_days * 0.8:
                prices[i] = prices[i-1] * 1.01  # Trend up
            else:
                prices[i] = prices[i-1] * 0.995  # Pullback
                
        signal = self.gene.calculate_signal(prices)
        
        # Test della media mobile come supporto dovrebbe dare segnale
        self.assertNotEqual(signal, 0.0)
        
    def test_momentum(self):
        """Testa il comportamento con momentum variabile."""
        # Crea una serie di prezzi con momentum variabile
        n_days = 50
        base_price = 100
        prices = np.zeros(n_days)
        prices[0] = base_price
        
        # Momentum crescente
        for i in range(1, n_days):
            momentum = i / n_days  # Momentum crescente
            prices[i] = prices[i-1] * (1 + 0.01 * momentum)
            
        signal = self.gene.calculate_signal(prices)
        
        # Con momentum crescente, il segnale dovrebbe essere positivo
        self.assertGreater(signal, 0)
        
    def test_trend_reversal(self):
        """Testa il comportamento durante inversione del trend."""
        # Crea una serie di prezzi con inversione del trend
        n_days = 50
        base_price = 100
        prices = np.zeros(n_days)
        prices[0] = base_price
        
        # Prima metà in uptrend
        for i in range(1, n_days//2):
            prices[i] = prices[i-1] * 1.01
            
        # Seconda metà in downtrend
        for i in range(n_days//2, n_days):
            prices[i] = prices[i-1] * 0.99
            
        signal = self.gene.calculate_signal(prices)
        
        # Durante inversione, il segnale dovrebbe essere significativo
        self.assertTrue(abs(signal) > 0.5)
        
    def test_short_data(self):
        """Testa il comportamento con serie temporale corta."""
        # Serie più corta del periodo più lungo
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
