"""
Config Loader
------------
Gestisce il caricamento e la validazione delle configurazioni del sistema.
Supporta file YAML multipli e validazione schema.
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
    
    CONFIG_FILES = [
        "system.yaml",
        "networks.yaml", 
        "portfolio.yaml",
        "logging.yaml",
        "security.yaml"
    ]
    
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
        
    def load_config_file(self, filename: str) -> Dict[str, Any]:
        """
        Carica un singolo file di configurazione.
        
        Args:
            filename: Nome del file di configurazione
            
        Returns:
            Configurazione caricata dal file
            
        Raises:
            ConfigLoadError: Se ci sono errori nel caricamento
        """
        file_path = self.config_dir / filename
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            if not isinstance(config, dict):
                raise ConfigLoadError(f"Il file {filename} deve contenere un dizionario")
                
            return config
            
        except YAMLError as e:
            raise ConfigLoadError(f"Errore nel parsing YAML di {filename}: {str(e)}")
        except OSError as e:
            raise ConfigLoadError(f"Errore di I/O per {filename}: {str(e)}")
            
    def load_all_configs(self):
        """
        Carica tutti i file di configurazione e li unisce.
        
        Raises:
            ConfigLoadError: Se ci sono errori nel caricamento
            ConfigValidationError: Se ci sono errori di validazione
        """
        merged_config = {}
        
        for filename in self.CONFIG_FILES:
            try:
                config = self.load_config_file(filename)
                self.merge_config(merged_config, config)
            except ConfigLoadError as e:
                raise ConfigLoadError(f"Errore nel caricamento di {filename}: {str(e)}")
                
        # Valida la configurazione completa
        errors = self.validate_config(merged_config)
        if errors:
            raise ConfigValidationError(
                "Errori di validazione:\n" + "\n".join(errors)
            )
            
        self.config = merged_config
        return merged_config
        
    def save_config(self, section: str):
        """
        Salva una sezione della configurazione nel file appropriato.
        
        Args:
            section: Nome della sezione da salvare (system, networks, portfolio, logging, security)
            
        Raises:
            ConfigError: Se ci sono errori nel salvataggio
        """
        section_mapping = {
            'system': 'system.yaml',
            'networks': 'networks.yaml',
            'portfolio': 'portfolio.yaml',
            'logging': 'logging.yaml',
            'security': 'security.yaml'
        }
        
        if section not in section_mapping:
            raise ConfigError(f"Sezione non valida: {section}")
            
        filename = section_mapping[section]
        file_path = self.config_dir / filename
        
        try:
            # Estrai solo la sezione richiesta
            section_config = {section: self.config.get(section, {})}
            
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(section_config, f, default_flow_style=False)
        except Exception as e:
            raise ConfigError(f"Errore nel salvataggio della configurazione {section}: {str(e)}")
            
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
        
        # Salva la sezione appropriata
        section = keys[0]
        self.save_config(section)
        
    def merge_config(self, base: Dict[str, Any], other: Dict[str, Any]):
        """
        Unisce due configurazioni ricorsivamente.
        
        Args:
            base: Configurazione base
            other: Configurazione da unire
        """
        for key, value in other.items():
            if (
                key in base and 
                isinstance(base[key], dict) and 
                isinstance(value, dict)
            ):
                self.merge_config(base[key], value)
            else:
                base[key] = value
                
    def create_default_configs(self):
        """
        Crea i file di configurazione predefiniti.
        """
        default_configs = {
            'system.yaml': {
                'system': {
                    'data_dir': 'data',
                    'log_level': 'INFO',
                    'log_format': 'colored',
                    'indicators': {
                        'enabled': True,
                        'cache_size': 1000
                    }
                }
            },
            'networks.yaml': {
                'networks': {
                    'binance': {
                        'api_key': 'your_api_key_here',
                        'api_secret': 'your_api_secret_here'
                    }
                }
            },
            'portfolio.yaml': {
                'portfolio': {
                    'mode': 'backtest',
                    'symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'],
                    'timeframes': ['1h', '4h', '1d']
                }
            },
            'logging.yaml': {
                'logging': {
                    'handlers': {
                        'console': {
                            'enabled': True,
                            'format': 'colored'
                        },
                        'file': {
                            'enabled': True,
                            'path': 'logs/tradingdna.log',
                            'format': 'detailed'
                        }
                    }
                }
            },
            'security.yaml': {
                'security': {
                    'enable_backup': True,
                    'backup_interval': 86400
                }
            }
        }
        
        for filename, config in default_configs.items():
            file_path = self.config_dir / filename
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(config, f, default_flow_style=False)
            except Exception as e:
                raise ConfigError(f"Errore nella creazione del file {filename}: {str(e)}")

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
