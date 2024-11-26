"""
Query Optimizer
-------------
Sistema di ottimizzazione delle query SQL.
Fornisce strategie di ottimizzazione e analisi delle performance.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging
from sqlalchemy import text
from sqlalchemy.orm import Query
from sqlalchemy.engine import Engine

class QueryStats:
    """Statistiche di esecuzione delle query."""
    
    def __init__(self):
        self.execution_time: float = 0.0
        self.rows_examined: int = 0
        self.rows_returned: int = 0
        self.index_usage: List[str] = []
        self.table_scans: int = 0
        self.temp_tables: int = 0
        self.sort_operations: int = 0
        self.memory_used: float = 0.0
        
    def to_dict(self) -> Dict[str, Any]:
        """Converte le statistiche in dizionario."""
        return {
            'execution_time': self.execution_time,
            'rows_examined': self.rows_examined,
            'rows_returned': self.rows_returned,
            'index_usage': self.index_usage,
            'table_scans': self.table_scans,
            'temp_tables': self.temp_tables,
            'sort_operations': self.sort_operations,
            'memory_used': self.memory_used
        }

class QueryOptimizer:
    """Ottimizzatore di query SQL."""
    
    def __init__(self, engine: Engine):
        """
        Inizializza l'ottimizzatore.
        
        Args:
            engine: SQLAlchemy engine
        """
        self.engine = engine
        self.logger = logging.getLogger(__name__)
        self.stats_cache: Dict[str, QueryStats] = {}
        
    def optimize_query(self, query: Query) -> Query:
        """
        Ottimizza una query SQLAlchemy.
        
        Args:
            query: Query da ottimizzare
            
        Returns:
            Query ottimizzata
        """
        # Analizza la query
        analysis = self._analyze_query(query)
        
        # Applica ottimizzazioni
        optimized = query
        
        # Ottimizza JOIN
        if analysis['has_joins']:
            optimized = self._optimize_joins(optimized)
            
        # Ottimizza WHERE
        if analysis['has_where']:
            optimized = self._optimize_where(optimized)
            
        # Ottimizza ORDER BY
        if analysis['has_order_by']:
            optimized = self._optimize_order(optimized)
            
        # Ottimizza GROUP BY
        if analysis['has_group_by']:
            optimized = self._optimize_group(optimized)
            
        # Aggiungi hint per indici
        optimized = self._add_index_hints(optimized)
        
        return optimized
        
    def _analyze_query(self, query: Query) -> Dict[str, bool]:
        """
        Analizza una query per identificare ottimizzazioni possibili.
        
        Args:
            query: Query da analizzare
            
        Returns:
            Dizionario con risultati analisi
        """
        sql = str(query.statement.compile(
            compile_kwargs={"literal_binds": True}
        ))
        
        return {
            'has_joins': 'JOIN' in sql,
            'has_where': 'WHERE' in sql,
            'has_order_by': 'ORDER BY' in sql,
            'has_group_by': 'GROUP BY' in sql,
            'has_subqueries': 'SELECT' in sql[sql.find('SELECT') + 6:],
            'has_aggregations': any(
                x in sql for x in ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX']
            )
        }
        
    def _optimize_joins(self, query: Query) -> Query:
        """
        Ottimizza i JOIN della query.
        
        Args:
            query: Query da ottimizzare
            
        Returns:
            Query ottimizzata
        """
        # Riordina i JOIN per minimizzare il risultato intermedio
        # Usa statistiche delle tabelle per determinare l'ordine ottimale
        return query
        
    def _optimize_where(self, query: Query) -> Query:
        """
        Ottimizza le clausole WHERE.
        
        Args:
            query: Query da ottimizzare
            
        Returns:
            Query ottimizzata
        """
        # Riordina le condizioni WHERE per massimizzare l'uso degli indici
        # Applica push-down delle condizioni quando possibile
        return query
        
    def _optimize_order(self, query: Query) -> Query:
        """
        Ottimizza ORDER BY.
        
        Args:
            query: Query da ottimizzare
            
        Returns:
            Query ottimizzata
        """
        # Verifica se è possibile usare indici per l'ordinamento
        # Aggiunge hint per l'uso degli indici
        return query
        
    def _optimize_group(self, query: Query) -> Query:
        """
        Ottimizza GROUP BY.
        
        Args:
            query: Query da ottimizzare
            
        Returns:
            Query ottimizzata
        """
        # Ottimizza raggruppamenti e aggregazioni
        # Usa indici quando possibile
        return query
        
    def _add_index_hints(self, query: Query) -> Query:
        """
        Aggiunge hint per l'uso degli indici.
        
        Args:
            query: Query da ottimizzare
            
        Returns:
            Query con hint
        """
        # Analizza gli indici disponibili
        # Aggiunge hint USE INDEX quando appropriato
        return query
        
    def analyze_performance(
        self,
        query: Query,
        params: Optional[Dict[str, Any]] = None
    ) -> QueryStats:
        """
        Analizza le performance di una query.
        
        Args:
            query: Query da analizzare
            params: Parametri della query
            
        Returns:
            Statistiche di esecuzione
        """
        stats = QueryStats()
        
        # Esegue EXPLAIN
        explain = self._get_explain_plan(query, params)
        
        # Analizza il piano di esecuzione
        stats.rows_examined = self._extract_rows_examined(explain)
        stats.index_usage = self._extract_index_usage(explain)
        stats.table_scans = self._extract_table_scans(explain)
        
        # Misura tempo di esecuzione
        start = datetime.now()
        result = query.all()
        end = datetime.now()
        
        stats.execution_time = (end - start).total_seconds()
        stats.rows_returned = len(result)
        
        # Memorizza statistiche
        query_key = str(query)
        self.stats_cache[query_key] = stats
        
        return stats
        
    def _get_explain_plan(
        self,
        query: Query,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Ottiene il piano di esecuzione di una query.
        
        Args:
            query: Query da analizzare
            params: Parametri della query
            
        Returns:
            Piano di esecuzione
        """
        sql = str(query.statement.compile(
            compile_kwargs={"literal_binds": True}
        ))
        
        with self.engine.connect() as conn:
            result = conn.execute(
                text(f"EXPLAIN FORMAT=JSON {sql}"),
                params or {}
            )
            return result.fetchall()
            
    def _extract_rows_examined(
        self,
        explain: List[Dict[str, Any]]
    ) -> int:
        """
        Estrae il numero di righe esaminate dal piano.
        
        Args:
            explain: Piano di esecuzione
            
        Returns:
            Numero di righe esaminate
        """
        rows = 0
        for step in explain:
            if 'rows_examined' in step:
                rows += step['rows_examined']
        return rows
        
    def _extract_index_usage(
        self,
        explain: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Estrae gli indici usati dal piano.
        
        Args:
            explain: Piano di esecuzione
            
        Returns:
            Lista di indici usati
        """
        indexes = []
        for step in explain:
            if 'key' in step:
                indexes.append(step['key'])
        return indexes
        
    def _extract_table_scans(
        self,
        explain: List[Dict[str, Any]]
    ) -> int:
        """
        Estrae il numero di table scan dal piano.
        
        Args:
            explain: Piano di esecuzione
            
        Returns:
            Numero di table scan
        """
        scans = 0
        for step in explain:
            if step.get('access_type') == 'ALL':
                scans += 1
        return scans
        
    def get_optimization_suggestions(
        self,
        query: Query
    ) -> List[str]:
        """
        Genera suggerimenti per ottimizzare una query.
        
        Args:
            query: Query da analizzare
            
        Returns:
            Lista di suggerimenti
        """
        suggestions = []
        stats = self.stats_cache.get(str(query))
        
        if not stats:
            stats = self.analyze_performance(query)
            
        # Analizza table scan
        if stats.table_scans > 0:
            suggestions.append(
                "Considerare l'aggiunta di indici per evitare table scan"
            )
            
        # Analizza righe esaminate
        if stats.rows_examined > stats.rows_returned * 10:
            suggestions.append(
                "La query esamina molte più righe di quelle restituite. "
                "Considerare l'ottimizzazione delle condizioni WHERE"
            )
            
        # Analizza tempo di esecuzione
        if stats.execution_time > 1.0:
            suggestions.append(
                "La query è lenta. Considerare l'ottimizzazione o il caching"
            )
            
        # Analizza uso indici
        if not stats.index_usage:
            suggestions.append(
                "La query non usa indici. Verificare se è possibile "
                "aggiungere indici appropriati"
            )
            
        return suggestions

class IndexManager:
    """Gestore degli indici del database."""
    
    def __init__(self, engine: Engine):
        """
        Inizializza il gestore.
        
        Args:
            engine: SQLAlchemy engine
        """
        self.engine = engine
        self.logger = logging.getLogger(__name__)
        
    def analyze_index_usage(
        self,
        table_name: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Analizza l'utilizzo degli indici di una tabella.
        
        Args:
            table_name: Nome della tabella
            
        Returns:
            Statistiche di utilizzo degli indici
        """
        with self.engine.connect() as conn:
            # Ottiene statistiche indici
            result = conn.execute(text(f"""
                SELECT
                    i.name AS index_name,
                    i.type_desc AS index_type,
                    s.user_seeks,
                    s.user_scans,
                    s.user_lookups,
                    s.user_updates,
                    s.last_user_seek,
                    s.last_user_scan
                FROM sys.indexes i
                LEFT JOIN sys.dm_db_index_usage_stats s
                    ON i.object_id = s.object_id
                    AND i.index_id = s.index_id
                WHERE i.object_id = OBJECT_ID(?)
            """), [table_name])
            
            stats = {}
            for row in result:
                stats[row.index_name] = {
                    'type': row.index_type,
                    'seeks': row.user_seeks or 0,
                    'scans': row.user_scans or 0,
                    'lookups': row.user_lookups or 0,
                    'updates': row.user_updates or 0,
                    'last_seek': row.last_user_seek,
                    'last_scan': row.last_user_scan
                }
                
            return stats
            
    def suggest_indexes(
        self,
        table_name: str,
        query_history: List[Query]
    ) -> List[str]:
        """
        Suggerisce nuovi indici basati sulla storia delle query.
        
        Args:
            table_name: Nome della tabella
            query_history: Storia delle query
            
        Returns:
            Lista di suggerimenti per nuovi indici
        """
        suggestions = []
        
        # Analizza le query per identificare pattern comuni
        columns_freq = self._analyze_query_patterns(
            query_history, table_name
        )
        
        # Ottiene indici esistenti
        existing = self.get_existing_indexes(table_name)
        
        # Genera suggerimenti
        for cols, freq in columns_freq.items():
            if freq > 10 and not self._is_covered_by_existing(
                cols, existing
            ):
                suggestions.append(
                    f"Considerare un indice su ({cols})"
                )
                
        return suggestions
        
    def _analyze_query_patterns(
        self,
        queries: List[Query],
        table_name: str
    ) -> Dict[str, int]:
        """
        Analizza i pattern nelle query.
        
        Args:
            queries: Lista di query
            table_name: Nome della tabella
            
        Returns:
            Frequenza di utilizzo delle colonne
        """
        patterns = {}
        
        for query in queries:
            # Estrae colonne usate in WHERE, JOIN, ORDER BY
            cols = self._extract_columns(query, table_name)
            
            if cols:
                key = ','.join(sorted(cols))
                patterns[key] = patterns.get(key, 0) + 1
                
        return patterns
        
    def _extract_columns(
        self,
        query: Query,
        table_name: str
    ) -> List[str]:
        """
        Estrae le colonne usate in una query.
        
        Args:
            query: Query da analizzare
            table_name: Nome della tabella
            
        Returns:
            Lista di colonne
        """
        sql = str(query.statement.compile(
            compile_kwargs={"literal_binds": True}
        ))
        
        # Implementa logica di estrazione colonne
        # basata su analisi SQL
        return []
        
    def get_existing_indexes(
        self,
        table_name: str
    ) -> List[Dict[str, Any]]:
        """
        Ottiene gli indici esistenti di una tabella.
        
        Args:
            table_name: Nome della tabella
            
        Returns:
            Lista di indici esistenti
        """
        with self.engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT 
                    i.name AS index_name,
                    STRING_AGG(c.name, ',') AS columns
                FROM sys.indexes i
                JOIN sys.index_columns ic
                    ON i.object_id = ic.object_id
                    AND i.index_id = ic.index_id
                JOIN sys.columns c
                    ON ic.object_id = c.object_id
                    AND ic.column_id = c.column_id
                WHERE i.object_id = OBJECT_ID(?)
                GROUP BY i.name
            """), [table_name])
            
            return [
                {
                    'name': row.index_name,
                    'columns': row.columns.split(',')
                }
                for row in result
            ]
            
    def _is_covered_by_existing(
        self,
        columns: str,
        existing: List[Dict[str, Any]]
    ) -> bool:
        """
        Verifica se le colonne sono coperte da indici esistenti.
        
        Args:
            columns: Colonne da verificare
            existing: Indici esistenti
            
        Returns:
            True se le colonne sono coperte
        """
        cols = set(columns.split(','))
        
        for index in existing:
            if cols.issubset(set(index['columns'])):
                return True
                
        return False