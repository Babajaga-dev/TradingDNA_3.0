"""
Menu Package
-----------
Package per la gestione del menu interattivo CLI.
"""

from typing import Dict, Any, List
from .menu_manager import MenuManager
from .menu_items import (
    create_command,
    create_submenu,
    create_separator,
    download_historical_data,
    view_historical_data,
    config_menu_items,
    MenuItem,
    CommandMenuItem,
    SubMenuItem,
    SeparatorMenuItem,
    MenuContext
)

def create_menu(title: str = "TradingDNA CLI") -> MenuManager:
    """
    Crea e restituisce un'istanza di MenuManager.
    
    Args:
        title: Titolo del menu (opzionale)
    
    Returns:
        Istanza di MenuManager configurata con il titolo specificato
    """
    return MenuManager(title)

def create_menu_from_dict(menu_config: Dict[str, Any], title: str = "TradingDNA CLI") -> MenuManager:
    """
    Crea un menu a partire da una configurazione dizionario.
    
    Args:
        menu_config: Dizionario contenente la configurazione del menu
        title: Titolo del menu (opzionale)
    
    Returns:
        Istanza di MenuManager configurata con gli elementi del dizionario
    """
    menu = create_menu(title)
    
    def _create_menu_item(item_config: Dict[str, Any]) -> MenuItem:
        """Crea un elemento del menu a partire dalla sua configurazione."""
        item_type = item_config.get('type', 'command')
        name = item_config.get('name', '')
        description = item_config.get('description', '')
        
        if item_type == 'submenu':
            # Ricorsivamente crea sottomenu
            subitems = [_create_menu_item(subitem) for subitem in item_config.get('items', [])]
            return create_submenu(name, subitems, description)
        
        elif item_type == 'separator':
            return create_separator()
        
        elif item_type == 'command':
            # Assume che la callback sia definita altrove o passata come stringa
            callback_name = item_config.get('callback')
            
            # Mappa delle callback predefinite
            predefined_callbacks = {
                'download_historical_data': download_historical_data,
                'view_historical_data': view_historical_data,
                # Aggiungi altre callback predefinite se necessario
            }
            
            callback = predefined_callbacks.get(callback_name)
            
            if callback is None:
                raise ValueError(f"Callback non trovata per {callback_name}")
            
            return create_command(name, callback, description)
        
        else:
            raise ValueError(f"Tipo di menu item non supportato: {item_type}")
    
    # Aggiungi gli elementi al menu
    for item_config in menu_config.get('items', []):
        menu_item = _create_menu_item(item_config)
        menu.add_menu_item(menu_item)
    
    return menu

__all__ = [
    'MenuManager',
    'create_command',
    'create_submenu',
    'create_separator',
    'download_historical_data',
    'view_historical_data',
    'config_menu_items',
    'MenuItem',
    'CommandMenuItem',
    'SubMenuItem',
    'SeparatorMenuItem',
    'MenuContext',
    'create_menu',
    'create_menu_from_dict'  # Aggiungo create_menu_from_dict a __all__
]
