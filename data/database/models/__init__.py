"""
TradingDNA Data System - Database Models
-------------------------------------
Modelli SQLAlchemy per il sistema di dati.
"""

from typing import List, Dict, Any, AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager

from .market_data import (
    Exchange,
    Symbol,
    MarketData,
    DataValidation
)

from .patterns import (
    PatternDefinition,
    PatternInstance,
    PatternCandle,
    CANDLESTICK_PATTERNS,
    CHART_PATTERNS
)

from .metrics import (
    PerformanceMetrics,
    RiskMetrics,
    MarketRegime
)

__all__ = [
    # Market Data
    'Exchange',
    'Symbol',
    'MarketData',
    'DataValidation',
    
    # Patterns
    'PatternDefinition',
    'PatternInstance',
    'PatternCandle',
    'CANDLESTICK_PATTERNS',
    'CHART_PATTERNS',
    
    # Metrics
    'PerformanceMetrics',
    'RiskMetrics',
    'MarketRegime',
    
    # Factory functions
    'create_tables',
    'drop_tables',
    'get_session'
]

# Configurazione database
DATABASE_URL = "sqlite+aiosqlite:///data/tradingdna.db"
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager per ottenere una sessione asincrona.
    
    Yields:
        Sessione SQLAlchemy asincrona
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

def create_tables(engine: Any) -> None:
    """
    Crea tutte le tabelle nel database.
    
    Args:
        engine: SQLAlchemy engine
    """
    # Market Data
    Exchange.metadata.create_all(engine)
    Symbol.metadata.create_all(engine)
    MarketData.metadata.create_all(engine)
    DataValidation.metadata.create_all(engine)
    
    # Patterns
    PatternDefinition.metadata.create_all(engine)
    PatternInstance.metadata.create_all(engine)
    PatternCandle.metadata.create_all(engine)
    
    # Metrics
    PerformanceMetrics.metadata.create_all(engine)
    RiskMetrics.metadata.create_all(engine)
    MarketRegime.metadata.create_all(engine)

def drop_tables(engine: Any) -> None:
    """
    Elimina tutte le tabelle dal database.
    
    Args:
        engine: SQLAlchemy engine
    """
    # Metrics
    MarketRegime.metadata.drop_all(engine)
    RiskMetrics.metadata.drop_all(engine)
    PerformanceMetrics.metadata.drop_all(engine)
    
    # Patterns
    PatternCandle.metadata.drop_all(engine)
    PatternInstance.metadata.drop_all(engine)
    PatternDefinition.metadata.drop_all(engine)
    
    # Market Data
    DataValidation.metadata.drop_all(engine)
    MarketData.metadata.drop_all(engine)
    Symbol.metadata.drop_all(engine)
    Exchange.metadata.drop_all(engine)