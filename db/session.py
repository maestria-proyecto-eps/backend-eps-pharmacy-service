from sqlalchemy import NullPool, create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import settings
from fastapi import Depends
from core.auth_utils import get_current_user_id
USER = settings.DB_OP_USER
PASSWORD = settings.DB_OP_PASSWORD
HOST = settings.DB_OP_HOST
PORT = settings.DB_OP_PORT
DBNAME = settings.DB_OP_NAME

USER_ADM = settings.DB_ADMIN_USER
PASSWORD_ADM = settings.DB_ADMIN_PASSWORD
HOST_ADM = settings.DB_ADMIN_HOST
PORT_ADM = settings.DB_ADMIN_PORT
DBNAME_ADM = settings.DB_ADMIN_NAME

DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"
DATABASE_URL_ADM = f"postgresql+psycopg2://{USER_ADM}:{PASSWORD_ADM}@{HOST_ADM}:{PORT_ADM}/{DBNAME_ADM}?sslmode=require"

# Crear engine (sincrónico)
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool
)
engineDMA = create_engine(
    DATABASE_URL_ADM,
    poolclass=NullPool
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

SessionLocalAdmin = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engineDMA,
)

Base = declarative_base()
BaseAdmin = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()       
    except Exception:
        db.rollback() 
        raise
    finally:
        db.close()

def get_db_admin():
    db = SessionLocalAdmin()
    try:
        yield db
        db.commit()       
    except Exception:
        db.rollback() 
        raise
    finally:
        db.close()
        
def get_db_audit(
    user_id: int = Depends(get_current_user_id)
):
    db = SessionLocal()

    try:
        db.execute(
            text("SET LOCAL my.app_user_id = :uid"),
            {"uid": str(user_id)}
        )
        yield db
        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()
        
def get_db_admin_audit(
    user_id: int = Depends(get_current_user_id)
):
    db = SessionLocalAdmin()

    try:
        db.execute(
            text("SET LOCAL my.app_user_id = :uid"),
            {"uid": str(user_id)}
        )
        yield db
        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()