"""
Gene Manager Analytics
--------------------
Gestisce le funzionalità di test e analisi dei geni del trading system.
"""

import numpy as np
from typing import Dict, List, Tuple
from pathlib import Path
import matplotlib.pyplot as plt
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from data.database.models.models import (
    get_session, Symbol, MarketData
)
from ..genes import RSIGene, MovingAverageGene
from .gene_manager_base import GeneManagerBase

class GeneManagerAnalytics(GeneManagerBase):
    """Gestore delle operazioni di test e analisi dei geni."""

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
