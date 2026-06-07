import os
from pathlib import Path

class Config:
    """Конфигурация FastAPI приложения"""
    
    # Пути к данным
    DATA_PATH: Path = Path(os.getenv("DATA_PATH", "/app/data"))
    MODEL_PATH: Path = Path(os.getenv("MODEL_PATH", "/app/recommender/model.pkl"))
    
    # Настройки модели
    ALS_FACTORS: int = int(os.getenv("ALS_FACTORS", "50"))
    ALS_REGULARIZATION: float = float(os.getenv("ALS_REGULARIZATION", "0.01"))
    ALS_ITERATIONS: int = int(os.getenv("ALS_ITERATIONS", "20"))
    
    # Гиперпараметры гибридной модели
    HYBRID_ALPHA: float = float(os.getenv("HYBRID_ALPHA", "0.7"))  # Вес collaborative фильтрации
    
    # Логирование
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")