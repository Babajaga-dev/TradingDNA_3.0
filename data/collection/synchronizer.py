"""
Data Synchronizer
---------------
Sistema di sincronizzazione dati tra timeframe.
Gestisce aggregazione e allineamento temporale.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass
class TimeframeConfig:
    """Configurazione timeframe."""
    name: str
    minutes: int
    candles: int
    requires: Optional[str] = None

class SyncStats:
    """Statistiche sincronizzazione."""
    
    def __init__(self):
        self.total_candles = 0
        self.synced_candles = 0
        self.missing_candles = 0
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        
    def update(
        self,
        total: int,
        synced: int,
        missing: int
    ):
        """Aggiorna statistiche."""
        self.total_candles += total
        self.synced_candles += synced
        self.missing_candles += missing
        
    def complete(self):
        """Completa sincronizzazione."""
        self.end_time = datetime.utcnow()
        
    @property
    def duration(self) -> float:
        """Calcola durata sincronizzazione."""
        if not self.end_time:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()
        
    @property
    def sync_rate(self) -> float:
        """Calcola tasso sincronizzazione."""
        if self.total_candles == 0:
            return 0.0
        return self.synced_candles / self.total_candles

class DataSynchronizer:
    """Sincronizzatore dati tra timeframe."""
    
    def __init__(self):
        """Inizializza il sincronizzatore."""
        self.logger = logging.getLogger(__name__)
        self.stats = SyncStats()
        self.timeframes = self._setup_timeframes()
        
    def _setup_timeframes(self) -> Dict[str, TimeframeConfig]:
        """
        Configura timeframe supportati.
        
        Returns:
            Dizionario configurazioni
        """
        return {
            "1m": TimeframeConfig("1m", 1, 1440),
            "5m": TimeframeConfig("5m", 5, 288, "1m"),
            "15m": TimeframeConfig("15m", 15, 96, "5m"),
            "30m": TimeframeConfig("30m", 30, 48, "15m"),
            "1h": TimeframeConfig("1h", 60, 24, "30m"),
            "4h": TimeframeConfig("4h", 240, 6, "1h"),
            "1d": TimeframeConfig("1d", 1440, 1, "4h")
        }
        
    def sync_timeframes(
        self,
        data: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """
        Sincronizza dati tra timeframe.
        
        Args:
            data: Dizionario DataFrame per timeframe
            
        Returns:
            Dati sincronizzati
        """
        result = {}
        
        # Ordina timeframe per periodo
        timeframes = sorted(
            data.keys(),
            key=lambda x: self.timeframes[x].minutes
        )
        
        for tf in timeframes:
            config = self.timeframes[tf]
            df = data[tf]
            
            # Verifica dipendenza
            if config.requires and config.requires in data:
                # Aggrega dal timeframe inferiore
                base_df = data[config.requires]
                agg_df = self._aggregate_timeframe(
                    base_df, config
                )
                
                # Sincronizza
                df = self._sync_dataframes(df, agg_df)
                
            # Valida e salva
            df = self._validate_timeframe(df, config)
            result[tf] = df
            
            # Aggiorna statistiche
            self.stats.update(
                len(df),
                len(df.dropna()),
                len(df) - len(df.dropna())
            )
            
        return result
        
    def _aggregate_timeframe(
        self,
        df: pd.DataFrame,
        config: TimeframeConfig
    ) -> pd.DataFrame:
        """
        Aggrega dati a timeframe superiore.
        
        Args:
            df: DataFrame base
            config: Configurazione target
            
        Returns:
            DataFrame aggregato
        """
        # Imposta indice temporale
        df = df.set_index('timestamp')
        
        # Calcola intervallo resample
        minutes = config.minutes
        if minutes < 60:
            freq = f"{minutes}T"
        elif minutes < 1440:
            freq = f"{minutes//60}H"
        else:
            freq = f"{minutes//1440}D"
            
        # Aggrega OHLCV
        agg_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        
        df_agg = df.resample(freq).agg(agg_dict)
        
        # Ripristina indice come colonna
        df_agg = df_agg.reset_index()
        
        return df_agg
        
    def _sync_dataframes(
        self,
        df1: pd.DataFrame,
        df2: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Sincronizza due DataFrame.
        
        Args:
            df1: Primo DataFrame
            df2: Secondo DataFrame
            
        Returns:
            DataFrame sincronizzato
        """
        # Merge su timestamp
        df = pd.merge(
            df1,
            df2,
            on='timestamp',
            how='outer',
            suffixes=('', '_agg')
        )
        
        # Usa valori aggregati dove mancano originali
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].fillna(df[f"{col}_agg"])
            df = df.drop(f"{col}_agg", axis=1)
            
        return df
        
    def _validate_timeframe(
        self,
        df: pd.DataFrame,
        config: TimeframeConfig
    ) -> pd.DataFrame:
        """
        Valida DataFrame per timeframe.
        
        Args:
            df: DataFrame da validare
            config: Configurazione timeframe
            
        Returns:
            DataFrame validato
        """
        # Verifica timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Ordina per timestamp
        df = df.sort_values('timestamp')
        
        # Rimuovi duplicati
        df = df.drop_duplicates('timestamp')
        
        # Verifica intervalli
        minutes = config.minutes
        expected_diff = pd.Timedelta(minutes=minutes)
        
        df['diff'] = df['timestamp'].diff()
        gaps = df['diff'] != expected_diff
        
        if gaps.any():
            self.logger.warning(
                f"Gap trovati in {config.name}: "
                f"{gaps.sum()} su {len(df)} candele"
            )
            
        # Rimuovi colonna diff
        df = df.drop('diff', axis=1)
        
        return df
        
    def get_missing_ranges(
        self,
        df: pd.DataFrame,
        config: TimeframeConfig,
        start_time: datetime,
        end_time: datetime
    ) -> List[Tuple[datetime, datetime]]:
        """
        Trova intervalli mancanti.
        
        Args:
            df: DataFrame da analizzare
            config: Configurazione timeframe
            start_time: Inizio periodo
            end_time: Fine periodo
            
        Returns:
            Lista tuple (inizio, fine) intervalli mancanti
        """
        # Crea indice completo
        minutes = config.minutes
        idx = pd.date_range(
            start=start_time,
            end=end_time,
            freq=f"{minutes}T"
        )
        
        # Trova timestamp mancanti
        missing = idx.difference(df['timestamp'])
        
        # Raggruppa in intervalli
        ranges = []
        if len(missing) > 0:
            # Converti in array numpy per efficienza
            missing_arr = missing.values
            diff = np.diff(missing_arr)
            splits = np.where(
                diff > np.timedelta64(minutes, 'm')
            )[0] + 1
            
            # Dividi in intervalli
            ranges = list(zip(
                np.split(missing_arr, splits)[:-1],
                np.split(missing_arr, splits)[1:]
            ))
            
            # Aggiungi ultimo intervallo
            if len(ranges) > 0:
                ranges.append((
                    missing_arr[splits[-1]],
                    missing_arr[-1]
                ))
            else:
                ranges.append((
                    missing_arr[0],
                    missing_arr[-1]
                ))
                
        return ranges
        
    def estimate_download_size(
        self,
        timeframe: str,
        start_time: datetime,
        end_time: datetime
    ) -> int:
        """
        Stima numero candele da scaricare.
        
        Args:
            timeframe: Timeframe target
            start_time: Inizio periodo
            end_time: Fine periodo
            
        Returns:
            Numero stimato candele
        """
        config = self.timeframes[timeframe]
        minutes = config.minutes
        
        # Calcola differenza in minuti
        diff = end_time - start_time
        total_minutes = diff.total_seconds() / 60
        
        # Stima numero candele
        return int(total_minutes / minutes)
        
    def get_required_timeframes(
        self,
        timeframe: str
    ) -> List[str]:
        """
        Trova timeframe richiesti.
        
        Args:
            timeframe: Timeframe target
            
        Returns:
            Lista timeframe richiesti
        """
        required = []
        current = timeframe
        
        while current:
            config = self.timeframes[current]
            if config.requires:
                required.append(config.requires)
                current = config.requires
            else:
                break
                
        return required