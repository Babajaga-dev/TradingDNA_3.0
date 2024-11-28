"""
Menu Core
--------
Definizione delle classi base per gli elementi del menu interattivo.
"""

from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

class MenuItem(ABC):
    """Classe base astratta per gli elementi del menu."""
    
    def __init__(
        self,
        name: str,
        description: str = "",
        enabled: bool = True,
        visible: bool = True
    ):
        self.name = name
        self.description = description
        self.enabled = enabled
        self.visible = visible
        
    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Esegue l'azione associata all'elemento del menu."""
        pass
    
    def is_enabled(self) -> bool:
        """Verifica se l'elemento è abilitato."""
        return self.enabled
    
    def is_visible(self) -> bool:
        """Verifica se l'elemento è visibile."""
        return self.visible

class CommandMenuItem(MenuItem):
    """Elemento del menu che esegue un comando."""
    
    def __init__(
        self,
        name: str,
        callback: Callable[..., Any],
        description: str = "",
        enabled: bool = True,
        visible: bool = True,
        confirm: bool = False
    ):
        super().__init__(name, description, enabled, visible)
        self.callback = callback
        self.confirm = confirm
        
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Esegue il callback associato al comando."""
        if self.confirm:
            confirm = input(f"Confermi l'esecuzione di '{self.name}'? [s/N]: ")
            if confirm.lower() != 's':
                return None
        return self.callback(*args, **kwargs)

class SubMenuItem(MenuItem):
    """Elemento del menu che rappresenta un sottomenu."""
    
    def __init__(
        self,
        name: str,
        items: List[MenuItem],
        description: str = "",
        enabled: bool = True,
        visible: bool = True
    ):
        super().__init__(name, description, enabled, visible)
        self.items = items
        
    def execute(self, *args: Any, **kwargs: Any) -> None:
        """Non fa nulla, la gestione del sottomenu è delegata al MenuManager."""
        return None
    
    def add_item(self, item: MenuItem) -> None:
        """Aggiunge un elemento al sottomenu."""
        self.items.append(item)
    
    def remove_item(self, name: str) -> None:
        """Rimuove un elemento dal sottomenu."""
        self.items = [item for item in self.items if item.name != name]
    
    def get_items(self) -> List[MenuItem]:
        """Ritorna la lista degli elementi del sottomenu."""
        return self.items

class SeparatorMenuItem(MenuItem):
    """Elemento del menu che rappresenta un separatore."""
    
    def __init__(self, char: str = "-", length: int = 40):
        super().__init__("separator", "", True, True)
        self.char = char
        self.length = length
        
    def execute(self, *args: Any, **kwargs: Any) -> None:
        """Non fa nulla, è solo un separatore visivo."""
        pass

@dataclass
class MenuContext:
    """Contesto per la gestione dello stato del menu."""
    
    current_path: List[str] = field(default_factory=list)
    history: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    
    def push_path(self, name: str) -> None:
        """Aggiunge un elemento al path corrente."""
        self.current_path.append(name)
        self.history.append(name)
        
    def pop_path(self) -> Optional[str]:
        """Rimuove e ritorna l'ultimo elemento del path."""
        if self.current_path:
            return self.current_path.pop()
        return None
    
    def get_current_path(self) -> str:
        """Ritorna il path corrente come stringa."""
        return " > ".join(self.current_path)
    
    def clear(self) -> None:
        """Pulisce il contesto."""
        self.current_path.clear()
        self.history.clear()
        self.data.clear()

def create_command(
    name: str,
    callback: Callable[..., Any],
    description: str = "",
    **kwargs: Any
) -> CommandMenuItem:
    """
    Factory function per creare un comando del menu.
    
    Args:
        name: Nome del comando
        callback: Funzione da eseguire
        description: Descrizione del comando
        **kwargs: Argomenti aggiuntivi per CommandMenuItem
        
    Returns:
        Istanza di CommandMenuItem
    """
    return CommandMenuItem(name, callback, description, **kwargs)

def create_submenu(
    name: str,
    items: List[MenuItem],
    description: str = "",
    **kwargs: Any
) -> SubMenuItem:
    """
    Factory function per creare un sottomenu.
    
    Args:
        name: Nome del sottomenu
        items: Lista di elementi del menu
        description: Descrizione del sottomenu
        **kwargs: Argomenti aggiuntivi per SubMenuItem
        
    Returns:
        Istanza di SubMenuItem
    """
    return SubMenuItem(name, items, description, **kwargs)

def create_separator(char: str = "-", length: int = 40) -> SeparatorMenuItem:
    """
    Factory function per creare un separatore.
    
    Args:
        char: Carattere da usare per il separatore
        length: Lunghezza del separatore
        
    Returns:
        Istanza di SeparatorMenuItem
    """
    return SeparatorMenuItem(char, length)
