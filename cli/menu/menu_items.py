"""
Menu Items
----------
Re-esporta le classi e funzioni dei menu dai moduli specializzati.
Mantiene la compatibilità con il resto del sistema.
"""

# Re-esporta le classi base
from .menu_core import (
    MenuItem,
    CommandMenuItem,
    SubMenuItem,
    SeparatorMenuItem,
    MenuContext,
    create_command,
    create_submenu,
    create_separator
)

# Re-esporta le funzioni di utilità
from .menu_utils import (
    force_close_connections,
    shutdown_all_loggers,
    reset_system,
    manage_parameters,
    view_historical_data,
    genetic_optimization_placeholder
)

# Re-esporta le definizioni dei menu
from .menu_definitions import (
    download_historical_data,
    config_menu_items,
    rsi_menu_items,
    moving_average_menu_items,
    gene_menu_items,
    all_menu_items
)

# Per mantenere la compatibilità con il codice esistente
__all__ = [
    # Classi base
    'MenuItem',
    'CommandMenuItem',
    'SubMenuItem',
    'SeparatorMenuItem',
    'MenuContext',
    'create_command',
    'create_submenu',
    'create_separator',
    
    # Funzioni di utilità
    'force_close_connections',
    'shutdown_all_loggers',
    'reset_system',
    'manage_parameters',
    'view_historical_data',
    'genetic_optimization_placeholder',
    
    # Definizioni dei menu
    'download_historical_data',
    'config_menu_items',
    'rsi_menu_items',
    'moving_average_menu_items',
    'gene_menu_items',
    'all_menu_items'
]
