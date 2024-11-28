"""
Gene Base
---------
Classe base per tutti i geni del trading system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import numpy as np
from ..config.config_loader import get_config_loader
from ..logger.log_manager import get_logger

class Gene(ABC):
    """Classe base per tutti i geni."""
    
    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        """
        Inizializza il gene.
        
        Args:
            name: Nome del gene
            params: Parametri specifici del gene (opzionale)
        """
        self.name = name
        self.logger = get_logger(__name__)
        self.config = get_config_loader()
        
        # Carica configurazioni base
        base_config = self.config.get_value('gene.base', {})
        self.mutation_rate = base_config.get('mutation_rate', 0.1)
        self.crossover_rate = base_config.get('crossover_rate', 0.7)
        self.weight = base_config.get('weight', 1.0)
        self.test_period_days = base_config.get('test_period_days', 30)
        
        # Carica parametri specifici del gene
        gene_config = self.config.get_value(f'gene.{name}.default', {})
        self.params = gene_config.copy()
        if params:
            self.params.update(params)
            
        # Carica vincoli
        self.constraints = self.config.get_value(f'gene.{name}.constraints', {})
        
        self.logger.info(f"Gene {name} inizializzato con parametri: {self.params}")
        
    def validate_params(self) -> bool:
        """
        Valida i parametri del gene secondo i vincoli configurati.
        
        Returns:
            True se i parametri sono validi, False altrimenti
        """
        try:
            for param, value in self.params.items():
                if param in self.constraints:
                    constraint = self.constraints[param]
                    
                    # Controlla limiti min/max per parametri numerici
                    if isinstance(value, (int, float)):
                        if 'min' in constraint and value < constraint['min']:
                            raise ValueError(f"Parametro {param} sotto il minimo: {value} < {constraint['min']}")
                        if 'max' in constraint and value > constraint['max']:
                            raise ValueError(f"Parametro {param} sopra il massimo: {value} > {constraint['max']}")
                            
                    # Controlla valori enum
                    if 'types' in constraint and value not in constraint['types']:
                        raise ValueError(f"Valore non valido per {param}: {value}. Valori permessi: {constraint['types']}")
                        
            return True
            
        except ValueError as e:
            self.logger.error(f"Validazione parametri fallita per {self.name}: {str(e)}")
            return False
            
    def mutate(self) -> None:
        """
        Applica mutazione ai parametri del gene.
        """
        if np.random.random() > self.mutation_rate:
            return
            
        param = np.random.choice(list(self.params.keys()))
        constraint = self.constraints.get(param, {})
        
        if isinstance(self.params[param], (int, float)):
            # Mutazione parametri numerici
            min_val = constraint.get('min', self.params[param] * 0.5)
            max_val = constraint.get('max', self.params[param] * 1.5)
            
            if isinstance(self.params[param], int):
                self.params[param] = np.random.randint(min_val, max_val + 1)
            else:
                self.params[param] = np.random.uniform(min_val, max_val)
                
        elif 'types' in constraint:
            # Mutazione parametri enum
            self.params[param] = np.random.choice(constraint['types'])
            
        self.logger.info(f"Gene {self.name} mutato: {param} = {self.params[param]}")
        
    def crossover(self, other: 'Gene') -> tuple['Gene', 'Gene']:
        """
        Esegue il crossover con un altro gene.
        
        Args:
            other: Altro gene per il crossover
            
        Returns:
            Tupla con i due geni figli
        """
        if not isinstance(other, type(self)):
            raise ValueError(f"Crossover non possibile tra {type(self)} e {type(other)}")
            
        if np.random.random() > self.crossover_rate:
            return self, other
            
        child1 = type(self)(self.name, self.params.copy())
        child2 = type(self)(self.name, other.params.copy())
        
        # Scambia casualmente i parametri
        for param in self.params:
            if np.random.random() < 0.5:
                child1.params[param], child2.params[param] = child2.params[param], child1.params[param]
                
        self.logger.info(f"Crossover eseguito tra due geni {self.name}")
        return child1, child2
        
    @abstractmethod
    def calculate_signal(self, data: np.ndarray) -> float:
        """
        Calcola il segnale del gene sui dati forniti.
        
        Args:
            data: Array numpy con i dati di mercato
            
        Returns:
            Segnale normalizzato tra -1 e 1
        """
        pass
        
    @abstractmethod
    def evaluate(self, data: np.ndarray) -> float:
        """
        Valuta le performance del gene sui dati forniti.
        
        Args:
            data: Array numpy con i dati di mercato
            
        Returns:
            Punteggio di fitness del gene
        """
        pass
