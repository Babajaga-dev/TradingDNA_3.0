"""
TradingDNA Data System - Database Models
-------------------------------------
Modelli SQLAlchemy per il sistema di dati.
"""

from typing import List, Dict, Any, AsyncGenerator
import sqlite3
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
import os

from .market_data import (
    Exchange,
    Symbol,
    MarketData,
    DataValidation,
    Base
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
    'get_session',
    'initialize_database'
]

# Configurazione database
DATABASE_URL = "sqlite+aiosqlite:///data/tradingdna.db"
SYNC_DATABASE_URL = "sqlite:///data/tradingdna.db"

def configure_sqlite_connection(dbapi_connection, connection_record):
    """Configura le connessioni SQLite per prestazioni e concorrenza ottimali."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        # Abilita il supporto alle foreign key
        dbapi_connection.execute('PRAGMA foreign_keys = ON')
        # Configura il timeout per i lock
        dbapi_connection.execute('PRAGMA busy_timeout = 30000')  # 30 secondi
        # Usa il journaling WAL per migliore concorrenza
        dbapi_connection.execute('PRAGMA journal_mode = WAL')
        # Sincronizzazione normale per bilanciare sicurezza e performance
        dbapi_connection.execute('PRAGMA synchronous = NORMAL')
        # Cache più grande per migliori performance
        dbapi_connection.execute('PRAGMA cache_size = -64000')  # 64MB
        # Ottimizzazione delle query
        dbapi_connection.execute('PRAGMA temp_store = MEMORY')
        dbapi_connection.execute('PRAGMA mmap_size = 64000000')  # 64MB

# Crea engine asincrono con configurazione ottimizzata
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={'timeout': 30}  # 30 secondi timeout
)

# Configura l'engine sincrono
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=False,
    connect_args={'timeout': 30}
)

# Applica la configurazione SQLite a tutte le connessioni
event.listen(sync_engine, 'connect', configure_sqlite_connection)

# Crea session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

def execute_migration(db_path: str, migration_file: str) -> None:
    """
    Esegue uno script di migrazione SQL.
    
    Args:
        db_path: Percorso del database SQLite
        migration_file: Percorso del file di migrazione
    """
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    conn = sqlite3.connect(db_path, timeout=30)
    try:
        # Configura la connessione
        configure_sqlite_connection(conn, None)
        conn.executescript(migration_sql)
        conn.commit()
    finally:
        conn.close()

def initialize_database() -> None:
    """
    Inizializza il database creando tutte le tabelle necessarie
    ed eseguendo le migrazioni SQL.
    """
    # Crea il database e le tabelle usando SQLAlchemy
    Base.metadata.create_all(sync_engine)
    
    # Esegui le migrazioni SQL
    db_path = "data/tradingdna.db"
    migrations_dir = "data/database/migrations"
    
    # Assicurati che la directory del database esista
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Esegui tutte le migrazioni nella directory in ordine alfabetico
    migrations = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
    for migration_file in migrations:
        migration_path = os.path.join(migrations_dir, migration_file)
        execute_migration(db_path, migration_path)

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager per ottenere una sessione asincrona.
    
    Yields:
        Sessione SQLAlchemy asincrona
    """
    session = async_session_factory()
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
    Base.metadata.create_all(engine)

def drop_tables(engine: Any) -> None:
    """
    Elimina tutte le tabelle dal database.
    
    Args:
        engine: SQLAlchemy engine
    """
    Base.metadata.drop_all(engine)
