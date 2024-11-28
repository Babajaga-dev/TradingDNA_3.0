"""
Menu Items
----------
Definizione delle classi per gli elementi del menu interattivo.
Supporta comandi, sottomenu e separatori.
"""

import logging
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import asyncio
import nest_asyncio
from datetime import datetime, timedelta
from sqlalchemy import create_engine, select, func, text
from tabulate import tabulate
import sqlite3
import os
import time

from data.collection.downloader import DataDownloader, DownloadConfig
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, sessionmaker
from data.database.models import (
    get_session, Symbol, MarketData, Exchange, SYNC_DATABASE_URL
)
from cli.config import get_config_loader
from .download_manager import DownloadManager
from .gene_manager import GeneManager

# Abilita il supporto per asyncio nidificato
nest_asyncio.apply()

class MenuItem(ABC):
    """Classe base astratta per gli elementi del menu."""
    
    def __init__(
        self,
        name: str,
        description: str = "",
        enabled: bool = True,
        visible: bool = True
    ):
        self.name = name
        self.description = description
        self.enabled = enabled
        self.visible = visible
        
    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Esegue l'azione associata all'elemento del menu."""
        pass
    
    def is_enabled(self) -> bool:
        """Verifica se l'elemento è abilitato."""
        return self.enabled
    
    def is_visible(self) -> bool:
        """Verifica se l'elemento è visibile."""
        return self.visible

class CommandMenuItem(MenuItem):
    """Elemento del menu che esegue un comando."""
    
    def __init__(
        self,
        name: str,
        callback: Callable[..., Any],
        description: str = "",
        enabled: bool = True,
        visible: bool = True,
        confirm: bool = False
    ):
        super().__init__(name, description, enabled, visible)
        self.callback = callback
        self.confirm = confirm
        
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Esegue il callback associato al comando."""
        if self.confirm:
            confirm = input(f"Confermi l'esecuzione di '{self.name}'? [s/N]: ")
            if confirm.lower() != 's':
                return None
        return self.callback(*args, **kwargs)

class SubMenuItem(MenuItem):
    """Elemento del menu che rappresenta un sottomenu."""
    
    def __init__(
        self,
        name: str,
        items: List[MenuItem],
        description: str = "",
        enabled: bool = True,
        visible: bool = True
    ):
        super().__init__(name, description, enabled, visible)
        self.items = items
        
    def execute(self, *args: Any, **kwargs: Any) -> None:
        """Non fa nulla, la gestione del sottomenu è delegata al MenuManager."""
        return None
    
    def add_item(self, item: MenuItem) -> None:
        """Aggiunge un elemento al sottomenu."""
        self.items.append(item)
    
    def remove_item(self, name: str) -> None:
        """Rimuove un elemento dal sottomenu."""
        self.items = [item for item in self.items if item.name != name]
    
    def get_items(self) -> List[MenuItem]:
        """Ritorna la lista degli elementi del sottomenu."""
        return self.items

class SeparatorMenuItem(MenuItem):
    """Elemento del menu che rappresenta un separatore."""
    
    def __init__(self, char: str = "-", length: int = 40):
        super().__init__("separator", "", True, True)
        self.char = char
        self.length = length
        
    def execute(self, *args: Any, **kwargs: Any) -> None:
        """Non fa nulla, è solo un separatore visivo."""
        pass

@dataclass
class MenuContext:
    """Contesto per la gestione dello stato del menu."""
    
    current_path: List[str] = field(default_factory=list)
    history: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    
    def push_path(self, name: str) -> None:
        """Aggiunge un elemento al path corrente."""
        self.current_path.append(name)
        self.history.append(name)
        
    def pop_path(self) -> Optional[str]:
        """Rimuove e ritorna l'ultimo elemento del path."""
        if self.current_path:
            return self.current_path.pop()
        return None
    
    def get_current_path(self) -> str:
        """Ritorna il path corrente come stringa."""
        return " > ".join(self.current_path)
    
    def clear(self) -> None:
        """Pulisce il contesto."""
        self.current_path.clear()
        self.history.clear()
        self.data.clear()

def create_command(
    name: str,
    callback: Callable[..., Any],
    description: str = "",
    **kwargs: Any
) -> CommandMenuItem:
    """
    Factory function per creare un comando del menu.
    
    Args:
        name: Nome del comando
        callback: Funzione da eseguire
        description: Descrizione del comando
        **kwargs: Argomenti aggiuntivi per CommandMenuItem
        
    Returns:
        Istanza di CommandMenuItem
    """
    return CommandMenuItem(name, callback, description, **kwargs)

def create_submenu(
    name: str,
    items: List[MenuItem],
    description: str = "",
    **kwargs: Any
) -> SubMenuItem:
    """
    Factory function per creare un sottomenu.
    
    Args:
        name: Nome del sottomenu
        items: Lista di elementi del menu
        description: Descrizione del sottomenu
        **kwargs: Argomenti aggiuntivi per SubMenuItem
        
    Returns:
        Istanza di SubMenuItem
    """
    return SubMenuItem(name, items, description, **kwargs)

def create_separator(char: str = "-", length: int = 40) -> SeparatorMenuItem:
    """
    Factory function per creare un separatore.
    
    Args:
        char: Carattere da usare per il separatore
        length: Lunghezza del separatore
        
    Returns:
        Istanza di SeparatorMenuItem
    """
    return SeparatorMenuItem(char, length)

def force_close_connections():
    """Forza la chiusura di tutte le connessioni al database."""
    try:
        # Chiudi tutte le connessioni SQLite
        sqlite3.connect(':memory:').close()
        
        # Importa gli engine globali
        from data.database.models import engine, sync_engine
        
        # Chiudi l'engine asincrono
        if hasattr(engine, 'dispose'):
            asyncio.get_event_loop().run_until_complete(engine.dispose())
        
        # Chiudi l'engine sincrono
        if hasattr(sync_engine, 'dispose'):
            sync_engine.dispose()
        
        # Chiudi tutte le sessioni attive
        Session = sessionmaker(bind=sync_engine)
        if hasattr(Session, 'close_all'):
            Session.close_all()
        
        # Forza il garbage collector
        import gc
        gc.collect()
        
        # Attendi un momento per permettere la chiusura delle connessioni
        time.sleep(5)  # Aumentato il tempo di attesa
        
        # Verifica se ci sono ancora connessioni attive
        try:
            # Prova ad aprire il database in modalità esclusiva
            test_conn = sqlite3.connect(
                "data/tradingdna.db", 
                timeout=1,
                isolation_level='EXCLUSIVE'
            )
            test_conn.close()
        except sqlite3.OperationalError:
            # Se non riesce ad aprire il database, ci sono ancora connessioni attive
            print("Attenzione: Ci sono ancora connessioni attive al database")
            # Attendi ulteriormente
            time.sleep(5)  # Aumentato il tempo di attesa
            
    except Exception as e:
        print(f"Errore durante la chiusura delle connessioni: {e}")

def shutdown_all_loggers():
    """Chiude tutti i logger e i loro handler."""
    # Ottieni tutti i logger
    loggers = [logging.getLogger()] + list(logging.Logger.manager.loggerDict.values())
    
    # Chiudi tutti gli handler di ogni logger
    for logger in loggers:
        if hasattr(logger, 'handlers'):
            for handler in logger.handlers[:]:
                try:
                    handler.close()
                    logger.removeHandler(handler)
                except:
                    pass
    
    # Chiudi il LogManager
    from cli.logger import get_log_manager
    log_manager = get_log_manager()
    log_manager.shutdown()
    
    # Resetta il logging di base
    logging.shutdown()

def reset_system():
    """Resetta il sistema eliminando database, log e ricreando le tabelle."""
    try:
        print("\nAvvio procedura di reset del sistema...")
        
        # 1. Chiudi tutti i logger
        shutdown_all_loggers()
        
        # 2. Attendi un momento per permettere la chiusura dei file
        time.sleep(2)
        
        # 3. Elimina i file di log
        import shutil
        from pathlib import Path
        log_dir = Path("logs")
        if log_dir.exists():
            print("Eliminazione file di log...")
            try:
                # Prima prova a eliminare i singoli file
                for file in log_dir.glob("*"):
                    try:
                        if file.is_file():
                            os.chmod(file, 0o777)  # Cambia i permessi per assicurarsi di poter eliminare
                            file.unlink()
                    except Exception as e:
                        print(f"Avviso: Impossibile eliminare {file}: {e}")
                
                # Poi prova a eliminare la directory
                if log_dir.exists():
                    shutil.rmtree(log_dir, ignore_errors=True)
            except Exception as e:
                print(f"Avviso: Impossibile eliminare alcuni file di log: {e}")
            
            # Ricrea la directory
            log_dir.mkdir(exist_ok=True)
            print("Directory log ricreata.")
        
        # 4. Gestione eliminazione database
        db_path = Path("data/tradingdna.db")
        journal_path = Path("data/tradingdna.db-journal")
        wal_path = Path("data/tradingdna.db-wal")
        shm_path = Path("data/tradingdna.db-shm")
        
        if any(p.exists() for p in [db_path, journal_path, wal_path, shm_path]):
            print("Eliminazione database e file correlati...")
            
            # Forza la chiusura delle connessioni
            force_close_connections()
            
            # Attendi un momento per permettere la chiusura delle connessioni
            time.sleep(2)
            
            # Elimina tutti i file correlati al database
            for path in [db_path, journal_path, wal_path, shm_path]:
                try:
                    if path.exists():
                        os.chmod(path, 0o777)  # Cambia i permessi per assicurarsi di poter eliminare
                        path.unlink()
                except Exception as e:
                    print(f"Avviso: Impossibile eliminare {path}: {e}")
            
            print("Database e file correlati eliminati.")
        
        # 5. Ricrea il database da zero
        print("Inizializzazione nuovo database...")
        os.makedirs(db_path.parent, exist_ok=True)
        
        # Crea una nuova connessione al database
        engine = create_engine(
            SYNC_DATABASE_URL,
            isolation_level='SERIALIZABLE',
            connect_args={'timeout': 30}
        )
        
        # Inizializza il database con le nuove tabelle
        from data.database.models import initialize_database, initialize_gene_parameters
        initialize_database()
        
        # 6. Inserisci Binance con il nome corretto
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            # Verifica se Binance esiste già
            result = session.execute(
                text("SELECT id FROM exchanges WHERE name = 'binance'")
            ).fetchone()
            
            if result:
                # Aggiorna l'exchange esistente
                session.execute(
                    text("""
                    UPDATE exchanges 
                    SET is_active = 1, 
                        updated_at = CURRENT_TIMESTAMP 
                    WHERE name = 'binance'
                    """)
                )
            else:
                # Inserisci nuovo exchange
                session.execute(
                    text("""
                    INSERT INTO exchanges (name, is_active, created_at, updated_at)
                    VALUES ('binance', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """)
                )
            session.commit()
        finally:
            session.close()
            
        print("Database inizializzato con exchange 'binance'")
        
        # 7. Inizializza i parametri dei geni dai valori di default
        print("Inizializzazione parametri dei geni...")
        config = get_config_loader().config
        initialize_gene_parameters(config)
        print("Parametri dei geni inizializzati dai valori di default")
        
        # 8. Reset dei geni
        print("Reset dei geni in corso...")
        gene_manager = GeneManager()
        gene_types = ['rsi', 'moving_average']  # Lista dei tipi di geni disponibili
        for gene_type in gene_types:
            try:
                gene_manager.reset_gene_params(gene_type)
                print(f"Gene {gene_type} resettato con successo")
            except Exception as e:
                print(f"Errore durante il reset del gene {gene_type}: {e}")
        
        # 9. Riconfigura il logging
        print("Riconfigurazione sistema di logging...")
        from cli.logger import setup_logging
        setup_logging("config/logging.yaml")
        
        return "Reset del sistema completato con successo."
        
    except Exception as e:
        print(f"\nErrore durante il reset del sistema: {str(e)}")
        return "Errore durante il reset del sistema."

def manage_parameters():
    """Gestisce i parametri del sistema."""
    config = get_config_loader()
    current_config = config.config
    return f"""Parametri correnti:
Log Level: {current_config['system']['log_level']}
Trading Mode: {current_config['portfolio']['mode']}
Symbols: {', '.join(current_config['portfolio']['symbols'])}
Timeframes: {', '.join(current_config['portfolio']['timeframes'])}"""

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

def get_candles_per_day(timeframe: str) -> int:
    """Calcola il numero di candele per giorno per un dato timeframe."""
    timeframe_minutes = {
        '1m': 1,
        '5m': 5,
        '15m': 15,
        '1h': 60,
        '4h': 240,
        '1d': 1440
    }
    minutes_per_day = 24 * 60
    return minutes_per_day // timeframe_minutes[timeframe]

def view_historical_data():
    """Funzione per visualizzare i dati storici delle crypto."""
    try:
        # Crea engine e session sincroni
        engine = create_engine(SYNC_DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Recupera tutte le crypto disponibili
            symbols = session.query(Symbol).join(Exchange).all()
            
            if not symbols:
                print("Nessuna crypto disponibile nel database.")
                return
            
            # Mostra le crypto disponibili
            print("\nCrypto disponibili:")
            for i, symbol in enumerate(symbols, 1):
                print(f"{i}. {symbol.name} ({symbol.exchange.name})")
            
            # Selezione della crypto
            while True:
                try:
                    scelta = int(input("\nSeleziona il numero della crypto (0 per uscire): "))
                    if scelta == 0:
                        return
                    if 1 <= scelta <= len(symbols):
                        break
                    print("Scelta non valida.")
                except ValueError:
                    print("Inserisci un numero valido.")
            
            symbol_selezionato = symbols[scelta - 1]
            
            # Recupera il range di date disponibili
            result = session.query(
                func.min(MarketData.timestamp),
                func.max(MarketData.timestamp)
            ).filter(MarketData.symbol_id == symbol_selezionato.id).first()
            
            min_date, max_date = result
            
            if not min_date or not max_date:
                print("Nessun dato disponibile per questa crypto.")
                return
            
            giorni_totali = (max_date - min_date).days
            print(f"\nGiorni totali disponibili: {giorni_totali}")
            
            # Input giorni da visualizzare
            while True:
                try:
                    giorni = int(input(f"\nQuanti giorni vuoi visualizzare (1-{giorni_totali}): "))
                    if 1 <= giorni <= giorni_totali:
                        break
                    print(f"Inserisci un numero tra 1 e {giorni_totali}.")
                except ValueError:
                    print("Inserisci un numero valido.")
            
            data_inizio = max_date - timedelta(days=giorni)
            
            # Recupera i dati per ogni timeframe
            timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
            
            for timeframe in timeframes:
                print(f"\nDati per timeframe {timeframe}:")
                
                # Calcola il numero di candele attese per questo timeframe
                candles_per_day = get_candles_per_day(timeframe)
                expected_candles = giorni * candles_per_day
                
                market_data = session.query(MarketData).filter(
                    MarketData.symbol_id == symbol_selezionato.id,
                    MarketData.timeframe == timeframe,
                    MarketData.timestamp >= data_inizio,
                    MarketData.timestamp <= max_date
                ).order_by(MarketData.timestamp.desc()).all()
                
                if not market_data:
                    print(f"Nessun dato disponibile per il timeframe {timeframe}")
                    continue
                
                # Prepara i dati per la tabella
                headers = ['Data', 'Open', 'High', 'Low', 'Close', 'Volume']
                rows = [
                    [
                        md.timestamp.strftime('%Y-%m-%d %H:%M'),
                        f"{md.open:.8f}",
                        f"{md.high:.8f}",
                        f"{md.low:.8f}",
                        f"{md.close:.8f}",
                        f"{md.volume:.2f}"
                    ] for md in market_data
                ]
                
                print(tabulate(rows, headers=headers, tablefmt='grid'))
                
        finally:
            session.close()
            
        return "Visualizzazione dati completata"
        
    except Exception as e:
        print(f"Si è verificato un errore: {str(e)}")
        return "Errore durante la visualizzazione dei dati"


def genetic_optimization_placeholder(*args, **kwargs):
    """Placeholder per l'ottimizzazione genetica."""
    print("\n[In Sviluppo] Ottimizzazione genetica dei parametri")
    input("\nPremi INVIO per continuare...")
    return None

# Definizione dei menu items
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

# Istanza del gene manager
gene_manager = GeneManager()

# Menu items per i geni
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

# Aggiorna la lista dei menu disponibili
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
