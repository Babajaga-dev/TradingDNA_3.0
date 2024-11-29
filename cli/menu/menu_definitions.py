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

# Menu items per i geni MACD
macd_menu_items = [
    create_command(
        name="Test Gene",
        callback=lambda: gene_manager.test_gene('macd'),
        description="Testa il gene MACD su dati storici"
    ),
    create_command(
        name="Visualizza Parametri",
        callback=lambda: gene_manager.view_gene_params('macd'),
        description="Visualizza i parametri correnti del gene"
    ),
    create_command(
        name="Modifica Parametri",
        callback=lambda: gene_manager.set_gene_params('macd'),
        description="Modifica i parametri del gene"
    ),
    create_command(
        name="Reset Parametri",
        callback=lambda: gene_manager.reset_gene_params('macd'),
        description="Resetta i parametri ai valori di default",
        confirm=True
    )
]

# Menu items per i geni Bollinger
bollinger_menu_items = [
    create_command(
        name="Test Gene",
        callback=lambda: gene_manager.test_gene('bollinger'),
        description="Testa il gene Bollinger Bands su dati storici"
    ),
    create_command(
        name="Visualizza Parametri",
        callback=lambda: gene_manager.view_gene_params('bollinger'),
        description="Visualizza i parametri correnti del gene"
    ),
    create_command(
        name="Modifica Parametri",
        callback=lambda: gene_manager.set_gene_params('bollinger'),
        description="Modifica i parametri del gene"
    ),
    create_command(
        name="Reset Parametri",
        callback=lambda: gene_manager.reset_gene_params('bollinger'),
        description="Resetta i parametri ai valori di default",
        confirm=True
    )
]

# Menu items per i geni Stochastic
stochastic_menu_items = [
    create_command(
        name="Test Gene",
        callback=lambda: gene_manager.test_gene('stochastic'),
        description="Testa il gene Stochastic Oscillator su dati storici"
    ),
    create_command(
        name="Visualizza Parametri",
        callback=lambda: gene_manager.view_gene_params('stochastic'),
        description="Visualizza i parametri correnti del gene"
    ),
    create_command(
        name="Modifica Parametri",
        callback=lambda: gene_manager.set_gene_params('stochastic'),
        description="Modifica i parametri del gene"
    ),
    create_command(
        name="Reset Parametri",
        callback=lambda: gene_manager.reset_gene_params('stochastic'),
        description="Resetta i parametri ai valori di default",
        confirm=True
    )
]

# Menu items per i geni ATR
atr_menu_items = [
    create_command(
        name="Test Gene",
        callback=lambda: gene_manager.test_gene('atr'),
        description="Testa il gene ATR su dati storici"
    ),
    create_command(
        name="Visualizza Parametri",
        callback=lambda: gene_manager.view_gene_params('atr'),
        description="Visualizza i parametri correnti del gene"
    ),
    create_command(
        name="Modifica Parametri",
        callback=lambda: gene_manager.set_gene_params('atr'),
        description="Modifica i parametri del gene"
    ),
    create_command(
        name="Reset Parametri",
        callback=lambda: gene_manager.reset_gene_params('atr'),
        description="Resetta i parametri ai valori di default",
        confirm=True
    )
]

# Menu items per i geni Volume
volume_menu_items = [
    create_command(
        name="Test Gene",
        callback=lambda: gene_manager.test_gene('volume'),
        description="Testa il gene Volume su dati storici"
    ),
    create_command(
        name="Visualizza Parametri",
        callback=lambda: gene_manager.view_gene_params('volume'),
        description="Visualizza i parametri correnti del gene"
    ),
    create_command(
        name="Modifica Parametri",
        callback=lambda: gene_manager.set_gene_params('volume'),
        description="Modifica i parametri del gene"
    ),
    create_command(
        name="Reset Parametri",
        callback=lambda: gene_manager.reset_gene_params('volume'),
        description="Resetta i parametri ai valori di default",
        confirm=True
    )
]

# Menu items per i geni OBV
obv_menu_items = [
    create_command(
        name="Test Gene",
        callback=lambda: gene_manager.test_gene('obv'),
        description="Testa il gene OBV su dati storici"
    ),
    create_command(
        name="Visualizza Parametri",
        callback=lambda: gene_manager.view_gene_params('obv'),
        description="Visualizza i parametri correnti del gene"
    ),
    create_command(
        name="Modifica Parametri",
        callback=lambda: gene_manager.set_gene_params('obv'),
        description="Modifica i parametri del gene"
    ),
    create_command(
        name="Reset Parametri",
        callback=lambda: gene_manager.reset_gene_params('obv'),
        description="Resetta i parametri ai valori di default",
        confirm=True
    )
]

# Menu items per i geni Volatility Breakout
volatility_breakout_menu_items = [
    create_command(
        name="Test Gene",
        callback=lambda: gene_manager.test_gene('volatility_breakout'),
        description="Testa il gene Volatility Breakout su dati storici"
    ),
    create_command(
        name="Visualizza Parametri",
        callback=lambda: gene_manager.view_gene_params('volatility_breakout'),
        description="Visualizza i parametri correnti del gene"
    ),
    create_command(
        name="Modifica Parametri",
        callback=lambda: gene_manager.set_gene_params('volatility_breakout'),
        description="Modifica i parametri del gene"
    ),
    create_command(
        name="Reset Parametri",
        callback=lambda: gene_manager.reset_gene_params('volatility_breakout'),
        description="Resetta i parametri ai valori di default",
        confirm=True
    )
]

# Menu items per i geni Candlestick
candlestick_menu_items = [
    create_command(
        name="Test Gene",
        callback=lambda: gene_manager.test_gene('candlestick'),
        description="Testa il gene Candlestick su dati storici"
    ),
    create_command(
        name="Visualizza Parametri",
        callback=lambda: gene_manager.view_gene_params('candlestick'),
        description="Visualizza i parametri correnti del gene"
    ),
    create_command(
        name="Modifica Parametri",
        callback=lambda: gene_manager.set_gene_params('candlestick'),
        description="Modifica i parametri del gene"
    ),
    create_command(
        name="Reset Parametri",
        callback=lambda: gene_manager.reset_gene_params('candlestick'),
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
    create_submenu(
        name="MACD",
        items=macd_menu_items,
        description="Moving Average Convergence Divergence"
    ),
    create_submenu(
        name="Bollinger Bands",
        items=bollinger_menu_items,
        description="Bollinger Bands"
    ),
    create_submenu(
        name="Stochastic",
        items=stochastic_menu_items,
        description="Stochastic Oscillator"
    ),
    create_submenu(
        name="ATR",
        items=atr_menu_items,
        description="Average True Range"
    ),
    create_submenu(
        name="Volume",
        items=volume_menu_items,
        description="Volume Analysis"
    ),
    create_submenu(
        name="OBV",
        items=obv_menu_items,
        description="On Balance Volume"
    ),
    create_submenu(
        name="Volatility Breakout",
        items=volatility_breakout_menu_items,
        description="Volatility Breakout Strategy"
    ),
    create_submenu(
        name="Candlestick",
        items=candlestick_menu_items,
        description="Candlestick Pattern Analysis"
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
