"""
Menu Items
----------
Definizione delle classi per gli elementi del menu interattivo.
Supporta comandi, sottomenu e separatori.
"""

from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from data.collection.downloader import DataDownloader, DownloadConfig
from sqlalchemy.ext.asyncio import AsyncSession
from data.database.models import get_session
from cli.config import get_config_loader
import asyncio
from datetime import datetime, timedelta  # Importazione aggiunta

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
        
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Mostra il sottomenu."""
        from .menu_manager import MenuManager
        submenu = MenuManager()
        for item in self.items:
            submenu.add_menu_item(item)
        return submenu.show_menu()
    
    def add_item(self, item: MenuItem) -> None:
        """Aggiunge un elemento al sottomenu."""
        self.items.append(item)
    
    def remove_item(self, name: str) -> None:
        """Rimuove un elemento dal sottomenu."""
        self.items = [item for item in self.items if item.name != name]

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

# Aggiunta del comando per il download dei dati storici
async def download_historical_data():
    """Funzione per eseguire il download dei dati storici."""
    config = get_config_loader().config
    download_config = DownloadConfig(
        exchanges=[{
            'id': 'binance',
            'config': {
                'apiKey': config['exchanges']['binance']['api_key'],
                'secret': config['exchanges']['binance']['api_secret']
            }
        }],
        symbols=config['trading']['symbols'],
        timeframes=config['trading']['timeframes'],
        start_date=datetime.utcnow() - timedelta(days=365),  # Ultimo anno
        validate_data=True,
        update_metrics=True,
        max_concurrent=5,
        batch_size=1000
    )
    
    async with get_session() as session:
        downloader = DataDownloader(session, download_config)
        await downloader.download_data()

# Creazione del nuovo elemento di menu per il download dei dati storici
download_data_command = create_command(
    name="Scarica Dati Storici",
    callback=lambda: asyncio.run(download_historical_data()),
    description="Scarica i dati storici dai mercati configurati."
)
