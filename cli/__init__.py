"""
TradingDNA CLI Framework
------------------------
Framework CLI per la gestione del sistema di trading TradingDNA.
Fornisce interfacce interattive e strumenti per la gestione del sistema.
"""

__version__ = "0.1.0"
__author__ = "TradingDNA Team"
__license__ = "MIT"

from typing import List, Dict, Any

# Versione minima di Python richiesta
PYTHON_REQUIRES = ">=3.8"

# Dipendenze principali
DEPENDENCIES = [
    "rich>=13.0.0",
    "prompt-toolkit>=3.0.36",
    "click>=8.1.3",
    "colorama>=0.4.6",
    "pyyaml>=6.0.1"
]

# Importa e espone i componenti principali
from .menu import (
    MenuManager,
    MenuItem,
    CommandMenuItem,
    SubMenuItem,
    SeparatorMenuItem,
    MenuContext,
    create_command,
    create_submenu,
    create_separator,
    create_menu,
    create_menu_from_dict
)

from .config import (
    ConfigError,
    load_system_config,
    get_config_loader
)

from .logger import (
    setup_logging,
    get_logger
)

from .progress import (
    create_spinner,
    create_progress_bar
)

__all__ = [
    # Menu components
    'MenuManager',
    'MenuItem',
    'CommandMenuItem',
    'SubMenuItem',
    'SeparatorMenuItem',
    'MenuContext',
    'create_command',
    'create_submenu',
    'create_separator',
    'create_menu',
    'create_menu_from_dict',
    
    # Config components
    'ConfigError',
    'load_system_config',
    'get_config_loader',
    
    # Logging components
    'setup_logging',
    'get_logger',
    
    # Progress components
    'create_spinner',
    'create_progress_bar'
]