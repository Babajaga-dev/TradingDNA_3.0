"""
Market Metrics Model
------------------
Modello SQLAlchemy per le metriche di mercato.
Include metriche di performance, rischio e volatilità.
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

class PerformanceMetrics(Base):
    """Metriche di performance del mercato."""
    
    __tablename__ = 'performance_metrics'
    
    id = Column(Integer, primary_key=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    symbol_id = Column(Integer, ForeignKey('symbols.id'), nullable=False)
    timeframe = Column(String(10), nullable=False)
    
    # Intervallo temporale
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    
    # Metriche di rendimento
    total_return = Column(Float)
    annualized_return = Column(Float)
    risk_free_rate = Column(Float)
    alpha = Column(Float)
    beta = Column(Float)
    sharpe_ratio = Column(Float)
    sortino_ratio = Column(Float)
    max_drawdown = Column(Float)
    
    # Metriche di volatilità
    volatility = Column(Float)
    downside_volatility = Column(Float)
    upside_volatility = Column(Float)
    skewness = Column(Float)
    kurtosis = Column(Float)
    
    # Metriche di volume
    avg_volume = Column(Float)
    volume_trend = Column(Float)
    volume_volatility = Column(Float)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indici
    __table_args__ = (
        Index(
            'idx_performance_lookup',
            'exchange_id', 'symbol_id', 'timeframe',
            'start_time', 'end_time'
        ),
    )
    
    def calculate_metrics(self, prices: List[float], volumes: List[float]) -> None:
        """
        Calcola tutte le metriche di performance.
        
        Args:
            prices: Lista dei prezzi
            volumes: Lista dei volumi
        """
        import numpy as np
        from scipy import stats
        
        # Calcola rendimenti
        returns = np.diff(prices) / prices[:-1]
        
        # Metriche di rendimento
        self.total_return = (prices[-1] / prices[0]) - 1
        self.annualized_return = (
            (1 + self.total_return) ** (252 / len(returns)) - 1
        )
        
        # Volatilità
        self.volatility = np.std(returns) * np.sqrt(252)
        negative_returns = returns[returns < 0]
        self.downside_volatility = np.std(negative_returns) * np.sqrt(252)
        positive_returns = returns[returns > 0]
        self.upside_volatility = np.std(positive_returns) * np.sqrt(252)
        
        # Momenti statistici
        self.skewness = stats.skew(returns)
        self.kurtosis = stats.kurtosis(returns)
        
        # Metriche di rischio
        if self.risk_free_rate is not None:
            excess_returns = returns - self.risk_free_rate / 252
            self.sharpe_ratio = (
                np.mean(excess_returns) / np.std(excess_returns)
            ) * np.sqrt(252)
            
        if len(negative_returns) > 0:
            self.sortino_ratio = (
                np.mean(returns) / np.std(negative_returns)
            ) * np.sqrt(252)
            
        # Maximum Drawdown
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = cumulative / running_max - 1
        self.max_drawdown = np.min(drawdowns)
        
        # Metriche di volume
        self.avg_volume = np.mean(volumes)
        volume_returns = np.diff(volumes) / volumes[:-1]
        self.volume_volatility = np.std(volume_returns)
        self.volume_trend = np.polyfit(
            range(len(volumes)), volumes, 1
        )[0] / self.avg_volume

class RiskMetrics(Base):
    """Metriche di rischio del mercato."""
    
    __tablename__ = 'risk_metrics'
    
    id = Column(Integer, primary_key=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    symbol_id = Column(Integer, ForeignKey('symbols.id'), nullable=False)
    timeframe = Column(String(10), nullable=False)
    
    # Intervallo temporale
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    
    # Value at Risk
    var_95 = Column(Float)
    var_99 = Column(Float)
    cvar_95 = Column(Float)
    cvar_99 = Column(Float)
    
    # Metriche di rischio avanzate
    expected_shortfall = Column(Float)
    tail_risk = Column(Float)
    information_ratio = Column(Float)
    treynor_ratio = Column(Float)
    
    # Correlazioni
    market_correlation = Column(Float)
    sector_correlation = Column(Float)
    
    # Metriche di liquidità
    bid_ask_spread = Column(Float)
    liquidity_ratio = Column(Float)
    turnover_ratio = Column(Float)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indici
    __table_args__ = (
        Index(
            'idx_risk_lookup',
            'exchange_id', 'symbol_id', 'timeframe',
            'start_time', 'end_time'
        ),
    )
    
    def calculate_var(
        self,
        returns: List[float],
        confidence_level: float = 0.95
    ) -> float:
        """
        Calcola il Value at Risk.
        
        Args:
            returns: Lista dei rendimenti
            confidence_level: Livello di confidenza
            
        Returns:
            VaR calcolato
        """
        import numpy as np
        
        returns = np.array(returns)
        var = np.percentile(returns, (1 - confidence_level) * 100)
        return abs(var)
    
    def calculate_cvar(
        self,
        returns: List[float],
        confidence_level: float = 0.95
    ) -> float:
        """
        Calcola il Conditional Value at Risk.
        
        Args:
            returns: Lista dei rendimenti
            confidence_level: Livello di confidenza
            
        Returns:
            CVaR calcolato
        """
        import numpy as np
        
        returns = np.array(returns)
        var = self.calculate_var(returns, confidence_level)
        return abs(np.mean(returns[returns <= -var]))
    
    def calculate_metrics(
        self,
        returns: List[float],
        market_returns: List[float],
        volumes: List[float]
    ) -> None:
        """
        Calcola tutte le metriche di rischio.
        
        Args:
            returns: Lista dei rendimenti
            market_returns: Lista dei rendimenti di mercato
            volumes: Lista dei volumi
        """
        import numpy as np
        
        # Value at Risk
        self.var_95 = self.calculate_var(returns, 0.95)
        self.var_99 = self.calculate_var(returns, 0.99)
        self.cvar_95 = self.calculate_cvar(returns, 0.95)
        self.cvar_99 = self.calculate_cvar(returns, 0.99)
        
        # Expected Shortfall
        sorted_returns = np.sort(returns)
        worst_5_percent = int(len(returns) * 0.05)
        self.expected_shortfall = abs(
            np.mean(sorted_returns[:worst_5_percent])
        )
        
        # Tail Risk (usando la teoria dei valori estremi)
        tail_returns = sorted_returns[:worst_5_percent]
        if len(tail_returns) > 0:
            self.tail_risk = abs(np.mean(tail_returns) / np.std(tail_returns))
        
        # Correlazioni
        self.market_correlation = np.corrcoef(returns, market_returns)[0, 1]
        
        # Metriche di liquidità
        avg_volume = np.mean(volumes)
        if avg_volume > 0:
            self.liquidity_ratio = np.std(volumes) / avg_volume
            self.turnover_ratio = np.sum(volumes) / (
                len(volumes) * avg_volume
            )

class MarketRegime(Base):
    """Classificazione dei regimi di mercato."""
    
    __tablename__ = 'market_regimes'
    
    id = Column(Integer, primary_key=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    symbol_id = Column(Integer, ForeignKey('symbols.id'), nullable=False)
    timeframe = Column(String(10), nullable=False)
    
    # Intervallo temporale
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    
    # Classificazione regime
    regime_type = Column(String(20), nullable=False)  # trend, range, volatile
    confidence = Column(Float)
    
    # Metriche regime
    trend_strength = Column(Float)
    volatility_level = Column(Float)
    momentum = Column(Float)
    
    # Parametri tecnici
    support_level = Column(Float)
    resistance_level = Column(Float)
    pivot_points = Column(JSON)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indici
    __table_args__ = (
        Index(
            'idx_regime_lookup',
            'exchange_id', 'symbol_id', 'timeframe',
            'start_time', 'end_time'
        ),
        Index('idx_regime_type', 'regime_type'),
    )
    
    def classify_regime(
        self,
        prices: List[float],
        volumes: List[float]
    ) -> None:
        """
        Classifica il regime di mercato.
        
        Args:
            prices: Lista dei prezzi
            volumes: Lista dei volumi
        """
        import numpy as np
        from scipy import stats
        
        # Calcola rendimenti
        returns = np.diff(prices) / prices[:-1]
        
        # Calcola metriche
        volatility = np.std(returns)
        momentum = np.mean(returns)
        
        # Analisi del trend
        x = np.arange(len(prices))
        slope, _, r_value, _, _ = stats.linregress(x, prices)
        trend_strength = abs(r_value)
        
        self.trend_strength = trend_strength
        self.volatility_level = volatility
        self.momentum = momentum
        
        # Classifica regime
        if trend_strength > 0.7:
            self.regime_type = 'trend'
            self.confidence = trend_strength
        elif volatility > np.percentile(returns, 75):
            self.regime_type = 'volatile'
            self.confidence = (
                volatility / np.percentile(returns, 75)
            )
        else:
            self.regime_type = 'range'
            self.confidence = 1 - trend_strength
        
        # Calcola livelli
        window = min(20, len(prices))
        self.support_level = np.min(prices[-window:])
        self.resistance_level = np.max(prices[-window:])
        
        # Calcola pivot points
        high = np.max(prices)
        low = np.min(prices)
        close = prices[-1]
        
        pivot = (high + low + close) / 3
        r1 = 2 * pivot - low
        s1 = 2 * pivot - high
        r2 = pivot + (high - low)
        s2 = pivot - (high - low)
        
        self.pivot_points = {
            'pivot': float(pivot),
            'r1': float(r1),
            'r2': float(r2),
            's1': float(s1),
            's2': float(s2)
        }