"""
Gene Manager
-----------
Gestisce le operazioni sui geni del trading system attraverso il menu CLI.
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import matplotlib.pyplot as plt
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from ..genes import Gene, RSIGene, MovingAverageGene
from ..config.config_loader import get_config_loader
from ..logger.log_manager import get_logger
from data.database.models import (
    get_session, initialize_gene_parameters,
    GeneParameter, update_gene_parameter,
    MarketData, Symbol, initialize_database
)

class GeneManager:
    """Gestore delle operazioni sui geni."""
    
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

    def get_available_pairs_timeframes(self) -> List[Tuple[str, str]]:
        """
        Recupera tutte le coppie e timeframe disponibili nel database.
        
        Returns:
            Lista di tuple (coppia, timeframe)
        """
        if not self.check_database_data():
            return []
            
        session = get_session()
        try:
            # Query diretta con group by
            results = session.query(Symbol.name, MarketData.timeframe)\
                .join(MarketData)\
                .filter(MarketData.is_valid == True)\
                .group_by(Symbol.name, MarketData.timeframe)\
                .order_by(Symbol.name, MarketData.timeframe)\
                .all()
            
            self.logger.info(f"Coppie/timeframe trovati: {results}")
            
            if not results:
                self.console.print(Panel(
                    "[red]Nessuna coppia/timeframe trovata![/red]\n\n"
                    "[yellow]Per utilizzare il sistema è necessario:[/yellow]\n"
                    "1. Selezionare 'Scarica Dati Storici' dal menu principale\n"
                    "2. Scegliere le coppie di trading da scaricare\n"
                    "3. Selezionare il timeframe desiderato\n"
                    "4. Attendere il completamento del download",
                    title="Attenzione",
                    border_style="red"
                ))
                input("\nPremi INVIO per continuare...")
                
            return results
        except Exception as e:
            self.logger.error(f"Errore nel recupero delle coppie/timeframe: {str(e)}")
            return []
        finally:
            session.close()

    def get_historical_data(self, pair: str, timeframe: str, days: int) -> np.ndarray:
        """
        Recupera i dati storici dal database.
        
        Args:
            pair: Coppia di trading
            timeframe: Timeframe
            days: Numero di giorni di dati da recuperare
            
        Returns:
            Array numpy con i prezzi di chiusura
        """
        session = get_session()
        try:
            # Query più sicura con join esplicito e ordinamento ascendente
            data = session.query(MarketData)\
                .join(Symbol, Symbol.id == MarketData.symbol_id)\
                .filter(Symbol.name == pair)\
                .filter(MarketData.timeframe == timeframe)\
                .order_by(MarketData.timestamp.asc())\
                .limit(days)\
                .all()
                
            if not data:
                self.console.print(f"[red]Nessun dato trovato per {pair} ({timeframe})[/red]")
                return np.array([])
                
            return np.array([d.close for d in data])
        except Exception as e:
            self.logger.error(f"Errore nel recupero dei dati storici: {str(e)}")
            return np.array([])
        finally:
            session.close()

    def evaluate_performance(self, stats: Dict[str, float]) -> str:
        """
        Valuta la performance del gene basandosi sulle statistiche.
        
        Args:
            stats: Dizionario contenente le statistiche del test
            
        Returns:
            Stringa contenente la valutazione della performance
        """
        # Analisi del numero di segnali
        n_signals = stats['Numero totale segnali']
        signal_frequency = "alta" if n_signals > 30 else "media" if n_signals > 15 else "bassa"
        
        # Analisi della forza dei segnali
        mean_signal = abs(stats['Media segnali'])
        signal_strength = "forte" if mean_signal > 0.7 else "moderata" if mean_signal > 0.4 else "debole"
        
        # Analisi della consistenza
        std_dev = stats['Deviazione standard']
        consistency = "molto consistente" if std_dev < 0.2 else "consistente" if std_dev < 0.4 else "variabile"
        
        # Analisi del fitness score
        fitness = stats['Fitness score']
        performance = "eccellente" if fitness > 0.8 else "buona" if fitness > 0.6 else "discreta" if fitness > 0.4 else "da migliorare"
        
        # Genera il commento
        comment = (
            f"Performance {performance}. Il gene mostra una frequenza di segnali {signal_frequency} "
            f"con una forza {signal_strength} e una {consistency} consistenza nei segnali generati. "
        )
        
        # Aggiungi suggerimenti specifici
        if fitness < 0.6:
            comment += "Si consiglia di ottimizzare i parametri per migliorare la performance."
        elif std_dev > 0.4:
            comment += "Si potrebbe lavorare sulla stabilità dei segnali."
        elif mean_signal < 0.4:
            comment += "Si potrebbe aumentare la sensibilità del gene."
            
        return comment
        
    def test_gene(self, gene_type: str) -> None:
        """
        Testa un gene su tutte le coppie e timeframe disponibili.
        
        Args:
            gene_type: Tipo di gene da testare (es. 'rsi', 'moving_average')
        """
        # Verifica disponibilità coppie/timeframe
        pairs_timeframes = self.get_available_pairs_timeframes()
        if not pairs_timeframes:
            return
            
        # Richiedi periodo di test
        days = Prompt.ask(
            f"Numero di giorni di test (a partire dal più vecchio)",
            default="30"
        )
        try:
            days = int(days)
            if days < 1:
                raise ValueError("Il numero di giorni deve essere positivo")
        except ValueError as e:
            self.console.print(f"[red]Errore: {str(e)}[/red]")
            return
            
        # Mapping dei tipi di gene alle classi
        gene_classes = {
            'rsi': RSIGene,
            'moving_average': MovingAverageGene
        }
        
        if gene_type not in gene_classes:
            self.console.print(f"[red]Tipo di gene non supportato: {gene_type}[/red]")
            return
            
        # Crea istanza del gene
        gene_class = gene_classes[gene_type]
        gene = gene_class()
        
        # Carica i parametri dal database
        params = self.get_gene_parameters(gene_type)
        if params:
            gene.params = params
            
        # Tabella riassuntiva dei risultati
        results_table = Table(title=f"Test Gene {gene_type.upper()} - Risultati")
        results_table.add_column("Coppia", style="cyan")
        results_table.add_column("Timeframe", style="magenta")
        results_table.add_column("Fitness Score", style="green")
        results_table.add_column("Valutazione", style="yellow")
        
        # Testa su ogni coppia/timeframe
        for pair, timeframe in pairs_timeframes:
            self.console.print(f"\n[bold]Testing {pair} ({timeframe})[/bold]")
            
            # Recupera dati storici
            prices = self.get_historical_data(pair, timeframe, days)
            if len(prices) == 0:
                continue
                
            if len(prices) < days:
                self.console.print(f"[yellow]Attenzione: recuperati solo {len(prices)} giorni di dati[/yellow]")
                
            # Calcola segnali
            signals = []
            min_data_points = int(gene.params.get('period', 14)) + 1  # Default a 14 per RSI se non specificato
            
            for i in range(min_data_points, len(prices) + 1):
                signal = gene.calculate_signal(prices[:i])
                signals.append(signal)
                
            # Padding con zeri all'inizio per mantenere la lunghezza
            signals = [0] * (min_data_points - 1) + signals
            
            # Visualizza grafico
            plt.figure(figsize=(12, 6))
            
            # Subplot superiore per i prezzi
            plt.subplot(2, 1, 1)
            plt.plot(prices, label='Prezzo')
            if gene_type == 'moving_average':
                ma = gene.calculate_ma(prices)
                plt.plot(ma, label=f'{gene.params["type"]} ({gene.params["period"]})', linestyle='--')
            plt.title(f'Test Gene {gene_type.upper()} - {pair} ({timeframe})')
            plt.legend()
            plt.grid(True)
            
            # Subplot inferiore per i segnali
            plt.subplot(2, 1, 2)
            plt.plot(signals, label='Segnale', color='orange')
            plt.axhline(y=0, color='r', linestyle='--')
            plt.legend()
            plt.grid(True)
            
            # Salva il grafico
            output_dir = Path('data/gene_tests')
            output_dir.mkdir(parents=True, exist_ok=True)
            plt.savefig(output_dir / f'{gene_type}_{pair.replace("/", "_")}_{timeframe}_test.png')
            plt.close()
            
            # Calcola statistiche
            non_zero_signals = [s for s in signals if s != 0]
            stats = {
                'Numero totale segnali': len(non_zero_signals),
                'Media segnali': np.mean(non_zero_signals) if non_zero_signals else 0,
                'Deviazione standard': np.std(non_zero_signals) if non_zero_signals else 0,
                'Segnale minimo': min(non_zero_signals) if non_zero_signals else 0,
                'Segnale massimo': max(non_zero_signals) if non_zero_signals else 0,
                'Fitness score': gene.evaluate(prices)
            }
            
            # Valuta performance
            evaluation = self.evaluate_performance(stats)
            
            # Aggiungi alla tabella riassuntiva
            results_table.add_row(
                pair,
                timeframe,
                f"{stats['Fitness score']:.4f}",
                evaluation
            )
            
            # Mostra statistiche dettagliate
            stats_table = Table(title=f"Statistiche Dettagliate - {pair} ({timeframe})")
            stats_table.add_column("Metrica", style="cyan")
            stats_table.add_column("Valore", style="magenta")
            
            for metric, value in stats.items():
                stats_table.add_row(metric, f"{value:.4f}")
                
            self.console.print(stats_table)
            self.console.print(f"\n[bold]Valutazione Performance:[/bold]")
            self.console.print(f"[yellow]{evaluation}[/yellow]")
            self.console.print(f"\n[green]Grafico salvato in: data/gene_tests/{gene_type}_{pair.replace('/', '_')}_{timeframe}_test.png[/green]")
            
            # Pausa per permettere di visualizzare i risultati
            input("\nPremi INVIO per continuare con la prossima coppia...")
            
        # Mostra tabella riassuntiva finale
        self.console.print("\n[bold]Riepilogo Complessivo:[/bold]")
        self.console.print(results_table)
        input("\nPremi INVIO per terminare...")
        
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
