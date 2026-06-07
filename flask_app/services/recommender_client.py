import logging
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)

class RecommenderAPIClient:
    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip('/')
    
    def health_check(self) -> bool:
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def get_recommendations(self, user_id: int, n: int = 10) -> Optional[List[Dict]]:
        try:
            response = requests.post(f"{self.api_url}/recommend", json={"user_id": user_id, "n_recommendations": n}, timeout=10)
            response.raise_for_status()
            return response.json().get("recommendations", [])
        except Exception as e:
            logger.error(f"Error: {e}")
            return None
        
    def get_recommendations_by_genres(self, genres: List[str], n: int = 10) -> Optional[List[Dict]]:
        """Получение рекомендаций по жанрам"""
        try:
            response = requests.post(
                f"{self.api_url}/recommend-by-genres",
                json={"genres": genres, "n_recommendations": n},
                timeout=10
            )
            response.raise_for_status()
            return response.json().get("recommendations", [])
        except Exception as e:
            logger.error(f"Error: {e}")
            return None