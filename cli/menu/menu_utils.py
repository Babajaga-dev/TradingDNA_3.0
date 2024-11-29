"""
Menu Utilities
------------
Utility per la gestione del menu CLI.
"""

import logging
import os
import time
import sqlite3
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import shutil
from typing import Callable, Optional, Any, Dict, List
from sqlalchemy import create_engine, select, func, text
from sqlalchemy.orm import Session, sessionmaker
from tabulate import tabulate
from rich.panel import Panel

from ..config import get_config_loader
from data.database.models.models import (
    get_session, initialize_gene_parameters,
    MarketData, Symbol, Exchange, SYNC_DATABASE_URL,
    initialize_database
)
from .gene_manager import GeneManager
from .download_manager import DownloadManager
from cli.logger.log_manager import get_logger

# Setup logger
logger = get_logger('menu_utils')

def get_user_input(
    prompt: str,
    validator: Optional[Callable[[str], bool]] = None,
    error_msg: str = "Input non valido",
    default: Optional[str] = None,
    required: bool = True
) -> Optional[str]:
    """
    Ottiene input dall'utente con validazione.
    
    Args:
        prompt: Messaggio da mostrare
        validator: Funzione di validazione (opzionale)
        error_msg: Messaggio di errore
        default: Valore default (opzionale)
        required: Se l'input è obbligatorio
        
    Returns:
        str: Input validato o None
    """
    while True:
        # Mostra prompt con default
        if default:
            user_input = input(f"{prompt} [{default}]: ").strip()
            if not user_input:
                return default
        else:
            user_input = input(f"{prompt}").strip()
            
        # Gestisci input vuoto
        if not user_input:
            if not required:
                return None
            print("Input richiesto")
            continue
            
        # Valida input
        if validator:
            try:
                if validator(user_input):
                    return user_input
                print(error_msg)
            except Exception:
                print(error_msg)
        else:
            return user_input

def print_table(data: list, columns: Optional[list] = None) -> str:
    """
    Formatta dati in una tabella ASCII.
    
    Args:
        data: Lista di dizionari con i dati
        columns: Lista colonne da mostrare (opzionale)
        
    Returns:
        str: Tabella formattata
    """
    if not data:
        return "Nessun dato da visualizzare"
        
    # Usa tutte le colonne se non specificate
    if not columns:
        columns = list(data[0].keys())
        
    # Calcola larghezza colonne
    widths = {col: len(str(col)) for col in columns}
    for row in data:
        for col in columns:
            width = len(str(row.get(col, '')))
            widths[col] = max(widths[col], width)
            
    # Crea separatore
    separator = '+' + '+'.join('-' * (w + 2) for w in widths.values()) + '+'
    
    # Formatta header
    header = '|' + '|'.join(
        f" {col:{widths[col]}} "
        for col in columns
    ) + '|'
    
    # Formatta righe
    rows = []
    for row in data:
        rows.append('|' + '|'.join(
            f" {str(row.get(col, '')):{widths[col]}} "
            for col in columns
        ) + '|')
        
    # Unisci tutto
    table = [
        separator,
        header,
        separator,
        *rows,
        separator
    ]
    
    return '\n'.join(table)

def confirm_action(prompt: str) -> bool:
    """
    Chiede conferma all'utente.
    
    Args:
        prompt: Messaggio da mostrare
        
    Returns:
        bool: True se confermato, False altrimenti
    """
    response = get_user_input(
        f"{prompt} (s/n): ",
        validator=lambda x: x.lower() in ['s', 'n'],
        error_msg="Rispondere 's' o 'n'"
    )
    return response and response.lower() == 's'

def force_close_connections():
    """Forza la chiusura di tutte le connessioni al database."""
    try:
        # Chiudi tutte le connessioni SQLite
        sqlite3.connect(':memory:').close()
        
        # Importa gli engine globali
        from data.database.models.models import engine, sync_engine
        
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
        # Lista aggiornata dei tipi di geni disponibili
        gene_types = ['rsi', 'moving_average', 'macd', 'bollinger', 'stochastic', 'atr']
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
