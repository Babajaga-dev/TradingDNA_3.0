"""
Menu Manager
-----------
Gestisce l'interfaccia interattiva del menu CLI.
Utilizza rich per una UI moderna e reattiva.
"""

import sys
import logging
from typing import List, Optional, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.style import Style
from rich.text import Text
from rich.box import ROUNDED

from .menu_items import (
    MenuItem, MenuContext, SeparatorMenuItem, 
    SubMenuItem
)

class MenuManager:
    """Gestore del menu interattivo."""
    
    def __init__(self, title: str = "TradingDNA CLI"):
        self.title = title
        self.items: List[MenuItem] = []
        self.context = MenuContext()
        self.console = Console()
        self.menu_stack: List[List[MenuItem]] = []  # Stack per tenere traccia dei menu
        self.current_items: Optional[List[MenuItem]] = None
        self.logger = logging.getLogger(__name__)
        
    def add_menu_item(self, item: MenuItem) -> None:
        """
        Aggiunge un elemento al menu.
        
        Args:
            item: Elemento del menu da aggiungere
        """
        self.items.append(item)
        
    def remove_menu_item(self, name: str) -> None:
        """
        Rimuove un elemento dal menu.
        
        Args:
            name: Nome dell'elemento da rimuovere
        """
        self.items = [item for item in self.items if item.name != name]
        
    def _create_menu_table(self) -> Table:
        """
        Crea una tabella rich per visualizzare il menu.
        
        Returns:
            Tabella formattata con gli elementi del menu
        """
        table = Table(show_header=True, header_style="bold magenta", box=ROUNDED, padding=(0, 2))
        
        # Aggiungi colonne per indice, icona e nome
        table.add_column("", style="cyan", justify="center", width=4)  # Indice
        table.add_column("", style="cyan", justify="center", width=4)  # Icona
        table.add_column("Nome", style="bold white", justify="left")
        table.add_column("Descrizione", style="dim", justify="left")
        
        # Usa il menu corrente se presente, altrimenti usa il menu principale
        items_to_show = self.current_items if self.current_items is not None else self.items
        
        # Aggiungi elementi visibili
        visible_items = [item for item in items_to_show if item.is_visible()]
        
        # Contatore per l'indice degli elementi non-separatori
        idx_counter = 1
        
        for item in visible_items:
            if isinstance(item, SeparatorMenuItem):
                # Aggiungi separatore
                table.add_row(
                    "",
                    "",
                    item.char * item.length,
                    "",
                    style="dim"
                )
            else:
                # Stile per elementi disabilitati
                style = "dim" if not item.is_enabled() else None
                
                # Scegli l'icona in base al tipo di elemento
                if isinstance(item, SubMenuItem):  # SubMenuItem
                    icon = "📁"
                elif hasattr(item, 'callback'):  # CommandMenuItem
                    if "configur" in item.name.lower():
                        icon = "⚙️"
                    elif "scarica" in item.name.lower() or "download" in item.name.lower():
                        icon = "⬇️"
                    elif "visualizza" in item.name.lower():
                        icon = "👁️"
                    elif "analisi" in item.name.lower():
                        icon = "📊"
                    elif "report" in item.name.lower():
                        icon = "📝"
                    elif "monitor" in item.name.lower():
                        icon = "📺"
                    elif "backup" in item.name.lower():
                        icon = "💾"
                    elif "status" in item.name.lower():
                        icon = "🔧"
                    else:
                        icon = "🔧"
                else:
                    icon = "📌"
                
                table.add_row(
                    str(idx_counter) if item.is_enabled() else "-",
                    icon,
                    item.name,
                    item.description,
                    style=style
                )
                
                # Incrementa l'indice solo per gli elementi non-separatori
                idx_counter += 1
                
        return table
        
    def _display_menu(self) -> None:
        """Visualizza il menu corrente."""
        # Pulisci lo schermo
        self.console.clear()
        
        # Mostra il titolo
        if self.context.current_path:
            title = f"{self.title} - {self.context.get_current_path()}"
        else:
            title = self.title
            
        title_text = Text(title, style="bold blue on white", justify="center")
        self.console.print(Panel(title_text, style="bold blue", border_style="bright_yellow"))
        
        # Mostra la tabella del menu
        table = self._create_menu_table()
        self.console.print(table)
        
        # Mostra opzioni di navigazione
        if self.context.current_path:
            self.console.print("\n[dim]0. 🔙 Torna indietro[/dim]")
        self.console.print("[dim]q. 🚪 Esci[/dim]")
        
    def _get_visible_enabled_items(self) -> List[MenuItem]:
        """
        Ottiene la lista di elementi visibili e abilitati.
        
        Returns:
            Lista di elementi del menu visibili e abilitati
        """
        items_to_check = self.current_items if self.current_items is not None else self.items
        return [
            item for item in items_to_check 
            if item.is_visible() and item.is_enabled() and 
            not isinstance(item, SeparatorMenuItem)
        ]
        
    def _handle_input(self, choice: str) -> bool:
        """
        Gestisce l'input dell'utente.
        
        Args:
            choice: Scelta dell'utente
            
        Returns:
            True se continuare, False se uscire
        """
        if choice.lower() == 'q':
            return False
            
        if choice == '0' and self.context.current_path:
            self.context.pop_path()
            if self.menu_stack:  # Se c'è un menu precedente nello stack
                self.current_items = self.menu_stack.pop()  # Ripristina il menu precedente
            else:
                self.current_items = None  # Solo se lo stack è vuoto, torna al menu principale
            return True
            
        try:
            idx = int(choice) - 1
            
            # Debug: stampa tutti gli elementi visibili
            self.logger.debug("Elementi visibili nel menu:")
            enabled_items = self._get_visible_enabled_items()
            for i, item in enumerate(enabled_items):
                self.logger.debug(f"Indice {i+1}: Nome={item.name}, Tipo={type(item)}")
            
            if 0 <= idx < len(enabled_items):
                item = enabled_items[idx]
                
                # Gestisci sottomenu
                if isinstance(item, SubMenuItem):
                    self.logger.debug(f"Selezionato sottomenu: {item.name}")
                    self.logger.debug(f"Dettagli sottomenu:")
                    for subitem in item.get_items():
                        self.logger.debug(f"Nome: {subitem.name}, Visibile: {subitem.is_visible()}, Tipo: {type(subitem)}")
                    
                    self.context.push_path(item.name)
                    self.menu_stack.append(self.current_items if self.current_items is not None else self.items)
                    self.current_items = item.get_items()
                    return True
                    
                try:
                    # Esegui l'azione dell'elemento
                    result = item.execute()
                    
                    # Mostra il risultato se presente
                    if result is not None:
                        self.console.print(f"\nRisultato: {result}")
                        input("\nPremi INVIO per continuare...")
                        
                except Exception as e:
                    self.console.print(f"[red]Errore: {str(e)}[/red]")
                    input("\nPremi INVIO per continuare...")
                    
            else:
                self.console.print("[red]Scelta non valida[/red]")
                
        except ValueError:
            self.console.print("[red]Inserisci un numero valido[/red]")
            
        return True
        
    def show_menu(self) -> None:
        """Mostra il menu interattivo e gestisce l'interazione."""
        running = True
        
        while running:
            self._display_menu()
            
            choice = Prompt.ask("\nScegli un'opzione", default="")
            running = self._handle_input(choice)
            
    def clear(self) -> None:
        """Pulisce il menu e il suo contesto."""
        self.items.clear()
        self.context.clear()
        self.current_items = None
        self.menu_stack.clear()
        
    def set_data(self, key: str, value: Any) -> None:
        """
        Imposta un valore nel contesto del menu.
        
        Args:
            key: Chiave del dato
            value: Valore da memorizzare
        """
        self.context.data[key] = value
        
    def get_data(self, key: str, default: Any = None) -> Any:
        """
        Recupera un valore dal contesto del menu.
        
        Args:
            key: Chiave del dato
            default: Valore predefinito se la chiave non esiste
            
        Returns:
            Valore memorizzato o default
        """
        return self.context.data.get(key, default)
