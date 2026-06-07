import os
from pathlib import Path

class Config:
    """Конфигурация FastAPI приложения"""
    
    # Пути к данным
    DATA_PATH: Path = Path(os.getenv("DATA_PATH", "/app/data"))
    MODEL_PATH: Path = Path(os.getenv("MODEL_PATH", "/app/recommender/model.pkl"))
    
    # Для локального запуска без Docker - проверяем и исправляем путь
    if not DATA_PATH.exists() and DATA_PATH == Path("/app/data"):
        # Пробуем найти локальную папку data
        local_data = Path("C:/vscode/Semestr/data")
        if local_data.exists():
            DATA_PATH = local_data
        else:
            # Ищем относительно текущего файла
            current_dir = Path(__file__).parent.parent
            local_data = current_dir / "data"
            if local_data.exists():
                DATA_PATH = local_data
    
    # Настройки модели
    ALS_FACTORS: int = int(os.getenv("ALS_FACTORS", "50"))
    ALS_REGULARIZATION: float = float(os.getenv("ALS_REGULARIZATION", "0.01"))
    ALS_ITERATIONS: int = int(os.getenv("ALS_ITERATIONS", "20"))
    
    # Гиперпараметры гибридной модели
    HYBRID_ALPHA: float = float(os.getenv("HYBRID_ALPHA", "0.7"))  # Вес collaborative фильтрации
    
    # Логирование
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")