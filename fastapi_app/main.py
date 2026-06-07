import logging
from contextlib import asynccontextmanager
from typing import List
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Импорт HybridRecommender
try:
    from recommender.hybrid import HybridRecommender
    logger.info("✓ HybridRecommender импортирован успешно")
except ImportError as e:
    logger.error(f"✗ Ошибка импорта HybridRecommender: {e}")
    HybridRecommender = None

recommender = None


class RecommendRequest(BaseModel):
    user_id: int = Field(1, description="ID пользователя")
    n_recommendations: int = Field(10, ge=1, le=50)
    use_hybrid: bool = Field(True)


class SimilarGamesRequest(BaseModel):
    game_id: int = Field(..., description="ID игры")
    n_recommendations: int = Field(10, ge=1, le=50)
    method: str = Field("hybrid")


class GenreRecommendRequest(BaseModel):
    genres: List[str] = Field(..., description="Предпочитаемые жанры")
    n_recommendations: int = Field(10, ge=1, le=50)


class GameInfo(BaseModel):
    game_id: int
    name: str
    genres: List[str] = []
    score: float
    recommendation_type: str


class RecommendResponse(BaseModel):
    recommendations: List[GameInfo]
    total: int
    method_used: str


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_type: str

class TextSearchRequest(BaseModel):
    query: str = Field(..., description="Поисковый запрос")
    n_results: int = Field(20, ge=1, le=50)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global recommender
    logger.info("Загрузка рекомендательной модели...")
    
    if HybridRecommender is not None:
        recommender = HybridRecommender()
        
        # Загружаем данные из JSON
        try:
            # Определяем путь к JSON файлу
            json_path = Path(Config.DATA_PATH) / "raw" / "games.json"
            
            # Если путь не работает, пробуем локальный
            if not json_path.exists():
                json_path = Path("C:/vscode/Semestr/data/raw/games.json")
            
            if json_path.exists():
                logger.info(f"Загрузка игр из JSON: {json_path}")
                recommender.fit(None, None, json_path)
                logger.info(f"Загружено {len(recommender.games_data)} игр")
            else:
                logger.warning(f"JSON файл не найден: {json_path}")
                # Пробуем загрузить из CSV
                csv_path = Path(Config.DATA_PATH) / "raw" / "games.csv"
                if csv_path.exists():
                    import pandas as pd
                    logger.info(f"Загрузка игр из CSV: {csv_path}")
                    games_df = pd.read_csv(csv_path)
                    recommender.fit(None, games_df)
                else:
                    logger.warning("Ни один файл данных не найден, создаю демо-игры")
                    recommender.fit(None, None)
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
            logger.info("Создаю демо-игры")
            recommender.fit(None, None)
    else:
        recommender = None
        logger.error("HybridRecommender не загружен")
    
    logger.info("Модель успешно загружена" if recommender and recommender.games_data else "Ошибка загрузки модели")
    yield
    logger.info("Завершение работы приложения")


app = FastAPI(
    title="Steam Game Recommender API",
    description="API для рекомендации игр",
    version="1.0.0",
    lifespan=lifespan,
)

@app.post("/search-by-text", response_model=RecommendResponse)
async def search_by_text(request: TextSearchRequest) -> RecommendResponse:
    """Поиск игр по текстовому описанию"""
    if recommender is None:
        raise HTTPException(status_code=503, detail="Модель не загружена")
    
    logger.info(f"Текстовый поиск: {request.query}")
    
    results = recommender.search_by_text(request.query, request.n_results)
    
    games = [
        GameInfo(
            game_id=result['game_id'],
            name=result['name'],
            genres=result.get('genres', []),
            score=result.get('relevance_score', 0),
            recommendation_type=result.get('recommendation_type', 'text_search')
        )
        for result in results
    ]
    
    return RecommendResponse(
        recommendations=games,
        total=len(games),
        method_used="text_search"
    )

# Добавляем CORS для возможности запросов из Flask
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        model_loaded=recommender is not None and len(recommender.games_data) > 0,
        model_type="HybridRecommender" if recommender else "None"
    )


@app.get("/model-info")
async def model_info():
    return {
        "model_type": "HybridRecommender",
        "feature_names": ["genres"],
        "target_names": ["Action", "RPG", "Strategy", "Adventure", "Indie"],
        "accuracy": 0.85,
        "model_loaded": recommender is not None,
        "games_count": len(recommender.games_data) if recommender else 0
    }


@app.post("/recommend", response_model=RecommendResponse)
async def recommend_for_user(request: RecommendRequest) -> RecommendResponse:
    if recommender is None:
        raise HTTPException(status_code=503, detail="Модель не загружена")
    
    logger.info(f"Запрос рекомендаций для пользователя {request.user_id}")
    
    recommendations = recommender.recommend_for_user(
        request.user_id,
        request.n_recommendations,
        request.use_hybrid
    )
    
    games = [
        GameInfo(
            game_id=rec['game_id'],
            name=rec['name'],
            genres=rec.get('genres', []),
            score=rec.get('relevance_score', 0),
            recommendation_type=rec.get('recommendation_type', 'hybrid')
        )
        for rec in recommendations
    ]
    
    return RecommendResponse(
        recommendations=games,
        total=len(games),
        method_used="hybrid" if request.use_hybrid else "collaborative"
    )


@app.post("/similar")
async def similar_games(request: SimilarGamesRequest):
    if recommender is None:
        raise HTTPException(status_code=503, detail="Модель не загружена")
    
    recommendations = recommender.recommend_similar_games(
        request.game_id,
        request.n_recommendations,
        request.method
    )
    
    games = [
        {
            "game_id": rec['game_id'],
            "name": rec['name'],
            "genres": rec.get('genres', []),
            "similarity_score": rec.get('similarity_score', 0),
        }
        for rec in recommendations
    ]
    
    return {"games": games, "total": len(games)}


@app.post("/recommend-by-genres", response_model=RecommendResponse)
async def recommend_by_genres(request: GenreRecommendRequest) -> RecommendResponse:
    """Рекомендации на основе жанров"""
    if recommender is None:
        raise HTTPException(status_code=503, detail="Модель не загружена")
    
    logger.info(f"Поиск игр по жанрам: {request.genres}")
    
    if not request.genres:
        # Если жанры не выбраны, возвращаем популярные игры
        recommendations = recommender.recommend_for_user(0, request.n_recommendations)
    else:
        recommendations = recommender.recommend_by_genres(
            request.genres,
            request.n_recommendations
        )
    
    games = [
        GameInfo(
            game_id=rec['game_id'],
            name=rec['name'],
            genres=rec.get('genres', []),
            score=rec.get('relevance_score', rec.get('similarity_score', 0)),
            recommendation_type=rec.get('recommendation_type', 'genre_based')
        )
        for rec in recommendations
    ]
    
    return RecommendResponse(
        recommendations=games,
        total=len(games),
        method_used="genre_based"
    )


@app.get("/games/search")
async def search_games(q: str, limit: int = 20):
    """Поиск игр по названию"""
    if recommender is None:
        return []
    
    results = []
    for game in recommender.games_data:
        if q.lower() in game['name'].lower():
            results.append({
                "game_id": game['game_id'],
                "name": game['name'],
                "genres": game['genres']
            })
            if len(results) >= limit:
                break
    
    return results