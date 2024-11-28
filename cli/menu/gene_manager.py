"""
Gene Manager
-----------
Wrapper per la gestione dei geni del trading system attraverso il menu CLI.
Mantiene la stessa interfaccia verso l'esterno delegando le operazioni
alle classi specializzate GeneManagerBase e GeneManagerAnalytics.
"""

from .gene_manager_analytics import GeneManagerAnalytics

class GeneManager(GeneManagerAnalytics):
    """
    Wrapper per la gestione dei geni.
    Eredita da GeneManagerAnalytics che a sua volta eredita da GeneManagerBase,
    mantenendo così tutte le funzionalità in un'unica interfaccia.
    """
    pass
