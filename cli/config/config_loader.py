"""
Config Loader
------------
Gestisce il caricamento e la validazione delle configurazioni del sistema.
Supporta file YAML e validazione schema.
"""

import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import yaml
from yaml.error import YAMLError

class ConfigError(Exception):
    """Errore base per problemi di configurazione."""
    pass

class ConfigValidationError(ConfigError):
    """Errore di validazione configurazione."""
    pass

class ConfigLoadError(ConfigError):
    """Errore di caricamento configurazione."""
    pass

class ConfigLoader:
    """Gestore delle configurazioni del sistema."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Inizializza il ConfigLoader.
        
        Args:
            config_dir: Directory delle configurazioni (opzionale)
        """
        self.config_dir = Path(config_dir) if config_dir else Path("config")
        self.config: Dict[str, Any] = {}
        self.validators: List[callable] = []
        
        # Crea directory config se non esiste
        self.config_dir.mkdir(exist_ok=True)
        
    def add_validator(self, validator: callable):
        """
        Aggiunge un validatore per la configurazione.
        
        Args:
            validator: Funzione di validazione
        """
        self.validators.append(validator)
        
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Valida la configurazione usando i validatori registrati.
        
        Args:
            config: Configurazione da validare
            
        Returns:
            Lista di errori di validazione
        """
        errors = []
        for validator in self.validators:
            try:
                validator(config)
            except Exception as e:
                errors.append(str(e))
        return errors
        
    def load_config(self, filename: str) -> Dict[str, Any]:
        """
        Carica la configurazione da file YAML.
        
        Args:
            filename: Nome del file di configurazione
            
        Returns:
            Configurazione caricata
            
        Raises:
            ConfigLoadError: Se ci sono errori nel caricamento
        """
        file_path = self.config_dir / filename
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            if not isinstance(config, dict):
                raise ConfigLoadError("Il file di configurazione deve contenere un dizionario")
                
            # Valida la configurazione
            errors = self.validate_config(config)
            if errors:
                raise ConfigValidationError(
                    "Errori di validazione:\n" + "\n".join(errors)
                )
                
            self.config = config
            return config
            
        except YAMLError as e:
            raise ConfigLoadError(f"Errore nel parsing YAML: {str(e)}")
        except OSError as e:
            raise ConfigLoadError(f"Errore di I/O: {str(e)}")
            
    def save_config(self, filename: str):
        """
        Salva la configurazione corrente su file.
        
        Args:
            filename: Nome del file di destinazione
            
        Raises:
            ConfigError: Se ci sono errori nel salvataggio
        """
        file_path = self.config_dir / filename
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self.config, f, default_flow_style=False)
        except Exception as e:
            raise ConfigError(f"Errore nel salvataggio della configurazione: {str(e)}")
            
    def get_value(self, key: str, default: Any = None) -> Any:
        """
        Recupera un valore dalla configurazione.
        
        Args:
            key: Chiave del valore
            default: Valore predefinito se la chiave non esiste
            
        Returns:
            Valore dalla configurazione o default
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
        
    def set_value(self, key: str, value: Any):
        """
        Imposta un valore nella configurazione.
        
        Args:
            key: Chiave del valore
            value: Valore da impostare
        """
        keys = key.split('.')
        config = self.config
        
        # Naviga la gerarchia delle chiavi
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        config[keys[-1]] = value
        
    def merge_config(self, other_config: Dict[str, Any]):
        """
        Unisce un'altra configurazione con quella corrente.
        
        Args:
            other_config: Configurazione da unire
        """
        def merge_dict(base: dict, other: dict):
            for key, value in other.items():
                if (
                    key in base and 
                    isinstance(base[key], dict) and 
                    isinstance(value, dict)
                ):
                    merge_dict(base[key], value)
                else:
                    base[key] = value
                    
        merge_dict(self.config, other_config)
        
    def create_default_config(self, filename: str = "config.yaml"):
        """
        Crea un file di configurazione predefinito.
        
        Args:
            filename: Nome del file di configurazione
        """
        default_config = {
            'system': {
                'log_level': 'INFO',
                'log_format': 'colored',
                'data_dir': 'data'
            },
            'trading': {
                'mode': 'backtest',
                'symbols': ['BTCUSDT', 'ETHUSDT'],
                'timeframes': ['1h', '4h', '1d']
            },
            'indicators': {
                'enabled': True,
                'cache_size': 1000
            },
            'security': {
                'enable_backup': True,
                'backup_interval': 86400  # 24h in secondi
            }
        }
        
        self.config = default_config
        self.save_config(filename)

# Istanza singleton del ConfigLoader
_config_loader: Optional[ConfigLoader] = None

def get_config_loader() -> ConfigLoader:
    """
    Ottiene l'istanza singleton del ConfigLoader.
    
    Returns:
        Istanza del ConfigLoader
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader