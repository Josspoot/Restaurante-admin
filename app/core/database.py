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


def sembrar_si_hace_falta() -> None:
    """Carga el menú y los usuarios de ejemplo si la base está vacía.

    Existe porque en las plataformas de despliegue gratuitas no hay consola
    para ejecutar `python seed.py` a mano: sin esto la aplicación arranca con
    la base creada pero sin un solo usuario, y nadie puede entrar.
    """
    if not settings.SEMBRAR_INICIAL:
        return

    from sqlalchemy import func, select

    from app.models import Usuario

    with SessionLocal() as db:
        if db.scalar(select(func.count(Usuario.id))):
            return  # ya hay datos: no se toca nada

    import seed

    seed.main()
