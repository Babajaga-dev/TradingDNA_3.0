"""
Market Patterns Model
-------------------
Modello SQLAlchemy per i pattern di mercato.
Include pattern candlestick e pattern tecnici.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, Integer, Float, String, DateTime, 
    ForeignKey, Index, UniqueConstraint, Boolean,
    JSON
)
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class PatternDefinition(Base):
    """Definizione dei pattern di mercato."""
    
    __tablename__ = 'pattern_definitions'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    type = Column(String(20), nullable=False)  # candlestick, chart, indicator
    description = Column(String)
    timeframes = Column(String)  # comma-separated list of valid timeframes
    min_candles = Column(Integer, nullable=False)
    max_candles = Column(Integer, nullable=False)
    
    # Parametri di configurazione
    parameters = Column(JSON)
    validation_rules = Column(JSON)
    
    # Metadati
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relazioni
    instances = relationship("PatternInstance", back_populates="definition")
    
    # Indici
    __table_args__ = (
        Index('idx_pattern_lookup', 'type', 'is_active'),
    )

class PatternInstance(Base):
    """Istanza di un pattern identificato."""
    
    __tablename__ = 'pattern_instances'
    
    id = Column(Integer, primary_key=True)
    definition_id = Column(Integer, ForeignKey('pattern_definitions.id'), nullable=False)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    symbol_id = Column(Integer, ForeignKey('symbols.id'), nullable=False)
    timeframe = Column(String(10), nullable=False)
    
    # Intervallo temporale del pattern
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    
    # Metriche del pattern
    strength = Column(Float)  # 0-1, forza del pattern
    reliability = Column(Float)  # 0-1, affidabilità storica
    risk_reward = Column(Float)  # rapporto rischio/rendimento
    
    # Livelli chiave
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    
    # Risultati
    outcome = Column(String(20))  # success, failure, pending
    profit_loss = Column(Float)
    max_adverse_excursion = Column(Float)
    max_favorable_excursion = Column(Float)
    
    # Metadati pattern
    parameters = Column(JSON)
    validation_score = Column(Float)
    notes = Column(String)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relazioni
    definition = relationship("PatternDefinition", back_populates="instances")
    candles = relationship("PatternCandle", back_populates="pattern")
    
    # Indici
    __table_args__ = (
        Index(
            'idx_pattern_instance_lookup',
            'definition_id', 'exchange_id', 'symbol_id',
            'timeframe', 'start_time', 'end_time'
        ),
        Index('idx_pattern_outcome', 'outcome'),
    )
    
    @property
    def duration(self) -> float:
        """Calcola la durata del pattern in minuti."""
        return (self.end_time - self.start_time).total_seconds() / 60
    
    @property
    def risk_amount(self) -> float:
        """Calcola l'importo a rischio."""
        return abs(self.entry_price - self.stop_loss)
    
    @property
    def reward_amount(self) -> float:
        """Calcola il potenziale profitto."""
        return abs(self.take_profit - self.entry_price)
    
    @property
    def is_completed(self) -> bool:
        """Verifica se il pattern è completato."""
        return self.outcome in ['success', 'failure']
    
    def validate(self) -> Dict[str, Any]:
        """
        Valida il pattern secondo le regole definite.
        
        Returns:
            Dict con risultati validazione
        """
        results = {
            'is_valid': True,
            'score': 0.0,
            'checks': []
        }
        
        if not self.definition.validation_rules:
            return results
            
        for rule in self.definition.validation_rules:
            check = {
                'rule': rule['name'],
                'passed': False,
                'score': 0.0,
                'details': None
            }
            
            # Implementa logica di validazione specifica
            # per ogni tipo di regola
            
            results['checks'].append(check)
            
        # Calcola score complessivo
        if results['checks']:
            results['score'] = sum(
                c['score'] for c in results['checks']
            ) / len(results['checks'])
            
        results['is_valid'] = results['score'] >= 0.7
        return results

class PatternCandle(Base):
    """Candele associate a un pattern."""
    
    __tablename__ = 'pattern_candles'
    
    id = Column(Integer, primary_key=True)
    pattern_id = Column(
        Integer,
        ForeignKey('pattern_instances.id'),
        nullable=False
    )
    market_data_id = Column(
        Integer,
        ForeignKey('market_data.id'),
        nullable=False
    )
    position = Column(Integer, nullable=False)  # posizione nel pattern
    role = Column(String(20))  # ruolo della candela nel pattern
    
    # Relazioni
    pattern = relationship("PatternInstance", back_populates="candles")
    market_data = relationship("MarketData")
    
    # Indici
    __table_args__ = (
        UniqueConstraint(
            'pattern_id', 'market_data_id',
            name='uix_pattern_candle'
        ),
    )

# Pattern predefiniti
CANDLESTICK_PATTERNS = {
    'doji': {
        'type': 'candlestick',
        'min_candles': 1,
        'max_candles': 1,
        'timeframes': '1h,4h,1d',
        'parameters': {
            'body_size_threshold': 0.1,
            'shadow_ratio_threshold': 0.1
        },
        'validation_rules': [
            {
                'name': 'body_size',
                'type': 'threshold',
                'value': 0.1,
                'weight': 0.6
            },
            {
                'name': 'shadow_ratio',
                'type': 'ratio',
                'value': 0.1,
                'weight': 0.4
            }
        ]
    },
    'hammer': {
        'type': 'candlestick',
        'min_candles': 1,
        'max_candles': 1,
        'timeframes': '1h,4h,1d',
        'parameters': {
            'body_size_threshold': 0.3,
            'lower_shadow_ratio': 2.0
        },
        'validation_rules': [
            {
                'name': 'body_position',
                'type': 'position',
                'value': 'top',
                'weight': 0.4
            },
            {
                'name': 'lower_shadow',
                'type': 'ratio',
                'value': 2.0,
                'weight': 0.6
            }
        ]
    },
    'engulfing': {
        'type': 'candlestick',
        'min_candles': 2,
        'max_candles': 2,
        'timeframes': '1h,4h,1d',
        'parameters': {
            'body_size_ratio': 1.5
        },
        'validation_rules': [
            {
                'name': 'opposite_colors',
                'type': 'boolean',
                'weight': 0.3
            },
            {
                'name': 'body_size_ratio',
                'type': 'ratio',
                'value': 1.5,
                'weight': 0.7
            }
        ]
    }
}

# Pattern tecnici
CHART_PATTERNS = {
    'double_bottom': {
        'type': 'chart',
        'min_candles': 20,
        'max_candles': 50,
        'timeframes': '4h,1d',
        'parameters': {
            'bottom_threshold': 0.02,
            'height_threshold': 0.1
        },
        'validation_rules': [
            {
                'name': 'bottom_alignment',
                'type': 'threshold',
                'value': 0.02,
                'weight': 0.4
            },
            {
                'name': 'height_ratio',
                'type': 'ratio',
                'value': 0.1,
                'weight': 0.3
            },
            {
                'name': 'volume_confirmation',
                'type': 'volume',
                'weight': 0.3
            }
        ]
    },
    'head_and_shoulders': {
        'type': 'chart',
        'min_candles': 30,
        'max_candles': 60,
        'timeframes': '4h,1d',
        'parameters': {
            'shoulder_alignment': 0.05,
            'head_height_ratio': 1.2
        },
        'validation_rules': [
            {
                'name': 'shoulder_alignment',
                'type': 'threshold',
                'value': 0.05,
                'weight': 0.3
            },
            {
                'name': 'head_height',
                'type': 'ratio',
                'value': 1.2,
                'weight': 0.4
            },
            {
                'name': 'neckline',
                'type': 'trend',
                'weight': 0.3
            }
        ]
    }
}