from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Remplacez par vos vrais identifiants
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:Mohamed2001@localhost:5433/Patch"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dépendance pour obtenir la session de DB dans les routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()