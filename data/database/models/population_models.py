"""
Population Models
---------------
Modelli SQLAlchemy per la gestione delle popolazioni di trading.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, 
    DateTime, ForeignKey, JSON, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import Base
from cli.logger.log_manager import get_logger

# Setup logger
logger = get_logger('population_models')

class Population(Base):
    """Modello per le popolazioni di trading."""
    __tablename__ = 'populations'
    
    population_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    max_size = Column(Integer, nullable=False)
    current_generation = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    status = Column(String(20), default='active')
    diversity_score = Column(Float, default=1.0)
    performance_score = Column(Float, default=0.0)
    
    # Parametri evolutivi
    mutation_rate = Column(Float, default=0.01)
    selection_pressure = Column(Integer, default=5)
    generation_interval = Column(Integer, default=4)
    diversity_threshold = Column(Float, default=0.7)
    
    # Configurazione trading
    symbol_id = Column(Integer, ForeignKey('symbols.id'), nullable=False)
    timeframe = Column(String(10), nullable=False)
    
    # Relazioni
    symbol = relationship("Symbol", backref="populations")
    chromosomes = relationship("Chromosome", back_populates="population")
    evolution_history = relationship("EvolutionHistory", back_populates="population")
    
    # Vincoli
    __table_args__ = (
        CheckConstraint('max_size BETWEEN 50 AND 500'),
        CheckConstraint('mutation_rate BETWEEN 0.001 AND 0.05'),
        CheckConstraint('selection_pressure BETWEEN 1 AND 10'),
        CheckConstraint('generation_interval BETWEEN 1 AND 24'),
        CheckConstraint('diversity_threshold BETWEEN 0.5 AND 1.0'),
        CheckConstraint("status IN ('active', 'paused', 'archived')"),
    )
    
    def __repr__(self):
        return f"<Population(id={self.population_id}, name='{self.name}', generation={self.current_generation})>"

class Chromosome(Base):
    """Modello per i cromosomi delle strategie."""
    __tablename__ = 'chromosomes'
    
    chromosome_id = Column(Integer, primary_key=True)
    population_id = Column(Integer, ForeignKey('populations.population_id'), nullable=False)
    fingerprint = Column(String(64), nullable=False)
    generation = Column(Integer, nullable=False)
    age = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    parent1_id = Column(Integer, ForeignKey('chromosomes.chromosome_id'))
    parent2_id = Column(Integer, ForeignKey('chromosomes.chromosome_id'))
    status = Column(String(20), default='active')
    performance_metrics = Column(JSON)
    weight_distribution = Column(JSON)
    last_test_date = Column(DateTime)
    test_results = Column(JSON)
    
    # Relazioni
    population = relationship("Population", back_populates="chromosomes")
    genes = relationship("ChromosomeGene", back_populates="chromosome")
    parent1 = relationship("Chromosome", remote_side=[chromosome_id], foreign_keys=[parent1_id])
    parent2 = relationship("Chromosome", remote_side=[chromosome_id], foreign_keys=[parent2_id])
    
    # Vincoli
    __table_args__ = (
        CheckConstraint("status IN ('active', 'testing', 'archived')"),
    )
    
    def __repr__(self):
        return f"<Chromosome(id={self.chromosome_id}, population={self.population_id}, generation={self.generation})>"

class ChromosomeGene(Base):
    """Modello per i geni dei cromosomi."""
    __tablename__ = 'chromosome_genes'
    
    chromosome_gene_id = Column(Integer, primary_key=True)
    chromosome_id = Column(Integer, ForeignKey('chromosomes.chromosome_id'), nullable=False)
    gene_type = Column(String(50), nullable=False)
    parameters = Column(JSON, nullable=False)
    weight = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    performance_contribution = Column(Float, default=0.0)
    last_mutation_date = Column(DateTime)
    mutation_history = Column(JSON)
    validation_rules = Column(JSON)
    
    # Relazioni
    chromosome = relationship("Chromosome", back_populates="genes")
    
    # Vincoli
    __table_args__ = (
        CheckConstraint('weight BETWEEN 0.0 AND 1.0'),
    )
    
    def __repr__(self):
        return f"<ChromosomeGene(id={self.chromosome_gene_id}, type='{self.gene_type}', active={self.is_active})>"

class EvolutionHistory(Base):
    """Modello per la storia evolutiva delle popolazioni."""
    __tablename__ = 'evolution_history'
    
    history_id = Column(Integer, primary_key=True)
    population_id = Column(Integer, ForeignKey('populations.population_id'), nullable=False)
    generation = Column(Integer, nullable=False)
    best_fitness = Column(Float, nullable=False)
    avg_fitness = Column(Float, nullable=False)
    diversity_metric = Column(Float, nullable=False)
    mutation_rate = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=func.now())
    generation_stats = Column(JSON)
    mutation_stats = Column(JSON)
    selection_stats = Column(JSON)
    performance_breakdown = Column(JSON)
    
    # Relazioni
    population = relationship("Population", back_populates="evolution_history")
    
    def __repr__(self):
        return f"<EvolutionHistory(id={self.history_id}, population={self.population_id}, generation={self.generation})>"
