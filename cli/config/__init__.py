"""
TradingDNA CLI Framework - Config Module
--------------------------------------
Modulo per la gestione delle configurazioni del sistema.
Fornisce caricamento e validazione delle configurazioni.
"""

from typing import Dict, Any, Optional

from .config_loader import (
    ConfigLoader,
    ConfigError,
    ConfigValidationError,
    ConfigLoadError,
    get_config_loader
)

from .validators import (
    ValidationError,
    validate_type,
    validate_range,
    validate_string_length,
    validate_regex,
    validate_list_items,
    validate_required_fields,
    validate_path,
    ConfigValidator,
    create_system_validator
)

__all__ = [
    # Classi principali
    'ConfigLoader',
    'ConfigValidator',
    
    # Errori
    'ConfigError',
    'ConfigValidationError',
    'ConfigLoadError',
    'ValidationError',
    
    # Funzioni di validazione
    'validate_type',
    'validate_range',
    'validate_string_length',
    'validate_regex',
    'validate_list_items',
    'validate_required_fields',
    'validate_path',
    
    # Factory functions
    'create_system_validator',
    'create_config',
    
    # Getter functions
    'get_config_loader'
]

def create_config(config_dir: Optional[str] = None) -> ConfigLoader:
    """
    Crea una nuova istanza di ConfigLoader.
    
    Args:
        config_dir: Directory delle configurazioni (opzionale)
        
    Returns:
        Nuova istanza di ConfigLoader
    """
    loader = ConfigLoader(config_dir)
    
    # Aggiungi validatore di sistema predefinito
    validator = create_system_validator()
    loader.add_validator(validator.validate)
    
    return loader

def load_system_config() -> Dict[str, Any]:
    """
    Carica la configurazione di sistema.
    
    Returns:
        Configurazione caricata
        
    Raises:
        ConfigError: Se ci sono errori nel caricamento
    """
    loader = get_config_loader()
    
    try:
        # Se i file non esistono, crea configurazioni predefinite
        config_files_exist = all((loader.config_dir / f).exists() for f in loader.CONFIG_FILES)
        if not config_files_exist:
            loader.create_default_configs()
            
        return loader.load_all_configs()
        
    except Exception as e:
        raise ConfigError(f"Errore nel caricamento della configurazione: {str(e)}")
