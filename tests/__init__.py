"""
Test Suite TradingDNA
-------------------
Suite completa di test per il sistema TradingDNA.
"""

import unittest
from tests.genes.test_rsi_gene import TestRSIGene
from tests.genes.test_macd_gene import TestMACDGene
from tests.genes.test_bollinger_gene import TestBollingerGene
from tests.genes.test_moving_average_gene import TestMovingAverageGene
from tests.genes.test_atr_gene import TestATRGene
from tests.genes.test_obv_gene import TestOBVGene
from tests.genes.test_stochastic_gene import TestStochasticGene
from tests.genes.test_volume_gene import TestVolumeGene
from tests.genes.test_candlestick_gene import TestCandlestickGene
from tests.genes.test_volatility_breakout_gene import TestVolatilityBreakoutGene

def run_all_tests():
    """Esegue tutti i test del sistema."""
    # Crea test suite
    test_suite = unittest.TestSuite()
    
    # Aggiungi tutti i test dei geni
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestRSIGene))
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMACDGene))
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestBollingerGene))
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMovingAverageGene))
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestATRGene))
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestOBVGene))
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestStochasticGene))
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestVolumeGene))
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCandlestickGene))
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestVolatilityBreakoutGene))
    
    # Esegui i test
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(test_suite)

if __name__ == '__main__':
    run_all_tests()
