"""
Data Downloader
-------------
Sistema di download dati da exchange.
Gestisce download asincrono e validazione.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..database.models import (
    Exchange, Symbol, MarketData,
    PerformanceMetrics, RiskMetrics
)
from ..connectors import (
    BaseConnector,
    create_connector,
    RetryWithCircuitBreaker
)

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
    max_concurrent: int = 5
    batch_size: int = 1000

class DownloadStats:
    """Statistiche download."""
    
    def __init__(self):
        self.total_candles = 0
        self.valid_candles = 0
        self.invalid_candles = 0
        self.missing_candles = 0
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        
    def update(
        self,
        total: int,
        valid: int,
        invalid: int,
        missing: int
    ):
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
    
    def __init__(
        self,
        session: AsyncSession,
        config: DownloadConfig
    ):
        """
        Inizializza il downloader.
        
        Args:
            session: Sessione database
            config: Configurazione download
        """
        self.session = session
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.stats = DownloadStats()
        self.connectors: Dict[str, BaseConnector] = {}
        
        # Semaforo per limitare concorrenza
        self._semaphore = asyncio.Semaphore(config.max_concurrent)
        
    async def setup(self):
        """Setup iniziale."""
        # Crea connettori
        for exchange in self.config.exchanges:
            connector = await create_connector(
                exchange['id'],
                exchange['config']
            )
            self.connectors[exchange['id']] = connector
            
        # Verifica simboli supportati
        for exchange_id, connector in self.connectors.items():
            symbols = await connector.get_symbols()
            unsupported = set(self.config.symbols) - set(symbols)
            if unsupported:
                self.logger.warning(
                    f"Simboli non supportati su {exchange_id}: "
                    f"{', '.join(unsupported)}"
                )
                
    async def download_data(self) -> DownloadStats:
        """
        Esegue download dati.
        
        Returns:
            Statistiche download
        """
        try:
            # Crea tasks
            tasks = []
            for exchange_id, connector in self.connectors.items():
                for symbol in self.config.symbols:
                    for timeframe in self.config.timeframes:
                        task = self._download_symbol_data(
                            connector,
                            exchange_id,
                            symbol,
                            timeframe
                        )
                        tasks.append(task)
                        
            # Esegui download
            results = await asyncio.gather(*tasks)
            
            # Aggiorna statistiche
            for result in results:
                self.stats.update(*result)
                
            # Aggiorna metriche
            if self.config.update_metrics:
                await self._update_metrics()
                
            return self.stats
            
        finally:
            # Chiudi connettori
            for connector in self.connectors.values():
                await connector.close()
                
    async def _download_symbol_data(
        self,
        connector: BaseConnector,
        exchange_id: str,
        symbol: str,
        timeframe: str
    ) -> Tuple[int, int, int, int]:
        """
        Scarica dati per un simbolo.
        
        Args:
            connector: Connettore exchange
            exchange_id: ID exchange
            symbol: Simbolo
            timeframe: Timeframe
            
        Returns:
            Tuple con statistiche (total, valid, invalid, missing)
        """
        async with self._semaphore:
            self.logger.info(
                f"Download {symbol} {timeframe} da {exchange_id}"
            )
            
            try:
                # Recupera date
                start_date = self.config.start_date
                if not start_date:
                    # Recupera ultima data
                    start_date = await self._get_last_date(
                        exchange_id, symbol, timeframe
                    )
                    
                end_date = self.config.end_date or datetime.utcnow()
                
                # Scarica dati
                candles = await connector.fetch_ohlcv(
                    symbol,
                    timeframe,
                    int(start_date.timestamp() * 1000),
                    None
                )
                
                # Valida e salva dati
                total = len(candles)
                valid = invalid = missing = 0
                
                for i in range(0, total, self.config.batch_size):
                    batch = candles[i:i + self.config.batch_size]
                    
                    if self.config.validate_data:
                        batch, stats = await self._validate_candles(
                            batch, exchange_id, symbol, timeframe
                        )
                        valid += stats[0]
                        invalid += stats[1]
                        missing += stats[2]
                    else:
                        valid = total
                        
                    await self._save_candles(
                        batch, exchange_id, symbol, timeframe
                    )
                    
                return total, valid, invalid, missing
                
            except Exception as e:
                self.logger.error(
                    f"Errore download {symbol} {timeframe}: {str(e)}"
                )
                return 0, 0, 0, 0
                
    async def _validate_candles(
        self,
        candles: List[List[float]],
        exchange_id: str,
        symbol: str,
        timeframe: str
    ) -> Tuple[List[List[float]], Tuple[int, int, int]]:
        """
        Valida candele.
        
        Args:
            candles: Lista candele
            exchange_id: ID exchange
            symbol: Simbolo
            timeframe: Timeframe
            
        Returns:
            Tuple con candele valide e statistiche
        """
        valid_candles = []
        valid = invalid = missing = 0
        
        # Verifica gaps
        timestamps = [c[0] for c in candles]
        expected = set(range(
            min(timestamps),
            max(timestamps) + 1,
            connector.parse_timeframe(timeframe)
        ))
        actual = set(timestamps)
        
        missing = len(expected - actual)
        
        # Valida singole candele
        for candle in candles:
            if self._is_valid_candle(candle):
                valid_candles.append(candle)
                valid += 1
            else:
                invalid += 1
                
        return valid_candles, (valid, invalid, missing)
        
    def _is_valid_candle(self, candle: List[float]) -> bool:
        """
        Valida una candela.
        
        Args:
            candle: Dati candela
            
        Returns:
            True se valida
        """
        # Verifica timestamp
        if not candle[0] or candle[0] <= 0:
            return False
            
        # Verifica prezzi
        if any(p <= 0 for p in candle[1:5]):
            return False
            
        # Verifica ordine prezzi
        open_price, high, low, close = candle[1:5]
        if not (low <= open_price <= high and
                low <= close <= high):
            return False
            
        # Verifica volume
        if candle[5] < 0:
            return False
            
        return True
        
    async def _save_candles(
        self,
        candles: List[List[float]],
        exchange_id: str,
        symbol: str,
        timeframe: str
    ):
        """
        Salva candele nel database.
        
        Args:
            candles: Lista candele
            exchange_id: ID exchange
            symbol: Simbolo
            timeframe: Timeframe
        """
        # Recupera o crea exchange
        exchange = await self._get_or_create_exchange(exchange_id)
        
        # Recupera o crea simbolo
        symbol_obj = await self._get_or_create_symbol(
            exchange.id, symbol
        )
        
        # Crea oggetti MarketData
        market_data = []
        for candle in candles:
            data = MarketData(
                exchange_id=exchange.id,
                symbol_id=symbol_obj.id,
                timestamp=datetime.fromtimestamp(candle[0] / 1000),
                timeframe=timeframe,
                open=candle[1],
                high=candle[2],
                low=candle[3],
                close=candle[4],
                volume=candle[5]
            )
            market_data.append(data)
            
        # Salva in batch
        self.session.add_all(market_data)
        await self.session.commit()
        
    async def _get_or_create_exchange(
        self,
        exchange_id: str
    ) -> Exchange:
        """
        Recupera o crea exchange.
        
        Args:
            exchange_id: ID exchange
            
        Returns:
            Oggetto Exchange
        """
        stmt = select(Exchange).where(Exchange.name == exchange_id)
        result = await self.session.execute(stmt)
        exchange = result.scalar_one_or_none()
        
        if not exchange:
            exchange = Exchange(name=exchange_id)
            self.session.add(exchange)
            await self.session.commit()
            
        return exchange
        
    async def _get_or_create_symbol(
        self,
        exchange_id: int,
        symbol: str
    ) -> Symbol:
        """
        Recupera o crea simbolo.
        
        Args:
            exchange_id: ID exchange
            symbol: Nome simbolo
            
        Returns:
            Oggetto Symbol
        """
        stmt = select(Symbol).where(
            Symbol.exchange_id == exchange_id,
            Symbol.name == symbol
        )
        result = await self.session.execute(stmt)
        symbol_obj = result.scalar_one_or_none()
        
        if not symbol_obj:
            base, quote = symbol.split('/')
            symbol_obj = Symbol(
                exchange_id=exchange_id,
                name=symbol,
                base_asset=base,
                quote_asset=quote
            )
            self.session.add(symbol_obj)
            await self.session.commit()
            
        return symbol_obj
        
    async def _get_last_date(
        self,
        exchange_id: str,
        symbol: str,
        timeframe: str
    ) -> datetime:
        """
        Recupera ultima data per simbolo.
        
        Args:
            exchange_id: ID exchange
            symbol: Simbolo
            timeframe: Timeframe
            
        Returns:
            Ultima data o data default
        """
        stmt = select(MarketData.timestamp).where(
            MarketData.exchange_id == exchange_id,
            MarketData.symbol == symbol,
            MarketData.timeframe == timeframe
        ).order_by(MarketData.timestamp.desc()).limit(1)
        
        result = await self.session.execute(stmt)
        last_date = result.scalar_one_or_none()
        
        if not last_date:
            # Default a 1 anno fa
            return datetime.utcnow() - timedelta(days=365)
            
        return last_date
        
    async def _update_metrics(self):
        """Aggiorna metriche di performance e rischio."""
        self.logger.info("Aggiornamento metriche...")
        
        # Recupera dati per calcolo metriche
        stmt = select(MarketData).order_by(
            MarketData.exchange_id,
            MarketData.symbol_id,
            MarketData.timeframe,
            MarketData.timestamp
        )
        result = await self.session.execute(stmt)
        market_data = result.scalars().all()
        
        # Raggruppa per simbolo/timeframe
        groups: Dict[Tuple[int, int, str], List[MarketData]] = {}
        for data in market_data:
            key = (data.exchange_id, data.symbol_id, data.timeframe)
            if key not in groups:
                groups[key] = []
            groups[key].append(data)
            
        # Calcola metriche per gruppo
        for (exchange_id, symbol_id, timeframe), data in groups.items():
            # Performance
            perf = PerformanceMetrics(
                exchange_id=exchange_id,
                symbol_id=symbol_id,
                timeframe=timeframe,
                start_time=data[0].timestamp,
                end_time=data[-1].timestamp
            )
            
            prices = [d.close for d in data]
            volumes = [d.volume for d in data]
            
            perf.calculate_metrics(prices, volumes)
            self.session.add(perf)
            
            # Rischio
            risk = RiskMetrics(
                exchange_id=exchange_id,
                symbol_id=symbol_id,
                timeframe=timeframe,
                start_time=data[0].timestamp,
                end_time=data[-1].timestamp
            )
            
            returns = [
                (data[i].close - data[i-1].close) / data[i-1].close
                for i in range(1, len(data))
            ]
            
            risk.calculate_metrics(returns)
            self.session.add(risk)
            
        await self.session.commit()