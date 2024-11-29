"""
Trading Simulator
--------------
Simulazione del trading basata sui segnali.
"""

from typing import Dict, List, Union
import time
from datetime import datetime
from data.database.models.models import MarketData
from cli.logger.log_manager import get_logger

# Setup logger
logger = get_logger('trading_simulator')

class TradingSimulator:
    """Simula il trading basato sui segnali."""
    
    def __init__(self):
        """Inizializza il simulator."""
        print("[DEBUG] TradingSimulator inizializzato")
        
    def simulate_trading(
        self, 
        signals: Dict, 
        market_data: List[Union[MarketData, Dict]]
    ) -> List[Dict]:
        """Simula il trading usando i segnali."""
        performance = []
        position = None
        entry_price = 0.0
        
        try:
            print("\n[DEBUG] === INIZIO SIMULAZIONE TRADING ===")
            print(f"[DEBUG] Numero segnali disponibili: {len(signals)}")
            print(f"[DEBUG] Numero candele disponibili: {len(market_data)}")
            
            start_time = time.time()
            trades_count = {'long': 0, 'short': 0}
            current_pnl = 0.0
            
            print("[DEBUG] Inizio elaborazione candele...")
            for i, data in enumerate(market_data, 1):
                # Gestisce sia oggetti MarketData che dizionari
                timestamp = data['timestamp'] if isinstance(data, dict) else data.timestamp
                close = data['close'] if isinstance(data, dict) else data.close
                
                signal = signals.get(timestamp, 0.0)
                
                print(f"\n[DEBUG] Candela {i}/{len(market_data)} - {timestamp}")
                print(f"[DEBUG] Prezzo: {close:.2f}, Segnale: {signal:.2f}")
                print(f"[DEBUG] Posizione corrente: {position}")
                
                # Logica trading semplificata
                if position is None and signal > 0.5:
                    # Apri long
                    print(f"[DEBUG] Apertura LONG a {close:.2f}")
                    position = 'long'
                    entry_price = close
                    trades_count['long'] += 1
                    
                elif position is None and signal < -0.5:
                    # Apri short
                    print(f"[DEBUG] Apertura SHORT a {close:.2f}")
                    position = 'short'
                    entry_price = close
                    trades_count['short'] += 1
                    
                elif position == 'long' and signal < 0:
                    # Chiudi long
                    print(f"[DEBUG] Chiusura LONG: Entry={entry_price:.2f}, Exit={close:.2f}")
                    pnl = (close - entry_price) / entry_price
                    current_pnl += pnl
                    print(f"[DEBUG] PnL operazione: {pnl:.2%}")
                    
                    performance.append({
                        'timestamp': timestamp,
                        'type': 'long',
                        'entry': entry_price,
                        'exit': close,
                        'pnl': pnl
                    })
                    position = None
                    
                elif position == 'short' and signal > 0:
                    # Chiudi short
                    print(f"[DEBUG] Chiusura SHORT: Entry={entry_price:.2f}, Exit={close:.2f}")
                    pnl = (entry_price - close) / entry_price
                    current_pnl += pnl
                    print(f"[DEBUG] PnL operazione: {pnl:.2%}")
                    
                    performance.append({
                        'timestamp': timestamp,
                        'type': 'short',
                        'entry': entry_price,
                        'exit': close,
                        'pnl': pnl
                    })
                    position = None
                else:
                    print("[DEBUG] Nessuna azione per questa candela")
            
            # Statistiche finali
            sim_time = time.time() - start_time
            total_trades = len(performance)
            avg_pnl = current_pnl / total_trades if total_trades > 0 else 0
            
            print("\n[DEBUG] === FINE SIMULAZIONE TRADING ===")
            print(f"[DEBUG] Tempo simulazione: {sim_time:.2f}s")
            print(f"[DEBUG] Trade totali: {total_trades}")
            print(f"[DEBUG] - Long: {trades_count['long']}")
            print(f"[DEBUG] - Short: {trades_count['short']}")
            print(f"[DEBUG] PnL totale: {current_pnl:.2%}")
            print(f"[DEBUG] PnL medio per trade: {avg_pnl:.2%}")
            
            return performance
            
        except Exception as e:
            print(f"[DEBUG] ERRORE simulazione trading: {str(e)}")
            logger.error(f"Errore simulazione trading: {str(e)}")
            return []
