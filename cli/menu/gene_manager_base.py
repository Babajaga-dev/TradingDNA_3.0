"""
Gene Manager Base
----------------
Classe base per la gestione dei geni del trading system.
"""

from typing import Dict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from ..config.config_loader import get_config_loader
from ..logger.log_manager import get_logger
from data.database.models.models import (
    get_session, initialize_gene_parameters,
    GeneParameter, update_gene_parameter,
    MarketData, Symbol, initialize_database
)

class GeneManagerBase:
    """Classe base per la gestione dei geni."""
    
    def __init__(self):
        """Inizializza il gene manager."""
        self.console = Console()
        self.logger = get_logger(__name__)
        self.config = get_config_loader()
        
        # Assicura che il database sia inizializzato
        initialize_database()
        
    def check_database_data(self) -> bool:
        """
        Verifica se ci sono dati nel database.
        
        Returns:
            True se ci sono dati, False altrimenti
        """
        session = get_session()
        try:
            # Verifica se esistono simboli
            symbols_exist = session.query(Symbol).first() is not None
            if not symbols_exist:
                self.console.print(Panel(
                    "[red]Database vuoto![/red]\n\n"
                    "[yellow]Per utilizzare il sistema è necessario:[/yellow]\n"
                    "1. Selezionare 'Scarica Dati Storici' dal menu principale\n"
                    "2. Scegliere le coppie di trading da scaricare\n"
                    "3. Selezionare il timeframe desiderato\n"
                    "4. Attendere il completamento del download",
                    title="Attenzione",
                    border_style="red"
                ))
                input("\nPremi INVIO per continuare...")
                return False
                
            # Verifica se esistono dati di mercato
            data_exist = session.query(MarketData).first() is not None
            if not data_exist:
                self.console.print(Panel(
                    "[red]Nessun dato di mercato trovato![/red]\n\n"
                    "[yellow]Per utilizzare il sistema è necessario:[/yellow]\n"
                    "1. Selezionare 'Scarica Dati Storici' dal menu principale\n"
                    "2. Scegliere le coppie di trading da scaricare\n"
                    "3. Selezionare il timeframe desiderato\n"
                    "4. Attendere il completamento del download",
                    title="Attenzione",
                    border_style="red"
                ))
                input("\nPremi INVIO per continuare...")
                return False
                
            return True
        finally:
            session.close()

    def get_gene_parameters(self, gene_type: str) -> Dict[str, float]:
        """
        Recupera i parametri di un gene dal database.
        
        Args:
            gene_type: Tipo di gene (es. 'rsi', 'moving_average')
            
        Returns:
            Dizionario dei parametri del gene
        """
        session = get_session()
        try:
            params = session.query(GeneParameter).filter_by(gene_type=gene_type).all()
            
            # Recupera i vincoli dalla configurazione per determinare il tipo di valore
            constraints = self.config.get_value(f'gene.{gene_type}.constraints', {})
            
            result = {}
            for param in params:
                # Se il parametro ha dei tipi specifici nei vincoli, mantienilo come stringa
                if 'types' in constraints.get(param.parameter_name, {}):
                    result[param.parameter_name] = param.value
                else:
                    # Altrimenti convertilo in float
                    result[param.parameter_name] = float(param.value)
                    
            return result
        finally:
            session.close()

    def view_gene_params(self, gene_type: str) -> None:
        """
        Visualizza i parametri correnti di un gene.
        
        Args:
            gene_type: Tipo di gene da visualizzare
        """
        self.logger.debug(f"Tentativo di visualizzare i parametri per il gene: {gene_type}")
        
        # Recupera i parametri dal database
        params = self.get_gene_parameters(gene_type)
        self.logger.debug(f"Parametri recuperati dal database per {gene_type}: {params}")
        
        if not params:
            self.console.print(f"[yellow]Parametri non trovati nel database per il gene: {gene_type}[/yellow]")
            self.console.print("[yellow]Inizializzazione parametri dai valori di default...[/yellow]")
            
            # Inizializza i parametri dai valori di default
            config = self.config.config
            initialize_gene_parameters(config)
            
            # Riprova a recuperare i parametri
            params = self.get_gene_parameters(gene_type)
            if not params:
                self.console.print(f"[red]Impossibile inizializzare i parametri per il gene: {gene_type}[/red]")
                return
        
        # Recupera i vincoli dalla configurazione
        constraints = self.config.get_value(f'gene.{gene_type}.constraints', {})
        
        table = Table(title=f"Parametri Gene {gene_type.upper()}")
        table.add_column("Parametro", style="cyan")
        table.add_column("Valore", style="magenta")
        table.add_column("Vincoli", style="green")
        
        for param_name, value in params.items():
            constraint = constraints.get(param_name, {})
            constraints_str = ""
            
            if 'min' in constraint and 'max' in constraint:
                constraints_str = f"min: {constraint['min']} max: {constraint['max']}"
            elif 'types' in constraint:
                constraints_str = f"tipi: {', '.join(constraint['types'])}"
                
            table.add_row(
                param_name,
                str(value),
                constraints_str
            )
            
        self.console.print(table)
        input("\nPremi INVIO per continuare...")

    def set_gene_params(self, gene_type: str) -> None:
        """
        Modifica i parametri di un gene.
        
        Args:
            gene_type: Tipo di gene da modificare
        """
        # Recupera i parametri dal database
        params = self.get_gene_parameters(gene_type)
        if not params:
            self.console.print(f"[red]Parametri non trovati per il gene: {gene_type}[/red]")
            return
            
        # Recupera i vincoli dalla configurazione
        constraints = self.config.get_value(f'gene.{gene_type}.constraints', {})
        
        # Modifica parametri
        for param_name, value in params.items():
            constraint = constraints.get(param_name, {})
            
            while True:
                new_value = Prompt.ask(
                    f"Nuovo valore per {param_name} (attuale: {value})",
                    default=str(value)
                )
                
                try:
                    # Controlla se il parametro ha dei tipi specifici nei vincoli
                    if 'types' in constraint:
                        if new_value not in constraint['types']:
                            raise ValueError(f"Valore non valido. Valori consentiti: {', '.join(constraint['types'])}")
                        value_to_set = new_value
                    else:
                        # Converti al tipo corretto
                        value_to_set = float(new_value)
                        # Valida secondo i vincoli
                        if 'min' in constraint and value_to_set < constraint['min']:
                            raise ValueError(f"Valore minimo consentito: {constraint['min']}")
                        if 'max' in constraint and value_to_set > constraint['max']:
                            raise ValueError(f"Valore massimo consentito: {constraint['max']}")
                            
                    # Aggiorna il valore nel database
                    update_gene_parameter(gene_type, param_name, value_to_set)
                    break
                    
                except ValueError as e:
                    self.console.print(f"[red]Errore: {str(e)}[/red]")
                    if not Confirm.ask("Vuoi riprovare?"):
                        break
                        
        self.console.print("[green]Parametri aggiornati con successo[/green]")
        input("\nPremi INVIO per continuare...")

    def reset_gene_params(self, gene_type: str) -> None:
        """
        Resetta i parametri di un gene ai valori di default dal file di configurazione.
        
        Args:
            gene_type: Tipo di gene da resettare
        """
        self.logger.debug(f"Tentativo di resettare i parametri per il gene: {gene_type}")
        
        # Recupera i valori di default dalla configurazione
        default_params = self.config.get_value(f'gene.{gene_type}.default', {})
        constraints = self.config.get_value(f'gene.{gene_type}.constraints', {})
        
        if not default_params:
            self.console.print(f"[red]Valori di default non trovati per il gene: {gene_type}[/red]")
            return
            
        # Conferma dell'operazione
        if not Confirm.ask(f"Sei sicuro di voler resettare i parametri del gene {gene_type} ai valori di default?"):
            self.console.print("[yellow]Operazione annullata[/yellow]")
            return
            
        try:
            # Aggiorna ogni parametro nel database con il valore di default
            for param_name, default_value in default_params.items():
                # Controlla se il parametro ha dei tipi specifici nei vincoli
                if 'types' in constraints.get(param_name, {}):
                    # Se è un parametro di tipo stringa, lo lasciamo come stringa
                    value_to_set = default_value
                else:
                    # Altrimenti lo convertiamo in float
                    value_to_set = float(default_value)
                    
                update_gene_parameter(gene_type, param_name, value_to_set)
                
            self.console.print("[green]Parametri resettati con successo ai valori di default[/green]")
            
            # Mostra i nuovi valori
            self.view_gene_params(gene_type)
            
        except Exception as e:
            self.logger.error(f"Errore durante il reset dei parametri: {str(e)}")
            self.console.print(f"[red]Errore durante il reset dei parametri: {str(e)}[/red]")
