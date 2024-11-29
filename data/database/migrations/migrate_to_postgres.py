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

def setup_postgres_schema():
    """Configura lo schema PostgreSQL."""
    try:
        config = load_config()
        conn = psycopg2.connect(config['url'])
        cur = conn.cursor()
        
        print("Creazione schema PostgreSQL...")
        
        # Crea funzione per updated_at
        print("Creazione funzione update_timestamp...")
        cur.execute("""
            CREATE OR REPLACE FUNCTION update_timestamp()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        # Crea tabella exchanges
        print("Creazione tabella exchanges...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS exchanges (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Trigger per exchanges
        cur.execute("""
            DROP TRIGGER IF EXISTS update_exchanges_timestamp ON exchanges;
            CREATE TRIGGER update_exchanges_timestamp
                BEFORE UPDATE ON exchanges
                FOR EACH ROW
                EXECUTE FUNCTION update_timestamp();
        """)
        
        # Crea tabella symbols
        print("Creazione tabella symbols...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS symbols (
                id SERIAL PRIMARY KEY,
                exchange_id INTEGER NOT NULL,
                name VARCHAR(20) NOT NULL,
                base_asset VARCHAR(10) NOT NULL,
                quote_asset VARCHAR(10) NOT NULL,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (exchange_id) REFERENCES exchanges(id),
                UNIQUE (exchange_id, name)
            )
        """)
        
        # Trigger per symbols
        cur.execute("""
            DROP TRIGGER IF EXISTS update_symbols_timestamp ON symbols;
            CREATE TRIGGER update_symbols_timestamp
                BEFORE UPDATE ON symbols
                FOR EACH ROW
                EXECUTE FUNCTION update_timestamp();
        """)
        
        # Crea tabella market_data
        print("Creazione tabella market_data...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                id SERIAL PRIMARY KEY,
                exchange_id INTEGER NOT NULL,
                symbol_id INTEGER NOT NULL,
                timeframe VARCHAR(10) NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                open DOUBLE PRECISION NOT NULL,
                high DOUBLE PRECISION NOT NULL,
                low DOUBLE PRECISION NOT NULL,
                close DOUBLE PRECISION NOT NULL,
                volume DOUBLE PRECISION NOT NULL,
                is_valid BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (exchange_id) REFERENCES exchanges(id),
                FOREIGN KEY (symbol_id) REFERENCES symbols(id)
            )
        """)
        
        # Trigger per market_data
        cur.execute("""
            DROP TRIGGER IF EXISTS update_market_data_timestamp ON market_data;
            CREATE TRIGGER update_market_data_timestamp
                BEFORE UPDATE ON market_data
                FOR EACH ROW
                EXECUTE FUNCTION update_timestamp();
        """)
        
        # Crea tabella populations
        print("Creazione tabella populations...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS populations (
                population_id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                max_size INTEGER NOT NULL,
                current_generation INTEGER DEFAULT 0,
                performance_score DOUBLE PRECISION DEFAULT 0.0,
                diversity_score DOUBLE PRECISION DEFAULT 0.0,
                mutation_rate DOUBLE PRECISION NOT NULL,
                selection_pressure DOUBLE PRECISION NOT NULL,
                generation_interval INTEGER NOT NULL,
                diversity_threshold DOUBLE PRECISION NOT NULL,
                timeframe VARCHAR(10) NOT NULL,
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Trigger per populations
        cur.execute("""
            DROP TRIGGER IF EXISTS update_populations_timestamp ON populations;
            CREATE TRIGGER update_populations_timestamp
                BEFORE UPDATE ON populations
                FOR EACH ROW
                EXECUTE FUNCTION update_timestamp();
        """)
        
        # Crea tabella chromosomes
        print("Creazione tabella chromosomes...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chromosomes (
                chromosome_id SERIAL PRIMARY KEY,
                population_id INTEGER NOT NULL,
                performance_metrics TEXT,
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (population_id) REFERENCES populations(population_id)
            )
        """)
        
        # Trigger per chromosomes
        cur.execute("""
            DROP TRIGGER IF EXISTS update_chromosomes_timestamp ON chromosomes;
            CREATE TRIGGER update_chromosomes_timestamp
                BEFORE UPDATE ON chromosomes
                FOR EACH ROW
                EXECUTE FUNCTION update_timestamp();
        """)
        
        # Crea tabella chromosome_genes
        print("Creazione tabella chromosome_genes...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chromosome_genes (
                gene_id SERIAL PRIMARY KEY,
                chromosome_id INTEGER NOT NULL,
                gene_type VARCHAR(50) NOT NULL,
                parameters TEXT NOT NULL,
                weight DOUBLE PRECISION NOT NULL,
                performance_contribution DOUBLE PRECISION DEFAULT 0.0,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chromosome_id) REFERENCES chromosomes(chromosome_id)
            )
        """)
        
        # Trigger per chromosome_genes
        cur.execute("""
            DROP TRIGGER IF EXISTS update_chromosome_genes_timestamp ON chromosome_genes;
            CREATE TRIGGER update_chromosome_genes_timestamp
                BEFORE UPDATE ON chromosome_genes
                FOR EACH ROW
                EXECUTE FUNCTION update_timestamp();
        """)
        
        # Funzione di validazione per chromosome_genes
        cur.execute("""
            CREATE OR REPLACE FUNCTION validate_chromosome_gene()
            RETURNS TRIGGER AS $$
            BEGIN
                IF NEW.weight < 0 OR NEW.weight > 1 THEN
                    RAISE EXCEPTION 'Weight must be between 0 and 1';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        # Trigger di validazione per chromosome_genes
        cur.execute("""
            DROP TRIGGER IF EXISTS validate_chromosome_gene_insert ON chromosome_genes;
            CREATE TRIGGER validate_chromosome_gene_insert
                BEFORE INSERT ON chromosome_genes
                FOR EACH ROW
                EXECUTE FUNCTION validate_chromosome_gene();
        """)
        
        conn.commit()
        print("Schema PostgreSQL creato con successo")
        
    except Exception as e:
        print(f"Errore setup schema: {str(e)}")
        conn.rollback()
        sys.exit(1)
    finally:
        cur.close()
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
                
                for i in range(0, total, batch_size):
                    batch = rows[i:i + batch_size]
                    # Converti ogni riga
                    values = [convert_row(row, columns) for row in batch]
                    
                    # Inserisci batch in PostgreSQL
                    pg_cur.executemany(
                        f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})",
                        values
                    )
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
