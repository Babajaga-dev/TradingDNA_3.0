"""
Progress Indicators
-----------------
Gestisce gli indicatori di progresso come spinner e barre.
Fornisce feedback visuale per operazioni lunghe.
"""

import time
import threading
from typing import Optional, Dict, Any, Callable
from rich.progress import Progress, SpinnerColumn, BarColumn
from rich.console import Console
from rich.style import Style
from rich.live import Live
from rich.spinner import Spinner

class ProgressIndicator:
    """Classe base per gli indicatori di progresso."""
    
    def __init__(self, description: str = ""):
        self.description = description
        self.console = Console()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
    def start(self):
        """Avvia l'indicatore."""
        self._running = True
        
    def stop(self):
        """Ferma l'indicatore."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join()
            
    def update(self, value: Any = None):
        """
        Aggiorna l'indicatore.
        
        Args:
            value: Valore di aggiornamento
        """
        pass

class SpinnerIndicator(ProgressIndicator):
    """Spinner animato per operazioni senza progresso definito."""
    
    SPINNERS = {
        'dots': '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏',
        'line': '|/-\\',
        'pulse': '█▉▊▋▌▍▎▏▎▍▌▋▊▉',
        'points': '⣾⣽⣻⢿⡿⣟⣯⣷',
        'clock': '🕐🕑🕒🕓🕔🕕🕖🕗🕘🕙🕚🕛'
    }
    
    def __init__(
        self,
        description: str = "",
        style: str = "dots",
        speed: float = 0.1
    ):
        super().__init__(description)
        self.style = style
        self.speed = speed
        self._current_frame = 0
        
    def _get_frame(self) -> str:
        """Ottiene il frame corrente dell'animazione."""
        frames = self.SPINNERS.get(self.style, self.SPINNERS['dots'])
        frame = frames[self._current_frame % len(frames)]
        self._current_frame += 1
        return frame
        
    def _animate(self):
        """Gestisce l'animazione dello spinner."""
        with Live(auto_refresh=False) as live:
            while self._running:
                frame = self._get_frame()
                live.update(f"{frame} {self.description}")
                live.refresh()
                time.sleep(self.speed)
                
    def start(self):
        """Avvia lo spinner in un thread separato."""
        super().start()
        self._thread = threading.Thread(target=self._animate)
        self._thread.start()

class ProgressBar(ProgressIndicator):
    """Barra di progresso per operazioni con avanzamento definito."""
    
    STYLES = {
        'default': '[▰▰▰▱▱▱]',
        'blocks': '█▉▊▋▌▍▎▏',
        'line': '━',
        'dots': '⣀⣄⣤⣦⣶⣷⣿',
        'squares': '⬜⬛'
    }
    
    def __init__(
        self,
        total: int,
        description: str = "",
        style: str = "default",
        show_percentage: bool = True,
        show_eta: bool = True
    ):
        super().__init__(description)
        self.total = total
        self.style = style
        self.show_percentage = show_percentage
        self.show_eta = show_eta
        self.current = 0
        self._start_time = 0
        
    def _format_time(self, seconds: float) -> str:
        """Formatta il tempo in formato leggibile."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = int(seconds / 60)
        seconds = seconds % 60
        if minutes < 60:
            return f"{minutes}m {seconds:.0f}s"
        hours = int(minutes / 60)
        minutes = minutes % 60
        return f"{hours}h {minutes}m"
        
    def _calculate_eta(self) -> str:
        """Calcola il tempo stimato rimanente."""
        if self.current == 0 or not self._start_time:
            return "???"
            
        elapsed = time.time() - self._start_time
        if elapsed <= 0:
            return "???"
            
        try:
            rate = self.current / elapsed
            if rate <= 0:
                return "???"
                
            remaining = (self.total - self.current) / rate
            return self._format_time(remaining)
        except (ZeroDivisionError, ValueError):
            return "???"
        
    def _get_progress_bar(self) -> str:
        """Genera la barra di progresso."""
        width = 30
        filled = int(width * self.current / self.total) if self.total > 0 else 0
        style = self.STYLES.get(self.style, self.STYLES['default'])
        
        if len(style) == 2:  # Per stili come squares
            bar = style[1] * filled + style[0] * (width - filled)
        else:  # Per stili graduali
            bar = style[-1] * filled + style[0] * (width - filled)
            
        text = [f"{self.description} [{bar}]"]
        
        if self.show_percentage:
            percentage = (self.current / self.total) * 100 if self.total > 0 else 0
            text.append(f"{percentage:.1f}%")
            
        if self.show_eta and self._start_time:
            text.append(f"ETA: {self._calculate_eta()}")
            
        return " ".join(text)
        
    def start(self):
        """Avvia la barra di progresso."""
        super().start()
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._update_display)
        self._thread.start()
        
    def _update_display(self):
        """Aggiorna il display della barra."""
        with Live(auto_refresh=False) as live:
            while self._running:
                try:
                    live.update(self._get_progress_bar())
                    live.refresh()
                except Exception as e:
                    # Log error but continue
                    print(f"Errore aggiornamento progress bar: {str(e)}")
                time.sleep(0.1)
                
    def update(self, value: int):
        """
        Aggiorna il progresso.
        
        Args:
            value: Nuovo valore del progresso
        """
        self.current = min(value, self.total)

class ProgressManager:
    """Gestore centralizzato per gli indicatori di progresso."""
    
    def __init__(self):
        self.indicators: Dict[str, ProgressIndicator] = {}
        
    def create_spinner(
        self,
        name: str,
        description: str = "",
        style: str = "dots",
        speed: float = 0.1
    ) -> SpinnerIndicator:
        """
        Crea un nuovo spinner.
        
        Args:
            name: Nome identificativo dello spinner
            description: Descrizione dello spinner
            style: Stile dell'animazione
            speed: Velocità dell'animazione
            
        Returns:
            Nuovo spinner configurato
        """
        spinner = SpinnerIndicator(description, style, speed)
        self.indicators[name] = spinner
        return spinner
        
    def create_progress_bar(
        self,
        name: str,
        total: int,
        description: str = "",
        style: str = "default",
        show_percentage: bool = True,
        show_eta: bool = True
    ) -> ProgressBar:
        """
        Crea una nuova barra di progresso.
        
        Args:
            name: Nome identificativo della barra
            total: Valore totale del progresso
            description: Descrizione della barra
            style: Stile della barra
            show_percentage: Mostra percentuale
            show_eta: Mostra tempo stimato
            
        Returns:
            Nuova barra di progresso configurata
        """
        bar = ProgressBar(total, description, style, show_percentage, show_eta)
        self.indicators[name] = bar
        return bar
        
    def get_indicator(self, name: str) -> Optional[ProgressIndicator]:
        """
        Ottiene un indicatore esistente.
        
        Args:
            name: Nome dell'indicatore
            
        Returns:
            Indicatore se esiste, None altrimenti
        """
        return self.indicators.get(name)
        
    def remove_indicator(self, name: str):
        """
        Rimuove un indicatore.
        
        Args:
            name: Nome dell'indicatore da rimuovere
        """
        if name in self.indicators:
            indicator = self.indicators[name]
            indicator.stop()
            del self.indicators[name]
            
    def clear(self):
        """Rimuove tutti gli indicatori."""
        for name in list(self.indicators.keys()):
            self.remove_indicator(name)

# Istanza singleton del ProgressManager
_progress_manager: Optional[ProgressManager] = None

def get_progress_manager() -> ProgressManager:
    """
    Ottiene l'istanza singleton del ProgressManager.
    
    Returns:
        Istanza del ProgressManager
    """
    global _progress_manager
    if _progress_manager is None:
        _progress_manager = ProgressManager()
    return _progress_manager
