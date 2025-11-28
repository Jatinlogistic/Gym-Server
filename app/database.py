# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, declarative_base
# from config import settings

# # Create DB engine
# engine = create_engine(settings.DB_URL)

# # Create session
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# # Base model
# Base = declarative_base()

# # Dependency for routes
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Load from .env through settings
DATABASE_URL = settings.DB_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

