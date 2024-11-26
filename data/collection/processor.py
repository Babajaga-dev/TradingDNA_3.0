"""
Data Processor
------------
Sistema di processing dati di mercato.
Implementa pipeline di trasformazione e calcolo indicatori.
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import numpy as np
import pandas as pd
import talib

class ProcessingStage(Enum):
    """Stadi di processing."""
    PREPROCESSING = "preprocessing"
    INDICATORS = "indicators"
    FEATURES = "features"
    POSTPROCESSING = "postprocessing"

@dataclass
class ProcessingStep:
    """Step di processing."""
    name: str
    stage: ProcessingStage
    function: Callable
    params: Optional[Dict[str, Any]] = None
    requires: Optional[List[str]] = None
    enabled: bool = True

class ProcessingStats:
    """Statistiche processing."""
    
    def __init__(self):
        self.total_steps = 0
        self.completed_steps = 0
        self.failed_steps = 0
        self.added_columns = 0
        self.removed_columns = 0
        
    def update(
        self,
        completed: bool,
        added: int = 0,
        removed: int = 0
    ):
        """Aggiorna statistiche."""
        self.total_steps += 1
        if completed:
            self.completed_steps += 1
        else:
            self.failed_steps += 1
        self.added_columns += added
        self.removed_columns += removed
        
    @property
    def success_rate(self) -> float:
        """Calcola tasso di successo."""
        if self.total_steps == 0:
            return 0.0
        return self.completed_steps / self.total_steps

class DataProcessor:
    """Processore dati di mercato."""
    
    def __init__(self):
        """Inizializza il processore."""
        self.logger = logging.getLogger(__name__)
        self.stats = ProcessingStats()
        self.steps = self._setup_steps()
        
    def _setup_steps(self) -> List[ProcessingStep]:
        """
        Configura step di processing.
        
        Returns:
            Lista degli step
        """
        return [
            # Preprocessing
            ProcessingStep(
                name="remove_duplicates",
                stage=ProcessingStage.PREPROCESSING,
                function=self._remove_duplicates
            ),
            ProcessingStep(
                name="sort_index",
                stage=ProcessingStage.PREPROCESSING,
                function=self._sort_index
            ),
            ProcessingStep(
                name="fill_missing",
                stage=ProcessingStage.PREPROCESSING,
                function=self._fill_missing
            ),
            
            # Indicatori tecnici base
            ProcessingStep(
                name="sma",
                stage=ProcessingStage.INDICATORS,
                function=self._add_sma,
                params={'periods': [20, 50, 200]}
            ),
            ProcessingStep(
                name="ema",
                stage=ProcessingStage.INDICATORS,
                function=self._add_ema,
                params={'periods': [20, 50, 200]}
            ),
            ProcessingStep(
                name="rsi",
                stage=ProcessingStage.INDICATORS,
                function=self._add_rsi,
                params={'period': 14}
            ),
            ProcessingStep(
                name="macd",
                stage=ProcessingStage.INDICATORS,
                function=self._add_macd,
                params={
                    'fastperiod': 12,
                    'slowperiod': 26,
                    'signalperiod': 9
                }
            ),
            ProcessingStep(
                name="bollinger",
                stage=ProcessingStage.INDICATORS,
                function=self._add_bollinger,
                params={'period': 20, 'stdev': 2}
            ),
            
            # Indicatori volume
            ProcessingStep(
                name="volume_sma",
                stage=ProcessingStage.INDICATORS,
                function=self._add_volume_sma,
                params={'periods': [20, 50]}
            ),
            ProcessingStep(
                name="obv",
                stage=ProcessingStage.INDICATORS,
                function=self._add_obv
            ),
            
            # Features
            ProcessingStep(
                name="returns",
                stage=ProcessingStage.FEATURES,
                function=self._add_returns
            ),
            ProcessingStep(
                name="log_returns",
                stage=ProcessingStage.FEATURES,
                function=self._add_log_returns
            ),
            ProcessingStep(
                name="volatility",
                stage=ProcessingStage.FEATURES,
                function=self._add_volatility,
                params={'window': 20}
            ),
            ProcessingStep(
                name="momentum",
                stage=ProcessingStage.FEATURES,
                function=self._add_momentum,
                params={'periods': [1, 5, 10, 20]}
            ),
            
            # Postprocessing
            ProcessingStep(
                name="remove_nan",
                stage=ProcessingStage.POSTPROCESSING,
                function=self._remove_nan
            ),
            ProcessingStep(
                name="clip_outliers",
                stage=ProcessingStage.POSTPROCESSING,
                function=self._clip_outliers,
                params={'std_dev': 3}
            )
        ]
        
    def process_data(
        self,
        df: pd.DataFrame,
        stages: Optional[List[ProcessingStage]] = None
    ) -> pd.DataFrame:
        """
        Processa DataFrame.
        
        Args:
            df: DataFrame da processare
            stages: Stage da eseguire
            
        Returns:
            DataFrame processato
        """
        if stages is None:
            stages = list(ProcessingStage)
            
        # Copia DataFrame
        df = df.copy()
        
        # Esegui step per ogni stage
        for stage in stages:
            steps = [
                s for s in self.steps
                if s.stage == stage and s.enabled
            ]
            
            for step in steps:
                try:
                    # Verifica dipendenze
                    if step.requires:
                        missing = [
                            r for r in step.requires
                            if r not in df.columns
                        ]
                        if missing:
                            raise ValueError(
                                f"Colonne mancanti: {missing}"
                            )
                            
                    # Esegui step
                    cols_before = set(df.columns)
                    df = step.function(df, **(step.params or {}))
                    cols_after = set(df.columns)
                    
                    # Aggiorna statistiche
                    self.stats.update(
                        completed=True,
                        added=len(cols_after - cols_before),
                        removed=len(cols_before - cols_after)
                    )
                    
                except Exception as e:
                    self.logger.error(
                        f"Errore in {step.name}: {str(e)}"
                    )
                    self.stats.update(completed=False)
                    
        return df
        
    def _remove_duplicates(
        self,
        df: pd.DataFrame,
        **kwargs: Any
    ) -> pd.DataFrame:
        """Rimuove righe duplicate."""
        return df.drop_duplicates()
        
    def _sort_index(
        self,
        df: pd.DataFrame,
        **kwargs: Any
    ) -> pd.DataFrame:
        """Ordina per timestamp."""
        return df.sort_index()
        
    def _fill_missing(
        self,
        df: pd.DataFrame,
        **kwargs: Any
    ) -> pd.DataFrame:
        """Riempie valori mancanti."""
        # Forward fill per OHLC
        df[['open', 'high', 'low', 'close']] = df[
            ['open', 'high', 'low', 'close']
        ].ffill()
        
        # Fill 0 per volume
        df['volume'] = df['volume'].fillna(0)
        
        return df
        
    def _add_sma(
        self,
        df: pd.DataFrame,
        periods: List[int],
        **kwargs: Any
    ) -> pd.DataFrame:
        """Aggiunge SMA."""
        for period in periods:
            df[f'sma_{period}'] = talib.SMA(
                df['close'].values,
                timeperiod=period
            )
        return df
        
    def _add_ema(
        self,
        df: pd.DataFrame,
        periods: List[int],
        **kwargs: Any
    ) -> pd.DataFrame:
        """Aggiunge EMA."""
        for period in periods:
            df[f'ema_{period}'] = talib.EMA(
                df['close'].values,
                timeperiod=period
            )
        return df
        
    def _add_rsi(
        self,
        df: pd.DataFrame,
        period: int,
        **kwargs: Any
    ) -> pd.DataFrame:
        """Aggiunge RSI."""
        df['rsi'] = talib.RSI(
            df['close'].values,
            timeperiod=period
        )
        return df
        
    def _add_macd(
        self,
        df: pd.DataFrame,
        fastperiod: int,
        slowperiod: int,
        signalperiod: int,
        **kwargs: Any
    ) -> pd.DataFrame:
        """Aggiunge MACD."""
        macd, signal, hist = talib.MACD(
            df['close'].values,
            fastperiod=fastperiod,
            slowperiod=slowperiod,
            signalperiod=signalperiod
        )
        df['macd'] = macd
        df['macd_signal'] = signal
        df['macd_hist'] = hist
        return df
        
    def _add_bollinger(
        self,
        df: pd.DataFrame,
        period: int,
        stdev: float,
        **kwargs: Any
    ) -> pd.DataFrame:
        """Aggiunge Bollinger Bands."""
        upper, middle, lower = talib.BBANDS(
            df['close'].values,
            timeperiod=period,
            nbdevup=stdev,
            nbdevdn=stdev
        )
        df['bb_upper'] = upper
        df['bb_middle'] = middle
        df['bb_lower'] = lower
        return df
        
    def _add_volume_sma(
        self,
        df: pd.DataFrame,
        periods: List[int],
        **kwargs: Any
    ) -> pd.DataFrame:
        """Aggiunge SMA volume."""
        for period in periods:
            df[f'volume_sma_{period}'] = talib.SMA(
                df['volume'].values,
                timeperiod=period
            )
        return df
        
    def _add_obv(
        self,
        df: pd.DataFrame,
        **kwargs: Any
    ) -> pd.DataFrame:
        """Aggiunge On Balance Volume."""
        df['obv'] = talib.OBV(
            df['close'].values,
            df['volume'].values
        )
        return df
        
    def _add_returns(
        self,
        df: pd.DataFrame,
        **kwargs: Any
    ) -> pd.DataFrame:
        """Aggiunge rendimenti."""
        df['returns'] = df['close'].pct_change()
        return df
        
    def _add_log_returns(
        self,
        df: pd.DataFrame,
        **kwargs: Any
    ) -> pd.DataFrame:
        """Aggiunge log rendimenti."""
        df['log_returns'] = np.log(df['close']).diff()
        return df
        
    def _add_volatility(
        self,
        df: pd.DataFrame,
        window: int,
        **kwargs: Any
    ) -> pd.DataFrame:
        """Aggiunge volatilità."""
        df['volatility'] = df['returns'].rolling(
            window=window
        ).std()
        return df
        
    def _add_momentum(
        self,
        df: pd.DataFrame,
        periods: List[int],
        **kwargs: Any
    ) -> pd.DataFrame:
        """Aggiunge momentum."""
        for period in periods:
            df[f'momentum_{period}'] = df['close'].pct_change(
                periods=period
            )
        return df
        
    def _remove_nan(
        self,
        df: pd.DataFrame,
        **kwargs: Any
    ) -> pd.DataFrame:
        """Rimuove righe con NaN."""
        return df.dropna()
        
    def _clip_outliers(
        self,
        df: pd.DataFrame,
        std_dev: float,
        **kwargs: Any
    ) -> pd.DataFrame:
        """Clip outliers."""
        numeric_cols = df.select_dtypes(
            include=[np.number]
        ).columns
        
        for col in numeric_cols:
            mean = df[col].mean()
            std = df[col].std()
            df[col] = df[col].clip(
                lower=mean - std_dev * std,
                upper=mean + std_dev * std
            )
            
        return df