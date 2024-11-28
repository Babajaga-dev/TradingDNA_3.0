"""
Database Check Utility
---------------------
Verifica e inizializza il database se necessario.
"""

import asyncio
from sqlalchemy import create_engine, inspect, text, delete
from data.database.models import (
    initialize_database,
    engine as async_engine,
    get_session,
    Exchange,
    Symbol,
    MarketData,
    SYNC_DATABASE_URL
)

def check_tables_sync():
    """Verifica la presenza e la struttura delle tabelle usando una connessione sincrona."""
    print("\nTabelle nel database:")
    
    # Crea engine sincrono per l'ispezione
    sync_engine = create_engine(SYNC_DATABASE_URL)
    inspector = inspect(sync_engine)
    existing_tables = inspector.get_table_names()
    
    if not existing_tables:
        print("Nessuna tabella trovata. Inizializzazione database...")
        initialize_database()
        print("Database inizializzato con successo.")
        # Aggiorna la lista delle tabelle dopo l'inizializzazione
        existing_tables = inspector.get_table_names()
    
    for table in existing_tables:
        print(f"\n- {table}")
        columns = inspector.get_columns(table)
        for col in columns:
            print(f"  * {col['name']} ({col['type']})")

async def check_data():
    """Verifica i dati presenti nel database."""
    async with get_session() as session:
        try:
            # Conta gli exchanges
            result = await session.execute(text("SELECT COUNT(*) FROM exchanges"))
            exchange_count = result.scalar()
            print(f"\nNumero di exchanges: {exchange_count}")
            
            # Conta i simboli
            result = await session.execute(text("SELECT COUNT(*) FROM symbols"))
            symbol_count = result.scalar()
            print(f"Numero di simboli: {symbol_count}")
            
            # Conta i dati di mercato totali
            result = await session.execute(text("SELECT COUNT(*) FROM market_data"))
            market_data_count = result.scalar()
            print(f"Numero totale di candele: {market_data_count}")
            
            # Conta candele per timeframe
            result = await session.execute(text("""
                SELECT timeframe, COUNT(*) as count 
                FROM market_data 
                GROUP BY timeframe 
                ORDER BY timeframe
            """))
            print("\nCandele per timeframe:")
            for row in result:
                print(f"- {row[0]}: {row[1]} candele")
            
            # Mostra ultimi dati per ogni timeframe
            print("\nUltimi dati per timeframe:")
            result = await session.execute(text("""
                WITH LastData AS (
                    SELECT 
                        m.*,
                        s.name as symbol_name,
                        ROW_NUMBER() OVER (PARTITION BY m.timeframe ORDER BY m.timestamp DESC) as rn
                    FROM market_data m
                    JOIN symbols s ON m.symbol_id = s.id
                )
                SELECT 
                    timeframe,
                    symbol_name,
                    timestamp,
                    open,
                    high,
                    low,
                    close,
                    volume
                FROM LastData
                WHERE rn = 1
                ORDER BY timeframe
            """))
            for row in result:
                print(f"\n{row[0]} - {row[1]}:")
                print(f"  Timestamp: {row[2]}")
                print(f"  OHLCV: {row[3]}, {row[4]}, {row[5]}, {row[6]}, {row[7]}")
            
            if exchange_count == 0:
                print("\nNessun exchange presente nel database.")
                print("Inserimento exchange di default (Binance)...")
                # Inserisci Binance come exchange di default
                await session.execute(
                    text("""
                    INSERT INTO exchanges (name, is_active, created_at, updated_at)
                    VALUES ('Binance', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """)
                )
                await session.commit()
                print("Exchange Binance inserito con successo.")
            
        except Exception as e:
            print(f"Errore durante il controllo dei dati: {str(e)}")
            raise

async def clean_old_data():
    """Elimina i dati vecchi per i timeframe 1h e 4h."""
    async with get_session() as session:
        try:
            print("\nPulizia dati vecchi...")
            
            # Verifica dati prima della pulizia
            result = await session.execute(text("""
                SELECT timeframe, COUNT(*) 
                FROM market_data 
                WHERE timeframe IN ('1h', '4h') 
                GROUP BY timeframe
            """))
            print("Dati prima della pulizia:")
            for row in result:
                print(f"- {row[0]}: {row[1]} candele")
            
            # Elimina dati 1h e 4h
            result = await session.execute(
                text("DELETE FROM market_data WHERE timeframe IN ('1h', '4h')")
            )
            deleted_count = result.rowcount
            await session.commit()
            
            # Verifica dati dopo la pulizia
            result = await session.execute(text("""
                SELECT timeframe, COUNT(*) 
                FROM market_data 
                WHERE timeframe IN ('1h', '4h') 
                GROUP BY timeframe
            """))
            print("\nDati dopo la pulizia:")
            rows = result.fetchall()
            if not rows:
                print("Nessun dato trovato per timeframe 1h e 4h")
            else:
                for row in rows:
                    print(f"- {row[0]}: {row[1]} candele")
            
            print(f"\nTotale record eliminati: {deleted_count}")
            
        except Exception as e:
            print(f"Errore durante la pulizia dei dati: {str(e)}")
            await session.rollback()
            raise

async def main():
    """Funzione principale per il controllo del database."""
    print("Controllo database in corso...")
    
    try:
        # Usa l'approccio sincrono per controllare le tabelle
        check_tables_sync()
        
        # Usa l'approccio asincrono per controllare i dati
        await check_data()
        
        # Chiedi all'utente se vuole pulire i dati vecchi
        choice = input("\nVuoi eliminare i dati vecchi per i timeframe 1h e 4h? (s/n): ")
        if choice.lower() == 's':
            await clean_old_data()
            print("\nStato del database dopo la pulizia:")
            await check_data()
        
        print("\nControllo database completato con successo.")
    except Exception as e:
        print(f"\nErrore durante il controllo del database: {str(e)}")

if __name__ == "__main__":
    # Crea un nuovo event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Esegui il controllo del database
        loop.run_until_complete(main())
    finally:
        # Chiudi il loop
        loop.close()
