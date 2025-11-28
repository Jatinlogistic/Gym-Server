import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "FitnessAI")
    BASE_URL: str = os.getenv("BASE_URL", "")

    # JWT
    # JWT_SECRET: str = os.getenv("JWT_SECRET")
    # JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    # JWT_EXPIRY: int = int(os.getenv("JWT_EXPIRY", 24))
    
    # Groq AI
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    # GROQ_MODEL: str = os.getenv("GROQ_MODEL")

    #Google Api
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    # Database
    DB_URL: str = os.getenv("DB_URL", "")

    # Logging
    # LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")


# Single instance to import anywhere
settings = Settings()
