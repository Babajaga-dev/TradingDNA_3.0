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
import nest_asyncio
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import select, func
from tabulate import tabulate

from cli.logger import setup_logging, get_logger
from cli.menu import (
    MenuManager,
    create_command,
    create_submenu,
    create_separator,
    download_historical_data,
    view_historical_data,
    config_menu_items
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
from cli.menu.download_manager import DownloadManager
from data.database.models import get_session, Symbol, MarketData, Exchange

# Configura un logger specifico per questo modulo
logger = logging.getLogger(__name__)

# Abilita il supporto per asyncio nidificato
nest_asyncio.apply()

def simulate_loading(duration: float = 2.0) -> None:
    """Simula un caricamento per testing."""
    logger.debug(f"Inizio simulazione caricamento di {duration} secondi")
    spinner = create_spinner(
        description="Caricamento",
        style="dots",
        speed=0.1
    )
    
    spinner.start()
    time.sleep(duration)
    spinner.stop()
    logger.debug("Fine simulazione caricamento")

def check_system_status() -> str:
    """Verifica lo stato del sistema."""
    logger.debug("Inizio verifica stato sistema")
    
    spinner = create_spinner(description="Verifica stato in corso")
    spinner.start()
    
    try:
        # Carica configurazione corrente
        config = get_config_loader().config
        
        # Verifica componenti
        status = []
        status.append(f"Log Level: {config['system']['log_level']}")
        status.append(f"Data Directory: {config['system']['data_dir']}")
        status.append(f"Trading Mode: {config['portfolio']['mode']}")
        status.append(f"Symbols: {', '.join(config['portfolio']['symbols'])}")
        status.append(f"Timeframes: {', '.join(config['portfolio']['timeframes'])}")
        
        logger.debug("Fine verifica stato sistema")
        return "\n".join(status)
    finally:
        spinner.stop()

def setup_main_menu() -> MenuManager:
    """
    Configura il menu principale dell'applicazione.
    
    Returns:
        MenuManager configurato con tutti i comandi
    """
    logger.debug("Inizio configurazione menu principale")
    menu = MenuManager("TradingDNA CLI")
    
    # Aggiungi Status Sistema
    menu.add_menu_item(create_command(
        name="Status Sistema",
        callback=lambda: check_system_status(),
        description="Verifica lo stato del sistema"
    ))
    
    # Aggiungi separatore
    menu.add_menu_item(create_separator())
    
    # Crea sottomenu Gestione Dati
    logger.debug("Creazione comandi Gestione Dati")
    data_menu_items = [
        create_command(
            name="Scarica Dati Storici",
            callback=download_historical_data,
            description="Scarica dati storici da exchange",
            visible=True  # Forza la visibilità
        ),
        create_command(
            name="Visualizza Dati Storici",
            callback=view_historical_data,
            description="Visualizza i dati storici delle crypto disponibili",
            visible=True  # Forza la visibilità
        )
    ]
    
    # Debug: stampa i comandi del sottomenu Gestione Dati
    logger.debug("Comandi nel sottomenu Gestione Dati:")
    for item in data_menu_items:
        logger.debug(f"Nome: {item.name}, Visibile: {item.is_visible()}, Tipo: {type(item)}")
    
    data_menu = create_submenu(
        name="Gestione Dati",
        items=data_menu_items,
        description="Operazioni sui dati"
    )
    menu.add_menu_item(data_menu)
    
    # Crea sottomenu Configurazione
    config_menu = create_submenu(
        name="Configurazione",
        items=config_menu_items,  # Usa i config_menu_items definiti in menu_items.py
        description="Impostazioni sistema"
    )
    menu.add_menu_item(config_menu)
    
    logger.debug("Fine configurazione menu principale")
    return menu

def initialize_event_loop():
    """Inizializza l'event loop globale."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop

def main():
    """Entry point principale dell'applicazione."""
    try:
        # Setup logging di base per messaggi iniziali
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            stream=sys.stdout
        )
        
        # Configura il logger specifico per questo modulo
        logger.setLevel(logging.DEBUG)
        
        logger.info("Inizializzazione TradingDNA CLI Framework...")
        
        # Inizializza l'event loop globale
        loop = initialize_event_loop()
        
        # Carica configurazione
        logger.debug("Caricamento configurazione...")
        try:
            config = load_system_config()
            
            # Configura logging con le impostazioni del sistema
            logger.debug("Configurazione logging...")
            setup_logging("config/logging.yaml")
            
            logger.debug("Logging configurato da YAML")
            
        except ConfigError as e:
            logger.error(f"Errore configurazione: {str(e)}")
            logger.info("Utilizzo configurazione predefinita")
            setup_logging("config/logging.yaml")
        
        # Simula caricamento iniziale
        simulate_loading()
        
        # Crea e mostra il menu principale
        logger.debug("Creazione menu principale")
        menu = setup_main_menu()
        logger.debug("Menu principale creato, inizio visualizzazione")
        menu.show_menu()
        
        logger.info("Chiusura applicazione...")
        
    except KeyboardInterrupt:
        logger.info("Interruzione da tastiera - Chiusura in corso...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Errore fatale: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        # Chiudi l'event loop
        try:
            loop = asyncio.get_event_loop()
            loop.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
