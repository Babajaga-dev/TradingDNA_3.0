"""
Data Downloader
-------------
Sistema di download dati da exchange.
Gestisce download asincrono e validazione.
"""

import asyncio
import logging
import sys
import platform
import json
from typing import Dict, List, Any, Optional, Set, Tuple, Callable
from datetime import datetime, timedelta
import pytz
from dataclasses import dataclass
import time
import numpy as np
from scipy import stats

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError

from ..database.session_manager import DBSessionManager
from ..database.models import (
    Exchange, Symbol, MarketData,
    initialize_database
)
from ..connectors import (
    BaseConnector,
    create_connector,
    RetryWithCircuitBreaker
)
from cli.config import get_config_loader

def setup_event_loop():
    """Configura il loop di eventi appropriato per il sistema operativo."""
    if platform.system().lower() == 'windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Configura il loop di eventi all'importazione del modulo
setup_event_loop()

# Inizializza il database
initialize_database()

def convert_to_local_time(utc_timestamp: float) -> datetime:
    """
    Converte un timestamp UTC in ora locale.
    
    Args:
        utc_timestamp: Timestamp UTC in millisecondi
        
    Returns:
        datetime: Data e ora in fuso orario locale
    """
    utc_dt = datetime.fromtimestamp(utc_timestamp / 1000, tz=pytz.UTC)
    local_tz = pytz.timezone('Europe/Rome')
    local_dt = utc_dt.astimezone(local_tz)
    return local_dt

@dataclass
class DownloadConfig:
    """Configurazione download."""
    exchanges: List[Dict[str, Any]]
    symbols: List[str]
    timeframes: List[str]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    validate_data: bool = True
    update_metrics: bool = True
    max_concurrent: int = 2
    batch_size: Optional[Dict[str, int]] = None
    progress_callback: Optional[Callable[[str, int, int], None]] = None

class DownloadStats:
    """Statistiche download."""
    
    def __init__(self):
        self.total_candles = 0
        self.valid_candles = 0
        self.invalid_candles = 0
        self.missing_candles = 0
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        
    def update(self, total: int, valid: int, invalid: int, missing: int):
        """Aggiorna statistiche."""
        self.total_candles += total
        self.valid_candles += valid
        self.invalid_candles += invalid
        self.missing_candles += missing
        
    def complete(self):
        """Completa download."""
        self.end_time = datetime.utcnow()
        
    @property
    def duration(self) -> float:
        """Calcola durata download."""
        if not self.end_time:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()
        
    @property
    def validation_rate(self) -> float:
        """Calcola tasso validazione."""
        if self.total_candles == 0:
            return 0.0
        return self.valid_candles / self.total_candles

class DataDownloader:
    """Downloader dati da exchange."""
    
    def __init__(self, config: DownloadConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.stats = DownloadStats()
        self.connectors: Dict[str, BaseConnector] = {}
        self._exchange_map: Dict[int, str] = {}
        self.db = DBSessionManager()
        
        system_config = get_config_loader().config
        self.batch_sizes = system_config['system']['download']['batch_size']
        
    async def setup(self):
        """Setup iniziale."""
        try:
            for exchange in self.config.exchanges:
                self.logger.info(f"Creazione connettore per {exchange['id']}...")
                connector = await create_connector(exchange['id'], exchange['config'])
                self.connectors[exchange['id']] = connector
                
            for exchange_id, connector in self.connectors.items():
                self.logger.info(f"Verifica simboli su {exchange_id}...")
                symbols = await connector.get_symbols()
                unsupported = set(self.config.symbols) - set(symbols)
                if unsupported:
                    self.logger.warning(
                        f"Simboli non supportati su {exchange_id}: {', '.join(unsupported)}"
                    )
        except Exception as e:
            self.logger.error(f"Errore durante il setup: {str(e)}")
            raise

    async def _download_batch(
        self,
        connector: BaseConnector,
        symbol: str,
        timeframe: str,
        start_ts: int,
        end_ts: int,
        batch_size: int
    ) -> List[List[float]]:
        """Scarica un batch di candele."""
        try:
            candles = await connector.fetch_ohlcv(
                symbol,
                timeframe,
                start_ts,
                batch_size
            )
            return [c for c in candles if c[0] <= end_ts]
        except Exception as e:
            self.logger.error(f"Errore download batch {symbol} {timeframe}: {str(e)}")
            return []

    def _validate_candles(
        self,
        candles: List[List[float]],
        exchange_id: int,
        symbol: str,
        timeframe: str
    ) -> Tuple[List[List[float]], Tuple[int, int, int]]:
        """Valida candele."""
        valid_candles = []
        valid = invalid = missing = 0
        
        timestamps = [c[0] for c in candles]
        if timestamps:
            exchange_name = self._exchange_map[exchange_id]
            expected = set(range(
                min(timestamps),
                max(timestamps) + 1,
                self.connectors[exchange_name].parse_timeframe(timeframe)
            ))
            actual = set(timestamps)
            missing = len(expected - actual)
        
        for candle in candles:
            if self._is_valid_candle(candle):
                valid_candles.append(candle)
                valid += 1
            else:
                invalid += 1
                
        return valid_candles, (valid, invalid, missing)
        
    def _is_valid_candle(self, candle: List[float]) -> bool:
        """Valida una candela."""
        try:
            if not candle[0] or candle[0] <= 0:
                return False
                
            if any(p <= 0 for p in candle[1:5]):
                return False
                
            open_price, high, low, close = candle[1:5]
            if not (low <= open_price <= high and low <= close <= high):
                return False
                
            if candle[5] < 0:
                return False
                
            return True
            
        except (IndexError, TypeError):
            return False

    def _get_or_create_exchange(self, exchange_id: str) -> Exchange:
        """Ottiene o crea un exchange."""
        with self.db.session() as session:
            stmt = text("SELECT id FROM exchanges WHERE name = :name")
            result = session.execute(stmt, {"name": exchange_id}).scalar_one_or_none()
            
            if not result:
                exchange_obj = Exchange(name=exchange_id)
                session.add(exchange_obj)
                session.flush()
                session.refresh(exchange_obj)
                return exchange_obj
            
            return session.get(Exchange, result)

    def _get_or_create_symbol(self, exchange_id: int, symbol: str) -> Symbol:
        """Ottiene o crea un simbolo."""
        with self.db.session() as session:
            stmt = text("""
                SELECT id FROM symbols 
                WHERE exchange_id = :exchange_id AND name = :name
            """)
            result = session.execute(stmt, {
                "exchange_id": exchange_id,
                "name": symbol
            }).scalar_one_or_none()
            
            if not result:
                if symbol.endswith('USDT'):
                    base = symbol[:-4]
                    quote = 'USDT'
                elif symbol.endswith('BTC'):
                    base = symbol[:-3]
                    quote = 'BTC'
                elif symbol.endswith('ETH'):
                    base = symbol[:-3]
                    quote = 'ETH'
                else:
                    quote = symbol[-4:]
                    base = symbol[:-4]
                    
                symbol_obj = Symbol(
                    exchange_id=exchange_id,
                    name=symbol,
                    base_asset=base,
                    quote_asset=quote
                )
                session.add(symbol_obj)
                session.flush()
                session.refresh(symbol_obj)
                return symbol_obj
            
            return session.get(Symbol, result)

    def _save_market_data(self, exchange_id: int, symbol_id: int,
                         timeframe: str, candles: List[List[float]]):
        """Salva i dati di mercato usando UPSERT."""
        try:
            with self.db.session() as session:
                for candle in candles:
                    local_timestamp = convert_to_local_time(candle[0])
                    
                    # Prepara i dati per l'inserimento/aggiornamento
                    data = {
                        'exchange_id': exchange_id,
                        'symbol_id': symbol_id,
                        'timeframe': timeframe,
                        'timestamp': local_timestamp,
                        'open': candle[1],
                        'high': candle[2],
                        'low': candle[3],
                        'close': candle[4],
                        'volume': candle[5],
                        'updated_at': datetime.utcnow(),
                        'is_valid': True
                    }
                    
                    # Crea la query UPSERT per PostgreSQL
                    stmt = text("""
                        INSERT INTO market_data (
                            exchange_id, symbol_id, timeframe, timestamp,
                            open, high, low, close, volume, updated_at, is_valid
                        ) VALUES (
                            :exchange_id, :symbol_id, :timeframe, :timestamp,
                            :open, :high, :low, :close, :volume, :updated_at, :is_valid
                        )
                        ON CONFLICT (exchange_id, symbol_id, timeframe, timestamp)
                        DO UPDATE SET
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            volume = EXCLUDED.volume,
                            updated_at = EXCLUDED.updated_at,
                            is_valid = EXCLUDED.is_valid
                    """)
                    
                    session.execute(stmt, data)
            
        except Exception as e:
            self.logger.error(f"Errore salvataggio dati: {str(e)}")
            raise

    async def _process_symbol_timeframe(self, exchange_obj: Exchange, connector: BaseConnector,
                                      symbol: str, timeframe: str) -> Tuple[int, int, int, int]:
        """Processa un singolo simbolo e timeframe."""
        try:
            self.logger.info(f"Download {symbol} {timeframe}")
            
            symbol_obj = self._get_or_create_symbol(exchange_obj.id, symbol)
            
            with self.db.session() as session:
                stmt = text("""
                    SELECT timestamp FROM market_data 
                    WHERE exchange_id = :exchange_id 
                    AND symbol_id = :symbol_id 
                    AND timeframe = :timeframe 
                    ORDER BY timestamp DESC LIMIT 1
                """)
                last_date = session.execute(stmt, {
                    "exchange_id": exchange_obj.id,
                    "symbol_id": symbol_obj.id,
                    "timeframe": timeframe
                }).scalar_one_or_none()
            
            start_date = self.config.start_date
            if not start_date:
                if last_date and (datetime.utcnow() - last_date).days <= 7:
                    start_date = last_date
                else:
                    start_date = datetime.utcnow() - timedelta(days=365)
            
            end_date = self.config.end_date or datetime.utcnow()
            
            start_ts = int(start_date.timestamp() * 1000)
            end_ts = int(end_date.timestamp() * 1000)
            
            batch_size = self.batch_sizes[timeframe]
            
            timeframe_ms = connector.parse_timeframe(timeframe)
            total_candles = (end_ts - start_ts) // timeframe_ms
            num_batches = (total_candles + batch_size - 1) // batch_size
            
            all_candles = []
            for i in range(num_batches):
                batch_start = start_ts + (i * batch_size * timeframe_ms)
                batch_end = min(batch_start + (batch_size * timeframe_ms), end_ts)
                
                batch = await self._download_batch(
                    connector,
                    symbol,
                    timeframe,
                    batch_start,
                    batch_end,
                    batch_size
                )
                all_candles.extend(batch)
                
                if self.config.progress_callback:
                    self.config.progress_callback(
                        f"Download {symbol} {timeframe} batch {i+1}/{num_batches}",
                        i+1,
                        num_batches
                    )
                
                await asyncio.sleep(0.5)
            
            total = len(all_candles)
            valid = invalid = missing = 0
            
            if self.config.validate_data:
                batch, stats = self._validate_candles(
                    all_candles, exchange_obj.id, symbol, timeframe
                )
                valid, invalid, missing = stats
                all_candles = batch
            else:
                valid = total
            
            if all_candles:
                self._save_market_data(
                    exchange_obj.id,
                    symbol_obj.id,
                    timeframe,
                    all_candles
                )
            
            return total, valid, invalid, missing
            
        except Exception as e:
            self.logger.error(f"Errore download {symbol} {timeframe}: {str(e)}")
            raise
            
    async def download_data(self) -> DownloadStats:
        """Esegue download dati."""
        try:
            self.logger.info("Inizializzazione download...")
            await self.setup()
            
            total_tasks = len(self.config.symbols) * len(self.config.timeframes)
            completed_tasks = 0
            
            if self.config.progress_callback:
                self.config.progress_callback(
                    "Inizializzazione download...",
                    completed_tasks,
                    total_tasks
                )
            
            for exchange in self.config.exchanges:
                exchange_id = exchange['id']
                exchange_obj = self._get_or_create_exchange(exchange_id)
                self._exchange_map[exchange_obj.id] = exchange_id
                
                for symbol in self.config.symbols:
                    for timeframe in self.config.timeframes:
                        try:
                            result = await self._process_symbol_timeframe(
                                exchange_obj,
                                self.connectors[exchange_id],
                                symbol,
                                timeframe
                            )
                            
                            self.stats.update(*result)
                            completed_tasks += 1
                            
                            if self.config.progress_callback:
                                self.config.progress_callback(
                                    "Download in corso...",
                                    completed_tasks,
                                    total_tasks
                                )
                                
                        except Exception as e:
                            self.logger.error(f"Errore durante il download di {symbol} {timeframe}: {str(e)}")
                            continue
            
            if self.config.update_metrics:
                self.logger.info("Aggiornamento metriche...")
                self._update_metrics()
            
            self.stats.complete()
            self.logger.info("Download completato.")
            return self.stats
            
        except Exception as e:
            self.logger.error(f"Errore durante il download: {str(e)}")
            raise
        finally:
            for connector in self.connectors.values():
                await connector.close()
                
    def _update_metrics(self):
        """Aggiorna metriche di performance e rischio."""
        try:
            with self.db.session() as session:
                stmt = text("""
                    SELECT * FROM market_data 
                    ORDER BY exchange_id, symbol_id, timeframe, timestamp
                """)
                result = session.execute(stmt)
                market_data = result.fetchall()
                
                groups: Dict[Tuple[int, int, str], List[Any]] = {}
                for data in market_data:
                    key = (data.exchange_id, data.symbol_id, data.timeframe)
                    if key not in groups:
                        groups[key] = []
                    groups[key].append(data)
                
                for (exchange_id, symbol_id, timeframe), data in groups.items():
                    if len(data) < 2:
                        continue
                        
                    prices = [d.close for d in data]
                    volumes = [d.volume for d in data]
                    returns = [
                        (data[i].close - data[i-1].close) / data[i-1].close
                        for i in range(1, len(data))
                    ]
                    
                    # Calcola metriche di performance
                    total_return = (prices[-1] / prices[0]) - 1
                    annualized_return = ((1 + total_return) ** (252 / len(returns))) - 1
                    volatility = np.std(returns) * np.sqrt(252)
                    sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) != 0 else 0
                    
                    # Calcola metriche di rischio
                    var_95 = np.percentile(returns, 5)
                    var_99 = np.percentile(returns, 1)
                    es_95 = np.mean([r for r in returns if r <= var_95])
                    es_99 = np.mean([r for r in returns if r <= var_99])
                    
                    # Calcola drawdown
                    cumulative = np.cumprod(1 + np.array(returns))
                    running_max = np.maximum.accumulate(cumulative)
                    drawdowns = cumulative / running_max - 1
                    max_drawdown = float(np.min(drawdowns))
                    
                    # Prepara i dizionari delle metriche
                    metrics = {
                        'performance': {
                            'total_return': float(total_return),
                            'annualized_return': float(annualized_return),
                            'sharpe_ratio': float(sharpe_ratio),
                            'volatility': float(volatility)
                        },
                        'risk': {
                            'value_at_risk_95': float(var_95),
                            'value_at_risk_99': float(var_99),
                            'expected_shortfall_95': float(es_95),
                            'expected_shortfall_99': float(es_99),
                            'max_drawdown': float(max_drawdown)
                        }
                    }
                    
                    indicators = {}  # Placeholder per futuri indicatori tecnici
                    
                    # Aggiorna il database
                    stmt = text("""
                        UPDATE market_data 
                        SET market_metrics = cast(:metrics as jsonb),
                            technical_indicators = cast(:indicators as jsonb)
                        WHERE id = :id
                    """)
                    
                    session.execute(stmt, {
                        'id': data[-1].id,
                        'metrics': json.dumps(metrics),
                        'indicators': json.dumps(indicators)
                    })
                
                session.commit()
                
        except SQLAlchemyError as e:
            self.logger.error(f"Errore aggiornamento metriche: {str(e)}")
            raise
