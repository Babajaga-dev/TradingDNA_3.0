"""
Fix Signals Genes
---------------
Script per correggere i geni di tipo 'signals' nel database.
"""

from sqlalchemy import create_engine, text

def fix_signals_genes():
    try:
        # Connessione al database
        engine = create_engine('postgresql://postgres:ninja@localhost:5432/tradingdna')
        
        # Disattiva i geni di tipo 'signals'
        with engine.connect() as conn:
            result = conn.execute(
                text('UPDATE chromosome_genes SET is_active = false WHERE gene_type = :gene_type'),
                {"gene_type": "signals"}
            )
            conn.commit()
            print(f"Disattivati {result.rowcount} geni di tipo 'signals'")
            
    except Exception as e:
        print(f"Errore durante la correzione dei geni: {str(e)}")

if __name__ == "__main__":
    fix_signals_genes()
