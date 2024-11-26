"""
Data Validator
------------
Sistema di validazione dati di mercato.
Implementa regole e controlli di qualità.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import numpy as np
from scipy import stats

@dataclass
class ValidationRule:
    """Regola di validazione."""
    name: str
    description: str
    severity: str  # critical, warning, info
    enabled: bool = True
    parameters: Optional[Dict[str, Any]] = None

class ValidationSeverity(Enum):
    """Livelli di severità validazione."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

@dataclass
class ValidationResult:
    """Risultato validazione."""
    rule: ValidationRule
    passed: bool
    details: Optional[str] = None
    value: Optional[Any] = None

class ValidationStats:
    """Statistiche validazione."""
    
    def __init__(self):
        self.total_checks = 0
        self.passed_checks = 0
        self.failed_checks = 0
        self.critical_failures = 0
        self.warnings = 0
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        
    def update(
        self,
        passed: bool,
        severity: ValidationSeverity
    ):
        """
        Aggiorna statistiche.
        
        Args:
            passed: Test passato
            severity: Severità test
        """
        self.total_checks += 1
        if passed:
            self.passed_checks += 1
        else:
            self.failed_checks += 1
            if severity == ValidationSeverity.CRITICAL:
                self.critical_failures += 1
            elif severity == ValidationSeverity.WARNING:
                self.warnings += 1
                
    def complete(self):
        """Completa validazione."""
        self.end_time = datetime.utcnow()
        
    @property
    def duration(self) -> float:
        """Calcola durata validazione."""
        if not self.end_time:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()
        
    @property
    def pass_rate(self) -> float:
        """Calcola tasso di successo."""
        if self.total_checks == 0:
            return 0.0
        return self.passed_checks / self.total_checks

class DataValidator:
    """Validatore dati di mercato."""
    
    def __init__(self):
        """Inizializza il validatore."""
        self.logger = logging.getLogger(__name__)
        self.stats = ValidationStats()
        self.rules = self._setup_rules()
        
    def _setup_rules(self) -> List[ValidationRule]:
        """
        Configura regole di validazione.
        
        Returns:
            Lista delle regole
        """
        return [
            # Regole timestamp
            ValidationRule(
                name="timestamp_sequence",
                description="Verifica sequenza timestamp",
                severity="critical",
                parameters={"max_gap": 2}  # max gap in periodi
            ),
            ValidationRule(
                name="timestamp_future",
                description="Verifica timestamp futuri",
                severity="critical"
            ),
            
            # Regole prezzi
            ValidationRule(
                name="price_range",
                description="Verifica range prezzi",
                severity="critical",
                parameters={
                    "min_price": 0,
                    "max_change": 0.5  # 50% max variazione
                }
            ),
            ValidationRule(
                name="price_consistency",
                description="Verifica consistenza OHLC",
                severity="critical"
            ),
            
            # Regole volume
            ValidationRule(
                name="volume_range",
                description="Verifica range volume",
                severity="critical",
                parameters={"min_volume": 0}
            ),
            ValidationRule(
                name="volume_spikes",
                description="Verifica spike volume",
                severity="warning",
                parameters={"threshold": 10}  # 10x media mobile
            ),
            
            # Regole statistiche
            ValidationRule(
                name="price_gaps",
                description="Verifica gap prezzi",
                severity="warning",
                parameters={"threshold": 0.1}  # 10% gap max
            ),
            ValidationRule(
                name="price_volatility",
                description="Verifica volatilità",
                severity="warning",
                parameters={"threshold": 5}  # 5 deviazioni standard
            ),
            
            # Regole qualità
            ValidationRule(
                name="data_density",
                description="Verifica densità dati",
                severity="warning",
                parameters={"min_density": 0.9}  # 90% completezza
            ),
            ValidationRule(
                name="outliers",
                description="Verifica outliers",
                severity="warning",
                parameters={"threshold": 3}  # 3 deviazioni standard
            )
        ]
        
    def validate_candles(
        self,
        candles: List[List[float]],
        timeframe: str
    ) -> Tuple[List[ValidationResult], ValidationStats]:
        """
        Valida lista di candele.
        
        Args:
            candles: Lista candele OHLCV
            timeframe: Timeframe dati
            
        Returns:
            Tuple con risultati e statistiche
        """
        results = []
        
        # Converti in array numpy
        data = np.array(candles)
        timestamps = data[:, 0]
        opens = data[:, 1]
        highs = data[:, 2]
        lows = data[:, 3]
        closes = data[:, 4]
        volumes = data[:, 5]
        
        # Valida timestamp
        results.extend(self._validate_timestamps(
            timestamps, timeframe
        ))
        
        # Valida prezzi
        results.extend(self._validate_prices(
            opens, highs, lows, closes
        ))
        
        # Valida volumi
        results.extend(self._validate_volumes(volumes))
        
        # Valida statistiche
        results.extend(self._validate_statistics(
            timestamps, closes, volumes, timeframe
        ))
        
        # Aggiorna statistiche
        for result in results:
            self.stats.update(
                result.passed,
                ValidationSeverity(result.rule.severity)
            )
            
        return results, self.stats
        
    def _validate_timestamps(
        self,
        timestamps: np.ndarray,
        timeframe: str
    ) -> List[ValidationResult]:
        """
        Valida timestamp.
        
        Args:
            timestamps: Array timestamp
            timeframe: Timeframe dati
            
        Returns:
            Lista risultati validazione
        """
        results = []
        
        # Verifica sequenza
        rule = self._get_rule("timestamp_sequence")
        if rule and rule.enabled:
            # Calcola gaps
            diff = np.diff(timestamps)
            period = self._parse_timeframe(timeframe)
            max_gap = period * rule.parameters["max_gap"]
            
            gaps = diff > max_gap
            if np.any(gaps):
                results.append(ValidationResult(
                    rule=rule,
                    passed=False,
                    details=f"Gap trovati: {np.sum(gaps)}",
                    value=diff[gaps].tolist()
                ))
            else:
                results.append(ValidationResult(
                    rule=rule,
                    passed=True
                ))
                
        # Verifica futuro
        rule = self._get_rule("timestamp_future")
        if rule and rule.enabled:
            now = datetime.utcnow().timestamp() * 1000
            future = timestamps > now
            
            if np.any(future):
                results.append(ValidationResult(
                    rule=rule,
                    passed=False,
                    details=f"Timestamp futuri: {np.sum(future)}",
                    value=timestamps[future].tolist()
                ))
            else:
                results.append(ValidationResult(
                    rule=rule,
                    passed=True
                ))
                
        return results
        
    def _validate_prices(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray
    ) -> List[ValidationResult]:
        """
        Valida prezzi.
        
        Args:
            opens: Prezzi apertura
            highs: Prezzi massimi
            lows: Prezzi minimi
            closes: Prezzi chiusura
            
        Returns:
            Lista risultati validazione
        """
        results = []
        
        # Verifica range
        rule = self._get_rule("price_range")
        if rule and rule.enabled:
            min_price = rule.parameters["min_price"]
            max_change = rule.parameters["max_change"]
            
            # Verifica prezzi negativi
            invalid = (
                (opens < min_price) |
                (highs < min_price) |
                (lows < min_price) |
                (closes < min_price)
            )
            
            # Verifica variazioni eccessive
            changes = np.abs(np.diff(closes) / closes[:-1])
            invalid |= changes > max_change
            
            if np.any(invalid):
                results.append(ValidationResult(
                    rule=rule,
                    passed=False,
                    details=f"Prezzi invalidi: {np.sum(invalid)}",
                    value={
                        'invalid_prices': np.where(invalid)[0].tolist(),
                        'max_change': float(np.max(changes))
                    }
                ))
            else:
                results.append(ValidationResult(
                    rule=rule,
                    passed=True
                ))
                
        # Verifica consistenza
        rule = self._get_rule("price_consistency")
        if rule and rule.enabled:
            invalid = (
                (lows > opens) |
                (lows > closes) |
                (highs < opens) |
                (highs < closes) |
                (highs < lows)
            )
            
            if np.any(invalid):
                results.append(ValidationResult(
                    rule=rule,
                    passed=False,
                    details=f"Candele inconsistenti: {np.sum(invalid)}",
                    value=np.where(invalid)[0].tolist()
                ))
            else:
                results.append(ValidationResult(
                    rule=rule,
                    passed=True
                ))
                
        return results
        
    def _validate_volumes(
        self,
        volumes: np.ndarray
    ) -> List[ValidationResult]:
        """
        Valida volumi.
        
        Args:
            volumes: Array volumi
            
        Returns:
            Lista risultati validazione
        """
        results = []
        
        # Verifica range
        rule = self._get_rule("volume_range")
        if rule and rule.enabled:
            min_volume = rule.parameters["min_volume"]
            invalid = volumes < min_volume
            
            if np.any(invalid):
                results.append(ValidationResult(
                    rule=rule,
                    passed=False,
                    details=f"Volumi invalidi: {np.sum(invalid)}",
                    value=np.where(invalid)[0].tolist()
                ))
            else:
                results.append(ValidationResult(
                    rule=rule,
                    passed=True
                ))
                
        # Verifica spike
        rule = self._get_rule("volume_spikes")
        if rule and rule.enabled:
            # Calcola media mobile
            window = 20
            if len(volumes) >= window:
                ma = np.convolve(
                    volumes,
                    np.ones(window)/window,
                    mode='valid'
                )
                ma = np.pad(ma, (window-1, 0), mode='edge')
                
                # Trova spike
                threshold = rule.parameters["threshold"]
                spikes = volumes > (ma * threshold)
                
                if np.any(spikes):
                    results.append(ValidationResult(
                        rule=rule,
                        passed=False,
                        details=f"Volume spike: {np.sum(spikes)}",
                        value={
                            'spike_indexes': np.where(spikes)[0].tolist(),
                            'max_ratio': float(np.max(volumes / ma))
                        }
                    ))
                else:
                    results.append(ValidationResult(
                        rule=rule,
                        passed=True
                    ))
                    
        return results
        
    def _validate_statistics(
        self,
        timestamps: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
        timeframe: str
    ) -> List[ValidationResult]:
        """
        Valida statistiche.
        
        Args:
            timestamps: Array timestamp
            closes: Prezzi chiusura
            volumes: Volumi
            timeframe: Timeframe dati
            
        Returns:
            Lista risultati validazione
        """
        results = []
        
        # Verifica gap prezzi
        rule = self._get_rule("price_gaps")
        if rule and rule.enabled:
            # Calcola gap percentuali
            gaps = np.abs(np.diff(closes) / closes[:-1])
            threshold = rule.parameters["threshold"]
            
            large_gaps = gaps > threshold
            if np.any(large_gaps):
                results.append(ValidationResult(
                    rule=rule,
                    passed=False,
                    details=f"Gap prezzi: {np.sum(large_gaps)}",
                    value={
                        'gap_indexes': np.where(large_gaps)[0].tolist(),
                        'max_gap': float(np.max(gaps))
                    }
                ))
            else:
                results.append(ValidationResult(
                    rule=rule,
                    passed=True
                ))
                
        # Verifica volatilità
        rule = self._get_rule("price_volatility")
        if rule and rule.enabled:
            # Calcola rendimenti
            returns = np.diff(np.log(closes))
            
            # Calcola z-score
            z_scores = np.abs(stats.zscore(returns))
            threshold = rule.parameters["threshold"]
            
            high_vol = z_scores > threshold
            if np.any(high_vol):
                results.append(ValidationResult(
                    rule=rule,
                    passed=False,
                    details=f"Alta volatilità: {np.sum(high_vol)}",
                    value={
                        'vol_indexes': np.where(high_vol)[0].tolist(),
                        'max_zscore': float(np.max(z_scores))
                    }
                ))
            else:
                results.append(ValidationResult(
                    rule=rule,
                    passed=True
                ))
                
        # Verifica densità
        rule = self._get_rule("data_density")
        if rule and rule.enabled:
            # Calcola periodi attesi
            period = self._parse_timeframe(timeframe)
            expected = (timestamps[-1] - timestamps[0]) / period
            density = len(timestamps) / expected
            
            min_density = rule.parameters["min_density"]
            if density < min_density:
                results.append(ValidationResult(
                    rule=rule,
                    passed=False,
                    details="Densità dati insufficiente",
                    value={
                        'density': float(density),
                        'missing': int(expected - len(timestamps))
                    }
                ))
            else:
                results.append(ValidationResult(
                    rule=rule,
                    passed=True
                ))
                
        # Verifica outliers
        rule = self._get_rule("outliers")
        if rule and rule.enabled:
            # Calcola z-score per prezzi e volumi
            z_prices = np.abs(stats.zscore(closes))
            z_volumes = np.abs(stats.zscore(volumes))
            
            threshold = rule.parameters["threshold"]
            price_outliers = z_prices > threshold
            volume_outliers = z_volumes > threshold
            
            if np.any(price_outliers) or np.any(volume_outliers):
                results.append(ValidationResult(
                    rule=rule,
                    passed=False,
                    details=(
                        f"Outliers prezzi: {np.sum(price_outliers)}, "
                        f"volumi: {np.sum(volume_outliers)}"
                    ),
                    value={
                        'price_outliers': np.where(price_outliers)[0].tolist(),
                        'volume_outliers': np.where(volume_outliers)[0].tolist()
                    }
                ))
            else:
                results.append(ValidationResult(
                    rule=rule,
                    passed=True
                ))
                
        return results
        
    def _get_rule(self, name: str) -> Optional[ValidationRule]:
        """
        Recupera regola per nome.
        
        Args:
            name: Nome regola
            
        Returns:
            Regola se esiste
        """
        return next(
            (r for r in self.rules if r.name == name),
            None
        )
        
    def _parse_timeframe(self, timeframe: str) -> int:
        """
        Converte timeframe in millisecondi.
        
        Args:
            timeframe: Timeframe (es. 1m, 1h, 1d)
            
        Returns:
            Millisecondi
        """
        units = {
            'm': 60 * 1000,
            'h': 60 * 60 * 1000,
            'd': 24 * 60 * 60 * 1000,
            'w': 7 * 24 * 60 * 60 * 1000
        }
        
        amount = int(timeframe[:-1])
        unit = timeframe[-1]
        
        if unit not in units:
            raise ValueError(f"Timeframe non valido: {timeframe}")
            
        return amount * units[unit]