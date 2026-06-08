import logging
import random
import json
import math

from collections import Counter
from pathlib import Path
from typing import List, Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)

class HybridRecommender:
    def __init__(self, alpha=0.7):
        self.alpha = alpha
        self.games_data = []
        self.word_weights = {}
    
    def is_adult_content(self, game: Dict) -> bool:
        """Проверка на 18+ по названию, жанрам и описанию"""
        name_lower = game.get('name', '').lower()
        genres_lower = ' '.join(game.get('genres', [])).lower()
        description_lower = game.get('description', '').lower()
        
        # Ищем везде
        full_text = f"{name_lower} {genres_lower} {description_lower}"
        
        adult_keywords = [
            'hentai', 'porn', 'sex', 'naked', 'nude', 'erotic', 'adult only',
            'xxx', 'nsfw', 'henta', 'ecchi', 'lewd', 'seduce',
            'порно', 'эротика', 'эротический', 'adult game',
            'sexual', 'masturbate', 'intercourse', 'orgasm', 'pussy', 'dick',
            'blowjob', 'handjob', 'strip', 'stripper', 'censor', 'uncensored',
            'boobs', 'boob', 'tits', 'breast', 'busty', 'cleavage', 'booty',
            'sexy girl', 'hot girl', 'anime girl', 'sexy zombie',
            'dating sim', 'waifu', 'harem', 'seduce', 'sensual',
            'mature content', 'adult content', 'explicit', 'nudity'
        ]
        
        for keyword in adult_keywords:
            if keyword in full_text:
                logger.info(f"Исключена игра '{game['name']}' (18+-контент: {keyword})")
                return True
        
        return False
    
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
            description = game_data.get('detailed_description', '') or game_data.get('short_description', '') or game_data.get('about_the_game', '')[:500]
            header_image = f"https://steamcdn-a.akamaihd.net/steam/apps/{app_id}/header.jpg"
            
            self.games_data.append({
                'game_id': int(app_id),
                'name': name,
                'genres': genres,
                'popularity': popularity,
                'price': float(price) if price else 0,
                'description': description[:500],
                'image_url': header_image,
                'release_date': game_data.get('release_date', '')
            })
            
            games_loaded += 1
            if games_loaded % 1000 == 0:
                logger.info(f"Прогресс: загружено {games_loaded} игр...")
        
        logger.info(f"Загружено {len(self.games_data)} игр из JSON")
        
        self._build_word_weights()

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

        self._build_word_weights()

        logger.info(
            f"Построены веса для {len(self.word_weights)} слов"
        )

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
        
        # Фильтруем порно-игры
        filtered_games = [game for game in self.games_data if not self.is_adult_content(game)]
        
        sorted_games = sorted(filtered_games, key=lambda x: x['popularity'], reverse=True)
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
        
        # Фильтруем порно-игры
        filtered_games = [game for game in self.games_data if not self.is_adult_content(game)]
        
        scored_games = []
        for game in filtered_games:
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
                "relevance_score": min(score / 100, 1.0),
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
        
        # Фильтруем порно-игры
        filtered_games = [game for game in self.games_data if not self.is_adult_content(game)]
        
        scored = []
        for game in filtered_games:
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
    
    def _build_word_weights(self):
        """Строим веса слов по всей базе игр"""

        logger.info("Подсчет весов слов...")

        word_counts = Counter()
        total_games = len(self.games_data)

        for game in self.games_data:

            words = set()

            words.update(
                w.lower()
                for w in game.get("genres", [])
            )

            description = (
                game.get("description", "") or ""
            ).lower()

            name = game["name"].lower()

            for word in name.split():
                if len(word) > 2:
                    words.add(word)

            for word in description.split():
                if len(word) > 2:
                    words.add(word)

            for word in words:
                word_counts[word] += 1

        self.word_weights = {}

        for word, count in word_counts.items():

            # IDF
            self.word_weights[word] = math.log(
                (total_games + 1) / (count + 1)
            )

        logger.info(
            f"Построены веса для {len(self.word_weights)} слов"
        )
    
    def search_by_text(
        self,
        query: str,
        n_results: int = 30
    ) -> List[Dict]:

        if not self.games_data:
            return []

        # Фильтруем порно-игры
        filtered_games = [game for game in self.games_data if not self.is_adult_content(game)]
        
        logger.info(f"Всего игр: {len(self.games_data)}, после фильтрации: {len(filtered_games)}")

        query_lower = query.lower()

        query_words = [
            w.strip()
            for w in query_lower.split()
            if len(w.strip()) > 2
        ]

        translations = {
            'стратегия': ['strategy', 'strategic', 'rts', 'tactical', 'tower defense', '4x'],
            'зомби': ['zombie', 'zombies', 'undead', 'infected', 'walking dead'],
            'симулятор': ['simulation', 'simulator'],
            'марс': ['mars'],
            'марсе': ['mars'],
            'космос': ['space'],
            'поселение': [
                'colony',
                'settlement',
                'base',
                'city'
            ],
            'колония': [
                'colony',
                'settlement',
                'base',
                'city'
            ],
            'постройка': [
                'building',
                'builder',
                'construction'
            ],
            'строительство': [
                'building',
                'builder',
                'construction'
            ],
            'выживание': [
                'survival'
            ]
        }

        search_terms = set()

        for word in query_words:

            search_terms.add(word)

            if word in translations:
                search_terms.update(
                    translations[word]
                )

        logger.info(
            f"Поиск '{query}' -> {search_terms}"
        )

        # Список известных игр с их ключевыми словами
        famous_games = {
            644930: {  # They Are Billions
                'keywords': ['strategy', 'zombie', 'survival', 'colony', 'base building'],
                'boost': 100
            },
            219980: {  # Zombie Tycoon 2
                'keywords': ['zombie', 'strategy', 'tycoon'],
                'boost': 80
            }
        }

        scored = []

        for game in filtered_games:

            name = game["name"].lower()

            genres = " ".join(
                game.get("genres", [])
            ).lower()

            description = (
                game.get("description", "") or ""
            ).lower()

            full_text = f"{name} {genres} {description}"
            
            score = 0
            matched_terms = 0

            # Проверка известных игр
            game_id = game["game_id"]
            boost = 0
            if game_id in famous_games:
                famous = famous_games[game_id]
                # Проверяем, соответствует ли игра запросу
                query_matches = 0
                for term in search_terms:
                    if term in full_text:
                        query_matches += 1
                if query_matches >= 2:  # Если есть хотя бы 2 совпадения
                    boost = famous['boost']
                    logger.info(f"Бонус для {game['name']}: +{boost}")

            for term in search_terms:

                weight = self.word_weights.get(
                    term,
                    3.0
                )

                if term in name:
                    score += weight * 20  # Увеличил вес названия
                    matched_terms += 1

                elif term in genres:
                    score += weight * 12  # Увеличил вес жанров
                    matched_terms += 1

                if term in description:
                    score += weight * 12  # Увеличил вес описания
                    matched_terms += 1

            # Добавляем бонус за известные игры
            score += boost
            
            if matched_terms == 0:
                continue

            # покрытие запроса
            coverage = (
                matched_terms /
                max(len(search_terms), 1)
            )

            score *= coverage

            # бонус популярности
            score += (
                game.get("popularity", 50)
                * 0.15
            )

            scored.append(
                (game, score)
            )

        scored.sort(
            key=lambda x: x[1],
            reverse=True
        )

        # Нормализуем score для отображения
        max_score = max([s for _, s in scored[:n_results]]) if scored else 1

        results = []

        for game, score in scored[:n_results]:

            normalized_score = min(score / max_score, 1.0)

            results.append({
                "game_id": game["game_id"],
                "name": game["name"],
                "genres": game["genres"][:10],
                "description": (
                    game.get("description", "")[:200]
                ),
                "image_url":
                    f"https://steamcdn-a.akamaihd.net/steam/apps/{game['game_id']}/header.jpg",
                "price": game.get("price", 0),
                "relevance_score": normalized_score,
                "popularity": game.get(
                    "popularity",
                    50
                ),
                "recommendation_type":
                    "text_search"
            })

        logger.info(
            f"Найдено {len(results)} игр"
        )
        
        # Логируем топ-5 результатов
        for i, r in enumerate(results[:5]):
            logger.info(f"  {i+1}. {r['name']} (score: {r['relevance_score']:.2f})")

        return results