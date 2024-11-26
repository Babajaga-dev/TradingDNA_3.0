"""
Progress Formatters
-----------------
Formattatori per gli indicatori di progresso.
Fornisce stili e formattazione personalizzata.
"""

from typing import Dict, Any, Optional
from rich.style import Style
from rich.text import Text
from rich.console import Console

class ProgressFormatter:
    """Formattatore base per gli indicatori di progresso."""
    
    # Stili predefiniti per diversi tipi di progresso
    DEFAULT_STYLES = {
        'normal': Style(color="blue"),
        'success': Style(color="green"),
        'warning': Style(color="yellow"),
        'error': Style(color="red"),
        'info': Style(color="cyan")
    }
    
    # Simboli per diversi stati
    STATUS_SYMBOLS = {
        'normal': '◈',
        'success': '✔',
        'warning': '⚠',
        'error': '✘',
        'info': 'ℹ'
    }
    
    def __init__(self):
        """Inizializza il formattatore."""
        self.console = Console()
        self.styles = self.DEFAULT_STYLES.copy()
        
    def format_progress(
        self,
        text: str,
        status: str = 'normal',
        show_symbol: bool = True
    ) -> Text:
        """
        Formatta il testo del progresso.
        
        Args:
            text: Testo da formattare
            status: Stato del progresso
            show_symbol: Mostra simbolo di stato
            
        Returns:
            Testo formattato
        """
        result = Text()
        
        if show_symbol:
            symbol = self.STATUS_SYMBOLS.get(status, self.STATUS_SYMBOLS['normal'])
            result.append(f"{symbol} ", style=self.styles.get(status))
            
        result.append(text, style=self.styles.get(status))
        return result
        
    def add_style(self, name: str, style: Style):
        """
        Aggiunge un nuovo stile.
        
        Args:
            name: Nome dello stile
            style: Stile da aggiungere
        """
        self.styles[name] = style
        
    def get_style(self, name: str) -> Optional[Style]:
        """
        Ottiene uno stile.
        
        Args:
            name: Nome dello stile
            
        Returns:
            Stile se esiste, None altrimenti
        """
        return self.styles.get(name)

class BarFormatter(ProgressFormatter):
    """Formattatore specifico per barre di progresso."""
    
    # Stili predefiniti per le barre
    BAR_STYLES = {
        'solid': {
            'complete': '█',
            'incomplete': '░'
        },
        'line': {
            'complete': '━',
            'incomplete': '─'
        },
        'double': {
            'complete': '▰',
            'incomplete': '▱'
        },
        'dots': {
            'complete': '⣿',
            'incomplete': '⣀'
        }
    }
    
    def format_bar(
        self,
        progress: float,
        width: int = 20,
        style: str = 'solid'
    ) -> Text:
        """
        Formatta una barra di progresso.
        
        Args:
            progress: Valore del progresso (0-1)
            width: Larghezza della barra
            style: Stile della barra
            
        Returns:
            Barra formattata
        """
        bar_chars = self.BAR_STYLES.get(style, self.BAR_STYLES['solid'])
        filled = int(progress * width)
        
        result = Text()
        result.append(bar_chars['complete'] * filled)
        result.append(bar_chars['incomplete'] * (width - filled))
        
        return result

class SpinnerFormatter(ProgressFormatter):
    """Formattatore specifico per spinner."""
    
    # Frame per diversi tipi di spinner
    SPINNER_FRAMES = {
        'dots': '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏',
        'line': '|/-\\',
        'pulse': '█▉▊▋▌▍▎▏▎▍▌▋▊▉',
        'points': '⣾⣽⣻⢿⡿⣟⣯⣷',
        'clock': '🕐🕑🕒🕓🕔🕕🕖🕗🕘🕙🕚🕛'
    }
    
    def format_spinner(
        self,
        frame_index: int,
        style: str = 'dots'
    ) -> Text:
        """
        Formatta un frame dello spinner.
        
        Args:
            frame_index: Indice del frame
            style: Stile dello spinner
            
        Returns:
            Frame formattato
        """
        frames = self.SPINNER_FRAMES.get(style, self.SPINNER_FRAMES['dots'])
        frame = frames[frame_index % len(frames)]
        
        return Text(frame, style=self.styles['normal'])

class TimeFormatter(ProgressFormatter):
    """Formattatore per tempi e durate."""
    
    def format_time(self, seconds: float) -> Text:
        """
        Formatta un tempo in secondi.
        
        Args:
            seconds: Tempo in secondi
            
        Returns:
            Tempo formattato
        """
        if seconds < 60:
            return Text(f"{seconds:.1f}s")
            
        minutes = int(seconds / 60)
        seconds = seconds % 60
        
        if minutes < 60:
            return Text(f"{minutes}m {seconds:.0f}s")
            
        hours = int(minutes / 60)
        minutes = minutes % 60
        
        return Text(f"{hours}h {minutes}m")
        
    def format_eta(self, seconds: float) -> Text:
        """
        Formatta un tempo stimato.
        
        Args:
            seconds: Tempo stimato in secondi
            
        Returns:
            ETA formattato
        """
        if seconds < 0:
            return Text("Completato", style=self.styles['success'])
            
        time_text = self.format_time(seconds)
        return Text(f"ETA: {time_text}")

# Istanze singleton dei formattatori
_progress_formatter: Optional[ProgressFormatter] = None
_bar_formatter: Optional[BarFormatter] = None
_spinner_formatter: Optional[SpinnerFormatter] = None
_time_formatter: Optional[TimeFormatter] = None

def get_progress_formatter() -> ProgressFormatter:
    """Ottiene l'istanza del ProgressFormatter."""
    global _progress_formatter
    if _progress_formatter is None:
        _progress_formatter = ProgressFormatter()
    return _progress_formatter

def get_bar_formatter() -> BarFormatter:
    """Ottiene l'istanza del BarFormatter."""
    global _bar_formatter
    if _bar_formatter is None:
        _bar_formatter = BarFormatter()
    return _bar_formatter

def get_spinner_formatter() -> SpinnerFormatter:
    """Ottiene l'istanza dello SpinnerFormatter."""
    global _spinner_formatter
    if _spinner_formatter is None:
        _spinner_formatter = SpinnerFormatter()
    return _spinner_formatter

def get_time_formatter() -> TimeFormatter:
    """Ottiene l'istanza del TimeFormatter."""
    global _time_formatter
    if _time_formatter is None:
        _time_formatter = TimeFormatter()
    return _time_formatter