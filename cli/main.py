#!/usr/bin/env python3
"""
TradingDNA CLI Framework
------------------------
Entry point per il framework CLI che fornisce un'interfaccia interattiva
per la gestione del sistema di trading.
"""

import sys
import time
import traceback
import logging
import asyncio
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta

from cli.logger import setup_logging, get_logger
from cli.menu import (
    MenuManager,
    create_command,
    create_submenu,
    create_separator,
    create_menu_from_dict
)
from cli.progress import (
    create_spinner,
    create_progress_bar
)
from cli.config import (
    ConfigError,
    load_system_config,
    get_config_loader
)

from data.collection.downloader import DataDownloader, DownloadConfig
from data.database.models import get_session

def simulate_long_operation(steps: int = 10, delay: float = 0.2) -> None:
    """Simula un'operazione lunga per testing."""
    progress = create_progress_bar(
        total=steps,
        description="Elaborazione in corso",
        style="blocks",
        show_percentage=True,
        show_eta=True
    )
    
    progress.start()
    for i in range(steps):
        time.sleep(delay)
        progress.update(i + 1)
    progress.stop()

def simulate_loading(duration: float = 2.0) -> None:
    """Simula un caricamento per testing."""
    spinner = create_spinner(
        description="Caricamento",
        style="dots",
        speed=0.1
    )
    
    spinner.start()
    time.sleep(duration)
    spinner.stop()

def check_system_status() -> str:
    """Verifica lo stato del sistema."""
    logger = get_logger(__name__)
    logger.info("Verificando stato sistema...")
    
    spinner = create_spinner(description="Verifica stato in corso")
    spinner.start()
    
    try:
        # Carica configurazione corrente
        config = get_config_loader().config
        
        # Verifica componenti
        status = []
        status.append(f"Log Level: {config['system']['log_level']}")
        status.append(f"Data Directory: {config['system']['data_dir']}")
        status.append(f"Trading Mode: {config['trading']['mode']}")
        status.append(f"Symbols: {', '.join(config['trading']['symbols'])}")
        status.append(f"Timeframes: {', '.join(config['trading']['timeframes'])}")
        status.append(f"Indicators Enabled: {config['indicators']['enabled']}")
        status.append(f"Backup Enabled: {config['security']['enable_backup']}")
        
        return "\n".join(status)
    finally:
        spinner.stop()

async def download_historical_data() -> str:
    """Scarica dati storici."""
    logger = get_logger(__name__)
    logger.info("Avvio download dati storici...")
    
    config = get_config_loader().config
    
    # Crea configurazione download
    download_config = DownloadConfig(
        exchanges=[{
            'id': 'binance',
            'config': {
                'apiKey': config['exchanges']['binance']['api_key'],
                'secret': config['exchanges']['binance']['api_secret']
            }
        }],
        symbols=config['trading']['symbols'],
        timeframes=config['trading']['timeframes'],
        start_date=datetime.utcnow() - timedelta(days=365),  # Ultimo anno
        validate_data=True,
        update_metrics=True,
        max_concurrent=5,
        batch_size=1000
    )
    
    # Crea sessione database
    async with get_session() as session:
        # Inizializza downloader
        downloader = DataDownloader(session, download_config)
        
        # Progress bar
        progress = create_progress_bar(
            total=len(download_config.symbols) * len(download_config.timeframes),
            description="Download dati storici",
            style="blocks",
            show_percentage=True,
            show_eta=True
        )
        
        try:
            # Setup iniziale
            await downloader.setup()
            
            # Avvia download
            progress.start()
            stats = await downloader.download_data()
            progress.stop()
            
            # Prepara report
            duration = stats.duration
            minutes = int(duration / 60)
            seconds = int(duration % 60)
            
            return f"""Download completato in {minutes}m {seconds}s
Candele totali: {stats.total_candles}
Candele valide: {stats.valid_candles}
Candele invalide: {stats.invalid_candles}
Candele mancanti: {stats.missing_candles}
Tasso validazione: {stats.validation_rate:.1%}"""
            
        except Exception as e:
            logger.error(f"Errore durante il download: {str(e)}")
            return f"Errore durante il download: {str(e)}"

def import_data() -> str:
    """Importa dati nel sistema."""
    logger = get_logger(__name__)
    logger.info("Avvio importazione dati...")
    
    config = get_config_loader().config
    data_dir = Path(config['system']['data_dir'])
    symbols = config['trading']['symbols']
    
    # Simula importazione con progress bar
    steps = len(symbols)
    progress = create_progress_bar(
        total=steps,
        description="Importazione dati",
        style="blocks",
        show_percentage=True,
        show_eta=True
    )
    
    progress.start()
    for i, symbol in enumerate(symbols):
        logger.info(f"Importazione {symbol}...")
        time.sleep(0.5)  # Simula operazione
        progress.update(i + 1)
    progress.stop()
    
    return "Importazione completata con successo"

def export_data() -> str:
    """Esporta dati dal sistema."""
    logger = get_logger(__name__)
    logger.info("Avvio esportazione dati...")
    
    config = get_config_loader().config
    data_dir = Path(config['system']['data_dir'])
    timeframes = config['trading']['timeframes']
    
    # Simula esportazione con progress bar
    steps = len(timeframes)
    progress = create_progress_bar(
        total=steps,
        description="Esportazione dati",
        style="blocks",
        show_percentage=True,
        show_eta=True
    )
    
    progress.start()
    for i, tf in enumerate(timeframes):
        logger.info(f"Esportazione timeframe {tf}...")
        time.sleep(0.4)  # Simula operazione
        progress.update(i + 1)
    progress.stop()
    
    return "Esportazione completata con successo"

def manage_parameters() -> str:
    """Gestisce i parametri del sistema."""
    logger = get_logger(__name__)
    logger.info("Apertura gestione parametri...")
    
    config = get_config_loader()
    
    # Simula caricamento
    spinner = create_spinner(description="Caricamento parametri")
    spinner.start()
    time.sleep(1)
    spinner.stop()
    
    # Mostra parametri correnti
    current_config = config.config
    return f"""Parametri correnti:
Log Level: {current_config['system']['log_level']}
Trading Mode: {current_config['trading']['mode']}
Indicators Enabled: {current_config['indicators']['enabled']}
Cache Size: {current_config['indicators']['cache_size']}
Backup Enabled: {current_config['security']['enable_backup']}
Backup Interval: {current_config['security']['backup_interval']}s"""

def manage_backup() -> str:
    """Gestisce i backup del sistema."""
    logger = get_logger(__name__)
    logger.info("Avvio procedura backup...")
    
    config = get_config_loader().config
    if not config['security']['enable_backup']:
        return "Backup disabilitato nelle impostazioni"
    
    # Simula backup con progress bar
    progress = create_progress_bar(
        total=5,
        description="Backup in corso",
        style="blocks",
        show_percentage=True,
        show_eta=True
    )
    
    progress.start()
    
    # Simula fasi del backup
    steps = [
        ("Preparazione backup", 0.3),
        ("Backup configurazione", 0.4),
        ("Backup dati trading", 0.6),
        ("Backup indicatori", 0.4),
        ("Finalizzazione", 0.3)
    ]
    
    for i, (step, duration) in enumerate(steps):
        logger.info(f"Backup: {step}...")
        time.sleep(duration)
        progress.update(i + 1)
    
    progress.stop()
    return "Backup completato con successo"

def setup_main_menu() -> MenuManager:
    """
    Configura il menu principale dell'applicazione.
    
    Returns:
        MenuManager configurato con tutti i comandi
    """
    # Crea il menu principale
    menu_structure = {
        'name': 'Menu Principale',
        'items': [
            {
                'type': 'command',
                'name': 'Status Sistema',
                'callback': lambda: check_system_status(),
                'description': 'Verifica lo stato del sistema'
            },
            {
                'type': 'separator'
            },
            {
                'type': 'submenu',
                'name': 'Gestione Dati',
                'description': 'Operazioni sui dati',
                'items': [
                    {
                        'type': 'command',
                        'name': 'Scarica Dati Storici',
                        'callback': lambda: asyncio.run(download_historical_data()),
                        'description': 'Scarica dati storici da exchange'
                    },
                    {
                        'type': 'command',
                        'name': 'Importa Dati',
                        'callback': lambda: import_data(),
                        'description': 'Importa nuovi dati nel sistema'
                    },
                    {
                        'type': 'command',
                        'name': 'Esporta Dati',
                        'callback': lambda: export_data(),
                        'description': 'Esporta dati dal sistema'
                    }
                ]
            },
            {
                'type': 'submenu',
                'name': 'Configurazione',
                'description': 'Impostazioni sistema',
                'items': [
                    {
                        'type': 'command',
                        'name': 'Parametri',
                        'callback': lambda: manage_parameters(),
                        'description': 'Gestione parametri sistema'
                    },
                    {
                        'type': 'command',
                        'name': 'Backup',
                        'callback': lambda: manage_backup(),
                        'description': 'Gestione backup sistema',
                        'confirm': True
                    }
                ]
            }
        ]
    }
    
    return create_menu_from_dict(menu_structure, "TradingDNA CLI")

def main():
    """Entry point principale dell'applicazione."""
    try:
        print("Initializing...")  # Debug print
        
        # Carica configurazione
        logger = get_logger(__name__)
        print("Logger created...")  # Debug print
        logger.info("Caricamento configurazione...")
        
        try:
            config = load_system_config()
            setup_logging(
                log_level=config['system']['log_level'],
                format_type="colored"
            )
        except ConfigError as e:
            print(f"Config error: {str(e)}")  # Debug print
            logger.error(f"Errore configurazione: {str(e)}")
            logger.info("Utilizzo configurazione predefinita")
            setup_logging(log_level="INFO", format_type="colored")
        
        logger.info("Inizializzazione TradingDNA CLI Framework...")
        
        # Simula caricamento iniziale
        simulate_loading()
        
        # Crea e mostra il menu principale
        menu = setup_main_menu()
        menu.show_menu()
        
        logger.info("Chiusura applicazione...")
        
    except KeyboardInterrupt:
        print("Keyboard interrupt detected...")  # Debug print
        logger.info("Interruzione da tastiera - Chiusura in corso...")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {str(e)}")  # Debug print
        print("\nTraceback completo:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()