"""
Market Data Model
----------------
Modello SQLAlchemy per i dati di mercato.
Include OHLCV data e indicatori tecnici.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, Float, String, DateTime, Boolean,
    ForeignKey, Index, UniqueConstraint, select
)
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Exchange(Base):
    """Modello per gli exchange."""
    
    __tablename__ = 'exchanges'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relazioni
    symbols = relationship("Symbol", back_populates="exchange")
    market_data = relationship("MarketData", back_populates="exchange")

class Symbol(Base):
    """Modello per i simboli di trading."""
    
    __tablename__ = 'symbols'
    
    id = Column(Integer, primary_key=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    name = Column(String(20), nullable=False)
    base_asset = Column(String(10), nullable=False)
    quote_asset = Column(String(10), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relazioni
    exchange = relationship("Exchange", back_populates="symbols")
    market_data = relationship("MarketData", back_populates="symbol")
    
    # Indici e vincoli
    __table_args__ = (
        UniqueConstraint('exchange_id', 'name', name='uix_exchange_symbol'),
        Index('idx_symbol_lookup', 'exchange_id', 'name', 'is_active')
    )

class MarketData(Base):
    """Modello per i dati di mercato OHLCV."""
    
    __tablename__ = 'market_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    symbol_id = Column(Integer, ForeignKey('symbols.id'), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    timeframe = Column(String(10), nullable=False)  # 1m, 5m, 15m, 1h, 4h, 1d
    
    # Dati OHLCV
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    
    # Indicatori tecnici di base
    sma_20 = Column(Float)
    ema_50 = Column(Float)
    rsi_14 = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_hist = Column(Float)
    bb_upper = Column(Float)
    bb_middle = Column(Float)
    bb_lower = Column(Float)
    
    # Metriche di mercato
    volatility = Column(Float)
    trend_strength = Column(Float)
    volume_ma_20 = Column(Float)
    
    # Metadati
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_valid = Column(Boolean, default=True)
    validation_errors = Column(String)
    
    # Relazioni
    exchange = relationship("Exchange", back_populates="market_data")
    symbol = relationship("Symbol", back_populates="market_data")
    
    # Indici per ottimizzazione query
    __table_args__ = (
        # Indice principale per ricerche temporali
        Index(
            'idx_market_lookup',
            'exchange_id', 'symbol_id', 'timeframe',
            'timestamp', 'is_valid'
        ),
        # Indice per analisi temporali
        Index('idx_timestamp', 'timestamp'),
        # Indice per validazione dati
        Index('idx_validation', 'is_valid'),
        # Vincolo di unicità per evitare duplicati
        UniqueConstraint(
            'exchange_id', 'symbol_id', 'timeframe',
            'timestamp',
            name='uix_market_data'
        )
    )

    @classmethod
    async def insert_and_get_id(cls, session, **kwargs):
        """Inserisce un nuovo record e restituisce l'ID."""
        instance = cls(**kwargs)
        session.add(instance)
        await session.flush()  # Forza il flush per ottenere l'ID
        await session.refresh(instance)  # Ricarica l'istanza per assicurarsi di avere l'ID
        return instance.id
    
    @property
    def tr(self) -> float:
        """Calcola il True Range."""
        return max(
            self.high - self.low,
            abs(self.high - self.close),
            abs(self.low - self.close)
        )
    
    @property
    def body_size(self) -> float:
        """Calcola la dimensione del corpo della candela."""
        return abs(self.close - self.open)
    
    @property
    def upper_shadow(self) -> float:
        """Calcola l'ombra superiore della candela."""
        return self.high - max(self.open, self.close)
    
    @property
    def lower_shadow(self) -> float:
        """Calcola l'ombra inferiore della candela."""
        return min(self.open, self.close) - self.low
    
    @property
    def is_bullish(self) -> bool:
        """Verifica se la candela è rialzista."""
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        """Verifica se la candela è ribassista."""
        return self.close < self.open
    
    @property
    def is_doji(self) -> bool:
        """Verifica se la candela è un doji."""
        return abs(self.close - self.open) <= 0.1 * (self.high - self.low)

class DataValidation(Base):
    """Modello per la validazione dei dati."""
    
    __tablename__ = 'data_validations'
    
    id = Column(Integer, primary_key=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    symbol_id = Column(Integer, ForeignKey('symbols.id'), nullable=False)
    timeframe = Column(String(10), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    
    # Metriche di validazione
    total_candles = Column(Integer, nullable=False)
    missing_candles = Column(Integer, default=0)
    invalid_candles = Column(Integer, default=0)
    gaps_detected = Column(Integer, default=0)
    anomalies_detected = Column(Integer, default=0)
    
    # Dettagli validazione
    validation_details = Column(String)
    is_valid = Column(Boolean, default=True)
    
    # Metadati
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indici
    __table_args__ = (
        Index(
            'idx_validation_lookup',
            'exchange_id', 'symbol_id', 'timeframe',
            'start_time', 'end_time'
        ),
    )
