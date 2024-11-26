"""
TradingDNA CLI Framework - Progress Module
----------------------------------------
Modulo per la gestione degli indicatori di progresso.
Fornisce barre di progresso e spinner animati.
"""

from typing import Optional, Any

from .indicators import (
    ProgressIndicator,
    SpinnerIndicator,
    ProgressBar,
    ProgressManager,
    get_progress_manager
)

from .formatters import (
    ProgressFormatter,
    BarFormatter,
    SpinnerFormatter,
    TimeFormatter,
    get_progress_formatter,
    get_bar_formatter,
    get_spinner_formatter,
    get_time_formatter
)

__all__ = [
    # Classi base
    'ProgressIndicator',
    'SpinnerIndicator',
    'ProgressBar',
    'ProgressManager',
    
    # Formattatori
    'ProgressFormatter',
    'BarFormatter',
    'SpinnerFormatter',
    'TimeFormatter',
    
    # Factory functions
    'create_progress_bar',
    'create_spinner',
    
    # Getter functions
    'get_progress_manager',
    'get_progress_formatter',
    'get_bar_formatter',
    'get_spinner_formatter',
    'get_time_formatter'
]

def create_progress_bar(
    total: int,
    description: str = "",
    style: str = "default",
    show_percentage: bool = True,
    show_eta: bool = True
) -> ProgressBar:
    """
    Crea una nuova barra di progresso.
    
    Args:
        total: Valore totale del progresso
        description: Descrizione della barra
        style: Stile della barra
        show_percentage: Mostra percentuale
        show_eta: Mostra tempo stimato
        
    Returns:
        Nuova barra di progresso configurata
    """
    manager = get_progress_manager()
    return manager.create_progress_bar(
        name=description or "progress",
        total=total,
        description=description,
        style=style,
        show_percentage=show_percentage,
        show_eta=show_eta
    )

def create_spinner(
    description: str = "",
    style: str = "dots",
    speed: float = 0.1
) -> SpinnerIndicator:
    """
    Crea un nuovo spinner.
    
    Args:
        description: Descrizione dello spinner
        style: Stile dell'animazione
        speed: Velocità dell'animazione
        
    Returns:
        Nuovo spinner configurato
    """
    manager = get_progress_manager()
    return manager.create_spinner(
        name=description or "spinner",
        description=description,
        style=style,
        speed=speed
    )