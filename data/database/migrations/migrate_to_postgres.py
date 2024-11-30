"""
PostgreSQL Migration Script
-------------------------
Script per migrare i dati da SQLite a PostgreSQL.
"""

import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse
import psycopg2
import yaml
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.schema import CreateTable

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
        
        print("\nCreazione schema...")
        cur = conn.cursor()
        
        # Crea la funzione update_timestamp
        print("Creazione funzione update_timestamp...")
        cur.execute("""
            CREATE OR REPLACE FUNCTION update_timestamp()
            RETURNS TRIGGER
            LANGUAGE plpgsql
            AS
            $function$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'UTC';
                RETURN NEW;
            END;
            $function$;
        """)
        
        # Crea le tabelle
        print("Creazione tabelle...")
        cur.execute("""
            CREATE TABLE exchanges (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                is_active BOOLEAN DEFAULT true,
                api_config JSONB DEFAULT '{}',
                rate_limits JSONB DEFAULT '{}',
                supported_features JSONB DEFAULT '[]',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE symbols (
                id SERIAL PRIMARY KEY,
                exchange_id INTEGER NOT NULL REFERENCES exchanges(id) ON DELETE CASCADE,
                name VARCHAR(50) NOT NULL,
                base_asset VARCHAR(20) NOT NULL,
                quote_asset VARCHAR(20) NOT NULL,
                is_active BOOLEAN DEFAULT true,
                trading_config JSONB DEFAULT '{}',
                filters JSONB DEFAULT '{}',
                limits JSONB DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (exchange_id, name)
            );

            CREATE TABLE market_data (
                id SERIAL PRIMARY KEY,
                exchange_id INTEGER NOT NULL REFERENCES exchanges(id) ON DELETE CASCADE,
                symbol_id INTEGER NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
                timeframe VARCHAR(10) NOT NULL,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                open DOUBLE PRECISION NOT NULL,
                high DOUBLE PRECISION NOT NULL,
                low DOUBLE PRECISION NOT NULL,
                close DOUBLE PRECISION NOT NULL,
                volume DOUBLE PRECISION NOT NULL,
                sma_20 DOUBLE PRECISION,
                ema_50 DOUBLE PRECISION,
                rsi_14 DOUBLE PRECISION,
                macd DOUBLE PRECISION,
                macd_signal DOUBLE PRECISION,
                macd_hist DOUBLE PRECISION,
                bb_upper DOUBLE PRECISION,
                bb_middle DOUBLE PRECISION,
                bb_lower DOUBLE PRECISION,
                volatility DOUBLE PRECISION,
                trend_strength DOUBLE PRECISION,
                volume_ma_20 DOUBLE PRECISION,
                technical_indicators JSONB DEFAULT '{}',
                pattern_recognition JSONB DEFAULT '{}',
                market_metrics JSONB DEFAULT '{}',
                is_valid BOOLEAN DEFAULT true,
                validation_errors JSONB DEFAULT '[]',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (exchange_id, symbol_id, timeframe, timestamp)
            );

            CREATE TABLE gene_parameters (
                id SERIAL PRIMARY KEY,
                gene_type VARCHAR(50) NOT NULL,
                parameter_name VARCHAR(50) NOT NULL,
                value VARCHAR(100) NOT NULL,
                validation_rules JSONB DEFAULT '{}',
                optimization_bounds JSONB DEFAULT '{}',
                dependencies JSONB DEFAULT '[]',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (gene_type, parameter_name)
            );
        """)
        
        # Crea i trigger
        print("Creazione trigger...")
        cur.execute("""
            CREATE TRIGGER update_exchanges_timestamp
                BEFORE UPDATE ON exchanges
                FOR EACH ROW
                EXECUTE FUNCTION update_timestamp();

            CREATE TRIGGER update_symbols_timestamp
                BEFORE UPDATE ON symbols
                FOR EACH ROW
                EXECUTE FUNCTION update_timestamp();

            CREATE TRIGGER update_market_data_timestamp
                BEFORE UPDATE ON market_data
                FOR EACH ROW
                EXECUTE FUNCTION update_timestamp();

            CREATE TRIGGER update_gene_parameters_timestamp
                BEFORE UPDATE ON gene_parameters
                FOR EACH ROW
                EXECUTE FUNCTION update_timestamp();
        """)
        
        # Crea gli indici
        print("Creazione indici...")
        cur.execute("""
            CREATE INDEX idx_exchange_lookup ON exchanges (name, is_active);
            CREATE INDEX idx_symbol_lookup ON symbols (exchange_id, name, is_active);
            CREATE INDEX idx_symbol_assets ON symbols (base_asset, quote_asset);
            CREATE INDEX idx_market_data_lookup ON market_data (exchange_id, symbol_id, timeframe, timestamp, is_valid);
            CREATE INDEX idx_market_timestamp ON market_data (timestamp);
            CREATE INDEX idx_market_validation ON market_data (is_valid);
            CREATE INDEX idx_gene_lookup ON gene_parameters (gene_type, parameter_name);
        """)
        
        conn.commit()
        print("Schema PostgreSQL configurato con successo")
        
    except Exception as e:
        print(f"Errore setup schema: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        sys.exit(1)
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

def main():
    """Funzione principale per la migrazione."""
    print("=== INIZIO MIGRAZIONE A POSTGRESQL ===\n")
    
    # Step 1: Crea database
    print("Step 1: Creazione database PostgreSQL")
    create_postgres_db()
    
    # Step 2: Setup schema
    print("\nStep 2: Setup schema PostgreSQL")
    setup_postgres_schema()
    
    print("\n=== MIGRAZIONE COMPLETATA ===")

if __name__ == '__main__':
    main()
