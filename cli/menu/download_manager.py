"""
Download Manager
--------------
Gestisce l'interfaccia utente per il download dei dati storici.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn, SpinnerColumn
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.live import Live

from data.collection.downloader import DataDownloader, DownloadConfig, DownloadStats
from data.database.models import get_session
from cli.config import get_config_loader

class DownloadManager:
    """Gestisce l'interfaccia utente per il download dei dati."""
    
    def __init__(self):
        """Inizializza il download manager."""
        self.console = Console()
        self.config = get_config_loader().config
        self.progress: Optional[Progress] = None
        self.task_id = None
        
    async def run_download(self) -> None:
        """Esegue il processo di download interattivo."""
        # Mostra configurazione corrente
        self._show_current_config()
        
        # Selezione simboli
        symbols = self._select_symbols()
        if not symbols:
            self.console.print("[red]Nessun simbolo selezionato. Download annullato.[/red]")
            return
            
        # Selezione timeframes
        timeframes = self._select_timeframes()
        if not timeframes:
            self.console.print("[red]Nessun timeframe selezionato. Download annullato.[/red]")
            return
            
        # Selezione periodo
        days = self._select_period()
        if not days:
            self.console.print("[red]Periodo non valido. Download annullato.[/red]")
            return
            
        # Conferma configurazione
        if not self._confirm_config(symbols, timeframes, days):
            self.console.print("[yellow]Download annullato dall'utente.[/yellow]")
            return
            
        # Esegue download
        await self._execute_download(symbols, timeframes, days)
        
    def _show_current_config(self) -> None:
        """Mostra la configurazione corrente."""
        self.console.print("\n[bold blue]Configurazione Corrente[/bold blue]")
        
        table = Table(show_header=True)
        table.add_column("Parametro")
        table.add_column("Valore")
        
        table.add_row(
            "Exchange",
            "Binance"
        )
        table.add_row(
            "Simboli Disponibili",
            ", ".join(self.config['portfolio']['symbols'])
        )
        table.add_row(
            "Timeframes Disponibili", 
            ", ".join(self.config['portfolio']['timeframes'])
        )
        
        # Mostra anche batch sizes
        batch_sizes = self.config['system']['download']['batch_size']
        for tf, size in batch_sizes.items():
            table.add_row(
                f"Batch Size {tf}",
                str(size)
            )
        
        self.console.print(table)
        
    def _select_symbols(self) -> List[str]:
        """
        Permette la selezione dei simboli.
        
        Returns:
            Lista dei simboli selezionati
        """
        self.console.print("\n[bold blue]Selezione Simboli[/bold blue]")
        
        available_symbols = self.config['portfolio']['symbols']
        selected_symbols = []
        
        for symbol in available_symbols:
            if Confirm.ask(f"Includere {symbol}?", default=True):
                selected_symbols.append(symbol)
                
        return selected_symbols
        
    def _select_timeframes(self) -> List[str]:
        """
        Permette la selezione dei timeframes.
        
        Returns:
            Lista dei timeframes selezionati
        """
        self.console.print("\n[bold blue]Selezione Timeframes[/bold blue]")
        
        available_timeframes = self.config['portfolio']['timeframes']
        selected_timeframes = []
        
        for tf in available_timeframes:
            if Confirm.ask(f"Includere {tf}?", default=True):
                selected_timeframes.append(tf)
                
        return selected_timeframes
        
    def _select_period(self) -> int:
        """
        Permette la selezione del periodo di download.
        
        Returns:
            Numero di giorni da scaricare
        """
        self.console.print("\n[bold blue]Selezione Periodo[/bold blue]")
        
        days = Prompt.ask(
            "Giorni da scaricare",
            default="365"
        )
        
        try:
            days = int(days)
            if days <= 0:
                return 0
            return days
        except ValueError:
            return 0
            
    def _confirm_config(
        self,
        symbols: List[str],
        timeframes: List[str],
        days: int
    ) -> bool:
        """
        Chiede conferma della configurazione.
        
        Args:
            symbols: Simboli selezionati
            timeframes: Timeframes selezionati
            days: Giorni da scaricare
            
        Returns:
            True se confermato
        """
        self.console.print("\n[bold blue]Riepilogo Download[/bold blue]")
        
        table = Table(show_header=True)
        table.add_column("Parametro")
        table.add_column("Valore")
        
        table.add_row("Simboli", ", ".join(symbols))
        table.add_row("Timeframes", ", ".join(timeframes))
        table.add_row("Periodo", f"{days} giorni")
        
        # Mostra batch sizes per i timeframes selezionati
        batch_sizes = self.config['system']['download']['batch_size']
        for tf in timeframes:
            if tf in batch_sizes:
                table.add_row(
                    f"Batch Size {tf}",
                    str(batch_sizes[tf])
                )
        
        self.console.print(table)
        
        return Confirm.ask("\nConfermi il download?", default=True)
        
    def _progress_callback(
        self,
        description: str,
        completed: int,
        total: int
    ) -> None:
        """
        Callback per aggiornare la barra di progresso.
        
        Args:
            description: Descrizione operazione
            completed: Tasks completati
            total: Totale tasks
        """
        if self.progress and self.task_id is not None:
            self.progress.update(
                self.task_id,
                description=description,
                completed=completed,
                total=total
            )
        
    async def _execute_download(
        self,
        symbols: List[str],
        timeframes: List[str],
        days: int
    ) -> None:
        """
        Esegue il download con barra di progresso.
        
        Args:
            symbols: Simboli da scaricare
            timeframes: Timeframes da scaricare
            days: Giorni da scaricare
        """
        self.console.print("\n[bold blue]Download in corso...[/bold blue]")
        
        # Crea configurazione
        download_config = DownloadConfig(
            exchanges=[{
                'id': 'binance',
                'config': {
                    'apiKey': self.config['networks']['binance']['api_key'],
                    'secret': self.config['networks']['binance']['api_secret']
                }
            }],
            symbols=symbols,
            timeframes=timeframes,
            start_date=datetime.utcnow() - timedelta(days=days),
            validate_data=True,
            update_metrics=True,
            max_concurrent=2,
            batch_size=self.config['system']['download']['batch_size'],
            progress_callback=self._progress_callback
        )
        
        # Crea progress bar
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            transient=True  # Rimuove la barra quando completata
        )
        
        # Esegue download
        async with get_session() as session:
            downloader = DataDownloader(session, download_config)
            
            with Live(progress, refresh_per_second=10):
                self.progress = progress
                self.task_id = progress.add_task(
                    "Download in corso...",
                    total=len(symbols) * len(timeframes)
                )
                
                try:
                    # Esegue download
                    stats = await downloader.download_data()
                    
                    # Mostra statistiche
                    self._show_stats(stats)
                    
                    # Mostra risultato
                    self.console.print("\n[green]Risultato: Download completato con successo[/green]")
                    
                except Exception as e:
                    self.console.print(f"\n[red]Errore durante il download: {str(e)}[/red]")
                finally:
                    self.progress = None
                    self.task_id = None
        
    def _show_stats(self, stats: DownloadStats) -> None:
        """
        Mostra statistiche del download.
        
        Args:
            stats: Statistiche da mostrare
        """
        self.console.print("\n[bold blue]Statistiche Download[/bold blue]")
        
        table = Table(show_header=True)
        table.add_column("Metrica")
        table.add_column("Valore")
        
        table.add_row("Candele Totali", str(stats.total_candles))
        table.add_row("Candele Valide", str(stats.valid_candles))
        table.add_row("Candele Non Valide", str(stats.invalid_candles))
        table.add_row("Candele Mancanti", str(stats.missing_candles))
        table.add_row("Durata", f"{stats.duration:.1f} secondi")
        table.add_row(
            "Tasso Validazione",
            f"{stats.validation_rate*100:.1f}%"
        )
        
        self.console.print(table)
