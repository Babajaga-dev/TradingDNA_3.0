"""
Log Formatters
-------------
Formattatori personalizzati per i messaggi di log del framework CLI.
Fornisce stili diversi e supporto per emoji e colori.
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime

class BaseFormatter:
    """Classe base per i formattatori di log."""
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        self.fmt = fmt
        self.datefmt = datefmt
        
    def formatTime(self, record: Any, datefmt: Optional[str] = None) -> str:
        """Formatta il timestamp del record."""
        if datefmt:
            return datetime.fromtimestamp(record.created).strftime(datefmt)
        return str(datetime.fromtimestamp(record.created))
        
    def formatException(self, exc_info: Tuple) -> str:
        """Formatta l'informazione sull'eccezione."""
        import traceback
        return '\n'.join(traceback.format_exception(*exc_info))
        
    def format(self, record: Any) -> str:
        """Metodo base per la formattazione."""
        return str(record.msg)

class ColoredFormatter(BaseFormatter):
    """Formattatore che aggiunge colori e stili ai messaggi di log."""
    
    def __init__(self, *args, **kwargs):
        """Inizializza il formattatore."""
        super().__init__(*args, **kwargs)
        # Importa qui per evitare importazione circolare
        from rich.console import Console
        self.console = Console()
        
    def format(self, record: Any) -> str:
        """
        Formatta il record di log con colori e emoji.
        
        Args:
            record: Record di log da formattare
            
        Returns:
            Messaggio formattato
        """
        # Importa qui per evitare importazione circolare
        import logging
        from rich.style import Style
        from rich.text import Text
        
        # Stili predefiniti per i diversi livelli di log
        LEVEL_STYLES = {
            logging.DEBUG: Style(color="cyan", dim=True),
            logging.INFO: Style(color="blue"),
            logging.WARNING: Style(color="yellow", bold=True),
            logging.ERROR: Style(color="red", bold=True),
            logging.CRITICAL: Style(color="red", bold=True, reverse=True)
        }
        
        # Emoji per i diversi livelli di log
        LEVEL_EMOJIS = {
            logging.DEBUG: "🔍",
            logging.INFO: "ℹ️",
            logging.WARNING: "⚠️",
            logging.ERROR: "❌",
            logging.CRITICAL: "🚨"
        }
        
        # Crea il testo base
        text = Text()
        
        # Aggiungi timestamp
        text.append(
            self.formatTime(record, self.datefmt),
            style=Style(dim=True)
        )
        text.append(" | ")
        
        # Aggiungi emoji e livello
        emoji = LEVEL_EMOJIS.get(record.levelno, "")
        level_name = record.levelname.ljust(8)
        text.append(
            f"{emoji} {level_name}",
            style=LEVEL_STYLES.get(record.levelno, Style())
        )
        text.append(" | ")
        
        # Aggiungi nome del logger
        text.append(f"{record.name} | ", style=Style(dim=True))
        
        # Aggiungi il messaggio
        text.append(str(record.msg))
        
        # Gestisci eccezioni se presenti
        if record.exc_info:
            text.append("\n")
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
            text.append(record.exc_text, style=Style(color="red"))
            
        return str(text)

class JsonFormatter(BaseFormatter):
    """Formattatore che produce output in formato JSON."""
    
    def format(self, record: Any) -> str:
        """
        Formatta il record di log in JSON.
        
        Args:
            record: Record di log da formattare
            
        Returns:
            Stringa JSON formattata
        """
        import json
        
        output_dict = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage()
        }
        
        # Aggiungi informazioni sullo stack trace se presente
        if record.exc_info:
            output_dict['exc_info'] = self.formatException(record.exc_info)
            
        # Aggiungi attributi extra se presenti
        if hasattr(record, 'extra_data'):
            output_dict['extra_data'] = record.extra_data
            
        return json.dumps(output_dict)

class CompactFormatter(BaseFormatter):
    """Formattatore che produce output compatto per i log."""
    
    def format(self, record: Any) -> str:
        """
        Formatta il record di log in formato compatto.
        
        Args:
            record: Record di log da formattare
            
        Returns:
            Messaggio formattato in modo compatto
        """
        # Usa solo le prime lettere del livello
        level = record.levelname[0]
        
        # Formatta il timestamp in modo compatto
        timestamp = self.formatTime(record, "%H:%M:%S")
        
        # Crea il messaggio base
        msg = f"{timestamp}|{level}|{record.name}|{record.getMessage()}"
        
        # Aggiungi info sulle eccezioni se presenti
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
            msg = f"{msg}\n{record.exc_text}"
            
        return msg

def get_formatter(format_type: str = "colored", **kwargs: Any) -> BaseFormatter:
    """
    Factory function per ottenere il formattatore desiderato.
    
    Args:
        format_type: Tipo di formattatore ('colored', 'json', 'compact')
        **kwargs: Argomenti aggiuntivi per il formattatore
        
    Returns:
        Istanza del formattatore richiesto
    """
    formatters = {
        "colored": ColoredFormatter,
        "json": JsonFormatter,
        "compact": CompactFormatter
    }
    
    formatter_class = formatters.get(format_type, ColoredFormatter)
    return formatter_class(**kwargs)