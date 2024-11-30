"""
Menu Utilities
------------
Utility per la gestione del menu CLI.
"""

import logging
import os
import time
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import shutil
from typing import Callable, Optional, Any, Dict, List
from sqlalchemy import text, func
from tabulate import tabulate
from rich.panel import Panel
import psycopg2
from urllib.parse import urlparse
import yaml

from ..config import get_config_loader
from data.database.session_manager import DBSessionManager
from data.database.models.models import (
    initialize_gene_parameters,
    MarketData, Symbol, Exchange,
    initialize_database
)
from .gene_manager import GeneManager
from .download_manager import DownloadManager
from cli.logger.log_manager import get_logger

# Setup logger
logger = get_logger('menu_utils')

# Ottieni l'istanza del session manager
db = DBSessionManager()

__all__ = [
    'get_user_input',
    'print_table',
    'confirm_action',
    'force_close_connections',
    'shutdown_all_loggers',
    'reset_system',
    'manage_parameters',
    'get_candles_per_day',
    'view_historical_data',
    'genetic_optimization_placeholder'
]

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
                            os.chmod(file, 0o777)
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
        
        # 4. Forza la chiusura delle connessioni
        print("Chiusura connessioni al database...")
        force_close_connections()
        
        # 5. Attendi un momento per permettere la chiusura delle connessioni
        time.sleep(2)
        
        # 6. Reset del database usando il nuovo metodo
        print("Reset del database in corso...")
        from data.database.models.models import reset_database, verify_database_state
        reset_database()  # Questo metodo ora include la verifica
        
        # 7. Verifica lo stato del database
        print("Verifica stato del database...")
        if not verify_database_state():
            raise Exception("Verifica stato database fallita dopo il reset")
        
        # 8. Inserisci Binance con il nome corretto
        print("Configurazione exchange Binance...")
        with db.session() as session:
            # Verifica se Binance esiste già
            result = session.execute(
                text("SELECT id FROM exchanges WHERE name = 'binance'")
            ).fetchone()
            
            if result:
                # Aggiorna l'exchange esistente
                session.execute(
                    text("""
                    UPDATE exchanges 
                    SET is_active = true, 
                        updated_at = CURRENT_TIMESTAMP 
                    WHERE name = 'binance'
                    """)
                )
            else:
                # Inserisci nuovo exchange
                session.execute(
                    text("""
                    INSERT INTO exchanges (name, is_active, created_at, updated_at)
                    VALUES ('binance', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """)
                )
            
        print("Exchange Binance configurato")
        
        # 9. Inizializza i parametri dei geni dai valori di default
        print("Inizializzazione parametri dei geni...")
        try:
            with open("config/gene.yaml", 'r') as f:
                gene_config = yaml.safe_load(f)
                initialize_gene_parameters(gene_config)
            print("Parametri dei geni inizializzati dai valori di default")
        except Exception as e:
            print(f"Avviso: Errore durante l'inizializzazione dei parametri dei geni: {e}")
            print("Il sistema continuerà con i parametri di default")
        
        # 10. Reset dei geni
        print("Reset dei geni in corso...")
        gene_manager = GeneManager()
        # Lista aggiornata dei tipi di geni disponibili
        gene_types = ['rsi', 'moving_average', 'macd', 'bollinger', 'stochastic', 'atr']
        for gene_type in gene_types:
            try:
                gene_manager.reset_gene_params(gene_type)
                print(f"Gene {gene_type} resettato con successo")
            except Exception as e:
                print(f"Avviso: Errore durante il reset del gene {gene_type}: {e}")
        
        # 11. Riconfigura il logging
        print("Riconfigurazione sistema di logging...")
        from cli.logger import setup_logging
        setup_logging("config/logging.yaml")
        
        # 12. Verifica finale
        print("Verifica finale del sistema...")
        if not verify_database_state():
            raise Exception("Verifica finale del sistema fallita")
        
        return "Reset del sistema completato con successo."
        
    except Exception as e:
        error_msg = f"\nErrore durante il reset del sistema: {str(e)}"
        logger.error(error_msg)
        return error_msg

def force_close_connections():
    """Forza la chiusura di tutte le connessioni al database."""
    try:
        # Chiudi l'engine del DBSessionManager
        if hasattr(db.engine, 'dispose'):
            db.engine.dispose()
        
        # Forza il garbage collector
        import gc
        gc.collect()
        
        # Attendi un momento per permettere la chiusura delle connessioni
        time.sleep(5)
        
        # Verifica se ci sono ancora connessioni attive
        try:
            # Carica la configurazione del database da security.yaml
            with open('config/security.yaml', 'r') as f:
                security_config = yaml.safe_load(f)
                db_config = security_config.get('database', {})
                if not db_config:
                    raise ValueError("Configurazione database non trovata in security.yaml")
                
            test_conn = psycopg2.connect(db_config['url'])
            test_conn.close()
        except psycopg2.OperationalError:
            print("Attenzione: Ci sono ancora connessioni attive al database")
            time.sleep(5)
            
    except Exception as e:
        print(f"Errore durante la chiusura delle connessioni: {str(e)}")

def manage_parameters():
    """Gestisce i parametri del sistema."""
    try:
        config = get_config_loader()
        current_config = config.config
        
        # Carica la configurazione del portfolio
        with open('config/portfolio.yaml', 'r') as f:
            portfolio_config = yaml.safe_load(f)
        
        return f"""Parametri correnti:
Log Level: {current_config.get('system', {}).get('log_level', 'N/A')}
Trading Mode: {portfolio_config.get('portfolio', {}).get('mode', 'N/A')}
Symbols: {', '.join(portfolio_config.get('portfolio', {}).get('symbols', []))}
Timeframes: {', '.join(portfolio_config.get('portfolio', {}).get('timeframes', []))}"""
    except Exception as e:
        return f"Errore lettura configurazione: {str(e)}"

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
        with db.session() as session:
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
            
        return "Visualizzazione dati completata"
        
    except Exception as e:
        print(f"Si è verificato un errore: {str(e)}")
        return "Errore durante la visualizzazione dei dati"

def genetic_optimization_placeholder(*args, **kwargs):
    """Placeholder per l'ottimizzazione genetica."""
    print("\n[In Sviluppo] Ottimizzazione genetica dei parametri")
    input("\nPremi INVIO per continuare...")
    return None
