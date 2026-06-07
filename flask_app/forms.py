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
    user_id = StringField("ID пользователя (если есть)", validators=[Length(max=50)])
    genres = SelectMultipleField("Предпочитаемые жанры", choices=[], coerce=str)
    submit = SubmitField("Получить рекомендации")