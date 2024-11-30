"""
Population Models
---------------
Modelli SQLAlchemy per la gestione delle popolazioni di trading.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List, Union, Tuple
import numpy as np
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, 
    DateTime, ForeignKey, JSON, CheckConstraint, Index,
    and_, or_, func
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import Base
from data.database.session_manager import DBSessionManager

# Ottieni l'istanza del session manager
db = DBSessionManager()

# Configurazioni di default per i geni
DEFAULT_GENE_CONFIGS = {
    'rsi': {
        'period': 14,
        'overbought': 70,
        'oversold': 30,
        'weight': 1.0,
        'risk_factor': 0.5
    },
    'macd': {
        'fast_period': 12,
        'slow_period': 26,
        'signal_period': 9,
        'weight': 1.0,
        'risk_factor': 0.6
    },
    'bollinger': {
        'period': 20,
        'std_dev': 2,
        'weight': 1.0,
        'risk_factor': 0.7
    },
    'moving_average': {
        'fast_period': 10,
        'slow_period': 30,
        'weight': 1.0,
        'risk_factor': 0.4
    },
    'atr': {
        'period': 14,
        'multiplier': 2,
        'weight': 1.0,
        'risk_factor': 0.8
    }
}

class RiskProfile:
    """Classe per la gestione del profilo di rischio."""
    
    def __init__(self, max_drawdown: float = 0.2, 
                 position_size: float = 0.1,
                 stop_loss: float = 0.02,
                 take_profit: float = 0.04,
                 risk_reward_ratio: float = 2.0):
        self.max_drawdown = max_drawdown
        self.position_size = position_size
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.risk_reward_ratio = risk_reward_ratio

    def to_dict(self) -> Dict[str, float]:
        """Converte il profilo in dizionario."""
        return {
            'max_drawdown': self.max_drawdown,
            'position_size': self.position_size,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'risk_reward_ratio': self.risk_reward_ratio
        }

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'RiskProfile':
        """Crea profilo da dizionario."""
        return cls(**data)

    def validate(self) -> Tuple[bool, List[str]]:
        """Valida il profilo di rischio."""
        errors = []
        
        if self.max_drawdown <= 0 or self.max_drawdown > 0.5:
            errors.append("Max drawdown deve essere tra 0 e 0.5")
            
        if self.position_size <= 0 or self.position_size > 1:
            errors.append("Position size deve essere tra 0 e 1")
            
        if self.stop_loss <= 0:
            errors.append("Stop loss deve essere maggiore di 0")
            
        if self.take_profit <= self.stop_loss:
            errors.append("Take profit deve essere maggiore dello stop loss")
            
        if self.risk_reward_ratio < 1:
            errors.append("Risk/reward ratio deve essere almeno 1")
            
        return len(errors) == 0, errors

class GeneOptimizer:
    """Classe per l'ottimizzazione dei parametri dei geni."""
    
    def __init__(self, gene_type: str, parameters: Dict[str, Any]):
        self.gene_type = gene_type
        self.parameters = parameters
        self.optimization_history = []
        
    def optimize(self, performance_metric: float) -> Dict[str, Any]:
        """Ottimizza i parametri basandosi sulla performance."""
        if not self.optimization_history:
            self.optimization_history.append({
                'parameters': self.parameters.copy(),
                'performance': performance_metric,
                'timestamp': datetime.utcnow().isoformat()
            })
            return self.parameters
            
        # Trova i migliori parametri storici
        best_config = max(
            self.optimization_history,
            key=lambda x: x['performance']
        )
        
        # Se la performance attuale è peggiore, adatta i parametri
        if performance_metric < best_config['performance']:
            new_params = self._adapt_parameters(
                best_config['parameters'],
                self.parameters,
                performance_metric / best_config['performance']
            )
        else:
            new_params = self.parameters
            
        self.optimization_history.append({
            'parameters': new_params.copy(),
            'performance': performance_metric,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return new_params
        
    def _adapt_parameters(self, 
                         best_params: Dict[str, Any],
                         current_params: Dict[str, Any],
                         performance_ratio: float) -> Dict[str, Any]:
        """Adatta i parametri verso la configurazione migliore."""
        adapted = {}
        
        for key, value in current_params.items():
            if key not in best_params:
                adapted[key] = value
                continue
                
            if isinstance(value, (int, float)):
                # Interpola verso i migliori parametri
                delta = best_params[key] - value
                adapted[key] = value + delta * (1 - performance_ratio)
                
                # Arrotonda a int se necessario
                if isinstance(value, int):
                    adapted[key] = int(round(adapted[key]))
            else:
                # Per parametri non numerici, usa il migliore se la performance è molto peggiore
                adapted[key] = best_params[key] if performance_ratio < 0.5 else value
                
        return adapted

class Population(Base):
    """Modello per le popolazioni di trading."""
    __tablename__ = 'populations'
    
    population_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    max_size = Column(Integer, nullable=False, default=100)
    current_generation = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    status = Column(String(20), default='active')
    diversity_score = Column(Float, default=1.0)
    performance_score = Column(Float, default=0.0)
    
    # Parametri evolutivi
    mutation_rate = Column(Float, default=0.01)
    selection_pressure = Column(Integer, default=5)
    generation_interval = Column(Integer, default=4)
    diversity_threshold = Column(Float, default=0.7)
    
    # Configurazione trading
    symbol_id = Column(Integer, ForeignKey('symbols.id', ondelete='CASCADE'), nullable=False)
    timeframe = Column(String(10), nullable=False)
    
    # Configurazione avanzata
    evolution_config = Column(JSON, default={})
    performance_thresholds = Column(JSON, default={})
    optimization_settings = Column(JSON, default={})
    risk_profile = Column(JSON, default={})
    
    # Relazioni
    symbol = relationship("Symbol", backref="populations", lazy='joined')
    chromosomes = relationship(
        "Chromosome",
        back_populates="population",
        cascade="all, delete-orphan",
        lazy='selectin'
    )
    evolution_history = relationship(
        "EvolutionHistory",
        back_populates="population",
        cascade="all, delete-orphan",
        lazy='selectin'
    )
    
    # Vincoli
    __table_args__ = (
        CheckConstraint('max_size BETWEEN 50 AND 500'),
        CheckConstraint('mutation_rate BETWEEN 0.001 AND 0.05'),
        CheckConstraint('selection_pressure BETWEEN 1 AND 10'),
        CheckConstraint('generation_interval BETWEEN 1 AND 24'),
        CheckConstraint('diversity_threshold BETWEEN 0.5 AND 1.0'),
        CheckConstraint("status IN ('active', 'paused', 'archived')"),
        Index('idx_population_symbol', 'symbol_id'),
        Index('idx_population_status', 'status')
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Inizializza profilo di rischio di default
        if not self.risk_profile:
            self.risk_profile = RiskProfile().to_dict()
    
    def __repr__(self):
        return f"<Population(id={self.population_id}, name='{self.name}', generation={self.current_generation})>"

    @classmethod
    def get_active_populations(cls) -> List["Population"]:
        """Ottiene tutte le popolazioni attive."""
        with db.session() as session:
            return session.query(cls).filter_by(status='active').all()

    @classmethod
    def get_by_symbol(cls, symbol_id: int) -> List["Population"]:
        """Ottiene tutte le popolazioni per un dato simbolo."""
        with db.session() as session:
            return session.query(cls).filter_by(symbol_id=symbol_id).all()

    def update_metrics(self) -> None:
        """Aggiorna le metriche della popolazione."""
        if not self.chromosomes:
            return
            
        # Calcola performance media
        performances = [float(c.performance_metrics.get('total_return', 0)) 
                       for c in self.chromosomes if c.performance_metrics]
        if performances:
            self.performance_score = sum(performances) / len(performances)
            
        # Calcola diversità
        gene_types = set()
        for c in self.chromosomes:
            for g in c.genes:
                gene_types.add(g.gene_type)
        
        total_genes = len(self.chromosomes) * len(gene_types)
        active_genes = sum(1 for c in self.chromosomes 
                          for g in c.genes if g.is_active)
        
        self.diversity_score = active_genes / total_genes if total_genes > 0 else 0

    def evolve_generation(self) -> None:
        """Evolve la popolazione alla prossima generazione."""
        with db.session() as session:
            # Incrementa generazione
            self.current_generation += 1
            
            # Seleziona i migliori cromosomi
            best_chromosomes = Chromosome.get_best_performers(
                self.population_id, 
                limit=int(self.max_size * 0.2)  # Top 20%
            )
            
            # Crea nuova generazione
            new_generation = []
            while len(new_generation) < self.max_size:
                # Seleziona genitori
                parent1, parent2 = np.random.choice(
                    best_chromosomes, 
                    size=2, 
                    replace=False
                )
                
                # Crea figlio
                child = Chromosome.crossover(parent1, parent2)
                
                # Applica mutazione
                if np.random.random() < self.mutation_rate:
                    child.mutate()
                    
                new_generation.append(child)
            
            # Aggiorna popolazione
            session.query(Chromosome)\
                .filter_by(population_id=self.population_id)\
                .update({"status": "archived"})
                
            for chromosome in new_generation:
                session.add(chromosome)
            
            # Aggiorna metriche
            self.update_metrics()
            
            # Registra storia evoluzione
            history = EvolutionHistory(
                population_id=self.population_id,
                generation=self.current_generation,
                mutation_rate=self.mutation_rate
            )
            history.calculate_metrics()
            session.add(history)
            
            session.commit()

    def update_risk_profile(self, profile: RiskProfile) -> Tuple[bool, List[str]]:
        """Aggiorna il profilo di rischio della popolazione."""
        is_valid, errors = profile.validate()
        if not is_valid:
            return False, errors
            
        self.risk_profile = profile.to_dict()
        return True, []

class Chromosome(Base):
    """Modello per i cromosomi delle strategie."""
    __tablename__ = 'chromosomes'
    
    chromosome_id = Column(Integer, primary_key=True)
    population_id = Column(Integer, ForeignKey('populations.population_id', ondelete='CASCADE'), nullable=False)
    fingerprint = Column(String(64), nullable=False)
    generation = Column(Integer, nullable=False)
    age = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    parent1_id = Column(Integer, ForeignKey('chromosomes.chromosome_id', ondelete='SET NULL'))
    parent2_id = Column(Integer, ForeignKey('chromosomes.chromosome_id', ondelete='SET NULL'))
    status = Column(String(20), default='active')
    last_test_date = Column(DateTime(timezone=True))
    
    # Dati strutturati
    performance_metrics = Column(JSON, default={})
    weight_distribution = Column(JSON, default={})
    test_results = Column(JSON, default={})
    fitness_history = Column(JSON, default=[])
    mutation_stats = Column(JSON, default={})
    risk_metrics = Column(JSON, default={})
    
    # Relazioni
    population = relationship(
        "Population",
        back_populates="chromosomes",
        lazy='joined'
    )
    genes = relationship(
        "ChromosomeGene",
        back_populates="chromosome",
        cascade="all, delete-orphan",
        lazy='selectin'
    )
    parent1 = relationship(
        "Chromosome",
        remote_side=[chromosome_id],
        foreign_keys=[parent1_id],
        lazy='selectin'
    )
    parent2 = relationship(
        "Chromosome",
        remote_side=[chromosome_id],
        foreign_keys=[parent2_id],
        lazy='selectin'
    )
    
    # Vincoli e indici
    __table_args__ = (
        CheckConstraint("status IN ('active', 'testing', 'archived')"),
        Index('idx_chromosome_population', 'population_id'),
        Index('idx_chromosome_fingerprint', 'fingerprint'),
        Index('idx_chromosome_status', 'status')
    )
    
    def __repr__(self):
        return f"<Chromosome(id={self.chromosome_id}, population={self.population_id}, generation={self.generation})>"

    @classmethod
    def get_best_performers(cls, population_id: int, limit: int = 10) -> List["Chromosome"]:
        """Ottiene i migliori cromosomi per una data popolazione."""
        with db.session() as session:
            return session.query(cls)\
                .filter_by(population_id=population_id, status='active')\
                .order_by(cls.performance_metrics['total_return'].desc())\
                .limit(limit)\
                .all()

    def calculate_fitness(self) -> float:
        """Calcola il fitness del cromosoma."""
        if not self.performance_metrics or not self.risk_metrics:
            return 0.0
            
        # Metriche di performance
        total_return = float(self.performance_metrics.get('total_return', 0))
        sharpe = float(self.performance_metrics.get('sharpe_ratio', 0))
        
        # Metriche di rischio
        max_dd = float(self.risk_metrics.get('max_drawdown', 0))
        volatility = float(self.risk_metrics.get('volatility', 0))
        var = float(self.risk_metrics.get('value_at_risk', 0))
        
        # Penalizzazioni
        dd_penalty = abs(max_dd) * 2 if abs(max_dd) > 0.2 else 0
        vol_penalty = volatility * 1.5 if volatility > 0.3 else 0
        var_penalty = abs(var) if abs(var) > 0.1 else 0
        
        # Combina le metriche
        fitness = (
            total_return * 0.3 + 
            sharpe * 0.3 - 
            dd_penalty * 0.15 -
            vol_penalty * 0.15 -
            var_penalty * 0.1
        )
                  
        return max(0.0, fitness)

    @classmethod
    def crossover(cls, parent1: "Chromosome", parent2: "Chromosome") -> "Chromosome":
        """Esegue il crossover tra due cromosomi genitori."""
        # Crea nuovo cromosoma
        child = cls(
            population_id=parent1.population_id,
            generation=parent1.population.current_generation + 1,
            parent1_id=parent1.chromosome_id,
            parent2_id=parent2.chromosome_id
        )
        
        # Mescola i geni dei genitori
        gene_types = {g.gene_type for g in parent1.genes + parent2.genes}
        for gene_type in gene_types:
            # Prendi il gene da uno dei genitori
            parent_gene = np.random.choice([
                g for g in (parent1.genes + parent2.genes)
                if g.gene_type == gene_type
            ])
            
            # Crea nuovo gene
            new_gene = ChromosomeGene(
                gene_type=gene_type,
                parameters=parent_gene.parameters.copy(),
                weight=parent_gene.weight,
                is_active=parent_gene.is_active,
                risk_factor=parent_gene.risk_factor
            )
            child.genes.append(new_gene)
        
        # Genera fingerprint
        child.fingerprint = child.generate_fingerprint()
        
        return child

    def mutate(self) -> None:
        """Applica mutazione al cromosoma."""
        mutation_stats = []
        
        for gene in self.genes:
            # Probabilità di mutazione per ogni gene
            if np.random.random() < 0.1:  # 10% per gene
                mutation = gene.mutate()
                if mutation:
                    mutation_stats.append(mutation)
        
        if mutation_stats:
            self.mutation_stats['mutations'] = \
                self.mutation_stats.get('mutations', []) + mutation_stats
            self.last_mutation_date = datetime.utcnow()

    def generate_fingerprint(self) -> str:
        """Genera un fingerprint unico per il cromosoma."""
        import hashlib
        
        # Combina informazioni rilevanti
        data = [
            str(self.population_id),
            str(self.generation),
            str(sorted([
                (g.gene_type, str(g.parameters), g.weight, g.is_active)
                for g in self.genes
            ]))
        ]
        
        # Genera hash
        return hashlib.sha256(''.join(data).encode()).hexdigest()

    def validate(self) -> Tuple[bool, List[str]]:
        """Valida il cromosoma e i suoi geni."""
        errors = []
        
        # Verifica presenza geni
        if not self.genes:
            errors.append("Nessun gene presente nel cromosoma")
            
        # Verifica geni
        for gene in self.genes:
            if not gene.validate_parameters():
                errors.append(f"Parametri non validi per gene {gene.gene_type}")
        
        # Verifica distribuzione pesi
        total_weight = sum(g.weight for g in self.genes if g.is_active)
        if total_weight <= 0:
            errors.append("Nessun gene attivo nel cromosoma")
        elif abs(total_weight - 1.0) > 0.01:
            errors.append(f"Somma pesi non normalizzata: {total_weight}")
            
        # Verifica rischio
        total_risk = sum(g.risk_factor * g.weight 
                        for g in self.genes if g.is_active)
        if total_risk > self.population.risk_profile['max_drawdown']:
            errors.append(f"Rischio totale ({total_risk}) superiore al massimo consentito")
            
        return len(errors) == 0, errors

    def calculate_risk_metrics(self, returns: List[float]) -> None:
        """Calcola le metriche di rischio del cromosoma."""
        if not returns:
            return
            
        returns_array = np.array(returns)
        
        # Calcola Value at Risk
        var_95 = np.percentile(returns_array, 5)
        var_99 = np.percentile(returns_array, 1)
        
        # Calcola Expected Shortfall
        es_95 = np.mean(returns_array[returns_array <= var_95])
        es_99 = np.mean(returns_array[returns_array <= var_99])
        
        # Calcola drawdown
        cumulative = np.cumprod(1 + returns_array)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = cumulative / running_max - 1
        max_dd = float(np.min(drawdowns))
        
        # Aggiorna metriche
        self.risk_metrics.update({
            'value_at_risk_95': float(var_95),
            'value_at_risk_99': float(var_99),
            'expected_shortfall_95': float(es_95),
            'expected_shortfall_99': float(es_99),
            'max_drawdown': max_dd,
            'volatility': float(np.std(returns_array)),
            'skewness': float(stats.skew(returns_array)),
            'kurtosis': float(stats.kurtosis(returns_array))
        })

class ChromosomeGene(Base):
    """Modello per i geni dei cromosomi."""
    __tablename__ = 'chromosome_genes'
    
    chromosome_gene_id = Column(Integer, primary_key=True)
    chromosome_id = Column(Integer, ForeignKey('chromosomes.chromosome_id', ondelete='CASCADE'), nullable=False)
    gene_type = Column(String(50), nullable=False)
    weight = Column(Float, nullable=False, default=1.0)
    is_active = Column(Boolean, default=True)
    performance_contribution = Column(Float, default=0.0)
    risk_factor = Column(Float, nullable=False, default=0.5)
    last_mutation_date = Column(DateTime(timezone=True))
    
    # Dati strutturati
    parameters = Column(JSON, nullable=False, default={})
    mutation_history = Column(JSON, default=[])
    validation_rules = Column(JSON, default={})
    optimization_history = Column(JSON, default=[])
    performance_metrics = Column(JSON, default={})
    
    # Relazioni
    chromosome = relationship(
        "Chromosome",
        back_populates="genes",
        lazy='joined'
    )
    
    # Vincoli e indici
    __table_args__ = (
        CheckConstraint('weight BETWEEN 0.1 AND 5.0'),
        CheckConstraint('risk_factor BETWEEN 0.1 AND 1.0'),
        Index('idx_gene_chromosome', 'chromosome_id'),
        Index('idx_gene_type', 'gene_type'),
        Index('idx_gene_active', 'is_active')
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Inizializza parametri di default se non forniti
        if self.gene_type in DEFAULT_GENE_CONFIGS and not self.parameters:
            self.parameters = DEFAULT_GENE_CONFIGS[self.gene_type].copy()
            self.risk_factor = self.parameters.pop('risk_factor', 0.5)
    
    def __repr__(self):
        return f"<ChromosomeGene(id={self.chromosome_gene_id}, type='{self.gene_type}', active={self.is_active})>"

    @classmethod
    def get_by_type(cls, chromosome_id: int, gene_type: str) -> Optional["ChromosomeGene"]:
        """Ottiene un gene specifico per tipo da un cromosoma."""
        with db.session() as session:
            return session.query(cls)\
                .filter_by(chromosome_id=chromosome_id, gene_type=gene_type)\
                .first()

    def validate_parameters(self) -> bool:
        """Valida i parametri del gene secondo le regole definite."""
        if not self.validation_rules or not self.parameters:
            return True
            
        for param, rules in self.validation_rules.items():
            if param not in self.parameters:
                continue
                
            value = self.parameters[param]
            
            # Controlla range
            if 'min' in rules and value < rules['min']:
                return False
            if 'max' in rules and value > rules['max']:
                return False
                
            # Controlla tipo
            if 'type' in rules:
                if rules['type'] == 'int' and not isinstance(value, int):
                    return False
                elif rules['type'] == 'float' and not isinstance(value, (int, float)):
                    return False
                    
            # Controlla dipendenze
            if 'depends_on' in rules:
                dep_param = rules['depends_on']
                if dep_param not in self.parameters:
                    return False
                dep_value = self.parameters[dep_param]
                
                if 'min_ratio' in rules and value < dep_value * rules['min_ratio']:
                    return False
                if 'max_ratio' in rules and value > dep_value * rules['max_ratio']:
                    return False
                    
        return True

    def optimize(self, performance_metric: float) -> None:
        """Ottimizza i parametri del gene."""
        optimizer = GeneOptimizer(self.gene_type, self.parameters)
        self.parameters = optimizer.optimize(performance_metric)
        self.optimization_history = optimizer.optimization_history

    def mutate(self) -> Optional[Dict[str, Any]]:
        """
        Applica una mutazione al gene.
        
        Returns:
            Dict con dettagli della mutazione o None se nessuna mutazione applicata
        """
        mutation_type = np.random.choice([
            'parameter',
            'weight',
            'activation',
            'risk'
        ])
        
        mutation_info = {
            'gene_type': self.gene_type,
            'mutation_type': mutation_type,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if mutation_type == 'parameter':
            # Seleziona parametro random
            if not self.parameters:
                return None
            param = np.random.choice(list(self.parameters.keys()))
            old_value = self.parameters[param]
            
            # Applica mutazione
            if isinstance(old_value, (int, float)):
                # Mutazione numerica
                mutation_scale = 0.1  # 10% variazione
                delta = old_value * mutation_scale * np.random.normal()
                new_value = old_value + delta
                
                # Applica vincoli se presenti
                rules = self.validation_rules.get(param, {})
                if 'min' in rules:
                    new_value = max(rules['min'], new_value)
                if 'max' in rules:
                    new_value = min(rules['max'], new_value)
                    
                # Converti a int se necessario
                if isinstance(old_value, int):
                    new_value = int(round(new_value))
                    
                self.parameters[param] = new_value
                
            elif isinstance(old_value, bool):
                # Inversione booleana
                self.parameters[param] = not old_value
                
            mutation_info.update({
                'parameter': param,
                'old_value': old_value,
                'new_value': self.parameters[param]
            })
            
        elif mutation_type == 'weight':
            # Muta peso
            old_weight = self.weight
            delta = 0.1 * np.random.normal()  # ±10% variazione
            new_weight = max(0.1, min(5.0, old_weight + delta))
            self.weight = new_weight
            
            mutation_info.update({
                'old_weight': old_weight,
                'new_weight': new_weight
            })
            
        elif mutation_type == 'risk':
            # Muta fattore di rischio
            old_risk = self.risk_factor
            delta = 0.05 * np.random.normal()  # ±5% variazione
            new_risk = max(0.1, min(1.0, old_risk + delta))
            self.risk_factor = new_risk
            
            mutation_info.update({
                'old_risk': old_risk,
                'new_risk': new_risk
            })
            
        else:  # activation
            # Inverte stato attivazione
            self.is_active = not self.is_active
            mutation_info['new_state'] = self.is_active
            
        # Aggiorna storia mutazioni
        self.mutation_history.append(mutation_info)
        self.last_mutation_date = datetime.utcnow()
        
        return mutation_info

class EvolutionHistory(Base):
    """Modello per la storia evolutiva delle popolazioni."""
    __tablename__ = 'evolution_history'
    
    history_id = Column(Integer, primary_key=True)
    population_id = Column(Integer, ForeignKey('populations.population_id', ondelete='CASCADE'), nullable=False)
    generation = Column(Integer, nullable=False)
    best_fitness = Column(Float, nullable=False, default=0.0)
    avg_fitness = Column(Float, nullable=False, default=0.0)
    diversity_metric = Column(Float, nullable=False, default=1.0)
    mutation_rate = Column(Float, nullable=False, default=0.01)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Dati strutturati
    generation_stats = Column(JSON, default={})
    mutation_stats = Column(JSON, default={})
    selection_stats = Column(JSON, default={})
    performance_breakdown = Column(JSON, default={})
    fitness_distribution = Column(JSON, default=[])
    population_metrics = Column(JSON, default={})
    
    # Relazioni
    population = relationship(
        "Population",
        back_populates="evolution_history",
        lazy='joined'
    )
    
    # Vincoli e indici
    __table_args__ = (
        Index('idx_history_population', 'population_id'),
        Index('idx_history_generation', 'generation')
    )
    
    def __repr__(self):
        return f"<EvolutionHistory(id={self.history_id}, population={self.population_id}, generation={self.generation})>"

    @classmethod
    def get_latest_history(cls, population_id: int, limit: int = 10) -> List["EvolutionHistory"]:
        """Ottiene la storia evolutiva più recente per una popolazione."""
        with db.session() as session:
            return session.query(cls)\
                .filter_by(population_id=population_id)\
                .order_by(cls.generation.desc())\
                .limit(limit)\
                .all()

    def calculate_metrics(self) -> None:
        """Calcola e aggiorna le metriche della generazione."""
        with db.session() as session:
            # Ottieni cromosomi attivi
            chromosomes = session.query(Chromosome)\
                .filter_by(
                    population_id=self.population_id,
                    generation=self.generation,
                    status='active'
                ).all()
            
            if not chromosomes:
                return
                
            # Calcola fitness
            fitness_values = [c.calculate_fitness() for c in chromosomes]
            self.fitness_distribution = fitness_values
            
            # Statistiche fitness
            self.best_fitness = max(fitness_values)
            self.avg_fitness = sum(fitness_values) / len(fitness_values)
            
            # Calcola diversità
            gene_types = set()
            for c in chromosomes:
                for g in c.genes:
                    gene_types.add(g.gene_type)
                    
            total_possible = len(chromosomes) * len(gene_types)
            active_genes = sum(1 for c in chromosomes 
                             for g in c.genes if g.is_active)
            
            self.diversity_metric = active_genes / total_possible if total_possible > 0 else 0
            
            # Statistiche mutazioni
            mutations = []
            for c in chromosomes:
                if c.mutation_stats and 'mutations' in c.mutation_stats:
                    mutations.extend(c.mutation_stats['mutations'])
            
            if mutations:
                mutation_types = {}
                for m in mutations:
                    m_type = m['mutation_type']
                    mutation_types[m_type] = mutation_types.get(m_type, 0) + 1
                    
                self.mutation_stats = {
                    'total_mutations': len(mutations),
                    'mutation_types': mutation_types
                }
            
            # Metriche popolazione
            self.population_metrics.update({
                'total_chromosomes': len(chromosomes),
                'fitness_std': float(np.std(fitness_values)),
                'fitness_median': float(np.median(fitness_values)),
                'fitness_quartiles': [
                    float(np.percentile(fitness_values, 25)),
                    float(np.percentile(fitness_values, 50)),
                    float(np.percentile(fitness_values, 75))
                ]
            })
