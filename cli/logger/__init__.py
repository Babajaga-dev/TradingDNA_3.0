"""
TradingDNA CLI Framework - Logger Module
----------------------------------------
Modulo per la gestione del logging nell'applicazione CLI.
Fornisce formattatori personalizzati e gestione centralizzata dei log.
"""

from typing import Optional, Any, Union

from .log_manager import (
    LogManager, 
    get_log_manager,
    setup_logging,
    get_logger
)
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
    config: Union[str, dict, None] = None,
    log_level: str = "INFO",
    format_type: str = "colored",
    **kwargs: Any
) -> LogManager:
    """
    Configura il sistema di logging con le impostazioni specificate.
    
    Args:
        config: Percorso del file di configurazione YAML o dizionario di configurazione
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
    
    # Se è un percorso di file, configura da YAML
    if isinstance(config, str):
        log_manager.configure_from_yaml(config)
    
    # Configura il formattatore
    formatter = get_formatter(format_type, **kwargs)
    
    # Aggiorna i formattatori degli handler esistenti
    for handler in log_manager.handlers.values():
        handler.setFormatter(formatter)
        
    return log_manager
