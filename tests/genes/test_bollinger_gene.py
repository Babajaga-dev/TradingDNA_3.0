"""
Test Bollinger Gene
------------------
Test funzionali per il gene Bollinger Bands.
"""

import unittest
import numpy as np
from cli.genes.bollinger_gene import BollingerGene

class TestBollingerGene(unittest.TestCase):
    """Test case per il gene Bollinger."""
    
    def setUp(self):
        """Setup del test case."""
        self.gene = BollingerGene(params={
            'period': 20,         # Periodo standard per le bande
            'num_std': 2.0        # Numero di deviazioni standard
        })
        
    def test_breakout_up(self):
        """Testa il comportamento con breakout rialzista."""
        # Crea una serie di prezzi con breakout sopra la banda superiore
        n_days = 50
        base_price = 100
        prices = np.ones(n_days) * base_price
        
        # Ultimi giorni con forte movimento rialzista
        breakout_days = 5
        for i in range(n_days - breakout_days, n_days):
            prices[i] = prices[i-1] * 1.02  # +2% al giorno
            
        signal = self.gene.calculate_signal(prices)
        
        # Con breakout rialzista, dovrebbe dare segnale positivo forte
        self.assertGreater(signal, 0.7)
        self.assertLessEqual(signal, 1.0)
        
    def test_breakout_down(self):
        """Testa il comportamento con breakout ribassista."""
        # Crea una serie di prezzi con breakout sotto la banda inferiore
        n_days = 50
        base_price = 100
        prices = np.ones(n_days) * base_price
        
        # Ultimi giorni con forte movimento ribassista
        breakout_days = 5
        for i in range(n_days - breakout_days, n_days):
            prices[i] = prices[i-1] * 0.98  # -2% al giorno
            
        signal = self.gene.calculate_signal(prices)
        
        # Con breakout ribassista, dovrebbe dare segnale negativo forte
        self.assertLess(signal, -0.7)
        self.assertGreaterEqual(signal, -1.0)
        
    def test_squeeze(self):
        """Testa il comportamento durante uno squeeze delle bande."""
        # Crea una serie di prezzi con bassa volatilità
        n_days = 50
        base_price = 100
        noise = 0.001  # Volatilità molto bassa
        
        prices = base_price * (1 + np.random.normal(0, noise, n_days))
        signal = self.gene.calculate_signal(prices)
        
        # Durante uno squeeze, il segnale dovrebbe essere vicino a zero
        self.assertGreater(signal, -0.3)
        self.assertLess(signal, 0.3)
        
    def test_expansion(self):
        """Testa il comportamento durante l'espansione delle bande."""
        # Crea una serie di prezzi con volatilità crescente
        n_days = 50
        base_price = 100
        prices = np.zeros(n_days)
        prices[0] = base_price
        
        # Volatilità crescente
        for i in range(1, n_days):
            volatility = 0.001 * (i / 10)  # Volatilità crescente
            prices[i] = prices[i-1] * (1 + np.random.normal(0, volatility))
            
        signal = self.gene.calculate_signal(prices)
        
        # Con espansione delle bande, il segnale dovrebbe essere significativo
        self.assertTrue(abs(signal) > 0.5)
        
    def test_mean_reversion(self):
        """Testa il comportamento durante il ritorno alla media."""
        # Crea una serie di prezzi che torna verso la media
        n_days = 50
        base_price = 100
        prices = np.zeros(n_days)
        prices[0] = base_price
        
        # Prima metà: allontanamento dalla media
        for i in range(1, n_days//2):
            prices[i] = prices[i-1] * 1.01
            
        # Seconda metà: ritorno verso la media
        for i in range(n_days//2, n_days):
            target = base_price
            prices[i] = prices[i-1] + (target - prices[i-1]) * 0.1
            
        signal = self.gene.calculate_signal(prices)
        
        # Durante mean reversion, il segnale dovrebbe indicare la direzione del movimento
        if prices[-1] > base_price:
            self.assertLess(signal, 0)  # Segnale di vendita se sopra la media
        else:
            self.assertGreater(signal, 0)  # Segnale di acquisto se sotto la media
            
    def test_high_volatility(self):
        """Testa il comportamento in condizioni di alta volatilità."""
        # Crea una serie di prezzi con alta volatilità
        n_days = 50
        base_price = 100
        high_volatility = 0.03  # 3% di volatilità
        
        prices = base_price * (1 + np.random.normal(0, high_volatility, n_days))
        signal = self.gene.calculate_signal(prices)
        
        # Con alta volatilità, il segnale dovrebbe essere più forte
        self.assertTrue(abs(signal) > 0.5)
        
    def test_low_volatility(self):
        """Testa il comportamento in condizioni di bassa volatilità."""
        # Crea una serie di prezzi con bassa volatilità
        n_days = 50
        base_price = 100
        low_volatility = 0.001  # 0.1% di volatilità
        
        prices = base_price * (1 + np.random.normal(0, low_volatility, n_days))
        signal = self.gene.calculate_signal(prices)
        
        # Con bassa volatilità, il segnale dovrebbe essere più debole
        self.assertTrue(abs(signal) < 0.3)
        
    def test_trend_with_volatility(self):
        """Testa il comportamento con trend e volatilità variabile."""
        # Crea una serie di prezzi con trend e volatilità variabile
        n_days = 50
        base_price = 100
        prices = np.zeros(n_days)
        prices[0] = base_price
        
        for i in range(1, n_days):
            trend = 0.001 * i  # Trend crescente
            volatility = 0.002 * (1 + np.sin(i/10))  # Volatilità oscillante
            prices[i] = prices[i-1] * (1 + trend + np.random.normal(0, volatility))
            
        signal = self.gene.calculate_signal(prices)
        
        # Verifica che il segnale sia entro i limiti
        self.assertGreaterEqual(signal, -1.0)
        self.assertLessEqual(signal, 1.0)
        
    def test_short_data(self):
        """Testa il comportamento con serie temporale corta."""
        # Serie più corta del periodo delle bande
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
