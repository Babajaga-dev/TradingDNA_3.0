"""
LogManager
----------
Gestisce il sistema di logging centralizzato per il framework CLI.
Fornisce formattazione personalizzata e gestione dei livelli di log.
"""

from typing import Dict, Optional
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
        
        # Crea directory logs se non esiste
        self.log_dir.mkdir(exist_ok=True)
        
        # Configurazione base
        self._setup_base_config()
        
    def _setup_base_config(self):
        """Configura le impostazioni base del logging."""
        # Importa qui per evitare importazione circolare
        import logging
        from rich.console import Console
        from rich.logging import RichHandler
        from .formatters import ColoredFormatter
        
        # Handler per console con rich formatting
        console = Console()
        console_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            rich_tracebacks=True
        )
        console_handler.setFormatter(ColoredFormatter())
        self.handlers['console'] = console_handler
        
        # Handler per file con rotazione giornaliera
        today = datetime.now().strftime('%Y-%m-%d')
        file_handler = logging.FileHandler(
            self.log_dir / f"tradingdna_{today}.log",
            encoding='utf-8'
        )
        file_handler.setFormatter(ColoredFormatter())
        self.handlers['file'] = file_handler
        
    def get_logger(self, name: str) -> 'logging.Logger':
        """
        Ottiene un logger configurato per il modulo specificato.
        
        Args:
            name: Nome del logger/modulo
            
        Returns:
            Logger configurato
        """
        import logging
        logger = logging.getLogger(name)
        logger.setLevel(self.log_level)
        
        # Rimuovi handler esistenti
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Aggiungi i nostri handler
        for handler in self.handlers.values():
            logger.addHandler(handler)
            
        return logger
    
    def set_level(self, level: int):
        """
        Imposta il livello di logging.
        
        Args:
            level: Nuovo livello di logging
        """
        import logging
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
        
        handler = logging.FileHandler(
            self.log_dir / filename,
            encoding='utf-8'
        )
        
        if formatter:
            handler.setFormatter(formatter)
        else:
            handler.setFormatter(ColoredFormatter())
            
        self.handlers[filename] = handler
        
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