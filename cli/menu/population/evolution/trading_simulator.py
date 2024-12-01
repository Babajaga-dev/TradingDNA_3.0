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
from cli.config.config_loader import get_config_loader

class TradingSimulator:
    """Simula il trading basato sui segnali."""
    
    def __init__(self):
        """Inizializza il simulator."""
        self.logger = get_logger('trading_simulator')
        self.config = get_config_loader()
        
        # Carica configurazione risk management
        self.risk_config = self.config.get_value('portfolio.risk_management', {})
        
    def simulate_trading(
        self, 
        signals: Dict, 
        market_data: List[Union[MarketData, Dict]]
    ) -> List[Dict]:
        """Simula il trading usando i segnali."""
        performance = []
        position = None
        entry_price = 0.0
        stop_loss = 0.0
        take_profit = 0.0
        trailing_stop = 0.0
        
        # Carica configurazioni da portfolio.yaml
        signal_threshold = self.risk_config.get('signal_threshold', 0.2)
        stop_loss_pct = self.risk_config.get('stop_loss_pct', 0.02)
        take_profit_pct = self.risk_config.get('take_profit_pct', 0.04)
        max_position_size = self.risk_config.get('max_position_size', 0.1)
        trailing_stop_pct = self.risk_config.get('trailing_stop_pct', 0.01)
        equity = self.risk_config.get('initial_capital', 1000.0)
        commission = self.risk_config.get('commission', 0.001)
        slippage = self.risk_config.get('slippage', 0.001)
        
        max_equity = equity
        
        try:
            if not market_data or not signals:
                self.logger.error("Dati di mercato o segnali vuoti")
                return []
            
            start_time = time.time()
            trades_count = {'long': 0, 'short': 0}
            current_pnl = 0.0
            
            # Log iniziale
            self.logger.debug(f"Inizio simulazione con {len(market_data)} candele e {len(signals)} segnali")
            self.logger.debug(f"Configurazione: threshold={signal_threshold}, SL={stop_loss_pct*100}%, TP={take_profit_pct*100}%")
            
            for i, data in enumerate(market_data):
                timestamp = data['timestamp'] if isinstance(data, dict) else data.timestamp
                close = float(data['close'] if isinstance(data, dict) else data.close)
                high = float(data['high'] if isinstance(data, dict) else data.high)
                low = float(data['low'] if isinstance(data, dict) else data.low)
                
                signal = signals.get(timestamp, 0.0)
                
                # Log segnali significativi
                if abs(signal) > signal_threshold:
                    self.logger.debug(f"Segnale significativo: {signal:.3f} a {timestamp}")
                
                # Aggiorna trailing stop se posizione aperta
                if position:
                    if position == 'long' and close > entry_price:
                        new_trailing_stop = close * (1 - trailing_stop_pct)
                        if new_trailing_stop > trailing_stop:
                            self.logger.debug(f"Aggiornamento trailing stop long: {trailing_stop:.2f} -> {new_trailing_stop:.2f}")
                            trailing_stop = new_trailing_stop
                    elif position == 'short' and close < entry_price:
                        new_trailing_stop = close * (1 + trailing_stop_pct)
                        trailing_stop = min(trailing_stop, new_trailing_stop) if trailing_stop > 0 else new_trailing_stop
                        if trailing_stop != new_trailing_stop:
                            self.logger.debug(f"Aggiornamento trailing stop short: {trailing_stop:.2f}")
                
                # Verifica condizioni di chiusura
                if position == 'long':
                    close_reason = None
                    if low <= stop_loss:
                        close_reason = 'stop_loss'
                    elif high >= take_profit:
                        close_reason = 'take_profit'
                    elif low <= trailing_stop:
                        close_reason = 'trailing_stop'
                    elif signal < -signal_threshold:
                        close_reason = 'signal'
                        
                    if close_reason:
                        # Applica commissioni e slippage
                        exit_price = close * (1 - commission - slippage)
                        pnl = (exit_price - entry_price) / entry_price
                        current_pnl += pnl
                        equity *= (1 + pnl * max_position_size)
                        max_equity = max(max_equity, equity)
                        
                        self.logger.debug(f"Chiusura long per {close_reason}: entry={entry_price:.2f}, exit={exit_price:.2f}, pnl={pnl*100:.2f}%")
                        
                        performance.append({
                            'timestamp': timestamp,
                            'type': 'long',
                            'entry': entry_price,
                            'exit': exit_price,
                            'pnl': pnl,
                            'reason': close_reason
                        })
                        position = None
                        
                elif position == 'short':
                    close_reason = None
                    if high >= stop_loss:
                        close_reason = 'stop_loss'
                    elif low <= take_profit:
                        close_reason = 'take_profit'
                    elif high >= trailing_stop:
                        close_reason = 'trailing_stop'
                    elif signal > signal_threshold:
                        close_reason = 'signal'
                        
                    if close_reason:
                        # Applica commissioni e slippage
                        exit_price = close * (1 + commission + slippage)
                        pnl = (entry_price - exit_price) / entry_price
                        current_pnl += pnl
                        equity *= (1 + pnl * max_position_size)
                        max_equity = max(max_equity, equity)
                        
                        self.logger.debug(f"Chiusura short per {close_reason}: entry={entry_price:.2f}, exit={exit_price:.2f}, pnl={pnl*100:.2f}%")
                        
                        performance.append({
                            'timestamp': timestamp,
                            'type': 'short',
                            'entry': entry_price,
                            'exit': exit_price,
                            'pnl': pnl,
                            'reason': close_reason
                        })
                        position = None
                
                # Apri nuove posizioni solo se non ne abbiamo già una
                if position is None:
                    if signal > signal_threshold:
                        # Applica commissioni e slippage per entry
                        entry_price = close * (1 + commission + slippage)
                        position = 'long'
                        stop_loss = entry_price * (1 - stop_loss_pct)
                        take_profit = entry_price * (1 + take_profit_pct)
                        trailing_stop = stop_loss
                        trades_count['long'] += 1
                        self.logger.debug(f"Apertura long: prezzo={entry_price:.2f}, sl={stop_loss:.2f}, tp={take_profit:.2f}")
                        
                    elif signal < -signal_threshold:
                        # Applica commissioni e slippage per entry
                        entry_price = close * (1 - commission - slippage)
                        position = 'short'
                        stop_loss = entry_price * (1 + stop_loss_pct)
                        take_profit = entry_price * (1 - take_profit_pct)
                        trailing_stop = stop_loss
                        trades_count['short'] += 1
                        self.logger.debug(f"Apertura short: prezzo={entry_price:.2f}, sl={stop_loss:.2f}, tp={take_profit:.2f}")
            
            # Chiudi posizione aperta alla fine del periodo
            if position:
                # Applica commissioni e slippage per chiusura finale
                exit_price = close * (1 - commission - slippage) if position == 'long' else close * (1 + commission + slippage)
                pnl = ((exit_price - entry_price) / entry_price) if position == 'long' else ((entry_price - exit_price) / entry_price)
                current_pnl += pnl
                equity *= (1 + pnl * max_position_size)
                max_equity = max(max_equity, equity)
                
                self.logger.debug(f"Chiusura {position} a fine periodo: entry={entry_price:.2f}, exit={exit_price:.2f}, pnl={pnl*100:.2f}%")
                
                performance.append({
                    'timestamp': timestamp,
                    'type': position,
                    'entry': entry_price,
                    'exit': exit_price,
                    'pnl': pnl,
                    'reason': 'period_end'
                })
            
            # Aggiungi statistiche finali
            total_trades = len(performance)
            if total_trades > 0:
                win_trades = sum(1 for t in performance if t['pnl'] > 0)
                win_rate = win_trades / total_trades
                avg_win = sum(t['pnl'] for t in performance if t['pnl'] > 0) / win_trades if win_trades > 0 else 0
                avg_loss = sum(t['pnl'] for t in performance if t['pnl'] <= 0) / (total_trades - win_trades) if (total_trades - win_trades) > 0 else 0
                
                self.logger.debug(f"Performance finale: trades={total_trades}, win_rate={win_rate*100:.1f}%, "
                           f"avg_win={avg_win*100:.1f}%, avg_loss={avg_loss*100:.1f}%")
                
                performance.append({
                    'summary': {
                        'total_trades': total_trades,
                        'win_rate': win_rate,
                        'avg_win': avg_win,
                        'avg_loss': avg_loss,
                        'final_equity': equity,
                        'max_drawdown': (max_equity - equity) / max_equity if max_equity > 0 else 0,
                        'trades_distribution': trades_count
                    }
                })
            else:
                self.logger.warning("Nessun trade eseguito durante la simulazione")
            
            return performance
            
        except Exception as e:
            self.logger.error(f"Errore simulazione trading: {str(e)}")
            return []
