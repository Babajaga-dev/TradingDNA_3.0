"""
Test Stochastic Gene
-------------------
Test funzionali per il gene Stochastic.
"""

import unittest
import numpy as np
from cli.genes.stochastic_gene import StochasticGene

class TestStochasticGene(unittest.TestCase):
    """Test case per il gene Stochastic."""
    
    def setUp(self):
        """Setup del test case."""
        self.gene = StochasticGene(params={
            'k_period': 14,     # Periodo per %K
            'd_period': 3,      # Periodo per %D
            'slowing': 3        # Periodo di rallentamento
        })
        
    def generate_hlc_data(self, n_days, base_price=100):
        """
        Genera dati High, Low, Close simulati.
        
        Args:
            n_days: Numero di giorni
            base_price: Prezzo base iniziale
            
        Returns:
            Tuple di array (highs, lows, closes)
        """
        highs = np.zeros(n_days)
        lows = np.zeros(n_days)
        closes = np.zeros(n_days)
        
        closes[0] = base_price
        highs[0] = base_price * 1.01
        lows[0] = base_price * 0.99
        
        return highs, lows, closes
        
    def test_overbought(self):
        """Testa il comportamento in condizioni di ipercomprato."""
        n_days = 50
        base_price = 100
        
        highs, lows, closes = self.generate_hlc_data(n_days, base_price)
        
        # Crea una serie di prezzi che porta a condizioni di ipercomprato
        for i in range(1, n_days):
            closes[i] = closes[i-1] * 1.01  # +1% al giorno
            highs[i] = closes[i] * 1.005    # High leggermente sopra close
            lows[i] = closes[i] * 0.998     # Low vicino al close
            
        data = np.array([highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # In condizioni di ipercomprato, dovrebbe dare segnale negativo forte
        self.assertLess(signal, -0.7)
        self.assertGreaterEqual(signal, -1.0)
        
    def test_oversold(self):
        """Testa il comportamento in condizioni di ipervenduto."""
        n_days = 50
        base_price = 100
        
        highs, lows, closes = self.generate_hlc_data(n_days, base_price)
        
        # Crea una serie di prezzi che porta a condizioni di ipervenduto
        for i in range(1, n_days):
            closes[i] = closes[i-1] * 0.99   # -1% al giorno
            highs[i] = closes[i] * 1.002     # High vicino al close
            lows[i] = closes[i] * 0.995      # Low leggermente sotto close
            
        data = np.array([highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # In condizioni di ipervenduto, dovrebbe dare segnale positivo forte
        self.assertGreater(signal, 0.7)
        self.assertLessEqual(signal, 1.0)
        
    def test_kd_crossover_up(self):
        """Testa il comportamento durante crossover rialzista di %K e %D."""
        n_days = 50
        base_price = 100
        
        highs, lows, closes = self.generate_hlc_data(n_days, base_price)
        
        # Crea una serie che genera crossover rialzista
        for i in range(1, n_days-5):
            closes[i] = closes[i-1] * 0.99
            highs[i] = closes[i] * 1.005
            lows[i] = closes[i] * 0.995
            
        # Ultimi giorni con movimento rialzista per generare crossover
        for i in range(n_days-5, n_days):
            closes[i] = closes[i-1] * 1.02
            highs[i] = closes[i] * 1.01
            lows[i] = closes[i] * 0.99
            
        data = np.array([highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Durante crossover rialzista, dovrebbe dare segnale positivo
        self.assertGreater(signal, 0)
        
    def test_kd_crossover_down(self):
        """Testa il comportamento durante crossover ribassista di %K e %D."""
        n_days = 50
        base_price = 100
        
        highs, lows, closes = self.generate_hlc_data(n_days, base_price)
        
        # Crea una serie che genera crossover ribassista
        for i in range(1, n_days-5):
            closes[i] = closes[i-1] * 1.01
            highs[i] = closes[i] * 1.005
            lows[i] = closes[i] * 0.995
            
        # Ultimi giorni con movimento ribassista per generare crossover
        for i in range(n_days-5, n_days):
            closes[i] = closes[i-1] * 0.98
            highs[i] = closes[i] * 1.01
            lows[i] = closes[i] * 0.99
            
        data = np.array([highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Durante crossover ribassista, dovrebbe dare segnale negativo
        self.assertLess(signal, 0)
        
    def test_divergence(self):
        """Testa il comportamento con divergenza prezzo-momentum."""
        n_days = 50
        base_price = 100
        
        highs, lows, closes = self.generate_hlc_data(n_days, base_price)
        
        # Crea divergenza: prezzi fanno nuovi massimi ma momentum diminuisce
        for i in range(1, n_days):
            closes[i] = closes[i-1] * (1 + 0.01 * (1 - i/n_days))  # Momentum decrescente
            highs[i] = closes[i] * (1 + 0.01 * (1 - i/n_days))
            lows[i] = closes[i] * (1 - 0.01 * (1 - i/n_days))
            
        data = np.array([highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con divergenza, dovrebbe dare segnale significativo
        self.assertTrue(abs(signal) > 0.5)
        
    def test_sideways(self):
        """Testa il comportamento in mercato laterale."""
        n_days = 50
        base_price = 100
        
        highs, lows, closes = self.generate_hlc_data(n_days, base_price)
        
        # Crea movimento laterale
        for i in range(1, n_days):
            closes[i] = base_price * (1 + np.random.normal(0, 0.005))
            highs[i] = closes[i] * 1.005
            lows[i] = closes[i] * 0.995
            
        data = np.array([highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # In mercato laterale, il segnale dovrebbe essere moderato
        self.assertGreater(signal, -0.3)
        self.assertLess(signal, 0.3)
        
    def test_strong_trend(self):
        """Testa il comportamento durante trend forte."""
        n_days = 50
        base_price = 100
        
        highs, lows, closes = self.generate_hlc_data(n_days, base_price)
        
        # Crea trend forte
        for i in range(1, n_days):
            closes[i] = closes[i-1] * 1.02  # +2% al giorno
            highs[i] = closes[i] * 1.01
            lows[i] = closes[i] * 0.99
            
        data = np.array([highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con trend forte, il segnale dovrebbe essere significativo
        self.assertTrue(abs(signal) > 0.7)
        
    def test_short_data(self):
        """Testa il comportamento con serie temporale corta."""
        highs, lows, closes = self.generate_hlc_data(3, 100)
        data = np.array([highs, lows, closes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con dati insufficienti dovrebbe restituire 0
        self.assertEqual(signal, 0.0)
        
    def test_signal_bounds(self):
        """Testa che il segnale sia sempre tra -1 e 1."""
        n_days = 50
        scenarios = [
            (1.02, 1.01, 0.99),  # Trend rialzista
            (0.98, 1.01, 0.99),  # Trend ribassista
            (1.00, 1.01, 0.99),  # Mercato laterale
            (1.05, 1.02, 0.98)   # Alta volatilità
        ]
        
        for close_mult, high_mult, low_mult in scenarios:
            highs, lows, closes = self.generate_hlc_data(n_days, 100)
            
            for i in range(1, n_days):
                closes[i] = closes[i-1] * close_mult
                highs[i] = closes[i] * high_mult
                lows[i] = closes[i] * low_mult
                
            data = np.array([highs, lows, closes]).T
            signal = self.gene.calculate_signal(data)
            
            self.assertGreaterEqual(signal, -1.0)
            self.assertLessEqual(signal, 1.0)
            
    def test_null_data(self):
        """Testa il comportamento con dati nulli."""
        data = np.zeros((50, 3))  # [high, low, close] tutti zero
        signal = self.gene.calculate_signal(data)
        
        # Con dati nulli dovrebbe restituire 0
        self.assertEqual(signal, 0.0)
        
    def test_nan_data(self):
        """Testa il comportamento con dati NaN."""
        data = np.full((50, 3), np.nan)  # [high, low, close] tutti NaN
        signal = self.gene.calculate_signal(data)
        
        # Con dati NaN dovrebbe restituire 0
        self.assertEqual(signal, 0.0)
        
if __name__ == '__main__':
    unittest.main()
