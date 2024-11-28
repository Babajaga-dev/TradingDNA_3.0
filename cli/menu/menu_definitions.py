"""
Menu Definitions
--------------
Definizione della struttura del menu e dei suoi elementi.
"""

import asyncio
import nest_asyncio
from data.collection.downloader import DataDownloader, DownloadConfig
from data.database.models.models import (
    get_session, initialize_gene_parameters,
    MarketData, Symbol, Exchange, SYNC_DATABASE_URL,
    initialize_database
)
from .menu_core import create_command, create_submenu, create_separator
from .menu_utils import (
    manage_parameters,
    reset_system,
    view_historical_data,
    genetic_optimization_placeholder
)
from .gene_manager import GeneManager
from .download_manager import DownloadManager

# Abilita il supporto per asyncio nidificato
nest_asyncio.apply()

def download_historical_data():
    """Funzione per eseguire il download dei dati storici."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Esegue il download
        manager = DownloadManager()
        loop.run_until_complete(manager.run_download())
        return "Download completato con successo"
    finally:
        loop.close()

# Istanza del gene manager
gene_manager = GeneManager()

# Menu items per la configurazione
config_menu_items = [
    create_command(
        name="Parametri",
        callback=manage_parameters,
        description="Gestione parametri sistema"
    ),
    create_command(
        name="Reset Sistema",
        callback=reset_system,
        description="Elimina database, log e ricrea le tabelle",
        confirm=True  # Richiede conferma prima dell'esecuzione
    )
]

# Menu items per i geni RSI
rsi_menu_items = [
    create_command(
        name="Test Gene",
        callback=lambda: gene_manager.test_gene('rsi'),
        description="Testa il gene RSI su dati storici"
    ),
    create_command(
        name="Visualizza Parametri",
        callback=lambda: gene_manager.view_gene_params('rsi'),
        description="Visualizza i parametri correnti del gene"
    ),
    create_command(
        name="Modifica Parametri",
        callback=lambda: gene_manager.set_gene_params('rsi'),
        description="Modifica i parametri del gene"
    ),
    create_command(
        name="Reset Parametri",
        callback=lambda: gene_manager.reset_gene_params('rsi'),
        description="Resetta i parametri ai valori di default",
        confirm=True
    )
]

# Menu items per i geni Moving Average
moving_average_menu_items = [
    create_command(
        name="Test Gene",
        callback=lambda: gene_manager.test_gene('moving_average'),
        description="Testa il gene Moving Average su dati storici"
    ),
    create_command(
        name="Visualizza Parametri",
        callback=lambda: gene_manager.view_gene_params('moving_average'),
        description="Visualizza i parametri correnti del gene"
    ),
    create_command(
        name="Modifica Parametri",
        callback=lambda: gene_manager.set_gene_params('moving_average'),
        description="Modifica i parametri del gene"
    ),
    create_command(
        name="Reset Parametri",
        callback=lambda: gene_manager.reset_gene_params('moving_average'),
        description="Resetta i parametri ai valori di default",
        confirm=True
    )
]

# Sottomenu per ogni gene
gene_menu_items = [
    create_submenu(
        name="RSI",
        items=rsi_menu_items,
        description="Relative Strength Index"
    ),
    create_submenu(
        name="Moving Average",
        items=moving_average_menu_items,
        description="Moving Average"
    ),
    create_separator(),
    create_command(
        name="Ottimizzazione Genetica",
        callback=genetic_optimization_placeholder,
        description="Ottimizzazione genetica dei parametri"
    )
]

# Menu principale
all_menu_items = [
    create_submenu(
        name="Configurazione",
        items=config_menu_items,
        description="Gestione configurazione sistema"
    ),
    create_separator(),
    create_command(
        name="Scarica Dati",
        callback=download_historical_data,
        description="Scarica dati storici"
    ),
    create_command(
        name="Visualizza Dati",
        callback=view_historical_data,
        description="Visualizza dati storici"
    ),
    create_separator(),
    create_submenu(
        name="Geni",
        items=gene_menu_items,
        description="Gestione e test dei geni"
    )
]
