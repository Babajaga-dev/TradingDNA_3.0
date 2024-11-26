"""
TradingDNA Data System - Exchange Connectors
----------------------------------------
Sistema di connettori per exchange di trading.
"""

from typing import Dict, Any, Optional, Set, Type, Union

from .base_connector import (
    BaseConnector,
    ExchangeError,
    RateLimitError,
    AuthenticationError,
    NetworkError
)

from .ccxt_connector import (
    CCXTConnector,
    CCXTConnectorFactory
)

from .rate_limiter import (
    RateLimitStrategy,
    RateLimitRule,
    RateLimitStats,
    RateLimitManager
)

from .retry_handler import (
    RetryStrategy,
    RetryConfig,
    RetryStats,
    RetryError,
    RetryHandler,
    CircuitBreaker,
    RetryWithCircuitBreaker,
    retry
)

__all__ = [
    # Base Connector
    'BaseConnector',
    'ExchangeError',
    'RateLimitError',
    'AuthenticationError',
    'NetworkError',
    
    # CCXT Connector
    'CCXTConnector',
    'CCXTConnectorFactory',
    
    # Rate Limiter
    'RateLimitStrategy',
    'RateLimitRule',
    'RateLimitStats',
    'RateLimitManager',
    
    # Retry Handler
    'RetryStrategy',
    'RetryConfig',
    'RetryStats',
    'RetryError',
    'RetryHandler',
    'CircuitBreaker',
    'RetryWithCircuitBreaker',
    'retry',
    
    # Factory functions
    'create_connector',
    'create_rate_limiter',
    'create_retry_handler'
]

def create_connector(
    exchange_id: str,
    config: Dict[str, Any]
) -> BaseConnector:
    """
    Crea un nuovo connettore per exchange.
    
    Args:
        exchange_id: ID dell'exchange
        config: Configurazione connettore
        
    Returns:
        Istanza configurata del connettore
        
    Raises:
        ExchangeError: Se la creazione fallisce
    """
    return CCXTConnectorFactory.create_connector(exchange_id, config)

def create_rate_limiter(
    max_requests: int,
    time_window: float,
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
) -> RateLimitManager:
    """
    Crea un nuovo rate limiter.
    
    Args:
        max_requests: Massimo numero richieste
        time_window: Finestra temporale
        strategy: Strategia da usare
        
    Returns:
        Istanza configurata del rate limiter
    """
    manager = RateLimitManager()
    rule = RateLimitRule(max_requests, time_window)
    manager.add_limiter("default", strategy, rule)
    return manager

def create_retry_handler(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    exceptions: Optional[Set[Type[Exception]]] = None,
    use_circuit_breaker: bool = True,
    failure_threshold: int = 5,
    reset_timeout: float = 60.0
) -> Union[RetryHandler, RetryWithCircuitBreaker]:
    """
    Crea un nuovo retry handler.
    
    Args:
        max_attempts: Massimo numero tentativi
        base_delay: Delay base
        max_delay: Delay massimo
        strategy: Strategia retry
        exceptions: Eccezioni da gestire
        use_circuit_breaker: Usa circuit breaker
        failure_threshold: Soglia fallimenti
        reset_timeout: Timeout reset
        
    Returns:
        Istanza configurata del retry handler
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        strategy=strategy,
        exceptions=exceptions
    )
    
    if use_circuit_breaker:
        return RetryWithCircuitBreaker(
            config,
            failure_threshold,
            reset_timeout
        )
    else:
        return RetryHandler(config)