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
import yaml
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
    config_menu_items,
    gene_menu_items  # Aggiungo l'import dei gene_menu_items
)
from cli.progress import (
    create_spinner,
    create_progress_bar
)
from cli.config import (
    ConfigError,
    get_config_loader
)
from cli.menu.download_manager import DownloadManager
from cli.menu.population.population_menu import PopulationMenuManager
from data.database.models import (
    Symbol, MarketData, Exchange,
    initialize_gene_parameters, check_gene_parameters_exist
)
from data.database.session_manager import DBSessionManager

# Configura il logger usando get_logger
logger = get_logger(__name__)

# Abilita il supporto per asyncio nidificato
nest_asyncio.apply()

# Inizializza il session manager
db = DBSessionManager()

def simulate_loading(duration: float = 2.0) -> None:
    """Simula un caricamento per testing."""
    logger.info(f"Inizio simulazione caricamento di {duration} secondi")
    spinner = create_spinner(
        description="Caricamento",
        style="dots",
        speed=0.1
    )
    
    spinner.start()
    time.sleep(duration)
    spinner.stop()
    logger.info("Fine simulazione caricamento")

def check_system_status() -> str:
    """Verifica lo stato del sistema."""
    logger.info("Inizio verifica stato sistema")
    
    spinner = create_spinner(description="Verifica stato in corso")
    spinner.start()
    
    try:
        # Carica configurazione da logging.yaml
        with open("config/logging.yaml", 'r') as f:
            config = yaml.safe_load(f)
            system_config = config.get('system', {})
            
            # Verifica componenti
            status = []
            status.append(f"Log Level: {system_config.get('log_level', 'N/A')}")
            status.append(f"Data Directory: {system_config.get('data_dir', 'N/A')}")
            
            # Verifica indicatori
            indicators = system_config.get('indicators', {})
            status.append(f"Cache Size: {indicators.get('cache_size', 'N/A')}")
            status.append(f"Indicators Enabled: {indicators.get('enabled', 'N/A')}")
            
            # Verifica batch sizes
            batch_sizes = system_config.get('download', {}).get('batch_size', {})
            status.append("\nBatch Sizes:")
            for timeframe, size in batch_sizes.items():
                status.append(f"  {timeframe}: {size}")
            
            # Verifica handlers di logging
            handlers = config.get('handlers', {})
            status.append("\nLog Handlers:")
            for handler_name, handler in handlers.items():
                status.append(f"  {handler_name}: {handler.get('level', 'N/A')} -> {handler.get('filename', 'console')}")
            
            logger.info("Fine verifica stato sistema")
            return "\n".join(status)
            
    except Exception as e:
        logger.error(f"Errore verifica stato: {str(e)}")
        return f"Errore: {str(e)}"
    finally:
        spinner.stop()

def setup_main_menu() -> MenuManager:
    """
    Configura il menu principale dell'applicazione.
    
    Returns:
        MenuManager configurato con tutti i comandi
    """
    logger.info("Inizio configurazione menu principale")
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
    logger.info("Creazione comandi Gestione Dati")
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
    
    # Log i comandi del sottomenu Gestione Dati
    logger.info("Comandi nel sottomenu Gestione Dati:")
    for item in data_menu_items:
        logger.info(f"Nome: {item.name}, Visibile: {item.is_visible()}, Tipo: {type(item)}")
    
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
    
    # Aggiungi separatore prima del menu dei geni
    menu.add_menu_item(create_separator())
    
    # Crea sottomenu Geni
    genes_menu = create_submenu(
        name="Geni",
        items=gene_menu_items,  # Usa i gene_menu_items definiti in menu_items.py
        description="Gestione e test dei geni"
    )
    menu.add_menu_item(genes_menu)

    # Aggiungi separatore prima del menu popolazione
    menu.add_menu_item(create_separator())

    # Crea sottomenu Popolazione
    population_manager = PopulationMenuManager()
    population_menu = create_submenu(
        name="Popolazione",
        items=population_manager.get_menu_items(),
        description="Gestione delle popolazioni e evoluzione"
    )
    menu.add_menu_item(population_menu)
    
    logger.info("Fine configurazione menu principale")
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
        # Configura logging da YAML
        setup_logging("config/logging.yaml")
        
        logger.info("Inizializzazione TradingDNA CLI Framework...")
        
        # Inizializza l'event loop globale
        loop = initialize_event_loop()
        
        # Carica configurazione
        logger.info("Caricamento configurazione...")
        try:
            # Carica configurazione da logging.yaml
            with open("config/logging.yaml", 'r') as f:
                config = yaml.safe_load(f)
                system_config = config.get('system', {})
            
            # Verifica e inizializza i parametri dei geni se non esistono
            if not check_gene_parameters_exist():
                logger.info("Inizializzazione parametri dei geni...")
                initialize_gene_parameters(system_config)
                logger.info("Parametri dei geni inizializzati")
            
        except Exception as e:
            logger.error(f"Errore configurazione: {str(e)}")
            logger.info("Utilizzo configurazione predefinita")
        
        # Simula caricamento iniziale
        simulate_loading()
        
        # Crea e mostra il menu principale
        logger.info("Creazione menu principale")
        menu = setup_main_menu()
        logger.info("Menu principale creato, inizio visualizzazione")
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
