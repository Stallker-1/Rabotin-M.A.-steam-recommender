import pytest
import requests

BASE_URL = "http://localhost:8000"
FLASK_URL = "http://localhost:5000"


class TestFastAPI:
    
    def test_health_check(self):
        """Проверка эндпоинта /health"""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "model_loaded" in data
    
    def test_predict_endpoint(self):
        """Проверка эндпоинта /predict"""
        payload = {"query": "стратегия", "n_results": 5}
        response = requests.post(f"{BASE_URL}/predict", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert "total" in data
    
    def test_search_by_text(self):
        """Проверка текстового поиска"""
        payload = {"query": "зомби", "n_results": 5}
        response = requests.post(f"{BASE_URL}/search-by-text", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data


class TestFlask:
    
    def test_home_page(self):
        """Проверка главной страницы"""
        response = requests.get(f"{FLASK_URL}/")
        assert response.status_code == 200
    
    def test_login_page(self):
        """Проверка страницы входа"""
        response = requests.get(f"{FLASK_URL}/login")
        assert response.status_code == 200
    
    def test_register_page(self):
        """Проверка страницы регистрации"""
        response = requests.get(f"{FLASK_URL}/register")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])