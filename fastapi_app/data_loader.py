"""Загрузка и предобработка данных Steam из CSV и JSON файлов"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class SteamDataLoader:
    """Загрузчик данных Steam из CSV и JSON файлов"""

    def __init__(self, data_path: Path):
        self.data_path = Path(data_path)
        self.games_df: Optional[pd.DataFrame] = None
        self.interactions_df: Optional[pd.DataFrame] = None

    def load_games_from_csv(self, filename: str = "games.csv") -> pd.DataFrame:
        """
        Загрузка игр из CSV файла
        
        Ожидаемые колонки:
        - app_id/id: ID игры в Steam
        - name/title: Название игры
        - genres: Жанры (обычно строка с разделителями)
        - developers: Разработчики
        - publishers: Издатели
        - release_date: Дата релиза
        """
        csv_path = self.data_path / filename
        if not csv_path.exists():
            raise FileNotFoundError(f"Файл не найден: {csv_path}")
        
        logger.info(f"📂 Загрузка данных из {csv_path}")
        df = pd.read_csv(csv_path)
        logger.info(f"   Загружено {len(df)} игр")
        logger.info(f"   Колонки: {df.columns.tolist()}")
        
        # Определение названия колонки с ID игры
        id_col = None
        for col in ['app_id', 'id', 'steam_id', 'game_id', 'AppID', 'ID']:
            if col in df.columns:
                id_col = col
                break
        
        if id_col is None:
            raise ValueError("Не найдена колонка с ID игры")
        
        # Определение названия колонки с названием игры
        name_col = None
        for col in ['name', 'title', 'game_name', 'Name', 'GameName']:
            if col in df.columns:
                name_col = col
                break
        
        if name_col is None:
            name_col = id_col
        
        # Стандартизация названий колонок
        df.rename(columns={
            id_col: 'game_id',
            name_col: 'name'
        }, inplace=True)
        
        # Обработка жанров
        if 'genres' in df.columns:
            df['genres'] = df['genres'].fillna('')
            # Если жанры в формате JSON строки
            if df['genres'].astype(str).str.startswith('[').any():
                df['genres'] = df['genres'].apply(self._parse_genres_from_json)
            # Если жанры через запятую
            elif df['genres'].astype(str).str.contains(',').any():
                pass  # Оставляем как есть
        
        # Добавление колонки для поиска
        df['search_text'] = df['name'].fillna('') + ' ' + df.get('genres', '').fillna('')
        
        self.games_df = df
        return df

    def load_games_from_json(self, filename: str = "games.json") -> pd.DataFrame:
        """
        Загрузка игр из JSON файла (более детальная информация)
        """
        json_path = self.data_path / filename
        if not json_path.exists():
            logger.warning(f"⚠️ JSON файл не найден: {json_path}")
            return pd.DataFrame()
        
        logger.info(f"📂 Загрузка данных из {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Обработка разных форматов JSON
        if isinstance(data, dict):
            games_data = []
            for game_id, game_info in data.items():
                if isinstance(game_info, dict):
                    try:
                        game_info['game_id'] = int(game_id) if str(game_id).isdigit() else game_id
                    except (ValueError, TypeError):
                        game_info['game_id'] = game_id
                    games_data.append(game_info)
            df = pd.DataFrame(games_data)
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            logger.error(f"Неизвестный формат JSON: {type(data)}")
            return pd.DataFrame()
        
        logger.info(f"   Загружено {len(df)} игр из JSON")
        
        # Стандартизация колонок
        id_col = None
        for col in ['game_id', 'app_id', 'id', 'steam_id', 'AppID']:
            if col in df.columns:
                id_col = col
                break
        
        if id_col and id_col != 'game_id':
            df.rename(columns={id_col: 'game_id'}, inplace=True)
        
        # Объединение с CSV данными если они есть
        if self.games_df is not None:
            extra_cols = [col for col in df.columns if col not in self.games_df.columns and col != 'game_id']
            if extra_cols:
                logger.info(f"   Добавление колонок из JSON: {extra_cols}")
                self.games_df = self.games_df.merge(
                    df[['game_id'] + extra_cols], 
                    on='game_id', 
                    how='left'
                )
        else:
            self.games_df = df
        
        return self.games_df

    def _parse_genres_from_json(self, genres_str: str) -> str:
        """Парсинг жанров из JSON строки"""
        if pd.isna(genres_str) or not genres_str:
            return ''
        
        try:
            if isinstance(genres_str, str) and genres_str.startswith('['):
                genres_list = json.loads(genres_str)
                if isinstance(genres_list, list):
                    genre_names = []
                    for g in genres_list:
                        if isinstance(g, dict):
                            genre_names.append(g.get('name') or g.get('genre', str(g)))
                        else:
                            genre_names.append(str(g))
                    return ', '.join(genre_names)
            return genres_str
        except json.JSONDecodeError:
            return genres_str

    def generate_synthetic_interactions(self, n_users: int = 5000) -> pd.DataFrame:
        """
        Генерация синтетических взаимодействий пользователей с играми
        """
        if self.games_df is None:
            raise ValueError("Сначала загрузите данные игр")
        
        logger.info(f"🎮 Генерация синтетических взаимодействий для {n_users} пользователей...")
        
        # Создаем распределение популярности игр
        popularity_score = np.ones(len(self.games_df))
        
        if 'positive_ratings' in self.games_df.columns:
            pos_ratings = self.games_df['positive_ratings'].fillna(0)
            popularity_score += np.log1p(pos_ratings)
        
        if 'average_playtime' in self.games_df.columns:
            playtime = self.games_df['average_playtime'].fillna(0)
            popularity_score += np.log1p(playtime) * 0.3
        
        popularity_prob = popularity_score / popularity_score.sum()
        
        # Генерация взаимодействий
        interactions = []
        games_indices = list(range(len(self.games_df)))
        
        # Распределение количества игр на пользователя
        games_per_user = np.random.power(0.5, n_users) * 30 + 1
        games_per_user = games_per_user.astype(int)
        
        for user_id in range(1, n_users + 1):
            n_games = min(games_per_user[user_id - 1], len(games_indices))
            
            selected_indices = np.random.choice(
                games_indices,
                size=n_games,
                p=popularity_prob,
                replace=False
            )
            
            for idx in selected_indices:
                game_id = self.games_df.iloc[idx]['game_id']
                hours = min(np.random.exponential(10) + 0.5, 500)
                
                interactions.append({
                    'user_id': user_id,
                    'game_id': game_id,
                    'hours_played': round(hours, 1)
                })
        
        self.interactions_df = pd.DataFrame(interactions)
        logger.info(f"✅ Сгенерировано {len(self.interactions_df)} взаимодействий")
        logger.info(f"   Среднее игр на пользователя: {len(self.interactions_df) / n_users:.1f}")
        
        return self.interactions_df

    def get_game_info(self, game_id: int) -> Dict[str, Any]:
        """Получение информации об игре по ID"""
        if self.games_df is None:
            return {}
        
        game_row = self.games_df[self.games_df['game_id'] == game_id]
        if game_row.empty:
            return {}
        
        game = game_row.iloc[0].to_dict()
        
        # Преобразование для JSON
        for key, value in game.items():
            if pd.isna(value):
                game[key] = None
            elif isinstance(value, (np.integer, np.int64)):
                game[key] = int(value)
            elif isinstance(value, (np.floating, np.float64)):
                game[key] = float(value)
        
        return game

    def search_games(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Поиск игр по названию"""
        if self.games_df is None:
            return []
        
        mask = self.games_df['name'].str.contains(query, case=False, na=False)
        results = self.games_df[mask].head(limit)
        
        games = []
        for _, row in results.iterrows():
            games.append({
                'game_id': int(row['game_id']),
                'name': row['name'],
                'genres': row.get('genres', ''),
            })
        
        return games