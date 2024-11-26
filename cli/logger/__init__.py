"""
TradingDNA CLI Framework - Logger Module
----------------------------------------
Modulo per la gestione del logging nell'applicazione CLI.
Fornisce formattatori personalizzati e gestione centralizzata dei log.
"""

from typing import Optional, Any

from .log_manager import LogManager, get_log_manager
from .formatters import (
    ColoredFormatter,
    JsonFormatter,
    CompactFormatter,
    get_formatter
)

__all__ = [
    'LogManager',
    'get_log_manager',
    'ColoredFormatter',
    'JsonFormatter',
    'CompactFormatter',
    'get_formatter',
    'setup_logging',
    'get_logger'
]

def setup_logging(
    log_level: str = "INFO",
    format_type: str = "colored",
    **kwargs: Any
) -> LogManager:
    """
    Configura il sistema di logging con le impostazioni specificate.
    
    Args:
        log_level: Livello di logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Tipo di formattatore da utilizzare
        **kwargs: Argomenti aggiuntivi per la configurazione
        
    Returns:
        Istanza configurata del LogManager
    """
    import logging
    
    # Converti il livello di log da stringa a costante
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Ottieni l'istanza del LogManager
    log_manager = get_log_manager()
    
    # Imposta il livello di log
    log_manager.set_level(numeric_level)
    
    # Configura il formattatore
    formatter = get_formatter(format_type, **kwargs)
    
    # Aggiorna i formattatori degli handler esistenti
    for handler in log_manager.handlers.values():
        handler.setFormatter(formatter)
        
    return log_manager

def get_logger(name: str) -> Any:
    """
    Ottiene un logger configurato per il modulo specificato.
    
    Args:
        name: Nome del logger/modulo
        
    Returns:
        Logger configurato
    """
    return get_log_manager().get_logger(name)