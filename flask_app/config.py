import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://steamuser:steampassword@db:5432/steamdb")
    RECOMMENDER_API_URL = os.environ.get("RECOMMENDER_API_URL", "http://fastapi:8000")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False