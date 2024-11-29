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

class LogManager:
    """Gestore centralizzato per il logging dell'applicazione."""
    
    def __init__(self):
        """Inizializza il LogManager."""
        self.log_dir = Path("logs")
        self.handlers: Dict[str, 'logging.Handler'] = {}
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
                print(f"Errore test scrittura: {e}")
                raise
            
        except Exception as e:
            print(f"Errore creazione directory log: {e}")
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
            
            # Carica configurazione logging
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Estrai configurazioni di sistema
            system_config = config.get('system', {})
            
            # Estrai log level e formato
            log_level = system_config.get('log_level', 'INFO').upper()
            log_format = system_config.get('log_format', 'colored')
            
            # Crea una copia della configurazione senza la sezione system
            logging_config = {k: v for k, v in config.items() if k != 'system'}
            
            # Aggiorna livello di logging
            if 'root' in logging_config:
                logging_config['root']['level'] = log_level
                
                # Aggiorna anche i livelli degli handlers
                for handler in logging_config['handlers'].values():
                    handler['level'] = log_level
                    
                # Aggiorna i livelli dei loggers
                for logger in logging_config['loggers'].values():
                    logger['level'] = log_level
            
            # Gestisci formattazione
            if log_format == 'colored':
                for handler in logging_config.get('handlers', {}).values():
                    if handler.get('formatter') == 'simple':
                        handler['formatter'] = 'colored'
            
            # Stampa debug info
            print("Configurazione logging:")
            print(f"Level: {log_level}")
            print(f"Format: {log_format}")
            print("Handlers:", list(logging_config.get('handlers', {}).keys()))
            print("Loggers:", list(logging_config.get('loggers', {}).keys()))
            
            # Applica configurazione finale
            logging.config.dictConfig(logging_config)
            
            # Test logging
            root_logger = logging.getLogger()
            root_logger.debug("Test debug message")
            root_logger.info("Test info message")
            
        except Exception as e:
            print(f"Errore configurazione logging: {e}")
            import traceback
            traceback.print_exc()
            raise
            
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
            print(f"Errore aggiunta file handler: {e}")
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
