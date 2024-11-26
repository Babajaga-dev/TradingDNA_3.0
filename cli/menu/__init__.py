"""
TradingDNA CLI Framework - Menu Module
------------------------------------
Modulo per la gestione dei menu interattivi nell'applicazione CLI.
Fornisce classi per la creazione e gestione di menu gerarchici.
"""

from typing import List, Optional, Any, Callable

from .menu_items import (
    MenuItem,
    CommandMenuItem,
    SubMenuItem,
    SeparatorMenuItem,
    MenuContext,
    create_command,
    create_submenu,
    create_separator
)

from .menu_manager import MenuManager

__all__ = [
    # Classi base
    'MenuItem',
    'CommandMenuItem',
    'SubMenuItem',
    'SeparatorMenuItem',
    'MenuContext',
    'MenuManager',
    
    # Factory functions
    'create_command',
    'create_submenu',
    'create_separator',
    
    # Funzioni di utilità
    'create_menu',
    'create_menu_from_dict'
]

def create_menu(title: str = "TradingDNA CLI") -> MenuManager:
    """
    Crea un nuovo menu manager con il titolo specificato.
    
    Args:
        title: Titolo del menu
        
    Returns:
        Istanza configurata di MenuManager
    """
    return MenuManager(title)

def create_menu_from_dict(
    menu_dict: dict,
    title: str = "TradingDNA CLI"
) -> MenuManager:
    """
    Crea un menu da una struttura dizionario.
    
    Args:
        menu_dict: Dizionario con la struttura del menu
        title: Titolo del menu
        
    Returns:
        MenuManager configurato con la struttura specificata
        
    Example:
        menu_dict = {
            'name': 'Menu Principale',
            'items': [
                {
                    'type': 'command',
                    'name': 'Comando 1',
                    'callback': lambda: print('Comando 1'),
                    'description': 'Descrizione comando 1'
                },
                {
                    'type': 'submenu',
                    'name': 'Sottomenu 1',
                    'items': [
                        {
                            'type': 'command',
                            'name': 'Comando 2',
                            'callback': lambda: print('Comando 2')
                        }
                    ]
                },
                {
                    'type': 'separator'
                }
            ]
        }
    """
    menu = MenuManager(title)
    
    def _create_items(items_dict: List[dict]) -> List[MenuItem]:
        items = []
        for item in items_dict:
            item_type = item.get('type', '')
            
            if item_type == 'command':
                items.append(create_command(
                    name=item['name'],
                    callback=item['callback'],
                    description=item.get('description', ''),
                    enabled=item.get('enabled', True),
                    visible=item.get('visible', True),
                    confirm=item.get('confirm', False)
                ))
            elif item_type == 'submenu':
                subitems = _create_items(item['items'])
                items.append(create_submenu(
                    name=item['name'],
                    items=subitems,
                    description=item.get('description', ''),
                    enabled=item.get('enabled', True),
                    visible=item.get('visible', True)
                ))
            elif item_type == 'separator':
                items.append(create_separator(
                    char=item.get('char', '-'),
                    length=item.get('length', 40)
                ))
                
        return items
    
    # Crea gli elementi del menu dalla struttura dizionario
    if 'items' in menu_dict:
        items = _create_items(menu_dict['items'])
        for item in items:
            menu.add_menu_item(item)
            
    return menu