"""FastAPI приложение для рекомендательной системы Steam"""
import logging
import pickle
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import Config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Глобальная переменная для рекомендательной системы
recommender = None


# ========== Pydantic модели для запросов/ответов ==========

class RecommendRequest(BaseModel):
    """Запрос на рекомендации для пользователя"""
    user_id: int = Field(..., description="ID пользователя", ge=1)
    n_recommendations: int = Field(10, description="Количество рекомендаций", ge=1, le=50)
    use_hybrid: bool = Field(True, description="Использовать гибридный подход")


class SimilarGamesRequest(BaseModel):
    """Запрос на поиск похожих игр"""
    game_id: int = Field(..., description="ID игры в Steam", ge=1)
    n_recommendations: int = Field(10, description="Количество рекомендаций", ge=1, le=50)
    method: str = Field("hybrid", description="Метод: collaborative, content_based, hybrid")


class GenreRecommendRequest(BaseModel):
    """Запрос на рекомендации по жанрам"""
    genres: List[str] = Field(..., description="Предпочитаемые жанры", min_length=1)
    n_recommendations: int = Field(10, description="Количество рекомендаций", ge=1, le=50)


class GameInfo(BaseModel):
    """Информация об игре"""
    game_id: int
    name: str
    genres: List[str] = []
    score: float
    recommendation_type: str


class RecommendResponse(BaseModel):
    """Ответ с рекомендациями"""
    recommendations: List[GameInfo]
    total: int
    method_used: str


class HealthResponse(BaseModel):
    """Проверка здоровья сервиса"""
    status: str
    model_loaded: bool
    model_type: str = ""


class ModelInfoResponse(BaseModel):
    """Информация о модели"""
    model_type: str
    n_users: int = 0
    n_games: int = 0
    algorithms: List[str] = []


# ========== Жизненный цикл приложения ==========

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения - загрузка модели при старте"""
    global recommender
    logger.info("=" * 50)
    logger.info("Загрузка рекомендательной модели...")
    logger.info("=" * 50)
    
    try:
        if Config.MODEL_PATH.exists():
            with open(Config.MODEL_PATH, 'rb') as f:
                recommender = pickle.load(f)
            logger.info(f"✅ Модель успешно загружена из {Config.MODEL_PATH}")
            
            # Вывод статистики модели если есть
            if hasattr(recommender, 'collaborative') and recommender.collaborative:
                logger.info(f"   - Пользователей в модели: {len(recommender.collaborative.user_ids)}")
                logger.info(f"   - Игр в модели: {len(recommender.collaborative.game_ids)}")
        else:
            logger.warning(f"⚠️ Файл модели не найден: {Config.MODEL_PATH}")
            logger.warning("   Модель будет обучена при первом запросе или запустите train_recommender.py")
            recommender = None
            
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки модели: {e}")
        recommender = None
    
    yield
    
    logger.info("Завершение работы приложения")


# ========== Создание FastAPI приложения ==========

app = FastAPI(
    title="Steam Game Recommender API",
    description="Рекомендательная система игр на основе данных Steam с использованием гибридного подхода (ALS Collaborative Filtering + Content-based)",
    version="1.0.0",
    lifespan=lifespan,
)

# Добавление CORS для возможности запросов из Flask
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== Эндпоинты API ==========

@app.get("/", tags=["root"])
async def root() -> Dict[str, str]:
    """Корневой эндпоинт"""
    return {
        "message": "Steam Game Recommender API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Проверка работоспособности сервиса"""
    model_type = "None"
    if recommender:
        model_type = "HybridRecommender"
    elif hasattr(recommender, 'collaborative'):
        model_type = "CollaborativeFiltering"
    
    return HealthResponse(
        status="healthy",
        model_loaded=recommender is not None,
        model_type=model_type
    )


@app.get("/model-info", response_model=ModelInfoResponse, tags=["info"])
async def get_model_info() -> ModelInfoResponse:
    """Информация о загруженной модели"""
    if recommender is None:
        raise HTTPException(status_code=503, detail="Модель не загружена")
    
    n_users = 0
    n_games = 0
    algorithms = []
    
    if hasattr(recommender, 'collaborative') and recommender.collaborative:
        n_users = len(getattr(recommender.collaborative, 'user_ids', []))
        n_games = len(getattr(recommender.collaborative, 'game_ids', []))
        algorithms.append("ALS Collaborative Filtering")
    
    if hasattr(recommender, 'content_based') and recommender.content_based:
        algorithms.append("Content-based Filtering")
    
    algorithms.append("Hybrid Combination")
    
    return ModelInfoResponse(
        model_type="HybridRecommender",
        n_users=n_users,
        n_games=n_games,
        algorithms=algorithms
    )


@app.post("/recommend", response_model=RecommendResponse, tags=["recommendations"])
async def recommend_for_user(request: RecommendRequest) -> RecommendResponse:
    """
    Получение персонализированных рекомендаций для пользователя
    
    - **user_id**: ID пользователя в системе
    - **n_recommendations**: количество рекомендаций (1-50)
    - **use_hybrid**: использовать гибридный подход или только collaborative
    """
    if recommender is None:
        raise HTTPException(status_code=503, detail="Модель не загружена, сервис временно недоступен")
    
    logger.info(f"📊 Запрос рекомендаций для пользователя {request.user_id}")
    
    try:
        recommendations = recommender.recommend_for_user(
            request.user_id,
            request.n_recommendations,
            request.use_hybrid
        )
        
        games = []
        for rec in recommendations:
            games.append(GameInfo(
                game_id=rec['game_id'],
                name=rec.get('name', f"Game_{rec['game_id']}"),
                genres=rec.get('genres', []),
                score=rec.get('hybrid_score', rec.get('relevance_score', rec.get('similarity_score', 0))),
                recommendation_type=rec.get('recommendation_type', 'unknown')
            ))
        
        method = "hybrid" if request.use_hybrid else "collaborative"
        logger.info(f"✅ Рекомендации выданы: {len(games)} игр")
        
        return RecommendResponse(
            recommendations=games,
            total=len(games),
            method_used=method
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка при получении рекомендаций: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/similar", response_model=RecommendResponse, tags=["recommendations"])
async def get_similar_games(request: SimilarGamesRequest) -> RecommendResponse:
    """
    Поиск игр, похожих на указанную
    
    - **game_id**: ID игры для поиска аналогов
    - **n_recommendations**: количество рекомендаций (1-50)
    - **method**: метод поиска (collaborative, content_based, hybrid)
    """
    if recommender is None:
        raise HTTPException(status_code=503, detail="Модель не загружена, сервис временно недоступен")
    
    logger.info(f"🎮 Поиск игр, похожих на ID {request.game_id} методом {request.method}")
    
    try:
        recommendations = recommender.recommend_similar_games(
            request.game_id,
            request.n_recommendations,
            request.method
        )
        
        games = []
        for rec in recommendations:
            games.append(GameInfo(
                game_id=rec['game_id'],
                name=rec.get('name', f"Game_{rec['game_id']}"),
                genres=rec.get('genres', []),
                score=rec.get('similarity_score', 0),
                recommendation_type=rec.get('recommendation_type', 'similar')
            ))
        
        logger.info(f"✅ Найдено {len(games)} похожих игр")
        
        return RecommendResponse(
            recommendations=games,
            total=len(games),
            method_used=request.method
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка при поиске похожих игр: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recommend-by-genres", response_model=RecommendResponse, tags=["recommendations"])
async def recommend_by_genres(request: GenreRecommendRequest) -> RecommendResponse:
    """
    Рекомендации игр на основе предпочитаемых жанров
    
    - **genres**: список предпочитаемых жанров (например, ["Action", "RPG"])
    - **n_recommendations**: количество рекомендаций (1-50)
    """
    if recommender is None:
        raise HTTPException(status_code=503, detail="Модель не загружена, сервис временно недоступен")
    
    logger.info(f"🎭 Рекомендации по жанрам: {request.genres}")
    
    try:
        if hasattr(recommender, 'recommend_by_genres'):
            recommendations = recommender.recommend_by_genres(
                request.genres,
                request.n_recommendations
            )
        else:
            recommendations = []
        
        games = []
        for rec in recommendations:
            games.append(GameInfo(
                game_id=rec['game_id'],
                name=rec.get('name', f"Game_{rec['game_id']}"),
                genres=rec.get('genres', []),
                score=rec.get('genre_match_score', 0),
                recommendation_type=rec.get('recommendation_type', 'genre')
            ))
        
        logger.info(f"✅ Найдено {len(games)} игр по жанрам")
        
        return RecommendResponse(
            recommendations=games,
            total=len(games),
            method_used="genre_based"
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка при рекомендации по жанрам: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/games/search", tags=["games"])
async def search_games(q: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Поиск игр по названию
    
    - **q**: поисковый запрос
    - **limit**: максимальное количество результатов
    """
    # Этот эндпоинт требует доступа к данным игр
    # Реализация может быть добавлена позже
    return []


@app.get("/games/popular", tags=["games"])
async def get_popular_games(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Получение популярных игр
    
    - **limit**: количество популярных игр
    """
    if recommender is None:
        raise HTTPException(status_code=503, detail="Модель не загружена")
    
    try:
        if hasattr(recommender, 'collaborative'):
            popular = recommender.collaborative.get_popular_recommendations(limit)
            return [
                {
                    "game_id": p['game_id'],
                    "name": p.get('name', f"Game_{p['game_id']}"),
                    "genres": p.get('genres', []),
                    "popularity_score": p.get('popularity_score', 0)
                }
                for p in popular
            ]
        return []
    except Exception as e:
        logger.error(f"Ошибка получения популярных игр: {e}")
        return []