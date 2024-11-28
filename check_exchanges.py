"""
Check Exchanges
--------------
Script per verificare gli exchange nel database.
"""

import asyncio
from sqlalchemy import text
from data.database.models import get_session

async def check_exchanges():
    """Verifica gli exchange nel database."""
    async with get_session() as session:
        # Controlla gli exchange
        result = await session.execute(text("SELECT id, name, is_active FROM exchanges"))
        rows = result.fetchall()
        
        print("\nExchanges nel database:")
        print("------------------------")
        for row in rows:
            print(f"ID: {row[0]}, Nome: {row[1]}, Attivo: {row[2]}")
        
        # Controlla i simboli
        result = await session.execute(text("SELECT id, exchange_id, name FROM symbols"))
        rows = result.fetchall()
        
        print("\nSimboli nel database:")
        print("---------------------")
        for row in rows:
            print(f"ID: {row[0]}, Exchange ID: {row[1]}, Nome: {row[2]}")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(check_exchanges())
    finally:
        loop.close()
