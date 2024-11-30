"""
PostgreSQL Migration Script
-------------------------
Script per migrare i dati da SQLite a PostgreSQL.
"""

import os
import sys
import time
from urllib.parse import urlparse
from sqlalchemy import create_engine, text, MetaData, Table, inspect
from sqlalchemy.orm import sessionmaker
import psycopg2
import yaml

def load_config():
    """Carica la configurazione del database."""
    try:
        with open('config/security.yaml', 'r') as f:
            config = yaml.safe_load(f)
            return config['database']
    except Exception as e:
        print(f"Errore caricamento configurazione: {str(e)}")
        sys.exit(1)

def create_postgres_db():
    """Crea il database PostgreSQL se non esiste."""
    config = load_config()
    db_url = config['url']
    
    # Parse dell'URL del database
    url = urlparse(db_url)
    db_name = url.path[1:]  # Rimuove lo slash iniziale
    
    # Costruisce URL per database postgres
    postgres_url = f"{url.scheme}://{url.username}:{url.password}@{url.hostname}:{url.port}/postgres"
    
    try:
        # Connessione al database postgres
        conn = psycopg2.connect(postgres_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Verifica se il database esiste
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cur.fetchone()
        
        if not exists:
            print(f"Creazione database {db_name}...")
            cur.execute(f'CREATE DATABASE {db_name}')
            print(f"Database {db_name} creato con successo")
        else:
            print(f"Database {db_name} già esistente")
            
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Errore creazione database: {str(e)}")
        sys.exit(1)

def execute_sql_file(conn, filename):
    """Esegue uno script SQL da file."""
    try:
        cur = conn.cursor()
        with open(filename, 'r') as f:
            sql = f.read()
            cur.execute(sql)
        conn.commit()
        print(f"Script {filename} eseguito con successo")
    except Exception as e:
        print(f"Errore esecuzione {filename}: {str(e)}")
        conn.rollback()
        raise
    finally:
        cur.close()

def reset_database(conn):
    """Resetta il database eliminando tutte le tabelle."""
    try:
        cur = conn.cursor()
        
        # Disabilita temporaneamente i vincoli di foreign key
        cur.execute("SET session_replication_role = 'replica';")
        
        # Elimina tutte le tabelle
        cur.execute("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
            END $$;
        """)
        
        # Riabilita i vincoli di foreign key
        cur.execute("SET session_replication_role = 'origin';")
        
        conn.commit()
        print("Database resettato con successo")
        
    except Exception as e:
        print(f"Errore reset database: {str(e)}")
        conn.rollback()
        raise
    finally:
        cur.close()

def setup_postgres_schema():
    """Configura lo schema PostgreSQL."""
    try:
        config = load_config()
        conn = psycopg2.connect(config['url'])
        
        # Reset database
        print("\nReset database...")
        reset_database(conn)
        
        # Esegue script creazione tabelle base
        print("\nCreazione schema base...")
        execute_sql_file(conn, 'data/database/migrations/create_base_tables_pg.sql')
        
        # Esegue script aggiornamento struttura
        print("\nAggiornamento struttura tabelle...")
        execute_sql_file(conn, 'data/database/migrations/update_tables_structure.sql')
        
        print("\nSchema PostgreSQL configurato con successo")
        
    except Exception as e:
        print(f"Errore setup schema: {str(e)}")
        sys.exit(1)
    finally:
        conn.close()

def get_column_names(engine, table_name):
    """Ottiene i nomi delle colonne di una tabella."""
    inspector = inspect(engine)
    return [col['name'] for col in inspector.get_columns(table_name)]

def convert_row(row, columns):
    """Converte i valori di una riga per PostgreSQL."""
    converted = []
    for i, value in enumerate(row):
        col_name = columns[i].lower()
        # Converti booleani
        if col_name in ('is_active', 'is_valid') and isinstance(value, int):
            converted.append(bool(value))
        else:
            converted.append(value)
    return tuple(converted)

def migrate_data():
    """Migra i dati da SQLite a PostgreSQL."""
    try:
        # Configura connessione SQLite
        sqlite_url = "sqlite:///data/tradingdna.db"
        sqlite_engine = create_engine(sqlite_url)
        
        # Configura connessione PostgreSQL
        config = load_config()
        pg_conn = psycopg2.connect(config['url'])
        pg_cur = pg_conn.cursor()
        
        # Lista delle tabelle da migrare nell'ordine corretto
        tables = [
            'exchanges',  # Prima le tabelle senza foreign keys
            'symbols',    # Dipende da exchanges
            'market_data',  # Dipende da exchanges e symbols
            'populations',  # Indipendente
            'chromosomes',  # Dipende da populations
            'chromosome_genes'  # Dipende da chromosomes
        ]
        
        print("\nInizio migrazione dati...")
        for table in tables:
            print(f"\nMigrazione tabella {table}...")
            
            try:
                # Ottieni nomi colonne
                columns = get_column_names(sqlite_engine, table)
                
                # Leggi dati da SQLite
                with sqlite_engine.connect() as conn:
                    result = conn.execute(text(f"SELECT * FROM {table}"))
                    rows = result.fetchall()
                    
                total = len(rows)
                if total == 0:
                    print(f"Nessun dato da migrare per {table}")
                    continue
                    
                print(f"Trovate {total} righe da migrare")
                
                # Migra in batch
                batch_size = 1000
                column_names = ', '.join(columns)
                placeholders = ', '.join(['%s'] * len(columns))
                
                # Costruisci la query con ON CONFLICT DO NOTHING
                id_column = 'id'
                if table == 'populations':
                    id_column = 'population_id'
                elif table == 'chromosomes':
                    id_column = 'chromosome_id'
                elif table == 'chromosome_genes':
                    id_column = 'chromosome_gene_id'
                    
                query = f"""
                    INSERT INTO {table} ({column_names})
                    VALUES ({placeholders})
                    ON CONFLICT ({id_column}) DO NOTHING
                """
                
                for i in range(0, total, batch_size):
                    batch = rows[i:i + batch_size]
                    # Converti ogni riga
                    values = [convert_row(row, columns) for row in batch]
                    
                    # Inserisci batch in PostgreSQL
                    pg_cur.executemany(query, values)
                    pg_conn.commit()
                    
                    print(f"Migrati {min(i + batch_size, total)}/{total} record")
                    
                print(f"Migrazione {table} completata")
                
            except Exception as e:
                print(f"ERRORE migrazione tabella {table}: {str(e)}")
                pg_conn.rollback()
                continue
            
        print("\nMigrazione completata con successo!")
        
    except Exception as e:
        print(f"Errore migrazione dati: {str(e)}")
        if 'pg_conn' in locals():
            pg_conn.rollback()
        sys.exit(1)
    finally:
        if 'pg_cur' in locals():
            pg_cur.close()
        if 'pg_conn' in locals():
            pg_conn.close()

def main():
    """Funzione principale per la migrazione."""
    start_time = time.time()
    
    print("=== INIZIO MIGRAZIONE A POSTGRESQL ===\n")
    
    # Step 1: Crea database
    print("Step 1: Creazione database PostgreSQL")
    create_postgres_db()
    
    # Step 2: Setup schema
    print("\nStep 2: Setup schema PostgreSQL")
    setup_postgres_schema()
    
    # Step 3: Migrazione dati
    print("\nStep 3: Migrazione dati")
    migrate_data()
    
    elapsed = time.time() - start_time
    print(f"\n=== MIGRAZIONE COMPLETATA IN {elapsed:.2f}s ===")

if __name__ == '__main__':
    main()
