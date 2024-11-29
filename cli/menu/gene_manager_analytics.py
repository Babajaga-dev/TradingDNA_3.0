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
from ..genes import (
    RSIGene, MovingAverageGene, MACDGene, BollingerGene,
    StochasticGene, ATRGene, VolumeGene, OBVGene, 
    VolatilityBreakoutGene, CandlestickGene
)
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
            Array numpy con i dati OHLC
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
                
            # Restituisce array OHLC completo
            return np.array([[d.open, d.high, d.low, d.close, d.volume] for d in data])
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
            'moving_average': MovingAverageGene,
            'macd': MACDGene,
            'bollinger': BollingerGene,
            'stochastic': StochasticGene,
            'atr': ATRGene,
            'volume': VolumeGene,
            'obv': OBVGene,
            'volatility_breakout': VolatilityBreakoutGene,
            'candlestick': CandlestickGene
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
            data = self.get_historical_data(pair, timeframe, days)
            if len(data) == 0:
                continue
                
            if len(data) < days:
                self.console.print(f"[yellow]Attenzione: recuperati solo {len(data)} giorni di dati[/yellow]")
                
            # Determina il minimo numero di punti dati necessari in base al tipo di gene
            if gene_type == 'macd':
                min_data_points = max(
                    int(float(gene.params['fast_period'])),
                    int(float(gene.params['slow_period'])),
                    int(float(gene.params['signal_period']))
                ) + 1
            elif gene_type == 'bollinger':
                min_data_points = int(float(gene.params['period'])) + 1
            elif gene_type == 'stochastic':
                min_data_points = max(
                    int(float(gene.params['k_period'])),
                    int(float(gene.params['d_period']))
                ) + 1
            elif gene_type == 'atr':
                min_data_points = int(float(gene.params['period'])) + 1
            elif gene_type == 'volume':
                min_data_points = int(float(gene.params['period'])) + 1
            elif gene_type == 'obv':
                min_data_points = int(float(gene.params['period'])) + 1
            elif gene_type == 'volatility_breakout':
                min_data_points = max(
                    int(float(gene.params['period'])),
                    int(float(gene.params['consolidation_periods']))
                ) + 1
            elif gene_type == 'candlestick':
                min_data_points = 3  # Servono almeno 3 candele per alcuni pattern
            else:
                min_data_points = int(float(gene.params.get('period', 14))) + 1
                
            # Calcola segnali
            signals = []
            for i in range(min_data_points, len(data) + 1):
                signal = gene.calculate_signal(data[:i])
                signals.append(signal)
                
            # Padding con zeri all'inizio per mantenere la lunghezza
            signals = [0] * (min_data_points - 1) + signals
            
            # Visualizza grafico
            plt.figure(figsize=(12, 6))
            
            # Subplot superiore per i prezzi e indicatori
            plt.subplot(2, 1, 1)
            plt.plot(data[:, 3], label='Prezzo', color='blue')  # Close price
            
            # Aggiungi indicatori specifici al grafico
            if gene_type == 'moving_average':
                ma = gene.calculate_ma(data[:, 3])  # Close price
                plt.plot(ma, label=f'{gene.params["type"]} ({gene.params["period"]})', linestyle='--')
            elif gene_type == 'macd':
                macd_line, signal_line, _ = gene.calculate_macd(data[:, 3])  # Close price
                plt.plot(macd_line, label='MACD Line', linestyle='--')
                plt.plot(signal_line, label='Signal Line', linestyle=':')
            elif gene_type == 'bollinger':
                middle_band, upper_band, lower_band = gene.calculate_bands(data[:, 3])  # Close price
                plt.plot(middle_band, label='Middle Band', linestyle='--')
                plt.plot(upper_band, label='Upper Band', linestyle=':')
                plt.plot(lower_band, label='Lower Band', linestyle=':')
            elif gene_type == 'stochastic':
                k_line, d_line = gene.calculate_stochastic(data[:, 1], data[:, 2], data[:, 3])  # High, Low, Close
                plt.plot(k_line, label='%K Line', linestyle='--')
                plt.plot(d_line, label='%D Line', linestyle=':')
            elif gene_type == 'atr':
                atr = gene.calculate_atr(data[:, 1], data[:, 2], data[:, 3])  # High, Low, Close
                plt.plot(atr, label='ATR', linestyle='--')
            elif gene_type == 'volume':
                volume_ma, volume_ratio = gene.calculate_volume_metrics(data[:, 4])  # Volume
                plt.subplot(2, 1, 1)  # Prezzo
                plt.plot(data[:, 3], label='Prezzo', color='blue')
                plt.legend()
                plt.grid(True)
                
                # Subplot centrale per il volume
                plt.subplot(3, 1, 2)
                plt.bar(range(len(data)), data[:, 4], label='Volume', alpha=0.3, color='gray')
                plt.plot(volume_ma, label=f'Volume MA ({gene.params["period"]})', color='orange')
                plt.legend()
                plt.grid(True)
                
                # Subplot inferiore per il volume ratio
                plt.subplot(3, 1, 3)
                plt.plot(volume_ratio, label='Volume Ratio', color='green')
                plt.axhline(y=float(gene.params['threshold']), color='r', linestyle='--', label='Threshold')
                plt.axhline(y=1/float(gene.params['threshold']), color='r', linestyle='--')
            elif gene_type == 'obv':
                obv, obv_ma = gene.calculate_obv(data[:, 3], data[:, 4])  # Close, Volume
                plt.subplot(2, 1, 1)  # Prezzo
                plt.plot(data[:, 3], label='Prezzo', color='blue')
                plt.legend()
                plt.grid(True)
                
                # Subplot inferiore per OBV
                plt.subplot(2, 1, 2)
                plt.plot(obv, label='OBV', color='purple')
                plt.plot(obv_ma, label=f'OBV MA ({gene.params["period"]})', color='orange', linestyle='--')
                plt.legend()
                plt.grid(True)
            elif gene_type == 'volatility_breakout':
                upper_band, lower_band = gene.calculate_volatility_bands(data[:, 1], data[:, 2], data[:, 3])  # High, Low, Close
                plt.plot(upper_band, label='Upper Band', linestyle='--', color='red')
                plt.plot(lower_band, label='Lower Band', linestyle='--', color='green')
                plt.fill_between(range(len(data)), upper_band, lower_band, alpha=0.1, color='gray')
            elif gene_type == 'candlestick':
                # Crea subplot per il grafico candlestick
                plt.subplot(2, 1, 1)
                
                # Plot candele
                for i in range(len(data)):
                    # Colori candele
                    color = 'green' if data[i, 3] > data[i, 0] else 'red'
                    
                    # Corpo candela
                    plt.plot([i, i], [data[i, 0], data[i, 3]], color=color, linewidth=3)
                    # Shadow superiore e inferiore
                    plt.plot([i, i], [data[i, 1], data[i, 2]], color=color, linewidth=1)
                    
                    # Evidenzia pattern riconosciuti
                    if i >= 2:  # Servono almeno 3 candele per alcuni pattern
                        # Doji
                        if gene.is_doji(data[i, 0], data[i, 1], data[i, 2], data[i, 3]):
                            plt.plot(i, data[i, 1], 'ko', markersize=8, label='Doji' if i == 2 else "")
                            
                        # Hammer/Hanging Man
                        hammer, hanging = gene.is_hammer(data[i, 0], data[i, 1], data[i, 2], data[i, 3])
                        if hammer or hanging:
                            plt.plot(i, data[i, 1], 'b^' if hammer else 'rv', markersize=8, 
                                   label='Hammer' if hammer and i == 2 else 'Hanging Man' if hanging and i == 2 else "")
                            
                        # Engulfing
                        if i > 0:
                            bull_eng, bear_eng = gene.is_engulfing(
                                data[i-1, 0], data[i-1, 3], data[i, 0], data[i, 3]
                            )
                            if bull_eng or bear_eng:
                                plt.plot(i, data[i, 1], 'g*' if bull_eng else 'r*', markersize=10,
                                       label='Bullish Engulfing' if bull_eng and i == 2 else 
                                             'Bearish Engulfing' if bear_eng and i == 2 else "")
                                
                        # Morning/Evening Star
                        morning, evening = gene.is_star(data, i)
                        if morning or evening:
                            plt.plot(i, data[i, 1], 'g^' if morning else 'rv', markersize=12,
                                   label='Morning Star' if morning and i == 2 else 
                                         'Evening Star' if evening and i == 2 else "")
                            
                        # Harami
                        if i > 0:
                            bull_harami, bear_harami = gene.is_harami(
                                data[i-1, 0], data[i-1, 3], data[i, 0], data[i, 3]
                            )
                            if bull_harami or bear_harami:
                                plt.plot(i, data[i, 1], 'gs' if bull_harami else 'rs', markersize=8,
                                       label='Bullish Harami' if bull_harami and i == 2 else 
                                             'Bearish Harami' if bear_harami and i == 2 else "")
                
                plt.legend(loc='upper left')
            
            plt.title(f'Test Gene {gene_type.upper()} - {pair} ({timeframe})')
            plt.legend()
            plt.grid(True)
            
            if gene_type != 'volume':
                # Subplot inferiore per i segnali (non per volume che ha già 3 subplot)
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
                'Fitness score': gene.evaluate(data)
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
