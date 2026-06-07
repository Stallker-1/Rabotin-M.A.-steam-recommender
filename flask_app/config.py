import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    
    # Используем SQLite вместо PostgreSQL для локального запуска
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///steam.db")
    
    RECOMMENDER_API_URL = os.environ.get("RECOMMENDER_API_URL", "http://localhost:8000")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False