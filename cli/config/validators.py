"""
Config Validators
---------------
Validatori per le configurazioni del sistema.
Fornisce funzioni per validare diversi tipi di configurazioni.
"""

from typing import Any, Dict, List, Optional, Union, Callable
import re
from pathlib import Path

class ValidationError(Exception):
    """Errore di validazione configurazione."""
    pass

def validate_type(value: Any, expected_type: type, field_name: str):
    """
    Valida il tipo di un valore.
    
    Args:
        value: Valore da validare
        expected_type: Tipo atteso
        field_name: Nome del campo
        
    Raises:
        ValidationError: Se il tipo non corrisponde
    """
    if not isinstance(value, expected_type):
        raise ValidationError(
            f"Il campo '{field_name}' deve essere di tipo {expected_type.__name__}, "
            f"non {type(value).__name__}"
        )

def validate_range(
    value: Union[int, float],
    field_name: str,
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None
):
    """
    Valida che un valore numerico sia in un range.
    
    Args:
        value: Valore da validare
        field_name: Nome del campo
        min_value: Valore minimo (opzionale)
        max_value: Valore massimo (opzionale)
        
    Raises:
        ValidationError: Se il valore è fuori range
    """
    if min_value is not None and value < min_value:
        raise ValidationError(
            f"Il campo '{field_name}' deve essere >= {min_value}"
        )
    if max_value is not None and value > max_value:
        raise ValidationError(
            f"Il campo '{field_name}' deve essere <= {max_value}"
        )

def validate_string_length(
    value: str,
    field_name: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None
):
    """
    Valida la lunghezza di una stringa.
    
    Args:
        value: Stringa da validare
        field_name: Nome del campo
        min_length: Lunghezza minima (opzionale)
        max_length: Lunghezza massima (opzionale)
        
    Raises:
        ValidationError: Se la lunghezza non è valida
    """
    if min_length is not None and len(value) < min_length:
        raise ValidationError(
            f"Il campo '{field_name}' deve avere almeno {min_length} caratteri"
        )
    if max_length is not None and len(value) > max_length:
        raise ValidationError(
            f"Il campo '{field_name}' deve avere al massimo {max_length} caratteri"
        )

def validate_regex(value: str, pattern: str, field_name: str):
    """
    Valida una stringa contro un pattern regex.
    
    Args:
        value: Stringa da validare
        pattern: Pattern regex
        field_name: Nome del campo
        
    Raises:
        ValidationError: Se la stringa non corrisponde al pattern
    """
    if not re.match(pattern, value):
        raise ValidationError(
            f"Il campo '{field_name}' non corrisponde al pattern richiesto"
        )

def validate_list_items(
    items: List[Any],
    field_name: str,
    validator: Callable[[Any], None]
):
    """
    Valida ogni elemento di una lista.
    
    Args:
        items: Lista da validare
        field_name: Nome del campo
        validator: Funzione di validazione per ogni elemento
        
    Raises:
        ValidationError: Se un elemento non è valido
    """
    for i, item in enumerate(items):
        try:
            validator(item)
        except ValidationError as e:
            raise ValidationError(
                f"Elemento {i} di '{field_name}' non valido: {str(e)}"
            )

def validate_required_fields(
    config: Dict[str, Any],
    required_fields: List[str]
):
    """
    Valida la presenza di campi obbligatori.
    
    Args:
        config: Configurazione da validare
        required_fields: Lista di campi obbligatori
        
    Raises:
        ValidationError: Se mancano campi obbligatori
    """
    missing_fields = [
        field for field in required_fields
        if field not in config
    ]
    
    if missing_fields:
        raise ValidationError(
            f"Campi obbligatori mancanti: {', '.join(missing_fields)}"
        )

def validate_path(path: Union[str, Path], field_name: str):
    """
    Valida un percorso file/directory.
    
    Args:
        path: Percorso da validare
        field_name: Nome del campo
        
    Raises:
        ValidationError: Se il percorso non è valido
    """
    try:
        Path(path).resolve()
    except Exception as e:
        raise ValidationError(
            f"Percorso non valido per '{field_name}': {str(e)}"
        )

class ConfigValidator:
    """Validatore configurazione con supporto per regole multiple."""
    
    def __init__(self):
        """Inizializza il validatore."""
        self.rules: List[Callable[[Dict[str, Any]], None]] = []
        
    def add_rule(self, rule: Callable[[Dict[str, Any]], None]):
        """
        Aggiunge una regola di validazione.
        
        Args:
            rule: Funzione di validazione
        """
        self.rules.append(rule)
        
    def validate(self, config: Dict[str, Any]):
        """
        Valida la configurazione usando tutte le regole.
        
        Args:
            config: Configurazione da validare
            
        Raises:
            ValidationError: Se la validazione fallisce
        """
        for rule in self.rules:
            rule(config)

def create_system_validator() -> ConfigValidator:
    """
    Crea un validatore per la configurazione di sistema.
    
    Returns:
        Validatore configurato
    """
    validator = ConfigValidator()
    
    # Valida campi obbligatori
    def validate_required(config: Dict[str, Any]):
        validate_required_fields(config, [
            'system',
            'trading',
            'indicators',
            'security'
        ])
    validator.add_rule(validate_required)
    
    # Valida configurazione sistema
    def validate_system(config: Dict[str, Any]):
        system = config.get('system', {})
        validate_type(system, dict, 'system')
        
        if 'log_level' in system:
            validate_type(system['log_level'], str, 'system.log_level')
            if system['log_level'] not in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
                raise ValidationError(
                    "system.log_level deve essere uno tra: DEBUG, INFO, WARNING, ERROR"
                )
                
        if 'data_dir' in system:
            validate_type(system['data_dir'], str, 'system.data_dir')
            validate_path(system['data_dir'], 'system.data_dir')
    validator.add_rule(validate_system)
    
    # Valida configurazione trading
    def validate_trading(config: Dict[str, Any]):
        trading = config.get('trading', {})
        validate_type(trading, dict, 'trading')
        
        if 'symbols' in trading:
            validate_type(trading['symbols'], list, 'trading.symbols')
            for symbol in trading['symbols']:
                validate_type(symbol, str, 'trading.symbols[]')
                validate_regex(symbol, r'^[A-Z0-9]+$', 'trading.symbols[]')
                
        if 'timeframes' in trading:
            validate_type(trading['timeframes'], list, 'trading.timeframes')
            valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
            for tf in trading['timeframes']:
                if tf not in valid_timeframes:
                    raise ValidationError(
                        f"Timeframe non valido: {tf}. "
                        f"Valori validi: {', '.join(valid_timeframes)}"
                    )
    validator.add_rule(validate_trading)
    
    # Valida configurazione indicatori
    def validate_indicators(config: Dict[str, Any]):
        indicators = config.get('indicators', {})
        validate_type(indicators, dict, 'indicators')
        
        if 'enabled' in indicators:
            validate_type(indicators['enabled'], bool, 'indicators.enabled')
            
        if 'cache_size' in indicators:
            validate_type(indicators['cache_size'], int, 'indicators.cache_size')
            validate_range(
                indicators['cache_size'],
                'indicators.cache_size',
                min_value=100,
                max_value=10000
            )
    validator.add_rule(validate_indicators)
    
    # Valida configurazione sicurezza
    def validate_security(config: Dict[str, Any]):
        security = config.get('security', {})
        validate_type(security, dict, 'security')
        
        if 'enable_backup' in security:
            validate_type(security['enable_backup'], bool, 'security.enable_backup')
            
        if 'backup_interval' in security:
            validate_type(security['backup_interval'], int, 'security.backup_interval')
            validate_range(
                security['backup_interval'],
                'security.backup_interval',
                min_value=3600,  # minimo 1 ora
                max_value=604800  # massimo 1 settimana
            )
    validator.add_rule(validate_security)
    
    return validator