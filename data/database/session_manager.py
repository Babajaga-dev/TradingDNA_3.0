"""
Session Manager
--------------
Manager centralizzato per la gestione delle sessioni PostgreSQL.
"""

import time
from contextlib import contextmanager, asynccontextmanager
from typing import Generator, AsyncGenerator, Optional, TypeVar, Type, List
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.ext.declarative import DeclarativeMeta
import yaml

from cli.logger.log_manager import get_logger

# Type variable per i modelli
T = TypeVar('T', bound=DeclarativeMeta)

# Setup logger
logger = get_logger('session_manager')

class DBSessionManager:
    """
    Manager centralizzato per la gestione delle sessioni PostgreSQL.
    Implementa il pattern Singleton per garantire un'unica istanza.
    """
    _instance = None
    _engine: Optional[Engine] = None
    _async_engine = None
    _session_maker: Optional[sessionmaker] = None
    _async_session_maker = None

    def __new__(cls):
        if cls._instance is None:
            print("[DEBUG] Creazione nuova istanza DBSessionManager")
            cls._instance = super(DBSessionManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        print("[DEBUG] Inizializzazione DBSessionManager")
        self._load_config()
        self._setup_engines()
        self._initialized = True
        print("[DEBUG] DBSessionManager inizializzato con successo")

    def _load_config(self) -> None:
        """Carica la configurazione dal file security.yaml"""
        try:
            print("[DEBUG] Caricamento configurazione database")
            with open('config/security.yaml', 'r') as f:
                config = yaml.safe_load(f)
            
            self._config = config.get('database', {})
            self._database_url = self._config.get('url')
            if not self._database_url:
                raise ValueError("URL del database non configurato in security.yaml")
                
            # URL per connessione asincrona (sostituisce postgresql:// con postgresql+asyncpg://)
            self._async_database_url = self._database_url.replace('postgresql://', 'postgresql+asyncpg://')
            print(f"[DEBUG] URL database: {self._database_url}")
            
        except Exception as e:
            print(f"[DEBUG] ERRORE caricamento configurazione database: {str(e)}")
            logger.error(f"Errore caricamento configurazione database: {str(e)}")
            raise

    def _setup_engines(self) -> None:
        """Configura gli engine sincrono e asincrono del database"""
        try:
            print("[DEBUG] Configurazione engine database")
            
            # Engine sincrono con configurazioni da security.yaml
            print("[DEBUG] Creazione engine sincrono")
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
            
            # Rimuovi i parametri None per usare i default di SQLAlchemy
            engine_config = {k: v for k, v in engine_config.items() if v is not None}
            if 'connect_args' in engine_config:
                engine_config['connect_args'] = {
                    k: v for k, v in engine_config['connect_args'].items() if v is not None
                }
            
            self._engine = create_engine(
                self._database_url,
                **engine_config
            )
            
            # Applica i parametri runtime PostgreSQL
            self._apply_runtime_params(self._engine)
            
            self._session_maker = sessionmaker(
                bind=self._engine,
                expire_on_commit=False
            )
            print("[DEBUG] Engine sincrono creato")
            
            # Engine asincrono con le stesse configurazioni
            print("[DEBUG] Creazione engine asincrono")
            self._async_engine = create_async_engine(
                self._async_database_url,
                **engine_config
            )
            
            self._async_session_maker = async_sessionmaker(
                bind=self._async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            print("[DEBUG] Engine asincrono creato")
            
        except Exception as e:
            print(f"[DEBUG] ERRORE configurazione engine: {str(e)}")
            logger.error(f"Errore configurazione engine: {str(e)}")
            raise

    def _apply_runtime_params(self, engine: Engine) -> None:
        """Applica i parametri runtime PostgreSQL dopo la connessione."""
        runtime_params = self._config.get('runtime_params', {})
        if runtime_params:
            try:
                with engine.connect() as conn:
                    for param, value in runtime_params.items():
                        conn.execute(text(f"SET {param} = {value}"))
                    conn.commit()
            except Exception as e:
                print(f"[DEBUG] ERRORE applicazione parametri runtime: {str(e)}")
                logger.error(f"Errore applicazione parametri runtime: {str(e)}")

    @property
    def engine(self) -> Engine:
        """Restituisce l'engine sincrono del database."""
        return self._engine

    @property
    def async_engine(self):
        """Restituisce l'engine asincrono del database."""
        return self._async_engine

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Context manager per la gestione delle sessioni sincrone.
        
        Yields:
            Session: Sessione del database
        """
        session = self._session_maker()
        session_id = id(session)
        start_time = time.time()
        
        try:
            print(f"[DEBUG] Nuova sessione database creata (ID: {session_id})")
            yield session
            session.commit()
            elapsed = time.time() - start_time
            print(f"[DEBUG] Sessione {session_id} committata con successo in {elapsed:.2f}s")
            
        except Exception as e:
            print(f"[DEBUG] ERRORE sessione {session_id}: {str(e)}")
            session.rollback()
            print(f"[DEBUG] Sessione {session_id} rollback eseguito")
            logger.error(f"Errore sessione database: {str(e)}")
            raise
            
        finally:
            session.close()
            elapsed = time.time() - start_time
            print(f"[DEBUG] Sessione {session_id} chiusa dopo {elapsed:.2f}s")

    @asynccontextmanager
    async def async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager per la gestione delle sessioni asincrone.
        
        Yields:
            AsyncSession: Sessione asincrona del database
        """
        session = self._async_session_maker()
        session_id = id(session)
        start_time = time.time()
        
        try:
            print(f"[DEBUG] Nuova sessione asincrona creata (ID: {session_id})")
            yield session
            await session.commit()
            elapsed = time.time() - start_time
            print(f"[DEBUG] Sessione asincrona {session_id} committata in {elapsed:.2f}s")
            
        except Exception as e:
            print(f"[DEBUG] ERRORE sessione asincrona {session_id}: {str(e)}")
            await session.rollback()
            print(f"[DEBUG] Sessione asincrona {session_id} rollback eseguito")
            logger.error(f"Errore sessione asincrona: {str(e)}")
            raise
            
        finally:
            await session.close()
            elapsed = time.time() - start_time
            print(f"[DEBUG] Sessione asincrona {session_id} chiusa dopo {elapsed:.2f}s")

    def get_or_create(self, model: Type[T], **kwargs) -> tuple[T, bool]:
        """
        Ottiene un'istanza esistente o ne crea una nuova se non esiste.
        
        Args:
            model: Classe del modello
            **kwargs: Attributi per filtrare/creare l'istanza
            
        Returns:
            Tuple[instance, created]: Istanza e flag che indica se è stata creata
        """
        with self.session() as session:
            instance = session.query(model).filter_by(**kwargs).first()
            if instance:
                print(f"[DEBUG] Istanza esistente trovata per {model.__name__}")
                return instance, False
            
            instance = model(**kwargs)
            session.add(instance)
            print(f"[DEBUG] Nuova istanza creata per {model.__name__}")
            return instance, True

    def bulk_create(self, model: Type[T], objects: List[dict]) -> List[T]:
        """
        Crea multiple istanze di un modello in bulk.
        
        Args:
            model: Classe del modello
            objects: Lista di dizionari con gli attributi delle istanze
            
        Returns:
            List[T]: Lista delle istanze create
        """
        with self.session() as session:
            instances = [model(**obj) for obj in objects]
            session.bulk_save_objects(instances)
            print(f"[DEBUG] Create {len(instances)} istanze di {model.__name__} in bulk")
            return instances

    def update_or_create(self, model: Type[T], defaults: dict = None, **kwargs) -> tuple[T, bool]:
        """
        Aggiorna un'istanza esistente o ne crea una nuova.
        
        Args:
            model: Classe del modello
            defaults: Valori di default per l'aggiornamento
            **kwargs: Attributi per filtrare/creare l'istanza
            
        Returns:
            Tuple[instance, created]: Istanza e flag che indica se è stata creata
        """
        defaults = defaults or {}
        with self.session() as session:
            instance = session.query(model).filter_by(**kwargs).first()
            if instance:
                for key, value in defaults.items():
                    setattr(instance, key, value)
                print(f"[DEBUG] Istanza di {model.__name__} aggiornata")
                return instance, False
            
            params = {**kwargs, **defaults}
            instance = model(**params)
            session.add(instance)
            print(f"[DEBUG] Nuova istanza di {model.__name__} creata")
            return instance, True

    def delete(self, model: Type[T], **kwargs) -> bool:
        """
        Elimina le istanze che corrispondono ai criteri.
        
        Args:
            model: Classe del modello
            **kwargs: Criteri di filtro
            
        Returns:
            bool: True se almeno un'istanza è stata eliminata
        """
        with self.session() as session:
            count = session.query(model).filter_by(**kwargs).delete()
            print(f"[DEBUG] Eliminate {count} istanze di {model.__name__}")
            return count > 0

    def count(self, model: Type[T], **kwargs) -> int:
        """
        Conta le istanze che corrispondono ai criteri.
        
        Args:
            model: Classe del modello
            **kwargs: Criteri di filtro
            
        Returns:
            int: Numero di istanze trovate
        """
        with self.session() as session:
            count = session.query(model).filter_by(**kwargs).count()
            print(f"[DEBUG] Trovate {count} istanze di {model.__name__}")
            return count

    def exists(self, model: Type[T], **kwargs) -> bool:
        """
        Verifica se esistono istanze che corrispondono ai criteri.
        
        Args:
            model: Classe del modello
            **kwargs: Criteri di filtro
            
        Returns:
            bool: True se esiste almeno un'istanza
        """
        return self.count(model, **kwargs) > 0
