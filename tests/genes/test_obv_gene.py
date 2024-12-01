"""
Test OBV Gene
------------
Test funzionali per il gene OBV (On Balance Volume).
"""

import unittest
import numpy as np
from cli.genes.obv_gene import OBVGene

class TestOBVGene(unittest.TestCase):
    """Test case per il gene OBV."""
    
    def setUp(self):
        """Setup del test case."""
        self.gene = OBVGene(params={
            'period': 20  # Periodo per la media mobile dell'OBV
        })
        
    def generate_price_volume_data(self, n_days, base_price=100, base_volume=1000000):
        """
        Genera dati di prezzo e volume simulati.
        
        Args:
            n_days: Numero di giorni
            base_price: Prezzo base iniziale
            base_volume: Volume base giornaliero
            
        Returns:
            Tuple di array (prices, volumes)
        """
        prices = np.zeros(n_days)
        volumes = np.zeros(n_days)
        
        prices[0] = base_price
        volumes[0] = base_volume
        
        return prices, volumes
        
    def test_trend_confirmation(self):
        """Testa il comportamento con trend confermato dal volume."""
        n_days = 50
        base_price = 100
        base_volume = 1000000
        
        prices, volumes = self.generate_price_volume_data(n_days, base_price, base_volume)
        
        # Crea trend rialzista con volume crescente
        for i in range(1, n_days):
            prices[i] = prices[i-1] * (1 + 0.01)  # +1% al giorno
            volumes[i] = base_volume * (1 + i/n_days)  # Volume crescente
            
        data = np.array([prices, volumes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con trend confermato dal volume, dovrebbe dare segnale forte
        self.assertGreater(signal, 0.7)
        self.assertLessEqual(signal, 1.0)
        
    def test_trend_divergence(self):
        """Testa il comportamento con divergenza prezzo-volume."""
        n_days = 50
        base_price = 100
        base_volume = 1000000
        
        prices, volumes = self.generate_price_volume_data(n_days, base_price, base_volume)
        
        # Crea trend rialzista con volume decrescente (divergenza)
        for i in range(1, n_days):
            prices[i] = prices[i-1] * (1 + 0.01)  # +1% al giorno
            volumes[i] = base_volume * (1 - i/n_days/2)  # Volume decrescente
            
        data = np.array([prices, volumes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con divergenza, dovrebbe dare segnale negativo
        self.assertLess(signal, 0)
        
    def test_breakout_volume(self):
        """Testa il comportamento durante breakout con volume."""
        n_days = 50
        base_price = 100
        base_volume = 1000000
        
        prices, volumes = self.generate_price_volume_data(n_days, base_price, base_volume)
        
        # Crea movimento laterale seguito da breakout con volume
        for i in range(1, n_days):
            if i < n_days - 5:
                prices[i] = prices[i-1] * (1 + np.random.normal(0, 0.002))
                volumes[i] = base_volume * (1 + np.random.normal(0, 0.1))
            else:
                # Breakout negli ultimi 5 giorni
                prices[i] = prices[i-1] * 1.02  # +2% al giorno
                volumes[i] = base_volume * 2  # Volume doppio
                
        data = np.array([prices, volumes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con breakout su volume, dovrebbe dare segnale forte
        self.assertGreater(abs(signal), 0.7)
        
    def test_increasing_volume(self):
        """Testa il comportamento con volume crescente."""
        n_days = 50
        base_price = 100
        base_volume = 1000000
        
        prices, volumes = self.generate_price_volume_data(n_days, base_price, base_volume)
        
        # Crea trend con volume costantemente crescente
        for i in range(1, n_days):
            prices[i] = prices[i-1] * (1 + np.random.normal(0, 0.005))
            volumes[i] = base_volume * (1 + i/n_days)
            
        data = np.array([prices, volumes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con volume crescente, dovrebbe dare segnale positivo
        self.assertGreater(signal, 0)
        
    def test_decreasing_volume(self):
        """Testa il comportamento con volume decrescente."""
        n_days = 50
        base_price = 100
        base_volume = 1000000
        
        prices, volumes = self.generate_price_volume_data(n_days, base_price, base_volume)
        
        # Crea trend con volume costantemente decrescente
        for i in range(1, n_days):
            prices[i] = prices[i-1] * (1 + np.random.normal(0, 0.005))
            volumes[i] = base_volume * (1 - i/n_days/2)
            
        data = np.array([prices, volumes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con volume decrescente, dovrebbe dare segnale negativo
        self.assertLess(signal, 0)
        
    def test_flat_market_increasing_volume(self):
        """Testa il comportamento in mercato laterale con volume crescente."""
        n_days = 50
        base_price = 100
        base_volume = 1000000
        
        prices, volumes = self.generate_price_volume_data(n_days, base_price, base_volume)
        
        # Crea mercato laterale con volume crescente
        for i in range(1, n_days):
            prices[i] = prices[i-1] * (1 + np.random.normal(0, 0.002))
            volumes[i] = base_volume * (1 + i/n_days)
            
        data = np.array([prices, volumes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con accumulo di volume, dovrebbe dare segnale positivo moderato
        self.assertGreater(signal, 0)
        self.assertLess(signal, 0.7)
        
    def test_price_surge_low_volume(self):
        """Testa il comportamento con aumento di prezzo ma basso volume."""
        n_days = 50
        base_price = 100
        base_volume = 1000000
        
        prices, volumes = self.generate_price_volume_data(n_days, base_price, base_volume)
        
        # Crea forte aumento di prezzo con volume basso
        for i in range(1, n_days):
            prices[i] = prices[i-1] * 1.02  # +2% al giorno
            volumes[i] = base_volume * 0.5  # Volume dimezzato
            
        data = np.array([prices, volumes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con movimento non supportato dal volume, dovrebbe dare segnale negativo
        self.assertLess(signal, 0)
        
    def test_short_data(self):
        """Testa il comportamento con serie temporale corta."""
        prices, volumes = self.generate_price_volume_data(3, 100, 1000000)
        data = np.array([prices, volumes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con dati insufficienti dovrebbe restituire 0
        self.assertEqual(signal, 0.0)
        
    def test_signal_bounds(self):
        """Testa che il segnale sia sempre tra -1 e 1."""
        n_days = 50
        scenarios = [
            (0.01, 1.1),   # Prezzo +1%, volume +10%
            (-0.01, 0.9),  # Prezzo -1%, volume -10%
            (0.02, 2.0),   # Prezzo +2%, volume +100%
            (-0.02, 0.5)   # Prezzo -2%, volume -50%
        ]
        
        for price_change, volume_mult in scenarios:
            prices, volumes = self.generate_price_volume_data(n_days, 100, 1000000)
            
            for i in range(1, n_days):
                prices[i] = prices[i-1] * (1 + price_change)
                volumes[i] = volumes[0] * volume_mult
                
            data = np.array([prices, volumes]).T
            signal = self.gene.calculate_signal(data)
            
            self.assertGreaterEqual(signal, -1.0)
            self.assertLessEqual(signal, 1.0)
            
    def test_null_data(self):
        """Testa il comportamento con dati nulli."""
        data = np.zeros((50, 2))  # [prices, volumes] tutti zero
        signal = self.gene.calculate_signal(data)
        
        # Con dati nulli dovrebbe restituire 0
        self.assertEqual(signal, 0.0)
        
    def test_nan_data(self):
        """Testa il comportamento con dati NaN."""
        data = np.full((50, 2), np.nan)  # [prices, volumes] tutti NaN
        signal = self.gene.calculate_signal(data)
        
        # Con dati NaN dovrebbe restituire 0
        self.assertEqual(signal, 0.0)
        
if __name__ == '__main__':
    unittest.main()
