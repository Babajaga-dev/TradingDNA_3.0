"""
Population Models
---------------
Modelli SQLAlchemy per la gestione delle popolazioni di trading.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, 
    DateTime, ForeignKey, JSON, CheckConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from . import Base

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
    symbol_id = Column(Integer, ForeignKey('symbols.id', ondelete='CASCADE'), nullable=False)
    timeframe = Column(String(10), nullable=False)
    
    # Relazioni
    symbol = relationship("Symbol", backref="populations", lazy='joined')
    chromosomes = relationship(
        "Chromosome",
        back_populates="population",
        cascade="all, delete-orphan",
        lazy='selectin'  # Eager loading per performance
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
    
    def __repr__(self):
        return f"<Population(id={self.population_id}, name='{self.name}', generation={self.current_generation})>"

class Chromosome(Base):
    """Modello per i cromosomi delle strategie."""
    __tablename__ = 'chromosomes'
    
    chromosome_id = Column(Integer, primary_key=True)
    population_id = Column(Integer, ForeignKey('populations.population_id', ondelete='CASCADE'), nullable=False)
    fingerprint = Column(String(64), nullable=False)
    generation = Column(Integer, nullable=False)
    age = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    parent1_id = Column(Integer, ForeignKey('chromosomes.chromosome_id', ondelete='SET NULL'))
    parent2_id = Column(Integer, ForeignKey('chromosomes.chromosome_id', ondelete='SET NULL'))
    status = Column(String(20), default='active')
    performance_metrics = Column(JSONB)
    weight_distribution = Column(JSONB)
    last_test_date = Column(DateTime)
    test_results = Column(JSONB)
    
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

class ChromosomeGene(Base):
    """Modello per i geni dei cromosomi."""
    __tablename__ = 'chromosome_genes'
    
    chromosome_gene_id = Column(Integer, primary_key=True)
    chromosome_id = Column(Integer, ForeignKey('chromosomes.chromosome_id', ondelete='CASCADE'), nullable=False)
    gene_type = Column(String(50), nullable=False)
    parameters = Column(JSONB, nullable=False)
    weight = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    performance_contribution = Column(Float, default=0.0)
    last_mutation_date = Column(DateTime)
    mutation_history = Column(JSONB)
    validation_rules = Column(JSONB)
    
    # Relazioni
    chromosome = relationship(
        "Chromosome",
        back_populates="genes",
        lazy='joined'
    )
    
    # Vincoli e indici
    __table_args__ = (
        CheckConstraint('weight BETWEEN 0.1 AND 5.0'),
        Index('idx_gene_chromosome', 'chromosome_id'),
        Index('idx_gene_type', 'gene_type'),
        Index('idx_gene_active', 'is_active')
    )
    
    def __repr__(self):
        return f"<ChromosomeGene(id={self.chromosome_gene_id}, type='{self.gene_type}', active={self.is_active})>"

class EvolutionHistory(Base):
    """Modello per la storia evolutiva delle popolazioni."""
    __tablename__ = 'evolution_history'
    
    history_id = Column(Integer, primary_key=True)
    population_id = Column(Integer, ForeignKey('populations.population_id', ondelete='CASCADE'), nullable=False)
    generation = Column(Integer, nullable=False)
    best_fitness = Column(Float, nullable=False)
    avg_fitness = Column(Float, nullable=False)
    diversity_metric = Column(Float, nullable=False)
    mutation_rate = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=func.now())
    generation_stats = Column(JSONB)
    mutation_stats = Column(JSONB)
    selection_stats = Column(JSONB)
    performance_breakdown = Column(JSONB)
    
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
