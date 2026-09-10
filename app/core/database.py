"""Capa de acceso a datos: engine, sesiones y Base declarativa.

Equivalente al DataSource + EntityManagerFactory de JPA/Hibernate.
"""
import warnings
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.exc import SAWarning
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# SQLite guarda los Numeric como float; SQLAlchemy avisa de posible perdida de
# precision. Como redondeamos todo el dinero a 2 decimales con Decimal.quantize
# antes de persistir, el aviso no aplica en este proyecto.
warnings.filterwarnings("ignore", category=SAWarning, message=".*Decimal objects natively.*")

es_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine = create_engine(
    settings.DATABASE_URL,
    # SQLite bloquea el uso de una conexion desde varios hilos; FastAPI usa un
    # threadpool para los endpoints sincronos, asi que hay que desactivarlo.
    connect_args={"check_same_thread": False} if es_sqlite else {},
    echo=False,
)

if es_sqlite:

    @event.listens_for(engine, "connect")
    def _activar_claves_foraneas(dbapi_connection, connection_record):
        """SQLite ignora las FK a menos que se activen en cada conexion."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Clase padre de todas las entidades (equivale a @Entity + @MappedSuperclass)."""


def get_db() -> Generator[Session, None, None]:
    """Dependencia de FastAPI: abre una sesion por request y la cierra al final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def crear_tablas() -> None:
    """Equivale a spring.jpa.hibernate.ddl-auto=update (para desarrollo)."""
    from app import models  # noqa: F401  importa las entidades para registrarlas

    Base.metadata.create_all(bind=engine)
