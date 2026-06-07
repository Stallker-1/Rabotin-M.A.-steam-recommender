import logging
import random
import json
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd

logger = logging.getLogger(__name__)

class HybridRecommender:
    def __init__(self, alpha=0.7):
        self.alpha = alpha
        self.games_data = []
        logger.info("HybridRecommender initialized")
    
    def load_games_from_json(self, json_path: Path):
        """Загрузка игр из JSON файла"""
        self.games_data = []
        
        if not json_path.exists():
            logger.error(f"JSON файл не найден: {json_path}")
            return self._create_demo_games()
        
        logger.info(f"Загрузка игр из JSON: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        games_loaded = 0
        for app_id, game_data in data.items():
            if not isinstance(game_data, dict):
                continue
            
            name = game_data.get('name', '')
            if not name or len(name) < 2:
                continue
            
            genres = []
            if 'genres' in game_data and game_data['genres']:
                genres = game_data['genres']
            elif 'tags' in game_data and game_data['tags']:
                tags = game_data['tags']
                if isinstance(tags, dict):
                    sorted_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)
                    genres = [tag for tag, _ in sorted_tags]
                elif isinstance(tags, list):
                    genres = tags
            
            if not genres:
                continue
            
            genres = [str(g).strip() for g in genres if g and str(g).strip()]
            
            popularity = 50
            if 'recommendations' in game_data and game_data['recommendations']:
                try:
                    popularity = min(100, int(game_data['recommendations']) // 100)
                except:
                    pass
            elif 'positive' in game_data and game_data['positive']:
                try:
                    pos = int(game_data['positive'])
                    neg = int(game_data.get('negative', 0))
                    if pos + neg > 0:
                        popularity = int((pos / (pos + neg)) * 100)
                except:
                    pass
            
            price = game_data.get('price', 0)
            description = game_data.get('short_description', '') or game_data.get('about_the_game', '')[:200]
            header_image = f"https://steamcdn-a.akamaihd.net/steam/apps/{app_id}/header.jpg"
            
            self.games_data.append({
                'game_id': int(app_id),
                'name': name,
                'genres': genres,
                'popularity': popularity,
                'price': float(price) if price else 0,
                'description': description[:300],
                'image_url': header_image,
                'release_date': game_data.get('release_date', '')
            })
            
            games_loaded += 1
            if games_loaded % 1000 == 0:
                logger.info(f"Прогресс: загружено {games_loaded} игр...")
        
        logger.info(f"Загружено {len(self.games_data)} игр из JSON")
        
        if self.games_data:
            logger.info(f"Пример игры: ID={self.games_data[0]['game_id']}, Name={self.games_data[0]['name']}")
        else:
            logger.warning("Не найдено игр в JSON, создаю демо-игры")
            self._create_demo_games()
        
        return self.games_data
    
    def load_games_from_csv(self, games_df: pd.DataFrame):
        """Загрузка игр из CSV (резервный вариант)"""
        self.games_data = []
        
        id_col = 'AppID'
        name_col = 'Name'
        genres_col = 'Genres'
        
        logger.info(f"Загрузка из CSV: ID={id_col}, Название={name_col}, Жанры={genres_col}")
        
        for idx, row in games_df.iterrows():
            name = row[name_col] if pd.notna(row[name_col]) else None
            if not name or len(str(name)) < 3:
                continue
            
            name_str = str(name).strip()
            
            if any(month in name_str for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']):
                if ',' in name_str:
                    continue
            
            game_id = row[id_col]
            try:
                game_id = int(game_id)
            except (ValueError, TypeError):
                continue
            
            genres = []
            if pd.notna(row[genres_col]):
                genres_str = str(row[genres_col])
                if ',' in genres_str:
                    genres = [g.strip() for g in genres_str.split(',')]
                else:
                    genres = [genres_str]
            
            if not genres:
                continue
            
            self.games_data.append({
                'game_id': game_id,
                'name': name_str,
                'genres': genres,
                'popularity': random.randint(1, 100),
                'price': 0,
                'description': '',
                'image_url': f"https://steamcdn-a.akamaihd.net/steam/apps/{game_id}/header.jpg",
                'release_date': ''
            })
            
            if len(self.games_data) >= 500:
                break
        
        logger.info(f"Загружено {len(self.games_data)} игр из CSV")
        return self.games_data
    
    def fit(self, interactions_df, games_df=None, json_path=None):
        """Обучение модели"""
        if json_path and Path(json_path).exists():
            self.load_games_from_json(Path(json_path))
        elif games_df is not None:
            self.load_games_from_csv(games_df)
        else:
            self._create_demo_games()
        
        logger.info(f"Model fit completed. Всего игр: {len(self.games_data)}")
        return self
    
    def _create_demo_games(self):
        """Создание демонстрационных игр"""
        demo_games = [
            (730, "Counter-Strike: Global Offensive", ["Action", "Shooter"], 95),
            (570, "Dota 2", ["Strategy", "MOBA"], 90),
            (440, "Team Fortress 2", ["Action", "Shooter"], 85),
            (10, "Half-Life", ["Action", "FPS"], 88),
            (220, "Half-Life 2", ["Action", "FPS"], 92),
            (400, "Portal", ["Puzzle", "Action"], 96),
            (500, "Left 4 Dead 2", ["Action", "Horror"], 94),
            (240, "BioShock", ["Action", "RPG"], 91),
            (1050, "The Witcher 3", ["RPG", "Adventure"], 98),
            (377160, "Fallout 4", ["RPG", "Action"], 87),
            (578080, "PUBG", ["Action", "Shooter"], 82),
            (252950, "Rocket League", ["Sports", "Action"], 89),
        ]
        
        for game_id, name, genres, popularity in demo_games:
            self.games_data.append({
                'game_id': game_id,
                'name': name,
                'genres': genres,
                'popularity': popularity,
                'price': 0,
                'description': f"Популярная игра {name}",
                'image_url': f"https://steamcdn-a.akamaihd.net/steam/apps/{game_id}/header.jpg",
                'release_date': ''
            })
        logger.info(f"Создано {len(self.games_data)} демо-игр")
    
    def recommend_for_user(self, user_id, n_recommendations=10, use_hybrid=True):
        """Рекомендации для пользователя"""
        if not self.games_data:
            return []
        
        sorted_games = sorted(self.games_data, key=lambda x: x['popularity'], reverse=True)
        recommendations = []
        
        for game in sorted_games[:n_recommendations]:
            recommendations.append({
                "game_id": game['game_id'],
                "name": game['name'],
                "genres": game['genres'],
                "relevance_score": game['popularity'] / 100,
                "recommendation_type": "popular"
            })
        
        return recommendations
    
    def recommend_by_genres(self, preferred_genres: List[str], n_recommendations: int = 10):
        """Рекомендации на основе жанров"""
        if not preferred_genres or not self.games_data:
            return self.recommend_for_user(0, n_recommendations)
        
        scored_games = []
        for game in self.games_data:
            matches = set(game['genres']) & set(preferred_genres)
            score = len(matches) / max(len(preferred_genres), 1)
            
            if score > 0:
                scored_games.append((game, score))
        
        scored_games.sort(key=lambda x: x[1], reverse=True)
        
        recommendations = []
        for game, score in scored_games[:n_recommendations]:
            recommendations.append({
                "game_id": game['game_id'],
                "name": game['name'],
                "genres": game['genres'],
                "relevance_score": score,
                "recommendation_type": "genre_based"
            })
        
        return recommendations
    
    def recommend_similar_games(self, game_id, n_recommendations=10, method="hybrid"):
        """Похожие игры по жанрам"""
        if not self.games_data:
            return []
        
        target_game = None
        for game in self.games_data:
            if game['game_id'] == game_id:
                target_game = game
                break
        
        if not target_game:
            return []
        
        scored = []
        for game in self.games_data:
            if game['game_id'] == game_id:
                continue
            matches = set(game['genres']) & set(target_game['genres'])
            score = len(matches) / max(len(target_game['genres']), 1)
            if score > 0:
                scored.append((game, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        recommendations = []
        for game, score in scored[:n_recommendations]:
            recommendations.append({
                "game_id": game['game_id'],
                "name": game['name'],
                "genres": game['genres'],
                "similarity_score": score,
                "recommendation_type": "similar_games"
            })
        
        return recommendations
    
    def search_by_text(self, query: str, n_results: int = 30) -> List[Dict]:
        """Поиск игр с поддержкой русского и английского языка"""
        if not self.games_data:
            return []
        
        query_lower = query.lower()
        
        # Словарь перевода ключевых слов
        translations = {
            'стратегия': ['strategy', 'strategic', 'rts', 'tactical', 'tower defense', 'base building'],
            'зомби': ['zombie', 'zombies', 'undead', 'infected', 'walking dead'],
            'выживание': ['survival', 'survive', 'crafting'],
            'ролевая': ['rpg', 'role playing', 'roleplaying'],
            'шутер': ['shooter', 'fps', 'action'],
            'симулятор': ['simulator', 'simulation', 'sim'],
            'приключение': ['adventure', 'quest', 'exploration'],
            'хоррор': ['horror', 'scary', 'terror'],
        }
        
        # Разбираем запрос на слова
        query_words = query_lower.split()
        
        # Расширяем поисковые слова с учётом перевода
        search_words = set()
        for word in query_words:
            if len(word) < 3:
                continue
            search_words.add(word)
            # Добавляем переводы
            for russian, english_list in translations.items():
                if word == russian or word in russian:
                    for eng in english_list:
                        search_words.add(eng)
                for eng in english_list:
                    if word == eng or word in eng:
                        search_words.add(russian)
                        search_words.add(eng)
        
        logger.info(f"Поисковые слова (с переводами): {search_words}")
        
        scored = []
        for game in self.games_data:
            name_lower = game['name'].lower()
            genres_lower = ' '.join(game['genres']).lower()
            description_lower = game.get('description', '').lower()
            full_text = f"{name_lower} {genres_lower} {description_lower}"
            
            # Проверяем наличие ВСЕХ исходных слов (или их переводов)
            all_found = True
            for original_word in query_words:
                if len(original_word) < 3:
                    continue
                
                # Проверяем, есть ли слово или его перевод в тексте
                word_found = False
                for search_word in search_words:
                    if search_word in full_text:
                        word_found = True
                        break
                
                if not word_found:
                    all_found = False
                    break
            
            if not all_found:
                continue
            
            # Считаем релевантность
            relevance = 0
            for search_word in search_words:
                if search_word in name_lower:
                    relevance += 10
                elif search_word in genres_lower:
                    relevance += 5
                elif search_word in description_lower:
                    relevance += 2
            
            # Бонус за точное совпадение с названием игры
            for original_word in query_words:
                if len(original_word) > 2 and original_word in name_lower:
                    relevance += 15
            
            popularity = game.get('popularity', 50)
            final_score = (relevance * 0.6) + (popularity * 0.4)
            
            if relevance > 0:
                scored.append((game, final_score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        seen_names = set()
        
        for game, final_score in scored[:n_results]:
            if game['name'] in seen_names:
                continue
            seen_names.add(game['name'])
            
            normalized_score = min(final_score / 50, 1.0)
            
            # РАБОЧИЙ URL КАРТИНКИ С STEAM CDN
            image_url = f"https://steamcdn-a.akamaihd.net/steam/apps/{game['game_id']}/header.jpg"
            
            results.append({
                "game_id": game['game_id'],
                "name": game['name'],
                "genres": game['genres'][:10],
                "description": game.get('description', '')[:300],
                "image_url": image_url,
                "price": game.get('price', 0),
                "relevance_score": normalized_score,
                "popularity": game.get('popularity', 50),
                "recommendation_type": "text_search"
            })
        
        logger.info(f"По запросу '{query}' найдено {len(results)} игр")
        
        for i, r in enumerate(results[:5]):
            logger.info(f"  {i+1}. {r['name']} (score: {r['relevance_score']:.2f})")
        
        return results