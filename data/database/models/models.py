"""
Database Models
--------------
Definizione dei modelli del database per il framework TradingDNA.
"""

# Standard library imports
from datetime import datetime
from typing import Optional, List, Dict, Any
import yaml

# Third-party imports
import numpy as np
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, JSON, Text, Enum, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

# Local imports
from data.database.session_manager import DBSessionManager

# Carica configurazione database
with open('config/security.yaml', 'r') as f:
    config = yaml.safe_load(f)
    DATABASE_URL = config['database']['url']
    SYNC_DATABASE_URL = DATABASE_URL

# Base class per i modelli
Base = declarative_base()

# Ottieni l'istanza del session manager
db = DBSessionManager()

class Exchange(Base):
    """Modello per gli exchange supportati."""
    __tablename__ = 'exchanges'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relazioni
    symbols = relationship("Symbol", back_populates="exchange")
    market_data = relationship("MarketData", back_populates="exchange")

class Symbol(Base):
    """Modello per i simboli/coppie di trading."""
    __tablename__ = 'symbols'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(20), nullable=False)
    base_asset = Column(String(10), nullable=False)  # es. 'BTC', 'ETH'
    quote_asset = Column(String(10), nullable=False)  # es. 'USDT', 'BTC'
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relazioni
    exchange = relationship("Exchange", back_populates="symbols")
    market_data = relationship("MarketData", back_populates="symbol")
    
    # Vincolo di unicità composito
    __table_args__ = (
        UniqueConstraint('name', 'exchange_id', name='uix_symbol_exchange'),
    )

class MarketData(Base):
    """Modello per i dati di mercato."""
    __tablename__ = 'market_data'
    
    id = Column(Integer, primary_key=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    symbol_id = Column(Integer, ForeignKey('symbols.id'), nullable=False)
    timeframe = Column(String(10), nullable=False)  # es. '1m', '5m', '1h', '1d'
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_valid = Column(Boolean, default=True)
    
    # Relazioni
    exchange = relationship("Exchange", back_populates="market_data")
    symbol = relationship("Symbol", back_populates="market_data")
    
    # Vincoli di unicità
    __table_args__ = (
        UniqueConstraint('exchange_id', 'symbol_id', 'timeframe', 'timestamp', name='uix_market_data'),
    )

class GeneParameter(Base):
    """Modello per i parametri dei geni."""
    __tablename__ = 'gene_parameters'
    
    id = Column(Integer, primary_key=True)
    gene_type = Column(String(50), nullable=False)  # es. 'rsi', 'moving_average'
    parameter_name = Column(String(50), nullable=False)
    value = Column(String(50), nullable=False)  # Cambiato da Float a String per supportare sia numeri che stringhe
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Vincolo di unicità composito
    __table_args__ = (
        UniqueConstraint('gene_type', 'parameter_name', name='uix_gene_parameter'),
    )

class PerformanceMetrics(Base):
    """Modello per le metriche di performance."""
    __tablename__ = 'performance_metrics'
    
    id = Column(Integer, primary_key=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    symbol_id = Column(Integer, ForeignKey('symbols.id'), nullable=False)
    timeframe = Column(String(10), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    
    # Metriche di performance
    total_return = Column(Float)
    annualized_return = Column(Float)
    volatility = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    avg_daily_volume = Column(Float)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def calculate_metrics(self, prices: List[float], volumes: List[float]) -> None:
        """Calcola le metriche di performance."""
        if len(prices) < 2:
            return
            
        # Calcola rendimenti
        returns = np.diff(prices) / prices[:-1]
        
        # Total return
        self.total_return = (prices[-1] - prices[0]) / prices[0]
        
        # Annualized return
        days = (self.end_time - self.start_time).days
        self.annualized_return = (1 + self.total_return) ** (365/days) - 1
        
        # Volatilità
        self.volatility = np.std(returns) * np.sqrt(252)
        
        # Sharpe ratio
        risk_free_rate = 0.02  # 2% annuo
        excess_return = self.annualized_return - risk_free_rate
        self.sharpe_ratio = excess_return / self.volatility if self.volatility != 0 else 0
        
        # Maximum drawdown
        peak = prices[0]
        max_dd = 0
        for price in prices[1:]:
            if price > peak:
                peak = price
            dd = (peak - price) / peak
            max_dd = max(max_dd, dd)
        self.max_drawdown = max_dd
        
        # Average daily volume
        self.avg_daily_volume = np.mean(volumes)

class RiskMetrics(Base):
    """Modello per le metriche di rischio."""
    __tablename__ = 'risk_metrics'
    
    id = Column(Integer, primary_key=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    symbol_id = Column(Integer, ForeignKey('symbols.id'), nullable=False)
    timeframe = Column(String(10), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    
    # Metriche di rischio
    beta = Column(Float)
    alpha = Column(Float)
    var_95 = Column(Float)
    var_99 = Column(Float)
    expected_shortfall = Column(Float)
    liquidity_ratio = Column(Float)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def calculate_metrics(self, returns: List[float], market_returns: List[float], volumes: List[float]) -> None:
        """Calcola le metriche di rischio."""
        if len(returns) < 2:
            return
            
        # Beta e Alpha
        cov = np.cov(returns, market_returns)[0][1]
        market_var = np.var(market_returns)
        self.beta = cov / market_var if market_var != 0 else 1
        
        avg_return = np.mean(returns)
        avg_market_return = np.mean(market_returns)
        self.alpha = avg_return - self.beta * avg_market_return
        
        # Value at Risk
        returns_sorted = np.sort(returns)
        n = len(returns_sorted)
        self.var_95 = returns_sorted[int(0.05 * n)]
        self.var_99 = returns_sorted[int(0.01 * n)]
        
        # Expected Shortfall (CVaR)
        var_95_idx = int(0.05 * n)
        self.expected_shortfall = np.mean(returns_sorted[:var_95_idx])
        
        # Liquidity Ratio (Volume-weighted price impact)
        price_changes = np.abs(returns)
        self.liquidity_ratio = np.mean(price_changes / volumes) if volumes else 0

def initialize_database() -> None:
    """Inizializza il database creando tutte le tabelle."""
    Base.metadata.create_all(db.engine)

def reset_database() -> None:
    """Resetta il database eliminando e ricreando tutte le tabelle."""
    Base.metadata.drop_all(db.engine)
    Base.metadata.create_all(db.engine)

def check_gene_parameters_exist() -> bool:
    """
    Verifica se esistono parametri dei geni nel database.
    Controlla specificamente ogni tipo di gene.
    
    Returns:
        True se tutti i geni hanno i loro parametri, False altrimenti
    """
    with db.session() as session:
        # Lista dei geni da verificare
        gene_types = ['rsi', 'moving_average', 'macd', 'bollinger', 'stochastic', 'atr']
        
        for gene_type in gene_types:
            # Verifica se esistono parametri per questo gene
            exists = session.query(GeneParameter).filter_by(gene_type=gene_type).first() is not None
            if not exists:
                return False
                
        return True

def initialize_gene_parameters(config: Dict[str, Any]) -> None:
    """
    Inizializza i parametri dei geni nel database usando i valori di default dalla configurazione.
    Elimina tutti i parametri esistenti e li ricrea dai valori di default.
    
    Args:
        config: Configurazione contenente i valori di default dei geni
    """
    try:
        # Carica la configurazione dei geni da gene.yaml
        with open('config/gene.yaml', 'r') as f:
            gene_config = yaml.safe_load(f).get('gene', {})
        
        with db.session() as session:
            # Elimina tutti i parametri esistenti
            session.query(GeneParameter).delete()
            
            # Per ogni tipo di gene
            for gene_type, gene_data in gene_config.items():
                if gene_type == 'base':  # Salta la configurazione base
                    continue
                    
                # Ottieni i parametri di default
                default_params = gene_data.get('default', {})
                if not default_params:
                    print(f"Nessun parametro di default trovato per il gene {gene_type}")
                    continue
                    
                # Salva ogni parametro nel database
                for param_name, value in default_params.items():
                    param = GeneParameter(
                        gene_type=gene_type,
                        parameter_name=param_name,
                        value=str(value)  # Converti tutto in stringa
                    )
                    session.add(param)
                    
            session.commit()
            print("Parametri dei geni inizializzati con successo")
                    
    except Exception as e:
        print(f"Errore durante l'inizializzazione dei parametri dei geni: {str(e)}")
        raise

def update_gene_parameter(gene_type: str, parameter_name: str, value: Any) -> None:
    """
    Aggiorna un parametro di un gene nel database.
    
    Args:
        gene_type: Tipo di gene (es. 'rsi', 'moving_average')
        parameter_name: Nome del parametro
        value: Nuovo valore (può essere numero o stringa)
    """
    with db.session() as session:
        # Cerca il parametro esistente
        param = session.query(GeneParameter).filter_by(
            gene_type=gene_type,
            parameter_name=parameter_name
        ).first()
        
        if param:
            # Se esiste, aggiorna il valore
            param.value = str(value)
            param.updated_at = func.now()
        else:
            # Se non esiste, crea un nuovo record
            param = GeneParameter(
                gene_type=gene_type,
                parameter_name=parameter_name,
                value=str(value)
            )
            session.add(param)
