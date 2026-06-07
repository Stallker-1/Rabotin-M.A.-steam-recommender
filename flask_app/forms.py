from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectMultipleField
from wtforms.validators import DataRequired, Length

class RegistrationForm(FlaskForm):
    username = StringField("Имя пользователя", validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField("Пароль", validators=[DataRequired(), Length(min=6, max=100)])
    submit = SubmitField("Зарегистрироваться")

class LoginForm(FlaskForm):
    username = StringField("Имя пользователя", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    submit = SubmitField("Войти")

class RecommendForm(FlaskForm):
    # Убираем поле user_id, оставляем только жанры
    genres = SelectMultipleField(
        "Предпочитаемые жанры",
        choices=[
            ('Action', '🎮 Action'),
            ('RPG', '⚔️ RPG'),
            ('Strategy', '🎯 Strategy'),
            ('Adventure', '🗺️ Adventure'),
            ('Indie', '🎨 Indie'),
            ('Simulation', '🏭 Simulation'),
            ('Sports', '⚽ Sports'),
            ('Puzzle', '🧩 Puzzle'),
            ('Horror', '👻 Horror'),
            ('Fighting', '🥊 Fighting'),
            ('Shooter', '🔫 Shooter'),
            ('Racing', '🏎️ Racing'),
            ('Casual', '😊 Casual'),
            ('MMO', '🌍 MMO')
        ],
        coerce=str,
        default=[]
    )
    submit = SubmitField("🎮 Получить рекомендации")

class TextSearchForm(FlaskForm):
    query = StringField("Поиск игр", validators=[DataRequired(), Length(min=2, max=200)])
    genres_filter = SelectMultipleField("Фильтр по жанрам (опционально)", 
                                         choices=[('Strategy', 'Стратегии'), 
                                                  ('Zombie', 'Зомби'),
                                                  ('RPG', 'RPG'),
                                                  ('Action', 'Экшен'),
                                                  ('Survival', 'Выживание'),
                                                  ('Horror', 'Ужасы')],
                                         coerce=str)
    submit = SubmitField("🔍 Найти игры")