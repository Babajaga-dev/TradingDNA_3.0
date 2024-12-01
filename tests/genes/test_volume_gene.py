"""
Test Volume Gene
--------------
Test funzionali per il gene Volume.
"""

import unittest
import numpy as np
from cli.genes.volume_gene import VolumeGene

class TestVolumeGene(unittest.TestCase):
    """Test case per il gene Volume."""
    
    def setUp(self):
        """Setup del test case."""
        self.gene = VolumeGene(params={
            'period': '20',  # Periodo per la media mobile del volume
            'threshold': '2.0',  # Soglia per il volume ratio
            'min_price_change': '0.005'  # Variazione minima del prezzo
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
        
    def test_increasing_volume(self):
        """Testa il comportamento con volume crescente."""
        n_days = 50
        base_price = 100
        base_volume = 1000000
        
        prices, volumes = self.generate_price_volume_data(n_days, base_price, base_volume)
        
        # Crea volume crescente
        for i in range(1, n_days):
            prices[i] = prices[i-1] * (1 + np.random.normal(0, 0.005))
            volumes[i] = base_volume * (1 + i/n_days)  # Volume crescente linearmente
            
        data = np.array([prices, volumes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con volume crescente, dovrebbe dare segnale positivo
        self.assertGreater(signal, 0.3)
        self.assertLessEqual(signal, 1.0)
        
    def test_decreasing_volume(self):
        """Testa il comportamento con volume decrescente."""
        n_days = 50
        base_price = 100
        base_volume = 1000000
        
        prices, volumes = self.generate_price_volume_data(n_days, base_price, base_volume)
        
        # Crea volume decrescente
        for i in range(1, n_days):
            prices[i] = prices[i-1] * (1 + np.random.normal(0, 0.005))
            volumes[i] = base_volume * (1 - i/n_days/2)  # Volume decrescente
            
        data = np.array([prices, volumes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con volume decrescente, dovrebbe dare segnale negativo
        self.assertLess(signal, -0.3)
        self.assertGreaterEqual(signal, -1.0)
        
    def test_volume_spike(self):
        """Testa il comportamento con spike di volume."""
        n_days = 50
        base_price = 100
        base_volume = 1000000
        
        prices, volumes = self.generate_price_volume_data(n_days, base_price, base_volume)
        
        # Crea volume normale con uno spike
        for i in range(1, n_days):
            prices[i] = prices[i-1] * (1 + np.random.normal(0, 0.005))
            if i == n_days - 1:  # Ultimo giorno con spike
                volumes[i] = base_volume * 5  # Volume 5x
            else:
                volumes[i] = base_volume * (1 + np.random.normal(0, 0.1))
                
        data = np.array([prices, volumes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con spike di volume, dovrebbe dare segnale forte
        self.assertTrue(abs(signal) > 0.7)
        
    def test_volume_with_trend(self):
        """Testa il comportamento del volume con trend di prezzo."""
        n_days = 50
        base_price = 100
        base_volume = 1000000
        
        prices, volumes = self.generate_price_volume_data(n_days, base_price, base_volume)
        
        # Crea trend rialzista con volume correlato
        for i in range(1, n_days):
            prices[i] = prices[i-1] * 1.01  # +1% al giorno
            volumes[i] = base_volume * (1 + i/n_days)  # Volume crescente con il trend
            
        data = np.array([prices, volumes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con trend supportato dal volume, dovrebbe dare segnale positivo
        self.assertGreater(signal, 0.5)
        
    def test_volume_breakout(self):
        """Testa il comportamento del volume durante breakout."""
        n_days = 50
        base_price = 100
        base_volume = 1000000
        
        prices, volumes = self.generate_price_volume_data(n_days, base_price, base_volume)
        
        # Crea consolidamento seguito da breakout
        for i in range(1, n_days):
            if i < n_days - 5:  # Consolidamento
                prices[i] = prices[i-1] * (1 + np.random.normal(0, 0.002))
                volumes[i] = base_volume * (1 + np.random.normal(0, 0.1))
            else:  # Breakout
                prices[i] = prices[i-1] * 1.02  # +2% al giorno
                volumes[i] = base_volume * 3  # Volume triplo
                
        data = np.array([prices, volumes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con breakout su volume, dovrebbe dare segnale forte
        self.assertTrue(abs(signal) > 0.7)
        
    def test_volume_consolidation(self):
        """Testa il comportamento del volume durante consolidamento."""
        n_days = 50
        base_price = 100
        base_volume = 1000000
        
        prices, volumes = self.generate_price_volume_data(n_days, base_price, base_volume)
        
        # Crea periodo di consolidamento
        for i in range(1, n_days):
            prices[i] = prices[i-1] * (1 + np.random.normal(0, 0.002))
            volumes[i] = base_volume * (1 - i/n_days/3)  # Volume gradualmente decrescente
            
        data = np.array([prices, volumes]).T
        signal = self.gene.calculate_signal(data)
        
        # Durante consolidamento, dovrebbe dare segnale debole
        self.assertGreater(signal, -0.3)
        self.assertLess(signal, 0.3)
        
    def test_volume_price_divergence(self):
        """Testa il comportamento con divergenza prezzo-volume."""
        n_days = 50
        base_price = 100
        base_volume = 1000000
        
        prices, volumes = self.generate_price_volume_data(n_days, base_price, base_volume)
        
        # Crea divergenza: prezzo sale ma volume scende
        for i in range(1, n_days):
            prices[i] = prices[i-1] * 1.01  # Prezzo sale
            volumes[i] = base_volume * (1 - i/n_days/2)  # Volume scende
            
        data = np.array([prices, volumes]).T
        signal = self.gene.calculate_signal(data)
        
        # Con divergenza, dovrebbe dare segnale negativo
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
            (1.01, 1.1),   # Prezzo e volume crescenti
            (0.99, 0.9),   # Prezzo e volume decrescenti
            (1.00, 2.0),   # Prezzo stabile, volume raddoppiato
            (1.02, 0.5)    # Prezzo sale, volume dimezzato
        ]
        
        for price_mult, volume_mult in scenarios:
            prices, volumes = self.generate_price_volume_data(n_days, 100, 1000000)
            
            for i in range(1, n_days):
                prices[i] = prices[i-1] * price_mult
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
