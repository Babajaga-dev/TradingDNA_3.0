"""
Menu Manager
-----------
Gestisce l'interfaccia interattiva del menu CLI.
Utilizza rich per una UI moderna e reattiva.
"""

import sys
from typing import List, Optional, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.style import Style
from rich.text import Text
from rich.box import ROUNDED

from .menu_items import MenuItem, MenuContext, SeparatorMenuItem, download_data_command

class MenuManager:
    """Gestore del menu interattivo."""
    
    def __init__(self, title: str = "TradingDNA CLI"):
        self.title = title
        self.items: List[MenuItem] = []
        self.context = MenuContext()
        self.console = Console()
        
        # Aggiungi il comando per il download dei dati storici
        self.add_menu_item(download_data_command)
        
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
        
        # Aggiungi colonne per indice e nome
        table.add_column("Index", style="cyan", justify="center")
        table.add_column("Name", style="bold white", justify="left")
        table.add_column("Description", style="dim", justify="left")
        
        # Aggiungi elementi visibili
        visible_items = [item for item in self.items if item.is_visible()]
        
        for idx, item in enumerate(visible_items, 1):
            if isinstance(item, SeparatorMenuItem):
                # Aggiungi separatore
                table.add_row(
                    "",
                    item.char * item.length,
                    "",
                    style="dim"
                )
            else:
                # Stile per elementi disabilitati
                style = "dim" if not item.is_enabled() else None
                
                table.add_row(
                    str(idx) if item.is_enabled() else "-",
                    item.name,
                    item.description,
                    style=style
                )
                
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
            self.console.print("\n[dim]0. Torna indietro[/dim]")
        self.console.print("[dim]q. Esci[/dim]")
        
    def _get_visible_enabled_items(self) -> List[MenuItem]:
        """
        Ottiene la lista di elementi visibili e abilitati.
        
        Returns:
            Lista di elementi del menu visibili e abilitati
        """
        return [
            item for item in self.items 
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
            return True
            
        try:
            idx = int(choice) - 1
            enabled_items = self._get_visible_enabled_items()
            
            if 0 <= idx < len(enabled_items):
                item = enabled_items[idx]
                
                # Aggiorna il contesto per sottomenu
                if hasattr(item, 'items'):
                    self.context.push_path(item.name)
                    
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
