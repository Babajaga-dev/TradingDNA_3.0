"""
Database Models
--------------
Definizione dei modelli del database per il framework TradingDNA.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import numpy as np
from scipy import stats
import yaml
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, 
    ForeignKey, JSON, Text, Enum, UniqueConstraint, Index,
    text, inspect
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

from data.database.session_manager import DBSessionManager

# Carica configurazione database
with open('config/security.yaml', 'r') as f:
    config = yaml.safe_load(f)
    DATABASE_URL = config['database']['url']

# Base class per i modelli
Base = declarative_base()

# Ottieni l'istanza del session manager
db = DBSessionManager()

class Exchange(Base):
    """Modello per gli exchange supportati."""
    __tablename__ = 'exchanges'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Configurazione
    api_config = Column(JSON, default={})
    rate_limits = Column(JSON, default={})
    supported_features = Column(JSON, default=[])
    
    # Relazioni
    symbols = relationship("Symbol", back_populates="exchange", cascade="all, delete-orphan", lazy='selectin')
    market_data = relationship("MarketData", back_populates="exchange", cascade="all, delete-orphan", lazy='selectin')

    # Indici
    __table_args__ = (
        Index('idx_exchange_lookup', 'name', 'is_active'),
    )

class Symbol(Base):
    """Modello per i simboli/coppie di trading."""
    __tablename__ = 'symbols'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    base_asset = Column(String(20), nullable=False)
    quote_asset = Column(String(20), nullable=False)
    exchange_id = Column(Integer, ForeignKey('exchanges.id', ondelete='CASCADE'), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Configurazione
    trading_config = Column(JSON, default={})
    filters = Column(JSON, default={})
    limits = Column(JSON, default={})
    
    # Relazioni
    exchange = relationship("Exchange", back_populates="symbols", lazy='joined')
    market_data = relationship("MarketData", back_populates="symbol", cascade="all, delete-orphan", lazy='selectin')
    
    # Indici e vincoli
    __table_args__ = (
        UniqueConstraint('name', 'exchange_id', name='uix_symbol_exchange'),
        Index('idx_symbol_lookup', 'exchange_id', 'name', 'is_active'),
        Index('idx_symbol_assets', 'base_asset', 'quote_asset')
    )

class MarketData(Base):
    """Modello per i dati di mercato OHLCV e indicatori tecnici."""
    __tablename__ = 'market_data'
    
    id = Column(Integer, primary_key=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id', ondelete='CASCADE'), nullable=False)
    symbol_id = Column(Integer, ForeignKey('symbols.id', ondelete='CASCADE'), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    timeframe = Column(String(10), nullable=False)  # 1m, 5m, 15m, 1h, 4h, 1d
    
    # Dati OHLCV
    open = Column(Float(precision=10, decimal_return_scale=True), nullable=False)
    high = Column(Float(precision=10, decimal_return_scale=True), nullable=False)
    low = Column(Float(precision=10, decimal_return_scale=True), nullable=False)
    close = Column(Float(precision=10, decimal_return_scale=True), nullable=False)
    volume = Column(Float(precision=10, decimal_return_scale=True), nullable=False)
    
    # Indicatori tecnici
    sma_20 = Column(Float(precision=10, decimal_return_scale=True))
    ema_50 = Column(Float(precision=10, decimal_return_scale=True))
    rsi_14 = Column(Float(precision=10, decimal_return_scale=True))
    macd = Column(Float(precision=10, decimal_return_scale=True))
    macd_signal = Column(Float(precision=10, decimal_return_scale=True))
    macd_hist = Column(Float(precision=10, decimal_return_scale=True))
    bb_upper = Column(Float(precision=10, decimal_return_scale=True))
    bb_middle = Column(Float(precision=10, decimal_return_scale=True))
    bb_lower = Column(Float(precision=10, decimal_return_scale=True))
    
    # Metriche di mercato
    volatility = Column(Float(precision=10, decimal_return_scale=True))
    trend_strength = Column(Float(precision=10, decimal_return_scale=True))
    volume_ma_20 = Column(Float(precision=10, decimal_return_scale=True))
    
    # Dati strutturati
    technical_indicators = Column(JSON, default={})
    pattern_recognition = Column(JSON, default={})
    market_metrics = Column(JSON, default={})
    
    # Metadati
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_valid = Column(Boolean, default=True)
    validation_errors = Column(JSON, default=[])
    
    # Relazioni
    exchange = relationship("Exchange", back_populates="market_data", lazy='joined')
    symbol = relationship("Symbol", back_populates="market_data", lazy='joined')
    
    # Indici e vincoli
    __table_args__ = (
        UniqueConstraint('exchange_id', 'symbol_id', 'timeframe', 'timestamp', name='uix_market_data'),
        Index('idx_market_lookup', 'exchange_id', 'symbol_id', 'timeframe', 'timestamp', 'is_valid'),
        Index('idx_market_timestamp', 'timestamp'),
        Index('idx_market_validation', 'is_valid')
    )
    
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

class GeneParameter(Base):
    """Modello per i parametri dei geni."""
    __tablename__ = 'gene_parameters'
    
    id = Column(Integer, primary_key=True)
    gene_type = Column(String(50), nullable=False)
    parameter_name = Column(String(50), nullable=False)
    value = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Configurazione
    validation_rules = Column(JSON, default={})
    optimization_bounds = Column(JSON, default={})
    dependencies = Column(JSON, default=[])
    
    # Vincoli e indici
    __table_args__ = (
        UniqueConstraint('gene_type', 'parameter_name', name='uix_gene_parameter'),
        Index('idx_gene_lookup', 'gene_type', 'parameter_name')
    )

def verify_database_state() -> bool:
    """
    Verifica lo stato del database dopo un reset o inizializzazione.
    
    Returns:
        bool: True se il database è in uno stato valido, False altrimenti
    """
    try:
        with db.session() as session:
            # Verifica che tutte le tabelle esistano
            inspector = inspect(db.engine)
            required_tables = {
                'exchanges', 'symbols', 'market_data', 'gene_parameters'
            }
            existing_tables = set(inspector.get_table_names())
            
            if not required_tables.issubset(existing_tables):
                missing = required_tables - existing_tables
                print(f"Tabelle mancanti: {missing}")
                return False
            
            # Verifica che i vincoli siano attivi
            for table in required_tables:
                constraints = inspector.get_foreign_keys(table)
                pk = inspector.get_pk_constraint(table)
                if not pk:
                    print(f"Chiave primaria mancante in {table}")
                    return False
            
            #print("Stato del database verificato con successo")
            return True
            
    except Exception as e:
        print(f"Errore durante la verifica del database: {str(e)}")
        return False

def reset_database() -> None:
    """Resetta il database eliminando e ricreando tutte le tabelle."""
    try:
        print("Inizio reset database...")
        
        # Usa una connessione diretta per eseguire DROP CASCADE
        with db.engine.connect() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
            conn.commit()
            
        print("Schema eliminato e ricreato con successo")
        
        # Ricrea le tabelle
        Base.metadata.create_all(db.engine)
        print("Tabelle ricreate con successo")
        
        # Verifica lo stato dopo il reset
        if not verify_database_state():
            raise Exception("Verifica stato database fallita dopo il reset")
            
        print("Database resettato e verificato con successo")
        
    except Exception as e:
        print(f"Errore durante il reset del database: {str(e)}")
        raise

def initialize_database() -> None:
    """Inizializza il database creando tutte le tabelle."""
    try:
        Base.metadata.create_all(db.engine)
        
        # Verifica lo stato dopo l'inizializzazione
        if not verify_database_state():
            raise Exception("Verifica stato database fallita dopo l'inizializzazione")
            
        print("Database inizializzato e verificato con successo")
        
    except Exception as e:
        print(f"Errore durante l'inizializzazione del database: {str(e)}")
        raise

def check_gene_parameters_exist() -> bool:
    """Verifica se esistono parametri dei geni nel database."""
    with db.session() as session:
        gene_types = ['rsi', 'moving_average', 'macd', 'bollinger', 'stochastic', 'atr']
        return all(
            session.query(GeneParameter).filter_by(gene_type=gene_type).first() is not None
            for gene_type in gene_types
        )

def initialize_gene_parameters(config: Dict[str, Any]) -> None:
    """Inizializza i parametri dei geni nel database."""
    try:
        with open('config/gene.yaml', 'r') as f:
            gene_config = yaml.safe_load(f).get('gene', {})
        
        with db.session() as session:
            # Elimina tutti i parametri esistenti
            session.query(GeneParameter).delete()
            
            for gene_type, gene_data in gene_config.items():
                if gene_type == 'base':
                    continue
                    
                default_params = gene_data.get('default', {})
                if not default_params:
                    continue
                    
                for param_name, value in default_params.items():
                    param = GeneParameter(
                        gene_type=gene_type,
                        parameter_name=param_name,
                        value=str(value),
                        validation_rules=gene_data.get('validation', {}),
                        optimization_bounds=gene_data.get('optimization_bounds', {}),
                        dependencies=gene_data.get('dependencies', [])
                    )
                    session.add(param)
                    
            session.commit()
            print("Parametri dei geni inizializzati con successo")
            
    except Exception as e:
        print(f"Errore durante l'inizializzazione dei parametri dei geni: {str(e)}")
        raise

def update_gene_parameter(gene_type: str, parameter_name: str, value: Any) -> None:
    """Aggiorna un parametro di un gene nel database."""
    with db.session() as session:
        param = session.query(GeneParameter).filter_by(
            gene_type=gene_type,
            parameter_name=parameter_name
        ).first()
        
        if param:
            param.value = str(value)
            param.updated_at = func.now()
        else:
            param = GeneParameter(
                gene_type=gene_type,
                parameter_name=parameter_name,
                value=str(value)
            )
            session.add(param)
            
        session.commit()
