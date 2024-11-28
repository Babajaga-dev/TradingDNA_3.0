"""
LogManager
----------
Gestisce il sistema di logging centralizzato per il framework CLI.
Fornisce formattazione personalizzata e gestione dei livelli di log.
"""

import logging
import logging.config
import yaml
import os
import sys
from typing import Dict, Optional, Any
from pathlib import Path
from datetime import datetime

# Definizione costanti di logging
DEBUG = 10
INFO = 20
WARNING = 30
ERROR = 40
CRITICAL = 50

class LogManager:
    """Gestore centralizzato per il logging dell'applicazione."""
    
    def __init__(self, log_level: int = INFO):
        """
        Inizializza il LogManager.
        
        Args:
            log_level: Livello di logging predefinito
        """
        self.log_level = log_level
        self.log_dir = Path("logs")
        self.handlers: Dict[str, 'logging.Handler'] = {}
        
        # Setup logging di base per debug iniziale
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            stream=sys.stdout
        )
        self._debug_logger = logging.getLogger('LogManager')
        
        # Crea directory logs se non esiste
        self._ensure_log_directory()
        
    def _ensure_log_directory(self):
        """Crea la directory dei log se non esiste."""
        try:
            # Converti in percorso assoluto
            log_path = self.log_dir.resolve()
            
            # Verifica e crea directory
            log_path.mkdir(parents=True, exist_ok=True)
            
            # Verifica permessi di scrittura
            test_file = log_path / "test_write.txt"
            try:
                with open(test_file, 'w') as f:
                    f.write("Test scrittura log")
                test_file.unlink()  # Rimuovi il file di test
            except Exception as e:
                raise
            
        except Exception as e:
            raise
        
    def configure_from_yaml(self, config_path: str):
        """
        Configura il logging da file YAML.
        
        Args:
            config_path: Percorso del file di configurazione YAML
        """
        try:
            # Verifica esistenza file
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"File di configurazione non trovato: {config_path}")
            
            # Ricarica il file per parsing
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Verifica struttura configurazione
            if not config or 'logging' not in config:
                raise ValueError("Configurazione logging non valida")
            
            # Carica configurazione di sistema
            system_config = self._load_system_config()
            
            # Applica impostazioni da system.yaml
            config = self._apply_system_config(config, system_config)
            
            # Configura il logging
            logging.config.dictConfig(config['logging'])
            
            # Test scrittura log
            test_logger = logging.getLogger('LogTest')
            test_logger.info("Test scrittura log - Configurazione completata")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._setup_base_config()
        
    def _load_system_config(self) -> Dict[str, Any]:
        """Carica la configurazione di sistema."""
        try:
            with open("config/system.yaml", 'r') as f:
                system_yaml = yaml.safe_load(f)
                return system_yaml.get('system', {})
        except Exception as e:
            return {}
        
    def _apply_system_config(self, config: Dict, system_config: Dict) -> Dict:
        """Applica le impostazioni di sistema alla configurazione di logging."""
        # Estrai log level e formato da system_config
        log_level = system_config.get('log_level', 'INFO').upper()
        log_format = system_config.get('log_format', 'colored')
        
        # Aggiorna livello di logging
        if 'logging' in config and 'root' in config['logging']:
            config['logging']['root']['level'] = log_level
        
        # Gestisci formattazione
        if log_format == 'colored':
            for handler in config.get('logging', {}).get('handlers', {}).values():
                if handler.get('formatter') == 'simple':
                    handler['formatter'] = 'colored'
        
        return config
    
    def get_logger(self, name: str) -> 'logging.Logger':
        """
        Ottiene un logger configurato per il modulo specificato.
        
        Args:
            name: Nome del logger/modulo
            
        Returns:
            Logger configurato
        """
        return logging.getLogger(name)
    
    def set_level(self, level: int):
        """
        Imposta il livello di logging.
        
        Args:
            level: Nuovo livello di logging
        """
        self.log_level = level
        logging.getLogger().setLevel(level)
        
    def add_file_handler(self, filename: str, 
                        formatter: Optional['logging.Formatter'] = None):
        """
        Aggiunge un nuovo file handler.
        
        Args:
            filename: Nome del file di log
            formatter: Formattatore personalizzato (opzionale)
        """
        import logging
        from .formatters import ColoredFormatter
        
        try:
            self._ensure_log_directory()
            
            log_path = str(self.log_dir / filename)
            handler = logging.FileHandler(log_path, encoding='utf-8')
            
            if formatter:
                handler.setFormatter(formatter)
            else:
                handler.setFormatter(ColoredFormatter())
                
            self.handlers[filename] = handler
            
        except Exception as e:
            raise
        
    def remove_handler(self, handler_name: str):
        """
        Rimuove un handler specifico.
        
        Args:
            handler_name: Nome dell'handler da rimuovere
        """
        if handler_name in self.handlers:
            handler = self.handlers.pop(handler_name)
            handler.close()
            
    def shutdown(self):
        """Chiude tutti gli handler e libera le risorse."""
        for handler in self.handlers.values():
            handler.close()
        self.handlers.clear()

# Istanza singleton del LogManager
_log_manager: Optional[LogManager] = None

def get_log_manager() -> LogManager:
    """
    Ottiene l'istanza singleton del LogManager.
    
    Returns:
        Istanza del LogManager
    """
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
    return _log_manager

def setup_logging(config_path: str) -> LogManager:
    """
    Configura il logging dal file YAML specificato.
    
    Args:
        config_path: Percorso del file di configurazione
        
    Returns:
        Istanza configurata del LogManager
    """
    manager = get_log_manager()
    manager.configure_from_yaml(config_path)
    return manager

def get_logger(name: str) -> 'logging.Logger':
    """
    Funzione helper per ottenere un logger configurato.
    
    Args:
        name: Nome del logger/modulo
        
    Returns:
        Logger configurato
    """
    return get_log_manager().get_logger(name)
