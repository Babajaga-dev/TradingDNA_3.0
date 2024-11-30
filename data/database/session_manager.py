"""
Database Session Manager
-----------------------
Manager centralizzato per la gestione delle sessioni PostgreSQL con gestione robusta
della serializzazione dei dati e pattern Singleton.
"""

import time
import json
from typing import Generator, AsyncGenerator, Optional, TypeVar, Type, List, Any, Dict
from contextlib import contextmanager, asynccontextmanager

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine, Engine, text, inspect
from sqlalchemy.ext.declarative import DeclarativeMeta
import yaml

from .utils import get_db_logger

# Type variable per i modelli
T = TypeVar('T', bound=DeclarativeMeta)

# Setup logger
logger = get_db_logger('session_manager')

class SerializationError(Exception):
    """Eccezione sollevata per errori di serializzazione."""
    pass

class DBSessionManager:
    """
    Manager centralizzato per la gestione delle sessioni PostgreSQL.
    Implementa il pattern Singleton per garantire un'unica istanza.
    """
    _instance = None
    _initialized = False
    
    # Campi che potrebbero contenere dati JSON o strutture complesse
    SERIALIZABLE_FIELDS = {
        'parameters', 'mutation_history', 'validation_rules',
        'performance_metrics', 'weight_distribution', 'test_results',
        'generation_stats', 'mutation_stats', 'selection_stats',
        'performance_breakdown', 'pivot_points', 'validation_details',
        'api_config', 'rate_limits', 'supported_features',
        'trading_config', 'filters', 'limits',
        'technical_indicators', 'pattern_recognition', 'market_metrics',
        'evolution_config', 'performance_thresholds', 'optimization_settings',
        'fitness_history', 'optimization_history', 'fitness_distribution',
        'population_metrics', 'detailed_metrics', 'risk_metrics',
        'trade_statistics'
    }

    def __new__(cls):
        if cls._instance is None:
            logger.debug("Creating new DBSessionManager instance")
            cls._instance = super(DBSessionManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        logger.debug("Initializing DBSessionManager")
        self._load_config()
        self._setup_engines()
        self._initialized = True
        logger.info("DBSessionManager initialized successfully")

    @property
    def engine(self) -> Engine:
        """
        Restituisce l'engine sincrono del database.
        
        Returns:
            Engine: SQLAlchemy Engine instance
        """
        return self._engine

    def _load_config(self) -> None:
        """Carica la configurazione dal file security.yaml con gestione errori migliorata."""
        try:
            logger.debug("Loading database configuration")
            with open('config/security.yaml', 'r') as f:
                config = yaml.safe_load(f)
            
            if not isinstance(config, dict) or 'database' not in config:
                raise ValueError("Invalid configuration format in security.yaml")
                
            self._config = config.get('database', {})
            self._database_url = self._config.get('url')
            
            if not self._database_url:
                raise ValueError("Database URL not configured in security.yaml")
                
            self._async_database_url = self._database_url.replace(
                'postgresql://', 
                'postgresql+asyncpg://'
            )
            
            logger.info("Database configuration loaded successfully")
            
        except FileNotFoundError:
            logger.error("security.yaml configuration file not found")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing security.yaml: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading configuration: {e}")
            raise

    def _setup_engines(self) -> None:
        """Configura gli engine del database con gestione errori migliorata."""
        try:
            logger.debug("Setting up database engines")
            
            engine_config = self._prepare_engine_config()
            
            # Engine sincrono
            self._engine = create_engine(
                self._database_url,
                **engine_config
            )
            
            # Applica i parametri runtime
            self._apply_runtime_params(self._engine)
            
            self._session_maker = sessionmaker(
                bind=self._engine,
                expire_on_commit=False,
                autoflush=False
            )
            
            # Engine asincrono
            self._async_engine = create_async_engine(
                self._async_database_url,
                **engine_config
            )
            
            self._async_session_maker = async_sessionmaker(
                bind=self._async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False
            )
            
            logger.info("Database engines configured successfully")
            
        except Exception as e:
            logger.error(f"Error setting up database engines: {e}")
            raise

    def _prepare_engine_config(self) -> Dict[str, Any]:
        """Prepara la configurazione dell'engine rimuovendo valori None."""
        engine_config = {
            'pool_size': self._config.get('pool_size'),
            'max_overflow': self._config.get('max_overflow'),
            'pool_timeout': self._config.get('pool_timeout'),
            'pool_recycle': self._config.get('pool_recycle'),
            'echo': self._config.get('echo'),
            'isolation_level': self._config.get('isolation_level'),
            'pool_pre_ping': self._config.get('pool_pre_ping'),
            'connect_args': self._config.get('connect_args', {})
        }
        
        # Rimuovi parametri None
        engine_config = {k: v for k, v in engine_config.items() if v is not None}
        
        if 'connect_args' in engine_config:
            engine_config['connect_args'] = {
                k: v for k, v in engine_config['connect_args'].items() 
                if v is not None
            }
            
        return engine_config

    def _apply_runtime_params(self, engine: Engine) -> None:
        """
        Applica parametri runtime all'engine del database.
        
        Args:
            engine: SQLAlchemy Engine instance
        """
        try:
            logger.debug("Applying runtime parameters to database engine")
            
            # Ottieni i parametri runtime dalla configurazione
            runtime_params = self._config.get('runtime_params', {})
            
            if not runtime_params:
                logger.debug("No runtime parameters to apply")
                return
                
            # Applica i parametri usando una connessione raw
            with engine.connect() as conn:
                for param, value in runtime_params.items():
                    try:
                        conn.execute(text(f"SET {param} = :value"), {"value": value})
                        logger.debug(f"Applied runtime parameter: {param} = {value}")
                    except Exception as e:
                        logger.warning(f"Failed to apply runtime parameter {param}: {e}")
                        
            logger.info("Runtime parameters applied successfully")
            
        except Exception as e:
            logger.error(f"Error applying runtime parameters: {e}")
            raise

    def _serialize_field(self, value: Any) -> Optional[str]:
        """
        Serializza un campo in formato JSON se necessario.
        
        Args:
            value: Valore da serializzare
            
        Returns:
            str: Valore serializzato o None
        """
        if value is None:
            return None
            
        try:
            if isinstance(value, (dict, list)):
                return json.dumps(value)
            if isinstance(value, (int, float, bool)):
                return str(value)
            if isinstance(value, str):
                # Verifica se è già JSON
                try:
                    json.loads(value)
                    return value
                except:
                    return value
            # Per altri tipi, prova a convertirli in stringa
            return str(value)
        except (TypeError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Serialization error: {e}")
            raise SerializationError(f"Could not serialize value: {value}") from e

    def _prepare_objects_for_commit(self, session: Session) -> None:
        """
        Prepara tutti gli oggetti nella sessione per il commit.
        
        Args:
            session: Sessione SQLAlchemy
        """
        for obj in session:
            if isinstance(obj, DeclarativeMeta):
                mapper = inspect(obj.__class__)
                for field in self.SERIALIZABLE_FIELDS:
                    if hasattr(obj, field) and field in mapper.columns:
                        value = getattr(obj, field)
                        try:
                            serialized = self._serialize_field(value)
                            setattr(obj, field, serialized)
                        except SerializationError as e:
                            logger.error(f"Error preparing {field} for commit: {e}")
                            raise

    def _handle_session_error(
        self, 
        session: Session, 
        error: Exception,
        session_id: int
    ) -> None:
        """
        Gestisce gli errori della sessione in modo centralizzato.
        
        Args:
            session: Sessione SQLAlchemy
            error: Eccezione sollevata
            session_id: ID della sessione
        """
        logger.error(f"Session {session_id} error: {str(error)}")
        logger.debug(f"Error details: {error.__class__.__name__}, {error.args}")
        logger.debug(f"Session state before rollback: {session.is_active}")
        
        try:
            session.rollback()
            logger.debug(f"Session {session_id} rollback completed")
        except Exception as rollback_error:
            logger.error(f"Rollback error: {str(rollback_error)}")
        
        raise error

    def reset_database(self) -> None:
        """Resetta il database eliminando e ricreando tutte le tabelle."""
        try:
            logger.info("Resetting database...")
            
            # Disabilita temporaneamente i vincoli di foreign key
            with self._engine.connect() as conn:
                conn.execute(text("SET session_replication_role = 'replica';"))
                
                # Elimina tutte le tabelle
                conn.execute(text("""
                    DO $$ DECLARE
                        r RECORD;
                    BEGIN
                        FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                            EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                        END LOOP;
                    END $$;
                """))
                
                # Riabilita i vincoli di foreign key
                conn.execute(text("SET session_replication_role = 'origin';"))
                conn.commit()
            
            # Ricrea tutte le tabelle
            from data.database.models.models import Base
            Base.metadata.create_all(self._engine)
            
            logger.info("Database reset completed successfully")
            
        except Exception as e:
            logger.error(f"Error resetting database: {e}")
            raise

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Context manager per sessioni sincrone con gestione errori migliorata."""
        session = self._session_maker()
        session_id = id(session)
        start_time = time.time()
        
        logger.debug(f"Opening new database session (ID: {session_id})")
        
        try:
            yield session
            
            logger.debug(f"Preparing session {session_id} for commit")
            self._prepare_objects_for_commit(session)
            
            session.commit()
            elapsed = time.time() - start_time
            logger.info(f"Session {session_id} committed successfully in {elapsed:.2f}s")
            
        except Exception as e:
            self._handle_session_error(session, e, session_id)
            
        finally:
            session.close()
            elapsed = time.time() - start_time
            logger.debug(f"Session {session_id} closed after {elapsed:.2f}s")

    @asynccontextmanager
    async def async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Context manager per sessioni asincrone con gestione errori migliorata."""
        session = self._async_session_maker()
        session_id = id(session)
        start_time = time.time()
        
        logger.debug(f"Opening new async session (ID: {session_id})")
        
        try:
            yield session
            
            logger.debug(f"Preparing async session {session_id} for commit")
            self._prepare_objects_for_commit(session)
            
            await session.commit()
            elapsed = time.time() - start_time
            logger.info(f"Async session {session_id} committed in {elapsed:.2f}s")
            
        except Exception as e:
            self._handle_session_error(session, e, session_id)
            
        finally:
            await session.close()
            elapsed = time.time() - start_time
            logger.debug(f"Async session {session_id} closed after {elapsed:.2f}s")

    def get_or_create(self, model: Type[T], **kwargs) -> tuple[T, bool]:
        """
        Ottiene un'istanza esistente o ne crea una nuova con gestione errori migliorata.
        
        Args:
            model: Classe del modello
            **kwargs: Attributi per filtrare/creare l'istanza
            
        Returns:
            Tuple[instance, created]: Istanza e flag che indica se è stata creata
        """
        with self.session() as session:
            try:
                instance = session.query(model).filter_by(**kwargs).first()
                if instance:
                    logger.debug(f"Found existing instance of {model.__name__}")
                    return instance, False
                
                instance = model(**kwargs)
                session.add(instance)
                logger.debug(f"Created new instance of {model.__name__}")
                return instance, True
                
            except Exception as e:
                logger.error(f"Error in get_or_create for {model.__name__}: {e}")
                raise

    def bulk_create(self, model: Type[T], objects: List[dict]) -> List[T]:
        """
        Crea multiple istanze di un modello in bulk con gestione errori migliorata.
        
        Args:
            model: Classe del modello
            objects: Lista di dizionari con gli attributi
            
        Returns:
            List[T]: Lista delle istanze create
        """
        with self.session() as session:
            try:
                instances = [model(**obj) for obj in objects]
                session.bulk_save_objects(instances)
                logger.info(f"Bulk created {len(instances)} instances of {model.__name__}")
                return instances
                
            except Exception as e:
                logger.error(f"Error in bulk_create for {model.__name__}: {e}")
                raise

    def exists(self, model: Type[T], **kwargs) -> bool:
        """
        Verifica se esistono istanze che corrispondono ai criteri.
        
        Args:
            model: Classe del modello
            **kwargs: Criteri di filtro
            
        Returns:
            bool: True se esiste almeno un'istanza
        """
        with self.session() as session:
            return session.query(model).filter_by(**kwargs).first() is not None
